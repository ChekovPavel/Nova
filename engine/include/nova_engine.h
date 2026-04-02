#pragma once
/*
 * Nova Inference Engine – Public C API
 *
 * Designed to be loaded from Python via ctypes.  All state lives behind
 * the opaque NovaEngine pointer so the library has no global side effects.
 */

#include <stddef.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

#ifdef _WIN32
#  define NOVA_API __declspec(dllexport)
#else
#  define NOVA_API __attribute__((visibility("default")))
#endif

/* Opaque engine handle */
typedef struct NovaEngine NovaEngine;

/* Generation configuration – all fields have safe defaults if zeroed */
typedef struct {
    uint32_t max_new_tokens; /* max tokens to generate (0 → 200)    */
    float    temperature;    /* sampling temperature  (0 → greedy)  */
    float    top_p;          /* nucleus threshold     (0 → disabled) */
    int32_t  top_k;          /* top-k filtering       (0 → disabled) */
    uint32_t seed;           /* RNG seed (0 → 42)                   */
} NovaGenConfig;

/*
 * Create an engine.
 *
 * model_path  – path to a .nova model file; NULL or "" loads a tiny
 *               randomly-initialised model (useful for smoke-tests).
 * max_seq_len – maximum context length (0 → 512).
 *
 * Returns NULL on failure; call nova_engine_last_error() for details.
 */
NOVA_API NovaEngine* nova_engine_create(const char* model_path,
                                         uint32_t    max_seq_len);

/*
 * Generate a completion for the given prompt.
 *
 * Writes at most (buf_size – 1) UTF-8 bytes to out_buf (always NUL-terminated).
 * Returns the number of tokens generated, or -1 on error.
 */
NOVA_API int32_t nova_engine_generate(NovaEngine*          engine,
                                       const char*          prompt,
                                       const NovaGenConfig* cfg,
                                       char*                out_buf,
                                       size_t               buf_size);

/*
 * Reset the engine's generation state (KV-cache, if any).
 */
NOVA_API void nova_engine_reset(NovaEngine* engine);

/*
 * Free all resources.
 */
NOVA_API void nova_engine_destroy(NovaEngine* engine);

/*
 * Return the last error message (thread-local, never NULL).
 */
NOVA_API const char* nova_engine_last_error(void);

/*
 * Return the engine version string.
 */
NOVA_API const char* nova_engine_version(void);

#ifdef __cplusplus
}
#endif
