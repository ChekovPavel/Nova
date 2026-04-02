#pragma once
/*
 * Nova Inference Engine – Tokenizer
 *
 * Byte-level tokenizer: maps every byte value 0-255 to a unique token ID,
 * with four reserved special tokens.  This gives a fixed vocabulary of 260
 * tokens and handles all valid UTF-8 without a separate BPE table.
 *
 * In production you can swap this class for a BPE or SentencePiece tokenizer
 * while keeping the same encode()/decode() interface.
 */

#include <string>
#include <unordered_map>
#include <vector>

namespace nova {

/* Special token IDs */
constexpr int TOK_PAD = 0;
constexpr int TOK_UNK = 1;
constexpr int TOK_BOS = 2;
constexpr int TOK_EOS = 3;

class Tokenizer {
public:
    /* Build the default byte-level vocabulary. */
    Tokenizer() {
        _enc["<pad>"] = TOK_PAD;  _dec[TOK_PAD] = "<pad>";
        _enc["<unk>"] = TOK_UNK;  _dec[TOK_UNK] = "<unk>";
        _enc["<bos>"] = TOK_BOS;  _dec[TOK_BOS] = "<bos>";
        _enc["<eos>"] = TOK_EOS;  _dec[TOK_EOS] = "<eos>";
        for (int b = 0; b < 256; b++) {
            std::string key(1, static_cast<char>(b));
            int id = b + 4;
            _enc[key] = id;
            _dec[id]  = key;
        }
        _vocab_size = 260;
    }

    int vocab_size() const { return _vocab_size; }

    /* Encode UTF-8 string to token IDs (prepends BOS by default). */
    std::vector<int> encode(const std::string& text, bool add_bos = true) const {
        std::vector<int> ids;
        ids.reserve(text.size() + 1);
        if (add_bos) ids.push_back(TOK_BOS);
        for (unsigned char c : text) {
            auto it = _enc.find(std::string(1, static_cast<char>(c)));
            ids.push_back(it != _enc.end() ? it->second : TOK_UNK);
        }
        return ids;
    }

    /* Decode token IDs to UTF-8 string (skips special tokens). */
    std::string decode(const std::vector<int>& ids) const {
        std::string out;
        out.reserve(ids.size());
        for (int id : ids) {
            if (id == TOK_BOS || id == TOK_EOS || id == TOK_PAD) continue;
            auto it = _dec.find(id);
            if (it != _dec.end() && it->second.size() == 1)
                out += it->second;
        }
        return out;
    }

    /* Replace the vocabulary (called by the model loader). */
    void set_vocab(const std::unordered_map<std::string, int>& enc) {
        _enc = enc;
        _dec.clear();
        for (auto& [k, v] : enc) _dec[v] = k;
        _vocab_size = static_cast<int>(_enc.size());
    }

private:
    std::unordered_map<std::string, int> _enc;
    std::unordered_map<int, std::string> _dec;
    int _vocab_size = 0;
};

} // namespace nova
