"""Copy every image used by the four lab guides into the cloned GitHub repo,
and write a copy of each guide whose image links point to raw.githubusercontent.com.

Run it from the Deep_Learning_Lab folder:   python push_images_helper.py
Edit the four settings below first.
"""
import re
import shutil
from pathlib import Path
from urllib.parse import quote

# ---- edit these ----
REPO_DIR = Path(r"D:\lab-asset")             # where you cloned poridhiEng/lab-asset
OWNER_REPO = "poridhiEng/lab-asset"
BRANCH = "main"
TOP_FOLDER = "MLOps Lab/Deep-Learning-Fundamentals"   # inside the repo's existing "MLOps Lab" folder
# --------------------

LABS = {
    "lab-78.1": ("dl-reproducibility", "LAB_DL_Environment_Setup_and_Reproducibility.md"),
    "lab-78.2": ("dl-architecture-tour", "LAB_DL_Architecture_Tour.md"),
    "lab-78.3": ("dl-compute-planning", "LAB_DL_Compute_Planning.md"),
    "lab-78.4": ("dl-inference-tradeoffs", "LAB_DL_Batch_vs_Online_Inference.md"),
    "lab-78.5": ("dl-data-versioning", "LAB_DL_Data_Versioning.md"),
}
IMAGE_LINK = re.compile(r"!\[([^\]]*)\]\((docs/images/[^)]+)\)")

for lab, (folder, md_name) in LABS.items():
    md_path = Path(folder) / md_name
    text = md_path.read_text(encoding="utf-8")
    dest = REPO_DIR / TOP_FOLDER / lab
    dest.mkdir(parents=True, exist_ok=True)

    def to_raw(match):
        src = Path(folder) / match.group(2)
        shutil.copy2(src, dest / src.name)
        url = "https://raw.githubusercontent.com/{}/{}/{}/{}/{}".format(
            OWNER_REPO, BRANCH, quote(TOP_FOLDER), quote(lab), quote(src.name))
        return "![{}]({})".format(match.group(1), url)

    new_text, count = IMAGE_LINK.subn(to_raw, text)
    out = md_path.with_name(md_path.stem + "_github.md")
    out.write_text(new_text, encoding="utf-8")
    print("{}: {} images copied to {} | links updated in {}".format(lab, count, dest, out))
