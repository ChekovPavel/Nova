#!/usr/bin/env python3
"""
create_nova_model.py - Create or convert a .nova model file.

Usage - tiny random model (smoke-test):
    python scripts/create_nova_model.py --output models/tiny.nova

Usage - convert a HuggingFace GPT-2 model:
    pip install torch transformers
    python scripts/create_nova_model.py --hf gpt2 --output models/gpt2.nova
"""

from __future__ import annotations

import argparse
import os
import struct
import sys

MAGIC = b"NOVA"
VERSION = 1


def _write_tensor(f, name: str, data: list, shape: list) -> None:
    name_b = name.encode()
    f.write(struct.pack("<I", len(name_b)))
    f.write(name_b)
    f.write(struct.pack("<I", len(shape)))
    for s in shape:
        f.write(struct.pack("<I", s))
    f.write(struct.pack(f"<{len(data)}f", *data))


# ---------------------------------------------------------------------------
# Tiny random model
# ---------------------------------------------------------------------------


def create_random_model(
    output_path: str,
    vocab_size: int = 260,
    hidden_size: int = 64,
    num_layers: int = 2,
    num_heads: int = 4,
    ffn_size: int = 256,
    max_seq_len: int = 256,
    seed: int = 42,
) -> None:
    """Write a randomly-initialised .nova model (useful for smoke-testing)."""
    import random

    rng = random.Random(seed)

    def randn(n: int, scale: float = 0.02) -> list:
        return [rng.gauss(0.0, scale) for _ in range(n)]

    def zeros(n: int) -> list:
        return [0.0] * n

    def ones(n: int) -> list:
        return [1.0] * n

    H, V, L, NH, F, S = (
        hidden_size,
        vocab_size,
        num_layers,
        num_heads,
        ffn_size,
        max_seq_len,
    )

    tensors: list = []

    # Embeddings
    tensors.append(("tok_embed", randn(V * H), [V, H]))
    tensors.append(("pos_embed", randn(S * H), [S, H]))

    # Per-layer tensors
    for i in range(L):
        p = f"layers.{i}"
        tensors += [
            (f"{p}.ln1.weight", ones(H), [H]),
            (f"{p}.ln1.bias", zeros(H), [H]),
            (f"{p}.ln2.weight", ones(H), [H]),
            (f"{p}.ln2.bias", zeros(H), [H]),
            (f"{p}.attn.q.weight", randn(H * H), [H, H]),
            (f"{p}.attn.q.bias", zeros(H), [H]),
            (f"{p}.attn.k.weight", randn(H * H), [H, H]),
            (f"{p}.attn.k.bias", zeros(H), [H]),
            (f"{p}.attn.v.weight", randn(H * H), [H, H]),
            (f"{p}.attn.v.bias", zeros(H), [H]),
            (f"{p}.attn.out.weight", randn(H * H), [H, H]),
            (f"{p}.attn.out.bias", zeros(H), [H]),
            (f"{p}.mlp.fc1.weight", randn(F * H), [F, H]),
            (f"{p}.mlp.fc1.bias", zeros(F), [F]),
            (f"{p}.mlp.fc2.weight", randn(H * F), [H, F]),
            (f"{p}.mlp.fc2.bias", zeros(H), [H]),
        ]

    # Final norm + LM head
    tensors.append(("ln_f.weight", ones(H), [H]))
    tensors.append(("ln_f.bias", zeros(H), [H]))
    tensors.append(("lm_head.weight", randn(V * H), [V, H]))

    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    with open(output_path, "wb") as f:
        f.write(MAGIC)
        f.write(struct.pack("<IIIIIIII", VERSION, V, H, L, NH, F, S, len(tensors)))
        for name, data, shape in tensors:
            _write_tensor(f, name, data, shape)

    size_mb = os.path.getsize(output_path) / 1024 / 1024
    print(f"✓ {output_path}  ({size_mb:.1f} MB, {len(tensors)} Tensoren)")
    print(f"  vocab={V}  hidden={H}  layers={L}  heads={NH}  ffn={F}  seq={S}")


# ---------------------------------------------------------------------------
# HuggingFace GPT-2 converter
# ---------------------------------------------------------------------------


def create_from_hf(hf_model: str, output_path: str) -> None:
    """Convert a HuggingFace GPT-2 checkpoint to .nova format."""
    try:
        from transformers import GPT2LMHeadModel
    except ImportError:
        print(
            "ERROR: torch und transformers werden benötigt: pip install torch transformers"
        )
        sys.exit(1)

    print(f"Lade {hf_model} von HuggingFace …")
    model = GPT2LMHeadModel.from_pretrained(hf_model)
    model.eval()
    c = model.config

    V = c.vocab_size
    H = c.n_embd
    L = c.n_layer
    NH = c.n_head
    F = c.n_inner or 4 * H
    S = c.n_positions

    sd = model.state_dict()

    def tolist(t) -> list:
        return t.detach().float().cpu().numpy().flatten().tolist()

    tensors: list = []
    tensors.append(("tok_embed", tolist(sd["transformer.wte.weight"]), [V, H]))
    tensors.append(("pos_embed", tolist(sd["transformer.wpe.weight"]), [S, H]))

    for i in range(L):
        p = f"layers.{i}"
        src = f"transformer.h.{i}"

        # GPT-2 uses Conv1D (weight is transposed vs. standard Linear)
        qkv_w = sd[f"{src}.attn.c_attn.weight"].float().T  # (3H, H)
        qkv_b = sd[f"{src}.attn.c_attn.bias"].float()
        q_w, k_w, v_w = qkv_w.chunk(3, dim=0)
        q_b, k_b, v_b = qkv_b.chunk(3, dim=0)

        out_w = sd[f"{src}.attn.c_proj.weight"].float().T
        out_b = sd[f"{src}.attn.c_proj.bias"].float()
        fc1_w = sd[f"{src}.mlp.c_fc.weight"].float().T
        fc1_b = sd[f"{src}.mlp.c_fc.bias"].float()
        fc2_w = sd[f"{src}.mlp.c_proj.weight"].float().T
        fc2_b = sd[f"{src}.mlp.c_proj.bias"].float()

        tensors += [
            (f"{p}.ln1.weight", tolist(sd[f"{src}.ln_1.weight"]), [H]),
            (f"{p}.ln1.bias", tolist(sd[f"{src}.ln_1.bias"]), [H]),
            (f"{p}.ln2.weight", tolist(sd[f"{src}.ln_2.weight"]), [H]),
            (f"{p}.ln2.bias", tolist(sd[f"{src}.ln_2.bias"]), [H]),
            (f"{p}.attn.q.weight", tolist(q_w), [H, H]),
            (f"{p}.attn.q.bias", tolist(q_b), [H]),
            (f"{p}.attn.k.weight", tolist(k_w), [H, H]),
            (f"{p}.attn.k.bias", tolist(k_b), [H]),
            (f"{p}.attn.v.weight", tolist(v_w), [H, H]),
            (f"{p}.attn.v.bias", tolist(v_b), [H]),
            (f"{p}.attn.out.weight", tolist(out_w), [H, H]),
            (f"{p}.attn.out.bias", tolist(out_b), [H]),
            (f"{p}.mlp.fc1.weight", tolist(fc1_w), [F, H]),
            (f"{p}.mlp.fc1.bias", tolist(fc1_b), [F]),
            (f"{p}.mlp.fc2.weight", tolist(fc2_w), [H, F]),
            (f"{p}.mlp.fc2.bias", tolist(fc2_b), [H]),
        ]

    tensors.append(("ln_f.weight", tolist(sd["transformer.ln_f.weight"]), [H]))
    tensors.append(("ln_f.bias", tolist(sd["transformer.ln_f.bias"]), [H]))
    tensors.append(("lm_head.weight", tolist(sd["lm_head.weight"]), [V, H]))

    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    with open(output_path, "wb") as f:
        f.write(MAGIC)
        f.write(struct.pack("<IIIIIIII", VERSION, V, H, L, NH, F, S, len(tensors)))
        for name, data, shape in tensors:
            _write_tensor(f, name, data, shape)

    size_mb = os.path.getsize(output_path) / 1024 / 1024
    print(f"✓ {hf_model} → {output_path}  ({size_mb:.1f} MB)")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Erstellt oder konvertiert eine .nova-Modelldatei."
    )
    parser.add_argument(
        "--output",
        "-o",
        default="models/tiny.nova",
        help="Ausgabepfad (Standard: models/tiny.nova)",
    )
    parser.add_argument(
        "--hf", default=None, help="HuggingFace-Modellname (z. B. gpt2)"
    )
    parser.add_argument("--hidden-size", type=int, default=64)
    parser.add_argument("--num-layers", type=int, default=2)
    parser.add_argument("--num-heads", type=int, default=4)
    parser.add_argument("--ffn-size", type=int, default=256)
    parser.add_argument("--max-seq-len", type=int, default=256)
    args = parser.parse_args()

    if args.hf:
        create_from_hf(args.hf, args.output)
    else:
        create_random_model(
            args.output,
            hidden_size=args.hidden_size,
            num_layers=args.num_layers,
            num_heads=args.num_heads,
            ffn_size=args.ffn_size,
            max_seq_len=args.max_seq_len,
        )
