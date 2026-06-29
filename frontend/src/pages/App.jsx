import { useState } from "react";
import { useAuth } from "../context/AuthContext";
import { useTheme } from "../context/ThemeContext";
import api from "../utils/axiosInstance";
import "../App.css";
import FeatureImportance from "../components/FeatureImportance";
import PredictionExplanation from "../components/PredictionExplanation";
import History from "../components/History";
import WordCloud from "../components/WordCloud";
import FeedbackWidget from "../components/FeedbackWidget";
import Login from "./Login.jsx";
import Register from "./Register.jsx";
import EmailHeaderAnalyzer from "../components/EmailHeaderAnalyzer";
import BulkSpamDetection from "../components/BulkSpamDetection";
import SpamInsightsDashboard from "../components/SpamInsightsDashboard";
import EmailScannerDashboard from "../components/EmailScannerDashboard";
import Chatbot from "../components/Chatbot";
import Footer from "../components/Footer";
import InstallAppButton from "../components/InstallAppButton";
import { useNavigate } from "react-router-dom";
import RulesManager from "../components/RulesManager";

function App() {
  const navigate = useNavigate();
  const [text, setText] = useState("");
  const [result, setResult] = useState("");
  const [errorInfo, setErrorInfo] = useState(null);
  const [confidence, setConfidence] = useState(null);
  const [explanation, setExplanation] = useState(null); 
  const [loading, setLoading] = useState(false);
  const [type, setType] = useState("message");
  const [copied, setCopied] = useState(false);

  const detectType = (text) => {
    if (!text || text.trim().length === 0) return 'message';
    const trimmed = text.trim();
    if (trimmed.includes('http://') || trimmed.includes('https://')) return 'url';
    if (trimmed.includes('@') && trimmed.includes('.')) {
      const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
      if (emailRegex.test(trimmed)) return 'email';
    }
    if (trimmed.length < 160 && !trimmed.includes('\n')) return 'sms';
    return 'message';
  };


  const [darkMode, setDarkMode] = useState(false);
  const [showHistory, setShowHistory] = useState(false);
  const [theme, setTheme] = useState("ocean");
  const [showThemes, setShowThemes] = useState(false);

  const [showSettings, setShowSettings] = useState(false);
  const [activeTab, setActiveTab] = useState(() => {
    const params = new URLSearchParams(window.location.search);
    if (params.get("provider") && params.get("code")) {
      return "scanner";
    }
    return "detector";
  });

  const { user, logout } = useAuth();
  const handleLogout = () => {
    logout();
    localStorage.removeItem("user");
    navigate("/");
  };

  const {
    themeMode,
    setThemeMode,
    colorTheme,
    setColorTheme,
    isDark,
    activeTheme,
    THEME_PALETTES,
  } = useTheme();

// Map a failed /predict request to a user-facing title, message and whether
// a retry is worth offering. Prefers the structured fields the Express layer
// returns (code/retryable), with sensible fallbacks for network errors.
const classifyPredictError = (error) => {
  const data = error?.response?.data;
  const status = error?.response?.status;
  const code = data?.code;

  if (code === "ML_TIMEOUT") {
    return {
      title: "Request timed out",
      message: data.error || "The analysis service took too long to respond.",
      retryable: true,
    };
  }
  if (code === "ML_SERVICE_UNAVAILABLE") {
    return {
      title: "Service unavailable",
      message: data.error || "The analysis service is currently unavailable.",
      retryable: true,
    };
  }
  if (code === "ML_SERVICE_ERROR") {
    return {
      title: "Analysis failed",
      message: data.error || "The analysis service encountered an error.",
      retryable: true,
    };
  }
  if (code === "INVALID_INPUT" || (status >= 400 && status < 500)) {
    return {
      title: "Invalid input",
      message:
        data?.error || "Your message could not be analyzed. Please review it and try again.",
      retryable: false,
    };
  }
  // No response (network failure / CORS / server down) or unknown error.
  if (!error?.response) {
    return {
      title: "Connection problem",
      message: "Couldn't reach the server. Check your connection and try again.",
      retryable: true,
    };
  }
  return {
    title: "Something went wrong",
    message: data?.error || "An unexpected error occurred. Please try again.",
    retryable: true,
  };
};

const handlePredict = async () => {
  if (!text || text.trim().length === 0) return;
  try {
    setLoading(true);
    setErrorInfo(null);
    const res = await api.post(`${import.meta.env.VITE_API_URI}/predict`, {
      text: text,
      type: type,
    });
    setResult(res.data.prediction);
    setConfidence(res.data.confidence ?? null);
    setExplanation(res.data.explanation ?? null);
  } catch (err) {
    console.error("Predict error:", err);
    setResult("Error");
    setExplanation(null);
    setConfidence(null);
    setErrorInfo(classifyPredictError(err));
  } finally {
    setLoading(false);
  }
};

  const confidencePct =
    confidence !== null
      ? Math.min(confidence * 50 + 50, 100).toFixed(1)
      : "0.0";

  const confidenceValue = Number(confidencePct);

  const riskLevel = confidenceValue >= 80 ? "High" : confidenceValue >= 50 ? "Medium" : "Low";

  return (
    <div
      className={`min-h-screen flex flex-col items-center px-4 py-8 pb-32 transition-all duration-500 ${
        isDark ? activeTheme.dark : activeTheme.light
      }`}
    >
      {/* Top Controls */}
      <div className="absolute top-4 right-4 flex gap-3 flex-wrap justify-end">
        {/* <button
          onClick={() => setThemeMode(isDark ? 'light' : 'dark')}
          
          className="px-4 py-2.5 rounded-xl font-bold transition-all active:scale-95 flex items-center gap-2 shadow-md"
          style={{
            background: isDark ? '#fbbf24' : '#1e293b',
            color: isDark ? '#1e293b' : '#fbbf24',
            border: 'none',
            cursor: 'pointer'
          }}
        >
          {isDark ? '☀️' : '🌙'}
        </button> */}
        <InstallAppButton />
        <button
          onClick={() => setShowSettings(!showSettings)}
          className={`px-4 py-2.5 rounded-xl font-bold transition-all active:scale-95 flex items-center gap-2 shadow-md ${
            isDark
              ? "bg-slate-800 text-white hover:bg-slate-700"
              : "bg-white/35 text-slate-850 hover:bg-white/50"
          }`}
        >
          ⚙️ Customize Theme
        </button>
        <button
          onClick={handleLogout}
          className="px-4 py-2.5 rounded-xl font-bold bg-red-650 hover:bg-red-600 text-white transition-all active:scale-95 shadow-md"
        >
          Logout
        </button>
      </div>

      <div className="absolute top-4 left-4 flex items-center gap-3">
        <label className="cursor-pointer relative group">
          {user?.avatarUrl ? (
            <img src={user.avatarUrl} alt="Avatar" className="w-10 h-10 rounded-full border-2 border-slate-300 object-cover shadow-sm" />
          ) : (
            <div className={`w-10 h-10 rounded-full flex items-center justify-center text-lg shadow-sm border ${isDark ? 'bg-slate-800 border-slate-600' : 'bg-white border-slate-300'}`}>👤</div>
          )}
          <div className="absolute inset-0 bg-black/60 rounded-full flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity">
            <span className="text-[10px] text-white font-bold uppercase tracking-wider">Edit</span>
          </div>
          <input type="file" className="hidden" accept="image/*" onChange={async (e) => {
            const file = e.target.files[0];
            if (!file) return;
            const formData = new FormData();
            formData.append('avatar', file);
            try {
              const token = localStorage.getItem('token');
              const res = await api.post(`${import.meta.env.VITE_API_URI || ''}/api/v1/auth/avatar`, formData, {
                headers: {
                  'Content-Type': 'multipart/form-data',
                  Authorization: `Bearer ${token}`
                }
              });
              localStorage.setItem('user', JSON.stringify(res.data.user));
              window.location.reload();
               const file = e.target.files[0];
             if (!file) return;
             const formData = new FormData();
             formData.append('avatar', file);
             try {
                const res = await api.post(`/api/v1/auth/avatar`, formData, {
                   headers: { 
                     'Content-Type': 'multipart/form-data'
                   }
                });
                localStorage.setItem('user', JSON.stringify(res.data.user));
                login(res.data.user);
             } catch(err) {
                alert('Failed to upload avatar: ' + (err.response?.data?.error || err.message));
             }
            } catch(err) {
              alert('Failed to upload avatar: ' + (err.response?.data?.error || err.message));
            }
          }} />
        </label>
        <span
          className={`text-sm font-semibold px-4 py-2 rounded-full shadow-sm backdrop-blur-md ${
            isDark
              ? "bg-slate-800/80 text-slate-200 border border-slate-700/50"
              : "bg-white/30 text-slate-850 border border-white/20"
          }`}
        >
          {user?.username}
        </span>
      </div>

      {/* Settings Modal */}
      {showSettings && (
        <div className="fixed inset-0 bg-slate-900/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div
            className={`w-full max-w-md rounded-3xl p-6 shadow-2xl border transition-all duration-300 ${
              isDark
                ? "bg-slate-900 text-slate-100 border-slate-700"
                : "bg-white text-slate-900 border-slate-200"
            }`}
          >
            <div className="flex justify-between items-center mb-6">
              <h3 className="text-xl font-bold">🎨 Theme Settings</h3>
              <button
                onClick={() => setShowSettings(false)}
                className={`w-8 h-8 rounded-full flex items-center justify-center font-bold ${
                  isDark
                    ? "bg-slate-800 hover:bg-slate-700"
                    : "bg-slate-100 hover:bg-slate-200"
                }`}
              >
                ✕
              </button>
            </div>

            <div className="mb-6">
              <label className="block text-sm font-semibold mb-3">Theme Mode</label>
              <div className="grid grid-cols-3 gap-2">
                {[
                  { mode: "light", label: "☀️ Light" },
                  { mode: "dark", label: "🌙 Dark" },
                  { mode: "system", label: "⚙️ System" },
                ].map((item) => (
                  <button
                    key={item.mode}
                    onClick={() => setThemeMode(item.mode)}
                    className={`py-2 px-3 rounded-xl text-sm font-medium transition-all ${
                      themeMode === item.mode
                        ? activeTheme.accent
                        : isDark
                          ? "bg-slate-800 hover:bg-slate-750 text-slate-300"
                          : "bg-slate-100 hover:bg-slate-150 text-slate-700"
                    }`}
                  >
                    {item.label}
                  </button>
                ))}
              </div>
            </div>

            <div>
              <label className="block text-sm font-semibold mb-3">Color Accent</label>
              <div className="flex flex-col gap-2">
                {Object.entries(THEME_PALETTES).map(([key, value]) => (
                  <button
                    key={key}
                    onClick={() => setColorTheme(key)}
                    className={`w-full flex items-center justify-between p-3.5 rounded-xl text-left text-sm font-semibold border transition-all ${
                      colorTheme === key
                        ? isDark
                          ? "border-blue-500 bg-slate-800"
                          : "border-indigo-500 bg-slate-100"
                        : isDark
                          ? "border-slate-800 bg-slate-850 hover:bg-slate-800"
                          : "border-slate-100 bg-slate-50 hover:bg-slate-100"
                    }`}
                  >
                    <span>{value.name}</span>
                    <span className={`w-8 h-5 rounded-full ${value.light}`} />
                  </button>
                ))}
              </div>
            </div>

            <button
              onClick={() => setShowSettings(false)}
              className={`w-full mt-6 py-3 rounded-xl font-bold text-white shadow-md transition-all active:scale-95 ${activeTheme.accent}`}
            >
              Done
            </button>
          </div>
        </div>
      )}

      {/* Main card */}
      <div className="flex-1 flex items-center justify-center w-full">
        <div
          className={`w-full max-w-lg backdrop-blur-xl border rounded-3xl shadow-2xl p-6 sm:p-8 text-center transition-all duration-500 ${
            isDark
              ? "bg-slate-950/40 border-slate-750"
              : "bg-white/20 border-white/20"
          }`}
        >
          <div
            className={`w-full max-w-md rounded-2xl shadow-3xl p-6 sm:p-8 text-center mx-auto transition-all duration-500 ${
              isDark
                ? activeTheme.cardDark
                : `${activeTheme.card} backdrop-blur-md`
            }`}
          >
            <h1 className="text-3xl font-extrabold mb-2 tracking-tight">
              📨 Spam Detector
            </h1>
            <p className="font-semibold text-sm mb-6 opacity-75">
              Analyze messages, emails & URLs instantly
            </p>

            {/* Navigation Tabs */}
            <div className="flex flex-wrap justify-center gap-2 mb-6 border-b border-slate-500/20 pb-3 text-sm font-bold">
              <button
                onClick={() => setActiveTab("detector")}
                className={`pb-1 px-4 transition-all border-b-2 ${
                  activeTab === "detector"
                    ? "border-current opacity-100"
                    : "border-transparent opacity-50 hover:opacity-75"
                }`}
              >
                Spam Detector
              </button>
              <button
                onClick={() => setActiveTab("bulk")}
                className={`pb-1 px-4 transition-all border-b-2 ${
                  activeTab === "bulk"
                    ? "border-current opacity-100"
                    : "border-transparent opacity-50 hover:opacity-75"
                }`}
              >
                Bulk Detector
              </button>
              <button
                onClick={() => setActiveTab("insights")}
                className={`pb-1 px-4 transition-all border-b-2 ${
                  activeTab === "insights"
                    ? "border-current opacity-100"
                    : "border-transparent opacity-50 hover:opacity-75"
                }`}
              >
                Insights
              </button>
              <button
                onClick={() => setActiveTab("authenticity")}
                className={`pb-1 px-4 transition-all border-b-2 ${
                  activeTab === "authenticity"
                    ? "border-current opacity-100"
                    : "border-transparent opacity-50 hover:opacity-75"
                }`}
              >
                Sender Verifier
              </button>
              <button
                onClick={() => setActiveTab("scanner")}
                className={`pb-1 px-4 transition-all border-b-2 ${
                  activeTab === "scanner"
                    ? "border-current opacity-100"
                    : "border-transparent opacity-50 hover:opacity-75"
                }`}
              >
                Email Scanner
              </button>
              <button
                onClick={() => setActiveTab("rules")}
                className={`pb-1 px-4 transition-all border-b-2 ${
                  activeTab === "rules"
                    ? "border-current opacity-100"
                    : "border-transparent opacity-50 hover:opacity-75"
                }`}
              >
                Rules Manager
              </button>
              <button
                onClick={() => setActiveTab("history")}
                className={`pb-1 px-4 transition-all border-b-2 ${
                  activeTab === "history"
                    ? "border-current opacity-100"
                    : "border-transparent opacity-50 hover:opacity-75"
                }`}
              >
                History
              </button>
              <button
                onClick={() => navigate("/dashboard")}
                className="pb-1 px-4 transition-all border-b-2 border-transparent opacity-50 hover:opacity-75"
              >
                <span className="inline-flex items-center gap-1 whitespace-nowrap">
                  <span>📊</span>
                  <span>Dashboard</span>
                </span>
              </button>
            </div>

            {activeTab === "detector" ? (
              <>
                {/* Enhanced Input Section */}
                <div className="relative w-full mb-4 group text-left">
                  <textarea
                    className={`w-full border p-4 pr-12 rounded-2xl focus:outline-none focus:ring-2 resize-none text-sm sm:text-base transition-all shadow-inner leading-relaxed
                      [&::-webkit-scrollbar]:w-2
                      [&::-webkit-scrollbar-track]:bg-transparent
                      [&::-webkit-scrollbar-thumb]:rounded-full
                      ${
                        isDark
                          ? `${activeTheme.inputDark} focus:border-blue-500/50 [&::-webkit-scrollbar-thumb]:bg-slate-700 hover:[&::-webkit-scrollbar-thumb]:bg-slate-600`
                          : `${activeTheme.input} focus:border-indigo-500/50 [&::-webkit-scrollbar-thumb]:bg-slate-300 hover:[&::-webkit-scrollbar-thumb]:bg-slate-400`
                      }`}
                    rows="5"
                    placeholder={
                      type === "url"
                        ? "Paste or type the suspicious website link URL here to test..."
                        : type === "message"
                          ? "Type your SMS or chat message content here for inspection..."
                          : "Paste the full text or body of your email content here..."
                    }
                    value={text}
                    onChange={(e) => {
                      const value = e.target.value;
                      setText(value);
                      const detected = detectType(value);
                      setType(detected);
                    }}
                  />

                  {text && (
                    <button
                      onClick={() => setText("")}
                      className={`absolute top-3.5 right-3.5 w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold transition-all hover:scale-110 shadow-sm ${
                        isDark
                          ? "bg-slate-800 text-slate-400 hover:bg-slate-700 hover:text-white"
                          : "bg-slate-200 text-slate-500 hover:bg-slate-300 hover:text-slate-800"
                      }`}
                      title="Clear input"
                    >
                      ✕
                    </button>
                  )}

                  <div className="flex justify-end items-center mt-1.5 px-1 text-xs font-medium tracking-wide opacity-70">
                    {text.length > 5000 ? (
                      <span className="text-red-500 font-bold">
                        {text.length.toLocaleString()} / 5000 characters (Limit exceeded)
                      </span>
                    ) : (
                      <span className={text.length > 500 ? "text-orange-500" : ""}>
                        {text.length.toLocaleString()} characters
                      </span>
                    )}
                  </div>
                </div>

                <button
                  onClick={() => {
                    if (!text.trim()) return;
                    handlePredict();
                  }}
                  disabled={loading || text.trim().length === 0 || text.length > 5000}
                  className={`mt-2 w-full py-3.5 rounded-xl font-bold text-white shadow-md active:scale-95 transition-all disabled:opacity-70 disabled:cursor-not-allowed flex items-center justify-center gap-2 ${activeTheme.accent}`}
                >
                  {loading && (
                    <svg className="animate-spin h-4 w-4 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                    </svg>
                  )}
                  {loading ? "Analyzing..." : `Analyze ${type === "url" ? "URL" : type}`}
                </button>

                {/* Error Section */}
                {result === "Error" && errorInfo && (
                  <div
                    className={`mt-5 rounded-3xl p-5 shadow-lg border ${
                      isDark
                        ? "bg-yellow-500/10 border-yellow-600/40"
                        : "bg-yellow-50 border-yellow-300"
                    }`}
                  >
                    <div className="flex items-start gap-3">
                      <span className="text-2xl leading-none">⚠️</span>
                      <div className="flex-1">
                        <h3
                          className={`text-base font-bold ${
                            isDark ? "text-yellow-300" : "text-yellow-800"
                          }`}
                        >
                          {errorInfo.title}
                        </h3>
                        <p
                          className={`mt-1 text-sm ${
                            isDark ? "text-yellow-200/80" : "text-yellow-700"
                          }`}
                        >
                          {errorInfo.message}
                        </p>
                        {errorInfo.retryable && (
                          <button
                            onClick={handlePredict}
                            disabled={loading}
                            className={`mt-3 px-4 py-2 rounded-lg font-semibold text-sm transition-all active:scale-95 disabled:opacity-60 disabled:cursor-not-allowed ${
                              isDark
                                ? "bg-yellow-500 text-slate-900 hover:bg-yellow-400"
                                : "bg-yellow-500 text-white hover:bg-yellow-600"
                            }`}
                          >
                            {loading ? "Retrying..." : "🔄 Retry"}
                          </button>
                        )}
                      </div>
                    </div>
                  </div>
                )}

                {/* Results Section */}
                {result && result !== "Error" && (
                  <div
                    className={`mt-5 rounded-3xl p-5 shadow-lg border ${
                      isDark
                        ? "bg-slate-900/50 border-slate-700"
                        : "bg-white/70 border-slate-200"
                    }`}
                  >
                    {/* Heading */}
                    <div className="flex justify-between items-center mb-5">
                      <div className="flex items-center gap-2">
                        <h2 className="text-lg font-bold">📊 Analysis Result</h2>
                        <button
                          onClick={() => {
                            const scoreStr = confidence !== null ? ` | Confidence: ${confidencePct}%` : "";
                            const copyText = `Prediction: ${result === 'ham' || result === 'safe' ? 'Safe' : result === 'spam' || result === 'malicious' ? 'Spam/Malicious' : result === 'smishing' ? 'Fraud' : result}${scoreStr}`;
                            navigator.clipboard.writeText(copyText);
                            setCopied(true);
                            setTimeout(() => setCopied(false), 2000);
                          }}
                          className={`ml-1 w-7 h-7 flex items-center justify-center rounded-full transition-all text-[11px] ${
                            isDark ? "hover:bg-slate-700 bg-slate-800 text-slate-300" : "hover:bg-slate-200 bg-slate-100 text-slate-600"
                          }`}
                          title="Copy Result to Clipboard"
                        >
                          {copied ? "✅" : "📋"}
                        </button>
                      </div>

                      {/* Badge */}
                      <span
                        className={`px-4 py-2 rounded-full text-sm font-bold ${
                          result === "ham" || result === "safe"
                            ? "bg-green-500 text-white"
                            : result === "spam" || result === "malicious"
                              ? "bg-red-500 text-white"
                              : result === "smishing"
                                ? "bg-orange-500 text-white"
                                : "bg-yellow-500 text-white"
                        }`}
                      >
                        {result === "ham" && "✅ Safe"}
                        {result === "safe" && "✅ Safe"}
                        {result === "spam" && "🚫 Spam"}
                        {result === "malicious" && "🚨 Malicious"}
                        {result === "smishing" && "⚠️ Fraud"}
                        {result === "Error" && "⚠️ Error"}
                      </span>
                    </div>

                    {/* Confidence */}
                    {confidence !== null && result !== "Error" && (
                      <>
                        <p className="text-sm opacity-70 mb-1">Confidence Score</p>
                        <h3 className="text-3xl font-bold mb-4">{confidencePct}%</h3>
                        <div className={`w-full rounded-full h-3 mb-5 ${isDark ? "bg-slate-700" : "bg-slate-200"}`} />
                      </>
                    )}

                    {result && confidence !== null && result !== "Error" && (
                      <div className="mt-4 text-left">
                        <p className="text-xs font-semibold mb-1 opacity-70">
                          Model Confidence: {confidencePct}%
                        </p>
                        <div className={`w-full rounded-full h-2 ${isDark ? "bg-slate-800" : "bg-slate-200"}`}>
                          <div
                            className={`h-3 rounded-full transition-all duration-500 ${
                              result === "ham" || result === "safe"
                                ? "bg-green-500"
                                : result === "spam" || result === "malicious"
                                  ? "bg-red-500"
                                  : "bg-orange-500"
                            }`}
                            style={{ width: `${confidencePct}%` }}
                          />
                        </div>

                        <div className="mb-5">
                          <p className="text-sm opacity-70 mb-2">Risk Level</p>
                          <span className={`px-4 py-2 rounded-full text-sm font-semibold ${
                            riskLevel === "Low"
                              ? "bg-green-100 text-green-700"
                              : riskLevel === "Medium"
                                ? "bg-yellow-100 text-yellow-700"
                                : "bg-red-100 text-red-700"
                          }`}>
                            {riskLevel === "Low" && "🟢 Low"}
                            {riskLevel === "Medium" && "🟠 Medium"}
                            {riskLevel === "High" && "🔴 High"}
                          </span>
                        </div>

                        <div className="mt-4 mb-4">
                          <button
                            onClick={() => {
                              const fullReport = `
        📊 Spam Detection Report
        ─────────────────────
        🔍 Prediction: ${result === 'ham' || result === 'safe' ? '✅ Safe' : result === 'spam' || result === 'malicious' ? '🚫 Spam/Malicious' : result === 'smishing' ? '⚠️ Fraud' : '⚠️ Error'}
        📝 Message: ${text}
        📈 Confidence: ${confidence ? confidencePct + '%' : 'N/A'}
        ⚠️ Risk Level: ${riskLevel}
        📅 Date: ${new Date().toLocaleString()}
         ─────────────────────
        Powered by Spam Detection System`;
                              navigator.clipboard.writeText(fullReport);
                              setCopied(true);
                              setTimeout(() => setCopied(false), 2000);
                            }}
                            className={`px-4 py-2 rounded-lg text-sm font-medium transition-all flex items-center gap-2 w-full justify-center ${
                              isDark
                                ? "bg-slate-700 hover:bg-slate-600 text-slate-200"
                                : "bg-slate-200 hover:bg-slate-300 text-slate-700"
                            }`}
                          >
                            {copied ? '✅ Copied!' : '📋 Copy Full Report'}
                          </button>
                        </div>

                        <p className="text-sm opacity-75 leading-relaxed">
                          {(result === "spam" || result === "smishing" || result === "malicious") &&
                            "This content contains characteristics commonly found in spam, phishing, or malicious attacks."}
                          {(result === "ham" || result === "safe") &&
                            "No suspicious patterns were detected in this content."}
                        </p>
                      </div>
                    )}
                    <div className="mt-4 text-left">
                     <p className="text-xs font-semibold mb-1 opacity-70">
                        Model Confidence: {confidencePct}%
                        </p>
                          <div className={`w-full rounded-full h-2 ${isDark ? "bg-slate-800" : "bg-slate-200"}`}>
                           <div
                             className={`h-3 rounded-full transition-all duration-500 ${
                             result === "ham" || result === "safe"
                             ? "bg-green-500"
                             : result === "spam" || result === "malicious"
                             ? "bg-red-500"
                             : "bg-orange-500"
                            }`}
                            style={{ width: `${confidencePct}%` }}
                            />
                          </div>

                    {/* Risk Level */}
                    <div className="mb-5">
                      <p className="text-sm opacity-70 mb-2">Risk Level</p>
                      <span className={`px-4 py-2 rounded-full text-sm font-semibold ${
                      riskLevel === "Low"
                      ? "bg-green-100 text-green-700"
                      : riskLevel === "Medium"
                      ? "bg-yellow-100 text-yellow-700"
                      : "bg-red-100 text-red-700"
                    }`}>

                      {riskLevel === "Low" && "🟢 Low"}
        {riskLevel === "Medium" && "🟠 Medium"}
        {riskLevel === "High" && "🔴 High"}
      </span>
    </div>
  
    {/* Copy Full Report Button */}
    <div className="mt-4 mb-4">
      <button
        onClick={() => {
          const fullReport = `
📊 Spam Detection Report
─────────────────────
🔍 Prediction: ${result === 'ham' || result === 'safe' ? '✅ Safe' : result === 'spam' || result === 'malicious' ? '🚫 Spam/Malicious' : result === 'smishing' ? '⚠️ Fraud' : '⚠️ Error'}
📝 Message: ${text}
📈 Confidence: ${confidence ? confidencePct + '%' : 'N/A'}
⚠️ Risk Level: ${riskLevel}
📅 Date: ${new Date().toLocaleString()}
─────────────────────
Powered by Spam Detection System`;
          navigator.clipboard.writeText(fullReport);
          setCopied(true);
          setTimeout(() => setCopied(false), 2000);
        }}
        className={`px-4 py-2 rounded-lg text-sm font-medium transition-all flex items-center gap-2 w-full justify-center ${
          isDark 
            ? "bg-slate-700 hover:bg-slate-600 text-slate-200" 
            : "bg-slate-200 hover:bg-slate-300 text-slate-700"
        }`}
      >
        {copied ? '✅ Copied!' : '📋 Copy Full Report'}
      </button>
    </div>
              {explanation && result !== "Error" && (
                <PredictionExplanation explanation={explanation} result={result} />
              )}

              {result && result !== "Error" && type !== "url" && (
                <FeedbackWidget
                  key={`${text}|${result}|${confidence}`}
                  text={text}
                  predictedLabel={result}
                  darkMode={isDark}
                />
              )}

              <button
                onClick={() => {
                  setText("");
                  setResult("");
                  setConfidence(null);
                  setExplanation(null);
                  setErrorInfo(null);
                  setType("message");
                }}
                className={`mt-4 w-full py-3.5 rounded-xl font-bold shadow-sm transition-all ${
                  isDark
                    ? activeTheme.btnSecondaryDark
                    : activeTheme.btnSecondary
                }`}
              >
                Reset
              </button>

    {/* Description */}
    <p className="text-sm opacity-75 leading-relaxed">
      {(result === "spam" || result === "smishing" || result === "malicious") &&
        "This content contains characteristics commonly found in spam, phishing, or malicious attacks."}
      {(result === "ham" || result === "safe") &&
        "No suspicious patterns were detected in this content."}
    </p>
  </div>

                  </div>
                )}

                {result && result !== "Error" && type !== "url" && (
                  <FeedbackWidget
                    key={`${text}|${result}|${confidence}`}
                    text={text}
                    predictedLabel={result}
                    darkMode={isDark}
                  />
                )}

                <button
                  onClick={() => {
                    setText("");
                    setResult("");
                    setConfidence(null);
                    setErrorInfo(null);
                    setType("message");
                  }}
                  className={`mt-4 w-full py-3.5 rounded-xl font-bold shadow-sm transition-all ${
                    isDark ? activeTheme.btnSecondaryDark : activeTheme.btnSecondary
                  }`}
                >
                  Reset
                </button>

                <FeatureImportance darkMode={isDark} />
              </>
            ) : activeTab === "bulk" ? (
              <BulkSpamDetection />
            ) : activeTab === "insights" ? (
              <SpamInsightsDashboard />
            ) : activeTab === "scanner" ? (
              <EmailScannerDashboard />
            ) : activeTab === "rules" ? (
              <RulesManager />
            ) : activeTab === "history" ? (
              <History />
            ) : (
              <EmailHeaderAnalyzer />
            )}
            <WordCloud darkMode={isDark} />
          </div>
        </div>
      </div>
      <Footer />
      <Chatbot />
    </div>
  )};



export default App;