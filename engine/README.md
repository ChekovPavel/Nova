# Nova Inference Engine

A from-scratch C++17 transformer inference engine – no external dependencies,
fully on-device, loadable from Python via ctypes.

## Directory layout

```
engine/
├── include/
│   └── nova_engine.h       Public C API (ctypes-compatible)
├── src/
│   ├── tensor.hpp          Float32 tensor with all transformer ops
│   ├── tokenizer.hpp       Byte-level tokenizer (BPE-extensible)
│   ├── transformer.hpp     Model architecture declarations
│   └── transformer.cpp     Forward pass implementation
├── nova_engine.cpp         C ABI entry point
├── CMakeLists.txt          CMake build
└── Makefile                Simple make wrapper
```

## Building

### Make (Linux / macOS)

```bash
cd engine
make          # → nova_engine.so  (Linux)
              # → nova_engine.dylib (macOS)
```

### CMake

```bash
cd engine
cmake -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build -j$(nproc)
# shared library is in build/
```

## Model format  (`.nova`)

A simple little-endian binary format:

| Bytes    | Field                                      |
|----------|--------------------------------------------|
| 4        | Magic `NOVA`                               |
| 4        | Version (`1`)                              |
| 4 × 7    | vocab_size, hidden_size, num_layers, num_heads, ffn_size, max_seq_len, num_tensors |
| …        | Tensors (name_len, name, ndim, shape[], data[]) |

### Create a tiny random model (smoke-test)

```bash
python scripts/create_nova_model.py --output models/tiny.nova
```

### Convert a HuggingFace GPT-2 model

```bash
pip install torch transformers
python scripts/create_nova_model.py --hf gpt2 --output models/gpt2.nova
```

## Configuration (`config.json`)

```json
{
  "nova_engine": {
    "model_path":     "models/tiny.nova",
    "max_seq_len":    512,
    "temperature":    0.7,
    "top_p":          0.9,
    "top_k":          40,
    "max_new_tokens": 200
  }
}
```

## Integration with Nova

Nova tries inference backends in priority order:

1. **nova_engine** – this engine (on-device, no HTTP, zero latency overhead)
2. **Ollama** – local HTTP server
3. **External LLM** – cloud API
4. **Rule-based** – built-in templates (always available)

## Architecture

GPT-2-style decoder-only transformer:

- Token embeddings + sinusoidal positional encoding
- N × TransformerBlock
  - Pre-norm LayerNorm
  - Causal multi-head self-attention (scaled dot-product, causal mask)
  - Pre-norm LayerNorm
  - Feed-forward network (GELU activation)
  - Residual connections
- Final LayerNorm + LM-head projection

## Sampling strategies

- **Greedy** (`temperature = 0`)
- **Temperature** scaling
- **Top-k** filtering
- **Top-p (nucleus)** sampling
