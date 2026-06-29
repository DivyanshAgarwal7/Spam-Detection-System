/* Spam Detection System — service worker
 * Enables installability (PWA) and a basic offline app shell.
 * Strategy:
 *   - Navigation/static assets: network-first, fall back to cache when offline.
 *   - API calls (POST / cross-origin / /api,/predict,...) are never cached.
 */
const CACHE = "sds-shell-v1";
const APP_SHELL = [
  "/",
  "/index.html",
  "/manifest.webmanifest",
  "/pwa-192x192.png",
  "/pwa-512x512.png",
];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE).then((cache) => cache.addAll(APP_SHELL)).then(() => self.skipWaiting())
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((keys) => Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

const API_PREFIXES = [
  "/api",
  "/predict",
  "/feedback",
  "/analyze-email-header",
  "/bulk-predict",
  "/spam-insights",
  "/gmail",
  "/outlook",
  "/scan-emails",
  "/importance",
  "/analytics",
];

function isApiRequest(url) {
  return API_PREFIXES.some((p) => url.pathname === p || url.pathname.startsWith(p + "/"));
}

self.addEventListener("fetch", (event) => {
  const { request } = event;
  // Only handle same-origin GET requests; let everything else hit the network.
  const url = new URL(request.url);
  if (request.method !== "GET" || url.origin !== self.location.origin || isApiRequest(url)) {
    return;
  }

  event.respondWith(
    fetch(request)
      .then((response) => {
        // Cache a copy of successful basic responses for offline use.
        if (response && response.status === 200 && response.type === "basic") {
          const copy = response.clone();
          caches.open(CACHE).then((cache) => cache.put(request, copy));
        }
        return response;
      })
      .catch(async () => {
        const cached = await caches.match(request);
        if (cached) return cached;
        // SPA fallback: serve the app shell for navigations when offline.
        if (request.mode === "navigate") {
          const shell = await caches.match("/index.html");
          if (shell) return shell;
        }
        return Response.error();
      })
  );
});
