"""Small CNN for 8x8 digits and a loader that reads exactly the images in the manifest."""
import csv
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
from PIL import Image

SPLIT = Path("data/split")


def build_model():
    return nn.Sequential(
        nn.Conv2d(1, 16, 3, padding=1), nn.ReLU(),
        nn.Conv2d(16, 32, 3, padding=1), nn.ReLU(), nn.MaxPool2d(2),
        nn.Flatten(), nn.Linear(32 * 4 * 4, 64), nn.ReLU(), nn.Linear(64, 10))


def load_split(split):
    rows = [r for r in csv.DictReader(open("data/manifest.csv")) if r["split"] == split]
    x = np.stack([np.asarray(Image.open(SPLIT / r["path"]), dtype=np.float32) / 255.0 for r in rows])
    y = np.array([int(r["label"]) for r in rows])
    return torch.from_numpy(x).unsqueeze(1), torch.from_numpy(y), [r["path"] for r in rows]
