# Capítulo 7: Sandboxing e Isolamento

## 7.1 Introdução ao Sandboxing

Sandboxing é uma técnica fundamental de segurança que consiste em executar código em um ambiente restrito, isolado do sistema operacional host e de outros processos. O objetivo é limitar o impacto potencial de código malicioso ou com falhas, garantindo que danos permaneçam confinados dentro do sandbox.

No contexto de WebAssembly, o sandboxing assume uma importância redobrada. O modelo de segurança do Wasm é construído sobre o princípio de menor privilégio, onde módulos Wasm não possuem acesso direto a recursos do sistema operacional. Todo acesso a I/O, rede, sistema de arquivos ou outros recursos deve ser concedido explicitamente através de interfaces definidas.

### 7.1.1 Princípios Fundamentais de Sandboxing

O sandboxing eficaz segue vários princípios fundamentais que devem ser compreendidos antes de mergulharmos nas implementações específicas:

**Isolamento de processos**: Cada componente executável deve rodar em seu próprio processo isolado, com memória e estado separados. Isso previne que uma falha em um componente afete outros componentes ou o sistema host.

**Menor privilégio**: Cada processo ou componente deve receber apenas os privilégios mínimos necessários para realizar sua função. Se um componente não precisa de acesso à rede, ele não deve tê-lo.

**Defesa em profundidade**: Múltiplas camadas de segurança devem ser empregadas. Se uma camada falhar, outras camadas continuam protegendo o sistema.

**Reproutabilidade**: O ambiente de execução deve ser determinístico, permitindo que o mesmo código produza os mesmos resultados em diferentes execuções.

**Auditoria e observabilidade**: Todas as ações dentro do sandbox devem ser logadas e auditáveis, permitindo detecção de comportamento suspeito.

### 7.1.2 Níveis de Sandboxing

O sandboxing pode ser implementado em diferentes níveis de abstração, cada um oferecendo diferentes trade-offs entre segurança, performance e flexibilidade:

**Nível de linguagem**: Restrições impostas pelo compilador e runtime da linguagem. Exemplos incluem type checking em JavaScript, borrow checking em Rust, e o modelo de memória linear do Wasm.

**Nível de sistema operacional**: Utilização de recursos do kernel para isolar processos. Inclui namespaces, seccomp-bpf, cgroups, e ptrace.

**Nível de hipervisor**: Isolamento via virtualização de hardware. Inclui máquinas virtuais completas e microVMs como Firecracker.

**Nível de hardware**: Utilização de extensões de hardware como Intel SGX, ARM TrustZone, ou AMD SEV para criar enclaves protegidos.

## 7.2 Modelos de Isolamento de Processos

### 7.2.1 Isolamento Clássico com fork()

O modelo clássico de isolamento de processos no Unix utiliza a chamada `fork()` para criar cópias de processos. Cada processo filho recebe uma cópia do espaço de memória do processo pai, garantindo isolamento natural.

```c
#include <stdio.h>
#include <unistd.h>
#include <sys/wait.h>

int main() {
    pid_t pid = fork();
    
    if (pid == 0) {
        // Processo filho - sandbox
        printf("Processo filho PID: %d\n", getpid());
        printf("Processo pai PID: %d\n", getppid());
        
        // Executar código potencialmente inseguro
        execlp("/usr/bin/untrusted-program", "untrusted-program", NULL);
        
        perror("execlp falhou");
        return 1;
    } else if (pid > 0) {
        // Processo pai - monitor
        int status;
        waitpid(pid, &status, 0);
        
        if (WIFEXITED(status)) {
            printf("Processo filho terminou com código %d\n", 
                   WEXITSTATUS(status));
        }
    } else {
        perror("fork falhou");
        return 1;
    }
    
    return 0;
}
```

O isolamento via `fork()` oferece separação de memória, mas não restringe acesso a recursos do sistema como arquivos, rede ou dispositivos. Para um sandbox completo, é necessário combinar com outras técnicas.

### 7.2.2 chroot e jails

O `chroot` muda o diretório raiz de um processo, criando uma árvore de arquivos isolada. O processo não pode acessar arquivos fora de seu diretório raiz modificado.

```bash
# Criar estrutura de diretório para jail
mkdir -p /var/jail/{bin,lib,lib64,dev,etc,usr}
mkdir -p /var/jail/usr/{bin,lib}

# Copiar binários necessários
cp /bin/sh /var/jail/bin/
cp /bin/ls /var/jail/bin/

# Copiar bibliotecas necessárias
ldd /bin/sh | grep -o '/lib.*\.so\.[0-9]*' | while read lib; do
    dir=$(dirname "$lib")
    mkdir -p "/var/jail$dir"
    cp "$lib" "/var/jail$lib"
done

# Criar dispositivos básicos
mknod /var/jail/dev/null c 1 3
mknod /var/jail/dev/zero c 1 5
mknod /var/jail/dev/random c 1 8
mknod /var/jail/dev/urandom c 1 9
```

O FreeBSD implementa jails, que são uma evolução do chroot, adicionando isolamento de rede, processos e usuários:

```bash
# Configurar uma jail no FreeBSD
jail -c path=/var/jail/myjail \
     host.hostname=myjail \
     ip4=192.168.1.100 \
     allow.sysctl=false \
     allow.chflags=false \
     securelevel=3
```

### 7.2.3 Containers Linux

Containers modernos combinam múltiplos mecanismos de isolamento do Linux para criar ambientes virtualizados leves:

```c
#define _GNU_SOURCE
#include <sched.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <sys/mount.h>
#include <sys/wait.h>
#include <sys/types.h>
#include <fcntl.h>
#include <errno.h>

#define STACK_SIZE (1024 * 1024)

static char child_stack[STACK_SIZE];

typedef struct {
    char *hostname;
    char *rootfs;
    int uid_map;
    int enable_network;
} ContainerConfig;

static int child_main(void *arg) {
    ContainerConfig *config = (ContainerConfig *)arg;
    
    // Configurar hostname
    if (sethostname(config->hostname, strlen(config->hostname)) != 0) {
        perror("sethostname");
        return 1;
    }
    
    // Montar /proc
    if (mount("proc", "/proc", "proc", 0, NULL) != 0) {
        perror("mount proc");
        return 1;
    }
    
    // Montar tmpfs em /tmp
    if (mount("tmpfs", "/tmp", "tmpfs", 0, "size=100M") != 0) {
        perror("mount tmpfs");
        return 1;
    }
    
    // Criar diretórios essenciais
    mkdir("/dev", 0755);
    mkdir("/proc", 0755);
    mkdir("/sys", 0755);
    
    // Montar /dev com dispositivos básicos
    mount("tmpfs", "/dev", "tmpfs", 0, "size=10M,mode=0755");
    
    // Executar shell na jail
    execlp("/bin/sh", "/bin/sh", NULL);
    perror("execlp");
    return 1;
}

int main() {
    ContainerConfig config = {
        .hostname = "container-sandbox",
        .rootfs = "/var/container/rootfs",
        .enable_network = 0
    };
    
    // Criar novo namespace de PID e mount
    int flags = CLONE_NEWPID | CLONE_NEWNS | CLONE_NEWUTS;
    
    pid_t pid = clone(child_main, 
                      child_stack + STACK_SIZE,
                      flags | SIGCHLD, 
                      &config);
    
    if (pid == -1) {
        perror("clone");
        return 1;
    }
    
    printf("Container PID: %d\n", pid);
    
    int status;
    waitpid(pid, &status, 0);
    
    if (WIFEXITED(status)) {
        printf("Container terminou com código %d\n", WEXITSTATUS(status));
    }
    
    return 0;
}
```

## 7.3 Linux Namespaces

Namespaces são um mecanismo do kernel Linux que isola recursos do sistema para diferentes processos. Cada namespace encapsula um recurso global de modo que apenas processos que fazem parte do namespace podem ver ou acessar o recurso.

### 7.3.1 Tipos de Namespaces

O Linux suporta vários tipos de namespaces, cada um isolando um conjunto diferente de recursos:

**PID Namespace**: Isola o espaço de nomes de processos. Processos em um namespace PID não podem ver processos em outros namespaces.

```c
#define _GNU_SOURCE
#include <sched.h>
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <sys/wait.h>
#include <sys/mount.h>
#include <signal.h>

#define STACK_SIZE (1024 * 1024)
static char child_stack[STACK_SIZE];

static int child_fn(void *arg) {
    printf("Filho: PID = %d\n", getpid());
    printf("Filho: PPID = %d\n", getppid());
    
    // Listar processos visíveis
    printf("Filho: Listando processos:\n");
    system("ps aux");
    
    // Executar shell para exploração interativa
    execlp("/bin/sh", "/bin/sh", NULL);
    perror("execlp");
    return 1;
}

int main() {
    printf("Pai: PID = %d\n", getpid());
    
    // Criar novo PID namespace
    pid_t pid = clone(child_fn, 
                      child_stack + STACK_SIZE,
                      CLONE_NEWPID | SIGCHLD, 
                      NULL);
    
    if (pid == -1) {
        perror("clone");
        return 1;
    }
    
    printf("Pai: Filho criado com PID %d\n", pid);
    
    int status;
    waitpid(pid, &status, 0);
    
    return 0;
}
```

**Mount Namespace**: Isola o ponto de montagem, permitindo que cada namespace tenha sua própria árvore de sistemas de arquivos.

```c
#define _GNU_SOURCE
#include <sched.h>
#include <stdio.h>
#include <unistd.h>
#include <sys/mount.h>
#include <sys/wait.h>
#include <fcntl.h>

#define STACK_SIZE (1024 * 1024)
static char child_stack[STACK_SIZE];

static int child_fn(void *arg) {
    // Montar um novo filesystem tmpfs
    mkdir("/tmp/sandbox", 0755);
    mount("tmpfs", "/tmp/sandbox", "tmpfs", 0, "size=50M");
    
    // Criar estrutura de diretório isolada
    mkdir("/tmp/sandbox/usr", 0755);
    mkdir("/tmp/sandbox/bin", 0755);
    mkdir("/tmp/sandbox/lib", 0755);
    mkdir("/tmp/sandbox/tmp", 0755);
    
    // Mover para dentro do sandbox
    chroot("/tmp/sandbox");
    chdir("/");
    
    printf("Dentro do mount namespace isolado:\n");
    system("ls -la /");
    
    execlp("/bin/sh", "/bin/sh", NULL);
    perror("execlp");
    return 1;
}

int main() {
    pid_t pid = clone(child_fn, 
                      child_stack + STACK_SIZE,
                      CLONE_NEWNS | SIGCHLD, 
                      NULL);
    
    if (pid == -1) {
        perror("clone");
        return 1;
    }
    
    int status;
    waitpid(pid, &status, 0);
    return 0;
}
```

**Network Namespace**: Fornece isolamento completo da pilha de rede, incluindo interfaces de rede, tabelas de roteamento, firewalls e sockets.

```bash
# Criar um network namespace
ip netns add sandbox

# Criar um par de interfaces virtual
ip link add veth0 type veth peer name veth1

# Mover uma interface para o namespace
ip link set veth1 netns sandbox

# Configurar interfaces
ip addr add 10.0.0.1/24 dev veth0
ip link set veth0 up

ip netns exec sandbox ip addr add 10.0.0.2/24 dev veth1
ip netns exec sandbox ip link set veth1 up
ip netns exec sandbox ip link set lo up

# Testar conectividade
ping -c 3 10.0.0.2

# Configurar NAT para acesso à internet a partir do namespace
echo 1 > /proc/sys/net/ipv4/ip_forward
iptables -t nat -A POSTROUTING -s 10.0.0.0/24 -o eth0 -j MASQUERADE
iptables -A FORWARD -i veth0 -o eth0 -j ACCEPT
iptables -A FORWARD -i eth0 -o veth0 -m state --state RELATED,ESTABLISHED -j ACCEPT
```

**User Namespace**: Mapeia UIDs e GIDs entre namespaces, permitindo que um processo tenha privilégios elevados dentro do namespace sem tê-los no host.

```c
#define _GNU_SOURCE
#include <sched.h>
#include <stdio.h>
#include <unistd.h>
#include <sys/wait.h>
#include <sys/types.h>

#define STACK_SIZE (1024 * 1024)
static char child_stack[STACK_SIZE];

static int child_fn(void *arg) {
    printf("Filho: UID = %d, GID = %d\n", getuid(), getgid());
    printf("Filho: EUID = %d, EGID = %d\n", geteuid(), getegid());
    
    // Verificar mapeamento
    uid_t mappings[2];
    gid_t g_mappings[2];
    
    // Mapear root no namespace para usuário real no host
    mappings[0] = 0; // UID dentro do namespace
    mappings[1] = getuid(); // UID no host
    
    g_mappings[0] = 0;
    g_mappings[1] = getgid();
    
    // Verificar se pode executar operações de root
    if (setuid(0) == 0) {
        printf("Filho: Executando como root dentro do namespace\n");
        printf("Filho: Host UID real: %d\n", getuid());
    }
    
    return 0;
}

int main() {
    printf("Pai: UID = %d, GID = %d\n", getuid(), getgid());
    
    pid_t pid = clone(child_fn, 
                      child_stack + STACK_SIZE,
                      CLONE_NEWUSER | SIGCHLD, 
                      NULL);
    
    if (pid == -1) {
        perror("clone");
        return 1;
    }
    
    int status;
    waitpid(pid, &status, 0);
    return 0;
}
```

**UTS Namespace**: Isola identificadores de sistema (hostname e domínio NIS).

**IPC Namespace**: Isola recursos de comunicação entre processos (semáforos, message queues, shared memory).

**Cgroup Namespace**: Isola a visão de cgroups de um processo.

### 7.3.2 Combinação de Namespaces

A verdadeira potência dos namespaces vem de combiná-los para criar ambientes totalmente isolados:

```c
#define _GNU_SOURCE
#include <sched.h>
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <sys/mount.h>
#include <sys/wait.h>
#include <sys/stat.h>
#include <fcntl.h>
#include <string.h>

#define STACK_SIZE (1024 * 1024)
static char child_stack[STACK_SIZE];

static void setup_mounts() {
    // Tornar mount propagation private
    mount(NULL, "/", NULL, MS_PRIVATE | MS_REC, NULL);
    
    // Montar /proc
    mkdir("/proc", 0555);
    mount("proc", "/proc", "proc", 0, NULL);
    
    // Montar /sys somente leitura
    mkdir("/sys", 0555);
    mount("sysfs", "/sys", "sysfs", MS_RDONLY, NULL);
    
    // Montar tmpfs para /tmp
    mkdir("/tmp", 01777);
    mount("tmpfs", "/tmp", "tmpfs", 0, "size=100M");
    
    // Montar tmpfs para /dev
    mkdir("/dev", 0755);
    mount("tmpfs", "/dev", "tmpfs", 0, "size=10M,mode=0755");
    
    // Criar dispositivos básicos
    mknod("/dev/null", 0666 | S_IFCHR, makedev(1, 3));
    mknod("/dev/zero", 0666 | S_IFCHR, makedev(1, 5));
    mknod("/dev/random", 0666 | S_IFCHR, makedev(1, 8));
    mknod("/dev/urandom", 0666 | S_IFCHR, makedev(1, 9));
    mknod("/dev/tty", 0666 | S_IFCHR, makedev(5, 0));
}

static int child_fn(void *arg) {
    printf("PID namespace isolado: PID = %d\n", getpid());
    
    // Configurar mounts isolados
    setup_mounts();
    
    // Executar shell
    printf("Ambiente isolado configurado. Executando shell...\n");
    execlp("/bin/sh", "/bin/sh", NULL);
    perror("execlp");
    return 1;
}

int main() {
    // Combinar todos os namespaces para isolamento máximo
    int flags = CLONE_NEWPID |    // Isolar PIDs
                CLONE_NEWNS |     // Isolar mounts
                CLONE_NEWUTS |    // Isolar hostname
                CLONE_NEWIPC |    // Isolar IPC
                CLONE_NEWUSER |   // Isolar users
                CLONE_NEWNET |    // Isolar rede
                SIGCHLD;
    
    pid_t pid = clone(child_fn, 
                      child_stack + STACK_SIZE,
                      flags, 
                      NULL);
    
    if (pid == -1) {
        perror("clone");
        return 1;
    }
    
    int status;
    waitpid(pid, &status, 0);
    
    printf("Container finalizado\n");
    return 0;
}
```

## 7.4 seccomp-bpf

seccomp-bpf (Secure Computing mode com Berkeley Packet Filter) permite que processos filtrem quais chamadas de sistema podem ser executadas. É uma das ferramentas mais poderosas para sandboxing no Linux.

### 7.4.1 Fundamentos do seccomp

O seccomp tem três modos principais:

**SECCOMP_MODE_STRICT**: Restringe o processo a apenas quatro chamadas de sistema: `read()`, `write()`, `exit()` e `sigreturn()`.

**SECCOMP_MODE_FILTER**: Permite filtros BPF personalizados que examinam cada chamada de sistema.

**SECCOMP_MODE_SYNC_USER_RCU**: Modo avançado para filters que precisam de sincronização entre threads.

### 7.4.2 Criação de Filtros BPF

```c
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <seccomp.h>
#include <sys/prctl.h>

int main() {
    // Criar contexto do seccomp
    scmp_filter_ctx ctx = seccomp_init(SCMP_ACT_KILL);
    if (ctx == NULL) {
        perror("seccomp_init");
        return 1;
    }
    
    // Permitir chamadas de sistema essenciais
    seccomp_rule_add(ctx, SCMP_ACT_ALLOW, SCMP_SYS(read), 0);
    seccomp_rule_add(ctx, SCMP_ACT_ALLOW, SCMP_SYS(write), 0);
    seccomp_rule_add(ctx, SCMP_ACT_ALLOW, SCMP_SYS(exit), 0);
    seccomp_rule_add(ctx, SCMP_ACT_ALLOW, SCMP_SYS(exit_group), 0);
    seccomp_rule_add(ctx, SCMP_ACT_ALLOW, SCMP_SYS(sigreturn), 0);
    seccomp_rule_add(ctx, SCMP_ACT_ALLOW, SCMP_SYS(brk), 0);
    seccomp_rule_add(ctx, SCMP_ACT_ALLOW, SCMP_SYS(mmap), 0);
    seccomp_rule_add(ctx, SCMP_ACT_ALLOW, SCMP_SYS(munmap), 0);
    seccomp_rule_add(ctx, SCMP_ACT_ALLOW, SCMP_SYS(mprotect), 0);
    
    // Bloquear chamadas perigosas
    // seccomp_rule_add(ctx, SCMP_ACT_KILL, SCMP_SYS(execve), 0);
    // seccomp_rule_add(ctx, SCMP_ACT_KILL, SCMP_SYS(fork), 0);
    // seccomp_rule_add(ctx, SCMP_ACT_KILL, SCMP_SYS(connect), 0);
    // seccomp_rule_add(ctx, SCMP_ACT_KILL, SCMP_SYS(bind), 0);
    // seccomp_rule_add(ctx, SCMP_ACT_KILL, SCMP_SYS(listen), 0);
    
    // Carregar o filtro
    if (seccomp_load(ctx) != 0) {
        perror("seccomp_load");
        seccomp_release(ctx);
        return 1;
    }
    
    // Liberar o contexto
    seccomp_release(ctx);
    
    printf("Filtro seccomp carregado com sucesso\n");
    
    // Código aqui só pode executar chamadas permitidas
    char buf[] = "Teste de sandbox\n";
    write(1, buf, sizeof(buf) - 1);
    
    return 0;
}
```

### 7.4.3 Filtros Complexos com Argumentos

```c
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <seccomp.h>
#include <fcntl.h>
#include <errno.h>

int setup_file_access_filter(scmp_filter_ctx ctx) {
    // Permitir open apenas para leitura em diretórios específicos
    seccomp_rule_add(ctx, SCMP_ACT_ALLOW, SCMP_SYS(open), 1,
        SCMP_A0(SCMP_CMP_EQ, (scmp_datum_t)"/safe/input.txt"));
    
    // Permitir open com O_RDONLY
    seccomp_rule_add(ctx, SCMP_ACT_ALLOW, SCMP_SYS(openat), 1,
        SCMP_A1(SCMP_CMP_MASKED_EQ, O_RDONLY, O_RDONLY));
    
    // Bloquear open para escrita
    seccomp_rule_add(ctx, SCMP_ACT_ERRNO(EROFS), SCMP_SYS(open), 1,
        SCMP_A1(SCMP_CMP_MASKED_EQ, O_WRONLY, O_WRONLY));
    
    seccomp_rule_add(ctx, SCMP_ACT_ERRNO(EROFS), SCMP_SYS(open), 1,
        SCMP_A1(SCMP_CMP_MASKED_EQ, O_RDWR, O_RDWR));
    
    // Permitir close
    seccomp_rule_add(ctx, SCMP_ACT_ALLOW, SCMP_SYS(close), 0);
    
    // Permitir read com tamanho máximo
    seccomp_rule_add(ctx, SCMP_ACT_ALLOW, SCMP_SYS(read), 1,
        SCMP_A2(SCMP_CMP_LE, 1024 * 1024)); // Máximo 1MB por read
    
    // Bloquear write em arquivo
    seccomp_rule_add(ctx, SCMP_ACT_ERRNO(EROFS), SCMP_SYS(write), 0);
    
    return 0;
}

int setup_network_filter(scmp_filter_ctx ctx) {
    // Bloquear todas as chamadas de rede
    seccomp_rule_add(ctx, SCMP_ACT_KILL, SCMP_SYS(socket), 0);
    seccomp_rule_add(ctx, SCMP_ACT_KILL, SCMP_SYS(connect), 0);
    seccomp_rule_add(ctx, SCMP_ACT_KILL, SCMP_SYS(bind), 0);
    seccomp_rule_add(ctx, SCMP_ACT_KILL, SCMP_SYS(listen), 0);
    seccomp_rule_add(ctx, SCMP_ACT_KILL, SCMP_SYS(accept), 0);
    seccomp_rule_add(ctx, SCMP_ACT_KILL, SCMP_SYS(sendto), 0);
    seccomp_rule_add(ctx, SCMP_ACT_KILL, SCMP_SYS(recvfrom), 0);
    seccomp_rule_add(ctx, SCMP_ACT_KILL, SCMP_SYS(sendmsg), 0);
    seccomp_rule_add(ctx, SCMP_ACT_KILL, SCMP_SYS(recvmsg), 0);
    
    return 0;
}

int setup_process_filter(scmp_filter_ctx ctx) {
    // Bloquear fork e exec
    seccomp_rule_add(ctx, SCMP_ACT_KILL, SCMP_SYS(fork), 0);
    seccomp_rule_add(ctx, SCMP_ACT_KILL, SCMP_SYS(vfork), 0);
    seccomp_rule_add(ctx, SCMP_ACT_KILL, SCMP_SYS(clone), 0);
    seccomp_rule_add(ctx, SCMP_ACT_KILL, SCMP_SYS(execve), 0);
    seccomp_rule_add(ctx, SCMP_ACT_KILL, SCMP_SYS(execveat), 0);
    
    // Bloquear ptrace
    seccomp_rule_add(ctx, SCMP_ACT_KILL, SCMP_SYS(ptrace), 0);
    
    // Bloquear modificações ao sistema
    seccomp_rule_add(ctx, SCMP_ACT_KILL, SCMP_SYS(reboot), 0);
    seccomp_rule_add(ctx, SCMP_ACT_KILL, SCMP_SYS(sethostname), 0);
    seccomp_rule_add(ctx, SCMP_ACT_KILL, SCMP_SYS(setdomainname), 0);
    
    return 0;
}

int main() {
    scmp_filter_ctx ctx = seccomp_init(SCMP_ACT_KILL);
    if (ctx == NULL) {
        perror("seccomp_init");
        return 1;
    }
    
    // Configurar filtros
    setup_file_access_filter(ctx);
    setup_network_filter(ctx);
    setup_process_filter(ctx);
    
    // Carregar filtro
    if (seccomp_load(ctx) != 0) {
        perror("seccomp_load");
        seccomp_release(ctx);
        return 1;
    }
    
    seccomp_release(ctx);
    
    printf("Filtros seccomp complexos carregados\n");
    
    // Testar: esta operação deve funcionar
    int fd = open("/safe/input.txt", O_RDONLY);
    if (fd >= 0) {
        char buf[1024];
        ssize_t n = read(fd, buf, sizeof(buf));
        close(fd);
        printf("Leu %zd bytes\n", n);
    }
    
    // Testar: esta operação deve falhar
    fd = open("/etc/passwd", O_RDONLY);
    if (fd < 0) {
        printf("Acesso negado corretamente para /etc/passwd\n");
    }
    
    return 0;
}
```

### 7.4.4 Integração com WebAssembly

O seccomp-bpf pode ser usado para proteger runtimes Wasm, restringindo as chamadas de sistema que o runtime pode fazer:

```c
#include <stdio.h>
#include <seccomp.h>

int setup_wasm_runtime_filter(scmp_filter_ctx ctx) {
    // Permitir chamadas essenciais para Wasm runtime
    seccomp_rule_add(ctx, SCMP_ACT_ALLOW, SCMP_SYS(read), 0);
    seccomp_rule_add(ctx, SCMP_ACT_ALLOW, SCMP_SYS(write), 0);
    seccomp_rule_add(ctx, SCMP_ACT_ALLOW, SCMP_SYS(close), 0);
    seccomp_rule_add(ctx, SCMP_ACT_ALLOW, SCMP_SYS(exit), 0);
    seccomp_rule_add(ctx, SCMP_ACT_ALLOW, SCMP_SYS(exit_group), 0);
    
    // Memória
    seccomp_rule_add(ctx, SCMP_ACT_ALLOW, SCMP_SYS(brk), 0);
    seccomp_rule_add(ctx, SCMP_ACT_ALLOW, SCMP_SYS(mmap), 0);
    seccomp_rule_add(ctx, SCMP_ACT_ALLOW, SCMP_SYS(munmap), 0);
    seccomp_rule_add(ctx, SCMP_ACT_ALLOW, SCMP_SYS(mprotect), 0);
    seccomp_rule_add(ctx, SCMP_ACT_ALLOW, SCMP_SYS(mremap), 0);
    
    // Clock para timers
    seccomp_rule_add(ctx, SCMP_ACT_ALLOW, SCMP_SYS(clock_gettime), 0);
    seccomp_rule_add(ctx, SCMP_ACT_ALLOW, SCMP_SYS(nanosleep), 0);
    seccomp_rule_add(ctx, SCMP_ACT_ALLOW, SCMP_SYS(clock_nanosleep), 0);
    
    // Arquivo limitado
    seccomp_rule_add(ctx, SCMP_ACT_ALLOW, SCMP_SYS(openat), 0);
    seccomp_rule_add(ctx, SCMP_ACT_ALLOW, SCMP_SYS(readlink), 0);
    seccomp_rule_add(ctx, SCMP_ACT_ALLOW, SCMP_SYS(fstat), 0);
    
    // Bloquear rede
    seccomp_rule_add(ctx, SCMP_ACT_KILL, SCMP_SYS(socket), 0);
    seccomp_rule_add(ctx, SCMP_ACT_KILL, SCMP_SYS(connect), 0);
    seccomp_rule_add(ctx, SCMP_ACT_KILL, SCMP_SYS(bind), 0);
    seccomp_rule_add(ctx, SCMP_ACT_KILL, SCMP_SYS(listen), 0);
    seccomp_rule_add(ctx, SCMP_ACT_KILL, SCMP_SYS(accept), 0);
    
    // Bloquear exec
    seccomp_rule_add(ctx, SCMP_ACT_KILL, SCMP_SYS(execve), 0);
    seccomp_rule_add(ctx, SCMP_ACT_KILL, SCMP_SYS(fork), 0);
    seccomp_rule_add(ctx, SCMP_ACT_KILL, SCMP_SYS(clone), 0);
    
    return 0;
}
```

## 7.5 gVisor

gVisor é um runtime de aplicação que implementa um sistema operacional de usuário em espaço de kernel, fornecendo isolamento sem a sobrecarga de uma VM completa. Ele intercepta chamadas de sistema do aplicativo e as implementa em user-space, usando ptrace ou KVM para interceptação.

### 7.5.1 Arquitetura do gVisor

O gVisor consiste em três componentes principais:

**Sentry**: Implementa a maioria das chamadas de sistema do Linux em Go. Atua como um kernel de usuário que isola o aplicativo do kernel real do host.

**Gofer**: Processo de proxy que fornece acesso ao sistema de arquivos host. O Sentry se comunica com o Gofer via 9P protocol.

**Runsc**: Runtime OCI que gerencia o ciclo de vida do container usando Sentry e Gofer.

```bash
# Instalar gVisor
curl -fsSL https://gvisor.dev/archive.key | gpg --dearmor -o /usr/share/keyrings/gvisor-archive-keyring.gpg
echo "deb [arch=amd64 signed-by=/usr/share/keyrings/gvisor-archive-keyring.gpg] https://storage.googleapis.com/gvisor/releases release main" | tee /etc/apt/sources.list.d/gvisor.list > /dev/null
apt update && apt install runsc

# Configurar Docker para usar gVisor
cat > /etc/docker/daemon.json << 'EOF'
{
    "runtimes": {
        "runsc": {
            "path": "/usr/bin/runsc"
        }
    }
}
EOF

systemctl restart docker

# Executar container com gVisor
docker run --runtime=runsc -it ubuntu bash

# Verificar isolamento
cat /proc/version  # Mostrará versão gVisor, não do kernel real
```

### 7.5.2 Executando Wasm com gVisor

```bash
# Criar Dockerfile para Wasm com gVisor
cat > Dockerfile.wasm << 'EOF'
FROM scratch

COPY target/wasm32-wasi/release/app.wasm /app.wasm

# Configurar ponto de entrada para Wasm
ENTRYPOINT ["/runsc", "exec", "--", "/wasmtime", "/app.wasm"]
EOF

# Construir e executar
docker build -t wasm-app-gvisor -f Dockerfile.wasm .
docker run --runtime=runsc wasm-app-gvisor
```

### 7.5.3 Configuração Avançada do gVisor

```bash
# Configurar gVisor com limites de recursos
cat > /etc/gvisor/runsc.yaml << 'EOF'
runsc:
  path: /usr/bin/runsc
  runtime-root: /run/containerd/runtime
  network: sandbox
  platform: systrap
  directfs: true
  
  # Limites de memória
  total-memory-limit: 1073741824  # 1GB
  
  # Limites de CPU
  cpu-quota: 50000
  cpu-period: 100000
  
  # Limites de I/O
  iops-read: 1000
  iops-write: 1000
  
  # Controle de acesso ao filesystem
  overlay2:
    enabled: true
    size: 10737418240  # 10GB
EOF
```

## 7.6 Firecracker microVMs

Firecracker é um VMM (Virtual Machine Monitor) leve, projetado para criar e gerenciar microVMs. Foi desenvolvido pela AWS para seus serviços serverless (Lambda e Fargate).

### 7.6.1 Arquitetura do Firecracker

O Firecracker fornece isolamento de VM com sobrecarga mínima:

- **Kernel Linux minimalista**: Apenas os subsistemas necessários
- **Device model simplificado**: Virtio-net, virtio-blk, serial console, keyboard
- **Sem BIOS**: Boot direto via ELF kernel
- **Snapshot/restore**: Suporte a snapshots rápidos para cold start

```bash
# Instalar Firecracker
curl -L -o firecracker https://github.com/firecracker-microvm/firecracker/releases/latest/download/firecracker-v$(uname -m)
chmod +x firecracker

# Criar rootfs mínimo
dd if=/dev/zero of=rootfs.ext4 bs=1M count=512
mkfs.ext4 rootfs.ext4
mkdir -p /mnt/rootfs
mount rootfs.ext4 /mnt/rootfs

# Instalar sistema mínimo
debootstrap --variant=minbase bullseye /mnt/rootfs

# Configurar init
cat > /mnt/rootfs/init << 'EOF'
#!/bin/sh
mount -t proc proc /proc
mount -t sysfs sysfs /sys
mount -t tmpfs tmpfs /tmp

echo "Firecracker microVM iniciada"

# Executar Wasm
if [ -f /app.wasm ]; then
    /wasmtime /app.wasm
fi

exec /bin/sh
EOF
chmod +x /mnt/rootfs/init

umount /mnt/rootfs

# Criar configuração do Firecracker
cat > firecracker-config.json << 'EOF'
{
    "boot-source": {
        "kernel_image_path": "vmlinux",
        "boot_args": "console=ttyS0 reboot=k panic=1 pci=off"
    },
    "drives": [
        {
            "drive_id": "rootfs",
            "path_on_host": "rootfs.ext4",
            "is_root_device": true,
            "is_read_only": false
        }
    ],
    "machine-config": {
        "vcpu_count": 2,
        "mem_size_mib": 512
    },
    "network-interfaces": [
        {
            "iface_id": "eth0",
            "guest_mac": "AA:FC:00:00:00:01",
            "host_dev_name": "tap0"
        }
    ]
}
EOF
```

### 7.6.2 API do Firecracker

```python
import requests
import json
import os

class FirecrackerClient:
    def __init__(self, socket_path="/tmp/firecracker.socket"):
        self.socket_path = socket_path
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json'
        })
    
    def _request(self, method, url, **kwargs):
        # Firecracker usa Unix socket
        url = f"http://localhost{url}"
        response = self.session.request(method, url, **kwargs)
        response.raise_for_status()
        return response.json() if response.content else None
    
    def get_instance_info(self):
        return self._request('GET', '/instance-info')
    
    def get_machine_config(self):
        return self._request('GET', '/machine-config')
    
    def update_machine_config(self, vcpu_count=None, mem_size_mib=None):
        config = {}
        if vcpu_count is not None:
            config['vcpu_count'] = vcpu_count
        if mem_size_mib is not None:
            config['mem_size_mib'] = mem_size_mib
        return self._request('PUT', '/machine-config', json=config)
    
    def create_network_interface(self, iface_id, guest_mac, host_dev_name):
        return self._request('PUT', f'/network-interfaces/{iface_id}', json={
            'iface_id': iface_id,
            'guest_mac': guest_mac,
            'host_dev_name': host_dev_name
        })
    
    def set_boot_source(self, kernel_path, boot_args):
        return self._request('PUT', '/boot-source', json={
            'kernel_image_path': kernel_path,
            'boot_args': boot_args
        })
    
    def set_root_drive(self, drive_id, path_on_host, is_read_only=False):
        return self._request('PUT', f'/drives/{drive_id}', json={
            'drive_id': drive_id,
            'path_on_host': path_on_host,
            'is_root_device': True,
            'is_read_only': is_read_only
        })
    
    def start_instance(self):
        return self._request('PUT', '/actions', json={
            'action_type': 'InstanceStart'
        })
    
    def create_snapshot(self, snapshot_type, mem_file_path, snapshot_path):
        return self._request('PUT', '/snapshot/create', json={
            'snapshot_type': snapshot_type,
            'snapshot_path': snapshot_path,
            'mem_file_path': mem_file_path
        })
    
    def load_snapshot(self, snapshot_path, mem_file_path):
        return self._request('PUT', '/snapshot/load', json={
            'snapshot_path': snapshot_path,
            'mem_file_path': mem_file_path
        })

# Uso
client = FirecrackerClient()

# Configurar microVM
client.set_boot_source('vmlinux', 'console=ttyS0 reboot=k panic=1')
client.set_root_drive('rootfs', 'rootfs.ext4')
client.update_machine_config(vcpu_count=2, mem_size_mib=512)

# Criar rede
client.create_network_interface('eth0', 'AA:FC:00:00:00:01', 'tap0')

# Iniciar
client.start_instance()

# Criar snapshot para cold start rápido
client.create_snapshot('Full', 'vm.mem', 'vm.snap')
```

### 7.6.3 Executando Wasm em Firecracker

```bash
# Criar microVM otimizada para Wasm
cat > wasm-vm-config.json << 'EOF'
{
    "boot-source": {
        "kernel_image_path": "vmlinux-minimal",
        "boot_args": "console=ttyS0 reboot=k panic=1 pci=off init=/init-wasm"
    },
    "drives": [
        {
            "drive_id": "rootfs",
            "path_on_host": "wasm-rootfs.ext4",
            "is_root_device": true,
            "is_read_only": true
        }
    ],
    "machine-config": {
        "vcpu_count": 1,
        "mem_size_mib": 256
    }
}
EOF

# Rootfs com wasmtime e módulos Wasm
cat > build-wasm-rootfs.sh << 'EOF'
#!/bin/bash
set -e

# Criar rootfs
dd if=/dev/zero of=wasm-rootfs.ext4 bs=1M count=128
mkfs.ext4 wasm-rootfs.ext4

# Montar e instalar
mkdir -p /mnt/wasm-rootfs
mount wasm-rootfs.ext4 /mnt/wasm-rootfs

# Instalar sistema mínimo
debootstrap --variant=minbase bullseye /mnt/wasm-rootfs

# Instalar wasmtime
cd /tmp
wget https://github.com/bytecodealliance/wasmtime/releases/latest/download/wasmtime-linux-x86_64.tar.xz
tar xf wasmtime-*.tar.xz
cp wasmtime-*/wasmtime /mnt/wasm-rootfs/usr/local/bin/

# Copiar módulos Wasm
cp *.wasm /mnt/wasm-rootfs/app/

# Criar init script
cat > /mnt/wasm-rootfs/init-wasm << 'INIT'
#!/bin/sh
mount -t proc proc /proc
mount -t sysfs sysfs /sys

echo "Iniciando sandbox Wasm..."

# Listar e executar módulos Wasm
for module in /app/*.wasm; do
    echo "Executando: $module"
    timeout 30 /usr/local/bin/wasmtime "$module"
done

exec /bin/sh
INIT
chmod +x /mnt/wasm-rootfs/init-wasm

umount /mnt/wasm-rootfs
echo "Rootfs criado: wasm-rootfs.ext4"
EOF
```

## 7.7 Wasm Sandbox vs Process Sandbox

### 7.7.1 Comparação de Modelos

O sandboxing de Wasm oferece propriedades de segurança fundamentamente diferentes do sandboxing baseado em processos:

**Modelo de Memória**:

Wasm utiliza memória linear, onde todo o estado do módulo (heap, stack, dados) reside em um único ArrayBuffer contíguo. Isso permite bounds checking eficiente e previne acessos fuera de limites.

```wasm
;; Exemplo de bounds checking implícito no Wasm
(module
  (memory (export "memory") 1)  ;; 1 página de 64KB
  
  ;; Função que acessa memória com bounds checking
  (func $safe_access (param $index i32) (result i32)
    ;; O runtime verifica se o índice está dentro dos limites
    local.get $index
    i32.load  ;; Falha se index >= memory.size * 64KB
  )
  
  ;; Função que tenta acesso inválido
  (func $unsafe_access (param $index i32) (result i32)
    ;; Isso causará trap se o índice for inválido
    local.get $index
    i32.load
  )
)
```

**Isolamento de Recursos**:

Wasm não possui acesso direto a recursos do sistema. Todo I/O deve ser concedido através de WASI ou APIs específicas da plataforma.

```wasm
;; Módulo Wasm não pode fazer isso diretamente:
;; - Abrir arquivos arbitrários
;; - Criar conexões de rede
;; - Executar outros processos
;; - Acessar variáveis de ambiente
;; - Ler informações do sistema

;; Tudo deve ser feito através de interfaces explícitas
(module
  ;; Importar funções WASI
  (import "wasi_snapshot_preview1" "fd_write" 
    (func $fd_write (param i32 i32 i32 i32) (result i32)))
  
  ;; Exportar função para o host
  (func (export "process_data") (param i32 i32) (result i32)
    ;; Processar dados usando apenas memória linear
    local.get $0
    local.get $1
    call $internal_process
  )
)
```

### 7.7.2 Tabela Comparativa

| Característica | Wasm Sandbox | Process Sandbox | Container | microVM |
|----------------|--------------|-----------------|-----------|---------|
| **Isolamento de Memória** | Bounds checking em tempo de execução | Separação de espaço de endereço | Separação de espaço de endereço | Virtualização completa |
| **Isolamento de Rede** | Sem acesso sem WASI | Namespaces de rede | Namespaces de rede | Interface de rede virtual |
| **Isolamento de FS** | Sem acesso sem WASI | chroot/jail | Mount namespace | Disco virtual |
| **Isolamento de Processos** | Impossível sem WASI | PID namespace | PID namespace | Kernel separado |
| **Performance Startup** | ~1ms | ~10ms | ~100ms | ~125ms |
| **Overhead de Memória** | Mínimo | Baixo | Médio | Alto |
| **Attack Surface** | Mínimo | Médio | Médio | Pequeno |
| **Complexidade** | Baixa | Média | Média | Alta |

### 7.7.3 Sandboxing Nível de Linguagem

Diferentes linguagens compiladas para Wasm oferecem diferentes níveis de segurança:

**Rust**: Borrow checker previne use-after-free e data races em compile time. Em Wasm, essas garantias se traduzem em segurança de memória sem overhead runtime.

```rust
use wasm_bindgen::prelude::*;

#[wasm_bindgen]
pub fn safe_string_operation(input: &str) -> String {
    // Rust garante que não há dangling pointers
    let processed = input.to_uppercase();
    let result = format!("Processed: {}", processed);
    result // Ownership transferido corretamente
}

#[wasm_bindgen]
pub fn safe_collection_operation(data: &[i32]) -> Vec<i32> {
    // Rust previne buffer overflow
    data.iter()
        .filter(|&&x| x > 0)
        .map(|&x| x * 2)
        .collect() // Vec gerenciado automaticamente
}
```

**AssemblyScript**: Type checking em compile time, mas sem borrow checker. Oferece segurança intermediária.

```typescript
// AssemblyScript com type safety
export function processData(input: StaticArray<i32>): StaticArray<i32> {
    const length = input.length;
    const result = new StaticArray<i32>(length);
    
    for (let i = 0; i < length; i++) {
        // Bounds checking em tempo de execução
        unchecked {
            result[i] = input[i] * 2;
        }
    }
    
    return result;
}
```

**C/C++ via Emscripten**: Sem proteção automática de memória. Requer ferramentas como AddressSanitizer para detecção de bugs.

```c
// C em Wasm - sem proteção automática
#include <stdlib.h>
#include <string.h>

// Perigoso: buffer overflow
void unsafe_copy(char *dest, const char *src, int len) {
    // Sem bounds checking em C puro
    memcpy(dest, src, len);  // Pode causar overflow
}

// Mais seguro: com bounds checking
void safe_copy(char *dest, int dest_size, const char *src, int src_len) {
    int copy_len = (src_len < dest_size - 1) ? src_len : dest_size - 1;
    memcpy(dest, src, copy_len);
    dest[copy_len] = '\0';
}

// Usando WASI para I/O seguro
#include <wasi/api.h>

__wasi_errno_t safe_file_read(const char *path, char *buffer, size_t buffer_size) {
    __wasi_fd_t fd;
    __wasi_errno_t err;
    
    // Abrir arquivo com permissões limitadas
    err = __wasi_path_open(
        __WASI_FD_PREOPEN,
        0,
        path,
        strlen(path),
        __WASI_RIGHTS_FD_READ,
        0,
        0,
        &fd
    );
    
    if (err != __WASI_ERRNO_SUCCESS) {
        return err;
    }
    
    // Ler com tamanho limitado
    size_t bytes_read;
    err = __wasi_fd_read(fd, &(const __wasi_iovec_t){buffer, buffer_size}, 1, &bytes_read);
    
    __wasi_fd_close(fd);
    return err;
}
```

## 7.8 Isolamento de Rede

### 7.8.1 Namespaces de Rede

Namespaces de rede criam pilhas de rede completamente isoladas para cada container ou processo:

```bash
# Criar namespace de rede
ip netns add wasm-sandbox

# Criar par de interfaces virtuais
ip link add veth-host type veth peer name veth-sandbox

# Mover interface para o namespace
ip link set veth-sandbox netns wasm-sandbox

# Configurar interfaces
ip addr add 10.100.0.1/24 dev veth-host
ip link set veth-host up

ip netns exec wasm-sandbox ip addr add 10.100.0.2/24 dev veth-sandbox
ip netns exec wasm-sandbox ip link set veth-sandbox up
ip netns exec wasm-sandbox ip link set lo up

# Configurar rota padrão no sandbox
ip netns exec wasm-sandbox ip route add default via 10.100.0.1

# Configurar NAT e firewall
echo 1 > /proc/sys/net/ipv4/ip_forward

# Regras iptables para isolar o sandbox
iptables -A FORWARD -i veth-host -o eth0 -j ACCEPT
iptables -A FORWARD -i eth0 -o veth-host -m state --state RELATED,ESTABLISHED -j ACCEPT
iptables -t nat -A POSTROUTING -s 10.100.0.0/24 -o eth0 -j MASQUERADE

# Limitar bandwidth
tc qdisc add dev veth-host root tbf rate 10mbit burst 32kbit latency 400ms

# Bloquear acesso a serviços sensíveis
iptables -A FORWARD -s 10.100.0.0/24 -d 169.254.169.254/32 -j DROP  # Metadata AWS
iptables -A FORWARD -s 10.100.0.0/24 -d 10.0.0.0/8 -j DROP  # Rede interna
```

### 7.8.2 Firewalls para Wasm

```bash
# Criar regras iptables específicas para módulos Wasm
# Cada módulo pode ter suas próprias restrições de rede

# Função para configurar sandbox de rede para um módulo Wasm
setup_wasm_network_sandbox() {
    local MODULE_ID=$1
    local ALLOWED_PORTS=$2
    local NETNS="wasm-$MODULE_ID"
    
    # Criar namespace
    ip netns add "$NETNS"
    
    # Criar interface virtual
    ip link add "veth-$MODULE_ID" type veth peer name "veth-wasm-$MODULE_ID"
    ip link set "veth-wasm-$MODULE_ID" netns "$NETNS"
    
    # Configurar IPs
    ip addr add "10.$((RANDOM % 256)).$((RANDOM % 256)).1/24" dev "veth-$MODULE_ID"
    ip link set "veth-$MODULE_ID" up
    
    ip netns exec "$NETNS" ip addr add "10.$((RANDOM % 256)).$((RANDOM % 256)).2/24" dev "veth-wasm-$MODULE_ID"
    ip netns exec "$NETNS" ip link set "veth-wasm-$MODULE_ID" up
    ip netns exec "$NETNS" ip link set lo up
    
    # Configurar NAT
    echo 1 > /proc/sys/net/ipv4/ip_forward
    iptables -t nat -A POSTROUTING -s "10.$((RANDOM % 256)).$((RANDOM % 256)).0/24" -o eth0 -j MASQUERADE
    
    # Regras de firewall por porta
    for port in $ALLOWED_PORTS; do
        iptables -A FORWARD -s "10.$((RANDOM % 256)).$((RANDOM % 256)).0/24" -p tcp --dport "$port" -j ACCEPT
    done
    
    # Bloquear tudo mais
    iptables -A FORWARD -s "10.$((RANDOM % 256)).$((RANDOM % 256)).0/24" -j DROP
    
    echo "Sandbox de rede configurado para módulo $MODULE_ID"
}

# Uso
setup_wasm_network_sandbox "module1" "80 443"
setup_wasm_network_sandbox "module2" "8080"
```

### 7.8.3 Proxy de Rede para Wasm

```c
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#include <poll.h>
#include <errno.h>

typedef struct {
    int client_fd;
    int upstream_fd;
    char buffer[65536];
    size_t buffer_len;
    int connected;
} ProxyConnection;

typedef struct {
    char *allowed_hosts[100];
    int allowed_ports[100];
    int num_rules;
    size_t max_bandwidth;
    int timeout_seconds;
} FirewallRules;

int check_firewall_rules(FirewallRules *rules, const char *host, int port) {
    for (int i = 0; i < rules->num_rules; i++) {
        if (strcmp(rules->allowed_hosts[i], "*") == 0 || 
            strcmp(rules->allowed_hosts[i], host) == 0) {
            if (rules->allowed_ports[i] == port || rules->allowed_ports[i] == 0) {
                return 1; // Permitido
            }
        }
    }
    return 0; // Bloqueado
}

int create_upstream_connection(const char *host, int port) {
    int sock = socket(AF_INET, SOCK_STREAM, 0);
    if (sock < 0) {
        perror("socket");
        return -1;
    }
    
    struct sockaddr_in addr;
    memset(&addr, 0, sizeof(addr));
    addr.sin_family = AF_INET;
    addr.sin_port = htons(port);
    inet_pton(AF_INET, host, &addr.sin_addr);
    
    if (connect(sock, (struct sockaddr *)&addr, sizeof(addr)) < 0) {
        perror("connect");
        close(sock);
        return -1;
    }
    
    return sock;
}

void handle_proxy(ProxyConnection *conn) {
    struct pollfd fds[2];
    fds[0].fd = conn->client_fd;
    fds[0].events = POLLIN;
    fds[1].fd = conn->upstream_fd;
    fds[1].events = POLLIN;
    
    while (1) {
        int ret = poll(fds, 2, 5000); // 5 second timeout
        
        if (ret < 0) {
            perror("poll");
            break;
        }
        
        if (ret == 0) {
            printf("Timeout na conexão proxy\n");
            break;
        }
        
        // Dados do cliente para upstream
        if (fds[0].revents & POLLIN) {
            ssize_t n = read(conn->client_fd, conn->buffer, sizeof(conn->buffer));
            if (n <= 0) break;
            
            write(conn->upstream_fd, conn->buffer, n);
        }
        
        // Dados do upstream para cliente
        if (fds[1].revents & POLLIN) {
            ssize_t n = read(conn->upstream_fd, conn->buffer, sizeof(conn->buffer));
            if (n <= 0) break;
            
            write(conn->client_fd, conn->buffer, n);
        }
        
        // Erros
        if (fds[0].revents & (POLLERR | POLLHUP)) break;
        if (fds[1].revents & (POLLERR | POLLHUP)) break;
    }
}

int main(int argc, char *argv[]) {
    if (argc < 4) {
        fprintf(stderr, "Uso: %s <port> <upstream_host> <upstream_port>\n", argv[0]);
        return 1;
    }
    
    int listen_port = atoi(argv[1]);
    char *upstream_host = argv[2];
    int upstream_port = atoi(argv[3]);
    
    // Configurar regras de firewall
    FirewallRules rules = {
        .allowed_hosts = {"example.com", "api.example.com", "*"},
        .allowed_ports = {80, 443, 0},
        .num_rules = 3,
        .max_bandwidth = 1024 * 1024, // 1MB/s
        .timeout_seconds = 30
    };
    
    int server_fd = socket(AF_INET, SOCK_STREAM, 0);
    if (server_fd < 0) {
        perror("socket");
        return 1;
    }
    
    int opt = 1;
    setsockopt(server_fd, SOL_SOCKET, SO_REUSEADDR, &opt, sizeof(opt));
    
    struct sockaddr_in addr;
    addr.sin_family = AF_INET;
    addr.sin_addr.s_addr = INADDR_ANY;
    addr.sin_port = htons(listen_port);
    
    if (bind(server_fd, (struct sockaddr *)&addr, sizeof(addr)) < 0) {
        perror("bind");
        close(server_fd);
        return 1;
    }
    
    if (listen(server_fd, 10) < 0) {
        perror("listen");
        close(server_fd);
        return 1;
    }
    
    printf("Proxy de segurança escutando na porta %d\n", listen_port);
    
    while (1) {
        struct sockaddr_in client_addr;
        socklen_t client_len = sizeof(client_addr);
        int client_fd = accept(server_fd, (struct sockaddr *)&client_addr, &client_len);
        
        if (client_fd < 0) {
            perror("accept");
            continue;
        }
        
        // Verificar firewall
        if (!check_firewall_rules(&rules, upstream_host, upstream_port)) {
            printf("Conexão bloqueada pelo firewall\n");
            close(client_fd);
            continue;
        }
        
        // Criar conexão upstream
        int upstream_fd = create_upstream_connection(upstream_host, upstream_port);
        if (upstream_fd < 0) {
            printf("Falha ao conectar upstream\n");
            close(client_fd);
            continue;
        }
        
        // Criar conexão proxy
        ProxyConnection conn = {
            .client_fd = client_fd,
            .upstream_fd = upstream_fd,
            .connected = 1
        };
        
        handle_proxy(&conn);
        
        close(client_fd);
        close(upstream_fd);
    }
    
    close(server_fd);
    return 0;
}
```

## 7.9 Isolamento de Sistema de Arquivos

### 7.9.1 Mount Namespaces para Isolamento de FS

```c
#define _GNU_SOURCE
#include <sched.h>
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <sys/mount.h>
#include <sys/stat.h>
#include <sys/wait.h>
#include <fcntl.h>
#include <string.h>
#include <errno.h>

#define STACK_SIZE (1024 * 1024)
static char child_stack[STACK_SIZE];

static void create_minimal_rootfs(const char *rootfs_path) {
    mkdir(rootfs_path, 0755);
    mkdir("/tmp/sandbox/dev", 0755);
    mkdir("/tmp/sandbox/proc", 0555);
    mkdir("/tmp/sandbox/sys", 0555);
    mkdir("/tmp/sandbox/tmp", 01777);
    mkdir("/tmp/sandbox/app", 0755);
    
    // Montar tmpfs como raiz
    mount("tmpfs", "/tmp/sandbox", "tmpfs", 0, 
          "size=100M,mode=0755,noexec,nosuid");
    
    // Montar /proc
    mount("proc", "/tmp/sandbox/proc", "proc", 0, NULL);
    
    // Montar /sys somente leitura
    mount("sysfs", "/tmp/sandbox/sys", "sysfs", MS_RDONLY, NULL);
    
    // Criar dispositivos básicos
    mknod("/tmp/sandbox/dev/null", 0666 | S_IFCHR, makedev(1, 3));
    mknod("/tmp/sandbox/dev/zero", 0666 | S_IFCHR, makedev(1, 5));
    mknod("/tmp/sandbox/dev/random", 0666 | S_IFCHR, makedev(1, 8));
    mknod("/tmp/sandbox/dev/urandom", 0666 | S_IFCHR, makedev(1, 9));
}

static int child_fn(void *arg) {
    char *rootfs = (char *)arg;
    
    // Criar rootfs mínimo
    create_minimal_rootfs(rootfs);
    
    // Mover para dentro do sandbox
    chroot(rootfs);
    chdir("/");
    
    printf("Dentro do sandbox de filesystem:\n");
    system("ls -la /");
    
    // Testar isolamento
    printf("\nTestando isolamento:\n");
    
    // Tentar acessar filesystem real (deve falhar)
    FILE *f = fopen("/etc/passwd", "r");
    if (f) {
        printf("ERRO: conseguiu acessar /etc/passwd!\n");
        fclose(f);
    } else {
        printf("OK: não conseguiu acessar /etc/passwd\n");
    }
    
    // Criar arquivo no sandbox
    f = fopen("/tmp/test.txt", "w");
    if (f) {
        fprintf(f, "Arquivo criado no sandbox\n");
        fclose(f);
        printf("OK: criou arquivo no sandbox\n");
    }
    
    execlp("/bin/sh", "/bin/sh", NULL);
    perror("execlp");
    return 1;
}

int main() {
    printf("Criando sandbox de filesystem...\n");
    
    pid_t pid = clone(child_fn, 
                      child_stack + STACK_SIZE,
                      CLONE_NEWNS | SIGCHLD, 
                      "/tmp/sandbox");
    
    if (pid == -1) {
        perror("clone");
        return 1;
    }
    
    int status;
    waitpid(pid, &status, 0);
    
    // Limpar mounts
    umount2("/tmp/sandbox/sys", MNT_DETACH);
    umount2("/tmp/sandbox/proc", MNT_DETACH);
    umount2("/tmp/sandbox", MNT_DETACH);
    
    return 0;
}
```

### 7.9.2 Overlay Filesystems para Isolamento

```bash
# Criar overlay filesystem para isolar writes
mkdir -p /var/sandbox/{lower,upper,work,merged}

# Lower layer (read-only) - base do sistema
mount -o ro /path/to/base /var/sandbox/lower

# Upper layer (read-write) - onde as mudanças são registradas
mount -t tmpfs -o size=1G tmpfs /var/sandbox/upper

# Work directory (obrigatório para overlay)
mount -t tmpfs -o size=100M tmpfs /var/sandbox/work

# Montar overlay
mount -t overlay overlay \
    -o lowerdir=/var/sandbox/lower,\
upperdir=/var/sandbox/upper,\
workdir=/var/sandbox/work \
    /var/sandbox/merged

# Agora /var/sandbox/merged tem o filesystem base
# mas todas as escritas vão para /var/sandbox/upper

# Criar script de isolamento
cat > /usr/local/bin/wasm-overlay.sh << 'EOF'
#!/bin/bash
MODULE_ID=$1
OVERLAY_DIR="/var/sandbox/wasm-$MODULE_ID"

mkdir -p "$OVERLAY_DIR"/{lower,upper,work,merged}

# Montar lower layer (read-only)
mount -o ro /usr/share/wasm-base "$OVERLAY_DIR/lower"

# Montar upper layer (read-write, temporário)
mount -t tmpfs -o size=100M tmpfs "$OVERLAY_DIR/upper"

# Montar work directory
mount -t tmpfs -o size=10M tmpfs "$OVERLAY_DIR/work"

# Montar overlay
mount -t overlay overlay \
    -o lowerdir="$OVERLAY_DIR/lower",\
upperdir="$OVERLAY_DIR/upper",\
workdir="$OVERLAY_DIR/work" \
    "$OVERLAY_DIR/merged"

echo "Overlay filesystem criado para módulo $MODULE_ID"
echo "Ponto de montagem: $OVERLAY_DIR/merged"
EOF

chmod +x /usr/local/bin/wasm-overlay.sh
```

### 7.9.3 Filesystem Virtual com FUSE

```c
#define FUSE_USE_VERSION 31
#include <fuse3/fuse.h>
#include <stdio.h>
#include <string.h>
#include <errno.h>
#include <fcntl.h>
#include <stdlib.h>
#include <unistd.h>
#include <sys/stat.h>

typedef struct {
    char *real_path;
    char *allowed_extensions[100];
    int num_extensions;
    size_t max_file_size;
    int read_only;
} SandboxConfig;

static SandboxConfig config;

static int sandbox_getattr(const char *path, struct stat *stbuf,
                          struct fuse_file_info *fi) {
    char full_path[4096];
    snprintf(full_path, sizeof(full_path), "%s%s", config.real_path, path);
    
    int res = stat(full_path, stbuf);
    if (res == -1) return -errno;
    
    return 0;
}

static int sandbox_readdir(const char *path, void *buf,
                          fuse_fill_dir_t filler, off_t offset,
                          struct fuse_file_info *fi,
                          enum fuse_readdir_flags flags) {
    char full_path[4096];
    snprintf(full_path, sizeof(full_path), "%s%s", config.real_path, path);
    
    DIR *dp = opendir(full_path);
    if (dp == NULL) return -errno;
    
    struct dirent *de;
    while ((de = readdir(dp)) != NULL) {
        struct stat st;
        memset(&st, 0, sizeof(st));
        st.st_ino = de->d_ino;
        st.st_mode = de->d_type << 12;
        
        // Filtrar por extensões permitidas
        char *ext = strrchr(de->d_name, '.');
        if (ext && config.num_extensions > 0) {
            int allowed = 0;
            for (int i = 0; i < config.num_extensions; i++) {
                if (strcmp(ext, config.allowed_extensions[i]) == 0) {
                    allowed = 1;
                    break;
                }
            }
            if (!allowed) continue;
        }
        
        if (filler(buf, de->d_name, &st, 0, 0)) break;
    }
    
    closedir(dp);
    return 0;
}

static int sandbox_open(const char *path, struct fuse_file_info *fi) {
    char full_path[4096];
    snprintf(full_path, sizeof(full_path), "%s%s", config.real_path, path);
    
    // Verificar permissões
    if (config.read_only && (fi->flags & O_WRONLY || fi->flags & O_RDWR)) {
        return -EROFS;
    }
    
    // Verificar extensão
    char *ext = strrchr(path, '.');
    if (ext && config.num_extensions > 0) {
        int allowed = 0;
        for (int i = 0; i < config.num_extensions; i++) {
            if (strcmp(ext, config.allowed_extensions[i]) == 0) {
                allowed = 1;
                break;
            }
        }
        if (!allowed) return -EACCES;
    }
    
    int fd = open(full_path, fi->flags);
    if (fd == -1) return -errno;
    
    fi->fh = fd;
    return 0;
}

static int sandbox_read(const char *path, char *buf, size_t size,
                       off_t offset, struct fuse_file_info *fi) {
    ssize_t res = pread(fi->fh, buf, size, offset);
    if (res == -1) return -errno;
    
    return res;
}

static int sandbox_write(const char *path, const char *buf, size_t size,
                        off_t offset, struct fuse_file_info *fi) {
    if (config.read_only) return -EROFS;
    
    // Verificar tamanho máximo
    struct stat st;
    fstat(fi->fh, &st);
    if (st.st_size + size > config.max_file_size) {
        return -EFBIG;
    }
    
    ssize_t res = pwrite(fi->fh, buf, size, offset);
    if (res == -1) return -errno;
    
    return res;
}

static const struct fuse_operations sandbox_ops = {
    .getattr = sandbox_getattr,
    .readdir = sandbox_readdir,
    .open = sandbox_open,
    .read = sandbox_read,
    .write = sandbox_write,
};

int main(int argc, char *argv[]) {
    // Configurar sandbox
    config.real_path = "/var/data/sandbox";
    config.allowed_extensions[0] = ".txt";
    config.allowed_extensions[1] = ".json";
    config.allowed_extensions[2] = ".wasm";
    config.num_extensions = 3;
    config.max_file_size = 10 * 1024 * 1024; // 10MB
    config.read_only = 0;
    
    return fuse_main(argc, argv, &sandbox_ops, NULL);
}
```

## 7.10 Limites de Recursos (Memória, CPU)

### 7.10.1 Cgroups para Controle de Recursos

Cgroups (Control Groups) são uma feature do kernel Linux que permite limitar, accounting e isolar recursos para processos:

```c
#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <sys/stat.h>
#include <sys/mount.h>
#include <sys/wait.h>
#include <fcntl.h>
#include <errno.h>

int create_cgroup(const char *name, long memory_limit_bytes, 
                  int cpu_quota, int cpu_period) {
    char path[256];
    char value[64];
    
    // Criar diretório do cgroup
    snprintf(path, sizeof(path), "/sys/fs/cgroup/%s", name);
    mkdir(path, 0755);
    
    // Configurar limite de memória
    if (memory_limit_bytes > 0) {
        snprintf(path, sizeof(path), 
                 "/sys/fs/cgroup/%s/memory.max", name);
        snprintf(value, sizeof(value), "%ld", memory_limit_bytes);
        
        int fd = open(path, O_WRONLY);
        if (fd >= 0) {
            write(fd, value, strlen(value));
            close(fd);
            printf("Limite de memória configurado: %ld bytes\n", 
                   memory_limit_bytes);
        }
        
        // Configurar memory.swap.max (limitar swap)
        snprintf(path, sizeof(path), 
                 "/sys/fs/cgroup/%s/memory.swap.max", name);
        fd = open(path, O_WRONLY);
        if (fd >= 0) {
            write(fd, "0", 1);  // Sem swap
            close(fd);
        }
    }
    
    // Configurar CPU
    if (cpu_quota > 0 && cpu_period > 0) {
        // Configurar CPU quota usando cpu.max
        snprintf(path, sizeof(path), 
                 "/sys/fs/cgroup/%s/cpu.max", name);
        snprintf(value, sizeof(value), "%d %d", cpu_quota, cpu_period);
        
        int fd = open(path, O_WRONLY);
        if (fd >= 0) {
            write(fd, value, strlen(value));
            close(fd);
            printf("CPU quota configurado: %d/%d\n", 
                   cpu_quota, cpu_period);
        }
    }
    
    // Configurar I/O
    snprintf(path, sizeof(path), 
             "/sys/fs/cgroup/%s/io.max", name);
    int fd = open(path, O_WRONLY);
    if (fd >= 0) {
        // Limitar leitura: 10MB/s
        write(fd, "8:0 rbps=10485760", 18);
        // Limitar escrita: 5MB/s
        write(fd, "\n8:0 wbps=5242880", 17);
        close(fd);
    }
    
    // Limitar PIDs
    snprintf(path, sizeof(path), 
             "/sys/fs/cgroup/%s/pids.max", name);
    fd = open(path, O_WRONLY);
    if (fd >= 0) {
        write(fd, "100", 3);  // Máximo 100 processos
        close(fd);
    }
    
    return 0;
}

int add_process_to_cgroup(const char *cgroup_name, pid_t pid) {
    char path[256];
    char value[32];
    
    snprintf(path, sizeof(path), 
             "/sys/fs/cgroup/%s/cgroup.procs", cgroup_name);
    snprintf(value, sizeof(value), "%d", pid);
    
    int fd = open(path, O_WRONLY);
    if (fd < 0) {
        perror("open cgroup.procs");
        return -1;
    }
    
    write(fd, value, strlen(value));
    close(fd);
    
    printf("Processo %d adicionado ao cgroup %s\n", 
           pid, cgroup_name);
    
    return 0;
}

int main() {
    // Criar cgroup para módulo Wasm
    create_cgroup("wasm-sandbox", 
                  256 * 1024 * 1024,  // 256MB memória
                  50000,               // 50% CPU (50000/100000)
                  100000);             // Período 100ms
    
    // Criar processo filho
    pid_t pid = fork();
    
    if (pid == 0) {
        // Processo filho - executar módulo Wasm
        add_process_to_cgroup("wasm-sandbox", getpid());
        
        // Executar módulo Wasm
        execlp("wasmtime", "wasmtime", "--dir=.", "module.wasm", NULL);
        perror("exec");
        return 1;
    } else if (pid > 0) {
        // Processo pai - monitorar
        int status;
        waitpid(pid, &status, 0);
        
        // Ler estatísticas do cgroup
        char path[256];
        char value[256];
        
        // Memória usada
        snprintf(path, sizeof(path), 
                 "/sys/fs/cgroup/wasm-sandbox/memory.current");
        int fd = open(path, O_RDONLY);
        if (fd >= 0) {
            ssize_t n = read(fd, value, sizeof(value) - 1);
            if (n > 0) {
                value[n] = '\0';
                printf("Memória usada: %s bytes\n", value);
            }
            close(fd);
        }
        
        // CPU usada
        snprintf(path, sizeof(path), 
                 "/sys/fs/cgroup/wasm-sandbox/cpu.stat");
        fd = open(path, O_RDONLY);
        if (fd >= 0) {
            ssize_t n = read(fd, value, sizeof(value) - 1);
            if (n > 0) {
                value[n] = '\0';
                printf("Estatísticas CPU:\n%s\n", value);
            }
            close(fd);
        }
    }
    
    return 0;
}
```

### 7.10.2 Monitoramento de Recursos para Wasm

```c
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <sys/resource.h>
#include <sys/time.h>
#include <signal.h>
#include <time.h>

typedef struct {
    long memory_limit;
    long memory_used;
    double cpu_time_used;
    int num_page_faults;
    int num_ctx_switches;
    time_t start_time;
    time_t end_time;
} ResourceMonitor;

ResourceMonitor monitor;

void signal_handler(int sig) {
    if (sig == SIGXCPU) {
        fprintf(stderr, "ERRO: Limite de CPU excedido\n");
        _exit(1);
    }
    if (sig == SIGXFSZ) {
        fprintf(stderr, "ERRO: Limite de arquivo excedido\n");
        _exit(1);
    }
}

int setup_resource_limits(long max_memory, long max_cpu_seconds,
                         long max_file_size, int max_open_files) {
    struct rlimit rl;
    
    // Limite de memória
    if (max_memory > 0) {
        rl.rlim_cur = max_memory;
        rl.rlim_max = max_memory;
        setrlimit(RLIMIT_AS, &rl);
        
        printf("Limite de memória: %ld bytes\n", max_memory);
    }
    
    // Limite de CPU
    if (max_cpu_seconds > 0) {
        rl.rlim_cur = max_cpu_seconds;
        rl.rlim_max = max_cpu_seconds + 1;
        setrlimit(RLIMIT_CPU, &rl);
        
        printf("Limite de CPU: %ld segundos\n", max_cpu_seconds);
    }
    
    // Limite de tamanho de arquivo
    if (max_file_size > 0) {
        rl.rlim_cur = max_file_size;
        rl.rlim_max = max_file_size;
        setrlimit(RLIMIT_FSIZE, &rl);
        
        printf("Limite de arquivo: %ld bytes\n", max_file_size);
    }
    
    // Limite de arquivos abertos
    if (max_open_files > 0) {
        rl.rlim_cur = max_open_files;
        rl.rlim_max = max_open_files;
        setrlimit(RLIMIT_NOFILE, &rl);
        
        printf("Limite de arquivos abertos: %d\n", max_open_files);
    }
    
    // Limite de processos
    rl.rlim_cur = 100;
    rl.rlim_max = 100;
    setrlimit(RLIMIT_NPROC, &rl);
    
    // Instalar handlers de sinal
    signal(SIGXCPU, signal_handler);
    signal(SIGXFSZ, signal_handler);
    
    return 0;
}

int get_resource_usage(ResourceMonitor *mon) {
    struct rusage usage;
    struct rlimit rl;
    
    if (getrusage(RUSAGE_SELF, &usage) == 0) {
        mon->cpu_time_used = usage.ru_utime.tv_sec + 
                            usage.ru_utime.tv_usec / 1000000.0;
        mon->num_page_faults = usage.ru_minflt + usage.ru_majflt;
        mon->num_ctx_switches = usage.ru_nvcsw + usage.ru_nivcsw;
    }
    
    // Memória usada (RSS)
    FILE *f = fopen("/proc/self/status", "r");
    if (f) {
        char line[256];
        while (fgets(line, sizeof(line), f)) {
            if (strncmp(line, "VmRSS:", 6) == 0) {
                sscanf(line + 6, "%ld", &mon->memory_used);
                mon->memory_used *= 1024;  // Converter de KB para bytes
            }
        }
        fclose(f);
    }
    
    // Limite de memória
    if (getrlimit(RLIMIT_AS, &rl) == 0) {
        mon->memory_limit = rl.rlim_cur;
    }
    
    return 0;
}

void print_resource_report(ResourceMonitor *mon) {
    printf("\n=== Relatório de Recursos ===\n");
    printf("Memória usada: %ld bytes (%.2f MB)\n", 
           mon->memory_used, mon->memory_used / (1024.0 * 1024.0));
    printf("Limite de memória: %ld bytes (%.2f MB)\n", 
           mon->memory_limit, mon->memory_limit / (1024.0 * 1024.0));
    printf("CPU usada: %.2f segundos\n", mon->cpu_time_used);
    printf("Page faults: %d\n", mon->num_page_faults);
    printf("Context switches: %d\n", mon->num_ctx_switches);
    printf("============================\n\n");
}

int main(int argc, char *argv[]) {
    if (argc < 2) {
        fprintf(stderr, "Uso: %s <módulo.wasm>\n", argv[0]);
        return 1;
    }
    
    // Configurar limites de recursos
    setup_resource_limits(
        256 * 1024 * 1024,  // 256MB memória
        30,                  // 30 segundos CPU
        10 * 1024 * 1024,   // 10MB tamanho de arquivo
        64                   // 64 arquivos abertos
    );
    
    // Inicializar monitor
    monitor.start_time = time(NULL);
    
    printf("Executando módulo Wasm: %s\n", argv[1]);
    
    // Executar módulo Wasm
    // (Substituir por chamada real ao runtime Wasm)
    pid_t pid = fork();
    if (pid == 0) {
        execlp("wasmtime", "wasmtime", argv[1], NULL);
        perror("exec");
        return 1;
    }
    
    int status;
    waitpid(pid, &status, 0);
    
    monitor.end_time = time(NULL);
    
    // Obter e imprimir uso de recursos
    get_resource_usage(&monitor);
    print_resource_report(&monitor);
    
    return 0;
}
```

### 7.10.3 Limites em Docker com Wasm

```bash
# Criar container Wasm com limites de recursos
docker run \
    --runtime=io.containerd.wasmtime.v1 \
    --memory=256m \
    --memory-swap=256m \
    --cpus=1.0 \
    --cpu-shares=512 \
    --pids-limit=100 \
    --ulimit nofile=1024:1024 \
    --ulimit nproc=100:100 \
    --read-only \
    --tmpfs /tmp:size=100M,noexec,nosuid \
    --security-opt no-new-privileges \
    --cap-drop ALL \
    --cap-add NET_BIND_SERVICE \
    --network none \
    --volumes-from wasm-base:ro \
    wasm-app

# Configurar cgroup manualmente para mais controle
# Encontrar o PID do container
CONTAINER_PID=$(docker inspect --format '{{.State.Pid}}' wasm-container)

# Criar cgroup personalizado
mkdir -p /sys/fs/cgroup/wasm-custom

# Configurar limites
echo "268435456" > /sys/fs/cgroup/wasm-custom/memory.max  # 256MB
echo "0" > /sys/fs/cgroup/wasm-custom/memory.swap.max  # Sem swap
echo "50000 100000" > /sys/fs/cgroup/wasm-custom/cpu.max  # 50% CPU
echo "100" > /sys/fs/cgroup/wasm-custom/pids.max  # 100 processos
echo "8:0 rbps=10485760 wbps=5242880" > /sys/fs/cgroup/wasm-custom/io.max

# Adicionar container ao cgroup
echo $CONTAINER_PID > /sys/fs/cgroup/wasm-custom/cgroup.procs

# Monitorar uso de recursos
watch -n 1 "cat /sys/fs/cgroup/wasm-custom/memory.current; \
            cat /sys/fs/cgroup/wasm-custom/cpu.stat"
```

## 7.11 Docker com WebAssembly

### 7.11.1 Containerd e Wasm

O suporte nativo a Wasm no Docker é fornecido através do containerd com shims específicos para cada runtime Wasm:

```bash
# Instalar containerd com suporte a Wasm
apt-get update && apt-get install -y containerd

# Configurar containerd para usar wasmtime
cat > /etc/containerd/config.toml << 'EOF'
version = 2

[plugins."io.containerd.grpc.v1.cri".containerd.runtimes.wasmtime]
  runtime_type = "io.containerd.wasmtime.v1"
  
[plugins."io.containerd.grpc.v1.cri".containerd.runtimes.wasmtime.options]
  BinaryName = "/usr/local/bin/containerd-shim-wasmtime-v1"

[plugins."io.containerd.grpc.v1.cri".containerd.runtimes.wasmedge]
  runtime_type = "io.containerd.wasmedge.v1"
  
[plugins."io.containerd.grpc.v1.cri".containerd.runtimes.wasmer]
  runtime_type = "io.containerd.wasmer.v1"
EOF

systemctl restart containerd

# Criar imagem Wasm
cat > Dockerfile << 'EOF'
FROM scratch

# Copiar módulo Wasm
COPY target/wasm32-wasi/release/app.wasm /app.wasm

# Configurar metadados
LABEL org.opencontainers.image.title="Wasm App"
LABEL org.opencontainers.image.description="Aplicação WebAssembly isolada"

# Ponto de entrada
ENTRYPOINT ["/app.wasm"]
EOF

# Construir com buildkit
DOCKER_BUILDKIT=1 docker build -t wasm-app:latest .

# Executar com Docker
docker run --rm \
    --runtime=io.containerd.wasmtime.v1 \
    wasm-app:latest

# Executar com limites de recursos
docker run --rm \
    --runtime=io.containerd.wasmtime.v1 \
    --memory=128m \
    --cpus=0.5 \
    --read-only \
    --tmpfs /tmp:size=10M \
    --cap-drop ALL \
    --security-opt no-new-privileges \
    wasm-app:latest
```

### 7.11.2 Docker Compose com Wasm

```yaml
# docker-compose.yml
version: '3.8'

services:
  wasm-worker:
    image: wasm-worker:latest
    runtime: io.containerd.wasmtime.v1
    deploy:
      resources:
        limits:
          cpus: '0.5'
          memory: 256M
        reservations:
          cpus: '0.25'
          memory: 128M
    read_only: true
    tmpfs:
      - /tmp:size=10M,noexec,nosuid
    cap_drop:
      - ALL
    cap_add:
      - NET_BIND_SERVICE
    security_opt:
      - no-new-privileges:true
    networks:
      - sandbox-net
    environment:
      - WASM_LOG=info
      - WASM_MEMORY_LIMIT=256m
    healthcheck:
      test: ["CMD", "wasmtime", "--dir=.", "/health.wasm"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 5s

  wasm-proxy:
    image: wasm-proxy:latest
    runtime: io.containerd.wasmtime.v1
    ports:
      - "8080:8080"
    deploy:
      resources:
        limits:
          cpus: '1.0'
          memory: 512M
    read_only: true
    tmpfs:
      - /tmp:size=50M
    cap_drop:
      - ALL
    networks:
      - sandbox-net
    depends_on:
      - wasm-worker

networks:
  sandbox-net:
    driver: bridge
    internal: false
    ipam:
      config:
        - subnet: 172.28.0.0/16
```

### 7.11.3 Orquestração com Kubernetes

```yaml
# wasm-pod.yaml
apiVersion: v1
kind: Pod
metadata:
  name: wasm-app
  labels:
    app: wasm-app
spec:
  runtimeClassName: wasmtime  # Usar runtime Wasm
  containers:
    - name: wasm-app
      image: wasm-app:latest
      resources:
        limits:
          memory: "256Mi"
          cpu: "500m"
        requests:
          memory: "128Mi"
          cpu: "250m"
      securityContext:
        runAsNonRoot: true
        runAsUser: 1000
        runAsGroup: 1000
        readOnlyRootFilesystem: true
        allowPrivilegeEscalation: false
        capabilities:
          drop:
            - ALL
      volumeMounts:
        - name: tmp
          mountPath: /tmp
  volumes:
    - name: tmp
      emptyDir:
        sizeLimit: 10Mi

---
# wasm-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: wasm-deployment
spec:
  replicas: 3
  selector:
    matchLabels:
      app: wasm-app
  template:
    metadata:
      labels:
        app: wasm-app
    spec:
      runtimeClassName: wasmtime
      containers:
        - name: wasm-app
          image: wasm-app:latest
          resources:
            limits:
              memory: "256Mi"
              cpu: "500m"
          securityContext:
            runAsNonRoot: true
            runAsUser: 1000
            readOnlyRootFilesystem: true
            allowPrivilegeEscalation: false
            capabilities:
              drop:
                - ALL
          ports:
            - containerPort: 8080
          livenessProbe:
            httpGet:
              path: /health
              port: 8080
            initialDelaySeconds: 5
            periodSeconds: 10
          readinessProbe:
            httpGet:
              path: /ready
              port: 8080
            initialDelaySeconds: 3
            periodSeconds: 5

---
# network-policy.yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: wasm-network-policy
spec:
  podSelector:
    matchLabels:
      app: wasm-app
  policyTypes:
    - Ingress
    - Egress
  ingress:
    - from:
        - podSelector:
            matchLabels:
              app: wasm-proxy
      ports:
        - protocol: TCP
          port: 8080
  egress:
    - to:
        - podSelector:
            matchLabels:
              app: wasm-worker
      ports:
        - protocol: TCP
          port: 8080
    - to:  # DNS
        - namespaceSelector: {}
      ports:
        - protocol: UDP
          port: 53
```

## 7.12 Tabela Comparativa de Segurança

### 7.12.1 Comparação Detalhada de Mecanismos

| Mecanismo | Isolamento de Memória | Isolamento de Processo | Isolamento de Rede | Isolamento de FS | Performance | Complexidade |
|-----------|----------------------|------------------------|-------------------|-----------------|-------------|--------------|
| **Wasm Sandbox** | Bounds checking em runtime | Impossível (single-threaded) | Sem acesso sem WASI | Sem acesso sem WASI | Excelente | Baixa |
| **Linux Namespaces** | Separação de espaço de endereço | PID namespace | Network namespace | Mount namespace | Boa | Média |
| **seccomp-bpf** | N/A | Filtragem de syscalls | Filtragem de syscalls | Filtragem de syscalls | Excelente | Média |
| **gVisor** | Interceptação em user-space | Kernel em user-space | Pilha de rede em user-space | Filesystem em user-space | Boa | Alta |
| **Firecracker** | Virtualização completa | VM separada | Interface virtual | Disco virtual | Média | Alta |
| **Docker+Wasm** | Bounds checking + namespaces | Namespaces combinados | Network namespace | Overlay filesystem | Boa | Média |
| **Intel SGX** | Enclave isolado | Enclave isolado | Sem rede direta | Sem FS direto | Média | Muito Alta |

### 7.12.2 Casos de Uso Recomendados

| Caso de Uso | Mecanismo Recomendado | Justificativa |
|-------------|----------------------|---------------|
| **Serverless functions** | Wasm + Docker | Startup rápido, isolamento forte |
| **Edge computing** | Wasm + Firecracker | Segurança de VM com sobrecarga mínima |
| **Multi-tenant** | Wasm + Namespaces | Isolamento granular por tenant |
| **Browser extensions** | Wasm puro | Sandbox nativo do browser |
| **Microservices** | Docker + seccomp | Balance entre segurança e performance |
| **High security** | Firecracker + seccomp | Defesa em profundidade |
| **IoT/Embedded** | Wasm + cgroups | Recursos limitados |

### 7.12.3 Matriz de Decisão

```markdown
## Decidindo o Mecanismo de Sandboxing

### Pergunta 1: O código é executado no browser?
- SIM → Wasm puro (sandbox nativo do browser)
- NÃO → Pergunta 2

### Pergunta 2: Precisa de isolamento de kernel?
- SIM → Pergunta 3
- NÃO → Wasm + Namespaces

### Pergunta 3: Precisa de isolamento forte entre tenants?
- SIM → Firecracker microVM
- NÃO → Pergunta 4

### Pergunta 4: Quer baixa sobrecarga de memória?
- SIM → Wasm + seccomp-bpf
- NÃO → gVisor ou Docker+Wasm

### Pergunta 5: Precisa de snapshots rápidos?
- SIM → Firecracker
- NÃO → Docker+Wasm ou gVisor
```

### 7.12.4 Benchmarks de Performance

```bash
# Script de benchmark para comparar mecanismos de sandboxing

#!/bin/bash

echo "=== Benchmark de Sandboxing ==="
echo ""

# Função para medir tempo de startup
measure_startup() {
    local name=$1
    local command=$2
    
    echo "Testando: $name"
    
    # Medir 10 startups
    total=0
    for i in {1..10}; do
        start=$(date +%s%N)
        eval "$command" > /dev/null 2>&1
        end=$(date +%s%N)
        elapsed=$(( (end - start) / 1000000 ))
        total=$((total + elapsed))
    done
    
    avg=$((total / 10))
    echo "  Tempo médio de startup: ${avg}ms"
    echo ""
}

# Função para medir consumo de memória
measure_memory() {
    local name=$1
    local command=$2
    
    echo "Testando memória: $name"
    
    # Executar e medir pico de memória
    /usr/bin/time -v $command 2>&1 | grep "Maximum resident" | awk '{print "  Memória máxima: " $6 "KB"}'
    echo ""
}

# Benchmark: Processo nativo
measure_startup "Processo nativo" "echo test"

# Benchmark: Docker tradicional
measure_startup "Docker tradicional" \
    "docker run --rm alpine echo test"

# Benchmark: Docker com Wasm
measure_startup "Docker + Wasm" \
    "docker run --runtime=io.containerd.wasmtime.v1 --rm wasm-app"

# Benchmark: gVisor
measure_startup "gVisor" \
    "docker run --runtime=runsc --rm alpine echo test"

# Benchmark: Firecracker (se disponível)
if command -v firecracker &> /dev/null; then
    measure_startup "Firecracker" \
        "firecracker --api-sock /tmp/firecracker.sock"
fi

echo "=== Fim do Benchmark ==="
```

## 7.13 Padrões Avançados de Sandboxing

### 7.13.1 Defense in Depth para Wasm

Uma abordagem de defesa em profundidade combina múltiplos mecanismos de segurança:

```c
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <seccomp.h>
#include <sys/resource.h>
#include <sys/mount.h>
#include <sys/wait.h>
#include <sched.h>
#include <signal.h>
#include <fcntl.h>

#define STACK_SIZE (1024 * 1024)
static char child_stack[STACK_SIZE];

typedef struct {
    long memory_limit;
    long cpu_time_limit;
    int max_processes;
    int enable_network;
    char *allowed_paths[100];
    int num_allowed_paths;
} SandboxConfig;

int setup_layer1_namespaces(SandboxConfig *config) {
    // Camada 1: Namespaces do Linux
    int flags = CLONE_NEWPID |    // Isolar processos
                CLONE_NEWNS |     // Isolar filesystem
                CLONE_NEWUTS |    // Isolar hostname
                CLONE_NEWIPC |    // Isolar IPC
                CLONE_NEWUSER;    // Isolar usuários
    
    if (!config->enable_network) {
        flags |= CLONE_NEWNET;    // Isolar rede se desabilitado
    }
    
    // Nota: Na prática, esses flags seriam usados no clone()
    // Aqui apenas documentamos a intenção
    printf("Camada 1: Namespaces configurados (flags: 0x%x)\n", flags);
    
    return 0;
}

int setup_layer2_seccomp() {
    // Camada 2: Filtros seccomp-bpf
    scmp_filter_ctx ctx = seccomp_init(SCMP_ACT_KILL);
    if (ctx == NULL) {
        perror("seccomp_init");
        return -1;
    }
    
    // Permitir apenas chamadas essenciais
    seccomp_rule_add(ctx, SCMP_ACT_ALLOW, SCMP_SYS(read), 0);
    seccomp_rule_add(ctx, SCMP_ACT_ALLOW, SCMP_SYS(write), 0);
    seccomp_rule_add(ctx, SCMP_ACT_ALLOW, SCMP_SYS(close), 0);
    seccomp_rule_add(ctx, SCMP_ACT_ALLOW, SCMP_SYS(exit), 0);
    seccomp_rule_add(ctx, SCMP_ACT_ALLOW, SCMP_SYS(exit_group), 0);
    seccomp_rule_add(ctx, SCMP_ACT_ALLOW, SCMP_SYS(brk), 0);
    seccomp_rule_add(ctx, SCMP_ACT_ALLOW, SCMP_SYS(mmap), 0);
    seccomp_rule_add(ctx, SCMP_ACT_ALLOW, SCMP_SYS(munmap), 0);
    seccomp_rule_add(ctx, SCMP_ACT_ALLOW, SCMP_SYS(mprotect), 0);
    seccomp_rule_add(ctx, SCMP_ACT_ALLOW, SCMP_SYS(clock_gettime), 0);
    seccomp_rule_add(ctx, SCMP_ACT_ALLOW, SCMP_SYS(nanosleep), 0);
    
    // Bloquear operações perigosas
    seccomp_rule_add(ctx, SCMP_ACT_KILL, SCMP_SYS(execve), 0);
    seccomp_rule_add(ctx, SCMP_ACT_KILL, SCMP_SYS(fork), 0);
    seccomp_rule_add(ctx, SCMP_ACT_KILL, SCMP_SYS(clone), 0);
    seccomp_rule_add(ctx, SCMP_ACT_KILL, SCMP_SYS(ptrace), 0);
    seccomp_rule_add(ctx, SCMP_ACT_KILL, SCMP_SYS(socket), 0);
    seccomp_rule_add(ctx, SCMP_ACT_KILL, SCMP_SYS(connect), 0);
    seccomp_rule_add(ctx, SCMP_ACT_KILL, SCMP_SYS(bind), 0);
    seccomp_rule_add(ctx, SCMP_ACT_KILL, SCMP_SYS(reboot), 0);
    seccomp_rule_add(ctx, SCMP_ACT_KILL, SCMP_SYS(sethostname), 0);
    
    if (seccomp_load(ctx) != 0) {
        perror("seccomp_load");
        seccomp_release(ctx);
        return -1;
    }
    
    seccomp_release(ctx);
    printf("Camada 2: Filtros seccomp carregados\n");
    
    return 0;
}

int setup_layer3_limits(SandboxConfig *config) {
    // Camada 3: Limites de recursos
    struct rlimit rl;
    
    // Limite de memória
    if (config->memory_limit > 0) {
        rl.rlim_cur = config->memory_limit;
        rl.rlim_max = config->memory_limit;
        setrlimit(RLIMIT_AS, &rl);
        printf("  Memória: %ld bytes\n", config->memory_limit);
    }
    
    // Limite de CPU
    if (config->cpu_time_limit > 0) {
        rl.rlim_cur = config->cpu_time_limit;
        rl.rlim_max = config->cpu_time_limit + 1;
        setrlimit(RLIMIT_CPU, &rl);
        printf("  CPU: %ld segundos\n", config->cpu_time_limit);
    }
    
    // Limite de processos
    rl.rlim_cur = config->max_processes;
    rl.rlim_max = config->max_processes;
    setrlimit(RLIMIT_NPROC, &rl);
    printf("  Processos: %d\n", config->max_processes);
    
    // Limite de arquivos abertos
    rl.rlim_cur = 64;
    rl.rlim_max = 64;
    setrlimit(RLIMIT_NOFILE, &rl);
    printf("  Arquivos abertos: 64\n");
    
    // Limite de tamanho de arquivo
    rl.rlim_cur = 10 * 1024 * 1024;  // 10MB
    rl.rlim_max = 10 * 1024 * 1024;
    setrlimit(RLIMIT_FSIZE, &rl);
    printf("  Tamanho de arquivo: 10MB\n");
    
    printf("Camada 3: Limites de recursos configurados\n");
    
    return 0;
}

int setup_layer4_filesystem(SandboxConfig *config) {
    // Camada 4: Isolamento de filesystem
    mkdir("/tmp/deep-sandbox", 0755);
    
    // Montar rootfs mínimo
    mount("tmpfs", "/tmp/deep-sandbox", "tmpfs", 0, 
          "size=50M,mode=0755,noexec,nosuid,nodev");
    
    // Criar estrutura de diretório
    mkdir("/tmp/deep-sandbox/dev", 0755);
    mkdir("/tmp/deep-sandbox/proc", 0555);
    mkdir("/tmp/deep-sandbox/tmp", 01777);
    mkdir("/tmp/deep-sandbox/app", 0755);
    
    // Montar dispositivos mínimos
    mknod("/tmp/deep-sandbox/dev/null", 0666 | S_IFCHR, makedev(1, 3));
    mknod("/tmp/deep-sandbox/dev/zero", 0666 | S_IFCHR, makedev(1, 5));
    mknod("/tmp/deep-sandbox/dev/random", 0666 | S_IFCHR, makedev(1, 8));
    mknod("/tmp/deep-sandbox/dev/urandom", 0666 | S_IFCHR, makedev(1, 9));
    
    // Montar /proc
    mount("proc", "/tmp/deep-sandbox/proc", "proc", 0, NULL);
    
    // Bind mount para módulos Wasm (somente leitura)
    mount("/usr/share/wasm-modules", "/tmp/deep-sandbox/app", 
          NULL, MS_BIND | MS_RDONLY, NULL);
    
    printf("Camada 4: Filesystem isolado configurado\n");
    
    return 0;
}

static int child_fn(void *arg) {
    SandboxConfig *config = (SandboxConfig *)arg;
    
    printf("Filho: Iniciando sandbox em profundidade\n");
    
    // Aplicar camadas de segurança
    setup_layer2_seccomp();
    setup_layer3_limits(config);
    setup_layer4_filesystem(config);
    
    // Entrar no sandbox
    chroot("/tmp/deep-sandbox");
    chdir("/");
    
    printf("Filho: Dentro do sandbox profundo\n");
    printf("Filho: PID = %d\n", getpid());
    
    // Executar módulo Wasm
    execlp("wasmtime", "wasmtime", "/app/module.wasm", NULL);
    perror("execlp");
    
    return 1;
}

int main() {
    printf("=== Sandbox em Profundidade ===\n\n");
    
    SandboxConfig config = {
        .memory_limit = 256 * 1024 * 1024,  // 256MB
        .cpu_time_limit = 30,                 // 30 segundos
        .max_processes = 50,
        .enable_network = 0,
        .num_allowed_paths = 0
    };
    
    printf("Configuração:\n");
    printf("  Memória: 256MB\n");
    printf("  CPU: 30s\n");
    printf("  Processos: 50\n");
    printf("  Rede: Desabilitada\n\n");
    
    // Criar processo isolado
    int flags = CLONE_NEWPID | CLONE_NEWNS | CLONE_NEWUTS | 
                CLONE_NEWIPC | CLONE_NEWUSER | CLONE_NEWNET | SIGCHLD;
    
    pid_t pid = clone(child_fn, 
                      child_stack + STACK_SIZE,
                      flags, 
                      &config);
    
    if (pid == -1) {
        perror("clone");
        return 1;
    }
    
    printf("Pai: Sandbox criado (PID: %d)\n", pid);
    
    int status;
    waitpid(pid, &status, 0);
    
    if (WIFEXITED(status)) {
        printf("Pai: Sandbox terminou com código %d\n", 
               WEXITSTATUS(status));
    }
    
    // Limpar
    umount2("/tmp/deep-sandbox/proc", MNT_DETACH);
    umount2("/tmp/deep-sandbox/app", MNT_DETACH);
    umount2("/tmp/deep-sandbox", MNT_DETACH);
    
    return 0;
}
```

### 7.13.2 Padrão de Sandboxing para Produção

```yaml
# config/sandbox-production.yaml
apiVersion: sandboxing.dev/v1
kind: WasmSandbox
metadata:
  name: production-sandbox
spec:
  # Runtime configuration
  runtime:
    engine: wasmtime
    version: "14.0"
    
  # Resource limits
  resources:
    memory:
      limit: 512Mi
      request: 256Mi
      swap: false
    cpu:
      limit: "2.0"
      request: "0.5"
    storage:
      limit: 1Gi
    pids:
      limit: 100
      
  # Security context
  security:
    runAsNonRoot: true
    runAsUser: 1000
    runAsGroup: 1000
    readOnlyRootFilesystem: true
    allowPrivilegeEscalation: false
    capabilities:
      drop:
        - ALL
    seccompProfile:
      type: RuntimeDefault
      
  # Network isolation
  network:
    enabled: false
    allowedPorts: []
    dnsPolicy: None
    
  # Filesystem isolation
  filesystem:
    rootfs:
      type: overlay
      upperLayer: tmpfs
      size: 100Mi
    volumes:
      - name: app
        mountPath: /app
        readOnly: true
        size: 50Mi
      - name: tmp
        mountPath: /tmp
        size: 10Mi
        
  # Monitoring
  monitoring:
    enabled: true
    metrics:
      - memory_usage
      - cpu_usage
      - network_bytes
      - disk_io
    alerts:
      - metric: memory_usage
        threshold: 90%
        action: restart
      - metric: cpu_usage
        threshold: 80%
        action: throttle
        
  # Audit logging
  audit:
    enabled: true
    logPath: /var/log/sandbox/audit.log
    events:
      - syscall_denied
      - memory_violation
      - resource_limit
      - network_blocked
```

### 7.13.3 Testes de Segurança para Sandboxing

```python
import unittest
import subprocess
import os
import signal
import time
import resource

class WasmSandboxSecurityTests(unittest.TestCase):
    """Testes de segurança para sandboxing de Wasm"""
    
    def setUp(self):
        """Configurar ambiente de teste"""
        self.sandbox_cmd = [
            "wasmtime",
            "--dir=.",
            "--env=TESTING=1",
            "test_module.wasm"
        ]
        self.timeout = 10  # segundos
        
    def test_memory_limit(self):
        """Testar se o limite de memória é respeitado"""
        # Criar módulo que tenta alocar muita memória
        result = subprocess.run(
            self.sandbox_cmd + ["--memory=64M"],
            capture_output=True,
            text=True,
            timeout=self.timeout
        )
        
        # Deve falhar ou ser limitado
        self.assertIn("memory", result.stderr.lower())
        
    def test_cpu_limit(self):
        """Testar se o limite de CPU é respeitado"""
        # Criar módulo com loop infinito
        start = time.time()
        result = subprocess.run(
            self.sandbox_cmd + ["--cpu=1"],
            capture_output=True,
            text=True,
            timeout=5
        )
        elapsed = time.time() - start
        
        # Deve terminar em ~1 segundo
        self.assertLess(elapsed, 2.0)
        
    def test_filesystem_isolation(self):
        """Testar isolamento do filesystem"""
        # Tentar acessar arquivos do host
        result = subprocess.run(
            self.sandbox_cmd + ["--test-fs-access"],
            capture_output=True,
            text=True,
            timeout=self.timeout
        )
        
        # Não deve conseguir ler /etc/passwd
        self.assertNotIn("root:", result.stdout)
        
    def test_network_isolation(self):
        """Testar isolamento de rede"""
        # Tentar fazer conexão de rede
        result = subprocess.run(
            self.sandbox_cmd + ["--test-network"],
            capture_output=True,
            text=True,
            timeout=self.timeout
        )
        
        # Deve falhar ao conectar
        self.assertIn("denied", result.stderr.lower())
        
    def test_process_isolation(self):
        """Testar impossibilidade de criar processos"""
        # Tentar fork
        result = subprocess.run(
            self.sandbox_cmd + ["--test-fork"],
            capture_output=True,
            text=True,
            timeout=self.timeout
        )
        
        # Deve falhar
        self.assertNotEqual(result.returncode, 0)
        
    def test_symlink_escape(self):
        """Testar se escape via symlink não funciona"""
        # Criar symlink para /etc
        os.symlink("/etc", "/tmp/symlink_test")
        
        result = subprocess.run(
            self.sandbox_cmd + ["--test-symlink"],
            capture_output=True,
            text=True,
            timeout=self.timeout
        )
        
        # Não deve conseguir acessar
        self.assertNotIn("root:", result.stdout)
        
        # Limpar
        os.unlink("/tmp/symlink_test")
        
    def test_signal_handling(self):
        """Testar tratamento de sinais"""
        # Enviar SIGKILL
        proc = subprocess.Popen(self.sandbox_cmd)
        time.sleep(0.1)
        
        os.kill(proc.pid, signal.SIGKILL)
        
        # Deve terminar
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            self.fail("Processo não terminou após SIGKILL")
            
    def test_resource_exhaustion(self):
        """Testar comportamento com exaustão de recursos"""
        # Criar módulo que consome muitos recursos
        result = subprocess.run(
            self.sandbox_cmd + ["--test-exhaustion"],
            capture_output=True,
            text=True,
            timeout=self.timeout
        )
        
        # Deve ser limitado pelo sandbox
        self.assertNotEqual(result.returncode, 0)
        
    def test_temp_file_cleanup(self):
        """Testar limpeza de arquivos temporários"""
        # Criar arquivos temporários
        result = subprocess.run(
            self.sandbox_cmd + ["--test-temp-files"],
            capture_output=True,
            text=True,
            timeout=self.timeout
        )
        
        # Verificar que arquivos temporários foram limpos
        temp_dir = "/tmp/wasm-sandbox/"
        if os.path.exists(temp_dir):
            files = os.listdir(temp_dir)
            self.assertEqual(len(files), 0)
            
    def test_audit_logging(self):
        """Testar se eventos de segurança são logados"""
        # Executar operações que devem ser logadas
        result = subprocess.run(
            self.sandbox_cmd + ["--test-audit"],
            capture_output=True,
            text=True,
            timeout=self.timeout
        )
        
        # Verificar se log existe e contém eventos
        log_path = "/var/log/sandbox/audit.log"
        if os.path.exists(log_path):
            with open(log_path, 'r') as f:
                log_content = f.read()
                self.assertIn("syscall_denied", log_content)

if __name__ == '__main__':
    unittest.main()
```

## 7.14 Considerações Finais

O sandboxing e isolamento são componentes fundamentais da segurança em WebAssembly. A combinação adequada de mecanismos de isolamento pode proporcionar segurança robusta com sobrecarga mínima.

Pontos-chave para lembrar:

1. **Wasm fornece sandboxing por design**: O modelo de memória linear e a ausência de acesso direto a recursos do sistema oferecem uma base sólida de segurança.

2. **Defesa em profundidade é essencial**: Nenhum mecanismo de isolamento é perfeito sozinho. A combinação de namespaces, seccomp, limites de recursos e isolamento de filesystem proporciona segurança robusta.

3. **Escolha o mecanismo certo para o caso de uso**: Diferentes cenários requerem diferentes níveis de isolamento. Browser, edge, cloud e IoT têm necessidades distintas.

4. **Monitore sempre**: Sandbox sem monitoramento é sandbox cego. Implemente logging, métricas e alertas para detectar comportamento suspeito.

5. **Teste regularmente**: Implemente testes automatizados para validar as propriedades de segurança do seu sandbox.

6. **Mantenha-se atualizado**: Mecanismos de sandboxing evoluem rapidamente. Acompanhe atualizações de segurança e melhores práticas.

O sandboxing eficaz não é apenas sobre implementar tecnologias, mas sobre entender os trade-offs entre segurança, performance e usabilidade. O objetivo final é criar ambientes onde código potencialmente inseguro pode ser executado com risco mínimo para o sistema host.

No próximo capítulo, exploraremos o Component Model do WebAssembly, que estende as capacidades de isolamento com interfaces tipadas e composição segura de módulos.
