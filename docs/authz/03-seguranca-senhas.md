---
layout: default
title: "03-seguranca-senhas"
---

# Capítulo 3 — Segurança de Senhas

> *"Uma senha armazenada em texto plano não é uma senha — é um convite aberto."*

---

## Objetivos de Aprendizado

Ao final deste capítulo, você será capaz de:

1. **Implementar armazenamento seguro de senhas** usando algoritmos de hashing modernos (Argon2id, bcrypt, scrypt), compreendendo por que MD5, SHA-1 e SHA-256 são inadequados para proteger credenciais.
2. **Configurar parâmetros de hashing** que equilibrem segurança e performance, ajustando custo computacional conforme o hardware disponível evolui.
3. **Implementar salting e peppering** corretamente, entendendo o papel de cada um na proteção contra rainbow tables e ataques offline.
4. **Aplicar políticas de senha baseadas em evidências** seguindo o NIST SP 800-63B, evitando requisitos arbitrários que degradam a experiência do usuário sem melhorar a segurança.
5. **Integrar verificações contra databases de vazamentos** (Have I Been Pwned) para impedir o uso de senhas comprometidas.
6. **Implementar rate limiting, bloqueio de contas e fluxos seguros de recuperação de senha** que protejam contra força bruta e abuso.
7. **Analisar o caso Misantropi4** demonstrando como senhas não rotacionadas e reutilizadas entre sistemas transformaram uma violação pontual em um ataque nacional.

---

## 3.1 Armazenamento de Senhas: Hashing vs Criptografia

### 3.1.1 A Diferença Fundamental

A escolha entre hashing e criptografia para proteger senhas não é uma preferência — é uma questão de segurança com uma resposta correta e uma errada.

| Aspecto | Hashing | Criptografia |
|---------|---------|-------------|
| Operacao | Unidirecional (irreversivel) | Bidirecional (reversivel) |
| Objetivo | Verificar sem revelar | Proteger para revelar depois |
| Uso correto | Senhas, biometria | Dados que precisam ser recuperados |
| Uso para senhas | CORRETO | INCORRETO |
| Recuperacao da original | Impossivel (intencionalmente) | Possivel com a chave |

**Por que hashing é correto para senhas:**

Se um atacante obtém o banco de dados, com hashing ele precisa fazer força bruta para descobrir cada senha. Com criptografia, se o atacante obtém a chave de criptografia, todas as senhas são reveladas instantaneamente.

O caso Adobe (2013) é o exemplo mais claro: a empresa usou 3DES em modo ECB com chave fixa para "criptografar" senhas. Quando 153 milhões de contas foram vazadas, os pesquisadores conseguiram recuperar senhas em massa porque o esquema era reversível.

### 3.1.2 Por Que MD5/SHA-1/SHA-256 Não São Hashes de Senha

Algoritmos como MD5, SHA-1 e SHA-256 são funções de hash criptográficas, não funções de hashing de senhas. A distinção é crucial:

| Caracteristica | Hash Criptografico (MD5/SHA) | Hash de Senha (Argon2/bcrypt) |
|---------------|------------------------------|-------------------------------|
| Velocidade | O mais rapido possivel | Intencionalmente lento |
| Resistencia a GPU | Baixa (GPU acelera massivamente) | Alta (memória intencionalmente usada) |
| Salt incorporado | Nao | Sim |
| Parametros ajustaveis | Nao | Sim |
| Work factor | Fixo | Ajustavel ao hardware |

**A velocidade é o problema:**

Uma GPU moderna (RTX 4090) pode calcular:
- **~10 bilhões** de hashes SHA-256 por segundo
- **~500 milhões** de hashes bcrypt (cost=5) por segundo
- **~2 milhões** de hashes Argon2id (64MB, 3 iterações) por segundo

Para um atacante, isso significa:

| Algoritmo | Senhas por segundo (1 GPU) | Tempo para 1 bilhao de senhas |
|-----------|--------------------------|-------------------------------|
| MD5 | 50 bilhoes | 0.02 segundos |
| SHA-256 | 10 bilhoes | 0.1 segundos |
| bcrypt (cost=10) | 30.000 | 9.3 horas |
| Argon2id (64MB) | 2.000 | 5.8 dias |

A diferença é de ordens de magnitude. Usar SHA-256 para senhas é como trancar a porta da frente e deixar a janela do quarto escancarada.

```python
import hashlib
import time
import secrets

class VulnerablePasswordHasher:
    """VULNERABLE: Using SHA-256 for password hashing. DO NOT USE."""

    def hash_password(self, password: str) -> str:
        """SHA-256 hash without salt. Trivially crackable."""
        return hashlib.sha256(password.encode()).hexdigest()

    def benchmark(self, iterations: int = 100000) -> float:
        """Benchmark SHA-256 speed."""
        start = time.time()
        for _ in range(iterations):
            self.hash_password("test_password_123")
        elapsed = time.time() - start
        return iterations / elapsed

# Result: ~5,000,000 hashes/second on a single CPU core
# An attacker with 10 GPUs could test 50 billion passwords/second
```

```python
import argon2
import time

class SecurePasswordHasher:
    """SECURE: Using Argon2id for password hashing."""

    def __init__(self):
        self.hasher = argon2.PasswordHasher(
            time_cost=3,
            memory_cost=65536,  # 64 MB
            parallelism=4,
            hash_len=32,
            salt_len=16,
        )

    def hash_password(self, password: str) -> str:
        """Argon2id hash with built-in salt."""
        return self.hasher.hash(password)

    def verify_password(self, password: str,
                        stored_hash: str) -> bool:
        """Constant-time verification."""
        try:
            return self.hasher.verify(stored_hash, password)
        except argon2.exceptions.VerifyMismatchError:
            return False
        except argon2.exceptions.InvalidHashError:
            return False

    def benchmark(self, iterations: int = 100) -> float:
        """Benchmark Argon2id speed."""
        start = time.time()
        for _ in range(iterations):
            self.hash_password("test_password_123")
        elapsed = time.time() - start
        return iterations / elapsed

# Result: ~50 hashes/second on a single CPU core
# An attacker with 10 GPUs: ~500 hashes/second
# Time to crack 1 billion passwords: ~63 years
```

---

## 3.2 Algoritmos de Hashing: Comparação Detalhada

### 3.2.1 bcrypt

bcrypt é baseado no algoritmo Blowfish e é um dos mais usados para hashing de senhas. Foi projetado para ser lento e resistente a ataques de hardware.

**Parâmetros:**
- **Cost factor (log_rounds)**: Controla o número de iterações. O padrão é 12, mas deve ser ajustado para manter ~100ms por hash.
- **Salt**: 16 bytes gerados aleatoriamente, incorporados automaticamente.

**Vantagens:**
- Amplamente suportado (bibliotecas em todas as linguagens)
- Fácil de usar corretamente
- Resistente a GPU ( Blowfish usa operações de lookup table)

**Limitações:**
- Uso de memória é limitado (4KB por padrão)
- Pode ser acelerado com FPGA/ASIC dedicados
- Tamanho da senha limitado a 72 bytes (na maioria das implementações)

```python
import bcrypt
import secrets
import time

class BcryptPasswordHasher:
    """bcrypt password hashing with adaptive cost."""

    def __init__(self, base_cost: int = 12):
        self.base_cost = base_cost

    def hash_password(self, password: str) -> str:
        """Hash password with bcrypt."""
        salt = bcrypt.gensalt(rounds=self.base_cost)
        return bcrypt.hashpw(
            password.encode("utf-8"), salt
        ).decode("utf-8")

    def verify_password(self, password: str,
                        stored_hash: str) -> bool:
        """Verify password against bcrypt hash."""
        return bcrypt.checkpw(
            password.encode("utf-8"),
            stored_hash.encode("utf-8")
        )

    def needs_rehash(self, stored_hash: str) -> bool:
        """Check if hash needs rehashing with higher cost."""
        current_cost = bcrypt.gensalt(
            rounds=self.base_cost
        ).rounds
        stored_cost = int(stored_hash.split("$")[2])
        return stored_cost < current_cost

    def benchmark(self, iterations: int = 100) -> float:
        """Benchmark bcrypt speed."""
        start = time.time()
        for _ in range(iterations):
            self.hash_password("test_password_123")
        elapsed = time.time() - start
        return iterations / elapsed

# Cost factor comparison:
# cost=10: ~30,000 hashes/second (too fast for 2026)
# cost=12: ~8,000 hashes/second (minimum recommended)
# cost=14: ~500 hashes/second (good for 2026)
# cost=16: ~30 hashes/second (overkill for most systems)
```

### 3.2.2 scrypt

scrypt foi projetado para ser resistente a ataques com hardware dedicado (FPGA/ASIC) ao exigir grande quantidade de memória durante o cálculo.

**Parâmetros:**
- **N (CPU/memory cost)**: Parâmetro de custo principal. Deve ser potência de 2.
- **r (block size)**: Tamanho do bloco interno.
- **p (parallelization)**: Número de threads paralelas.
- **Memória total**: N * 128 * r bytes.

**Vantagens:**
- Alto custo de memória dificulta ataques com hardware dedicado
- Parâmetros granulares para ajuste fino
- Usado em criptomoedas (Bitcoin, Ethereum)

**Limitações:**
- Menos suportado que bcrypt
- Parâmetros mais complexos de configurar
- Pode ser problemático em sistemas com pouca memória

```python
import hashlib
import os
import time
import base64

class ScryptPasswordHasher:
    """scrypt password hashing with configurable parameters."""

    def __init__(self, n: int = 16384, r: int = 8, p: int = 1):
        """
        Initialize with scrypt parameters.

        N: CPU/memory cost (must be power of 2)
        r: Block size
        p: Parallelization factor

        Memory usage: N * 128 * r bytes
        Default: 16384 * 128 * 8 = 16 MB
        """
        self.n = n
        self.r = r
        self.p = p
        self.salt_len = 16
        self.key_len = 32

    def hash_password(self, password: str) -> str:
        """Hash password with scrypt."""
        salt = os.urandom(self.salt_len)
        dk = hashlib.scrypt(
            password.encode("utf-8"),
            salt=salt,
            n=self.n,
            r=self.r,
            p=self.p,
            dklen=self.key_len
        )

        # Format: scrypt:N:r:p:salt:hash
        salt_b64 = base64.b64encode(salt).decode()
        hash_b64 = base64.b64encode(dk).decode()
        return f"scrypt:{self.n}:{self.r}:{self.p}:{salt_b64}:{hash_b64}"

    def verify_password(self, password: str,
                        stored_hash: str) -> bool:
        """Verify password against scrypt hash."""
        parts = stored_hash.split(":")
        if len(parts) != 6 or parts[0] != "scrypt":
            return False

        n, r, p = int(parts[1]), int(parts[2]), int(parts[3])
        salt = base64.b64decode(parts[4])
        expected_hash = base64.b64decode(parts[5])

        dk = hashlib.scrypt(
            password.encode("utf-8"),
            salt=salt,
            n=n, r=r, p=p,
            dklen=len(expected_hash)
        )

        # Constant-time comparison
        return hashlib.compare_digest(dk, expected_hash)

    def memory_usage_mb(self) -> float:
        """Calculate memory usage in MB."""
        return (self.n * 128 * self.r) / (1024 * 1024)

# Parameter comparison:
# N=16384, r=8: 16 MB memory, fast on modern hardware
# N=65536, r=8: 64 MB memory, good balance
# N=262144, r=8: 256 MB memory, strong but slow
# N=1048576, r=8: 1 GB memory, very strong, very slow
```

### 3.2.3 Argon2id: O Padrão Atual

Argon2id é o vencedor do Password Hashing Competition (2015) e é o algoritmo recomendado para hashing de senhas em 2026. Combina as melhores características de Argon2i (resistente a ataques de canal lateral) e Argon2d (resistente a ataques GPU/ASIC).

**Parâmetros:**
- **time_cost (t)**: Número de iterações. Mínimo: 2, recomendado: 3-5.
- **memory_cost (m)**: Quantidade de memória em KB. Mínimo: 65536 (64MB), recomendado: 256MB+.
- **parallelism (p)**: Número de threads paralelas. Recomendado: 4.

**Por que Argon2id é superior:**

| Caracteristica | bcrypt | scrypt | Argon2id |
|---------------|--------|--------|----------|
| Resistencia GPU | Media | Alta | Muito Alta |
| Resistencia ASIC | Media | Alta | Muito Alta |
| Resistencia canal lateral | N/A | Baixa | Alta |
| Memoria ajustavel | Nao (4KB fixo) | Sim | Sim |
| CPU ajustavel | Sim | Sim | Sim |
| Paralelismo | Nao | Sim | Sim |
| Padrao NIST | Nao | Nao | Sim (recomendado) |
| Recomendacao OWASP | Sim | Sim | SIM (preferido) |

```python
import argon2
from argon2 import PasswordHasher
from argon2.exceptions import (
    VerifyMismatchError,
    InvalidHashError,
    VerificationError,
)
import time

class Argon2idPasswordHasher:
    """Argon2id password hashing following OWASP guidelines."""

    # OWASP 2024 recommended parameters
    TIME_COST = 3           # 3 iterations
    MEMORY_COST = 256000    # 256 MB
    PARALLELISM = 4         # 4 threads
    HASH_LEN = 32           # 32 bytes output
    SALT_LEN = 16           # 16 bytes salt

    def __init__(self, time_cost: int = TIME_COST,
                 memory_cost: int = MEMORY_COST,
                 parallelism: int = PARALLELISM):
        self.hasher = PasswordHasher(
            time_cost=time_cost,
            memory_cost=memory_cost,
            parallelism=parallelism,
            hash_len=self.HASH_LEN,
            salt_len=self.SALT_LEN,
        )
        self.time_cost = time_cost
        self.memory_cost = memory_cost
        self.parallelism = parallelism

    def hash_password(self, password: str) -> str:
        """Hash password with Argon2id."""
        return self.hasher.hash(password)

    def verify_password(self, password: str,
                        stored_hash: str) -> bool:
        """Verify password against Argon2id hash."""
        try:
            return self.hasher.verify(stored_hash, password)
        except VerifyMismatchError:
            return False
        except InvalidHashError:
            return False

    def needs_rehash(self, stored_hash: str) -> bool:
        """Check if hash needs rehashing with new parameters."""
        try:
            return self.hasher.check_needs_rehash(stored_hash)
        except Exception:
            return True

    def rehash_if_needed(self, password: str,
                         stored_hash: str) -> str:
        """Rehash if parameters have changed."""
        if self.needs_rehash(stored_hash):
            if self.verify_password(password, stored_hash):
                return self.hash_password(password)
        return stored_hash

    def benchmark(self, iterations: int = 5) -> float:
        """Benchmark Argon2id speed (this is intentionally slow)."""
        start = time.time()
        for _ in range(iterations):
            self.hash_password("test_password_123!")
        elapsed = time.time() - start
        return elapsed / iterations

    def memory_usage_mb(self) -> float:
        """Calculate memory usage in MB."""
        return self.memory_cost / 1024

# Example usage and benchmarking:
hasher = Argon2idPasswordHasher()
hash_time = hasher.benchmark()
memory = hasher.memory_usage_mb()
print(f"Time per hash: {hash_time:.2f}s")
print(f"Memory per hash: {memory:.0f} MB")
print(f"Hashes per second: {1/hash_time:.2f}")
print(f"Memory per 1000 concurrent users: {memory * 1000:.0f} MB")
```

### 3.2.4 Tabela Comparativa Final

| Algoritmo | Ano | Velocidade (CPU) | Velocidade (GPU) | Memoria | Tamanho Hash | Recomendacao |
|-----------|-----|------------------|------------------|---------|-------------|-------------|
| MD5 | 1991 | 50M/s | 50B/s | 0 | 16 bytes | NUNCA usar |
| SHA-1 | 1995 | 40M/s | 10B/s | 0 | 20 bytes | NUNCA usar |
| SHA-256 | 2001 | 25M/s | 10B/s | 0 | 32 bytes | NUNCA usar |
| bcrypt | 1999 | 30K/s | 300K/s | 4KB | 60 bytes | Aceitavel |
| scrypt | 2009 | 20K/s | 100K/s | 16MB+ | 64+ bytes | Bom |
| Argon2id | 2015 | 50/s | 200/s | 256MB | 128 bytes | MELHOR |

---

## 3.3 Geração e Armazenamento de Salt

### 3.3.1 O que é Salt?

Salt é um valor aleatório único adicionado à senha antes do hashing. Cada senha armazenada deve ter um salt diferente, mesmo que duas pessoas usem a mesma senha.

**Por que salt é essencial:**

Sem salt, um atacante pode criar rainbow tables — tabelas pré-computadas de hashes para senhas comuns. Com salt, cada senha requer uma rainbow table separada, tornando o ataque impraticável.

```
┌──────────────────────────────────────────────────────────────────────┐
│                    EFEITO DO SALT                                      │
│                                                                      │
│  SEM SALT:                                                           │
│  ├── "password123" → hash = a1b2c3d4...                              │
│  ├── "password123" → hash = a1b2c3d4...  (MESMO HASH!)              │
│  └── Rainbow table funciona para TODOS os usuarios                   │
│                                                                      │
│  COM SALT:                                                           │
│  ├── "password123" + salt_abc → hash = x1y2z3...                    │
│  ├── "password123" + salt_def → hash = m4n5o6...  (HASH DIFERENTE!) │
│  └── Rainbow table precisa ser recriada para CADA salt               │
│                                                                      │
│  Custo do ataque:                                                    │
│  ├── Sem salt: 1 tabela vale para todos                              │
│  ├── Com salt: 1 tabela por usuario (milhoes de tabelas)            │
│  └── Com salt + pepper: rainbow tables impossiveis                   │
└──────────────────────────────────────────────────────────────────────┘
```

### 3.3.2 Geração Segura de Salt

```python
import os
import secrets
import hashlib

class SaltGenerator:
    """Cryptographically secure salt generation."""

    MIN_SALT_BYTES = 16  # 128 bits minimum
    RECOMMENDED_SALT_BYTES = 32  # 256 bits recommended

    @staticmethod
    def generate(length: int = None) -> bytes:
        """Generate a cryptographically secure salt."""
        if length is None:
            length = SaltGenerator.RECOMMENDED_SALT_BYTES

        if length < SaltGenerator.MIN_SALT_BYTES:
            raise ValueError(
                f"Salt must be at least {SaltGenerator.MIN_SALT_BYTES} bytes"
            )

        # Use CSPRNG
        return secrets.token_bytes(length)

    @staticmethod
    def validate_salt(salt: bytes) -> bool:
        """Validate that a salt meets security requirements."""
        if not isinstance(salt, bytes):
            return False
        if len(salt) < SaltGenerator.MIN_SALT_BYTES:
            return False
        # Check not all zeros (shouldn't happen with CSPRNG, but verify)
        if all(b == 0 for b in salt):
            return False
        return True

    @staticmethod
    def salt_to_hex(salt: bytes) -> str:
        """Convert salt to hex string for storage."""
        return salt.hex()

    @staticmethod
    def hex_to_salt(hex_str: str) -> bytes:
        """Convert hex string back to salt."""
        return bytes.fromhex(hex_str)


class SaltedPasswordHasher:
    """Password hasher with explicit salt management."""

    def __init__(self):
        self.salt_gen = SaltGenerator()
        self.hasher = argon2.PasswordHasher()

    def hash_password(self, password: str) -> dict:
        """Hash password with explicit salt."""
        salt = self.salt_gen.generate()
        salt_hex = self.salt_gen.salt_to_hex(salt)

        # Combine password and salt before hashing
        salted_password = password.encode() + salt

        # Use Argon2id for the actual hashing
        password_hash = self.hasher.hash(
            salted_password.decode("latin-1")
        )

        return {
            "hash": password_hash,
            "salt": salt_hex,
            "algorithm": "argon2id",
        }

    def verify_password(self, password: str,
                        stored: dict) -> bool:
        """Verify password against salted hash."""
        salt = self.salt_gen.hex_to_salt(stored["salt"])
        salted_password = password.encode() + salt

        try:
            return self.hasher.verify(
                stored["hash"],
                salted_password.decode("latin-1")
            )
        except Exception:
            return False
```

### 3.3.3 Onde Armazenar o Salt

A maioria dos algoritmos modernos (Argon2, bcrypt) incorpora o salt no hash resultante. Isso significa que o salt é armazenado junto com o hash, mas de forma segura:

```
Exemplo de hash Argon2id armazenado:
$argon2id$v=19$m=256000,t=3,p=4$c2FsdF92YWx1ZQ$hash_value

Onde:
- $argon2id$v=19$ → algoritmo e versao
- m=256000,t=3,p=4 → parametros (memoria, tempo, paralelismo)
- c2FsdF92YWx1ZQ → salt (em base64)
- hash_value → o hash resultante
```

Isso é seguro porque:
1. O salt é único por usuário
2. O hash não pode ser revertido para obter a senha
3. Mesmo que o atacante veja o salt, ele precisa calcular o hash para cada tentativa

---

## 3.4 Peppering

### 3.4.1 O que é Pepper?

Pepper é um segredo adicional adicionado à senha antes do hashing, semelhante a um salt, mas com uma diferença crucial: o pepper é **o mesmo para todos os usuários** e é **armazenado fora do banco de dados** (tipicamente em um HSM, vault, ou variável de ambiente segura).

```
┌──────────────────────────────────────────────────────────────────────┐
│                    SALT vs PEPPER                                      │
│                                                                      │
│  SALT:                                                               │
│  ├── Unico por usuario                                               │
│  ├── Armazenado NO banco de dados (junto ao hash)                    │
│  ├── Protege contra rainbow tables                                    │
│  └── Se o banco for comprometido, salt tambem                       │
│                                                                      │
│  PEPPER:                                                             │
│  ├── Compartilhado entre todos os usuarios                           │
│  ├── Armazenado FORA do banco de dados (HSM, vault, env var)        │
│  ├── Protege contra ataque offline apos vazamento                    │
│  └── Se o banco for comprometido, pepper continua protegendo        │
│                                                                      │
│  COMBINACAO:                                                         │
│  hash = Argon2id(pepper + salt + password)                           │
│  └── Protecao em duas camadas: salt + pepper                         │
└──────────────────────────────────────────────────────────────────────┘
```

### 3.4.2 Implementação com Pepper

```python
import os
import json
import hashlib
import argon2
from typing import Optional

class PepperService:
    """Manage pepper for password hashing."""

    def __init__(self, pepper_source: str = "env"):
        """
        Initialize pepper from secure source.

        pepper_source:
            "env" - Read from PEPPER_SECRET environment variable
            "hsm" - Read from Hardware Security Module
            "vault" - Read from HashiCorp Vault
            "file" - Read from encrypted file
        """
        self.pepper = self._load_pepper(pepper_source)
        self.hasher = argon2.PasswordHasher(
            time_cost=3,
            memory_cost=256000,
            parallelism=4,
        )

    def _load_pepper(self, source: str) -> bytes:
        """Load pepper from secure source."""
        if source == "env":
            pepper_hex = os.environ.get("PEPPER_SECRET")
            if not pepper_hex:
                raise ValueError("PEPPER_SECRET not set")
            return bytes.fromhex(pepper_hex)
        elif source == "hsm":
            # In production, use HSM library
            raise NotImplementedError("HSM integration")
        elif source == "vault":
            # In production, use Vault API
            raise NotImplementedError("Vault integration")
        else:
            raise ValueError(f"Unknown pepper source: {source}")

    def hash_password(self, password: str, salt: bytes) -> str:
        """Hash password with pepper and salt."""
        # Combine: pepper + salt + password
        combined = self.pepper + salt + password.encode("utf-8")
        return self.hasher.hash(combined.decode("latin-1"))

    def verify_password(self, password: str, salt: bytes,
                        stored_hash: str) -> bool:
        """Verify password with pepper."""
        combined = self.pepper + salt + password.encode("utf-8")
        try:
            return self.hasher.verify(
                stored_hash, combined.decode("latin-1")
            )
        except Exception:
            return False

    @staticmethod
    def generate_pepper() -> str:
        """Generate a new pepper (store securely!)."""
        return secrets.token_hex(32)


class PepperedPasswordManager:
    """Complete password management with pepper and salt."""

    def __init__(self, pepper_service: PepperService):
        self.pepper = pepper_service
        self.salt_gen = SaltGenerator()

    def create_password(self, password: str) -> dict:
        """Create a new peppered and salted password hash."""
        salt = self.salt_gen.generate()
        peppered_hash = self.pepper.hash_password(password, salt)

        return {
            "hash": peppered_hash,
            "salt": self.salt_gen.salt_to_hex(salt),
            "algorithm": "argon2id-peppered",
            "version": 1,
        }

    def verify_password(self, password: str,
                        stored: dict) -> bool:
        """Verify a password against stored peppered hash."""
        salt = self.salt_gen.hex_to_salt(stored["salt"])
        return self.pepper.verify_password(
            password, salt, stored["hash"]
        )

    def migrate_to_new_pepper(self, password: str,
                               stored: dict,
                               new_pepper: PepperService) -> dict:
        """Migrate to new pepper (requires knowing old password)."""
        # First verify with old pepper
        salt = self.salt_gen.hex_to_salt(stored["salt"])
        if not self.pepper.verify_password(
            password, salt, stored["hash"]
        ):
            raise ValueError("Password verification failed")

        # Re-hash with new pepper
        new_salt = self.salt_gen.generate()
        new_hash = new_pepper.hash_password(password, new_salt)

        return {
            "hash": new_hash,
            "salt": self.salt_gen.salt_to_hex(new_salt),
            "algorithm": "argon2id-peppered",
            "version": 2,
        }
```

### 3.4.3 Gerenciamento Seguro de Pepper

```python
import os
import json
from pathlib import Path

class PepperVault:
    """Secure pepper storage and rotation."""

    def __init__(self, vault_path: str = None):
        if vault_path is None:
            vault_path = os.environ.get(
                "PEPPER_VAULT_PATH",
                "/etc/devsecurity/pepper.vault"
            )
        self.vault_path = Path(vault_path)
        self._peppers = self._load_vault()

    def _load_vault(self) -> dict:
        """Load pepper vault from encrypted file."""
        if not self.vault_path.exists():
            return self._create_vault()

        # In production, this file would be encrypted
        # with a key from HSM or KMS
        with open(self.vault_path, "r") as f:
            return json.load(f)

    def _create_vault(self) -> dict:
        """Create new pepper vault."""
        vault = {
            "current_pepper": secrets.token_hex(32),
            "previous_pepper": None,
            "created_at": time.time(),
            "last_rotated": time.time(),
            "rotation_count": 0,
        }
        self._save_vault(vault)
        return vault

    def _save_vault(self, vault: dict):
        """Save vault to encrypted file."""
        self.vault_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.vault_path, "w") as f:
            json.dump(vault, f, indent=2)
        # Restrict permissions
        os.chmod(self.vault_path, 0o600)

    def get_current_pepper(self) -> str:
        """Get current pepper."""
        return self._peppers["current_pepper"]

    def rotate_pepper(self) -> str:
        """Rotate pepper: current becomes previous, new pepper generated."""
        new_pepper = secrets.token_hex(32)

        self._peppers["previous_pepper"] = (
            self._peppers["current_pepper"]
        )
        self._peppers["current_pepper"] = new_pepper
        self._peppers["last_rotated"] = time.time()
        self._peppers["rotation_count"] += 1

        self._save_vault(self._peppers)
        return new_pepper

    def can_verify_with_previous(self) -> bool:
        """Check if previous pepper is available for migration."""
        return self._peppers.get("previous_pepper") is not None
```

---

## 3.5 Políticas de Senha Baseadas em Evidências

### 3.5.1 NIST SP 800-63B: As Novas Regras

O NIST SP 800-63B (Digital Identity Guidelines) revolucionou as recomendações de senhas ao basear suas diretrizes em evidências científicas, não em intuições de segurança.

**Mudanças fundamentais:**

| Regra Antiga (Errada) | Regra Nova (NIST) | Por que mudou |
|----------------------|-------------------|---------------|
| Minimo 8 caracteres com maiuscula, numero, especial | Minimo 8 caracteres, aceitar todos | Complexidade arbitraria leva a senhas fracas |
| Trocar senha a cada 90 dias | Nao trocar periodicamente | Troca forcada leva a padroes previsiveis |
| Perguntas secretas | Nao usar perguntas secretas | Respostas sao adivinhaveis ou publicas |
| Bloquear apos 3 tentativas | ate 100 tentativas por hora | Bloqueio cedo favorece DoS |
| Gerenciador de senhas proibido | Gerenciador de senhas recomendado | Senhas unicas sao mais seguras |

**Resumo das diretrizes NIST:**

```
┌──────────────────────────────────────────────────────────────────────┐
│              NIST SP 800-63B - RESUMO DAS DIRETRIZES                  │
│                                                                      │
│  OBRIGATORIO:                                                        │
│  ├── Comprimento minimo: 8 caracteres                                │
│  ├── Comprimento maximo: 64+ caracteres                              │
│  ├── Aceitar TODOS os caracteres imprimiveis incluindo espacos       │
│  ├── Verificar contra listas de senhas vazadas (HIBP, etc.)          │
│  ├── Bloquear senhas que contem nome de usuario ou e-mail            │
│  ├── Suportar colar/colar e paste de senhas                          │
│  ├── Suportar gerenciadores de senhas                                │
│  ├── Armazenar senhas com hashing forte (Argon2id, bcrypt)           │
│  └── Notificar usuarios sobre tentativas de login falhas             │
│                                                                      │
│  PROIBIDO:                                                           │
│  ├── Nao forcar troca periodica de senha                             │
│  ├── Nao exigir reutilizacao de senhas                               │
│  ├── Nao exigir complexidade arbitraria (maiuscula+numero+especial)  │
│  ├── Nao usar perguntas de seguranca como autenticacao               │
│  ├── Nao usar dicas de senha                                         │
│  └── Nao limitar excessivamente tentativas de login (max 100/hora)   │
│                                                                      │
│  RECOMENDADO:                                                        │
│  ├── Comprimento minimo de 15 caracteres para contas privilegiadas   │
│  ├── MFA para contas de alto risco                                   │
│  ├── Notificacoes de login suspeito                                  │
│  └── Verificacao contra bases de vazamentos conhecidos               │
└──────────────────────────────────────────────────────────────────────┘
```

### 3.5.2 Implementação de Política NIST

```python
import re
import hashlib
import time
from typing import Tuple, List, Optional

class NISTPasswordPolicy:
    """Password policy following NIST SP 800-63B."""

    MIN_LENGTH = 8
    MAX_LENGTH = 64
    PRIVILEGED_MIN_LENGTH = 15
    MAX_FAILED_ATTEMPTS = 100  # per hour
    LOCKOUT_DURATION = 3600    # 1 hour

    # Common passwords from NIST reference data
    COMMON_PASSWORDS_URL = "https://api.pwnedpasswords.com/range/"

    def __init__(self, hibp_enabled: bool = True):
        self.hibp_enabled = hibp_enabled

    def validate(
        self,
        password: str,
        context: Optional[dict] = None
    ) -> Tuple[bool, List[str]]:
        """
        Validate password against NIST guidelines.

        context: dict with optional keys:
            - email: user's email address
            - username: user's username
            - privileged: bool, if account has elevated access
        """
        if context is None:
            context = {}

        violations = []
        is_privileged = context.get("privileged", False)

        # Length check
        min_length = (
            self.PRIVILEGED_MIN_LENGTH if is_privileged
            else self.MIN_LENGTH
        )
        if len(password) < min_length:
            violations.append(
                f"Senha deve ter no minimo {min_length} caracteres"
            )

        if len(password) > self.MAX_LENGTH:
            violations.append(
                f"Senha deve ter no maximo {self.MAX_LENGTH} caracteres"
            )

        # Check against breached passwords
        if self.hibp_enabled and self._is_breached(password):
            violations.append(
                "Esta senha foi encontrada em vazamentos de dados"
            )

        # Check if contains user context
        email = context.get("email", "")
        username = context.get("username", "")
        if email:
            email_local = email.split("@")[0].lower()
            if email_local in password.lower():
                violations.append(
                    "Senha nao deve conter partes do seu e-mail"
                )
        if username and username.lower() in password.lower():
            violations.append(
                "Senha nao deve conter seu nome de usuario"
            )

        # Check for repeated characters
        if re.search(r'(.)\1{3,}', password):
            violations.append(
                "Senha nao deve conter 4+ caracteres repetidos"
            )

        return (len(violations) == 0, violations)

    def _is_breached(self, password: str) -> bool:
        """Check password against HIBP API using k-anonymity."""
        import requests

        sha1 = hashlib.sha1(
            password.encode("utf-8")
        ).hexdigest().upper()
        prefix, suffix = sha1[:5], sha1[5:]

        try:
            response = requests.get(
                self.COMMON_PASSWORDS_URL + prefix,
                timeout=5,
                headers={"Add-Padding": "true"}
            )
            if response.status_code == 200:
                for line in response.text.splitlines():
                    hash_suffix, count = line.split(":")
                    if hash_suffix == suffix:
                        return int(count) > 0
        except requests.RequestException:
            pass

        return False


class PasswordPolicyEnforcer:
    """Enforce password policy throughout the password lifecycle."""

    def __init__(self, policy: NISTPasswordPolicy,
                 user_store, audit_log):
        self.policy = policy
        self.user_store = user_store
        self.audit = audit_log

    def validate_new_password(self, user_id: str,
                              new_password: str) -> dict:
        """Validate new password for creation or change."""
        user = self.user_store.get(user_id)
        if not user:
            return {"valid": False, "errors": ["Usuario nao encontrado"]}

        context = {
            "email": user.get("email", ""),
            "username": user.get("username", ""),
            "privileged": user.get("privileged", False),
        }

        is_valid, violations = self.policy.validate(
            new_password, context
        )

        if is_valid:
            self.audit.log("password_validation_passed", {
                "user_id": user_id,
            })
        else:
            self.audit.log("password_validation_failed", {
                "user_id": user_id,
                "violations": violations,
            })

        return {
            "valid": is_valid,
            "errors": violations,
        }

    def should_force_change(self, user_id: str) -> dict:
        """Determine if user should be prompted to change password."""
        user = self.user_store.get(user_id)
        if not user:
            return {"force": False}

        # Only force change if evidence of compromise
        reasons = []

        if user.get("password_in_breach"):
            reasons.append("Senha encontrada em vazamento de dados")

        if user.get("login_from_suspicious_ip"):
            reasons.append("Login detectado a partir de IP suspeito")

        if user.get("credential_stuffing_detected"):
            reasons.append(
                "Tentativa de credential stuffing detectada"
            )

        return {
            "force": len(reasons) > 0,
            "reasons": reasons,
        }
```

---

## 3.6 Verificação Contra Databases de Vazamentos

### 3.6.1 Have I Been Pwned (HIBP)

O HIBP é o serviço mais usado para verificar se senhas foram comprometidas em vazamentos conhecidos. Usa k-anonymity para verificar senhas sem revelá-las ao servidor.

**Como funciona o k-anonymity:**

```
┌──────────────────────────────────────────────────────────────────────┐
│              HIBP K-ANONYMITY                                        │
│                                                                      │
│  1. Senha: "MinhaSenh@123"                                          │
│  2. SHA-1: "8B6E11F0A1B2C3D4E5F6A7B8C9D0E1F2A3B4C5D6"             │
│  3. Prefixo (5 chars): "8B6E1"                                       │
│  4. Sufixo (35 chars): "1F0A1B2C3D4E5F6A7B8C9D0E1F2A3B4C5D6"      │
│                                                                      │
│  Cliente envia APENAS o prefixo ao servidor:                         │
│  GET /range/8B6E1                                                     │
│                                                                      │
│  Servidor retorna TODOS os sufixos que comecam com "8B6E1":         │
│  1F0A1B2C3D4E5F6A7B8C9D0E1F2A3B4C5D6:1234                          │
│  2A3B4C5D6E7F8A9B0C1D2E3F4A5B6C7D8E9:5678                          │
│  ...                                                                 │
│                                                                      │
│  Cliente verifica localmente se o seu sufixo esta na lista           │
│                                                                      │
│  SEGURANCA:                                                          │
│  ├── Servidor NUNCA vê a senha completa                              │
│  ├── Prefixo de 5 chars e inofensivo (1M de combinações)            │
│  └── Sufixo so e verificado no dispositivo do cliente                │
└──────────────────────────────────────────────────────────────────────┘
```

### 3.6.2 Implementação HIBP

```python
import hashlib
import requests
from typing import Optional

class HIBPChecker:
    """Check passwords against Have I Been Pwned API."""

    API_BASE = "https://api.pwnedpasswords.com/range/"
    TIMEOUT = 5

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key
        self.session = requests.Session()
        if api_key:
            self.session.headers["hibp-api-key"] = api_key

    def check_password(self, password: str) -> dict:
        """
        Check if password has been breached.

        Uses k-anonymity: sends only SHA-1 prefix to API.
        """
        sha1 = hashlib.sha1(
            password.encode("utf-8")
        ).hexdigest().upper()
        prefix = sha1[:5]
        suffix = sha1[5:]

        try:
            response = self.session.get(
                self.API_BASE + prefix,
                timeout=self.TIMEOUT,
                headers={
                    "Add-Padding": "true",
                    "User-Agent": "DevSecurity-PasswordCheck/1.0",
                }
            )

            if response.status_code == 200:
                for line in response.text.splitlines():
                    hash_suffix, count = line.split(":")
                    if hash_suffix == suffix:
                        breach_count = int(count.strip())
                        return {
                            "breached": breach_count > 0,
                            "count": breach_count,
                            "message": (
                                f"Senha encontrada em {breach_count:,} "
                                f"vazamentos"
                                if breach_count > 0
                                else "Senha nao encontrada em vazamentos"
                            ),
                        }
                return {
                    "breached": False,
                    "count": 0,
                    "message": "Senha nao encontrada em vazamentos",
                }
            elif response.status_code == 404:
                return {
                    "breached": False,
                    "count": 0,
                    "message": "Senha segura",
                }
            elif response.status_code == 401:
                return {
                    "breached": False,
                    "count": 0,
                    "error": "API key invalida",
                }
            else:
                return {
                    "breached": False,
                    "count": 0,
                    "error": f"API error: {response.status_code}",
                }
        except requests.RequestException as e:
            return {
                "breached": False,
                "count": 0,
                "error": f"Erro de conexao: {str(e)}",
            }

    def check_username(self, email: str) -> dict:
        """Check if email has been in any data breach."""
        try:
            response = self.session.get(
                f"https://haveibeenpwned.com/api/v3/breachedaccount/{email}",
                timeout=self.TIMEOUT,
                params={"truncateResponse": "false"},
            )
            if response.status_code == 200:
                breaches = response.json()
                return {
                    "breached": True,
                    "count": len(breaches),
                    "breaches": [
                        {
                            "name": b.get("Name"),
                            "date": b.get("BreachDate"),
                            "data_classes": b.get("DataClasses"),
                        }
                        for b in breaches
                    ],
                }
            elif response.status_code == 404:
                return {"breached": False, "count": 0}
            else:
                return {
                    "breached": False,
                    "error": f"API error: {response.status_code}",
                }
        except requests.RequestException as e:
            return {"breached": False, "error": str(e)}


class BreachAwarePasswordValidator:
    """Password validator with breach checking integration."""

    def __init__(self, hibp_checker: HIBPChecker,
                 audit_log):
        self.hibp = hibp_checker
        self.audit = audit_log
        self.local_breach_cache = {}  # Cache to reduce API calls

    def validate(self, password: str,
                 user_context: dict = None) -> dict:
        """Full validation including breach check."""
        results = {
            "valid": True,
            "warnings": [],
            "errors": [],
        }

        # Check length
        min_length = 15 if user_context.get("privileged") else 8
        if len(password) < min_length:
            results["errors"].append(
                f"Minimo {min_length} caracteres"
            )
            results["valid"] = False

        # Check against common passwords
        if self._is_common(password):
            results["errors"].append("Senha e muito comum")
            results["valid"] = False

        # Check against HIBP (with caching)
        cache_key = hashlib.sha256(
            password.encode()
        ).hexdigest()
        if cache_key in self.local_breach_cache:
            breach_info = self.local_breach_cache[cache_key]
        else:
            breach_info = self.hibp.check_password(password)
            self.local_breach_cache[cache_key] = breach_info

        if breach_info.get("breached"):
            results["errors"].append(
                f"Senha encontrada em {breach_info['count']:,} "
                f"vazamentos de dados"
            )
            results["valid"] = False
            self.audit.log("breached_password_attempt", {
                "user_id": user_context.get("user_id"),
                "breach_count": breach_info["count"],
            })

        return results

    def _is_common(self, password: str) -> bool:
        """Check against list of common passwords."""
        common = {
            "password", "123456", "12345678", "qwerty",
            "abc123", "monkey", "master", "dragon",
            "login", "princess", "football", "shadow",
            "sunshine", "trustno1", "iloveyou", "batman",
            "access", "hello", "charlie", "letmein",
            "welcome", "password1", "password123",
            "admin", "passw0rd", "p@ssword", "p@ssw0rd",
        }
        return password.lower() in common
```

---

## 3.7 Rate Limiting para Login

### 3.7.1 Por Que Rate Limiting é Essencial

Sem rate limiting, um atacante pode:
- Testar milhões de senhas por segundo (força bruta)
- Usar listas de credenciais vazadas (credential stuffing)
- Causar negação de serviço (DoS) contra contas específicas
- Sobrecarregar o sistema com tentativas inválidas

```python
import time
import hashlib
from collections import defaultdict
from dataclasses import dataclass
from typing import Optional

@dataclass
class RateLimitConfig:
    """Rate limit configuration."""
    max_attempts: int = 5
    window_seconds: int = 300  # 5 minutes
    lockout_seconds: int = 1800  # 30 minutes
    progressive_delay: bool = True
    ip_based_limit: int = 20  # Max attempts per IP
    account_based_limit: int = 5  # Max attempts per account

class RateLimiter:
    """In-memory rate limiter for login attempts."""

    def __init__(self, config: RateLimitConfig = None):
        self.config = config or RateLimitConfig()
        self.attempts = defaultdict(list)  # key -> [timestamps]
        self.lockouts = {}  # key -> lockout_until

    def _get_key(self, identifier: str,
                 key_type: str) -> str:
        """Generate rate limit key."""
        return f"{key_type}:{identifier}"

    def check_rate_limit(self, identifier: str,
                         key_type: str = "account") -> dict:
        """Check if identifier is rate limited."""
        key = self._get_key(identifier, key_type)
        now = time.time()

        # Check lockout
        if key in self.lockouts:
            if now < self.lockouts[key]:
                remaining = int(self.lockouts[key] - now)
                return {
                    "allowed": False,
                    "locked": True,
                    "remaining_seconds": remaining,
                    "message": f"Conta bloqueada por {remaining} segundos",
                }
            else:
                del self.lockouts[key]

        # Get recent attempts
        max_limit = (
            self.config.ip_based_limit
            if key_type == "ip"
            else self.config.account_based_limit
        )

        # Clean old attempts
        cutoff = now - self.config.window_seconds
        self.attempts[key] = [
            t for t in self.attempts[key] if t > cutoff
        ]

        # Check count
        if len(self.attempts[key]) >= max_limit:
            # Apply lockout
            lockout_until = now + self.config.lockout_seconds
            self.lockouts[key] = lockout_until
            return {
                "allowed": False,
                "locked": True,
                "remaining_seconds": self.config.lockout_seconds,
                "message": "Limite de tentativas excedido",
            }

        return {
            "allowed": True,
            "remaining": max_limit - len(self.attempts[key]),
            "window_remaining": int(
                self.config.window_seconds - (now - min(self.attempts[key], default=now))
            ),
        }

    def record_attempt(self, identifier: str,
                       key_type: str = "account"):
        """Record a login attempt."""
        key = self._get_key(identifier, key_type)
        self.attempts[key].append(time.time())

    def calculate_delay(self, identifier: str,
                        key_type: str = "account") -> int:
        """Calculate progressive delay for next attempt."""
        if not self.config.progressive_delay:
            return 0

        key = self._get_key(identifier, key_type)
        now = time.time()
        cutoff = now - self.config.window_seconds
        recent = [t for t in self.attempts[key] if t > cutoff]
        count = len(recent)

        # Exponential backoff: 0, 1, 2, 4, 8, 16, 32 seconds
        if count <= 1:
            return 0
        return min(2 ** (count - 2), 32)

    def reset(self, identifier: str,
              key_type: str = "account"):
        """Reset rate limit for identifier (e.g., after successful login)."""
        key = self._get_key(identifier, key_type)
        self.attempts[key] = []
        if key in self.lockouts:
            del self.lockouts[key]


class LoginRateLimiter:
    """Login-specific rate limiting with dual key tracking."""

    def __init__(self, config: RateLimitConfig = None):
        self.config = config or RateLimitConfig()
        self.account_limiter = RateLimiter(self.config)
        self.ip_limiter = RateLimiter(self.config)

    def check_login_allowed(self, email: str,
                           ip_address: str) -> dict:
        """Check if login attempt is allowed."""
        # Check account-level limit
        account_check = self.account_limiter.check_rate_limit(
            email, "account"
        )
        if not account_check["allowed"]:
            return account_check

        # Check IP-level limit
        ip_check = self.ip_limiter.check_rate_limit(
            ip_address, "ip"
        )
        if not ip_check["allowed"]:
            return ip_check

        # Calculate progressive delay
        delay = max(
            self.account_limiter.calculate_delay(email, "account"),
            self.ip_limiter.calculate_delay(ip_address, "ip"),
        )

        return {
            "allowed": True,
            "delay": delay,
            "remaining_attempts": min(
                account_check.get("remaining", 5),
                ip_check.get("remaining", 20),
            ),
        }

    def record_login_attempt(self, email: str,
                            ip_address: str):
        """Record a login attempt."""
        self.account_limiter.record_attempt(email, "account")
        self.ip_limiter.record_attempt(ip_address, "ip")

    def on_successful_login(self, email: str,
                           ip_address: str):
        """Reset counters on successful login."""
        self.account_limiter.reset(email, "account")
        # Don't reset IP - protect against account enumeration
```

---

## 3.8 Estratégias de Bloqueio de Conta

### 3.8.1 Tipos de Bloqueio

| Tipo | Descricao | Quando Usar |
|------|-----------|-------------|
| Progressivo | Delay crescente entre tentativas | Padrao para todos os usuarios |
| Temporario | Bloqueio por tempo determinado | Apos N tentativas falhas |
| por Investigacao | Bloqueio ate revisao manual | Atividade suspeita confirmada |
| Permanente | Conta encerrada | Virolacao grave de termos |

### 3.8.2 Implementação Completa

```python
import time
from enum import Enum
from typing import Optional, List

class LockoutReason(Enum):
    FAILED_ATTEMPTS = "failed_attempts"
    SUSPICIOUS_ACTIVITY = "suspicious_activity"
    ADMIN_ACTION = "admin_action"
    BREACH_DETECTED = "breach_detected"

class AccountLockoutManager:
    """Complete account lockout management."""

    def __init__(self, user_store, notification_service,
                 audit_log):
        self.user_store = user_store
        self.notifications = notification_service
        self.audit = audit_log

        # Configuration
        self.FAILED_ATTEMPTS_THRESHOLD = 5
        self.LOCKOUT_DURATIONS = {
            1: 300,      # 5 minutes after 1st lockout
            2: 1800,     # 30 minutes after 2nd lockout
            3: 3600,     # 1 hour after 3rd lockout
            4: 86400,    # 24 hours after 4th lockout
        }
        self.PROGRESSIVE_DELAYS = [0, 5, 30, 300, 1800]

    def record_failed_attempt(self, email: str,
                             ip_address: str) -> dict:
        """Record failed login and apply lockout if needed."""
        user = self.user_store.get_by_email(email)
        if not user:
            # Simulate constant-time response (prevent enumeration)
            time.sleep(0.05)
            return {"locked": False, "attempts_remaining": 5}

        failed_count = user.get("failed_attempts", 0) + 1
        lockout_count = user.get("lockout_count", 0)

        # Calculate progressive delay
        delay_index = min(
            failed_count - 1,
            len(self.PROGRESSIVE_DELAYS) - 1
        )
        delay = self.PROGRESSIVE_DELAYS[delay_index]

        # Update user
        self.user_store.update(user["id"], {
            "failed_attempts": failed_count,
            "last_failed_attempt": time.time(),
        })

        # Check if should lock out
        if failed_count >= self.FAILED_ATTEMPTS_THRESHOLD:
            lockout_duration = self.LOCKOUT_DURATIONS.get(
                min(lockout_count + 1, 4),
                86400
            )
            lockout_until = time.time() + lockout_duration

            self.user_store.update(user["id"], {
                "locked_until": lockout_until,
                "failed_attempts": 0,
                "lockout_count": lockout_count + 1,
                "last_lockout_reason": LockoutReason.FAILED_ATTEMPTS.value,
            })

            # Notify user
            self.notifications.send_lockout_email(
                email,
                lockout_duration=lockout_duration,
                ip_address=ip_address,
            )

            self.audit.log("account_locked", {
                "user_id": user["id"],
                "reason": "failed_attempts",
                "lockout_duration": lockout_duration,
                "ip": ip_address,
            })

            return {
                "locked": True,
                "lockout_seconds": lockout_duration,
                "message": "Conta bloqueada devido a multiplas tentativas",
            }

        return {
            "locked": False,
            "attempts_remaining": (
                self.FAILED_ATTEMPTS_THRESHOLD - failed_count
            ),
            "delay_seconds": delay,
        }

    def check_lockout(self, email: str) -> dict:
        """Check if account is currently locked."""
        user = self.user_store.get_by_email(email)
        if not user:
            return {"locked": False}

        locked_until = user.get("locked_until")
        if locked_until and locked_until > time.time():
            remaining = int(locked_until - time.time())
            return {
                "locked": True,
                "remaining_seconds": remaining,
                "reason": user.get("last_lockout_reason"),
            }

        # Auto-unlock if lockout period passed
        if locked_until:
            self.user_store.update(user["id"], {
                "locked_until": None,
                "failed_attempts": 0,
            })

        return {"locked": False}

    def manual_unlock(self, email: str, admin_id: str,
                     reason: str) -> dict:
        """Admin unlock a locked account."""
        user = self.user_store.get_by_email(email)
        if not user:
            return {"success": False, "error": "User not found"}

        self.user_store.update(user["id"], {
            "locked_until": None,
            "failed_attempts": 0,
        })

        self.audit.log("manual_unlock", {
            "user_id": user["id"],
            "admin_id": admin_id,
            "reason": reason,
        })

        self.notifications.send_unlock_notification(email)

        return {"success": True, "message": "Conta desbloqueada"}

    def on_successful_login(self, email: str):
        """Reset lockout state on successful login."""
        user = self.user_store.get_by_email(email)
        if user:
            self.user_store.update(user["id"], {
                "failed_attempts": 0,
                "locked_until": None,
            })
```

---

## 3.9 Segurança do Fluxo de Recuperação de Senha

### 3.9.1 Fluxo Seguro

O fluxo de recuperação de senha é frequentemente o elo mais fraco na cadeia de autenticação. Um atacante que compromete o fluxo de recuperação pode assumir o controle de qualquer conta.

```
┌──────────────────────────────────────────────────────────────────────┐
│              FLUXO SEGURO DE RECUPERACAO DE SENHA                      │
│                                                                      │
│  1. Usuario solicita recuperacao                                     │
│  │   POST /password-reset-request { email }                          │
│  │                                                                   │
│  2. Sistema verifica se email existe (MENSAGEM GENERICA!)            │
│  │                                                                   │
│  3. Gera token aleatorio (32+ bytes)                                 │
│  │                                                                   │
│  4. Armazena hash do token (nao o token em si)                       │
│  │                                                                   │
│  5. Envia email com link contendo token                              │
│  │                                                                   │
│  6. Link expira em 15 minutos (curto!)                               │
│  │                                                                   │
│  7. Token e de uso UNICO (invalidado apos uso)                       │
│  │                                                                   │
│  8. Sistema exige nova senha forte                                   │
│  │                                                                   │
│  9. TODAS as sessoes do usuario sao invalidadas                      │
│  │                                                                   │
│  10. Usuario recebe notificacao de alteracao                         │
│                                                                      │
│  SEGURANCA:                                                          │
│  ├── Token nao revela o email (previne enumeracao)                   │
│  ├── Token e hash-armazenado (previne vazamento)                     │
│  ├── Expiracao curta (minimiza janela de ataque)                     │
│  ├── Uso unico (previne replay)                                      │
│  ├── Invalidacao de sessoes (previne sequestro)                      │
│  └── Notificacao ao usuario (detecta ataques)                        │
└──────────────────────────────────────────────────────────────────────┘
```

### 3.9.2 Implementação Segura

```python
import secrets
import hashlib
import time
from typing import Optional

class SecurePasswordReset:
    """Secure password reset flow implementation."""

    TOKEN_LENGTH = 32
    TOKEN_TTL = 900  # 15 minutes
    MAX_RESETS_PER_HOUR = 3

    def __init__(self, user_store, email_service,
                 session_store, audit_log):
        self.user_store = user_store
        self.email = email_service
        self.sessions = session_store
        self.audit = audit_log
        self.tokens = {}  # token_hash -> metadata

    def request_reset(self, email: str,
                     ip_address: str) -> dict:
        """Initiate password reset process."""
        # Rate limiting
        recent_resets = self._count_recent_resets(email)
        if recent_resets >= self.MAX_RESETS_PER_HOUR:
            self.audit.log("reset_rate_limited", {
                "email": email,
                "ip": ip_address,
                "recent_resets": recent_resets,
            })
            # Still return success to prevent enumeration
            return {
                "success": True,
                "message": "Se o email existir, voce recebera um link",
            }

        # Find user (silently ignore if not found)
        user = self.user_store.get_by_email(email)
        if not user:
            # Constant-time response
            time.sleep(0.05)
            return {
                "success": True,
                "message": "Se o email existir, voce recebera um link",
            }

        # Generate secure token
        token = secrets.token_urlsafe(self.TOKEN_LENGTH)
        token_hash = hashlib.sha256(token.encode()).hexdigest()

        # Store token metadata (NOT the token itself)
        self.tokens[token_hash] = {
            "user_id": user["id"],
            "email": email,
            "created_at": time.time(),
            "used": False,
            "ip_address": ip_address,
        }

        # Send reset email
        reset_link = (
            f"https://devsecurity.com/reset-password"
            f"?token={token}"
        )
        self.email.send(
            to=email,
            subject="Recuperacao de Senha - DevSecurity",
            body=(
                f"Voce solicitou a recuperacao de senha.\n\n"
                f"Link: {reset_link}\n\n"
                f"Este link expira em 15 minutos.\n"
                f"Se voce nao solicitou, ignore este email."
            ),
        )

        self.audit.log("reset_requested", {
            "user_id": user["id"],
            "ip": ip_address,
        })

        return {
            "success": True,
            "message": "Se o email existir, voce recebera um link",
        }

    def complete_reset(self, token: str,
                       new_password: str,
                       ip_address: str) -> dict:
        """Complete password reset with new password."""
        token_hash = hashlib.sha256(token.encode()).hexdigest()

        # Find token metadata
        token_data = self.tokens.get(token_hash)
        if not token_data:
            return {
                "success": False,
                "error": "Link invalido ou expirado",
            }

        # Check expiration
        if time.time() - token_data["created_at"] > self.TOKEN_TTL:
            del self.tokens[token_hash]
            return {
                "success": False,
                "error": "Link expirado. Solicite uma nova recuperacao.",
            }

        # Check if already used
        if token_data["used"]:
            self.audit.log("reset_token_reuse", {
                "user_id": token_data["user_id"],
                "ip": ip_address,
            })
            return {
                "success": False,
                "error": "Link ja utilizado. Solicite uma nova recuperacao.",
            }

        # Validate new password
        user = self.user_store.get(token_data["user_id"])
        if not user:
            return {
                "success": False,
                "error": "Erro interno",
            }

        policy = NISTPasswordPolicy()
        context = {
            "email": user.get("email", ""),
            "username": user.get("username", ""),
            "privileged": user.get("privileged", False),
        }
        is_valid, violations = policy.validate(new_password, context)

        if not is_valid:
            return {
                "success": False,
                "errors": violations,
            }

        # Update password
        self.user_store.update_password(
            token_data["user_id"],
            new_password
        )

        # Mark token as used
        token_data["used"] = True

        # Invalidate ALL sessions for this user
        self.sessions.delete_all_for_user(token_data["user_id"])

        # Send notification
        self.email.send(
            to=token_data["email"],
            subject="Senha alterada - DevSecurity",
            body=(
                "Sua senha foi alterada com sucesso.\n\n"
                "Se voce nao realizou esta alteracao, "
                "entre em contato com o suporte imediatamente."
            ),
        )

        self.audit.log("password_reset_completed", {
            "user_id": token_data["user_id"],
            "ip": ip_address,
        })

        return {
            "success": True,
            "message": "Senha alterada com sucesso",
        }

    def _count_recent_resets(self, email: str) -> int:
        """Count reset requests in the last hour."""
        cutoff = time.time() - 3600
        count = 0
        for token_data in self.tokens.values():
            if (token_data["email"] == email and
                token_data["created_at"] > cutoff):
                count += 1
        return count

    def cleanup_expired_tokens(self):
        """Remove expired reset tokens."""
        now = time.time()
        expired = [
            k for k, v in self.tokens.items()
            if now - v["created_at"] > self.TOKEN_TTL
        ]
        for k in expired:
            del self.tokens[k]
```

---

## 3.10 Rotação de Senhas e Gerenciamento de Ciclo de Vida

### 3.10.1 Quando Rotacionar Senhas

Conforme o NIST SP 800-63B, **não se deve forçar troca periódica de senhas**. A rotação deve ocorrer apenas quando houver evidência de comprometimento:

| Cenário | Acao | Obrigatorio? |
|---------|------|-------------|
| Vazamento de dados confirmado | Forcar troca para todos afetados | Sim |
| Credenciais encontradas no HIBP | Forcar troca para o usuario | Sim |
| Login suspeito detectado | Notificar e oferecer troca | Recomendado |
| MFA ativado pela primeira vez | Nao forcar troca | N/A |
| Periodo de 90 dias | Nao forcar troca | Nao (NIST) |
| Funcionario desligado | Invalidar todas as credenciais | Obrigatorio |

### 3.10.2 Verificação Automática de Vazamentos

```python
import time
import hashlib

class BreachMonitor:
    """Automatic breach monitoring for stored passwords."""

    def __init__(self, hibp_checker, user_store,
                 notification_service, audit_log):
        self.hibp = hibp_checker
        self.user_store = user_store
        self.notifications = notification_service
        self.audit = audit_log
        self.CHECK_INTERVAL = 86400  # Daily

    def check_all_users(self) -> dict:
        """Check all users against breach database."""
        results = {
            "checked": 0,
            "breached": 0,
            "notified": 0,
            "errors": 0,
        }

        users = self.user_store.get_all_active()
        for user in users:
            results["checked"] += 1
            try:
                email = user["email"]
                breach_result = self.hibp.check_username(email)

                if breach_result.get("breached"):
                    results["breached"] += 1
                    self._handle_breach(user, breach_result)
                    results["notified"] += 1
            except Exception as e:
                results["errors"] += 1
                self.audit.log("breach_check_error", {
                    "user_id": user["id"],
                    "error": str(e),
                })

        self.audit.log("breach_check_completed", results)
        return results

    def _handle_breach(self, user: dict,
                       breach_result: dict):
        """Handle detected breach."""
        # Mark user as potentially compromised
        self.user_store.update(user["id"], {
            "password_in_breach": True,
            "breach_detected_at": time.time(),
        })

        # Send urgent notification
        self.notifications.send_breach_notification(
            user["email"],
            breaches=breach_result.get("breaches", []),
        )

        # Force password change on next login
        self.user_store.update(user["id"], {
            "force_password_change": True,
        })

        self.audit.log("breach_detected", {
            "user_id": user["id"],
            "breach_count": breach_result.get("count", 0),
        })
```

---

## 3.11 Caso Misantropi4: Senhas Vazadas e Por Que Rotação Importa

### 3.11.1 Análise das Credenciais Comprometidas

O ataque Misantropi4 ao IDAP foi possível porque múltiplas falhas no gerenciamento de senhas se combinaram:

```
┌──────────────────────────────────────────────────────────────────────┐
│              ANALISE: FALHAS DE SENHA NO IDAP                         │
│                                                                      │
│  FALHA 1: Credenciais Reutilizadas                                   │
│  ├── Funcionarios usavam a mesma senha em multiplos sistemas         │
│  ├── Senha vazada em servidor publico diferente                      │
│  └── Mesma senha funcionou no IDAP                                   │
│                                                                      │
│  FALHA 2: Senhas Nunca Rotacionadas                                  │
│  ├── Credenciais tinham anos sem alteracao                           │
│  ├── Nenhuma politica de rotacao baseada em evidencia                │
│  └── Senhas comprometidas permaneceram validas por anos              │
│                                                                      │
│  FALHA 3: Sem Verificacao contra Vazamentos                          │
│  ├── Sistema nao verificava senhas contra HIBP                       │
│  ├── Funcionarios nao tinham orientacao                              │
│  └── Senhas fracas e vazadas nao eram detectadas                     │
│                                                                      │
│  FALHA 4: Hashing Inadequado (presumido)                             │
│  ├── Sistema legado possivelmente usava MD5 ou SHA-1                 │
│  ├── Senhas vazadas eram rapidamente crackeaveis                     │
│  └── Senhas fracas foram recuperadas em minutos                      │
│                                                                      │
│  FALHA 5: Sem Bloqueio por Forca Bruta                               │
│  ├── Atacante testou centenas de credenciais                         │
│  ├── Nenhum bloqueio ou delay progressivo                            │
│  └── Todas as credenciais vazadas funcionaram                        │
│                                                                      │
│  RESULTADO:                                                          │
│  ├── Atacante obteve acesso com credenciais validas                  │
│  ├── MFA ausente = acesso completo                                   │
│  └── Alertas falsos enviados para milhares de cidadaos               │
└──────────────────────────────────────────────────────────────────────┘
```

### 3.11.2 Por Que Rotação de Senhas Teria Prevenido o Ataque

**Cenário com rotação de senhas:**

Se o IDAP tivesse uma política de rotação baseada em evidências (não periódica, mas reativa), o ataque teria sido prevenido ou mitigado:

1. **Verificação automática contra HIBP**: Quando as credenciais foram vazadas em outro servidor, o sistema teria detectado e forçado a troca.

2. **Detecção de credential stuffing**: O padrão de tentativas de login (múltiplas contas, mesmo IP) teria acionado alertas e bloqueios.

3. **Rotação reativa**: Se o IDAP tivesse detectado o vazamento no servidor fonte, poderia ter forçado a troca de senhas antes do ataque.

4. **Re-hashing periódico**: Mesmo sem rotação forçada, o sistema poderia ter verificado periodicamente se as senhas armazenadas ainda eram seguras (usando HIBP localmente).

### 3.11.3 Recomendações Concretas

Para evitar repetição do caso Misantropi4, qualquer sistema governamental ou de alto impacto deve implementar:

| Medida | Descricao | Prioridade |
|--------|-----------|-----------|
| HIBP integration | Verificar senhas contra vazamentos conhecidos | Critica |
| Re-hashing | Migrar senhas antigas para Argon2id | Alta |
| Bloqueio progressivo | Delay e lockout apos tentativas falhas | Critica |
| Notificacoes | Alertar usuarios sobre logins suspeitos | Alta |
| Forcar troca reativa | Quando evidencia de comprometimento | Critica |
| Re-hashing automatico | Verificar e atualizar hashes periodicamente | Media |
| Auditoria | Log completo de tentativas de login | Critica |
| MFA obrigatorio | Para todos os operadores | Critica |

---

## 3.12 Resumo e Próximos Passos

Neste capítulo, mergulhamos profundamente na segurança de senhas:

- **Armazenamento**: Nunca usar MD5, SHA-1 ou SHA-256 para senhas. Argon2id é o padrão atual, seguido por bcrypt e scrypt.
- **Salt**: Valor aleatório único por usuário, incorporado no hash. Previne rainbow tables.
- **Pepper**: Segredo compartilhado armazenado fora do banco de dados. Previne ataques offline.
- **Políticas NIST**: Comprimento mínimo 8 caracteres, sem complexidade arbitrária, sem troca forçada periódica, verificação contra vazamentos.
- **HIBP**: Verificação contra databases de vazamentos usando k-anonymity. Essencial para prevenir uso de credenciais comprometidas.
- **Rate limiting**: Controle de tentativas de login por conta e por IP. Previne força bruta e DoS.
- **Bloqueio de conta**: Estratégias progressivas com delay crescente e notificações ao usuário.
- **Recuperação de senha**: Fluxo seguro com tokens de uso único, expiração curta, e invalidação de sessões.
- **Caso Misantropi4**: Demonstrou como a ausência de todas essas práticas resultou em um ataque devastador.

No próximo capítulo, exploraremos **OAuth 2.0** — o framework de autorização que permite a terceiros acessar recursos em nome do usuário, com segurança e granularidade.

---

## 3.13 Exercícios

1. **Benchmarking**: Implemente e compare o tempo de execução de Argon2id, bcrypt e scrypt com diferentes parâmetros em sua máquina.
2. **HIBP Integration**: Implemente a verificação de senhas contra o HIBP API e teste com senhas conhecidas como comprometidas.
3. **Rate Limiter**: Implemente um rate limiter completo que suporte contas e IPs, com delay progressivo e bloqueio temporário.
4. **Password Reset**: Implemente o fluxo completo de recuperação de senha seguindo todas as práticas de segurança descritas.
5. **Caso Misantropi4**: Escreva um plano de remediação detalhado para o IDAP, incluindo prazos, responsáveis e métricas de sucesso.

---

## 3.14 Migração de Algoritmos de Hashing

### 3.14.1 Por Que Migrar?

Migrar de um algoritmo de hashing inadequado para outro melhor é uma operação comum em sistemas legados. Muitos sistemas ainda usam MD5 ou SHA-1 devido a decisões antigas, e a migração deve ser feita sem interromper o serviço.

```
┌──────────────────────────────────────────────────────────────────────┐
│              ESTRATEGIA DE MIGRACAO DE HASHING                        │
│                                                                      │
│  Migracao Transparente (Rehash on Login):                            │
│  ├── Usuario faz login com senha antiga                              │
│  ├── Sistema verifica com algoritmo antigo                           │
│  ├── Se valido, re-hash com novo algoritmo                           │
│  ├── Atualiza hash no banco de dados                                 │
│  └── Proximo login usa novo algoritmo                                │
│                                                                      │
│  Vantagens:                                                          │
│  ├── Zero downtime                                                   │
│  ├── Sem forcar troca de senha                                       │
│  ├── Migra gradualmente (usuarios ativos primeiro)                   │
│  └── Rollback facil (manter algoritmo antigo como fallback)          │
│                                                                      │
│  Desvantagens:                                                       │
│  ├── Usuarios inativos nunca migram                                  │
│  └── Senhas fracas continuam validas ate login                       │
│                                                                      │
│  Migracao Forcada:                                                   │
│  ├── Sistema envia email pedindo nova senha                          │
│  ├── Conta bloqueada ate nova senha ser definida                     │
│  └── Garante migracao completa                                       │
│                                                                      │
│  Migracao em Background:                                             │
│  ├── Job roda periodicamente re-hashing senhas                       │
│  ├── Verifica contra banco de dados por lotes                        │
│  └── Garante migracao completa sem acao do usuario                   │
└──────────────────────────────────────────────────────────────────────┘
```

### 3.14.2 Implementação de Migração Transparente

```python
import time
import hashlib
from typing import Optional, Tuple

class PasswordHashingMigrator:
    """Migrate passwords between hashing algorithms transparently."""

    def __init__(self, old_hasher, new_hasher, user_store):
        self.old = old_hasher
        self.new = new_hasher
        self.users = user_store

    def verify_and_migrate(self, email: str,
                          password: str) -> dict:
        """
        Verify password with old algorithm, migrate to new if valid.

        This is called during login:
        1. Try to verify with old algorithm
        2. If valid, re-hash with new algorithm
        3. Update database
        """
        user = self.users.get_by_email(email)
        if not user:
            return {"authenticated": False, "error": "User not found"}

        stored_hash = user.get("password_hash")
        algorithm = user.get("hash_algorithm", "unknown")

        # Check which algorithm was used
        if self._is_old_algorithm(stored_hash, algorithm):
            # Verify with old algorithm
            if self.old.verify(stored_hash, password):
                # Re-hash with new algorithm
                new_hash = self.new.hash_password(password)

                # Update database
                self.users.update(user["id"], {
                    "password_hash": new_hash,
                    "hash_algorithm": "argon2id",
                    "migrated_at": time.time(),
                })

                return {
                    "authenticated": True,
                    "migrated": True,
                    "user_id": user["id"],
                }
            else:
                return {"authenticated": False, "error": "Invalid password"}

        elif self._is_new_algorithm(stored_hash):
            # Already using new algorithm
            if self.new.verify_password(password, stored_hash):
                return {"authenticated": True, "migrated": False, "user_id": user["id"]}
            else:
                return {"authenticated": False, "error": "Invalid password"}

        else:
            return {"authenticated": False, "error": "Unknown hash algorithm"}

    def _is_old_algorithm(self, hash_value: str,
                         algorithm: str) -> bool:
        """Check if hash uses old algorithm."""
        old_indicators = ["md5", "sha1", "sha256", "des"]
        if algorithm.lower() in old_indicators:
            return True
        # Check hash format
        if hash_value.startswith("$2b$") or hash_value.startswith("$2a$"):
            return False  # bcrypt
        if hash_value.startswith("$argon2"):
            return False  # Argon2
        if len(hash_value) == 32:  # MD5 hex
            return True
        if len(hash_value) == 40:  # SHA1 hex
            return True
        if len(hash_value) == 64:  # SHA256 hex
            return True
        return False

    def _is_new_algorithm(self, hash_value: str) -> bool:
        """Check if hash uses new algorithm."""
        return (hash_value.startswith("$argon2") or
                hash_value.startswith("$2b$") or
                hash_value.startswith("$2a$"))

    def batch_migrate(self, batch_size: int = 1000,
                     max_batches: int = 100) -> dict:
        """
        Background migration for inactive users.

        Process users who haven't logged in since migration started.
        """
        migrated = 0
        errors = 0
        processed = 0

        for batch_num in range(max_batches):
            # Get users with old hashing
            users = self.users.get_unmigrated(batch_size)
            if not users:
                break

            for user in users:
                processed += 1
                try:
                    # We can't re-hash without the password
                    # So we mark for migration on next login
                    self.users.update(user["id"], {
                        "needs_password_change": True,
                        "migration_reason": "Algorithm upgrade required",
                    })
                    migrated += 1
                except Exception as e:
                    errors += 1

        return {
            "processed": processed,
            "marked_for_migration": migrated,
            "errors": errors,
        }
```

### 3.14.3 Tabela de Migração

| Algoritmo Atual | Algoritmo Destino | Dificuldade | Tempo Estimado |
|----------------|------------------|-------------|----------------|
| MD5 | Argon2id | Facil (rehash no login) | Gradual |
| SHA-1 | Argon2id | Facil (rehash no login) | Gradual |
| SHA-256 | Argon2id | Facil (rehash no login) | Gradual |
| bcrypt (cost=10) | Argon2id | Facil (rehash no login) | Gradual |
| bcrypt (cost=12) | Argon2id | Media (manter bcrypt) | Opcional |
| scrypt | Argon2id | Media (manter scrypt) | Opcional |
| 3DES/ECB (Adobe) | Argon2id | Dificil (descriptografar) | Urgente |

---

## 3.15 Senhas em Sistemas Legados

### 3.15.1 Desafios de Sistemas Legados

Sistemas legados frequentemente apresentam desafios únicos para segurança de senhas:

```python
class LegacySystemPasswordHandler:
    """Handle passwords from legacy systems with weak hashing."""

    def __init__(self, legacy_db, modern_hasher):
        self.legacy = legacy_db
        self.modern = modern_hasher

    def authenticate_legacy_user(self, email: str,
                                password: str) -> dict:
        """Authenticate user from legacy system."""
        # Get legacy user record
        legacy_user = self.legacy.get_user(email)
        if not legacy_user:
            return {"authenticated": False}

        stored_hash = legacy_user["password"]
        algorithm = legacy_user.get("hash_type", "md5")

        # Verify based on algorithm
        if algorithm == "md5":
            computed = hashlib.md5(password.encode()).hexdigest()
            valid = (computed == stored_hash)
        elif algorithm == "sha1":
            computed = hashlib.sha1(password.encode()).hexdigest()
            valid = (computed == stored_hash)
        elif algorithm == "sha256":
            computed = hashlib.sha256(password.encode()).hexdigest()
            valid = (computed == stored_hash)
        elif algorithm == "plaintext":
            # Yes, some systems still store plaintext
            valid = (password == stored_hash)
            if valid:
                # URGENT: Migrate immediately
                self._emergency_migrate(email, password)
        else:
            return {"authenticated": False, "error": "Unknown algorithm"}

        if valid:
            # Migrate to modern hashing on successful login
            new_hash = self.modern.hash_password(password)
            self.legacy.update_password(email, new_hash, "argon2id")
            return {"authenticated": True, "migrated": True}

        return {"authenticated": False}

    def _emergency_migrate(self, email: str, password: str):
        """Immediately hash plaintext password."""
        new_hash = self.modern.hash_password(password)
        self.legacy.update_password(email, new_hash, "argon2id")

    def audit_legacy_systems(self) -> dict:
        """Audit all legacy passwords for security issues."""
        results = {
            "total_users": 0,
            "plaintext": 0,
            "md5": 0,
            "sha1": 0,
            "sha256": 0,
            "modern": 0,
            "weak_passwords": 0,
        }

        for user in self.legacy.get_all_users():
            results["total_users"] += 1
            algo = user.get("hash_type", "unknown")

            if algo == "plaintext":
                results["plaintext"] += 1
            elif algo == "md5":
                results["md5"] += 1
            elif algo == "sha1":
                results["sha1"] += 1
            elif algo == "sha256":
                results["sha256"] += 1
            elif algo in ["argon2id", "bcrypt"]:
                results["modern"] += 1

            # Check for weak passwords (if we can test)
            if self._is_weak_password(user):
                results["weak_passwords"] += 1

        return results

    def _is_weak_password(self, user: dict) -> bool:
        """Check if password hash corresponds to weak password."""
        # This is a simplified check
        # In production, use HIBP or known weak password database
        return False
```

---

## 3.16 Segurança de Senhas em Ambientes Distribuídos

### 3.16.1 Desafios de Sincronização

Em sistemas distribuídos, a verificação de senha deve ser consistente entre múltiplos servidores:

```python
class DistributedPasswordService:
    """Password verification in distributed systems."""

    def __init__(self, primary_store, replica_store,
                 cache_store):
        self.primary = primary_store
        self.replicas = replica_store
        self.cache = cache_store
        self.hasher = Argon2idPasswordHasher()

    def verify_password(self, email: str,
                       password: str) -> dict:
        """
        Verify password with read-through cache.

        Strategy:
        1. Check local cache (fast path)
        2. Check primary database
        3. Check replicas (if primary unavailable)
        4. Update cache on success
        """
        # Try cache first
        cached = self.cache.get(f"pwd:{email}")
        if cached:
            if self.hasher.verify_password(password, cached["hash"]):
                return {"authenticated": True, "source": "cache"}

        # Try primary database
        try:
            user = self.primary.get_by_email(email)
            if user and self.hasher.verify_password(
                password, user["password_hash"]
            ):
                # Update cache
                self.cache.set(
                    f"pwd:{email}",
                    {"hash": user["password_hash"]},
                    ttl=3600,
                )
                return {"authenticated": True, "source": "primary"}
        except Exception:
            pass

        # Try replicas
        for replica in self.replicas:
            try:
                user = replica.get_by_email(email)
                if user and self.hasher.verify_password(
                    password, user["password_hash"]
                ):
                    return {"authenticated": True, "source": "replica"}
            except Exception:
                continue

        return {"authenticated": False}

    def update_password(self, email: str,
                       new_password: str) -> dict:
        """Update password across all stores."""
        new_hash = self.hasher.hash_password(new_password)

        # Update primary
        self.primary.update_password(email, new_hash)

        # Propagate to replicas
        for replica in self.replicas:
            try:
                replica.update_password(email, new_hash)
            except Exception:
                # Log but don't fail - async replication
                pass

        # Invalidate cache
        self.cache.delete(f"pwd:{email}")

        return {"success": True}
```

---

## 3.17 Métricas e Monitoramento de Segurança de Senhas

### 3.17.1 Métricas Essenciais

```python
class PasswordSecurityMetrics:
    """Track password security metrics."""

    def __init__(self, user_store, audit_log):
        self.users = user_store
        self.audit = audit_log

    def calculate_metrics(self) -> dict:
        """Calculate comprehensive password security metrics."""
        all_users = self.users.get_all_active()

        metrics = {
            "total_active_users": len(all_users),
            "password_age": {
                "never_changed": 0,
                "changed_last_30_days": 0,
                "changed_last_90_days": 0,
                "changed_last_year": 0,
                "older_than_year": 0,
            },
            "hash_algorithm": {
                "argon2id": 0,
                "bcrypt": 0,
                "scrypt": 0,
                "sha256": 0,
                "md5": 0,
                "unknown": 0,
            },
            "mfa_status": {
                "enabled": 0,
                "disabled": 0,
                "pending": 0,
            },
            "breach_status": {
                "clean": 0,
                "breached": 0,
                "unknown": 0,
            },
            "account_status": {
                "active": 0,
                "locked": 0,
                "disabled": 0,
            },
        }

        now = time.time()

        for user in all_users:
            # Password age
            last_changed = user.get("password_changed_at", 0)
            if last_changed == 0:
                metrics["password_age"]["never_changed"] += 1
            elif now - last_changed < 30 * 86400:
                metrics["password_age"]["changed_last_30_days"] += 1
            elif now - last_changed < 90 * 86400:
                metrics["password_age"]["changed_last_90_days"] += 1
            elif now - last_changed < 365 * 86400:
                metrics["password_age"]["changed_last_year"] += 1
            else:
                metrics["password_age"]["older_than_year"] += 1

            # Hash algorithm
            algo = user.get("hash_algorithm", "unknown")
            if algo in metrics["hash_algorithm"]:
                metrics["hash_algorithm"][algo] += 1
            else:
                metrics["hash_algorithm"]["unknown"] += 1

            # MFA status
            mfa = user.get("mfa_enabled", False)
            if mfa:
                metrics["mfa_status"]["enabled"] += 1
            else:
                metrics["mfa_status"]["disabled"] += 1

            # Breach status
            breached = user.get("password_in_breach", False)
            if breached:
                metrics["breach_status"]["breached"] += 1
            else:
                metrics["breach_status"]["clean"] += 1

            # Account status
            status = user.get("status", "active")
            if status in metrics["account_status"]:
                metrics["account_status"][status] += 1

        # Calculate security scores
        metrics["security_score"] = self._calculate_score(metrics)

        return metrics

    def _calculate_score(self, metrics: dict) -> dict:
        """Calculate security score from metrics."""
        total = metrics["total_active_users"]
        if total == 0:
            return {"overall": 100, "details": {}}

        # Modern hashing score (0-25)
        modern = (metrics["hash_algorithm"]["argon2id"] +
                 metrics["hash_algorithm"]["bcrypt"] +
                 metrics["hash_algorithm"]["scrypt"])
        hashing_score = (modern / total) * 25

        # MFA adoption score (0-25)
        mfa_score = (metrics["mfa_status"]["enabled"] / total) * 25

        # Breach clean score (0-25)
        clean = metrics["breach_status"]["clean"]
        breach_score = (clean / total) * 25

        # Password freshness score (0-25)
        fresh = (metrics["password_age"]["changed_last_90_days"] +
                metrics["password_age"]["changed_last_30_days"])
        freshness_score = (fresh / total) * 25

        overall = hashing_score + mfa_score + breach_score + freshness_score

        return {
            "overall": round(overall, 1),
            "details": {
                "hashing": round(hashing_score, 1),
                "mfa": round(mfa_score, 1),
                "breach_free": round(breach_score, 1),
                "freshness": round(freshness_score, 1),
            },
            "rating": self._get_rating(overall),
        }

    def _get_rating(self, score: float) -> str:
        """Get rating from score."""
        if score >= 90:
            return "Excelente"
        elif score >= 75:
            return "Bom"
        elif score >= 50:
            return "Regular"
        elif score >= 25:
            return "Ruim"
        else:
            return "Critico"

    def generate_report(self) -> dict:
        """Generate comprehensive security report."""
        metrics = self.calculate_metrics()

        report = {
            "timestamp": time.time(),
            "metrics": metrics,
            "recommendations": [],
        }

        # Generate recommendations based on metrics
        if metrics["hash_algorithm"]["md5"] > 0:
            report["recommendations"].append({
                "priority": "alta",
                "action": "Migrar senhas MD5 para Argon2id",
                "affected": metrics["hash_algorithm"]["md5"],
                "impact": "Seguranca comprometida por algoritmo fraco",
            })

        if metrics["mfa_status"]["disabled"] > 0:
            pct = (metrics["mfa_status"]["disabled"] /
                  metrics["total_active_users"] * 100)
            report["recommendations"].append({
                "priority": "alta",
                "action": "Habilitar MFA para todos os usuarios",
                "affected": metrics["mfa_status"]["disabled"],
                "impact": f"{pct:.0f}% dos usuarios sem MFA",
            })

        if metrics["breach_status"]["breached"] > 0:
            report["recommendations"].append({
                "priority": "critica",
                "action": "Forcar troca de senha para usuarios comprometidos",
                "affected": metrics["breach_status"]["breached"],
                "impact": "Credenciais potencialmente vazadas",
            })

        return report
```

---

## 3.18 Referências Adicionais

1. NIST SP 800-63B - Digital Identity Guidelines
2. OWASP Password Storage Cheat Sheet
3. OWASP Authentication Cheat Sheet
4. RFC 9106 - Argon2 Memory-Hard Hash Function
5. Have I Been Pwned API Documentation
6. Password Hashing Competition (PHC) Results
7. Cyber Essentials - Password Guidance
8. ENISA - Password Management Guidelines
9. PCI DSS v4.0 - Requirement 8: Identify Users and Authenticate Access
10. CIS Controls v8 - Control 5: Account Management

---

## 3.19 Glossário

| Termo | Definicao |
|-------|-----------|
| Hash | Funcao unidirecional que transforma dados em valor fixo |
| Salt | Valor aleatorio unico adicionado ao hash |
| Pepper | Segredo compartilhado fora do banco de dados |
| Argon2id | Algoritmo de hashing de senhas vencedor do PHC |
| bcrypt | Algoritmo de hashing baseado em Blowfish |
| scrypt | Algoritmo de hashing resistente a hardware |
| HIBP | Have I Been Pwned - Database de vazamentos |
| k-anonymity | Tecnica que envia apenas prefixo do hash |
| PBKDF2 | Password-Based Key Derivation Function 2 |
| Work factor | Parametro que controla custo computacional |
| Rainbow table | Tabela pre-computada de hashes para ataque |
| Credential stuffing | Uso automatizado de credenciais vazadas |
| Brute force | Ataque de forca bruta por tentativa |
| Rate limiting | Controle de taxa de requisicoes |
| Account lockout | Bloqueio de conta apos tentativas falhas |
| NIST SP 800-63B | Padrao de diretrizes de identidade digital |

---

## 3.20 Casos de Estudo Adicionais

### 3.20.1 LastPass (2022)

Em agosto de 2022, a LastPass sofreu um ataque que comprometeu o vault de senhas de usuarios. Embora os vaults fossem criptografados, o atacante obteve copias dos dados criptografados.

**O que deu errado:**
- Chave de criptografia derivada de senha de usuario com work factor insuficiente
- Vault continha senhas em texto plano (apos descriptografia local)
- Metadados (URLs, nomes de servicos) nao eram criptografados

**Licao aprendida:** O work factor do KDF deve ser ajustado para proteger contra ataques offline. Se o atacante obtiver o vault criptografado, a derivacao da chave de criptografia deve ser intencionalmente lenta.

```python
class SecureVaultEncryption:
    """Example of proper vault encryption with strong KDF."""

    def __init__(self):
        self.KDF_TIME_COST = 4
        self.KDF_MEMORY_COST = 256000  # 256 MB
        self.KDF_PARALLELISM = 4

    def derive_vault_key(self, master_password: str,
                        salt: bytes) -> bytes:
        """Derive encryption key from master password."""
        import argon2

        # Use Argon2id with strong parameters
        dk = argon2.low_level.hash_secret_raw(
            secret=master_password.encode(),
            salt=salt,
            time_cost=self.KDF_TIME_COST,
            memory_cost=self.KDF_MEMORY_COST,
            parallelism=self.KDF_PARALLELISM,
            hash_len=32,
            type=argon2.low_level.Type.ID,
        )
        return dk

    def encrypt_vault(self, vault_data: dict,
                     master_password: str) -> dict:
        """Encrypt vault data with derived key."""
        import os
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM

        salt = os.urandom(16)
        key = self.derive_vault_key(master_password, salt)

        # Encrypt with AES-256-GCM
        nonce = os.urandom(12)
        aesgcm = AESGCM(key)

        import json
        plaintext = json.dumps(vault_data).encode()
        ciphertext = aesgcm.encrypt(nonce, plaintext, None)

        return {
            "salt": salt.hex(),
            "nonce": nonce.hex(),
            "ciphertext": ciphertext.hex(),
            "kdf_params": {
                "algorithm": "argon2id",
                "time_cost": self.KDF_TIME_COST,
                "memory_cost": self.KDF_MEMORY_COST,
                "parallelism": self.KDF_PARALLELISM,
            },
        }

    def decrypt_vault(self, encrypted_vault: dict,
                     master_password: str) -> dict:
        """Decrypt vault data."""
        import json
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM

        salt = bytes.fromhex(encrypted_vault["salt"])
        nonce = bytes.fromhex(encrypted_vault["nonce"])
        ciphertext = bytes.fromhex(encrypted_vault["ciphertext"])

        key = self.derive_vault_key(master_password, salt)

        aesgcm = AESGCM(key)
        plaintext = aesgcm.decrypt(nonce, ciphertext, None)

        return json.loads(plaintext.decode())
```

### 3.20.2 Colonial Pipeline (2021)

O Colonial Pipeline foi forçado a encerrar operações por dias devido a ransomware. A causa raiz foi credenciais comprometidas sem MFA na VPN corporativa.

**Relevancia para seguranca de senhas:**
- Credenciais vazadas de outro servico
- Senha reutilizada pelo funcionario
- VPN sem MFA permitiu acesso direto
- Credenciais nunca foram rotacionadas

### 3.20.3 Uber (2022)

Um atacante usou MFA fatigue attack para obter acesso a sistemas internos da Uber. O atacante environmentou multiples solicitacoes de push ate que um funcionario as aprovasse.

**Licao aprendida:** Push MFA deve incluir contexto (IP, localizacao, dispositivo) para que o usuario possa tomar decisoes informadas.

---

## 3.21 Melhores Praticas Resumidas

### 3.21.1 Checklist de Seguranca de Senhas

```
┌──────────────────────────────────────────────────────────────────────┐
│              CHECKLIST DE SEGURANCA DE SENHAS                         │
│                                                                      │
│  ARMAZENAMENTO:                                                      │
│  [X] Usar Argon2id (ou bcrypt/scrypt como alternativa)              │
│  [X] Parameters: time_cost >= 3, memory_cost >= 256MB               │
│  [X] Salt unico por senha (16+ bytes, CSPRNG)                       │
│  [X] Pepper armazenado fora do banco de dados                        │
│  [X] Hash em coluna dedicada (nao "password")                        │
│  [X] Nunca armazenar senha em texto plano                            │
│  [X] Nunca criptografar senha (usar hashing)                         │
│                                                                      │
│  POLITICA:                                                           │
│  [X] Comprimento minimo 8 caracteres (15+ para privilegiados)       │
│  [X] Aceitar todos os caracteres imprimiveis                         │
│  [X] Verificar contra HIBP ou similar                                │
│  [X] Nao forcar troca periodica                                      │
│  [X] Forcar troca quando evidencia de comprometimento               │
│  [X] Notificar usuarios sobre logins suspeitos                       │
│                                                                      │
│  CONTROLE DE ACESSO:                                                  │
│  [X] Rate limiting por conta (max 100 tentativas/hora)              │
│  [X] Rate limiting por IP                                            │
│  [X] Bloqueio progressivo apos 5 tentativas                          │
│  [X] Delay progressivo entre tentativas                              │
│  [X] Mensagens genericas de erro (nao revelar se usuario existe)    │
│                                                                      │
│  RECUPERACAO:                                                        │
│  [X] Tokens de uso unico                                            │
│  [X] Expiracao curta (15 minutos)                                    │
│  [X] Invalidacao de sessoes apos reset                               │
│  [X] Notificacao ao usuario                                          │
│  [X] Limite de solicitacoes por hora                                 │
│                                                                      │
│  MONITORAMENTO:                                                      │
│  [X] Logs de auditoria para todas as tentativas                      │
│  [X] Alertas para padroes anomalos                                   │
│  [X] Verificacao periodica contra HIBP                               │
│  [X] Metricas de seguranca (hashing score, MFA adoption)            │
└──────────────────────────────────────────────────────────────────────┘
```

### 3.21.2 Erros Fatais a Evitar

| Erro | Por que e fatal | Consequencia |
|------|----------------|-------------|
| MD5/SHA-256 para senhas | Rapido demais, sem salt | Atacante testa bilhoes de senhas/segundo |
| Senha em texto plano | Qualquer vazamento revela tudo | Contas comprometidas imediatamente |
| Sem MFA | Credenciais vazadas dao acesso completo | Ataque trivial com dados de vazamento |
| Troca periodica forcada | Usuarios criam padroes previsiveis | Senhas fracas sao continuamente reutilizadas |
| Perguntas secretas | Respostas adivinhaveis ou publicas | Contas recuperadas por atacantes |
| Sem rate limiting | Forca bruta ilimitada | Qualquer senha fraca e descoberta |
| Mensagens de erro especificas | Revelam se usuario existe | Enumeracao de usuarios facilitada |

---

## 3.22 Exercicios Adicionais

6. **KDF Benchmark**: Implemente um benchmark que meça o tempo de hashing de Argon2id com diferentes parâmetros (memory: 64MB, 128MB, 256MB, 512MB) e relate o tradeoff segurança/performance.

7. **Migration Script**: Implemente um script de migração que mova senhas de MD5 para Argon2id de forma transparente, incluindo logging e rollback.

8. **Vault Encryption**: Implemente um sistema de vault de senhas que use Argon2id para derivar a chave de criptografia e AES-256-GCM para criptografar os dados.

9. **Security Metrics**: Implemente o PasswordSecurityMetrics e gere um relatório para um banco de dados simulado com 1000 usuarios.

10. **Incident Response**: Escreva um plano de resposta a incidente para o cenário onde o banco de dados de senhas é comprometido. Inclua: detecção, contenção, erradicação, recuperação e lições aprendidas.

---

## 3.23 Resumo Final

A segurança de senhas é a camada mais fundamental de proteção de identidade. Neste capítulo, cobrimos:

- **Armazenamento**: Argon2id é o padrão atual, com bcrypt e scrypt como alternativas aceitáveis. MD5, SHA-1 e SHA-256 são inaceitáveis.
- **Salt e Pepper**: Salt é único por usuário e armazenado com o hash. Pepper é compartilhado e armazenado fora do banco de dados.
- **Políticas NIST**: Comprimento mínimo 8 caracteres, sem complexidade arbitrária, sem troca forçada periódica.
- **HIBP**: Verificação contra databases de vazamentos é essencial.
- **Rate limiting e bloqueio**: Previne força bruta e DoS.
- **Recuperação de senha**: Fluxo seguro com tokens de uso único e expiração curta.
- **Migração**: Sistemas legados devem ser migrados para algoritmos modernos de forma transparente.
- **Monitoramento**: Métricas e alertas permitem detectar problemas antes de se tornarem incidentes.
- **Caso Misantropi4**: Demonstra como a ausência de todas essas práticas resultou em um ataque devastador.

A segurança de senhas não é apenas uma questão técnica — é uma questão de confiança. Quando um usuário cria uma conta no seu sistema, ele confia que você protegerá suas credenciais. Essa confiança deve ser tratada com o máximo respeito e responsabilidade.

---

*[Próximo capítulo: 04 — OAuth 2.0](04-oauth2.md)*
