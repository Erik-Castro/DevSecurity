# Capítulo 16 — SIMD, GPU e Computação Heterogênea

## Objetivos de Aprendizado

1. Utilizar intrinsics SIMD para processamento vetorial
2. Entender os fundamentos de CUDA/HIP para GPU computing
3. Implementar kernels básicos de GPU
4. Gerenciar memória entre host e device

---

## 1. SIMD Fundamentals

### 1.1 SSE/AVX Intrinsics

```cpp
#include <immintrin.h>
#include <vector>
#include <chrono>
#include <iostream>
#include <cmath>

// Versão escalar
void add_scalar(const float* a, const float* b, float* c, size_t n) {
    for (size_t i = 0; i < n; ++i) {
        c[i] = a[i] + b[i];
    }
}

// Versão SSE (128-bit, 4 floats)
void add_sse(const float* a, const float* b, float* c, size_t n) {
    size_t i = 0;
    for (; i + 4 <= n; i += 4) {
        __m128 va = _mm_loadu_ps(a + i);
        __m128 vb = _mm_loadu_ps(b + i);
        __m128 vc = _mm_add_ps(va, vb);
        _mm_storeu_ps(c + i, vc);
    }
    for (; i < n; ++i) {
        c[i] = a[i] + b[i];
    }
}

// Versão AVX2 (256-bit, 8 floats)
void add_avx2(const float* a, const float* b, float* c, size_t n) {
    size_t i = 0;
    for (; i + 8 <= n; i += 8) {
        __m256 va = _mm256_loadu_ps(a + i);
        __m256 vb = _mm256_loadu_ps(b + i);
        __m256 vc = _mm256_add_ps(va, vb);
        _mm256_storeu_ps(c + i, vc);
    }
    for (; i < n; ++i) {
        c[i] = a[i] + b[i];
    }
}

// Versão AVX-512 (512-bit, 16 floats)
void add_avx512(const float* a, const float* b, float* c, size_t n) {
    size_t i = 0;
    for (; i + 16 <= n; i += 16) {
        __m512 va = _mm512_loadu_ps(a + i);
        __m512 vb = _mm512_loadu_ps(b + i);
        __m512 vc = _mm512_add_ps(va, vb);
        _mm512_storeu_ps(c + i, vc);
    }
    for (; i < n; ++i) {
        c[i] = a[i] + b[i];
    }
}

// Benchmark
void benchmark() {
    const size_t N = 10000000;
    std::vector<float> a(N, 1.0f), b(N, 2.0f), c(N);
    
    auto bench = [&](auto func, const char* name) {
        auto start = std::chrono::high_resolution_clock::now();
        func(a.data(), b.data(), c.data(), N);
        auto end = std::chrono::high_resolution_clock::now();
        auto us = std::chrono::duration_cast<std::chrono::microseconds>(end - start).count();
        double bandwidth = (3.0 * N * sizeof(float)) / (us * 1e3);
        std::cout << name << ": " << us << "µs, " << bandwidth << " GB/s\n";
    };
    
    bench(add_scalar, "Scalar");
    bench(add_sse, "SSE   ");
    bench(add_avx2, "AVX2  ");
    bench(add_avx512, "AVX512");
}

int main() {
    benchmark();
    return 0;
}
```

---

## 2. Auto-Vetorização

```cpp
#include <vector>
#include <cmath>
#include <numeric>

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
        data[i] = data[i-1] + 1.0f;  // Dependência em data[i-1]
    }
}

// GCC flags: -O3 -march=native -ftree-vectorize -fopt-info-vec
```

---

## 3. CUDA Fundamentals

```cuda
#include <cuda_runtime.h>
#include <stdio.h>

// Kernel básico
__global__ void vector_add(const float* a, const float* b, float* c, int n) {
    int idx = blockIdx.x * blockDim.x + threadIdx.x;
    if (idx < n) {
        c[idx] = a[idx] + b[idx];
    }
}

// Exemplo de uso
void cuda_example() {
    int n = 1000000;
    size_t bytes = n * sizeof(float);
    
    // Host allocation
    float *h_a = new float[n];
    float *h_b = new float[n];
    float *h_c = new float[n];
    
    for (int i = 0; i < n; ++i) {
        h_a[i] = 1.0f;
        h_b[i] = 2.0f;
    }
    
    // Device allocation
    float *d_a, *d_b, *d_c;
    cudaMalloc(&d_a, bytes);
    cudaMalloc(&d_b, bytes);
    cudaMalloc(&d_c, bytes);
    
    // Copy to device
    cudaMemcpy(d_a, h_a, bytes, cudaMemcpyHostToDevice);
    cudaMemcpy(d_b, h_b, bytes, cudaMemcpyHostToDevice);
    
    // Launch kernel
    int block_size = 256;
    int grid_size = (n + block_size - 1) / block_size;
    vector_add<<<grid_size, block_size>>>(d_a, d_b, d_c, n);
    
    // Copy result back
    cudaMemcpy(h_c, d_c, bytes, cudaMemcpyDeviceToHost);
    
    // Verify
    printf("c[0] = %f (expected 3.0)\n", h_c[0]);
    
    // Cleanup
    delete[] h_a; delete[] h_b; delete[] h_c;
    cudaFree(d_a); cudaFree(d_b); cudaFree(d_c);
}

int main() {
    cuda_example();
    return 0;
}
```

---

## 4. Memory Management

```cuda
#include <cuda_runtime.h>
#include <stdio.h>

void memory_patterns() {
    int n = 1000000;
    size_t bytes = n * sizeof(float);
    
    // Pattern 1: Regular allocation + memcpy
    float *d1;
    cudaMalloc(&d1, bytes);
    // cudaMemcpy(d1, h1, bytes, cudaMemcpyHostToDevice);
    
    // Pattern 2: Unified Memory (C++)
    float *d2;
    cudaMallocManaged(&d2, bytes);
    // Direct access from both CPU and GPU
    d2[0] = 1.0f;  // Works!
    
    // Pattern 3: Pinned memory for async transfers
    float *h_pinned;
    cudaMallocHost(&h_pinned, bytes);  // Pinned (page-locked)
    cudaMemcpyAsync(d1, h_pinned, bytes, cudaMemcpyHostToDevice);
    
    // Cleanup
    cudaFree(d1);
    cudaFree(d2);
    cudaFreeHost(h_pinned);
}
```

---

## 5. Shared Memory

```cuda
#include <cuda_runtime.h>

// Reduction using shared memory
__global__ void reduce_sum(const float* input, float* output, int n) {
    extern __shared__ float sdata[];
    
    unsigned int tid = threadIdx.x;
    unsigned int i = blockIdx.x * blockDim.x * 2 + threadIdx.x;
    
    float val = 0;
    if (i < n) val = input[i];
    if (i + blockDim.x < n) val += input[i + blockDim.x];
    
    sdata[tid] = val;
    __syncthreads();
    
    // Reduction in shared memory
    for (unsigned int s = blockDim.x / 2; s > 32; s >>= 1) {
        if (tid < s) {
            sdata[tid] += sdata[tid + s];
        }
        __syncthreads();
    }
    
    // Warp-level reduction
    if (tid < 32) {
        volatile float* vdata = sdata;
        vdata[tid] += vdata[tid + 32];
        vdata[tid] += vdata[tid + 16];
        vdata[tid] += vdata[tid + 8];
        vdata[tid] += vdata[tid + 4];
        vdata[tid] += vdata[tid + 2];
        vdata[tid] += vdata[tid + 1];
    }
    
    if (tid == 0) {
        output[blockIdx.x] = sdata[0];
    }
}
```

---

## 6. Referências

- **CUDA Programming Guide** — docs.nvidia.com/cuda/cuda-c-programming-guide/
- **Intel Intrinsics Guide** — software.intel.com/sites/landingpage/IntrinsicsGuide/
- **CUDA by Example** — Sanders & Kandrot
- **GPU Gems** — developer.nvidia.com/gpugems
- **Programming Massively Parallel Processors** — Hwu, Kirk, Hajj
