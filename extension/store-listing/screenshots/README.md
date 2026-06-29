# Screenshots needed before submission

Both Chrome Web Store and Firefox AMO require at least one real screenshot
(Chrome: 1280x800 or 640x400 PNG/JPEG). These need to come from an actual
browser session against a live, logged-in Gmail/Outlook inbox — that wasn't
possible to produce from the sandboxed environment this extension was built
in (no real browser/Gmail session available there).

Once you've loaded the extension unpacked and confirmed it works (see the
main `extension/README.md`), capture:

1. **Inbox with badges** — a Gmail or Outlook inbox view with a few visible
   messages, at least one showing each badge type (Safe/Spam/Smishing/
   Offensive) if you can arrange test messages that trigger them.
2. **Options page** — `src/options/options.html` with the API URL field
   filled in (blur out or use a placeholder token).
3. **Popup** — the toolbar popup showing "Connected to ..." status.

Save them in this folder (e.g. `01-inbox-badges.png`, `02-options.png`,
`03-popup.png`) before uploading to the store dashboard.
