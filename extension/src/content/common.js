(function () {
  const { badgeForPrediction } = window.SDS.textUtils;

  const STYLE_ID = "sds-inline-styles";

  function ensureStyles() {
    if (document.getElementById(STYLE_ID)) return;
    const style = document.createElement("style");
    style.id = STYLE_ID;
    style.textContent = `
      .sds-badge { display:inline-flex; align-items:center; gap:4px; margin-left:6px;
        padding:1px 6px; border-radius:10px; font-size:11px; font-weight:600;
        line-height:1.6; vertical-align:middle; white-space:nowrap; }
      .sds-badge-safe { background:#e6f4ea; color:#1e7e34; }
      .sds-badge-spam { background:#fdecea; color:#c0392b; }
      .sds-badge-smishing { background:#fff4e5; color:#b06000; }
      .sds-badge-offensive { background:#fdecea; color:#8b0000; }
      .sds-badge-unknown { background:#eee; color:#666; }
      .sds-badge-loading { background:#eee; color:#666; }
      .sds-badge button { border:none; background:transparent; cursor:pointer;
        font-size:10px; padding:0 2px; line-height:1; color:inherit; }
    `;
    document.head.appendChild(style);
  }

  // Builds (or rebuilds) the inline badge for one message row. `onRescan`/`onDismiss`
  // are wired to the row's message id so each badge acts independently.
  function renderBadge(existingBadge, state, handlers) {
    ensureStyles();
    const badge = existingBadge || document.createElement("span");
    badge.className = "sds-badge";
    badge.dataset.sdsBadge = "true";

    if (state.loading) {
      badge.classList.add("sds-badge-loading");
      badge.textContent = "Scanning…";
      return badge;
    }

    if (state.error) {
      badge.classList.add("sds-badge-unknown");
      badge.textContent = "Scan failed";
      badge.title = state.error;
      return badge;
    }

    const info = badgeForPrediction(state.prediction);
    badge.classList.add(info.className);
    badge.innerHTML = "";

    const label = document.createElement("span");
    label.textContent = `${info.emoji} ${info.label}`;
    badge.appendChild(label);

    const rescanBtn = document.createElement("button");
    rescanBtn.type = "button";
    rescanBtn.title = "Rescan this message";
    rescanBtn.textContent = "↻";
    rescanBtn.addEventListener("click", (e) => {
      e.stopPropagation();
      e.preventDefault();
      handlers.onRescan();
    });
    badge.appendChild(rescanBtn);

    const dismissBtn = document.createElement("button");
    dismissBtn.type = "button";
    dismissBtn.title = "Dismiss this flag";
    dismissBtn.textContent = "✕";
    dismissBtn.addEventListener("click", (e) => {
      e.stopPropagation();
      e.preventDefault();
      handlers.onDismiss();
    });
    badge.appendChild(dismissBtn);

    return badge;
  }

  function removeBadge(container) {
    const existing = container.querySelector('[data-sds-badge="true"]');
    if (existing) existing.remove();
  }

  // Debounced MutationObserver: webmail inboxes re-render rows constantly while
  // scrolling/loading, so we batch and only react once things settle.
  function observeList(target, onChange, debounceMs) {
    let timer = null;
    const observer = new MutationObserver(() => {
      if (timer) clearTimeout(timer);
      timer = setTimeout(onChange, debounceMs || 300);
    });
    observer.observe(target, { childList: true, subtree: true });
    return observer;
  }

  // Generic scanning engine shared by every webmail provider. `config` supplies
  // the provider-specific DOM knowledge (selectors + extraction); everything
  // else (caching, badge lifecycle, mutation handling) is identical.
  function createInboxScanner(config) {
    const cache = window.SDS.cache.createScanCache();
    const { classify } = window.SDS.classifier;
    const { truncateForClassification } = window.SDS.textUtils;

    async function scanRow(row, forceRescan) {
      const messageId = config.getMessageId(row);
      if (!messageId) return;

      if (!cache.shouldRescan(messageId, forceRescan)) return;

      const anchor = config.getBadgeAnchor(row);
      if (!anchor) return;

      let badge = anchor.querySelector('[data-sds-badge="true"]');
      badge = window.SDS.common.renderBadge(badge, { loading: true }, {});
      if (!badge.parentElement) anchor.appendChild(badge);

      const text = truncateForClassification(
        `${config.getSubject(row) || ""}. ${config.getPreview(row) || ""}`
      );

      try {
        const result = await classify(text, "email");
        cache.set(messageId, result);
        const updated = window.SDS.common.renderBadge(
          badge,
          { prediction: result.prediction },
          {
            onRescan: () => scanRow(row, true),
            onDismiss: () => {
              cache.dismiss(messageId);
              window.SDS.common.removeBadge(anchor);
            },
          }
        );
        if (!updated.parentElement) anchor.appendChild(updated);
      } catch (err) {
        window.SDS.common.renderBadge(badge, { error: err.message }, {});
      }
    }

    function scanVisible(forceRescan) {
      const rows = document.querySelectorAll(config.rowSelector);
      rows.forEach((row) => scanRow(row, forceRescan));
    }

    function start() {
      scanVisible(false);
      const container = document.querySelector(config.listContainerSelector) || document.body;
      window.SDS.common.observeList(container, () => scanVisible(false));

      chrome.runtime.onMessage.addListener((message) => {
        if (message?.type === "RESCAN_ALL") {
          scanVisible(true);
        }
      });
    }

    return { start, scanVisible };
  }

  window.SDS = window.SDS || {};
  window.SDS.common = { renderBadge, removeBadge, observeList, createInboxScanner };
})();
