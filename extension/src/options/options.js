const DEFAULTS = { apiBaseUrl: "http://localhost:3000", authToken: "" };

function load() {
  chrome.storage.local.get(DEFAULTS, (settings) => {
    document.getElementById("apiBaseUrl").value = settings.apiBaseUrl;
    document.getElementById("authToken").value = settings.authToken;
  });
}

function save() {
  const apiBaseUrl = document.getElementById("apiBaseUrl").value.trim() || DEFAULTS.apiBaseUrl;
  const authToken = document.getElementById("authToken").value.trim();

  chrome.storage.local.set({ apiBaseUrl, authToken }, () => {
    const status = document.getElementById("status");
    status.textContent = "Saved.";
    setTimeout(() => (status.textContent = ""), 2000);
  });
}

document.getElementById("save").addEventListener("click", save);
load();
