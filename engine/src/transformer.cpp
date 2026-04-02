/*
 * Nova Inference Engine – Transformer implementation
 */

#include "transformer.hpp"

#include <algorithm>
#include <cstdio>
#include <cstring>
#include <numeric>
#include <stdexcept>

namespace nova {

/* -----------------------------------------------------------------------
 * Multi-head causal self-attention forward pass
 * --------------------------------------------------------------------- */
Tensor MultiHeadAttention::forward(const Tensor& x) const {
    const size_t T  = x.rows();
    const size_t H  = x.cols();
    const size_t nh = num_heads;
    const size_t d  = head_dim;

    const float scale = 1.f / std::sqrt(static_cast<float>(d));

    Tensor Q = q_proj.forward(x);   /* (T, H) */
    Tensor K = k_proj.forward(x);
    Tensor V = v_proj.forward(x);

    Tensor out_all({T, H}, 0.f);

    for (size_t h = 0; h < nh; h++) {
        /* Extract head h: (T, d) */
        Tensor Qh({T, d}), Kh({T, d}), Vh({T, d});
        for (size_t t = 0; t < T; t++) {
            for (size_t j = 0; j < d; j++) {
                Qh.at(t, j) = Q.at(t, h * d + j);
                Kh.at(t, j) = K.at(t, h * d + j);
                Vh.at(t, j) = V.at(t, h * d + j);
            }
        }

        /* Attention scores: (T, T) = Qh @ Kh^T * scale */
        Tensor scores = Tensor::matmul(Qh, Kh.T());
        scores *= scale;

        /* Causal mask */
        Tensor::apply_causal_mask(scores, T);

        /* Softmax and context */
        Tensor attn_w = Tensor::softmax(scores);
        Tensor ctx    = Tensor::matmul(attn_w, Vh);   /* (T, d) */

        /* Write head output back */
        for (size_t t = 0; t < T; t++)
            for (size_t j = 0; j < d; j++)
                out_all.at(t, h * d + j) = ctx.at(t, j);
    }

    return out_proj.forward(out_all);
}

/* -----------------------------------------------------------------------
 * TransformerModel constructor – sinusoidal positional encoding
 * --------------------------------------------------------------------- */
TransformerModel::TransformerModel(const ModelConfig& c)
    : cfg(c),
      tok_embed({c.vocab_size,  c.hidden_size}, 0.f),
      pos_embed({c.max_seq_len, c.hidden_size}, 0.f),
      ln_f_gamma({c.hidden_size}, 1.f),
      ln_f_beta ({c.hidden_size}, 0.f),
      lm_head(c.hidden_size, c.vocab_size, /*bias=*/false)
{
    blocks.reserve(c.num_layers);
    for (uint32_t i = 0; i < c.num_layers; i++)
        blocks.emplace_back(c);

    /* Sinusoidal positional encoding (no parameters needed) */
    for (uint32_t pos = 0; pos < c.max_seq_len; pos++) {
        for (uint32_t i = 0; i < c.hidden_size; i++) {
            float angle = static_cast<float>(pos) /
                          std::pow(10000.f,
                                   2.f * (i / 2) / static_cast<float>(c.hidden_size));
            pos_embed.at(pos, i) = (i % 2 == 0) ? std::sin(angle) : std::cos(angle);
        }
    }
}

/* -----------------------------------------------------------------------
 * Forward pass: token IDs → logits (T, V)
 * --------------------------------------------------------------------- */
Tensor TransformerModel::forward(const std::vector<int>& ids) const {
    const size_t T = ids.size();
    assert(T > 0 && T <= cfg.max_seq_len);

    /* Token embeddings + positional encoding */
    Tensor h = Tensor::embed(ids, tok_embed);
    h += pos_embed.slice_rows(0, T);

    /* Transformer blocks */
    for (const auto& block : blocks)
        h = block.forward(h);

    /* Final layer norm */
    h = Tensor::layer_norm(h, ln_f_gamma, ln_f_beta);

    /* LM head → logits (T, V) */
    return lm_head.forward(h);
}

/* -----------------------------------------------------------------------
 * .nova binary model loader
 *
 * File layout (little-endian):
 *   [4]           magic "NOVA"
 *   [4]           version (uint32, must be 1)
 *   [4×7]         vocab_size, hidden_size, num_layers, num_heads,
 *                 ffn_size, max_seq_len, num_tensors
 *   For each tensor:
 *     [4]         name_len
 *     [name_len]  name (no NUL)
 *     [4]         ndim
 *     [ndim×4]    shape (uint32[])
 *     [numel×4]   data  (float32[])
 * --------------------------------------------------------------------- */
static bool rd_u32(std::FILE* f, uint32_t& v) {
    return std::fread(&v, 4, 1, f) == 1;
}

bool TransformerModel::load(const std::string& path, std::string& err) {
    std::FILE* f = std::fopen(path.c_str(), "rb");
    if (!f) { err = "Cannot open: " + path; return false; }

    /* Magic */
    char magic[5] = {};
    if (std::fread(magic, 1, 4, f) != 4 || std::strcmp(magic, "NOVA") != 0) {
        err = "Invalid .nova magic bytes"; std::fclose(f); return false;
    }

    /* Header */
    uint32_t version, vs, hs, nl, nh, fs, ms, nt;
    if (!rd_u32(f, version) || version != 1) {
        err = "Unsupported .nova version"; std::fclose(f); return false;
    }
    if (!rd_u32(f, vs) || !rd_u32(f, hs) || !rd_u32(f, nl) ||
        !rd_u32(f, nh) || !rd_u32(f, fs) || !rd_u32(f, ms) || !rd_u32(f, nt)) {
        err = "Truncated header"; std::fclose(f); return false;
    }

    cfg.vocab_size  = vs; cfg.hidden_size = hs; cfg.num_layers  = nl;
    cfg.num_heads   = nh; cfg.ffn_size    = fs; cfg.max_seq_len = ms;

    /* Re-initialise model with loaded config */
    *this = TransformerModel(cfg);

    /* Map tensor name → destination Tensor* */
    auto find_tensor = [&](const std::string& name) -> Tensor* {
        if (name == "tok_embed")      return &tok_embed;
        if (name == "pos_embed")      return &pos_embed;
        if (name == "ln_f.weight")    return &ln_f_gamma;
        if (name == "ln_f.bias")      return &ln_f_beta;
        if (name == "lm_head.weight") return &lm_head.weight;

        if (name.rfind("layers.", 0) == 0) {
            size_t dot = name.find('.', 7);
            if (dot == std::string::npos) return nullptr;
            int idx = std::stoi(name.substr(7, dot - 7));
            if (idx < 0 || static_cast<size_t>(idx) >= blocks.size()) return nullptr;
            auto& blk = blocks[static_cast<size_t>(idx)];
            std::string sub = name.substr(dot + 1);
            if (sub == "ln1.weight")      return &blk.ln1_gamma;
            if (sub == "ln1.bias")        return &blk.ln1_beta;
            if (sub == "ln2.weight")      return &blk.ln2_gamma;
            if (sub == "ln2.bias")        return &blk.ln2_beta;
            if (sub == "attn.q.weight")   return &blk.attn.q_proj.weight;
            if (sub == "attn.q.bias")     return &blk.attn.q_proj.bias;
            if (sub == "attn.k.weight")   return &blk.attn.k_proj.weight;
            if (sub == "attn.k.bias")     return &blk.attn.k_proj.bias;
            if (sub == "attn.v.weight")   return &blk.attn.v_proj.weight;
            if (sub == "attn.v.bias")     return &blk.attn.v_proj.bias;
            if (sub == "attn.out.weight") return &blk.attn.out_proj.weight;
            if (sub == "attn.out.bias")   return &blk.attn.out_proj.bias;
            if (sub == "mlp.fc1.weight")  return &blk.mlp.fc1.weight;
            if (sub == "mlp.fc1.bias")    return &blk.mlp.fc1.bias;
            if (sub == "mlp.fc2.weight")  return &blk.mlp.fc2.weight;
            if (sub == "mlp.fc2.bias")    return &blk.mlp.fc2.bias;
        }
        return nullptr;
    };

    /* Load each tensor */
    for (uint32_t i = 0; i < nt; i++) {
        uint32_t name_len;
        if (!rd_u32(f, name_len)) { err = "Bad tensor header"; std::fclose(f); return false; }
        std::string name(name_len, '\0');
        if (std::fread(name.data(), 1, name_len, f) != name_len) {
            err = "Truncated tensor name"; std::fclose(f); return false;
        }
        uint32_t ndim;
        if (!rd_u32(f, ndim)) { err = "Bad ndim"; std::fclose(f); return false; }
        std::vector<uint32_t> sh32(ndim);
        if (std::fread(sh32.data(), 4, ndim, f) != ndim) {
            err = "Bad shape"; std::fclose(f); return false;
        }
        size_t numel = 1;
        for (auto s : sh32) numel *= s;

        Tensor* dst = find_tensor(name);
        if (dst) {
            std::vector<size_t> sh(sh32.begin(), sh32.end());
            dst->shape = sh;
            dst->data.resize(numel);
            if (std::fread(dst->data.data(), 4, numel, f) != numel) {
                err = "Truncated data for " + name;
                std::fclose(f); return false;
            }
        } else {
            /* Unknown tensor – skip */
            std::fseek(f, static_cast<long>(numel * 4), SEEK_CUR);
        }
    }

    std::fclose(f);
    return true;
}

/* -----------------------------------------------------------------------
 * Sampler
 * --------------------------------------------------------------------- */
int Sampler::sample(const Tensor& logits, float temperature,
                     float top_p, int top_k) const
{
    const size_t V        = logits.cols();
    const size_t last_row = logits.rows() - 1;
    const float* raw      = logits.data.data() + last_row * V;

    /* Greedy */
    if (temperature <= 0.f)
        return static_cast<int>(std::max_element(raw, raw + V) - raw);

    /* Apply temperature */
    std::vector<float> p(raw, raw + V);
    float mx = *std::max_element(p.begin(), p.end());
    float sum = 0.f;
    for (auto& v : p) { v = std::exp((v - mx) / temperature); sum += v; }
    for (auto& v : p) v /= sum;

    /* Top-k */
    if (top_k > 0 && static_cast<size_t>(top_k) < V) {
        std::vector<float> sorted_p = p;
        std::nth_element(sorted_p.begin(), sorted_p.begin() + top_k,
                         sorted_p.end(), std::greater<float>());
        float kth = sorted_p[static_cast<size_t>(top_k) - 1];
        for (auto& v : p) if (v < kth) v = 0.f;
        sum = 0.f;
        for (auto v : p) sum += v;
        for (auto& v : p) v /= sum;
    }

    /* Top-p (nucleus) */
    if (top_p > 0.f && top_p < 1.f) {
        std::vector<std::pair<float, int>> pairs;
        pairs.reserve(V);
        for (size_t i = 0; i < V; i++)
            pairs.push_back({p[i], static_cast<int>(i)});
        std::sort(pairs.begin(), pairs.end(),
                  [](const auto& a, const auto& b){ return a.first > b.first; });
        float cumsum = 0.f;
        for (auto& [prob, idx] : pairs) {
            cumsum += prob;
            if (cumsum - prob > top_p) p[static_cast<size_t>(idx)] = 0.f;
        }
        sum = 0.f;
        for (auto v : p) sum += v;
        if (sum > 0.f) for (auto& v : p) v /= sum;
    }

    std::discrete_distribution<int> dist(p.begin(), p.end());
    return dist(_rng);
}

} // namespace nova
