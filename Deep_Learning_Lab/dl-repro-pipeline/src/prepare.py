"""Stage 1: data/raw -> data/split/{train,test}/<label>/ + data/manifest.csv (one MD5 per image)."""
import csv
import hashlib
import shutil
from pathlib import Path

import yaml
from sklearn.model_selection import train_test_split

RAW, SPLIT = Path("data/raw"), Path("data/split")


def main():
    params = yaml.safe_load(open("params.yaml"))["prepare"]
    files = sorted(RAW.rglob("*.png"))
    labels = [f.parent.name for f in files]
    train, test = train_test_split(files, test_size=params["test_size"], stratify=labels,
                                   random_state=params["seed"])
    if SPLIT.exists():
        shutil.rmtree(SPLIT)
    rows = []
    for name, group in (("train", sorted(train)), ("test", sorted(test))):
        for f in group:
            dest = SPLIT / name / f.parent.name / f.name
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(f, dest)
            rows.append({"path": dest.relative_to(SPLIT).as_posix(), "split": name,
                         "label": int(f.parent.name), "md5": hashlib.md5(dest.read_bytes()).hexdigest()})
    with open("data/manifest.csv", "w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=["path", "split", "label", "md5"])
        writer.writeheader()
        writer.writerows(rows)
    print("prepare: {} images -> train {} | test {} (seed {})".format(
        len(files), len(train), len(test), params["seed"]))


if __name__ == "__main__":
    main()
