"""Stage 3 (manifest -> model): train a small CNN on exactly the images listed in the manifest.

Writes models/model.pt and metrics.json (dataset hash, accuracy, model hash). Seeds and
deterministic ops make the same data + code + params give bit-identical weights.
"""
import csv
import hashlib
import json
import os
import random
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
import yaml
from PIL import Image

SPLIT = Path("data/split")


def set_seed(seed):
    os.environ["PYTHONHASHSEED"] = str(seed)
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.use_deterministic_algorithms(True)
    torch.set_num_threads(1)


def load(rows, split):
    part = [r for r in rows if r["split"] == split]
    x = np.stack([np.asarray(Image.open(SPLIT / r["path"]), dtype=np.float32) / 255.0 for r in part])
    y = np.array([int(r["label"]) for r in part])
    return torch.from_numpy(x).unsqueeze(1), torch.from_numpy(y)


def build_model():
    return nn.Sequential(
        nn.Conv2d(1, 16, 3, padding=1), nn.ReLU(),
        nn.Conv2d(16, 32, 3, padding=1), nn.ReLU(), nn.MaxPool2d(2),
        nn.Flatten(), nn.Linear(32 * 4 * 4, 64), nn.ReLU(), nn.Linear(64, 10))


def weights_sha256(model):
    h = hashlib.sha256()
    for name, tensor in sorted(model.state_dict().items()):
        h.update(name.encode())
        h.update(tensor.detach().cpu().numpy().tobytes())
    return h.hexdigest()


def main():
    params = yaml.safe_load(open("params.yaml"))["train"]
    set_seed(params["seed"])
    rows = list(csv.DictReader(open("data/manifest.csv")))
    dataset = json.loads(Path("data/dataset.json").read_text())
    x_train, y_train = load(rows, "train")
    x_test, y_test = load(rows, "test")

    model = build_model()
    optimizer = torch.optim.Adam(model.parameters(), lr=params["lr"])
    criterion = nn.CrossEntropyLoss()
    gen = torch.Generator().manual_seed(params["seed"])
    for epoch in range(1, params["epochs"] + 1):
        model.train()
        perm = torch.randperm(len(x_train), generator=gen)
        for i in range(0, len(perm), params["batch_size"]):
            idx = perm[i:i + params["batch_size"]]
            optimizer.zero_grad()
            loss = criterion(model(x_train[idx]), y_train[idx])
            loss.backward()
            optimizer.step()

    model.eval()
    with torch.no_grad():
        test_acc = (model(x_test).argmax(1) == y_test).float().mean().item()

    Path("models").mkdir(exist_ok=True)
    torch.save(model.state_dict(), "models/model.pt")
    metrics = {"dataset_hash": dataset["dataset_hash"][:16], "train_images": len(y_train),
               "test_images": len(y_test), "test_acc": round(test_acc, 4),
               "model_sha256": weights_sha256(model)[:16]}
    Path("metrics.json").write_text(json.dumps(metrics, indent=2) + "\n")
    print("trained on {} images | test_acc {:.4f} | model_sha256 {}".format(
        len(y_train), test_acc, metrics["model_sha256"]))


if __name__ == "__main__":
    main()
