from flask import Flask, request, jsonify
import csv
import joblib
import os
import re
from urllib.parse import urlparse
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

MODEL_PATH = os.getenv("MODEL_PATH")
VECTORIZER_PATH = os.getenv("VECTORIZER_PATH")
LABEL_ENCODER_PATH = os.getenv("LABEL_ENCODER_PATH")

if not MODEL_PATH or not VECTORIZER_PATH or not LABEL_ENCODER_PATH:
    raise ValueError("Required environment variables are missing")

model = joblib.load(MODEL_PATH)
vectorizer = joblib.load(VECTORIZER_PATH)
label_encoder = joblib.load(LABEL_ENCODER_PATH)

URL_MODEL_PATH = os.getenv("URL_MODEL_PATH", "url_detector.pkl")
URL_VECTORIZER_PATH = os.getenv("URL_VECTORIZER_PATH", "url_vectorizer.pkl")

url_model = joblib.load(URL_MODEL_PATH)
url_vectorizer = joblib.load(URL_VECTORIZER_PATH)

# url_detector.pkl predicts numeric classes with no bundled label encoder
URL_LABELS = {0: "malicious", 1: "safe"}

# Heuristic checks to catch obviously malicious URL patterns that the
# model is too biased toward "safe" to flag on its own.
SUSPICIOUS_TLDS = {
    "tk", "ml", "ga", "cf", "gq", "xyz", "top", "work", "click", "loan", "men", "review",
}
IPV4_RE = re.compile(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$")


def heuristic_url_is_malicious(url):
    candidate = url if "://" in url else f"http://{url}"
    host = urlparse(candidate).hostname or ""

    if "@" in url:
        return True
    if IPV4_RE.match(host):
        return True
    if host.startswith("xn--") or ".xn--" in host:
        return True
    if host.count("-") >= 3:
        return True
    tld = host.rsplit(".", 1)[-1] if "." in host else ""
    return tld in SUSPICIOUS_TLDS


FEEDBACK_FILE = "feedback_store.csv"
FEEDBACK_LABELS = set(label_encoder.classes_)


@app.route("/")
def home():
    return "ML API Running 🚀"


@app.route("/predict", methods=["POST"])
def predict():
    try:
        data = request.get_json()

        text = data.get("text")
        input_type = data.get("type", "message")
        if not text:
            # Simple file append for warning
            with open("api.log", "a") as f:
                f.write(f"WARNING: No text provided at {__import__('datetime').datetime.now()}\n")
            return jsonify({"error": "No text provided"}), 400

        if input_type == "url":
            text_vector = url_vectorizer.transform([text])
            prediction = url_model.predict(text_vector)
            final_output = URL_LABELS.get(int(prediction[0]), "unknown")
            if final_output == "safe" and heuristic_url_is_malicious(text):
                final_output = "malicious"
        else:
            text_vector = vectorizer.transform([text])
            prediction = model.predict(text_vector)
            final_output = label_encoder.inverse_transform(prediction)[0]

        # Simple file append for prediction log
        text_preview = text[:50] + "..." if len(text) > 50 else text
        with open("api.log", "a") as f:
            from datetime import datetime
            f.write(f"{datetime.now()} - Prediction: '{text_preview}' -> {final_output}\n")
        return jsonify({"input": text, "prediction": final_output})

    except Exception as e:
        with open("api.log", "a") as f:
            from datetime import datetime
            f.write(f"{datetime.now()} - ERROR: {str(e)}\n")
        return jsonify({"error": str(e)}), 500


@app.route("/feedback", methods=["POST"])
def feedback():
    data = request.get_json(silent=True) or {}

    text = str(data.get("text", "")).strip()
    predicted_label = str(data.get("predicted_label", "")).strip()
    correct_label = str(data.get("correct_label", "")).strip()

    if not text or correct_label not in FEEDBACK_LABELS:
        return jsonify({"error": "Invalid feedback data"}), 400

    file_exists = os.path.isfile(FEEDBACK_FILE)
    with open(FEEDBACK_FILE, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(["text", "predicted_label", "correct_label", "submitted_at"])
        from datetime import datetime, timezone
        writer.writerow([text, predicted_label, correct_label, datetime.now(timezone.utc).isoformat()])

    return jsonify({"message": "Feedback recorded. Thank you!"}), 201


if __name__ == "__main__":
    FLASK_PORT = int(os.getenv("FLASK_PORT", 5000))
    app.run(host="0.0.0.0", port=FLASK_PORT, debug=True)