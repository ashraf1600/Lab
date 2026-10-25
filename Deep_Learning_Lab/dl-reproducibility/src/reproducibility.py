"""Reproducibility helpers: seeding, determinism, weight hashing, env report."""
import hashlib
import json
import os
import platform
import random

import numpy as np
import torch


def set_global_seed(seed: int) -> None:
    """Seed Python, NumPy and PyTorch (CPU + all GPUs) RNGs."""
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)


def enable_determinism() -> None:
    """Force deterministic cuDNN / PyTorch algorithms."""
    os.environ.setdefault("CUBLAS_WORKSPACE_CONFIG", ":4096:8")
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False
    torch.use_deterministic_algorithms(True)


def seed_worker(worker_id: int) -> None:
    """DataLoader worker_init_fn: seed NumPy/random inside each worker."""
    worker_seed = torch.initial_seed() % 2**32
    np.random.seed(worker_seed)
    random.seed(worker_seed)


def make_generator(seed: int) -> torch.Generator:
    """Seeded generator that fixes the DataLoader shuffle order."""
    g = torch.Generator()
    g.manual_seed(seed)
    return g


def state_dict_sha256(model: torch.nn.Module) -> str:
    """SHA-256 fingerprint of every weight (name + raw bytes)."""
    digest = hashlib.sha256()
    for name, tensor in sorted(model.state_dict().items()):
        digest.update(name.encode("utf-8"))
        digest.update(tensor.detach().cpu().contiguous().numpy().tobytes())
    return digest.hexdigest()


def environment_report() -> dict:
    cuda = torch.cuda.is_available()
    return {
        "python": platform.python_version(),
        "torch": torch.__version__,
        "numpy": np.__version__,
        "cuda_available": cuda,
        "cudnn_version": torch.backends.cudnn.version() if cuda else None,
        "torch_num_threads": torch.get_num_threads(),
        "PYTHONHASHSEED": os.environ.get("PYTHONHASHSEED"),
        "CUBLAS_WORKSPACE_CONFIG": os.environ.get("CUBLAS_WORKSPACE_CONFIG"),
        "deterministic_algorithms": torch.are_deterministic_algorithms_enabled(),
        "cudnn_deterministic": torch.backends.cudnn.deterministic,
        "cudnn_benchmark": torch.backends.cudnn.benchmark,
    }


if __name__ == "__main__":
    print("Before enable_determinism():")
    print(json.dumps(environment_report(), indent=2))
    enable_determinism()
    print("After enable_determinism():")
    print(json.dumps(environment_report(), indent=2))
