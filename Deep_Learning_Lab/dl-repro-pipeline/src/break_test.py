"""Remove one reproducibility pillar at a time and show which hash breaks.

Each case trains twice with the same settings and compares the two runs, so a case is
REPRODUCIBLE only if both runs give bit-identical weights and loss curves.
"""
import hashlib
import sys

import torch
import yaml

from src.model import load_split
from src.repro import sha256_state
from src.train import train_model


def data_hash(x):
    return hashlib.sha256(x.numpy().tobytes()).hexdigest()[:12]


def run(x, y, p, seed_everything=True):
    model, losses = train_model(x, y, p, seed_everything)
    return sha256_state(model)[:12], float(losses[-1]).hex()


def main():
    base = yaml.safe_load(open("params.yaml"))["train"]
    base = dict(base, epochs=3)  # shorter runs, enough to show the effect
    x, y, _ = load_split("train")
    x_edit = x.clone()
    x_edit[0, 0, 4, 4] = 1.0 - x_edit[0, 0, 4, 4]  # change one pixel of one training image

    cases = [
        ("all pillars on (baseline)", x, base, True),
        ("no seed", x, base, False),
        ("deterministic off, 4 threads", x, dict(base, deterministic=False, threads=4), True),
        ("one pixel changed in data", x_edit, base, True),
    ]
    _, ref_loss = run(x, y, base)
    ref_w = run(x, y, base)[0]
    print("{:<30} {:>12} {:>12} {:>9} {:>13}".format("case", "data_sha", "weights_sha", "run1=run2", "vs baseline"))
    for name, data, p, seeded in cases:
        w1, l1 = run(data, y, p, seeded)
        w2, l2 = run(data, y, p, seeded)
        same = "yes" if (w1, l1) == (w2, l2) else "NO"
        vs = "identical" if w1 == ref_w and l1 == ref_loss else "DIFFERENT"
        print("{:<30} {:>12} {:>12} {:>9} {:>13}".format(name, data_hash(data), w1, same, vs))
    sys.stdout.flush()


if __name__ == "__main__":
    main()
