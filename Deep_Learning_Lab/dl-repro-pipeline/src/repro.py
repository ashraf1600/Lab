"""One place that pins every source of randomness and non-determinism."""
import hashlib
import os
import random

import numpy as np
import torch


def make_reproducible(seed, threads=1, deterministic=True):
    """Seed Python, NumPy and PyTorch, force deterministic ops and a fixed thread count."""
    os.environ["PYTHONHASHSEED"] = str(seed)
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.use_deterministic_algorithms(deterministic)
    torch.set_num_threads(threads)


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_state(model):
    """Hash of every weight tensor, in a fixed order."""
    h = hashlib.sha256()
    for name, tensor in sorted(model.state_dict().items()):
        h.update(name.encode())
        h.update(tensor.detach().cpu().numpy().tobytes())
    return h.hexdigest()
