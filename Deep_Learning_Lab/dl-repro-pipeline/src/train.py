"""Stage 2: train the CNN with every reproducibility setting from params.yaml.

Writes models/model.pt and outputs/loss_curve.csv (loss per epoch, written as exact hex floats).
"""
from pathlib import Path

import torch
import torch.nn as nn
import yaml

from src.model import build_model, load_split
from src.repro import make_reproducible, sha256_state


def train_model(x, y, p, seed_everything=True):
    """Train and return (model, losses). seed_everything=False is used only by the break tests."""
    if seed_everything:
        make_reproducible(p["seed"], p["threads"], p["deterministic"])
        gen = torch.Generator().manual_seed(p["seed"])
    else:
        torch.use_deterministic_algorithms(p["deterministic"])
        torch.set_num_threads(p["threads"])
        gen = torch.Generator()
        gen.seed()  # a fresh random seed, like code that forgets to seed
    model = build_model()
    optimizer = torch.optim.Adam(model.parameters(), lr=p["lr"])
    criterion = nn.CrossEntropyLoss()
    losses = []
    for _ in range(p["epochs"]):
        model.train()
        perm = torch.randperm(len(x), generator=gen)
        total = 0.0
        for i in range(0, len(perm), p["batch_size"]):
            idx = perm[i:i + p["batch_size"]]
            optimizer.zero_grad()
            loss = criterion(model(x[idx]), y[idx])
            loss.backward()
            optimizer.step()
            total += loss.item() * len(idx)
        losses.append(total / len(x))
    return model, losses


def main():
    p = yaml.safe_load(open("params.yaml"))["train"]
    x, y, _ = load_split("train")
    model, losses = train_model(x, y, p)
    Path("models").mkdir(exist_ok=True)
    Path("outputs").mkdir(exist_ok=True)
    torch.save(model.state_dict(), "models/model.pt")
    with open("outputs/loss_curve.csv", "w") as fh:
        fh.write("epoch,loss_hex,loss\n")
        for epoch, loss in enumerate(losses, 1):
            fh.write("{},{},{:.6f}\n".format(epoch, float(loss).hex(), loss))
    print("train: {} images | seed {} | deterministic {} | threads {} | final loss {:.6f}".format(
        len(y), p["seed"], p["deterministic"], p["threads"], losses[-1]))
    print("train: weights sha256 {}".format(sha256_state(model)[:16]))


if __name__ == "__main__":
    main()
