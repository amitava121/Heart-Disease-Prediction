#!/usr/bin/env python3
"""Train and save the heart disease prediction model for production use."""

import joblib
import pandas as pd
from pathlib import Path
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler


PROJECT_ROOT = Path(__file__).resolve().parent
CSV_CANDIDATE_PATHS = (
    PROJECT_ROOT / "data" / "framingham.csv",
    PROJECT_ROOT / "framingham.csv",
)
FEATURE_COLUMNS = [
    "male",
    "age",
    "currentSmoker",
    "cigsPerDay",
    "BPMeds",
    "prevalentStroke",
    "prevalentHyp",
    "diabetes",
    "totChol",
    "sysBP",
    "diaBP",
    "BMI",
    "heartRate",
    "glucose",
]
MODEL_OUTPUT_PATH = PROJECT_ROOT / "model_bundle.joblib"


def load_training_data() -> pd.DataFrame:
    """Load and preprocess the training data."""
    csv_path = next((path for path in CSV_CANDIDATE_PATHS if path.exists()), None)
    if csv_path is None:
        raise FileNotFoundError(
            "framingham.csv not found. Place it at data/framingham.csv (preferred) or framingham.csv in project root."
        )

    data = pd.read_csv(csv_path)
    if "education" in data.columns:
        data = data.drop(columns=["education"])
    return data.dropna(axis=0)


def train_and_save_model() -> None:
    """Train the model and save it to disk."""
    print("Loading training data...")
    data = load_training_data()
    target = data["TenYearCHD"].astype(int)
    features = data[FEATURE_COLUMNS].astype(float)

    print("Splitting data...")
    x_train, _, y_train, _ = train_test_split(features, target, test_size=0.2, random_state=42)

    print("Training scaler...")
    scaler = StandardScaler()
    x_train_scaled = scaler.fit_transform(x_train)

    print("Training model...")
    model = LogisticRegression(max_iter=2000)
    model.fit(x_train_scaled, y_train)

    defaults = {col: float(features[col].median()) for col in FEATURE_COLUMNS}
    bundle = {
        "scaler": scaler,
        "model": model,
        "defaults": defaults,
        "feature_columns": FEATURE_COLUMNS,
    }

    print(f"Saving model bundle to {MODEL_OUTPUT_PATH}...")
    joblib.dump(bundle, MODEL_OUTPUT_PATH)
    print("Model saved successfully!")


if __name__ == "__main__":
    train_and_save_model()
