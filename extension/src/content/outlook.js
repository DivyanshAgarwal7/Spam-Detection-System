(function () {
  // Outlook web's message list items are ARIA listbox options. Like Gmail, this
  // markup is unofficial and may shift between Outlook releases — re-inspect a
  // row in devtools and update these selectors if scanning stops matching rows.
  const config = {
    listContainerSelector: 'div[role="listbox"]',
    rowSelector: 'div[role="option"]',
    getMessageId(row) {
      return row.getAttribute("id") || row.getAttribute("data-convid");
    },
    getSubject(row) {
      const el = row.querySelector('span[id^="MessageSubject"], span[class*="subject" i]');
      return el ? el.textContent : "";
    },
    getPreview(row) {
      const el = row.querySelector('span[class*="preview" i], span[class*="bodyPreview" i]');
      return el ? el.textContent : "";
    },
    getBadgeAnchor(row) {
      return row.querySelector('span[id^="MessageSubject"], span[class*="subject" i]')?.parentElement || row;
    },
  };

  const scanner = window.SDS.common.createInboxScanner(config);
  scanner.start();
})();
