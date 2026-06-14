import { useState } from "react";
import { AuthProvider, useAuth } from "../context/AuthContext";
import ProtectedRoute from "../components/ProtectedRoute";
import Login from "./Login.jsx";
import Register from "./Register.jsx";
import api from "../utils/axiosInstance";
import "../App.css";
import FeatureImportance from "../components/FeatureImportance";
import FeedbackWidget from "../components/FeedbackWidget";

const THEMES = {
  ocean: {
    name: "🌊 Ocean",
    light: "bg-gradient-to-br from-blue-500 via-cyan-400 to-teal-500",
    dark: "bg-gradient-to-br from-blue-900 via-cyan-900 to-teal-900",
    card: "bg-[#FAF1E6]/35",
    accent: "bg-indigo-500 hover:bg-indigo-600",
  },
  sunset: {
    name: "🌅 Sunset",
    light: "bg-gradient-to-br from-orange-400 via-pink-400 to-red-500",
    dark: "bg-gradient-to-br from-orange-900 via-pink-900 to-red-900",
    card: "bg-[#FFF5E6]/35",
    accent: "bg-orange-500 hover:bg-orange-600",
  },
  forest: {
    name: "🌿 Forest",
    light: "bg-gradient-to-br from-green-400 via-emerald-400 to-teal-500",
    dark: "bg-gradient-to-br from-green-900 via-emerald-900 to-teal-900",
    card: "bg-[#E6FAF1]/35",
    accent: "bg-green-600 hover:bg-green-700",
  },
  purple: {
    name: "💜 Purple",
    light: "bg-gradient-to-br from-purple-500 via-violet-400 to-pink-500",
    dark: "bg-gradient-to-br from-purple-900 via-violet-900 to-pink-900",
    card: "bg-[#F5E6FA]/35",
    accent: "bg-purple-600 hover:bg-purple-700",
  },
  mono: {
    name: "🖤 Mono",
    light: "bg-gradient-to-br from-gray-300 via-gray-400 to-gray-500",
    dark: "bg-gradient-to-br from-gray-900 via-gray-800 to-black",
    card: "bg-white/35",
    accent: "bg-gray-700 hover:bg-gray-800",
  },
};

function SpamDetector() {
>>>>>>> 50211f6 (feat: add multi-theme customization with light/dark mode support):frontend/src/App.jsx
  const [text, setText] = useState("");
  const [result, setResult] = useState("");
  const [confidence, setConfidence] = useState(null);
  const [loading, setLoading] = useState(false);
  const [type, setType] = useState("message");
  const [darkMode, setDarkMode] = useState(false);
  const [theme, setTheme] = useState("ocean");
  const [showThemes, setShowThemes] = useState(false);
  const { user, logout } = useAuth();

  const currentTheme = THEMES[theme];

  const handlePredict = async () => {
    if (!text) return;
    try {
      setLoading(true);
      const res = await api.post(
        `${import.meta.env.VITE_API_URI}/predict`, {
        text: text,
        type: type,
      });
      setResult(res.data.prediction);
      setConfidence(res.data.confidence ?? null);
    } catch (error) {
      setResult("Error");
    } finally {
      setLoading(false);
    }
  };

  const getColor = () => {
    if (result === "ham" || result === "safe") return "text-green-600";
    if (result === "spam" || result === "malicious") return "text-red-600";
    if (result === "smishing") return "text-orange-500";
    if (result === "Error") {
    return darkMode ? "text-yellow-300" : "text-yellow-700";
  }
  return darkMode ? "text-gray-300" : "text-gray-600";
  };

  const getBg = () => {
    if (result === "ham" || result === "safe") return "bg-[#81912F]/25 backdrop-blur-md border border-white/30";
    if (result === "spam" || result === "malicious") return "bg-red-400/20 backdrop-blur-md border border-white/30";
    if (result === "smishing") return "bg-orange-400/20 backdrop-blur-md border border-white/30";
    return "bg-white/20 backdrop-blur-md border border-white/30";
  };

  const confidencePct = confidence !== null ? Math.min(confidence * 50 + 50, 100).toFixed(1) : "0.0";

  return (
    <div className={`min-h-screen flex items-center justify-center px-4 transition-all duration-500 ${
      darkMode ? currentTheme.dark : currentTheme.light
    }`}>

      {/* Top right controls */}
      <div className="absolute top-4 right-4 flex gap-2 flex-wrap justify-end">
        {/* Theme picker */}
        <div className="relative">
          <button
            onClick={() => setShowThemes(!showThemes)}
            className={`px-4 py-2 rounded-xl font-semibold transition-all duration-300 ${
              darkMode ? "bg-gray-700 text-white hover:bg-gray-600" : "bg-white/30 text-gray-800 hover:bg-white/50"
            }`}
          >
            🎨 Theme
          </button>
          {showThemes && (
            <div className={`absolute right-0 mt-2 w-44 rounded-xl shadow-xl z-50 overflow-hidden border ${
              darkMode ? "bg-gray-800 border-gray-600" : "bg-white border-gray-200"
            }`}>
              {Object.entries(THEMES).map(([key, t]) => (
                <button
                  key={key}
                  onClick={() => { setTheme(key); setShowThemes(false); }}
                  className={`w-full text-left px-4 py-2 text-sm transition-colors ${
                    theme === key
                      ? darkMode ? "bg-gray-600 text-white font-semibold" : "bg-indigo-100 text-indigo-700 font-semibold"
                      : darkMode ? "text-gray-300 hover:bg-gray-700" : "text-gray-700 hover:bg-gray-100"
                  }`}
                >
                  {t.name}
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Dark mode toggle */}
        <button
          onClick={() => setDarkMode(!darkMode)}
          className={`px-4 py-2 rounded-xl font-semibold transition-all duration-300 ${
            darkMode ? "bg-yellow-400 text-black hover:bg-yellow-300" : "bg-gray-800 text-white hover:bg-gray-700"
          }`}
        >
          {darkMode ? "☀️ Light" : "🌙 Dark"}
        </button>

        {/* Logout */}
        <button
          onClick={logout}
          className="px-4 py-2 rounded-xl font-semibold bg-red-600 text-white hover:bg-red-500 transition-all duration-300"
        >
          Logout
        </button>
      </div>

      {/* Top left user */}
      <div className="absolute top-4 left-4">
        <span className={`text-sm font-medium px-3 py-1 rounded-full ${
          darkMode ? "bg-gray-700 text-gray-300" : "bg-white/30 text-gray-800"
        }`}>
          👤 {user?.username}
        </span>
      </div>

      {/* Main card */}
      <div className={`w-full max-w-lg backdrop-blur-xl border rounded-3xl shadow-2xl p-6 sm:p-8 text-center transition-all duration-500 ${
        darkMode ? "bg-gray-900/40 border-gray-600" : "bg-white/20 border-white/20"
      }`}>
        <div className={`w-full max-w-md rounded-2xl shadow-3xl p-6 sm:p-8 text-center mx-auto transition-all duration-500 ${
          darkMode ? "bg-gray-800/70 text-white" : `${currentTheme.card} text-black`
        }`}>

          <h1 className={`text-3xl font-bold mb-2 ${darkMode ? "text-white" : "text-black"}`}>
            📨 Spam Detector
          </h1>

          <p className={`font-semibold text-sm mb-4 ${darkMode ? "text-gray-300" : "text-gray-700"}`}>
            Analyze messages, emails & URLs instantly
          </p>

          <div className="flex mb-4 bg-gray-100 rounded-xl overflow-hidden">
            <select
              value={type}
              onChange={(e) => setType(e.target.value)}
              className={`w-full p-3 rounded-xl border border-gray-200 focus:outline-none focus:ring-2 focus:ring-indigo-500 ${
                darkMode ? "bg-gray-700 text-white" : "bg-white text-black"
              }`}
            >
              <option value="message">Message</option>
              <option value="email">Email</option>
              <option value="url">URL</option>
            </select>
          </div>

          <textarea
            className={`w-full border border-gray-300 p-3 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-400 resize-none text-sm sm:text-base transition mt-4 ${
              darkMode ? "bg-gray-700 text-white" : "bg-white text-black"
            }`}
            rows="4"
            placeholder={
              type === "url" ? "Enter URL to check..." :
              type === "message" ? "Type your message..." :
              "Paste your email content..."
            }
            value={text}
            onChange={(e) => setText(e.target.value)}
          />

          <button
            onClick={handlePredict}
            className={`mt-4 w-full py-3 rounded-xl font-medium text-white active:scale-95 transition-all ${currentTheme.accent}`}
          >
            {loading ? "Analyzing..." : `Analyze ${type === "url" ? "URL" : type}`}
          </button>

          {result && (
            <div className="mt-3 border border-gray-300 rounded-xl p-2">
              <div className={`p-4 rounded-xl font-semibold transition-all duration-300 ${getBg()} ${getColor()}`}>
                {result === "ham" && "✅ Safe Message"}
                {result === "spam" && "🚫 Spam Detected"}
                {result === "smishing" && "⚠️ Fraud Alert"}
                {result === "safe" && "✅ Safe URL"}
                {result === "malicious" && "🚨 Malicious URL"}
                {result === "Error" && "⚠️ Something went wrong"}
              </div>
            </div>
          )}

          {result && confidence !== null && result !== "Error" && (
            <div className="mt-3 text-left">
              <p className={`text-xs font-medium mb-1 ${ darkMode ? "text-gray-400" : "text-gray-600" }`}>
                Model Confidence: {confidencePct}%
              </p>
              <div className="w-full bg-gray-200 rounded-full h-2">
                <div
                  className={`h-2 rounded-full transition-all duration-500 ${
                    result === "ham" ? "bg-green-500" :
                    result === "spam" ? "bg-red-500" : "bg-orange-500"
                  }`}
                  style={{ width: `${confidencePct}%` }}
                />
              </div>
            </div>
          )}

          {result && result !== "Error" && type !== "url" && (
            <FeedbackWidget
              key={`${text}|${result}|${confidence}`}
              text={text}
              predictedLabel={result}
              darkMode={darkMode}
            />
          )}

          <button
            onClick={() => { setText(""); setResult(""); setConfidence(null); setType("message"); }}
            className="mt-3 w-full py-3 rounded-xl font-medium bg-gray-500 text-white hover:bg-gray-600 transition-all"
          >
            Reset
          </button>

          <FeatureImportance darkMode={darkMode} />

        </div>
      </div>
    </div>
  );
}

export default SpamDetector;