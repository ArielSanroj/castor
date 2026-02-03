/**
 * Service Worker para Castor Control Electoral - Testigos
 * Maneja push notifications y caching offline.
 */

const CACHE_NAME = 'castor-testigos-v1';
const OFFLINE_URL = '/testigo/offline';

// Archivos a cachear para funcionamiento offline
const PRECACHE_URLS = [
    '/',
    '/testigo/registro',
    '/static/css/witness.css',
    '/static/js/witness.js',
    '/static/manifest.json'
];

// ============================================================
// INSTALL - Precache archivos esenciales
// ============================================================
self.addEventListener('install', (event) => {
    console.log('[SW] Installing Service Worker...');

    event.waitUntil(
        caches.open(CACHE_NAME)
            .then((cache) => {
                console.log('[SW] Precaching offline assets');
                return cache.addAll(PRECACHE_URLS);
            })
            .then(() => {
                console.log('[SW] Installation complete');
                return self.skipWaiting();
            })
            .catch((error) => {
                console.error('[SW] Precache failed:', error);
            })
    );
});

// ============================================================
// ACTIVATE - Limpiar caches antiguos
// ============================================================
self.addEventListener('activate', (event) => {
    console.log('[SW] Activating Service Worker...');

    event.waitUntil(
        caches.keys()
            .then((cacheNames) => {
                return Promise.all(
                    cacheNames
                        .filter((name) => name !== CACHE_NAME)
                        .map((name) => {
                            console.log('[SW] Deleting old cache:', name);
                            return caches.delete(name);
                        })
                );
            })
            .then(() => {
                console.log('[SW] Activation complete');
                return self.clients.claim();
            })
    );
});

// ============================================================
// FETCH - Network first, fallback to cache
// ============================================================
self.addEventListener('fetch', (event) => {
    // Solo manejar requests GET
    if (event.request.method !== 'GET') {
        return;
    }

    // Ignorar requests a APIs externas
    if (!event.request.url.startsWith(self.location.origin)) {
        return;
    }

    event.respondWith(
        fetch(event.request)
            .then((response) => {
                // Cachear respuestas exitosas
                if (response.status === 200) {
                    const responseClone = response.clone();
                    caches.open(CACHE_NAME)
                        .then((cache) => {
                            cache.put(event.request, responseClone);
                        });
                }
                return response;
            })
            .catch(() => {
                // Si falla la red, buscar en cache
                return caches.match(event.request)
                    .then((cachedResponse) => {
                        if (cachedResponse) {
                            return cachedResponse;
                        }
                        // Si no hay cache, mostrar página offline
                        if (event.request.mode === 'navigate') {
                            return caches.match(OFFLINE_URL);
                        }
                        return new Response('Offline', { status: 503 });
                    });
            })
    );
});

// ============================================================
// PUSH - Manejar notificaciones push
// ============================================================
self.addEventListener('push', (event) => {
    console.log('[SW] Push notification received');

    let data = {
        title: 'Castor Control Electoral',
        body: 'Tienes una nueva notificación',
        data: {}
    };

    if (event.data) {
        try {
            data = event.data.json();
        } catch (e) {
            data.body = event.data.text();
        }
    }

    const options = {
        body: data.body,
        icon: '/static/images/icon-192x192.png',
        badge: '/static/images/badge-72x72.png',
        vibrate: [200, 100, 200],
        tag: data.data?.assignment_id || 'castor-notification',
        renotify: true,
        requireInteraction: data.data?.type === 'ASSIGNMENT',
        data: data.data || {},
        actions: getNotificationActions(data.data?.type)
    };

    event.waitUntil(
        self.registration.showNotification(data.title, options)
    );
});

/**
 * Obtiene acciones según tipo de notificación
 */
function getNotificationActions(type) {
    switch (type) {
        case 'ASSIGNMENT':
            return [
                { action: 'accept', title: 'Aceptar', icon: '/static/images/check.png' },
                { action: 'reject', title: 'Rechazar', icon: '/static/images/close.png' }
            ];
        case 'ALERT':
            return [
                { action: 'view', title: 'Ver Detalles' }
            ];
        default:
            return [];
    }
}

// ============================================================
// NOTIFICATION CLICK - Manejar clicks en notificaciones
// ============================================================
self.addEventListener('notificationclick', (event) => {
    console.log('[SW] Notification clicked:', event.action);

    event.notification.close();

    const data = event.notification.data || {};
    let url = '/testigo/asignaciones';

    // Manejar acciones
    if (event.action === 'accept' && data.assignment_id) {
        // Llamar API para aceptar asignación
        event.waitUntil(
            fetch(`/api/witness/assignments/${data.assignment_id}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ status: 'ACCEPTED' })
            })
            .then(() => {
                return self.registration.showNotification('Asignación Aceptada', {
                    body: `Has aceptado la asignación a ${data.mesa_id || 'la mesa'}`,
                    icon: '/static/images/icon-192x192.png'
                });
            })
            .catch((error) => {
                console.error('[SW] Error accepting assignment:', error);
            })
        );
        return;
    }

    if (event.action === 'reject' && data.assignment_id) {
        event.waitUntil(
            fetch(`/api/witness/assignments/${data.assignment_id}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ status: 'REJECTED' })
            })
        );
        return;
    }

    // Abrir la app en la URL correspondiente
    if (data.assignment_id) {
        url = `/testigo/asignaciones?id=${data.assignment_id}`;
    }

    event.waitUntil(
        clients.matchAll({ type: 'window', includeUncontrolled: true })
            .then((clientList) => {
                // Si ya hay una ventana abierta, enfocarla
                for (const client of clientList) {
                    if (client.url.includes('/testigo') && 'focus' in client) {
                        client.navigate(url);
                        return client.focus();
                    }
                }
                // Si no, abrir nueva ventana
                if (clients.openWindow) {
                    return clients.openWindow(url);
                }
            })
    );
});

// ============================================================
// NOTIFICATION CLOSE - Tracking (opcional)
// ============================================================
self.addEventListener('notificationclose', (event) => {
    console.log('[SW] Notification closed without action');
    // Aquí podrías enviar tracking de notificaciones cerradas
});

// ============================================================
// PUSH SUBSCRIPTION CHANGE - Renovar suscripción
// ============================================================
self.addEventListener('pushsubscriptionchange', (event) => {
    console.log('[SW] Push subscription changed');

    event.waitUntil(
        self.registration.pushManager.subscribe({
            userVisibleOnly: true,
            applicationServerKey: urlBase64ToUint8Array(self.VAPID_PUBLIC_KEY)
        })
        .then((subscription) => {
            // Enviar nueva suscripción al servidor
            return fetch('/api/witness/push/subscribe', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    witness_id: self.WITNESS_ID, // Se setea desde el cliente
                    subscription: subscription.toJSON()
                })
            });
        })
        .catch((error) => {
            console.error('[SW] Failed to renew subscription:', error);
        })
    );
});

// ============================================================
// HELPER FUNCTIONS
// ============================================================

/**
 * Convierte VAPID key de base64 a Uint8Array
 */
function urlBase64ToUint8Array(base64String) {
    const padding = '='.repeat((4 - base64String.length % 4) % 4);
    const base64 = (base64String + padding)
        .replace(/-/g, '+')
        .replace(/_/g, '/');

    const rawData = atob(base64);
    const outputArray = new Uint8Array(rawData.length);

    for (let i = 0; i < rawData.length; ++i) {
        outputArray[i] = rawData.charCodeAt(i);
    }
    return outputArray;
}

// ============================================================
// MESSAGE - Comunicación con el cliente
// ============================================================
self.addEventListener('message', (event) => {
    console.log('[SW] Message received:', event.data);

    if (event.data.type === 'SET_WITNESS_ID') {
        self.WITNESS_ID = event.data.witnessId;
        console.log('[SW] Witness ID set:', self.WITNESS_ID);
    }

    if (event.data.type === 'SET_VAPID_KEY') {
        self.VAPID_PUBLIC_KEY = event.data.vapidKey;
        console.log('[SW] VAPID key set');
    }

    if (event.data.type === 'SKIP_WAITING') {
        self.skipWaiting();
    }
});

console.log('[SW] Service Worker loaded');
