"""Train one architecture family.

  python -m src.train --model cnn | lstm | transformer
"""
import argparse
import json
import time
from pathlib import Path

import torch
import torch.nn as nn

from src.data import digits_loaders, notes_loaders, vitals_loaders
from src.models import build_model, count_parameters
from src.reproducibility import enable_determinism, set_global_seed

TASKS = {  # task description, epochs, learning rate
    "cnn": ("digit image -> class 0-9", 15, 1e-3),
    "lstm": ("heart-rate sequence -> trend", 15, 3e-3),
    "transformer": ("clinical note -> masked words", 30, 1e-3),
}


def run_epoch(model, loader, criterion, optimizer=None):
    training = optimizer is not None
    model.train(training)
    total_loss, correct, count = 0.0, 0, 0
    with torch.set_grad_enabled(training):
        for x, y in loader:
            logits = model(x)
            if logits.dim() == 3:  # MLM: score only the masked positions
                logits, y = logits.reshape(-1, logits.size(-1)), y.reshape(-1)
                keep = y != -100
                logits, y = logits[keep], y[keep]
            loss = criterion(logits, y)
            if training:
                optimizer.zero_grad(set_to_none=True)
                loss.backward()
                optimizer.step()
            total_loss += loss.item() * y.size(0)
            correct += (logits.argmax(dim=1) == y).sum().item()
            count += y.size(0)
    return total_loss / count, correct / count


def main():
    p = argparse.ArgumentParser(description="Train one architecture family")
    p.add_argument("--model", choices=sorted(TASKS), required=True)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--output-dir", default="outputs")
    args = p.parse_args()

    torch.set_num_threads(1)
    set_global_seed(args.seed)
    enable_determinism()

    task, epochs, lr = TASKS[args.model]
    vocab_size = None
    if args.model == "cnn":
        train_loader, val_loader = digits_loaders(args.seed)
    elif args.model == "lstm":
        train_loader, val_loader = vitals_loaders(args.seed)
    else:
        train_loader, val_loader, vocab_size = notes_loaders(args.seed)

    model = build_model(args.model, vocab_size)
    optimizer = torch.optim.Adam(model.parameters(), lr=lr)
    criterion = nn.CrossEntropyLoss()
    tag = f"[{args.model}]"
    print(f"{tag} task: {task} | params={count_parameters(model):,} | batches/epoch={len(train_loader)}")

    start = time.perf_counter()
    for epoch in range(1, epochs + 1):
        train_loss, _ = run_epoch(model, train_loader, criterion, optimizer)
        val_loss, val_acc = run_epoch(model, val_loader, criterion)
        if epoch == 1 or epoch % 5 == 0:
            print(f"{tag} epoch {epoch:02d}/{epochs} | train_loss {train_loss:.4f} | val_loss {val_loss:.4f} | val_acc {val_acc:.4f}")
    seconds = time.perf_counter() - start

    out = Path(args.output_dir) / args.model
    out.mkdir(parents=True, exist_ok=True)
    torch.save(model.state_dict(), out / "model.pt")
    metrics = {"model": args.model, "task": task, "params": count_parameters(model), "epochs": epochs,
               "val_loss": val_loss, "val_accuracy": val_acc, "train_seconds": round(seconds, 2)}
    (out / "metrics.json").write_text(json.dumps(metrics, indent=2))
    print(f"{tag} final val_acc={val_acc:.4f} | train time {seconds:.1f}s | saved -> {out}/metrics.json")


if __name__ == "__main__":
    main()
