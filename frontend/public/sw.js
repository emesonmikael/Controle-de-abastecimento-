// Minimal service worker for offline shell caching. Refined caching in later iteration.
const CACHE = "frota-nfc-v1";
const ASSETS = ["/", "/index.html"];

self.addEventListener("install", (e) => {
  e.waitUntil(caches.open(CACHE).then((c) => c.addAll(ASSETS)));
  self.skipWaiting();
});

self.addEventListener("activate", (e) => {
  e.waitUntil(
    caches.keys().then((keys) => Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k))))
  );
  self.clients.claim();
});

self.addEventListener("fetch", (e) => {
  const req = e.request;
  if (req.method !== "GET" || req.url.includes("/api/")) return;
  e.respondWith(
    caches.match(req).then((cached) => cached || fetch(req).catch(() => caches.match("/index.html")))
  );
});
