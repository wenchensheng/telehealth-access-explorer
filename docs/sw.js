/* Service worker: precache the app shell + data so the app opens offline after the first visit. */
const CACHE = "tae-v1";
const ASSETS = [
  "./", "index.html", "styles.css", "app.js", "manifest.json",
  "vendor/d3.min.js", "vendor/topojson-client.min.js",
  "data/app.json", "data/states-albers-10m.json",
  "icons/icon-192.png", "icons/icon-512.png", "icons/icon-maskable-512.png", "icons/apple-touch-icon.png", "icons/favicon-32.png",
];

self.addEventListener("install", (e) => {
  e.waitUntil(caches.open(CACHE).then((c) => c.addAll(ASSETS)).then(() => self.skipWaiting()));
});

self.addEventListener("activate", (e) => {
  e.waitUntil(caches.keys().then((keys) => Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k))))
    .then(() => self.clients.claim()));
});

// Stale-while-revalidate for same-origin GETs: answer from cache instantly, refresh in the background.
self.addEventListener("fetch", (e) => {
  const req = e.request;
  if (req.method !== "GET" || new URL(req.url).origin !== location.origin) return;
  e.respondWith(caches.open(CACHE).then(async (cache) => {
    const key = req.mode === "navigate" ? "index.html" : req;
    const hit = await cache.match(key, { ignoreSearch: true });
    const net = fetch(req).then((res) => { if (res.ok) cache.put(key, res.clone()); return res; }).catch(() => null);
    return hit || (await net) || new Response("Offline", { status: 503, statusText: "Offline" });
  }));
});
