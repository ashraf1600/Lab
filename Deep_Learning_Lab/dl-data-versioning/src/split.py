"""Stage 1 (raw -> split): copy data/raw into data/split/{train,test}/<label>/ with a fixed seed."""
import shutil
from collections import Counter
from pathlib import Path

import yaml
from sklearn.model_selection import train_test_split

RAW, OUT = Path("data/raw"), Path("data/split")


def main():
    params = yaml.safe_load(open("params.yaml"))["split"]
    files = sorted(RAW.rglob("*.png"))
    labels = [f.parent.name for f in files]
    train, test = train_test_split(files, test_size=params["test_size"], stratify=labels,
                                   random_state=params["seed"])
    if OUT.exists():
        shutil.rmtree(OUT)
    for name, group in (("train", train), ("test", test)):
        for f in group:
            dest = OUT / name / f.parent.name / f.name
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(f, dest)
    print("split {} raw images -> train {} | test {} (seed {}, test_size {})".format(
        len(files), len(train), len(test), params["seed"], params["test_size"]))
    print("test per label: " + ", ".join("{}={}".format(k, v) for k, v in sorted(
        Counter(f.parent.name for f in test).items())))


if __name__ == "__main__":
    main()
