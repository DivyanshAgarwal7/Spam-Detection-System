# Chrome Web Store / Firefox AMO listing

Draft copy for whoever submits this extension under their own developer
account. Nothing here is submitted automatically — paste it into the
respective store's dashboard.

## Extension name

Spam Detection Inbox Scanner

## Summary (132 characters max, Chrome Web Store)

Flags spam, smishing and offensive messages inline in Gmail and Outlook, scored by the Spam Detection System's own model.

## Category

Productivity (Chrome) / Privacy & Security (Firefox AMO alternative category)

## Detailed description

Spam Detection Inbox Scanner scans the messages visible in your Gmail or
Outlook web inbox and shows an inline badge — Safe, Spam, Smishing, or
Offensive — next to each one, scored by the same classification model used
elsewhere in the Spam Detection System project.

Features:
- Inline badges next to visible inbox rows, no need to open a message first
- Manual rescan (↻) and dismiss (✕) controls on every badge
- Uses your own Spam Detection System account/backend — no third-party
  classification service involved
- Only a short, truncated snippet (subject + preview, max 500 characters) is
  ever sent for classification, never the full message body
- Classification results are kept in memory only for the current page
  load — nothing is written to disk beyond your API URL and login token

Requires a running instance of the Spam Detection System backend (self-hosted
or your organization's deployment) and an account on it. This extension does
not work standalone — it's a companion UI for that project.

## Permission justifications (required by the Chrome Web Store dashboard)

- `storage` — stores the configured API base URL and your login token
  locally so you don't have to re-enter them every session.
- `host_permissions` for `mail.google.com` / `outlook.live.com` /
  `outlook.office.com` — required to run the content scripts that read
  visible message subjects/previews and inject the inline badges.
- `host_permissions` for the backend origin(s) (default
  `localhost:3000`/`localhost:5000`) — required for the background service
  worker to call the classification API.

## Privacy policy URL

Host `PRIVACY_POLICY.md` (in this folder) at a public URL — e.g. as a GitHub
Pages page or a raw GitHub link — and paste that URL into the store
dashboard's "Privacy policy" field. Both Chrome Web Store and Firefox AMO
require this for any extension that handles user data.

## Screenshots

See `screenshots/README.md` — these need to be captured from a real browser
session against a live Gmail/Outlook inbox, which wasn't possible from the
sandboxed environment this extension was built in.
