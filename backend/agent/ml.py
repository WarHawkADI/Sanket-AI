"""
Predictive-maintenance classifiers wired in as an agent capability.

Loads the trained AI4I model (models/ai4i_classifier.joblib) and exposes a
simple predict().  If scikit-learn / the model file is unavailable, it falls
back to a transparent physics-style heuristic so the tool degrades gracefully
and the demo never breaks.
"""
from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

MODEL_PATH = Path("models/ai4i_classifier.joblib")

FAILURE_LABELS = {
    "TWF": "Tool Wear Failure",
    "HDF": "Heat Dissipation Failure",
    "PWF": "Power Failure",
    "OSF": "Overstrain Failure",
    "RNF": "Random Failure",
}


@lru_cache(maxsize=1)
def _load():
    try:
        import joblib  # noqa
        if MODEL_PATH.exists():
            return joblib.load(MODEL_PATH)
    except Exception:
        pass
    return None


def predict(air_temp_k: float, process_temp_k: float, rot_speed_rpm: float,
            torque_nm: float, tool_wear_min: float) -> dict:
    """Predict machine-failure risk + likely mode from sensor readings.

    Returns {'source', 'failure_probability', 'predicted_modes':[...], 'note'}.
    """
    features = [air_temp_k, process_temp_k, rot_speed_rpm, torque_nm, tool_wear_min]
    model = _load()

    if model is not None:
        try:
            import warnings
            import numpy as np
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")  # model fit with feature names; array input is fine
                X = np.array([features], dtype=float)
                prob = float(model["binary"].predict_proba(X)[0][1])
                modes = []
                multi = model["multi"]
                preds = multi.predict(X)[0]
                for code, flag in zip(model["failure_cols"], preds):
                    if int(flag) == 1:
                        modes.append(FAILURE_LABELS.get(code, code))
                # if none flagged, surface the two most probable modes for context
                if not modes:
                    probs = [(model["failure_cols"][i], est.predict_proba(X)[0][1])
                             for i, est in enumerate(multi.estimators_)]
                    probs.sort(key=lambda x: x[1], reverse=True)
                    modes = [f"{FAILURE_LABELS.get(c, c)} (p={p:.2f})" for c, p in probs[:2] if p > 0.05]
            return {"source": "ai4i_random_forest", "failure_probability": round(prob, 3),
                    "predicted_modes": modes,
                    "note": "Prediction from trained UCI AI4I RandomForest classifier."}
        except Exception as exc:  # model present but prediction failed
            return _heuristic(features, note=f"heuristic (model error: {exc})")

    return _heuristic(features)


def _heuristic(features, note="heuristic (trained model unavailable)") -> dict:
    air, proc, rpm, torque, wear = features
    risk = 0.0
    modes = []
    if proc - air > 8.6 and rpm < 1380:
        risk += 0.4; modes.append("Heat Dissipation Failure")
    if torque * rpm * 2 * 3.14159 / 60 < 3500 or torque * rpm * 2 * 3.14159 / 60 > 9000:
        risk += 0.3; modes.append("Power Failure")
    if wear > 200 and torque > 45:
        risk += 0.3; modes.append("Overstrain / Tool-Wear Failure")
    return {"source": "heuristic", "failure_probability": round(min(risk, 0.95), 3),
            "predicted_modes": modes, "note": note}
