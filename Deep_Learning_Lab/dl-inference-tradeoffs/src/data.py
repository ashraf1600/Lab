"""scikit-learn digits (1,797 images, 8x8, bundled offline) scaled to [0, 1]."""
import numpy as np
from sklearn.datasets import load_digits
from sklearn.model_selection import train_test_split

SEED = 42


def load_split():
    X, y = load_digits(return_X_y=True)
    X = (X / 16.0).astype(np.float32)
    return train_test_split(X, y, test_size=0.2, stratify=y, random_state=SEED)


def load_test_images(n):
    """Return n test images (repeating the test set if n is larger) and their true labels."""
    _, X_test, _, y_test = load_split()
    idx = np.arange(n) % len(X_test)
    return X_test[idx], y_test[idx]
