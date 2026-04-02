/*
 * Nova Inference Engine – C ABI entry point
 *
 * Provides the extern "C" functions declared in include/nova_engine.h.
 * Each NovaEngine instance is fully self-contained; there is no global state
 * other than the thread-local error buffer.
 */

#include "include/nova_engine.h"
#include "src/transformer.hpp"
#include "src/tokenizer.hpp"

#include <algorithm>
#include <cstring>
#include <memory>
#include <string>

/* Thread-local error buffer */
static thread_local std::string g_last_error;

static void set_error(const std::string& msg) { g_last_error = msg; }

/* ----------------------------------------------------------------------- *
 * Internal engine struct
 * --------------------------------------------------------------------- */
struct NovaEngine {
    nova::TransformerModel model;
    nova::Tokenizer        tokenizer;
    nova::Sampler          sampler;
    uint32_t               max_seq_len = 512;
    bool                   ready       = false;
};

/* ----------------------------------------------------------------------- *
 * Public API
 * --------------------------------------------------------------------- */
extern "C" {

NOVA_API const char* nova_engine_version(void) {
    return "nova-engine/0.1.0";
}

NOVA_API const char* nova_engine_last_error(void) {
    return g_last_error.c_str();
}

NOVA_API NovaEngine* nova_engine_create(const char* model_path,
                                         uint32_t    max_seq_len)
{
    auto* e = new NovaEngine();
    e->max_seq_len = (max_seq_len > 0) ? max_seq_len : 512;
    e->sampler     = nova::Sampler(42);

    if (model_path && *model_path) {
        std::string err;
        if (!e->model.load(model_path, err)) {
            set_error(err);
            delete e;
            return nullptr;
        }
    } else {
        /* No model path: boot a tiny random model for smoke-testing. */
        nova::ModelConfig cfg;
        cfg.vocab_size  = 260;
        cfg.hidden_size = 64;
        cfg.num_layers  = 2;
        cfg.num_heads   = 4;
        cfg.ffn_size    = 256;
        cfg.max_seq_len = e->max_seq_len;
        e->model = nova::TransformerModel(cfg);
    }

    e->ready = true;
    return e;
}

NOVA_API int32_t nova_engine_generate(NovaEngine*          engine,
                                       const char*          prompt,
                                       const NovaGenConfig* cfg,
                                       char*                out_buf,
                                       size_t               buf_size)
{
    if (!engine || !engine->ready) { set_error("Engine not initialised"); return -1; }
    if (!prompt || !out_buf || buf_size == 0) { set_error("Invalid arguments"); return -1; }

    /* Read generation config (fall back to safe defaults for zeroed struct) */
    const float    temperature = (cfg && cfg->temperature > 0.f) ? cfg->temperature : 0.7f;
    const float    top_p       = (cfg && cfg->top_p > 0.f)       ? cfg->top_p       : 0.9f;
    const int      top_k       = (cfg && cfg->top_k  > 0)        ? cfg->top_k       : 40;
    const uint32_t max_new     = (cfg && cfg->max_new_tokens > 0) ? cfg->max_new_tokens : 200;

    /* Tokenise */
    std::string prompt_str(prompt);
    std::vector<int> ids = engine->tokenizer.encode(prompt_str);

    const size_t max_ctx = engine->model.cfg.max_seq_len;
    if (ids.size() >= max_ctx)
        ids = std::vector<int>(ids.end() - static_cast<std::ptrdiff_t>(max_ctx - 1),
                               ids.end());

    /* Autoregressive generation loop */
    std::vector<int> generated;
    generated.reserve(max_new);

    for (uint32_t step = 0; step < max_new; step++) {
        if (ids.size() >= max_ctx)
            ids.erase(ids.begin());          /* sliding window */

        nova::Tensor logits = engine->model.forward(ids);
        int next_id = engine->sampler.sample(logits, temperature, top_p, top_k);

        if (next_id == nova::TOK_EOS) break;
        ids.push_back(next_id);
        generated.push_back(next_id);
    }

    /* Decode to UTF-8 */
    std::string text = engine->tokenizer.decode(generated);

    size_t copy_len = std::min(text.size(), buf_size - 1);
    std::memcpy(out_buf, text.c_str(), copy_len);
    out_buf[copy_len] = '\0';

    return static_cast<int32_t>(generated.size());
}

NOVA_API void nova_engine_reset(NovaEngine* engine) {
    /* Stateless forward pass – nothing to reset in this implementation */
    (void)engine;
}

NOVA_API void nova_engine_destroy(NovaEngine* engine) {
    delete engine;
}

} /* extern "C" */
