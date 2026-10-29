"""Stage 2 (split -> training manifest): one row per image with its split, label and MD5 hash.

Writes data/manifest.csv and data/dataset.json. dataset_hash is a SHA-256 over every
"path,md5" line, so it changes if any image is added, removed, moved or edited.
"""
import csv
import hashlib
import json
from collections import Counter
from pathlib import Path

SPLIT = Path("data/split")


def md5(path):
    return hashlib.md5(path.read_bytes()).hexdigest()


def main():
    rows = []
    for f in sorted(SPLIT.rglob("*.png")):
        rel = f.relative_to(SPLIT)
        rows.append({"path": rel.as_posix(), "split": rel.parts[0], "label": int(rel.parts[1]),
                     "md5": md5(f), "bytes": f.stat().st_size})

    with open("data/manifest.csv", "w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    dataset_hash = hashlib.sha256("\n".join("{},{}".format(r["path"], r["md5"]) for r in rows).encode()).hexdigest()
    counts = Counter(r["split"] for r in rows)
    info = {"dataset_hash": dataset_hash, "images": len(rows), "train": counts["train"], "test": counts["test"]}
    Path("data/dataset.json").write_text(json.dumps(info, indent=2) + "\n")
    print("manifest: {} rows -> data/manifest.csv".format(len(rows)))
    print("dataset_hash: {}".format(dataset_hash))


if __name__ == "__main__":
    main()
