# Privacy Policy — Spam Detection Inbox Scanner

_Last updated: [fill in date before publishing]_

This browser extension ("the extension") is a companion UI for the Spam
Detection System project. It does not collect, sell, or share any data with
the developer or any third party.

## What data the extension touches

- **Message content**: when scanning your Gmail/Outlook inbox, the extension
  reads the subject line and a short preview snippet (truncated to 500
  characters) of messages currently visible on screen. This snippet is sent
  to the classification backend you configure (your own Spam Detection
  System instance) for the sole purpose of returning a spam/smishing/
  offensive/safe classification. The full message body is never read or
  sent.
- **Account token**: a login token for your configured Spam Detection System
  backend, stored locally in the browser's extension storage
  (`chrome.storage.local`) so you don't have to re-enter it every session.
- **API base URL**: the address of the backend you're connecting to, stored
  the same way.

## What the extension does NOT do

- It does not store message content anywhere beyond the current page's
  lifetime — classification results live in memory only and are cleared on
  reload.
- It does not send any data to the extension's developer or any analytics/
  telemetry service.
- It does not run on any site other than Gmail, Outlook web, and the
  configured backend's web app (for the optional automatic token sync).

## Where your data goes

All classification requests go directly from your browser to the backend
URL you configured in the extension's options page — i.e. your own
self-hosted (or your organization's) instance of the Spam Detection System.
The extension's developer has no access to this traffic.

## Revoking access

Uninstalling the extension, or clearing its storage via
`chrome://extensions` → Details → "Clear data", removes the stored API URL
and token immediately. No server-side action is required since nothing is
stored server-side specifically for this extension beyond your normal
backend account.

## Contact

[fill in a contact email or repository issue link before publishing]
