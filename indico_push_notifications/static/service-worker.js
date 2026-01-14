// Service Worker for Indico Push Notifications
// This service worker handles push notifications and background sync

const CACHE_NAME = 'indico-push-notifications-v1';
const NOTIFICATION_ICON = '/static/images/indico-icon.png';
const NOTIFICATION_BADGE = '/static/images/indico-badge.png';

// Install event - cache static assets
self.addEventListener('install', event => {
    console.log('Service Worker: Installing...');

    event.waitUntil(
        caches.open(CACHE_NAME)
            .then(cache => {
                console.log('Service Worker: Caching static assets');
                return cache.addAll([
                    '/static/images/indico-icon.png',
                    '/static/images/indico-badge.png'
                ]);
            })
            .then(() => {
                console.log('Service Worker: Install completed');
                return self.skipWaiting();
            })
    );
});

// Activate event - clean up old caches
self.addEventListener('activate', event => {
    console.log('Service Worker: Activating...');

    event.waitUntil(
        caches.keys().then(cacheNames => {
            return Promise.all(
                cacheNames.map(cacheName => {
                    if (cacheName !== CACHE_NAME) {
                        console.log('Service Worker: Deleting old cache', cacheName);
                        return caches.delete(cacheName);
                    }
                })
            );
        })
        .then(() => {
            console.log('Service Worker: Activation completed');
            return self.clients.claim();
        })
    );
});

// Push event - handle incoming push notifications
self.addEventListener('push', event => {
    console.log('Service Worker: Push received', event);

    let notificationData = {
        title: 'Indico Notification',
        body: 'You have a new notification',
        icon: NOTIFICATION_ICON,
        badge: NOTIFICATION_BADGE,
        tag: 'indico-notification',
        data: {},
        actions: []
    };

    // Parse push data
    if (event.data) {
        try {
            const data = event.data.json();
            console.log('Service Worker: Parsed push data', data);

            // Merge with default notification data
            notificationData = {
                ...notificationData,
                ...data,
                data: {
                    ...notificationData.data,
                    ...(data.data || {}),
                    originalData: data
                }
            };

            // Add default action if not specified
            if (!notificationData.actions || notificationData.actions.length === 0) {
                notificationData.actions = [
                    {
                        action: 'open',
                        title: 'Open',
                        icon: '/static/images/open-icon.png'
                    },
                    {
                        action: 'dismiss',
                        title: 'Dismiss',
                        icon: '/static/images/dismiss-icon.png'
                    }
                ];
            }
        } catch (error) {
            console.error('Service Worker: Failed to parse push data', error);

            // Try to get text data
            const text = event.data.text();
            if (text) {
                notificationData.body = text;
            }
        }
    }

    // Show notification
    event.waitUntil(
        self.registration.showNotification(notificationData.title, notificationData)
            .then(() => {
                console.log('Service Worker: Notification shown successfully');
            })
            .catch(error => {
                console.error('Service Worker: Failed to show notification', error);
            })
    );
});

// Notification click event - handle user interaction with notifications
self.addEventListener('notificationclick', event => {
    console.log('Service Worker: Notification clicked', event);

    const notification = event.notification;
    const action = event.action;
    const notificationData = notification.data || {};

    // Close the notification
    notification.close();

    // Handle different actions
    if (action === 'dismiss') {
        console.log('Service Worker: Notification dismissed');
        return;
    }

    // Default action: open Indico or specific URL
    let urlToOpen = '/';

    if (notificationData.url) {
        urlToOpen = notificationData.url;
    } else if (notificationData.originalData && notificationData.originalData.url) {
        urlToOpen = notificationData.originalData.url;
    } else if (notificationData.eventId) {
        urlToOpen = `/event/${notificationData.eventId}`;
    }

    // Focus or open window
    event.waitUntil(
        clients.matchAll({
            type: 'window',
            includeUncontrolled: true
        })
        .then(windowClients => {
            // Check if there's already a window open with the URL
            for (const client of windowClients) {
                if (client.url.includes(urlToOpen) && 'focus' in client) {
                    return client.focus();
                }
            }

            // If no window found, open a new one
            if (clients.openWindow) {
                return clients.openWindow(urlToOpen);
            }
        })
        .catch(error => {
            console.error('Service Worker: Failed to open window', error);
        })
    );
});

// Notification close event
self.addEventListener('notificationclose', event => {
    console.log('Service Worker: Notification closed', event);

    // You could send analytics here
    const notification = event.notification;
    const notificationData = notification.data || {};

    console.log('Service Worker: Notification closed with data', notificationData);
});

// Background sync event (for offline support)
self.addEventListener('sync', event => {
    console.log('Service Worker: Background sync event', event.tag);

    if (event.tag === 'sync-notifications') {
        event.waitUntil(
            syncNotifications()
                .then(() => {
                    console.log('Service Worker: Notifications synced successfully');
                })
                .catch(error => {
                    console.error('Service Worker: Failed to sync notifications', error);
                })
        );
    }
});

// Periodic sync event (for periodic updates)
self.addEventListener('periodicsync', event => {
    console.log('Service Worker: Periodic sync event', event.tag);

    if (event.tag === 'check-notifications') {
        event.waitUntil(
            checkForNewNotifications()
                .then(hasNewNotifications => {
                    if (hasNewNotifications) {
                        console.log('Service Worker: New notifications found');
                        // Could show a notification here
                    }
                })
                .catch(error => {
                    console.error('Service Worker: Failed to check notifications', error);
                })
        );
    }
});

// Fetch event - handle network requests
self.addEventListener('fetch', event => {
    // You can add caching strategies here if needed
    // For now, just pass through
    // event.respondWith(fetch(event.request));
});

// Helper function to sync notifications
async function syncNotifications() {
    try {
        // Get pending notifications from IndexedDB
        const db = await openNotificationsDB();
        const pendingNotifications = await getAllPendingNotifications(db);

        // Send pending notifications to server
        for (const notification of pendingNotifications) {
            await sendNotificationToServer(notification);
            await markNotificationAsSent(db, notification.id);
        }

        return true;
    } catch (error) {
        console.error('Service Worker: Error syncing notifications', error);
        throw error;
    }
}

// Helper function to check for new notifications
async function checkForNewNotifications() {
    try {
        // In a real implementation, this would check the server for new notifications
        // For now, return false
        return false;
    } catch (error) {
        console.error('Service Worker: Error checking notifications', error);
        return false;
    }
}

// IndexedDB helper functions
function openNotificationsDB() {
    return new Promise((resolve, reject) => {
        const request = indexedDB.open('indico-notifications', 1);

        request.onerror = () => reject(request.error);
        request.onsuccess = () => resolve(request.result);

        request.onupgradeneeded = event => {
            const db = event.target.result;

            // Create object store for pending notifications
            if (!db.objectStoreNames.contains('pendingNotifications')) {
                const store = db.createObjectStore('pendingNotifications', {
                    keyPath: 'id',
                    autoIncrement: true
                });

                // Create indexes
                store.createIndex('status', 'status', { unique: false });
                store.createIndex('created', 'created', { unique: false });
            }
        };
    });
}

function getAllPendingNotifications(db) {
    return new Promise((resolve, reject) => {
        const transaction = db.transaction(['pendingNotifications'], 'readonly');
        const store = transaction.objectStore('pendingNotifications');
        const index = store.index('status');
        const request = index.getAll('pending');

        request.onerror = () => reject(request.error);
        request.onsuccess = () => resolve(request.result);
    });
}

function markNotificationAsSent(db, id) {
    return new Promise((resolve, reject) => {
        const transaction = db.transaction(['pendingNotifications'], 'readwrite');
        const store = transaction.objectStore('pendingNotifications');
        const request = store.get(id);

        request.onerror = () => reject(request.error);
        request.onsuccess = () => {
            const notification = request.result;
            if (notification) {
                notification.status = 'sent';
                notification.sentAt = new Date().toISOString();

                const updateRequest = store.put(notification);
                updateRequest.onerror = () => reject(updateRequest.error);
                updateRequest.onsuccess = () => resolve();
            } else {
                resolve();
            }
        };
    });
}

async function sendNotificationToServer(notification) {
    // In a real implementation, this would send the notification to your server
    // For now, just log it
    console.log('Service Worker: Would send notification to server', notification);
    return Promise.resolve();
}

// Message event - handle messages from the main thread
self.addEventListener('message', event => {
    console.log('Service Worker: Message received', event.data);

    const { type, data } = event.data || {};

    switch (type) {
        case 'SKIP_WAITING':
            self.skipWaiting();
            break;

        case 'CLAIM_CLIENTS':
            self.clients.claim();
            break;

        case 'TEST_NOTIFICATION':
            self.registration.showNotification('Test Notification', {
                body: 'This is a test notification from the service worker',
                icon: NOTIFICATION_ICON,
                badge: NOTIFICATION_BADGE,
                tag: 'test-notification'
            });
            break;

        default:
            console.log('Service Worker: Unknown message type', type);
    }
});

// Error handling
self.addEventListener('error', event => {
    console.error('Service Worker: Error occurred', event.error);
});

self.addEventListener('unhandledrejection', event => {
    console.error('Service Worker: Unhandled promise rejection', event.reason);
});
