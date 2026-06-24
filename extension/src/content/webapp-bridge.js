(function () {
  // Runs only on the Spam Detection web app itself (not Gmail/Outlook). Picks up
  // the login token the app already stores in localStorage so the user doesn't
  // have to copy/paste it into the extension's options page by hand.
  let lastSynced = null;

  function syncToken() {
    let token;
    try {
      token = window.localStorage.getItem("token");
    } catch {
      return;
    }
    if (!token || token === lastSynced) return;
    lastSynced = token;
    chrome.runtime.sendMessage({ type: "SYNC_TOKEN", payload: { token } });
  }

  syncToken();
  setInterval(syncToken, 5000);
  // Fires in this tab when localStorage is changed from another tab/window of
  // the same origin (e.g. logging in from a second tab) — same-document writes
  // don't trigger it, which is what the interval above covers.
  window.addEventListener("storage", syncToken);
})();
