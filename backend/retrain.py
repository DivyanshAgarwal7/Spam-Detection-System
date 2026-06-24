"""
retrain.py
----------
Retrains the spam-detection model using the original dataset PLUS
any accumulated user feedback, then overwrites the production model files.

Usage:
    python retrain.py
    python retrain.py --dataset dataset.csv --feedback feedback_store.csv

Behavior (per README spec):
    1. Loads the original training dataset (DATASET_PATH env var, default: dataset.csv)
    2. Loads feedback_store.csv (the corrected labels submitted via /feedback)
    3. Merges them into one training set (feedback's `correct_label` becomes the label)
    4. Retrains TfidfVectorizer + LinearSVC + LabelEncoder
    5. Overwrites:
         - linear_svm_model.pkl
         - tfidf_vectorizer.pkl
         - label_encoder.pkl
    6. Backs up the previous .pkl files (with timestamp) before overwriting,
       so a bad retrain can be rolled back.

Run this from the backend/ directory:
    cd backend
    python retrain.py
"""

import argparse
import os
import pickle
from collections import Counter

import shutil
import sys
from datetime import datetime

import pandas as pd
import joblib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.svm import LinearSVC
from sklearn.preprocessing import LabelEncoder
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report

VALID_LABELS = {"ham", "spam", "smishing"}

MODEL_PATH = "linear_svm_model.pkl"
VECTORIZER_PATH = "tfidf_vectorizer.pkl"
LABEL_ENCODER_PATH = "label_encoder.pkl"


def backup_existing_files():
    """Copy existing .pkl files to a timestamped backup folder before overwriting."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = os.path.join("backups", timestamp)
    files_to_backup = [MODEL_PATH, VECTORIZER_PATH, LABEL_ENCODER_PATH]
    existing = [f for f in files_to_backup if os.path.exists(f)]
    if not existing:
        print("No existing model files found to back up (first-time training).")
        return

    os.makedirs(backup_dir, exist_ok=True)
    for f in existing:
        shutil.copy(f, os.path.join(backup_dir, f))
    print(f"Backed up existing model files to: {backup_dir}")


def load_dataset(path):
    if not os.path.exists(path):
        print(f" Dataset not found: {path}")
        sys.exit(1)

    df = pd.read_csv(path)
    if "text" not in df.columns and "message" in df.columns:
        df.rename(columns={"message": "text"}, inplace=True)

    if "text" not in df.columns or "label" not in df.columns:
        print("Dataset CSV must have 'text' (or 'message') and 'label' columns.")
        sys.exit(1)

    df = df[["text", "label"]].dropna()
    print(f"Loaded base dataset: {len(df)} rows from {path}")
    return df


def load_feedback(path):
    if not os.path.exists(path):
        print(f"ℹ No feedback file found at {path} — training on base dataset only.")
        return pd.DataFrame(columns=["text", "label"])

    fb = pd.read_csv(path)
    required_cols = {"text", "predicted_label", "correct_label"}
    if not required_cols.issubset(fb.columns):
        print(f"  {path} is missing expected columns {required_cols}. Skipping feedback.")
        return pd.DataFrame(columns=["text", "label"])

    # Use the user-corrected label, not the model's original prediction
    fb = fb.rename(columns={"correct_label": "label"})[["text", "label"]]

    # Validate labels
    before = len(fb)
    fb = fb[fb["label"].isin(VALID_LABELS)]
    fb = fb.dropna(subset=["text", "label"])
    dropped = before - len(fb)
    if dropped > 0:
        print(f"  Dropped {dropped} feedback rows with invalid/missing labels.")

    print(f" Loaded feedback: {len(fb)} usable rows from {path}")
    return fb


def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    default_feedback = os.path.join(script_dir, "output", "feedback_store.csv")
    default_dataset = os.path.join(script_dir, "dataset.csv")

    parser = argparse.ArgumentParser(description="Retrain spam detection model with feedback data")
    parser.add_argument(
        "--dataset",
        default=os.environ.get("DATASET_PATH", default_dataset),
        help="Path to original training dataset CSV (default: dataset.csv or $DATASET_PATH)",
    )
    parser.add_argument(
        "--feedback",
        default=default_feedback,
        help="Path to feedback CSV collected from /feedback endpoint",
    )
    parser.add_argument(
        "--max-features",
        type=int,
        default=5000,
        help="Max TF-IDF vocabulary size (default: 5000, matches production model)",
    )
    parser.add_argument(
        "--test-size",
        type=float,
        default=0.2,
        help="Fraction of data held out for evaluation (default: 0.2)",
    )
    args = parser.parse_args()

    print("=" * 60)
    print("Spam Detection Model Retraining")
    print("=" * 60)

    # Step 1: Load base dataset + feedback
    base_df = load_dataset(args.dataset)
    feedback_df = load_feedback(args.feedback)

    # Step 2: Merge
    combined = pd.concat([base_df, feedback_df], ignore_index=True)
    combined = combined.drop_duplicates(subset=["text"], keep="last")  # feedback overrides duplicates
    combined = combined[combined["label"].isin(VALID_LABELS)]

    print(f"\n Combined training set: {len(combined)} rows")
    print(f"   Label distribution:\n{combined['label'].value_counts().to_string()}")

    if len(combined) < 10:
        print("Not enough data to retrain (need at least 10 rows). Aborting.")
        sys.exit(1)

    # Step 3: Encode labels
    label_encoder = LabelEncoder()
    y = label_encoder.fit_transform(combined["label"])
    print(f"\n Label encoder classes: {list(label_encoder.classes_)}")

    # Step 4: Train/test split for a quick sanity check on accuracy
    X_train_text, X_test_text, y_train, y_test = train_test_split(
        combined["text"], y, test_size=args.test_size, random_state=42, stratify=y
    )

    # Step 5: Fit vectorizer on training data only (avoid leakage)
    print(f"\n Fitting TfidfVectorizer (max_features={args.max_features})...")
    vectorizer = TfidfVectorizer(max_features=args.max_features)
    X_train_vec = vectorizer.fit_transform(X_train_text)
    X_test_vec = vectorizer.transform(X_test_text)

    # Step 6: Train model
    print("Training LinearSVC...")
    model = LinearSVC()
    model.fit(X_train_vec, y_train)

    # Step 7: Evaluate
    y_pred = model.predict(X_test_vec)
    acc = accuracy_score(y_test, y_pred)
    print(f"\nHeld-out accuracy: {acc * 100:.2f}%")
    print(classification_report(y_test, y_pred, target_names=label_encoder.classes_))

    # Step 8: Refit vectorizer + model on FULL combined data for production
    print("Refitting on full dataset for production model...")
    final_vectorizer = TfidfVectorizer(max_features=args.max_features)
    X_full_vec = final_vectorizer.fit_transform(combined["text"])
    final_model = LinearSVC()
    final_model.fit(X_full_vec, y)

    # Step 9: Backup old files, then save new ones
    backup_existing_files()

    joblib.dump(final_model, MODEL_PATH)
    joblib.dump(final_vectorizer, VECTORIZER_PATH)
    joblib.dump(label_encoder, LABEL_ENCODER_PATH)

    print(f"\n Saved: {MODEL_PATH}")
    print(f" Saved: {VECTORIZER_PATH}")
    print(f" Saved: {LABEL_ENCODER_PATH}")
    print("\n Retraining complete! Restart the ML API to load the new model.")


if __name__ == "__main__":
    main()