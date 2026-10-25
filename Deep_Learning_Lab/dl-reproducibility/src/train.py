"""Training entry point.

  python -m src.train --run-name run_a --seed 42       # controlled run
  python -m src.train --run-name run_c --random-seed   # uncontrolled baseline
"""
import argparse
import json
import os
import time
from pathlib import Path

import torch
import torch.nn as nn

from src.data import build_dataloaders
from src.model import DigitsCNN, count_parameters
from src.reproducibility import enable_determinism, environment_report, set_global_seed, state_dict_sha256


def parse_args():
    p = argparse.ArgumentParser(description="Reproducible CNN training on scikit-learn digits")
    p.add_argument("--run-name", required=True)
    seed_group = p.add_mutually_exclusive_group()
    seed_group.add_argument("--seed", type=int, default=42)
    seed_group.add_argument("--random-seed", action="store_true", help="OS-random seed, determinism OFF")
    p.add_argument("--split-seed", type=int, default=42)
    p.add_argument("--epochs", type=int, default=15)
    p.add_argument("--batch-size", type=int, default=64)
    p.add_argument("--lr", type=float, default=1e-3)
    p.add_argument("--num-workers", type=int, default=2)
    p.add_argument("--threads", type=int, default=1)
    p.add_argument("--device", choices=["cpu", "cuda"], default="cpu")
    p.add_argument("--output-dir", default="outputs")
    return p.parse_args()


def evaluate(model, loader, criterion, device):
    model.eval()
    total_loss, correct, count = 0.0, 0, 0
    with torch.no_grad():
        for images, labels in loader:
            images, labels = images.to(device), labels.to(device)
            logits = model(images)
            total_loss += criterion(logits, labels).item() * labels.size(0)
            correct += (logits.argmax(dim=1) == labels).sum().item()
            count += labels.size(0)
    return total_loss / count, correct / count


def main():
    args = parse_args()
    if args.device == "cuda" and not torch.cuda.is_available():
        raise SystemExit("--device cuda requested but CUDA is not available.")
    torch.set_num_threads(args.threads)

    if args.random_seed:
        seed = int.from_bytes(os.urandom(4), "little")  # different every run
        set_global_seed(seed)
        deterministic = False
    else:
        seed = args.seed
        set_global_seed(seed)
        enable_determinism()
        deterministic = True

    device = torch.device(args.device)
    train_loader, val_loader = build_dataloaders(args.batch_size, args.split_seed, seed, args.num_workers)
    model = DigitsCNN().to(device)
    criterion = nn.CrossEntropyLoss()
    optimizer = torch.optim.Adam(model.parameters(), lr=args.lr)
    tag = f"[{args.run_name}]"
    print(f"{tag} seed={seed} deterministic={deterministic} device={device} "
          f"params={count_parameters(model)} batches/epoch={len(train_loader)}")

    step_losses, epoch_metrics = [], []
    start = time.perf_counter()
    for epoch in range(1, args.epochs + 1):
        model.train()
        running, seen = 0.0, 0
        for images, labels in train_loader:
            images, labels = images.to(device), labels.to(device)
            optimizer.zero_grad(set_to_none=True)
            loss = criterion(model(images), labels)
            loss.backward()
            optimizer.step()
            value = loss.item()
            step_losses.append(value)
            running += value * labels.size(0)
            seen += labels.size(0)
        val_loss, val_acc = evaluate(model, val_loader, criterion, device)
        epoch_metrics.append({"epoch": epoch, "train_loss": running / seen,
                              "val_loss": val_loss, "val_accuracy": val_acc})
        print(f"{tag} epoch {epoch:02d}/{args.epochs} | train_loss {running / seen:.6f} "
              f"| val_loss {val_loss:.6f} | val_acc {val_acc:.4f}")

    train_seconds = time.perf_counter() - start
    model_hash = state_dict_sha256(model)
    run_dir = Path(args.output_dir) / args.run_name
    run_dir.mkdir(parents=True, exist_ok=True)
    torch.save(model.state_dict(), run_dir / "model.pt")
    metrics = {
        "run_name": args.run_name,
        "seed": seed,
        "deterministic": deterministic,
        "config": vars(args),
        "environment": environment_report(),
        "num_parameters": count_parameters(model),
        "num_steps": len(step_losses),
        "step_losses_hex": [float.hex(v) for v in step_losses],  # exact bit pattern
        "epoch_metrics": epoch_metrics,
        "final_val_accuracy": epoch_metrics[-1]["val_accuracy"],
        "model_sha256": model_hash,
        "train_seconds": round(train_seconds, 3),
    }
    with open(run_dir / "metrics.json", "w") as f:
        json.dump(metrics, f, indent=2)

    print(f"{tag} final step loss = {step_losses[-1]!r} (hex {float.hex(step_losses[-1])})")
    print(f"{tag} model sha256    = {model_hash}")
    print(f"{tag} train time      = {train_seconds:.2f}s")
    print(f"{tag} saved           -> {run_dir}/metrics.json, model.pt")


if __name__ == "__main__":
    main()
