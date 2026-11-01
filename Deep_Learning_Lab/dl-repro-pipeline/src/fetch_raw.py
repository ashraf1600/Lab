"""Simulate a data delivery: write the first N scikit-learn digits as PNG files.

  python -m src.fetch_raw --count 1200   # delivery v1
  python -m src.fetch_raw --count 1797   # delivery v2 (all images)

Output: data/raw/<label>/<id>.png  (8x8 grayscale). The same image id always gives
byte-identical PNG bytes, so v2 contains v1's files unchanged plus new ones.
"""
import argparse
import shutil
from collections import Counter
from pathlib import Path

import numpy as np
from PIL import Image
from sklearn.datasets import load_digits

RAW = Path("data/raw")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--count", type=int, required=True)
    args = parser.parse_args()

    X, y = load_digits(return_X_y=True)
    count = min(args.count, len(X))
    if RAW.exists():
        shutil.rmtree(RAW)
    for i in range(count):
        folder = RAW / str(y[i])
        folder.mkdir(parents=True, exist_ok=True)
        pixels = (X[i].reshape(8, 8) * 255 / 16).astype(np.uint8)
        Image.fromarray(pixels, mode="L").save(folder / "{:04d}.png".format(i))

    per_label = Counter(int(v) for v in y[:count])
    print("wrote {} images to {}".format(count, RAW))
    print("per label: " + ", ".join("{}={}".format(k, per_label[k]) for k in sorted(per_label)))


if __name__ == "__main__":
    main()
