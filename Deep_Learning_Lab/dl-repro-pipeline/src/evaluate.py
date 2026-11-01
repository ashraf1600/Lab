"""Stage 3: evaluate the saved model -> outputs/predictions.csv + outputs/metrics.json."""
import json

import torch

from src.model import build_model, load_split


def main():
    torch.set_num_threads(1)
    model = build_model()
    model.load_state_dict(torch.load("models/model.pt"))
    model.eval()
    x, y, paths = load_split("test")
    with torch.no_grad():
        pred = model(x).argmax(1)
    with open("outputs/predictions.csv", "w") as fh:
        fh.write("path,label,pred\n")
        for path, label, p in zip(paths, y.tolist(), pred.tolist()):
            fh.write("{},{},{}\n".format(path, label, p))
    acc = (pred == y).float().mean().item()
    metrics = {"test_images": len(y), "test_acc": round(acc, 4), "errors": int((pred != y).sum())}
    with open("outputs/metrics.json", "w") as fh:
        fh.write(json.dumps(metrics, indent=2) + "\n")
    print("evaluate: {} test images | test_acc {:.4f} | errors {}".format(len(y), acc, metrics["errors"]))


if __name__ == "__main__":
    main()
