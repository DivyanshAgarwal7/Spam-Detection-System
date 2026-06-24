(function (root) {
  // Keeps the payload we send for classification small and strips data we don't
  // need to retain (e.g. excess whitespace from DOM text nodes).
  function truncateForClassification(text, maxLen) {
    const limit = typeof maxLen === "number" ? maxLen : 500;
    const normalized = (text || "").replace(/\s+/g, " ").trim();
    return normalized.slice(0, limit);
  }

  function badgeForPrediction(prediction) {
    const p = (prediction || "").toLowerCase();
    if (p === "ham" || p === "safe") {
      return { label: "Safe", className: "sds-badge-safe", emoji: "✅" };
    }
    if (p === "spam") {
      return { label: "Spam", className: "sds-badge-spam", emoji: "⚠️" };
    }
    if (p === "smishing") {
      return { label: "Smishing", className: "sds-badge-smishing", emoji: "🎯" };
    }
    if (p === "offensive") {
      return { label: "Offensive", className: "sds-badge-offensive", emoji: "🚫" };
    }
    return { label: "Unknown", className: "sds-badge-unknown", emoji: "❔" };
  }

  const textUtils = { truncateForClassification, badgeForPrediction };

  if (typeof module !== "undefined" && module.exports) {
    module.exports = textUtils;
  } else {
    root.SDS = root.SDS || {};
    root.SDS.textUtils = textUtils;
  }
})(typeof window !== "undefined" ? window : globalThis);
