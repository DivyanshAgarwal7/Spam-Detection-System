(function (root) {
  // Content scripts can't call the backend directly (no host permissions for
  // arbitrary user-configured API URLs + CORS), so classification requests are
  // relayed through the background service worker, which holds the API
  // base URL/token in chrome.storage.local.
  function classify(text, type, runtime) {
    const messaging = runtime || (typeof chrome !== "undefined" ? chrome.runtime : null);
    if (!messaging) {
      return Promise.reject(new Error("Extension messaging runtime is unavailable"));
    }
    return new Promise((resolve, reject) => {
      messaging.sendMessage({ type: "CLASSIFY", payload: { text, type } }, (response) => {
        if (!response) {
          reject(new Error("No response from background worker"));
          return;
        }
        if (!response.ok) {
          reject(new Error(response.error || "Classification failed"));
          return;
        }
        resolve(response.data);
      });
    });
  }

  const classifierModule = { classify };

  if (typeof module !== "undefined" && module.exports) {
    module.exports = classifierModule;
  } else {
    root.SDS = root.SDS || {};
    root.SDS.classifier = classifierModule;
  }
})(typeof window !== "undefined" ? window : globalThis);
