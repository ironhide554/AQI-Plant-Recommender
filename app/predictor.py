import os
import sys
import joblib
import numpy as np
import pandas as pd

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(CURRENT_DIR, "Voting_model.pkl")
MLB_PATH = os.path.join(CURRENT_DIR, "mlb.pkl")

# Load model and MultiLabelBinarizer once
try:
    model = joblib.load(MODEL_PATH)
    mlb = joblib.load(MLB_PATH)
except Exception as e:
    print(f"[ERROR] Error loading ML model or label binarizer from {CURRENT_DIR}: {e}")
    model = None
    mlb = None

FEATURE_ORDER = [
    "PM2.5", "PM10", "NO", "NO2", "NOx", "NH3",
    "CO", "SO2", "O3", "Benzene", "Toluene", "Xylene", "AQI"
]

def predict_plants(input_data: dict) -> dict:
    """
    Given a dictionary containing the 13 air quality parameters,
    returns the top 3 recommendations and all plant prediction confidences.
    
    Accepts keys with either 'PM2.5' or 'PM2_5'.
    """
    if model is None or mlb is None:
        raise RuntimeError("ML model or label binarizer is not loaded.")

    # Normalize keys if PM2_5 was passed instead of PM2.5
    normalized = dict(input_data)
    if "PM2_5" in normalized and "PM2.5" not in normalized:
        normalized["PM2.5"] = normalized.pop("PM2_5")

    # Validate that all required features exist
    missing_features = [f for f in FEATURE_ORDER if f not in normalized or normalized[f] is None]
    if missing_features:
        raise ValueError(f"Missing required air quality features: {missing_features}")

    # Build single-row DataFrame with strict column order
    row_data = {feat: float(normalized[feat]) for feat in FEATURE_ORDER}
    input_df = pd.DataFrame([row_data], columns=FEATURE_ORDER)

    # Predict probabilities (shape: 1 x num_classes)
    probs = model.predict_proba(input_df)
    class_probs = probs[0] if len(probs.shape) == 2 else probs

    # Build all predictions list
    all_preds = [
        {"plant": str(mlb.classes_[i]), "confidence": round(float(class_probs[i]), 2)}
        for i in range(len(mlb.classes_))
    ]

    # Rank top 3
    top3_indices = np.argsort(class_probs)[::-1][:3]
    top3_preds = [
        {"plant": str(mlb.classes_[i]), "confidence": round(float(class_probs[i]), 2)}
        for i in top3_indices
    ]

    return {
        "recommendations": top3_preds,
        "all_predictions": all_preds
    }
