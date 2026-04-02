#pragma once
/*
 * Nova Inference Engine – Transformer Model
 *
 * GPT-2-style decoder-only transformer:
 *   - Token embeddings + sinusoidal positional encoding
 *   - N × TransformerBlock (pre-norm LayerNorm, causal MHA, MLP with GELU)
 *   - Final LayerNorm + output projection (LM head)
 */

#include <cassert>
#include <cmath>
#include <memory>
#include <random>
#include <string>
#include <vector>

#include "tensor.hpp"
#include "tokenizer.hpp"

namespace nova {

/* ----------------------------------------------------------------------- *
 * Model hyperparameters
 * --------------------------------------------------------------------- */
struct ModelConfig {
    uint32_t vocab_size     = 260;
    uint32_t hidden_size    = 128;
    uint32_t num_layers     = 4;
    uint32_t num_heads      = 4;
    uint32_t ffn_size       = 512;
    uint32_t max_seq_len    = 512;
};

/* ----------------------------------------------------------------------- *
 * Linear layer  (weight: out × in, bias: out)
 * --------------------------------------------------------------------- */
struct Linear {
    Tensor weight;   /* shape (out, in)  */
    Tensor bias;     /* shape (out,)     */
    bool   use_bias;

    Linear() : use_bias(false) {}
    Linear(size_t in, size_t out, bool bias = true)
        : weight({out, in}, 0.f), bias({out}, 0.f), use_bias(bias) {}

    /* x: (T, in) → (T, out) */
    Tensor forward(const Tensor& x) const {
        Tensor y = Tensor::matmul(x, weight.T());
        if (use_bias) y += bias;
        return y;
    }
};

/* ----------------------------------------------------------------------- *
 * Multi-head causal self-attention
 * --------------------------------------------------------------------- */
struct MultiHeadAttention {
    Linear   q_proj, k_proj, v_proj, out_proj;
    uint32_t num_heads, head_dim;

    MultiHeadAttention() : num_heads(1), head_dim(1) {}
    MultiHeadAttention(uint32_t hidden, uint32_t n_heads)
        : q_proj(hidden, hidden),
          k_proj(hidden, hidden),
          v_proj(hidden, hidden),
          out_proj(hidden, hidden),
          num_heads(n_heads),
          head_dim(hidden / n_heads)
    {
        assert(hidden % n_heads == 0);
    }

    /* x: (T, H) → (T, H) */
    Tensor forward(const Tensor& x) const;
};

/* ----------------------------------------------------------------------- *
 * Feed-forward network (2-layer MLP with GELU)
 * --------------------------------------------------------------------- */
struct MLP {
    Linear fc1, fc2;

    MLP() = default;
    MLP(uint32_t hidden, uint32_t ffn)
        : fc1(hidden, ffn), fc2(ffn, hidden) {}

    /* x: (T, H) → (T, H) */
    Tensor forward(const Tensor& x) const {
        return fc2.forward(Tensor::gelu(fc1.forward(x)));
    }
};

/* ----------------------------------------------------------------------- *
 * Transformer block (pre-norm)
 * --------------------------------------------------------------------- */
struct TransformerBlock {
    Tensor ln1_gamma, ln1_beta;
    Tensor ln2_gamma, ln2_beta;
    MultiHeadAttention attn;
    MLP                mlp;

    TransformerBlock() = default;
    explicit TransformerBlock(const ModelConfig& cfg)
        : ln1_gamma({cfg.hidden_size}, 1.f),
          ln1_beta ({cfg.hidden_size}, 0.f),
          ln2_gamma({cfg.hidden_size}, 1.f),
          ln2_beta ({cfg.hidden_size}, 0.f),
          attn(cfg.hidden_size, cfg.num_heads),
          mlp(cfg.hidden_size, cfg.ffn_size) {}

    /* x: (T, H) → (T, H) */
    Tensor forward(const Tensor& x) const {
        Tensor h   = x;
        Tensor ln1 = Tensor::layer_norm(h, ln1_gamma, ln1_beta);
        h += attn.forward(ln1);
        Tensor ln2 = Tensor::layer_norm(h, ln2_gamma, ln2_beta);
        h += mlp.forward(ln2);
        return h;
    }
};

/* ----------------------------------------------------------------------- *
 * Full transformer model
 * --------------------------------------------------------------------- */
class TransformerModel {
public:
    ModelConfig                  cfg;
    Tensor                       tok_embed;     /* (V, H)       */
    Tensor                       pos_embed;     /* (seq, H)     */
    std::vector<TransformerBlock> blocks;
    Tensor                       ln_f_gamma;
    Tensor                       ln_f_beta;
    Linear                       lm_head;       /* (V, H), no bias */

    TransformerModel() = default;
    explicit TransformerModel(const ModelConfig& c);

    /* ids → logits (T, V) */
    Tensor forward(const std::vector<int>& ids) const;

    /* Load weights from a .nova binary file. */
    bool load(const std::string& path, std::string& err);

    int vocab_size() const { return static_cast<int>(cfg.vocab_size); }
};

/* ----------------------------------------------------------------------- *
 * Sampler
 * --------------------------------------------------------------------- */
class Sampler {
public:
    explicit Sampler(uint32_t seed = 42) : _rng(seed) {}

    /* Sample next token from last-row logits (T, V).
     * temperature == 0 → greedy argmax. */
    int sample(const Tensor& logits, float temperature,
               float top_p, int top_k) const;

private:
    mutable std::mt19937 _rng;
};

} // namespace nova
