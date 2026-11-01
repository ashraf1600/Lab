"""Stage 4: record WHAT produced the results (fingerprint.json) and WHAT the results are (artifacts.sha256).

fingerprint.json  - environment, code, data, params and randomness settings, all as content hashes
artifacts.sha256  - SHA-256 of every output file; a teammate checks it with: sha256sum -c artifacts.sha256
Nothing machine-specific (host name, time, git commit) is stored, so the files are byte-identical on a rerun.
"""
import hashlib
import json
import os
import platform
import subprocess
import sys
from pathlib import Path

import numpy
import torch
import yaml

from src.repro import sha256_file

ARTIFACTS = ["data/manifest.csv", "models/model.pt", "outputs/loss_curve.csv",
             "outputs/predictions.csv", "outputs/metrics.json"]
CODE = sorted(str(p) for p in Path("src").glob("*.py")) + ["params.yaml", "dvc.yaml", "requirements.txt",
                                                           "Dockerfile"]


def combined_hash(paths):
    h = hashlib.sha256()
    for path in paths:
        h.update(path.encode())
        h.update(sha256_file(path).encode())
    return h.hexdigest()


def main():
    freeze = subprocess.run([sys.executable, "-m", "pip", "freeze"], capture_output=True, text=True).stdout
    params = yaml.safe_load(open("params.yaml"))
    fingerprint = {
        "environment": {
            "base_image": os.environ.get("BASE_IMAGE", "unknown"),
            "python": platform.python_version(),
            "torch": torch.__version__,
            "numpy": numpy.__version__,
            "pip_freeze_sha256": hashlib.sha256(freeze.encode()).hexdigest()[:16],
        },
        "code_sha256": combined_hash(CODE)[:16],
        "data": {
            "raw_dvc_md5": yaml.safe_load(open("data/raw.dvc"))["outs"][0]["md5"],
            "manifest_sha256": sha256_file("data/manifest.csv")[:16],
        },
        "randomness": {
            "seed": params["train"]["seed"],
            "split_seed": params["prepare"]["seed"],
            "deterministic": params["train"]["deterministic"],
            "threads": params["train"]["threads"],
        },
    }
    Path("fingerprint.json").write_text(json.dumps(fingerprint, indent=2) + "\n")
    lines = ["{}  {}".format(sha256_file(p), p) for p in ARTIFACTS]
    Path("artifacts.sha256").write_text("\n".join(lines) + "\n")
    print("fingerprint: base image {}".format(fingerprint["environment"]["base_image"].split("@")[-1][:19]))
    print("fingerprint: code {} | data {} | env {}".format(
        fingerprint["code_sha256"], fingerprint["data"]["raw_dvc_md5"][:16],
        fingerprint["environment"]["pip_freeze_sha256"]))
    for line in lines:
        print("artifact: " + line[:16] + "  " + line.split("  ")[1])


if __name__ == "__main__":
    main()
