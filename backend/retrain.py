"""Retrain the spam classifier using collected user feedback (#58).

Merges `feedback_store.csv` (created by the `/feedback` endpoint in api.py)
with the original training dataset, retrains the TF-IDF vectorizer +
LinearSVC model + label encoder, and overwrites the .pkl files used by
api.py.

Usage:
    cd backend
    python retrain.py

Environment variables (all optional, same defaults as api.py):
    DATASET_PATH        Path to the original training CSV (text/message + label columns).
                         Default: dataset.csv
    FEEDBACK_PATH       Path to the feedback CSV. Default: feedback_store.csv
    MODEL_PATH          Output path for the trained model. Default: linear_svm_model.pkl
    VECTORIZER_PATH     Output path for the TF-IDF vectorizer. Default: tfidf_vectorizer.pkl
    LABEL_ENCODER_PATH  Output path for the label encoder. Default: label_encoder.pkl
"""

import csv
import os
from collections import Counter

import joblib
from dotenv import load_dotenv
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics import classification_report
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from sklearn.svm import LinearSVC

load_dotenv()

DATASET_PATH = os.getenv("DATASET_PATH", "dataset.csv")
FEEDBACK_PATH = os.getenv("FEEDBACK_PATH", "feedback_store.csv")
MODEL_PATH = os.getenv("MODEL_PATH", "linear_svm_model.pkl")
VECTORIZER_PATH = os.getenv("VECTORIZER_PATH", "tfidf_vectorizer.pkl")
LABEL_ENCODER_PATH = os.getenv("LABEL_ENCODER_PATH", "label_encoder.pkl")


def load_dataset_samples(path):
    """Read a dataset CSV with `text`/`message` and `label` columns."""
    samples = []
    if not os.path.isfile(path):
        print(f"No dataset found at '{path}', skipping.")
        return samples

    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            text = row.get("text") or row.get("message")
            label = row.get("label")
            if text and label:
                samples.append((text, label))
    print(f"Loaded {len(samples)} samples from '{path}'.")
    return samples


def load_feedback_samples(path):
    """Read feedback CSV, using the user-corrected label."""
    samples = []
    if not os.path.isfile(path):
        print(f"No feedback found at '{path}', skipping.")
        return samples

    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            text = row.get("text")
            label = row.get("correct_label")
            if text and label:
                samples.append((text, label))
    print(f"Loaded {len(samples)} samples from '{path}'.")
    return samples


def main():
    samples = load_dataset_samples(DATASET_PATH) + load_feedback_samples(FEEDBACK_PATH)
    if not samples:
        raise SystemExit("No training data found. Provide a dataset and/or feedback_store.csv.")

    texts, labels = zip(*samples)

    label_encoder = LabelEncoder()
    y = label_encoder.fit_transform(labels)

    # Hold out a test split when there's enough data per class to stratify;
    # otherwise train on everything and skip the report.
    counts = Counter(y)
    can_split = len(samples) >= 5 and min(counts.values()) >= 2
    if can_split:
        X_train, X_test, y_train, y_test = train_test_split(
            texts, y, test_size=0.2, random_state=42, stratify=y
        )
    else:
        X_train, y_train = texts, y
        X_test, y_test = [], []
        print("Not enough samples per class for a held-out test split; "
              "training on all available data.")

    vectorizer = TfidfVectorizer()
    X_train_vec = vectorizer.fit_transform(X_train)

    model = LinearSVC()
    model.fit(X_train_vec, y_train)

    if X_test:
        X_test_vec = vectorizer.transform(X_test)
        print("\nClassification Report:")
        print(classification_report(
            y_test, model.predict(X_test_vec), target_names=label_encoder.classes_
        ))

    joblib.dump(model, MODEL_PATH)
    joblib.dump(vectorizer, VECTORIZER_PATH)
    joblib.dump(label_encoder, LABEL_ENCODER_PATH)
    print(f"\nSaved model to '{MODEL_PATH}', vectorizer to '{VECTORIZER_PATH}', "
          f"label encoder to '{LABEL_ENCODER_PATH}'.")


if __name__ == "__main__":
    main()
