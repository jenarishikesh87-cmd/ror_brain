self.addEventListener("install", e=>{
  e.waitUntil(
    caches.open("ror-cache").then(cache=>{
      return cache.addAll([
        "/",
        "/static/style.css",
        "/static/app.js"
      ]);
    })
  );
});

self.addEventListener("fetch", e=>{
  e.respondWith(
    caches.match(e.request).then(res=>{
      return res || fetch(e.request);
    })
  );
});
