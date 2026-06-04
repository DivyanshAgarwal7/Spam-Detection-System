![License](https://img.shields.io/badge/License-MIT-green.svg)

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

## 🗄️ Email Classification Database

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

### Email Record Fields

- `email_id` — Auto-generated unique ID
- `subject` — Email subject
- `sender` — Sender email address
- `is_spam` — Boolean spam status
- `timestamp` — Record creation time

---

## 🔐 Features

* ✅ Spam / Smishing Detection
* ✅ Offensive Content Classification
* ✅ Real-time Prediction API
* ✅ Cross-platform (Web + Mobile)
* ✅ Scalable Architecture

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


