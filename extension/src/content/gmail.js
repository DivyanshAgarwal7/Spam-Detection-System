(function () {
  // Gmail's inbox table rows use the long-standing (but unofficial/undocumented)
  // class names below. Gmail changes its DOM without notice, so if scanning stops
  // working, re-inspect a row in devtools and update these selectors first.
  const config = {
    listContainerSelector: 'div[role="main"]',
    rowSelector: "tr.zA",
    getMessageId(row) {
      return row.getAttribute("data-legacy-thread-id") || row.getAttribute("id");
    },
    getSubject(row) {
      const el = row.querySelector(".bog");
      return el ? el.textContent : "";
    },
    getPreview(row) {
      const el = row.querySelector(".y2");
      return el ? el.textContent : "";
    },
    getBadgeAnchor(row) {
      return row.querySelector(".y6") || row.querySelector(".bog")?.parentElement;
    },
  };

  const scanner = window.SDS.common.createInboxScanner(config);
  scanner.start();
})();
