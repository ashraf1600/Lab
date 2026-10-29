"""Train the digit CNN once, save outputs/model.pt, and time the model alone at batch 1 vs batch 128."""
import time

import numpy as np
import torch
import torch.nn as nn

from src.data import load_split
from src.model import MODEL_PATH, DigitCNN, predict_labels, set_threads

EPOCHS = 8
BATCH_SIZE = 64


def model_ms_per_image(model, X, batch_size, repeats=20):
    x = X[:batch_size]
    predict_labels(model, x)  # warm-up
    start = time.perf_counter()
    for _ in range(repeats):
        predict_labels(model, x)
    return (time.perf_counter() - start) / repeats / batch_size * 1000


def main():
    torch.manual_seed(42)
    set_threads()
    X_train, X_test, y_train, y_test = load_split()
    xt = torch.from_numpy(X_train).reshape(-1, 1, 8, 8)
    yt = torch.from_numpy(y_train).long()

    model = DigitCNN()
    optimizer = torch.optim.Adam(model.parameters(), lr=1e-3)
    criterion = nn.CrossEntropyLoss()
    for epoch in range(1, EPOCHS + 1):
        model.train()
        perm = torch.randperm(len(xt))
        total = 0.0
        for i in range(0, len(xt), BATCH_SIZE):
            idx = perm[i:i + BATCH_SIZE]
            optimizer.zero_grad()
            loss = criterion(model(xt[idx]), yt[idx])
            loss.backward()
            optimizer.step()
            total += loss.item() * len(idx)
        model.eval()
        acc = float(np.mean(predict_labels(model, X_test) == y_test))
        print("epoch {} | train_loss {:.4f} | test_acc {:.4f}".format(epoch, total / len(xt), acc))

    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    torch.save(model.state_dict(), MODEL_PATH)
    print("saved -> {} ({:,} parameters)".format(MODEL_PATH, sum(p.numel() for p in model.parameters())))

    one = model_ms_per_image(model, X_test, 1)
    many = model_ms_per_image(model, X_test, 128)
    print("model only, threads={}: batch 1 = {:.3f} ms/image | batch 128 = {:.3f} ms/image | {:.1f}x cheaper per image".format(
        torch.get_num_threads(), one, many, one / many))


if __name__ == "__main__":
    main()
