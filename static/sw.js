// ✅ sw.js (در مسیر: static/sw.js)

importScripts('https://www.gstatic.com/firebasejs/9.23.0/firebase-app-compat.js');
importScripts('https://www.gstatic.com/firebasejs/9.23.0/firebase-messaging-compat.js');

firebase.initializeApp({
    apiKey: "AIzaSyBL_pXyrbTJehyf51uCXqX2BClfOFw4TyQ",
    authDomain: "behdari-8f765.firebaseapp.com",
    projectId: "behdari-8f765",
    storageBucket: "behdari-8f765.firebasestorage.app",
    messagingSenderId: "1027377060017",
    appId: "1:1027377060017:web:aba0894305f72d1b9caa90",
    measurementId: "G-BR8J9TTP2N"
});

const messaging = firebase.messaging();

messaging.onBackgroundMessage((payload) => {
  console.log('[firebase-messaging-sw.js] Background Message:', payload);
  const notificationTitle = payload.notification.title || 'پیام جدید از سیستم';
  const notificationOptions = {
    body: payload.notification.body || 'شما یک پیام جدید دارید.',
    icon: payload.notification.icon || '/static/images/notification-icon.png',
    badge: '/static/images/badge-icon.png',
    data: { url: payload.data?.url || '/' },
    vibrate: [200, 100, 200],
    tag: 'firebase-notification',
    renotify: true
  };
  self.registration.showNotification(notificationTitle, notificationOptions);
});

self.addEventListener('push', (event) => {
    let notificationData = {};
    try {
        notificationData = event.data?.json() || {};
    } catch (e) {
        console.error("Error parsing push event data:", e);
    }
    const title = notificationData.title || 'اطلاعیه جدید';
    const options = {
        body: notificationData.body || 'شما ویزیت‌های ارجاعی جدید دارید.',
        icon: notificationData.icon || '/static/images/notification-icon.png',
        badge: notificationData.badge || '/static/images/badge-icon.png',
        data: {
            url: notificationData.url || 'http://94.101.177.176/visits/?view=referred_to_me'
        },
        vibrate: [200, 100, 200],
        tag: 'referred-visits-notification',
        renotify: true
    };
    event.waitUntil(
        self.registration.showNotification(title, options)
    );
});

self.addEventListener('notificationclick', (event) => {
    event.notification.close();
    const targetUrl = event.notification.data.url;
    event.waitUntil(
        clients.matchAll({ type: 'window' }).then(windowClients => {
            for (const client of windowClients) {
                if (client.url === targetUrl && 'focus' in client) {
                    return client.focus();
                }
            }
            if (clients.openWindow) {
                return clients.openWindow(targetUrl);
            }
        })
    );
});

self.addEventListener('fetch', (event) => {
    event.respondWith(fetch(event.request));
});
