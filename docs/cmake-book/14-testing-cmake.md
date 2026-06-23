---
layout: default
title: "14-testing-cmake"
---

# Capítulo 14: Testing no CMake

## Sumário

1. [Objetivos de Aprendizado](#1-objetivos-de-aprendizado)
2. [CTest: enable_testing e add_test](#2-ctest-enable_testing-e-add_test)
3. [Integração com GoogleTest](#3-integração-com-googletest)
4. [Integração com Catch2](#4-integração-com-catch2)
5. [Propriedades de Teste](#5-propriedades-de-teste)
6. [Descoberta de Testes](#6-descoberta-de-testes)
7. [Cobertura de Código](#7-cobertura-de-código)
8. [Integração com Fuzzing](#8-integração-com-fuzzing)
9. [Benchmarking com Google Benchmark](#9-benchmarking-com-google-benchmark)
10. [Testes de Mutação com Mull](#10-testes-de-mutação-com-mull)
11. [CI/CD: Resultados de Testes e Saída do CTest](#11-cicd-resultados-de-testes-e-saída-do-ctest)
12. [CMake Presets para Testes](#12-cmake-presets-para-testes)
13. [Exemplo: Projeto com Suite Completa](#13-exemplo-projeto-com-suite-completa)
14. [Exercícios](#14-exercícios)
15. [Referências](#15-referências)

---

## 1. Objetivos de Aprendizado

Ao final deste capítulo, o leitor será capaz de:

- Configurar e utilizar o CTest como framework de teste nativo do CMake
- Integrar frameworks populares como GoogleTest e Catch2 em projetos CMake
- Definir propriedades avançadas de teste como TIMEOUT, LABELS e FIXTURES_REQUIRED
- Implementar descoberta automática de testes em projetos grandes
- Configurar ferramentas de cobertura de código como gcov, lcov e llvm-cov
- Integrar ferramentas de fuzzing como libFuzzer e AFL++ nos processos de build
- Utilizar o Google Benchmark para medição de desempenho
- Configurar testes de mutação com o Mull
- Gerar relatórios de teste para pipelines de CI/CD
- Utilizar CMake Presets para gerenciar diferentes configurações de teste

O testing é uma parte fundamental do desenvolvimento de software seguro. No contexto do DevSecurity, onde a segurança do código é prioridade, a capacidade de testar de forma abrangente e automatizada é essencial para garantir que vulnerabilidades sejam detectadas antes que cheguem ao ambiente de produção.

### Por que Testing é Crítico para Segurança

A segurança de software depende fundamentalmente da qualidade das verificações automatizadas. Um sistema de testes robusto permite:

- **Detecção precoce de vulnerabilidades**: Testes unitários e de integração podem capturar bugs que seriam explorados por atacantes
- **Regressão de segurança**: Quando uma vulnerabilidade é corrigida, testes específicos garantem que ela não retorne em versões futuras
- **Validação de inputs**: Testes de fuzzing exploram entradas inesperadas que poderiam causar buffers overflow, injeções ou outras vulnerabilidades
- **Cobertura de código**: Medir a cobertura ajuda a identificar código não testado que pode conter vulnerabilidades ocultas
- **Documentação viva**: Testes servem como documentação executável do comportamento esperado do sistema

### Ecossistema de Testing no CMake

O CMake não é apenas uma ferramenta de build — ele oferece um ecossistema completo para gerenciamento de testes. O CTest é o componente nativo que orquestra a execução de testes, enquanto o CMake fornece integração direta com os frameworks mais populares do mercado.

A integração ocorre em vários níveis:

1. **Nível de build**: Definição de alvos de teste e suas dependências
2. **Nível de execução**: Controle de paralelismo, timeouts e filtros
3. **Nível de relatório**: Geração de resultados em formatos padrão para ferramentas de CI/CD
4. **Nível de análise**: Cobertura, performance e mutação testing

---

## 2. CTest: enable_testing e add_test

### Fundamentos do CTest

O CTest é o executor de testes nativo do CMake. Ele permite definir testes diretamente nos arquivos CMakeLists.txt e executá-los de forma padronizada através do comando `ctest`.

#### Ativação do CTest

Para habilitar o CTest em um projeto, é necessário chamar `enable_testing()` no diretório raiz do projeto:

```cmake
cmake_minimum_required(VERSION 3.20)
project(SecureApp VERSION 1.0 LANGUAGES C CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Habilitar CTest no diretório raiz
enable_testing()

# Adicionar subdiretórios com testes
add_subdirectory(src)
add_subdirectory(tests)
```

O comando `enable_testing()` deve ser chamado no diretório raiz do projeto ou nos diretórios onde os testes serão executados. É importante notar que este comando não deve ser colocado dentro de condicionais, pois isso pode causar comportamento inesperado.

#### Adicionando Testes Simples

O comando `add_test()` define um teste individual que o CTest poderá executar:

```cmake
# Em tests/CMakeLists.txt

# Teste simples de execução de comando
add_test(
    NAME test_connection
    COMMAND ${CMAKE_CURRENT_SOURCE_DIR}/test_connection.sh
)

# Teste com argumentos
add_test(
    NAME test_authentication
    COMMAND test_auth --username=admin --password=secret
)

# Teste usando executável do projeto
add_test(
    NAME test_string_utils
    COMMAND test_string_utils --verbose
)
```

#### Estrutura de Diretórios Recomendada

Para projetos de segurança, é recomendado seguinte estrutura:

```
SecureApp/
├── CMakeLists.txt
├── src/
│   ├── CMakeLists.txt
│   ├── auth/
│   │   └── CMakeLists.txt
│   └── crypto/
│       └── CMakeLists.txt
├── tests/
│   ├── CMakeLists.txt
│   ├── unit/
│   │   └── CMakeLists.txt
│   ├── integration/
│   │   └── CMakeLists.txt
│   ├── security/
│   │   └── CMakeLists.txt
│   └── fuzz/
│       └── CMakeLists.txt
└── benchmarks/
    └── CMakeLists.txt
```

#### Configuração Básica do CTest

O arquivo `CTestConfig.cmake` define as configurações globais do CTest:

```cmake
# CTestConfig.cmake

# Configuração do dashboard
set(CTEST_PROJECT_NAME "SecureApp")
set(CTEST_NIGHTLY_START_TIME "01:00:00 UTC")
set(CTEST_DROP_METHOD "https")
set(CTEST_DROP_SITE "myserver.com")
set(CTEST_DROP_LOCATION "/submit.php?project=SecureApp")
set(CTEST_DROP_SITE_CDASH TRUE)

# Configurações de build
set(CTEST_BUILD_CONFIGURATION "Release")
set(CTEST_BUILD_OPTIONS "-DCMAKE_BUILD_TYPE=Release -DENABLE_SECURITY_TESTS=ON")

# Configurações de teste
set(CTEST_TEST_TIMEOUT 300)
set(CTEST_TEST_PARALLEL_LEVEL 4)
```

#### Executando Testes

Após configurar os testes, a execução é feita através do comando `ctest`:

```bash
# Executar todos os testes
ctest

# Executar com verbose
ctest --output-on-failure

# Executar testes específicos por nome
ctest -R "test_connection"

# Executar testes específicos por label
ctest -L "security"

# Executar com paralelismo
ctest -j 4

# Gerar relatório XML
ctest --output-junit results.xml

# Executar apenas testes que falharam anteriormente
ctest --rerun-failed
```

#### Variáveis de Ambiente para Testes

O CMake fornece variáveis de ambiente que podem ser utilizadas nos testes:

```cmake
# Em tests/CMakeLists.txt

# Configurar variáveis de ambiente para testes
set_tests_properties(test_database_connection PROPERTIES
    ENVIRONMENT "DB_HOST=localhost;DB_PORT=5432;DB_NAME=test_db"
)

# Usar variáveis de build no ambiente de teste
set_tests_properties(test_config_load PROPERTIES
    ENVIRONMENT "CONFIG_PATH=${CMAKE_SOURCE_DIR}/config/test.ini"
)

# Adicionar diretório de trabalho
set_tests_properties(test_file_operations PROPERTIES
    WORKING_DIRECTORY ${CMAKE_BINARY_DIR}/test_output
)
```

#### Testes com Dependências

Para testes que dependem de outros testes ou alvos:

```cmake
# Teste que depende de outro teste
add_test(NAME test_database_integration COMMAND test_db_integration)
set_tests_properties(test_database_integration PROPERTIES
    DEPENDS test_database_setup
    FIXTURES_REQUIRED database_setup
)

# Teste que depende de um alvo de build
add_test(NAME test_compiled_plugin COMMAND test_plugin_loader $<TARGET_FILE:myplugin>)
set_tests_properties(test_compiled_plugin PROPERTIES
    DEPENDS myplugin
)
```

#### Executando Testes com CTest Dashboard

O CTest suporta a geração de dashboards para monitoramento de qualidade:

```bash
# Criar diretório de build
mkdir build && cd build

# Configurar com CMake
cmake -DCMAKE_BUILD_TYPE=Release ..

# Build
cmake --build . --config Release

# Executar testes e submeter ao dashboard
ctest -D Experimental
ctest -D Nightly
ctest -D Continuous
```

#### Arquivo CTestCustom

O `CTestCustom.cmake` permite personalizar o comportamento do CTest:

```cmake
# CTestCustom.cmake

# Filtros de teste
list(APPEND CTEST_CUSTOM_TESTS_IGNORE
    "test_known_failure_1"
    "test_known_failure_2"
)

# Limpar diretórios após testes
list(APPEND CTEST_CUSTOM_POST_TEST "clean_test_artifacts.cmake")

# Configurações de memória
set(CTEST_MEMORYCHECK_COMMAND "valgrind")
set(CTEST_MEMORYCHECK_COMMAND_OPTIONS "--leak-check=full --track-origins=yes")
set(CTEST_MEMORYCHECK_SUPPRESSIONS_FILE "${CMAKE_SOURCE_DIR}/valgrind.supp")
```

---

## 3. Integração com GoogleTest

### GoogleTest: O Framework Padrão

O GoogleTest é o framework de testes mais utilizado em projetos C++, oferecendo suporte completo a testes unitários, testes de integração e testes de parâmetros.

#### FetchContent: Download Automático

A forma mais moderna de integrar o GoogleTest é através do `FetchContent`:

```cmake
# CMakeLists.txt principal

cmake_minimum_required(VERSION 3.20)
project(SecureApp VERSION 1.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Habilitar testes
enable_testing()

# Buscar GoogleTest via FetchContent
include(FetchContent)
FetchContent_Declare(
    googletest
    GIT_REPOSITORY https://github.com/google/googletest.git
    GIT_TAG v1.14.0
)

# Configurar GoogleTest para usar o mesmo runtime do projeto
set(gtest_force_shared_crt ON CACHE BOOL "" FORCE)
FetchContent_MakeAvailable(googletest)

# Adicionar diretórios
add_subdirectory(src)
add_subdirectory(tests)
```

#### find_package: GoogleTest Instalado

Para projetos que preferem usar o GoogleTest já instalado no sistema:

```cmake
# CMakeLists.txt

find_package(GTest REQUIRED)
find_package(Threads REQUIRED)

# Criar executável de teste
add_executable(unit_tests
    test_string_utils.cpp
    test_crypto.cpp
    test_auth.cpp
)

# Linkar com GoogleTest
target_link_libraries(unit_tests
    PRIVATE
        GTest::gtest
        GTest::gtest_main
        Threads::Threads
        myproject_lib
)

# Adicionar ao CTest
include(GoogleTest)
gtest_discover_tests(unit_tests)
```

#### Estrutura de Testes com GoogleTest

```cpp
// tests/unit/test_string_utils.cpp

#include <gtest/gtest.h>
#include "string_utils.h"

class StringUtilsTest : public ::testing::Test {
protected:
    void SetUp() override {
        // Configuração comum para todos os testes
        test_input = "sensitive_data_123";
    }

    void TearDown() override {
        // Limpeza após cada teste
        test_input.clear();
    }

    std::string test_input;
};

// Teste de validação de entrada
TEST_F(StringUtilsTest, ValidatesInputCorrectly) {
    EXPECT_TRUE(is_valid_input("normal_string"));
    EXPECT_FALSE(is_valid_input(""));
    EXPECT_FALSE(is_valid_input(nullptr));
}

// Teste de sanitização de strings
TEST_F(StringUtilsTest, SanitizesSpecialCharacters) {
    std::string input = "user<script>alert('xss')</script>";
    std::string expected = "user&lt;script&gt;alert(&#39;xss&#39;)&lt;/script&gt;";
    EXPECT_EQ(sanitize_string(input), expected);
}

// Teste de criptografia básica
TEST_F(StringUtilsTest, EncryptionRoundTrip) {
    std::string original = "dados_sensiveis";
    std::string encrypted = encrypt_string(original);
    std::string decrypted = decrypt_string(encrypted);

    EXPECT_EQ(original, decrypted);
    EXPECT_NE(original, encrypted);
}

// Teste de performance
TEST_F(StringUtilsTest, LargeStringPerformance) {
    std::string large_string(1000000, 'a');

    auto start = std::chrono::high_resolution_clock::now();
    std::string result = sanitize_string(large_string);
    auto end = std::chrono::high_resolution_clock::now();

    auto duration = std::chrono::duration_cast<std::chrono::milliseconds>(end - start);
    EXPECT_LT(duration.count(), 100); // Deve ser menor que 100ms
}

// Testes de parâmetros
class ParameterizedTest : public ::testing::TestWithParam<std::pair<std::string, bool>> {};

TEST_P(ParameterizedTest, InputValidation) {
    auto [input, expected] = GetParam();
    EXPECT_EQ(is_valid_input(input), expected);
}

INSTANTIATE_TEST_SUITE_P(
    SecurityTests,
    ParameterizedTest,
    ::testing::Values(
        std::make_pair("normal_input", true),
        std::make_pair("'; DROP TABLE users;--", false),
        std::make_pair("<script>alert(1)</script>", false),
        std::make_pair("../../../etc/passwd", false),
        std::make_pair("valid_user_123", true)
    )
);
```

#### GoogleTest com Mocks

Para testes de integração que requerem mocks:

```cmake
# tests/CMakeLists.txt

# Biblioteca de mocks
add_library(security_mocks STATIC
    mocks/mock_database.cpp
    mocks/mock_crypto_provider.cpp
    mocks/mock_network.cpp
)

target_include_directories(security_mocks
    PUBLIC ${CMAKE_CURRENT_SOURCE_DIR}/mocks
)

target_link_libraries(security_mocks
    PUBLIC
        GTest::gmock
        myproject_lib
)

# Testes de integração
add_executable(integration_tests
    integration/test_auth_flow.cpp
    integration/test_database_operations.cpp
)

target_link_libraries(integration_tests
    PRIVATE
        security_mocks
        GTest::gtest
        GTest::gtest_main
        GTest::gmock
        myproject_lib
)

gtest_discover_tests(integration_tests)
```

#### Exemplo de Mock

```cpp
// tests/mocks/mock_database.hpp

#pragma once

#include <gmock/gmock.h>
#include "database_interface.h"

class MockDatabase : public IDatabase {
public:
    MOCK_METHOD(bool, connect, (const std::string& host, int port), (override));
    MOCK_METHOD(bool, disconnect, (), (override));
    MOCK_METHOD(QueryResult, execute, (const std::string& query), (override));
    MOCK_METHOD(bool, begin_transaction, (), (override));
    MOCK_METHOD(bool, commit_transaction, (), (override));
    MOCK_METHOD(bool, rollback_transaction, (), (override));
    MOCK_METHOD(bool, is_connected, (), (const, override));
};

// Teste usando o mock
TEST(AuthenticationTest, LoginWithValidCredentials) {
    MockDatabase mock_db;

    EXPECT_CALL(mock_db, connect(testing::_, testing::_))
        .WillOnce(testing::Return(true));

    EXPECT_CALL(mock_db, execute(testing::_))
        .WillOnce(testing::Return(QueryResult{true, {{"user_id", "123"}}}));

    EXPECT_CALL(mock_db, disconnect())
        .WillOnce(testing::Return(true));

    AuthService auth_service(&mock_db);
    EXPECT_TRUE(auth_service.login("admin", "secure_password"));
}
```

#### Configurações Avançadas do GoogleTest

```cmake
# Configurações avançadas do GoogleTest

# Habilitar testes assíncronos
set(INSTALL_GTEST OFF CACHE BOOL "" FORCE)

# Configurar comportamento de falha
add_compile_definitions(
    GTEST_FAIL_ON_FAST_LEAK=1
    GTEST_HAS_ABSL=1
)

# Testes com sanitizers
option(ENABLE_ASAN "Enable AddressSanitizer" OFF)
option(ENABLE_TSAN "Enable ThreadSanitizer" OFF)
option(ENABLE_UBSAN "Enable UndefinedBehaviorSanitizer" OFF)

if(ENABLE_ASAN)
    target_compile_options(unit_tests PRIVATE -fsanitize=address -fno-omit-frame-pointer)
    target_link_options(unit_tests PRIVATE -fsanitize=address)
endif()

if(ENABLE_TSAN)
    target_compile_options(unit_tests PRIVATE -fsanitize=thread -fno-omit-frame-pointer)
    target_link_options(unit_tests PRIVATE -fsanitize=thread)
endif()

if(ENABLE_UBSAN)
    target_compile_options(unit_tests PRIVATE -fsanitize=undefined)
    target_link_options(unit_tests PRIVATE -fsanitize=undefined)
endif()
```

---

## 4. Integração com Catch2

### Catch2: Framework Moderno e Expressivo

O Catch2 é um framework de testes moderno que oferece uma sintaxe mais expressiva e intuitiva, além de recursos avançados como testes BDD (Behavior-Driven Development).

#### Instalação via FetchContent

```cmake
# CMakeLists.txt principal

cmake_minimum_required(VERSION 3.20)
project(SecureApp VERSION 1.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

enable_testing()

# Buscar Catch2 via FetchContent
include(FetchContent)
FetchContent_Declare(
    Catch2
    GIT_REPOSITORY https://github.com/catchorg/Catch2.git
    GIT_TAG v3.5.2
)
FetchContent_MakeAvailable(Catch2)

# Adicionar diretórios
add_subdirectory(src)
add_subdirectory(tests)
```

#### Estrutura de Testes com Catch2

```cpp
// tests/unit/test_crypto.cpp

#define CATCH_CONFIG_MAIN
#include <catch2/catch_test_macros.hpp>
#include <catch2/catch_approx.hpp>
#include <catch2/catch_session.hpp>
#include "crypto_utils.h"

using Catch::Approx;

// Teste simples de criptografia
TEST_CASE("Encryption and Decryption", "[crypto]") {
    GIVEN("A valid encryption key") {
        std::string key = generate_key(256);
        REQUIRE_FALSE(key.empty());

        WHEN("Encrypting a plaintext") {
            std::string plaintext = "dados_sensiveis";
            std::string encrypted = encrypt_aes256(plaintext, key);

            THEN("The ciphertext should be different from plaintext") {
                REQUIRE(encrypted != plaintext);
                REQUIRE_FALSE(encrypted.empty());
            }

            AND_WHEN("Decrypting the ciphertext") {
                std::string decrypted = decrypt_aes256(encrypted, key);

                THEN("The decrypted text should match the original") {
                    REQUIRE(decrypted == plaintext);
                }
            }
        }
    }
}

// Teste de validação de certificate
TEST_CASE("Certificate Validation", "[security][certificate]") {
    SECTION("Valid certificate") {
        Certificate cert("valid_cert.pem");
        REQUIRE(cert.is_valid());
        REQUIRE_FALSE(cert.has_expired());
        REQUIRE(cert.get_issuer() == "Trusted CA");
    }

    SECTION("Expired certificate") {
        Certificate cert("expired_cert.pem");
        REQUIRE_FALSE(cert.is_valid());
        REQUIRE(cert.has_expired());
    }

    SECTION("Self-signed certificate") {
        Certificate cert("self_signed.pem");
        REQUIRE_FALSE(cert.is_trusted());
    }
}

// Teste de performance com benchmarks
TEST_CASE("Performance benchmarks", "[!benchmark]") {
    std::string large_data(1000000, 'x');

    BENCHMARK("AES256 encryption") {
        return encrypt_aes256(large_data, generate_key(256));
    };

    BENCHMARK("SHA256 hashing") {
        return sha256(large_data);
    };
}

// Teste parametrizado
TEST_CASE("Parameterized input validation", "[security][validation]") {
    auto [input, expected_valid] = GENERATE(
        table<std::string, bool>({
            {"normal_input", true},
            {"'; DROP TABLE users;--", false},
            {"<script>alert(1)</script>", false},
            {"../../../etc/passwd", false},
            {"valid_user_123", true},
            {"", false},
            {"admin' OR '1'='1", false}
        })
    );

    REQUIRE(is_valid_input(input) == expected_valid);
}
```

#### Configuração CMake para Catch2

```cmake
# tests/CMakeLists.txt

# Executável de testes unitários
add_executable(unit_tests
    unit/test_crypto.cpp
    unit/test_auth.cpp
    unit/test_database.cpp
    unit/test_network.cpp
)

target_link_libraries(unit_tests
    PRIVATE
        Catch2::Catch2WithMain
        myproject_lib
)

# Descoberta automática de testes
include(Catch)
catch_discover_tests(unit_tests
    TEST_PREFIX "unit."
    PROPERTIES
        LABELS "unit;security"
        TIMEOUT 30
)

# Testes de integração
add_executable(integration_tests
    integration/test_auth_flow.cpp
    integration/test_database.cpp
)

target_link_libraries(integration_tests
    PRIVATE
        Catch2::Catch2WithMain
        myproject_lib
        GTest::gmock
)

catch_discover_tests(integration_tests
    TEST_PREFIX "integration."
    PROPERTIES
        LABELS "integration"
        TIMEOUT 120
)

# Testes de segurança
add_executable(security_tests
    security/test_input_validation.cpp
    security/test_buffer_overflow.cpp
    security/test_sql_injection.cpp
)

target_link_libraries(security_tests
    PRIVATE
        Catch2::Catch2WithMain
        myproject_lib
)

catch_discover_tests(security_tests
    TEST_PREFIX "security."
    PROPERTIES
        LABELS "security;critical"
        TIMEOUT 60
)
```

#### Configurações Avançadas do Catch2

```cpp
// tests/unit/test_config.cpp

#include <catch2/catch_test_macros.hpp>
#include <catch2/catch_session.hpp>

// Custom reporter para output em JSON
class JsonReporter : public Catch::EventListenerBase {
public:
    using EventListenerBase::EventListenerBase;

    void testRunEnded(Catch::TestRunStats const& testRunStats) override {
        // Gerar relatório JSON dos resultados
        nlohmann::json report;
        report["total"] = testRunStats.totals.testCases.all();
        report["passed"] = testRunStats.totals.testCases.passed;
        report["failed"] = testRunStats.totals.testCases.failed;

        std::ofstream file("test_results.json");
        file << report.dump(4);
    }
};

CATCH_REGISTER_LISTENER(JsonReporter)

// Custom section para testes de segurança
class SecurityTestListener : public Catch::TestEventListenerBase {
public:
    using TestEventListenerBase::TestEventListenerBase;

    void testCaseStarting(Catch::TestCaseInfo const& testInfo) override {
        if (testInfo.hasTag("[security]")) {
            std::cout << "Running security test: " << testInfo.name << std::endl;
        }
    }
};
```

---

## 5. Propriedades de Teste

### Definindo Propriedades Avançadas

O CMake permite definir propriedades detalhadas para cada teste, controlando comportamento como timeout, labels, fixtures e muito mais.

#### Propriedade TIMEOUT

```cmake
# Configurar timeout para testes específicos

# Teste rápido: máximo 10 segundos
add_test(NAME test_quick_check COMMAND test_quick)
set_tests_properties(test_quick_check PROPERTIES TIMEOUT 10)

# Teste de integração: máximo 5 minutos
add_test(NAME test_full_integration COMMAND test_integration)
set_tests_properties(test_full_integration PROPERTIES TIMEOUT 300)

# Teste de longa duração: máximo 30 minutos
add_test(NAME test_stress COMMAND test_stress --duration=1800)
set_tests_properties(test_stress PROPERTIES TIMEOUT 1800)

# Timeout global (aplicável a todos os testes)
set_tests_properties(
    test_a
    test_b
    test_c
    PROPERTIES TIMEOUT 60
)
```

#### Propriedade LABELS

Labels permitem categorizar testes para execução seletiva:

```cmake
# Definir labels para diferentes categorias de teste

# Testes unitários
set_tests_properties(
    test_string_utils
    test_crypto_basic
    test_auth_unit
    PROPERTIES LABELS "unit;fast"
)

# Testes de integração
set_tests_properties(
    test_database_integration
    test_auth_flow
    PROPERTIES LABELS "integration;slow"
)

# Testes de segurança (críticos)
set_tests_properties(
    test_buffer_overflow
    test_sql_injection
    test_xss_prevention
    PROPERTIES LABELS "security;critical"
)

# Testes de performance
set_tests_properties(
    test_encryption_performance
    test_hash_performance
    PROPERTIES LABELS "performance;benchmark"
)

# Executar apenas testes de segurança
# ctest -L security

# Executar testes rápidos
# ctest -L "fast"

# Excluir testes de longa duração
# ctest -LE "slow"
```

#### Propriedade FIXTURES_REQUIRED

Fixtures garantem que testes executem na ordem correta e com o ambiente adequado:

```cmake
# Definir fixture de setup
add_test(NAME setup_database COMMAND setup_test_db)
set_tests_properties(setup_database PROPERTIES
    FIXTURES_SETUP database_fixture
    TIMEOUT 60
)

# Testes que requerem o fixture
add_test(NAME test_user_creation COMMAND test_user_create)
set_tests_properties(test_user_creation PROPERTIES
    FIXTURES_REQUIRED database_fixture
    FIXTURES_CLEANUP database_fixture
    DEPENDS setup_database
)

add_test(NAME test_user_authentication COMMAND test_auth_user)
set_tests_properties(test_user_authentication PROPERTIES
    FIXTURES_REQUIRED database_fixture
    DEPENDS test_user_creation
)

# Fixture de cleanup automático
add_test(NAME cleanup_database COMMAND cleanup_test_db)
set_tests_properties(cleanup_database PROPERTIES
    FIXTURES_CLEANUP database_fixture
    TIMEOUT 30
)

# Múltiplos fixtures
add_test(NAME setup_crypto COMMAND setup_crypto_env)
set_tests_properties(setup_crypto PROPERTIES
    FIXTURES_SETUP crypto_fixture
)

add_test(NAME test_encryption COMMAND test_encrypt)
set_tests_properties(test_encryption PROPERTIES
    FIXTURES_REQUIRED "database_fixture;crypto_fixture"
)
```

#### Propriedade WORKING_DIRECTORY

```cmake
# Configurar diretório de trabalho para testes

# Teste que precisa de arquivos no diretório atual
add_test(NAME test_config_load COMMAND test_config)
set_tests_properties(test_config_load PROPERTIES
    WORKING_DIRECTORY ${CMAKE_SOURCE_DIR}/config
)

# Teste com diretório temporário
add_test(NAME test_file_operations COMMAND test_files)
set_tests_properties(test_file_operations PROPERTIES
    WORKING_DIRECTORY ${CMAKE_BINARY_DIR}/test_output
)

# Criar diretório antes do teste
file(MAKE_DIRECTORY ${CMAKE_BINARY_DIR}/test_output)
```

#### Propriedade ENVIRONMENT

```cmake
# Configurar variáveis de ambiente para testes

# Variáveis de banco de dados
set_tests_properties(test_database COMMAND test_db)
set_tests_properties(test_database PROPERTIES
    ENVIRONMENT
        "DB_HOST=localhost;DB_PORT=5432;DB_NAME=test_db;DB_USER=test;DB_PASS=test123"
)

# Variáveis de configuração
set_tests_properties(test_config COMMAND test_config)
set_tests_properties(test_config PROPERTIES
    ENVIRONMENT
        "APP_ENV=test;LOG_LEVEL=debug;CACHE_TTL=300"
)

# Usar variáveis do CMake no ambiente
set_tests_properties(test_paths COMMAND test_paths)
set_tests_properties(test_paths PROPERTIES
    ENVIRONMENT
        "PROJECT_ROOT=${CMAKE_SOURCE_DIR};BUILD_DIR=${CMAKE_BINARY_DIR}"
)
```

#### Propriedade PROCESSORS

Controla quantos processadores um teste pode utilizar:

```cmake
# Teste single-threaded
add_test(NAME test_single_thread COMMAND test_single)
set_tests_properties(test_single_thread PROPERTIES
    PROCESSORS 1
)

# Teste multi-threaded
add_test(NAME test_multi_thread COMMAND test_multi --threads=8)
set_tests_properties(test_multi_thread PROPERTIES
    PROCESSORS 8
)

# Configurar paralelismo global
set(CTEST_TEST_PARALLEL_LEVEL 4)
```

#### Propriedade RESOURCE_LOCK

Garante exclusividade de recursos entre testes:

```cmake
# Testes que usam o mesmo banco de dados não podem rodar em paralelo
add_test(NAME test_db_write_1 COMMAND test_write1)
set_tests_properties(test_db_write_1 PROPERTIES
    RESOURCE_LOCK database
)

add_test(NAME test_db_write_2 COMMAND test_write2)
set_tests_properties(test_db_write_2 PROPERTIES
    RESOURCE_LOCK database
)

# Teste de leitura pode rodar em paralelo
add_test(NAME test_db_read COMMAND test_read)
set_tests_properties(test_db_read PROPERTIES
    RESOURCE_LOCK database_read
)
```

#### Propriedade WILL_FAIL

Útil para testes que verificam comportamento de falha:

```cmake
# Teste que deve falhar (verificação negativa)
add_test(NAME test_invalid_input COMMAND test_validation "malicious_input")
set_tests_properties(test_invalid_input PROPERTIES
    WILL_FAIL TRUE
    LABELS "security;negative"
)

# Teste de timeout que deve exceder o limite
add_test(NAME test_timeout_behavior COMMAND test_long_running)
set_tests_properties(test_timeout_behavior PROPERTIES
    TIMEOUT 5
    WILL_FAIL TRUE
)
```

#### Propriedade PASS_REGULAR_EXPRESSION e FAIL_REGULAR_EXPRESSION

```cmake
# Verificar saída do teste com expressões regulares

# Teste deve conter "PASS" na saída
add_test(NAME test_output_check COMMAND test_output)
set_tests_properties(test_output_check PROPERTIES
    PASS_REGULAR_EXPRESSION "Test passed|All tests passed"
)

# Teste deve conter "ERROR" na saída para indicar falha
add_test(NAME test_error_handling COMMAND test_errors)
set_tests_properties(test_error_handling PROPERTIES
    PASS_REGULAR_EXPRESSION "ERROR:.*handled correctly"
    FAIL_REGULAR_EXPRESSION "FATAL|SEGFAULT"
)

# Teste deve conter "100%" para verificar completude
add_test(NAME test_coverage_check COMMAND test_coverage)
set_tests_properties(test_coverage_check PROPERTIES
    PASS_REGULAR_EXPRESSION "Coverage: 100%"
)
```

#### Propriedade ATTACHED_FILES e ATTACHED_FILES_ON_FAIL

```cmake
# Anexar arquivos aos resultados do teste

# Sempre anexar log
add_test(NAME test_with_log COMMAND test_app)
set_tests_properties(test_with_log PROPERTIES
    ATTACHED_FILES "${CMAKE_BINARY_DIR}/test.log"
)

# Anexar arquivos apenas em caso de falha
add_test(NAME test_debug_output COMMAND test_app --verbose)
set_tests_properties(test_debug_output PROPERTIES
    ATTACHED_FILES_ON_FAIL
        "${CMAKE_BINARY_DIR}/debug.log;${CMAKE_BINARY_DIR}/core.dump"
)
```

#### Propriedade SKIP_REGULAR_EXPRESSION

```cmake
# Pular teste se determinada mensagem aparecer na saída
add_test(NAME test_optional_feature COMMAND test_feature)
set_tests_properties(test_optional_feature PROPERTIES
    SKIP_REGULAR_EXPRESSION "Feature not available;Not implemented"
)
```

---

## 6. Descoberta de Testes

### Descoberta Automática de Testes

Em projetos grandes com muitos testes, a descoberta automática elimina a necessidade de listar cada teste manualmente no CMakeLists.txt.

#### GoogleTest Discovery

O `gtest_discover_tests()` do CMake permite descoberta automática:

```cmake
# tests/CMakeLists.txt

find_package(GTest REQUIRED)

# Criar executável de testes
add_executable(all_tests
    unit/test1.cpp
    unit/test2.cpp
    integration/test3.cpp
    security/test4.cpp
)

target_link_libraries(all_tests
    PRIVATE
        GTest::gtest
        GTest::gtest_main
        myproject_lib
)

# Descoberta automática de testes
include(GoogleTest)
gtest_discover_tests(all_tests
    # Prefixo para todos os testes descobertos
    TEST_PREFIX myproject.
    
    # Separador entre prefixo e nome do teste
    TEST_SEPARATOR "/"
    
    # Propriedades padrão para todos os testes
    PROPERTIES
        TIMEOUT 30
        LABELS "unit"
    
    # Filtrar testes por nome
    DISCOVERY_TIMEOUT 30
    
    # Usar propriedades de discovery
    DISCOVERY_MODE PRE_TEST
)

# Descoberta com filtros específicos
gtest_discover_tests(all_tests
    TEST_PREFIX security.
    PROPERTIES LABELS "security;critical"
    DISCOVERY_MODE POST_TEST
)
```

#### Catch2 Discovery

O `catch_discover_tests()` oferece funcionalidade similar:

```cmake
find_package(Catch2 3 REQUIRED)

add_executable(catch_tests
    test_auth.cpp
    test_crypto.cpp
    test_database.cpp
)

target_link_libraries(catch_tests
    PRIVATE
        Catch2::Catch2WithMain
        myproject_lib
)

include(Catch)
catch_discover_tests(catch_tests
    TEST_PREFIX catch.
    PROPERTIES
        TIMEOUT 60
        LABELS "unit;security"
    
    # Configurar argumentos extras para discovery
    EXTRA_ARGS "--reporter" "xml"
    
    # Filtrar testes
    TEST_SPEC "[security]"
    
    # Usar diretório de trabalho específico
    WORKING_DIRECTORY ${CMAKE_BINARY_DIR}
)
```

#### CTestTestfile.cmake

O `CTestTestfile.cmake` é gerado automaticamente pelo CMake durante a configuração:

```cmake
# CTestTestfile.cmake (gerado automaticamente)

# Este arquivo é gerado pelo CMake e não deve ser editado manualmente

# Adicionar testes deste diretório
add_test("unit/test_string_utils" "test_string_utils")
set_tests_properties("unit/test_string_utils" PROPERTIES
    LABELS "unit;fast"
    TIMEOUT 10
)

add_test("unit/test_crypto" "test_crypto")
set_tests_properties("unit/test_crypto" PROPERTIES
    LABELS "unit;security"
    TIMEOUT 30
)

# Adicionar subdiretórios
subdirs("integration")
subdirs("security")
```

#### Estrutura de Descoberta em Projetos Grandes

```cmake
# tests/CMakeLists.txt

# Função para adicionar suite de testes
function(add_test_suite SUITE_NAME)
    set(options "")
    set(oneValueArgs LABEL TIMEOUT)
    set(multiValueArgs SOURCES DEPENDS)
    
    cmake_parse_arguments(SUITE "${options}" "${oneValueArgs}" "${multiValueArgs}" ${ARGN})
    
    # Criar executável
    add_executable(${SUITE_NAME}_tests ${SUITE_SOURCES})
    
    # Linkar dependências
    target_link_libraries(${SUITE_NAME}_tests
        PRIVATE
            GTest::gtest
            GTest::gtest_main
            myproject_lib
            ${SUITE_DEPENDS}
    )
    
    # Descobrir testes
    gtest_discover_tests(${SUITE_NAME}_tests
        TEST_PREFIX ${SUITE_NAME}.
        PROPERTIES
            LABELS "${SUITE_LABEL}"
            TIMEOUT "${SUITE_TIMEOUT}"
    )
endfunction()

# Usar a função
add_test_suite(unit
    SOURCES
        unit/test_string.cpp
        unit/test_crypto.cpp
    LABEL "unit"
    TIMEOUT 30
)

add_test_suite(integration
    SOURCES
        integration/test_auth.cpp
        integration/test_database.cpp
    LABEL "integration"
    TIMEOUT 120
    DEPENDS GTest::gmock
)

add_test_suite(security
    SOURCES
        security/test_xss.cpp
        security/test_sqli.cpp
    LABEL "security;critical"
    TIMEOUT 60
)
```

#### Custom Discovery Script

Para casos onde a descoberta padrão não atende:

```cmake
# custom_discovery.cmake

function(custom_discover_tests TEST_EXECUTABLE)
    # Executar o executável com flag de listagem
    execute_process(
        COMMAND ${TEST_EXECUTABLE} --list-tests
        OUTPUT_VARIABLE TEST_LIST
        OUTPUT_STRIP_TRAILING_WHITESPACE
    )
    
    # Processar cada teste
    string(REPLACE "\n" ";" TEST_LINES "${TEST_LIST}")
    foreach(TEST_LINE ${TEST_LINES})
        if(TEST_LINE MATCHES "^  ([a-zA-Z0-9_]+)")
            set(TEST_NAME ${CMAKE_MATCH_1})
            
            add_test(
                NAME ${TEST_EXECUTABLE}/${TEST_NAME}
                COMMAND ${TEST_EXECUTABLE} --run=${TEST_NAME}
            )
            
            set_tests_properties(${TEST_EXECUTABLE}/${TEST_NAME} PROPERTIES
                TIMEOUT 30
                LABELS "auto-discovered"
            )
        endif()
    endforeach()
endfunction()

# Usar
custom_discover_tests(my_test_executable)
```

#### Organização por Diretórios

```cmake
# tests/unit/CMakeLists.txt

file(GLOB_RECURSE UNIT_TEST_SOURCES "*.cpp")
add_executable(unit_tests ${UNIT_TEST_SOURCES})

target_link_libraries(unit_tests
    PRIVATE
        GTest::gtest
        GTest::gtest_main
        myproject_lib
)

# Descobrir com prefixo baseado no diretório
gtest_discover_tests(unit_tests
    TEST_PREFIX unit/
    PROPERTIES
        LABELS "unit"
        TIMEOUT 30
)

# tests/integration/CMakeLists.txt

file(GLOB_RECURSE INTEGRATION_TEST_SOURCES "*.cpp")
add_executable(integration_tests ${INTEGRATION_TEST_SOURCES})

target_link_libraries(integration_tests
    PRIVATE
        GTest::gtest
        GTest::gtest_main
        myproject_lib
)

gtest_discover_tests(integration_tests
    TEST_PREFIX integration/
    PROPERTIES
        LABELS "integration"
        TIMEOUT 120
)

# tests/security/CMakeLists.txt

file(GLOB_RECURSE SECURITY_TEST_SOURCES "*.cpp")
add_executable(security_tests ${SECURITY_TEST_SOURCES})

target_link_libraries(security_tests
    PRIVATE
        GTest::gtest
        GTest::gtest_main
        myproject_lib
)

gtest_discover_tests(security_tests
    TEST_PREFIX security/
    PROPERTIES
        LABELS "security;critical"
        TIMEOUT 60
)
```

---

## 7. Cobertura de Código

### Medindo Cobertura de Código

A cobertura de código é essencial para identificar partes do código que não estão sendo testadas, o que é particularmente importante em projetos de segurança.

#### Configuração com gcov/lcov

```cmake
# CMakeLists.txt principal

option(ENABLE_COVERAGE "Enable code coverage" OFF)

if(ENABLE_COVERAGE)
    # Verificar se o compilador suporta coverage
    if(CMAKE_CXX_COMPILER_ID MATCHES "GNU|Clang")
        message(STATUS "Enabling code coverage with ${CMAKE_CXX_COMPILER_ID}")
        
        # Adicionar flags de coverage
        add_compile_options(-fprofile-arcs -ftest-coverage)
        add_link_options(-fprofile-arcs -ftest-coverage)
        
        # Encontrar lcov e genhtml
        find_program(LCOV_PATH lcov)
        find_program(GENHTML_PATH genhtml)
        
        if(NOT LCOV_PATH)
            message(FATAL_ERROR "lcov not found! Install lcov package.")
        endif()
        
        if(NOT GENHTML_PATH)
            message(FATAL_ERROR "genhtml not found! Install lcov package.")
        endif()
        
        # Target para capturar coverage
        add_custom_target(coverage
            COMMAND ${LCOV_PATH} --directory ${CMAKE_BINARY_DIR} --zerocounters
            COMMAND ${CMAKE_CTEST_COMMAND} --output-on-failure
            COMMAND ${LCOV_PATH} --directory ${CMAKE_BINARY_DIR} --capture --output-file coverage.info
            COMMAND ${LCOV_PATH} --remove coverage.info '/usr/*' '${CMAKE_SOURCE_DIR}/tests/*' --output-file coverage_filtered.info
            COMMAND ${GENHTML_PATH} coverage_filtered.info --output-directory coverage_report
            WORKING_DIRECTORY ${CMAKE_BINARY_DIR}
            COMMENT "Generating code coverage report"
        )
        
        # Target para limpar coverage
        add_custom_target(clean-coverage
            COMMAND ${LCOV_PATH} --directory ${CMAKE_BINARY_DIR} --zerocounters
            COMMAND rm -f coverage.info coverage_filtered.info
            COMMAND rm -rf coverage_report
            WORKING_DIRECTORY ${CMAKE_BINARY_DIR}
            COMMENT "Cleaning coverage data"
        )
    else()
        message(WARNING "Code coverage not supported with ${CMAKE_CXX_COMPILER_ID}")
    endif()
endif()
```

#### Configuração com llvm-cov

```cmake
# Para Clang/LLVM

if(ENABLE_COVERAGE AND CMAKE_CXX_COMPILER_ID MATCHES "Clang")
    # Encontrar llvm-cov
    find_program(LLVM_COV_PATH llvm-cov)
    find_program(LLVM_PROFDATA_PATH llvm-profdata)
    
    if(NOT LLVM_COV_PATH)
        message(FATAL_ERROR "llvm-cov not found!")
    endif()
    
    # Flags específicas para Clang
    add_compile_options(
        -fprofile-instr-generate
        -fcoverage-mapping
    )
    add_link_options(
        -fprofile-instr-generate
    )
    
    # Target para gerar relatório
    add_custom_target(coverage-clang
        COMMAND ${CMAKE_CTEST_COMMAND} --output-on-failure
        COMMAND ${LLVM_PROFDATA_PATH} merge -sparse default.profraw -o coverage.profdata
        COMMAND ${LLVM_COV_PATH} report ${CMAKE_BINARY_DIR}/my_app -instr-profile=coverage.profdata
        COMMAND ${LLVM_COV_PATH} show ${CMAKE_BINARY_DIR}/my_app -instr-profile=coverage.profdata -format=html > coverage_report.html
        WORKING_DIRECTORY ${CMAKE_BINARY_DIR}
        COMMENT "Generating LLVM coverage report"
    )
endif()
```

#### Configuração com gcovr

```cmake
# Alternativa ao lcov: gcovr

find_program(GCOVR_PATH gcovr)

if(GCOVR_PATH AND ENABLE_COVERAGE)
    add_custom_target(coverage-gcovr
        COMMAND ${GCOVR_PATH}
            --root ${CMAKE_SOURCE_DIR}
            --filter ${CMAKE_SOURCE_DIR}/src/
            --exclude ${CMAKE_SOURCE_DIR}/tests/
            --print-summary
            --xml-pretty
            --xml coverage.xml
            --html-details coverage.html
            --json coverage.json
            --decisions
            --calls
            --merge-mode-functions=separate
            ${CMAKE_BINARY_DIR}
        WORKING_DIRECTORY ${CMAKE_BINARY_DIR}
        COMMENT "Generating coverage report with gcovr"
    )
endif()
```

#### Coverage para Múltiplos Alvos

```cmake
# Coverage granular por biblioteca

function(add_coverage_target TARGET_NAME)
    if(ENABLE_COVERAGE)
        add_custom_target(${TARGET_NAME}-coverage
            COMMAND ${LCOV_PATH} --directory ${CMAKE_BINARY_DIR}/CMakeFiles/${TARGET_NAME}.dir --capture --output-file ${TARGET_NAME}.info
            COMMAND ${LCOV_PATH} --extract ${TARGET_NAME}.info '${CMAKE_SOURCE_DIR}/src/${TARGET_NAME}/*' --output-file ${TARGET_NAME}_filtered.info
            COMMAND ${GENHTML_PATH} ${TARGET_NAME}_filtered.info --output-directory coverage_${TARGET_NAME}
            WORKING_DIRECTORY ${CMAKE_BINARY_DIR}
            COMMENT "Generating coverage for ${TARGET_NAME}"
        )
    endif()
endfunction()

# Criar targets de coverage para cada biblioteca
add_coverage_target(auth)
add_coverage_target(crypto)
add_coverage_target(database)
add_coverage_target(network)

# Coverage total
add_custom_target(coverage-all
    DEPENDS auth-coverage crypto-coverage database-coverage network-coverage
    COMMENT "Generating coverage for all components"
)
```

#### Threshold de Coverage

```cmake
# Verificar threshold mínimo de coverage

if(ENABLE_COVERAGE)
    add_custom_target(check-coverage
        COMMAND ${Python3_EXECUTABLE} ${CMAKE_SOURCE_DIR}/scripts/check_coverage.py
            --input coverage_filtered.info
            --min-line 80
            --min-function 75
            --min-branch 70
        WORKING_DIRECTORY ${CMAKE_BINARY_DIR}
        COMMENT "Checking coverage thresholds"
    )
    
    # Script Python para verificação (scripts/check_coverage.py)
    # Lê o arquivo .info do lcov e verifica thresholds
endif()
```

#### Coverage no CTest

```cmake
# Integrar coverage com CTest

if(ENABLE_COVERAGE)
    # Adicionar teste de coverage
    add_test(NAME coverage_check
        COMMAND ${CMAKE_SOURCE_DIR}/scripts/check_coverage.sh
        WORKING_DIRECTORY ${CMAKE_BINARY_DIR}
    )
    
    set_tests_properties(coverage_check PROPERTIES
        LABELS "coverage"
        TIMEOUT 120
        PASS_REGULAR_EXPRESSION "Coverage passed: [0-9]+%"
    )
    
    # Script de verificação (scripts/check_coverage.sh)
    #!/bin/bash
    # lcov --capture --directory . --output-file coverage.info
    # COVERAGE=$(lcov --summary coverage.info 2>&1 | grep "lines" | awk '{print $2}' | sed 's/%//')
    # if [ $(echo "$COVERAGE < 80" | bc) -eq 1 ]; then
    #     echo "FAIL: Coverage $COVERAGE% is below 80% threshold"
    #     exit 1
    # fi
    # echo "PASS: Coverage $COVERAGE% meets threshold"
endif()
```

#### Coverage com Exclusão de Código

```cmake
# Excluir código específico da coverage

# Usar pragmas no código C++
# // LCOV_EXCL_START
# void not_tested_function() {
#     // código não testado intencionalmente
# }
# // LCOV_EXCL_STOP

# Ou configurar no CMake para excluir por padrão
if(ENABLE_COVERAGE)
    set(COVERAGE_EXCLUDE_PATTERNS
        "*/tests/*"
        "*/mocks/*"
        "*/third_party/*"
        "*/vendor/*"
        "*generated*"
    )
    
    string(REPLACE ";" "\\|" COVERAGE_EXCLUDE_REGEX "${COVERAGE_EXCLUDE_PATTERNS}")
    
    add_custom_target(coverage
        COMMAND ${LCOV_PATH} --capture --directory . --output-file coverage.info
        COMMAND ${LCOV_PATH} --remove coverage.info ${COVERAGE_EXCLUDE_REGEX} --output-file coverage_filtered.info
        COMMAND ${GENHTML_PATH} coverage_filtered.info --output-directory coverage_report
        WORKING_DIRECTORY ${CMAKE_BINARY_DIR}
        COMMENT "Generating coverage with exclusions"
    )
endif()
```

---

## 8. Integração com Fuzzing

### Fuzzing: Explorando Limites do Código

O fuzzing é uma técnica de teste que gera entradas aleatórias para encontrar vulnerabilidades como crashes, memory leaks e comportamentos indefinidos.

#### Configuração com libFuzzer

```cmake
# CMakeLists.txt

option(ENABLE_FUZZING "Enable fuzzing with libFuzzer" OFF)

if(ENABLE_FUZZING)
    # Verificar se o compilador suporta fuzzing
    if(CMAKE_CXX_COMPILER_ID MATCHES "Clang")
        # Criar target de fuzzing
        add_executable(fuzz_string_parser
            fuzz/fuzz_string_parser.cpp
        )
        
        target_link_libraries(fuzz_string_parser
            PRIVATE
                myproject_lib
        )
        
        # Configurar flags de fuzzing
        target_compile_options(fuzz_string_parser PRIVATE
            -fsanitize=fuzzer,address,undefined
            -fno-omit-frame-pointer
        )
        
        target_link_options(fuzz_string_parser PRIVATE
            -fsanitize=fuzzer,address,undefined
        )
        
        # Adicionar ao CTest
        add_test(NAME fuzz_string_parser
            COMMAND fuzz_string_parser -max_total_time=60 -max_len=1024
            WORKING_DIRECTORY ${CMAKE_BINARY_DIR}/fuzz_output
        )
        
        set_tests_properties(fuzz_string_parser PROPERTIES
            TIMEOUT 120
            LABELS "fuzzing"
        )
        
        # Target para executar fuzzing
        add_custom_target(run-fuzz
            COMMAND fuzz_string_parser -max_total_time=300 -print_final_stats=1
            WORKING_DIRECTORY ${CMAKE_BINARY_DIR}/fuzz_output
            COMMENT "Running fuzzing for 5 minutes"
        )
    else()
        message(WARNING "Fuzzing only supported with Clang")
    endif()
endif()
```

#### Estrutura de Fuzz Test

```cpp
// fuzz/fuzz_string_parser.cpp

#include <cstdint>
#include <cstddef>
#include <cstring>
#include "string_parser.h"

// Entry point para libFuzzer
extern "C" int LLVMFuzzerTestOneInput(const uint8_t *data, size_t size) {
    // Ignorar entradas muito grandes
    if (size > 4096) {
        return 0;
    }
    
    // Criar string a partir dos dados
    std::string input(reinterpret_cast<const char*>(data), size);
    
    // Testar o parser
    try {
        auto result = parse_string(input);
        
        // Verificar invariantes
        if (result.is_valid()) {
            // Se a entrada é válida, o resultado deve ser consistente
            assert(result.value().length() <= input.length());
            assert(!result.value().empty());
        }
    } catch (const std::exception&) {
        // Exceptions são aceitas em fuzzing
    }
    
    return 0;
}

// Fuzz target para parsing de JSON
extern "C" int LLVMFuzzerTestJSON(const uint8_t *data, size_t size) {
    if (size > 8192) {
        return 0;
    }
    
    std::string input(reinterpret_cast<const char*>(data), size);
    
    try {
        auto json = parse_json(input);
        // Verificar que o JSON parseado é válido
        if (json.is_valid()) {
            // Round-trip: serializar e parsear novamente
            std::string serialized = json.serialize();
            auto reparsed = parse_json(serialized);
            assert(reparsed == json);
        }
    } catch (const std::exception&) {
    }
    
    return 0;
}

// Fuzz target para autenticação
extern "C" int LLVMFuzzerTestAuth(const uint8_t *data, size_t size) {
    if (size > 1024) {
        return 0;
    }
    
    // Dividir dados em username e password
    const char* sep = strchr(reinterpret_cast<const char*>(data), '|');
    if (!sep) {
        return 0;
    }
    
    std::string username(data, sep - data);
    std::string password(sep + 1, size - (sep - data) - 1);
    
    // Testar autenticação (não deve crashar)
    try {
        auto auth = authenticate(username, password);
        // Resultado pode ser true ou false, mas não deve crashar
    } catch (const std::exception&) {
    }
    
    return 0;
}
```

#### Configuração com AFL++

```cmake
# AFL++ Integration

option(ENABLE_AFL "Enable AFL++ fuzzing" OFF)

if(ENABLE_AFL)
    # Encontrar AFL++ compiler
    find_program(AFL_CC afl-clang-fast)
    find_program(AFL_CXX afl-clang-fast++)
    
    if(AFL_CC AND AFL_CXX)
        # Criar target de fuzzing com AFL
        add_executable(a fuzz/fuzz_afl.cpp)
        
        # Configurar compilador AFL
        set_target_properties(a PROPERTIES
            C_COMPILER ${AFL_CC}
            CXX_COMPILER ${AFL_CXX}
        )
        
        target_compile_options(a PRIVATE
            -fsanitize=address,undefined
            -fno-omit-frame-pointer
        )
        
        # Target para executar AFL
        add_custom_target(run-afl
            COMMAND afl-fuzz -i ${CMAKE_SOURCE_DIR}/fuzz/corpus -o ${CMAKE_BINARY_DIR}/fuzz_output --
            $<TARGET_FILE:a>
            WORKING_DIRECTORY ${CMAKE_BINARY_DIR}
            COMMENT "Running AFL++ fuzzing"
        )
    endif()
endif()
```

#### Corpus Management

```cmake
# Gerenciamento de corpus para fuzzing

# Criar diretório de corpus
file(MAKE_DIRECTORY ${CMAKE_SOURCE_DIR}/fuzz/corpus)

# Adicionar seed files
set(FUZZ_SEEDS
    "fuzz/seeds/valid_input.txt"
    "fuzz/seeds/empty.txt"
    "fuzz/seeds/large_input.txt"
    "fuzz/seeds/special_chars.txt"
)

# Target para gerar corpus
add_custom_target(generate-corpus
    COMMAND ${CMAKE_COMMAND} -E make_directory ${CMAKE_BINARY_DIR}/fuzz_corpus
    COMMAND ${CMAKE_COMMAND} -E copy ${FUZZ_SEEDS} ${CMAKE_BINARY_DIR}/fuzz_corpus/
    COMMENT "Generating fuzzing corpus"
)

# Target para minimizar corpus
add_custom_target(minimize-corpus
    COMMAND afl-cmin -i ${CMAKE_BINARY_DIR}/fuzz_output -o ${CMAKE_BINARY_DIR}/fuzz_corpus_min -- $<TARGET_FILE:a>
    WORKING_DIRECTORY ${CMAKE_BINARY_DIR}
    COMMENT "Minimizing fuzzing corpus"
)
```

#### Fuzzing com Cobertura

```cmake
# Integrar fuzzing com coverage

if(ENABLE_FUZZING AND ENABLE_COVERAGE)
    # Fuzzing com coverage instrumentation
    add_executable(fuzz_with_coverage
        fuzz/fuzz_coverage.cpp
    )
    
    target_compile_options(fuzz_with_coverage PRIVATE
        -fsanitize=fuzzer,address,undefined
        -fprofile-instr-generate
        -fcoverage-mapping
    )
    
    target_link_options(fuzz_with_coverage PRIVATE
        -fsanitize=fuzzer,address,undefined
        -fprofile-instr-generate
    )
    
    # Target para fuzzing com coverage
    add_custom_target(fuzz-coverage
        COMMAND fuzz_with_coverage -max_total_time=300
        COMMAND ${LLVM_PROFDATA_PATH} merge -sparse default.profraw -o fuzz.profdata
        COMMAND ${LLVM_COV_PATH} report $<TARGET_FILE:fuzz_with_coverage> -instr-profile=fuzz.profdata
        WORKING_DIRECTORY ${CMAKE_BINARY_DIR}
        COMMENT "Running fuzzing with coverage"
    )
endif()
```

#### Estrutura de Diretórios para Fuzzing

```
project/
├── CMakeLists.txt
├── fuzz/
│   ├── CMakeLists.txt
│   ├── fuzz_string_parser.cpp
│   ├── fuzz_json_parser.cpp
│   ├── fuzz_auth.cpp
│   ├── corpus/
│   │   ├── valid_input.txt
│   │   ├── edge_cases.txt
│   │   └── malicious_input.txt
│   └── seeds/
│       ├── seed1.txt
│       └── seed2.txt
└── src/
    └── ...
```

---

## 9. Benchmarking com Google Benchmark

### Medindo Performance com Google Benchmark

O Google Benchmark é uma biblioteca para micro-benchmarking que ajuda a medir e comparar performance de código.

#### Configuração CMake

```cmake
# CMakeLists.txt

option(ENABLE_BENCHMARKS "Enable Google Benchmark" ON)

if(ENABLE_BENCHMARKS)
    # Buscar Google Benchmark
    include(FetchContent)
    FetchContent_Declare(
        googlebenchmark
        GIT_REPOSITORY https://github.com/google/benchmark.git
        GIT_TAG v1.8.3
    )
    
    # Configurar para não builds testes do benchmark
    set(BENCHMARK_ENABLE_TESTING OFF CACHE BOOL "" FORCE)
    set(BENCHMARK_ENABLE_GTEST_TESTS OFF CACHE BOOL "" FORCE)
    
    FetchContent_MakeAvailable(googlebenchmark)
    
    # Criar executável de benchmarks
    add_executable(benchmarks
        benchmarks/bench_crypto.cpp
        benchmarks/bench_string.cpp
        benchmarks/bench_database.cpp
    )
    
    target_link_libraries(benchmarks
        PRIVATE
            benchmark::benchmark
            benchmark::benchmark_main
            myproject_lib
    )
    
    # Adicionar ao CTest
    add_test(NAME benchmarks COMMAND benchmarks --benchmark_format=json)
    
    set_tests_properties(benchmarks PROPERTIES
        TIMEOUT 300
        LABELS "benchmark;performance"
    )
    
    # Target para executar benchmarks
    add_custom_target(run-benchmarks
        COMMAND benchmarks --benchmark_format=console --benchmark_counters_tabular=true
        WORKING_DIRECTORY ${CMAKE_BINARY_DIR}
        COMMENT "Running performance benchmarks"
    )
    
    # Target para comparar benchmarks
    add_custom_target(compare-benchmarks
        COMMAND benchmarks --benchmark_format=json --benchmark_out=benchmark_results.json
        COMMAND ${Python3_EXECUTABLE} ${CMAKE_SOURCE_DIR}/scripts/compare_benchmarks.py
            --baseline baseline_results.json
            --current benchmark_results.json
        WORKING_DIRECTORY ${CMAKE_BINARY_DIR}
        COMMENT "Comparing benchmark results"
    )
endif()
```

#### Estrutura de Benchmarks

```cpp
// benchmarks/bench_crypto.cpp

#include <benchmark/benchmark.h>
#include "crypto_utils.h"

// Benchmark de criptografia AES
static void BM_AES256_Encrypt(benchmark::State& state) {
    std::string data(state.range(0), 'x');
    std::string key = generate_key(256);
    
    for (auto _ : state) {
        benchmark::DoNotOptimize(encrypt_aes256(data, key));
    }
    
    state.SetBytesProcessed(state.iterations() * state.range(0));
    state.SetComplexityN(state.range(0));
}

BENCHMARK(BM_AES256_Encrypt)
    ->RangeMultiplier(2)
    ->Range(1 << 10, 1 << 20)
    ->Complexity(benchmark::oN)
    ->Unit(benchmark::kMillisecond);

// Benchmark de hashing SHA256
static void BM_SHA256(benchmark::State& state) {
    std::string data(state.range(0), 'x');
    
    for (auto _ : state) {
        benchmark::DoNotOptimize(sha256(data));
    }
    
    state.SetBytesProcessed(state.iterations() * state.range(0));
}

BENCHMARK(BM_SHA256)
    ->RangeMultiplier(2)
    ->Range(1 << 10, 1 << 20)
    ->Unit(benchmark::kMicrosecond);

// Benchmark de RSA
static void BM_RSA2048_Sign(benchmark::State& state) {
    RSAKey key = generate_rsa_key(2048);
    std::string data(state.range(0), 'x');
    
    for (auto _ : state) {
        benchmark::DoNotOptimize(rsa_sign(data, key));
    }
    
    state.SetBytesProcessed(state.iterations() * state.range(0));
}

BENCHMARK(BM_RSA2048_Sign)
    ->RangeMultiplier(2)
    ->Range(32, 1024)
    ->Unit(benchmark::kMicrosecond);

// Benchmark de comparação de strings
static void BM_StringComparison(benchmark::State& state) {
    std::string a(state.range(0), 'a');
    std::string b(state.range(0), 'b');
    
    for (auto _ : state) {
        benchmark::DoNotOptimize(a == b);
    }
    
    state.SetComplexityN(state.range(0));
}

BENCHMARK(BM_StringComparison)
    ->RangeMultiplier(2)
    ->Range(1 << 8, 1 << 16)
    ->Complexity(benchmark::oN);

BENCHMARK_MAIN();
```

#### Benchmarks com Fixture

```cpp
// benchmarks/bench_database.cpp

#include <benchmark/benchmark.h>
#include "database.h"

class DatabaseBenchmark : public benchmark::Fixture {
public:
    void SetUp(const benchmark::State& state) override {
        db = std::make_unique<Database>("bench_db");
        db->connect();
        db->begin_transaction();
        
        // Pré-popular banco de dados
        for (int i = 0; i < state.range(0); ++i) {
            db->insert("INSERT INTO users (name, email) VALUES (?, ?)",
                       "user_" + std::to_string(i),
                       "user_" + std::to_string(i) + "@example.com");
        }
    }
    
    void TearDown(const benchmark::State& state) override {
        db->rollback_transaction();
        db->disconnect();
    }
    
    std::unique_ptr<Database> db;
};

BENCHMARK_DEFINE_F(DatabaseBenchmark, Insert)(benchmark::State& state) {
    for (auto _ : state) {
        db->insert("INSERT INTO logs (message, timestamp) VALUES (?, ?)",
                   "log_" + std::to_string(state.iterations()),
                   std::time(nullptr));
    }
    state.SetItemsProcessed(state.iterations());
}

BENCHMARK_REGISTER_F(DatabaseBenchmark, Insert)
    ->RangeMultiplier(10)
    ->Range(10, 1000)
    ->Unit(benchmark::kMicrosecond);

BENCHMARK_DEFINE_F(DatabaseBenchmark, Select)(benchmark::State& state) {
    for (auto _ : state) {
        auto results = db->select("SELECT * FROM users WHERE id = ?",
                                  state.range(0) % state.range(0) + 1);
        benchmark::DoNotOptimize(results);
    }
    state.SetItemsProcessed(state.iterations());
}

BENCHMARK_REGISTER_F(DatabaseBenchmark, Select)
    ->RangeMultiplier(10)
    ->Range(10, 1000)
    ->Unit(benchmark::kMicrosecond);

BENCHMARK_DEFINE_F(DatabaseBenchmark, BulkInsert)(benchmark::State& state) {
    for (auto _ : state) {
        state.PauseTiming();
        db->begin_transaction();
        state.ResumeTiming();
        
        for (int i = 0; i < state.range(0); ++i) {
            db->insert("INSERT INTO temp_data (value) VALUES (?)", i);
        }
        
        state.PauseTiming();
        db->rollback_transaction();
        state.ResumeTiming();
    }
    state.SetItemsProcessed(state.iterations() * state.range(0));
}

BENCHMARK_REGISTER_F(DatabaseBenchmark, BulkInsert)
    ->RangeMultiplier(10)
    ->Range(100, 10000)
    ->Unit(benchmark::kMillisecond);

BENCHMARK_MAIN();
```

#### Configuração de Output

```cmake
# Configurar formatos de saída dos benchmarks

# Output no console
add_custom_target(benchmark-console
    COMMAND benchmarks --benchmark_format=console
    WORKING_DIRECTORY ${CMAKE_BINARY_DIR}
)

# Output em JSON
add_custom_target(benchmark-json
    COMMAND benchmarks --benchmark_format=json --benchmark_out=benchmark_results.json
    WORKING_DIRECTORY ${CMAKE_BINARY_DIR}
)

# Output em CSV
add_custom_target(benchmark-csv
    COMMAND benchmarks --benchmark_format=csv --benchmark_out=benchmark_results.csv
    WORKING_DIRECTORY ${CMAKE_BINARY_DIR}
)

# Output com contadores tabulares
add_custom_target(benchmark-tabular
    COMMAND benchmarks --benchmark_format=console --benchmark_counters_tabular=true
    WORKING_DIRECTORY ${CMAKE_BINARY_DIR}
)
```

#### Comparação de Benchmarks

```python
#!/usr/bin/env python3
# scripts/compare_benchmarks.py

import json
import sys
import argparse
from typing import Dict, List

def load_results(filename: str) -> Dict:
    with open(filename, 'r') as f:
        return json.load(f)

def compare_results(baseline: Dict, current: Dict, threshold: float = 0.1) -> List:
    comparisons = []
    
    baseline_benchmarks = {b['name']: b for b in baseline.get('benchmarks', [])}
    current_benchmarks = {b['name']: b for b in current.get('benchmarks', [])}
    
    for name in current_benchmarks:
        if name in baseline_benchmarks:
            base_time = baseline_benchmarks[name]['real_time']
            curr_time = current_benchmarks[name]['real_time']
            
            change = (curr_time - base_time) / base_time
            
            comparisons.append({
                'name': name,
                'baseline': base_time,
                'current': curr_time,
                'change': change,
                'regression': change > threshold
            })
    
    return comparisons

def main():
    parser = argparse.ArgumentParser(description='Compare benchmark results')
    parser.add_argument('--baseline', required=True, help='Baseline results file')
    parser.add_argument('--current', required=True, help='Current results file')
    parser.add_argument('--threshold', type=float, default=0.1, help='Regression threshold')
    args = parser.parse_args()
    
    baseline = load_results(args.baseline)
    current = load_results(args.current)
    
    comparisons = compare_results(baseline, current, args.threshold)
    
    print("\nBenchmark Comparison Results:")
    print("-" * 80)
    print(f"{'Name':<50} {'Baseline':>12} {'Current':>12} {'Change':>10}")
    print("-" * 80)
    
    for comp in comparisons:
        change_pct = comp['change'] * 100
        marker = " REGRESSION" if comp['regression'] else ""
        print(f"{comp['name']:<50} {comp['baseline']:>12.2f} {comp['current']:>12.2f} {change_pct:>+9.2f}%{marker}")
    
    print("-" * 80)
    
    regressions = [c for c in comparisons if c['regression']]
    if regressions:
        print(f"\nWARNING: {len(regressions)} regression(s) detected!")
        sys.exit(1)
    else:
        print("\nNo regressions detected.")
        sys.exit(0)

if __name__ == '__main__':
    main()
```

---

## 10. Testes de Mutação com Mull

### Mull: Testes de Mutação para C++

O Mull é uma ferramenta de testes de mutação para C/C++ que ajuda a avaliar a qualidade dos testes introduzindo mutações no código e verificando se os testes detectam essas mutações.

#### Configuração CMake

```cmake
# CMakeLists.txt

option(ENABLE_MUTATION_TESTING "Enable mutation testing with Mull" OFF)

if(ENABLE_MUTATION_TESTING)
    # Verificar se Mull está disponível
    find_program(MULL Mull)
    
    if(NOT MULL)
        message(WARNING "Mull not found. Install from https://mull-project.org/")
    else()
        # Criar target para mutation testing
        add_custom_target(mutation-testing
            COMMAND ${MULL}
                --test-framework GoogleTest
                --test-program $<TARGET_FILE:unit_tests>
                --compdb ${CMAKE_BINARY_DIR}/compile_commands.json
                --mutators cxx_add_to_sub
                --mutators cxx_remove_void
                --mutators cxx_replace_scalar_return
                --timeout 1000
                --max-tests-per-run 100
            DEPENDS unit_tests
            WORKING_DIRECTORY ${CMAKE_BINARY_DIR}
            COMMENT "Running mutation testing with Mull"
        )
        
        # Target para mutation testing com relatório
        add_custom_target(mutation-testing-report
            COMMAND ${MULL}
                --test-framework GoogleTest
                --test-program $<TARGET_FILE:unit_tests>
                --compdb ${CMAKE_BINARY_DIR}/compile_commands.json
                --output-source-dir ${CMAKE_SOURCE_DIR}
                --report-name mutation_report
                --report-dir ${CMAKE_BINARY_DIR}/mutation_report
            DEPENDS unit_tests
            WORKING_DIRECTORY ${CMAKE_BINARY_DIR}
            COMMENT "Generating mutation testing report"
        )
        
        # Adicionar ao CTest
        add_test(NAME mutation-testing
            COMMAND ${MULL}
                --test-framework GoogleTest
                --test-program $<TARGET_FILE:unit_tests>
                --compdb ${CMAKE_BINARY_DIR}/compile_commands.json
            WORKING_DIRECTORY ${CMAKE_BINARY_DIR}
        )
        
        set_tests_properties(mutation-testing PROPERTIES
            TIMEOUT 600
            LABELS "mutation;quality"
        )
    endif()
endif()
```

#### Configuração de Mutantes

```yaml
# mull.yml (configuração do Mull)

mutators:
  # Mutadores aritméticos
  - cxx_add_to_sub
  - cxx_sub_to_add
  - cxx_mul_to_div
  - cxx_div_to_mul
  
  # Mutadores lógicos
  - cxx_eq_to_ne
  - cxx_ne_to_eq
  - cxx_gt_to_le
  - cxx_lt_to_ge
  
  # Mutadores de retorno
  - cxx_replace_scalar_return
  - cxx_remove_void_function
  
  # Mutadores de ponteiro
  - cxx_replace_nullptr_with_global
  - cxx_remove_reference

# Configurações de execução
timeout: 1000
max-tests-per-run: 100
max-error-mutations: 10

# Filtros
filters:
  exclude:
    - "*third_party*"
    - "*vendor*"
    - "*test*"
```

#### Análise de Resultados

```cmake
# Script para análise de mutation score

function(analyze_mutation_score REPORT_DIR)
    if(EXISTS "${REPORT_DIR}/mutation_report.json")
        add_custom_target(analyze-mutations
            COMMAND ${Python3_EXECUTABLE}
                ${CMAKE_SOURCE_DIR}/scripts/analyze_mutations.py
                --report ${REPORT_DIR}/mutation_report.json
                --min-score 0.8
            WORKING_DIRECTORY ${CMAKE_BINARY_DIR}
            COMMENT "Analyzing mutation testing results"
        )
    endif()
endfunction()

analyze_mutation_score(${CMAKE_BINARY_DIR}/mutation_report)
```

```python
#!/usr/bin/env python3
# scripts/analyze_mutations.py

import json
import sys
import argparse

def analyze_report(report_path: str, min_score: float) -> None:
    with open(report_path, 'r') as f:
        report = json.load(f)
    
    total_mutants = len(report.get('mutants', []))
    killed_mutants = sum(1 for m in report.get('mutants', []) if m['status'] == 'KILLED')
    survived_mutants = sum(1 for m in report.get('mutants', []) if m['status'] == 'SURVIVED')
    
    mutation_score = killed_mutants / total_mutants if total_mutants > 0 else 0
    
    print(f"\nMutation Testing Results:")
    print(f"  Total mutants: {total_mutants}")
    print(f"  Killed: {killed_mutants}")
    print(f"  Survived: {survived_mutants}")
    print(f"  Mutation score: {mutation_score:.2%}")
    
    if mutation_score < min_score:
        print(f"\nFAILED: Mutation score {mutation_score:.2%} is below threshold {min_score:.2%}")
        sys.exit(1)
    else:
        print(f"\nPASSED: Mutation score meets threshold")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--report', required=True)
    parser.add_argument('--min-score', type=float, default=0.8)
    args = parser.parse_args()
    
    analyze_report(args.report, args.min_score)

if __name__ == '__main__':
    main()
```

---

## 11. CI/CD: Resultados de Testes e Saída do CTest

### Integração com CI/CD

A integração de testes com pipelines de CI/CD é essencial para garantir que cada alteração seja automaticamente verificada.

#### GitHub Actions

```yaml
# .github/workflows/test.yml

name: Tests

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    
    strategy:
      matrix:
        build_type: [Debug, Release, RelWithDebInfo]
        compiler: [gcc, clang]
    
    steps:
    - uses: actions/checkout@v4
      with:
        fetch-depth: 0
    
    - name: Install dependencies
      run: |
        sudo apt-get update
        sudo apt-get install -y cmake g++ lcov gcovr
    
    - name: Configure CMake
      run: |
        cmake -B build \
          -DCMAKE_BUILD_TYPE=${{ matrix.build_type }} \
          -DCMAKE_CXX_COMPILER=${{ matrix.compiler }}++ \
          -DENABLE_COVERAGE=ON \
          -DENABLE_BENCHMARKS=ON
    
    - name: Build
      run: cmake --build build --config ${{ matrix.build_type }} -j$(nproc)
    
    - name: Run tests
      run: |
        cd build
        ctest --output-on-failure --output-junit test_results.xml
    
    - name: Generate coverage
      run: |
        cd build
        lcov --capture --directory . --output-file coverage.info
        lcov --remove coverage.info '/usr/*' '*/tests/*' --output-file coverage_filtered.info
        genhtml coverage_filtered.info --output-directory coverage_report
    
    - name: Upload test results
      uses: actions/upload-artifact@v4
      if: always()
      with:
        name: test-results-${{ matrix.build_type }}-${{ matrix.compiler }}
        path: |
          build/test_results.xml
          build/coverage_report/
    
    - name: Publish test results
      uses: dorny/test-reporter@v1
      if: always()
      with:
        name: Test Results (${{ matrix.build_type }}, ${{ matrix.compiler }})
        path: build/test_results.xml
        reporter: java-junit
```

#### GitLab CI

```yaml
# .gitlab-ci.yml

stages:
  - build
  - test
  - coverage
  - benchmarks

variables:
  CMAKE_BUILD_TYPE: Release
  ENABLE_COVERAGE: "ON"

build:
  stage: build
  script:
    - cmake -B build -DCMAKE_BUILD_TYPE=$CMAKE_BUILD_TYPE -DENABLE_COVERAGE=$ENABLE_COVERAGE
    - cmake --build build -j$(nproc)
  artifacts:
    paths:
      - build/
    expire_in: 1 hour

test:unit:
  stage: test
  script:
    - cd build
    - ctest --output-on-failure --output-junit unit_results.xml -L unit
  artifacts:
    reports:
      junit: build/unit_results.xml
    paths:
      - build/unit_results.xml

test:integration:
  stage: test
  script:
    - cd build
    - ctest --output-on-failure --output-junit integration_results.xml -L integration
  artifacts:
    reports:
      junit: build/integration_results.xml

test:security:
  stage: test
  script:
    - cd build
    - ctest --output-on-failure --output-junit security_results.xml -L security
  artifacts:
    reports:
      junit: build/security_results.xml

coverage:
  stage: coverage
  script:
    - cd build
    - lcov --capture --directory . --output-file coverage.info
    - lcov --remove coverage.info '/usr/*' '*/tests/*' --output-file coverage_filtered.info
    - lcov --list coverage_filtered.info
    - genhtml coverage_filtered.info --output-directory coverage_report
  artifacts:
    paths:
      - build/coverage_report/
    reports:
      coverage_report:
        coverage_format: cobertura
        path: build/coverage.xml

benchmarks:
  stage: benchmarks
  script:
    - cd build
    - ./benchmarks --benchmark_format=json --benchmark_out=benchmark_results.json
  artifacts:
    paths:
      - build/benchmark_results.json
```

#### Geração de Relatórios XML

```cmake
# Configurar saída de testes em XML para CI/CD

# Habilitar saída JUnit XML no CTest
set(CTEST_OUTPUT_XML ON)

# Configurar diretório de saída
set(CTEST_XML_OUTPUT_DIR ${CMAKE_BINARY_DIR}/test_results)

# Criar diretório
file(MAKE_DIRECTORY ${CTEST_XML_OUTPUT_DIR})

# Função para adicionar teste com XML output
function(add_test_with_xml TEST_NAME TEST_COMMAND)
    add_test(NAME ${TEST_NAME} COMMAND ${TEST_COMMAND})
    
    set_tests_properties(${TEST_NAME} PROPERTIES
        ATTACHED_FILES "${CTEST_XML_OUTPUT_DIR}/${TEST_NAME}.xml"
    )
endfunction()
```

#### Cobertura no CI/CD

```cmake
# Configurar coverage para CI/CD

if(ENABLE_COVERAGE)
    # Target para gerar relatório de coverage em XML (Cobertura)
    add_custom_target(coverage-xml
        COMMAND ${Python3_EXECUTABLE} ${CMAKE_SOURCE_DIR}/scripts/coverage_to_cobertura.py
            --input ${CMAKE_BINARY_DIR}/coverage_filtered.info
            --output ${CMAKE_BINARY_DIR}/coverage.xml
        WORKING_DIRECTORY ${CMAKE_BINARY_DIR}
        COMMENT "Generating Cobertura XML report"
    )
    
    # Target para upload de coverage
    add_custom_target(upload-coverage
        COMMAND ${Python3_EXECUTABLE} ${CMAKE_SOURCE_DIR}/scripts/upload_coverage.py
            --file ${CMAKE_BINARY_DIR}/coverage.xml
            --token ${CODECOV_TOKEN}
        WORKING_DIRECTORY ${CMAKE_BINARY_DIR}
        COMMENT "Uploading coverage to Codecov"
    )
endif()
```

#### Badges de Coverage

```cmake
# Gerar badges de coverage

add_custom_target(generate-badges
    COMMAND ${Python3_EXECUTABLE} ${CMAKE_SOURCE_DIR}/scripts/generate_badges.py
        --coverage-file ${CMAKE_BINARY_DIR}/coverage_filtered.info
        --output-dir ${CMAKE_BINARY_DIR}/badges
    WORKING_DIRECTORY ${CMAKE_BINARY_DIR}
    COMMENT "Generating coverage badges"
)

# Script para gerar badges
# scripts/generate_badges.py
# Gera badges SVG com o percentage de coverage
```

---

## 12. CMake Presets para Testes

### CMake Presets: Configurações Padronizadas

Os CMake Presets permitem definir configurações reutilizáveis para diferentes cenários de teste.

#### Estrutura de CMakePresets.json

```json
{
    "version": 6,
    "cmakeMinimumRequired": {
        "major": 3,
        "minor": 25,
        "patch": 0
    },
    "configurePresets": [
        {
            "name": "default",
            "hidden": true,
            "binaryDir": "${sourceDir}/build/${presetName}",
            "installDir": "${sourceDir}/install/${presetName}",
            "cacheVariables": {
                "CMAKE_BUILD_TYPE": "Release",
                "CMAKE_EXPORT_COMPILE_COMMANDS": "ON"
            }
        },
        {
            "name": "debug",
            "displayName": "Debug Build",
            "inherits": "default",
            "cacheVariables": {
                "CMAKE_BUILD_TYPE": "Debug",
                "ENABLE_COVERAGE": "ON",
                "ENABLE_ASAN": "ON"
            }
        },
        {
            "name": "release",
            "displayName": "Release Build",
            "inherits": "default",
            "cacheVariables": {
                "CMAKE_BUILD_TYPE": "Release",
                "ENABLE_COVERAGE": "OFF"
            }
        },
        {
            "name": "testing",
            "displayName": "Testing Configuration",
            "inherits": "default",
            "cacheVariables": {
                "CMAKE_BUILD_TYPE": "RelWithDebInfo",
                "ENABLE_TESTING": "ON",
                "ENABLE_COVERAGE": "ON",
                "ENABLE_BENCHMARKS": "ON"
            }
        },
        {
            "name": "security-testing",
            "displayName": "Security Testing",
            "inherits": "testing",
            "cacheVariables": {
                "ENABLE_FUZZING": "ON",
                "ENABLE_MUTATION_TESTING": "ON",
                "ENABLE_ASAN": "ON",
                "ENABLE_TSAN": "ON",
                "ENABLE_UBSAN": "ON"
            }
        },
        {
            "name": "ci",
            "displayName": "CI/CD Configuration",
            "inherits": "testing",
            "cacheVariables": {
                "CMAKE_BUILD_TYPE": "Release",
                "ENABLE_COVERAGE": "ON",
                "ENABLE_BENCHMARKS": "ON"
            },
            "environment": {
                "CI": "true"
            }
        }
    ],
    "buildPresets": [
        {
            "name": "debug",
            "configurePreset": "debug"
        },
        {
            "name": "release",
            "configurePreset": "release"
        },
        {
            "name": "testing",
            "configurePreset": "testing"
        },
        {
            "name": "security-testing",
            "configurePreset": "security-testing"
        }
    ],
    "testPresets": [
        {
            "name": "default",
            "hidden": true,
            "output": {
                "outputOnFailure": true,
                "verbosity": "extra"
            },
            "execution": {
                "noTestsAction": "error",
                "stopOnFailure": false
            }
        },
        {
            "name": "unit-tests",
            "displayName": "Unit Tests",
            "inherits": "default",
            "configurePreset": "testing",
            "filter": {
                "include": {
                    "label": "unit"
                }
            }
        },
        {
            "name": "integration-tests",
            "displayName": "Integration Tests",
            "inherits": "default",
            "configurePreset": "testing",
            "filter": {
                "include": {
                    "label": "integration"
                }
            },
            "execution": {
                "stopOnFailure": true
            }
        },
        {
            "name": "security-tests",
            "displayName": "Security Tests",
            "inherits": "default",
            "configurePreset": "security-testing",
            "filter": {
                "include": {
                    "label": "security"
                }
            },
            "execution": {
                "stopOnFailure": true
            }
        },
        {
            "name": "fuzzing",
            "displayName": "Fuzzing Tests",
            "inherits": "default",
            "configurePreset": "security-testing",
            "filter": {
                "include": {
                    "label": "fuzzing"
                }
            },
            "execution": {
                "timeout": 600
            }
        },
        {
            "name": "benchmarks",
            "displayName": "Performance Benchmarks",
            "inherits": "default",
            "configurePreset": "testing",
            "filter": {
                "include": {
                    "label": "benchmark"
                }
            }
        },
        {
            "name": "ci",
            "displayName": "CI/CD Tests",
            "inherits": "default",
            "configurePreset": "ci",
            "output": {
                "outputOnFailure": true,
                "verbosity": "extra",
                "outputFile": "test_results.xml"
            },
            "execution": {
                "noTestsAction": "error"
            }
        }
    ]
}
```

#### Uso dos Presets

```bash
# Configurar com preset
cmake --preset testing

# Build com preset
cmake --build --preset testing

# Executar testes com preset
ctest --preset unit-tests
ctest --preset security-tests
ctest --preset ci

# Listar presets disponíveis
cmake --list-presets
ctest --list-presets
```

#### Presets para Diferentes Plataformas

```json
{
    "version": 6,
    "configurePresets": [
        {
            "name": "linux-ci",
            "displayName": "Linux CI",
            "condition": {
                "type": "equals",
                "lhs": "${hostSystemName}",
                "rhs": "Linux"
            },
            "binaryDir": "${sourceDir}/build/linux-ci",
            "cacheVariables": {
                "CMAKE_BUILD_TYPE": "Release",
                "CMAKE_C_COMPILER": "gcc",
                "CMAKE_CXX_COMPILER": "g++"
            }
        },
        {
            "name": "macos-ci",
            "displayName": "macOS CI",
            "condition": {
                "type": "equals",
                "lhs": "${hostSystemName}",
                "rhs": "Darwin"
            },
            "binaryDir": "${sourceDir}/build/macos-ci",
            "cacheVariables": {
                "CMAKE_BUILD_TYPE": "Release",
                "CMAKE_C_COMPILER": "clang",
                "CMAKE_CXX_COMPILER": "clang++"
            }
        },
        {
            "name": "windows-ci",
            "displayName": "Windows CI",
            "condition": {
                "type": "equals",
                "lhs": "${hostSystemName}",
                "rhs": "Windows"
            },
            "binaryDir": "${sourceDir}/build/windows-ci",
            "generator": "Visual Studio 17 2022",
            "cacheVariables": {
                "CMAKE_BUILD_TYPE": "Release"
            }
        }
    ]
}
```

---

## 13. Exemplo: Projeto com Suite Completa

### Estrutura do Projeto

```
SecureProject/
├── CMakeLists.txt
├── CMakePresets.json
├── src/
│   ├── CMakeLists.txt
│   ├── auth/
│   │   ├── CMakeLists.txt
│   │   ├── auth.h
│   │   └── auth.cpp
│   ├── crypto/
│   │   ├── CMakeLists.txt
│   │   ├── crypto.h
│   │   └── crypto.cpp
│   └── database/
│       ├── CMakeLists.txt
│       ├── database.h
│       └── database.cpp
├── tests/
│   ├── CMakeLists.txt
│   ├── unit/
│   │   ├── test_auth.cpp
│   │   ├── test_crypto.cpp
│   │   └── test_database.cpp
│   ├── integration/
│   │   ├── test_auth_flow.cpp
│   │   └── test_database_ops.cpp
│   └── security/
│       ├── test_input_validation.cpp
│       └── test_buffer_overflow.cpp
├── benchmarks/
│   ├── CMakeLists.txt
│   ├── bench_crypto.cpp
│   └── bench_database.cpp
├── fuzz/
│   ├── CMakeLists.txt
│   ├── fuzz_auth.cpp
│   ├── fuzz_crypto.cpp
│   └── corpus/
├── scripts/
│   ├── run_tests.sh
│   ├── generate_coverage.sh
│   └── ci_pipeline.sh
└── .github/
    └── workflows/
        └── test.yml
```

#### CMakeLists.txt Principal

```cmake
cmake_minimum_required(VERSION 3.20)

project(SecureProject
    VERSION 1.0.0
    DESCRIPTION "Secure Project with Comprehensive Testing"
    LANGUAGES CXX
)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

# Opções do projeto
option(ENABLE_TESTING "Enable testing" ON)
option(ENABLE_COVERAGE "Enable code coverage" OFF)
option(ENABLE_BENCHMARKS "Enable benchmarks" ON)
option(ENABLE_FUZZING "Enable fuzzing" OFF)
option(ENABLE_MUTATION_TESTING "Enable mutation testing" OFF)
option(ENABLE_ASAN "Enable AddressSanitizer" OFF)
option(ENABLE_TSAN "Enable ThreadSanitizer" OFF)
option(ENABLE_UBSAN "Enable UndefinedBehaviorSanitizer" OFF)

# Habilitar testes
if(ENABLE_TESTING)
    enable_testing()
    include(CTest)
endif()

# Sanitizers
if(ENABLE_ASAN)
    add_compile_options(-fsanitize=address -fno-omit-frame-pointer)
    add_link_options(-fsanitize=address)
endif()

if(ENABLE_TSAN)
    add_compile_options(-fsanitize=thread -fno-omit-frame-pointer)
    add_link_options(-fsanitize=thread)
endif()

if(ENABLE_UBSAN)
    add_compile_options(-fsanitize=undefined)
    add_link_options(-fsanitize=undefined)
endif()

# Adicionar diretórios
add_subdirectory(src)

if(ENABLE_TESTING)
    add_subdirectory(tests)
    add_subdirectory(benchmarks)
    
    if(ENABLE_FUZZING)
        add_subdirectory(fuzz)
    endif()
endif()

# Coverage
if(ENABLE_COVERAGE)
    include(FetchContent)
    FetchContent_Declare(
        gcovr
        GIT_REPOSITORY https://github.com/gcovr/gcovr.git
        GIT_TAG 6.0
    )
    
    find_program(GCOVR_PATH gcovr)
    
    if(GCOVR_PATH)
        add_custom_target(coverage
            COMMAND ${GCOVR_PATH}
                --root ${CMAKE_SOURCE_DIR}
                --filter ${CMAKE_SOURCE_DIR}/src/
                --exclude ${CMAKE_SOURCE_DIR}/tests/
                --print-summary
                --xml-pretty
                --xml coverage.xml
                --html-details coverage.html
                ${CMAKE_BINARY_DIR}
            WORKING_DIRECTORY ${CMAKE_BINARY_DIR}
            COMMENT "Generating coverage report"
        )
    endif()
endif()
```

#### tests/CMakeLists.txt

```cmake
# tests/CMakeLists.txt

# Buscar GoogleTest
include(FetchContent)
FetchContent_Declare(
    googletest
    GIT_REPOSITORY https://github.com/google/googletest.git
    GIT_TAG v1.14.0
)
set(gtest_force_shared_crt ON CACHE BOOL "" FORCE)
FetchContent_MakeAvailable(googletest)

# Buscar Catch2
FetchContent_Declare(
    Catch2
    GIT_REPOSITORY https://github.com/catchorg/Catch2.git
    GIT_TAG v3.5.2
)
FetchContent_MakeAvailable(Catch2)

# Biblioteca de testes unitários
add_library(test_common STATIC
    common/test_utils.cpp
    common/mock_database.cpp
    common/mock_crypto.cpp
)

target_include_directories(test_common
    PUBLIC ${CMAKE_CURRENT_SOURCE_DIR}/common
)

target_link_libraries(test_common
    PUBLIC
        GTest::gmock
        Catch2::Catch2WithMain
        myproject_lib
)

# Testes Unitários com GoogleTest
add_executable(unit_tests_gtest
    unit/test_auth.cpp
    unit/test_crypto.cpp
    unit/test_database.cpp
)

target_link_libraries(unit_tests_gtest
    PRIVATE
        GTest::gtest
        GTest::gtest_main
        test_common
        myproject_lib
)

include(GoogleTest)
gtest_discover_tests(unit_tests_gtest
    TEST_PREFIX gtest.unit.
    PROPERTIES
        LABELS "unit;gtest"
        TIMEOUT 30
)

# Testes Unitários com Catch2
add_executable(unit_tests_catch2
    unit/test_auth_catch.cpp
    unit/test_crypto_catch.cpp
)

target_link_libraries(unit_tests_catch2
    PRIVATE
        Catch2::Catch2WithMain
        test_common
        myproject_lib
)

include(Catch)
catch_discover_tests(unit_tests_catch2
    TEST_PREFIX catch2.unit.
    PROPERTIES
        LABELS "unit;catch2"
        TIMEOUT 30
)

# Testes de Integração
add_executable(integration_tests
    integration/test_auth_flow.cpp
    integration/test_database_ops.cpp
)

target_link_libraries(integration_tests
    PRIVATE
        GTest::gtest
        GTest::gtest_main
        GTest::gmock
        test_common
        myproject_lib
)

gtest_discover_tests(integration_tests
    TEST_PREFIX integration.
    PROPERTIES
        LABELS "integration"
        TIMEOUT 120
)

# Testes de Segurança
add_executable(security_tests
    security/test_input_validation.cpp
    security/test_buffer_overflow.cpp
    security/test_sql_injection.cpp
)

target_link_libraries(security_tests
    PRIVATE
        GTest::gtest
        GTest::gtest_main
        Catch2::Catch2WithMain
        test_common
        myproject_lib
)

gtest_discover_tests(security_tests
    TEST_PREFIX security.
    PROPERTIES
        LABELS "security;critical"
        TIMEOUT 60
)

# Fixture para testes de segurança
add_test(NAME security_setup COMMAND security_test_setup)
set_tests_properties(security_setup PROPERTIES
    FIXTURES_SETUP security_fixture
    LABELS "security;fixture"
)

# Configurar fixtures para testes de segurança
get_property(TEST_LIST DIRECTORY PROPERTY TESTS)
foreach(TEST_NAME ${TEST_LIST})
    if(TEST_NAME MATCHES "^security\\.")
        set_tests_properties(${TEST_NAME} PROPERTIES
            FIXTURES_REQUIRED security_fixture
        )
    endif()
endforeach()
```

#### benchmarks/CMakeLists.txt

```cmake
# benchmarks/CMakeLists.txt

option(ENABLE_BENCHMARKS "Enable benchmarks" ON)

if(ENABLE_BENCHMARKS)
    # Buscar Google Benchmark
    include(FetchContent)
    FetchContent_Declare(
        googlebenchmark
        GIT_REPOSITORY https://github.com/google/benchmark.git
        GIT_TAG v1.8.3
    )
    set(BENCHMARK_ENABLE_TESTING OFF CACHE BOOL "" FORCE)
    FetchContent_MakeAvailable(googlebenchmark)
    
    # Criar executável de benchmarks
    add_executable(benchmarks
        bench_crypto.cpp
        bench_database.cpp
        bench_string.cpp
    )
    
    target_link_libraries(benchmarks
        PRIVATE
            benchmark::benchmark
            benchmark::benchmark_main
            myproject_lib
    )
    
    # Adicionar ao CTest
    add_test(NAME benchmarks COMMAND benchmarks --benchmark_format=json)
    
    set_tests_properties(benchmarks PROPERTIES
        TIMEOUT 300
        LABELS "benchmark;performance"
    )
    
    # Targets úteis
    add_custom_target(run-benchmarks
        COMMAND benchmarks --benchmark_format=console --benchmark_counters_tabular=true
        WORKING_DIRECTORY ${CMAKE_BINARY_DIR}
        COMMENT "Running performance benchmarks"
    )
    
    add_custom_target(benchmark-compare
        COMMAND benchmarks --benchmark_format=json --benchmark_out=benchmark_results.json
        COMMAND ${Python3_EXECUTABLE} ${CMAKE_SOURCE_DIR}/scripts/compare_benchmarks.py
            --baseline baseline_results.json
            --current benchmark_results.json
        WORKING_DIRECTORY ${CMAKE_BINARY_DIR}
        COMMENT "Comparing benchmark results"
    )
endif()
```

#### fuzz/CMakeLists.txt

```cmake
# fuzz/CMakeLists.txt

option(ENABLE_FUZZING "Enable fuzzing" OFF)

if(ENABLE_FUZZING AND CMAKE_CXX_COMPILER_ID MATCHES "Clang")
    # Fuzz targets
    set(FUZZ_TARGETS
        fuzz_auth
        fuzz_crypto
        fuzz_string
    )
    
    foreach(FUZZ_TARGET ${FUZZ_TARGETS})
        add_executable(${FUZZ_TARGET}
            ${FUZZ_TARGET}.cpp
        )
        
        target_link_libraries(${FUZZ_TARGET}
            PRIVATE
                myproject_lib
        )
        
        target_compile_options(${FUZZ_TARGET} PRIVATE
            -fsanitize=fuzzer,address,undefined
            -fno-omit-frame-pointer
        )
        
        target_link_options(${FUZZ_TARGET} PRIVATE
            -fsanitize=fuzzer,address,undefined
        )
        
        # Adicionar ao CTest
        add_test(NAME ${FUZZ_TARGET}
            COMMAND ${FUZZ_TARGET} -max_total_time=60 -max_len=1024
            WORKING_DIRECTORY ${CMAKE_BINARY_DIR}/fuzz_output
        )
        
        set_tests_properties(${FUZZ_TARGET} PROPERTIES
            TIMEOUT 120
            LABELS "fuzzing"
        )
    endforeach()
    
    # Target para executar todos os fuzzers
    add_custom_target(run-fuzzing
        COMMAND ${CMAKE_COMMAND} -E make_directory ${CMAKE_BINARY_DIR}/fuzz_output
        COMMENT "Running all fuzzers"
    )
    
    foreach(FUZZ_TARGET ${FUZZ_TARGETS})
        add_custom_target(run-fuzz-${FUZZ_TARGET}
            COMMAND ${FUZZ_TARGET} -max_total_time=300 -print_final_stats=1
            WORKING_DIRECTORY ${CMAKE_BINARY_DIR}/fuzz_output
            COMMENT "Running ${FUZZ_TARGET}"
        )
        add_dependencies(run-fuzzing run-fuzz-${FUZZ_TARGET})
    endforeach()
endif()
```

#### Script de CI

```bash
#!/bin/bash
# scripts/ci_pipeline.sh

set -e

echo "=== CI Pipeline ==="
echo "Build Type: ${BUILD_TYPE:-Release}"
echo "Compiler: ${CXX:-g++}"

# Configurar
echo "=== Configuring ==="
cmake -B build \
    -DCMAKE_BUILD_TYPE=${BUILD_TYPE:-Release} \
    -DCMAKE_CXX_COMPILER=${CXX:-g++} \
    -DENABLE_TESTING=ON \
    -DENABLE_COVERAGE=${ENABLE_COVERAGE:-OFF} \
    -DENABLE_BENCHMARKS=ON

# Build
echo "=== Building ==="
cmake --build build -j$(nproc)

# Executar testes
echo "=== Running Tests ==="
cd build
ctest --output-on-failure --output-junit test_results.xml -j$(nproc)

# Coverage (se habilitado)
if [ "${ENABLE_COVERAGE}" = "ON" ]; then
    echo "=== Generating Coverage ==="
    make coverage
fi

# Benchmarks
echo "=== Running Benchmarks ==="
./benchmarks --benchmark_format=json --benchmark_out=benchmark_results.json

echo "=== CI Pipeline Complete ==="
```

---

## 14. Exercícios

### Exercício 1: Configuração Básica de CTest

**Objetivo**: Configurar CTest em um projeto existente.

**Instruções**:
1. Crie um novo projeto CMake com a seguinte estrutura:
   ```
   my_project/
   ├── CMakeLists.txt
   ├── src/
   │   ├── CMakeLists.txt
   │   └── calculator.cpp
   └── tests/
       ├── CMakeLists.txt
       └── test_calculator.cpp
   ```
2. Implemente uma calculadora simples com operações de soma, subtração, multiplicação e divisão
3. Configure CTest no CMakeLists.txt raiz
4. Crie testes unitários para todas as operações
5. Execute os testes com `ctest --output-on-failure`

**Código inicial**:

```cpp
// src/calculator.h
#pragma once

class Calculator {
public:
    double add(double a, double b);
    double subtract(double a, double b);
    double multiply(double a, double b);
    double divide(double a, double b);
};
```

**Esperado**:
- Todos os testes devem passar
- O CTest deve listar todos os testes disponíveis
- Deve ser possível executar testes específicos por nome

---

### Exercício 2: Integração com GoogleTest

**Objetivo**: Integrar GoogleTest em um projeto existente.

**Instruções**:
1. Adicione GoogleTest ao projeto do Exercício 1 usando `FetchContent`
2. Converta os testes para usar GoogleTest (TEST, EXPECT_EQ, etc.)
3. Adicione testes de boundary testing (valores limite)
4. Adicione um teste que verifique exceção em divisão por zero
5. Configure `gtest_discover_tests()` para descoberta automática

**Requisitos**:
- Usar `FetchContent` para download do GoogleTest
- Criar pelo menos 10 testes unitários
- Incluir testes de edge cases
- Verificar que a descoberta automática funciona

---

### Exercício 3: Testes com Fixtures

**Objetivo**: Criar testes que requerem setup e teardown complexo.

**Instruções**:
1. Crie um sistema de banco de dados simulado
2. Implemente fixtures que criam e limpam dados de teste
3. Configure `FIXTURES_SETUP`, `FIXTURES_REQUIRED` e `FIXTURES_CLEANUP`
4. Execute os testes e verifique a ordem de execução
5. Adicione `DEPENDS` para garantir dependências entre testes

**Cenário**:
```cpp
// Sistema de banco de dados simulado
class MockDatabase {
public:
    void connect();
    void disconnect();
    bool insert(const std::string& table, const std::string& data);
    bool remove(const std::string& table, int id);
    std::vector<std::string> query(const std::string& table);
};
```

**Esperado**:
- Fixture deve criar banco de dados antes dos testes
- Testes devem executar na ordem correta
- Cleanup deve ocorrer após todos os testes
- Falha em um teste não deve corromper outros testes

---

### Exercício 4: Cobertura de Código

**Objetivo**: Configurar e medir cobertura de código.

**Instruções**:
1. Configure o projeto para gerar dados de coverage com gcov
2. Instale lcov e configure targets para gerar relatórios HTML
3. Execute os testes com coverage habilitado
4. Analise o relatório de coverage
5. Identifique código não testado e adicione testes para aumentar a coverage

**Requisitos**:
- Criar target `coverage` no CMake
- Gerar relatório HTML com lcov
- Configurar exclusões para código de teste
- Atingir pelo menos 80% de line coverage

**Script auxiliar**:

```bash
#!/bin/bash
# run_coverage.sh

# Limpar dados anteriores
lcov --directory . --zerocounters

# Executar testes
ctest --output-on-failure

# Capturar dados
lcov --directory . --capture --output-file coverage.info

# Filtrar (remover código do sistema e testes)
lcov --remove coverage.info '/usr/*' '*/tests/*' --output-file coverage_filtered.info

# Gerar relatório HTML
genhtml coverage_filtered.info --output-directory coverage_report

# Mostrar resumo
lcov --list coverage_filtered.info
```

---

### Exercício 5: Fuzzing com libFuzzer

**Objetivo**: Implementar fuzzing para encontrar vulnerabilidades.

**Instruções**:
1. Configure o projeto para usar Clang com suporte a fuzzing
2. Implemente um parser de strings que processe entrada do usuário
3. Crie um fuzz target que teste o parser
4. Execute o fuzzing por pelo menos 60 segundos
5. Analise os crashes encontrados e corrija-os

**Parser para testar**:

```cpp
// src/parser.h
#pragma once
#include <string>
#include <vector>

struct ParsedResult {
    bool valid;
    std::string command;
    std::vector<std::string> arguments;
};

ParsedResult parse_input(const std::string& input);
```

**Requisitos**:
- Criar fuzz target com `LLVMFuzzerTestOneInput`
- Configurar flags `-fsanitize=fuzzer,address,undefined`
- Criar corpus inicial com casos de teste
- Documentar vulnerabilidades encontradas

---

### Exercício 6: CMake Presets para Testes

**Objetivo**: Criar presets para diferentes cenários de teste.

**Instruções**:
1. Crie um `CMakePresets.json` com os seguintes presets:
   - `debug-testing`: Debug build com coverage e sanitizers
   - `release-testing`: Release build com testes
   - `security-testing`: Configuração completa de segurança
   - `ci`: Configuração para CI/CD
2. Crie presets de teste correspondentes
3. Teste cada preset e documente as diferenças
4. Crie um script que execute todos os presets

**Estrutura esperada**:

```json
{
    "version": 6,
    "configurePresets": [...],
    "buildPresets": [...],
    "testPresets": [...]
}
```

---

### Exercício 7: CI/CD Pipeline Completo

**Objetivo**: Criar pipeline de CI/CD completo.

**Instruções**:
1. Crie um workflow GitHub Actions que execute:
   - Build em Debug e Release
   - Testes unitários e de integração
   - Cobertura de código
   - Benchmarks
2. Configure artifacts para relatórios
3. Adicione badges de status
4. Configure notificações para falhas

**Workflow mínimo**:

```yaml
name: CI
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Build and Test
        run: |
          cmake -B build -DCMAKE_BUILD_TYPE=Release
          cmake --build build
          cd build && ctest --output-on-failure
```

---

### Exercício 8: Benchmarks de Performance

**Objetivo**: Criar e analisar benchmarks.

**Instruções**:
1. Implemente diferentes algoritmos de ordenação (bubble sort, quick sort, merge sort)
2. Crie benchmarks comparando os algoritmos
3. Execute os benchmarks com diferentes tamanhos de entrada
4. Gere relatório comparativo
5. Identifique o algoritmo mais eficiente para cada caso

**Requisitos**:
- Usar Google Benchmark
- Testar com 100, 1000, 10000 e 100000 elementos
- Gerar output em formato JSON
- Criar script de comparação

---

## 15. Referências

### Documentação Oficial

1. **CMake Documentation**
   - CTest: https://cmake.org/cmake/help/latest/manual/ctest.1.html
   - GoogleTest: https://cmake.org/cmake/help/latest/module/GoogleTest.html
   - CTest Properties: https://cmake.org/cmake/help/latest/manual/cmake-properties.7.html#test-properties

2. **GoogleTest**
   - Documentation: https://google.github.io/googletest/
   - GitHub: https://github.com/google/googletest
   - Cookbook: https://google.github.io/googletest/primer.html

3. **Catch2**
   - Documentation: https://github.com/catchorg/Catch2/blob/devel/docs/README.md
   - GitHub: https://github.com/catchorg/Catch2

4. **Google Benchmark**
   - Documentation: https://github.com/google/benchmark
   - GitHub: https://github.com/google/benchmark

### Ferramentas de Coverage

5. **gcov**
   - Documentation: https://gcc.gnu.org/onlinedocs/gcc/Gcov.html

6. **lcov**
   - Documentation: https:// lcov.sourceforge.net/
   - GitHub: https://github.com/linux-test-project/lcov

7. **gcovr**
   - Documentation: https://gcovr.com/
   - GitHub: https://github.com/gcovr/gcovr

8. **llvm-cov**
   - Documentation: https://llvm.org/docs/CommandGuide/llvm-cov.html

### Ferramentas de Fuzzing

9. **libFuzzer**
   - Documentation: https://llvm.org/docs/LibFuzzer.html

10. **AFL++**
    - Documentation: https://aflplus.plus/
    - GitHub: https://github.com/AFLplusplus/AFLplusplus

### Mutation Testing

11. **Mull**
    - Documentation: https://mull-project.org/
    - GitHub: https://github.com/mull-project/mull

12. **Pit**
    - Documentation: https://pitest.org/
    - Para projetos Java, mas conceitos aplicáveis

### CI/CD

13. **GitHub Actions**
    - Documentation: https://docs.github.com/en/actions

14. **GitLab CI**
    - Documentation: https://docs.gitlab.com/ee/ci/

### Livros e Artigos

15. **"Modern CMake"** - Henrik Bengtsson
    - Práticas modernas de CMake incluindo testes

16. **"Google Test Primer"** - Google
    - Guia completo do GoogleTest

17. **"Continuous Delivery"** - Jez Humble, David Farley
    - Princípios de CI/CD que incluem testes automatizados

18. **"The Fuzzing Book"** - Universidade de Saarland
    - Teoria e prática de fuzzing: https://www.fuzzingbook.org/

### Comunidades e Recursos

19. **CMake Discourse**
    - https://discourse.cmake.org/

20. **Stack Overflow - CMake Tag**
    - https://stackoverflow.com/questions/tagged/cmake

---

## Resumo

Neste capítulo, exploramos o ecossistema completo de testing no CMake:

- **CTest**: O executor nativo do CMake para gerenciar e executar testes
- **GoogleTest e Catch2**: Frameworks populares de testes com integração direta no CMake
- **Propriedades de Teste**: Controle fino sobre timeout, labels, fixtures e comportamento
- **Descoberta Automática**: Eliminação de manutenção manual em projetos grandes
- **Cobertura de Código**: gcov, lcov e llvm-cov para medir a qualidade dos testes
- **Fuzzing**: libFuzzer e AFL++ para encontrar vulnerabilidades automaticamente
- **Benchmarking**: Google Benchmark para medição de performance
- **Mutation Testing**: Mull para avaliar a eficácia dos testes
- **CI/CD**: Integração com GitHub Actions e GitLab CI
- **CMake Presets**: Configurações reutilizáveis para diferentes cenários

O testing abrangente é fundamental para projetos de segurança. Uma suite de testes bem configurada não apenas detecta bugs, mas também serve como documentação viva do comportamento esperado do sistema, facilitando a manutenção e evolução do código.

No próximo capítulo, exploraremos como integrar todas essas técnicas em um pipeline de CI/CD completo, automatizando desde a build até a implantação.
---

*[Capítulo anterior: 13 — Cross Compilation](13-cross-compilation.md)*
*[Próximo capítulo: 15 — Install Packaging](15-install-packaging.md)*
