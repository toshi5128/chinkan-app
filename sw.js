// ネット優先・つながらない時だけ保存分（電車の地下でも勉強できるように）
const CACHE = "chinkan-v14";
self.addEventListener("install", () => self.skipWaiting());
self.addEventListener("activate", e => e.waitUntil(self.clients.claim()));
self.addEventListener("fetch", e => {
  const u = new URL(e.request.url);
  if (e.request.method !== "GET" || u.origin !== location.origin) return;
  // 音声ファイル（途中から読む範囲指定つき）はそのまま通す＝保存しない
  if (u.pathname.includes("/audio/") && !u.pathname.endsWith(".json") || e.request.headers.has("range")) return;
  e.respondWith(fetch(e.request, { cache: "no-store" }).then(r => {
    if (r.ok && r.status === 200) { const c = r.clone(); caches.open(CACHE).then(k => k.put(e.request, c)); }
    return r;
  }).catch(() => caches.match(e.request, { ignoreSearch: true })));
});
