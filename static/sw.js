self.addEventListener("install", e => {
  self.skipWaiting();
});

self.addEventListener("activate", e => {
  console.log("Service Worker Active");
});

// 🔔 PUSH EVENT (REAL NOTIFICATIONS)
self.addEventListener("push", function(event) {
  const data = event.data ? event.data.text() : "ROR Notification";

  event.waitUntil(
    self.registration.showNotification("ROR", {
      body: data,
      icon: "/static/ror-logo.png",
      badge: "/static/ror-logo.png"
    })
  );
});
