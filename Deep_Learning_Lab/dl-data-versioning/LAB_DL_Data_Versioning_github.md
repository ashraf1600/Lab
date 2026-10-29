# Data Dependencies and Versioning for DL

**Level:** Intermediate · **Stack:** Docker, Python 3.11.9, PyTorch 2.3.1, DVC 3.51.2, MinIO (S3)

---

## 1. Introduction

**ShasthyoLens** retrained its digit model and accuracy dropped. Nobody can say which images the old model saw, because the dataset folder was overwritten. Git versions the code, but not the 1,800 images behind it.

You will version an image dataset with **DVC**, store it in an **S3 bucket** (MinIO), hash every image, and record the lineage **raw → split → training manifest → model** as a DVC pipeline. Then you tag two experiments and rebuild the old one from a fresh clone, getting byte-identical metrics.

![Architecture](https://raw.githubusercontent.com/poridhiEng/lab-asset/main/MLOps%20Lab/Deep-Learning-Fundamentals/lab-78.5/architecture.svg)

`fetch_raw.py` simulates two data deliveries: v1 with 1,200 digit images and v2 with all 1,797. `dvc add` replaces the image folder in Git with a small pointer file holding its hash. The pipeline in `dvc.yaml` runs `split`, `manifest` and `train` inside the pinned image `dl-data:v1`. Each experiment is a Git tag, and `dvc push` uploads the images and outputs to MinIO. A teammate clone uses `git checkout` and `dvc pull` to get back exactly the same data.

**Key terms**

| Term | Meaning |
|---|---|
| **DVC** | Data Version Control. It versions large files next to Git, keeping only small pointer files in Git |
| **Remote** | Shared storage for the real data, here the S3 bucket `s3://dvc-store/digits` on MinIO |
| **Pointer file (`.dvc`)** | A small text file with the MD5 hash, size and file count of the tracked data |
| **Lineage** | Which inputs, code and parameters produced each output. DVC records it in `dvc.lock` |
| **Dataset hash** | A SHA-256 over every image path and MD5. One changed pixel gives a new hash |
| **Tag** | A Git name for one experiment (`exp-v1`) that pins code, params and data together |

---

## 2. Objectives

By the end of this lab, you will be able to:

- Explain why Git alone cannot version a DL dataset and how DVC fills the gap.
- Run an S3-compatible MinIO server and use it as a DVC remote.
- Track a dataset with `dvc add` and generate per-image and whole-dataset hashes.
- Record the lineage raw → split → training manifest → model as a DVC pipeline.
- Tag experiments, compare them with `dvc metrics diff`, and reproduce an old one from a fresh clone.

---

## 3. Project Structure

```text
dl-data-versioning/
├── Dockerfile
├── .dockerignore
├── .gitignore
├── requirements.txt
├── storage.env          # MinIO image digests, demo login and bucket name
├── params.yaml          # split and training parameters
├── dvc.yaml             # pipeline: split -> manifest -> train
├── src/
│   ├── __init__.py
│   ├── fetch_raw.py     # simulates data deliveries v1 / v2
│   ├── split.py         # stage 1: raw -> train/test
│   ├── manifest.py      # stage 2: per-image MD5 + dataset hash
│   └── train.py         # stage 3: small CNN, metrics.json
└── docs/images/
```

After the lab, DVC also creates `.dvc/`, `data/`, `models/`, `dvc.lock` and `metrics.json`.

---

## 4. Prerequisites

| Requirement | Purpose / Version |
|---|---|
| VS Code Server (Poridhi) | Editor + integrated terminal |
| Docker Engine | Builds the pinned image and runs MinIO |
| Git | Versions code, params and the DVC pointer files |
| Internet access | Pull the base image, pip packages and the MinIO image |
| Free ports 9000 and 9001 | MinIO S3 API and web console |

No GPU is needed.

> **About MinIO images.** MinIO removed `minio/minio` from Docker Hub in September 2026, and the `quay.io` images now refuse anonymous pulls. This lab uses MinIO built by Chainguard (`cgr.dev/chainguard/minio`), pinned by digest in `storage.env`. Any S3-compatible server works the same way with DVC.

---

## 5. Environment Setup

1. Open the terminal (**Terminal → New Terminal**). If VS Code shows *Restricted Mode*, click **Trust Folder & Continue**.
2. Check the machine:

```bash
nproc && free -h | head -2 && docker --version && git --version
```

![Machine check](https://raw.githubusercontent.com/poridhiEng/lab-asset/main/MLOps%20Lab/Deep-Learning-Fundamentals/lab-78.5/01-machine-check.png)

The boxes show 2 vCPUs, 1.9 GiB of RAM, Docker 29.7.2 and Git 2.43.0. That is enough, because the dataset is small and the model trains in seconds.

3. Create the project and its files with **Explorer → New File**. `src/__init__.py` stays empty.

```bash
mkdir -p ~/code/dl-data-versioning/src && cd ~/code/dl-data-versioning
```

---

## 6. Project Implementation

### Step 1 — Pin the Environment

**Objective:** fix every tool version, so the same data and code always give the same result.

**`requirements.txt`**

```text
--extra-index-url https://download.pytorch.org/whl/cpu
torch==2.3.1+cpu
numpy==1.26.4
scikit-learn==1.5.0
pillow==10.3.0
dvc[s3]==3.51.2
# DVC 3.51 imports a private name that newer pathspec releases removed
pathspec==0.12.1
```

**`Dockerfile`**

```dockerfile
FROM python:3.11.9-slim-bookworm

# DVC works on a Git repository, so the image needs git
RUN apt-get update && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/*

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HOME=/tmp

COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

# The project (code, data, .git, .dvc) is mounted at /work at run time, not copied
WORKDIR /work
CMD ["dvc", "--version"]
```

**`.dockerignore`** and **`.gitignore`**

```text
data/
models/
docs/
.dvc/cache/
**/__pycache__/
*.md
```

```text
__pycache__/
```

The image holds only the tools. The project is **mounted** at `/work` when a command runs, because DVC needs the live Git repository. `pathspec` is pinned on purpose: DVC 3.51.2 crashes with newer `pathspec` releases, a real example of why sub-dependencies need pinning too.

### Step 2 — Storage Settings

**Objective:** keep the MinIO image versions and bucket name in one file.

**`storage.env`**

```bash
# S3-compatible storage for the DVC remote (MinIO built by Chainguard, pinned by digest)
MINIO_IMAGE=cgr.dev/chainguard/minio@sha256:a1d2b3516a41296510f7fb49184c18b88287fa8f35cf3ce5c047289053b94964
MC_IMAGE=cgr.dev/chainguard/minio-client@sha256:778b2dac231584d5d5749ab663f9f61979d60dd5c00abf682af888db6a9f46e4
MINIO_USER=minioadmin
MINIO_PASS=minioadmin123
BUCKET=dvc-store
```

These are demo credentials for a MinIO running on your own VM. For real S3, never put keys in Git. DVC keeps them in `.dvc/config.local`, which Git ignores (Step 9).

### Step 3 — Simulated Data Deliveries

**Objective:** create the "raw" dataset that later changes, as real datasets do.

**`src/fetch_raw.py`**

```python
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
```

Each image is written as an 8×8 grayscale PNG under `data/raw/<label>/`. The same image always produces the same bytes, so v2 contains v1's 1,200 files unchanged plus 597 new ones.

### Step 4 — The Lineage Stages

**Objective:** turn raw images into a split, a manifest with hashes, and a trained model.

**`params.yaml`**

```yaml
split:
  seed: 42
  test_size: 0.2
train:
  seed: 42
  epochs: 15
  lr: 0.001
  batch_size: 64
```

**`src/split.py`**

```python
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
```

**`src/manifest.py`**

```python
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
```

**`src/train.py`**

```python
"""Stage 3 (manifest -> model): train a small CNN on exactly the images listed in the manifest.

Writes models/model.pt and metrics.json (dataset hash, accuracy, model hash). Seeds and
deterministic ops make the same data + code + params give bit-identical weights.
"""
import csv
import hashlib
import json
import os
import random
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
import yaml
from PIL import Image

SPLIT = Path("data/split")


def set_seed(seed):
    os.environ["PYTHONHASHSEED"] = str(seed)
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.use_deterministic_algorithms(True)
    torch.set_num_threads(1)


def load(rows, split):
    part = [r for r in rows if r["split"] == split]
    x = np.stack([np.asarray(Image.open(SPLIT / r["path"]), dtype=np.float32) / 255.0 for r in part])
    y = np.array([int(r["label"]) for r in part])
    return torch.from_numpy(x).unsqueeze(1), torch.from_numpy(y)


def build_model():
    return nn.Sequential(
        nn.Conv2d(1, 16, 3, padding=1), nn.ReLU(),
        nn.Conv2d(16, 32, 3, padding=1), nn.ReLU(), nn.MaxPool2d(2),
        nn.Flatten(), nn.Linear(32 * 4 * 4, 64), nn.ReLU(), nn.Linear(64, 10))


def weights_sha256(model):
    h = hashlib.sha256()
    for name, tensor in sorted(model.state_dict().items()):
        h.update(name.encode())
        h.update(tensor.detach().cpu().numpy().tobytes())
    return h.hexdigest()


def main():
    params = yaml.safe_load(open("params.yaml"))["train"]
    set_seed(params["seed"])
    rows = list(csv.DictReader(open("data/manifest.csv")))
    dataset = json.loads(Path("data/dataset.json").read_text())
    x_train, y_train = load(rows, "train")
    x_test, y_test = load(rows, "test")

    model = build_model()
    optimizer = torch.optim.Adam(model.parameters(), lr=params["lr"])
    criterion = nn.CrossEntropyLoss()
    gen = torch.Generator().manual_seed(params["seed"])
    for epoch in range(1, params["epochs"] + 1):
        model.train()
        perm = torch.randperm(len(x_train), generator=gen)
        for i in range(0, len(perm), params["batch_size"]):
            idx = perm[i:i + params["batch_size"]]
            optimizer.zero_grad()
            loss = criterion(model(x_train[idx]), y_train[idx])
            loss.backward()
            optimizer.step()

    model.eval()
    with torch.no_grad():
        test_acc = (model(x_test).argmax(1) == y_test).float().mean().item()

    Path("models").mkdir(exist_ok=True)
    torch.save(model.state_dict(), "models/model.pt")
    metrics = {"dataset_hash": dataset["dataset_hash"][:16], "train_images": len(y_train),
               "test_images": len(y_test), "test_acc": round(test_acc, 4),
               "model_sha256": weights_sha256(model)[:16]}
    Path("metrics.json").write_text(json.dumps(metrics, indent=2) + "\n")
    print("trained on {} images | test_acc {:.4f} | model_sha256 {}".format(
        len(y_train), test_acc, metrics["model_sha256"]))


if __name__ == "__main__":
    main()
```

The manifest lists every image with its split, label and MD5. Its `dataset_hash` summarises the whole training set in one value. `train.py` reads only the images in the manifest, uses fixed seeds and deterministic ops, and writes the dataset hash and a weight hash into `metrics.json`.

### Step 5 — The Pipeline File

**Objective:** declare each stage's command, inputs, parameters and outputs, so DVC can track lineage.

**`dvc.yaml`**

```yaml
stages:
  split:
    cmd: python -m src.split
    deps:
      - data/raw
      - src/split.py
    params:
      - split.seed
      - split.test_size
    outs:
      - data/split
  manifest:
    cmd: python -m src.manifest
    deps:
      - data/split
      - src/manifest.py
    outs:
      - data/manifest.csv
      - data/dataset.json
  train:
    cmd: python -m src.train
    deps:
      - data/manifest.csv
      - data/split
      - src/train.py
    params:
      - train
    outs:
      - models/model.pt
    metrics:
      - metrics.json:
          cache: false
```

DVC reruns a stage only when one of its `deps` or `params` changes. `outs` are cached and pushed to the remote. `metrics.json` has `cache: false`, so it stays in Git where `dvc metrics diff` can compare it between tags.

### Step 6 — Build the Image

**Objective:** package Python, PyTorch, DVC and Git into `dl-data:v1`.

```bash
ls -lA && ls -l src
```

![Project files](https://raw.githubusercontent.com/poridhiEng/lab-asset/main/MLOps%20Lab/Deep-Learning-Fundamentals/lab-78.5/02-project-files.png)

The first box is `storage.env` and the second box the five source files. There is no `data/` folder yet.

```bash
docker build -t dl-data:v1 .
```

![Docker build](https://raw.githubusercontent.com/poridhiEng/lab-asset/main/MLOps%20Lab/Deep-Learning-Fundamentals/lab-78.5/03-docker-build.png)

The build finished in about 329 seconds. Half of that was `pip install` (165.7 s, mostly PyTorch and DVC). The last box shows the image named `dl-data:v1`.

### Step 7 — Start MinIO

**Objective:** run an S3-compatible server to act as the DVC remote.

```bash
source storage.env && docker run -d --name minio -p 9000:9000 -p 9001:9001 -e MINIO_ROOT_USER=$MINIO_USER -e MINIO_ROOT_PASSWORD=$MINIO_PASS -v minio-data:/data $MINIO_IMAGE server /data --console-address ":9001"
docker logs minio 2>&1 | tail -8
```

![Start MinIO](https://raw.githubusercontent.com/poridhiEng/lab-asset/main/MLOps%20Lab/Deep-Learning-Fundamentals/lab-78.5/04-start-minio.png)

The first box shows MinIO version RELEASE.2026-10-23. The second box shows the S3 API on port 9000 and the web console on port 9001. The named volume `minio-data` keeps the bucket if the container restarts.

### Step 8 — Create the Shortcuts and the Bucket

**Objective:** run `dvc`, `python` and `mc` (the MinIO client) inside pinned containers with short commands.

```bash
alias dvc='docker run --rm --user "$(id -u):$(id -g)" -v /etc/passwd:/etc/passwd:ro -v /etc/group:/etc/group:ro --network host -v "$(pwd):/work" dl-data:v1 dvc'
alias dpy='docker run --rm --user "$(id -u):$(id -g)" -v /etc/passwd:/etc/passwd:ro -v /etc/group:/etc/group:ro --network host -v "$(pwd):/work" dl-data:v1 python'
alias mc='docker run --rm --network host -e MC_HOST_local=http://$MINIO_USER:$MINIO_PASS@localhost:9000 $MC_IMAGE'
mc mb local/$BUCKET
```

- `--user` writes files as you, not root.
- The two `/etc/passwd` and `/etc/group` mounts let DVC and Git look up your user name. Without them, DVC fails with `getpwuid(): uid not found`.
- `--network host` lets the container reach MinIO on `localhost:9000`.
- Aliases last only for one terminal. In a new terminal, run `source storage.env` and the three `alias` lines again.

### Step 9 — Initialise Git and DVC

**Objective:** create the repository, connect the S3 remote and keep credentials out of Git.

```bash
git init -q && git config user.name "Student" && git config user.email "student@example.com" && dvc init -q && dvc remote add -d storage s3://$BUCKET/digits && dvc remote modify storage endpointurl http://localhost:9000 && dvc remote modify --local storage access_key_id $MINIO_USER && dvc remote modify --local storage secret_access_key $MINIO_PASS && git add . && git commit -q -m "Code, pipeline and DVC remote" && git log --oneline && dvc remote list && git ls-files .dvc
```

![Git and DVC setup](https://raw.githubusercontent.com/poridhiEng/lab-asset/main/MLOps%20Lab/Deep-Learning-Fundamentals/lab-78.5/05-git-dvc-setup.png)

The first box shows the first commit and the default remote `s3://dvc-store/digits`. The second box is the important check: Git tracks only `.dvc/.gitignore` and `.dvc/config`. The keys, set with `--local`, live in `.dvc/config.local`, which is not in Git.

### Step 10 — Version Raw Data v1

**Objective:** deliver 1,200 images and let DVC track them by hash.

```bash
dpy -m src.fetch_raw --count 1200 && dvc add data/raw
```

![Add raw v1](https://raw.githubusercontent.com/poridhiEng/lab-asset/main/MLOps%20Lab/Deep-Learning-Fundamentals/lab-78.5/06-add-raw-v1.png)

The first box shows 1,200 images across all ten digits. The second box shows that DVC asks you to commit only `data/raw.dvc` and `data/.gitignore`. The images themselves are now ignored by Git and stored in DVC's cache.

```bash
git add data/raw.dvc data/.gitignore && git commit -q -m "Raw data v1: 1200 images" && git show HEAD -- data/raw.dvc | tail -n 9
```

![Raw pointer file](https://raw.githubusercontent.com/poridhiEng/lab-asset/main/MLOps%20Lab/Deep-Learning-Fundamentals/lab-78.5/07-raw-pointer.png)

The box is the entire Git record of 1,200 images: one MD5 for the folder (`7bcb644e…`), its size (147,924 bytes) and the file count. If any image changes, this hash changes.

### Step 11 — Run the Pipeline for v1

**Objective:** build the split, manifest and model, and record their lineage.

```bash
dvc repro
```

![Pipeline v1](https://raw.githubusercontent.com/poridhiEng/lab-asset/main/MLOps%20Lab/Deep-Learning-Fundamentals/lab-78.5/08-repro-v1.png)

The boxes follow the lineage. **Split:** 1,200 images become 960 train and 240 test (seed 42). **Manifest:** the dataset hash is `4a020a2c410bad6e…`. **Train:** test accuracy 0.9875 and model hash `786ac8f3cc386877`. DVC writes all input and output hashes to `dvc.lock`.

```bash
dvc dag
```

![Pipeline graph](https://raw.githubusercontent.com/poridhiEng/lab-asset/main/MLOps%20Lab/Deep-Learning-Fundamentals/lab-78.5/09-dvc-dag.png)

The graph is the lineage: `data/raw.dvc → split → manifest → train`. `train` also depends on `split` directly, because it reads the image files.

### Step 12 — Tag and Push Experiment v1

**Objective:** freeze v1 as a named experiment and upload its data to MinIO.

```bash
git add dvc.lock metrics.json models/.gitignore data/.gitignore && git commit -q -m "Experiment v1" && git tag exp-v1 && dvc push
```

![Push v1](https://raw.githubusercontent.com/poridhiEng/lab-asset/main/MLOps%20Lab/Deep-Learning-Fundamentals/lab-78.5/10-push-v1.png)

The box shows 1,208 files pushed. There are 1,200 raw images and 1,200 split copies, but each copy has the same content as its raw image, so DVC stores it **once**. The rest are the manifest, dataset info, model and folder listings.

### Step 13 — Version Data v2 and Rerun

**Objective:** deliver more data and let DVC update everything that depends on it.

```bash
dpy -m src.fetch_raw --count 1797 && dvc add -q data/raw && dvc repro
```

![Pipeline v2](https://raw.githubusercontent.com/poridhiEng/lab-asset/main/MLOps%20Lab/Deep-Learning-Fundamentals/lab-78.5/11-repro-v2.png)

DVC saw a new hash for `data/raw` and reran all three stages. The boxes show 1,437 train and 360 test images, a new dataset hash `980823889b4e…`, test accuracy 0.9722 and model hash `166540fd2f6ffc81`.

```bash
git add data/raw.dvc dvc.lock metrics.json && git commit -q -m "Experiment v2: 1797 images" && git tag exp-v2 && dvc push && git log --oneline --decorate
```

![Push v2](https://raw.githubusercontent.com/poridhiEng/lab-asset/main/MLOps%20Lab/Deep-Learning-Fundamentals/lab-78.5/12-push-v2.png)

Only 605 files were uploaded this time: the 597 new images plus the new outputs. v1's images were already in the bucket. The second box shows both experiment tags in the history.

### Step 14 — Compare the Two Experiments

**Objective:** see exactly what changed between two tags, in data and in results.

```bash
dvc metrics diff exp-v1 exp-v2 && git diff exp-v1 exp-v2 -- data/raw.dvc
```

![Compare experiments](https://raw.githubusercontent.com/poridhiEng/lab-asset/main/MLOps%20Lab/Deep-Learning-Fundamentals/lab-78.5/13-compare-experiments.png)

The first box compares `metrics.json` at both tags: dataset hash, model hash, accuracy (−0.0153) and image counts (+120 test, +477 train). The second box shows the data pointer moving from `7bcb644e…` (1,200 files) to `be8be55a…` (1,797 files). So the accuracy change is tied to a specific, provable data change.

---

## 7. Verification and Testing

**Check the remote:**

```bash
mc du local/$BUCKET; echo "objects in bucket: $(mc ls -r local/$BUCKET | wc -l)"
```

![Remote bucket](https://raw.githubusercontent.com/poridhiEng/lab-asset/main/MLOps%20Lab/Deep-Learning-Fundamentals/lab-78.5/14-remote-bucket.png)

The bucket holds 1,813 objects (1,208 + 605) in 1.1 MiB, with both experiments and no duplicates.

**Reproduce the old experiment as a teammate would.** Clone into a new folder, which has no DVC cache, check out `exp-v1`, set your own keys, and pull from MinIO:

```bash
cd ~/code && git clone -q dl-data-versioning teammate && cd teammate && git checkout -q exp-v1 && dvc remote modify --local storage access_key_id $MINIO_USER && dvc remote modify --local storage secret_access_key $MINIO_PASS && ls && dvc pull
```

![Teammate pull](https://raw.githubusercontent.com/poridhiEng/lab-asset/main/MLOps%20Lab/Deep-Learning-Fundamentals/lab-78.5/15-teammate-pull.png)

The box shows 1,205 files fetched from MinIO. These are the v1 images and outputs, not v2's, because the tag's `raw.dvc` and `dvc.lock` point to v1 hashes.

```bash
dvc repro --force -q && dvc metrics show && git diff --exit-code exp-v1 -- metrics.json && echo "metrics.json is byte-identical to tag exp-v1"
```

![Reproduce v1](https://raw.githubusercontent.com/poridhiEng/lab-asset/main/MLOps%20Lab/Deep-Learning-Fundamentals/lab-78.5/16-reproduce-v1.png)

`--force` reruns every stage from the pulled raw data instead of trusting the cache. The first box shows the same dataset hash and model hash as Step 11. The second box shows that the retrained `metrics.json` has **no difference** from the one tagged months earlier, so the experiment is reproduced exactly.

**What Git actually stores:**

```bash
cd ~/code/dl-data-versioning && git ls-files | tr "\n" " "; echo; git tag; du -sh .git data .dvc/cache
```

![Git tracked files](https://raw.githubusercontent.com/poridhiEng/lab-asset/main/MLOps%20Lab/Deep-Learning-Fundamentals/lab-78.5/17-git-tracked.png)

The first box lists every Git-tracked file: code, params, pipeline files and `data/raw.dvc`, but no images and no `config.local`. The second box shows the sizes on disk. The `.git` folder is 460 KB, while `data/` (15 MB) and the DVC cache (9.1 MB) hold the images. Git stays small however much data you add.

| Check | Success means |
|---|---|
| Credentials | `git ls-files .dvc` shows no `config.local` |
| Data tracked | `data/raw.dvc` has an MD5, size and `nfiles`, and Git has no PNG files |
| Lineage | `dvc dag` shows raw → split → manifest → train |
| Remote | `dvc push` succeeds and the bucket holds objects |
| Reproduction | From a fresh clone at `exp-v1`, `dvc pull` + `dvc repro --force` gives a `metrics.json` identical to the tag |

---

## 8. Results and Observations

| | exp-v1 | exp-v2 |
|---|---|---|
| Raw images | 1,200 | 1,797 |
| `data/raw.dvc` MD5 | `7bcb644e…` | `be8be55a…` |
| Train / test images | 960 / 240 | 1,437 / 360 |
| Dataset hash | `4a020a2c410bad6e` | `980823889b4e6699` |
| Test accuracy | 0.9875 | 0.9722 |
| Model hash | `786ac8f3cc386877` | `166540fd2f6ffc81` |
| Files pushed to MinIO | 1,208 | 605 (new only) |

**Observations**

- **Git stays tiny.** All 1,797 images are represented in Git by one six-line pointer file. The `.git` folder is 460 KB.
- **Deduplication is automatic.** Split copies cost nothing extra, and v2 uploaded only its new images, because DVC addresses files by content hash.
- **The data, not the code, explains the result change.** Code and params are the same in both tags. Only the data pointer differs, so the accuracy change has one cause. The test sets also differ (240 vs 360 images), so the two accuracies are not a like-for-like comparison.
- **Lineage drives reruns.** After v2, DVC reran all three stages because their input hashes changed. Running `dvc repro` again with no changes reruns nothing.
- **Reproduction is exact.** A clone with no local cache rebuilt `exp-v1` with the same dataset hash, model hash and a byte-identical `metrics.json`.

---

## 9. Troubleshooting

**`pull access denied for minio/minio, repository does not exist`**
- **Cause:** MinIO removed its images from Docker Hub in September 2026.
- **Fix:** use the Chainguard image pinned in `storage.env`, or another S3-compatible server.

**`ERROR: unexpected error - 'getpwuid(): uid not found: 1001'`**
- **Cause:** the container runs as your UID, but that UID is not in the container's `/etc/passwd`.
- **Fix:** mount `-v /etc/passwd:/etc/passwd:ro -v /etc/group:/etc/group:ro`, as in the Step 8 aliases. If `dvc init` failed this way, delete `.dvc` and run it again, otherwise `.dvc/.gitignore` may be missing.

**`cannot import name '_DIR_MARK' from 'pathspec.patterns.gitwildmatch'`**
- **Cause:** a newer `pathspec` release removed a name that DVC 3.51.2 imports.
- **Fix:** pin `pathspec==0.12.1` in `requirements.txt` and rebuild the image.

**`.dvc/config.local` appears in `git ls-files`**
- **Cause:** `.dvc/.gitignore` did not exist yet when you ran `git add .`.
- **Fix:** run `git rm --cached .dvc/config.local`, check `.dvc/.gitignore`, then commit. If the keys were real, rotate them.

**`dvc push` / `dvc pull`: `Unable to locate credentials` or `NoSuchBucket`**
- **Cause:** keys are not set in this clone, or the bucket does not exist.
- **Fix:** run the two `dvc remote modify --local` commands, then `mc mb local/$BUCKET`.

**`dvc: command not found` in a new terminal**
- **Cause:** aliases and `storage.env` variables exist only in the terminal where they were defined.
- **Fix:** run `source storage.env` and the three `alias` lines again.

---

## 10. Conclusion

ShasthyoLens could not explain an accuracy drop because its data was not versioned. In this lab you put the dataset under DVC with a MinIO S3 remote, so Git holds only a pointer file with its hash. You recorded the lineage raw → split → manifest → model in a pipeline, with a per-image manifest and a dataset hash in every result. Two tagged experiments showed exactly what changed between them (1,200 vs 1,797 images, accuracy 0.9875 vs 0.9722), and DVC uploaded only the new images. Finally, a fresh clone rebuilt `exp-v1` from the remote with byte-identical metrics. With data versioned like code, any old result can be traced back to the exact images that produced it and reproduced on demand.
