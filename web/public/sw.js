// Dhool's service worker, written by hand: the app opens without a network, and alerts arrive when it is closed.
// It keeps only the app's own files. Calls to the API, to sign-in and to the weather go straight to the
// network and are never kept here; the last verdict is kept by the app itself (src/store.js).
// ponytail: the fonts (another site) are not kept, so offline text falls back to the phone's own font; and
// files of older builds stay until CACHE is renamed. Fine at this size (about 100 KB a build).
const CACHE = "dhool-shell-1";

// Keep the page and the files it names, so the app opens offline after one visit, not two.
self.addEventListener("install", (event) => {
  self.skipWaiting();
  event.waitUntil((async () => {
    const page = await fetch("/", { cache: "no-store" });
    const files = [...(await page.clone().text()).matchAll(/(?:src|href)="(\/assets\/[^"]+)"/g)].map((m) => m[1]);
    const cache = await caches.open(CACHE);
    await cache.put("/", page);
    await cache.addAll([...files, "/icon.svg", "/manifest.webmanifest"]);
  })());
});

self.addEventListener("activate", (event) => {
  event.waitUntil((async () => {
    for (const name of await caches.keys()) if (name !== CACHE) await caches.delete(name);
    await self.clients.claim();
  })());
});

self.addEventListener("fetch", (event) => {
  const { request } = event, url = new URL(request.url);
  if (request.method !== "GET" || url.origin !== location.origin) return;  // API, Cognito, weather, fonts: not ours to keep
  if (request.mode === "navigate") {
    // The page: the network's copy when there is one (a new build shows at once), the kept one otherwise.
    event.respondWith(fetch(request).then((page) => {
      const copy = page.clone();  // taken now: the browser starts reading `page` as soon as it is returned
      if (page.ok) caches.open(CACHE).then((cache) => cache.put("/", copy));
      return page;
    }).catch(() => caches.match("/")));
  } else {
    // Vite names each file in /assets by its contents, so a kept copy is never out of date.
    event.respondWith(caches.match(request).then((hit) => hit || fetch(request).then((file) => {
      const copy = file.clone();
      if (file.ok && url.pathname.startsWith("/assets/")) caches.open(CACHE).then((cache) => cache.put(request, copy));
      return file;
    })));
  }
});

// An alert from the nightly run: { title, body, url }, already in the language the phone asked for.
self.addEventListener("push", (event) => {
  let alert = {};
  try { alert = event.data.json(); } catch { /* no text came with it: show the name alone */ }
  event.waitUntil(self.registration.showNotification(alert.title || "Dhool", {
    body: alert.body || "", icon: "/icon.svg", data: { url: alert.url || "/" },
  }));
});

// Tapping it brings the app forward at the page the alert names, or opens it there.
self.addEventListener("notificationclick", (event) => {
  event.notification.close();
  let url = new URL(event.notification.data?.url || "/", location.origin);
  if (url.origin !== location.origin) url = new URL("/", location.origin);  // only ever our own app
  event.waitUntil(self.clients.matchAll({ type: "window", includeUncontrolled: true }).then((open) =>
    (open[0] ? open[0].focus().then((tab) => tab.navigate(url.href)).catch(() => {}) : self.clients.openWindow(url.href))));
});
