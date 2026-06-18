"""
generate_vectorizer.py
----------------------
Regenerates tfidf_vectorizer.pkl from your dataset.

Usage:
    python generate_vectorizer.py                      # uses dataset.csv by default
    python generate_vectorizer.py --dataset mydata.csv # custom dataset path

The dataset CSV must have two columns:
    text    - the message text
    label   - one of: ham, spam, smishing
"""

import argparse
import os
import joblib
from sklearn.feature_extraction.text import TfidfVectorizer

def main():
    parser = argparse.ArgumentParser(description="Regenerate tfidf_vectorizer.pkl")
    parser.add_argument(
        "--dataset",
        default="dataset.csv",
        help="Path to training CSV file (must have 'text' and 'label' columns)",
    )
    args = parser.parse_args()

    # Check dataset exists
    if not os.path.exists(args.dataset):
        print(f" Dataset not found: {args.dataset}")
        print("   Provide your training CSV with --dataset path/to/file.csv")
        return

    try:
        import pandas as pd
    except ImportError:
        print(" pandas is not installed. Run: pip install pandas")
        return

    print(f" Loading dataset from: {args.dataset}")
    df = pd.read_csv(args.dataset)

    # Support both 'text'/'message' column names
    if "text" not in df.columns and "message" in df.columns:
        df.rename(columns={"message": "text"}, inplace=True)

    if "text" not in df.columns or "label" not in df.columns:
        print("CSV must have 'text' (or 'message') and 'label' columns.")
        return

    print(f"Loaded {len(df)} rows")
    print(f"   Label distribution:\n{df['label'].value_counts().to_string()}")

    # Fit TF-IDF vectorizer with max_features=5000 to match model
    print("\n  Fitting TfidfVectorizer (max_features=5000)...")
    vectorizer = TfidfVectorizer(max_features=5000)
    vectorizer.fit(df["text"])

    # Save vectorizer
    output_path = "tfidf_vectorizer.pkl"
    joblib.dump(vectorizer, output_path)
    print(f"\nSaved: {output_path}")
    print(f"   Vocabulary size: {len(vectorizer.vocabulary_)}")
    print("\n Done! You can now run docker-compose up")


if __name__ == "__main__":
    main()