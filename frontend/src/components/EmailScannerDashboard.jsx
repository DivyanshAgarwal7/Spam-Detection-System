import { useState, useEffect } from "react";
import { useTheme } from "../context/ThemeContext";
import api from "../utils/axiosInstance";

export default function EmailScannerDashboard() {
  const { isDark, activeTheme } = useTheme();

  // Connection states
  const [gmailConnected, setGmailConnected] = useState(null); // null (checking), true, false
  const [outlookConnected, setOutlookConnected] = useState(null);

  // Loading states
  const [loadingGmail, setLoadingGmail] = useState(false);
  const [loadingOutlook, setLoadingOutlook] = useState(false);
  const [scanning, setScanning] = useState(false);

  // Result and UI states
  const [activeProvider, setActiveProvider] = useState(null); // 'gmail' or 'outlook'
  const [scanResults, setScanResults] = useState(null);
  const [expandedEmailId, setExpandedEmailId] = useState(null);
  const [error, setError] = useState("");
  const [successMsg, setSuccessMsg] = useState("");

  // Check connectivity on mount
  useEffect(() => {
    checkConnectionStatus();
    handleOAuthCallback();
  }, []);

  const checkConnectionStatus = async () => {
    // Check Gmail
    try {
      await api.get("/gmail/emails");
      setGmailConnected(true);
    } catch (err) {
      setGmailConnected(false);
    }

    // Check Outlook
    try {
      await api.get("/outlook/emails");
      setOutlookConnected(true);
    } catch (err) {
      setOutlookConnected(false);
    }
  };

  const handleOAuthCallback = async () => {
    const params = new URLSearchParams(window.location.search);
    const provider = params.get("provider");
    const code = params.get("code");

    if (provider && code) {
      setError("");
      setSuccessMsg("");
      if (provider === "gmail") setLoadingGmail(true);
      else setLoadingOutlook(true);

      try {
        await api.get(`/${provider}/connect?code=${code}`);
        setSuccessMsg(`${provider === "gmail" ? "Gmail" : "Outlook"} connected successfully!`);
        if (provider === "gmail") setGmailConnected(true);
        else setOutlookConnected(true);
        setActiveProvider(provider);
        // Automatically scan emails
        handleScan(provider);
      } catch (err) {
        setError(err.response?.data?.error || `Failed to connect ${provider}.`);
      } finally {
        setLoadingGmail(false);
        setLoadingOutlook(false);
        // Clean URL query parameters
        window.history.replaceState({}, document.title, window.location.pathname);
      }
    }
  };

  const handleConnect = async (provider) => {
    setError("");
    setSuccessMsg("");
    if (provider === "gmail") setLoadingGmail(true);
    else setLoadingOutlook(true);

    try {
      const res = await api.get(`/${provider}/auth-url`);
      if (res.data.auth_url) {
        window.location.href = res.data.auth_url;
      } else {
        throw new Error("Auth URL not returned from backend");
      }
    } catch (err) {
      setError(err.response?.data?.error || `Failed to fetch auth URL for ${provider}.`);
      if (provider === "gmail") setLoadingGmail(false);
      else setLoadingOutlook(false);
    }
  };

  const handleScan = async (provider) => {
    if (!provider) return;
    setScanning(true);
    setError("");
    setSuccessMsg("");
    setScanResults(null);
    setExpandedEmailId(null);
    setActiveProvider(provider);

    try {
      const res = await api.post("/scan-emails", { provider });
      setScanResults(res.data);
      setSuccessMsg(`Successfully scanned ${res.data.total_scanned} emails from ${provider === "gmail" ? "Gmail" : "Outlook"}!`);
    } catch (err) {
      setError(err.response?.data?.error || `Failed to scan ${provider} emails.`);
    } finally {
      setScanning(false);
    }
  };

  const toggleExpandEmail = (id) => {
    setExpandedEmailId(expandedEmailId === id ? null : id);
  };

  const getPredictionColor = (pred) => {
    const p = pred.toLowerCase();
    if (p === "ham" || p === "safe") return "text-green-600 dark:text-green-400 bg-green-500/10 border-green-500/30";
    if (p === "spam" || p === "malicious") return "text-red-650 dark:text-red-400 bg-red-500/10 border-red-500/30";
    if (p === "smishing" || p === "offensive") return "text-orange-600 dark:text-orange-400 bg-orange-500/10 border-orange-500/30";
    return "text-slate-600 dark:text-slate-400 bg-slate-500/10 border-slate-500/30";
  };

  const getTrustBadgeClass = (level) => {
    if (!level) return "";
    const l = level.toLowerCase();
    if (l === "trusted") return "text-green-700 bg-green-100 dark:text-green-300 dark:bg-green-950/40 border border-green-500/20";
    if (l === "high risk") return "text-red-750 bg-red-100 dark:text-red-350 dark:bg-red-950/40 border border-red-500/20";
    return "text-orange-700 bg-orange-100 dark:text-orange-350 dark:bg-orange-950/40 border border-orange-500/20";
  };

  return (
    <div className="flex flex-col gap-5 text-left mt-2">
      <p className="font-semibold text-xs opacity-75 text-center mb-1 leading-relaxed">
        Connect your email inbox to automatically scan incoming messages for spam, malicious links, and sender spoofing.
      </p>

      {/* Connection Status Section */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        {/* Gmail Card */}
        <div className={`p-5 rounded-2xl border transition-all duration-300 ${
          isDark ? "bg-slate-900/40 border-slate-800" : "bg-white/45 border-slate-200"
        } flex flex-col justify-between`}>
          <div>
            <div className="flex items-center justify-between mb-3">
              <span className="text-2xl">📧</span>
              <span className={`text-[10px] font-extrabold uppercase px-2.5 py-1 rounded-full border ${
                gmailConnected === true 
                  ? "text-green-600 bg-green-500/10 border-green-500/20" 
                  : gmailConnected === false 
                  ? "text-slate-500 bg-slate-500/10 border-slate-500/20" 
                  : "text-blue-500 bg-blue-500/10 border-blue-500/20 animate-pulse"
              }`}>
                {gmailConnected === true ? "Connected" : gmailConnected === false ? "Disconnected" : "Checking..."}
              </span>
            </div>
            <h3 className="text-base font-bold mb-1">Gmail Inbox</h3>
            <p className="text-[11px] opacity-70 mb-4 font-medium leading-relaxed">
              Scan emails using Google Gmail API. Requires authorization.
            </p>
          </div>

          <div className="flex gap-2">
            {gmailConnected === true ? (
              <>
                <button
                  onClick={() => handleScan("gmail")}
                  disabled={scanning || loadingGmail}
                  className={`flex-grow py-2.5 rounded-xl font-bold text-xs text-white shadow-md active:scale-95 transition-all ${activeTheme.accent}`}
                >
                  {scanning && activeProvider === "gmail" ? "Scanning..." : "Scan Inbox"}
                </button>
                <button
                  onClick={() => handleConnect("gmail")}
                  disabled={scanning || loadingGmail}
                  className={`px-3 py-2.5 rounded-xl font-bold text-xs border transition-all ${
                    isDark ? activeTheme.btnSecondaryDark : activeTheme.btnSecondary
                  }`}
                  title="Reconnect Google Account"
                >
                  🔄
                </button>
              </>
            ) : (
              <button
                onClick={() => handleConnect("gmail")}
                disabled={loadingGmail || gmailConnected === null}
                className={`w-full py-2.5 rounded-xl font-bold text-xs text-white shadow-md active:scale-95 transition-all bg-red-600 hover:bg-red-750`}
              >
                {loadingGmail ? "Connecting..." : "Connect Gmail"}
              </button>
            )}
          </div>
        </div>

        {/* Outlook Card */}
        <div className={`p-5 rounded-2xl border transition-all duration-300 ${
          isDark ? "bg-slate-900/40 border-slate-800" : "bg-white/45 border-slate-200"
        } flex flex-col justify-between`}>
          <div>
            <div className="flex items-center justify-between mb-3">
              <span className="text-2xl">📬</span>
              <span className={`text-[10px] font-extrabold uppercase px-2.5 py-1 rounded-full border ${
                outlookConnected === true 
                  ? "text-green-600 bg-green-500/10 border-green-500/20" 
                  : outlookConnected === false 
                  ? "text-slate-500 bg-slate-500/10 border-slate-500/20" 
                  : "text-blue-500 bg-blue-500/10 border-blue-500/20 animate-pulse"
              }`}>
                {outlookConnected === true ? "Connected" : outlookConnected === false ? "Disconnected" : "Checking..."}
              </span>
            </div>
            <h3 className="text-base font-bold mb-1">Outlook Inbox</h3>
            <p className="text-[11px] opacity-70 mb-4 font-medium leading-relaxed">
              Scan emails using Microsoft Graph API. Requires authorization.
            </p>
          </div>

          <div className="flex gap-2">
            {outlookConnected === true ? (
              <>
                <button
                  onClick={() => handleScan("outlook")}
                  disabled={scanning || loadingOutlook}
                  className={`flex-grow py-2.5 rounded-xl font-bold text-xs text-white shadow-md active:scale-95 transition-all ${activeTheme.accent}`}
                >
                  {scanning && activeProvider === "outlook" ? "Scanning..." : "Scan Inbox"}
                </button>
                <button
                  onClick={() => handleConnect("outlook")}
                  disabled={scanning || loadingOutlook}
                  className={`px-3 py-2.5 rounded-xl font-bold text-xs border transition-all ${
                    isDark ? activeTheme.btnSecondaryDark : activeTheme.btnSecondary
                  }`}
                  title="Reconnect Microsoft Account"
                >
                  🔄
                </button>
              </>
            ) : (
              <button
                onClick={() => handleConnect("outlook")}
                disabled={loadingOutlook || outlookConnected === null}
                className={`w-full py-2.5 rounded-xl font-bold text-xs text-white shadow-md active:scale-95 transition-all bg-blue-600 hover:bg-blue-750`}
              >
                {loadingOutlook ? "Connecting..." : "Connect Outlook"}
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Messages */}
      {error && (
        <div className="p-3 text-xs font-semibold rounded-xl bg-red-500/10 border border-red-500/35 text-red-500">
          ⚠️ {error}
        </div>
      )}
      {successMsg && (
        <div className="p-3 text-xs font-semibold rounded-xl bg-green-500/10 border border-green-500/35 text-green-650 dark:text-green-400">
          💡 {successMsg}
        </div>
      )}

      {/* Scanning status banner */}
      {scanning && (
        <div className={`p-8 rounded-2xl border text-center ${
          isDark ? "bg-slate-900/20 border-slate-800" : "bg-white/10 border-slate-200"
        }`}>
          <div className="inline-block animate-spin text-2xl mb-2">🔄</div>
          <p className="text-xs font-bold">Retrieving and analyzing your latest emails...</p>
          <p className="text-[10px] opacity-60 mt-1">This will evaluate the spam risk and verify sender domains.</p>
        </div>
      )}

      {/* Scan Results Display */}
      {scanResults && (
        <div className="flex flex-col gap-4 mt-2 transition-all duration-300">
          {/* Stats Summary Cards */}
          <div className="grid grid-cols-3 gap-3 text-center">
            <div className={`p-3 rounded-xl border ${isDark ? "bg-slate-900/30 border-slate-850" : "bg-white/40 border-slate-150"}`}>
              <span className="text-[10px] font-extrabold opacity-60 block uppercase">Total Scanned</span>
              <span className="text-xl font-black">{scanResults.total_scanned}</span>
            </div>
            <div className={`p-3 rounded-xl border bg-red-500/5 ${isDark ? "border-red-950/80" : "border-red-200"}`}>
              <span className="text-[10px] font-extrabold text-red-500 opacity-80 block uppercase">Spam / Risk</span>
              <span className="text-xl font-black text-red-600 dark:text-red-400">{scanResults.spam_count}</span>
            </div>
            <div className={`p-3 rounded-xl border bg-green-500/5 ${isDark ? "border-green-950/80" : "border-green-200"}`}>
              <span className="text-[10px] font-extrabold text-green-500 opacity-80 block uppercase">Clean</span>
              <span className="text-xl font-black text-green-600 dark:text-green-400">{scanResults.safe_count}</span>
            </div>
          </div>

          {/* Emails list table */}
          <div className={`border rounded-2xl overflow-hidden ${
            isDark ? "border-slate-800 bg-slate-900/20" : "border-slate-200 bg-white/20"
          }`}>
            <div className={`p-3 border-b text-xs font-extrabold uppercase tracking-wider ${
              isDark ? "bg-slate-900/60 border-slate-850 opacity-60" : "bg-slate-100/60 border-slate-200 opacity-70"
            }`}>
              Email Scanning Report
            </div>

            {scanResults.emails && scanResults.emails.length > 0 ? (
              <div className="divide-y divide-slate-200 dark:divide-slate-850 max-h-[350px] overflow-y-auto">
                {scanResults.emails.map((email) => {
                  const isExpanded = expandedEmailId === email.id;
                  const formattedDate = email.date ? new Date(email.date).toLocaleDateString(undefined, {
                    month: "short",
                    day: "numeric",
                    hour: "2-digit",
                    minute: "2-digit"
                  }) : "Unknown Date";

                  return (
                    <div key={email.id} className="transition-colors hover:bg-slate-500/5">
                      {/* Summary Row */}
                      <div 
                        onClick={() => toggleExpandEmail(email.id)}
                        className="p-3.5 flex items-center justify-between gap-3 cursor-pointer text-xs"
                      >
                        <div className="flex-1 min-w-0">
                          <div className="flex justify-between items-center gap-2 mb-1">
                            <span className="font-extrabold truncate max-w-[150px]">
                              {email.sender.replace(/<.*>/, "").trim() || email.sender}
                            </span>
                            <span className="opacity-50 text-[10px] shrink-0 font-semibold">{formattedDate}</span>
                          </div>
                          <p className="font-semibold text-slate-800 dark:text-slate-200 truncate pr-4">
                            {email.subject || "No Subject"}
                          </p>
                        </div>

                        <div className="flex items-center gap-2 shrink-0">
                          <span className={`px-2 py-0.5 rounded text-[10px] font-extrabold uppercase border ${getPredictionColor(email.prediction)}`}>
                            {email.prediction}
                          </span>
                          <span className="opacity-40">{isExpanded ? "▲" : "▼"}</span>
                        </div>
                      </div>

                      {/* Details Area */}
                      {isExpanded && (
                        <div className={`p-3.5 border-t text-xs font-semibold ${
                          isDark ? "bg-slate-950/30 border-slate-900" : "bg-slate-50/50 border-slate-150"
                        }`}>
                          {/* Subject / Sender details */}
                          <div className="mb-2">
                            <span className="opacity-50 text-[10px] uppercase font-bold block mb-0.5">Sender</span>
                            <span className="font-bold font-mono text-slate-700 dark:text-slate-300 break-all">
                              {email.sender}
                            </span>
                          </div>

                          {/* Email Body preview */}
                          <div className="mb-3">
                            <span className="opacity-50 text-[10px] uppercase font-bold block mb-0.5">Content Preview</span>
                            <p className="text-slate-800 dark:text-slate-200 italic leading-relaxed whitespace-pre-line bg-slate-500/5 p-2.5 rounded-lg border border-slate-550/10 font-normal">
                              {email.body || "(No message body content)"}
                            </p>
                          </div>

                          {/* Phishing sender alignment results (if available) */}
                          {email.trust_level && (
                            <div className={`p-3 rounded-xl border ${
                              email.trust_level === "Trusted" 
                                ? "bg-green-500/5 border-green-500/20" 
                                : email.trust_level === "High Risk"
                                ? "bg-red-500/5 border-red-500/20"
                                : "bg-orange-500/5 border-orange-500/20"
                            }`}>
                              <div className="flex justify-between items-center mb-1">
                                <span className="text-[10px] uppercase font-extrabold opacity-60">Sender Verification</span>
                                <span className={`px-2 py-0.5 rounded-full text-[9px] font-extrabold uppercase ${getTrustBadgeClass(email.trust_level)}`}>
                                  {email.trust_level}
                                </span>
                              </div>
                              {email.risk_score !== undefined && (
                                <div className="flex justify-between items-center text-[11px] font-bold">
                                  <span>Domain Authentication Risk Score:</span>
                                  <span className={email.risk_score > 60 ? "text-red-550" : email.risk_score > 20 ? "text-orange-500" : "text-green-500"}>
                                    {email.risk_score}/100
                                  </span>
                                </div>
                              )}
                              <p className="text-[10px] opacity-75 mt-1 font-medium leading-relaxed">
                                {email.trust_level === "Trusted" 
                                  ? "Domain authentication records (SPF, DKIM, DMARC) match and align perfectly with sender headers." 
                                  : email.trust_level === "High Risk"
                                  ? "Suspicious: Domain authentication checks failed or mismatch return paths. High likelihood of email spoofing."
                                  : "Warning: Missing or incomplete authentication signatures. Domain alignment cannot be fully verified."}
                              </p>
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            ) : (
              <div className="p-8 text-center text-xs opacity-50 font-bold">
                No emails found or loaded for scanning.
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
