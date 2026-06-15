# Design: Book 5 — Cryptography Engineering in C++

**Change**: cryptography-engineering  
**Status**: Draft  
**Date**: 2026-06-15  
**Spec Reference**: `/home/Projetos/DevSecurity/openspec/changes/sdd/cryptography-engineering/spec.md`

---

## 1. Book Architecture

### 1.1 Chapter Dependency Graph

```
Ch00 (Prefácio)
  └── Ch01 (Introdução)
        ├── Ch02 (Constant-Time) → Ch03 (Side-Channel)
        │     └── Ch12 (Verificação Formal)
        │           └── Ch13 (Testes)
        ├── Ch04 (HSM/Tokens) → Ch09 (TPM/Enclaves)
        ├── Ch05 (TLS 1.3) → Ch06 (PQC)
        │     └── Ch08 (Modern Protocols)
        ├── Ch07 (Key Management)
        │     └── Ch14 (Compliance)
        ├── Ch10 (Homomorphic)
        ├── Ch11 (ZKP)
        └── Ch15 (Case Study) ← depends on Ch02, Ch04, Ch05, Ch07
              └── Ch16 (Best Practices)
                    └── Ch17 (Conclusion)
```

### 1.2 Reading Paths by Profile

| Profile | Recommended Path | Focus |
|---------|------------------|-------|
| **Security Engineer** | 00→01→02→03→04→05→06→07→15→16 | Side-channels, HSM, TLS, key management |
| **C++ Developer** | 00→01→02→05→08→10→11→13→17 | Constant-time, protocols, modern crypto |
| **DevSecOps** | 00→01→05→06→14→15→16 | TLS, PQC migration, compliance, deployment |
| **Cryptography Researcher** | 00→01→02→03→10→11→12→17 | Side-channels, HE, ZKP, formal verification |
| **Hardware Security** | 00→01→04→09→15→16 | HSM, TPM, enclaves, case study |
| **Full Coverage** | 00→01→...→17 (sequential) | All chapters |

### 1.3 Modular Design Principles

- **Independence**: Each chapter is self-contained after prerequisites
- **Progressive Complexity**: Concepts build on prior chapters
- **Cross-Reference Network**: Explicit `→ see Chapter X` links for related topics
- **Optional Deep Dives**: Advanced sections marked for specialized readers

---

## 2. Content Architecture

### 2.1 Chapter Template Structure

Every chapter follows this standardized structure:

```markdown
# Chapter NN — Title

## Learning Objectives
- 3-5 concrete, measurable objectives

## Section Outline
| Section | Content | Est. Lines |
|---------|---------|------------|
| NN.1 | Introduction/Motivation | 250-300 |
| NN.2-N-1 | Core Content Sections | 300-450 each |
| NN.N | CVEs/Case Studies | 300-400 |
| NN.N+1 | Exercises and References | 250-300 |

## Code Examples
- Categorized: Basic → Intermediate → Advanced
- Each with: context, implementation, compilation, expected output

## Exercises
- 3-5 exercises per chapter
- Difficulty: Basic (1-2), Intermediate (2-3), Advanced (1-2)

## Cross-References
- Related chapters with specific section links
- Related CVEs across chapters
```

### 2.2 Section Content Patterns

| Section Type | Purpose | Structure | Lines |
|--------------|---------|-----------|-------|
| **Introductory** | Set context, motivate | Problem → Why it matters → Preview | 250-300 |
| **Conceptual** | Explain theory | Definition → Properties → Examples → Trade-offs | 350-400 |
| **Implementation** | Show code | API → Pattern → Full example → Edge cases | 400-450 |
| **CVE Analysis** | Document vulnerability | Timeline → Root cause → Impact → Fix → Lessons | 300-400 |
| **Case Study** | Real-world application | Requirements → Architecture → Implementation → Results | 350-450 |
| **Reference** | Quick lookup | Tables, lists, code snippets | 250-300 |

### 2.3 Content Density Strategy

**Target: 2,800-3,900 lines per chapter**

| Component | Min Lines | Max Lines | Weight |
|-----------|-----------|-----------|--------|
| Prose (PT-BR) | 1,200 | 1,800 | 40-45% |
| Code examples (EN) | 800 | 1,200 | 25-30% |
| Tables/Diagrams | 200 | 400 | 10-15% |
| Exercises | 250 | 350 | 10-12% |
| CVE Analysis | 200 | 400 | 8-12% |

**Density Validation Formula**:
```
Total Lines = Prose + Code + Tables + Exercises + CVE Analysis
Target Range: 2,800 ≤ Total ≤ 3,900
```

### 2.4 Prose Style Guidelines

- **Language**: PT-BR technical prose, formal but accessible
- **Tone**: Educational, professional, security-focused
- **Code Identifiers**: English (variable names, function names, comments)
- **Technical Terms**: Keep English originals with PT-BR explanations
- **Cross-References**: Use `→ Capítulo X, Seção Y` format

---

## 3. Code Architecture

### 3.1 Code Organization Principles

```
cryptography/
├── code/
│   ├── ch01-intro/
│   │   ├── CMakeLists.txt
│   │   ├── 01_basic_openssl.cpp
│   │   ├── 02_random_generation.cpp
│   │   └── ...
│   ├── ch02-constant-time/
│   │   ├── CMakeLists.txt
│   │   ├── 01_secure_compare.cpp
│   │   └── ...
│   ├── ...
│   ├── common/
│   │   ├── CMakeLists.txt
│   │   ├── crypto_utils.h
│   │   ├── timing_utils.h
│   │   └── ...
│   └── external/
│       ├── openssl/
│       ├── libsodium/
│       └── liboqs/
├── tests/
│   ├── ch01/
│   ├── ch02/
│   └── ...
└── benchmarks/
    ├── ch01/
    └── ...
```

### 3.2 Code Example Categories

| Category | Purpose | Complexity | Example |
|----------|---------|------------|---------|
| **Snippet** | Illustrate concept | Low | 10-30 lines, single function |
| **Program** | Complete example | Medium | 50-150 lines, compilable |
| **Project** | Full implementation | High | 200-500 lines, multi-file |
| **Library** | Reusable component | High | 100-300 lines, header+source |

### 3.3 Code Quality Standards

```cpp
// Template for all code examples
#pragma once
#include <stdexcept>
#include <string>

// Header guard pattern
namespace crypto_book {

// Exception hierarchy for crypto errors
class CryptoError : public std::runtime_error {
public:
    explicit CryptoError(const std::string& msg) 
        : std::runtime_error(msg) {}
};

// RAII wrapper pattern
class SecureMemory {
public:
    explicit SecureMemory(size_t size);
    ~SecureMemory();
    
    // Disable copy, enable move
    SecureMemory(const SecureMemory&) = delete;
    SecureMemory& operator=(const SecureMemory&) = delete;
    SecureMemory(SecureMemory&& other) noexcept;
    SecureMemory& operator=(SecureMemory&& other) noexcept;
    
    uint8_t* data();
    const uint8_t* data() const;
    size_t size() const;
    
private:
    uint8_t* ptr_;
    size_t size_;
};

}  // namespace crypto_book
```

### 3.4 Library Integration Patterns

#### OpenSSL 3.x Pattern
```cpp
// Context-based initialization (3.x style)
#include <openssl/provider.h>
#include <openssl/evp.h>

class OpenSSLContext {
public:
    OpenSSLContext() {
        lib_ctx_ = OSSL_LIB_CTX_new();
        if (!lib_ctx_) throw CryptoError("Failed to create lib context");
        
        default_prov_ = OSSL_PROVIDER_load(lib_ctx_, "default");
        fips_prov_ = OSSL_PROVIDER_load(lib_ctx_, "fips");
    }
    
    ~OpenSSLContext() {
        if (fips_prov_) OSSL_PROVIDER_unload(fips_prov_);
        if (default_prov_) OSSL_PROVIDER_unload(default_prov_);
        OSSL_LIB_CTX_free(lib_ctx_);
    }
    
    OSSL_LIB_CTX* context() { return lib_ctx_; }
    
private:
    OSSL_LIB_CTX* lib_ctx_ = nullptr;
    OSSL_PROVIDER* default_prov_ = nullptr;
    OSSL_PROVIDER* fips_prov_ = nullptr;
};
```

#### libsodium Pattern
```cpp
// Modern crypto with libsodium
#include <sodium.h>

class SecureEncryption {
public:
    static std::vector<uint8_t> encrypt(
        const uint8_t* key,
        const uint8_t* nonce,
        const uint8_t* plaintext, size_t plaintext_len,
        const uint8_t* ad, size_t ad_len
    ) {
        std::vector<uint8_t> ciphertext(plaintext_len + crypto_aead_xchacha20poly1305_ietf_ABYTES);
        
        size_t ciphertext_len;
        if (crypto_aead_xchacha20poly1305_ietf_encrypt(
                ciphertext.data(), &ciphertext_len,
                plaintext, plaintext_len,
                ad, ad_len,
                nullptr, nonce, key) != 0) {
            throw CryptoError("Encryption failed");
        }
        
        ciphertext.resize(ciphertext_len);
        return ciphertext;
    }
};
```

#### liboqs Pattern
```cpp
// Post-quantum cryptography with liboqs
#include <oqs/oqs.h>

class PQCKeyExchange {
public:
    PQCKeyExchange() {
        if (OQS_init() != OQS_SUCCESS) {
            throw CryptoError("Failed to initialize liboqs");
        }
    }
    
    ~PQCKeyExchange() {
        OQS_cleanup();
    }
    
    std::pair<std::vector<uint8_t>, std::vector<uint8_t>> generate_keypair() {
        OQS_KEM* kem = OQS_KEM_new(OQS_KEM_alg_ml_kem_768);
        if (!kem) throw CryptoError("Failed to create KEM");
        
        std::vector<uint8_t> public_key(kem->length_public_key);
        std::vector<uint8_t> secret_key(kem->length_secret_key);
        
        if (OQS_KEM_keypair(kem, public_key.data(), secret_key.data()) != OQS_SUCCESS) {
            OQS_KEM_free(kem);
            throw CryptoError("Key generation failed");
        }
        
        OQS_KEM_free(kem);
        return {public_key, secret_key};
    }
};
```

### 3.5 Compilation and Build System

```cmake
# CMakeLists.txt for chapter code
cmake_minimum_required(VERSION 3.16)
project(crypto_book_ch02 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Find dependencies
find_package(OpenSSL 3.0 REQUIRED)
find_package(PkgConfig REQUIRED)
pkg_check_modules(SODIUM REQUIRED libsodium)
pkg_check_modules(OQS REQUIRED liboqs)

# Common utilities
add_library(crypto_common INTERFACE)
target_include_directories(crypto_common INTERFACE ${CMAKE_CURRENT_SOURCE_DIR}/../common)
target_link_libraries(crypto_common INTERFACE OpenSSL::Crypto ${SODIUM_LIBRARIES} ${OQS_LIBRARIES})

# Code examples
add_executable(01_secure_compare 01_secure_compare.cpp)
target_link_libraries(01_secure_compare PRIVATE crypto_common)

add_executable(02_branchless 02_branchless.cpp)
target_link_libraries(02_branchless PRIVATE crypto_common)

# Tests
enable_testing()
add_executable(test_secure_compare test_secure_compare.cpp)
target_link_libraries(test_secure_compare PRIVATE crypto_common GTest::gtest_main)
add_test(NAME test_secure_compare COMMAND test_secure_compare)

# Benchmarks
add_executable(bench_timing bench_timing.cpp)
target_link_libraries(bench_timing PRIVATE crypto_common benchmark::benchmark_main)
```

---

## 4. CVE Integration Strategy

### 4.1 CVE Documentation Framework

Each CVE analysis follows this structured template:

```markdown
## CVE-XXXX-XXXX: [Vulnerability Name]

### Timeline
- **Discovery**: [Date/Researcher]
- **Disclosure**: [Date]
- **Patch**: [Date/Version]
- **CVSS Score**: [X.X]

### Root Cause Analysis
- **Type**: [Memory safety, timing, logic error, etc.]
- **Location**: [File/Function/Component]
- **Root Cause**: [Detailed technical explanation]

### Technical Details
[How the vulnerability works, code paths, attack vectors]

### Impact
- **Confidentiality**: [None/Low/Medium/High]
- **Integrity**: [None/Low/Medium/High]
- **Availability**: [None/Low/Medium/High]

### Proof of Concept
[Code example demonstrating the vulnerability - EDUCATIONAL ONLY]

### Mitigation/Fix
[How it was fixed, patches, workarounds]

### Lessons Learned
[What engineers should learn from this vulnerability]

### References
- [CVE link]
- [Paper/Article]
- [Patch commit]
```

### 4.2 CVE Distribution Across Chapters

| Chapter | CVEs | Focus |
|---------|------|-------|
| Ch01 | CVE-2008-0166, CVE-2013-2099, CVE-2014-0160 | RNG failures, memory safety |
| Ch02 | CVE-2013-0169, CVE-2019-15809, CVE-2020-1968 | Timing attacks |
| Ch03 | CVE-2022-23935, CVE-2022-40982, CVE-2019-11090 | Side-channels |
| Ch04 | CVE-2017-15361 | HSM vulnerabilities |
| Ch05 | CVE-2013-0169, CVE-2014-3566, CVE-2015-0204, CVE-2014-3513 | TLS attacks |
| Ch06 | CVE-2022-3676 | PQC implementation flaws |
| Ch08 | CVE-2015-4000, CVE-2016-2183, CVE-2021-3449 | Protocol attacks |
| Ch09 | CVE-2019-11090, CVE-2019-16863 | Hardware attacks |
| Ch13 | CVE-2016-0773 | Testing-related bugs |
| Ch15 | CVE-2014-0160 | Case study context |
| Ch16 | CVE-2017-1000364 | Monitoring context |

### 4.3 CVE Integration Patterns

**Pattern 1: Motivation (Chapter Start)**
```markdown
### CVE Context
Before diving into [topic], consider CVE-XXXX-XXXX: [brief description].
This vulnerability affected [impact] and teaches us [lesson].
Understanding this helps us build [what we're building].
```

**Pattern 2: Technical Deep Dive (Mid-Chapter)**
```markdown
### CVE Analysis: CVE-XXXX-XXXX
[Full CVE documentation following the template above]
```

**Pattern 3: Validation (End of Section)**
```markdown
### Security Check
Does our implementation avoid CVE-XXXX-XXXX?
✓ [Check 1]
✓ [Check 2]
✓ [Check 3]
```

**Pattern 4: Cross-Reference (Related Chapters)**
```markdown
→ See also: Capítulo X, Seção Y for related CVE analysis
→ Related: CVE-XXXX-XXXX (timing variant)
```

### 4.4 CVE Code Examples

Each CVE includes:
1. **Vulnerable Code**: Simplified version showing the bug (educational)
2. **Attack Demonstration**: How an attacker exploits it (controlled environment)
3. **Fixed Code**: The patched version with explanations
4. **Test Case**: Regression test to prevent reintroduction

```cpp
// CVE Example Pattern
namespace cve_analysis {

// VULNERABLE: Timing attack in comparison
bool vulnerable_compare(const uint8_t* a, const uint8_t* b, size_t len) {
    for (size_t i = 0; i < len; i++) {
        if (a[i] != b[i]) return false;  // Early exit leaks timing
    }
    return true;
}

// FIXED: Constant-time comparison
bool secure_compare(const uint8_t* a, const uint8_t* b, size_t len) {
    uint8_t result = 0;
    for (size_t i = 0; i < len; i++) {
        result |= a[i] ^ b[i];
    }
    return result == 0;
}

}  // namespace cve_analysis
```

---

## 5. Quality Architecture

### 5.1 Line Count Management

**Target Distribution per Chapter (2,800-3,900 lines)**:

| Component | Target | Tolerance | Validation |
|-----------|--------|-----------|------------|
| Prose | 1,400 lines | ±200 | Word count check |
| Code | 1,000 lines | ±150 | Compilation check |
| Tables | 300 lines | ±50 | Format check |
| Exercises | 300 lines | ±50 | Completeness check |
| CVE Analysis | 350 lines | ±100 | Template adherence |
| **Total** | **3,350 lines** | **±550** | **All components** |

### 5.2 Quality Gates

| Gate | Trigger | Validation | Action on Fail |
|------|---------|------------|----------------|
| **Line Count** | Chapter completion | `wc -l` validation | Add/remove content |
| **Code Compilation** | Every code block | `g++ -std=c++17` test | Fix compilation errors |
| **Link Check** | Final review | URL validation | Update/fix links |
| **Cross-Reference** | Final review | Chapter reference check | Add missing references |
| **CVE Completeness** | CVE section | Template validation | Complete missing fields |
| **PT-BR Grammar** | Prose sections | Language review | Grammar corrections |
| **English Consistency** | Code sections | Naming convention check | Standardize naming |

### 5.3 Content Review Checklist

```markdown
## Chapter NN Review Checklist

### Structure
- [ ] Learning objectives are clear and measurable
- [ ] Section outline matches actual content
- [ ] All sections within target line range
- [ ] Total lines within 2,800-3,900 range

### Content Quality
- [ ] Concepts build progressively
- [ ] Technical accuracy verified
- [ ] Code examples compile and run
- [ ] Tables are well-formatted
- [ ] Diagrams are clear (if any)

### CVE Integration
- [ ] All CVEs follow template
- [ ] CVEs are woven into narrative
- [ ] Code examples are educational
- [ ] References are complete

### Code Quality
- [ ] C++17 compliant
- [ ] Proper error handling
- [ ] RAII patterns used
- [ ] Memory safety ensured
- [ ] Constant-time where applicable

### Cross-References
- [ ] All internal links valid
- [ ] Related chapters mentioned
- [ ] Book 1-4 references included
- [ ] External references current

### Language
- [ ] PT-BR prose is natural
- [ ] Technical terms properly handled
- [ ] English code identifiers
- [ ] No regional slang
```

### 5.4 Consistency Mechanisms

**Style Guide Enforcement**:
- All chapters use identical section structure
- CVE analysis follows fixed template
- Code examples use consistent patterns
- Tables use standard formatting

**Automated Validation**:
```bash
# Line count validation
for ch in cryptography/ch*.md; do
    lines=$(wc -l < "$ch")
    if [ "$lines" -lt 2800 ] || [ "$lines" -gt 3900 ]; then
        echo "WARNING: $ch has $lines lines (target: 2800-3900)"
    fi
done

# Code compilation check
find cryptography/code -name "*.cpp" | while read f; do
    g++ -std=c++17 -fsyntax-only "$f" || echo "COMPILE ERROR: $f"
done
```

---

## 6. Library Integration Plan

### 6.1 Library Usage Matrix

| Library | Primary Use | Chapters | Code Examples | Tests |
|---------|-------------|----------|---------------|-------|
| **OpenSSL 3.x** | TLS, crypto ops, PKCS#11 | 01,02,04,05,07,08,15 | 40+ examples | 20+ tests |
| **libsodium** | Modern crypto, constant-time | 01,02,06,08 | 15+ examples | 10+ tests |
| **liboqs** | Post-quantum algorithms | 06,08 | 10+ examples | 5+ tests |
| **Botan** | Alternative implementation | 02,05,13 | 8+ examples | 5+ tests |
| **TPM2-TSS** | TPM 2.0 integration | 09 | 5+ examples | 3+ tests |
| **Microsoft SEAL** | Homomorphic encryption | 10 | 6+ examples | 3+ tests |
| **libsnark** | Zero-knowledge proofs | 11 | 5+ examples | 2+ tests |
| **Google Benchmark** | Performance testing | 13,15 | 10+ benchmarks | N/A |

### 6.2 Library Installation and Configuration

```bash
# OpenSSL 3.x
sudo apt-get install libssl-dev
# Or build from source for latest version
git clone https://github.com/openssl/openssl.git
cd openssl && ./Configure && make && sudo make install

# libsodium
sudo apt-get install libsodium-dev
# Or from source
git clone https://github.com/jedisct1/libsodium.git
cd libsodium && ./configure && make && sudo make install

# liboqs
git clone https://github.com/open-quantum-safe/liboqs.git
cd liboqs && mkdir build && cd build
cmake -DCMAKE_INSTALL_PREFIX=/usr/local ..
make && sudo make install

# Botan
sudo apt-get install libbotan-2-dev
# Or from source
git clone https://github.com/randombit/botan.git
cd botan && python3 configure.py && make && sudo make install

# TPM2-TSS
sudo apt-get install libtss2-dev
# Or from source
git clone https://github.com/tpm2-software/tpm2-tss.git
cd tpm2-tss && ./bootstrap && ./configure && make && sudo make install

# Microsoft SEAL
git clone https://github.com/microsoft/SEAL.git
cd SEAL && mkdir build && cd build
cmake -DCMAKE_INSTALL_PREFIX=/usr/local ..
make && sudo make install

# libsnark
git clone https://github.com/scipr-lab/libsnark.git
cd libsnark && mkdir build && cd build
cmake -DCURVE=ALT_BN128 ..
make && sudo make install
```

### 6.3 Version Compatibility

| Library | Minimum Version | Recommended | Notes |
|---------|-----------------|-------------|-------|
| OpenSSL | 3.0.0 | 3.2+ | Provider API required |
| libsodium | 1.0.18 | 1.0.19+ | XChaCha20 support |
| liboqs | 0.9.0 | 0.10+ | NIST PQC finalists |
| Botan | 2.19.0 | 3.0+ | C++17 support |
| TPM2-TSS | 3.0.0 | 4.0+ | ESAPI improvements |
| Microsoft SEAL | 3.5.0 | 4.0+ | CKKS improvements |
| libsnark | 2.0.0 | 2.1+ | Performance fixes |

### 6.4 Library Abstraction Pattern

```cpp
// Provider pattern for library abstraction
class CryptoProvider {
public:
    virtual ~CryptoProvider() = default;
    
    // Symmetric encryption
    virtual std::vector<uint8_t> encrypt_aes_gcm(
        const uint8_t* key, size_t key_len,
        const uint8_t* nonce, size_t nonce_len,
        const uint8_t* plaintext, size_t plaintext_len,
        const uint8_t* aad, size_t aad_len,
        uint8_t* tag, size_t tag_len
    ) = 0;
    
    // Key exchange
    virtual std::pair<std::vector<uint8_t>, std::vector<uint8_t>>
    generate_keypair_x25519() = 0;
    
    // Digital signatures
    virtual std::vector<uint8_t> sign_ed25519(
        const uint8_t* secret_key,
        const uint8_t* message, size_t message_len
    ) = 0;
};

// OpenSSL implementation
class OpenSSLProvider : public CryptoProvider { /* ... */ };

// libsodium implementation
class LibsodiumProvider : public CryptoProvider { /* ... */ };

// Factory pattern
std::unique_ptr<CryptoProvider> create_provider(
    const std::string& library_name
);
```

---

## 7. Series Integration

### 7.1 Book 1-4 References

| Book | Title | Key Topics | Cross-Reference Strategy |
|------|-------|------------|--------------------------|
| **Book 1** | SDD in C++ | Architecture, testing, design patterns | Reference architecture patterns |
| **Book 2** | DevSecOps in C++ | CI/CD, security automation, deployment | Reference security automation |
| **Book 3** | Malware Analysis in C++ | Reverse engineering, malware detection | Reference analysis techniques |
| **Book 4** | Concurrency in C++ | Threads, synchronization, performance | Reference concurrent crypto operations |

### 7.2 Cross-Reference Mapping

```markdown
## Book 5 → Book 1 References

### Architecture Patterns (Ch01, Ch15)
- Provider Pattern → Book 1, Ch12 (Design Patterns)
- RAII for Crypto Resources → Book 1, Ch04 (Memory Security)
- Error Handling → Book 1, Ch05 (Exception Safety)

### Testing (Ch13)
- Property-Based Testing → Book 1, Ch13 (Security Testing)
- Fuzzing → Book 1, Ch13 (Penetration Testing)

## Book 5 → Book 2 References

### CI/CD Integration (Ch12, Ch16)
- Security Scanning → Book 2, Ch06 (SAST/DAST)
- Dependency Management → Book 2, Ch04 (Supply Chain)
- Deployment → Book 2, Ch16 (Secure Deployment)

### Compliance Automation (Ch14)
- Automated Compliance → Book 2, Ch14 (Compliance as Code)

## Book 5 → Book 3 References

### Reverse Engineering (Ch03)
- Side-Channel Analysis → Book 3, Ch03 (Static Analysis)
- Hardware Interaction → Book 3, Ch04 (Dynamic Analysis)

### Malware Crypto Analysis (Ch01)
- Cryptographic Malware → Book 3, Ch08 (Ransomware Analysis)

## Book 5 → Book 4 References

### Concurrent Crypto (Ch08, Ch15)
- Thread-Safe HSM → Book 4, Ch02 (Synchronization)
- Connection Pooling → Book 4, Ch08 (Concurrent Containers)
- Lock-Free Crypto Operations → Book 4, Ch03 (Lock-Free Programming)
```

### 7.3 Progressive Complexity

| Topic | Book 1 | Book 2 | Book 3 | Book 4 | Book 5 |
|-------|--------|--------|--------|--------|--------|
| **Cryptography** | Basics (Ch08) | TLS basics | Malware crypto | N/A | Advanced engineering |
| **Security Testing** | Pentest basics | SAST/DAST | Malware detection | N/A | Formal verification |
| **Compliance** | Standards overview | CI/CD compliance | N/A | N/A | Deep compliance |
| **Memory Safety** | RAII basics | N/A | N/A | Lock-free | Secure memory |
| **Error Handling** | Exceptions | Error recovery | N/A | Concurrency errors | Crypto-specific |

### 7.4 Shared CVE Coverage

| CVE | Book 1 | Book 2 | Book 3 | Book 4 | Book 5 |
|-----|--------|--------|--------|--------|--------|
| CVE-2014-0160 | Brief mention | Brief mention | N/A | N/A | Deep analysis (Ch01, Ch15) |
| CVE-2008-0166 | N/A | N/A | N/A | N/A | Full analysis (Ch01, Ch07) |
| Timing attacks | N/A | N/A | N/A | N/A | Comprehensive (Ch02, Ch03) |

---

## 8. Implementation Roadmap

### 8.1 Phase 1: Foundation (Chapters 00-03)

**Duration**: 2-3 weeks  
**Focus**: Core concepts, constant-time programming, side-channels

| Task | Priority | Dependencies | Est. Hours |
|------|----------|--------------|------------|
| Ch00 Prefácio | High | None | 8 |
| Ch01 Introdução | High | Ch00 | 40 |
| Ch02 Constant-Time | High | Ch01 | 48 |
| Ch03 Side-Channel | Medium | Ch02 | 52 |
| Code infrastructure | High | None | 20 |
| Common utilities | High | None | 16 |

### 8.2 Phase 2: Hardware & Protocols (Chapters 04-09)

**Duration**: 3-4 weeks  
**Focus**: HSM, TLS, PQC, key management, protocols, TPM

| Task | Priority | Dependencies | Est. Hours |
|------|----------|--------------|------------|
| Ch04 HSM/Tokens | High | Ch01 | 44 |
| Ch05 TLS 1.3 | High | Ch01, Ch02 | 56 |
| Ch06 PQC | High | Ch05 | 48 |
| Ch07 Key Management | Medium | Ch04 | 44 |
| Ch08 Modern Protocols | Medium | Ch05 | 48 |
| Ch09 Hardware Security | Medium | Ch04 | 44 |

### 8.3 Phase 3: Advanced Topics (Chapters 10-14)

**Duration**: 2-3 weeks  
**Focus**: HE, ZKP, formal verification, testing, compliance

| Task | Priority | Dependencies | Est. Hours |
|------|----------|--------------|------------|
| Ch10 Homomorphic | Medium | Ch01 | 40 |
| Ch11 ZKP | Medium | Ch01 | 44 |
| Ch12 Formal Verification | Medium | Ch01, Ch02 | 40 |
| Ch13 Testing | Medium | Ch01 | 44 |
| Ch14 Compliance | Medium | Ch01 | 40 |

### 8.4 Phase 4: Integration (Chapters 15-17)

**Duration**: 2 weeks  
**Focus**: Case study, best practices, conclusion

| Task | Priority | Dependencies | Est. Hours |
|------|----------|--------------|------------|
| Ch15 Case Study | High | Ch02, Ch04, Ch05, Ch07 | 60 |
| Ch16 Best Practices | High | All | 40 |
| Ch17 Conclusion | Low | All | 24 |

### 8.5 Total Effort Estimate

| Phase | Chapters | Hours | Lines |
|-------|----------|-------|-------|
| Phase 1 | 00-03 | 188 | 12,200 |
| Phase 2 | 04-09 | 284 | 19,800 |
| Phase 3 | 10-14 | 208 | 15,400 |
| Phase 4 | 15-17 | 124 | 8,700 |
| **Total** | **18** | **804** | **56,100** |

---

## 9. Risk Mitigation

### 9.1 Technical Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Library version incompatibility | Medium | High | Pin versions, test early |
| Code compilation failures | Medium | Medium | CI/CD validation |
| CVE information outdated | Low | Medium | Multiple sources, verification |
| Performance benchmarks inconsistent | High | Low | Standardized environment |

### 9.2 Content Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Line count outside target | High | Medium | Content templates, validation |
| Cross-references broken | Medium | Low | Automated link checking |
| PT-BR grammar issues | Low | Low | Language review |
| Code examples too complex | Medium | Medium | Progressive complexity |

### 9.3 Schedule Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Phase delays | Medium | High | Buffer time, priority focus |
| External dependency changes | Low | High | Version pinning |
| Review bottlenecks | High | Medium | Parallel review tracks |

---

## 10. Success Criteria

### 10.1 Technical Metrics

- [ ] All 18 chapters completed (17 + preface)
- [ ] 2,800-3,900 lines per chapter (excluding preface)
- [ ] 20+ unique CVEs documented
- [ ] All code examples compile with C++17
- [ ] All code examples tested
- [ ] Performance benchmarks included

### 10.2 Quality Metrics

- [ ] Cross-references validated
- [ ] CVE templates complete
- [ ] PT-BR prose reviewed
- [ ] English code identifiers consistent
- [ ] Library versions documented

### 10.3 Integration Metrics

- [ ] Book 1-4 cross-references included
- [ ] Shared CVEs documented
- [ ] Progressive complexity maintained
- [ ] Reading paths defined

---

## Next Recommended Step

**sdd-tasks**: Break this design into implementation tasks with:
- Task breakdown per chapter
- Dependencies and sequencing
- Acceptance criteria
- Time estimates
- Resource requirements

---

**Status**: Design complete  
**Artifacts**: This design document  
**Next Phase**: sdd-tasks (implementation planning)
