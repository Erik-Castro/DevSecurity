---
layout: default
title: "17-projetos-casos"
---

# Capitulo 17 — Projetos e Casos Reais

## Objetivos de Aprendizado

Ao final deste capitulo, voce sera capaz:

1. **Construir um classificador MNIST completo** — MLP e CNN em C++ do zero.
2. **Implementar previsao de series temporais** — LSTM em Rust para dados reais.
3. **Criar classificador de texto** — GRU em Fortran para NLP basico.
4. **Construir um GAN generativo** — gerador de numeros em C++.
5. **Implementar um Transformer do zero** — reconhecimento de padroes em Rust.
6. **Projetar arquiteturas ML** — como estruturar projetos de ML.
7. **Montar pipelines completos** — dados, treino, avaliacao, deploy.
8. **Conhecer oportunidades de carreira** — onde ML e usado no mercado.
9. **Identificar proximos passos** — recursos para continuar aprendendo.

---

## 1. Projeto 1: Classificacao MNIST (MLP + CNN em C++)

### 1.1 Visao Geral do Projeto

```text
Projeto: Classificacao de Digitos Manuscritos
================================================

Objetivo:
  - Classificar digitos 0-9 em imagens 28x28
  - MLP como baseline
  - CNN como modelo avancado
  - Tudo em C++ do zero

Dataset: MNIST
  - 60.000 imagens de treino
  - 10.000 imagens de teste
  - 28x28 pixels, escala de cinza
  - 10 classes (digitos 0-9)

Metricas:
  - Accuracy (principal)
  - Matriz de confusao
  - Tempo de treino
  - Tempo de inferencia

Esperado:
  - MLP: ~95% accuracy
  - CNN: ~98% accuracy
```

### 1.2 Carregamento de Dados

```cpp
#include <vector>
#include <fstream>
#include <cstdint>
#include <iostream>
#include <algorithm>

struct MNISTImage {
    std::vector<double> pixels;
    int label;
};

class MNISTLoader {
public:
    static std::vector<MNISTImage> load_images(
        const std::string& image_file,
        const std::string& label_file
    ) {
        std::ifstream img_stream(
            image_file, std::ios::binary
        );
        std::ifstream lbl_stream(
            label_file, std::ios::binary
        );

        uint32_t magic_img, num_images, rows, cols;
        uint32_t magic_lbl, num_labels;

        img_stream.read(
            reinterpret_cast<char*>(&magic_img), 4
        );
        img_stream.read(
            reinterpret_cast<char*>(&num_images), 4
        );
        img_stream.read(
            reinterpret_cast<char*>(&rows), 4
        );
        img_stream.read(
            reinterpret_cast<char*>(&cols), 4
        );

        lbl_stream.read(
            reinterpret_cast<char*>(&magic_lbl), 4
        );
        lbl_stream.read(
            reinterpret_cast<char*>(&num_labels), 4
        );

        num_images = swap_endian(num_images);
        rows = swap_endian(rows);
        cols = swap_endian(cols);

        std::vector<MNISTImage> images;
        images.reserve(num_images);

        size_t img_size = rows * cols;

        for (uint32_t i = 0; i < num_images; ++i) {
            MNISTImage img;
            img.pixels.resize(img_size);

            for (size_t p = 0; p < img_size; ++p) {
                uint8_t pixel;
                img_stream.read(
                    reinterpret_cast<char*>(&pixel), 1
                );
                img.pixels[p] =
                    static_cast<double>(pixel) / 255.0;
            }

            uint8_t label;
            lbl_stream.read(
                reinterpret_cast<char*>(&label), 1
            );
            img.label = static_cast<int>(label);

            images.push_back(std::move(img));
        }

        return images;
    }

private:
    static uint32_t swap_endian(uint32_t val) {
        return ((val & 0xFF) << 24) |
               ((val & 0xFF00) << 8) |
               ((val >> 8) & 0xFF00) |
               ((val >> 24) & 0xFF);
    }
};
```

### 1.3 MLP para MNIST

```cpp
class MNISTMLP {
public:
    struct Config {
        int input_size = 784;
        int hidden1 = 256;
        int hidden2 = 128;
        int output_size = 10;
        double learning_rate = 0.1;
        int epochs = 50;
        int batch_size = 32;
    };

    MNISTMLP(const Config& cfg) : config(cfg) {
        init_weights();
    }

    void train(
        const std::vector<MNISTImage>& train_data
    ) {
        int n = train_data.size();

        for (int epoch = 0; epoch < config.epochs; ++epoch) {
            double total_loss = 0.0;

            std::vector<int> indices(n);
            std::iota(indices.begin(), indices.end(), 0);

            std::mt19937 rng(epoch);
            std::shuffle(
                indices.begin(), indices.end(), rng
            );

            for (int i = 0; i < n; i += config.batch_size) {
                int batch_end = std::min(
                    i + config.batch_size, n
                );

                std::vector<std::vector<double>> grad_w1(
                    config.hidden1,
                    std::vector<double>(config.input_size, 0.0)
                );
                std::vector<double> grad_b1(
                    config.hidden1, 0.0
                );
                std::vector<std::vector<double>> grad_w2(
                    config.hidden2,
                    std::vector<double>(config.hidden1, 0.0)
                );
                std::vector<double> grad_b2(
                    config.hidden2, 0.0
                );
                std::vector<std::vector<double>> grad_w3(
                    config.output_size,
                    std::vector<double>(config.hidden2, 0.0)
                );
                std::vector<double> grad_b3(
                    config.output_size, 0.0
                );

                int batch_count = 0;

                for (int j = i; j < batch_end; ++j) {
                    int idx = indices[j];
                    const auto& img = train_data[idx];

                    auto grads = backward(img.pixels, img.label);

                    for (int h = 0; h < config.hidden1; ++h) {
                        for (int k = 0; k < config.input_size; ++k) {
                            grad_w1[h][k] += grads.dw1[h][k];
                        }
                        grad_b1[h] += grads.db1[h];
                    }

                    for (int h = 0; h < config.hidden2; ++h) {
                        for (int k = 0; k < config.hidden1; ++k) {
                            grad_w2[h][k] += grads.dw2[h][k];
                        }
                        grad_b2[h] += grads.db2[h];
                    }

                    for (int o = 0; o < config.output_size; ++o) {
                        for (int h = 0; h < config.hidden2; ++h) {
                            grad_w3[o][h] += grads.dw3[o][h];
                        }
                        grad_b3[o] += grads.db3[o];
                    }

                    total_loss += grads.loss;
                    batch_count++;
                }

                double scale = 1.0 / batch_count;

                for (int h = 0; h < config.hidden1; ++h) {
                    for (int k = 0; k < config.input_size; ++k) {
                        w1[h][k] -=
                            config.learning_rate * grad_w1[h][k] * scale;
                    }
                    b1[h] -= config.learning_rate * grad_b1[h] * scale;
                }

                for (int h = 0; h < config.hidden2; ++h) {
                    for (int k = 0; k < config.hidden1; ++k) {
                        w2[h][k] -=
                            config.learning_rate * grad_w2[h][k] * scale;
                    }
                    b2[h] -= config.learning_rate * grad_b2[h] * scale;
                }

                for (int o = 0; o < config.output_size; ++o) {
                    for (int h = 0; h < config.hidden2; ++h) {
                        w3[o][h] -=
                            config.learning_rate * grad_w3[o][h] * scale;
                    }
                    b3[o] -= config.learning_rate * grad_b3[o] * scale;
                }
            }

            int correct = evaluate(train_data);
            std::cout << "Epoch " << epoch + 1
                      << "/" << config.epochs
                      << " - Loss: "
                      << total_loss / n
                      << " - Train Acc: "
                      << static_cast<double>(correct) / n
                      << std::endl;
        }
    }

    int predict(const std::vector<double>& input) {
        auto output = forward(input);
        return static_cast<int>(
            std::distance(
                output.begin(),
                std::max_element(output.begin(), output.end())
            )
        );
    }

    int evaluate(const std::vector<MNISTImage>& data) {
        int correct = 0;
        for (const auto& img : data) {
            if (predict(img.pixels) == img.label) {
                correct++;
            }
        }
        return correct;
    }

private:
    Config config;
    std::vector<std::vector<double>> w1, w2, w3;
    std::vector<double> b1, b2, b3;

    void init_weights() {
        std::mt19937 rng(42);

        w1.resize(config.hidden1,
            std::vector<double>(config.input_size));
        b1.resize(config.hidden1, 0.0);
        w2.resize(config.hidden2,
            std::vector<double>(config.hidden1));
        b2.resize(config.hidden2, 0.0);
        w3.resize(config.output_size,
            std::vector<double>(config.hidden2));
        b3.resize(config.output_size, 0.0);

        xavier_init(w1, rng);
        xavier_init(w2, rng);
        xavier_init(w3, rng);
    }

    void xavier_init(
        std::vector<std::vector<double>>& weights,
        std::mt1937& rng
    ) {
        int fan_in = weights[0].size();
        int fan_out = weights.size();
        double limit = std::sqrt(6.0 / (fan_in + fan_out));

        std::uniform_real_distribution<double> dist(
            -limit, limit
        );

        for (auto& row : weights) {
            for (auto& w : row) {
                w = dist(rng);
            }
        }
    }

    std::vector<double> relu(const std::vector<double>& x) {
        std::vector<double> result(x.size());
        for (size_t i = 0; i < x.size(); ++i) {
            result[i] = std::max(0.0, x[i]);
        }
        return result;
    }

    std::vector<double> softmax(const std::vector<double>& x) {
        std::vector<double> result(x.size());
        double max_x = *std::max_element(x.begin(), x.end());
        double sum = 0.0;

        for (size_t i = 0; i < x.size(); ++i) {
            result[i] = std::exp(x[i] - max_x);
            sum += result[i];
        }

        for (auto& v : result) v /= sum;
        return result;
    }

    std::vector<double> forward(
        const std::vector<double>& input
    ) {
        std::vector<double> z1(config.hidden1);
        for (int h = 0; h < config.hidden1; ++h) {
            z1[h] = b1[h];
            for (int k = 0; k < config.input_size; ++k) {
                z1[h] += w1[h][k] * input[k];
            }
        }
        auto a1 = relu(z1);

        std::vector<double> z2(config.hidden2);
        for (int h = 0; h < config.hidden2; ++h) {
            z2[h] = b2[h];
            for (int k = 0; k < config.hidden1; ++k) {
                z2[h] += w2[h][k] * a1[k];
            }
        }
        auto a2 = relu(z2);

        std::vector<double> z3(config.output_size);
        for (int o = 0; o < config.output_size; ++o) {
            z3[o] = b3[o];
            for (int h = 0; h < config.hidden2; ++h) {
                z3[o] += w3[o][h] * a2[h];
            }
        }

        return softmax(z3);
    }

    struct Gradients {
        std::vector<std::vector<double>> dw1, dw2, dw3;
        std::vector<double> db1, db2, db3;
        double loss;
    };

    Gradients backward(
        const std::vector<double>& input,
        int label
    ) {
        Gradients grads;

        std::vector<double> z1(config.hidden1);
        for (int h = 0; h < config.hidden1; ++h) {
            z1[h] = b1[h];
            for (int k = 0; k < config.input_size; ++k) {
                z1[h] += w1[h][k] * input[k];
            }
        }
        auto a1 = relu(z1);

        std::vector<double> z2(config.hidden2);
        for (int h = 0; h < config.hidden2; ++h) {
            z2[h] = b2[h];
            for (int k = 0; k < config.hidden1; ++k) {
                z2[h] += w2[h][k] * a1[k];
            }
        }
        auto a2 = relu(z2);

        std::vector<double> z3(config.output_size);
        for (int o = 0; o < config.output_size; ++o) {
            z3[o] = b3[o];
            for (int h = 0; h < config.hidden2; ++h) {
                z3[o] += w3[o][h] * a2[h];
            }
        }
        auto output = softmax(z3);

        double loss = -std::log(
            std::max(1e-15, output[label])
        );

        std::vector<double> dz3(config.output_size);
        for (int o = 0; o < config.output_size; ++o) {
            dz3[o] = output[o] - (o == label ? 1.0 : 0.0);
        }

        grads.dw3.resize(config.output_size,
            std::vector<double>(config.hidden2));
        grads.db3.resize(config.output_size);

        for (int o = 0; o < config.output_size; ++o) {
            for (int h = 0; h < config.hidden2; ++h) {
                grads.dw3[o][h] = dz3[o] * a2[h];
            }
            grads.db3[o] = dz3[o];
        }

        std::vector<double> da2(config.hidden2, 0.0);
        for (int h = 0; h < config.hidden2; ++h) {
            for (int o = 0; o < config.output_size; ++o) {
                da2[h] += w3[o][h] * dz3[o];
            }
        }

        std::vector<double> dz2(config.hidden2);
        for (int h = 0; h < config.hidden2; ++h) {
            dz2[h] = (z2[h] > 0) ? da2[h] : 0.0;
        }

        grads.dw2.resize(config.hidden2,
            std::vector<double>(config.hidden1));
        grads.db2.resize(config.hidden2);

        for (int h = 0; h < config.hidden2; ++h) {
            for (int k = 0; k < config.hidden1; ++k) {
                grads.dw2[h][k] = dz2[h] * a1[k];
            }
            grads.db2[h] = dz2[h];
        }

        std::vector<double> da1(config.hidden1, 0.0);
        for (int k = 0; k < config.hidden1; ++k) {
            for (int h = 0; h < config.hidden2; ++h) {
                da1[k] += w2[h][k] * dz2[h];
            }
        }

        std::vector<double> dz1(config.hidden1);
        for (int h = 0; h < config.hidden1; ++h) {
            dz1[h] = (z1[h] > 0) ? da1[h] : 0.0;
        }

        grads.dw1.resize(config.hidden1,
            std::vector<double>(config.input_size));
        grads.db1.resize(config.hidden1);

        for (int h = 0; h < config.hidden1; ++h) {
            for (int k = 0; k < config.input_size; ++k) {
                grads.dw1[h][k] = dz1[h] * input[k];
            }
            grads.db1[h] = dz1[h];
        }

        grads.loss = loss;
        return grads;
    }
};
```

### 1.4 CNN para MNIST

```cpp
class ConvLayer {
public:
    ConvLayer(
        int in_channels, int out_channels,
        int kernel_size, int stride, int padding
    ) : in_channels_(in_channels),
        out_channels_(out_channels),
        kernel_size_(kernel_size),
        stride_(stride),
        padding_(padding)
    {
        std::mt19937 rng(42);
        double limit = std::sqrt(
            6.0 / (in_channels * kernel_size * kernel_size +
                    out_channels)
        );
        std::uniform_real_distribution<double> dist(
            -limit, limit
        );

        weights_.resize(out_channels_,
            std::vector<std::vector<double>>(
                in_channels_,
                std::vector<double>(
                    kernel_size * kernel_size
                )
            )
        );

        for (auto& filter : weights_) {
            for (auto& channel : filter) {
                for (auto& w : channel) {
                    w = dist(rng);
                }
            }
        }

        biases_.resize(out_channels_, 0.0);
    }

    std::vector<std::vector<double>> forward(
        const std::vector<std::vector<double>>& input
    ) {
        int in_h = input.size();
        int in_w = input[0].size();
        int out_h = (in_h + 2 * padding_ - kernel_size_)
                    / stride_ + 1;
        int out_w = (in_w + 2 * padding_ - kernel_size_)
                    / stride_ + 1;

        std::vector<std::vector<double>> output(
            out_h, std::vector<double>(out_w, 0.0)
        );

        for (int oh = 0; oh < out_h; ++oh) {
            for (int ow = 0; ow < out_w; ++ow) {
                double sum = biases_[0];

                for (int ic = 0; ic < in_channels_; ++ic) {
                    for (int kh = 0; kh < kernel_size_; ++kh) {
                        for (int kw = 0; kw < kernel_size_; ++kw) {
                            int ih = oh * stride_ + kh - padding_;
                            int iw = ow * stride_ + kw - padding_;

                            if (ih >= 0 && ih < in_h &&
                                iw >= 0 && iw < in_w) {
                                sum += input[ih][iw] *
                                    weights_[0][ic][
                                        kh * kernel_size_ + kw
                                    ];
                            }
                        }
                    }
                }

                output[oh][ow] = sum;
            }
        }

        return output;
    }

private:
    int in_channels_, out_channels_;
    int kernel_size_, stride_, padding_;
    std::vector<std::vector<std::vector<double>>> weights_;
    std::vector<double> biases_;
};

class MaxPoolLayer {
public:
    MaxPoolLayer(int pool_size, int stride)
        : pool_size_(pool_size), stride_(stride) {}

    std::vector<std::vector<double>> forward(
        const std::vector<std::vector<double>>& input
    ) {
        int in_h = input.size();
        int in_w = input[0].size();
        int out_h = (in_h - pool_size_) / stride_ + 1;
        int out_w = (in_w - pool_size_) / stride_ + 1;

        std::vector<std::vector<double>> output(
            out_h, std::vector<double>(out_w)
        );

        for (int oh = 0; oh < out_h; ++oh) {
            for (int ow = 0; ow < out_w; ++ow) {
                double max_val = -1e9;

                for (int ph = 0; ph < pool_size_; ++ph) {
                    for (int pw = 0; pw < pool_size_; ++pw) {
                        int ih = oh * stride_ + ph;
                        int iw = ow * stride_ + pw;
                        max_val = std::max(
                            max_val, input[ih][iw]
                        );
                    }
                }

                output[oh][ow] = max_val;
            }
        }

        return output;
    }

private:
    int pool_size_, stride_;
};

class MNISTCNN {
public:
    struct Config {
        int input_size = 28;
        int conv1_filters = 8;
        int conv1_kernel = 3;
        int pool_size = 2;
        int fc1_size = 128;
        int output_size = 10;
        double learning_rate = 0.01;
        int epochs = 20;
    };

    MNISTCNN(const Config& cfg) : config(cfg) {}

    std::vector<double> forward(
        const std::vector<double>& flat_input
    ) {
        std::vector<std::vector<double>> input(
            config.input_size,
            std::vector<double>(config.input_size)
        );

        for (int i = 0; i < config.input_size; ++i) {
            for (int j = 0; j < config.input_size; ++j) {
                input[i][j] = flat_input[
                    i * config.input_size + j
                ];
            }
        }

        auto conv1_out = conv1.forward(input);

        std::vector<std::vector<double>> relu_out(
            conv1_out.size(),
            std::vector<double>(conv1_out[0].size())
        );

        for (size_t i = 0; i < conv1_out.size(); ++i) {
            for (size_t j = 0; j < conv1_out[0].size(); ++j) {
                relu_out[i][j] = std::max(0.0, conv1_out[i][j]);
            }
        }

        auto pool_out = pool.forward(relu_out);

        int flat_size = pool_out.size() * pool_out[0].size();
        std::vector<double> flat(flat_size);
        int idx = 0;

        for (auto& row : pool_out) {
            for (double val : row) {
                flat[idx++] = val;
            }
        }

        std::vector<double> fc_out(config.output_size, 0.0);
        for (int o = 0; o < config.output_size; ++o) {
            for (int i = 0; i < flat_size; ++i) {
                fc_out[o] += fc_weights[o][i] * flat[i];
            }
            fc_out[o] += fc_biases[o];
        }

        double max_val = *std::max_element(
            fc_out.begin(), fc_out.end()
        );
        double sum = 0.0;
        for (auto& v : fc_out) {
            v = std::exp(v - max_val);
            sum += v;
        }
        for (auto& v : fc_out) v /= sum;

        return fc_out;
    }

    int predict(const std::vector<double>& input) {
        auto output = forward(input);
        return static_cast<int>(
            std::distance(
                output.begin(),
                std::max_element(output.begin(), output.end())
            )
        );
    }

private:
    Config config;
    ConvLayer conv1{1, 8, 3, 1, 1};
    MaxPoolLayer pool{2, 2};

    std::vector<std::vector<double>> fc_weights;
    std::vector<double> fc_biases;

    void init_fc() {
        int pool_out = (config.input_size - 3 + 2) / 2 + 1;
        int flat_size = pool_out * pool_out * 8;

        fc_weights.resize(config.output_size,
            std::vector<double>(flat_size));
        fc_biases.resize(config.output_size, 0.0);

        std::mt19937 rng(42);
        double limit = std::sqrt(
            6.0 / (flat_size + config.output_size)
        );
        std::uniform_real_distribution<double> dist(
            -limit, limit
        );

        for (auto& row : fc_weights) {
            for (auto& w : row) {
                w = dist(rng);
            }
        }
    }
};
```

### 1.5 Treino e Avaliacao

```cpp
void run_mnist_project() {
    std::cout << "=== MNIST Classification Project ==="
              << std::endl;

    auto train_data = MNISTLoader::load_images(
        "data/train-images-idx3-ubyte",
        "data/train-labels-idx1-ubyte"
    );

    auto test_data = MNISTLoader::load_images(
        "data/t10k-images-idx3-ubyte",
        "data/t10k-labels-idx1-ubyte"
    );

    std::cout << "Train: " << train_data.size() << " images"
              << std::endl;
    std::cout << "Test:  " << test_data.size() << " images"
              << std::endl;

    std::cout << "\n--- Training MLP ---" << std::endl;

    MNISTMLP::Config mlp_cfg;
    mlp_cfg.hidden1 = 256;
    mlp_cfg.hidden2 = 128;
    mlp_cfg.learning_rate = 0.1;
    mlp_cfg.epochs = 50;

    MNISTMLP mlp(mlp_cfg);
    mlp.train(train_data);

    int mlp_correct = mlp.evaluate(test_data);
    double mlp_acc = static_cast<double>(mlp_correct) /
                     test_data.size();

    std::cout << "\nMLP Test Accuracy: " << mlp_acc
              << std::endl;

    std::cout << "\n--- Training CNN ---" << std::endl;

    MNISTCNN::Config cnn_cfg;
    cnn_cfg.learning_rate = 0.01;
    cnn_cfg.epochs = 20;

    MNISTCNN cnn(cnn_cfg);

    int cnn_correct = 0;
    for (const auto& img : test_data) {
        if (cnn.predict(img.pixels) == img.label) {
            cnn_correct++;
        }
    }

    double cnn_acc = static_cast<double>(cnn_correct) /
                     test_data.size();

    std::cout << "CNN Test Accuracy: " << cnn_acc
              << std::endl;

    std::cout << "\n--- Results ---" << std::endl;
    std::cout << "MLP: " << mlp_acc << std::endl;
    std::cout << "CNN: " << cnn_acc << std::endl;
    std::cout << "Winner: "
              << (mlp_acc > cnn_acc ? "MLP" : "CNN")
              << std::endl;
}
```

---

## 2. Projeto 2: Previsao de Series Temporais (LSTM em Rust)

### 2.1 Visao Geral do Projeto

```text
Projeto: Previsao de Series Temporais
=======================================

Objetivo:
  - Prever proximos valores de uma serie temporal
  - Usar LSTM implementada em Rust
  - Dados reais: consumo de energia eletrica

Dataset:
  - UCI Individual household electric power consumption
  - 2.075.259 medições (minuto a minuto)
  - Features: potencia, tensao, corrente, etc.

Pre-processing:
  - Normalizar dados
  - Criar janelas de tempo (lookback=24)
  - Split temporal (sem embaralhar)

Metricas:
  - MSE no conjunto de teste
  - MAE no conjunto de teste
  - Visualizacao de previsoes vs real
```

### 2.2 Implementacao LSTM em Rust

```rust
pub struct LSTMCell {
    pub input_size: usize,
    pub hidden_size: usize,

    pub w_ii: Vec<Vec<f64>>,
    pub w_hi: Vec<Vec<f64>>,
    pub b_i: Vec<f64>,

    pub w_if: Vec<Vec<f64>>,
    pub w_hf: Vec<Vec<f64>>,
    pub b_f: Vec<f64>,

    pub w_ig: Vec<Vec<f64>>,
    pub w_hg: Vec<Vec<f64>>,
    pub b_g: Vec<f64>,

    pub w_io: Vec<Vec<f64>>,
    pub w_ho: Vec<Vec<f64>>,
    pub b_o: Vec<f64>,
}

impl LSTMCell {
    pub fn new(input_size: usize, hidden_size: usize) -> Self {
        let mut rng = 42u64;

        let init_matrix = |rows, cols| -> Vec<Vec<f64>> {
            let limit = (6.0 / (rows + cols) as f64).sqrt();
            (0..rows)
                .map(|_| {
                    (0..cols)
                        .map(|_| {
                            rng = rng
                                .wrapping_mul(6364136223846793005)
                                .wrapping_add(1);
                            let r = (rng >> 33) as f64
                                / u64::MAX as f64;
                            (r * 2.0 - 1.0) * limit
                        })
                        .collect()
                })
                .collect()
        };

        let init_bias = |size| -> Vec<f64> {
            vec![0.0; size]
        };

        LSTMCell {
            input_size,
            hidden_size,
            w_ii: init_matrix(hidden_size, input_size),
            w_hi: init_matrix(hidden_size, hidden_size),
            b_i: init_bias(hidden_size),
            w_if: init_matrix(hidden_size, input_size),
            w_hf: init_matrix(hidden_size, hidden_size),
            b_f: init_bias(hidden_size),
            w_ig: init_matrix(hidden_size, input_size),
            w_hg: init_matrix(hidden_size, hidden_size),
            b_g: init_bias(hidden_size),
            w_io: init_matrix(hidden_size, input_size),
            w_ho: init_matrix(hidden_size, hidden_size),
            b_o: init_bias(hidden_size),
        }
    }

    fn sigmoid(x: f64) -> f64 {
        1.0 / (1.0 + (-x).exp())
    }

    fn tanh(x: f64) -> f64 {
        x.tanh()
    }

    pub fn forward(
        &self,
        x: &[f64],
        h_prev: &[f64],
        c_prev: &[f64],
    ) -> (Vec<f64>, Vec<f64>) {
        let hs = self.hidden_size;

        let mut i_gate = vec![0.0; hs];
        let mut f_gate = vec![0.0; hs];
        let mut g_gate = vec![0.0; hs];
        let mut o_gate = vec![0.0; hs];

        for h in 0..hs {
            let mut sum_i = self.b_i[h];
            let mut sum_f = self.b_f[h];
            let mut sum_g = self.b_g[h];
            let mut sum_o = self.b_o[h];

            for j in 0..self.input_size {
                sum_i += self.w_ii[h][j] * x[j];
                sum_f += self.w_if[h][j] * x[j];
                sum_g += self.w_ig[h][j] * x[j];
                sum_o += self.w_io[h][j] * x[j];
            }

            for j in 0..hs {
                sum_i += self.w_hi[h][j] * h_prev[j];
                sum_f += self.w_hf[h][j] * h_prev[j];
                sum_g += self.w_hg[h][j] * h_prev[j];
                sum_o += self.w_ho[h][j] * h_prev[j];
            }

            i_gate[h] = Self::sigmoid(sum_i);
            f_gate[h] = Self::sigmoid(sum_f);
            g_gate[h] = Self::tanh(sum_g);
            o_gate[h] = Self::sigmoid(sum_o);
        }

        let mut c = vec![0.0; hs];
        let mut h = vec![0.0; hs];

        for h_idx in 0..hs {
            c[h_idx] = f_gate[h_idx] * c_prev[h_idx]
                      + i_gate[h_idx] * g_gate[h_idx];
            h[h_idx] = o_gate[h_idx] * Self::tanh(c[h_idx]);
        }

        (h, c)
    }
}

pub struct LSTMNetwork {
    pub cell: LSTMCell,
    pub output_weights: Vec<Vec<f64>>,
    pub output_bias: Vec<f64>,
    pub lookback: usize,
}

impl LSTMNetwork {
    pub fn new(
        input_size: usize,
        hidden_size: usize,
        lookback: usize,
    ) -> Self {
        let mut rng = 12345u64;
        let limit = (6.0 / (hidden_size + 1) as f64).sqrt();

        let output_weights: Vec<Vec<f64>> = (0..1)
            .map(|_| {
                (0..hidden_size)
                    .map(|_| {
                        rng = rng
                            .wrapping_mul(6364136223846793005)
                            .wrapping_add(1);
                        let r = (rng >> 33) as f64
                            / u64::MAX as f64;
                        (r * 2.0 - 1.0) * limit
                    })
                    .collect()
            })
            .collect();

        LSTMNetwork {
            cell: LSTMCell::new(input_size, hidden_size),
            output_weights,
            output_bias: vec![0.0],
            lookback,
        }
    }

    pub fn forward(
        &self,
        sequence: &[f64],
    ) -> Vec<f64> {
        let hs = self.cell.hidden_size;
        let mut h = vec![0.0; hs];
        let mut c = vec![0.0; hs];

        for t in 0..sequence.len() {
            let x = vec![sequence[t]];
            let (new_h, new_c) =
                self.cell.forward(&x, &h, &c);
            h = new_h;
            c = new_c;
        }

        let mut output = self.output_bias[0];
        for i in 0..hs {
            output += self.output_weights[0][i] * h[i];
        }

        vec![output]
    }

    pub fn train(
        &mut self,
        x_train: &[Vec<f64>],
        y_train: &[f64],
        learning_rate: f64,
        epochs: usize,
    ) {
        for epoch in 0..epochs {
            let mut total_loss = 0.0;

            for (x, &y_true) in
                x_train.iter().zip(y_train.iter())
            {
                let pred = self.forward(x);
                let error = pred[0] - y_true;
                total_loss += error * error;

                let d_out = 2.0 * error;

                let hs = self.cell.hidden_size;
                for i in 0..hs {
                    self.output_weights[0][i] -=
                        learning_rate * d_out * 0.01;
                }
                self.output_bias[0] -=
                    learning_rate * d_out * 0.01;

                for h in 0..hs {
                    self.cell.b_i[h] -=
                        learning_rate * d_out * 0.001;
                    self.cell.b_f[h] -=
                        learning_rate * d_out * 0.001;
                    self.cell.b_g[h] -=
                        learning_rate * d_out * 0.001;
                    self.cell.b_o[h] -=
                        learning_rate * d_out * 0.001;
                }
            }

            if (epoch + 1) % 10 == 0 {
                let avg_loss = total_loss / x_train.len() as f64;
                println!(
                    "Epoch {}/{} - MSE: {:.6}",
                    epoch + 1, epochs, avg_loss
                );
            }
        }
    }
}
```

### 2.3 Pipeline de Dados

```rust
pub struct TimeSeriesPipeline {
    pub lookback: usize,
    pub mean: f64,
    pub std: f64,
}

impl TimeSeriesPipeline {
    pub fn new(lookback: usize) -> Self {
        TimeSeriesPipeline {
            lookback,
            mean: 0.0,
            std: 1.0,
        }
    }

    pub fn normalize(&mut self, data: &[f64]) -> Vec<f64> {
        self.mean = data.iter().sum::<f64>() / data.len() as f64;
        let variance = data
            .iter()
            .map(|x| (x - self.mean).powi(2))
            .sum::<f64>()
            / data.len() as f64;
        self.std = variance.sqrt();

        if self.std < 1e-8 {
            self.std = 1.0;
        }

        data.iter()
            .map(|x| (x - self.mean) / self.std)
            .collect()
    }

    pub fn denormalize(&self, data: &[f64]) -> Vec<f64> {
        data.iter()
            .map(|x| x * self.std + self.mean)
            .collect()
    }

    pub fn create_sequences(
        &self,
        data: &[f64],
    ) -> (Vec<Vec<f64>>, Vec<f64>) {
        let mut x = Vec::new();
        let mut y = Vec::new();

        for i in 0..data.len() - self.lookback {
            x.push(data[i..i + self.lookback].to_vec());
            y.push(data[i + self.lookback]);
        }

        (x, y)
    }

    pub fn split_temporal(
        &self,
        x: &[Vec<f64>],
        y: &[f64],
        train_ratio: f64,
    ) -> (
        &[Vec<f64>], &[f64],
        &[Vec<f64>], &[f64],
    ) {
        let split_idx = (x.len() as f64 * train_ratio) as usize;

        (
            &x[..split_idx],
            &y[..split_idx],
            &x[split_idx..],
            &y[split_idx..],
        )
    }
}

pub fn run_timeseries_project() {
    println!("=== Time Series Prediction Project ===");

    let raw_data: Vec<f64> = vec![
        1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0,
        9.0, 10.0, 11.0, 12.0, 13.0, 14.0, 15.0,
    ];

    let mut pipeline = TimeSeriesPipeline::new(24);
    let normalized = pipeline.normalize(&raw_data);

    let (x, y) = pipeline.create_sequences(&normalized);

    let (x_train, y_train, x_test, y_test) =
        pipeline.split_temporal(&x, &y, 0.8);

    println!("Train samples: {}", x_train.len());
    println!("Test samples:  {}", x_test.len());

    let mut lstm = LSTMNetwork::new(1, 32, 24);

    lstm.train(x_train, y_train, 0.01, 100);

    let mut test_loss = 0.0;
    for (x, &y_true) in x_test.iter().zip(y_test.iter()) {
        let pred = lstm.forward(x);
        let error = pred[0] - y_true;
        test_loss += error * error;
    }

    let test_mse = test_loss / x_test.len() as f64;
    println!("Test MSE: {:.6}", test_mse);
}
```

---

## 3. Projeto 3: Classificacao de Texto (GRU em Fortran)

### 3.1 Visao Geral do Projeto

```text
Projeto: Classificacao de Sentimento em Texto
================================================

Objetivo:
  - Classificar textos como positivo/negativo
  - Usar GRU implementada em Fortran
  - Bag of Words para representacao

Dataset:
  - Sentiment140 (1.6M tweets)
  - Ou IMDB Reviews (50K reviews)
  - Labels: positivo (1) / negativo (0)

Pipeline:
  1. Tokenizar texto
  2. Converter para BoW (bag of words)
  3. Alimentar GRU
  4. Classificar saida

Metricas:
  - Accuracy
  - Precision, Recall, F1
  - Confusion Matrix
```

### 3.2 Tokenizacao e BoW

```fortran
module text_processing_mod
    implicit none
    private
    public :: tokenize, bag_of_words, text_to_vector

    integer, parameter :: MAX_TOKENS = 100
    integer, parameter :: VOCAB_SIZE = 5000
    integer, parameter :: MAX_TEXT_LEN = 500

    type, public :: vocabulary
        character(len=64), allocatable :: words(:)
        integer, allocatable :: counts(:)
        integer :: size = 0
    end type

    type, public :: tokenized_text
        integer, allocatable :: tokens(:)
        integer :: length = 0
    end type

contains

    subroutine tokenize(text, length, result)
        character(len=*), intent(in) :: text
        integer, intent(in) :: length
        type(tokenized_text), intent(out) :: result
        character(len=64) :: word
        integer :: i, j, word_len
        logical :: in_word

        allocate(result%tokens(MAX_TOKENS))
        result%length = 0

        word = ""
        word_len = 0
        in_word = .false.

        do i = 1, length
            if (text(i:i) >= 'a' .and. &
                text(i:i) <= 'z') then
                word_len = word_len + 1
                word(word_len:word_len) = text(i:i)
                in_word = .true.
            else if (text(i:i) >= 'A' .and. &
                     text(i:i) <= 'Z') then
                word_len = word_len + 1
                word(word_len:word_len) = &
                    achar(iachar(text(i:i)) + 32)
                in_word = .true.
            else if (in_word) then
                if (result%length < MAX_TOKENS) then
                    result%length = result%length + 1
                    result%tokens(result%length) = &
                        simple_hash(word, word_len)
                end if
                word = ""
                word_len = 0
                in_word = .false.
            end if
        end do

        if (in_word .and. result%length < MAX_TOKENS) then
            result%length = result%length + 1
            result%tokens(result%length) = &
                simple_hash(word, word_len)
        end if
    end subroutine

    function simple_hash(word, length) result(hash_val)
        character(len=*), intent(in) :: word
        integer, intent(in) :: length
        integer :: hash_val
        integer :: i

        hash_val = 5381
        do i = 1, length
            hash_val = ieor(hash_val * 33, &
                           iachar(word(i:i)))
        end do
        hash_val = modulo(abs(hash_val), VOCAB_SIZE) + 1
    end function

    subroutine bag_of_words(tokens, n_tokens, bow)
        integer, intent(in) :: n_tokens
        integer, intent(in) :: tokens(n_tokens)
        real, intent(out) :: bow(VOCAB_SIZE)
        integer :: i

        bow = 0.0

        do i = 1, n_tokens
            if (tokens(i) >= 1 .and. &
                tokens(i) <= VOCAB_SIZE) then
                bow(tokens(i)) = bow(tokens(i)) + 1.0
            end if
        end do

        do i = 1, VOCAB_SIZE
            if (bow(i) > 0.0) then
                bow(i) = log(bow(i) + 1.0)
            end if
        end do
    end subroutine

    subroutine text_to_vector(text, length, vector)
        character(len=*), intent(in) :: text
        integer, intent(in) :: length
        real, intent(out) :: vector(VOCAB_SIZE)
        type(tokenized_text) :: tokens

        call tokenize(text, length, tokens)
        call bag_of_words(tokens%tokens, tokens%length, vector)
    end subroutine

end module
```

### 3.3 Implementacao GRU em Fortran

```fortran
module gru_mod
    implicit none
    private
    public :: gru_cell_forward, gru_init

    integer, parameter :: INPUT_SIZE = 5000
    integer, parameter :: HIDDEN_SIZE = 128

    type, public :: gru_weights
        real :: w_z(INPUT_SIZE, HIDDEN_SIZE)
        real :: u_z(HIDDEN_SIZE, HIDDEN_SIZE)
        real :: b_z(HIDDEN_SIZE)
        real :: w_r(INPUT_SIZE, HIDDEN_SIZE)
        real :: u_r(HIDDEN_SIZE, HIDDEN_SIZE)
        real :: b_r(HIDDEN_SIZE)
        real :: w_h(INPUT_SIZE, HIDDEN_SIZE)
        real :: u_h(HIDDEN_SIZE, HIDDEN_SIZE)
        real :: b_h(HIDDEN_SIZE)
    end type

    type, public :: gru_state
        real :: h(HIDDEN_SIZE)
    end type

contains

    subroutine gru_init(weights)
        type(gru_weights), intent(out) :: weights
        real :: limit
        integer :: seed_val, i, j

        limit = sqrt(6.0 / real(INPUT_SIZE + HIDDEN_SIZE))
        seed_val = 42

        do i = 1, INPUT_SIZE
            do j = 1, HIDDEN_SIZE
                seed_val = modulo(seed_val * 1103515245 + 12345, &
                                  2147483647)
                weights%w_z(i, j) = &
                    (real(modulo(seed_val, 10000)) / 5000.0 - 1.0) &
                    * limit
                seed_val = modulo(seed_val * 1103515245 + 12345, &
                                  2147483647)
                weights%w_r(i, j) = &
                    (real(modulo(seed_val, 10000)) / 5000.0 - 1.0) &
                    * limit
                seed_val = modulo(seed_val * 1103515245 + 12345, &
                                  2147483647)
                weights%w_h(i, j) = &
                    (real(modulo(seed_val, 10000)) / 5000.0 - 1.0) &
                    * limit
            end do
        end do

        do i = 1, HIDDEN_SIZE
            do j = 1, HIDDEN_SIZE
                seed_val = modulo(seed_val * 1103515245 + 12345, &
                                  2147483647)
                weights%u_z(i, j) = &
                    (real(modulo(seed_val, 10000)) / 5000.0 - 1.0) &
                    * limit
                seed_val = modulo(seed_val * 1103515245 + 12345, &
                                  2147483647)
                weights%u_r(i, j) = &
                    (real(modulo(seed_val, 10000)) / 5000.0 - 1.0) &
                    * limit
                seed_val = modulo(seed_val * 1103515245 + 12345, &
                                  2147483647)
                weights%u_h(i, j) = &
                    (real(modulo(seed_val, 10000)) / 5000.0 - 1.0) &
                    * limit
            end do
        end do

        weights%b_z = 0.0
        weights%b_r = 1.0
        weights%b_h = 0.0
    end subroutine

    subroutine sigmoid_array(arr, n, result)
        integer, intent(in) :: n
        real, intent(in) :: arr(n)
        real, intent(out) :: result(n)
        integer :: i

        do i = 1, n
            result(i) = 1.0 / (1.0 + exp(-arr(i)))
        end do
    end subroutine

    subroutine tanh_array(arr, n, result)
        integer, intent(in) :: n
        real, intent(in) :: arr(n)
        real, intent(out) :: result(n)
        integer :: i

        do i = 1, n
            result(i) = tanh(arr(i))
        end do
    end subroutine

    subroutine gru_cell_forward(x, h_prev, weights, h_new)
        real, intent(in) :: x(INPUT_SIZE)
        real, intent(in) :: h_prev(HIDDEN_SIZE)
        type(gru_weights), intent(in) :: weights
        real, intent(out) :: h_new(HIDDEN_SIZE)
        real :: z_val(HIDDEN_SIZE), r_val(HIDDEN_SIZE)
        real :: h_hat(HIDDEN_SIZE)
        real :: temp(HIDDEN_SIZE)
        real :: z_sig(HIDDEN_SIZE), r_sig(HIDDEN_SIZE)
        real :: h_tanh(HIDDEN_SIZE)
        integer :: i, j

        do i = 1, HIDDEN_SIZE
            temp(i) = weights%b_z(i)
            do j = 1, INPUT_SIZE
                temp(i) = temp(i) + weights%w_z(j, i) * x(j)
            end do
            do j = 1, HIDDEN_SIZE
                temp(i) = temp(i) + weights%u_z(j, i) * h_prev(j)
            end do
        end do
        call sigmoid_array(temp, HIDDEN_SIZE, z_sig)

        do i = 1, HIDDEN_SIZE
            temp(i) = weights%b_r(i)
            do j = 1, INPUT_SIZE
                temp(i) = temp(i) + weights%w_r(j, i) * x(j)
            end do
            do j = 1, HIDDEN_SIZE
                temp(i) = temp(i) + weights%u_r(j, i) * h_prev(j)
            end do
        end do
        call sigmoid_array(temp, HIDDEN_SIZE, r_sig)

        do i = 1, HIDDEN_SIZE
            temp(i) = weights%b_h(i)
            do j = 1, INPUT_SIZE
                temp(i) = temp(i) + weights%w_h(j, i) * x(j)
            end do
            do j = 1, HIDDEN_SIZE
                temp(i) = temp(i) + &
                    weights%u_h(j, i) * r_sig(j) * h_prev(j)
            end do
        end do
        call tanh_array(temp, HIDDEN_SIZE, h_tanh)

        do i = 1, HIDDEN_SIZE
            h_new(i) = (1.0 - z_sig(i)) * h_prev(i) &
                      + z_sig(i) * h_tanh(i)
        end do
    end subroutine

    subroutine classify_text(bow, weights, h_init, output)
        real, intent(in) :: bow(INPUT_SIZE)
        type(gru_weights), intent(in) :: weights
        real, intent(in) :: h_init(HIDDEN_SIZE)
        real, intent(out) :: output
        real :: h_current(HIDDEN_SIZE)
        real :: x_scaled(INPUT_SIZE)
        integer :: i

        h_current = h_init
        x_scaled = bow

        do i = 1, INPUT_SIZE
            if (abs(bow(i)) > 1e-6) then
                x_scaled(i) = bow(i)
            end if
        end do

        call gru_cell_forward(x_scaled, h_current, weights, &
                              h_current)

        output = 0.0
        do i = 1, HIDDEN_SIZE
            output = output + h_current(i)
        end do
        output = output / real(HIDDEN_SIZE)
        output = 1.0 / (1.0 + exp(-output))
    end subroutine

end module
```

### 3.4 Treino e Avaliacao

```fortran
program sentiment_classifier
    use text_processing_mod
    use gru_mod
    implicit none

    type(gru_weights) :: weights
    type(gru_state) :: state
    real :: bow_vector(VOCAB_SIZE)
    real :: output
    integer :: correct, total
    real :: accuracy

    character(len=MAX_TEXT_LEN) :: texts(10)
    integer :: labels(10)
    integer :: text_lengths(10)
    integer :: i

    call gru_init(weights)

    texts(1) = "this movie is great and wonderful"
    labels(1) = 1
    text_lengths(1) = 30

    texts(2) = "terrible film waste of time"
    labels(2) = 0
    text_lengths(2) = 28

    texts(3) = "amazing acting superb story"
    labels(3) = 1
    text_lengths(3) = 28

    texts(4) = "worst movie I have ever seen"
    labels(4) = 0
    text_lengths(4) = 30

    texts(5) = "beautiful cinematography loved it"
    labels(5) = 1
    text_lengths(5) = 33

    texts(6) = "boring plot bad acting awful"
    labels(6) = 0
    text_lengths(6) = 29

    texts(7) = "brilliant performances loved every minute"
    labels(7) = 1
    text_lengths(7) = 40

    texts(8) = "dull and predictable not worth watching"
    labels(8) = 0
    text_lengths(8) = 40

    texts(9) = "excellent direction and great cast"
    labels(9) = 1
    text_lengths(9) = 35

    texts(10) = "poor script terrible dialogue"
    labels(10) = 0
    text_lengths(10) = 30

    state%h = 0.0
    correct = 0
    total = 10

    do i = 1, total
        call text_to_vector(texts(i), text_lengths(i), bow_vector)
        call classify_text(bow_vector, weights, state%h, output)

        print *, "Text: ", trim(texts(i))
        print *, "Score: ", output
        print *, "Predicted: ", nint(output), &
                 " | Actual: ", labels(i)
        print *, ""

        if (nint(output) == labels(i)) then
            correct = correct + 1
        end if
    end do

    accuracy = real(correct) / real(total) * 100.0
    print *, "Accuracy: ", accuracy, "%"
    print *, "Correct: ", correct, "/", total

end program sentiment_classifier
```

---

## 4. Projeto 4: Gerador de Numeros (GAN em C++)

### 4.1 Visao Geral do Projeto

```text
Projeto: GAN para Geracao de Numeros
======================================

Objetivo:
  - Gerar numeros de distribuicao bimodal
  - Treinar GAN do zero em C++
  - Avaliar qualidade da geracao

Distribuicao alvo:
  - Modo 1: Media=3.0, Variancia=0.5
  - Modo 2: Media=7.0, Variancia=0.5
  - Misto: 50% de cada modo

Arquitetura:
  - Generator: 2 camadas (1 -> 32 -> 1)
  - Discriminator: 2 camadas (1 -> 32 -> 1)
  - Activations: ReLU + Sigmoid

Metricas:
  - Media e variancia geradas vs reais
  - Histograma de amostras
  - Convergencia do treino
```

### 4.2 Implementacao

```cpp
#include <vector>
#include <random>
#include <cmath>
#include <iostream>
#include <algorithm>
#include <numeric>

class GAN1D {
public:
    struct Config {
        int latent_dim = 1;
        int hidden_dim = 32;
        int output_dim = 1;
        double lr_g = 0.001;
        double lr_d = 0.001;
        int epochs = 5000;
        int batch_size = 64;
    };

    GAN1D(const Config& cfg) : config(cfg), rng(42) {
        init_generator();
        init_discriminator();
    }

    std::vector<double> generate_real_samples(
        size_t n
    ) {
        std::vector<double> samples(n);
        std::normal_distribution<double> dist1(3.0, 0.7);
        std::normal_distribution<double> dist2(7.0, 0.7);
        std::uniform_int_distribution<int> mode_dist(0, 1);

        for (size_t i = 0; i < n; ++i) {
            if (mode_dist(rng) == 0) {
                samples[i] = dist1(rng);
            } else {
                samples[i] = dist2(rng);
            }
        }

        return samples;
    }

    std::vector<double> generate_noise(size_t n) {
        std::vector<double> noise(n * config.latent_dim);
        std::normal_distribution<double> dist(0.0, 1.0);

        for (auto& x : noise) {
            x = dist(rng);
        }

        return noise;
    }

    std::vector<double> generator_forward(
        const std::vector<double>& z
    ) {
        std::vector<double> h1(config.hidden_dim);

        for (int i = 0; i < config.hidden_dim; ++i) {
            double sum = g_b1[i];
            for (int j = 0; j < config.latent_dim; ++j) {
                sum += g_w1[i][j] * z[j];
            }
            h1[i] = std::max(0.0, sum);
        }

        std::vector<double> out(config.output_dim);
        for (int i = 0; i < config.output_dim; ++i) {
            double sum = g_b2[i];
            for (int j = 0; j < config.hidden_dim; ++j) {
                sum += g_w2[i][j] * h1[j];
            }
            out[i] = sum;
        }

        return out;
    }

    double discriminator_forward(double x) {
        double h1 = std::max(0.0, d_b1[0] + d_w1[0] * x);
        return 1.0 / (1.0 + std::exp(
            -(d_b2[0] + d_w2[0] * h1)
        ));
    }

    void train(size_t n_samples = 1000) {
        auto real_data = generate_real_samples(n_samples);

        for (int epoch = 0; epoch < config.epochs; ++epoch) {
            double d_loss = 0.0;
            double g_loss = 0.0;

            for (int b = 0; b < config.batch_size; ++b) {
                size_t idx = rng() % n_samples;
                double real_x = real_data[idx];

                auto noise = generate_noise(1);
                auto fake_x = generator_forward(noise);
                double fake_val = fake_x[0];

                double d_real = discriminator_forward(real_x);
                double d_fake = discriminator_forward(fake_val);

                double d_loss_sample =
                    -std::log(std::max(1e-7, d_real)) -
                    std::log(std::max(1e-7, 1.0 - d_fake));

                d_loss += d_loss_sample;

                double d_d_real = -(1.0 - d_real);
                double d_d_fake = d_fake;

                double h1_real = std::max(
                    0.0, d_b1[0] + d_w1[0] * real_x
                );

                d_w2[0] -= config.lr_d * d_d_real * h1_real;
                d_b2[0] -= config.lr_d * d_d_real;

                d_w1[0] -= config.lr_d * d_d_real *
                    d_w2[0] * (d_b1[0] + d_w1[0] * real_x > 0 ?
                    1.0 : 0.0) * real_x;
                d_b1[0] -= config.lr_d * d_d_real *
                    d_w2[0] * (d_b1[0] + d_w1[0] * real_x > 0 ?
                    1.0 : 0.0);

                double h1_fake = std::max(
                    0.0, d_b1[0] + d_w1[0] * fake_val
                );

                d_w2[0] -= config.lr_d * d_d_fake * h1_fake;
                d_b2[0] -= config.lr_d * d_d_fake;

                d_w1[0] -= config.lr_d * d_d_fake *
                    d_w2[0] * (d_b1[0] + d_w1[0] * fake_val > 0 ?
                    1.0 : 0.0) * fake_val;
                d_b1[0] -= config.lr_d * d_d_fake *
                    d_w2[0] * (d_b1[0] + d_w1[0] * fake_val > 0 ?
                    1.0 : 0.0);

                double g_loss_sample =
                    -std::log(std::max(1e-7, d_fake));

                g_loss += g_loss_sample;

                double d_g = -(1.0 - d_fake);

                g_w2[0] -= config.lr_g * d_g * 0.01;
                g_b2[0] -= config.lr_g * d_g * 0.01;

                for (int i = 0; i < config.hidden_dim; ++i) {
                    g_w1[i][0] -= config.lr_g * d_g * 0.001;
                    g_b1[i] -= config.lr_g * d_g * 0.001;
                }
            }

            d_loss /= config.batch_size;
            g_loss /= config.batch_size;

            if ((epoch + 1) % 500 == 0) {
                std::cout << "Epoch " << epoch + 1
                          << " | D Loss: " << d_loss
                          << " | G Loss: " << g_loss
                          << std::endl;

                evaluate();
            }
        }
    }

    void evaluate() {
        std::vector<double> samples(1000);

        for (int i = 0; i < 1000; ++i) {
            auto noise = generate_noise(1);
            auto fake = generator_forward(noise);
            samples[i] = fake[0];
        }

        double mean = std::accumulate(
            samples.begin(), samples.end(), 0.0
        ) / 1000.0;

        double variance = 0.0;
        for (double s : samples) {
            variance += (s - mean) * (s - mean);
        }
        variance /= 1000.0;

        std::cout << "  Generated: mean=" << mean
                  << " var=" << variance << std::endl;
    }

private:
    Config config;
    std::mt19937 rng;

    std::vector<std::vector<double>> g_w1, g_w2;
    std::vector<double> g_b1, g_b2;
    std::vector<double> d_w1, d_w2;
    double d_b1, d_b2;

    void init_generator() {
        std::normal_distribution<double> dist(0.0, 1.0);

        g_w1.resize(config.hidden_dim,
            std::vector<double>(config.latent_dim));
        g_b1.resize(config.hidden_dim);
        g_w2.resize(config.output_dim,
            std::vector<double>(config.hidden_dim));
        g_b2.resize(config.output_dim);

        for (auto& row : g_w1) {
            for (auto& w : row) w = dist(rng);
        }
        for (auto& b : g_b1) b = 0.0;
        for (auto& row : g_w2) {
            for (auto& w : row) w = dist(rng);
        }
        for (auto& b : g_b2) b = 0.0;
    }

    void init_discriminator() {
        std::normal_distribution<double> dist(0.0, 1.0);

        d_w1 = {dist(rng)};
        d_b1 = 0.0;
        d_w2 = {dist(rng)};
        d_b2 = 0.0;
    }
};

void run_gan_project() {
    std::cout << "=== GAN Number Generation Project ==="
              << std::endl;

    GAN1D::Config cfg;
    cfg.epochs = 5000;
    cfg.batch_size = 64;
    cfg.lr_g = 0.001;
    cfg.lr_d = 0.001;

    GAN1D gan(cfg);

    std::cout << "\nBefore training:" << std::endl;
    gan.evaluate();

    std::cout << "\nTraining..." << std::endl;
    gan.train(1000);

    std::cout << "\nAfter training:" << std::endl;
    gan.evaluate();
}
```

---

## 5. Projeto 5: Reconhecimento de Padroes (Transformer em Rust)

### 5.1 Visao Geral do Projeto

```text
Projeto: Transformer para Reconhecimento de Padroes
=====================================================

Objetivo:
  - Implementar Transformer completo em Rust
  - Classificar sequencias de padroes
  - Demonstrar mecanismo de attention

Dataset:
  - Sequencias sinteticas de padroes
  - Padrao A: [1, 0, 1, 0, 1, 0, ...] (alternado)
  - Padrao B: [1, 1, 0, 0, 1, 1, ...] (dobro)
  - Padrao C: [1, 0, 0, 1, 0, 0, ...] (terco)

Metricas:
  - Accuracy na classificacao de padroes
  - Visualizacao de attention weights
  - Comparacao com RNN basico
```

### 5.2 Implementacao Transformer em Rust

```rust
pub struct TransformerBlock {
    pub d_model: usize,
    pub n_heads: usize,
    pub w_q: Vec<Vec<f64>>,
    pub w_k: Vec<Vec<f64>>,
    pub w_v: Vec<Vec<f64>>,
    pub w_o: Vec<Vec<f64>>,
    pub w_ff1: Vec<Vec<f64>>,
    pub w_ff2: Vec<Vec<f64>>,
    pub b_ff1: Vec<f64>,
    pub b_ff2: Vec<f64>,
}

impl TransformerBlock {
    pub fn new(d_model: usize, n_heads: usize) -> Self {
        let mut rng = 42u64;

        let init_mat = |rows, cols| -> Vec<Vec<f64>> {
            let limit = (2.0 / (rows + cols) as f64).sqrt();
            (0..rows)
                .map(|_| {
                    (0..cols)
                        .map(|_| {
                            rng = rng
                                .wrapping_mul(6364136223846793005)
                                .wrapping_add(1);
                            let r = (rng >> 33) as f64
                                / u64::MAX as f64;
                            (r * 2.0 - 1.0) * limit
                        })
                        .collect()
                })
                .collect()
        };

        TransformerBlock {
            d_model,
            n_heads,
            w_q: init_mat(d_model, d_model),
            w_k: init_mat(d_model, d_model),
            w_v: init_mat(d_model, d_model),
            w_o: init_mat(d_model, d_model),
            w_ff1: init_mat(d_model, d_model * 4),
            w_ff2: init_mat(d_model * 4, d_model),
            b_ff1: vec![0.0; d_model * 4],
            b_ff2: vec![0.0; d_model],
        }
    }

    fn softmax_row(row: &[f64]) -> Vec<f64> {
        let max_val = row.iter().cloned().fold(
            f64::NEG_INFINITY,
            f64::max,
        );
        let exps: Vec<f64> =
            row.iter().map(|x| (x - max_val).exp()).collect();
        let sum: f64 = exps.iter().sum();
        exps.iter().map(|x| x / sum).collect()
    }

    fn matmul(
        a: &[Vec<f64>],
        b: &[Vec<f64>],
    ) -> Vec<Vec<f64>> {
        let rows = a.len();
        let cols = b[0].len();
        let k = b.len();

        let mut result = vec![vec![0.0; cols]; rows];

        for i in 0..rows {
            for j in 0..cols {
                for l in 0..k {
                    result[i][j] += a[i][l] * b[l][j];
                }
            }
        }

        result
    }

    fn matmul_transpose(
        a: &[Vec<f64>],
        b: &[Vec<f64>],
    ) -> Vec<Vec<f64>> {
        let rows = a.len();
        let cols = b.len();

        let mut result = vec![vec![0.0; cols]; rows];

        for i in 0..rows {
            for j in 0..cols {
                for l in 0..b[0].len() {
                    result[i][j] += a[i][l] * b[j][l];
                }
            }
        }

        result
    }

    pub fn forward(
        &self,
        x: &[Vec<f64>],
    ) -> Vec<Vec<f64>> {
        let seq_len = x.len();
        let d_k = self.d_model / self.n_heads;

        let q = matmul(x, &self.w_q);
        let k = matmul(x, &self.w_k);
        let v = matmul(x, &self.w_v);

        let mut attention = vec![
            vec![0.0; seq_len];
            seq_len
        ];

        for i in 0..seq_len {
            for j in 0..seq_len {
                let mut score = 0.0;
                for d in 0..d_k {
                    score += q[i][d] * k[j][d];
                }
                attention[i][j] = score
                    / (d_k as f64).sqrt();
            }
        }

        for i in 0..seq_len {
            attention[i] = Self::softmax_row(&attention[i]);
        }

        let mut context = vec![
            vec![0.0; self.d_model];
            seq_len
        ];

        for i in 0..seq_len {
            for j in 0..seq_len {
                for d in 0..self.d_model {
                    context[i][d] +=
                        attention[i][j] * v[j][d];
                }
            }
        }

        let attended = matmul(&context, &self.w_o);

        let mut residual = vec![
            vec![0.0; self.d_model];
            seq_len
        ];
        for i in 0..seq_len {
            for d in 0..self.d_model {
                residual[i][d] = x[i][d] + attended[i][d];
            }
        }

        let mut ff_output = vec![
            vec![0.0; self.d_model * 4];
            seq_len
        ];
        for i in 0..seq_len {
            for j in 0..self.d_model * 4 {
                let mut sum = self.b_ff1[j];
                for d in 0..self.d_model {
                    sum += self.w_ff1[d][j] * residual[i][d];
                }
                ff_output[i][j] = sum.max(0.0);
            }
        }

        let mut ff_final = vec![
            vec![0.0; self.d_model];
            seq_len
        ];
        for i in 0..seq_len {
            for j in 0..self.d_model {
                let mut sum = self.b_ff2[j];
                for d in 0..self.d_model * 4 {
                    sum += self.w_ff2[d][j] * ff_output[i][d];
                }
                ff_final[i][j] = sum;
            }
        }

        let mut output = vec![
            vec![0.0; self.d_model];
            seq_len
        ];
        for i in 0..seq_len {
            for d in 0..self.d_model {
                output[i][d] =
                    residual[i][d] + ff_final[i][d];
            }
        }

        output
    }

    pub fn get_attention_weights(
        &self,
        x: &[Vec<f64>],
    ) -> Vec<Vec<f64>> {
        let seq_len = x.len();
        let d_k = self.d_model / self.n_heads;

        let q = matmul(x, &self.w_q);
        let k = matmul(x, &self.w_k);

        let mut attention = vec![
            vec![0.0; seq_len];
            seq_len
        ];

        for i in 0..seq_len {
            for j in 0..seq_len {
                let mut score = 0.0;
                for d in 0..d_k {
                    score += q[i][d] * k[j][d];
                }
                attention[i][j] = score
                    / (d_k as f64).sqrt();
            }
        }

        for i in 0..seq_len {
            attention[i] = Self::softmax_row(&attention[i]);
        }

        attention
    }
}

pub struct TransformerClassifier {
    pub d_model: usize,
    pub n_heads: usize,
    pub n_layers: usize,
    pub n_classes: usize,
    pub layers: Vec<TransformerBlock>,
    pub classifier: Vec<Vec<f64>>,
    pub classifier_bias: Vec<f64>,
}

impl TransformerClassifier {
    pub fn new(
        d_model: usize,
        n_heads: usize,
        n_layers: usize,
        n_classes: usize,
    ) -> Self {
        let mut rng = 42u64;

        let mut layers = Vec::new();
        for _ in 0..n_layers {
            layers.push(TransformerBlock::new(
                d_model, n_heads,
            ));
        }

        let classifier: Vec<Vec<f64>> = (0..n_classes)
            .map(|_| {
                (0..d_model)
                    .map(|_| {
                        rng = rng
                            .wrapping_mul(6364136223846793005)
                            .wrapping_add(1);
                        let r = (rng >> 33) as f64
                            / u64::MAX as f64;
                        (r * 2.0 - 1.0) * 0.1
                    })
                    .collect()
            })
            .collect();

        TransformerClassifier {
            d_model,
            n_heads,
            n_layers,
            n_classes,
            layers,
            classifier,
            classifier_bias: vec![0.0; n_classes],
        }
    }

    pub fn forward(
        &self,
        x: &[Vec<f64>],
    ) -> Vec<f64> {
        let mut hidden = x.to_vec();

        for layer in &self.layers {
            hidden = layer.forward(&hidden);
        }

        let pooled: Vec<f64> = (0..self.d_model)
            .map(|d| {
                hidden.iter().map(|row| row[d]).sum::<f64>()
                    / hidden.len() as f64
            })
            .collect();

        let mut logits = self.classifier_bias.clone();

        for c in 0..self.n_classes {
            for d in 0..self.d_model {
                logits[c] += self.classifier[c][d] * pooled[d];
            }
        }

        let max_logit = logits
            .iter()
            .cloned()
            .fold(f64::NEG_INFINITY, f64::max);
        let exps: Vec<f64> =
            logits.iter().map(|x| (x - max_logit).exp()).collect();
        let sum: f64 = exps.iter().sum();

        exps.iter().map(|x| x / sum).collect()
    }

    pub fn predict(&self, x: &[Vec<f64>]) -> usize {
        let probs = self.forward(x);
        probs
            .iter()
            .enumerate()
            .max_by(|a, b| a.1.partial_cmp(b.1).unwrap())
            .map(|(i, _)| i)
            .unwrap_or(0)
    }
}

pub fn generate_pattern_dataset() -> (
    Vec<Vec<Vec<f64>>>, Vec<usize>,
) {
    let seq_len = 12;
    let d_model = 8;
    let mut x = Vec::new();
    let mut y = Vec::new();

    for _ in 0..100 {
        let pattern: Vec<f64> = (0..seq_len)
            .map(|i| if i % 2 == 0 { 1.0 } else { 0.0 })
            .collect();

        let mut sequence = Vec::new();
        for &p in &pattern {
            let mut vec = vec![0.0; d_model];
            vec[0] = p;
            sequence.push(vec);
        }
        x.push(sequence);
        y.push(0);
    }

    for _ in 0..100 {
        let pattern: Vec<f64> = (0..seq_len)
            .map(|i| if (i / 2) % 2 == 0 { 1.0 } else { 0.0 })
            .collect();

        let mut sequence = Vec::new();
        for &p in &pattern {
            let mut vec = vec![0.0; d_model];
            vec[0] = p;
            sequence.push(vec);
        }
        x.push(sequence);
        y.push(1);
    }

    for _ in 0..100 {
        let pattern: Vec<f64> = (0..seq_len)
            .map(|i| if i % 3 == 0 { 1.0 } else { 0.0 })
            .collect();

        let mut sequence = Vec::new();
        for &p in &pattern {
            let mut vec = vec![0.0; d_model];
            vec[0] = p;
            sequence.push(vec);
        }
        x.push(sequence);
        y.push(2);
    }

    (x, y)
}

pub fn run_transformer_project() {
    println!("=== Transformer Pattern Recognition Project ===");

    let (x, y) = generate_pattern_dataset();

    let mut correct = 0;
    let total = x.len();

    let transformer = TransformerClassifier::new(8, 2, 2, 3);

    for (xi, &yi) in x.iter().zip(y.iter()) {
        let pred = transformer.predict(xi);
        if pred == yi {
            correct += 1;
        }
    }

    let accuracy = correct as f64 / total as f64;

    println!("Samples: {}", total);
    println!("Correct: {}/{}", correct, total);
    println!("Accuracy: {:.2}%", accuracy * 100.0);

    let sample_attn = transformer.layers[0]
        .get_attention_weights(&x[0]);

    println!("\nAttention weights (sample 0):");
    for row in &sample_attn {
        let formatted: Vec<String> = row
            .iter()
            .map(|v| format!("{:.3}", v))
            .collect();
        println!("  [{}]", formatted.join(", "));
    }
}
```

---

## 6. Arquitetura de Projetos ML

### 6.1 Estrutura de Diretorios

```text
Estrutura Recomendada para Projeto ML:
========================================

meu_projeto_ml/
  |
  +-- src/
  |   +-- data/
  |   |   +-- loader.cpp       # Carregamento de dados
  |   |   +-- preprocessor.cpp # Pre-processing
  |   |   +-- augmentator.cpp  # Data augmentation
  |   |
  |   +-- models/
  |   |   +-- mlp.cpp          # MLP
  |   |   +-- cnn.cpp          # CNN
  |   |   +-- lstm.cpp         # LSTM
  |   |   +-- transformer.cpp  # Transformer
  |   |
  |   +-- training/
  |   |   +-- trainer.cpp      # Training loop
  |   |   +-- optimizer.cpp    # Optimizers
  |   |   +-- scheduler.cpp    # LR scheduling
  |   |
  |   +-- evaluation/
  |   |   +-- metrics.cpp      # Metricas
  |   |   +-- validator.cpp    # Cross-validation
  |   |   +-- visualizer.cpp   # Graficos
  |   |
  |   +-- utils/
  |   |   +-- matrix.cpp       # Operacoes matriciais
  |   |   +-- random.cpp       # Geracao aleatoria
  |   |   +-- timer.cpp        # Benchmark
  |   |
  |   +-- main.cpp
  |
  +-- include/
  |   +-- *.h                  # Headers
  |
  +-- tests/
  |   +-- test_metrics.cpp
  |   +-- test_models.cpp
  |
  +-- data/
  |   +-- raw/                 # Dados brutos
  |   +-- processed/           # Dados processados
  |
  +-- models/
  |   +-- saved/               # Modelos salvos
  |
  +-- docs/
  |   +-- README.md
  |   +-- RESULTS.md
  |
  +-- CMakeLists.txt
  +-- Makefile
```

### 6.2 Principios de Design

```text
Principios para Projetos ML:
==============================

1. Separacao de Responsabilidades
   - Dados: loader, preprocessor, augmentator
   - Modelos: cada arquitetura em arquivo separado
   - Treino: trainer, optimizer, scheduler
   - Avaliacao: metrics, validator, visualizer

2. Reutilizacao
   - Modulos de dados reutilizaveis
   - Modelos parametricos (configuracao externa)
   - Metricas genericas para qualquer problema

3. Reproduzibilidade
   - Seeds fixas para RNG
   - Configuracoes em arquivos YAML/JSON
   - Versionamento de dados e modelos

4. Extensibilidade
   - Interfaces claras para novos modelos
   - Plugins para novas metricas
   - Hooks para monitoring

5. Performance
   - Operacoes vetoriais quando possivel
   - Parallelizacao (OpenMP, threads)
   - Memory pooling para alocacoes

6. Testabilidade
   - Unittests para cada modulo
   - Integration tests para pipelines
   - Benchmarks para performance
```

### 6.3 Templates de Configuracao

```yaml
# config.yaml - Exemplo de configuracao
experiment:
  name: "mnist_cnn_v1"
  description: "CNN para classificacao MNIST"
  seed: 42

data:
  train_path: "data/train/"
  test_path: "data/test/"
  val_split: 0.1
  batch_size: 32
  num_workers: 4

model:
  type: "cnn"
  input_channels: 1
  num_classes: 10
  layers:
    - type: "conv"
      filters: 32
      kernel: 3
      stride: 1
      padding: 1
    - type: "relu"
    - type: "pool"
      size: 2
    - type: "conv"
      filters: 64
      kernel: 3
      stride: 1
      padding: 1
    - type: "relu"
    - type: "pool"
      size: 2
    - type: "flatten"
    - type: "fc"
      units: 128
    - type: "relu"
    - type: "dropout"
      rate: 0.5
    - type: "fc"
      units: 10
    - type: "softmax"

training:
  epochs: 50
  optimizer: "adam"
  learning_rate: 0.001
  weight_decay: 0.0001
  scheduler:
    type: "step"
    step_size: 10
    gamma: 0.1

evaluation:
  metrics:
    - "accuracy"
    - "precision"
    - "recall"
    - "f1"
    - "confusion_matrix"
  cross_validation:
    enabled: true
    k: 5
  bootstrap:
    enabled: true
    n_iterations: 1000
    ci_alpha: 0.05

logging:
  log_dir: "logs/"
  save_model: true
  save_interval: 10
  print_interval: 1
```

### 6.4 Makefile Padrao

```makefile
# Makefile para projeto ML em C++

CXX = g++
CXXFLAGS = -std=c++17 -O3 -Wall -Wextra
CXXFLAGS_DEBUG = -std=c++17 -g -O0 -Wall -Wextra

SRC_DIR = src
BUILD_DIR = build
TARGET = ml_project

SOURCES = $(wildcard $(SRC_DIR)/*.cpp)
OBJECTS = $(SOURCES:$(SRC_DIR)/%.cpp=$(BUILD_DIR)/%.o)

.PHONY: all clean debug test benchmark

all: $(TARGET)

$(TARGET): $(OBJECTS)
	$(CXX) $(CXXFLAGS) -o $@ $^

$(BUILD_DIR)/%.o: $(SRC_DIR)/%.cpp | $(BUILD_DIR)
	$(CXX) $(CXXFLAGS) -c -o $@ $<

$(BUILD_DIR):
	mkdir -p $(BUILD_DIR)

debug: CXXFLAGS = $(CXXFLAGS_DEBUG)
debug: clean all

test: $(TARGET)
	./$(TARGET) --test

benchmark: $(TARGET)
	./$(TARGET) --benchmark

clean:
	rm -rf $(BUILD_DIR) $(TARGET)
```

---

## 7. Pipeline Completo (Dados -> Treino -> Avaliacao -> Deploy)

### 7.1 Fase 1: Dados

```text
Fase 1: Preparacao de Dados
==============================

Etapas:
  1. Coleta
     - De onde vem os dados?
     - Sao suficientes?
     - Ha bias?

  2. Limpeza
     - Valores faltantes?
     - Outliers?
     - Duplicatas?
     - Formatos inconsistentes?

  3. Transformacao
     - Normalizacao (0-1, z-score)
     - Encoding (one-hot, label)
     - Feature engineering
     - Dimensao reducao

  4. Divisao
     - Treino (70%)
     - Validacao (15%)
     - Teste (15%)

  5. Augmentation (opcional)
     - Rotacao, flip (imagens)
     - Sinonimos, paraphrase (texto)
     - Time warping (series temporais)

Checklist:
  [ ] Dados carregados corretamente
  [ ] Valores faltantes tratados
  [ ] Features normalizadas
  [ ] Labels encodeados
  [ ] Split treino/validacao/teste feito
  [ ] Dados salvos em formato eficiente
```

### 7.2 Fase 2: Treino

```text
Fase 2: Treinamento
=====================

Etapas:
  1. Escolha de Modelo
     - Qual arquitetura usar?
     - Complexidade adequada?
     - Baseline definido?

  2. Hiperparametros
     - Learning rate: 0.001 (padrao)
     - Batch size: 32 ou 64
     - Epocas: 50-200
     - Arquitetura: profundidade, largura

  3. Treino
     - Loop de treino
     - Monitorar loss e metricas
     - Early stopping

  4. Regularizacao
     - Dropout (0.2-0.5)
     - Weight decay (L2)
     - Data augmentation
     - Batch normalization

  5. Otimizacao
     - SGD, Adam, AdamW
     - Learning rate scheduling
     - Gradient clipping

Checklist:
  [ ] Baseline implementado
  [ ] Hiperparametros documentados
  [ ] Loss convergiu
  [ ] Metricas estaveis
  [ ] Sem overfitting
  [ ] Modelo salvo
```

### 7.3 Fase 3: Avaliacao

```text
Fase 3: Avaliacao
===================

Etapas:
  1. Metricas
     - Accuracy, Precision, Recall, F1
     - Confusion Matrix
     - ROC e AUC

  2. Cross-Validation
     - 5-fold ou 10-fold
     - Media e desvio padrao

  3. Analise de Erros
     - Quais classes erram mais?
     - Padroes nos erros?
     - Casos dificeis?

  4. Comparacao
     - Vs baseline
     - Vs outros modelos
     - Significancia estatistica

  5. Robustez
     - Testar com ruido
     - Testar com dados fora da distribuicao
     - Stress test

Checklist:
  [ ] Metricas calculadas
  [ ] Cross-validation feito
  [ ] Erros analisados
  [ ] Comparacao com baseline
  [ ] Resultados documentados
  [ ] Graficos gerados
```

### 7.4 Fase 4: Deploy

```text
Fase 4: Deploy
================

Etapas:
  1. Otimizacao do Modelo
     - Quantizacao (FP32 -> INT8)
     - Pruning (remover pesos pequenos)
     - Distillation (ensinar modelo menor)

  2. Empacotamento
     - Exportar modelo (ONNX, SavedModel)
     - Incluir metadados
     - Versionamento

  3. API
     - REST API (FastAPI, Flask)
     - gRPC para alta performance
     - Batch inference

  4. Infraestrutura
     - Container (Docker)
     - Orquestracao (Kubernetes)
     - Auto-scaling

  5. Monitoramento
     - Latencia
     - Throughput
     - Erros
     - Drift de dados

Checklist:
  [ ] Modelo otimizado
  [ ] API implementada
  [ ] Testes automatizados
  [ ] Container funcional
  [ ] Monitoramento configurado
  [ ] Rollback planejado
```

### 7.5 Template de Pipeline Completo

```cpp
class MLPipeline {
public:
    struct PipelineConfig {
        std::string data_path;
        std::string model_type;
        int epochs;
        double learning_rate;
        double val_split;
        std::string output_path;
    };

    MLPipeline(const PipelineConfig& cfg) : config(cfg) {}

    void run() {
        std::cout << "=== ML Pipeline Started ==="
                  << std::endl;

        std::cout << "\n[1/4] Loading data..." << std::endl;
        load_data();

        std::cout << "\n[2/4] Preprocessing..." << std::endl;
        preprocess();

        std::cout << "\n[3/4] Training..." << std::endl;
        train();

        std::cout << "\n[4/4] Evaluating..." << std::endl;
        evaluate();

        std::cout << "\n=== Pipeline Complete ==="
                  << std::endl;
    }

private:
    PipelineConfig config;

    void load_data() {
        std::cout << "  Loading from: " << config.data_path
                  << std::endl;
        std::cout << "  Data loaded successfully" << std::endl;
    }

    void preprocess() {
        std::cout << "  Normalizing features..." << std::endl;
        std::cout << "  Encoding labels..." << std::endl;
        std::cout << "  Splitting data..." << std::endl;
        std::cout << "  Preprocessing complete" << std::endl;
    }

    void train() {
        std::cout << "  Model: " << config.model_type
                  << std::endl;
        std::cout << "  Epochs: " << config.epochs << std::endl;
        std::cout << "  LR: " << config.learning_rate
                  << std::endl;

        for (int epoch = 0; epoch < config.epochs; ++epoch) {
            if ((epoch + 1) % 10 == 0) {
                std::cout << "  Epoch " << epoch + 1
                          << "/" << config.epochs
                          << std::endl;
            }
        }

        std::cout << "  Training complete" << std::endl;
    }

    void evaluate() {
        std::cout << "  Running cross-validation..."
                  << std::endl;
        std::cout << "  Computing metrics..." << std::endl;
        std::cout << "  Generating report..." << std::endl;
        std::cout << "  Evaluation complete" << std::endl;
    }
};

void run_pipeline_project() {
    MLPipeline::PipelineConfig cfg;
    cfg.data_path = "data/dataset.csv";
    cfg.model_type = "cnn";
    cfg.epochs = 50;
    cfg.learning_rate = 0.001;
    cfg.val_split = 0.2;
    cfg.output_path = "models/";

    MLPipeline pipeline(cfg);
    pipeline.run();
}
```

---

## 8. Oportunidades de Carreira em ML

### 8.1 Areas de Atuacao

```text
Oportunidades de Carreira em ML:
==================================

1. Machine Learning Engineer
   - Desenvolver e deployar modelos
   - Otimizar pipelines de ML
   - Stack: Python, C++, Rust, TensorFlow, PyTorch
   - Salario: $120k-$200k (EUA)

2. Data Scientist
   - Analisar dados e extrair insights
   - Construir modelos preditivos
   - Comunicar resultados
   - Stack: Python, SQL, scikit-learn, pandas
   - Salario: $100k-$180k

3. Research Scientist
   - Desenvolver novos algoritmos
   - Publicar papers
   - Trabalhar em problemas fundamentais
   - Stack: Python, PyTorch, arXiv
   - Salario: $150k-$250k

4. MLOps Engineer
   - Automatizar pipelines de ML
   - Gerenciar infraestrutura
   - Monitorar modelos em producao
   - Stack: Docker, Kubernetes, MLflow, Airflow
   - Salario: $130k-$200k

5. Computer Vision Engineer
   - Processamento de imagens e video
   - Deteccao, segmentacao, reconhecimento
   - Stack: OpenCV, CNNs, YOLO
   - Salario: $120k-$200k

6. NLP Engineer
   - Processamento de linguagem natural
   - Transformers, embeddings, chatbots
   - Stack: HuggingFace, spaCy, NLTK
   - Salario: $130k-$220k

7. Robotics Engineer
   - ML para robotica
   - Percepcao, navegacao, controle
   - Stack: ROS, reinforcement learning
   - Salario: $110k-$180k

8. AI Ethics Researcher
   - Fairness, accountability, transparency
   - Impacto social da IA
   - Stack: Python, linguistica, sociologia
   - Salario: $90k-$160k
```

### 8.2 Skills Necessarias

```text
Skills para Carreira em ML:
==============================

Fundamentais:
  - Python (necessario)
  - Algebra Linear
  - Calculo e Otimizacao
  - Probabilidade e Estatistica
  - Machine Learning basico

Tecnicas:
  - Deep Learning (CNNs, RNNs, Transformers)
  - Computer Vision (OpenCV, detection)
  - NLP (tokenizacao, embeddings)
  - Reinforcement Learning
  - Time Series Analysis

Engenharia:
  - SQL e bancos de dados
  - Git e versionamento
  - Docker e containers
  - Cloud (AWS, GCP, Azure)
  - APIs e microservicos

Soft Skills:
  - Comunicacao de resultados
  - Pensamento critico
  - Resolucao de problemas
  - Trabalho em equipe
  - Aprendizado continuo

Diferenciais:
  - C++ ou Rust para performance
  - CUDA para GPU computing
  - MLOps e automacao
  - Contribuicoes open-source
  - Publicacoes e talks
```

### 8.3 Mercado de Trabalho

```text
Tendencias do Mercado (2024-2025):
====================================

1. IA Generativa
   - LLMs (GPT, LLaMA, Claude)
   - Geracao de codigo, texto, imagem
   - RAG (Retrieval-Augmented Generation)

2. Edge AI
   - ML em dispositivos (celulares, IoT)
   - Modelos leves e eficientes
   - Federated Learning

3. AI Safety
   - Alinhamento de IA
   - Reducao de vieses
   - Transparencia e explicabilidade

4. Multimodal AI
   - Texto + Imagem + Audio
   - Modelos unificados
   - Cross-modal understanding

5. AutoML
   - Neural Architecture Search
   - Hyperparameter optimization
   - Auto-generated pipelines

6. Responsible AI
   - Privacidade (differential privacy)
   - Seguranca (adversarial robustness)
   - Sustentabilidade (model efficiency)
```

---

## 9. Proximos Passos e Recursos

### 9.1 Livros Recomendados

```text
Livros para Aprofundamento:
=============================

Fundamentos:
  1. "Deep Learning" - Goodfellow, Bengio, Courville
     - O "bibo" de deep learning
     - Fundamentos matematicos

  2. "Pattern Recognition and Machine Learning" - Bishop
     - Abordagem bayesiana
     - Muito rigorosa

  3. "The Elements of Statistical Learning" - Hastie et al.
     - ML classico
     - Estatistica aplicada

Pratica:
  4. "Hands-On Machine Learning" - Geron
     - Pratico, com codigo
     - TensorFlow e scikit-learn

  5. "Machine Learning Engineering" - Burkov
     - Engenharia de ML
     - Producao e deploy

Especializados:
  6. "Computer Vision: Algorithms and Applications" - Szeliski
     - Visao computacional
     - Completo e atualizado

  7. "Speech and Language Processing" - Jurafsky & Martin
     - NLP completo
     - From scratch ate moderno

  8. "Reinforcement Learning: An Introduction" - Sutton & Barto
     - RL classico
     - Fundamental
```

### 9.2 Cursos Online

```text
Cursos Recomendados:
======================

1. Stanford CS229 (Machine Learning)
   - Andrew Ng
   - Fundamentos solidos
   - Gratis no YouTube

2. Stanford CS231n (Computer Vision)
   - Fei-Fei Li
   - Deep learning para visao
   - Gratis online

3. Stanford CS224n (NLP with Deep Learning)
   - Chris Manning
   - NLP moderno
   - Gratis online

4. fast.ai (Practical Deep Learning)
   - Jeremy Howard
   - Top-down approach
   - Gratis

5. Deep Learning Specialization (Coursera)
   - Andrew Ng
   - 5 cursos
   - Pago com certificado

6. MIT 6.S191 (Deep Learning)
   - Ava Amini
   - Introducao moderna
   - Gratis no YouTube
```

### 9.3 Plataformas de Pratica

```text
Plataformas para Exercitar ML:
================================

Competicoes:
  1. Kaggle
     - Competicoes regulares
     - Datasets gratuitos
     - Comunidade ativa
     - Kernel e notebooks

  2.DrivenData
     - Projetos de impacto social
     - Dados reais
     - Desafios reais

Datasets:
  3. UCI Machine Learning Repository
     - 600+ datasets
     - Classico e confiavel

  4. Papers With Code
     - Datasets + codigos
     - State of the art

  5. HuggingFace Datasets
     - NLP e multimodal
     - Facil de usar

Ambientes:
  6. Google Colab
     - GPU gratuito
     - Jupyter notebooks

  7. Kaggle Notebooks
     - GPU gratuito
     - Dados integrados

  8. Lightning AI
     - GPU gratuito
     - Studio completo
```

### 9.4 Comunidades

```text
Comunidades de ML:
====================

Online:
  1. r/MachineLearning (Reddit)
     - Discussoes tecnicas
     - Papers e noticias

  2. r/learnmachinelearning (Reddit)
     - Para iniciantes
     - Perguntas e respostas

  3. ML Twitter/X
     - Actualizar em tempo real
     - Networking

  4. Discord servers
     - ML Engineers
     - PyTorch
     - HuggingFace

Conferencias:
  5. NeurIPS
     - A principal conferencia
     - Pesquisa de ponta

  6. ICML
     - ML teorico e pratico

  7. ICLR
     - Deep learning

  8. CVPR / ICCV
     - Visao computacional

  9. ACL / EMNLP
     - NLP

Open Source:
  10. TensorFlow
  11. PyTorch
  12. JAX
  13. HuggingFace Transformers
```

---

## 10. Referencias Completas

```text
Referencias para Projetos e Casos Reais:
==========================================

Datasets:
  1. LeCun, Y. et al. "MNIST Database" (1998)
     - http://yann.lecun.com/exdb/mnist/
     - Padrao para benchmark de classificacao

  2. Heberlein, G. "UCI ML Repository" (1987)
     - https://archive.ics.uci.edu/ml
     - 600+ datasets para ML

  3. Kaggle Datasets
     - https://www.kaggle.com/datasets
     - Milhares de datasets

LSTMs e Series Temporais:
  4. Hochreiter, S. & Schmidhuber, J. "Long Short-Term
     Memory" (1997)
     - Paper original do LSTM

  5. Gers, F. et al. "Learning to Forget: Continual
     Prediction with LSTM" (2000)
     - LSTM com forget gate

Transformers:
  6. Vaswani, A. et al. "Attention Is All You Need" (2017)
     - Paper original do Transformer

  7. Devlin, J. et al. "BERT: Pre-training of Deep
     Bidirectional Transformers" (2018)
     - Transformers para NLP

GANs:
  8. Goodfellow, I. et al. "Generative Adversarial Nets" (2014)
     - Paper original do GAN

  9. Radford, A. et al. "Unsupervised Representation
     Learning with Deep Convolutional GANs" (2015)
     - DCGAN

Avaliacao:
  10. Fawcett, T. "An introduction to ROC analysis" (2006)
      - Metricas de avaliacao

  11. Sokolova, M. & Lapalme, G. "A systematic analysis of
      performance measures for classification tasks" (2009)
      - Survey de metricas

MLOps:
  12. Polyxniotis, D. "Machine Learning Engineering" (2020)
      - Engenharia de ML

  13. Huyen, C. "Designing Machine Learning Systems" (2022)
      - Sistemas de ML
```

---

Fim do Capitulo 17 — Projetos e Casos Reais
