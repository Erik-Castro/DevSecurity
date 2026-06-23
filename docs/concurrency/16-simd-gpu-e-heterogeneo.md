# Capítulo 16 — SIMD, GPU e Computação Heterogênea

## Objetivos de Aprendizado

1. Utilizar intrinsics SIMD para processamento vetorial em CPU
2. Compreender os fundamentos de CUDA para GPU computing
3. Implementar kernels básicos de GPU com gerenciamento de memória
4. Otimizar transferências host-device e minimizar latência
5. Utilizar profiling tools para GPU (Nsight, compute-sanitizer)

---

## 1. SIMD Fundamentals

### 1.1 Registradores Vetoriais

```cpp
#include <immintrin.h>
#include <cstdint>
#include <iostream>

void demo_register_widths() {
    // SSE: 128-bit = 4 floats
    __m128 sse_vec = _mm_set_ps(1.0f, 2.0f, 3.0f, 4.0f);
    std::cout << "SSE: " << sizeof(__m128) << " bytes\n";
    
    // AVX2: 256-bit = 8 floats
    __m256 avx_vec = _mm256_set_ps(1.0f, 2.0f, 3.0f, 4.0f,
                                    5.0f, 6.0f, 7.0f, 8.0f);
    std::cout << "AVX2: " << sizeof(__m256) << " bytes\n";
    
    // AVX-512: 512-bit = 16 floats
    __m512 avx512_vec = _mm512_set_ps(1.0f, 2.0f, 3.0f, 4.0f,
                                       5.0f, 6.0f, 7.0f, 8.0f,
                                       9.0f, 10.0f, 11.0f, 12.0f,
                                       13.0f, 14.0f, 15.0f, 16.0f);
    std::cout << "AVX-512: " << sizeof(__m512) << " bytes\n";
}

int main() {
    demo_register_widths();
    return 0;
}
```

### 1.2 Operações Básicas

```cpp
#include <immintrin.h>
#include <iostream>
#include <cmath>

void vector_add_avx2(const float* a, const float* b, float* c, size_t n) {
    size_t i = 0;
    // Processa 8 floats por iteração
    for (; i + 8 <= n; i += 8) {
        __m256 va = _mm256_loadu_ps(a + i);
        __m256 vb = _mm256_loadu_ps(b + i);
        __m256 vc = _mm256_add_ps(va, vb);
        _mm256_storeu_ps(c + i, vc);
    }
    // Remainder
    for (; i < n; ++i) {
        c[i] = a[i] + b[i];
    }
}

void vector_mul_avx2(const float* a, const float* b, float* c, size_t n) {
    size_t i = 0;
    for (; i + 8 <= n; i += 8) {
        __m256 va = _mm256_loadu_ps(a + i);
        __m256 vb = _mm256_loadu_ps(b + i);
        __m256 vc = _mm256_mul_ps(va, vb);
        _mm256_storeu_ps(c + i, vc);
    }
    for (; i < n; ++i) {
        c[i] = a[i] * b[i];
    }
}

// FMA: a * b + c em uma instrução
void vector_fma_avx2(const float* a, const float* b, const float* c, float* d, size_t n) {
    size_t i = 0;
    for (; i + 8 <= n; i += 8) {
        __m256 va = _mm256_loadu_ps(a + i);
        __m256 vb = _mm256_loadu_ps(b + i);
        __m256 vc = _mm256_loadu_ps(c + i);
        __m256 vd = _mm256_fmadd_ps(va, vb, vc);  // a * b + c
        _mm256_storeu_ps(d + i, vd);
    }
    for (; i < n; ++i) {
        d[i] = a[i] * b[i] + c[i];
    }
}

// Redução horizontal (soma de todos os elementos)
float horizontal_sum_avx2(__m256 v) {
    __m128 vlow = _mm256_castps256_ps128(v);
    __m128 vhigh = _mm256_extractf128_ps(v, 1);
    __m128 vsum = _mm_add_ps(vlow, vhigh);
    __m128 vsum2 = _mm_add_ps(vsum, _mm_movehl_ps(vsum, vsum));
    __m128 vsum3 = _mm_add_ss(vsum2, _mm_shuffle_ps(vsum2, vsum2, 1));
    return _mm_cvtss_f32(vsum3);
}

float dot_product_avx2(const float* a, const float* b, size_t n) {
    __m256 sum_vec = _mm256_setzero_ps();
    size_t i = 0;
    
    for (; i + 8 <= n; i += 8) {
        __m256 va = _mm256_loadu_ps(a + i);
        __m256 vb = _mm256_loadu_ps(b + i);
        sum_vec = _mm256_fmadd_ps(va, vb, sum_vec);
    }
    
    float sum = horizontal_sum_avx2(sum_vec);
    for (; i < n; ++i) sum += a[i] * b[i];
    return sum;
}

int main() {
    const size_t N = 1000000;
    std::vector<float> a(N, 1.0f), b(N, 2.0f), c(N, 0.0f), d(N, 0.0f);
    
    vector_add_avx2(a.data(), b.data(), c.data(), N);
    vector_fma_avx2(a.data(), b.data(), c.data(), d.data(), N);
    
    float dot = dot_product_avx2(a.data(), b.data(), N);
    
    std::cout << "c[0] = " << c[0] << " (expected 3.0)\n";
    std::cout << "d[0] = " << d[0] << " (expected 3.0)\n";
    std::cout << "dot = " << dot << " (expected " << N << ")\n";
    
    return 0;
}
```

---

## 2. Auto-Vetorização

```cpp
#include <vector>
#include <cmath>
#include <numeric>
#include <iostream>

// GOOD: vetoriza automaticamente
void vectorizable(float* data, size_t n) {
    for (size_t i = 0; i < n; ++i) {
        data[i] = std::sqrt(data[i]) + 1.0f;
    }
}

// GOOD: reduction
float sum_array(const float* data, size_t n) {
    float sum = 0;
    for (size_t i = 0; i < n; ++i) {
        sum += data[i];
    }
    return sum;
}

// BAD: não vetoriza (dependência loop-carried)
void not_vectorizable(float* data, size_t n) {
    for (size_t i = 1; i < n; ++i) {
        data[i] = data[i-1] + 1.0f;
    }
}

// GCC flags: -O3 -march=native -ftree-vectorize -fopt-info-vec
```

---

## 3. CUDA Fundamentals

```cuda
#include <cuda_runtime.h>
#include <stdio.h>

__global__ void vector_add(const float* a, const float* b, float* c, int n) {
    int idx = blockIdx.x * blockDim.x + threadIdx.x;
    if (idx < n) {
        c[idx] = a[idx] + b[idx];
    }
}

void cuda_example() {
    int n = 1000000;
    size_t bytes = n * sizeof(float);
    
    float *h_a = new float[n];
    float *h_b = new float[n];
    float *h_c = new float[n];
    
    for (int i = 0; i < n; ++i) { h_a[i] = 1.0f; h_b[i] = 2.0f; }
    
    float *d_a, *d_b, *d_c;
    cudaMalloc(&d_a, bytes);
    cudaMalloc(&d_b, bytes);
    cudaMalloc(&d_c, bytes);
    
    cudaMemcpy(d_a, h_a, bytes, cudaMemcpyHostToDevice);
    cudaMemcpy(d_b, h_b, bytes, cudaMemcpyHostToDevice);
    
    int block_size = 256;
    int grid_size = (n + block_size - 1) / block_size;
    vector_add<<<grid_size, block_size>>>(d_a, d_b, d_c, n);
    
    cudaMemcpy(h_c, d_c, bytes, cudaMemcpyDeviceToHost);
    printf("c[0] = %f (expected 3.0)\n", h_c[0]);
    
    delete[] h_a; delete[] h_b; delete[] h_c;
    cudaFree(d_a); cudaFree(d_b); cudaFree(d_c);
}

int main() {
    cuda_example();
    return 0;
}
```

---

## 4. Shared Memory e Sincronização

```cuda
__global__ void reduce_sum(const float* input, float* output, int n) {
    extern __shared__ float sdata[];
    unsigned int tid = threadIdx.x;
    unsigned int i = blockIdx.x * blockDim.x * 2 + threadIdx.x;
    
    float val = 0;
    if (i < n) val = input[i];
    if (i + blockDim.x < n) val += input[i + blockDim.x];
    
    sdata[tid] = val;
    __syncthreads();
    
    for (unsigned int s = blockDim.x / 2; s > 32; s >>= 1) {
        if (tid < s) sdata[tid] += sdata[tid + s];
        __syncthreads();
    }
    
    if (tid < 32) {
        volatile float* vdata = sdata;
        vdata[tid] += vdata[tid + 32];
        vdata[tid] += vdata[tid + 16];
        vdata[tid] += vdata[tid + 8];
        vdata[tid] += vdata[tid + 4];
        vdata[tid] += vdata[tid + 2];
        vdata[tid] += vdata[tid + 1];
    }
    
    if (tid == 0) output[blockIdx.x] = sdata[0];
}
```

---

## 5. Memory Management CUDA

```cuda
void memory_patterns() {
    int n = 1000000;
    size_t bytes = n * sizeof(float);
    
    // Pattern 1: Regular allocation
    float *d1;
    cudaMalloc(&d1, bytes);
    
    // Pattern 2: Unified Memory
    float *d2;
    cudaMallocManaged(&d2, bytes);
    d2[0] = 1.0f;  // Direct access from CPU
    
    // Pattern 3: Pinned memory for async
    float *h_pinned;
    cudaMallocHost(&h_pinned, bytes);
    cudaMemcpyAsync(d1, h_pinned, bytes, cudaMemcpyHostToDevice);
    
    cudaFree(d1);
    cudaFree(d2);
    cudaFreeHost(h_pinned);
}
```

---

## 6. Profiling GPU

```bash
# Compute Sanitizer: memcheck, racecheck
compute-sanitizer --tool memcheck ./program
compute-sanitizer --tool racecheck ./program

# Nsight Compute: kernel analysis
ncu --metrics achieved_occupancy,sm_throughput,mem_throughput ./program

# Nsight Systems: timeline
nsys profile --trace=cuda,nvtx -o timeline ./program
```

---

## 7. Referências

- **CUDA Programming Guide** — docs.nvidia.com
- **Intel Intrinsics Guide** — software.intel.com
- **CUDA by Example** — Sanders & Kandrot
- **GPU Gems** — developer.nvidia.com
- **Programming Massively Parallel Processors** — Hwu, Kirk, Hajj
---

*[Capítulo anterior: 15 — Padroes Concorrencia](15-padroes-concorrencia.md)*
*[Próximo capítulo: 17 — Boas Praticas E Guia Referencia](17-boas-praticas-e-guia-referencia.md)*
