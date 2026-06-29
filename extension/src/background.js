const DEFAULT_SETTINGS = {
  apiBaseUrl: "http://localhost:3000",
  authToken: "",
};

const ALLOWED_TYPES = ["sms", "email", "url", "message"];

function getSettings() {
  return new Promise((resolve) => {
    chrome.storage.local.get(DEFAULT_SETTINGS, (stored) => resolve(stored));
  });
}

async function classify(text, type) {
  const { apiBaseUrl, authToken } = await getSettings();

  if (!authToken) {
    throw new Error("No API token configured. Open the extension options to add one.");
  }

  const safeType = ALLOWED_TYPES.includes(type) ? type : "email";

  const response = await fetch(`${apiBaseUrl.replace(/\/$/, "")}/predict`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${authToken}`,
    },
    body: JSON.stringify({ text, type: safeType }),
  });

  const data = await response.json().catch(() => ({}));

  if (!response.ok) {
    throw new Error(data.error || `Classification request failed (${response.status})`);
  }

  return data;
}

chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
  if (message?.type === "CLASSIFY") {
    classify(message.payload.text, message.payload.type)
      .then((data) => sendResponse({ ok: true, data }))
      .catch((err) => sendResponse({ ok: false, error: err.message }));
    return true; // keep the message channel open for the async response
  }

  if (message?.type === "GET_SETTINGS") {
    getSettings().then((settings) => sendResponse({ ok: true, data: settings }));
    return true;
  }

  if (message?.type === "SYNC_TOKEN") {
    chrome.storage.local.set({ authToken: message.payload.token }, () => sendResponse({ ok: true }));
    return true;
  }

  return false;
});
