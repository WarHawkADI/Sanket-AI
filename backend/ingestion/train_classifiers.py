"""
Trains two offline ML classifiers from UCI datasets.
These are saved as .joblib files and called by the RCA agent as tools.

Models produced:
  models/ai4i_classifier.joblib     — predicts failure mode from sensor readings
  models/hydraulic_classifier.joblib — predicts component health from sensor streams

Run: python -m backend.ingestion.train_classifiers
"""
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import joblib
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report

os.makedirs("models", exist_ok=True)


# ── 1. AI4I 2020 — failure mode classifier ────────────────────────────────
def train_ai4i():
    feat_path = Path("data/raw/uci/ai4i_features.csv")
    targ_path = Path("data/raw/uci/ai4i_targets.csv")

    if not feat_path.exists():
        print("AI4I data not found — skipping. Download with:\n"
              "  python -m backend.ingestion.download_uci")
        return

    print("Training AI4I failure mode classifier...")
    feat = pd.read_csv(feat_path)
    targ = pd.read_csv(targ_path)

    # Try both column name formats (with/without unit suffixes)
    feature_cols_with_units = [
        "Air temperature [K]", "Process temperature [K]",
        "Rotational speed [rpm]", "Torque [Nm]", "Tool wear [min]",
    ]
    feature_cols_bare = [
        "Air temperature", "Process temperature",
        "Rotational speed", "Torque", "Tool wear",
    ]
    feature_cols = feature_cols_with_units if feature_cols_with_units[0] in feat.columns else feature_cols_bare
    failure_cols = ["TWF", "HDF", "PWF", "OSF", "RNF"]

    X = feat[feature_cols]
    y_binary = targ["Machine failure"]
    y_multi = targ[failure_cols]

    X_tr, X_te, yb_tr, yb_te = train_test_split(X, y_binary, test_size=0.2, random_state=42)
    _, _, ym_tr, ym_te = train_test_split(X, y_multi, test_size=0.2, random_state=42)

    clf_binary = RandomForestClassifier(
        n_estimators=200, class_weight="balanced", random_state=42, n_jobs=-1
    )
    clf_binary.fit(X_tr, yb_tr)

    clf_multi = RandomForestClassifier(
        n_estimators=200, class_weight="balanced", random_state=42, n_jobs=-1
    )
    clf_multi.fit(X_tr, ym_tr)

    print(classification_report(yb_te, clf_binary.predict(X_te), target_names=["No Failure", "Failure"]))

    joblib.dump(
        {
            "binary": clf_binary,
            "multi": clf_multi,
            "feature_cols": feature_cols,
            "failure_cols": failure_cols,
        },
        "models/ai4i_classifier.joblib",
    )
    print("  ✓ Saved: models/ai4i_classifier.joblib")


# ── 2. UCI Hydraulic — component health classifier ─────────────────────────
def train_hydraulic():
    hydraulic_dir = Path("data/raw/uci/hydraulic")
    profile_path = hydraulic_dir / "profile.txt"

    if not profile_path.exists():
        print("Hydraulic data not found — skipping. Download with:\n"
              '  wget -P data/raw/uci/hydraulic/ '
              '"https://archive.ics.uci.edu/static/public/447/condition+monitoring+of+hydraulic+systems.zip"\n'
              "  cd data/raw/uci/hydraulic && unzip *.zip")
        return

    print("Training hydraulic component health classifier...")

    sensor_names = [
        "PS1", "PS2", "PS3", "PS4", "PS5", "PS6",
        "EPS1", "FS1", "FS2",
        "TS1", "TS2", "TS3", "TS4",
        "VS1", "CE", "CP", "SE",
    ]

    feature_blocks = []
    loaded = []
    for s in sensor_names:
        fpath = hydraulic_dir / f"{s}.txt"
        if not fpath.exists():
            continue
        data = np.loadtxt(str(fpath))   # (2205, timesteps)
        feature_blocks.append(np.column_stack([
            data.mean(axis=1),
            data.std(axis=1),
            data.max(axis=1),
        ]))
        loaded.append(s)

    if not feature_blocks:
        print("  No sensor .txt files found in hydraulic dir.")
        return

    X = np.hstack(feature_blocks)  # (2205, n_sensors * 3)
    profile = np.loadtxt(str(profile_path))
    # Columns: cooler_cond, valve_cond, pump_leakage, accumulator, stable
    # Binarise: 0 = healthy (at max), 1 = degraded
    max_healthy = [100, 100, 0, 130]
    target_names = ["cooler_cond", "valve_cond", "pump_leakage", "accumulator"]
    y = np.column_stack([
        (profile[:, i] != max_healthy[i]).astype(int) for i in range(4)
    ])

    X_tr, X_te, y_tr, y_te = train_test_split(X, y, test_size=0.2, random_state=42)
    clf = RandomForestClassifier(n_estimators=200, random_state=42, n_jobs=-1)
    clf.fit(X_tr, y_tr)

    per_label_acc = (clf.predict(X_te) == y_te).mean(axis=0)
    for name, acc in zip(target_names, per_label_acc):
        print(f"    {name}: {acc:.3f} accuracy")

    joblib.dump(
        {
            "model": clf,
            "sensors": loaded,
            "targets": target_names,
            "n_features": X.shape[1],
        },
        "models/hydraulic_classifier.joblib",
    )
    print("  ✓ Saved: models/hydraulic_classifier.joblib")


if __name__ == "__main__":
    train_ai4i()
    print()
    train_hydraulic()
    print("\nClassifier training complete.")
