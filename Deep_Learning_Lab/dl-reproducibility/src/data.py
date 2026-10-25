"""Data pipeline: scikit-learn digits (bundled, offline) -> seeded PyTorch DataLoaders."""
import numpy as np
import torch
from sklearn.datasets import load_digits
from sklearn.model_selection import train_test_split
from torch.utils.data import DataLoader, TensorDataset

from src.reproducibility import make_generator, seed_worker


def load_digit_datasets(split_seed: int, val_fraction: float = 0.2):
    """Return (train_ds, val_ds). The split depends only on split_seed."""
    digits = load_digits()                              # 1,797 images, 8x8, values 0..16
    images = (digits.images / 16.0).astype(np.float32)  # scale to [0, 1]
    labels = digits.target.astype(np.int64)
    x_train, x_val, y_train, y_val = train_test_split(
        images, labels, test_size=val_fraction, random_state=split_seed, stratify=labels
    )

    def to_dataset(x, y):
        # (N, 8, 8) -> (N, 1, 8, 8)
        return TensorDataset(torch.from_numpy(x).unsqueeze(1), torch.from_numpy(y))

    return to_dataset(x_train, y_train), to_dataset(x_val, y_val)


def build_dataloaders(batch_size: int, split_seed: int, loader_seed: int, num_workers: int):
    train_ds, val_ds = load_digit_datasets(split_seed)
    train_loader = DataLoader(
        train_ds,
        batch_size=batch_size,
        shuffle=True,
        num_workers=num_workers,
        worker_init_fn=seed_worker,             # seeds each worker process
        generator=make_generator(loader_seed),  # fixes the shuffle order
    )
    val_loader = DataLoader(val_ds, batch_size=256, shuffle=False, num_workers=0)
    return train_loader, val_loader
