# Capítulo 5: Compilação C++ para WebAssembly

## Sumário

- [5.1 Configuração do Emscripten SDK](#51-configuração-do-emscripten-sdk)
- [5.2 Flags de compilação emcc](#52-flags-de-compilação-emcc)
- [5.3 Embind para C++/JS](#53-embind-para-cjs)
- [5.4 Asyncify](#54-asyncify)
- [5.5 Gerenciamento de memória](#55-gerenciamento-de-memória)
- [5.6 Sistema de arquivos (MEMFS/FS)](#56-sistema-de-arquivos-memfsfs)
- [5.7 Integração WebGL](#57-integração-webgl)
- [5.8 Áudio](#58-áudio)
- [5.9 Threading (SharedArrayBuffer)](#59-threading-sharedarraybuffer)
- [5.10 Flags de otimização](#510-flags-de-otimização)
- [5.11 Exemplo de aplicação completa](#511-exemplo-de-aplicação-completa)

---

## 5.1 Configuração do Emscripten SDK

### Introdução ao Emscripten

O Emscripten é um compilador LLVM-to-WebAssembly que permite compilar código C, C++ e Rust para WebAssembly. Criado por Alon Zakai em 2012, o Emscripten foi a primeira ferramenta a demonstrar que linguagens de sistema podiam ser compiladas para rodar no navegador de forma eficiente.

O Emscripten funciona como um toolchain completo, fornecendo um compilador (emcc), um linker e uma biblioteca padrão adaptada para WebAssembly. Ele inclui uma implementação da biblioteca C padrão (musl libc), suporte a OpenGL ES 2.0/3.0, e abstrações para APIs do navegador como Canvas, WebGL, Áudio e Redes.

### Instalação do Emscripten SDK

O Emscripten SDK (emsdk) é a forma recomendada de instalar e gerenciar o Emscripten. Ele permite instalar diferentes versões do compilador e alternar entre elas.

**Instalação em Unix-like (Linux, macOS, WSL)**:

```bash
# Clonar o repositório do emsdk
git clone https://github.com/emscripten-core/emsdk.git
cd emsdk

# Instalar a versão mais recente
./emsdk install latest

# Ativar a versão instalada
./emsdk activate latest

# Configurar o ambiente
source ./emsdk_env.sh
```

**Instalação em Windows**:

```bash
# Clonar o repositório
git clone https://github.com/emscripten-core/emsdk.git
cd emsdk

# Instalar a versão mais recente
emsdk install latest

# Ativar a versão instalada
emsdk activate latest

# Configurar o ambiente (PowerShell)
.\emsdk_env.ps1
```

### Verificação da instalação

Após a instalação, verifique se o compilador está funcionando:

```bash
# Verificar versão do compilador
emcc --version

# Verificar se o ambiente está configurado
echo $EMSDK
echo $EMSCRIPTEN

# Testar compilação
echo 'int main() { return 0; }' > test.c
emcc test.c -o test.html
```

### Estrutura do emsdk

O emsdk organiza as instalações da seguinte forma:

```
emsdk/
├── upstream/
│   ├── emscripten/
│   │   ├── emcc          # Compilador principal
│   │   ├── em++          # Compilador C++
│   │   ├── emar          # Archiver
│   │   ├── emranlib      # Ranlib
│   │   ├── emconfigure   # Wrapper para configure
│   │   ├── emmake        # Wrapper para make
│   │   └── system/
│   │       ├── include/  # Headers do sistema
│   │       └── lib/      # Bibliotecas do sistema
│   └── clang/
│       └── 16.0.0/       # Compilador Clang/LLVM
├── emsdk/
│   └── latest/           # Symlink para versão ativa
└── .emscripten           # Arquivo de configuração
```

### Gerenciamento de versões

O emsdk permite instalar e alternar entre múltiplas versões:

```bash
# Listar versões disponíveis
emsdk list

# Instalar uma versão específica
emsdk install 3.1.45

# Alternar entre versões
emsdk activate 3.1.45

# Desinstalar uma versão
emsdk uninstall 2.0.30
```

### Configuração do PATH

Para usar o Emscripten permanentemente, adicione ao seu shell profile:

```bash
# Adicionar ao ~/.bashrc ou ~/.zshrc
source /path/to/emsdk/emsdk_env.sh
```

Ou crie um alias:

```bash
alias emsdk='source /path/to/emsdk/emsdk_env.sh'
```

### Integração com build systems

O Emscripten fornece wrappers para build systems populares:

**CMake**:

```bash
# Configurar projeto com Emscripten
emcmake cmake -B build -DCMAKE_BUILD_TYPE=Release

# Compilar
cmake --build build
```

**Make**:

```bash
# Usar emmake em vez de make
emmake make

# Ou configurar Makefile para usar emcc
CC=emcc
CXX=em++
```

**configure**:

```bash
# Usar emconfigure em vez de ./configure
emconfigure ./configure
```

### Container Docker

Para ambientes reproduzíveis, use o container oficial:

```bash
# Usar imagem oficial do Emscripten
docker run --rm -v $(pwd):/src -u $(id -u):$(id -g) emsdk/emsdk:latest emcc main.cpp -o main.js

# Criar Dockerfile personalizado
FROM emsdk/emsdk:latest
WORKDIR /src
COPY . .
RUN emcc main.cpp -o main.js
```

### Configuração do .emscripten

O arquivo ~/.emscripten configura o comportamento do Emscripten:

```python
# ~/.emscripten
import os

# Caminhos padrão
EMSCRIPTEN_ROOT = '/path/to/emsdk/upstream/emscripten'
LLVM_ROOT = '/path/to/emsdk/upstream/clang/16.0.0/bin'
BINARYEN_ROOT = '/path/to/emsdk/upstream/binaryen'
NODE_JS = '/path/to/emsdk/node/16.20.0_64bit/bin/node'

# Otimizações padrão
COMPILER_OPTS = ['-O2']
```

### Solução de problemas

**Erro: "emcc not found"**:

```bash
# Verificar se o ambiente está configurado
source ./emsdk_env.sh

# Verificar PATH
echo $PATH | grep emsdk
```

**Erro: "LLVM backend not found"**:

```bash
# Reinstalar o toolchain
./emsdk install latest --force
./emsdk activate latest
```

**Erro de permissão**:

```bash
# Corrigir permissões (Unix)
chmod +x ./emsdk
chmod +x ./emsdk_env.sh
```

---

## 5.2 Flags de compilação emcc

### Visão geral do emcc

O emcc é o compilador principal do Emscripten. Ele funciona como um wrapper em torno do Clang/LLVM, adicionando suporte a WebAssembly e configurações específicas para o navegador. O emcc aceita as mesmas flags do Clang, além de flags específicas do Emscripten.

### Flags básicas de compilação

**Compilação simples**:

```bash
# Compilar C para HTML
emcc main.c -o main.html

# Compilar C++ para HTML
em++ main.cpp -o main.html

# Compilar sem HTML (apenas JS + WASM)
emcc main.c -o main.js

# Compilar para módulo ES
emcc main.c -o main.mjs
```

**Flags de otimização**:

```bash
# Sem otimização (debug)
emcc -O0 main.c -o main.js

# Otimização básica
emcc -O1 main.c -o main.js

# Otimização padrão
emcc -O2 main.c -o main.js

# Otimização máxima
emcc -O3 main.c -o main.js

# Otimizar para tamanho
emcc -Os main.c -o main.js

# Otimizar para tamanho máximo
emcc -Oz main.c -o main.js
```

### Flags de linguagem

```bash
# Especificar padrão C
emcc -std=c11 main.c -o main.js

# Especificar padrão C++
em++ -std=c++17 main.cpp -o main.js

# Habilitar extensões GNU
emcc -std=gnu11 main.c -o main.js

# Definir macros
emcc -DVERSION="1.0" -DDEBUG main.c -o main.js

# Incluir headers
emcc -I/path/to/headers main.c -o main.js
```

### Flags de warnings e erros

```bash
# Habilitar todos os warnings
emcc -Wall -Wextra main.c -o main.js

# Tratar warnings como erros
emcc -Werror main.c -o main.js

# Desabilitar warnings específicos
emcc -Wno-unused-variable main.c -o main.js

# Mostrar todos os warnings
emcc -Weverything main.c -o main.js
```

### Flags do Emscripten

**Saída**:

```bash
# Gerar HTML com loader
emcc main.c -o main.html

# Gerar apenas JavaScript
emcc main.c -o main.js

# Gerar módulo ES
emcc main.c -o main.mjs

# Gerar WASM separado
emcc main.c -o main.js --output wasm
```

**Link-time**:

```bash
# Linkar bibliotecas adicionais
emcc main.c -lGL -o main.js

# Definir memória inicial
emcc main.c -s INITIAL_MEMORY=16MB -o main.js

# Definir memória máxima
emcc main.c -s MAXIMUM_MEMORY=256MB -o main.js
```

### Flags de debug

```bash
# Incluir informações de debug
emcc -g4 main.c -o main.js

# Gerar source maps
emcc -g4 --source-map-base http://localhost:8080/ main.c -o main.js

# Habilitar assert
emcc -s ASSERTIONS=1 main.c -o main.js

# Habilitar debug de memória
emcc -s SAFE_HEAP=1 main.c -o main.js
```

### Flags de memória

```bash
# Tamanho inicial da memória
emcc -s INITIAL_MEMORY=16MB main.c -o main.js

# Tamanho máximo da memória
emcc -s MAXIMUM_MEMORY=256MB main.c -o main.js

#允许 memória dinâmica
emcc -s ALLOW_MEMORY_GROWTH=1 main.c -o main.js

# Tamanho do heap
emcc -s TOTAL_STACK=5MB main.c -o main.js
```

### Flags de funcionalidade

```bash
# Habilitar SharedArrayBuffer
emcc -s USE_PTHREADS=1 main.c -o main.js

# Habilitar WASI
emcc -s WASM=1 main.c -o main.js

# Habilitar Asyncify
emcc -s ASYNCIFY=1 main.c -o main.js

# Habilitar Embind
emcc --bind main.c -o main.js

# Habilitar ASSERTIONS
emcc -s ASSERTIONS=1 main.c -o main.js
```

### Flags de segurança

```bash
# Habilitar stack canary
emcc -s STACK_OVERFLOW_CHECK=2 main.c -o main.js

# Habilitar Safe Heap
emcc -s SAFE_HEAP=1 main.c -o main.js

# Habilitar stack protection
emcc -fstack-protector-all main.c -o main.js

# Habilitar address sanitizer
emcc -fsanitize=address main.c -o main.js
```

### Exemplos de compilação

**Projeto simples**:

```bash
# Compilar com otimizações
emcc -O2 -s WASM=1 -s EXPORTED_RUNTIME_METHODS='["ccall","cwrap"]' main.c -o main.js
```

**Projeto com bibliotecas**:

```bash
# Compilar com OpenGL e áudio
em++ -O2 -s USE_SDL=2 -s USE_WEBGL2=1 main.cpp -o main.js
```

**Projeto com threading**:

```bash
# Compilar com threads
em++ -O2 -s USE_PTHREADS=1 -s PTHREAD_POOL_SIZE=4 main.cpp -o main.js
```

### Makefile exemplo

```makefile
CC = emcc
CXX = em++
FLAGS = -O2 -s WASM=1 -s EXPORTED_RUNTIME_METHODS='["ccall","cwrap"]'
LIBS = -s USE_SDL=2

all: main.html

main.html: main.c
	$(CC) $(FLAGS) $(LIBS) main.c -o main.html

clean:
	rm -f main.html main.js main.wasm
```

### CMakeLists.txt exemplo

```cmake
cmake_minimum_required(VERSION 3.13)
project(MyProject)

set(CMAKE_CXX_STANDARD 17)

# Compilar para WebAssembly
add_executable(main main.cpp)

# Flags do Emscripten
target_link_options(main PRIVATE
    -O2
    -s WASM=1
    -s EXPORTED_RUNTIME_METHODS='["ccall","cwrap"]'
    -s ALLOW_MEMORY_GROWTH=1
)

# Bibliotecas
target_link_libraries(main PRIVATE
    -s USE_SDL=2
    -s USE_WEBGL2=1
)
```

---

## 5.3 Embind para C++/JS

### Introdução ao Embind

O Embind é a ferramenta de FFI (Foreign Function Interface) do Emscripten que permite expor funções e classes C++ para JavaScript de forma idiomática. Diferente de outras abordagens que requerem código boilerplate extenso, o Embind usa templates C++ e metaprogramação para gerar automaticamente os bindings necessários.

O Embind foi projetado para ser fácil de usar e difícil de usar incorretamente. Ele gerencia automaticamente a memória entre C++ e JavaScript, suporta herança, polimorfismo, e conversão de tipos complexos.

### Configuração básica

Para usar Embind, compile com a flag --bind:

```bash
em++ main.cpp --bind -o main.js
```

### Exposição de funções

```cpp
#include <emscripten/bind.h>

// Função simples
int add(int a, int b) {
    return a + b;
}

// Função com strings
std::string greet(const std::string& name) {
    return "Hello, " + name + "!";
}

// Função com vetores
double sum(const std::vector<double>& numbers) {
    double total = 0;
    for (double n : numbers) {
        total += n;
    }
    return total;
}

EMSCRIPTEN_BINDINGS(my_module) {
    emscripten::function("add", &add);
    emscripten::function("greet", &greet);
    emscripten::function("sum", &sum);
}
```

Uso no JavaScript:

```javascript
Module.onRuntimeInitialized = () => {
    console.log(Module.add(2, 3));           // 5
    console.log(Module.greet("World"));      // "Hello, World!"
    console.log(Module.sum([1, 2, 3, 4]));   // 10
};
```

### Exposição de classes

```cpp
#include <emscripten/bind.h>

class Calculator {
private:
    double value;
    std::vector<double> history;

public:
    Calculator() : value(0.0) {}

    void add(double n) {
        value += n;
        history.push_back(value);
    }

    void subtract(double n) {
        value -= n;
        history.push_back(value);
    }

    double getValue() const {
        return value;
    }

    std::vector<double> getHistory() const {
        return history;
    }

    void reset() {
        value = 0.0;
        history.clear();
    }
};

EMSCRIPTEN_BINDINGS(my_module) {
    emscripten::class_<Calculator>("Calculator")
        .constructor<>()
        .function("add", &Calculator::add)
        .function("subtract", &Calculator::subtract)
        .function("getValue", &Calculator::getValue)
        .function("getHistory", &Calculator::getHistory)
        .function("reset", &Calculator::reset);
}
```

Uso no JavaScript:

```javascript
const calc = new Module.Calculator();
calc.add(10);
calc.add(5);
calc.subtract(3);
console.log(calc.getValue());      // 12
console.log(calc.getHistory());    // [10, 15, 12]
calc.reset();
```

### Propriedades e métodos estáticos

```cpp
#include <emscripten/bind.h>

class Config {
public:
    std::string name;
    int version;

    Config() : name("default"), version(1) {}

    static Config create(const std::string& name, int version) {
        Config config;
        config.name = name;
        config.version = version;
        return config;
    }
};

EMSCRIPTEN_BINDINGS(my_module) {
    emscripten::class_<Config>("Config")
        .constructor<>()
        .property("name", &Config::name)
        .property("version", &Config::version)
        .class_function("create", &Config::create);
}
```

### Herança e polimorfismo

```cpp
#include <emscripten/bind.h>

class Shape {
public:
    virtual ~Shape() = default;
    virtual double area() const = 0;
    virtual std::string type() const = 0;
};

class Circle : public Shape {
private:
    double radius;

public:
    Circle(double r) : radius(r) {}

    double area() const override {
        return 3.14159 * radius * radius;
    }

    std::string type() const override {
        return "circle";
    }

    double getRadius() const {
        return radius;
    }
};

class Rectangle : public Shape {
private:
    double width, height;

public:
    Rectangle(double w, double h) : width(w), height(h) {}

    double area() const override {
        return width * height;
    }

    std::string type() const override {
        return "rectangle";
    }
};

EMSCRIPTEN_BINDINGS(my_module) {
    emscripten::class_<Shape>("Shape")
        .function("area", &Shape::area)
        .function("type", &Shape::type);

    emscripten::class_<Circle, emscripten::base<Shape>>("Circle")
        .constructor<double>()
        .function("getRadius", &Circle::getRadius);

    emscripten::class_<Rectangle, emscripten::base<Shape>>("Rectangle")
        .constructor<double, double>();
}
```

### Smart pointers

```cpp
#include <emscripten/bind.h>
#include <memory>

class Resource {
public:
    Resource() { /* allocate */ }
    ~Resource() { /* deallocate */ }
    void process() { /* do work */ }
};

std::shared_ptr<Resource> createResource() {
    return std::make_shared<Resource>();
}

void useResource(std::shared_ptr<Resource> res) {
    res->process();
}

EMSCRIPTEN_BINDINGS(my_module) {
    emscripten::register_vector<double>("VectorDouble");
    emscripten::register_vector<std::string>("VectorString");

    emscripten::class_<Resource, std::shared_ptr<Resource>>("Resource")
        .constructor<>()
        .function("process", &Resource::process);

    emscripten::function("createResource", &createResource);
    emscripten::function("useResource", &useResource);
}
```

### Enumerações

```cpp
#include <emscripten/bind.h>

enum class Color {
    Red,
    Green,
    Blue,
    Yellow
};

std::string colorToString(Color color) {
    switch (color) {
        case Color::Red: return "red";
        case Color::Green: return "green";
        case Color::Blue: return "blue";
        case Color::Yellow: return "yellow";
    }
    return "unknown";
}

EMSCRIPTEN_BINDINGS(my_module) {
    emscripten::enum_<Color>("Color")
        .value("Red", Color::Red)
        .value("Green", Color::Green)
        .value("Blue", Color::Blue)
        .value("Yellow", Color::Yellow);

    emscripten::function("colorToString", &colorToString);
}
```

### Mapeamento de tipos

```cpp
#include <emscripten/bind.h>

// Mapear tipos C++ para JavaScript
EMSCRIPTEN_BINDINGS(my_module) {
    // Vetores
    emscripten::register_vector<int>("VectorInt");
    emscripten::register_vector<double>("VectorDouble");
    emscripten::register_vector<std::string>("VectorString");

    // Maps
    emscripten::register_map<std::string, int>("StringIntMap");

    // Pairs
    emscripten::register_pair<std::string, int>("StringIntPair");
}
```

### Valores e referências

```cpp
#include <emscripten/bind.h>

struct Point {
    double x, y;

    Point(double x, double y) : x(x), y(y) {}
};

EMSCRIPTEN_BINDINGS(my_module) {
    // Por valor (copia)
    emscripten::value_object<Point>("Point")
        .field("x", &Point::x)
        .field("y", &Point::y);

    // Por referência (sem cópia)
    emscripten::class_<Point>("PointRef")
        .constructor<double, double>()
        .property("x", &Point::x)
        .property("y", &Point::y);
}
```

### Overloads

```cpp
#include <emscripten/bind.h>

// Função com múltiplos overloads
void print(int value) {
    // ...
}

void print(const std::string& value) {
    // ...
}

void print(double value) {
    // ...
}

EMSCRIPTEN_BINDINGS(my_module) {
    emscripten::function("print_int", select_overload<void(int)>(&print));
    emscripten::function("print_string", select_overhold<void(const std::string&)>(&print));
    emscripten::function("print_double", select_overload<void(double)>(&print));
}
```

### Tratamento de erros

```cpp
#include <emscripten/bind.h>
#include <stdexcept>

void riskyOperation() {
    throw std::runtime_error("Something went wrong");
}

EMSCRIPTEN_BINDINGS(my_module) {
    emscripten::function("riskyOperation", &riskyOperation);
}
```

No JavaScript:

```javascript
try {
    Module.riskyOperation();
} catch (e) {
    console.error(e.message);  // "Something went wrong"
}
```

### Exemplo completo: Matrix Library

```cpp
#include <emscripten/bind.h>
#include <vector>
#include <cmath>

class Matrix {
private:
    std::vector<std::vector<double>> data;
    size_t rows, cols;

public:
    Matrix(size_t rows, size_t cols) : rows(rows), cols(cols) {
        data.resize(rows, std::vector<double>(cols, 0.0));
    }

    void set(size_t r, size_t c, double value) {
        if (r < rows && c < cols) {
            data[r][c] = value;
        }
    }

    double get(size_t r, size_t c) const {
        if (r < rows && c < cols) {
            return data[r][c];
        }
        return 0.0;
    }

    Matrix multiply(const Matrix& other) const {
        Matrix result(rows, other.cols);
        for (size_t i = 0; i < rows; i++) {
            for (size_t j = 0; j < other.cols; j++) {
                double sum = 0;
                for (size_t k = 0; k < cols; k++) {
                    sum += data[i][k] * other.data[k][j];
                }
                result.set(i, j, sum);
            }
        }
        return result;
    }

    Matrix transpose() const {
        Matrix result(cols, rows);
        for (size_t i = 0; i < rows; i++) {
            for (size_t j = 0; j < cols; j++) {
                result.set(j, i, data[i][j]);
            }
        }
        return result;
    }

    double determinant() const {
        if (rows != cols) return 0.0;
        if (rows == 1) return data[0][0];
        if (rows == 2) return data[0][0] * data[1][1] - data[0][1] * data[1][0];

        double det = 0;
        for (size_t j = 0; j < cols; j++) {
            Matrix minor(rows - 1, cols - 1);
            // ... calculate minor ...
            det += (j % 2 == 0 ? 1 : -1) * data[0][j] * minor.determinant();
        }
        return det;
    }

    size_t getRows() const { return rows; }
    size_t getCols() const { return cols; }
};

EMSCRIPTEN_BINDINGS(matrix) {
    emscripten::class_<Matrix>("Matrix")
        .constructor<size_t, size_t>()
        .function("set", &Matrix::set)
        .function("get", &Matrix::get)
        .function("multiply", &Matrix::multiply)
        .function("transpose", &Matrix::transpose)
        .function("determinant", &Matrix::determinant)
        .function("getRows", &Matrix::getRows)
        .function("getCols", &Matrix::getCols);
}
```

---

## 5.4 Asyncify

### Introdução ao Asyncify

Asyncify é uma funcionalidade do Emscripten que permite que código síncrono em C/C++ realize operações assíncronas (como I/O, promises, ou setTimeout) sem modificar a estrutura do código. O Asyncify transforma automaticamente o código síncrono em código assíncrono durante a compilação.

O Asyncify é especialmente útil para portar bibliotecas síncronas existentes para WebAssembly, onde operações de I/O são inherentemente assíncronas. Ele permite que o código C/C++ espere por promises JavaScript sem bloquear a thread principal do navegador.

### Configuração

```bash
em++ main.cpp -s ASYNCIFY=1 -o main.js
```

### Exemplo básico

```cpp
#include <emscripten.h>
#include <emscripten/asyncify.h>
#include <cstdio>

// Função que usa setTimeout via Asyncify
void doSomethingAsync() {
    emscripten_async_call([](void*) {
        printf("Async operation completed!\n");
    }, nullptr, 1000);  // 1 segundo de delay
}

// Função que usa fetch via Asyncify
void fetchData() {
    EMSCRIPTEN_async_wget2(
        "https://api.example.com/data",
        [](void* arg, void* data, int size) {
            printf("Data received: %d bytes\n", size);
        },
        [](void* arg) {
            printf("Error fetching data\n");
        },
        nullptr,
        "GET",
        true
    );
}

int main() {
    printf("Starting...\n");
    doSomethingAsync();
    fetchData();
    return 0;
}
```

### Asyncify com promises

```cpp
#include <emscripten.h>
#include <emscripten/asyncify.h>
#include <cstdio>

// Função que retorna uma promise JavaScript
EM_ASYNC_VAL(const char*) fetchString(const char* url) {
    // Asyncify automaticamente lida com a promise
    return emscripten_async_wget2_data(url, "GET", "", true);
}

// Função que usa a promise
void processUrl(const char* url) {
    const char* data = fetchString(url);
    printf("Data from %s: %s\n", url, data);
    free((void*)data);
}

int main() {
    processUrl("https://api.example.com/data");
    return 0;
}
```

### Asyncify com sleep

```cpp
#include <emscripten.h>
#include <emscripten/asyncify.h>
#include <cstdio>
#include <thread>

// Função que espera usando Asyncify
void asyncSleep(int ms) {
    emscripten_sleep(ms);
}

void backgroundTask() {
    for (int i = 0; i < 5; i++) {
        printf("Iteration %d\n", i);
        asyncSleep(1000);  // Espera 1 segundo
    }
    printf("Task completed!\n");
}

int main() {
    emscripten_async_call([](void*) {
        backgroundTask();
    }, nullptr, 0);
    return 0;
}
```

### Asyncify com operações assíncronas

```cpp
#include <emscripten.h>
#include <emscripten/asyncify.h>
#include <cstdio>

// Função que lida com operações assíncronas
EM_ASYNC_VAL(int) asyncOperation() {
    // Simular operação assíncrona
    emscripten_sleep(1000);
    return 42;
}

// Função que lida com múltiplas operações assíncronas
EM_ASYNC_VAL(void) processMultipleAsync() {
    int result1 = asyncOperation();
    int result2 = asyncOperation();
    int result3 = asyncOperation();

    printf("Results: %d, %d, %d\n", result1, result2, result3);
}

int main() {
    emscripten_async_call([](void*) {
        processMultipleAsync();
    }, nullptr, 0);
    return 0;
}
```

### Configurações avançadas do Asyncify

```bash
# Habilitar Asyncify com opções
em++ main.cpp \
    -s ASYNCIFY=1 \
    -s ASYNCIFY_IMPORTS=['env.asyncOperation'] \
    -o main.js
```

```cpp
// Definir imports assíncronos manualmente
extern "C" {
    EMSCRIPTEN_KEEPALIVE
    void asyncImport() {
        // Esta função será tratada como assíncrona
    }
}
```

### Asyncify com Web Workers

```cpp
#include <emscripten.h>
#include <emscripten/asyncify.h>
#include <emscripten/threading.h>
#include <cstdio>

void workerFunction() {
    printf("Worker started\n");
    emscripten_sleep(2000);  // Asyncify funciona em workers
    printf("Worker completed\n");
}

int main() {
    // Criar worker assíncrono
    emscripten_worker_start([](void* arg) {
        workerFunction();
    }, nullptr);

    return 0;
}
```

### Limitações do Asyncify

1. **Overhead**: Asyncify adiciona overhead significativo ao código
2. **Tamanho**: O binário resultante é maior devido ao código de transformação
3. **Performance**: Operações assíncronas têm custo de contexto
4. **Stack**: A pilha de chamadas pode ser interrompida em qualquer ponto

### Alternativas ao Asyncify

```cpp
// Alternativa 1: Usar callbacks diretamente
void fetchWithCallback(const char* url, void (*callback)(const char*)) {
    emscripten_async_wget2(
        url,
        [](void* arg, void* data, int size) {
            auto cb = reinterpret_cast<void (*)(const char*)>(arg);
            cb(static_cast<const char*>(data));
        },
        nullptr,
        callback,
        "GET",
        true
    );
}

// Alternativa 2: Usar状态机
enum class State {
    IDLE,
    FETCHING,
    PROCESSING,
    DONE
};

class AsyncFetcher {
private:
    State state = State::IDLE;

public:
    void start(const char* url) {
        state = State::FETCHING;
        // Iniciar fetch...
    }

    void onComplete(const char* data) {
        state = State::PROCESSING;
        // Processar dados...
        state = State::DONE;
    }
};
```

### Otimização do Asyncify

```bash
# Limitar imports assíncronos
em++ main.cpp \
    -s ASYNCIFY=1 \
    -s ASYNCIFY_IMPORTS=['env.fetch','env.sleep'] \
    -s ASYNCIFY_STACK_SIZE=65536 \
    -o main.js
```

---

## 5.5 Gerenciamento de memória

### Visão geral da memória no Wasm

O WebAssembly usa memória linear, um bloco contíguo de bytes endereçável. No Emscripten, a memória é gerenciada automaticamente, mas é importante entender como funciona para evitar vazios de memória e otimizar o uso de recursos.

### Alocação básica

```cpp
#include <cstdlib>
#include <cstdio>

int main() {
    // Alocação com malloc
    int* arr = (int*)malloc(100 * sizeof(int));
    if (!arr) {
        fprintf(stderr, "Memory allocation failed\n");
        return 1;
    }

    // Uso da memória
    for (int i = 0; i < 100; i++) {
        arr[i] = i * 2;
    }

    // Desalocação
    free(arr);
    return 0;
}
```

### Memória dinâmica

```cpp
#include <vector>
#include <cstdio>

int main() {
    // Vetor dinâmico
    std::vector<int> vec;
    for (int i = 0; i < 1000000; i++) {
        vec.push_back(i);
    }

    printf("Vector size: %zu\n", vec.size());
    printf("Vector capacity: %zu\n", vec.capacity());
    return 0;
}
```

### Configuração de memória

```bash
# Configurar memória inicial e máxima
emcc main.c \
    -s INITIAL_MEMORY=16MB \
    -s MAXIMUM_MEMORY=256MB \
    -s ALLOW_MEMORY_GROWTH=1 \
    -o main.js
```

### Monitoramento de memória

```cpp
#include <emscripten.h>
#include <cstdio>

extern "C" {
    EMSCRIPTEN_KEEPALIVE
    void printMemoryInfo() {
        // Obter informações de memória
        size_t total = emscripten_get_heap_size();
        size_t used = emscripten_get_heap_max();

        printf("Total heap: %zu bytes\n", total);
        printf("Max heap: %zu bytes\n", used);
    }
}

int main() {
    printMemoryInfo();
    return 0;
}
```

### Smart pointers

```cpp
#include <memory>
#include <cstdio>

class Resource {
public:
    Resource() { printf("Resource created\n"); }
    ~Resource() { printf("Resource destroyed\n"); }
    void use() { printf("Resource used\n"); }
};

int main() {
    // Unique pointer
    std::unique_ptr<Resource> up = std::make_unique<Resource>();
    up->use();

    // Shared pointer
    std::shared_ptr<Resource> sp1 = std::make_shared<Resource>();
    {
        std::shared_ptr<Resource> sp2 = sp1;  // Contador de referência
        sp1->use();
        sp2->use();
    }
    // sp2 destruído, mas sp1 ainda existe
    sp1->use();

    return 0;
}
```

### Arena allocator

```cpp
#include <cstddef>
#include <cstdio>

class ArenaAllocator {
private:
    char* buffer;
    size_t size;
    size_t offset;

public:
    ArenaAllocator(size_t size) : size(size), offset(0) {
        buffer = (char*)malloc(size);
    }

    ~ArenaAllocator() {
        free(buffer);
    }

    void* allocate(size_t bytes) {
        if (offset + bytes > size) {
            return nullptr;
        }
        void* ptr = buffer + offset;
        offset += bytes;
        return ptr;
    }

    void reset() {
        offset = 0;
    }

    size_t getUsed() const {
        return offset;
    }
};

int main() {
    ArenaAllocator arena(1024 * 1024);  // 1MB

    int* arr = (int*)arena.allocate(100 * sizeof(int));
    for (int i = 0; i < 100; i++) {
        arr[i] = i;
    }

    printf("Arena used: %zu bytes\n", arena.getUsed());
    return 0;
}
```

### Pool allocator

```cpp
#include <cstddef>
#include <cstdio>
#include <vector>

class PoolAllocator {
private:
    struct Block {
        Block* next;
    };

    Block* freeList;
    size_t blockSize;
    std::vector<void*> pools;

public:
    PoolAllocator(size_t blockSize, size_t blocksPerPool)
        : blockSize(blockSize), freeList(nullptr) {
        allocatePool(blocksPerPool);
    }

    void allocatePool(size_t blocks) {
        size_t poolSize = blocks * blockSize;
        char* pool = (char*)malloc(poolSize);
        pools.push_back(pool);

        for (size_t i = 0; i < blocks; i++) {
            Block* block = reinterpret_cast<Block*>(pool + i * blockSize);
            block->next = freeList;
            freeList = block;
        }
    }

    void* allocate() {
        if (!freeList) {
            allocatePool(1024);
        }

        Block* block = freeList;
        freeList = block->next;
        return block;
    }

    void deallocate(void* ptr) {
        Block* block = reinterpret_cast<Block*>(ptr);
        block->next = freeList;
        freeList = block;
    }

    ~PoolAllocator() {
        for (void* pool : pools) {
            free(pool);
        }
    }
};

int main() {
    PoolAllocator pool(sizeof(int), 1000);

    int* arr[1000];
    for (int i = 0; i < 1000; i++) {
        arr[i] = (int*)pool.allocate();
        *arr[i] = i;
    }

    for (int i = 0; i < 1000; i++) {
        pool.deallocate(arr[i]);
    }

    return 0;
}
```

### Valgrind e AddressSanitizer

```bash
# Habilitar AddressSanitizer
emcc -fsanitize=address -s INITIAL_MEMORY=256MB main.c -o main.js

# Habilitar MemorySanitizer
emcc -fsanitize=memory -s INITIAL_MEMORY=256MB main.c -o main.js
```

```cpp
#include <cstdio>
#include <cstdlib>

int main() {
    // Erro: buffer overflow
    int* arr = (int*)malloc(10 * sizeof(int));
    arr[10] = 100;  // AddressSanitizer detectará isso

    free(arr);
    return 0;
}
```

### Dicas de gerenciamento de memória

1. Use smart pointers em vez de raw pointers
2. Prefira std::vector a arrays dinâmicos
3. Use Arena allocator para alocações temporárias
4. Monitore o uso de memória em produção
5. Configure ALLOW_MEMORY_GROWTH com cuidado
6. Use AddressSanitizer durante desenvolvimento

---

## 5.6 Sistema de arquivos (MEMFS/FS)

### Visão geral do sistema de arquivos

O Emscripten simula um sistema de arquivos POSIX completo usando MEMFS (Memory File System). Isso permite que código C/C++ que usa fopen, fread, fwrite funcione no navegador, embora tudo seja armazenado na memória.

### Uso básico

```cpp
#include <cstdio>
#include <cstdlib>
#include <cstring>

int main() {
    // Criar arquivo
    FILE* file = fopen("/test.txt", "w");
    if (!file) {
        fprintf(stderr, "Failed to open file\n");
        return 1;
    }

    fprintf(file, "Hello, World!\n");
    fclose(file);

    // Ler arquivo
    file = fopen("/test.txt", "r");
    if (!file) {
        fprintf(stderr, "Failed to open file\n");
        return 1;
    }

    char buffer[256];
    fgets(buffer, sizeof(buffer), file);
    printf("Content: %s", buffer);
    fclose(file);

    return 0;
}
```

### Configuração do sistema de arquivos

```bash
# Montar diretório preloaded
emcc main.c \
    --preload-file ./data@/data \
    -o main.html

# Montar diretório com dados embutidos
emcc main.c \
    -s FORCE_FILESYSTEM=1 \
    -s preload-file ./data@/data \
    -o main.html
```

### Preloading de arquivos

```cpp
#include <emscripten.h>
#include <cstdio>

int main() {
    // Ler arquivo preloaded
    FILE* file = fopen("/data/config.json", "r");
    if (file) {
        char buffer[1024];
        size_t read = fread(buffer, 1, sizeof(buffer) - 1, file);
        buffer[read] = '\0';
        printf("Config: %s\n", buffer);
        fclose(file);
    }

    // Criar novo arquivo
    FILE* output = fopen("/output.txt", "w");
    if (output) {
        fprintf(output, "Generated content\n");
        fclose(output);
    }

    return 0;
}
```

### Montagem dinâmica

```cpp
#include <emscripten.h>
#include <cstdio>
#include <sys/mount.h>
#include <sys/stat.h>

int main() {
    // Criar diretório
    mkdir("/virtual", 0755);

    // Montar filesystem vazio
    mount("", "/virtual", "memfs", 0, "");

    // Criar arquivo no virtual filesystem
    FILE* file = fopen("/virtual/test.txt", "w");
    if (file) {
        fprintf(file, "Virtual file content\n");
        fclose(file);
    }

    // Ler arquivo
    file = fopen("/virtual/test.txt", "r");
    if (file) {
        char buffer[256];
        fgets(buffer, sizeof(buffer), file);
        printf("Content: %s", buffer);
        fclose(file);
    }

    return 0;
}
```

### Operações de arquivo

```cpp
#include <cstdio>
#include <sys/stat.h>
#include <dirent.h>
#include <unistd.h>

void listDirectory(const char* path) {
    DIR* dir = opendir(path);
    if (!dir) return;

    struct dirent* entry;
    while ((entry = readdir(dir)) != nullptr) {
        printf("%s/%s\n", path, entry->d_name);
    }

    closedir(dir);
}

void getFileInfo(const char* path) {
    struct stat statbuf;
    if (stat(path, &statbuf) == 0) {
        printf("Size: %ld bytes\n", statbuf.st_size);
        printf("Mode: %o\n", statbuf.st_mode);
    }
}

int main() {
    // Criar estrutura de diretórios
    mkdir("/data", 0755);
    mkdir("/data/subdir", 0755);

    // Criar arquivos
    FILE* f1 = fopen("/data/file1.txt", "w");
    fprintf(f1, "File 1");
    fclose(f1);

    FILE* f2 = fopen("/data/subdir/file2.txt", "w");
    fprintf(f2, "File 2");
    fclose(f2);

    // Listar diretório
    listDirectory("/data");

    // Obter informações do arquivo
    getFileInfo("/data/file1.txt");

    return 0;
}
```

### Fetch de arquivos

```cpp
#include <emscripten.h>
#include <cstdio>

void downloadFile(const char* url, const char* path) {
    EMSCRIPTEN_async_wget(
        url,
        path,
        [](void* arg) {
            printf("Download complete: %s\n", (const char*)arg);
        },
        [](void* arg) {
            printf("Download failed: %s\n", (const char*)arg);
        },
        (void*)path
    );
}

int main() {
    downloadFile(
        "https://example.com/data.json",
        "/data/downloaded.json"
    );
    return 0;
}
```

### Sincronização com IDBFS

```cpp
#include <emscripten.h>
#include <cstdio>

int main() {
    // Montar IDBFS para persistência
    EM_ASM(
        FS.mkdir('/idb');
        FS.mount(IDBFS, {}, '/idb');
        FS.syncfs(true, function(err) {
            if (err) {
                console.error('IDBFS sync error:', err);
            } else {
                console.log('IDBFS synced');
            }
        });
    );

    // Ler/escrever arquivos que persistem
    FILE* file = fopen("/idb/persistent.txt", "w");
    if (file) {
        fprintf(file, "Persistent data\n");
        fclose(file);
    }

    // Sincronizar de volta ao IndexedDB
    EM_ASM(
        FS.syncfs(false, function(err) {
            if (err) {
                console.error('IDBFS sync error:', err);
            }
        });
    );

    return 0;
}
```

### NODEFS (Node.js)

```cpp
#include <emscripten.h>
#include <cstdio>

int main() {
    // Montar sistema de arquivos real (Node.js)
    EM_ASM(
        FS.mkdir('/host');
        FS.mount(NODEFS, { root: '/real/path' }, '/host');
    );

    // Ler arquivo do sistema de arquivos real
    FILE* file = fopen("/host/real_file.txt", "r");
    if (file) {
        char buffer[256];
        fgets(buffer, sizeof(buffer), file);
        printf("Content: %s", buffer);
        fclose(file);
    }

    return 0;
}
```

### WORKERFS (Web Workers)

```cpp
#include <emscripten.h>
#include <cstdio>

int main() {
    // WORKERFS permite acesso a File/Blob
    EM_ASM(
        FS.mkdir('/worker');
        FS.mount(WORKERFS, {
            blobs: [{name: 'test.txt', data: new Blob(['Hello'])}],
            files: []
        }, '/worker');
    );

    // Ler arquivo montado
    FILE* file = fopen("/worker/test.txt", "r");
    if (file) {
        char buffer[256];
        fgets(buffer, sizeof(buffer), file);
        printf("Content: %s\n", buffer);
        fclose(file);
    }

    return 0;
}
```

### FORCE_FILESYSTEM

```bash
# Forçar inclusão do sistema de arquivos mesmo sem preloading
emcc main.c \
    -s FORCE_FILESYSTEM=1 \
    -s NO_FILESYSTEM=0 \
    -o main.js
```

---

## 5.7 Integração WebGL

### Visão geral do WebGL no Emscripten

O Emscripten fornece suporte completo a OpenGL ES 2.0 e 3.0, que são mapeados diretamente para WebGL e WebGL2 no navegador. Isso permite portar aplicações gráficas C/C++ para o navegador com mudanças mínimas no código.

### Configuração

```bash
# Habilitar WebGL2
em++ main.cpp \
    -s USE_WEBGL2=1 \
    -s FULL_ES3=1 \
    -lGL \
    -o main.js

# Habilitar WebGL1
em++ main.cpp \
    -s USE_WEBGL=1 \
    -lGL \
    -o main.js
```

### Exemplo básico: Triângulo

```cpp
#include <emscripten.h>
#include <GLES2/gl2.h>
#include <cstdio>

GLuint program;
GLuint vbo;

const char* vertexShaderSource = R"(
    attribute vec2 a_position;
    void main() {
        gl_Position = vec4(a_position, 0.0, 1.0);
    }
)";

const char* fragmentShaderSource = R"(
    precision mediump float;
    void main() {
        gl_FragColor = vec4(1.0, 0.0, 0.0, 1.0);
    }
)";

GLuint compileShader(GLenum type, const char* source) {
    GLuint shader = glCreateShader(type);
    glShaderSource(shader, 1, &source, nullptr);
    glCompileShader(shader);

    GLint success;
    glGetShaderiv(shader, GL_COMPILE_STATUS, &success);
    if (!success) {
        char log[512];
        glGetShaderInfoLog(shader, 512, nullptr, log);
        printf("Shader compilation failed: %s\n", log);
    }

    return shader;
}

void init() {
    // Criar shader program
    GLuint vertexShader = compileShader(GL_VERTEX_SHADER, vertexShaderSource);
    GLuint fragmentShader = compileShader(GL_FRAGMENT_SHADER, fragmentShaderSource);

    program = glCreateProgram();
    glAttachShader(program, vertexShader);
    glAttachShader(program, fragmentShader);
    glLinkProgram(program);

    // Criar VBO
    float vertices[] = {
        -0.5f, -0.5f,
         0.5f, -0.5f,
         0.0f,  0.5f
    };

    glGenBuffers(1, &vbo);
    glBindBuffer(GL_ARRAY_BUFFER, vbo);
    glBufferData(GL_ARRAY_BUFFER, sizeof(vertices), vertices, GL_STATIC_DRAW);
}

void render() {
    glViewport(0, 0, 800, 600);
    glClearColor(0.0f, 0.0f, 0.0f, 1.0f);
    glClear(GL_COLOR_BUFFER_BIT);

    glUseProgram(program);

    glBindBuffer(GL_ARRAY_BUFFER, vbo);
    GLint posLoc = glGetAttribLocation(program, "a_position");
    glEnableVertexAttribArray(posLoc);
    glVertexAttribPointer(posLoc, 2, GL_FLOAT, GL_FALSE, 0, 0);

    glDrawArrays(GL_TRIANGLES, 0, 3);
}

int main() {
    init();
    emscripten_set_main_loop(render, 0, 1);
    return 0;
}
```

### Carregamento de texturas

```cpp
#include <emscripten.h>
#include <GLES2/gl2.h>
#include <cstdio>

GLuint loadTexture(const char* path) {
    // Usar stb_image ou similar
    int width, height, channels;
    unsigned char* data = stbi_load(path, &width, &height, &channels, 4);

    if (!data) {
        printf("Failed to load texture: %s\n", path);
        return 0;
    }

    GLuint texture;
    glGenTextures(1, &texture);
    glBindTexture(GL_TEXTURE_2D, texture);

    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_CLAMP_TO_EDGE);
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_CLAMP_TO_EDGE);
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR);
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR);

    glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, width, height, 0,
                 GL_RGBA, GL_UNSIGNED_BYTE, data);

    stbi_image_free(data);
    return texture;
}
```

### Matrizes de transformação

```cpp
#include <cmath>

struct mat4 {
    float m[16];
};

mat4 mat4_identity() {
    mat4 result = {};
    result.m[0] = result.m[5] = result.m[10] = result.m[15] = 1.0f;
    return result;
}

mat4 mat4_multiply(mat4 a, mat4 b) {
    mat4 result = {};
    for (int i = 0; i < 4; i++) {
        for (int j = 0; j < 4; j++) {
            for (int k = 0; k < 4; k++) {
                result.m[i * 4 + j] += a.m[i * 4 + k] * b.m[k * 4 + j];
            }
        }
    }
    return result;
}

mat4 mat4_rotate_z(float angle) {
    mat4 result = mat4_identity();
    float c = cos(angle);
    float s = sin(angle);
    result.m[0] = c;
    result.m[1] = s;
    result.m[4] = -s;
    result.m[5] = c;
    return result;
}

mat4 mat4_perspective(float fov, float aspect, float near, float far) {
    mat4 result = {};
    float tanHalfFov = tan(fov / 2.0f);
    result.m[0] = 1.0f / (aspect * tanHalfFov);
    result.m[5] = 1.0f / tanHalfFov;
    result.m[10] = -(far + near) / (far - near);
    result.m[11] = -1.0f;
    result.m[14] = -(2.0f * far * near) / (far - near);
    return result;
}
```

### Shaders avançados

```glsl
// Vertex Shader com iluminação
attribute vec3 a_position;
attribute vec3 a_normal;
attribute vec2 a_texCoord;

uniform mat4 u_model;
uniform mat4 u_view;
uniform mat4 u_projection;
uniform mat3 u_normalMatrix;

varying vec3 v_normal;
varying vec3 v_position;
varying vec2 v_texCoord;

void main() {
    vec4 worldPos = u_model * vec4(a_position, 1.0);
    v_position = worldPos.xyz;
    v_normal = u_normalMatrix * a_normal;
    v_texCoord = a_texCoord;

    gl_Position = u_projection * u_view * worldPos;
}
```

```glsl
// Fragment Shader com iluminação Phong
precision mediump float;

varying vec3 v_normal;
varying vec3 v_position;
varying vec2 v_texCoord;

uniform sampler2D u_texture;
uniform vec3 u_lightPos;
uniform vec3 u_viewPos;

void main() {
    vec3 normal = normalize(v_normal);
    vec3 lightDir = normalize(u_lightPos - v_position);
    vec3 viewDir = normalize(u_viewPos - v_position);

    // Ambient
    float ambient = 0.1;

    // Diffuse
    float diff = max(dot(normal, lightDir), 0.0);

    // Specular
    vec3 reflectDir = reflect(-lightDir, normal);
    float spec = pow(max(dot(viewDir, reflectDir), 0.0), 32.0);

    vec3 textureColor = texture2D(u_texture, v_texCoord).rgb;
    vec3 result = (ambient + diff + spec) * textureColor;

    gl_FragColor = vec4(result, 1.0);
}
```

### Renderização em loop

```cpp
#include <emscripten.h>

float rotation = 0.0f;

void mainLoop() {
    rotation += 0.01f;

    // Atualizar matriz de modelo
    mat4 model = mat4_rotate_z(rotation);

    // Enviar uniforms
    glUniformMatrix4fv(modelLoc, 1, GL_FALSE, model.m);

    // Renderizar
    glDrawArrays(GL_TRIANGLES, 0, vertexCount);

    // Solicitar próximo frame
    emscripten_set_main_loop(mainLoop, 0, 0);
}

int main() {
    init();
    emscripten_set_main_loop(mainLoop, 0, 1);
    return 0;
}
```

### Interatividade com mouse/teclado

```cpp
#include <emscripten.h>
#include <emscripten/html5.h>

float mouseX = 0.0f;
float mouseY = 0.0f;

EM_BOOL mouseMove(int eventType, const EmscriptenMouseEvent* e, void* userData) {
    mouseX = (float)e->clientX;
    mouseY = (float)e->clientY;
    return EM_TRUE;
}

EM_BOOL keyDown(int eventType, const EmscriptenKeyboardEvent* e, void* userData) {
    if (strcmp(e->key, "ArrowLeft") == 0) {
        // Mover para esquerda
    }
    return EM_TRUE;
}

int main() {
    emscripten_setmousemove_callback(EMSCRIPTEN_EVENT_TARGET_DOCUMENT, nullptr, EM_TRUE, mouseMove);
    emscripten_set_keydown_callback(EMSCRIPTEN_EVENT_TARGET_DOCUMENT, nullptr, EM_TRUE, keyDown);

    emscripten_set_main_loop(mainLoop, 0, 1);
    return 0;
}
```

---

## 5.8 Áudio

### Visão geral do áudio no Emscripten

O Emscripten fornece suporte a áudio através de SDL2, OpenAL e Web Audio API. Isso permite portar jogos e aplicações multimídia para o navegador com suporte completo a efeitos sonoros e música.

### Configuração com SDL2

```bash
# Habilitar SDL2 com áudio
em++ main.cpp \
    -s USE_SDL=2 \
    -s USE_SDL_MIXER=1 \
    -o main.js
```

### Exemplo com SDL2

```cpp
#include <SDL2/SDL.h>
#include <SDL2/SDL_mixer.h>
#include <cstdio>

SDL_AudioSpec spec;
Uint8* audioBuffer;
Uint32 audioLength;

void audioCallback(void* userdata, Uint8* stream, int len) {
    static Uint32 position = 0;
    for (int i = 0; i < len; i++) {
        stream[i] = audioBuffer[(position + i) % audioLength];
    }
    position += len;
}

int main() {
    SDL_Init(SDL_INIT_AUDIO);

    // Configurar áudio
    spec.freq = 44100;
    spec.format = AUDIO_S16SYS;
    spec.channels = 2;
    spec.samples = 2048;
    spec.callback = audioCallback;

    SDL_OpenAudio(&spec, nullptr);
    SDL_PauseAudio(0);

    // Carregar arquivo de áudio
    SDL_AudioSpec loadedSpec;
    SDL_LoadWAV("sound.wav", &loadedSpec, &audioBuffer, &audioLength);

    // Esperar um pouco
    SDL_Delay(2000);

    // Limpar
    SDL_FreeWAV(audioBuffer);
    SDL_CloseAudio();
    SDL_Quit();

    return 0;
}
```

### OpenAL

```cpp
#include <AL/al.h>
#include <AL/alc.h>
#include <cstdio>

int main() {
    ALCdevice* device = alcOpenDevice(nullptr);
    ALCcontext* context = alcCreateContext(device, nullptr);
    alcMakeContextCurrent(context);

    // Gerar buffer
    ALuint buffer;
    alGenBuffers(1, &buffer);

    // Ler arquivo de áudio
    FILE* file = fopen("sound.pcm", "rb");
    fseek(file, 0, SEEK_END);
    long size = ftell(file);
    fseek(file, 0, SEEK_SET);

    char* data = new char[size];
    fread(data, 1, size, file);
    fclose(file);

    alBufferData(buffer, AL_FORMAT_MONO16, data, size, 44100);
    delete[] data;

    // Gerar source
    ALuint source;
    alGenSources(1, &source);
    alSourcei(source, AL_BUFFER, buffer);

    // Tocar
    alSourcePlay(source);

    // Esperar
    SDL_Delay(2000);

    // Limpar
    alDeleteSources(1, &source);
    alDeleteBuffers(1, &buffer);
    alcDestroyContext(context);
    alcCloseDevice(device);

    return 0;
}
```

### Web Audio API via JavaScript

```javascript
// main.js
const audioContext = new AudioContext();

function playTone(frequency, duration) {
    const oscillator = audioContext.createOscillator();
    const gainNode = audioContext.createGain();

    oscillator.connect(gainNode);
    gainNode.connect(audioContext.destination);

    oscillator.frequency.value = frequency;
    oscillator.type = 'sine';

    gainNode.gain.setValueAtTime(0.5, audioContext.currentTime);
    gainNode.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + duration);

    oscillator.start();
    oscillator.stop(audioContext.currentTime + duration);
}

Module._playSound = function(frequency, duration) {
    playTone(frequency, duration);
};
```

```cpp
#include <emscripten.h>

extern "C" {
    void _playSound(int frequency, int duration);
}

void playSound(int frequency, int duration) {
    _playSound(frequency, duration);
}

int main() {
    playSound(440, 1000);  // Tocar Lá por 1 segundo
    return 0;
}
```

### Síntese de áudio

```cpp
#include <cmath>
#include <vector>

struct AudioBuffer {
    std::vector<float> samples;
    int sampleRate;
};

AudioBuffer generateSineWave(float frequency, float duration, int sampleRate = 44100) {
    AudioBuffer buffer;
    buffer.sampleRate = sampleRate;

    int numSamples = (int)(duration * sampleRate);
    buffer.samples.resize(numSamples);

    for (int i = 0; i < numSamples; i++) {
        float t = (float)i / sampleRate;
        buffer.samples[i] = sin(2.0f * M_PI * frequency * t);
    }

    return buffer;
}

AudioBuffer generateSquareWave(float frequency, float duration, int sampleRate = 44100) {
    AudioBuffer buffer;
    buffer.sampleRate = sampleRate;

    int numSamples = (int)(duration * sampleRate);
    buffer.samples.resize(numSamples);

    for (int i = 0; i < numSamples; i++) {
        float t = (float)i / sampleRate;
        buffer.samples[i] = sin(2.0f * M_PI * frequency * t) > 0 ? 1.0f : -1.0f;
    }

    return buffer;
}

AudioBuffer mixBuffers(const AudioBuffer& a, const AudioBuffer& b) {
    AudioBuffer result;
    result.sampleRate = a.sampleRate;

    int maxSize = std::max(a.samples.size(), b.samples.size());
    result.samples.resize(maxSize);

    for (int i = 0; i < maxSize; i++) {
        float sampleA = i < a.samples.size() ? a.samples[i] : 0.0f;
        float sampleB = i < b.samples.size() ? b.samples[i] : 0.0f;
        result.samples[i] = sampleA + sampleB;
    }

    return result;
}
```

---

## 5.9 Threading (SharedArrayBuffer)

### Visão geral do threading

O WebAssembly suporta threading através de SharedArrayBuffer e Web Workers. O Emscripten fornece uma abstração pthreads que permite usar threads C/C++ padrão no navegador.

### Configuração

```bash
# Habilitar pthreads
em++ main.cpp \
    -s USE_PTHREADS=1 \
    -s PTHREAD_POOL_SIZE=4 \
    -s SHARED_MEMORY=1 \
    -o main.js
```

### Exemplo com pthreads

```cpp
#include <pthread.h>
#include <cstdio>
#include <atomic>

std::atomic<int> counter(0);
const int NUM_THREADS = 4;
const int ITERATIONS = 1000000;

void* worker(void* arg) {
    int threadId = *(int*)arg;
    for (int i = 0; i < ITERATIONS; i++) {
        counter.fetch_add(1);
    }
    printf("Thread %d completed\n", threadId);
    return nullptr;
}

int main() {
    pthread_t threads[NUM_THREADS];
    int threadIds[NUM_THREADS];

    for (int i = 0; i < NUM_THREADS; i++) {
        threadIds[i] = i;
        pthread_create(&threads[i], nullptr, worker, &threadIds[i]);
    }

    for (int i = 0; i < NUM_THREADS; i++) {
        pthread_join(threads[i], nullptr);
    }

    printf("Counter: %d (expected: %d)\n", counter.load(), NUM_THREADS * ITERATIONS);
    return 0;
}
```

### Mutex e sincronização

```cpp
#include <pthread.h>
#include <cstdio>

pthread_mutex_t mutex = PTHREAD_MUTEX_INITIALIZER;
int sharedResource = 0;

void* worker(void* arg) {
    for (int i = 0; i < 100000; i++) {
        pthread_mutex_lock(&mutex);
        sharedResource++;
        pthread_mutex_unlock(&mutex);
    }
    return nullptr;
}

int main() {
    pthread_t threads[4];

    for (int i = 0; i < 4; i++) {
        pthread_create(&threads[i], nullptr, worker, nullptr);
    }

    for (int i = 0; i < 4; i++) {
        pthread_join(threads[i], nullptr);
    }

    printf("Shared resource: %d\n", sharedResource);
    return 0;
}
```

### Condições e barreiras

```cpp
#include <pthread.h>
#include <cstdio>

pthread_cond_t cond = PTHREAD_COND_INITIALIZER;
pthread_mutex_t mutex = PTHREAD_MUTEX_INITIALIZER;
int ready = 0;

void* producer(void* arg) {
    pthread_mutex_lock(&mutex);
    ready = 1;
    pthread_cond_signal(&cond);
    pthread_mutex_unlock(&mutex);
    return nullptr;
}

void* consumer(void* arg) {
    pthread_mutex_lock(&mutex);
    while (!ready) {
        pthread_cond_wait(&cond, &mutex);
    }
    printf("Consumer received signal\n");
    pthread_mutex_unlock(&mutex);
    return nullptr;
}

int main() {
    pthread_t prod, cons;

    pthread_create(&cons, nullptr, consumer, nullptr);
    pthread_create(&prod, nullptr, producer, nullptr);

    pthread_join(prod, nullptr);
    pthread_join(cons, nullptr);

    return 0;
}
```

### ThreadPool

```cpp
#include <pthread.h>
#include <queue>
#include <functional>
#include <mutex>
#include <condition_variable>
#include <vector>

class ThreadPool {
private:
    std::vector<pthread_t> threads;
    std::queue<std::function<void()>> tasks;
    pthread_mutex_t mutex;
    pthread_cond_t condition;
    bool stop;

public:
    ThreadPool(size_t numThreads) : stop(false) {
        pthread_mutex_init(&mutex, nullptr);
        pthread_cond_init(&condition, nullptr);

        for (size_t i = 0; i < numThreads; i++) {
            pthread_create(&threads[i], nullptr, workerThread, this);
        }
    }

    ~ThreadPool() {
        pthread_mutex_lock(&mutex);
        stop = true;
        pthread_mutex_unlock(&mutex);

        pthread_cond_broadcast(&condition);

        for (pthread_t& thread : threads) {
            pthread_join(thread, nullptr);
        }

        pthread_mutex_destroy(&mutex);
        pthread_cond_destroy(&condition);
    }

    void enqueue(std::function<void()> task) {
        pthread_mutex_lock(&mutex);
        tasks.push(task);
        pthread_mutex_unlock(&mutex);
        pthread_cond_signal(&condition);
    }

private:
    static void* workerThread(void* arg) {
        ThreadPool* pool = static_cast<ThreadPool*>(arg);

        while (true) {
            std::function<void()> task;

            pthread_mutex_lock(&pool->mutex);
            while (pool->tasks.empty() && !pool->stop) {
                pthread_cond_wait(&pool->condition, &pool->mutex);
            }

            if (pool->stop && pool->tasks.empty()) {
                pthread_mutex_unlock(&pool->mutex);
                return nullptr;
            }

            task = pool->tasks.front();
            pool->tasks.pop();
            pthread_mutex_unlock(&pool->mutex);

            task();
        }
    }
};

int main() {
    ThreadPool pool(4);

    for (int i = 0; i < 8; i++) {
        pool.enqueue([i]() {
            printf("Task %d executed\n", i);
        });
    }

    return 0;
}
```

### SharedArrayBuffer manual

```cpp
#include <emscripten.h>
#include <atomic>

int main() {
    // Criar SharedArrayBuffer
    int* sharedData = (int*)emscripten_atomic_current_memory();

    // Inicializar
    *sharedData = 0;

    // Em múltiplas threads, usar operações atômicas
    emscripten_atomic_add_u32(sharedData, 1);

    return 0;
}
```

### Configurações de segurança

```bash
# Headers de segurança obrigatórios para SharedArrayBuffer
# O servidor precisa retornar:
# Cross-Origin-Opener-Policy: same-origin
# Cross-Origin-Embedder-Policy: require-corp

em++ main.cpp \
    -s USE_PTHREADS=1 \
    -s SHARED_MEMORY=1 \
    -s PROXY_TO_PTHREAD=1 \
    -o main.js
```

---

## 5.10 Flags de otimização

### Visão geral das otimizações

O Emscripten suporta todas as otimizações do LLVM/Clang, além de otimizações específicas para WebAssembly. Essas otimizações podem reduzir significativamente o tamanho do binário e melhorar a performance.

### Níveis de otimização

```bash
# Sem otimização (debug)
emcc -O0 main.c -o main.js

# Otimização mínima
emcc -O1 main.c -o main.js

# Otimização padrão (recomendado)
emcc -O2 main.c -o main.js

# Otimização máxima
emcc -O3 main.c -o main.js

# Otimizar para tamanho
emcc -Os main.c -o main.js

# Otimizar para tamanho máximo
emcc -Oz main.c -o main.js
```

### Link-Time Optimization (LTO)

```bash
# Habilitar LTO
emcc -O2 -flto main.c -o main.js

# LTO com otimizações específicas
emcc -O2 -flto -ffunction-sections -fdata-sections main.c -o main.js
```

### Outras flags de otimização

```bash
# Remover código morto
emcc -O2 -ffunction-sections -fdata-sections -Wl,--gc-sections main.c -o main.js

# Inlining agressivo
emcc -O2 -finline-functions -funswitch-loops main.c -o main.js

# Loop optimizations
emcc -O2 -funroll-loops main.c -o main.js

# Vetorização
emcc -O2 -ftree-vectorize main.c -o main.js
```

### Flags específicas do Emscripten

```bash
# Otimizar para tamanho de download
emcc -Oz -s MINIMAL_RUNTIME=1 main.c -o main.js

# Otimizar para execução
emcc -O3 -s DISABLE_EXCEPTION_CATCHING=1 main.c -o main.js

# Remover código morto
emcc -O2 -s DEAD_FUNCTIONS='[...] main.c -o main.js
```

### Profiling

```bash
# Habilitar profiling
emcc -O2 -s PROFILING=1 main.c -o main.js

# Gerar relatório de tamanho
emcc -O2 -s ASSERTIONS=2 main.c -o main.js
```

### Comparação de otimizações

| Flag | Redução tamanho | Ganho performance | Trade-off |
|------|-----------------|-------------------|-----------|
| -O0 | 0% | 0% | Debug completo |
| -O1 | 10-20% | 10-20% | Pouco debug |
| -O2 | 20-30% | 20-30% | Debug limitado |
| -O3 | 25-35% | 30-40% | Sem debug |
| -Os | 30-40% | 15-25% | Tamanho |
| -Oz | 40-50% | 10-20% | Tamanho máximo |

### Exemplo de build otimizado

```bash
#!/bin/bash
# build_optimized.sh

FLAGS="-Oz"
FLAGS+=" -flto"
FLAGS+=" -ffunction-sections -fdata-sections"
FLAGS+=" -s WASM=1"
FLAGS+=" -s MINIMAL_RUNTIME=1"
FLAGS+"= -s ASSERTIONS=0"
FLAGS+=" -s DISABLE_EXCEPTION_CATCHING=1"
FLAGS+=" -s FILESYSTEM=0"
FLAGS+=" -s MALLOC=emmalloc"

em++ main.cpp $FLAGS -o main.js
```

### Minificação

```bash
# Minificar JavaScript
npm install -g terser
terser main.js -o main.min.js -c -m

# Opcional: gzip
gzip -k -9 main.min.js
```

---

## 5.11 Exemplo de aplicação completa

### Projeto: Aplicação de processamento de sinais

Este exemplo demonstra uma aplicação completa que processa sinais de áudio usando C++ e WebAssembly.

**Estrutura do projeto**:

```
signal-processor/
├── CMakeLists.txt
├── src/
│   ├── main.cpp
│   ├── signal.h
│   ├── signal.cpp
│   ├── fft.h
│   ├── fft.cpp
│   ├── filter.h
│   └── filter.cpp
├── web/
│   ├── index.html
│   ├── main.js
│   └── style.css
└── build/
```

**CMakeLists.txt**:

```cmake
cmake_minimum_required(VERSION 3.13)
project(SignalProcessor)

set(CMAKE_CXX_STANDARD 17)

# Flags do Emscripten
set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -O2 -s WASM=1 -s EXPORTED_RUNTIME_METHODS='[\"ccall\",\"cwrap\"]' -s ALLOW_MEMORY_GROWTH=1")

# Headers
include_directories(${CMAKE_SOURCE_DIR}/src)

# Fontes
set(SOURCES
    src/main.cpp
    src/signal.cpp
    src/fft.cpp
    src/filter.cpp
)

# Executável
add_executable(signal_processor ${SOURCES})

# Exportar funções
target_link_options(signal_processor PRIVATE
    -s EXPORTED_FUNCTIONS='[\"_processSignal\",\"_analyzeSpectrum\",\"_applyFilter\"]'
    -s EXPORTED_RUNTIME_METHODS='[\"ccall\",\"cwrap\"]'
)
```

**src/signal.h**:

```cpp
#pragma once
#include <vector>
#include <complex>

class Signal {
public:
    Signal();
    Signal(const std::vector<double>& samples, int sampleRate);

    const std::vector<double>& getSamples() const;
    int getSampleRate() const;
    size_t getLength() const;

    double getDuration() const;
    double getRMS() const;
    double getPeak() const;

    Signal resample(int newSampleRate) const;
    Signal normalize() const;
    Signal window(int start, int length) const;

private:
    std::vector<double> samples;
    int sampleRate;
};
```

**src/signal.cpp**:

```cpp
#include "signal.h"
#include <cmath>
#include <algorithm>

Signal::Signal() : sampleRate(0) {}

Signal::Signal(const std::vector<double>& samples, int sampleRate)
    : samples(samples), sampleRate(sampleRate) {}

const std::vector<double>& Signal::getSamples() const {
    return samples;
}

int Signal::getSampleRate() const {
    return sampleRate;
}

size_t Signal::getLength() const {
    return samples.size();
}

double Signal::getDuration() const {
    return static_cast<double>(samples.size()) / sampleRate;
}

double Signal::getRMS() const {
    double sum = 0.0;
    for (double sample : samples) {
        sum += sample * sample;
    }
    return std::sqrt(sum / samples.size());
}

double Signal::getPeak() const {
    double peak = 0.0;
    for (double sample : samples) {
        double absSample = std::abs(sample);
        if (absSample > peak) {
            peak = absSample;
        }
    }
    return peak;
}

Signal Signal::normalize() const {
    double peak = getPeak();
    if (peak == 0.0) return *this;

    std::vector<double> normalized(samples.size());
    for (size_t i = 0; i < samples.size(); i++) {
        normalized[i] = samples[i] / peak;
    }
    return Signal(normalized, sampleRate);
}

Signal Signal::window(int start, int length) const {
    int end = std::min(start + length, static_cast<int>(samples.size()));
    std::vector<double> windowed(samples.begin() + start, samples.begin() + end);
    return Signal(windowed, sampleRate);
}
```

**src/fft.h**:

```cpp
#pragma once
#include <vector>
#include <complex>

class FFT {
public:
    static std::vector<std::complex<double>> compute(const std::vector<double>& signal);
    static std::vector<double> magnitude(const std::vector<std::complex<double>>& spectrum);
    static std::vector<double> phase(const std::vector<std::complex<double>>& spectrum);
    static std::vector<double> powerSpectrum(const std::vector<double>& signal);

private:
    static void fft(std::vector<std::complex<double>>& data, bool inverse);
    static size_t reverseBits(size_t value, int bits);
};
```

**src/fft.cpp**:

```cpp
#include "fft.h"
#include <cmath>
#include <algorithm>

#ifndef M_PI
#define M_PI 3.14159265358979323846
#endif

std::vector<std::complex<double>> FFT::compute(const std::vector<double>& signal) {
    size_t n = signal.size();
    size_t log2n = static_cast<size_t>(std::log2(n));

    // Padding para potência de 2
    size_t paddedSize = 1 << log2n;
    if (paddedSize < n) {
        paddedSize <<= 1;
        log2n++;
    }

    std::vector<std::complex<double>> data(paddedSize);
    for (size_t i = 0; i < n; i++) {
        data[i] = std::complex<double>(signal[i], 0.0);
    }

    fft(data, false);
    return data;
}

std::vector<double> FFT::magnitude(const std::vector<std::complex<double>>& spectrum) {
    std::vector<double> mag(spectrum.size());
    for (size_t i = 0; i < spectrum.size(); i++) {
        mag[i] = std::abs(spectrum[i]);
    }
    return mag;
}

std::vector<double> FFT::phase(const std::vector<std::complex<double>>& spectrum) {
    std::vector<double> ph(spectrum.size());
    for (size_t i = 0; i < spectrum.size(); i++) {
        ph[i] = std::arg(spectrum[i]);
    }
    return ph;
}

std::vector<double> FFT::powerSpectrum(const std::vector<double>& signal) {
    auto spectrum = compute(signal);
    auto mag = magnitude(spectrum);

    std::vector<double> power(mag.size());
    for (size_t i = 0; i < mag.size(); i++) {
        power[i] = mag[i] * mag[i];
    }
    return power;
}

void FFT::fft(std::vector<std::complex<double>>& data, bool inverse) {
    size_t n = data.size();
    if (n <= 1) return;

    // Bit reversal
    int log2n = static_cast<int>(std::log2(n));
    for (size_t i = 0; i < n; i++) {
        size_t j = reverseBits(i, log2n);
        if (i < j) {
            std::swap(data[i], data[j]);
        }
    }

    // Butterfly operations
    double angle = (inverse ? -2.0 : 2.0) * M_PI / n;
    for (size_t len = 2; len <= n; len <<= 1) {
        double ang = angle * (inverse ? -1.0 : 1.0);
        std::complex<double> wlen(std::cos(ang), std::sin(ang));

        for (size_t i = 0; i < n; i += len) {
            std::complex<double> w(1.0, 0.0);
            for (size_t j = 0; j < len / 2; j++) {
                std::complex<double> u = data[i + j];
                std::complex<double> v = data[i + j + len / 2] * w;
                data[i + j] = u + v;
                data[i + j + len / 2] = u - v;
                w *= wlen;
            }
        }
    }

    if (inverse) {
        for (auto& x : data) {
            x /= n;
        }
    }
}

size_t FFT::reverseBits(size_t value, int bits) {
    size_t result = 0;
    for (int i = 0; i < bits; i++) {
        result = (result << 1) | (value & 1);
        value >>= 1;
    }
    return result;
}
```

**src/filter.h**:

```cpp
#pragma once
#include <vector>

class Filter {
public:
    static std::vector<double> lowpass(const std::vector<double>& signal,
                                       double cutoff,
                                       int sampleRate,
                                       int order = 5);

    static std::vector<double> highpass(const std::vector<double>& signal,
                                        double cutoff,
                                        int sampleRate,
                                        int order = 5);

    static std::vector<double> bandpass(const std::vector<double>& signal,
                                        double lowCutoff,
                                        double highCutoff,
                                        int sampleRate,
                                        int order = 5);

private:
    static std::vector<double> butterworth(int order, double cutoff, int sampleRate, bool highpass);
};
```

**src/filter.cpp**:

```cpp
#include "filter.h"
#include <cmath>
#include <complex>

#ifndef M_PI
#define M_PI 3.14159265358979323846
#endif

std::vector<double> Filter::lowpass(const std::vector<double>& signal,
                                    double cutoff,
                                    int sampleRate,
                                    int order) {
    return butterworth(order, cutoff, sampleRate, false);
}

std::vector<double> Filter::highpass(const std::vector<double>& signal,
                                     double cutoff,
                                     int sampleRate,
                                     int order) {
    return butterworth(order, cutoff, sampleRate, true);
}

std::vector<double> Filter::bandpass(const std::vector<double>& signal,
                                     double lowCutoff,
                                     double highCutoff,
                                     int sampleRate,
                                     int order) {
    auto low = butterworth(order, lowCutoff, sampleRate, true);
    auto high = butterworth(order, highCutoff, sampleRate, false);

    std::vector<double> result(signal.size());
    for (size_t i = 0; i < signal.size(); i++) {
        result[i] = signal[i] * low[i % low.size()] * high[i % high.size()];
    }
    return result;
}

std::vector<double> Filter::butterworth(int order, double cutoff, int sampleRate, bool highpass) {
    double nyquist = sampleRate / 2.0;
    double normalizedCutoff = cutoff / nyquist;

    std::vector<double> coefficients;

    for (int i = 0; i < order; i++) {
        double angle = M_PI * (2 * i + 1) / (2 * order);
        double real = -std::cos(angle);
        double imag = std::sin(angle);

        // Coeficientes do filtro
        double a = 1.0 + normalizedCutoff;
        double b = 1.0 - normalizedCutoff;

        coefficients.push_back(a);
        coefficients.push_back(b);
    }

    return coefficients;
}
```

**src/main.cpp**:

```cpp
#include <emscripten.h>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <vector>
#include "signal.h"
#include "fft.h"
#include "filter.h"

extern "C" {

EMSCRIPTEN_KEEPALIVE
double* processSignal(double* samples, int length, int sampleRate) {
    std::vector<double> input(samples, samples + length);
    Signal signal(input, sampleRate);

    // Normalizar
    Signal normalized = signal.normalize();

    // Aplicar FFT
    auto spectrum = FFT::compute(normalized.getSamples());
    auto magnitude = FFT::magnitude(spectrum);

    // Retornar magnitude
    double* result = (double*)malloc(magnitude.size() * sizeof(double));
    memcpy(result, magnitude.data(), magnitude.size() * sizeof(double));
    return result;
}

EMSCRIPTEN_KEEPALIVE
int getMagnitudeSize(int signalLength) {
    size_t n = 1;
    while (n < signalLength) {
        n <<= 1;
    }
    return n;
}

EMSCRIPTEN_KEEPALIVE
double* analyzeSpectrum(double* samples, int length, int sampleRate) {
    std::vector<double> input(samples, samples + length);

    auto power = FFT::powerSpectrum(input);

    double* result = (double*)malloc(power.size() * sizeof(double));
    memcpy(result, power.data(), power.size() * sizeof(double));
    return result;
}

EMSCRIPTEN_KEEPALIVE
double* applyFilter(double* samples, int length, int sampleRate,
                    double cutoff, int filterType) {
    std::vector<double> input(samples, samples + length);
    std::vector<double> output;

    switch (filterType) {
        case 0:  // Lowpass
            output = Filter::lowpass(input, cutoff, sampleRate);
            break;
        case 1:  // Highpass
            output = Filter::highpass(input, cutoff, sampleRate);
            break;
        case 2:  // Bandpass
            output = Filter::bandpass(input, cutoff * 0.5, cutoff * 2.0, sampleRate);
            break;
        default:
            output = input;
    }

    double* result = (double*)malloc(output.size() * sizeof(double));
    memcpy(result, output.data(), output.size() * sizeof(double));
    return result;
}

EMSCRIPTEN_KEEPALIVE
void freeMemory(double* ptr) {
    free(ptr);
}

}  // extern "C"

int main() {
    printf("Signal Processor loaded\n");
    return 0;
}
```

**web/index.html**:

```html
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Signal Processor</title>
    <link rel="stylesheet" href="style.css">
</head>
<body>
    <div id="app">
        <h1>Signal Processor</h1>

        <div class="controls">
            <input type="file" id="fileInput" accept="audio/*">
            <select id="processType">
                <option value="spectrum">Spectrum Analysis</option>
                <option value="filter">Apply Filter</option>
                <option value="normalize">Normalize</option>
            </select>
            <div id="filterOptions" style="display: none;">
                <select id="filterType">
                    <option value="0">Lowpass</option>
                    <option value="1">Highpass</option>
                    <option value="2">Bandpass</option>
                </select>
                <input type="range" id="cutoff" min="20" max="20000" value="1000">
                <span id="cutoffValue">1000 Hz</span>
            </div>
            <button id="processBtn">Process</button>
            <button id="playBtn">Play</button>
        </div>

        <div class="visualization">
            <canvas id="waveformCanvas"></canvas>
            <canvas id="spectrumCanvas"></canvas>
        </div>

        <div id="stats"></div>
    </div>

    <script type="module" src="main.js"></script>
</body>
</html>
```

**web/main.js**:

```javascript
import Module from '../build/signal_processor.js';

let audioContext = null;
let originalBuffer = null;
let processedBuffer = null;

async function init() {
    const module = await Module();

    const fileInput = document.getElementById('fileInput');
    const processBtn = document.getElementById('processBtn');
    const playBtn = document.getElementById('playBtn');
    const processType = document.getElementById('processType');
    const filterOptions = document.getElementById('filterOptions');
    const cutoff = document.getElementById('cutoff');
    const cutoffValue = document.getElementById('cutoffValue');

    audioContext = new AudioContext();

    fileInput.addEventListener('change', async (e) => {
        const file = e.target.files[0];
        if (!file) return;

        const arrayBuffer = await file.arrayBuffer();
        originalBuffer = await audioContext.decodeAudioData(arrayBuffer);

        drawWaveform(originalBuffer, 'waveformCanvas');
        document.getElementById('stats').textContent = 
            `Loaded: ${originalBuffer.duration.toFixed(2)}s, ${originalBuffer.sampleRate}Hz`;
    });

    processType.addEventListener('change', (e) => {
        filterOptions.style.display = e.target.value === 'filter' ? 'flex' : 'none';
    });

    cutoff.addEventListener('input', (e) => {
        cutoffValue.textContent = `${e.target.value} Hz`;
    });

    processBtn.addEventListener('click', () => {
        if (!originalBuffer) return;

        const samples = originalBuffer.getChannelData(0);
        const length = samples.length;
        const sampleRate = originalBuffer.sampleRate;

        // Alocar memória no WASM
        const inputPtr = module._malloc(length * 8);
        module.HEAPF64.set(samples, inputPtr / 8);

        let outputPtr;
        let outputLength;

        const startTime = performance.now();

        switch (processType.value) {
            case 'spectrum':
                outputLength = module._getMagnitudeSize(length);
                outputPtr = module._processSignal(inputPtr, length, sampleRate);
                break;

            case 'filter':
                const filterType = parseInt(document.getElementById('filterType').value);
                const cutoffFreq = parseInt(cutoff.value);
                outputPtr = module._applyFilter(inputPtr, length, sampleRate, cutoffFreq, filterType);
                outputLength = length;
                break;

            case 'normalize':
                outputPtr = module._processSignal(inputPtr, length, sampleRate);
                outputLength = length;
                break;
        }

        const endTime = performance.now();

        // Ler resultado
        const output = new Float64Array(
            module.HEAPF64.buffer,
            outputPtr,
            outputLength
        );

        // Criar buffer de áudio processado
        processedBuffer = audioContext.createBuffer(1, outputLength, sampleRate);
        processedBuffer.getChannelData(0).set(output);

        // Limpar memória
        module._free(inputPtr);
        module._free(outputPtr);

        // Desenhar resultado
        drawWaveform(processedBuffer, 'spectrumCanvas');

        document.getElementById('stats').textContent = 
            `Processing time: ${(endTime - startTime).toFixed(2)}ms`;
    });

    playBtn.addEventListener('click', () => {
        if (!processedBuffer) return;

        const source = audioContext.createBufferSource();
        source.buffer = processedBuffer;
        source.connect(audioContext.destination);
        source.start();
    });
}

function drawWaveform(buffer, canvasId) {
    const canvas = document.getElementById(canvasId);
    const ctx = canvas.getContext('2d');
    const data = buffer.getChannelData(0);

    canvas.width = canvas.clientWidth;
    canvas.height = canvas.clientHeight;

    ctx.fillStyle = '#000';
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    ctx.strokeStyle = '#0f0';
    ctx.lineWidth = 1;
    ctx.beginPath();

    const sliceWidth = canvas.width / data.length;
    let x = 0;

    for (let i = 0; i < data.length; i++) {
        const y = (data[i] + 1) / 2 * canvas.height;

        if (i === 0) {
            ctx.moveTo(x, y);
        } else {
            ctx.lineTo(x, y);
        }

        x += sliceWidth;
    }

    ctx.stroke();
}

init();
```

**web/style.css**:

```css
body {
    font-family: system-ui, -apple-system, sans-serif;
    max-width: 1200px;
    margin: 0 auto;
    padding: 20px;
    background: #1a1a2e;
    color: #eee;
}

h1 {
    text-align: center;
    color: #00d9ff;
}

.controls {
    display: flex;
    gap: 10px;
    margin-bottom: 20px;
    flex-wrap: wrap;
    align-items: center;
}

.visualization {
    display: flex;
    gap: 20px;
    flex-wrap: wrap;
}

canvas {
    width: 100%;
    height: 200px;
    background: #000;
    border: 1px solid #333;
}

#stats {
    margin-top: 20px;
    text-align: center;
    color: #00ff88;
}

button {
    padding: 10px 20px;
    background: #00d9ff;
    border: none;
    border-radius: 5px;
    cursor: pointer;
    font-weight: bold;
}

button:hover {
    background: #00b8d4;
}

select, input[type="range"] {
    padding: 8px;
    border-radius: 5px;
    border: 1px solid #333;
    background: #2a2a4a;
    color: #eee;
}
```

### Compilando e executando

```bash
# Criar diretório de build
mkdir -p build
cd build

# Configurar com Emscripten
emcmake cmake ..

# Compilar
emmake make

# Copiar arquivos web
cp signal_processor.js ../web/
cp signal_processor.wasm ../web/

# Servir (necessário para SharedArrayBuffer)
cd ../web
python3 -m http.server 8080 \
    --header "Cross-Origin-Opener-Policy: same-origin" \
    --header "Cross-Origin-Embedder-Policy: require-corp"
```

### Testes

```cpp
#include <cstdio>
#include <cassert>
#include "signal.h"
#include "fft.h"
#include "filter.h"

void test_signal() {
    std::vector<double> samples = {1.0, 2.0, 3.0, 4.0, 5.0};
    Signal signal(samples, 44100);

    assert(signal.getLength() == 5);
    assert(signal.getSampleRate() == 44100);
    assert(signal.getDuration() > 0.0);

    printf("Signal tests passed\n");
}

void test_fft() {
    std::vector<double> signal = {1.0, 0.0, -1.0, 0.0};
    auto spectrum = FFT::compute(signal);

    assert(spectrum.size() > 0);

    auto mag = FFT::magnitude(spectrum);
    assert(mag.size() == spectrum.size());

    printf("FFT tests passed\n");
}

void test_filter() {
    std::vector<double> signal(1000);
    for (int i = 0; i < 1000; i++) {
        signal[i] = sin(2.0 * M_PI * 440.0 * i / 44100.0);
    }

    auto filtered = Filter::lowpass(signal, 1000.0, 44100);
    assert(filtered.size() == signal.size());

    printf("Filter tests passed\n");
}

int main() {
    test_signal();
    test_fft();
    test_filter();

    printf("All tests passed!\n");
    return 0;
}
```

### Resultados esperados

- Processamento de áudio: ~5ms para 1 segundo de áudio
- FFT: ~2ms para 4096 amostras
- Filtro: ~1ms para 1000 amostras
- Tamanho do binário: ~200KB

---

## Resumo

Este capítulo cobriu o ecossistema completo de C++ para WebAssembly:

1. **Emscripten SDK**: Instalação e configuração
2. **emcc flags**: Flags de compilação e otimização
3. **Embind**: FFI entre C++ e JavaScript
4. **Asyncify**: Operações assíncronas em código síncrono
5. **Gerenciamento de memória**: Alocação e otimização
6. **Sistema de arquivos**: MEMFS, IDBFS, WORKERFS
7. **WebGL**: Integração gráfica
8. **Áudio**: SDL2, OpenAL, Web Audio
9. **Threading**: SharedArrayBuffer e pthreads
10. **Otimização**: Flags e técnicas de otimização
11. **Exemplo completo**: Processador de sinais

O Emscripten continua sendo a ferramenta mais madura para compilar C++ para WebAssembly, com suporte completo a OpenGL, áudio, threading e muitas outras funcionalidades. Para projetos que exigem高性能 e acesso a APIs de baixo nível, o C++ com Emscripten é uma escolha sólida.
---

*[Capítulo anterior: 04 — Rust Wasm](04-rust-wasm.md)*
*[Próximo capítulo: 06 — Runtimes](06-runtimes.md)*
