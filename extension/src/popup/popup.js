function refreshStatus() {
  chrome.runtime.sendMessage({ type: "GET_SETTINGS" }, (response) => {
    const statusEl = document.getElementById("status");
    const settings = response?.data || {};
    if (settings.authToken) {
      statusEl.textContent = `Connected to ${settings.apiBaseUrl}`;
      statusEl.className = "ok";
    } else {
      statusEl.textContent = "No account token configured yet.";
      statusEl.className = "warn";
    }
  });
}

document.getElementById("rescan").addEventListener("click", () => {
  chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
    if (tabs[0]) {
      chrome.tabs.sendMessage(tabs[0].id, { type: "RESCAN_ALL" });
    }
  });
});

document.getElementById("openOptions").addEventListener("click", () => {
  chrome.runtime.openOptionsPage();
});

refreshStatus();
