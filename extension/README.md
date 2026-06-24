# Spam Detection Inbox Scanner (Browser Extension)

Chrome/Firefox extension (Manifest V3) that scans visible Gmail and Outlook web
messages and shows an inline spam/smishing/offensive badge, using the existing
Spam Detection System classification API as its backend. Implements issue #187.

## How it works

- Content scripts (`src/content/gmail.js`, `src/content/outlook.js`) find
  message rows in the inbox list, extract the subject + preview text, and ask
  the background service worker to classify it.
- The background service worker (`src/background.js`) holds the API base URL
  and an account token (set via the options page) and calls the existing
  `POST /predict` endpoint on the Node backend.
- Results are cached **in memory only**, per page load, keyed by the
  provider's own message/thread id. Reloading the tab clears the cache.
- Each badge has a rescan (↻) and dismiss (✕) control.

## Install (development / unpacked)

This extension is not on the Chrome Web Store or Firefox AMO — it ships as
source code in this repo, inside the `extension/` folder. You need that
folder on your local disk before a browser can load it.

### Step 1: Get the `extension/` folder onto your machine

Pick whichever is easiest for you:

- **Clone the whole repo (recommended if you'll also run the backend):**
  ```sh
  git clone https://github.com/Rudra-clrscr/Spam-Detection-System.git
  cd Spam-Detection-System
  git checkout feature/187-browser-extension
  ```
  The extension lives at `Spam-Detection-System/extension`.

- **Download just this PR's `extension/` folder as a zip, no git required:**
  1. Go to <https://download-directory.github.io/>
  2. Paste this URL and press enter:
     `https://github.com/Rudra-clrscr/Spam-Detection-System/tree/feature/187-browser-extension/extension`
  3. Unzip the downloaded file.

- **Download the whole branch as a zip from GitHub's UI:** on the
  [`feature/187-browser-extension` branch page](https://github.com/Rudra-clrscr/Spam-Detection-System/tree/feature/187-browser-extension),
  click the green "Code" button → "Download ZIP", then unzip and open the
  `extension` subfolder.

### Step 2: Load it into your browser

**Chrome / Edge / Brave:**
1. Go to `chrome://extensions`, enable "Developer mode" (toggle, top-right).
2. Click "Load unpacked" and select the `extension/` folder (the one
   containing `manifest.json` directly — not its parent).
3. You should see "Spam Detection Inbox Scanner" appear in the list with a
   purple envelope icon and no error badge.

**Firefox:**
1. Go to `about:debugging#/runtime/this-firefox`.
2. Click "Load Temporary Add-on…" and select `extension/manifest.json`.
   (Temporary add-ons are removed when Firefox restarts — see
   [web-ext](https://extensionworkshop.com/documentation/develop/web-ext-command-reference/)
   for a persistent dev workflow.)

## Configure

1. Click the extension icon → "Open settings".
2. Set the API base URL (defaults to `http://localhost:3000`, the Node
   gateway used by the rest of this project).
3. Log into the Spam Detection web app. If it's running locally at
   `localhost:5173` (the Vite dev default), a content script
   (`src/content/webapp-bridge.js`) picks up your login token from
   `localStorage` automatically within a few seconds — no manual step needed.
   Otherwise, open devtools on the web app's page, run
   `localStorage.getItem('token')`, and paste the result into "Account token".

If you deploy the frontend or backend somewhere other than `localhost`, add
that origin to `host_permissions`/the relevant `content_scripts.matches`
entry in `manifest.json` before loading the extension (or use
`chrome.permissions.request` — out of scope for this first pass).

## Privacy

- Only the subject + a short preview snippet (truncated to 500 characters) is
  sent to the classification API per message — never the full message body.
- Classification results are kept in memory only, scoped to the current page
  load. Nothing is written to `chrome.storage` or disk except your API base
  URL and account token (used to authenticate to your own backend).
- Dismissing a flag only affects local in-memory state; it does not call the
  backend.

## Known limitations

- Gmail/Outlook DOM selectors (`src/content/gmail.js`, `src/content/outlook.js`)
  are based on current unofficial markup and **will break** if Google/Microsoft
  change their markup. If badges stop appearing, inspect a message row in
  devtools and update the selectors at the top of the relevant file.
- Loaded unpacked against a real, logged-in Gmail inbox: badges rendered on
  visible rows, and the classification pipeline (content script → background
  worker → Node `/predict` → Flask ML API) was confirmed via backend logs to
  return real Safe/Spam/Smishing predictions for real message subjects/
  previews. Visual confirmation that every badge displays the correct label
  in the browser (vs. a stale/failed state) is still pending re-check after
  a backend restart during testing. Outlook web has not been separately
  verified live — its selectors are still best-effort.
- A failed scan (e.g. backend temporarily unreachable) renders a "Scan
  failed" badge and is **not cached**, so it retries automatically the next
  time the inbox DOM updates — this is intentional, not a bug, but can look
  alarming if every row shows it briefly while the backend is still starting
  up.

## Publishing (optional follow-up)

This PR ships the extension as source only — it is not published to any
store. Getting a one-click "Add to Chrome"/"Add to Firefox" install requires
the project maintainer to submit it under their own developer account. Draft
listing copy, a privacy policy, permission justifications, and icons are in
`store-listing/` and `icons/` to make that easier later; real screenshots
still need to be captured from a live browser session (see
`store-listing/screenshots/README.md`).

## Tests

Pure logic (caching, text truncation, badge mapping) is covered by
`node --test`:

```sh
cd extension
npm test
```

DOM scanning and the background/options/popup UI require a real browser and
are not covered by automated tests in this PR.
