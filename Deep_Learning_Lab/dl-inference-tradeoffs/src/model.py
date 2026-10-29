"""A small CNN for 8x8 handwritten digits, plus helpers to load it and run inference."""
import os
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn

MODEL_PATH = Path("outputs/model.pt")


class DigitCNN(nn.Module):
    def __init__(self):
        super().__init__()
        self.features = nn.Sequential(
            nn.Conv2d(1, 64, 3, padding=1), nn.ReLU(),
            nn.Conv2d(64, 128, 3, padding=1), nn.ReLU(),
            nn.Conv2d(128, 128, 3, padding=1), nn.ReLU(),
            nn.MaxPool2d(2),  # 8x8 -> 4x4
        )
        self.head = nn.Sequential(nn.Flatten(), nn.Linear(128 * 4 * 4, 128), nn.ReLU(), nn.Linear(128, 10))

    def forward(self, x):
        return self.head(self.features(x))


def set_threads():
    torch.set_num_threads(int(os.environ.get("MODEL_THREADS", "2")))


def load_model(path=MODEL_PATH):
    set_threads()
    model = DigitCNN()
    model.load_state_dict(torch.load(path, map_location="cpu"))
    model.eval()
    return model


@torch.inference_mode()
def predict_labels(model, x):
    """x: float32 array of shape (n, 64) with values in [0, 1]. Returns n class labels."""
    t = torch.from_numpy(np.ascontiguousarray(x, dtype=np.float32)).reshape(-1, 1, 8, 8)
    return model(t).argmax(dim=1).numpy()
