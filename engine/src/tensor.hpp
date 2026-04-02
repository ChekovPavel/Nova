#pragma once
/*
 * Nova Inference Engine – Tensor
 *
 * A minimal, row-major float32 tensor that supports all operations needed
 * for a GPT-style transformer forward pass.  No external dependencies.
 */

#include <algorithm>
#include <cassert>
#include <cmath>
#include <cstring>
#include <stdexcept>
#include <vector>

namespace nova {

class Tensor {
public:
    std::vector<size_t> shape;
    std::vector<float>  data;

    /* ---- constructors ------------------------------------------------- */

    Tensor() = default;

    explicit Tensor(std::vector<size_t> sh, float fill = 0.f)
        : shape(std::move(sh)), data(_numel(shape), fill) {}

    Tensor(std::vector<size_t> sh, const float* src)
        : shape(std::move(sh)), data(_numel(shape))
    {
        std::memcpy(data.data(), src, data.size() * sizeof(float));
    }

    /* ---- metadata ----------------------------------------------------- */

    size_t numel() const { return _numel(shape); }
    size_t ndim()  const { return shape.size(); }
    size_t rows()  const { assert(ndim() >= 2); return shape[ndim() - 2]; }
    size_t cols()  const { assert(ndim() >= 1); return shape[ndim() - 1]; }

    /* ---- element access ----------------------------------------------- */

    float& operator[](size_t i)       { return data[i]; }
    float  operator[](size_t i) const { return data[i]; }

    float& at(size_t r, size_t c)       { return data[r * cols() + c]; }
    float  at(size_t r, size_t c) const { return data[r * cols() + c]; }

    /* ---- arithmetic (in-place) ---------------------------------------- */

    /* Element-wise add; supports broadcast (T, H) += (H,) */
    Tensor& operator+=(const Tensor& o) {
        if (o.shape == shape) {
            for (size_t i = 0; i < data.size(); i++)
                data[i] += o.data[i];
        } else {
            assert(o.ndim() == 1 && shape.back() == o.shape[0]);
            size_t c = shape.back();
            for (size_t i = 0; i < data.size(); i++)
                data[i] += o.data[i % c];
        }
        return *this;
    }

    Tensor& operator*=(float s) {
        for (auto& v : data) v *= s;
        return *this;
    }

    Tensor operator+(const Tensor& o) const { Tensor t = *this; t += o; return t; }

    /* ---- reshaping ---------------------------------------------------- */

    Tensor view(std::vector<size_t> new_shape) const {
        assert(_numel(new_shape) == numel());
        Tensor t;
        t.shape = std::move(new_shape);
        t.data  = data;
        return t;
    }

    /* Slice rows [start, end) of a 2-D tensor */
    Tensor slice_rows(size_t start, size_t end) const {
        assert(ndim() == 2 && end <= shape[0]);
        Tensor t({end - start, shape[1]});
        std::memcpy(t.data.data(),
                    data.data() + start * shape[1],
                    (end - start) * shape[1] * sizeof(float));
        return t;
    }

    /* Transpose 2-D */
    Tensor T() const {
        assert(ndim() == 2);
        Tensor t({shape[1], shape[0]});
        for (size_t i = 0; i < shape[0]; i++)
            for (size_t j = 0; j < shape[1]; j++)
                t.at(j, i) = at(i, j);
        return t;
    }

    /* ---- math operations ---------------------------------------------- */

    /* (M, K) x (K, N) → (M, N) – cache-friendly inner loop */
    static Tensor matmul(const Tensor& A, const Tensor& B) {
        assert(A.ndim() == 2 && B.ndim() == 2);
        assert(A.cols() == B.rows());
        size_t M = A.rows(), K = A.cols(), N = B.cols();
        Tensor C({M, N}, 0.f);
        for (size_t i = 0; i < M; i++)
            for (size_t k = 0; k < K; k++) {
                float a = A.at(i, k);
                for (size_t j = 0; j < N; j++)
                    C.at(i, j) += a * B.at(k, j);
            }
        return C;
    }

    /* Softmax over last dimension (rows of a 2-D tensor) */
    static Tensor softmax(Tensor x) {
        assert(x.ndim() == 2);
        size_t R = x.rows(), C = x.cols();
        for (size_t i = 0; i < R; i++) {
            float* row = x.data.data() + i * C;
            float  mx  = *std::max_element(row, row + C);
            float  sum = 0.f;
            for (size_t j = 0; j < C; j++) { row[j] = std::exp(row[j] - mx); sum += row[j]; }
            for (size_t j = 0; j < C; j++) row[j] /= sum;
        }
        return x;
    }

    /* Layer normalisation over last dimension; gamma/beta shape (H,) */
    static Tensor layer_norm(const Tensor& x,
                              const Tensor& gamma,
                              const Tensor& beta,
                              float eps = 1e-5f)
    {
        assert(x.ndim() == 2);
        size_t R = x.rows(), H = x.cols();
        assert(gamma.numel() == H && beta.numel() == H);
        Tensor out({R, H});
        for (size_t i = 0; i < R; i++) {
            const float* row = x.data.data() + i * H;
            float mean = 0.f;
            for (size_t j = 0; j < H; j++) mean += row[j];
            mean /= static_cast<float>(H);
            float var = 0.f;
            for (size_t j = 0; j < H; j++) { float d = row[j] - mean; var += d * d; }
            var /= static_cast<float>(H);
            float inv = 1.f / std::sqrt(var + eps);
            float* orow = out.data.data() + i * H;
            for (size_t j = 0; j < H; j++)
                orow[j] = (row[j] - mean) * inv * gamma.data[j] + beta.data[j];
        }
        return out;
    }

    /* GELU activation (tanh approximation used by GPT-2) */
    static Tensor gelu(Tensor x) {
        constexpr float k = 0.7978845608028654f; /* sqrt(2/pi) */
        for (auto& v : x.data)
            v = 0.5f * v * (1.f + std::tanh(k * (v + 0.044715f * v * v * v)));
        return x;
    }

    /* Embedding lookup: ids shape (T,), weight shape (V, H) → (T, H) */
    static Tensor embed(const std::vector<int>& ids, const Tensor& weight) {
        assert(weight.ndim() == 2);
        size_t T = ids.size(), H = weight.cols();
        Tensor out({T, H});
        for (size_t i = 0; i < T; i++) {
            int id = ids[i];
            assert(id >= 0 && static_cast<size_t>(id) < weight.rows());
            std::memcpy(out.data.data() + i * H,
                        weight.data.data() + static_cast<size_t>(id) * H,
                        H * sizeof(float));
        }
        return out;
    }

    /* Apply causal mask: set upper-triangle entries to -∞ */
    static void apply_causal_mask(Tensor& attn, size_t T) {
        assert(attn.ndim() == 2 && attn.rows() == T && attn.cols() == T);
        constexpr float NEG_INF = -1e9f;
        for (size_t i = 0; i < T; i++)
            for (size_t j = i + 1; j < T; j++)
                attn.at(i, j) = NEG_INF;
    }

private:
    static size_t _numel(const std::vector<size_t>& sh) {
        if (sh.empty()) return 0;
        size_t n = 1;
        for (auto s : sh) n *= s;
        return n;
    }
};

} // namespace nova
