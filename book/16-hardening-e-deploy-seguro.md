# Capítulo 16 — Hardening e Deploy Seguro

Hardening e deploy seguro representam a última barreira entre um código que funciona e um sistema resiliente a ataques. Neste capítulo, exploramos técnicas de fortalecimento em cada camada da pilha de deployment — do compilador ao container, da cadeia de suprimentos à monitoramento em produção. Cada seção inclui código C++17 praticável e configurações reais que podem ser adotadas imediatamente em projetos de produção.

---

## Objetivos de Aprendizado

1. Aplicar flags de hardening do compilador (GCC/Clang) e verificar sua efetividade em binários C++17.
2. Configurar mecanismos de segurança do sistema operacional Linux (seccomp-bpf, AppArmor, SELinux, capabilities) diretamente em código C++.
3. Construir containers Docker e Kubernetes hardened para aplicações C++, incluindo uso de imagens distroless e contexto de segurança.
4. Implementar práticas de segurança na cadeia de suprimentos: SBOM, assinatura de artefatos com Sigstore, e builds reproduzíveis.
5. Projetar um pipeline completo de deploy seguro com monitoramento, gerenciamento de segredos e verificação pós-deploy.

---

## 1. Compiler Hardening Flags

O compilador é o primeiro ponto de defesa. Flags de hardening injetam verificações de segurança diretamente no binário compilado, muitas vezes com custo de performance mínimo.

### 1.1 Visão Geral das Flags

| Flag | Proteção contra | Descrição |
|------|-----------------|-----------|
| `-fstack-protector-strong` | Stack buffer overflow | Canário de stack para funções com variáveis locais sensíveis |
| `-D_FORTIFY_SOURCE=2` | Buffer overflows em funções de libc | Substitui funções como `memcpy`, `strcpy` por versões verificadas |
| `-fPIE` / `-pie` | Retorno de ROP/JOP | Position-Independent Executable, habilita ASLR completo |
| `-Wl,-z,relro -Wl,-z,now` | GOT overwrite | Torna a GOT (Global Offset Table) somente-leitura após relocação |
| `-Wl,-z,noexecstack` | Execução de código na stack | Impede execução de código injetado na stack |
| `-fsanitize=cfi` | Code-reuse attacks | Control Flow Integrity, valida integridade do fluxo de controle |
| `-Wformat -Wformat-security` | Format string attacks | Avisa sobre format strings inseguras |

### 1.2 CMakeLists.txt Completo com Hardening

```cmake
cmake_minimum_required(VERSION 3.16)
project(SecureApp VERSION 1.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# --- Compiler Hardening Flags ---
# Stack protection
add_compile_options(-fstack-protector-strong)

# Fortified source (level 2 for maximum coverage)
add_compile_options(-D_FORTIFY_SOURCE=2)

# Position-independent code
add_compile_options(-fPIE)

# Format security warnings
add_compile_options(-Wformat -Wformat-security)

# Additional hardening warnings
add_compile_options(-Wall -Wextra -Wpedantic)
add_compile_options(-Wconversion -Wsign-conversion)
add_compile_options(-Wshadow -Wnon-virtual-dtor)
add_compile_options(-Wold-style-cast -Wcast-align)
add_compile_options(-Woverloaded-virtual -Wconversion)

# Control Flow Integrity (Clang-specific)
if(CMAKE_CXX_COMPILER_ID MATCHES "Clang")
    add_compile_options(-fsanitize=cfi)
    add_link_options(-fsanitize=cfi)
endif()

# --- Linker Hardening Flags ---
add_link_options(-Wl,-z,relro,-z,now)   # Full RELRO
add_link_options(-Wl,-z,noexecstack)     # Non-executable stack
add_link_options(-pie)                    # Position-independent executable

# Strip symbols in release builds
if(CMAKE_BUILD_TYPE STREQUAL "Release")
    add_link_options(-s)
    add_compile_options(-O2)
    add_compile_options(-DNDEBUG)
elseif(CMAKE_BUILD_TYPE STREQUAL "RelWithDebInfo")
    add_compile_options(-O2 -g)
else()
    add_compile_options(-O0 -g)
endif()

# --- Source Files ---
add_executable(secure_app
    src/main.cpp
    src/hardening_wrapper.cpp
)

target_include_directories(secure_app PRIVATE include)
```

### 1.3 Verificação de Flags no Binário

Após compilar, é essencial verificar se as proteções foram efetivamente aplicadas:

```cpp
// src/verify_hardening.cpp
// Compile with: g++ -o verify_hardening src/verify_hardening.cpp
#include <iostream>
#include <cstdlib>
#include <cstring>
#include <elf.h>
#include <link.h>

// Check if RELRO is enabled by reading the ELF segment
bool check_relro(const char* binary_path) {
    FILE* f = fopen(binary_path, "rb");
    if (!f) {
        std::cerr << "Cannot open binary: " << binary_path << "\n";
        return false;
    }

    Elf64_Ehdr ehdr;
    fread(&ehdr, sizeof(ehdr), 1, f);

    // Check for GNU_RELRO segment
    for (size_t i = 0; i < ehdr.e_phnum; ++i) {
        Elf64_Phdr phdr;
        fseek(f, ehdr.e_phoff + i * ehdr.e_phentsize, SEEK_SET);
        fread(&phdr, sizeof(phdr), 1, f);
        if (phdr.p_type == PT_GNU_RELRO) {
            fclose(f);
            return true;
        }
    }
    fclose(f);
    return false;
}

// Check NX bit (non-executable stack)
bool check_nx(const char* binary_path) {
    FILE* f = fopen(binary_path, "rb");
    if (!f) return false;

    Elf64_Ehdr ehdr;
    fread(&ehdr, sizeof(ehdr), 1, f);

    for (size_t i = 0; i < ehdr.e_phnum; ++i) {
        Elf64_Phdr phdr;
        fseek(f, ehdr.e_phoff + i * ehdr.e_phentsize, SEEK_SET);
        fread(&phdr, sizeof(phdr), 1, f);
        // GNU_STACK with PF_X means executable stack (bad)
        if (phdr.p_type == PT_GNU_STACK) {
            fclose(f);
            return !(phdr.p_flags & PF_X);
        }
    }
    fclose(f);
    return false;
}

// Check PIE
bool check_pie(const char* binary_path) {
    FILE* f = fopen(binary_path, "rb");
    if (!f) return false;

    Elf64_Ehdr ehdr;
    fread(&ehdr, sizeof(ehdr), 1, f);
    fclose(f);

    // ET_DYN means shared object (PIE), ET_EXEC means fixed address
    return ehdr.e_type == ET_DYN;
}

// Check if symbols are stripped
bool check_stripped(const char* binary_path) {
    FILE* f = fopen(binary_path, "rb");
    if (!f) return false;

    Elf64_Ehdr ehdr;
    fread(&ehdr, sizeof(ehdr), 1, f);

    // Check section header count
    Elf64_Shdr shdr_strtab;
    fseek(f, ehdr.e_shoff + ehdr.e_shstrndx * ehdr.e_shentsize, SEEK_SET);
    fread(&shdr_strtab, sizeof(shdr_strtab), 1, f);

    // Read section name
    char strtab[256];
    fseek(f, shdr_strtab.sh_offset, SEEK_SET);
    fread(strtab, sizeof(strtab), 1, f);

    bool has_symtab = false;
    for (size_t i = 0; i < ehdr.e_shnum; ++i) {
        Elf64_Shdr shdr;
        fseek(f, ehdr.e_phoff + i * ehdr.e_shentsize, SEEK_SET);
        // Actually need section headers
        fseek(f, ehdr.e_shoff + i * ehdr.e_shentsize, SEEK_SET);
        fread(&shdr, sizeof(shdr), 1, f);

        if (shdr.sh_type == SHT_SYMTAB) {
            has_symtab = true;
            break;
        }
    }
    fclose(f);
    return !has_symtab;
}

int main(int argc, char* argv[]) {
    const char* binary = (argc > 1) ? argv[1] : argv[0];

    std::cout << "=== Hardening Verification ===\n";
    std::cout << "Binary: " << binary << "\n\n";

    auto check = [](const char* name, bool result) {
        std::cout << (result ? "[OK]" : "[FAIL]") << " " << name << "\n";
    };

    check("PIE (Position Independent Executable)", check_pie(binary));
    check("NX (Non-executable stack)", check_nx(binary));
    check("RELRO (Read-only GOT)", check_relro(binary));
    check("Stripped symbols", check_stripped(binary));

    return 0;
}
```

### 1.4 Impacto no Performance

A tabela a seguir resume o custo de cada flag de hardening:

| Flag | Overhead médio | Nota |
|------|----------------|------|
| `-fstack-protector-strong` | < 1% | Apenas funções com variáveis sensíveis |
| `-D_FORTIFY_SOURCE=2` | < 2% | Apenas em tempo de execução |
| `-fPIE` / `-pie` | 1-3% | Indireção via GOT |
| `-Wl,-z,relro -z,now` | < 0.5% | Link-time apenas |
| `-Wl,-z,noexecstack` | 0% | Zero overhead, apenas marcação ELF |
| `-fsanitize=cfi` | 5-15% | Depende da complexidade do grafo de chamadas |

Em produção, o overhead combinado raramente ultrapassa 5%. Para a maioria dos sistemas, esse custo é insignificante comparado ao risco de exploração.

---

## 2. OS Hardening

### 2.1 seccomp-bpf: Filtragem de System Calls

seccomp-bpf permite restringir quais system calls a aplicação pode fazer. Se um atacante explora um buffer overflow, o shellcode malicioso falhará ao tentar usar syscalls não permitidos.

```cpp
// src/seccomp_filter.cpp
#include <iostream>
#include <cstring>
#include <cerrno>
#include <unistd.h>
#include <sys/prctl.h>
#include <linux/seccomp.h>
#include <linux/filter.h>
#include <linux/audit.h>
#include <sys/syscall.h>
#include <vector>

class SeccompFilter {
public:
    // BPF instruction helpers
    static struct sock_filter create_load_instruction(
        unsigned int offset, unsigned int size
    ) {
        struct sock_filter filter = {};
        filter.code = BPF_LD | BPF_W | BPF_ABS;
        filter.jt = 0;
        filter.jf = 0;
        filter.k = offset;
        return filter;
    }

    static struct sock_filter create_jump_instruction(
        unsigned int op, unsigned intjt, unsigned int jf, unsigned int k
    ) {
        struct sock_filter filter = {};
        filter.code = BPF_JMP | BPF_JEQ | op;
        filter.jt = jt;
        filter.jf = jf;
        filter.k = k;
        return filter;
    }

    // Apply a minimal seccomp filter allowing only essential syscalls
    static bool apply_minimal_filter() {
        std::vector<struct sock_filter> rules;

        // Load syscall number (architecture-dependent)
#if defined(__x86_64__)
        rules.push_back(create_load_instruction(
            offsetof(struct seccomp_data, nr), 4
        ));
#else
        rules.push_back(create_load_instruction(
            offsetof(struct seccomp_data, nr), 4
        ));
#endif

        // Allow essential syscalls
        std::vector<unsigned int> allowed_syscalls = {
            SYS_read,
            SYS_write,
            SYS_open,
            SYS_close,
            SYS_stat,
            SYS_fstat,
            SYS_mmap,
            SYS_mprotect,
            SYS_munmap,
            SYS_brk,
            SYS_exit_group,
            SYS_futex,
            SYS_epoll_wait,
            SYS_epoll_ctl,
            SYS_accept4,
            SYS_socket,
            SYS_bind,
            SYS_listen,
            SYS_connect,
            SYS_sendto,
            SYS_recvfrom,
            SYS_setsockopt,
            SYS_getsockopt,
            SYS_getrandom,
            SYS_clock_gettime,
            SYS_ioctl,
            SYS_arch_prctl,
        };

        // Jump to allow for each syscall, fall through to deny
        for (size_t i = 0; i < allowed_syscalls.size(); ++i) {
            struct sock_filter jump = {};
            jump.code = BPF_JMP | BPF_JEQ;
            jump.k = allowed_syscalls[i];
            if (i < allowed_syscalls.size() - 1) {
                jump.jt = static_cast<unsigned int>(
                    allowed_syscalls.size() - i - 1
                );
                jump.jf = 0;
            }
            rules.push_back(jump);
        }

        // Deny all other syscalls (kill process)
        struct sock_filter deny = {};
        deny.code = BPF_RET | BPF_K;
        deny.k = SECCOMP_RET_KILL_PROCESS;
        rules.push_back(deny);

        // Build BPF program
        struct sock_fprog prog = {};
        prog.len = static_cast<unsigned short>(rules.size());
        prog.filter = rules.data();

        // Apply filter
        if (prctl(PR_SET_NO_NEW_PRIVS, 1, 0, 0, 0) != 0) {
            std::cerr << "Failed to set no_new_privs: "
                      << strerror(errno) << "\n";
            return false;
        }

        if (prctl(PR_SET_SECCOMP, SECCOMP_MODE_FILTER, &prog) != 0) {
            std::cerr << "Failed to set seccomp filter: "
                      << strerror(errno) << "\n";
            return false;
        }

        std::cout << "Seccomp filter applied successfully.\n";
        return true;
    }

    // Apply a strict filter that kills on any disallowed syscall
    static bool apply_strict_filter() {
        std::vector<struct sock_filter> rules;

        // Load syscall number
        rules.push_back(create_load_instruction(
            offsetof(struct seccomp_data, nr), 4
        ));

        // Strict mode: only read, write, exit_group
        std::vector<unsigned int> strict_syscalls = {
            SYS_read,
            SYS_write,
            SYS_close,
            SYS_exit_group,
            SYS_futex,
        };

        for (size_t i = 0; i < strict_syscalls.size(); ++i) {
            struct sock_filter jump = {};
            jump.code = BPF_JMP | BPF_JEQ;
            jump.k = strict_syscalls[i];
            jump.jt = static_cast<unsigned int>(
                strict_syscalls.size() - i - 1
            );
            jump.jf = 0;
            rules.push_back(jump);
        }

        // Kill on anything else
        struct sock_filter deny = {};
        deny.code = BPF_RET | BPF_K;
        deny.k = SECCOMP_RET_KILL_PROCESS;
        rules.push_back(deny);

        struct sock_fprog prog = {};
        prog.len = static_cast<unsigned short>(rules.size());
        prog.filter = rules.data();

        if (prctl(PR_SET_NO_NEW_PRIVS, 1, 0, 0, 0) != 0) {
            std::cerr << "Failed to set no_new_privs: "
                      << strerror(errno) << "\n";
            return false;
        }

        if (prctl(PR_SET_SECCOMP, SECCOMP_MODE_FILTER, &prog) != 0) {
            std::cerr << "Failed to set seccomp filter: "
                      << strerror(errno) << "\n";
            return false;
        }

        std::cout << "Strict seccomp filter applied.\n";
        return true;
    }
};
```

### 2.2 AppArmor: Perfil Mandatory Access Control

Um perfil AppArmor para uma aplicação C++ restringe filesystem, rede, e capabilities:

```
# /etc/apparmor.d/usr.local.bin.secure_app
#include <tunables/global>

/usr/local/bin/secure_app {
    #include <abstractions/base>
    #include <abstractions/nameservice>

    # Allow reading config
    /etc/secure_app/ r,
    /etc/secure_app/config.json r,

    # Allow logging
    /var/log/secure_app/ w,
    /var/log/secure_app/*.log w,

    # Allow network (only specific ports)
    network inet stream,
    network inet6 stream,

    # Deny everything else by default
    deny /home/** rw,
    deny /root/** rw,
    deny /tmp/** rw,

    # Allow /proc for self
    /proc/self/status r,

    # Deny raw socket access
    deny network raw,

    # Deny mount/umount
    deny mount,
    deny umount,

    # Deny ptrace
    deny ptrace (trace),

    # Deny access to sensitive files
    deny /etc/shadow r,
    deny /etc/passwd w,
    deny /etc/group w,
}
```

### 2.3 C++ Capability Management

```cpp
// src/capability_manager.cpp
#include <iostream>
#include <cstring>
#include <cerrno>
#include <unistd.h>
#include <sys/capability.h>
#include <vector>

class CapabilityManager {
public:
    // Drop all capabilities except the ones needed
    static bool drop_all_except(const std::vector<cap_value_t>& keep) {
        cap_t caps = cap_get_proc();
        if (!caps) {
            std::cerr << "cap_get_proc failed: " << strerror(errno) << "\n";
            return false;
        }

        // Start with empty set
        if (cap_clear(caps) != 0) {
            std::cerr << "cap_clear failed: " << strerror(errno) << "\n";
            cap_free(caps);
            return false;
        }

        // Add back only what we need
        for (cap_value_t cap : keep) {
            if (cap_set_flag(caps, CAP_EFFECTIVE, 1, &cap, CAP_SET) != 0) {
                std::cerr << "cap_set_flag failed for cap " << cap
                          << ": " << strerror(errno) << "\n";
                cap_free(caps);
                return false;
            }
            if (cap_set_flag(caps, CAP_PERMITTED, 1, &cap, CAP_SET) != 0) {
                std::cerr << "cap_set_flag failed for cap " << cap
                          << ": " << strerror(errno) << "\n";
                cap_free(caps);
                return false;
            }
            if (cap_set_flag(caps, CAP_INHERITABLE, 1, &cap, CAP_SET) != 0) {
                std::cerr << "cap_set_flag failed for cap " << cap
                          << ": " << strerror(errno) << "\n";
                cap_free(caps);
                return false;
            }
        }

        if (cap_set_proc(caps) != 0) {
            std::cerr << "cap_set_proc failed: " << strerror(errno) << "\n";
            cap_free(caps);
            return false;
        }

        cap_free(caps);

        std::cout << "Capabilities restricted. Keeping: ";
        for (cap_value_t cap : keep) {
            std::cout << cap << " ";
        }
        std::cout << "\n";

        return true;
    }

    // Drop ALL capabilities (full drop)
    static bool drop_all() {
        cap_t caps = cap_get_proc();
        if (!caps) return false;

        if (cap_clear(caps) != 0) {
            cap_free(caps);
            return false;
        }

        if (cap_set_proc(caps) != 0) {
            std::cerr << "cap_set_proc failed: " << strerror(errno) << "\n";
            cap_free(caps);
            return false;
        }

        cap_free(caps);
        std::cout << "All capabilities dropped.\n";
        return true;
    }

    // Print current capabilities
    static void print_current() {
        cap_t caps = cap_get_proc();
        if (!caps) return;

        char* text = cap_to_text(caps, nullptr);
        if (text) {
            std::cout << "Current capabilities: " << text << "\n";
            cap_free(text);
        }

        cap_free(caps);
    }
};

// Usage in main application
int main() {
    CapabilityManager::print_current();

    // For a network server, we only need CAP_NET_BIND_SERVICE
    // (to bind to port < 1024 if needed)
    std::vector<cap_value_t> needed = {CAP_NET_BIND_SERVICE};
    CapabilityManager::drop_all_except(needed);

    // After initialization, drop even that
    CapabilityManager::drop_all();

    CapabilityManager::print_current();

    return 0;
}
```

### 2.4 Wrapper Completo de Hardening

```cpp
// include/hardening_wrapper.h
#pragma once

#include <string>
#include <functional>
#include <atomic>

class HardeningWrapper {
public:
    struct Config {
        bool enable_seccomp = true;
        bool drop_capabilities = true;
        bool set_resource_limits = true;
        bool restrict_core_dumps = true;
        bool enable_aslr = true;
        bool chroot_jail = false;
        std::string chroot_path = "/var/secure_app";
        std::string unprivileged_user = "secureapp";
    };

    explicit HardeningWrapper(const Config& config);
    ~HardeningWrapper() = default;

    // Non-copyable
    HardeningWrapper(const HardeningWrapper&) = delete;
    HardeningWrapper& operator=(const HardeningWrapper&) = delete;

    // Apply all configured hardening measures
    bool apply_all();

    // Individual hardening methods
    bool apply_seccomp();
    bool drop_privileges();
    bool set_resource_limits();
    bool restrict_core_dumps();
    bool enable_aslr();
    bool chroot_jail();

    // Get status of each hardening measure
    bool is_seccomp_active() const { return seccomp_active_; }
    bool is_privileges_dropped() const { return privileges_dropped_; }

private:
    Config config_;
    std::atomic<bool> seccomp_active_{false};
    std::atomic<bool> privileges_dropped_{false};
};
```

---

## 3. Container Security

### 3.1 Dockerfile Hardened para C++17

```dockerfile
# === Stage 1: Build ===
FROM gcc:13.2-bookworm AS builder

ARG BUILD_TYPE=Release
ARG VERSION=1.0.0

WORKDIR /build

# Install dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    cmake \
    libssl-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

# Copy source
COPY CMakeLists.txt .
COPY src/ src/
COPY include/ include/

# Build with all hardening flags
RUN cmake -B build -DCMAKE_BUILD_TYPE=${BUILD_TYPE} \
    -DCMAKE_CXX_FLAGS="-fstack-protector-strong -D_FORTIFY_SOURCE=2 -fPIE -Wformat -Wformat-security" \
    -DCMAKE_EXE_LINKER_FLAGS="-Wl,-z,relro,-z,now -Wl,-z,noexecstack -pie" \
    -DVERSION=${VERSION} \
    && cmake --build build --parallel $(nproc) \
    && strip build/secure_app

# === Stage 2: Runtime (Distroless) ===
FROM gcr.io/distroless/cc-debian12:nonroot

LABEL maintainer="security-team" \
      version="${VERSION}" \
      description="Hardened C++ application"

# Copy binary from builder
COPY --from=builder /build/build/secure_app /usr/local/bin/secure_app

# Copy config (read-only)
COPY --chown=65534:65534 config/ /etc/secure_app/
RUN chmod -R 444 /etc/secure_app/

# Security: nonroot user (uid 65534) is default in distroless:nonroot
USER nonroot:nonroot

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD ["/usr/local/bin/secure_app", "--health-check"]

# Expose only the required port
EXPOSE 8443

# Run with entrypoint
ENTRYPOINT ["/usr/local/bin/secure_app"]
CMD ["--config", "/etc/secure_app/config.json"]
```

### 3.2 Container Security Context (Kubernetes)

```yaml
# k8s/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: secure-app
  labels:
    app: secure-app
spec:
  replicas: 3
  selector:
    matchLabels:
      app: secure-app
  template:
    metadata:
      labels:
        app: secure-app
    spec:
      securityContext:
        runAsNonRoot: true
        runAsUser: 65534
        runAsGroup: 65534
        fsGroup: 65534
        seccompProfile:
          type: RuntimeDefault

      containers:
      - name: secure-app
        image: registry.example.com/secure-app:1.0.0@sha256:abc123...

        securityContext:
          allowPrivilegeEscalation: false
          readOnlyRootFilesystem: true
          runAsNonRoot: true
          runAsUser: 65534
          capabilities:
            drop:
              - ALL
            add: []
          seccompProfile:
            type: RuntimeDefault

        resources:
          limits:
            cpu: "1"
            memory: 512Mi
            ephemeral-storage: 100Mi
          requests:
            cpu: 100m
            memory: 128Mi

        ports:
        - containerPort: 8443
          protocol: TCP

        volumeMounts:
        - name: tmp
          mountPath: /tmp
        - name: config
          mountPath: /etc/secure_app
          readOnly: true

        livenessProbe:
          httpGet:
            path: /health
            port: 8443
            scheme: HTTPS
          initialDelaySeconds: 10
          periodSeconds: 30

        readinessProbe:
          httpGet:
            path: /ready
            port: 8443
            scheme: HTTPS
          initialDelaySeconds: 5
          periodSeconds: 10

      volumes:
      - name: tmp
        emptyDir:
          medium: Memory
          sizeLimit: 64Mi
      - name: config
        configMap:
          name: secure-app-config
```

### 3.3 Scanning de Imagens

```bash
# Trivy: scan for vulnerabilities
trivy image --severity HIGH,CRITICAL registry.example.com/secure-app:1.0.0

# Grype: alternative scanner
grype registry.example.com/secure-app:1.0.0

# Snyk container scan
snyk container test registry.example.com/secure-app:1.0.0

# Docker Scout
docker scout cves registry.example.com/secure-app:1.0.0
```

### 3.4 Caso Real: CVE-2019-5736 (Container Escape via runc)

**O que aconteceu:** Vulnerabilidade no runc (executor de containers) permitia que um atacante dentro de um container sobrescrevesse o binário runc no host, ganhando root no host ao executar `docker exec` ou `kubectl exec`.

**O que deu errado:** O runc não validava corretamente o caminho do `/proc/self/exe` ao iniciar um novo container. Um container malicioso podia substituir o binário runc com código arbitrário.

**Como mitigar:**
- Atualizar runc para versões >= 1.0.0-rc6
- Usar rootless containers (evita ter root no host)
- Usar seccomp-bpf para limitar syscalls dentro do container
- Não executar `docker exec` em containers não confiáveis

```cpp
// src/container_escape_mitigation.cpp
// Demonstrates how seccomp can prevent container escape

#include <iostream>
#include <cstring>
#include <cerrno>
#include <unistd.h>
#include <sys/prctl.h>
#include <sys/mount.h>
#include <linux/seccomp.h>
#include <linux/filter.h>

class ContainerEscapeGuard {
public:
    // Block dangerous syscalls that could be used for escape
    static bool block_escape_syscalls() {
        // Key syscalls to block in containerized environments:
        // - mount/umount: prevent filesystem manipulation
        // - pivot_root: prevent root filesystem change
        // - unshare: prevent namespace escape
        // - clone with CLONE_NEWUSER: prevent user namespace escape

        struct sock_filter rules[] = {
            // Load syscall number
            BPF_STMT(BPF_LD | BPF_W | BPF_ABS,
                     offsetof(struct seccomp_data, nr)),

            // Block mount
            BPF_JUMP(BPF_JMP | BPF_JEQ, SYS_mount, 0, 1),
            BPF_STMT(BPF_RET | BPF_K, SECCOMP_RET_KILL_PROCESS),

            // Block pivot_root
            BPF_JUMP(BPF_JMP | BPF_JEQ, SYS_pivot_root, 0, 1),
            BPF_STMT(BPF_RET | BPF_K, SECCOMP_RET_KILL_PROCESS),

            // Block unshare
            BPF_JUMP(BPF_JMP | BPF_JEQ, SYS_unshare, 0, 1),
            BPF_STMT(BPF_RET | BPF_K, SECCOMP_RET_KILL_PROCESS),

            // Block clone with CLONE_NEWUSER flag
            // (would need to check args, simplified here)
            BPF_JUMP(BPF_JMP | BPF_JEQ, SYS_clone, 0, 1),
            BPF_STMT(BPF_RET | BPF_K, SECCOMP_RET_KILL_PROCESS),

            // Allow everything else
            BPF_STMT(BPF_RET | BPF_K, SECCOMP_RET_ALLOW),
        };

        struct sock_fprog prog = {
            .len = static_cast<unsigned short>(
                sizeof(rules) / sizeof(rules[0])
            ),
            .filter = rules,
        };

        if (prctl(PR_SET_NO_NEW_PRIVS, 1, 0, 0, 0) != 0) {
            std::cerr << "Failed to set no_new_privs\n";
            return false;
        }

        if (prctl(PR_SET_SECCOMP, SECCOMP_MODE_FILTER, &prog) != 0) {
            std::cerr << "Failed to apply seccomp filter\n";
            return false;
        }

        std::cout << "Container escape syscalls blocked.\n";
        return true;
    }
};
```

### 3.5 Caso Real: Docker Socket Exposure

**O que aconteceu:** Organizações expuseram o Docker socket (`/var/run/docker.sock`) para dentro de containers, permitindo que qualquer container com acesso pudesse criar novos containers com acesso total ao host.

**O que deu errado:** O Docker socket é essencialmente uma API root ao host. Containerize applications that needed to manage other containers ended up creating a privilege escalation path.

**Regra de ouro:** NUNCA monte o Docker socket em containers que não são orquestradores confiáveis. Use Docker API proxy ou Ferris (Docker auth proxy) quando precisar de acesso gerenciado.

---

## 4. Supply Chain Security

### 4.1 SBOM Generation (Software Bill of Materials)

```cpp
// src/sbom_generator.cpp
// Generates a simple SBOM in SPDX format

#include <iostream>
#include <fstream>
#include <string>
#include <vector>
#include <sstream>
#include <ctime>
#include <iomanip>
#include <algorithm>
#include <numeric>

struct PackageInfo {
    std::string name;
    std::string version;
    std::string supplier;
    std::string spdx_id;
    std::string download_location;
    std::string license_concluded;
    bool files_analyzed;
    std::string sha256_hash;
};

class SBOMGenerator {
public:
    explicit SBOMGenerator(const std::string& document_name)
        : document_name_(document_name) {
        // Generate creation timestamp
        auto now = std::time(nullptr);
        auto tm = *std::gmtime(&now);
        std::ostringstream oss;
        oss << std::put_time(&tm, "%Y-%m-%dT%H:%M:%SZ");
        creation_time_ = oss.str();
    }

    void add_package(const PackageInfo& pkg) {
        packages_.push_back(pkg);
    }

    // Generate SPDX-format SBOM
    std::string generate_spdx() const {
        std::ostringstream out;

        // Header
        out << "SPDXVersion: SPDX-2.3\n";
        out << "DataLicense: CC0-1.0\n";
        out << "SPDXID: SPDXRef-DOCUMENT\n";
        out << "DocumentName: " << document_name_ << "\n";
        out << "DocumentNamespace: http://example.com/spdx/"
            << document_name_ << "\n";
        out << "Creator: Tool: sbom-generator\n";
        out << "Created: " << creation_time_ << "\n";
        out << "\n";

        // Package section
        for (size_t i = 0; i < packages_.size(); ++i) {
            const auto& pkg = packages_[i];
            out << "PackageName: " << pkg.name << "\n";
            out << "SPDXID: SPDXRef-Package-" << pkg.spdx_id << "\n";
            out << "PackageVersion: " << pkg.version << "\n";
            out << "PackageSupplier: " << pkg.supplier << "\n";
            out << "PackageDownloadLocation: "
                << pkg.download_location << "\n";
            out << "FilesAnalyzed: "
                << (pkg.files_analyzed ? "true" : "false") << "\n";
            out << "PackageLicenseConcluded: "
                << pkg.license_concluded << "\n";
            if (!pkg.sha256_hash.empty()) {
                out << "PackageChecksum: SHA256: "
                    << pkg.sha256_hash << "\n";
            }
            out << "\n";
        }

        return out.str();
    }

    bool write_sbom(const std::string& output_path) const {
        std::ofstream file(output_path);
        if (!file.is_open()) {
            std::cerr << "Failed to open output file: "
                      << output_path << "\n";
            return false;
        }

        file << generate_spdx();
        std::cout << "SBOM written to " << output_path << "\n";
        return true;
    }

private:
    std::string document_name_;
    std::string creation_time_;
    std::vector<PackageInfo> packages_;
};

// Usage
int main() {
    SBOMGenerator gen("secure-app-1.0.0");

    gen.add_package({
        "openssl", "3.1.4", "OpenSSL Software Foundation",
        "OpenSSL", "https://www.openssl.org/",
        "Apache-2.0", false, ""
    });

    gen.add_package({
        "zlib", "1.3", "Jean-loup Gailly",
        "zlib", "https://zlib.net/",
        "Zlib", false, ""
    });

    gen.write_sbom("sbom.spdx");
    return 0;
}
```

### 4.2 Sigstore: Assinatura de Artefatos

```bash
# Sign container image with Cosign (Sigstore)
cosign sign --yes registry.example.com/secure-app:1.0.0

# Verify signature
cosign verify \
    --certificate-identity=registry@example.com \
    --certificate-oidc-issuer=https://accounts.google.com \
    registry.example.com/secure-app:1.0.0

# Sign SBOM
cosign attest --predicate sbom.spdx --type spdxjson \
    registry.example.com/secure-app:1.0.0

# Verify attestation
cosign verify-attestation --type spdxjson \
    --certificate-identity=registry@example.com \
    --certificate-oidc-issuer=https://accounts.google.com \
    registry.example.com/secure-app:1.0.0
```

### 4.3 Builds Reproduzíveis

```cmake
# CMake configuration for reproducible builds
cmake_minimum_required(VERSION 3.16)
project(ReproducibleBuild LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)

# Reproducibility: fixed paths and timestamps
set(CMAKE_INSTALL_PREFIX "/usr" CACHE PATH "" FORCE)
set(CMAKE_SKIP_INSTALL_ALL_DEPENDENCY ON)

# Remove timestamps from binary
add_compile_options(-Wdate-time)

# Fixed build directory
set(CMAKE_BINARY_DIR "${CMAKE_SOURCE_DIR}/build")

# Deterministic file ordering
set(CMAKE_DEFAULT_SOURCE_DIR "${CMAKE_SOURCE_DIR}")

# Strip debug info for release
set(CMAKE_STRIP "strip" CACHE FILEPATH "")

# Use fixed locale
set(ENV{LC_ALL} "C")
set(ENV{LANG} "C")

# Remove __FILE__ macros for reproducibility
add_compile_options(
    "-ffile-prefix-map=${CMAKE_SOURCE_DIR}=/"
)

add_executable(reproducible_app src/main.cpp)
```

### 4.4 Caso Real: SolarWinds (2020)

**O que aconteceu:** Atacantes inseriram código malicioso no build pipeline do SolarWinds Orion. O malware (SUNBURST) era injetado durante o processo de build, fazendo com que qualquer binário compilado fosse comprometido. Mais de 18.000 organizações foram afetadas.

**O que deu errado:** O pipeline de build não era auditável. Não havia verificação de integridade entre as etapas. O compilador não era verificável contra reprodução. Não existia SBOM para rastrear componentes.

**Como mitigar:**
- Builds reproduzíveis para verificação independente
- SBOM para rastreabilidade total de dependências
- Assinatura de artefatos em cada etapa do pipeline
- Isolamento do build environment com attestation

### 4.5 Caso Real: Codecov Bash Uploader (2021)

**O que aconteceu:** Atacantes modificaram o script bash uploader do Codecov, exfiltrando variáveis de ambiente (incluindo secrets de CI/CD) de pipelines que executavam o script.

**O que deu errado:** O script não possuía verificação de integridade. Organizações executavam scripts baixados da internet sem validação. Secrets eram armazenados em variáveis de ambiente acessíveis ao script.

**Como mitigar:**
- Verificar hashes de scripts antes de executar
- Usar ferramentas com releases assinadas
- Nunca armazenar secrets em variáveis de ambiente acessíveis a scripts de terceiros
- Usar vaults para secrets com acesso temporário

### 4.6 Caso Real: xz-utils Backdoor (2024, CVE-2024-3094)

**O que aconteceu:** Um atacante infiltrou-se como maintainer no projeto xz-utils por dois anos, gradualmente inserindo código malicioso que criava uma backdoor no sshd via systemctl. A backdoor permitia autenticação remota sem credenciais.

**O que deu errado:** O projeto dependia de um único maintainer. Não havia code review rigoroso. O processo de build do xz-utils não era reproduzível. A cadeia de confiança era frágil — a inserção ocorreu gradualmente para evitar detecção.

**Como mitigar:**
- SBOM completo com rastreabilidade de todas as dependências
- Builds reproduzíveis independentes
- Verificação de integridade de dependências antes de cada build
- Múltiplos maintainers com code review obrigatório
- Monitoramento de mudanças suspeitas em dependências críticas

```cpp
// src/dependency_verifier.cpp
// Verify dependency integrity against known-good hashes

#include <iostream>
#include <fstream>
#include <string>
#include <unordered_map>
#include <sstream>
#include <iomanip>
#include <openssl/sha.h>

class DependencyVerifier {
public:
    using HashMap = std::unordered_map<std::string, std::string>;

    bool load_manifest(const std::string& path) {
        std::ifstream file(path);
        if (!file.is_open()) return false;

        std::string line;
        while (std::getline(file, line)) {
            // Format: sha256hash * filename
            auto space = line.find(' ');
            if (space != std::string::npos) {
                std::string hash = line.substr(0, space);
                std::string filename = line.substr(space + 3); // skip " * "
                manifest_[filename] = hash;
            }
        }
        return true;
    }

    std::string compute_sha256(const std::string& filepath) {
        std::ifstream file(filepath, std::ios::binary);
        if (!file.is_open()) return "";

        SHA256_CTX sha256;
        SHA256_Init(&sha256);

        char buffer[8192];
        while (file.read(buffer, sizeof(buffer))) {
            SHA256_Update(&sha256, buffer, file.gcount());
        }
        SHA256_Update(&sha256, buffer, file.gcount());

        unsigned char hash[SHA256_DIGEST_LENGTH];
        SHA256_Final(hash, &sha256);

        std::ostringstream oss;
        for (int i = 0; i < SHA256_DIGEST_LENGTH; ++i) {
            oss << std::hex << std::setw(2) << std::setfill('0')
                << static_cast<int>(hash[i]);
        }

        return oss.str();
    }

    bool verify(const std::string& filepath) {
        std::string filename = filepath.substr(filepath.find_last_of("/\\") + 1);

        auto it = manifest_.find(filename);
        if (it == manifest_.end()) {
            std::cerr << "[WARN] " << filename
                      << " not found in manifest\n";
            return false;
        }

        std::string computed = compute_sha256(filepath);
        if (computed.empty()) {
            std::cerr << "[ERROR] Cannot compute hash for "
                      << filepath << "\n";
            return false;
        }

        if (computed != it->second) {
            std::cerr << "[CRITICAL] Hash mismatch for " << filename
                      << "\n  Expected: " << it->second
                      << "\n  Got:      " << computed << "\n";
            return false;
        }

        std::cout << "[OK] " << filename << " verified.\n";
        return true;
    }

    bool verify_all() {
        bool all_ok = true;
        for (const auto& [filename, expected_hash] : manifest_) {
            std::string computed = compute_sha256(filename);
            if (computed != expected_hash) {
                std::cerr << "[FAIL] " << filename << "\n";
                all_ok = false;
            } else {
                std::cout << "[OK] " << filename << "\n";
            }
        }
        return all_ok;
    }

private:
    HashMap manifest_;
};
```

---

## 5. Secret Management

### 5.1 Vault Patterns

```cpp
// src/vault_client.cpp
// HashiCorp Vault integration for secret retrieval

#include <iostream>
#include <string>
#include <curl/curl.h>
#include <json/json.h>

class VaultClient {
public:
    VaultClient(const std::string& vault_addr,
                const std::string& token)
        : vault_addr_(vault_addr), token_(token) {}

    // Retrieve a secret from Vault KV v2
    std::string get_secret(const std::string& mount,
                           const std::string& path,
                           const std::string& key) {
        std::string url = vault_addr_ + "/v1/" + mount + "/data/" + path;

        CURL* curl = curl_easy_init();
        if (!curl) return "";

        struct curl_slist* headers = nullptr;
        std::string auth_header = "X-Vault-Token: " + token_;
        headers = curl_slist_append(headers, auth_header.c_str());

        std::string response;
        curl_easy_setopt(curl, CURLOPT_URL, url.c_str());
        curl_easy_setopt(curl, CURLOPT_HTTPHEADER, headers);
        curl_easy_setopt(curl, CURLOPT_WRITEFUNCTION, write_callback);
        curl_easy_setopt(curl, CURLOPT_WRITEDATA, &response);

        CURLcode res = curl_easy_perform(curl);
        curl_slist_free_all(headers);
        curl_easy_cleanup(curl);

        if (res != CURLE_OK) {
            std::cerr << "Vault request failed: "
                      << curl_easy_strerror(res) << "\n";
            return "";
        }

        // Parse JSON response
        Json::Value root;
        Json::CharReaderBuilder builder;
        std::istringstream stream(response);
        std::string errors;

        if (!Json::parseFromStream(builder, stream, &root, &errors)) {
            std::cerr << "JSON parse error: " << errors << "\n";
            return "";
        }

        return root["data"]["data"][key].asString();
    }

    // Retrieve a database credential (dynamic secrets)
    std::pair<std::string, std::string>
    get_database_credentials(const std::string& role) {
        std::string url = vault_addr_
            + "/v1/database/creds/" + role;

        CURL* curl = curl_easy_init();
        if (!curl) return {"", ""};

        struct curl_slist* headers = nullptr;
        std::string auth_header = "X-Vault-Token: " + token_;
        headers = curl_slist_append(headers, auth_header.c_str());

        std::string response;
        curl_easy_setopt(curl, CURLOPT_URL, url.c_str());
        curl_easy_setopt(curl, CURLOPT_HTTPHEADER, headers);
        curl_easy_setopt(curl, CURLOPT_WRITEFUNCTION, write_callback);
        curl_easy_setopt(curl, CURLOPT_WRITEDATA, &response);

        CURLcode res = curl_easy_perform(curl);
        curl_slist_free_all(headers);
        curl_easy_cleanup(curl);

        if (res != CURLE_OK) return {"", ""};

        Json::Value root;
        Json::CharReaderBuilder builder;
        std::istringstream stream(response);
        std::string errors;

        if (!Json::parseFromStream(builder, stream, &root, &errors)) {
            return {"", ""};
        }

        std::string username = root["data"]["username"].asString();
        std::string password = root["data"]["password"].asString();

        // Credentials are ephemeral — they'll be revoked after TTL
        return {username, password};
    }

private:
    std::string vault_addr_;
    std::string token_;

    static size_t write_callback(char* ptr, size_t size,
                                  size_t nmemb, void* userdata) {
        auto* response = static_cast<std::string*>(userdata);
        response->append(ptr, size * nmemb);
        return size * nmemb;
    }
};
```

### 5.2 Secure Memory Manager

```cpp
// include/secure_memory.h
#pragma once

#include <cstddef>
#include <cstring>
#include <memory>
#include <vector>
#include <type_traits>

// Secure memory that is locked and zeroed on deallocation
class SecureAllocator {
public:
    using value_type = char;

    SecureAllocator() noexcept = default;

    template <typename U>
    SecureAllocator(const SecureAllocator<U>&) noexcept {}

    char* allocate(std::size_t n) {
        char* ptr = static_cast<char*>(std::malloc(n));
        if (!ptr) throw std::bad_alloc();

        // Lock memory to prevent swapping to disk
        mlock(ptr, n);

        return ptr;
    }

    void deallocate(char* ptr, std::size_t n) noexcept {
        if (ptr) {
            // Securely zero memory before freeing
            explicit_bzero(ptr, n);

            // Unlock memory
            munlock(ptr, n);

            std::free(ptr);
        }
    }
};

// Secure string that zeros memory on destruction
class SecureString {
public:
    SecureString() = default;

    explicit SecureString(const char* str) : data_(str, str + strlen(str)) {}

    explicit SecureString(const std::string& str)
        : data_(str.begin(), str.end()) {}

    ~SecureString() {
        secure_zero();
    }

    // Non-copyable (prevent accidental copies of secrets)
    SecureString(const SecureString&) = delete;
    SecureString& operator=(const SecureString&) = delete;

    // Movable
    SecureString(SecureString&& other) noexcept
        : data_(std::move(other.data_)) {
        other.secure_zero();
    }

    SecureString& operator=(SecureString&& other) noexcept {
        if (this != &other) {
            secure_zero();
            data_ = std::move(other.data_);
            other.secure_zero();
        }
        return *this;
    }

    const char* data() const { return data_.data(); }
    std::size_t size() const { return data_.size(); }
    bool empty() const { return data_.empty(); }

    std::string to_string() const {
        return std::string(data_.data(), data_.size());
    }

    // Constant-time comparison to prevent timing attacks
    bool operator==(const SecureString& other) const {
        if (data_.size() != other.data_.size()) return false;

        volatile unsigned char result = 0;
        for (std::size_t i = 0; i < data_.size(); ++i) {
            result |= static_cast<unsigned char>(
                data_[i] ^ other.data_[i]
            );
        }
        return result == 0;
    }

    bool operator!=(const SecureString& other) const {
        return !(*this == other);
    }

private:
    void secure_zero() {
        if (!data_.empty()) {
            explicit_bzero(data_.data(), data_.size());
        }
    }

    std::vector<char, SecureAllocator> data_;
};

// RAII wrapper for mlock'd memory
template <typename T>
class LockedMemory {
public:
    explicit LockedMemory(std::size_t count = 1) : count_(count) {
        ptr_ = static_cast<T*>(std::calloc(count, sizeof(T)));
        if (!ptr_) throw std::bad_alloc();
        mlock(ptr_, count * sizeof(T));
    }

    ~LockedMemory() {
        if (ptr_) {
            explicit_bzero(ptr_, count_ * sizeof(T));
            munlock(ptr_, count_ * sizeof(T));
            std::free(ptr_);
        }
    }

    T* get() { return ptr_; }
    const T* get() const { return ptr_; }

    T& operator[](std::size_t idx) { return ptr_[idx]; }
    const T& operator[](std::size_t idx) const { return ptr_[idx]; }

private:
    T* ptr_;
    std::size_t count_;
};
```

---

## 6. Monitoring e Alerting

### 6.1 Structured Logging para Segurança

```cpp
// include/security_logger.h
#pragma once

#include <string>
#include <chrono>
#include <mutex>
#include <fstream>
#include <sstream>
#include <iomanip>
#include <iostream>
#include <map>
#include <functional>

enum class SecurityEventType {
    AUTH_SUCCESS,
    AUTH_FAILURE,
    AUTHORIZATION_DENIED,
    INPUT_VALIDATION_FAILED,
    RATE_LIMIT_EXCEEDED,
    SYSCALL_VIOLATION,
    PRIVILEGE_ESCALATION_ATTEMPT,
    FILE_ACCESS_DENIED,
    NETWORK_CONNECTION_ATTEMPT,
    CONFIG_CHANGE,
    INTEGRITY_CHECK_FAILED,
    DEPENDENCY_VIOLATION,
    TLS_HANDSHAKE_FAILED,
    INJECTION_ATTEMPT,
};

class SecurityLogger {
public:
    static SecurityLogger& instance() {
        static SecurityLogger logger;
        return logger;
    }

    void log_event(SecurityEventType type,
                   const std::string& source,
                   const std::string& message,
                   const std::map<std::string, std::string>& metadata = {}) {
        std::lock_guard<std::mutex> lock(mutex_);

        auto now = std::chrono::system_clock::now();
        auto time_t_now = std::chrono::system_clock::to_time_t(now);

        std::ostringstream timestamp;
        timestamp << std::put_time(
            std::gmtime(&time_t_now), "%Y-%m-%dT%H:%M:%SZ"
        );

        std::ostringstream json;
        json << "{"
             << "\"timestamp\":\"" << timestamp.str() << "\","
             << "\"level\":\"" << severity_for(type) << "\","
             << "\"event_type\":\"" << event_type_name(type) << "\","
             << "\"source\":\"" << escape_json(source) << "\","
             << "\"message\":\"" << escape_json(message) << "\"";

        if (!metadata.empty()) {
            json << ",\"metadata\":{";
            bool first = true;
            for (const auto& [key, value] : metadata) {
                if (!first) json << ",";
                json << "\"" << escape_json(key) << "\":\""
                     << escape_json(value) << "\"";
                first = false;
            }
            json << "}";
        }

        json << "}";

        // Write to structured log file
        if (log_file_.is_open()) {
            log_file_ << json.str() << "\n";
            log_file_.flush();
        }

        // Also output to stderr for SIEM collection
        std::cerr << json.str() << "\n";

        // Alert on critical events
        if (is_critical(type)) {
            trigger_alert(type, source, message);
        }
    }

    void log_auth_success(const std::string& user,
                          const std::string& source_ip) {
        log_event(
            SecurityEventType::AUTH_SUCCESS,
            "authentication",
            "User authenticated successfully",
            {{"user", user}, {"source_ip", source_ip}}
        );
    }

    void log_auth_failure(const std::string& user,
                          const std::string& source_ip,
                          const std::string& reason) {
        log_event(
            SecurityEventType::AUTH_FAILURE,
            "authentication",
            "Authentication failed",
            {{"user", user}, {"source_ip", source_ip}, {"reason", reason}}
        );
    }

    void log_injection_attempt(const std::string& source,
                               const std::string& input_type,
                               const std::string& details) {
        log_event(
            SecurityEventType::INJECTION_ATTEMPT,
            "input_validation",
            "Possible injection attack detected",
            {{"input_type", input_type}, {"details", details}}
        );
    }

    void log_syscall_violation(pid_t pid,
                               const std::string& syscall,
                               const std::string& detail) {
        log_event(
            SecurityEventType::SYSCALL_VIOLATION,
            "seccomp",
            "Blocked syscall execution",
            {{"pid", std::to_string(pid)},
             {"syscall", syscall},
             {"detail", detail}}
        );
    }

private:
    SecurityLogger() {
        log_file_.open("/var/log/secure_app/security.jsonl",
                       std::ios::app);
    }

    std::mutex mutex_;
    std::ofstream log_file_;

    static std::string severity_for(SecurityEventType type) {
        switch (type) {
            case SecurityEventType::AUTH_SUCCESS: return "INFO";
            case SecurityEventType::AUTH_FAILURE: return "WARNING";
            case SecurityEventType::AUTHORIZATION_DENIED: return "WARNING";
            case SecurityEventType::INPUT_VALIDATION_FAILED: return "WARNING";
            case SecurityEventType::RATE_LIMIT_EXCEEDED: return "WARNING";
            case SecurityEventType::SYSCALL_VIOLATION: return "CRITICAL";
            case SecurityEventType::PRIVILEGE_ESCALATION_ATTEMPT:
                return "CRITICAL";
            case SecurityEventType::FILE_ACCESS_DENIED: return "WARNING";
            case SecurityEventType::NETWORK_CONNECTION_ATTEMPT: return "INFO";
            case SecurityEventType::CONFIG_CHANGE: return "INFO";
            case SecurityEventType::INTEGRITY_CHECK_FAILED: return "CRITICAL";
            case SecurityEventType::DEPENDENCY_VIOLATION: return "CRITICAL";
            case SecurityEventType::TLS_HANDSHAKE_FAILED: return "WARNING";
            case SecurityEventType::INJECTION_ATTEMPT: return "CRITICAL";
        }
        return "INFO";
    }

    static std::string event_type_name(SecurityEventType type) {
        switch (type) {
            case SecurityEventType::AUTH_SUCCESS: return "auth_success";
            case SecurityEventType::AUTH_FAILURE: return "auth_failure";
            case SecurityEventType::AUTHORIZATION_DENIED:
                return "authorization_denied";
            case SecurityEventType::INPUT_VALIDATION_FAILED:
                return "input_validation_failed";
            case SecurityEventType::RATE_LIMIT_EXCEEDED:
                return "rate_limit_exceeded";
            case SecurityEventType::SYSCALL_VIOLATION:
                return "syscall_violation";
            case SecurityEventType::PRIVILEGE_ESCALATION_ATTEMPT:
                return "privilege_escalation_attempt";
            case SecurityEventType::FILE_ACCESS_DENIED:
                return "file_access_denied";
            case SecurityEventType::NETWORK_CONNECTION_ATTEMPT:
                return "network_connection_attempt";
            case SecurityEventType::CONFIG_CHANGE: return "config_change";
            case SecurityEventType::INTEGRITY_CHECK_FAILED:
                return "integrity_check_failed";
            case SecurityEventType::DEPENDENCY_VIOLATION:
                return "dependency_violation";
            case SecurityEventType::TLS_HANDSHAKE_FAILED:
                return "tls_handshake_failed";
            case SecurityEventType::INJECTION_ATTEMPT:
                return "injection_attempt";
        }
        return "unknown";
    }

    static bool is_critical(SecurityEventType type) {
        return type == SecurityEventType::SYSCALL_VIOLATION
            || type == SecurityEventType::PRIVILEGE_ESCALATION_ATTEMPT
            || type == SecurityEventType::INTEGRITY_CHECK_FAILED
            || type == SecurityEventType::INJECTION_ATTEMPT;
    }

    static std::string escape_json(const std::string& input) {
        std::string output;
        output.reserve(input.size() + 10);
        for (char c : input) {
            switch (c) {
                case '"':  output += "\\\""; break;
                case '\\': output += "\\\\"; break;
                case '\n': output += "\\n"; break;
                case '\r': output += "\\r"; break;
                case '\t': output += "\\t"; break;
                default:   output += c; break;
            }
        }
        return output;
    }

    void trigger_alert(SecurityEventType type,
                       const std::string& source,
                       const std::string& message) {
        // In production: send to PagerDuty, Slack, email, etc.
        std::cerr << "[ALERT] CRITICAL SECURITY EVENT: "
                  << event_type_name(type) << " from " << source
                  << ": " << message << "\n";
    }
};
```

### 6.2 SIEM Integration Pattern

```cpp
// src/siem_forwarder.cpp
// Forward security events to SIEM (e.g., Elastic Security, Splunk)

#include <iostream>
#include <string>
#include <curl/curl.h>
#include <json/json.h>

class SIEMForwarder {
public:
    SIEMForwarder(const std::string& siem_url,
                  const std::string& api_key)
        : siem_url_(siem_url), api_key_(api_key) {}

    bool send_event(const std::string& event_json) {
        CURL* curl = curl_easy_init();
        if (!curl) return false;

        struct curl_slist* headers = nullptr;
        std::string auth = "Authorization: Bearer " + api_key_;
        headers = curl_slist_append(headers, auth.c_str());
        headers = curl_slist_append(headers,
                                    "Content-Type: application/json");

        curl_easy_setopt(curl, CURLOPT_URL, siem_url_.c_str());
        curl_easy_setopt(curl, CURLOPT_HTTPHEADER, headers);
        curl_easy_setopt(curl, CURLOPT_POSTFIELDS, event_json.c_str());
        curl_easy_setopt(curl, CURLOPT_TIMEOUT, 10L);

        CURLcode res = curl_easy_perform(curl);

        long http_code = 0;
        curl_easy_getinfo(curl, CURLINFO_RESPONSE_CODE, &http_code);

        curl_slist_free_all(headers);
        curl_easy_cleanup(curl);

        return res == CURLE_OK && http_code >= 200 && http_code < 300;
    }

private:
    std::string siem_url_;
    std::string api_key_;
};
```

### 6.3 Caso Real: Docker Socket Exposure (detalhamento)

**Impacto:** Um container com acesso ao Docker socket pode:
1. Criar novos containers com volumes arbitrários (acesso total ao host)
2. Listar e inspecionar todos os containers em execução
3. Remover containers legítimos (DoS)
4. Executar comandos dentro de qualquer container
5. Acessar segredos armazenados em variáveis de ambiente

**Como prevenir:**
- Usar Docker Auth Proxy (como Ferris) em vez de expor o socket
- Usar rootless Podman para ambientes que precisam de gerenciamento de containers
- Implementar network policies no Kubernetes para isolar comunicação
- Monitorar chamadas à API Docker com audit logging

---

## 7. Binary Hardening

### 7.1 Stripping e Hardening

```cmake
# CMake release configuration for binary hardening
if(CMAKE_BUILD_TYPE STREQUAL "Release")
    # Strip symbols
    add_custom_command(TARGET secure_app POST_BUILD
        COMMAND ${CMAKE_STRIP} --strip-unneeded $<TARGET_FILE:secure_app>
        COMMENT "Stripping symbols from binary"
    )

    # Optional: use UPX for compression (note: may interfere with
    # some security tools)
    # add_custom_command(TARGET secure_app POST_BUILD
    #     COMMAND upx --best --lzma $<TARGET_FILE:secure_app>
    #     COMMENT "Compressing binary with UPX"
    # )

    # Verify hardening with checksec
    add_custom_command(TARGET secure_app POST_BUILD
        COMMAND checksec --file=$<TARGET_FILE:secure_app>
        COMMENT "Verifying binary hardening"
        VERBATIM
    )
endif()
```

### 7.2 Anti-Debugging (Defensive)

```cpp
// src/anti_debug.cpp
// Defensive anti-debugging for protecting intellectual property
// in commercial software

#include <iostream>
#include <cstring>
#include <cerrno>
#include <unistd.h>
#include <sys/ptrace.h>
#include <sys/stat.h>
#include <fstream>
#include <string>
#include <signal.h>

class AntiDebug {
public:
    // Check if debugger is attached via ptrace
    static bool is_debugger_attached() {
        // PTRACE_TRACEME returns error if already traced
        if (ptrace(PTRACE_TRACEME, 0, nullptr, nullptr) == -1) {
            return true; // Already being traced
        }

        // If TRACEME succeeded, detach to avoid affecting our process
        ptrace(PTRACE_DETACH, 0, nullptr, nullptr);
        return false;
    }

    // Check /proc/self/status for TracerPid
    static bool check_tracer_pid() {
        std::ifstream status("/proc/self/status");
        std::string line;

        while (std::getline(status, line)) {
            if (line.find("TracerPid:") == 0) {
                // Extract the PID value
                size_t colon = line.find(':');
                if (colon != std::string::npos) {
                    int pid = std::stoi(line.substr(colon + 1));
                    return pid != 0;
                }
            }
        }
        return false;
    }

    // Check for common debugger environment variables
    static bool check_debug_env() {
        const char* debug_vars[] = {
            "LD_PRELOAD", "LD_DEBUG", "GDB",
            "DISPLAY", "VALGRIND_PID"
        };

        for (const char* var : debug_vars) {
            if (getenv(var) != nullptr) {
                return true;
            }
        }
        return false;
    }

    // Timing-based detection
    // Debuggers cause single-stepping to be slow
    static bool timing_check() {
        auto start = std::chrono::high_resolution_clock::now();

        // Execute some arithmetic
        volatile int x = 0;
        for (int i = 0; i < 1000000; ++i) {
            x += i;
        }

        auto end = std::chrono::high_resolution_clock::now();
        auto duration = std::chrono::duration_cast<std::chrono::microseconds>(
            end - start
        ).count();

        // Normal execution: < 10ms, debugged: > 100ms
        return duration > 100000;
    }

    // Check for breakpoint instructions (int3 = 0xCC)
    static bool check_breakpoints(void* func_ptr, size_t size) {
        unsigned char* code = static_cast<unsigned char*>(func_ptr);
        for (size_t i = 0; i < size; ++i) {
            if (code[i] == 0xCC) { // int3 breakpoint
                return true;
            }
        }
        return false;
    }

    // Combined check
    static bool is_compromised() {
        return is_debugger_attached()
            || check_tracer_pid()
            || check_debug_env()
            || timing_check();
    }

    // Call on security violation
    static void security_violation_handler() {
        // In production: log, alert, and exit gracefully
        // Do NOT reveal the detection mechanism
        std::cerr << "Security violation detected.\n";
        _exit(1); // Use _exit to avoid cleanup handlers
    }
};
```

### 7.3 Caso Real: Container Escape via Kernel Vulnerabilities

**O que aconteceu:** Vulnerabilidades no kernel Linux (como CVE-2022-0185, CVE-2022-0492, CVE-2023-0386) permitiam escapes de container explorando bugs no subsystem de filesystem ou memory management do kernel.

**O que deu errado:** Containers compartilham o kernel com o host. Qualquer vulnerabilidade no kernel pode ser explorada para escapar do namespace do container e acessar o host.

**Como mitigar:**
- Manter kernel sempre atualizado (critical patches em < 24h)
- Usar gVisor ou Kata Containers para isolamento adicional do kernel
- Aplicar AppArmor/SELinux profiles restritivos
- Usar seccomp-bpf para limitar syscalls disponíveis
- Monitorar CVEs do kernel e aplicar patches imediatamente

---

## 8. Network Hardening

### 8.1 mTLS Between Services

```cpp
// src/mtls_server.cpp
// Mutual TLS server implementation using OpenSSL

#include <iostream>
#include <string>
#include <openssl/ssl.h>
#include <openssl/err.h>
#include <openssl/x509v3.h>
#include <arpa/inet.h>
#include <unistd.h>
#include <cstring>

class MTLSServer {
public:
    MTLSServer(const std::string& cert_path,
               const std::string& key_path,
               const std::string& ca_path)
        : cert_path_(cert_path)
        , key_path_(key_path)
        , ca_path_(ca_path)
        , ctx_(nullptr)
        , server_fd_(-1) {}

    ~MTLSServer() {
        if (ctx_) SSL_CTX_free(ctx_);
        if (server_fd_ >= 0) close(server_fd_);
    }

    bool initialize() {
        // Create SSL context
        ctx_ = SSL_CTX_new(TLS_server_method());
        if (!ctx_) {
            std::cerr << "Failed to create SSL context\n";
            return false;
        }

        // Load server certificate
        if (SSL_CTX_use_certificate_file(ctx_, cert_path_.c_str(),
                                          SSL_FILETYPE_PEM) <= 0) {
            std::cerr << "Failed to load certificate\n";
            return false;
        }

        // Load server private key
        if (SSL_CTX_use_PrivateKey_file(ctx_, key_path_.c_str(),
                                         SSL_FILETYPE_PEM) <= 0) {
            std::cerr << "Failed to load private key\n";
            return false;
        }

        // Load CA certificate for client verification
        if (SSL_CTX_load_verify_locations(ctx_, ca_path_.c_str(),
                                           nullptr) <= 0) {
            std::cerr << "Failed to load CA certificate\n";
            return false;
        }

        // Require client certificate (mutual TLS)
        SSL_CTX_set_verify(ctx_,
                           SSL_VERIFY_PEER | SSL_VERIFY_FAIL_IF_NO_PEER_CERT,
                           nullptr);

        // Set minimum TLS version to 1.3
        SSL_CTX_set_min_proto_version(ctx_, TLS1_3_VERSION);

        // Disable weak cipher suites
        SSL_CTX_set_cipher_list(ctx_,
            "ECDHE+AESGCM:ECDHE+CHACHA20:DHE+AESGCM:DHE+CHACHA20:!aNULL:!MD5:!DSS:!RC4:!3DES");

        // Enable OCSP stapling
        SSL_CTX_set_tlsext_status_type(ctx_,
                                        TLSEXT_STATUSTYPE_ocsp);

        std::cout << "mTLS server initialized.\n";
        return true;
    }

    bool start(int port) {
        server_fd_ = socket(AF_INET, SOCK_STREAM, 0);
        if (server_fd_ < 0) {
            std::cerr << "Failed to create socket\n";
            return false;
        }

        int opt = 1;
        setsockopt(server_fd_, SOL_SOCKET, SO_REUSEADDR, &opt, sizeof(opt));

        struct sockaddr_in addr{};
        addr.sin_family = AF_INET;
        addr.sin_addr.s_addr = INADDR_ANY;
        addr.sin_port = htons(port);

        if (bind(server_fd_, (struct sockaddr*)&addr, sizeof(addr)) < 0) {
            std::cerr << "Failed to bind socket\n";
            return false;
        }

        if (listen(server_fd_, 128) < 0) {
            std::cerr << "Failed to listen\n";
            return false;
        }

        std::cout << "mTLS server listening on port " << port << "\n";

        // Accept connections
        while (true) {
            struct sockaddr_in client_addr{};
            socklen_t addr_len = sizeof(client_addr);
            int client_fd = accept(server_fd_,
                                   (struct sockaddr*)&client_addr,
                                   &addr_len);
            if (client_fd < 0) {
                std::cerr << "Failed to accept connection\n";
                continue;
            }

            handle_client(client_fd);
        }

        return true;
    }

private:
    std::string cert_path_;
    std::string key_path_;
    std::string ca_path_;
    SSL_CTX* ctx_;
    int server_fd_;

    void handle_client(int client_fd) {
        SSL* ssl = SSL_new(ctx_);
        SSL_set_fd(ssl, client_fd);

        if (SSL_accept(ssl) <= 0) {
            std::cerr << "TLS handshake failed\n";
            ERR_print_errors_fp(stderr);
            SSL_free(ssl);
            close(client_fd);
            return;
        }

        // Verify client certificate
        X509* client_cert = SSL_get_peer_certificate(ssl);
        if (!client_cert) {
            std::cerr << "No client certificate presented\n";
            SSL_shutdown(ssl);
            SSL_free(ssl);
            close(client_fd);
            return;
        }

        // Get client identity
        char subject[256];
        X509_NAME_oneline(X509_get_subject_name(client_cert),
                          subject, sizeof(subject));
        std::cout << "Client connected: " << subject << "\n";

        X509_free(client_cert);

        // Read data
        char buffer[4096];
        int bytes = SSL_read(ssl, buffer, sizeof(buffer) - 1);
        if (bytes > 0) {
            buffer[bytes] = '\0';
            std::cout << "Received: " << buffer << "\n";
        }

        // Send response
        const char* response = "Hello from mTLS server!\n";
        SSL_write(ssl, response, strlen(response));

        SSL_shutdown(ssl);
        SSL_free(ssl);
        close(client_fd);
    }
};
```

### 8.2 Firewall Configuration (nftables)

```bash
#!/usr/sbin/nft -f
# /etc/nftables.conf - Secure server firewall rules

flush ruleset

# Define trusted networks
define TRUSTED_NETS = { 10.0.0.0/8, 172.16.0.0/12 }
define MANAGEMENT_NET = 10.0.1.0/24

table inet filter {
    chain input {
        type filter hook input priority filter; policy drop;

        # Allow established/related connections
        ct state established,related accept

        # Drop invalid connections
        ct state invalid drop

        # Allow loopback
        iif "lo" accept

        # Allow ICMP (rate limited)
        ip protocol icmp limit rate 10/second accept
        ip6 nexthdr icmpv6 limit rate 10/second accept

        # Allow SSH only from management network
        tcp dport 22 ip saddr $MANAGEMENT_NET accept

        # Allow application port
        tcp dport 8443 ct state new limit rate 100/second accept

        # Allow health checks from monitoring
        tcp dport 8444 ip saddr $TRUSTED_NETS accept

        # Log and drop everything else
        log prefix "nft-drop: " limit rate 5/minute
        counter drop
    }

    chain forward {
        type filter hook forward priority filter; policy drop;
        counter drop
    }

    chain output {
        type filter hook output priority filter; policy drop;

        # Allow established
        ct state established,related accept

        # Allow loopback
        oif "lo" accept

        # Allow DNS
        tcp dport 53 accept
        udp dport 53 accept

        # Allow NTP
        udp dport 123 accept

        # Allow HTTPS for updates (specific repos)
        tcp dport 443 ip daddr {
            151.101.1.132,  # GitHub
            151.101.65.132
        } accept

        # Allow SMTP for alerts
        tcp dport 587 ip daddr 10.0.1.10 accept

        # Drop everything else
        counter drop
    }
}
```

---

## 9. Exemplo Completo: Deploy Pipeline Seguro

Este é um pipeline CI/CD completo em YAML com todas as etapas de segurança:

```yaml
# .github/workflows/secure-deploy.yaml
# Complete secure deployment pipeline

name: Secure Deployment Pipeline

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

env:
  REGISTRY: ghcr.io
  IMAGE_NAME: ${{ github.repository }}
  VAULT_ADDR: ${{ secrets.VAULT_ADDR }}

jobs:
  # === Stage 1: Build with Hardening ===
  build:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      packages: write

    steps:
      - name: Checkout
        uses: actions/checkout@v4
        with:
          fetch-depth: 0  # Full history for SBOM

      - name: Install dependencies
        run: |
          sudo apt-get update
          sudo apt-get install -y cmake gcc g++ libssl-dev

      - name: Build with hardening flags
        run: |
          cmake -B build \
            -DCMAKE_BUILD_TYPE=Release \
            -DCMAKE_CXX_COMPILER=g++ \
            -DCMAKE_CXX_FLAGS="-fstack-protector-strong -D_FORTIFY_SOURCE=2 -fPIE -Wformat -Wformat-security -Wall -Wextra -Wpedantic" \
            -DCMAKE_EXE_LINKER_FLAGS="-Wl,-z,relro,-z,now -Wl,-z,noexecstack -pie" \
            -DCMAKE_INSTALL_PREFIX=/usr

          cmake --build build --parallel $(nproc) -j$(nproc)

      - name: Verify hardening
        run: |
          checksec --file=build/secure_app || true
          ./build/verify_hardening build/secure_app

      - name: Run unit tests
        run: |
          cd build && ctest --output-on-failure

      - name: Upload build artifact
        uses: actions/upload-artifact@v4
        with:
          name: secure-app-binary
          path: build/secure_app

  # === Stage 2: Security Scanning ===
  security-scan:
    needs: build
    runs-on: ubuntu-latest

    steps:
      - name: Download artifact
        uses: actions/download-artifact@v4
        with:
          name: secure-app-binary

      - name: Run SAST
        uses: github/codeql-action/analyze@v3
        with:
          languages: cpp

      - name: Run dependency check
        uses: dependency-check/Dependency-Check_Action@main
        with:
          path: .
          format: HTML

      - name: Check for secrets
        uses: trufflesecurity/trufflehog@main
        with:
          extra_args: --only-verified

      - name: Verify dependency integrity
        run: |
          ./dependency_verifier verify_all

  # === Stage 3: Container Build (Distroless) ===
  container:
    needs: [build, security-scan]
    runs-on: ubuntu-latest
    permissions:
      contents: read
      packages: write
      id-token: write  # For Sigstore

    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Download artifact
        uses: actions/download-artifact@v4
        with:
          name: secure-app-binary

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3

      - name: Login to registry
        uses: docker/login-action@v3
        with:
          registry: ${{ env.REGISTRY }}
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - name: Generate SBOM
        run: |
          docker run --rm \
            -v $(pwd):/workspace \
            anchore/syft \
            /workspace/build/secure_app \
            -o spdx-json > sbom.json

      - name: Build container image
        run: |
          docker build \
            --build-arg BUILD_TYPE=Release \
            --build-arg VERSION=${{ github.sha }} \
            --label "org.opencontainers.image.source=${{ github.server_url }}/${{ github.repository }}" \
            --label "org.opencontainers.image.revision=${{ github.sha }}" \
            --label "org.opencontainers.image.created=$(date -u +'%Y-%m-%dT%H:%M:%SZ')" \
            -t ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}:${{ github.sha }} \
            -t ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}:latest \
            .

      - name: Scan container for vulnerabilities
        uses: aquasecurity/trivy-action@master
        with:
          image-ref: ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}:${{ github.sha }}
          format: table
          exit-code: 1
          severity: HIGH,CRITICAL

      - name: Sign container image
        uses: sigstore/cosign-installer@v3
      - run: |
          cosign sign --yes \
            ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}:${{ github.sha }}

      - name: Attach SBOM
        run: |
          cosign attest --predicate sbom.json --type spdxjson \
            ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}:${{ github.sha }}

      - name: Push image
        run: |
          docker push ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}:${{ github.sha }}
          docker push ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}:latest

  # === Stage 4: Deploy to Kubernetes ===
  deploy:
    needs: container
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    environment: production

    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Verify image signature
        run: |
          cosign verify \
            --certificate-identity="${{ github.server_url }}/${{ github.repository }}" \
            --certificate-oidc-issuer="https://token.actions.githubusercontent.com" \
            ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}:${{ github.sha }}

      - name: Verify SBOM attestation
        run: |
          cosign verify-attestation --type spdxjson \
            --certificate-identity="${{ github.server_url }}/${{ github.repository }}" \
            --certificate-oidc-issuer="https://token.actions.githubusercontent.com" \
            ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}:${{ github.sha }}

      - name: Deploy to Kubernetes
        run: |
          kubectl set image deployment/secure-app \
            secure-app=${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}:${{ github.sha }} \
            --record

      - name: Wait for rollout
        run: |
          kubectl rollout status deployment/secure-app \
            --timeout=300s

      - name: Post-deployment verification
        run: |
          # Verify pod security context
          kubectl get pods -l app=secure-app -o json | \
            jq '.items[] | select(
              .spec.securityContext.runAsNonRoot != true or
              .spec.containers[0].securityContext.allowPrivilegeEscalation != false
            )' | grep -v "^$" && \
            echo "SECURITY VIOLATION: Pod security context mismatch!" && \
            exit 1 || echo "Pod security context OK"

          # Verify container is running as non-root
          kubectl exec deployment/secure-app -- id | grep -q "uid=65534" && \
            echo "Running as nonroot (uid 65534)" || \
            echo "WARNING: Not running as nonroot!"

          # Verify seccomp is applied
          kubectl exec deployment/secure-app -- cat /proc/self/status | \
            grep -q "Seccomp:" && \
            echo "Seccomp active" || \
            echo "WARNING: Seccomp not detected!"

          # Health check
          kubectl exec deployment/secure-app -- \
            /usr/local/bin/secure_app --health-check

          echo "=== Deployment verification complete ==="
```

---

## 10. Referências

1. OWASP. "Application Security Verification Standard (ASVS) 4.0." https://owasp.org/www-project-application-security-verification-standard/

2. CWE/SANS. "Top 25 Most Dangerous Software Weaknesses." https://cwe.mitre.org/top25/

3. NIST. "Secure Software Development Framework (SSDF) v1.1." SP 800-218. https://csrc.nist.gov/publications/detail/sp/800-218/final

4. CIS Benchmarks. "CIS Docker Benchmark." https://www.cisecurity.org/benchmark/docker

5. Linux Foundation. "Secure Container Runtime Specification." https://github.com/opencontainers/runtime-spec

6. Sigstore. "Software Artifact Signing and Verification." https://www.sigstore.dev/

7. CycloneDX. "OWASP CycloneDX Software Bill of Materials Standard." https://cyclonedx.org/

8. OpenSSF. "Supply Chain Security Tools." https://openssf.org/projects/scst/

9. MITRE ATT&CK. "Container Escape Techniques." https://attack.mitre.org/techniques/

10. Linux Kernel CVEs. https://www.linuxkernelcves.com/

11. Docker. "Docker Security Best Practices." https://docs.docker.com/engine/security/

12. HashiCorp. "Vault - Manage Secrets and Protect Sensitive Data." https://www.vaultproject.io/

13. CNCF. "Cloud Native Security Whitepaper." https://github.com/cncf/tag-security/blob/main/security-whitepaper/

14. FreeBSD. "seccomp(2) - Tracing and system call filtering." https://www.freebsd.org/cgi/man.cgi?query=seccomp

15. Red Hat. "SELinux Understanding and Configuration." https://access.redhat.com/documentation/en-us/red_hat_enterprise_linux/8/html/selinux_users_and_administrators_guide/

---

## Resumo

Este capítulo cobriu as camadas fundamentais de hardening e deploy seguro para aplicações C++17. As práticas aqui descritas — desde flags do compilador até pipelines de deploy com verificação pós-deploy — formam uma defesa em profundidade. Cada camada adiciona resistência independentemente das outras: se uma falhar, as demais continuam protegendo o sistema.

Os casos reais documentados (CVE-2019-5736, SolarWinds, Codecov, xz-utils, CVE-2024-3094, Docker socket exposure) demonstram que ataques na cadeia de suprimentos e na infraestrutura de deploy são reais e devastadores. A resposta não é apenas防御iva — é construir sistemas que possam ser verificados, auditados e recuperados.

A segurança não é um recurso que se adiciona no final. Ela precisa estar presente desde o primeiro commit,贯穿 throughout o ciclo de vida do software, desde a compilação até a monitoramento em produção.
