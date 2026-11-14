"""Project-relative paths (single place to change layout)."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data"
RAW = DATA / "raw"
PROCESSED = DATA / "processed"
EXTERNAL = DATA / "external"
SPLITS = DATA / "splits"
CONFIGS = ROOT / "configs"
RESULTS = ROOT / "results"
RUNS = ROOT / "runs"
REPORTS = ROOT / "reports"
FIGURES = REPORTS / "figures"

TRAIN_LABELS = RAW / "stage_2_train_labels.csv"
CLASS_INFO = RAW / "stage_2_detailed_class_info.csv"
TRAIN_DICOM_DIR = RAW / "stage_2_train_images"
METADATA = PROCESSED / "metadata.csv"
BOXES = PROCESSED / "boxes.csv"
SPLIT_FILE = SPLITS / "split_v1.csv"
MLFLOW_URI = f"sqlite:///{ROOT / 'mlflow.db'}"
ORIG_SIZE = 1024


def image_cache(size: int) -> Path:
    return PROCESSED / f"images_{size}.npy"
