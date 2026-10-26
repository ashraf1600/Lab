"""Offline datasets for the three architecture families (no downloads)."""
import random

import numpy as np
import torch
from sklearn.datasets import load_digits
from sklearn.model_selection import train_test_split
from torch.utils.data import DataLoader, TensorDataset

SEQ_LEN = 48      # heart-rate sequence length (time steps)
NOTE_LEN = 16     # clinical-note length in tokens (padded)
PAD, MASK = 0, 1  # special token ids


def _loaders(x, y, batch_size, seed, stratify=None):
    x_tr, x_va, y_tr, y_va = train_test_split(x, y, test_size=0.2, random_state=seed, stratify=stratify)
    g = torch.Generator().manual_seed(seed)
    train = DataLoader(TensorDataset(torch.from_numpy(x_tr), torch.from_numpy(y_tr)),
                       batch_size=batch_size, shuffle=True, generator=g)
    val = DataLoader(TensorDataset(torch.from_numpy(x_va), torch.from_numpy(y_va)), batch_size=256)
    return train, val


def digits_loaders(seed, batch_size=64):
    """CNN task: classify 8x8 handwritten digits (0-9)."""
    d = load_digits()
    x = (d.images / 16.0).astype(np.float32)[:, None, :, :]  # (N, 1, 8, 8)
    y = d.target.astype(np.int64)
    return _loaders(x, y, batch_size, seed, stratify=y)


def vitals_loaders(seed, batch_size=64, n=3000):
    """RNN task: label a noisy heart-rate trace as falling (0), stable (1) or rising (2)."""
    rng = np.random.RandomState(seed)
    y = rng.randint(0, 3, size=n).astype(np.int64)
    t = np.arange(SEQ_LEN)
    slope = (y - 1)[:, None] * rng.uniform(0.15, 0.35, size=(n, 1))  # bpm per step
    base = rng.normal(75, 8, size=(n, 1))
    wave = 2.0 * np.sin(2 * np.pi * t / rng.uniform(8, 16, size=(n, 1)))
    hr = base + slope * t + wave + rng.normal(0, 1.5, size=(n, SEQ_LEN))
    x = ((hr - 75) / 10).astype(np.float32)[:, :, None]  # (N, 48, 1)
    return _loaders(x, y, batch_size, seed, stratify=y)


SUBJECTS = ["patient", "child", "woman", "man", "elderly patient"]
VERBS = ["reports", "complains of", "presents with", "has"]
DURATIONS = ["for two days", "for one week", "since yesterday", "since morning"]
PLAN_FOR = {  # each symptom has its own plan, so masked plan words are predictable from context
    "fever": "start paracetamol",
    "cough": "order chest xray",
    "headache": "advise rest",
    "chest pain": "refer to cardiology",
    "nausea": "give oral fluids",
    "back pain": "start physiotherapy",
}


def make_notes(n, seed):
    rng = random.Random(seed)
    notes = []
    for _ in range(n):
        symptom = rng.choice(sorted(PLAN_FOR))
        words = [rng.choice(SUBJECTS), rng.choice(VERBS), symptom, rng.choice(DURATIONS), "plan", PLAN_FOR[symptom]]
        notes.append(" ".join(words).split())
    return notes


def build_vocab():
    words = set()
    for group in (SUBJECTS, VERBS, DURATIONS, list(PLAN_FOR), list(PLAN_FOR.values()), ["plan"]):
        for phrase in group:
            words.update(phrase.split())
    return ["[PAD]", "[MASK]"] + sorted(words)


def notes_loaders(seed, batch_size=64, n=4000, mask_prob=0.15):
    """Transformer task: masked language modelling on short clinical notes."""
    vocab = build_vocab()
    index = {w: i for i, w in enumerate(vocab)}
    rng = np.random.RandomState(seed)
    ids = np.full((n, NOTE_LEN), PAD, dtype=np.int64)
    labels = np.full((n, NOTE_LEN), -100, dtype=np.int64)  # -100 = ignored by the loss
    for i, words in enumerate(make_notes(n, seed)):
        ids[i, :len(words)] = [index[w] for w in words]
        k = max(1, int(round(mask_prob * len(words))))
        pos = rng.choice(len(words), size=k, replace=False)
        labels[i, pos] = ids[i, pos]
        ids[i, pos] = MASK
    train, val = _loaders(ids, labels, batch_size, seed)
    return train, val, len(vocab)
