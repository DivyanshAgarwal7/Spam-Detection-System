![License](https://img.shields.io/badge/License-MIT-green.svg)
![Docker Build](https://github.com/Userunknown84/Spam-Detection-System/actions/workflows/docker.yml/badge.svg)

# 🚀 Spam Detection System

A full-stack application that detects **Spam / Smishing / Offensive content** using Machine Learning.
The system includes:

* 🧠 ML Model (Python)
* ⚡ Python API (Flask / FastAPI)
* 🌐 Node.js Backend
* 💻 React Web App
* 📱 React Native Mobile App (Android & iOS)

---

## 📌 Project Architecture

```
User Input (Web / Mobile)
        ↓
React / React Native UI
        ↓
Node.js Backend (API Gateway)
        ↓
Python ML API (Model Inference)
        ↓
Prediction (Spam / Ham / Offensive)
```

---
## Routes

Python: (http://localhost:5000 or http://127.0.0.1:5000)
Node: (http://localhost:3000)
Reactjs: (http://localhost:5173)


---
## System Stability & Environment Fixes
This update addresses critical runtime issues that prevented the system from executing in the local development environment:

* **Security Policy Compliance:** Migrated the project to a directory with appropriate execution permissions to resolve `DLL load` errors.
* **Model Loading Error:** Corrected file path references to ensure the ML models are properly detected at runtime.
* **API Stability:** Fixed `500 Internal Server Error` by correctly serializing NumPy model outputs to JSON.

For a detailed breakdown, please refer to the recently merged Pull Request.

## 🧠 Machine Learning Model

### 📊 Dataset

* CSV format:

  * `text` / `message`
  * `label` (spam / ham / offensive)

### ⚙️ Algorithms Used

* Logistic Regression
* Naive Bayes
* Linear SVM (Best Accuracy)

### 📈 Performance

* Accuracy: ~97–98%
* Metrics:

  * Precision
  * Recall
  * F1-score
  * Confusion Matrix

---

### 🏋️ Model Training (Python)

```python
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.svm import LinearSVC
import pickle

# Load dataset
X = df['text']
y = df['label']

# Vectorization
vectorizer = TfidfVectorizer()
X_vec = vectorizer.fit_transform(X)

# Model
model = LinearSVC()
model.fit(X_vec, y)

# Save
pickle.dump(model, open("model.pkl", "wb"))
pickle.dump(vectorizer, open("vectorizer.pkl", "wb"))
```

---

## 🐍 Python API (Flask)

### 📦 Install Dependencies

```bash
pip install flask scikit-learn
```

### 🚀 API Code

```python
from flask import Flask, request, jsonify
import pickle

app = Flask(__name__)

model = pickle.load(open("model.pkl", "rb"))
vectorizer = pickle.load(open("vectorizer.pkl", "rb"))

@app.route('/predict', methods=['POST'])
def predict():
    data = request.json['text']
    vec = vectorizer.transform([data])
    prediction = model.predict(vec)[0]
    return jsonify({"result": prediction})

if __name__ == "__main__":
    app.run(port=5000)
```

---

## 🌐 Node.js Backend

### 📦 Install

```bash
npm install express axios cors
```

## Mongo Db Atlas Backend
.env

MONGODB_URI=mongodb+srv://<user>:<password>@cluster0.xxxxx.mongodb.net/spamdetection?retryWrites=true&w=majority
JWT_SECRET=your_super_secret_jwt_key_change_this_in_production
JWT_EXPIRES_IN=7d



### ⚙️ Server Code

```javascript
const express = require("express");
const axios = require("axios");
const cors = require("cors");

const app = express();
app.use(cors());
app.use(express.json());

app.post("/predict", async (req, res) => {
  try {
    const response = await axios.post("http://localhost:5000/predict", {
      text: req.body.text,
    });
    res.json(response.data);
  } catch (err) {
    res.status(500).send("Error");
  }
});

app.listen(3000, () => console.log("Node server running"));
```

---

## 💻 React Frontend

### 📦 Setup

```bash
npm create vite@latest
npm install axios
```

### ⚛️ Example Component

```javascript
import { useState } from "react";
import axios from "axios";

function App() {
  const [text, setText] = useState("");
  const [result, setResult] = useState("");

  const handlePredict = async () => {
    const res = await axios.post("http://localhost:3000/predict", { text });
    setResult(res.data.result);
  };

  return (
    <div>
      <h1>Spam Detection</h1>
      <input onChange={(e) => setText(e.target.value)} />
      <button onClick={handlePredict}>Check</button>
      <p>{result}</p>
    </div>
  );
}

export default App;
```

---

## 📱 React Native App (Android & iOS)

### 📦 Setup

```bash
npx create-expo-app
npm install axios
```

### 📲 Example Code

```javascript
import { useState } from "react";
import { View, Text, TextInput, Button } from "react-native";
import axios from "axios";

export default function App() {
  const [text, setText] = useState("");
  const [result, setResult] = useState("");

  const predict = async () => {
    const res = await axios.post("http://YOUR_IP:3000/predict", { text });
    setResult(res.data.result);
  };

  return (
    <View>
      <Text>Spam Detection</Text>
      <TextInput onChangeText={setText} />
      <Button title="Check" onPress={predict} />
      <Text>{result}</Text>
    </View>
  );
}
```
---

## 🗄️ Email Classification Database (Flask)

A MySQL-based system to store and manage classified email records.

### Database Setup

```bash
mysql -u root -p < backend/schema.sql
```

### API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/emails/` | Insert new email record |
| PATCH | `/api/emails/{id}/mark` | Mark as spam or legitimate |
| GET | `/api/emails/spam` | Retrieve all spam emails |
| GET | `/api/emails/legitimate` | Retrieve all legitimate emails |
| GET | `/api/emails/count/spam` | Count total spam emails |
| GET | `/api/emails/count/legitimate` | Count total legitimate emails |

### Export Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/emails/export?format=csv` | Download all emails as CSV |
| GET | `/api/emails/export?format=pdf` | Download all emails as PDF report |

### CSV Export Format
email_id, subject, sender, is_spam, timestamp
1, Win a FREE iPhone!!!, promo@spam.com, Spam, 2024-01-01 10:00:00
2, Team standup at 10am, manager@company.com, Legitimate, 2024-01-01 11:00:00

### PDF Report Includes
- Summary: total emails, spam count, legitimate count
- Full table with all email records

### Email Record Fields

- `email_id` — Auto-generated unique ID
- `subject` — Email subject
- `sender` — Sender email address
- `is_spam` — Boolean spam status
- `timestamp` — Record creation time

---

## 🔁 User Feedback Loop

After every prediction, the web app asks **"Was this prediction correct?"**:

* ✅ **Yes** — records the prediction as confirmed correct
* ❌ **No** — shows a dropdown to pick the correct label (`ham`, `spam`, `smishing`), then submits the correction

### How it flows

```
React Widget → POST /feedback (Node backend) → POST /feedback (Flask ML API) → feedback_store.csv
```

### `POST /feedback`

Available on both the Node backend (`/feedback`, requires authentication) and the Flask ML API (`/feedback`).

**Request body:**
```json
{
  "text": "Congratulations! You won a free prize, click here",
  "predicted_label": "ham",
  "correct_label": "spam"
}
```

**Responses:**
* `201` — `{"message": "Feedback recorded. Thank you!"}`
* `400` — `{"error": "Invalid feedback data"}` if `text` is empty or `correct_label` is not one of `ham`, `spam`, `smishing`

Feedback is appended to `backend/feedback_store.csv` (gitignored) with columns:

| Column | Description |
|--------|-------------|
| `text` | The original input text |
| `predicted_label` | What the model predicted |
| `correct_label` | What the user said it should be |
| `submitted_at` | UTC timestamp |

### Retraining the model

Once enough feedback has accumulated, run:

```bash
cd backend
python retrain.py
```

This merges `feedback_store.csv` with the original training dataset (`DATASET_PATH`, default `dataset.csv`), retrains the TF-IDF vectorizer, LinearSVC model and label encoder, and overwrites `linear_svm_model.pkl`, `tfidf_vectorizer.pkl` and `label_encoder.pkl`.

---

## 🔐 Features

* ✅ Spam / Smishing Detection
* ✅ Offensive Content Classification
* ✅ Real-time Prediction API
* ✅ Cross-platform (Web + Mobile)
* ✅ Scalable Architecture

---

## 🛡️ Email Header Analysis for Sender Verification

Features:
* **SPF validation**: Verifies if the email sender is authorized by the domain's SPF records.
* **DKIM validation**: Confirms the email signature matches the sender's public keys.
* **DMARC validation**: Validates whether alignment passes based on SPF/DKIM verification results.
* **Return-Path analysis**: Checks for mismatches between the `From` address domain and `Return-Path` domain.
* **Sender verification**: Identifies display name domain mismatch or domain alignment anomalies.

### Scoring Logic
* SPF Failure: +30 points
* DKIM Failure: +30 points
* DMARC Failure: +30 points
* Return-Path Mismatch: +20 points
* Domain Mismatch: +20 points

### Trust Levels
* `0–20` score: **Trusted**
* `21–60` score: **Suspicious**
* `61+` score: **High Risk**

### Endpoint

#### `POST /analyze-email-header`
Supports both Option A (JSON body) and Option B (`multipart/form-data` with EML file upload).

**Request (Option A - JSON):**
```json
{
  "headers": "From: Alice <alice@example.com>\nReturn-Path: <spammer@evil.com>..."
}
```

**Request (Option B - multipart/form-data):**
Submit files (EML format) under key `file`.

**Response:**
```json
{
  "success": true,
  "trust_level": "Suspicious",
  "risk_score": 45,
  "findings": [
    "SPF validation failed",
    "Return-Path mismatch detected"
  ]
}
```

---

## 📬 Gmail & Outlook Integration for Automatic Email Scanning

Allows users to link their Gmail and Outlook accounts securely via OAuth 2.0 and automatically scan the latest incoming emails.

### Features
* **OAuth 2.0 Integration**: Authorize with Google and Microsoft to scan live inboxes.
* **Inline Risk Scoring**: Integrates directly with the Sender Verification analysis module to show trust levels (Trusted, Suspicious, High Risk) for each email based on SPF, DKIM, and DMARC headers.
* **Aggregated Insights**: Displays metrics cards showing Total, Spam/Risk, and Clean emails in the scanned inbox batch.
* **Collapsible Email Reports**: Expand any scanned email to view the snippet and domain alignment validation details.

### Environment Setup

Add these credentials to your backend `.env` file:
```env
# Google OAuth 2.0 Credentials
GOOGLE_CLIENT_ID=your_google_client_id
GOOGLE_CLIENT_SECRET=your_google_client_secret

# Microsoft Graph OAuth 2.0 Credentials
MICROSOFT_CLIENT_ID=your_microsoft_client_id
MICROSOFT_CLIENT_SECRET=your_microsoft_client_secret
```

### Endpoints

| Method | Endpoint | Access | Description |
|---|---|---|---|
| `GET` | `/gmail/auth-url` | Protected | Returns the Google OAuth 2.0 consent page URL |
| `GET` | `/gmail/connect` | Protected | Exchanges the authorization code for Gmail access/refresh tokens |
| `GET` | `/gmail/emails` | Protected | Fetches up to 50 of the latest Gmail emails |
| `GET` | `/outlook/auth-url` | Protected | Returns the Microsoft Graph OAuth 2.0 consent page URL |
| `GET` | `/outlook/connect` | Protected | Exchanges the authorization code for Microsoft Graph tokens |
| `GET` | `/outlook/emails` | Protected | Fetches up to 50 of the latest Outlook emails |
| `POST` | `/scan-emails` | Protected | Fetches latest emails for provider and runs ML classification and header verification |

---

## 🧠 Spam Pattern Insights & Analytics Dashboard

Features:
* **Top keywords frequency**: Displays the most common keywords associated with threats.
* **Trending phrases**: Analyzes bigrams/trigrams to identify key word sequences in spam (e.g. `claim your prize`).
* **Suspicious terms tracking**: Extracts recently flagged tokens from threat classifications.
* **Category indicators**: Groups common threat indicators by category (Spam, Smishing, Offensive).

### Endpoint

#### `GET /spam-insights`
Available on both the Node backend (`/spam-insights`, requires authentication) and the Flask ML API (`/spam-insights`).

**Query Parameters:**
- `limit` (optional, default: 10): Limits the number of keywords/phrases returned.
- `category` (optional, e.g. `spam`): Filters the source metrics to a specific threat category.

**Example Response:**
```json
{
  "top_keywords": [
    {"keyword": "free", "count": 45},
    {"keyword": "prize", "count": 35}
  ],
  "trending_phrases": [
    {"phrase": "click here now", "count": 25},
    {"phrase": "claim your prize", "count": 20}
  ],
  "recent_suspicious_terms": [
    "crypto giveaway",
    "verify wallet"
  ],
  "category_indicators": {
    "spam": ["free", "prize", "winner"],
    "smishing": ["otp", "verify", "bank"],
    "offensive": ["abusive", "hate"]
  }
}
```

---

## 📁 Bulk Spam Detection

Features:
* **CSV upload**: Upload a CSV file containing either a `text` or `message` column header (case-insensitive) to run batch predictions.
* **TXT upload**: Upload a TXT file containing one message per non-empty line.
* **Bulk predictions**: Batch inference is performed efficiently on the ML model.
* **Detection statistics**: Displays total messages, spam/non-spam counts, and spam percentages.
* **CSV report export**: Downloadable CSV file containing the original message and predicted classification.

### Endpoints

#### `POST /bulk-predict`
Requires `multipart/form-data` file upload with a key name of `file`.

**Example Response:**
```json
{
  "total_messages": 3,
  "spam_count": 2,
  "non_spam_count": 1,
  "spam_percentage": 66.67,
  "results": [
    {
      "message": "Congratulations! You won a free prize",
      "prediction": "spam"
    },
    {
      "message": "Meeting tomorrow at 10am",
      "prediction": "ham"
    }
  ]
}
```

#### `POST /bulk-predict/export`
Requires `multipart/form-data` file upload with a key name of `file`. Returns a downloadable CSV report file:
```csv
message,prediction
Congratulations! You won a free prize,spam
Meeting tomorrow at 10am,ham
```

---

## 🎨 Theme Customization System

The frontend now includes a fully customizable theme system that allows users to personalize the application's appearance.

## Features
Added 5 unique themes:
Ocean
Sunset
Forest
Purple
Mono

## Theme selector accessible through the 🎨 Theme button in the top-right corner.
Full support for Light Mode and Dark Mode across all themes.
Dynamic adaptation of:
Background gradients
Cards and panels
Buttons and accent colors
Interactive UI elements
Theme preferences are maintained throughout the user's active session.
Seamless theme switching without affecting application functionality.


---

## 🛠 Tech Stack

* Python (ML + API)
* Scikit-learn
* Flask
* Node.js
* Express
* React
* React Native
* Axios

---

## 📌 Future Improvements

*  Use Deep Learning (LSTM / BERT / CLIP)
*  Multilingual Support
*  More accuracy and advanced model 
* Include Email predicton perfectly and add mobile numbers also to track
* Include Url prediction perfectly to check url is safe or not

---

## 🐳 Running with Docker

> ✅ All three images (`ml-api`, `node-backend`, `frontend`) are automatically built and the ML API is smoke-tested via [GitHub Actions](.github/workflows/docker.yml) on every push and pull request to `main`, so the Dockerfiles always stay in sync with the latest code.

### Prerequisites
- [Docker](https://docs.docker.com/get-docker/) installed
- [Docker Compose](https://docs.docker.com/compose/install/) installed

### Docker Hub Images

Pre-built images are available — no build step required:

| Service | Docker Hub |
|---|---|
| Flask ML API | [rudra2006/spam-ml-api](https://hub.docker.com/r/rudra2006/spam-ml-api) |
| Node.js Backend | [rudra2006/spam-node-backend](https://hub.docker.com/r/rudra2006/spam-node-backend) |
| React Frontend | [rudra2006/spam-frontend](https://hub.docker.com/r/rudra2006/spam-frontend) |

### Quick Start (New Users — No Clone Needed)

Images are pre-built on Docker Hub. Just download the compose file and run:

```bash
curl -O https://raw.githubusercontent.com/Userunknown84/Spam-Detection-System/main/docker-compose.yml
docker-compose up
```

Docker will automatically pull all 3 images. No build step, no clone required.

### Quick Start (From Source)

```bash
git clone https://github.com/Userunknown84/Spam-Detection-System.git
cd Spam-Detection-System
docker-compose up --build
```

| Service | URL |
|---|---|
| React Frontend | http://localhost |
| Node.js Backend | http://localhost:3000 |
| Flask ML API | http://localhost:5000 |

### Stop all containers
```bash
docker-compose down
```

### Architecture in Docker

```
Browser → nginx (port 80) → node-backend (port 3000) → ml-api (port 5000)
```

- **ml-api**: Python Flask service that loads the SVM model and serves `/predict`
- **node-backend**: Node.js API gateway forwarding requests to ml-api
- **frontend**: React app built with Vite, served via nginx; nginx proxies `/predict` to node-backend

---

## 👨‍💻 Author

Aditya Sharma

---

## ⭐ Contribute

Feel free to fork, improve and contribute to this project!

---

## 📜 License

This project is open-source and available under the MIT License.

You are free to use, modify, and distribute this project for personal or commercial use, provided that proper credit is given.

For more details, see the [LICENSE](LICENSE) file.


