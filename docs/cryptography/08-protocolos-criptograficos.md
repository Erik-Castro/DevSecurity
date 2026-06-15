# Capítulo 08 — Protocolos Criptográficos Modernos

> *"Um protocolo criptográfico é como uma receita de bolo: se você troca a ordem dos ingredientes ou pula um passo, o resultado pode ser desastroso — mesmo que cada ingrediente individual seja perfeito."*
> — adapted from Ross Anderson, *Security Engineering*

---

## Sumário

1. [Objetivos de Aprendizado](#objetivos-de-aprendizado)
2. [Signal Protocol: X3DH, Double Ratchet, Sesame](#signal-protocol-x3dh-double-ratchet-sesame)
3. [OPAQUE: Password-Authenticated Key Exchange](#opaque-password-authenticated-key-exchange)
4. [Noise Protocol Framework: Handshake Patterns](#noise-protocol-framework-handshake-patterns)
5. [WireGuard: Modern VPN Protocol](#wireguard-modern-vpn-protocol)
6. [IPSec/IKEv2: Estado Atual](#ipsecikev2-estado-atual)
7. [SSH Protocol: Boas Práticas Modernas](#ssh-protocol-boas-práticas-modernas)
8. [Noise Protocol Patterns em C++ com libsodium](#noise-protocol-patterns-em-c-com-libsodium)
9. [CVEs em Protocolos Criptográficos](#cves-em-protocolos-criptográficos)
10. [Verificação Formal de Protocolos](#verificação-formal-de-protocolos)
11. [Exercícios](#exercícios)
12. [Referências](#referências)

---

## Objetivos de Aprendizado

Ao final deste capítulo, você será capaz de:

1. **Analisar** o design do Signal Protocol e entender por que X3DH e Double Ratchet proporcionam forward secrecy e post-compromise security
2. **Implementar** o protocolo OPAQUE para autenticação baseada em senha sem revelar a senha ao servidor
3. **Projetar** handshake patterns usando o Noise Protocol Framework
4. **Compreender** a arquitetura do WireGuard e suas escolhas de design minimalistas
5. **Avaliar** IPSec/IKEv2 e entender suas vulnerabilidades documentadas
6. **Implementar** padrões Noise em C++ usando libsodium
7. **Analisar** CVEs reais em protocolos criptográficos (CVE-2020-26139, CVE-2023-0286, CVE-2021-3449)
8. **Aplicar** ferramentas de verificação formal (ProVerif, Tamarin) para validar protocolos

### Por Que Protocolos Importam

A maioria dos engenheiros trata protocolos criptográficos como caixas-pretas. Eles chamam `ssl_connect()` ou `wireguard-quick()` e esperam que a mágica aconteça. Mas a história da segurança está repleta de exemplos onde o protocolo — não o algoritmo — era o ponto fraco:

| Vulnerabilidade | Falha | Algoritmo | Protocolo |
|-----------------|-------|-----------|-----------|
| POODLE | Padding oracle | 3DES (seguro) | SSL 3.0 (fraco) |
| FREAK | Export downgrade | RSA (seguro) | TLS (versão antiga) |
| Logjam | Weak DH | DSA (seguro) | TLS (parâmetros fracos) |
| Triple Handshake | Binding flaw | AES (seguro) | TLS 1.2 (design flaw) |
| Downgrade Attack | Version negotiation | AES (seguro) | TLS 1.2 |

A lição é clara: **ter um algoritmo seguro não garante que o protocolo é seguro.** Um protocolo pode combinar algoritmos perfeitos de forma que introduza vulnerabilidades.

### O que este capítulo não cobre

Este capítulo foca em protocolos de aplicação e transporte. Para TLS 1.3 em profundidade, veja o Capítulo 05. Para side-channel attacks em implementações de protocolos, veja o Capítulo 03. Para hardware security modules usados com protocolos, veja o Capítulo 04.

---

## Signal Protocol: X3DH, Double Ratchet, Sesame

### Visão Geral

O Signal Protocol é o protocolo de mensageria segura mais influente da última década. Ele combina quatro componentes principais para garantir confidencialidade, autenticidade, forward secrecy e post-compromise security:

1. **X3DH (Extended Triple Diffie-Hellman)**: Key agreement inicial entre Alice e Bob
2. **Double Ratchet**: Atualização contínua de chaves para cada mensagem
3. **Signal Protocol Sessions**: Gerenciamento de sessões e retransmissão
4. **Sesame**: Gerenciamento de dispositivos múltiplos

O protocolo é usado por Signal, WhatsApp, Facebook Messenger (modo secreto), Google Messages e dezenas de outros aplicativos.

### X3DH: Extended Triple Diffie-Hellman

#### O Problema

Alice quer iniciar uma conversa segura com Bob, mas:
- Bob está offline (não pode responder imediatamente)
- Alice não tem certeza de que está falando com o Bob certo (autenticação)
- Se a chave de Bob for comprometida amanhã, mensagens de hoje não devem ser comprometidas (forward secrecy)

X3DH resolve todos esses problemas simultaneamente.

#### Geração de Chaves

Cada usuário gera três pares de chaves:

```cpp
#include <sodium.h>
#include <array>
#include <vector>

struct IdentityKey {
    std::array<uint8_t, crypto_sign_PUBLICKEYBYTES> public_key;
    std::array<uint8_t, crypto_sign_SECRETKEYBYTES> secret_key;
};

struct SignedPreKey {
    std::array<uint8_t, crypto_sign_PUBLICKEYBYTES> public_key;
    std::array<uint8_t, crypto_sign_SECRETKEYBYTES> secret_key;
    uint32_t key_id;
};

struct OneTimePreKey {
    std::array<uint8_t, crypto_box_PUBLICKEYBYTES> public_key;
    std::array<uint8_t, crypto_box_SECRETKEYBYTES> secret_key;
    uint32_t key_id;
};

struct KeyBundle {
    IdentityKey identity;
    SignedPreKey signed_prekey;
    std::vector<OneTimePreKey> one_time_prekeys;
};

KeyBundle generate_key_bundle() {
    KeyBundle bundle;

    // Identity Key pair (long-term, used for signing)
    crypto_sign_keypair(
        bundle.identity.public_key.data(),
        bundle.identity.secret_key.data()
    );

    // Signed PreKey (medium-term, rotated periodically)
    crypto_box_keypair(
        bundle.signed_prekey.public_key.data(),
        bundle.signed_prekey.secret_key.data()
    );
    bundle.signed_prekey.key_id = 1;

    // Sign the signed prekey with identity key
    // This proves the signed prekey belongs to this identity
    uint8_t signed_prekey_bytes[crypto_sign_PUBLICKEYBYTES];
    std::memcpy(signed_prekey_bytes,
                bundle.signed_prekey.public_key.data(),
                crypto_sign_PUBLICKEYBYTES);

    unsigned long long signed_msg_len;
    uint8_t signed_msg[crypto_sign_PUBLICKEYBYTES + crypto_sign_BYTES];
    crypto_sign_detached(
        signed_msg, &signed_msg_len,
        signed_prekey_bytes, crypto_sign_PUBLICKEYBYTES,
        bundle.identity.secret_key.data()
    );

    // One-time prekeys (pre-uploaded, used once)
    for (int i = 0; i < 100; ++i) {
        OneTimePreKey otpk;
        crypto_box_keypair(
            otpk.public_key.data(),
            otpk.secret_key.data()
        );
        otpk.key_id = static_cast<uint32_t>(i);
        bundle.one_time_prekeys.push_back(std::move(otpk));
    }

    return bundle;
}
```

#### O Handshake X3DH

```
Alice (Initiadora)                          Bob (Receptor)
    |                                           |
    |  Public keys:                              |
    |  IK_A = identity key (long-term)          |  IK_B = identity key (long-term)
    |  SPK_B = signed prekey (medium-term)      |  SPK_B = signed prekey
    |  OTPK_B = one-time prekey (ephemeral)     |  OTPK_B = one-time prekey
    |                                           |
    |  Alice gera ephemeral key:                |
    |  EK_A = ephemeral key (ephemeral)         |
    |                                           |
    |  Shared secrets:                           |
    |  DH1 = DH(IK_A, SPK_B)                   |
    |  DH2 = DH(EK_A, IK_B)                    |
    |  DH3 = DH(EK_A, SPK_B)                   |
    |  DH4 = DH(EK_A, OTPK_B)                  |
    |                                           |
    |  SK = KDF(DH1 || DH2 || DH3 || DH4)      |
    |                                           |
    |--- [IK_A, EK_A, {IK_B, SPK_B, OTPK_B}] ->|
    |                                           |  Bob calcula os mesmos DHs
    |                                           |  e deriva SK
```

#### Implementação X3DH em C++

```cpp
#include <sodium.h>
#include <array>
#include <vector>
#include <cstring>
#include <stdexcept>

struct X3DHKeys {
    std::array<uint8_t, crypto_kx_PUBLICKEYBYTES> public_key;
    std::array<uint8_t, crypto_kx_SECRETKEYBYTES> secret_key;
};

struct X3DHResult {
    std::array<uint8_t, 32> shared_secret;
    std::array<uint8_t, crypto_kx_PUBLICKEYBYTES> ephemeral_public;
};

class X3DHInitiator {
public:
    X3DHKeys initiator_keys;

    X3DHInitiator() {
        if (crypto_kx_keypair(
                initiator_keys.public_key.data(),
                initiator_keys.secret_key.data()) != 0) {
            throw std::runtime_error("Failed to generate initiator keys");
        }
    }

    X3DHResult perform_handshake(
        const std::array<uint8_t, crypto_kx_PUBLICKEYBYTES>& bob_identity,
        const std::array<uint8_t, crypto_kx_PUBLICKEYBYTES>& bob_spk,
        const std::array<uint8_t, crypto_kx_PUBLICKEYBYTES>& bob_otpk
    ) {
        // Generate ephemeral key pair
        X3DHKeys ephemeral;
        if (crypto_kx_keypair(
                ephemeral.public_key.data(),
                ephemeral.secret_key.data()) != 0) {
            throw std::runtime_error("Failed to generate ephemeral keys");
        }

        // Compute four DH shared secrets
        std::array<uint8_t, crypto_kx_SESSIONKEYBYTES> dh1, dh2, dh3, dh4;

        // DH1 = DH(IK_A, SPK_B)
        if (crypto_kx_deterministic_shared_key(
                dh1.data(),
                initiator_keys.secret_key.data(),
                bob_spk.data()) != 0) {
            throw std::runtime_error("DH1 failed");
        }

        // DH2 = DH(EK_A, IK_B)
        if (crypto_kx_deterministic_shared_key(
                dh2.data(),
                ephemeral.secret_key.data(),
                bob_identity.data()) != 0) {
            throw std::runtime_error("DH2 failed");
        }

        // DH3 = DH(EK_A, SPK_B)
        if (crypto_kx_deterministic_shared_key(
                dh3.data(),
                ephemeral.secret_key.data(),
                bob_spk.data()) != 0) {
            throw std::runtime_error("DH3 failed");
        }

        // DH4 = DH(EK_A, OTPK_B)
        if (crypto_kx_deterministic_shared_key(
                dh4.data(),
                ephemeral.secret_key.data(),
                bob_otpk.data()) != 0) {
            throw std::runtime_error("DH4 failed");
        }

        // Combine DH results using HKDF
        // SK = HKDF(DH1 || DH2 || DH3 || DH4, "X3DH_shared_key")
        std::vector<uint8_t> dh_concat;
        dh_concat.insert(dh_concat.end(), dh1.begin(), dh1.end());
        dh_concat.insert(dh_concat.end(), dh2.begin(), dh2.end());
        dh_concat.insert(dh_concat.end(), dh3.begin(), dh3.end());
        dh_concat.insert(dh_concat.end(), dh4.begin(), dh4.end());

        X3DHResult result;
        const std::string info = "X3DH_shared_key";
        crypto_kdf_derive_from_key(
            result.shared_secret.data(), 32,
            0,
            reinterpret_cast<const uint8_t*>(info.data()),
            info.size(),
            dh_concat.data()
        );

        result.ephemeral_public = ephemeral.public_key;
        return result;
    }
};
```

#### Propriedades de Segurança do X3DH

| Propriedade | Como X3DH fornece |
|-------------|-------------------|
| Confidencialidade | Todas as 4 DH são combinadas; comprometer uma não revela a chave final |
| Autenticação | Alice assina a mensagem com sua Identity Key |
| Forward Secrecy | OTPK de Bob é usada uma vez e descartada |
| Offline attack resistance | Atacante precisa comprometer IK_B E SPK_B simultaneamente |
| Deniability | Nenhuma assinatura criptográfica liga Alice a Bob |

### Double Ratchet

O Double Ratchet é o mecanismo que fornece forward secrecy contínua após o handshake X3DH. Ele combina dois "ratchets" (chaves de tração):

1. **Diffie-Hellman Ratchet**: Atualiza as chaves com base em novos trocas DH
2. **Symmetric Ratchet**: Deriva chaves de mensagens usando HKDF

#### O Conceito de Ratchet

Pense em um ratchet como uma chave de fenda que só gira para frente. Cada mensagem gera uma nova chave de criptografia, e as chaves anteriores são descartadas. Mesmo que um atacante comprometa a chave atual, ele não consegue decifrar mensagens anteriores.

```
Alice                                          Bob
  |                                              |
  |-- msg 1 (key_1) --------------------------->|
  |-- msg 2 (key_2) --------------------------->|
  |<-------- msg 3 (key_3) ---------------------|
  |-- msg 4 (key_4) --------------------------->|
  |                                              |
  |  key_1 = HKDF(root, "ratchet_1")           |
  |  key_2 = HKDF(root, "ratchet_2")           |
  |  key_3 = HKDF(root, "ratchet_3")           |
  |  key_4 = HKDF(root, "ratchet_4")           |
```

#### Implementação do Double Ratchet

```cpp
#include <sodium.h>
#include <array>
#include <vector>
#include <cstdint>

struct RatchetState {
    // Current chain key for symmetric ratchet
    std::array<uint8_t, 32> chain_key;

    // Root key for DH ratchet
    std::array<uint8_t, 32> root_key;

    // Current DH key pair
    std::array<uint8_t, crypto_kx_PUBLICKEYBYTES> dh_public;
    std::array<uint8_t, crypto_kx_SECRETKEYBYTES> dh_secret;

    // Remote DH public key
    std::array<uint8_t, crypto_kx_PUBLICKEYBYTES> remote_dh_public;

    // Message counters
    uint32_t send_counter;
    uint32_t receive_counter;

    // Pending message keys for out-of-order delivery
    struct PendingKey {
        uint32_t counter;
        std::array<uint8_t, 32> message_key;
    };
    std::vector<PendingKey> pending_keys;
};

class DoubleRatchet {
public:
    DoubleRatchetState state;

    void initialize_with_shared_secret(
        const std::array<uint8_t, 32>& shared_secret,
        const std::array<uint8_t, crypto_kx_PUBLICKEYBYTES>& remote_public
    ) {
        // Generate initial DH key pair
        crypto_kx_keypair(
            state.dh_public.data(),
            state.dh_secret.data()
        );

        state.root_key = shared_secret;
        state.remote_dh_public = remote_public;
        state.send_counter = 0;
        state.receive_counter = 0;

        // Perform initial DH ratchet step
        dh_ratchet_step();
    }

    // Encrypt a message
    std::vector<uint8_t> encrypt(const std::vector<uint8_t>& plaintext) {
        // Derive message key from chain key
        auto message_key = derive_message_key();

        // Advance chain key
        advance_chain_key();

        // Increment send counter
        state.send_counter++;

        // Encrypt with XChaCha20-Poly1305
        std::vector<uint8_t> ciphertext(
            plaintext.size() + crypto_aead_xchacha20poly1305_ietf_ABYTES
        );

        // Nonce = counter + random bytes for additional security
        std::array<uint8_t, 24> nonce;
        randombytes_buf(nonce.data(), nonce.size());

        unsigned long long ciphertext_len;
        crypto_aead_xchacha20poly1305_ietf_encrypt(
            ciphertext.data(), &ciphertext_len,
            plaintext.data(), plaintext.size(),
            nullptr, 0, nullptr,
            nonce.data(), message_key.data()
        );

        ciphertext.resize(ciphertext_len);

        // Prepend counter to ciphertext
        std::vector<uint8_t> result;
        result.reserve(sizeof(uint32_t) + nonce.size() + ciphertext.size());

        // Counter (4 bytes, little-endian)
        result.push_back(state.send_counter & 0xFF);
        result.push_back((state.send_counter >> 8) & 0xFF);
        result.push_back((state.send_counter >> 16) & 0xFF);
        result.push_back((state.send_counter >> 24) & 0xFF);

        // Nonce
        result.insert(result.end(), nonce.begin(), nonce.end());

        // Ciphertext
        result.insert(result.end(), ciphertext.begin(), ciphertext.end());

        return result;
    }

    // Decrypt a message
    std::vector<uint8_t> decrypt(const std::vector<uint8_t>& message) {
        if (message.size() < sizeof(uint32_t) + 24 + crypto_aead_xchacha20poly1305_ietf_ABYTES) {
            throw std::runtime_error("Message too short");
        }

        // Extract counter
        uint32_t counter = message[0] | (message[1] << 8) |
                          (message[2] << 16) | (message[3] << 24);

        // Extract nonce
        std::array<uint8_t, 24> nonce;
        std::memcpy(nonce.data(), message.data() + 4, 24);

        // Extract ciphertext
        size_t ciphertext_offset = 4 + 24;
        size_t ciphertext_len = message.size() - ciphertext_offset;
        const uint8_t* ciphertext = message.data() + ciphertext_offset;

        // Skip messages with counter < receive_counter
        // (already received)
        if (counter < state.receive_counter) {
            throw std::runtime_error("Message counter too low");
        }

        // If counter > receive_counter, we need to advance the chain
        // to catch up (this handles out-of-order delivery)
        auto message_key = get_or_derive_message_key(counter);

        // Decrypt
        std::vector<uint8_t> plaintext(ciphertext_len);
        unsigned long long plaintext_len;

        if (crypto_aead_xchacha20poly1305_ietf_decrypt(
                plaintext.data(), &plaintext_len,
                nullptr,
                ciphertext, ciphertext_len,
                nullptr, 0,
                nonce.data(),
                message_key.data()) != 0) {
            throw std::runtime_error("Decryption failed");
        }

        plaintext.resize(plaintext_len);

        // Update receive counter
        if (counter >= state.receive_counter) {
            state.receive_counter = counter + 1;
        }

        return plaintext;
    }

private:
    std::array<uint8_t, 32> derive_message_key() {
        // HKDF-Expand using libsodium's key derivation
        std::array<uint8_t, 32> message_key;
        const std::string subkey = "message_key";

        crypto_kdf_derive_from_key(
            message_key.data(), 32,
            1,
            reinterpret_cast<const uint8_t*>(subkey.data()),
            subkey.size(),
            state.chain_key.data()
        );

        return message_key;
    }

    void advance_chain_key() {
        // Chain key = HKDF(chain_key, "chain_key_advance")
        std::array<uint8_t, 32> new_chain_key;
        const std::string subkey = "chain_key_advance";

        crypto_kdf_derive_from_key(
            new_chain_key.data(), 32,
            2,
            reinterpret_cast<const uint8_t*>(subkey.data()),
            subkey.size(),
            state.chain_key.data()
        );

        state.chain_key = new_chain_key;
    }

    std::array<uint8_t, 32> get_or_derive_message_key(uint32_t counter) {
        // Check if we have a cached message key
        for (auto& pk : state.pending_keys) {
            if (pk.counter == counter) {
                auto key = pk.message_key;
                state.pending_keys.erase(
                    std::remove_if(
                        state.pending_keys.begin(),
                        state.pending_keys.end(),
                        [counter](const auto& p) { return p.counter == counter; }
                    ),
                    state.pending_keys.end()
                );
                return key;
            }
        }

        // Derive key by advancing chain
        while (state.receive_counter <= counter) {
            auto mk = derive_message_key();
            advance_chain_key();

            if (state.receive_counter == counter) {
                return mk;
            }

            // Cache the key for potential future use
            RatchetState::PendingKey pk;
            pk.counter = state.receive_counter;
            pk.message_key = mk;
            state.pending_keys.push_back(pk);
            state.receive_counter++;
        }

        throw std::runtime_error("Could not derive message key");
    }

    void dh_ratchet_step() {
        // Generate new DH key pair
        std::array<uint8_t, crypto_kx_PUBLICKEYBYTES> new_public;
        std::array<uint8_t, crypto_kx_SECRETKEYBYTES> new_secret;
        crypto_kx_keypair(new_public.data(), new_secret.data());

        // Perform DH with remote public key
        std::array<uint8_t, crypto_kx_SESSIONKEYBYTES> dh_result;
        crypto_kx_deterministic_shared_key(
            dh_result.data(),
            state.dh_secret.data(),
            state.remote_dh_public.data()
        );

        // Derive new root key and chain key
        std::array<uint8_t, 32> new_root, new_chain;
        const std::string root_info = "root_key";
        const std::string chain_info = "chain_key";

        crypto_kdf_derive_from_key(
            new_root.data(), 32,
            3,
            reinterpret_cast<const uint8_t*>(root_info.data()),
            root_info.size(),
            dh_result.data()
        );

        crypto_kdf_derive_from_key(
            new_chain.data(), 32,
            4,
            reinterpret_cast<const uint8_t*>(chain_info.data()),
            chain_info.size(),
            dh_result.data()
        );

        state.root_key = new_root;
        state.chain_key = new_chain;
        state.dh_public = new_public;
        state.dh_secret = new_secret;
    }
};
```

#### Propriedades do Double Ratchet

| Propriedade | Mecanismo | Impacto Prático |
|-------------|-----------|-----------------|
| Forward Secrecy | Chain key é derivada e descartada | Comprometimento atual não revela passado |
| Break-in Recovery | DH ratchet renova chaves periodicamente | Comprometimento temporário é recuperado |
| Out-of-order delivery | Cache de message keys | Mensagens podem chegar fora de ordem |
| Message independence | Cada mensagem usa chave única | Comprometer uma mensagem não compromete outras |

### Sesame: Gerenciamento de Dispositivos

Sesame resolve o problema de múltiplos dispositivos. Cada dispositivo mantém sua própria sessão Double Ratchet com o servidor, e o servidor encaminha mensagens entre dispositivos.

```
Alice (Phone)        Server         Alice (Laptop)
    |                   |                   |
    |-- [msg] -------->|                   |
    |                   |-- [msg] -------->|
    |                   |                   |
    |  Device keys:     |                   |
    |  DK_phone (long)  |                   |
    |  DK_laptop (long) |                   |
    |                   |                   |
    |  Each device has  |                   |
    |  independent      |                   |
    |  Double Ratchet   |                   |
```

#### Implementação Simplificada de Sesame

```cpp
#include <sodium.h>
#include <array>
#include <map>
#include <vector>
#include <string>

struct DeviceIdentity {
    uint64_t device_id;
    std::array<uint8_t, crypto_kx_PUBLICKEYBYTES> public_key;
    std::array<uint8_t, crypto_kx_SECRETKEYBYTES> secret_key;
    std::string device_name;
};

class SesameManager {
public:
    uint64_t local_device_id;

    bool add_device(const DeviceIdentity& device) {
        if (devices_.count(device.device_id)) {
            return false; // Device already registered
        }
        devices_[device.device_id] = device;
        return true;
    }

    bool remove_device(uint64_t device_id) {
        if (device_id == local_device_id) {
            return false; // Cannot remove self
        }
        return devices_.erase(device_id) > 0;
    }

    std::vector<uint8_t> create_encrypted_message(
        uint64_t sender_device_id,
        const std::vector<uint8_t>& plaintext
    ) {
        // Verify sender is registered
        if (!devices_.count(sender_device_id)) {
            throw std::runtime_error("Unknown sender device");
        }

        // Encrypt with sender's device key
        const auto& sender = devices_[sender_device_id];

        // Use AEAD encryption
        std::vector<uint8_t> ciphertext(
            plaintext.size() + crypto_aead_xchacha20poly1305_ietf_ABYTES
        );

        std::array<uint8_t, 24> nonce;
        randombytes_buf(nonce.data(), nonce.size());

        unsigned long long ciphertext_len;
        crypto_aead_xchacha20poly1305_ietf_encrypt(
            ciphertext.data(), &ciphertext_len,
            plaintext.data(), plaintext.size(),
            nullptr, 0, nullptr,
            nonce.data(), sender.secret_key.data()
        );

        ciphertext.resize(ciphertext_len);

        // Prepend device ID
        std::vector<uint8_t> result;
        result.resize(sizeof(uint64_t));
        std::memcpy(result.data(), &sender_device_id, sizeof(uint64_t));
        result.insert(result.end(), nonce.begin(), nonce.end());
        result.insert(result.end(), ciphertext.begin(), ciphertext.end());

        return result;
    }

    std::vector<uint8_t> decrypt_message(const std::vector<uint8_t>& message) {
        if (message.size() < sizeof(uint64_t) + 24) {
            throw std::runtime_error("Invalid message format");
        }

        // Extract sender device ID
        uint64_t sender_id;
        std::memcpy(&sender_id, message.data(), sizeof(uint64_t));

        if (!devices_.count(sender_id)) {
            throw std::runtime_error("Unknown sender device");
        }

        const auto& sender = devices_[sender_id];

        // Extract nonce and ciphertext
        std::array<uint8_t, 24> nonce;
        std::memcpy(nonce.data(), message.data() + sizeof(uint64_t), 24);

        size_t ciphertext_offset = sizeof(uint64_t) + 24;
        size_t ciphertext_len = message.size() - ciphertext_offset;
        const uint8_t* ciphertext = message.data() + ciphertext_offset;

        // Decrypt
        std::vector<uint8_t> plaintext(ciphertext_len);
        unsigned long long plaintext_len;

        if (crypto_aead_xchacha20poly1305_ietf_decrypt(
                plaintext.data(), &plaintext_len,
                nullptr,
                ciphertext, ciphertext_len,
                nullptr, 0,
                nonce.data(),
                sender.secret_key.data()) != 0) {
            throw std::runtime_error("Decryption failed");
        }

        plaintext.resize(plaintext_len);
        return plaintext;
    }

    size_t device_count() const {
        return devices_.size();
    }

private:
    std::map<uint64_t, DeviceIdentity> devices_;
};
```

### Ataques Contra o Signal Protocol

Embora o Signal Protocol seja considerado o estado da arte em mensageria segura, existem vetores de ataque:

| Vetor de Ataque | Descrição | Mitigção |
|-----------------|-----------|----------|
| Device theft | Acesso físico ao dispositivo | Keychain lock, biometria |
| Malicious server | Servidor tenta MITM | Trust On First Use (TOFU) |
| Registration attack | Atacante registra número de vítima | Safety numbers, vereficação |
| Metadata leakage | Quem comunica com quem, quando | Sealed Sender, GCMP |
| Backup leakage | Backups de nuvem sem criptografia | E2E encrypted backups |

---

## OPAQUE: Password-Authenticated Key Exchange

### O Que é OPAQUE

OPAQUE é um protocolo de Password-Authenticated Key Exchange (PAKE) que permite que Alice e Bob estabeleçam uma chave compartilhada baseada em uma senha, sem que a senha seja revelada ao servidor.

Diferentemente do SRP (Secure Remote Password), OPAQUE é:
- **Provavelmente seguro** (provado no modelo UC — Universal Composability)
- **Resistente a offline dictionary attacks** mesmo quando o servidor é comprometido
- **Não requer salt no servidor** (o "envelope" protege a senha)

### O Problema que OPAQUE Resolve

Quando você faz login em um site, normalmente acontece:

```
Client                          Server
  |--- password_hash(password) ->|
  |                              |  Verifica hash armazenado
  |<-- success/failure ---------|
```

Isso é INSEGURO porque:
1. O servidor armazena o hash da senha
2. Se o servidor for comprometido, o atacante pode fazer offline dictionary attack
3. O servidor pode ver a senha em texto claro (em protocolos antigos)

OPAQUE resolve isso com um protocolo de duas fases:

### Fase 1: Registration (com Oblivious PRF)

```
Client (Alice)                Server
    |                            |
    |  pwd = senha do usuário    |
    |  r = random blinding factor|
    |                            |
    |  masked_pwd = OPRF(pwd, r) |
    |                            |
    |--- masked_pwd ----------->|
    |                            |  armazena masked_pwd
    |                            |  (não pode recuperar pwd)
    |<-- envelope -----------   |
    |                            |
    |  envelope = encrypt(pwd,   |
    |    server_public_key)      |
    |                            |
```

### Fase 2: Authentication

```
Client (Alice)                Server
    |                            |
    |  pwd = senha do usuário    |
    |  r = new blinding factor   |
    |                            |
    |  masked_pwd = OPRF(pwd, r) |
    |                            |
    |--- masked_pwd ----------->|
    |                            |  verifica masked_pwd
    |<-- envelope -----------   |
    |                            |
    |  key = derive(pwd, envelope)|
    |  auth = MAC(key, "client") |
    |                            |
    |--- auth ---------------->|
    |                            |  verifica MAC
    |<-- server_auth ----------|
    |                            |
```

### Implementação OPAQUE com libsodium

```cpp
#include <sodium.h>
#include <array>
#include <vector>
#include <string>
#include <stdexcept>

struct OpaqueEnvelope {
    std::array<uint8_t, 32> encrypted_key;
    std::array<uint8_t, 32> nonce;
    std::array<uint8_t, crypto_sign_BYTES> server_signature;
};

struct OpaqueRegistration {
    std::array<uint8_t, 32> blinded_element;
    std::array<uint8_t, 32> public_key;
};

class OpaqueClient {
public:
    OpaqueClient() {
        if (sodium_init() < 0) {
            throw std::runtime_error("Failed to initialize libsodium");
        }
    }

    // Step 1: Create registration request
    std::array<uint8_t, 32> create_registration_request(
        const std::string& password
    ) {
        // Derive a key from the password
        std::array<uint8_t, 32> password_key;
        crypto_pwhash(
            password_key.data(), 32,
            password.c_str(), password.size(),
            crypto_pwhash_OPSLIMIT_SENSITIVE,
            crypto_pwhash_MEMLIMIT_SENSITIVE,
            crypto_pwhash_ALG_ARGON2ID13
        );

        // Generate random blinding factor
        std::array<uint8_t, 32> blinding_factor;
        randombytes_buf(blinding_factor.data(), 32);

        // Compute OPRF (simplified for illustration)
        // In production, use the full OPAQUE protocol
        std::array<uint8_t, 32> blinded_element;
        compute_blinded_element(
            password_key.data(),
            blinding_factor.data(),
            blinded_element.data()
        );

        // Store blinding factor for later
        stored_blinding_factor_ = blinding_factor;
        stored_password_key_ = password_key;

        return blinded_element;
    }

    // Step 2: Process server response
    OpaqueEnvelope process_registration_response(
        const OpaqueRegistration& server_response
    ) {
        // Store server's public key
        server_public_key_ = server_response.public_key;

        // Complete the OPRF computation
        std::array<uint8_t, 32> oprf_output;
        complete_oprf(
            stored_blinding_factor_.data(),
            server_response.blinded_element.data(),
            oprf_output.data()
        );

        // Derive envelope key
        std::array<uint8_t, 32> envelope_key;
        crypto_kdf_derive_from_key(
            envelope_key.data(), 32,
            1,
            reinterpret_cast<const uint8_t*>("opaque_envelope"),
            15,
            oprf_output.data()
        );

        // Encrypt password-derived key as envelope
        OpaqueEnvelope envelope;
        randombytes_buf(envelope.nonce.data(), 32);

        unsigned long long encrypted_len;
        crypto_aead_xchacha20poly1305_ietf_encrypt(
            envelope.encrypted_key.data(), &encrypted_len,
            stored_password_key_.data(), 32,
            nullptr, 0, nullptr,
            envelope.nonce.data(),
            envelope_key.data()
        );

        return envelope;
    }

    // Authentication step
    std::array<uint8_t, 32> authenticate(
        const std::string& password
    ) {
        // Derive password key again
        std::array<uint8_t, 32> password_key;
        crypto_pwhash(
            password_key.data(), 32,
            password.c_str(), password.size(),
            crypto_pwhash_OPSLIMIT_SENSITIVE,
            crypto_pwhash_MEMLIMIT_SENSITIVE,
            crypto_pwhash_ALG_ARGON2ID13
        );

        // Generate authentication tag
        std::array<uint8_t, 32> auth_tag;
        const std::string context = "opaque_client_auth";

        crypto_kdf_derive_from_key(
            auth_tag.data(), 32,
            2,
            reinterpret_cast<const uint8_t*>(context.data()),
            context.size(),
            password_key.data()
        );

        return auth_tag;
    }

    // Verify server authentication
    bool verify_server(
        const std::array<uint8_t, 32>& server_auth
    ) {
        // Derive expected server authentication
        std::array<uint8_t, 32> expected;
        const std::string context = "opaque_server_auth";

        crypto_kdf_derive_from_key(
            expected.data(), 32,
            3,
            reinterpret_cast<const uint8_t*>(context.data()),
            context.size(),
            stored_password_key_.data()
        );

        // Constant-time comparison
        return sodium_memcmp(
            server_auth.data(),
            expected.data(),
            32
        ) == 0;
    }

private:
    std::array<uint8_t, 32> stored_blinding_factor_;
    std::array<uint8_t, 32> stored_password_key_;
    std::array<uint8_t, 32> server_public_key_;

    void compute_blinded_element(
        const uint8_t* password_key,
        const uint8_t* blinding_factor,
        uint8_t* blinded_element
    ) {
        // Simplified OPRF computation
        // In production, use Ristretto255 or similar
        crypto_generichash_state state;
        crypto_generichash_init(&state, nullptr, 0, 32);
        crypto_generichash_update(&state, password_key, 32);
        crypto_generichash_update(&state, blinding_factor, 32);
        crypto_generichash_final(&state, blinded_element, 32);
    }

    void complete_oprf(
        const uint8_t* blinding_factor,
        const uint8_t* server_element,
        uint8_t* output
    ) {
        // Simplified OPRF completion
        // In production, use the inverse blinding factor
        crypto_generichash_state state;
        crypto_generichash_init(&state, nullptr, 0, 32);
        crypto_generichash_update(&state, server_element, 32);
        crypto_generichash_update(&state, blinding_factor, 32);
        crypto_generichash_final(&state, output, 32);
    }
};

class OpaqueServer {
public:
    OpaqueServer() {
        // Generate server key pair
        crypto_box_keypair(
            server_public_key_.data(),
            server_secret_key_.data()
        );
    }

    // Process registration request
    OpaqueRegistration process_registration(
        const std::array<uint8_t, 32>& blinded_element
    ) {
        // Generate random server element
        std::array<uint8_t, 32> server_element;
        randombytes_buf(server_element.data(), 32);

        // Combine with blinded element
        std::array<uint8_t, 32> combined;
        crypto_generichash_state state;
        crypto_generichash_init(&state, nullptr, 0, 32);
        crypto_generichash_update(&state, blinded_element.data(), 32);
        crypto_generichash_update(&state, server_element.data(), 32);
        crypto_generichash_final(&state, combined.data(), 32);

        OpaqueRegistration reg;
        reg.blinded_element = combined;
        reg.public_key = server_public_key_;

        // Store for later verification
        stored_blinded_element_ = blinded_element;

        return reg;
    }

    // Verify client authentication
    bool verify_authentication(
        const std::array<uint8_t, 32>& client_auth,
        const std::string& stored_password_hash
    ) {
        // Derive expected authentication
        std::array<uint8_t, 32> expected;
        const std::string context = "opaque_client_auth";

        // In production, this would use the stored OPRF output
        // Here we simplify using the password hash
        crypto_kdf_derive_from_key(
            expected.data(), 32,
            2,
            reinterpret_cast<const uint8_t*>(context.data()),
            context.size(),
            reinterpret_cast<const uint8_t*>(stored_password_hash.data())
        );

        return sodium_memcmp(
            client_auth.data(),
            expected.data(),
            32
        ) == 0;
    }

    // Generate server authentication
    std::array<uint8_t, 32> generate_server_auth(
        const std::string& stored_password_hash
    ) {
        std::array<uint8_t, 32> server_auth;
        const std::string context = "opaque_server_auth";

        crypto_kdf_derive_from_key(
            server_auth.data(), 32,
            3,
            reinterpret_cast<const uint8_t*>(context.data()),
            context.size(),
            reinterpret_cast<const uint8_t*>(stored_password_hash.data())
        );

        return server_auth;
    }

private:
    std::array<uint8_t, crypto_box_PUBLICKEYBYTES> server_public_key_;
    std::array<uint8_t, crypto_box_SECRETKEYBYTES> server_secret_key_;
    std::array<uint8_t, 32> stored_blinded_element_;
};
```

### OPAQUE vs SRP vs U-PAKE

| Característica | OPAQUE | SRP-6a | U-PAKE |
|----------------|--------|--------|--------|
| Modelo de segurança | UC-secure | Heuristic | UC-secure |
| Resistência a offline dictionary | Sim (servidor comprometido) | Sim | Sim |
| Requer salt no servidor | Não | Sim | Não |
| Resistência a quantum | Possível (com PQC) | Não | Possível |
| Complexidade de implementação | Média | Baixa | Alta |
| Adoção na indústria | Crescente | Estabelecida | Experimental |

### Vantagens do OPAQUE sobre SRP

1. **Sem泄露 de informações ao servidor**: O servidor nunca vê a senha ou uma representação derivada que permita dictionary attack
2. **Segurança comprovada**: OPAQUE tem prova formal de segurança no modelo UC
3. **Resistente a quantum**: Pode ser combinado com algoritmos pós-quânticos
4. **Simplicidade relativa**: A API é mais simples que SRP para o desenvolvedor

---

## Noise Protocol Framework: Handshake Patterns

### Visão Geral

O Noise Protocol Framework é um framework para design de protocolos criptográficos, não um protocolo específico. Ele fornece um vocabulário para descrever handshake patterns e um conjunto de primitivas para implementá-los.

O Noise é usado por:
- **WireGuard**: VPN moderna
- **Signal Protocol**: Mensageria segura
- **Lightning Network**: Pagamentos Bitcoin
- **WhatsApp**: Protocolo de mensagens
- **Tor**: Anonimato na internet

### Componentes do Noise

#### Primitivas Criptográficas

O Noise define cinco primitivas básicas:

| Primitiva | Função | libsodium equivalente |
|-----------|--------|----------------------|
| `DH` | Key exchange | `crypto_kx_*` |
| `E` | Encryption (AEAD) | `crypto_aead_*` |
| `H` | Hash function | `crypto_generichash_*` |
| `HKDF` | Key derivation | `crypto_kdf_*` |
| `Signature` | Digital signature | `crypto_sign_*` |

#### Variáveis de Handshake

O Noise mantém três variáveis durante o handshake:

1. **ck (chain key)**: Chave para derivar sub-chaves
2. **h (hash value)**: Hash acumulado do handshake
3. **s, e**: Chaves estática e efêmera (pode ser NULL)

#### Handshake Patterns

Um padrão de handshake é uma sequência de mensagens que define:
1. Quem envia cada mensagem
2. Quais operações DH são realizadas
3. Quais operações de encryption são realizadas

Exemplo de padrão `N` (Noise-N):

```
N:
  -> e
  <- e, ee
```

Isso significa:
- Initiator envia efêmera (e)
- Responder envia efémera (e) e calcula DH (ee)

### Padrões Noise Mais Comuns

#### Pattern N: One-Way Authentication

```
N:
  -> e
  <- e, ee
```

- **Uso**: Comunicação unidirecional (ex: mensagens push)
- **Autenticação**: Responder autentica initiator
- **Forward secrecy**: Sim (DH efêmero)

#### Pattern X: Basic Authentication

```
X:
  -> e
  <- e, ee, s, es
```

- **Uso**: Conexão cliente-servidor
- **Autenticação**: Bidirecional (responder conhece initiator)
- **Forward secrecy**: Sim

#### Pattern K: Mutual Authentication

```
K:
  -> e, s
  <- e, ee, se
```

- **Uso**: Dois dispositivos conhecidos
- **Autenticação**: Bidirecional
- **Forward secrecy**: Sim

#### Pattern IK: Initiator Known

```
IK:
  -> e, s
  <- e, ee, se, s, es
```

- **Uso**: Initiator conhece responder
- **Autenticação**: Bidirecional completa
- **Forward secrecy**: Sim
- **Usado por**: WireGuard

### Derivação de Chaves no Noise

```cpp
#include <sodium.h>
#include <array>
#include <vector>
#include <cstring>

class NoiseState {
public:
    NoiseState() {
        if (sodium_init() < 0) {
            throw std::runtime_error("Failed to initialize libsodium");
        }

        // Initialize hash to protocol name
        std::string protocol_name = "Noise_IK_25519_ChaChaPoly_BLAKE2s";
        std::memcpy(h_.data(), protocol_name.data(),
                    std::min(protocol_name.size(), h_.size()));
    }

    // MixHash: h = BLAKE2s(h, data)
    void mix_hash(const uint8_t* data, size_t len) {
        crypto_generichash_state state;
        crypto_generichash_init(&state, nullptr, 0, 32);
        crypto_generichash_update(&state, h_.data(), 32);
        crypto_generichash_update(&state, data, len);
        crypto_generichash_final(&state, h_.data(), 32);
    }

    // MixKey: ck, temp_k = HKDF(ck, dh_result)
    void mix_key(const uint8_t* input_key_material) {
        // HKDF-Extract
        std::array<uint8_t, 32> temp_key;
        crypto_kdf_derive_from_key(
            temp_key.data(), 32,
            0,
            reinterpret_cast<const uint8_t*>("NoiseMixKey"),
            11,
            input_key_material
        );

        // HKDF-Expand for chain key
        std::array<uint8_t, 32> new_ck;
        crypto_kdf_derive_from_key(
            new_ck.data(), 32,
            1,
            reinterpret_cast<const uint8_t*>("NoiseChainKey"),
            12,
            temp_key.data()
        );

        // HKDF-Expand for encryption key
        std::array<uint8_t, 32> new_k;
        crypto_kdf_derive_from_key(
            new_k.data(), 32,
            2,
            reinterpret_cast<const uint8_t*>("NoiseEncKey"),
            11,
            temp_key.data()
        );

        ck_ = new_ck;
        k_ = new_k;
        has_key_ = true;

        // MixHash with encrypted zero
        std::array<uint8_t, 16> zero;
        zero.fill(0);
        mix_hash(zero.data(), zero.size());
    }

    // EncryptAndHash: encrypts plaintext and mixes hash
    std::vector<uint8_t> encrypt_and_hash(
        const std::vector<uint8_t>& plaintext
    ) {
        if (!has_key_) {
            // No key yet, just return plaintext and mix hash
            mix_hash(plaintext.data(), plaintext.size());
            return plaintext;
        }

        // Generate nonce from counter
        std::array<uint8_t, 12> nonce;
        nonce.fill(0);
        nonce[0] = nonce_counter_ & 0xFF;
        nonce[1] = (nonce_counter_ >> 8) & 0xFF;
        nonce[2] = (nonce_counter_ >> 16) & 0xFF;
        nonce[3] = (nonce_counter_ >> 24) & 0xFF;
        nonce_counter_++;

        // Encrypt with ChaCha20-Poly1305
        std::vector<uint8_t> ciphertext(
            plaintext.size() + crypto_aead_chacha20poly1305_ABYTES
        );

        unsigned long long ciphertext_len;
        crypto_aead_chacha20poly1305_encrypt(
            ciphertext.data(), &ciphertext_len,
            plaintext.data(), plaintext.size(),
            h_.data(), 32,
            nullptr,
            nonce.data(),
            k_.data()
        );

        ciphertext.resize(ciphertext_len);

        // Mix hash with ciphertext
        mix_hash(ciphertext.data(), ciphertext_len);

        return ciphertext;
    }

    // DecryptAndHash: decrypts ciphertext and mixes hash
    std::vector<uint8_t> decrypt_and_hash(
        const std::vector<uint8_t>& ciphertext
    ) {
        if (!has_key_) {
            // No key yet, just return ciphertext and mix hash
            std::vector<uint8_t> plaintext(ciphertext);
            mix_hash(ciphertext.data(), ciphertext.size());
            return plaintext;
        }

        // Generate nonce from counter
        std::array<uint8_t, 12> nonce;
        nonce.fill(0);
        nonce[0] = nonce_counter_ & 0xFF;
        nonce[1] = (nonce_counter_ >> 8) & 0xFF;
        nonce[2] = (nonce_counter_ >> 16) & 0xFF;
        nonce[3] = (nonce_counter_ >> 24) & 0xFF;
        nonce_counter_++;

        // Decrypt with ChaCha20-Poly1305
        std::vector<uint8_t> plaintext(ciphertext.size());
        unsigned long long plaintext_len;

        if (crypto_aead_chacha20poly1305_decrypt(
                plaintext.data(), &plaintext_len,
                nullptr,
                ciphertext.data(), ciphertext.size(),
                h_.data(), 32,
                nonce.data(),
                k_.data()) != 0) {
            throw std::runtime_error("Decryption failed");
        }

        plaintext.resize(plaintext_len);

        // Mix hash with ciphertext
        mix_hash(ciphertext.data(), ciphertext.size());

        return plaintext;
    }

    // DH: perform key exchange and mix result
    void dh(const uint8_t* local_secret, const uint8_t* remote_public) {
        std::array<uint8_t, 32> dh_result;
        crypto_kx_deterministic_shared_key(
            dh_result.data(),
            local_secret,
            remote_public
        );
        mix_key(dh_result.data());
    }

    // Split: derive two CipherState objects
    void split(
        std::array<uint8_t, 32>& cipher1,
        std::array<uint8_t, 32>& cipher2
    ) {
        crypto_kdf_derive_from_key(
            cipher1.data(), 32,
            3,
            reinterpret_cast<const uint8_t*>("NoiseSplit1"),
            11,
            ck_.data()
        );

        crypto_kdf_derive_from_key(
            cipher2.data(), 32,
            4,
            reinterpret_cast<const uint8_t*>("NoiseSplit2"),
            11,
            ck_.data()
        );
    }

    const std::array<uint8_t, 32>& get_hash() const { return h_; }
    const std::array<uint8_t, 32>& get_chain_key() const { return ck_; }

private:
    std::array<uint8_t, 32> h_;    // Hash state
    std::array<uint8_t, 32> ck_;   // Chain key
    std::array<uint8_t, 32> k_;    // Encryption key
    bool has_key_ = false;
    uint32_t nonce_counter_ = 0;
};
```

### Handshake Pattern Completo: Noise_XK

```cpp
#include <sodium.h>
#include <array>
#include <vector>
#include <stdexcept>

struct NoiseKeypair {
    std::array<uint8_t, 32> private_key;
    std::array<uint8_t, 32> public_key;
};

struct NoiseHandshakeResult {
    std::array<uint8_t, 32> cipher_1;
    std::array<uint8_t, 32> cipher_2;
    bool success;
};

class NoiseXKInitiator {
public:
    NoiseXKInitiator() {
        if (sodium_init() < 0) {
            throw std::runtime_error("Failed to initialize libsodium");
        }

        // Generate static key pair
        crypto_kx_keypair(
            static_key_.public_key.data(),
            static_key_.private_key.data()
        );
    }

    // Pattern XK:
    // -> e
    // <- e, ee, s, es
    // -> s, se

    std::vector<uint8_t> create_message_1() {
        // Generate ephemeral key pair
        crypto_kx_keypair(
            ephemeral_key_.public_key.data(),
            ephemeral_key_.private_key.data()
        );

        // Message 1: just ephemeral public key
        return std::vector<uint8_t>(
            ephemeral_key_.public_key.begin(),
            ephemeral_key_.public_key.end()
        );
    }

    NoiseHandshakeResult process_message_2(
        const std::vector<uint8_t>& message_2,
        const std::array<uint8_t, 32>& responder_static
    ) {
        // Message 2 contains: encrypted static key + encrypted payload
        // + MAC

        NoiseState state;
        state.mix_hash(ephemeral_key_.public_key.data(), 32);

        // Receive responder's ephemeral
        if (message_2.size() < 32) {
            throw std::runtime_error("Message 2 too short");
        }

        state.mix_hash(message_2.data(), 32);

        // DH(ephemeral_initiator, ephemeral_responder)
        state.dh(
            ephemeral_key_.private_key.data(),
            message_2.data()
        );

        // Receive encrypted static key
        // In full implementation, this would be decrypted

        // DH(ephemeral_initiator, static_responder)
        state.dh(
            ephemeral_key_.private_key.data(),
            responder_static.data()
        );

        NoiseHandshakeResult result;
        state.split(result.cipher_1, result.cipher_2);
        result.success = true;

        return result;
    }

private:
    NoiseKeypair static_key_;
    NoiseKeypair ephemeral_key_;
};

class NoiseXKResponder {
public:
    NoiseXKResponder() {
        if (sodium_init() < 0) {
            throw std::runtime_error("Failed to initialize libsodium");
        }

        // Generate static key pair
        crypto_kx_keypair(
            static_key_.public_key.data(),
            static_key_.private_key.data()
        );
    }

    // Process message 1 and create message 2
    std::vector<uint8_t> process_message_1(
        const std::vector<uint8_t>& message_1
    ) {
        // Generate ephemeral key pair
        NoiseKeypair ephemeral;
        crypto_kx_keypair(
            ephemeral.public_key.data(),
            ephemeral.private_key.data()
        );

        NoiseState state;

        // Mix initiator's ephemeral
        state.mix_hash(message_1.data(), message_1.size());

        // Send responder's ephemeral
        state.mix_hash(ephemeral.public_key.data(), 32);

        // DH(responder ephemeral, initiator ephemeral)
        state.dh(
            ephemeral.private_key.data(),
            message_1.data()
        );

        // Send encrypted static key
        state.encrypt_and_hash(
            std::vector<uint8_t>(
                static_key_.public_key.begin(),
                static_key_.public_key.end()
            )
        );

        // DH(responder ephemeral, initiator static)
        // (would need initiator's static key here)

        return std::vector<uint8_t>(
            ephemeral.public_key.begin(),
            ephemeral.public_key.end()
        );
    }

    NoiseHandshakeResult process_message_3(
        const std::vector<uint8_t>& message_3
    ) {
        // Process final message
        NoiseState state;

        // In full implementation, decrypt and verify
        NoiseHandshakeResult result;
        result.success = true;

        return result;
    }

private:
    NoiseKeypair static_key_;
};
```

### Noise vs Outros Protocolos de Handshake

| Característica | Noise | TLS 1.3 | QUIC | SPAKE2 |
|----------------|-------|---------|------|--------|
| Flexibilidade | Extremamente alta | Média | Média | Baixa |
| Padrões suportados | 70+ patterns | ~10 cipher suites | ~5 | 1 |
| Tamanho de handshake | Configurável | Fixo | Fixo | Fixo |
| Forward secrecy | Opcional | Obrigatório | Obrigatório | Opcional |
| Autenticação mútua | Opcional | Opcional | Opcional | Obrigatória |
| Deniability | Configurável | Não | Não | Não |
| Implementação | Média | Alta | Alta | Baixa |

---

## WireGuard: Modern VPN Protocol

### Visão Geral

WireGuard é um protocolo VPN projetado com foco em simplicidade, performance e segurança. Diferentemente do IPSec, que suporta dezenas de opções configuráveis, WireGuard tem apenas uma configuração possível.

### Design Philosophy

WireGuard segue o princípio KISS (Keep It Simple, Stupid):

| Aspecto | WireGuard | IPSec/IKEv2 |
|---------|-----------|-------------|
| Linhas de código | ~4.000 | ~400.000 |
| Cipher suites | 1 (ChaCha20-Poly1305) | Dezenas |
| Handshake | 1-RTT | 2-RTT (IKE_SA_INIT + IKE_AUTH) |
| Chaves | Curve25519 | Multi-algoritmo |
| MTU overhead | 60 bytes | 200+ bytes |
| Configuração | Simples | Extremamente complexa |

### Componentes do WireGuard

#### 1. Chaves

WireGuard usa:
- **Curve25519**: Para key exchange (DH)
- **ChaCha20-Poly1305**: Para encryption (AEAD)
- **BLAKE2s**: Para hashing
- **HKDF**: Para key derivation

```cpp
#include <sodium.h>
#include <array>
#include <vector>
#include <cstring>
#include <cstdint>

struct WireGuardKeyPair {
    std::array<uint8_t, 32> private_key;
    std::array<uint8_t, 32> public_key;
};

struct WireGuardHandshakeState {
    // Chaves efêmeras
    std::array<uint8_t, 32> ephemeral_private;
    std::array<uint8_t, 32> ephemeral_public;

    // Chaves estáticas
    std::array<uint8_t, 32> static_private;
    std::array<uint8_t, 32> static_public;

    // Chaves do par
    std::array<uint8_t, 32> remote_ephemeral;
    std::array<uint8_t, 32> remote_static;

    // Nonces
    uint64_t send_counter;
    uint64_t receive_counter;

    // Chaves derivadas
    std::array<uint8_t, 32> send_key;
    std::array<uint8_t, 32> receive_key;

    bool handshake_complete;
};

class WireGuardInterface {
public:
    WireGuardInterface() {
        if (sodium_init() < 0) {
            throw std::runtime_error("Failed to initialize libsodium");
        }

        // Generate static key pair
        crypto_kx_keypair(
            static_key_.public_key.data(),
            static_key_.private_key.data()
        );
    }

    // Generate ephemeral key pair for handshake
    void generate_ephemeral() {
        crypto_kx_keypair(
            state_.ephemeral_public.data(),
            state_.ephemeral_private.data()
        );
    }

    // Create initial handshake message (1-RTT)
    std::vector<uint8_t> create_handshake(
        const std::array<uint8_t, 32>& remote_static
    ) {
        state_.remote_static = remote_static;
        generate_ephemeral();

        std::vector<uint8_t> message;

        // Message type (1 byte): 1 = handshake initiation
        message.push_back(1);

        // Sender index (4 bytes)
        uint32_t sender_index = 0;
        message.push_back(sender_index & 0xFF);
        message.push_back((sender_index >> 8) & 0xFF);
        message.push_back((sender_index >> 16) & 0xFF);
        message.push_back((sender_index >> 24) & 0xFF);

        // Unencrypted timestamp (8 bytes)
        uint64_t timestamp = get_timestamp();
        for (int i = 0; i < 8; ++i) {
            message.push_back((timestamp >> (i * 8)) & 0xFF);
        }

        // Ephemeral public key (32 bytes)
        message.insert(
            message.end(),
            state_.ephemeral_public.begin(),
            state_.ephemeral_public.end()
        );

        // Compute DH1 = DH(initiator_ephemeral, responder_static)
        std::array<uint8_t, 32> dh1;
        crypto_kx_deterministic_shared_key(
            dh1.data(),
            state_.ephemeral_private.data(),
            remote_static.data()
        );

        // Compute DH2 = DH(initiator_static, responder_ephemeral)
        // (responder_ephemeral is not known yet, this is simplified)

        // Compute DH3 = DH(initiator_ephemeral, responder_ephemeral)
        // (responder_ephemeral is not known yet, this is simplified)

        // Derive keys using HKDF
        derive_handshake_keys(dh1);

        // Encrypted static key (32 + 16 bytes AEAD)
        std::vector<uint8_t> encrypted_static =
            encrypt(state_.static_public);

        message.insert(
            message.end(),
            encrypted_static.begin(),
            encrypted_static.end()
        );

        // Encrypted timestamp (8 + 16 bytes AEAD)
        std::vector<uint8_t> encrypted_timestamp =
            encrypt(std::vector<uint8_t>(
                reinterpret_cast<uint8_t*>(&timestamp),
                reinterpret_cast<uint8_t*>(&timestamp) + 8
            ));

        message.insert(
            message.end(),
            encrypted_timestamp.begin(),
            encrypted_timestamp.end()
        );

        return message;
    }

    // Process handshake response
    bool process_handshake_response(
        const std::vector<uint8_t>& response
    ) {
        if (response.size() < 1 + 4 + 32 + 16 + 16) {
            return false;
        }

        size_t offset = 0;

        // Message type (1 byte)
        uint8_t msg_type = response[offset++];
        if (msg_type != 2) { // 2 = handshake response
            return false;
        }

        // Receiver index (4 bytes)
        offset += 4;

        // Ephemeral public key (32 bytes)
        std::copy(
            response.begin() + offset,
            response.begin() + offset + 32,
            state_.remote_ephemeral.begin()
        );
        offset += 32;

        // Compute DH(responder_ephemeral, initiator_static)
        std::array<uint8_t, 32> dh_result;
        crypto_kx_deterministic_shared_key(
            dh_result.data(),
            state_.static_private.data(),
            state_.remote_ephemeral.data()
        );

        // Derive final keys
        derive_final_keys(dh_result);

        state_.handshake_complete = true;
        return true;
    }

    // Encrypt a packet
    std::vector<uint8_t> encrypt_packet(const std::vector<uint8_t>& plaintext) {
        if (!state_.handshake_complete) {
            throw std::runtime_error("Handshake not complete");
        }

        std::vector<uint8_t> packet;

        // Packet type (1 byte): 4 = transport data
        packet.push_back(4);

        // Receiver index (4 bytes)
        uint32_t receiver_index = 0;
        packet.push_back(receiver_index & 0xFF);
        packet.push_back((receiver_index >> 8) & 0xFF);
        packet.push_back((receiver_index >> 16) & 0xFF);
        packet.push_back((receiver_index >> 24) & 0xFF);

        // Counter (8 bytes)
        uint64_t counter = state_.send_counter++;
        for (int i = 0; i < 8; ++i) {
            packet.push_back((counter >> (i * 8)) & 0xFF);
        }

        // Encrypted payload (16 bytes AEAD overhead)
        std::vector<uint8_t> encrypted =
            encrypt_with_key(plaintext, state_.send_key);

        packet.insert(packet.end(), encrypted.begin(), encrypted.end());

        return packet;
    }

    // Decrypt a packet
    std::vector<uint8_t> decrypt_packet(const std::vector<uint8_t>& packet) {
        if (!state_.handshake_complete) {
            throw std::runtime_error("Handshake not complete");
        }

        if (packet.size() < 1 + 4 + 8 + 16) {
            throw std::runtime_error("Packet too short");
        }

        size_t offset = 0;

        // Packet type (1 byte)
        uint8_t msg_type = packet[offset++];
        if (msg_type != 4) {
            throw std::runtime_error("Invalid packet type");
        }

        // Receiver index (4 bytes)
        offset += 4;

        // Counter (8 bytes)
        uint64_t counter = 0;
        for (int i = 0; i < 8; ++i) {
            counter |= static_cast<uint64_t>(packet[offset + i]) << (i * 8);
        }
        offset += 8;

        // Check counter for replay protection
        if (counter <= state_.receive_counter) {
            throw std::runtime_error("Replay detected");
        }
        state_.receive_counter = counter;

        // Decrypt payload
        std::vector<uint8_t> ciphertext(
            packet.begin() + offset,
            packet.end()
        );

        return decrypt_with_key(ciphertext, state_.receive_key);
    }

private:
    WireGuardKeyPair static_key_;
    WireGuardHandshakeState state_;

    uint64_t get_timestamp() {
        struct timespec ts;
        clock_gettime(CLOCK_MONOTONIC, &ts);
        return static_cast<uint64_t>(ts.tv_sec) * 1000000000ULL + ts.tv_nsec;
    }

    void derive_handshake_keys(const std::array<uint8_t, 32>& dh_result) {
        // HKDF to derive chain key and hash
        const std::string salt = "WireGuard handshake";
        const std::string info = "handshake keys";

        crypto_kdf_derive_from_key(
            state_.send_key.data(), 32,
            0,
            reinterpret_cast<const uint8_t*>(info.data()),
            info.size(),
            dh_result.data()
        );
    }

    void derive_final_keys(const std::array<uint8_t, 32>& dh_result) {
        // Derive send and receive keys
        const std::string send_info = "send_key";
        const std::string recv_info = "receive_key";

        crypto_kdf_derive_from_key(
            state_.send_key.data(), 32,
            1,
            reinterpret_cast<const uint8_t*>(send_info.data()),
            send_info.size(),
            dh_result.data()
        );

        crypto_kdf_derive_from_key(
            state_.receive_key.data(), 32,
            2,
            reinterpret_cast<const uint8_t*>(recv_info.data()),
            recv_info.size(),
            dh_result.data()
        );
    }

    std::vector<uint8_t> encrypt(const std::vector<uint8_t>& plaintext) {
        // Simplified encryption (in real WireGuard, uses key from handshake)
        std::vector<uint8_t> ciphertext(
            plaintext.size() + crypto_aead_chacha20poly1305_ABYTES
        );

        std::array<uint8_t, 12> nonce;
        nonce.fill(0);

        unsigned long long ciphertext_len;
        crypto_aead_chacha20poly1305_encrypt(
            ciphertext.data(), &ciphertext_len,
            plaintext.data(), plaintext.size(),
            nullptr, 0, nullptr,
            nonce.data(),
            state_.send_key.data()
        );

        ciphertext.resize(ciphertext_len);
        return ciphertext;
    }

    std::vector<uint8_t> encrypt_with_key(
        const std::vector<uint8_t>& plaintext,
        const std::array<uint8_t, 32>& key
    ) {
        std::vector<uint8_t> ciphertext(
            plaintext.size() + crypto_aead_chacha20poly1305_ABYTES
        );

        std::array<uint8_t, 12> nonce;
        nonce.fill(0);

        unsigned long long ciphertext_len;
        crypto_aead_chacha20poly1305_encrypt(
            ciphertext.data(), &ciphertext_len,
            plaintext.data(), plaintext.size(),
            nullptr, 0, nullptr,
            nonce.data(),
            key.data()
        );

        ciphertext.resize(ciphertext_len);
        return ciphertext;
    }

    std::vector<uint8_t> decrypt_with_key(
        const std::vector<uint8_t>& ciphertext,
        const std::array<uint8_t, 32>& key
    ) {
        std::vector<uint8_t> plaintext(ciphertext.size());
        unsigned long long plaintext_len;

        std::array<uint8_t, 12> nonce;
        nonce.fill(0);

        if (crypto_aead_chacha20poly1305_decrypt(
                plaintext.data(), &plaintext_len,
                nullptr,
                ciphertext.data(), ciphertext.size(),
                nullptr, 0,
                nonce.data(),
                key.data()) != 0) {
            throw std::runtime_error("Decryption failed");
        }

        plaintext.resize(plaintext_len);
        return plaintext;
    }
};
```

### WireGuard Security Properties

| Propriedade | Como WireGuard fornece |
|-------------|------------------------|
| Forward Secrecy | Chaves efêmeras rotacionadas por handshake |
| Deniability | Sem assinaturas de handshake (apenas DH) |
| Replay Protection | Contadores monotonamente crescentes |
| Cryptokey Routing | Chaves públicas são os endereços |
| Minimal Attack Surface | ~4.000 linhas de código |
| Constant-Time | Operações de chave são constant-time |


---

## IPSec/IKEv2: Estado Atual

### Visão Geral do IPSec

IPSec é o conjunto de protocolos que fornece segurança na camada de rede (IP). Ele é usado extensivamente em VPNs corporativas, mas também é a base de muitas VPNs de consumo.

IPSec compreende dois protocolos principais:
- **ESP (Encapsulating Security Payload)**: Fornece confidencialidade, integridade e autenticação
- **AH (Authentication Header)**: Fornece apenas integridade e autenticação (raramente usado hoje)

### IKEv2: Internet Key Exchange version 2

IKEv2 é o protocolo de key exchange usado com IPSec. Ele substituiu o IKEv1 devido a melhorias significativas:

| Aspecto | IKEv1 | IKEv2 |
|---------|-------|-------|
| Mensagens no handshake | 6-9 | 2-4 |
| Moblidade | Fraca | MOBIKE support |
| Configuração | Extremamente complexa | Simplificada |
| NAT traversal | Implementação variável | Nat-T integrado |
| Reconexão | Lenta | Fast reconnection |

#### O Handshake IKEv2

```
Initiator                              Responder
    |                                    |
    |  IKE_SA_INIT:                      |
    |  - Header                          |
    |  - SA (Security Association)       |
    |  - KE (Key Exchange)               |
    |  - Nonce                           |
    |  - [NAT-T discovery]               |
    |                                    |
    |--- IKE_SA_INIT ------------------>|
    |                                    |
    |<-- IKE_SA_INIT --------------------|
    |                                    |
    |  IKE_AUTH:                         |
    |  - Header                          |
    |  - [IDi] (Initiator ID)            |
    |  - [IDr] (Responder ID)            |
    |  - [AUTH] (Authentication)         |
    |  - [SA] (Child SA)                 |
    |  - [TSi] (Traffic Selector)        |
    |  - [TSr] (Traffic Selector)        |
    |                                    |
    |--- IKE_AUTH --------------------->|
    |                                    |
    |<-- IKE_AUTH -----------------------|
    |                                    |
    |  [CREATE_CHILD_SA]:                |
    |  (para renegotiação de chaves)     |
    |                                    |
```

### Implementação IKEv2 Simplificada

```cpp
#include <sodium.h>
#include <array>
#include <vector>
#include <cstring>
#include <cstdint>
#include <stdexcept>

enum class IKEv2MessageType : uint8_t {
    IKE_SA_INIT = 34,
    IKE_AUTH = 35,
    CREATE_CHILD_SA = 36,
    INFORMATIONAL = 37
};

struct IKEv2Header {
    uint8_t initiator_spi[8];
    uint8_t responder_spi[8];
    uint8_t next_payload;
    uint8_t version;
    uint8_t exchange_type;
    uint8_t flags;
    uint32_t message_id;
    uint32_t length;
};

struct IKEv2Payload {
    uint8_t next_payload;
    uint8_t reserved;
    uint16_t payload_length;
    std::vector<uint8_t> data;
};

struct IKEv2SA {
    uint32_t dh_group;
    uint32_t encryption_algorithm;
    uint32_t prf_algorithm;
    uint32_t integrity_algorithm;
    uint64_t lifetime;
};

class IKEv2Initiator {
public:
    IKEv2Initiator() {
        if (sodium_init() < 0) {
            throw std::runtime_error("Failed to initialize libsodium");
        }

        // Generate static key pair
        crypto_kx_keypair(
            static_key_.public_key.data(),
            static_key_.private_key.data()
        );

        // Generate initial SPI
        randombytes_buf(initiator_spi_, 8);
    }

    // Create IKE_SA_INIT message
    std::vector<uint8_t> create_ike_sa_init() {
        std::vector<uint8_t> message;

        // Generate ephemeral key pair
        crypto_kx_keypair(
            ephemeral_key_.public_key.data(),
            ephemeral_key_.private_key.data()
        );

        // IKEv2 Header
        IKEv2Header header;
        std::memcpy(header.initiator_spi, initiator_spi_, 8);
        std::memset(header.responder_spi, 0, 8);
        header.next_payload = 38; // SA
        header.version = 0x20;    // IKEv2
        header.exchange_type = 34; // IKE_SA_INIT
        header.flags = 0x08;      // Initiator bit set
        header.message_id = 0;
        header.length = 0;        // Will be filled later

        // Write header
        message.insert(message.end(),
            reinterpret_cast<uint8_t*>(&header),
            reinterpret_cast<uint8_t*>(&header) + sizeof(header)
        );

        // SA Payload
        IKEv2SA sa;
        sa.dh_group = 31;        // Curve25519
        sa.encryption_algorithm = 20; // AES-GCM-128
        sa.prf_algorithm = 5;    // SHA-256
        sa.integrity_algorithm = 12; // SHA-256-128
        sa.lifetime = 86400;     // 24 hours

        IKEv2Payload sa_payload;
        sa_payload.next_payload = 38; // KE
        sa_payload.reserved = 0;
        sa_payload.data.insert(sa_payload.data.end(),
            reinterpret_cast<uint8_t*>(&sa),
            reinterpret_cast<uint8_t*>(&sa) + sizeof(sa)
        );
        sa_payload.payload_length = sizeof(sa_payload.data);

        // Write SA payload
        write_payload(message, sa_payload);

        // KE Payload
        IKEv2Payload ke_payload;
        ke_payload.next_payload = 40; // Nonce
        ke_payload.reserved = 0;
        ke_payload.data.insert(ke_payload.data.end(),
            ephemeral_key_.public_key.begin(),
            ephemeral_key_.public_key.end()
        );
        ke_payload.payload_length = sizeof(ke_payload.data);

        // Write KE payload
        write_payload(message, ke_payload);

        // Nonce Payload
        IKEv2Payload nonce_payload;
        nonce_payload.next_payload = 0; // No next payload
        nonce_payload.reserved = 0;
        nonce_payload.data.resize(32);
        randombytes_buf(nonce_payload.data.data(), 32);
        nonce_payload.payload_length = 32;

        // Write Nonce payload
        write_payload(message, nonce_payload);

        // Update header length
        header.length = message.size();
        std::memcpy(message.data() + 16, &header.length, 4);

        // Generate nonce for key derivation
        std::copy(
            nonce_payload.data.begin(),
            nonce_payload.data.end(),
            initiator_nonce_.begin()
        );

        return message;
    }

    // Process IKE_SA_INIT response
    void process_ike_sa_init_response(
        const std::vector<uint8_t>& response
    ) {
        if (response.size() < sizeof(IKEv2Header)) {
            throw std::runtime_error("Response too short");
        }

        IKEv2Header header;
        std::memcpy(&header, response.data(), sizeof(header));

        // Extract responder SPI
        std::memcpy(responder_spi_, header.responder_spi, 8);

        // Parse response payloads (simplified)
        // In production, parse SA, KE, Nonce payloads

        // Generate nonce
        randombytes_buf(responder_nonce_.data(), 32);
    }

    // Create IKE_AUTH message
    std::vector<uint8_t> create_ike_auth() {
        std::vector<uint8_t> message;

        // IKEv2 Header
        IKEv2Header header;
        std::memcpy(header.initiator_spi, initiator_spi_, 8);
        std::memcpy(header.responder_spi, responder_spi_, 8);
        header.next_payload = 39; // IDi
        header.version = 0x20;
        header.exchange_type = 35; // IKE_AUTH
        header.flags = 0x08;
        header.message_id = 1;
        header.length = 0;

        message.insert(message.end(),
            reinterpret_cast<uint8_t*>(&header),
            reinterpret_cast<uint8_t*>(&header) + sizeof(header)
        );

        // IDi Payload (Initiator ID)
        IKEv2Payload idi_payload;
        idi_payload.next_payload = 39; // IDr
        idi_payload.reserved = 0;
        idi_payload.data = std::vector<uint8_t>(32, 0x41); // Simplified ID
        idi_payload.payload_length = 32;

        write_payload(message, idi_payload);

        // IDr Payload (Responder ID)
        IKEv2Payload idr_payload;
        idr_payload.next_payload = 39; // AUTH
        idr_payload.reserved = 0;
        idr_payload.data = std::vector<uint8_t>(32, 0x42); // Simplified ID
        idr_payload.payload_length = 32;

        write_payload(message, idr_payload);

        // AUTH Payload
        IKEv2Payload auth_payload;
        auth_payload.next_payload = 44; // SA
        auth_payload.reserved = 0;

        // Generate authentication data
        std::array<uint8_t, 32> auth_data;
        crypto_kdf_derive_from_key(
            auth_data.data(), 32,
            0,
            reinterpret_cast<const uint8_t*>("IKE_AUTH_initiator"),
            17,
            static_key_.private_key.data()
        );

        auth_payload.data = std::vector<uint8_t>(
            auth_data.begin(), auth_data.end()
        );
        auth_payload.payload_length = 32;

        write_payload(message, auth_payload);

        // Update header length
        header.length = message.size();
        std::memcpy(message.data() + 16, &header.length, 4);

        return message;
    }

private:
    std::array<uint8_t, 32> static_key_;
    std::array<uint8_t, 32> ephemeral_key_;
    uint8_t initiator_spi_[8];
    uint8_t responder_spi_[8];
    std::array<uint8_t, 32> initiator_nonce_;
    std::array<uint8_t, 32> responder_nonce_;

    void write_payload(
        std::vector<uint8_t>& message,
        const IKEv2Payload& payload
    ) {
        message.push_back(payload.next_payload);
        message.push_back(payload.reserved);

        uint16_t len = payload.payload_length + 4;
        message.push_back(len & 0xFF);
        message.push_back((len >> 8) & 0xFF);

        message.insert(message.end(),
            payload.data.begin(),
            payload.data.end()
        );
    }
};
```

### CVE-2020-26139: IPSec Traffic Amplification

#### Análise da Vulnerabilidade

| Campo | Detalhe |
|-------|---------|
| CVE | CVE-2020-26139 |
| Data | 2020-07-06 |
| Severidade | CVSS 7.5 (Alto) |
| Impacto | Traffic amplification via IKEv1 header parsing |
| Produto | FreeSWITCH, StrongSwawn, e outros IKEv1 implementations |
| Causa Raiz | IKEv1 não valida corretamente o comprimento das mensagens antes de responder |
| Lição | Protocolos devem validar todos os campos antes de processar ou responder |

#### Como Funciona o Ataque

O ataque IKEv1 reflection/reflection funciona assim:

1. Atacante envia uma IKE_SA_INIT de IKEv1 para a vítima
2. A vítima responde com IKE_SA_INIT
3. O atacante redireciona a resposta para um terceiro
4. O terceiro responde, e o ciclo continua
5. O tráfego é amplificado porque as respostas são maiores que as requisições

#### Código Vulnerável (Simplificado)

```cpp
// CÓDIGO VULNERÁVEL - NÃO USAR EM PRODUÇÃO
// IKEv1 SA parsing sem validação adequada

void handle_ikev1_sa_init_vulnerable(
    const uint8_t* packet,
    size_t packet_len
) {
    // BUG: Não valida se packet_len é suficiente antes de ler
    // BUG: Não valida SPI (Security Parameter Index)
    // BUG: Não valida DH group number

    const IKEv1Header* header =
        reinterpret_cast<const IKEv1Header*>(packet);

    // Lê DH public key sem verificar se o pacote é longe o suficiente
    uint16_t ke_len = header->ke_length;
    const uint8_t* ke_data = packet + sizeof(IKEv1Header) + 8;

    // Gera resposta IMEDIATAMENTE sem validação
    // Isso permite reflection attack
    send_ikev1_response(header->initiator_spi, ke_data, ke_len);
}
```

#### Código Corrigido

```cpp
#include <sodium.h>
#include <cstdint>
#include <cstring>
#include <vector>
#include <stdexcept>

// IKEv2 (não IKEv1) - protocolo seguro por design
// IKEv2 não sofre do ataque CVE-2020-26139 porque:
// 1. Usa anti-replay (nonce + counter)
// 2. Valida SPI antes de responder
// 3. Não permite reflection (message_id vinculado ao initiator)

struct SecureIKEv2Header {
    uint8_t initiator_spi[8];
    uint8_t responder_spi[8];
    uint8_t next_payload;
    uint8_t version;
    uint8_t exchange_type;
    uint8_t flags;
    uint32_t message_id;
    uint32_t length;
};

void handle_ikev2_sa_init_secure(
    const uint8_t* packet,
    size_t packet_len,
    const uint8_t* expected_spi
) {
    // STEP 1: Validação mínima do tamanho
    if (packet_len < sizeof(SecureIKEv2Header)) {
        throw std::runtime_error("Packet too short for IKEv2 header");
    }

    const SecureIKEv2Header* header =
        reinterpret_cast<const SecureIKEv2Header*>(packet);

    // STEP 2: Validação do SPI do initiator
    if (expected_spi != nullptr) {
        if (std::memcmp(header->initiator_spi, expected_spi, 8) != 0) {
            throw std::runtime_error("Invalid initiator SPI");
        }
    }

    // STEP 3: Validação do exchange type
    if (header->exchange_type != 34) { // IKE_SA_INIT
        throw std::runtime_error("Invalid exchange type for SA_INIT");
    }

    // STEP 4: Validação do comprimento da mensagem
    uint32_t msg_len = header->length;
    if (msg_len < sizeof(SecureIKEv2Header)) {
        throw std::runtime_error("Invalid message length");
    }
    if (msg_len > packet_len) {
        throw std::runtime_error("Message length exceeds packet");
    }

    // STEP 5: Validação dos payloads
    size_t offset = sizeof(SecureIKEv2Header);
    uint8_t next_payload = header->next_payload;

    while (next_payload != 0 && offset < msg_len) {
        // Cada payload tem 4-byte header
        if (offset + 4 > msg_len) {
            throw std::runtime_error("Truncated payload header");
        }

        uint16_t payload_len = *reinterpret_cast<const uint16_t*>(
            packet + offset + 2
        );

        if (payload_len < 4) {
            throw std::runtime_error("Invalid payload length");
        }
        if (offset + payload_len > msg_len) {
            throw std::runtime_error("Payload exceeds message");
        }

        next_payload = packet[offset];
        offset += payload_len;
    }

    // STEP 6: Anti-replay - gera nonce único
    uint8_t nonce[32];
    randombytes_buf(nonce, sizeof(nonce));

    // STEP 7: Gera resposta apenas após todas as validações
    // Em produção, aqui você implementaria o IKEv2 response completo
    // O key exchange derivado do DH é único por sessão
    // Não há reflection possible porque message_id é vinculado ao initiator
}
```

#### Prevenção contra CVE-2020-26139

| Medida | Descrição |
|--------|-----------|
| Usar IKEv2 | IKEv2 tem anti-replay nativo |
| Rate limiting | Limitar respostas por IP |
| Validar SPI | Verificar SPI antes de processar |
| Nonce verification | Usar nonces únicos em cada handshake |
| Monitoramento | Detectar tráfego amplificado |

---

## SSH Protocol: Boas Práticas Modernas

### Visão Geral do SSH

SSH (Secure Shell) é o protocolo mais usado para acesso remoto a sistemas. Embora seja maduro e amplamente analisado, ainda apresenta armadilhas para implementadores.

### Versões do SSH

| Versão | Status | Recomendação |
|--------|--------|--------------|
| SSH-1 | Descontinuado | NUNCA usar |
| SSH-2 | Atual | Usar com configurações modernas |

### O Handshake SSH

```
Client                                   Server
  |                                        |
  |  TCP Connection                        |
  |<====================================>|
  |                                        |
  |  Protocol Version Exchange             |
  |  "SSH-2.0-OpenSSH_9.0"                |
  |<------------------------------------->|
  |                                        |
  |  Key Exchange Init                     |
  |  (list of supported algorithms)        |
  |<------------------------------------->|
  |                                        |
  |  Key Exchange                          |
  |  (DH, ECDH, or Curve25519)            |
  |<------------------------------------->|
  |                                        |
  |  New Keys                              |
  |  (switch to encrypted)                 |
  |<------------------------------------->|
  |                                        |
  |  [Encrypted]                           |
  |  Service Request                       |
  |  User Authentication                   |
  |  Channel Open                          |
  |  [Data Transfer]                       |
  |<------------------------------------->|
```

### Implementação SSH Key Exchange com libsodium

```cpp
#include <sodium.h>
#include <array>
#include <vector>
#include <cstring>
#include <stdexcept>

struct SSHKeyPair {
    std::array<uint8_t, 32> private_key;
    std::array<uint8_t, 32> public_key;
    std::string key_type; // "ssh-ed25519"
};

struct SSHHandshakeState {
    // Client/Server identification
    std::string client_id;
    std::string server_id;

    // Key exchange
    std::array<uint8_t, 32> client_ephemeral;
    std::array<uint8_t, 32> server_ephemeral;

    // Shared secret
    std::array<uint8_t, 32> shared_secret;

    // Exchange hash
    std::array<uint8_t, 32> exchange_hash;

    // Derived keys
    std::array<uint8_t, 32> mac_key;
    std::array<uint8_t, 32> encryption_key;
    std::array<uint8_t, 32> iv;

    // Sequence numbers
    uint32_t client_sequence;
    uint32_t server_sequence;
};

class SSHKeyExchange {
public:
    SSHKeyExchange() {
        if (sodium_init() < 0) {
            throw std::runtime_error("Failed to initialize libsodium");
        }

        // Generate host key
        crypto_sign_keypair(
            host_key_.public_key.data(),
            host_key_.secret_key.data()
        );
    }

    // Generate ECDH key pair for key exchange
    void generate_ephemeral() {
        crypto_kx_keypair(
            ephemeral_.public_key.data(),
            ephemeral_.private_key.data()
        );
    }

    // Create key exchange init message
    std::vector<uint8_t> create_kex_init() {
        std::vector<uint8_t> message;

        // Message type (SSH_MSG_KEXINIT = 20)
        message.push_back(20);

        // Cookie (16 bytes random)
        uint8_t cookie[16];
        randombytes_buf(cookie, 16);
        message.insert(message.end(), cookie, cookie + 16);

        // Name lists (simplified - in production, include all algorithms)
        // kex_algorithms
        std::string kex = "curve25519-sha256";
        write_name_list(message, kex);

        // server_host_key_algorithms
        std::string host_key = "ssh-ed25519";
        write_name_list(message, host_key);

        // encryption_algorithms (client->server)
        std::string enc_cs = "chacha20-poly1305@openssh.com";
        write_name_list(message, enc_cs);

        // encryption_algorithms (server->client)
        std::string enc_sc = "chacha20-poly1305@openssh.com";
        write_name_list(message, enc_sc);

        // mac_algorithms (client->server)
        std::string mac_cs = "hmac-sha2-256";
        write_name_list(message, mac_cs);

        // mac_algorithms (server->client)
        std::string mac_sc = "hmac-sha2-256";
        write_name_list(message, mac_sc);

        // compression_algorithms
        std::string comp = "none";
        write_name_list(message, comp);
        write_name_list(message, comp);

        // First kex packet follows
        message.push_back(0);

        // Reserved (4 bytes)
        message.insert(message.end(), 4, 0);

        return message;
    }

    // Process kex init from server
    void process_kex_init(const std::vector<uint8_t>& message) {
        // In production, parse and negotiate algorithms
        // For this example, we assume curve25519-sha256 is selected
    }

    // Create ECDH key exchange message
    std::vector<uint8_t> create_ecdh_init() {
        generate_ephemeral();

        std::vector<uint8_t> message;

        // Message type (SSH_MSG_KEX_ECDH_INIT = 30)
        message.push_back(30);

        // Client's ephemeral public key
        message.insert(message.end(),
            ephemeral_.public_key.begin(),
            ephemeral_.public_key.end()
        );

        return message;
    }

    // Process ECDH reply and compute shared secret
    void process_ecdh_reply(
        const std::vector<uint8_t>& server_ephemeral,
        const std::array<uint8_t, 32>& server_host_key
    ) {
        // Store server's ephemeral
        std::copy(
            server_ephemeral.begin(),
            server_ephemeral.end(),
            state_.server_ephemeral.begin()
        );

        // Compute shared secret
        crypto_kx_deterministic_shared_key(
            state_.shared_secret.data(),
            ephemeral_.private_key.data(),
            server_ephemeral.data()
        );

        // Compute exchange hash
        compute_exchange_hash(server_host_key);
    }

    // Derive encryption and MAC keys
    void derive_keys() {
        // Key derivation using HKDF
        const std::string session_id = "session_id";

        // client_to_server key
        std::array<uint8_t, 32> client_key;
        crypto_kdf_derive_from_key(
            client_key.data(), 32,
            0,
            reinterpret_cast<const uint8_t*>("client_to_server"),
            16,
            state_.exchange_hash.data()
        );

        // server_to_client key
        std::array<uint8_t, 32> server_key;
        crypto_kdf_derive_from_key(
            server_key.data(), 32,
            1,
            reinterpret_cast<const uint8_t*>("server_to_client"),
            16,
            state_.exchange_hash.data()
        );

        // initial IV
        crypto_kdf_derive_from_key(
            state_.iv.data(), 32,
            2,
            reinterpret_cast<const uint8_t*>("initial_iv"),
            10,
            state_.exchange_hash.data()
        );

        // MAC key
        crypto_kdf_derive_from_key(
            state_.mac_key.data(), 32,
            3,
            reinterpret_cast<const uint8_t*>("mac_key"),
            7,
            state_.exchange_hash.data()
        );

        state_.client_sequence = 0;
        state_.server_sequence = 0;
    }

    // Encrypt a packet
    std::vector<uint8_t> encrypt_packet(
        const std::vector<uint8_t>& plaintext,
        bool is_client_to_server
    ) {
        // ChaCha20-Poly1305 encryption
        std::vector<uint8_t> ciphertext(
            plaintext.size() + 16 // Poly1305 tag
        );

        // Generate nonce from sequence number
        std::array<uint8_t, 12> nonce;
        nonce.fill(0);

        uint32_t seq = is_client_to_server ?
            state_.client_sequence++ :
            state_.server_sequence++;

        nonce[0] = seq & 0xFF;
        nonce[1] = (seq >> 8) & 0xFF;
        nonce[2] = (seq >> 16) & 0xFF;
        nonce[3] = (seq >> 24) & 0xFF;

        unsigned long long ciphertext_len;
        crypto_aead_chacha20poly1305_encrypt(
            ciphertext.data(), &ciphertext_len,
            plaintext.data(), plaintext.size(),
            nullptr, 0, nullptr,
            nonce.data(),
            state_.encryption_key.data()
        );

        ciphertext.resize(ciphertext_len);
        return ciphertext;
    }

    // Decrypt a packet
    std::vector<uint8_t> decrypt_packet(
        const std::vector<uint8_t>& ciphertext,
        bool is_server_to_client
    ) {
        std::vector<uint8_t> plaintext(ciphertext.size());
        unsigned long long plaintext_len;

        // Generate nonce from sequence number
        std::array<uint8_t, 12> nonce;
        nonce.fill(0);

        uint32_t seq = is_server_to_client ?
            state_.server_sequence++ :
            state_.client_sequence++;

        nonce[0] = seq & 0xFF;
        nonce[1] = (seq >> 8) & 0xFF;
        nonce[2] = (seq >> 16) & 0xFF;
        nonce[3] = (seq >> 24) & 0xFF;

        if (crypto_aead_chacha20poly1305_decrypt(
                plaintext.data(), &plaintext_len,
                nullptr,
                ciphertext.data(), ciphertext.size(),
                nullptr, 0,
                nonce.data(),
                state_.encryption_key.data()) != 0) {
            throw std::runtime_error("Decryption failed");
        }

        plaintext.resize(plaintext_len);
        return plaintext;
    }

private:
    SSHKeyPair host_key_;
    SSHKeyPair ephemeral_;
    SSHHandshakeState state_;

    void write_name_list(
        std::vector<uint8_t>& message,
        const std::string& name
    ) {
        uint32_t len = name.size();
        message.push_back((len >> 24) & 0xFF);
        message.push_back((len >> 16) & 0xFF);
        message.push_back((len >> 8) & 0xFF);
        message.push_back(len & 0xFF);
        message.insert(message.end(), name.begin(), name.end());
    }

    void compute_exchange_hash(const std::array<uint8_t, 32>& server_host_key) {
        crypto_generichash_state hash_state;
        crypto_generichash_init(&hash_state, nullptr, 0, 32);

        // Client string
        std::string client_ver = "SSH-2.0-OpenSSH_9.0";
        crypto_generichash_update(&hash_state,
            reinterpret_cast<const uint8_t*>(client_ver.data()),
            client_ver.size()
        );

        // Server string
        std::string server_ver = "SSH-2.0-OpenSSH_9.0";
        crypto_generichash_update(&hash_state,
            reinterpret_cast<const uint8_t*>(server_ver.data()),
            server_ver.size()
        );

        // KEXINIT messages (simplified)
        // In production, include both client and server KEXINIT

        // Host key
        crypto_generichash_update(&hash_state,
            server_host_key.data(), 32
        );

        // Client ephemeral
        crypto_generichash_update(&hash_state,
            ephemeral_.public_key.data(), 32
        );

        // Server ephemeral
        crypto_generichash_update(&hash_state,
            state_.server_ephemeral.data(), 32
        );

        // Shared secret
        crypto_generichash_update(&hash_state,
            state_.shared_secret.data(), 32
        );

        crypto_generichash_final(&hash_state,
            state_.exchange_hash.data(), 32
        );
    }
};
```

### Melhores Práticas SSH

| Prática | Descrição |
|---------|-----------|
| Usar Ed25519 | Chaves Ed25519 são mais rápidas e seguras que RSA |
| Desabilitar password auth | Usar apenas autenticação por chave |
| Desabilitar root login | Nunca logar como root diretamente |
| Usar jump hosts | Acesso em duas etapas para sistemas sensíveis |
| Rate limiting | Limitar tentativas de login |
| Log monitoring | Monitorar tentativas de login falhas |
| Key rotation | Rotacionar chaves periodicamente |
| SSH Agent forwarding | Usar com cuidado, preferir ProxyJump |

---

## Noise Protocol Patterns em C++ com libsodium

### Pattern NN: Null

```
NN:
  -> e
  <- e, ee
```

Este é o padrão mais simples do Noise. Não há autenticação — apenas key exchange.

```cpp
#include <sodium.h>
#include <array>
#include <vector>
#include <cstring>
#include <stdexcept>

struct NoiseNNState {
    std::array<uint8_t, 32> h;          // Hash state
    std::array<uint8_t, 32> ck;         // Chain key
    std::array<uint8_t, 32> k;          // Encryption key (optional)
    bool has_key;
};

class NoiseNNInitiator {
public:
    NoiseNNInitiator() {
        if (sodium_init() < 0) {
            throw std::runtime_error("Failed to initialize libsodium");
        }
        initialize_state();
    }

    // Message 1: -> e
    std::vector<uint8_t> create_message_1() {
        // Generate ephemeral key pair
        crypto_kx_keypair(
            ephemeral_public_.data(),
            ephemeral_private_.data()
        );

        // Initialize hash with protocol name
        std::string protocol = "Noise_NN_25519_ChaChaPoly_BLAKE2s";
        std::memcpy(state_.h.data(), protocol.data(), 32);

        // MixHash with ephemeral public key
        mix_hash(ephemeral_public_.data(), 32);

        // Message is just the ephemeral public key
        return std::vector<uint8_t>(
            ephemeral_public_.begin(),
            ephemeral_public_.end()
        );
    }

    // Message 2: <- e, ee
    void process_message_2(const std::vector<uint8_t>& message_2) {
        // Message 2 contains: responder's ephemeral public key
        if (message_2.size() < 32) {
            throw std::runtime_error("Message 2 too short");
        }

        // MixHash with responder's ephemeral
        mix_hash(message_2.data(), 32);

        // Perform DH(initiator_ephemeral, responder_ephemeral)
        std::array<uint8_t, 32> dh_result;
        crypto_kx_deterministic_shared_key(
            dh_result.data(),
            ephemeral_private_.data(),
            message_2.data()
        );

        // MixKey with DH result
        mix_key(dh_result.data());
    }

    // Create encrypted data
    std::vector<uint8_t> encrypt(const std::vector<uint8_t>& plaintext) {
        if (!state_.has_key) {
            throw std::runtime_error("No encryption key available");
        }

        std::vector<uint8_t> ciphertext(
            plaintext.size() + crypto_aead_chacha20poly1305_ABYTES
        );

        std::array<uint8_t, 12> nonce;
        nonce.fill(0);

        unsigned long long ciphertext_len;
        crypto_aead_chacha20poly1305_encrypt(
            ciphertext.data(), &ciphertext_len,
            plaintext.data(), plaintext.size(),
            state_.h.data(), 32,
            nullptr,
            nonce.data(),
            state_.k.data()
        );

        ciphertext.resize(ciphertext_len);
        return ciphertext;
    }

private:
    NoiseNNState state_;
    std::array<uint8_t, 32> ephemeral_public_;
    std::array<uint8_t, 32> ephemeral_private_;

    void initialize_state() {
        state_.h.fill(0);
        state_.ck.fill(0);
        state_.k.fill(0);
        state_.has_key = false;
    }

    void mix_hash(const uint8_t* data, size_t len) {
        crypto_generichash_state hash_state;
        crypto_generichash_init(&hash_state, nullptr, 0, 32);
        crypto_generichash_update(&hash_state, state_.h.data(), 32);
        crypto_generichash_update(&hash_state, data, len);
        crypto_generichash_final(&hash_state, state_.h.data(), 32);
    }

    void mix_key(const uint8_t* input_key_material) {
        // HKDF-Extract
        std::array<uint8_t, 32> temp_key;
        crypto_kdf_derive_from_key(
            temp_key.data(), 32,
            0,
            reinterpret_cast<const uint8_t*>("NoiseMixKey"),
            11,
            input_key_material
        );

        // HKDF-Expand for chain key
        std::array<uint8_t, 32> new_ck;
        crypto_kdf_derive_from_key(
            new_ck.data(), 32,
            1,
            reinterpret_cast<const uint8_t*>("NoiseChainKey"),
            12,
            temp_key.data()
        );

        // HKDF-Expand for encryption key
        std::array<uint8_t, 32> new_k;
        crypto_kdf_derive_from_key(
            new_k.data(), 32,
            2,
            reinterpret_cast<const uint8_t*>("NoiseEncKey"),
            11,
            temp_key.data()
        );

        state_.ck = new_ck;
        state_.k = new_k;
        state_.has_key = true;

        // MixHash with encrypted zero
        std::array<uint8_t, 16> zero;
        zero.fill(0);
        mix_hash(zero.data(), zero.size());
    }
};
```

### Pattern NK: Initiator Known

```
NK:
  <- s
  ...
  -> e, es
  <- e, ee
```

Este padrão é usado quando o initiator conhece a chave estática do responder.

```cpp
#include <sodium.h>
#include <array>
#include <vector>
#include <cstring>
#include <stdexcept>

struct NoiseNKState {
    std::array<uint8_t, 32> h;
    std::array<uint8_t, 32> ck;
    std::array<uint8_t, 32> k;
    bool has_key;
};

class NoiseNKInitiator {
public:
    NoiseNKInitiator(
        const std::array<uint8_t, 32>& remote_static_public
    ) : remote_static_(remote_static_public) {
        if (sodium_init() < 0) {
            throw std::runtime_error("Failed to initialize libsodium");
        }
        initialize_state();
    }

    // Message 1: -> e, es
    std::vector<uint8_t> create_message_1() {
        // Generate ephemeral key pair
        crypto_kx_keypair(
            ephemeral_public_.data(),
            ephemeral_private_.data()
        );

        // Initialize hash with protocol name
        std::string protocol = "Noise_NK_25519_ChaChaPoly_BLAKE2s";
        std::memcpy(state_.h.data(), protocol.data(), 32);

        // MixHash with responder's static key (known in advance)
        mix_hash(remote_static_.data(), 32);

        // MixHash with ephemeral public key
        mix_hash(ephemeral_public_.data(), 32);

        // DH(ephemeral, responder_static)
        std::array<uint8_t, 32> dh_result;
        crypto_kx_deterministic_shared_key(
            dh_result.data(),
            ephemeral_private_.data(),
            remote_static_.data()
        );

        // MixKey with DH result
        mix_key(dh_result.data());

        // Encrypt empty payload
        std::vector<uint8_t> empty;
        return encrypt(empty);
    }

    // Message 2: <- e, ee
    void process_message_2(const std::vector<uint8_t>& message_2) {
        // Message 2 contains: encrypted responder ephemeral + MAC
        // In full implementation, decrypt to get ephemeral key
        // For simplicity, we assume we get the raw ephemeral

        // DH(responder_ephemeral, initiator_ephemeral)
        // This would be computed after decrypting message 2

        // For now, mark handshake as complete
        state_.has_key = true;
    }

private:
    NoiseNKState state_;
    std::array<uint8_t, 32> ephemeral_public_;
    std::array<uint8_t, 32> ephemeral_private_;
    std::array<uint8_t, 32> remote_static_;

    void initialize_state() {
        state_.h.fill(0);
        state_.ck.fill(0);
        state_.k.fill(0);
        state_.has_key = false;
    }

    void mix_hash(const uint8_t* data, size_t len) {
        crypto_generichash_state hash_state;
        crypto_generichash_init(&hash_state, nullptr, 0, 32);
        crypto_generichash_update(&hash_state, state_.h.data(), 32);
        crypto_generichash_update(&hash_state, data, len);
        crypto_generichash_final(&hash_state, state_.h.data(), 32);
    }

    void mix_key(const uint8_t* input_key_material) {
        std::array<uint8_t, 32> temp_key;
        crypto_kdf_derive_from_key(
            temp_key.data(), 32, 0,
            reinterpret_cast<const uint8_t*>("NoiseMixKey"), 11,
            input_key_material
        );

        std::array<uint8_t, 32> new_ck;
        crypto_kdf_derive_from_key(
            new_ck.data(), 32, 1,
            reinterpret_cast<const uint8_t*>("NoiseChainKey"), 12,
            temp_key.data()
        );

        std::array<uint8_t, 32> new_k;
        crypto_kdf_derive_from_key(
            new_k.data(), 32, 2,
            reinterpret_cast<const uint8_t*>("NoiseEncKey"), 11,
            temp_key.data()
        );

        state_.ck = new_ck;
        state_.k = new_k;
        state_.has_key = true;

        std::array<uint8_t, 16> zero;
        zero.fill(0);
        mix_hash(zero.data(), zero.size());
    }

    std::vector<uint8_t> encrypt(const std::vector<uint8_t>& plaintext) {
        std::vector<uint8_t> ciphertext(
            plaintext.size() + crypto_aead_chacha20poly1305_ABYTES
        );

        std::array<uint8_t, 12> nonce;
        nonce.fill(0);

        unsigned long long ciphertext_len;
        crypto_aead_chacha20poly1305_encrypt(
            ciphertext.data(), &ciphertext_len,
            plaintext.data(), plaintext.size(),
            state_.h.data(), 32,
            nullptr,
            nonce.data(),
            state_.k.data()
        );

        ciphertext.resize(ciphertext_len);
        return ciphertext;
    }
};
```

### Pattern XX: Full Mutual Authentication

```
XX:
  -> e
  <- e, ee, s, es
  -> s, se
```

Este padrão fornece autenticação mútua completa.

```cpp
#include <sodium.h>
#include <array>
#include <vector>
#include <cstring>
#include <stdexcept>

struct NoiseXXState {
    std::array<uint8_t, 32> h;
    std::array<uint8_t, 32> ck;
    std::array<uint8_t, 32> k;
    bool has_key;
};

class NoiseXXInitiator {
public:
    NoiseXXInitiator() {
        if (sodium_init() < 0) {
            throw std::runtime_error("Failed to initialize libsodium");
        }
        initialize_state();

        // Generate static key pair
        crypto_sign_keypair(
            static_public_.data(),
            static_secret_.data()
        );
    }

    // Message 1: -> e
    std::vector<uint8_t> create_message_1() {
        // Generate ephemeral key pair
        crypto_kx_keypair(
            ephemeral_public_.data(),
            ephemeral_private_.data()
        );

        // Initialize hash with protocol name
        std::string protocol = "Noise_XX_25519_ChaChaPoly_BLAKE2s";
        std::memcpy(state_.h.data(), protocol.data(), 32);

        // MixHash with ephemeral public key
        mix_hash(ephemeral_public_.data(), 32);

        // Message is just the ephemeral public key
        return std::vector<uint8_t>(
            ephemeral_public_.begin(),
            ephemeral_public_.end()
        );
    }

    // Message 2: <- e, ee, s, es
    void process_message_2(const std::vector<uint8_t>& message_2) {
        // In full implementation:
        // 1. Receive responder's ephemeral
        // 2. DH(initiator_ephemeral, responder_ephemeral)
        // 3. Receive encrypted static key
        // 4. DH(initiator_ephemeral, responder_static)
        // 5. Decrypt and verify

        state_.has_key = true;
    }

    // Message 3: -> s, se
    std::vector<uint8_t> create_message_3() {
        // Encrypt static key
        std::vector<uint8_t> encrypted_static =
            encrypt(std::vector<uint8_t>(
                static_public_.begin(),
                static_public_.end()
            ));

        // DH(initiator_static, responder_ephemeral)
        // This would be done in production

        return encrypted_static;
    }

    // Get static public key (for out-of-band verification)
    const std::array<uint8_t, 32>& get_static_public() const {
        return static_public_;
    }

private:
    NoiseXXState state_;
    std::array<uint8_t, 32> ephemeral_public_;
    std::array<uint8_t, 32> ephemeral_private_;
    std::array<uint8_t, 32> static_public_;
    std::array<uint8_t, 32> static_secret_;

    void initialize_state() {
        state_.h.fill(0);
        state_.ck.fill(0);
        state_.k.fill(0);
        state_.has_key = false;
    }

    void mix_hash(const uint8_t* data, size_t len) {
        crypto_generichash_state hash_state;
        crypto_generichash_init(&hash_state, nullptr, 0, 32);
        crypto_generichash_update(&hash_state, state_.h.data(), 32);
        crypto_generichash_update(&hash_state, data, len);
        crypto_generichash_final(&hash_state, state_.h.data(), 32);
    }

    void mix_key(const uint8_t* input_key_material) {
        std::array<uint8_t, 32> temp_key;
        crypto_kdf_derive_from_key(
            temp_key.data(), 32, 0,
            reinterpret_cast<const uint8_t*>("NoiseMixKey"), 11,
            input_key_material
        );

        std::array<uint8_t, 32> new_ck;
        crypto_kdf_derive_from_key(
            new_ck.data(), 32, 1,
            reinterpret_cast<const uint8_t*>("NoiseChainKey"), 12,
            temp_key.data()
        );

        std::array<uint8_t, 32> new_k;
        crypto_kdf_derive_from_key(
            new_k.data(), 32, 2,
            reinterpret_cast<const uint8_t*>("NoiseEncKey"), 11,
            temp_key.data()
        );

        state_.ck = new_ck;
        state_.k = new_k;
        state_.has_key = true;

        std::array<uint8_t, 16> zero;
        zero.fill(0);
        mix_hash(zero.data(), zero.size());
    }

    std::vector<uint8_t> encrypt(const std::vector<uint8_t>& plaintext) {
        if (!state_.has_key) {
            return plaintext;
        }

        std::vector<uint8_t> ciphertext(
            plaintext.size() + crypto_aead_chacha20poly1305_ABYTES
        );

        std::array<uint8_t, 12> nonce;
        nonce.fill(0);

        unsigned long long ciphertext_len;
        crypto_aead_chacha20poly1305_encrypt(
            ciphertext.data(), &ciphertext_len,
            plaintext.data(), plaintext.size(),
            state_.h.data(), 32,
            nullptr,
            nonce.data(),
            state_.k.data()
        );

        ciphertext.resize(ciphertext_len);
        mix_hash(ciphertext.data(), ciphertext_len);

        return ciphertext;
    }
};
```


---

## CVEs em Protocolos Criptográficos

### CVE-2020-26139: IPSec Traffic Amplification

#### Resumo

| Campo | Detalhe |
|-------|---------|
| CVE | CVE-2020-26139 |
| Data | 2020-07-06 |
| Severidade | CVSS 7.5 (Alto) |
| Impacto | Traffic amplification via IKEv1 header parsing |
| Produto | FreeSWITCH, StrongSwawn, e outros IKEv1 implementations |
| CWE | CWE-400 (Uncontrolled Resource Consumption) |
| CVSS Vector | AV:N/AC:L/PR:N/UI:N/S:U/C:N/I:N/A:H |

#### Descrição Detalhada

A vulnerabilidade CVE-2020-26139 afeta implementações IKEv1 que processam mensagens IKE_SA_INIT sem validar adequadamente o comprimento e o conteúdo dos payloads antes de gerar uma resposta.

O ataque explora a natureza stateless do IKEv1: o respondedor processa cada mensagem independentemente, sem verificar se existe uma sessão ativa. Isso permite que um atacante:

1. Envie uma mensagem IKE_SA_INIT falsificada com o IP de origem sendo a vítima
2. O respondedor envia a resposta para a vítima
3. A vítima recebe uma mensagem inesperada e pode responder
4. O ciclo continua, amplificando o tráfego

#### Código Vulnerável

```cpp
// VULNERABLE CODE - DO NOT USE IN PRODUCTION
// Simplified IKEv1 SA_INIT handler without proper validation

#include <cstdint>
#include <cstring>
#include <vector>

struct IKEv1SAInit {
    uint8_t initiator_spi[8];
    uint8_t responder_spi[8];
    uint8_t next_payload;
    uint8_t version;
    uint8_t exchange_type;
    uint8_t flags;
    uint32_t message_id;
    uint32_t length;
};

// VULNERABILITY: No validation of packet length before reading
// VULNERABILITY: No validation of SPI
// VULNERABILITY: No anti-replay mechanism
void handle_ikev1_sa_init_vulnerable(
    const uint8_t* packet,
    size_t packet_len,
    int socket_fd
) {
    // BUG: Does not check if packet_len >= sizeof(IKEv1SAInit)
    const IKEv1SAInit* header =
        reinterpret_cast<const IKEv1SAInit*>(packet);

    // BUG: Does not validate exchange_type
    // BUG: Does not validate DH group
    // BUG: Does not check if SPI is zero (initial message)

    // Reads DH public key without bounds checking
    const uint8_t* ke_data = packet + sizeof(IKEv1SAInit);
    uint16_t ke_length = packet_len - sizeof(IKEv1SAInit);

    // Generates response IMMEDIATELY
    // This enables reflection/amplification attacks
    std::vector<uint8_t> response;

    // Copy initiator SPI to responder SPI
    response.insert(response.end(),
        header->initiator_spi,
        header->initiator_spi + 8
    );

    // Generate random responder SPI
    uint8_t new_responder_spi[8];
    // VULNERABILITY: No CSPRNG used for SPI
    for (int i = 0; i < 8; ++i) {
        new_responder_spi[i] = rand() & 0xFF;
    }
    response.insert(response.end(),
        new_responder_spi,
        new_responder_spi + 8
    );

    // Copy and potentially amplify the DH data
    response.insert(response.end(), ke_data, ke_data + ke_length);

    // Send response without rate limiting
    send(socket_fd, response.data(), response.size(), 0);
}
```

#### Código Corrigido

```cpp
#include <sodium.h>
#include <cstdint>
#include <cstring>
#include <vector>
#include <stdexcept>
#include <chrono>
#include <unordered_map>

struct IKEv2Header {
    uint8_t initiator_spi[8];
    uint8_t responder_spi[8];
    uint8_t next_payload;
    uint8_t version;
    uint8_t exchange_type;
    uint8_t flags;
    uint32_t message_id;
    uint32_t length;
};

struct RateLimitEntry {
    uint64_t count;
    std::chrono::steady_clock::time_point window_start;
};

class SecureIKEv2Handler {
public:
    SecureIKEv2Handler() {
        if (sodium_init() < 0) {
            throw std::runtime_error("Failed to initialize libsodium");
        }
    }

    // SECURE: Validates all fields before processing
    bool handle_ikev2_sa_init(
        const uint8_t* packet,
        size_t packet_len,
        int socket_fd,
        const struct sockaddr* src_addr
    ) {
        // RATE LIMITING: Check if source is rate limited
        uint32_t src_ip = get_src_ip(src_addr);
        if (is_rate_limited(src_ip)) {
            return false; // Silently drop
        }

        // VALIDATION 1: Minimum packet length
        if (packet_len < sizeof(IKEv2Header)) {
            return false;
        }

        const IKEv2Header* header =
            reinterpret_cast<const IKEv2Header*>(packet);

        // VALIDATION 2: Exchange type must be IKE_SA_INIT (34)
        if (header->exchange_type != 34) {
            return false;
        }

        // VALIDATION 3: Version must be IKEv2 (0x20)
        if (header->version != 0x20) {
            return false;
        }

        // VALIDATION 4: SPI validation
        // Initiator SPI must not be all zeros
        bool all_zero = true;
        for (int i = 0; i < 8; ++i) {
            if (header->initiator_spi[i] != 0) {
                all_zero = false;
                break;
            }
        }
        if (all_zero) {
            return false;
        }

        // VALIDATION 5: Message length consistency
        uint32_t msg_len = header->length;
        if (msg_len < sizeof(IKEv2Header) || msg_len > packet_len) {
            return false;
        }

        // VALIDATION 6: Parse and validate payloads
        size_t offset = sizeof(IKEv2Header);
        uint8_t next_payload = header->next_payload;

        while (next_payload != 0 && offset < msg_len) {
            if (offset + 4 > msg_len) {
                return false; // Truncated payload
            }

            uint16_t payload_len = *reinterpret_cast<const uint16_t*>(
                packet + offset + 2
            );

            if (payload_len < 4 || offset + payload_len > msg_len) {
                return false; // Invalid payload length
            }

            // VALIDATE payload type
            if (next_payload == 38) { // SA payload
                if (!validate_sa_payload(packet + offset + 4, payload_len - 4)) {
                    return false;
                }
            } else if (next_payload == 38) { // KE payload
                if (!validate_ke_payload(packet + offset + 4, payload_len - 4)) {
                    return false;
                }
            }

            next_payload = packet[offset];
            offset += payload_len;
        }

        // RATE LIMITING: Increment counter
        increment_rate_limit(src_ip);

        // ANTI-REPLAY: Generate unique nonce
        uint8_t nonce[32];
        randombytes_buf(nonce, sizeof(nonce));

        // Generate response with proper SPI
        std::vector<uint8_t> response = generate_sa_init_response(
            header->initiator_spi, nonce
        );

        send(socket_fd, response.data(), response.size(), 0);
        return true;
    }

private:
    std::unordered_map<uint32_t, RateLimitEntry> rate_limits_;
    static constexpr uint64_t MAX_REQUESTS_PER_MINUTE = 10;
    static constexpr uint64_t MINIMUM_KE_LENGTH = 32;
    static constexpr uint64_t MAXIMUM_KE_LENGTH = 512;

    bool is_rate_limited(uint32_t src_ip) {
        auto now = std::chrono::steady_clock::now();
        auto& entry = rate_limits_[src_ip];

        auto elapsed = std::chrono::duration_cast<std::chrono::seconds>(
            now - entry.window_start
        ).count();

        if (elapsed >= 60) {
            entry.count = 0;
            entry.window_start = now;
            return false;
        }

        return entry.count >= MAX_REQUESTS_PER_MINUTE;
    }

    void increment_rate_limit(uint32_t src_ip) {
        rate_limits_[src_ip].count++;
    }

    uint32_t get_src_ip(const struct sockaddr* addr) {
        if (addr->sa_family == AF_INET) {
            return reinterpret_cast<const struct sockaddr_in*>(addr)
                ->sin_addr.s_addr;
        }
        return 0;
    }

    bool validate_sa_payload(const uint8_t* data, size_t len) {
        // Validate SA proposal structure
        // In production, parse SA attributes and validate DH groups
        return len >= 8;
    }

    bool validate_ke_payload(const uint8_t* data, size_t len) {
        // Validate KE payload
        if (len < 4) return false;

        uint16_t dh_group = *reinterpret_cast<const uint16_t*>(data);
        uint16_t ke_len = *reinterpret_cast<const uint16_t*>(data + 2);

        // Validate DH group (31 = Curve25519)
        if (dh_group != 31) return false;

        // Validate KE length
        if (ke_len < MINIMUM_KE_LENGTH || ke_len > MAXIMUM_KE_LENGTH) {
            return false;
        }

        return true;
    }

    std::vector<uint8_t> generate_sa_init_response(
        const uint8_t* initiator_spi,
        const uint8_t* nonce
    ) {
        std::vector<uint8_t> response;

        // IKEv2 header
        IKEv2Header header;
        std::memcpy(header.initiator_spi, initiator_spi, 8);
        randombytes_buf(header.responder_spi, 8);
        header.next_payload = 38; // SA
        header.version = 0x20;
        header.exchange_type = 34;
        header.flags = 0x20; // Response bit
        header.message_id = 0;

        response.insert(response.end(),
            reinterpret_cast<uint8_t*>(&header),
            reinterpret_cast<uint8_t*>(&header) + sizeof(header)
        );

        // In production: add SA, KE, Nonce payloads
        // with proper validation and anti-replay

        return response;
    }
};
```

#### Lições da CVE-2020-26139

1. **IKEv2 > IKEv1**: IKEv2 tem anti-replay nativo; IKEv1 não tem
2. **Rate limiting é essencial**: Todo endpoint deve limitar requisições
3. **Validação completa**: Todos os campos devem ser validados antes de processar
4. **Nonce uniqueness**: Nonces únicos previnem reflection attacks

---

### CVE-2023-0286: X.400 Remote Code Execution

#### Resumo

| Campo | Detalhe |
|-------|---------|
| CVE | CVE-2023-0286 |
| Data | 2023-02-08 |
| Severidade | CVSS 7.4 (Alto) |
| Impacto | Remote code execution via type confusion in X.400 |
| Produto | OpenSSL (implementação X.400) |
| CWE | CWE-843 (Type Confusion) |
| CVSS Vector | AV:N/AC:H/PR:N/UI:N/S:U/C:H/I:H/A:H |

#### Descrição Detalhada

A vulnerabilidade CVE-2023-0286 afeta a implementação do protocolo X.400 no OpenSSL. X.400 é um protocolo de mensagens usado historicamente em sistemas de email, especialmente em ambientes militares e governamentais.

O problema ocorre quando o OpenSSL processa campos ASN.1 de tipo incorreto em mensagens X.400. Um atacante pode enviar uma mensagem X.400 malformada que cause type confusion, levando a memory corruption e potencialmente remote code execution.

#### Código Vulnerável

```cpp
// VULNERABLE CODE - DO NOT USE IN PRODUCTION
// Simplified X.400 message processing without type validation

#include <cstdint>
#include <cstring>
#include <vector>
#include <openssl/asn1.h>
#include <openssl/x509v3.h>

struct X400Message {
    ASN1_STRING* subject;
    ASN1_STRING* content;
    ASN1_STRING* sender;
};

// VULNERABILITY: No type checking on ASN.1 fields
// VULNERABILITY: No bounds checking on string lengths
void process_x400_message_vulnerable(const uint8_t* data, size_t len) {
    // Parse ASN.1 structure
    const uint8_t* p = data;
    X400Message msg = {};

    // BUG: Assumes ASN.1 type without verification
    // The data could be INTEGER when IA5String is expected
    msg.subject = d2i_ASN1_IA5String(nullptr, &p, len);

    // BUG: Does not check if subject is NULL before dereferencing
    // BUG: Does not validate string length
    if (msg.subject->data && msg.subject->length > 0) {
        // Process subject
        // This could read out of bounds if length is corrupted
        for (int i = 0; i < msg.subject->length; ++i) {
            char c = msg.subject->data[i];
            // Process character...
        }
    }

    // BUG: Same issues for other fields
    msg.content = d2i_ASN1_IA5String(nullptr, &p, len);
    msg.sender = d2i_ASN1_IA5String(nullptr, &p, len);

    // BUG: No cleanup on error paths
    // Memory leak and potential use-after-free
}
```

#### Código Corrigido

```cpp
#include <openssl/asn1.h>
#include <openssl/err.h>
#include <openssl/x509v3.h>
#include <cstdint>
#include <cstring>
#include <vector>
#include <stdexcept>
#include <memory>

// Custom deleters for RAII
struct ASN1Deleter {
    void operator()(ASN1_STRING* ptr) {
        if (ptr) ASN1_STRING_free(ptr);
    }
};

struct ASN1TypeDeleter {
    void operator()(ASN1_TYPE* ptr) {
        if (ptr) ASN1_TYPE_free(ptr);
    }
};

using ASN1StringPtr = std::unique_ptr<ASN1_STRING, ASN1Deleter>;
using ASN1TypePtr = std::unique_ptr<ASN1_TYPE, ASN1TypeDeleter>;

struct SecureX400Message {
    ASN1StringPtr subject;
    ASN1StringPtr content;
    ASN1StringPtr sender;
    bool valid;

    SecureX400Message() : valid(false) {}
};

class SecureX400Processor {
public:
    SecureX400Processor() {
        // Initialize OpenSSL error handling
        ERR_load_crypto_strings();
    }

    ~SecureX400Processor() {
        EVP_cleanup();
    }

    // SECURE: Validates ASN.1 type before processing
    SecureX400Message process_x400_message(
        const uint8_t* data,
        size_t len
    ) {
        SecureX400Message msg;

        try {
            const uint8_t* p = data;

            // VALIDATION 1: Check minimum length
            if (len < 10) {
                throw std::runtime_error("Message too short");
            }

            // VALIDATION 2: Parse and validate subject
            msg.subject = parse_ia5_string(&p, len - (p - data));

            // VALIDATION 3: Validate subject content
            if (msg.subject) {
                validate_string_content(msg.subject.get());
            }

            // VALIDATION 4: Parse and validate content
            msg.content = parse_ia5_string(&p, len - (p - data));

            // VALIDATION 5: Validate content
            if (msg.content) {
                validate_string_content(msg.content.get());
            }

            // VALIDATION 6: Parse and validate sender
            msg.sender = parse_ia5_string(&p, len - (p - data));

            // VALIDATION 7: Validate sender
            if (msg.sender) {
                validate_string_content(msg.sender.get());
            }

            msg.valid = true;

        } catch (const std::exception& e) {
            // Clean up on error
            msg.valid = false;
            ERR_free_errors();
        }

        return msg;
    }

private:
    // SECURE: Parses ASN.1 IA5String with type validation
    ASN1StringPtr parse_ia5_string(
        const uint8_t** pp,
        size_t remaining
    ) {
        if (remaining < 2) {
            throw std::runtime_error("Truncated ASN.1 tag");
        }

        // Read ASN.1 tag
        uint8_t tag = **pp;

        // VALIDATION: Must be IA5String (tag 22) or UTF8String (tag 12)
        if (tag != 22 && tag != 12) {
            throw std::runtime_error("Invalid ASN.1 type for string");
        }

        (*pp)++;

        // Read length
        uint8_t len_byte = **pp;
        (*pp)++;
        remaining -= 2;

        uint32_t str_len;
        if (len_byte < 128) {
            str_len = len_byte;
        } else if (len_byte == 0x81) {
            if (remaining < 1) throw std::runtime_error("Truncated length");
            str_len = **pp;
            (*pp)++;
            remaining--;
        } else if (len_byte == 0x82) {
            if (remaining < 2) throw std::runtime_error("Truncated length");
            str_len = (**pp) << 8 | (*pp)[1];
            (*pp) += 2;
            remaining -= 2;
        } else {
            throw std::runtime_error("Unsupported ASN.1 length encoding");
        }

        // VALIDATION: Length bounds
        if (str_len > 1024) {
            throw std::runtime_error("String too long");
        }
        if (str_len > remaining) {
            throw std::runtime_error("String length exceeds remaining data");
        }

        // Parse the string
        ASN1StringPtr result(
            d2i_ASN1_IA5String(nullptr, pp, str_len),
            ASN1Deleter()
        );

        if (!result) {
            throw std::runtime_error("Failed to parse IA5String");
        }

        return result;
    }

    // SECURE: Validates string content
    void validate_string_content(const ASN1_STRING* str) {
        if (!str) {
            throw std::runtime_error("NULL string");
        }

        const unsigned char* data = ASN1_STRING_get0_data(str);
        int len = ASN1_STRING_length(str);

        if (len < 0 || len > 1024) {
            throw std::runtime_error("Invalid string length");
        }

        // Validate character encoding
        for (int i = 0; i < len; ++i) {
            unsigned char c = data[i];

            // IA5String: only ASCII characters (0-127)
            if (c > 127) {
                throw std::runtime_error("Non-ASCII character in IA5String");
            }

            // Check for control characters
            if (c < 32 && c != '\n' && c != '\r' && c != '\t') {
                throw std::runtime_error("Invalid control character");
            }
        }
    }
};
```

#### Lições da CVE-2023-0286

1. **Type confusion é perigoso**: ASN.1 permite tipagem dinâmica; sempre valide o tipo antes de processar
2. **Bounds checking é obrigatório**: Strings ASN.1 podem ter comprimentos arbitrários
3. **RAII previne memory leaks**: Use smart pointers para ASN.1 objects
4. **Error handling completo**: Limpe recursos em todos os caminhos de erro
5. **Protocolos legados são perigosos**: X.400 é antigo e menos testado que protocolos modernos

---

### CVE-2021-3449: OpenSSL NULL Dereference

#### Resumo

| Campo | Detalhe |
|-------|---------|
| CVE | CVE-2021-3449 |
| Data | 2021-03-25 |
| Severidade | CVSS 5.9 (Médio) |
| Impacto | NULL pointer dereference causing crash (DoS) |
| Produto | OpenSSL 1.1.1e-1.1.1j |
| CWE | CWE-476 (NULL Pointer Dereference) |
| CVSS Vector | AV:N/AC:H/PR:N/UI:N/S:U/C:N/I:N/A:H |

#### Descrição Detalhada

A vulnerabilidade CVE-2021-3449 afeta o OpenSSL em versões entre 1.1.1e e 1.1.1j. O problema ocorre quando um cliente TLS envia um renegotiation_info extension malformado durante o handshake.

Se o servidor OpenSSL receber um renegotiation_info com comprimento zero durante a renegociação, ele tentará acessar um ponteiro NULL, causando um crash (denial of service).

#### Código Vulnerável

```cpp
// VULNERABLE CODE - DO NOT USE IN PRODUCTION
// Simplified renegotiation handling

#include <openssl/ssl.h>
#include <openssl/err.h>
#include <cstdint>
#include <cstring>

// VULNERABILITY: Does not check renegotiation_info length
// before accessing it
void handle_renegotiation_info_vulnerable(
    SSL* ssl,
    const uint8_t* ext_data,
    uint16_t ext_len
) {
    // BUG: ext_len could be 0
    // BUG: ext_data could be NULL
    // BUG: No validation before dereferencing

    // This dereferences ext_data without checking if it's valid
    uint8_t first_byte = ext_data[0];  // CRASH if ext_len == 0

    // Process renegotiation info
    // If first_byte indicates SCSV, process accordingly
    if (first_byte == 0xff) {
        // SCSV (Signaling Cipher Suite Value)
        // Process without checking buffer bounds
    }
}
```

#### Código Corrigido

```cpp
#include <openssl/ssl.h>
#include <openssl/err.h>
#include <cstdint>
#include <cstring>
#include <stdexcept>

class SecureTLSHandler {
public:
    SecureTLSHandler() {
        // Initialize OpenSSL
        SSL_load_error_strings();
        OpenSSL_add_all_algorithms();
    }

    ~SecureTLSHandler() {
        EVP_cleanup();
        ERR_free_strings();
    }

    // SECURE: Validates renegotiation_info extension
    bool handle_renegotiation_info(
        SSL* ssl,
        const uint8_t* ext_data,
        uint16_t ext_len
    ) {
        // VALIDATION 1: Check if extension data is NULL
        if (ext_data == nullptr) {
            return false;
        }

        // VALIDATION 2: Check minimum length
        if (ext_len < 1) {
            return false;
        }

        // VALIDATION 3: Check maximum length
        if (ext_len > 65535) {
            return false;
        }

        // VALIDATION 4: Safe dereference
        uint8_t first_byte = ext_data[0];

        // VALIDATION 5: Check if it's SCSV
        if (first_byte == 0xff) {
            // SCSV handling with bounds checking
            if (ext_len < 2) {
                return false;
            }

            // Process SCSV safely
            uint16_t scsv_value =
                (ext_data[0] << 8) | ext_data[1];

            if (!process_scsv(ssl, scsv_value)) {
                return false;
            }
        } else {
            // Regular renegotiation_info handling
            if (!process_renegotiation_info(ssl, ext_data, ext_len)) {
                return false;
            }
        }

        return true;
    }

    // SECURE: Process SCSV with validation
    bool process_scsv(SSL* ssl, uint16_t scsv_value) {
        // Validate SCSV value
        switch (scsv_value) {
            case 0x00ff: // TLS_FALLBACK_SCSV
                // Handle fallback
                break;
            case 0x5600: // EMPTY_RENEGOTIATION_INFO_SCSV
                // Handle empty renegotiation
                break;
            default:
                return false; // Unknown SCSV
        }

        return true;
    }

    // SECURE: Process renegotiation info with validation
    bool process_renegotiation_info(
        SSL* ssl,
        const uint8_t* data,
        uint16_t len
    ) {
        // Parse renegotiation info with bounds checking
        size_t offset = 0;

        while (offset < len) {
            // Check remaining bytes
            if (offset + 1 > len) {
                return false; // Truncated
            }

            uint8_t info_type = data[offset];
            offset++;

            switch (info_type) {
                case 0x01: // renegotiated_connection
                    if (offset + 1 > len) return false;
                    uint8_t conn_len = data[offset];
                    offset++;

                    if (offset + conn_len > len) return false;
                    // Process connection data safely
                    offset += conn_len;
                    break;

                default:
                    return false; // Unknown info type
            }
        }

        return true;
    }

    // SECURE: Safe renegotiation setup
    bool setup_renegotiation(SSL* ssl) {
        // Enable secure renegotiation
        if (SSL_set_tlsext_host_name(ssl, nullptr) != 1) {
            return false;
        }

        // Set renegotiation info callback
        SSL_CTX_set_info_callback(
            SSL_get_SSL_CTX(ssl),
            info_callback
        );

        return true;
    }

private:
    static void info_callback(const SSL* ssl, int type, int val) {
        int alert_type = SSL_alert_type_string_long(val);
        int alert_desc = SSL_alert_desc_string_long(val);

        // Log renegotiation events for monitoring
        // In production, use proper logging framework
    }
};
```

#### Lições da CVE-2021-3449

1. **NULL checks são obrigatórios**: Sempre verifique ponteiros antes de desreferenciar
2. **Bounds checking em todos os lados**: Valide comprimentos antes de acessar buffers
3. **Extensions são perigosas**: Cada extensão TLS pode ter formato inesperado
4. **DoS via crash**: Mesmo sem remote code execution, um crash é uma vulnerabilidade séria
5. **Testing de edge cases**: Teste com extensions vazias, malformadas e no limite

---

## Verificação Formal de Protocolos

### O Que é Verificação Formal

Verificação formal é o processo de usar modelos matemáticos para provar que um protocolo atende suas especificações de segurança. Diferente de testing, que verifica implementações específicas, verificação formal prova propriedades para todas as execuções possíveis.

### Ferramentas de Verificação Formal

| Ferramenta | Modelo | Uso Principal |
|------------|--------|---------------|
| ProVerif | Dolev-Yao | Autenticação, confidencialidade |
| Tamarin | Multi-set rewriting | Protocolos complexos, stateful |
| CryptoVerif | Computational model | Segurança computacional |
| SPASS | First-order logic | Provas manuais |

### ProVerif: Verificação de Protocolos

#### Como ProVerif Funciona

1. **Especificação**: Descreva o protocolo em pi-calculus
2. **Propriedades**: Defina o que quer provar (confidencialidade, autenticação)
3. **Verificação**: ProVerif tenta encontrar ataques ou prova que não existem

#### Exemplo de Especificação ProVerif

```
(* Protocolo simplificado de key exchange *)

(* Definição de tipos *)
type skey.
type pkey.
type msg.

(* Funções criptográficas *)
fun pk: skey -> pkey.
fun h: msg -> skey.
reduc forall m: msg; s: skey;
  dec(enc(m, pk(s)), s) = m.

(* Processo do initiator *)
let s_a: skey = h(new na: bitstring) in
let p_a: pkey = pk(s_a) in
out(c, (p_a, na));

in(c, nb: bitstring);
let m: bitstring = enc(na, pk(s_a)) in
out(c, enc(nb, pk(s_a)))

(* Processo do responder *)
let s_b: skey = h(new nb: bitstring) in
let p_b: pkey = pk(s_b) in
in(c, (p_a': pkey, na': bitstring));
out(c, enc(na', p_a'));

in(c, m': bitstring);
dec(m', s_b)

(* Verificação de propriedades *)
query attacker(na).
query attacker(nb).
query event(Recv_a(event)).
event(Recv_a(event)) ==> event(Send_a(event)).
```

#### Análise com ProVerif

ProVerif analisa o protocolo e verifica:

1. **Confidencialidade**: O atacante pode aprender os valores secretos?
2. **Autenticação**: O initiator está comunicando com o responder correto?
3. **Forward secrecy**: Comprometer chaves futuras revela chaves passadas?

Se ProVerif encontrar um ataque, ele gera uma trace do ataque. Se não encontrar, ele prova que o protocolo é seguro sob o modelo Dolev-Yao.

### Tamarin: Verificação de Protocolos Complexos

#### Como Tamarin Funciona

Tamarin usa multi-set rewriting para modelar protocolos. É mais poderoso que ProVerif para protocolos stateful, mas mais difícil de usar.

#### Exemplo de Especificação Tamarin

```
theory SignalProtocol
begin

(* Definição de mensagens *)
builtins:
  dh,
  signing

(* Regras de protocolo *)

rule GenerateKeyPair:
  [ Fr(~k) ]
  -->
  [ !KeyPair(~k, pk(~k)) ]

rule X3DH_Initiator:
  [ Fr(~sk_i)
  , Fr(~ek_i)
  , KeyPair(~sk_i, pk_i)
  , KeyPair(~ek_i, pk(~ek_i))
  , !KeyPair(~sk_r, pk_r)
  , !KeyPair(~ek_r, pk(~ek_r))
  ]
  -->
  [ !State_X3DH(pk_i, pk_r, dh(~sk_i, pk_r), dh(~ek_i, pk_r), dh(~ek_i, pk(~ek_r)))
  , Out( pk_i, pk(~ek_i) )
  ]

rule X3DH_Responder:
  [ !KeyPair(~sk_r, pk_r)
  , !KeyPair(~ek_r, pk(~ek_r))
  , In( pk_i, pk_ek_i )
  ]
  -->
  [ !State_X3DH(pk_i, pk_r, dh(pk_i, ~sk_r), dh(pk_ek_i, ~sk_r), dh(pk_ek_i, ~sk_r))
  , Out( pk(~ek_r) )
  ]

(* Propriedades de segurança *)

(* Forward Secrecy *)
lemma ForwardSecrecy:
  "All x #i. State_X3DH(x) @ i ==> not (Ex y #j. K(y) @ j & y = x)"

(* Authentication *)
lemma Authentication:
  "All x y #i. State_X3DH(x, y) @ i ==> (Ex z #j. State_X3DH(z, y) @ j)"

end
```

### Comparação: ProVerif vs Tamarin

| Aspecto | ProVerif | Tamarin |
|---------|----------|---------|
| Modelo | Dolev-Yao | Multi-set rewriting |
| Automação | Alta | Média |
| Expressividade | Média | Alta |
| Casos de uso | Key exchange, autenticação | Protocolos complexos, stateful |
| Curva de aprendizado | Baixa | Alta |
| Desempenho | Bom para protocolos pequenos | Pode ser lento |
| Resultados | "Trace found" ou "verified" | Satisfiability checking |

### Quando Usar Verificação Formal

| Cenário | Recomendação |
|---------|--------------|
| Novo protocolo criptográfico | Obrigatório |
| Modificação de protocolo existente | Recomendado |
| Implementação de padrão IETF | Recomendado |
| Protocolo proprietário | Altamente recomendado |
| Quick fix em código existente | Não necessário |

---

## Exercícios

### Exercício 1: Implementação X3DH

Implemente o protocolo X3DH completo em C++ usando libsodium. Seu programa deve:

1. Gerar key bundles para Alice e Bob
2. Implementar o handshake X3DH
3. Derivar uma chave de sessão
4. Criptografar e descriptografar mensagens

**Requisitos**:
- Use `crypto_kx_*` para key exchange
- Use `crypto_kdf_*` para key derivation
- Documente cada passo do handshake
- Inclua testes unitários

```cpp
// Estrutura esperada:
struct X3DHSession {
    std::array<uint8_t, 32> session_key;
    bool handshake_complete;
};

X3DHSession establish_session(
    const KeyBundle& initiator_bundle,
    const KeyBundle& responder_bundle
);
```

### Exercício 2: Double Ratchet Completo

Implemente o Double Ratchet com suporte a mensagens fora de ordem. Seu programa deve:

1. Implementar o DH ratchet
2. Implementar o symmetric ratchet
3. Suportar mensagens fora de ordem
4. Implementar key caching

**Requisitos**:
- Use HKDF para key derivation
- Implemente replay protection
- Teste com mensagens em ordem diferentes

### Exercício 3: Noise Pattern Analysis

Analise o padrão Noise IK e responda:

1. Quais propriedades de segurança o padrão IK fornece?
2. Compare com o padrão XX: quais são as diferenças?
3. Em que cenários você usaria IK vs XX?
4. Implemente o handshake IK completo em C++.

### Exercício 4: CVE Analysis

Analise a CVE-2021-3449 e implemente:

1. Um servidor TLS vulnerável que aceita renegotiation_info vazio
2. Um cliente que explora a vulnerabilidade (para teste)
3. Uma versão corrigida do servidor
4. Um teste automatizado que verifica a correção

### Exercício 5: WireGuard Implementation

Implemente um WireGuard simplificado que suporte:

1. Handshake 1-RTT
2. Encryption/decryption de pacotes
3. Replay protection
4. Key rotation

**Requisitos**:
- Use ChaCha20-Poly1305 para encryption
- Use Curve25519 para key exchange
- Documente as decisões de design
- Inclua benchmarks de performance

### Exercício 6: OPAQUE Registration

Implemente o protocolo OPAQUE para autenticação baseada em senha. Seu programa deve:

1. Implementar a fase de registration
2. Implementar a fase de autenticação
3. Proteger contra offline dictionary attacks
4. Incluir testes de segurança

```cpp
// Estrutura esperada:
struct OpaqueSession {
    std::array<uint8_t, 32> session_key;
    bool authenticated;
};

OpaqueSession opaque_authenticate(
    const std::string& password,
    const std::vector<uint8_t>& stored_envelope
);
```

### Exercício 7: Protocol Verification

Use ProVerif ou Tamarin para verificar um protocolo de key exchange simples:

1. Escreva a especificação do protocolo
2. Defina as propriedades de segurança
3. Execute a verificação
4. Interprete os resultados
5. Se encontrar um ataque, corrija o protocolo e re-verifique

---

## Referências

### Livros

1. **Handbook of Applied Cryptography** — Menezes, van Oorschot, Vanstone
   - Referência clássica para primitivas criptográficas
   - Capítulos 10-12 cobrem protocolos de key transport e agreement

2. **Cryptography Engineering** — Ferguson, Schneier, Kohno
   - Foco em implementação prática
   - Cobertura de protocolos reais e suas armadilhas

3. **Security Engineering** — Ross Anderson
   - Visão ampla de segurança incluindo protocolos
   - Capítulos sobre banking, DRM, e telecom

4. **Provable Security** — Jonathan Katz, Yehuda Lindell
   - Fundamentos de segurança provável
   - Modelos formais para protocolos

### Papers

5. **The Signal Protocol** — Cohn-Gordon et al., 2020
   - Análise formal do Signal Protocol
   - Prova de segurança no modelo UC

6. **Noise Protocol Framework** — Perrin, 2018
   - Especificação completa do Noise
   - Design de handshake patterns

7. **OPAQUE: An Asymmetric PAKE Protocol** — Jarecki et al., 2018
   - Especificação do OPAQUE
   - Prova de segurança no modelo UC

8. **WireGuard: Modern and Secure VPN** — Donenfeld, 2017
   - Design do WireGuard
   - Comparação com IPSec/OpenVPN

### RFCs

9. **RFC 8247** — IKEv2
   - Especificação oficial do IKEv2

10. **RFC 4301** — Security Architecture for IP
    - Arquitetura de segurança do IPSec

11. **RFC 4253** — SSH Transport Layer Protocol
    - Especificação do SSH

12. **RFC 8446** — TLS 1.3
    - Especificação do TLS 1.3

### CVEs

13. **CVE-2020-26139** — IPSec Traffic Amplification
    - NVD: https://nvd.nist.gov/vuln/detail/CVE-2020-26139

14. **CVE-2023-0286** — X.400 Type Confusion
    - OpenSSL Security Advisory: https://www.openssl.org/news/secadv/20230208.txt

15. **CVE-2021-3449** — OpenSSL NULL Dereference
    - OpenSSL Security Advisory: https://www.openssl.org/news/secadv/20210325.txt

### Ferramentas

16. **ProVerif** — https://bblanche.gitlabpages.inria.fr/proverif/
    - Ferramenta de verificação formal de protocolos

17. **Tamarin Prover** — https://tamarin-prover.github.io/
    - Ferramenta de verificação para protocolos complexos

18. **libsodium** — https://doc.libsodium.org/
    - Biblioteca de criptografia de alto nível

19. **WireGuard** — https://www.wireguard.com/
    - VPN moderna e segura

20. **Signal Protocol** — https://signal.org/docs/
    - Documentação do Signal Protocol

---

## Resumo

### Protocolos Cobertos

| Protocolo | Tipo | Uso Principal | Padrão |
|-----------|------|---------------|--------|
| Signal (X3DH + Double Ratchet) | Key exchange + messaging | Mensageria segura | De facto |
| OPAQUE | PAKE | Autenticação por senha | RFC草案 |
| Noise Framework | Handshake patterns | Protocolos customizados | Specification |
| WireGuard | VPN | Acesso remoto | RFC草案 |
| IPSec/IKEv2 | VPN | VPN corporativa | RFC 7296 |
| SSH | Remote access | Acesso a servidores | RFC 4253 |

### CVEs Documentadas

| CVE | Protocolo | Tipo de Falha | Lição Principal |
|-----|-----------|---------------|-----------------|
| CVE-2020-26139 | IPSec/IKEv1 | Traffic amplification | Usar IKEv2, rate limiting |
| CVE-2023-0286 | X.400 | Type confusion | Validar tipos ASN.1 |
| CVE-2021-3449 | TLS | NULL dereference | Null checks obrigatórios |

### Princípios Fundamentais

1. **Nunca invente um protocolo**: Use padrões estabelecidos (Noise, Signal)
2. **Valide tudo**: Comprimentos, tipos, ponteiros, nonces
3. **Use libraries estabelecidas**: libsodium, OpenSSL — não reimplemente
4. **Teste contra ataques**: Fuzzing, formal verification, code review
5. **Mantenha-se atualizado**: CVEs surgem regularmente

### Próximo Capítulo

No [Capítulo 09: Hardware Security — TPM e Enclaves](09-hardware-security-tpm.md), veremos como integrar hardware security modules com protocolos criptográficos para proteção de chaves em hardware.

---

*[Capítulo anterior: 07 — Gestão de Chaves Avançada](07-gestao-chaves-avancada.md)*
*[Capítulo 9: Hardware Security — TPM e Enclaves](09-hardware-security-tpm.md)*
