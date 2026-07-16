#!/usr/bin/env bash
# Sanket AI — One-shot dataset acquisition script
# Run: bash get_datasets.sh YOUR_ROBOFLOW_API_KEY
set -e

ROBOFLOW_API_KEY="${1:-}"
DATA_DIR="$(pwd)/data/raw"
mkdir -p "$DATA_DIR"

echo "==> [1/4] Creating Python virtual environment..."
python3 -m venv .venv
source .venv/bin/activate
pip install --quiet --upgrade pip

echo "==> [2/4] Installing data acquisition dependencies..."
pip install --quiet \
  roboflow \
  ultralytics \
  paddlepaddle \
  paddleocr \
  opencv-python-headless \
  pillow \
  numpy \
  requests \
  tqdm

echo "==> [3/4] Downloading P&ID symbol dataset from Roboflow..."
if [ -z "$ROBOFLOW_API_KEY" ]; then
  echo "  WARNING: No Roboflow API key provided."
  echo "  To get one: sign up FREE at https://roboflow.com → Settings → API Keys"
  echo "  Then re-run: bash get_datasets.sh YOUR_API_KEY"
  echo "  Skipping Roboflow download. Using bundled demo graph instead."
else
  python3 - <<PYEOF
from roboflow import Roboflow
import os

rf = Roboflow(api_key="${ROBOFLOW_API_KEY}")

# P&ID Symbol Detection dataset (public, 1800+ annotated symbols)
# Dataset: https://universe.roboflow.com/pid-detection/pid-symbol-detection
print("  Downloading pid-symbol-detection (YOLOv8 format)...")
project = rf.workspace("pid-detection").project("pid-symbol-detection")
version = project.version(1)
dataset = version.download("yolov8", location="${DATA_DIR}/pid_yolo")
print(f"  Saved to: ${DATA_DIR}/pid_yolo")

# Second dataset: more diverse P&ID symbols
print("  Downloading second P&ID dataset...")
try:
    project2 = rf.workspace("p-id").project("p-id-symbols")
    version2 = project2.version(1)
    dataset2 = version2.download("yolov8", location="${DATA_DIR}/pid_yolo_v2")
    print(f"  Saved to: ${DATA_DIR}/pid_yolo_v2")
except Exception as e:
    print(f"  Second dataset not available: {e}")
    print("  That is fine — first dataset is sufficient.")
PYEOF
fi

echo "==> [4/4] Generating synthetic CMMS + ISO 14224 seed data..."
python3 scripts/generate_seed_data.py

echo ""
echo "Done! Dataset summary:"
echo "  P&ID YOLOv8 labels : data/raw/pid_yolo/"
echo "  ISO 14224 taxonomy  : backend/data/iso14224_taxonomy.json"
echo "  Work orders         : backend/data/work_orders.json"
echo "  Inspection logs     : backend/data/inspection_logs.json"
echo "  Demo P&ID graph     : backend/data/demo_pid_graph.json"
