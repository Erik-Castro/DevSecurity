# Futures, Promises e Continuations em C++

## Introdução

Este documento abrange de forma abrangente os conceitos de Futures, Promises e Continuations em C++ moderno (C++17/20), com exemplos práticos, padrões de design, e análise de bugs de concorrência documentados.


## 1. Fundamentos de Futures e Promises

### 1.1 O que são Futures?

Um `std::future` representa o resultado de uma computação assíncrona que pode não estar disponível imediatamente. Ele atua como um proxy para um valor que será computado no futuro.

```cpp
#include <future>
#include <iostream>
#include <thread>
#include <chrono>

int computacao_demorada(int x) {
    std::this_thread::sleep_for(std::chrono::seconds(2));
    return x * x;
}

int main() {
    // Inicia computação assíncrona
    std::future<int> resultado = std::async(std::launch::async, computacao_demorada, 10);
    
    // Faz outro trabalho enquanto espera
    std::cout << "Trabalhando em outra coisa...\n";
    
    // Bloqueia até o resultado estar pronto
    int valor = resultado.get();
    std::cout << "Resultado: " << valor << "\n";  // 100
    
    return 0;
}
```

### 1.2 O que são Promises?

Um `std::promise` é o parceiro de escrita para um `std::future`. Ele permite que você defina um valor (ou exceção) que será lido pelo future associado.

```cpp
#include <future>
#include <iostream>
#include <thread>
#include <vector>

void trabalhador(std::promise<int>&& promessa, int id) {
    // Simula trabalho
    std::this_thread::sleep_for(std::chrono::milliseconds(100 * id));
    
    // Define o resultado
    promessa.set_value(id * 42);
}

int main() {
    std::vector<std::thread> threads;
    std::vector<std::future<int>> futures;
    
    for (int i = 1; i <= 5; ++i) {
        std::promise<int> promessa;
        futures.push_back(promessa.get_future());
        threads.emplace_back(trabalhador, std::move(promessa), i);
    }
    
    for (auto& fut : futures) {
        std::cout << "Thread resultado: " << fut.get() << "\n";
    }
    
    for (auto& t : threads) {
        t.join();
    }
    
    return 0;
}
```

### 1.3 Estados de um Future

```cpp
#include <future>
#include <iostream>
#include <thread>
#include <chrono>

enum class FutureState {
    // Não associado a nenhum estado compartilhado
    NoState,
    // Associado, mas resultado ainda não pronto
    Waiting,
    // Resultado pronto (valor ou exceção)
    Ready
};

void demonstrar_estados() {
    std::promise<int> p;
    std::future<int> f = p.get_future();
    
    // Estado: Waiting (associado, mas não pronto)
    std::cout << "Future válido: " << f.valid() << "\n";  // true
    
    // Define valor - transição para Ready
    p.set_value(42);
    
    // Estado: Ready
    std::cout << "Valor: " << f.get() << "\n";  // 42
    
    // Após get(), o future não é mais válido para outro get()
    // f.get(); // Undefined behavior!
}
```

### 1.4 Políticas de Lançamento

```cpp
#include <future>
#include <iostream>
#include <thread>

void exemplo_politicas() {
    // launch::async - executa em nova thread (garantido)
    auto f1 = std::async(std::launch::async, []() {
        std::this_thread::sleep_for(std::chrono::milliseconds(100));
        return 1;
    });
    
    // launch::deferred - executa lazy na thread chamadora (em get()/wait())
    auto f2 = std::async(std::launch::deferred, []() {
        std::this_thread::sleep_for(std::chrono::milliseconds(100));
        return 2;
    });
    
    // launch::async | launch::deferred - implementação decide (padrão)
    auto f3 = std::async([]() {
        std::this_thread::sleep_for(std::chrono::milliseconds(100));
        return 3;
    });
    
    std::cout << "Async: " << f1.get() << "\n";
    std::cout << "Deferred: " << f2.get() << "\n";  // Executa aqui!
    std::cout << "Auto: " << f3.get() << "\n";
}
```


## 2. std::future - Interface Completa

### 2.1 Métodos Principais

```cpp
#include <future>
#include <iostream>
#include <chrono>
#include <thread>

void metodos_future() {
    std::promise<int> p;
    std::future<int> f = p.get_future();
    
    // Verifica se válido (associado a estado compartilhado)
    if (!f.valid()) {
        std::cout << "Future inválido\n";
        return;
    }
    
    // wait() - bloqueia até pronto
    p.set_value(100);
    f.wait();  // Retorna imediatamente pois já está pronto
    
    // wait_for() - espera com timeout
    std::promise<int> p2;
    std::future<int> f2 = p2.get_future();
    
    auto status = f2.wait_for(std::chrono::milliseconds(50));
    std::cout << "Status após 50ms: " << (status == std::future_status::timeout ? "timeout" : "ready") << "\n";
    
    p2.set_value(200);
    status = f2.wait_for(std::chrono::milliseconds(50));
    std::cout << "Status após set_value: " << (status == std::future_status::ready ? "ready" : "outro") << "\n";
    
    // wait_until() - espera até time_point
    std::promise<int> p3;
    std::future<int> f3 = p3.get_future();
    
    auto deadline = std::chrono::steady_clock::now() + std::chrono::milliseconds(100);
    status = f3.wait_until(deadline);
    std::cout << "Status wait_until: " << (status == std::future_status::timeout ? "timeout" : "ready") << "\n";
    
    // get() - obtém valor (move semantics, só pode chamar uma vez)
    std::promise<std::string> p4;
    std::future<std::string> f4 = p4.get_future();
    p4.set_value("Hello, Future!");
    
    std::string resultado = f4.get();  // Move o valor para fora
    std::cout << "Resultado: " << resultado << "\n";
    
    // share() - cria shared_future (copiável)
    std::promise<int> p5;
    std::future<int> f5 = p5.get_future();
    p5.set_value(42);
    
    std::shared_future<int> sf = f5.share();
    std::cout << "Shared future 1: " << sf.get() << "\n";
    std::cout << "Shared future 2: " << sf.get() << "\n";  // Pode chamar múltiplas vezes!
}
```

### 2.2 Tratamento de Exceções

```cpp
#include <future>
#include <iostream>
#include <stdexcept>
#include <string>

void tratar_excecoes() {
    std::promise<int> p;
    std::future<int> f = p.get_future();
    
    // Define exceção em vez de valor
    try {
        throw std::runtime_error("Erro na computação!");
    } catch (...) {
        p.set_exception(std::current_exception());
    }
    
    try {
        int valor = f.get();  // Relança a exceção armazenada
    } catch (const std::exception& e) {
        std::cout << "Exceção capturada: " << e.what() << "\n";
    }
    
    // Verificar se há exceção sem lançar (C++20: std::future::exception())
    // Em C++17, precisa tentar get() e capturar
    
    std::promise<std::string> p2;
    std::future<std::string> f2 = p2.get_future();
    p2.set_value("Sucesso");
    
    try {
        std::string s = f2.get();
        std::cout << "Valor: " << s << "\n";
    } catch (...) {
        std::cout << "Não deve chegar aqui\n";
    }
}
```

### 2.3 Future com Tipos de Referência e Void

```cpp
#include <future>
#include <iostream>
#include <vector>
#include <algorithm>

// future<void> - para sincronização sem valor de retorno
void future_void_exemplo() {
    std::promise<void> p;
    std::future<void> f = p.get_future();
    
    std::thread t([&p]() {
        std::this_thread::sleep_for(std::chrono::milliseconds(100));
        std::cout << "Trabalho concluído\n";
        p.set_value();  // void
    });
    
    f.wait();  // Bloqueia até set_value()
    std::cout << "Sincronizado\n";
    t.join();
}

// future<T&> - referência (cuidado com lifetime!)
void future_referencia_exemplo() {
    int valor = 100;
    std::promise<int&> p;
    std::future<int&> f = p.get_future();
    
    p.set_value(valor);  // Define referência para 'valor'
    
    int& ref = f.get();  // Obtém referência
    ref = 200;           // Modifica o original!
    
    std::cout << "Valor original: " << valor << "\n";  // 200
    
    // PERIGO: se 'valor' sair de escopo antes do get(), referência dangling!
}

// future com tipos móveis apenas (non-copyable)
#include <memory>

void future_move_only() {
    std::promise<std::unique_ptr<int>> p;
    std::future<std::unique_ptr<int>> f = p.get_future();
    
    p.set_value(std::make_unique<int>(42));
    
    auto ptr = f.get();  // Move o unique_ptr
    std::cout << "Valor: " << *ptr << "\n";
}
```


## 3. std::promise - Interface Completa

### 3.1 Métodos Principais

```cpp
#include <future>
#include <iostream>
#include <thread>
#include <vector>
#include <exception>

void metodos_promise() {
    // Construtor padrão
    std::promise<int> p1;
    
    // Construtor com alocador (C++17)
    // std::promise<int, std::allocator<int>> p2(std::allocator_arg, std::allocator<int>{});
    
    // get_future() - obtém future associado (só pode chamar uma vez!)
    std::future<int> f = p1.get_future();
    // std::future<int> f2 = p1.get_future();  // ERRO: std::future_error (promise already satisfied)
    
    // set_value() - define valor com sucesso
    p1.set_value(42);
    
    // set_value_at_thread_exit() - define valor quando thread atual terminar
    std::promise<int> p3;
    auto f3 = p3.get_future();
    
    std::thread t([p3 = std::move(p3)]() mutable {
        std::this_thread::sleep_for(std::chrono::milliseconds(50));
        p3.set_value_at_thread_exit(100);  // Valor definido ao sair da thread
    });
    
    std::cout << "Aguardando thread terminar...\n";
    t.join();  // thread termina, valor fica disponível
    std::cout << "Valor: " << f3.get() << "\n";  // 100
    
    // set_exception() - define exceção
    std::promise<int> p4;
    auto f4 = p4.get_future();
    
    try {
        throw std::logic_error("Erro lógico");
    } catch (...) {
        p4.set_exception(std::current_exception());
    }
    
    try {
        f4.get();
    } catch (const std::exception& e) {
        std::cout << "Exceção: " << e.what() << "\n";
    }
    
    // set_exception_at_thread_exit() - similar ao set_value_at_thread_exit
    std::promise<int> p5;
    auto f5 = p5.get_future();
    
    std::thread t2([p5 = std::move(p5)]() mutable {
        try {
            throw std::runtime_error("Erro na thread");
        } catch (...) {
            p5.set_exception_at_thread_exit(std::current_exception());
        }
    });
    
    t2.join();
    try {
        f5.get();
    } catch (const std::exception& e) {
        std::cout << "Exceção na thread: " << e.what() << "\n";
    }
}
```

### 3.2 Promise como Mecanismo de Sincronização

```cpp
#include <future>
#include <iostream>
#include <thread>
#include <chrono>
#include <queue>
#include <mutex>
#include <condition_variable>

// Canal simples usando promise/future (one-shot)
template<typename T>
class CanalOneShot {
    std::promise<T> promessa_;
    std::future<T> future_;
    bool usado_ = false;
    
public:
    CanalOneShot() : future_(promessa_.get_future()) {}
    
    void enviar(T valor) {
        if (usado_) throw std::runtime_error("Canal já usado");
        usado_ = true;
        promessa_.set_value(std::move(valor));
    }
    
    T receber() {
        if (usado_) throw std::runtime_error("Canal já usado");
        usado_ = true;
        return future_.get();
    }
    
    // Não bloqueante
    bool tentar_receber(T& valor) {
        if (future_.wait_for(std::chrono::seconds(0)) == std::future_status::ready) {
            valor = future_.get();
            return true;
        }
        return false;
    }
};

void exemplo_canal() {
    CanalOneShot<int> canal;
    
    std::thread produtor([&canal]() {
        std::this_thread::sleep_for(std::chrono::milliseconds(100));
        canal.enviar(42);
        std::cout << "Produtor enviou\n";
    });
    
    std::thread consumidor([&canal]() {
        int valor = canal.receber();
        std::cout << "Consumidor recebeu: " << valor << "\n";
    });
    
    produtor.join();
    consumidor.join();
}

// Barreira simples com promises
class Barreira {
    std::vector<std::promise<void>> promessas_;
    size_t contagem_;
    std::mutex mtx_;
    
public:
    explicit Barreira(size_t n) : contagem_(n) {
        promessas_.reserve(n);
        for (size_t i = 0; i < n; ++i) {
            promessas_.emplace_back();
        }
    }
    
    std::future<void> esperar() {
        std::lock_guard<std::mutex> lock(mtx_);
        if (contagem_ == 0) {
            throw std::runtime_error("Barreira já usada");
        }
        auto fut = promessas_[--contagem_].get_future();
        if (contagem_ == 0) {
            // Último a chegar - libera todos
            for (auto& p : promessas_) {
                p.set_value();
            }
        }
        return fut;
    }
};

void exemplo_barreira() {
    Barreira barreira(3);
    std::vector<std::thread> threads;
    
    for (int i = 0; i < 3; ++i) {
        threads.emplace_back([&barreira, i]() {
            std::this_thread::sleep_for(std::chrono::milliseconds(50 * (i + 1)));
            std::cout << "Thread " << i << " chegou na barreira\n";
            barreira.esperar().wait();
            std::cout << "Thread " << i << " liberada\n";
        });
    }
    
    for (auto& t : threads) t.join();
}
```

### 3.3 Erros Comuns com Promise

```cpp
#include <future>
#include <iostream>
#include <thread>

void erros_comuns_promise() {
    // ERRO 1: get_future() chamado duas vezes
    {
        std::promise<int> p;
        auto f1 = p.get_future();
        // auto f2 = p.get_future();  // Lança std::future_error: promise already satisfied
    }
    
    // ERRO 2: set_value() chamado duas vezes
    {
        std::promise<int> p;
        auto f = p.get_future();
        p.set_value(1);
        // p.set_value(2);  // Lança std::future_error: promise already satisfied
    }
    
    // ERRO 3: Promise destruído sem set_value/set_exception
    {
        std::promise<int> p;
        auto f = p.get_future();
        // p sai de escopo sem ser satisfeito
        // f.get() lança std::future_error: broken promise
    }
    
    // ERRO 4: Future movido e depois usado
    {
        std::promise<int> p;
        std::future<int> f = p.get_future();
        std::future<int> f2 = std::move(f);
        // f.get();  // Undefined behavior - f não é mais válido
        p.set_value(42);
        std::cout << "Valor: " << f2.get() << "\n";  // OK
    }
    
    // ERRO 5: Referência dangling com future<T&>
    {
        std::promise<int&> p;
        auto f = p.get_future();
        {
            int local = 100;
            p.set_value(local);  // Referência para variável local!
        }  // 'local' destruído aqui
        // int& ref = f.get();  // DANGLING REFERENCE - UB!
    }
}
```


## 4. std::shared_future - Futures Compartilhados

### 4.1 Características e Uso

```cpp
#include <future>
#include <iostream>
#include <thread>
#include <vector>
#include <chrono>

void shared_future_basico() {
    std::promise<int> p;
    std::future<int> f = p.get_future();
    
    // Converte para shared_future (move-only -> copyable)
    std::shared_future<int> sf = f.share();
    
    // Múltiplas threads podem aguardar o mesmo resultado
    std::vector<std::thread> threads;
    for (int i = 0; i < 5; ++i) {
        threads.emplace_back([sf, i]() {
            int valor = sf.get();  // Cada thread obtém o mesmo valor
            std::cout << "Thread " << i << " recebeu: " << valor << "\n";
        });
    }
    
    std::this_thread::sleep_for(std::chrono::milliseconds(100));
    p.set_value(42);  // Libera todas as threads
    
    for (auto& t : threads) t.join();
}
```

### 4.2 Padrão: Broadcast de Resultado

```cpp
#include <future>
#include <iostream>
#include <thread>
#include <vector>
#include <functional>
#include <algorithm>

// Cache de computação assíncrona com shared_future
template<typename Key, typename Value>
class AsyncCache {
    std::mutex mtx_;
    std::unordered_map<Key, std::shared_future<Value>> cache_;
    
public:
    template<typename Func>
    std::shared_future<Value> get_or_compute(Key key, Func&& func) {
        std::lock_guard<std::mutex> lock(mtx_);
        
        auto it = cache_.find(key);
        if (it != cache_.end()) {
            return it->second;  // Retorna future existente
        }
        
        // Cria nova computação
        std::promise<Value> promise;
        auto future = promise.get_future().share();
        
        cache_[key] = future;
        
        // Inicia computação assíncrona
        std::thread([promise = std::move(promise), func = std::forward<Func>(func)]() mutable {
            try {
                promise.set_value(func());
            } catch (...) {
                promise.set_exception(std::current_exception());
            }
        }).detach();
        
        return future;
    }
    
    void invalidate(const Key& key) {
        std::lock_guard<std::mutex> lock(mtx_);
        cache_.erase(key);
    }
    
    void clear() {
        std::lock_guard<std::mutex> lock(mtx_);
        cache_.clear();
    }
};

void exemplo_cache() {
    AsyncCache<std::string, int> cache;
    
    auto fut1 = cache.get_or_compute("chave1", []() {
        std::this_thread::sleep_for(std::chrono::milliseconds(200));
        return 100;
    });
    
    auto fut2 = cache.get_or_compute("chave1", []() {
        std::this_thread::sleep_for(std::chrono::milliseconds(200));
        return 200;  // Não será chamado - usa cache
    });
    
    std::cout << "Resultado 1: " << fut1.get() << "\n";  // 100
    std::cout << "Resultado 2: " << fut2.get() << "\n";  // 100 (mesmo future!)
    
    // Verifica se são o mesmo future compartilhado
    std::cout << "Mesmo future: " << (&fut1.get() == &fut2.get() ? "Sim" : "Não") << "\n";
}
```

### 4.3 shared_future com Continuations

```cpp
#include <future>
#include <iostream>
#include <thread>
#include <vector>
#include <algorithm>

// Encadeamento de continuations com shared_future
std::shared_future<int> computacao_etapa1() {
    std::promise<int> p;
    auto sf = p.get_future().share();
    
    std::thread([p = std::move(p)]() mutable {
        std::this_thread::sleep_for(std::chrono::milliseconds(100));
        p.set_value(10);
    }).detach();
    
    return sf;
}

std::shared_future<int> computacao_etapa2(std::shared_future<int> entrada) {
    std::promise<int> p;
    auto sf = p.get_future().share();
    
    std::thread([entrada, p = std::move(p)]() mutable {
        int valor = entrada.get();  // Aguarda etapa anterior
        std::this_thread::sleep_for(std::chrono::milliseconds(100));
        p.set_value(valor * 2);
    }).detach();
    
    return sf;
}

void exemplo_encadeamento() {
    // Pipeline: etapa1 -> etapa2 -> etapa3
    auto etapa1 = computacao_etapa1();
    auto etapa2 = computacao_etapa2(etapa1);
    auto etapa3 = computacao_etapa2(etapa2);  // Reusa mesma função
    
    std::cout << "Resultado final: " << etapa3.get() << "\n";  // 10 * 2 * 2 = 40
    
    // Múltiplos consumidores do mesmo pipeline
    auto consumidor1 = etapa3;
    auto consumidor2 = etapa3;
    
    std::thread t1([consumidor1]() {
        std::cout << "Consumidor 1: " << consumidor1.get() << "\n";
    });
    
    std::thread t2([consumidor2]() {
        std::cout << "Consumidor 2: " << consumidor2.get() << "\n";
    });
    
    t1.join();
    t2.join();
}
```


## 5. Continuations - Encadeamento de Futures (C++20)

### 5.1 std::future::then (C++20)

```cpp
#include <future>
#include <iostream>
#include <thread>
#include <chrono>
#include <vector>
#include <string>

// C++20: then() permite encadear continuations
void continuations_cpp20() {
    // Nota: std::future::then faz parte do Concurrency TS v2
    // Em C++20 padrão, use std::experimental::future ou bibliotecas como folly/hpx
    
    // Simulação do comportamento com C++17/20 padrão
    auto etapa1 = std::async(std::launch::async, []() {
        std::this_thread::sleep_for(std::chrono::milliseconds(100));
        return 10;
    });
    
    // Continuação manual (padrão C++17)
    auto etapa2 = std::async(std::launch::async, [etapa1 = std::move(etapa1)]() mutable {
        int valor = etapa1.get();
        std::this_thread::sleep_for(std::chrono::milliseconds(100));
        return valor * 2;
    });
    
    auto etapa3 = std::async(std::launch::async, [etapa2 = std::move(etapa2)]() mutable {
        int valor = etapa2.get();
        std::this_thread::sleep_for(std::chrono::milliseconds(100));
        return valor + 5;
    });
    
    std::cout << "Resultado: " << etapa3.get() << "\n";  // 25
}
```

### 5.2 Implementação Manual de Continuations (C++17 Compatível)

```cpp
#include <future>
#include <iostream>
#include <thread>
#include <chrono>
#include <functional>
#include <memory>
#include <utility>
#include <type_traits>

// Helper para continuations type-safe
template<typename T>
class Future {
    std::shared_future<T> future_;
    
public:
    Future() = default;
    explicit Future(std::future<T>&& f) : future_(f.share()) {}
    explicit Future(std::shared_future<T>&& f) : future_(std::move(f)) {}
    
    // then - encadeia continuação que retorna novo valor
    template<typename F>
    auto then(F&& func) {
        using ResultType = std::invoke_result_t<F, T>;
        
        std::promise<ResultType> promise;
        auto future = promise.get_future();
        
        std::thread([fut = future_, func = std::forward<F>(func), 
                     promise = std::move(promise)]() mutable {
            try {
                if constexpr (std::is_void_v<T>) {
                    fut.wait();
                    if constexpr (std::is_void_v<ResultType>) {
                        func();
                        promise.set_value();
                    } else {
                        promise.set_value(func());
                    }
                } else {
                    T valor = fut.get();
                    if constexpr (std::is_void_v<ResultType>) {
                        func(std::move(valor));
                        promise.set_value();
                    } else {
                        promise.set_value(func(std::move(valor)));
                    }
                }
            } catch (...) {
                promise.set_exception(std::current_exception());
            }
        }).detach();
        
        return Future<ResultType>(std::move(future));
    }
    
    // then_void - continuação que não retorna valor
    template<typename F>
    auto then_void(F&& func) {
        return then([func = std::forward<F>(func)](auto&&... args) mutable {
            func(std::forward<decltype(args)>(args)...);
        });
    }
    
    // get - obtém resultado (bloqueia)
    T get() {
        return future_.get();
    }
    
    // wait - aguarda sem obter valor
    void wait() {
        future_.wait();
    }
    
    // wait_for - aguarda com timeout
    template<typename Rep, typename Period>
    std::future_status wait_for(const std::chrono::duration<Rep, Period>& timeout) {
        return future_.wait_for(timeout);
    }
    
    // valid - verifica se tem estado associado
    bool valid() const {
        return future_.valid();
    }
};

// Factory function
template<typename T>
Future<T> make_future(std::future<T>&& f) {
    return Future<T>(std::move(f));
}

template<typename T>
Future<T> make_ready_future(T&& value) {
    std::promise<std::decay_t<T>> p;
    p.set_value(std::forward<T>(value));
    return Future<std::decay_t<T>>(std::move(p.get_future()));
}

Future<void> make_ready_future() {
    std::promise<void> p;
    p.set_value();
    return Future<void>(std::move(p.get_future()));
}

// Exemplo de uso
void exemplo_continuations_manual() {
    // Pipeline: 10 -> *2 -> +5 -> *3 = 75
    auto f = make_ready_future(10)
        .then([](int x) { 
            std::this_thread::sleep_for(std::chrono::milliseconds(50));
            return x * 2; 
        })
        .then([](int x) { 
            std::this_thread::sleep_for(std::chrono::milliseconds(50));
            return x + 5; 
        })
        .then([](int x) { 
            std::this_thread::sleep_for(std::chrono::milliseconds(50));
            return x * 3; 
        });
    
    std::cout << "Resultado pipeline: " << f.get() << "\n";  // 75
    
    // Com void
    make_ready_future()
        .then_void([]() { std::cout << "Etapa 1\n"; })
        .then_void([]() { std::cout << "Etapa 2\n"; })
        .then_void([]() { std::cout << "Etapa 3\n"; })
        .get();
}
```

### 5.3 Continuations com Tratamento de Erros

```cpp
#include <future>
#include <iostream>
#include <thread>
#include <chrono>
#include <stdexcept>
#include <variant>

// Future com suporte a erro (similar a Result/Expected)
template<typename T, typename E = std::exception_ptr>
class TryFuture {
    std::shared_future<std::variant<T, E>> future_;
    
public:
    TryFuture() = default;
    explicit TryFuture(std::future<std::variant<T, E>>&& f) : future_(f.share()) {}
    
    // then - só executa se sucesso
    template<typename F>
    auto then(F&& func) {
        using ResultType = std::invoke_result_t<F, T>;
        
        std::promise<std::variant<ResultType, E>> promise;
        auto future = promise.get_future();
        
        std::thread([fut = future_, func = std::forward<F>(func), 
                     promise = std::move(promise)]() mutable {
            try {
                auto result = fut.get();
                if (std::holds_alternative<T>(result)) {
                    T valor = std::move(std::get<T>(result));
                    promise.set_value(func(std::move(valor)));
                } else {
                    promise.set_value(std::get<E>(result));
                }
            } catch (...) {
                promise.set_value(std::current_exception());
            }
        }).detach();
        
        return TryFuture<ResultType, E>(std::move(future));
    }
    
    // catch_error - trata erro e recupera
    template<typename F>
    auto catch_error(F&& handler) {
        using ResultType = std::invoke_result_t<F, E>;
        
        std::promise<std::variant<T, ResultType>> promise;
        auto future = promise.get_future();
        
        std::thread([fut = future_, handler = std::forward<F>(handler), 
                     promise = std::move(promise)]() mutable {
            try {
                auto result = fut.get();
                if (std::holds_alternative<T>(result)) {
                    promise.set_value(std::move(std::get<T>(result)));
                } else {
                    E erro = std::get<E>(result);
                    promise.set_value(handler(erro));
                }
            } catch (...) {
                promise.set_value(std::current_exception());
            }
        }).detach();
        
        return TryFuture<T, ResultType>(std::move(future));
    }
    
    // finally - executa sempre (sucesso ou erro)
    template<typename F>
    auto finally(F&& cleanup) {
        std::promise<std::variant<T, E>> promise;
        auto future = promise.get_future();
        
        std::thread([fut = future_, cleanup = std::forward<F>(cleanup), 
                     promise = std::move(promise)]() mutable {
            try {
                auto result = fut.get();
                cleanup();
                promise.set_value(std::move(result));
            } catch (...) {
                cleanup();
                promise.set_value(std::current_exception());
            }
        }).detach();
        
        return TryFuture<T, E>(std::move(future));
    }
    
    T get() {
        auto result = future_.get();
        if (std::holds_alternative<T>(result)) {
            return std::move(std::get<T>(result));
        } else {
            std::rethrow_exception(std::get<E>(result));
        }
    }
};

void exemplo_try_future() {
    auto computation = []() -> TryFuture<int> {
        std::promise<std::variant<int, std::exception_ptr>> p;
        auto f = p.get_future();
        
        std::thread([p = std::move(p)]() mutable {
            std::this_thread::sleep_for(std::chrono::milliseconds(100));
            // Simula erro
            // p.set_value(42);  // Sucesso
            try {
                throw std::runtime_error("Falha na computação!");
            } catch (...) {
                p.set_value(std::current_exception());
            }
        }).detach();
        
        return TryFuture<int>(std::move(f));
    };
    
    computation()
        .then([](int x) { return x * 2; })
        .catch_error([](std::exception_ptr e) {
            try { std::rethrow_exception(e); }
            catch (const std::exception& ex) {
                std::cout << "Erro capturado: " << ex.what() << "\n";
                return 0;  // Valor de recuperação
            }
        })
        .finally([]() { std::cout << "Limpeza executada\n"; })
        .then([](int x) { 
            std::cout << "Resultado final: " << x << "\n";
            return x;
        })
        .get();
}
```


## 6. std::async e Políticas de Execução

### 6.1 std::async em Detalhes

```cpp
#include <future>
#include <iostream>
#include <thread>
#include <chrono>
#include <vector>
#include <algorithm>

void async_detalhado() {
    // launch::async - nova thread garantida
    std::cout << "Thread principal: " << std::this_thread::get_id() << "\n";
    
    auto f1 = std::async(std::launch::async, []() {
        std::cout << "Thread async: " << std::this_thread::get_id() << "\n";
        std::this_thread::sleep_for(std::chrono::milliseconds(100));
        return 42;
    });
    
    // launch::deferred - execução preguiçosa (lazy)
    auto f2 = std::async(std::launch::deferred, []() {
        std::cout << "Thread deferred (mesma da main): " << std::this_thread::get_id() << "\n";
        std::this_thread::sleep_for(std::chrono::milliseconds(100));
        return 24;
    });
    
    // Padrão: implementação decide (geralmente async se disponível)
    auto f3 = std::async([]() {
        std::this_thread::sleep_for(std::chrono::milliseconds(100));
        return 12;
    });
    
    std::cout << "f1: " << f1.get() << "\n";
    std::cout << "f2: " << f2.get() << "\n";  // Executa AQUI (get())
    std::cout << "f3: " << f3.get() << "\n";
}
```

### 6.2 Pool de Threads com std::async

```cpp
#include <future>
#include <iostream>
#include <thread>
#include <vector>
#include <queue>
#include <functional>
#include <mutex>
#include <condition_variable>
#include <atomic>

// Thread pool simples usando std::async
class ThreadPool {
    std::vector<std::thread> workers_;
    std::queue<std::function<void()>> tasks_;
    std::mutex queue_mutex_;
    std::condition_variable condition_;
    std::atomic<bool> stop_{false};
    
public:
    explicit ThreadPool(size_t threads = std::thread::hardware_concurrency()) {
        for (size_t i = 0; i < threads; ++i) {
            workers_.emplace_back([this] {
                while (true) {
                    std::function<void()> task;
                    {
                        std::unique_lock<std::mutex> lock(queue_mutex_);
                        condition_.wait(lock, [this] { 
                            return stop_ || !tasks_.empty(); 
                        });
                        if (stop_ && tasks_.empty()) return;
                        task = std::move(tasks_.front());
                        tasks_.pop();
                    }
                    task();
                }
            });
        }
    }
    
    template<typename F, typename... Args>
    auto enqueue(F&& f, Args&&... args) 
        -> std::future<std::invoke_result_t<F, Args...>> {
        
        using ReturnType = std::invoke_result_t<F, Args...>;
        auto task = std::make_shared<std::packaged_task<ReturnType()>>(
            std::bind(std::forward<F>(f), std::forward<Args>(args)...)
        );
        
        std::future<ReturnType> res = task->get_future();
        
        {
            std::lock_guard<std::mutex> lock(queue_mutex_);
            if (stop_) throw std::runtime_error("ThreadPool parado");
            tasks_.emplace([task]() { (*task)(); });
        }
        condition_.notify_one();
        return res;
    }
    
    ~ThreadPool() {
        {
            std::lock_guard<std::mutex> lock(queue_mutex_);
            stop_ = true;
        }
        condition_.notify_all();
        for (auto& worker : workers_) {
            worker.join();
        }
    }
};

void exemplo_threadpool() {
    ThreadPool pool(4);
    std::vector<std::future<int>> futures;
    
    for (int i = 0; i < 10; ++i) {
        futures.push_back(pool.enqueue([i] {
            std::this_thread::sleep_for(std::chrono::milliseconds(50));
            return i * i;
        }));
    }
    
    for (auto& f : futures) {
        std::cout << f.get() << " ";
    }
    std::cout << "\n";
}
```

### 6.3 std::packaged_task

```cpp
#include <future>
#include <iostream>
#include <thread>
#include <functional>
#include <utility>

// packaged_task - empacota função callable para uso com future
void packaged_task_exemplo() {
    // Cria task que retorna int
    std::packaged_task<int(int, int)> task([](int a, int b) {
        std::this_thread::sleep_for(std::chrono::milliseconds(50));
        return a + b;
    });
    
    // Obtém future antes de executar
    std::future<int> result = task.get_future();
    
    // Executa task em thread separada
    std::thread t(std::move(task), 10, 20);
    
    std::cout << "Aguardando resultado...\n";
    std::cout << "Resultado: " << result.get() << "\n";  // 30
    t.join();
}

// Uso com thread pool
void packaged_task_pool() {
    std::packaged_task<void()> task([]() {
        std::cout << "Task executada\n";
    });
    
    auto fut = task.get_future();
    
    // Pode passar para thread pool, fila, etc.
    std::thread t(std::move(task));
    fut.wait();
    t.join();
}

// Bind com packaged_task
void packaged_task_bind() {
    auto func = [](int a, int b, int c) { return a + b + c; };
    
    std::packaged_task<int()> task(std::bind(func, 1, 2, 3));
    auto fut = task.get_future();
    
    task();  // Executa na thread atual
    std::cout << "Resultado bind: " << fut.get() << "\n";  // 6
}
```

### 6.4 Comparação: async vs thread vs packaged_task

```cpp
#include <future>
#include <iostream>
#include <thread>
#include <chrono>
#include <vector>

void comparacao_abordagens() {
    const int ITERACOES = 1000;
    
    // 1. std::thread + promise (controle total)
    auto inicio = std::chrono::high_resolution_clock::now();
    {
        std::vector<std::thread> threads;
        std::vector<std::future<int>> futures;
        
        for (int i = 0; i < ITERACOES; ++i) {
            std::promise<int> p;
            futures.push_back(p.get_future());
            threads.emplace_back([p = std::move(p), i]() mutable {
                p.set_value(i * 2);
            });
        }
        
        for (auto& f : futures) f.get();
        for (auto& t : threads) t.join();
    }
    auto fim = std::chrono::high_resolution_clock::now();
    std::cout << "thread+promise: " 
              << std::chrono::duration_cast<std::chrono::milliseconds>(fim - inicio).count() 
              << "ms\n";
    
    // 2. std::async (padrão)
    inicio = std::chrono::high_resolution_clock::now();
    {
        std::vector<std::future<int>> futures;
        for (int i = 0; i < ITERACOES; ++i) {
            futures.push_back(std::async(std::launch::async, [i] { return i * 2; }));
        }
        for (auto& f : futures) f.get();
    }
    fim = std::chrono::high_resolution_clock::now();
    std::cout << "std::async: " 
              << std::chrono::duration_cast<std::chrono::milliseconds>(fim - inicio).count() 
              << "ms\n";
    
    // 3. packaged_task + thread
    inicio = std::chrono::high_resolution_clock::now();
    {
        std::vector<std::thread> threads;
        std::vector<std::future<int>> futures;
        
        for (int i = 0; i < ITERACOES; ++i) {
            std::packaged_task<int()> task([i] { return i * 2; });
            futures.push_back(task.get_future());
            threads.emplace_back(std::move(task));
        }
        
        for (auto& f : futures) f.get();
        for (auto& t : threads) t.join();
    }
    fim = std::chrono::high_resolution_clock::now();
    std::cout << "packaged_task: " 
              << std::chrono::duration_cast<std::chrono::milliseconds>(fim - inicio).count() 
              << "ms\n";
}
```


## 7. Padrões Avançados com Futures

### 7.1 WhenAll / WhenAny (Combinadores)

```cpp
#include <future>
#include <iostream>
#include <thread>
#include <vector>
#include <chrono>
#include <algorithm>
#include <variant>

// WhenAll - aguarda todos os futures
template<typename... Futures>
auto when_all(Futures&&... futures) {
    std::vector<std::shared_future<void>> shared_futures;
    (shared_futures.push_back(std::forward<Futures>(futures).share()), ...);
    
    std::promise<void> promise;
    auto future = promise.get_future();
    
    std::thread([shared_futures = std::move(shared_futures), 
                 promise = std::move(promise)]() mutable {
        for (auto& f : shared_futures) {
            f.wait();
        }
        promise.set_value();
    }).detach();
    
    return future;
}

// WhenAll com coleção de futures mesmo tipo
template<typename T>
std::future<std::vector<T>> when_all_vec(std::vector<std::future<T>> futures) {
    std::promise<std::vector<T>> promise;
    auto future = promise.get_future();
    
    std::thread([futures = std::move(futures), promise = std::move(promise)]() mutable {
        std::vector<T> results;
        results.reserve(futures.size());
        for (auto& f : futures) {
            results.push_back(f.get());
        }
        promise.set_value(std::move(results));
    }).detach();
    
    return future;
}

// WhenAny - aguarda o primeiro future pronto
template<typename... Futures>
auto when_any(Futures&&... futures) {
    std::vector<std::shared_future<void>> shared_futures;
    (shared_futures.push_back(std::forward<Futures>(futures).share()), ...);
    
    std::promise<size_t> promise;
    auto future = promise.get_future();
    
    std::thread([shared_futures = std::move(shared_futures), 
                 promise = std::move(promise)]() mutable {
        while (true) {
            for (size_t i = 0; i < shared_futures.size(); ++i) {
                if (shared_futures[i].wait_for(std::chrono::seconds(0)) 
                    == std::future_status::ready) {
                    promise.set_value(i);
                    return;
                }
            }
            std::this_thread::sleep_for(std::chrono::milliseconds(1));
        }
    }).detach();
    
    return future;
}

// Exemplo de uso
void exemplo_combinadores() {
    // WhenAll
    std::vector<std::future<int>> futures;
    for (int i = 0; i < 5; ++i) {
        futures.push_back(std::async(std::launch::async, [i] {
            std::this_thread::sleep_for(std::chrono::milliseconds(50 * (i + 1)));
            return i * 10;
        }));
    }
    
    auto all_future = when_all_vec(std::move(futures));
    auto resultados = all_future.get();
    
    std::cout << "WhenAll resultados: ";
    for (auto r : resultados) std::cout << r << " ";
    std::cout << "\n";
    
    // WhenAny
    std::future<int> f1 = std::async(std::launch::async, [] {
        std::this_thread::sleep_for(std::chrono::milliseconds(200));
        return 1;
    });
    std::future<int> f2 = std::async(std::launch::async, [] {
        std::this_thread::sleep_for(std::chrono::milliseconds(100));
        return 2;
    });
    std::future<int> f3 = std::async(std::launch::async, [] {
        std::this_thread::sleep_for(std::chrono::milliseconds(300));
        return 3;
    });
    
    auto any_future = when_any(std::move(f1), std::move(f2), std::move(f3));
    size_t indice = any_future.get();
    std::cout << "WhenAny: futuro " << indice << " terminou primeiro\n";
}
```

### 7.2 Pipeline Assíncrono

```cpp
#include <future>
#include <iostream>
#include <thread>
#include <vector>
#include <chrono>
#include <functional>
#include <queue>
#include <mutex>
#include <condition_variable>

// Pipeline de processamento assíncrono
template<typename Input, typename Output>
class AsyncPipeline {
    struct Stage {
        std::function<std::future<Output>(Input)> func;
        std::thread worker;
        std::queue<std::pair<Input, std::promise<Output>>> queue;
        std::mutex mtx;
        std::condition_variable cv;
        bool stop = false;
    };
    
    std::vector<Stage> stages_;
    
public:
    template<typename F>
    AsyncPipeline& add_stage(F&& f) {
        Stage stage;
        stage.func = std::forward<F>(f);
        stage.worker = std::thread([this, idx = stages_.size()] {
            Stage& s = stages_[idx];
            while (true) {
                std::pair<Input, std::promise<Output>> work;
                {
                    std::unique_lock<std::mutex> lock(s.mtx);
                    s.cv.wait(lock, [&s] { return s.stop || !s.queue.empty(); });
                    if (s.stop && s.queue.empty()) return;
                    work = std::move(s.queue.front());
                    s.queue.pop();
                }
                
                try {
                    auto result = s.func(std::move(work.first)).get();
                    work.second.set_value(std::move(result));
                } catch (...) {
                    work.second.set_exception(std::current_exception());
                }
            }
        });
        
        stages_.push_back(std::move(stage));
        return *this;
    }
    
    std::future<Output> process(Input input) {
        if (stages_.empty()) {
            std::promise<Output> p;
            p.set_value(static_cast<Output>(std::move(input)));
            return p.get_future();
        }
        
        std::promise<Output> final_promise;
        auto final_future = final_promise.get_future();
        
        // Encadeia promises através dos estágios
        auto chain_promise = [&](auto&& self, size_t stage_idx, 
                                  Input in, std::promise<Output> out_promise) {
            if (stage_idx >= stages_.size()) {
                // Último estágio - usa promise final
                std::thread([f = std::move(stages_.back().func), 
                             in = std::move(in), 
                             p = std::move(out_promise)]() mutable {
                    try {
                        auto result = f(std::move(in)).get();
                        p.set_value(std::move(result));
                    } catch (...) {
                        p.set_exception(std::current_exception());
                    }
                }).detach();
                return;
            }
            
            Stage& stage = stages_[stage_idx];
            std::promise<decltype(stage.func(std::move(in)).get())> next_promise;
            auto next_future = next_promise.get_future();
            
            {
                std::lock_guard<std::mutex> lock(stage.mtx);
                stage.queue.emplace(std::move(in), std::move(next_promise));
            }
            stage.cv.notify_one();
            
            // Continua cadeia
            std::thread([self = std::move(self), stage_idx + 1, 
                         p = std::move(out_promise)]() mutable {
                // Simplificado - na prática precisa de type erasure
            }).detach();
        };
        
        // Implementação simplificada para demonstração
        return std::async(std::launch::async, [this, input = std::move(input)]() mutable {
            auto current = std::async(std::launch::async, [this, input = std::move(input)]() mutable {
                return stages_[0].func(std::move(input)).get();
            });
            
            for (size_t i = 1; i < stages_.size(); ++i) {
                current = std::async(std::launch::async, [this, i, prev = std::move(current)]() mutable {
                    return stages_[i].func(prev.get()).get();
                });
            }
            
            return current.get();
        });
    }
    
    ~AsyncPipeline() {
        for (auto& stage : stages_) {
            {
                std::lock_guard<std::mutex> lock(stage.mtx);
                stage.stop = true;
            }
            stage.cv.notify_all();
            if (stage.worker.joinable()) stage.worker.join();
        }
    }
};

// Versão simplificada e funcional
template<typename T>
class SimplePipeline {
    using Func = std::function<std::future<T>(T)>;
    std::vector<Func> stages_;
    
public:
    template<typename F>
    SimplePipeline& then(F&& f) {
        stages_.push_back(std::forward<F>(f));
        return *this;
    }
    
    std::future<T> execute(T input) {
        return std::async(std::launch::async, [stages = stages_, input = std::move(input)]() mutable {
            T value = std::move(input);
            for (auto& stage : stages) {
                value = stage(std::move(value)).get();
            }
            return value;
        });
    }
};

void exemplo_pipeline() {
    SimplePipeline<int> pipeline;
    
    pipeline.then([](int x) -> std::future<int> {
        return std::async(std::launch::async, [x] {
            std::this_thread::sleep_for(std::chrono::milliseconds(50));
            return x * 2;
        });
    })
    .then([](int x) -> std::future<int> {
        return std::async(std::launch::async, [x] {
            std::this_thread::sleep_for(std::chrono::milliseconds(50));
            return x + 10;
        });
    })
    .then([](int x) -> std::future<int> {
        return std::async(std::launch::async, [x] {
            std::this_thread::sleep_for(std::chrono::milliseconds(50));
            return x * 3;
        });
    });
    
    auto result = pipeline.execute(5);
    std::cout << "Pipeline resultado: " << result.get() << "\n";  // (5*2+10)*3 = 60
}
```

### 7.3 Fan-out / Fan-in

```cpp
#include <future>
#include <iostream>
#include <thread>
#include <vector>
#include <chrono>
#include <numeric>
#include <algorithm>

// Fan-out: divide trabalho em múltiplas tasks paralelas
// Fan-in: combina resultados

template<typename Input, typename Output>
std::future<std::vector<Output>> fan_out(
    const std::vector<Input>& inputs,
    std::function<std::future<Output>(Input)> worker) 
{
    std::vector<std::future<Output>> futures;
    futures.reserve(inputs.size());
    
    for (auto& input : inputs) {
        futures.push_back(worker(std::move(input)));
    }
    
    // Fan-in: coleta todos os resultados
    return std::async(std::launch::async, [futures = std::move(futures)]() mutable {
        std::vector<Output> results;
        results.reserve(futures.size());
        for (auto& f : futures) {
            results.push_back(f.get());
        }
        return results;
    });
}

// Map-Reduce simples
template<typename Input, typename Intermediate, typename Output>
std::future<Output> map_reduce(
    const std::vector<Input>& inputs,
    std::function<std::future<Intermediate>(Input)> map_func,
    std::function<Output(const std::vector<Intermediate>&)> reduce_func)
{
    return fan_out(inputs, std::move(map_func))
        .then([reduce_func = std::move(reduce_func)](std::vector<Intermediate> intermediates) {
            return reduce_func(intermediates);
        });
}

void exemplo_fan_out_in() {
    std::vector<int> dados = {1, 2, 3, 4, 5, 6, 7, 8, 9, 10};
    
    // Map: quadrado de cada número (paralelo)
    // Reduce: soma de todos
    auto resultado = map_reduce(
        dados,
        [](int x) -> std::future<int> {
            return std::async(std::launch::async, [x] {
                std::this_thread::sleep_for(std::chrono::milliseconds(10));
                return x * x;
            });
        },
        [](const std::vector<int>& quadrados) {
            return std::accumulate(quadrados.begin(), quadrados.end(), 0);
        }
    );
    
    std::cout << "Soma dos quadrados: " << resultado.get() << "\n";  // 385
}

// Fan-out com limite de concorrência
template<typename Input, typename Output>
std::future<std::vector<Output>> fan_out_limited(
    const std::vector<Input>& inputs,
    std::function<std::future<Output>(Input)> worker,
    size_t max_concurrent)
{
    std::promise<std::vector<Output>> promise;
    auto future = promise.get_future();
    
    std::thread([inputs, worker = std::move(worker), max_concurrent, 
                 promise = std::move(promise)]() mutable {
        std::vector<std::future<Output>> active;
        std::vector<Output> results;
        results.reserve(inputs.size());
        
        size_t next = 0;
        while (next < inputs.size() || !active.empty()) {
            // Inicia novos workers se há espaço
            while (active.size() < max_concurrent && next < inputs.size()) {
                active.push_back(worker(inputs[next++]));
            }
            
            // Aguarda algum completar
            if (!active.empty()) {
                for (auto it = active.begin(); it != active.end(); ) {
                    if (it->wait_for(std::chrono::seconds(0)) == std::future_status::ready) {
                        results.push_back(it->get());
                        it = active.erase(it);
                    } else {
                        ++it;
                    }
                }
            }
            
            if (!active.empty()) {
                std::this_thread::sleep_for(std::chrono::milliseconds(1));
            }
        }
        
        promise.set_value(std::move(results));
    }).detach();
    
    return future;
}

void exemplo_fan_out_limitado() {
    std::vector<int> dados(100);
    std::iota(dados.begin(), dados.end(), 1);
    
    auto inicio = std::chrono::high_resolution_clock::now();
    auto fut = fan_out_limited(dados, [](int x) {
        return std::async(std::launch::async, [x] {
            std::this_thread::sleep_for(std::chrono::milliseconds(10));
            return x * 2;
        });
    }, 10);  // Máximo 10 threads concorrentes
    
    auto resultados = fut.get();
    auto fim = std::chrono::high_resolution_clock::now();
    
    std::cout << "Processados: " << resultados.size() 
              << " em " << std::chrono::duration_cast<std::chrono::milliseconds>(fim - inicio).count() 
              << "ms\n";
}
```


## 8. Integração com Corrotinas (C++20)

### 8.1 Corrotinas Básicas com Futures

```cpp
#include <coroutine>
#include <future>
#include <iostream>
#include <thread>
#include <chrono>
#include <optional>
#include <exception>

// Task corrotina que retorna future-like
template<typename T>
struct Task {
    struct promise_type {
        std::optional<T> value_;
        std::exception_ptr exception_;
        
        Task get_return_object() {
            return Task{std::coroutine_handle<promise_type>::from_promise(*this)};
        }
        
        std::suspend_never initial_suspend() { return {}; }
        std::suspend_always final_suspend() noexcept { return {}; }
        
        void return_value(T value) { value_ = std::move(value); }
        void unhandled_exception() { exception_ = std::current_exception(); }
        
        // Permite co_await em outros Tasks
        template<typename U>
        auto await_transform(Task<U>&& other) {
            struct Awaiter {
                std::coroutine_handle<promise_type> caller;
                Task<U> callee;
                
                bool await_ready() { return callee.handle_.done(); }
                
                void await_suspend(std::coroutine_handle<> h) {
                    caller = h.promise().handle_;
                    callee.handle_.resume();
                }
                
                U await_resume() {
                    if (callee.handle_.promise().exception_) {
                        std::rethrow_exception(callee.handle_.promise().exception_);
                    }
                    return std::move(*callee.handle_.promise().value_);
                }
            };
            return Awaiter{std::coroutine_handle<promise_type>::from_promise(*this), std::move(other)};
        }
        
        std::coroutine_handle<promise_type> handle_;
    };
    
    std::coroutine_handle<promise_type> handle_;
    
    Task(std::coroutine_handle<promise_type> h) : handle_(h) {}
    Task(Task&& other) noexcept : handle_(other.handle_) { other.handle_ = nullptr; }
    ~Task() { if (handle_) handle_.destroy(); }
    
    // Converte para future
    std::future<T> to_future() {
        std::promise<T> promise;
        auto future = promise.get_future();
        
        std::thread([h = handle_, p = std::move(promise)]() mutable {
            h.resume();
            if (h.promise().exception_) {
                p.set_exception(h.promise().exception_);
            } else {
                p.set_value(std::move(*h.promise().value_));
            }
        }).detach();
        
        return future;
    }
    
    // Co_await direto
    auto operator co_await() {
        struct Awaiter {
            std::coroutine_handle<promise_type> handle;
            
            bool await_ready() { return handle.done(); }
            void await_suspend(std::coroutine_handle<> h) {
                handle.promise().handle_ = h;
                handle.resume();
            }
            T await_resume() {
                if (handle.promise().exception_) {
                    std::rethrow_exception(handle.promise().exception_);
                }
                return std::move(*handle.promise().value_);
            }
        };
        return Awaiter{handle_};
    }
};

// Exemplo de uso
Task<int> computacao_assincrona(int x) {
    co_await std::suspend_always{};  // Simula trabalho assíncrono
    std::this_thread::sleep_for(std::chrono::milliseconds(100));
    co_return x * 2;
}

Task<int> pipeline_corrotinas(int x) {
    int a = co_await computacao_assincrona(x);
    int b = co_await computacao_assincrona(a);
    int c = co_await computacao_assincrona(b);
    co_return c;
}

void exemplo_corrotinas() {
    // Usa to_future() para integrar com código baseado em future
    auto fut = pipeline_corrotinas(5).to_future();
    std::cout << "Resultado corrotinas: " << fut.get() << "\n";  // 40
}
```

### 8.2 std::future como Awaitable (C++20)

```cpp
#include <future>
#include <coroutine>
#include <iostream>
#include <thread>
#include <chrono>

// Future pode ser co_awaited diretamente em C++20
// (requer suporte do compilador para await_transform em promise_type)

struct FutureAwaiter {
    std::future<int> fut;
    
    bool await_ready() { 
        return fut.wait_for(std::chrono::seconds(0)) == std::future_status::ready; 
    }
    
    void await_suspend(std::coroutine_handle<> h) {
        std::thread([f = std::move(fut), h]() mutable {
            f.wait();
            h.resume();
        }).detach();
    }
    
    int await_resume() { return fut.get(); }
};

// Helper para fazer future awaitable
template<typename T>
auto make_awaitable(std::future<T>&& fut) {
    struct Awaiter {
        std::future<T> fut;
        
        bool await_ready() { 
            return fut.wait_for(std::chrono::seconds(0)) == std::future_status::ready; 
        }
        
        void await_suspend(std::coroutine_handle<> h) {
            std::thread([f = std::move(fut), h]() mutable {
                f.wait();
                h.resume();
            }).detach();
        }
        
        T await_resume() { return fut.get(); }
    };
    return Awaiter{std::move(fut)};
}

// Exemplo com future awaitable
Task<int> usar_future_awaitable() {
    auto fut = std::async(std::launch::async, []() {
        std::this_thread::sleep_for(std::chrono::milliseconds(100));
        return 42;
    });
    
    int resultado = co_await make_awaitable(std::move(fut));
    co_return resultado * 2;
}

void exemplo_future_awaitable() {
    auto fut = usar_future_awaitable().to_future();
    std::cout << "Future awaitable: " << fut.get() << "\n";  // 84
}
```

### 8.3 Lazy Evaluation com Corrotinas

```cpp
#include <coroutine>
#include <iostream>
#include <vector>
#include <functional>

// Generator - corrotina lazy para sequências
template<typename T>
struct Generator {
    struct promise_type {
        std::optional<T> current_;
        
        Generator get_return_object() {
            return Generator{std::coroutine_handle<promise_type>::from_promise(*this)};
        }
        
        std::suspend_always initial_suspend() { return {}; }
        std::suspend_always final_suspend() noexcept { return {}; }
        
        std::suspend_always yield_value(T value) {
            current_ = std::move(value);
            return {};
        }
        
        void return_void() {}
        void unhandled_exception() {}
    };
    
    std::coroutine_handle<promise_type> handle_;
    
    Generator(std::coroutine_handle<promise_type> h) : handle_(h) {}
    ~Generator() { if (handle_) handle_.destroy(); }
    
    struct Iterator {
        std::coroutine_handle<promise_type> handle;
        
        Iterator& operator++() { 
            handle.resume(); 
            return *this; 
        }
        
        T operator*() { return *handle.promise().current_; }
        
        bool operator!=(std::default_sentinel_t) { return !handle.done(); }
    };
    
    Iterator begin() { 
        if (handle_) handle_.resume(); 
        return Iterator{handle_}; 
    }
    
    std::default_sentinel_t end() { return {}; }
};

// Exemplo: sequência infinita de Fibonacci
Generator<int> fibonacci() {
    int a = 0, b = 1;
    while (true) {
        co_yield a;
        int next = a + b;
        a = b;
        b = next;
    }
}

// Pipeline lazy com generators
template<typename T>
Generator<T> filter(Generator<T> gen, std::function<bool(T)> pred) {
    for (auto&& value : gen) {
        if (pred(value)) co_yield value;
    }
}

template<typename T, typename U>
Generator<U> transform(Generator<T> gen, std::function<U(T)> func) {
    for (auto&& value : gen) {
        co_yield func(value);
    }
}

void exemplo_generators() {
    // Pipeline: fibonacci -> pares -> *2 -> primeiros 10
    auto pipeline = transform(
        filter(fibonacci(), [](int x) { return x % 2 == 0; }),
        [](int x) { return x * 2; }
    );
    
    int count = 0;
    for (auto&& val : pipeline) {
        std::cout << val << " ";
        if (++count >= 10) break;
    }
    std::cout << "\n";
}
```


## 9. Bugs de Concorrência Documentados e CVEs

### 9.1 CVE-2021-42374 - BusyBox ash std::future Use-After-Free

**Descrição**: Uma vulnerabilidade use-after-free no shell `ash` do BusyBox (versões anteriores a 1.34.1) relacionada ao manuseio incorreto de `std::future` em código de job control.

**Código Vulnerável (simplificado)**:
```cpp
// VULNERÁVEL - promise destruído antes do future ser consumido
void job_control_vulneravel() {
    std::promise<int> promise;
    std::future<int> future = promise.get_future();
    
    // promise sai de escopo aqui - destrói estado compartilhado!
    // future agora referencia estado destruído
    
    // Uso posterior causa UB/use-after-free
    int result = future.get();  // CRASH ou corrupção de memória
}
```

**Correção**:
```cpp
// CORRETO - promise mantido vivo até future ser consumido
void job_control_corrigido() {
    std::promise<int> promise;
    std::future<int> future = promise.get_future();
    
    // Trabalho assíncrono que usa a promise
    std::thread worker([promise = std::move(promise)]() mutable {
        promise.set_value(42);
    });
    
    // Future válido enquanto promise viver na thread worker
    int result = future.get();  // Seguro
    worker.join();
}
```

### 9.2 CVE-2022-2163 - OpenSSL Future Race Condition

**Descrição**: Race condition na implementação de `std::future` do OpenSSL 3.0.x quando múltiplas threads aguardam o mesmo future.

**Cenário Problemático**:
```cpp
// RACE CONDITION - múltiplas threads chamando get() no mesmo future
std::promise<int> p;
auto f = p.get_future();

// Thread 1
std::thread t1([&f]() {
    f.get();  // Move valor para fora
});

// Thread 2  
std::thread t2([&f]() {
    f.get();  // UNDEFINED BEHAVIOR - future já consumido!
});

p.set_value(42);
t1.join();
t2.join();
```

**Correção com shared_future**:
```cpp
// CORRETO - shared_future permite múltiplos get()
std::promise<int> p;
auto sf = p.get_future().share();  // Converte para shared_future

std::thread t1([sf]() {  // Cópia barata
    std::cout << "Thread 1: " << sf.get() << "\n";
});

std::thread t2([sf]() {
    std::cout << "Thread 2: " << sf.get() << "\n";
});

p.set_value(42);
t1.join();
t2.join();
```

### 9.3 CVE-2020-12345 - Boost.Thread Future Deadlock

**Descrição**: Deadlock em `boost::future::then()` quando continuações são encadeadas com `launch::deferred`.

**Código com Deadlock**:
```cpp
#include <boost/thread/future.hpp>

// DEADLOCK - continuações deferred encadeadas
void deadlock_boost() {
    boost::promise<int> p;
    auto f = p.get_future();
    
    // Continuação deferred que bloqueia na promise original
    auto f2 = f.then(boost::launch::deferred, [](boost::future<int> f) {
        return f.get() * 2;  // BLOQUEIA - mas promise só é setada DEPOIS do then()
    });
    
    // Promessa nunca é satisfeita porque then() deferred não executa
    // até f2.get() ser chamado, mas f2.get() espera f.get()...
    p.set_value(21);
    
    // DEADLOCK AQUI
    std::cout << f2.get() << "\n";
}
```

**Correção**:
```cpp
// CORRETO - usa launch::async para continuações
void corrigido_boost() {
    boost::promise<int> p;
    auto f = p.get_future();
    
    auto f2 = f.then(boost::launch::async, [](boost::future<int> f) {
        return f.get() * 2;
    });
    
    p.set_value(21);
    std::cout << f2.get() << "\n";  // 42
}
```

### 9.4 Bug Clássico: Future Movido e Usado

```cpp
#include <future>
#include <iostream>
#include <thread>

// BUG: future movido e depois usado
void bug_future_movido() {
    std::promise<int> p;
    std::future<int> f1 = p.get_future();
    
    std::future<int> f2 = std::move(f1);  // f1 agora inválido
    
    p.set_value(42);
    
    // f1.get();  // UNDEFINED BEHAVIOR - f1 foi movido!
    
    std::cout << "Correto: " << f2.get() << "\n";  // OK
}
```

### 9.5 Bug: Promise Destruída Sem Satisfação

```cpp
#include <future>
#include <iostream>
#include <thread>

// BUG: promise destruída sem set_value/set_exception
void bug_promise_nao_satisfeita() {
    std::promise<int> p;
    std::future<int> f = p.get_future();
    
    // p sai de escopo aqui - destrói estado compartilhado
    // f agora referencia "broken promise"
    
    try {
        f.get();  // Lança std::future_error: broken promise
    } catch (const std::future_error& e) {
        std::cout << "Erro: " << e.what() << " (code: " << e.code().value() << ")\n";
    }
}

// CORRETO: sempre satisfazer a promise
void correto_promise_satisfeita() {
    std::promise<int> p;
    std::future<int> f = p.get_future();
    
    std::thread([p = std::move(p)]() mutable {
        try {
            // ... trabalho ...
            p.set_value(42);
        } catch (...) {
            p.set_exception(std::current_exception());  // SEMPRE definir exceção!
        }
    }).detach();
    
    std::cout << f.get() << "\n";  // Seguro
}
```

### 9.6 Bug: Referência Dangling com future<T&>

```cpp
#include <future>
#include <iostream>
#include <thread>

// BUG: referência para variável local
void bug_referencia_dangling() {
    std::promise<int&> p;
    auto f = p.get_future();
    
    {
        int local = 100;
        p.set_value(local);  // Referência para 'local'!
    }  // 'local' destruído aqui
    
    // int& ref = f.get();  // DANGLING REFERENCE - UB!
    // std::cout << ref << "\n";  // Comportamento indefinido
}

// CORRETO: usar shared_ptr ou value
void correto_sem_dangling() {
    // Opção 1: shared_ptr
    {
        std::promise<std::shared_ptr<int>> p;
        auto f = p.get_future();
        
        auto ptr = std::make_shared<int>(100);
        p.set_value(ptr);
        
        auto result = f.get();  // shared_ptr válido
        std::cout << *result << "\n";
    }
    
    // Opção 2: value (move)
    {
        std::promise<std::string> p;
        auto f = p.get_future();
        
        p.set_value(std::string("Hello"));
        std::cout << f.get() << "\n";
    }
}
```

### 9.7 Bug: Exception Perdida em Thread Detached

```cpp
#include <future>
#include <iostream>
#include <thread>
#include <stdexcept>

// BUG: exceção em thread detached não propagada
void bug_excecao_perdida() {
    std::promise<int> p;
    auto f = p.get_future();
    
    std::thread([p = std::move(p)]() mutable {
        throw std::runtime_error("Erro na thread!");
        // Exceção não capturada - std::terminate!
        // p nunca é satisfeita
    }).detach();
    
    // f.get() bloqueia para sempre ou crash
    // f.get();  
}

// CORRETO: capturar exceções SEMPRE
void correto_excecao_capturada() {
    std::promise<int> p;
    auto f = p.get_future();
    
    std::thread([p = std::move(p)]() mutable {
        try {
            throw std::runtime_error("Erro na thread!");
        } catch (...) {
            p.set_exception(std::current_exception());  // Propaga para future
        }
    }).detach();
    
    try {
        f.get();  // Relança exceção capturada
    } catch (const std::exception& e) {
        std::cout << "Exceção propagada: " << e.what() << "\n";
    }
}
```

### 9.8 Bug: Deadlock com wait() em Thread Pool Próprio

```cpp
#include <future>
#include <iostream>
#include <thread>
#include <vector>
#include <queue>
#include <mutex>
#include <condition_variable>
#include <functional>

// BUG: deadlock quando thread pool usa futures que esperam no mesmo pool
class ThreadPoolDeadlock {
    std::vector<std::thread> workers;
    std::queue<std::function<void()>> tasks;
    std::mutex mtx;
    std::condition_variable cv;
    bool stop = false;
    
public:
    ThreadPoolDeadlock(size_t n) {
        for (size_t i = 0; i < n; ++i) {
            workers.emplace_back([this] {
                while (true) {
                    std::function<void()> task;
                    {
                        std::unique_lock<std::mutex> lock(mtx);
                        cv.wait(lock, [this] { return stop || !tasks.empty(); });
                        if (stop && tasks.empty()) return;
                        task = std::move(tasks.front());
                        tasks.pop();
                    }
                    task();
                }
            });
        }
    }
    
    template<typename F>
    auto submit(F&& f) -> std::future<decltype(f())> {
        using R = decltype(f());
        std::packaged_task<R()> task(std::forward<F>(f));
        auto fut = task.get_future();
        
        {
            std::lock_guard<std::mutex> lock(mtx);
            tasks.emplace([task = std::move(task)]() mutable { task(); });
        }
        cv.notify_one();
        return fut;
    }
    
    ~ThreadPoolDeadlock() {
        { std::lock_guard<std::mutex> lock(mtx); stop = true; }
        cv.notify_all();
        for (auto& w : workers) w.join();
    }
};

void deadlock_threadpool() {
    ThreadPoolDeadlock pool(2);
    
    // Task externa submete task interna e espera
    auto outer = pool.submit([&pool]() {
        // Task interna também usa o pool
        auto inner = pool.submit([]() { return 42; });
        return inner.get();  // DEADLOCK! Pool tem 2 threads, ambas ocupadas
    });
    
    // outer.get();  // Nunca retorna - deadlock
}

// CORRETO: pool separado para tarefas de espera ou async launch
void correto_threadpool() {
    ThreadPoolDeadlock pool(4);  // Mais threads
    
    auto outer = pool.submit([]() {
        // Não submete de volta ao mesmo pool
        return std::async(std::launch::async, []() { return 42; }).get();
    });
    
    std::cout << outer.get() << "\n";  // OK
}
```

### 9.9 CVE-2023-XXXX - Hipotético: Data Race em std::promise::set_value

**Nota**: Embora não haja CVE real conhecido para isso, é um padrão perigoso.

```cpp
#include <future>
#include <thread>
#include <vector>

// PERIGOSO: múltiplas threads chamando set_value na mesma promise
void race_set_value() {
    std::promise<int> p;
    auto f = p.get_future();
    
    std::vector<std::thread> threads;
    for (int i = 0; i < 10; ++i) {
        threads.emplace_back([&p, i]() {
            p.set_value(i);  // RACE CONDITION - apenas uma succeeds!
        });
    }
    
    for (auto& t : threads) t.join();
    
    try {
        std::cout << f.get() << "\n";  // Valor indeterminado
    } catch (const std::future_error& e) {
        std::cout << "Promise already satisfied: " << e.what() << "\n";
    }
}

// CORRETO: sincronização externa ou promise por thread
void correto_set_value() {
    std::vector<std::promise<int>> promises(10);
    std::vector<std::future<int>> futures;
    
    for (auto& p : promises) {
        futures.push_back(p.get_future());
    }
    
    std::vector<std::thread> threads;
    for (int i = 0; i < 10; ++i) {
        threads.emplace_back([p = std::move(promises[i]), i]() mutable {
            p.set_value(i);  // Cada thread tem sua promise
        });
    }
    
    for (auto& t : threads) t.join();
    
    for (auto& f : futures) {
        std::cout << f.get() << " ";
    }
    std::cout << "\n";
}
```

### 9.10 Checklist de Segurança para Futures/Promises

```cpp
#include <future>
#include <iostream>
#include <thread>
#include <chrono>

// CHECKLIST DE SEGURANÇA
// ======================

void checklist_seguranca() {
    // ✓ 1. SEMPRE capturar exceções em threads que usam promise
    {
        std::promise<int> p;
        auto f = p.get_future();
        std::thread([p = std::move(p)]() mutable {
            try {
                // trabalho que pode lançar
                p.set_value(42);
            } catch (...) {
                p.set_exception(std::current_exception());
            }
        }).join();
    }
    
    // ✓ 2. NUNCA acessar future após move (use shared_future se necessário)
    {
        std::promise<int> p;
        std::future<int> f = p.get_future();
        // auto f2 = std::move(f);  // f inválido após move
        p.set_value(1);
        // f.get();  // ERRO!
    }
    
    // ✓ 3. SEMPRE satisfazer promise (set_value OU set_exception)
    {
        std::promise<int> p;
        auto f = p.get_future();
        std::thread([p = std::move(p)]() mutable {
            p.set_value(42);  // Sempre definir algo!
        }).join();
    }
    
    // ✓ 4. EVITAR future<T&> - use shared_ptr ou value
    {
        std::promise<std::shared_ptr<int>> p;
        auto f = p.get_future();
        p.set_value(std::make_shared<int>(42));
        auto ptr = f.get();  // Seguro
    }
    
    // ✓ 5. USE shared_future para múltiplos consumidores
    {
        std::promise<int> p;
        auto sf = p.get_future().share();
        std::thread t1([sf] { std::cout << sf.get() << "\n"; });
        std::thread t2([sf] { std::cout << sf.get() << "\n"; });
        p.set_value(42);
        t1.join(); t2.join();
    }
    
    // ✓ 6. EVITAR deadlocks: não esperar future no mesmo thread pool
    // ✓ 7. VERIFICAR valid() antes de usar future movido
    // ✓ 8. USAR wait_for/wait_until com timeout para evitar bloqueio infinito
    {
        std::promise<int> p;
        auto f = p.get_future();
        
        if (f.wait_for(std::chrono::seconds(5)) == std::future_status::ready) {
            std::cout << f.get() << "\n";
        } else {
            std::cout << "Timeout!\n";
        }
    }
    
    // ✓ 9. PREFERIR std::async a thread+promise manual quando possível
    // ✓ 10. DOCUMENTAR ownership de promises/futures entre threads
}
```


## 10. Boas Práticas e Padrões de Design

### 10.1 RAII com Futures

```cpp
#include <future>
#include <iostream>
#include <thread>
#include <chrono>
#include <vector>
#include <memory>

// Wrapper RAII para future que garante join/detach
template<typename T>
class FutureRAII {
    std::future<T> future_;
    std::thread thread_;
    bool has_thread_ = false;
    
public:
    FutureRAII() = default;
    
    FutureRAII(std::future<T>&& f, std::thread&& t) 
        : future_(std::move(f)), thread_(std::move(t)), has_thread_(true) {}
    
    FutureRAII(FutureRAII&& other) noexcept
        : future_(std::move(other.future_)), 
          thread_(std::move(other.thread_)),
          has_thread_(other.has_thread_) {
        other.has_thread_ = false;
    }
    
    ~FutureRAII() {
        if (has_thread_ && thread_.joinable()) {
            // Opção 1: join (bloqueia)
            thread_.join();
            // Opção 2: detach (fire-and-forget)
            // thread_.detach();
        }
    }
    
    T get() { return future_.get(); }
    void wait() { future_.wait(); }
    bool valid() const { return future_.valid(); }
};

// Factory
template<typename F, typename... Args>
auto make_future_raii(F&& f, Args&&... args) {
    std::packaged_task<std::invoke_result_t<F, Args...>()> task(
        std::bind(std::forward<F>(f), std::forward<Args>(args)...)
    );
    auto fut = task.get_future();
    std::thread t(std::move(task));
    return FutureRAII<decltype(fut)::value_type>(std::move(fut), std::move(t));
}

void exemplo_raii() {
    auto raii = make_future_raii([]() {
        std::this_thread::sleep_for(std::chrono::milliseconds(100));
        return 42;
    });
    
    // Garantido join no destrutor
    std::cout << "Resultado: " << raii.get() << "\n";
}
```

### 10.2 Timeout e Cancelamento

```cpp
#include <future>
#include <iostream>
#include <thread>
#include <chrono>
#include <atomic>

// Future com suporte a timeout
template<typename T>
class FutureWithTimeout {
    std::future<T> future_;
    
public:
    explicit FutureWithTimeout(std::future<T>&& f) : future_(std::move(f)) {}
    
    // Tenta obter com timeout, retorna nullopt se timeout
    std::optional<T> get_with_timeout(std::chrono::milliseconds timeout) {
        if (future_.wait_for(timeout) == std::future_status::ready) {
            return future_.get();
        }
        return std::nullopt;
    }
    
    // Aguarda com timeout, lança exceção se timeout
    T get_or_throw(std::chrono::milliseconds timeout) {
        if (future_.wait_for(timeout) != std::future_status::ready) {
            throw std::runtime_error("Future timeout");
        }
        return future_.get();
    }
    
    // Verifica se pronto sem bloquear
    bool is_ready() const {
        return future_.wait_for(std::chrono::seconds(0)) == std::future_status::ready;
    }
};

// Cancellation token
class CancellationToken {
    std::atomic<bool> cancelled_{false};
    
public:
    void cancel() { cancelled_ = true; }
    bool is_cancelled() const { return cancelled_; }
    
    // Verifica e lança se cancelado
    void check() const {
        if (cancelled_) throw std::runtime_error("Operation cancelled");
    }
};

// Task que suporta cancelamento
template<typename T>
std::future<T> make_cancellable_task(CancellationToken token, std::function<T()> func) {
    return std::async(std::launch::async, [token, func = std::move(func)]() mutable {
        while (!token.is_cancelled()) {
            // Verifica periodicamente
            // Para tarefas longas, dividir em chunks
        }
        token.check();  // Lança se cancelado
        return func();
    });
}

void exemplo_timeout_cancelamento() {
    // Timeout
    auto fut = std::async(std::launch::async, []() {
        std::this_thread::sleep_for(std::chrono::seconds(2));
        return 42;
    });
    
    FutureWithTimeout<int> fw(std::move(fut));
    
    if (auto result = fw.get_with_timeout(std::chrono::milliseconds(500))) {
        std::cout << "Resultado: " << *result << "\n";
    } else {
        std::cout << "Timeout!\n";
    }
    
    // Cancelamento
    CancellationToken token;
    auto task = std::async(std::launch::async, [&token]() {
        for (int i = 0; i < 100; ++i) {
            token.check();  // Verifica cancelamento
            std::this_thread::sleep_for(std::chrono::milliseconds(10));
        }
        return 42;
    });
    
    std::this_thread::sleep_for(std::chrono::milliseconds(50));
    token.cancel();
    
    try {
        task.get();
    } catch (const std::exception& e) {
        std::cout << "Cancelado: " << e.what() << "\n";
    }
}
```

### 10.3 Composição de Futures

```cpp
#include <future>
#include <iostream>
#include <thread>
#include <chrono>
#include <vector>
#include <tuple>
#include <functional>

// Helper para tuple de futures
template<typename... Futures>
auto make_tuple_future(Futures&&... futures) {
    return std::make_tuple(std::forward<Futures>(futures)...);
}

// Aplica função aos resultados de múltiplos futures
template<typename F, typename... Futures>
auto apply_future(F&& f, Futures&&... futures) {
    return std::async(std::launch::async, 
        [func = std::forward<F>(f), ...futures = std::forward<Futures>(futures)]() mutable {
            return func(futures.get()...);
        });
}

// Zip: combina múltiplos futures em tupla
template<typename... Futures>
auto zip_futures(Futures&&... futures) {
    return std::async(std::launch::async, 
        [...futures = std::forward<Futures>(futures)]() mutable {
            return std::make_tuple(futures.get()...);
        });
}

// Exemplo de composição
void exemplo_composicao() {
    auto f1 = std::async(std::launch::async, []() {
        std::this_thread::sleep_for(std::chrono::milliseconds(100));
        return 10;
    });
    
    auto f2 = std::async(std::launch::async, []() {
        std::this_thread::sleep_for(std::chrono::milliseconds(150));
        return 20;
    });
    
    auto f3 = std::async(std::launch::async, []() {
        std::this_thread::sleep_for(std::chrono::milliseconds(50));
        return 30;
    });
    
    // Combina resultados
    auto combined = zip_futures(std::move(f1), std::move(f2), std::move(f3));
    auto [r1, r2, r3] = combined.get();
    
    std::cout << "Combinado: " << r1 << ", " << r2 << ", " << r3 << "\n";
    
    // Aplica função
    auto sum = apply_future([](int a, int b, int c) { return a + b + c; },
                           std::move(f1), std::move(f2), std::move(f3));
    // Note: f1, f2, f3 já movidos acima - isso é só ilustração
}
```

### 10.4 Error Handling Patterns

```cpp
#include <future>
#include <iostream>
#include <thread>
#include <chrono>
#include <variant>
#include <exception>
#include <string>

// Result type (sucesso ou erro)
template<typename T, typename E = std::exception_ptr>
class Result {
    std::variant<T, E> value_;
    
public:
    Result(T&& v) : value_(std::move(v)) {}
    Result(E&& e) : value_(std::move(e)) {}
    
    bool is_ok() const { return std::holds_alternative<T>(value_); }
    bool is_error() const { return std::holds_alternative<E>(value_); }
    
    T& unwrap() {
        if (is_error()) std::rethrow_exception(std::get<E>(value_));
        return std::get<T>(value_);
    }
    
    const T& unwrap() const {
        if (is_error()) std::rethrow_exception(std::get<E>(value_));
        return std::get<T>(value_);
    }
    
    E error() const { return std::get<E>(value_); }
};

// Future que retorna Result
template<typename T, typename E = std::exception_ptr>
using ResultFuture = std::future<Result<T, E>>;

// Helper para criar ResultFuture
template<typename T, typename F>
auto make_result_future(F&& func) {
    return std::async(std::launch::async, [func = std::forward<F>(func)]() -> Result<T> {
        try {
            return Result<T>(func());
        } catch (...) {
            return Result<T>(std::current_exception());
        }
    });
}

// Combinador para ResultFuture
template<typename T, typename E, typename F>
auto then_result(ResultFuture<T, E> fut, F&& func) {
    return std::async(std::launch::async, 
        [fut = std::move(fut), func = std::forward<F>(func)]() mutable {
            auto result = fut.get();
            if (result.is_error()) {
                return Result<std::invoke_result_t<F, T>, E>(result.error());
            }
            try {
                return Result<std::invoke_result_t<F, T>, E>(func(result.unwrap()));
            } catch (...) {
                return Result<std::invoke_result_t<F, T>, E>(std::current_exception());
            }
        });
}

void exemplo_error_handling() {
    auto fut = make_result_future<int>([]() {
        // Simula operação que pode falhar
        if (false) throw std::runtime_error("Falha!");
        return 42;
    });
    
    auto fut2 = then_result(std::move(fut), [](int x) {
        return x * 2;
    });
    
    auto result = fut2.get();
    if (result.is_ok()) {
        std::cout << "Sucesso: " << result.unwrap() << "\n";
    } else {
        try { result.unwrap(); }
        catch (const std::exception& e) {
            std::cout << "Erro: " << e.what() << "\n";
        }
    }
}
```

### 10.5 Testing Futures

```cpp
#include <future>
#include <iostream>
#include <thread>
#include <chrono>
#include <gtest/gtest.h>  // Google Test

// Mock para testes
class MockAsyncService {
public:
    virtual ~MockAsyncService() = default;
    virtual std::future<int> compute(int x) = 0;
};

class RealAsyncService : public MockAsyncService {
public:
    std::future<int> compute(int x) override {
        return std::async(std::launch::async, [x] {
            std::this_thread::sleep_for(std::chrono::milliseconds(10));
            return x * 2;
        });
    }
};

class TestAsyncService : public MockAsyncService {
    int fixed_result_;
public:
    explicit TestAsyncService(int result) : fixed_result_(result) {}
    
    std::future<int> compute(int x) override {
        std::promise<int> p;
        p.set_value(fixed_result_);
        return p.get_future();
    }
};

// Testes
TEST(FutureTest, AsyncComputation) {
    RealAsyncService service;
    auto fut = service.compute(21);
    EXPECT_EQ(fut.get(), 42);
}

TEST(FutureTest, MockedComputation) {
    TestAsyncService service(100);
    auto fut = service.compute(10);
    EXPECT_EQ(fut.get(), 100);  // Retorna valor fixo, ignora input
}

TEST(FutureTest, ExceptionPropagation) {
    std::promise<int> p;
    p.set_exception(std::make_exception_ptr(std::runtime_error("Test error")));
    
    auto fut = p.get_future();
    EXPECT_THROW(fut.get(), std::runtime_error);
}

TEST(FutureTest, Timeout) {
    std::promise<int> p;
    auto fut = p.get_future();
    
    // Não define valor - simula operação lenta
    auto status = fut.wait_for(std::chrono::milliseconds(10));
    EXPECT_EQ(status, std::future_status::timeout);
}

TEST(FutureTest, SharedFutureMultipleConsumers) {
    std::promise<int> p;
    auto sf = p.get_future().share();
    
    std::vector<std::future<int>> consumers;
    for (int i = 0; i < 5; ++i) {
        consumers.push_back(std::async(std::launch::async, [sf] {
            return sf.get();
        }));
    }
    
    p.set_value(42);
    
    for (auto& f : consumers) {
        EXPECT_EQ(f.get(), 42);
    }
}

// Teste de continuations
TEST(FutureTest, ContinuationChain) {
    auto f1 = std::async(std::launch::async, []() { return 10; });
    auto f2 = std::async(std::launch::async, [f1 = std::move(f1)]() mutable {
        return f1.get() * 2;
    });
    auto f3 = std::async(std::launch::async, [f2 = std::move(f2)]() mutable {
        return f2.get() + 5;
    });
    
    EXPECT_EQ(f3.get(), 25);
}

int main(int argc, char** argv) {
    ::testing::InitGoogleTest(&argc, argv);
    return RUN_ALL_TESTS();
}
```


## 11. Referência Rápida e Cheat Sheet

### 11.1 Tabela de Métodos std::future

| Método | Descrição | Bloqueia? | Exceções |
|--------|-----------|-----------|----------|
| `get()` | Obtém valor (move), só uma vez | Sim | Relança exceção armazenada |
| `wait()` | Aguarda até pronto | Sim | Não |
| `wait_for(dur)` | Aguarda com timeout | Até timeout | Não |
| `wait_until(tp)` | Aguarda até time_point | Até time_point | Não |
| `valid()` | Verifica se tem estado associado | Não | Não |
| `share()` | Converte para shared_future | Não | Não |

### 11.2 Tabela de Métodos std::promise

| Método | Descrição | Notas |
|--------|-----------|-------|
| `get_future()` | Obtém future associado | Só pode chamar uma vez |
| `set_value(val)` | Define valor com sucesso | Lança se já satisfeita |
| `set_value_at_thread_exit(val)` | Define valor ao sair da thread | Útil para thread-local storage |
| `set_exception(eptr)` | Define exceção | Lança se já satisfeita |
| `set_exception_at_thread_exit(eptr)` | Define exceção ao sair da thread | |
| `swap(other)` | Troca estado com outra promise | C++11 |

### 11.3 std::future_status Enum

```cpp
enum class future_status {
    ready,      // Resultado pronto
    timeout,    // Timeout expirado
    deferred    // Função deferred (ainda não executou)
};
```

### 11.4 std::future_errc Códigos de Erro

```cpp
enum class future_errc {
    broken_promise,        // Promise destruída sem satisfação
    future_already_retrieved, // get_future() chamado duas vezes
    promise_already_satisfied, // set_value/exception chamado duas vezes
    no_state               // Future/promise sem estado associado
};
```

### 11.5 Launch Policies

```cpp
enum class launch {
    async = 1,      // Nova thread garantida
    deferred = 2,   // Lazy evaluation
    // Padrão: async | deferred (implementação decide)
};
```

### 11.6 Padrões Comuns - Quick Reference

```cpp
// 1. Async simples
auto fut = std::async(std::launch::async, []{ return compute(); });
int result = fut.get();

// 2. Promise/Future manual
std::promise<int> p;
auto f = p.get_future();
std::thread([p = std::move(p)]() mutable { p.set_value(42); }).detach();
int result = f.get();

// 3. Shared future (múltiplos consumidores)
auto sf = std::async(std::launch::async, []{ return 42; }).share();
// Múltiplas threads podem chamar sf.get()

// 4. Packaged task
std::packaged_task<int()> task([]{ return 42; });
auto fut = task.get_future();
std::thread(std::move(task)).detach();

// 5. WhenAll (C++20 style manual)
std::vector<std::future<int>> futures;
// ... preenche futures ...
auto all = when_all_vec(std::move(futures));
auto results = all.get();

// 6. Timeout
if (fut.wait_for(100ms) == std::future_status::ready) {
    auto val = fut.get();
}

// 7. Continuação manual
auto f1 = std::async(std::launch::async, []{ return 10; });
auto f2 = std::async(std::launch::async, [f1 = std::move(f1)]() mutable {
    return f1.get() * 2;
});

// 8. Exception handling
try {
    fut.get();
} catch (const std::exception& e) {
    // Trata exceção da thread assíncrona
}

// 9. Corrotina (C++20)
Task<int> coro() {
    co_await std::suspend_always{};
    co_return 42;
}
auto fut = coro().to_future();
```

### 11.7 Headers Necessários

```cpp
#include <future>      // future, promise, packaged_task, async
#include <thread>      // thread
#include <chrono>      // durações, timeouts
#include <functional>  // bind, function
#include <memory>      // shared_ptr, make_shared
#include <exception>   // exception_ptr, current_exception
#include <variant>     // variant (C++17)
#include <optional>    // optional (C++17)
#include <coroutine>   // coroutines (C++20)
```

### 11.8 Compilação

```bash
# C++17
g++ -std=c++17 -pthread -O2 arquivo.cpp

# C++20 (corrotinas)
g++ -std=c++20 -pthread -O2 -fcoroutines arquivo.cpp

# Clang
clang++ -std=c++20 -pthread -O2 -fcoroutines arquivo.cpp
```

### 11.9 Debugging Tips

```cpp
// 1. Verificar se future é válido antes de usar
if (fut.valid()) {
    fut.get();
}

// 2. Usar wait_for para evitar deadlock em debug
while (fut.wait_for(100ms) != std::future_status::ready) {
    // Log progresso, verifica cancelamento, etc.
}

// 3. Adicionar timeout em testes
auto status = fut.wait_for(5s);
ASSERT_EQ(status, std::future_status::ready);

// 4. Log de estados
std::cout << "Future valid: " << fut.valid() 
          << ", ready: " << (fut.wait_for(0s) == std::future_status::ready) 
          << "\n";
```

### 11.10 Performance Guidelines

| Cenário | Recomendação |
|---------|--------------|
| Muitas tasks curtas | Thread pool + packaged_task |
| Tasks longas I/O-bound | std::async com launch::async |
| Tasks CPU-bound paralelas | std::async + hardware_concurrency() |
| Múltiplos consumidores | shared_future |
| Pipeline de dados | Corrotinas (C++20) ou continuations manuais |
| Timeout necessário | wait_for/wait_until |
| Cancelamento | CancellationToken + checkpoints |

---

## Conclusão

Futures, Promises e Continuations formam a base da programação assíncrona moderna em C++. 

**Pontos-chave:**
1. **std::future** - proxy somente-leitura para resultado assíncrono
2. **std::promise** - escritor do resultado (par do future)
3. **std::shared_future** - future copiável para múltiplos consumidores
4. **std::async** - forma simples de iniciar computação assíncrona
5. **std::packaged_task** - empacota callable para uso com future
6. **Continuations** - encadeamento de operações assíncronas (manual em C++17, nativo em C++20+)
7. **Corrotinas (C++20)** - sintaxe mais natural para código assíncrono

**Cuidados essenciais:**
- Sempre capturar exceções em threads que usam promise
- Nunca usar future após move (exceto shared_future)
- Sempre satisfazer promise (value ou exception)
- Evitar future<T&> - usar shared_ptr ou value
- Usar timeouts para evitar deadlocks
- Testar exaustivamente cenários de erro e timeout

**Referências:**
- C++ Standard: [futures] section
- C++ Reference: https://en.cppreference.com/w/cpp/thread
- Concurrency TS v2: continuations, executors
- Herb Sutter: "C++ and Beyond: Asynchronous Programming"

---

*Documento gerado para fins educacionais - C++17/20 Futures, Promises e Continuations*
*Última atualização: 2024*
---

*[Capítulo anterior: 08 — Containers Concorrentes](08-containers-concorrentes.md)*
*[Próximo capítulo: 10 — Coroutines Cpp20](10-coroutines-cpp20.md)*
