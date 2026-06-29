(function (root) {
  // In-memory only: never persisted to chrome.storage or disk. Cleared whenever
  // the tab/page reloads, so no message content or classification result outlives
  // the page it was scanned on (privacy requirement from issue #187).
  const DEFAULT_TTL_MS = 10 * 60 * 1000;

  function createScanCache(ttlMs) {
    const ttl = typeof ttlMs === "number" ? ttlMs : DEFAULT_TTL_MS;
    const entries = new Map();

    function get(messageId) {
      return entries.get(messageId) || null;
    }

    function set(messageId, result) {
      entries.set(messageId, {
        prediction: result.prediction,
        confidence: result.confidence,
        dismissed: false,
        scannedAt: Date.now(),
      });
      return entries.get(messageId);
    }

    function dismiss(messageId) {
      const entry = entries.get(messageId);
      if (entry) entry.dismissed = true;
    }

    function shouldRescan(messageId, forceRescan) {
      if (forceRescan) return true;
      const entry = entries.get(messageId);
      if (!entry) return true;
      if (entry.dismissed) return false;
      return Date.now() - entry.scannedAt > ttl;
    }

    function clear() {
      entries.clear();
    }

    return { get, set, dismiss, shouldRescan, clear };
  }

  const cacheModule = { createScanCache };

  if (typeof module !== "undefined" && module.exports) {
    module.exports = cacheModule;
  } else {
    root.SDS = root.SDS || {};
    root.SDS.cache = cacheModule;
  }
})(typeof window !== "undefined" ? window : globalThis);
