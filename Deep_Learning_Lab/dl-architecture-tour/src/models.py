"""Three small models, one per architecture family."""
import math

import torch
import torch.nn as nn


class DigitsCNN(nn.Module):
    """CNN: small filters slide over the image and share weights across positions."""

    def __init__(self, num_classes=10):
        super().__init__()
        self.features = nn.Sequential(
            nn.Conv2d(1, 16, kernel_size=3, padding=1), nn.ReLU(),   # (1, 8, 8)  -> (16, 8, 8)
            nn.Conv2d(16, 32, kernel_size=3, padding=1), nn.ReLU(),  # (16, 8, 8) -> (32, 8, 8)
            nn.MaxPool2d(2),                                         # -> (32, 4, 4)
        )
        self.head = nn.Sequential(nn.Flatten(), nn.Linear(32 * 4 * 4, 64), nn.ReLU(), nn.Linear(64, num_classes))

    def forward(self, x):
        return self.head(self.features(x))


class VitalsLSTM(nn.Module):
    """RNN/LSTM: reads the sequence one time step at a time and carries a memory (h, c)."""

    def __init__(self, hidden=64, num_classes=3):
        super().__init__()
        self.hidden = hidden
        self.cell = nn.LSTMCell(input_size=1, hidden_size=hidden)
        self.head = nn.Linear(hidden, num_classes)

    def forward(self, x):  # x: (B, L, 1)
        h = x.new_zeros(x.size(0), self.hidden)
        c = x.new_zeros(x.size(0), self.hidden)
        for t in range(x.size(1)):  # sequential: step t needs the result of step t-1
            h, c = self.cell(x[:, t], (h, c))
        return self.head(h)


class SelfAttention(nn.Module):
    """Every token looks at every other token: scores are an (L x L) matrix."""

    def __init__(self, d_model, n_heads):
        super().__init__()
        self.h, self.d = n_heads, d_model // n_heads
        self.qkv = nn.Linear(d_model, 3 * d_model)
        self.out = nn.Linear(d_model, d_model)

    def forward(self, x, pad_mask):
        b, l, dm = x.shape
        q, k, v = self.qkv(x).reshape(b, l, 3, self.h, self.d).permute(2, 0, 3, 1, 4)
        scores = q @ k.transpose(-2, -1) / math.sqrt(self.d)  # (B, heads, L, L)
        scores = scores.masked_fill(pad_mask[:, None, None, :], float("-inf"))
        y = (scores.softmax(dim=-1) @ v).transpose(1, 2).reshape(b, l, dm)
        return self.out(y)


class TransformerBlock(nn.Module):
    def __init__(self, d_model, n_heads, d_ff, dropout):
        super().__init__()
        self.ln1, self.ln2 = nn.LayerNorm(d_model), nn.LayerNorm(d_model)
        self.attn = SelfAttention(d_model, n_heads)
        self.ff = nn.Sequential(nn.Linear(d_model, d_ff), nn.GELU(), nn.Linear(d_ff, d_model))
        self.drop = nn.Dropout(dropout)

    def forward(self, x, pad_mask):
        x = x + self.drop(self.attn(self.ln1(x), pad_mask))
        return x + self.drop(self.ff(self.ln2(x)))


class TinyTransformerMLM(nn.Module):
    """Transformer encoder that predicts the [MASK] tokens of a sentence."""

    def __init__(self, vocab_size, max_len=256, d_model=64, n_heads=4, d_ff=128, n_layers=2, dropout=0.1):
        super().__init__()
        self.tok = nn.Embedding(vocab_size, d_model)
        self.pos = nn.Embedding(max_len, d_model)
        self.blocks = nn.ModuleList([TransformerBlock(d_model, n_heads, d_ff, dropout) for _ in range(n_layers)])
        self.ln = nn.LayerNorm(d_model)
        self.head = nn.Linear(d_model, vocab_size)

    def forward(self, ids):  # ids: (B, L)
        pad_mask = ids == 0
        x = self.tok(ids) + self.pos(torch.arange(ids.size(1)))
        for block in self.blocks:
            x = block(x, pad_mask)
        return self.head(self.ln(x))  # (B, L, vocab)


def build_model(name, vocab_size=None):
    if name == "cnn":
        return DigitsCNN()
    if name == "lstm":
        return VitalsLSTM()
    return TinyTransformerMLM(vocab_size)


def count_parameters(model):
    return sum(p.numel() for p in model.parameters() if p.requires_grad)
