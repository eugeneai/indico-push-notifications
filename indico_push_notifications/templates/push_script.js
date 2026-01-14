// Push Notifications JavaScript
// This file contains the JavaScript logic for push notifications

// Configuration
const PushConfig = {
    vapidPublicKey: document.currentScript.getAttribute('data-vapid-public-key') || '',
    apiBaseUrl: document.currentScript.getAttribute('data-api-base-url') || '',
    userId: parseInt(document.currentScript.getAttribute('data-user-id')) || 0,
    isPushSupported: 'serviceWorker' in navigator && 'PushManager' in window
};

// State
let serviceWorkerRegistration = null;
let pushSubscription = null;
let isSubscribing = false;

// Initialize push notifications
async function initializePushNotifications() {
    if (!PushConfig.isPushSupported) {
        console.warn('Push notifications are not supported in this browser');
        return false;
    }

    try {
        // Register service worker
        serviceWorkerRegistration = await navigator.serviceWorker.register(
            '/static/push-notifications/service-worker.js'
        );

        console.log('Service Worker registered successfully');

        // Check existing subscription
        pushSubscription = await serviceWorkerRegistration.pushManager.getSubscription();

        if (pushSubscription) {
            console.log('Existing push subscription found');
            await updateSubscriptionOnServer(pushSubscription);
        }

        return true;
    } catch (error) {
        console.error('Failed to initialize push notifications:', error);
        return false;
    }
}

// Subscribe to push notifications
async function subscribeToPushNotifications() {
    if (isSubscribing) {
        console.log('Already subscribing...');
        return;
    }

    if (!PushConfig.isPushSupported) {
        alert('Push notifications are not supported in your browser.');
        return;
    }

    if (!serviceWorkerRegistration) {
        const initialized = await initializePushNotifications();
        if (!initialized) {
            alert('Failed to initialize push notifications.');
            return;
        }
    }

    isSubscribing = true;

    try {
        // Request permission
        const permission = await Notification.requestPermission();

        if (permission !== 'granted') {
            throw new Error('Permission not granted for notifications');
        }

        // Subscribe to push
        const applicationServerKey = urlBase64ToUint8Array(PushConfig.vapidPublicKey);
        pushSubscription = await serviceWorkerRegistration.pushManager.subscribe({
            userVisibleOnly: true,
            applicationServerKey: applicationServerKey
        });

        console.log('Push subscription successful:', pushSubscription);

        // Send subscription to server
        await saveSubscriptionToServer(pushSubscription);

        // Update UI
        updatePushUI(true);

        alert('Push notifications enabled successfully!');

    } catch (error) {
        console.error('Failed to subscribe to push notifications:', error);

        if (error.name === 'NotAllowedError') {
            alert('Please allow notifications in your browser settings.');
        } else {
            alert('Failed to enable push notifications: ' + error.message);
        }
    } finally {
        isSubscribing = false;
    }
}

// Unsubscribe from push notifications
async function unsubscribeFromPushNotifications() {
    if (!pushSubscription) {
        console.log('No active subscription to unsubscribe from');
        return;
    }

    try {
        // Unsubscribe from push
        const success = await pushSubscription.unsubscribe();

        if (success) {
            console.log('Push subscription unsubscribed successfully');

            // Remove subscription from server
            await deleteSubscriptionFromServer(pushSubscription.endpoint);

            // Update state
            pushSubscription = null;

            // Update UI
            updatePushUI(false);

            alert('Push notifications disabled successfully!');
        } else {
            throw new Error('Failed to unsubscribe');
        }
    } catch (error) {
        console.error('Failed to unsubscribe from push notifications:', error);
        alert('Failed to disable push notifications: ' + error.message);
    }
}

// Save subscription to server
async function saveSubscriptionToServer(subscription) {
    try {
        const response = await fetch(`${PushConfig.apiBaseUrl}/push/subscribe`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRF-Token': getCSRFToken()
            },
            body: JSON.stringify({
                subscription: subscriptionToObject(subscription)
            })
        });

        if (!response.ok) {
            throw new Error(`Server responded with ${response.status}`);
        }

        const data = await response.json();
        return data.success;
    } catch (error) {
        console.error('Failed to save subscription to server:', error);
        throw error;
    }
}

// Delete subscription from server
async function deleteSubscriptionFromServer(endpoint) {
    try {
        const response = await fetch(`${PushConfig.apiBaseUrl}/push/unsubscribe`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRF-Token': getCSRFToken()
            },
            body: JSON.stringify({ endpoint: endpoint })
        });

        if (!response.ok) {
            throw new Error(`Server responded with ${response.status}`);
        }

        const data = await response.json();
        return data.success;
    } catch (error) {
        console.error('Failed to delete subscription from server:', error);
        throw error;
    }
}

// Update subscription on server (for existing subscriptions)
async function updateSubscriptionOnServer(subscription) {
    try {
        const response = await fetch(`${PushConfig.apiBaseUrl}/push/subscriptions`, {
            method: 'GET',
            headers: {
                'X-CSRF-Token': getCSRFToken()
            }
        });

        if (response.ok) {
            const data = await response.json();
            const subscriptions = data.subscriptions || [];

            // Check if this subscription already exists
            const exists = subscriptions.some(sub =>
                sub.endpoint === subscription.endpoint
            );

            if (!exists) {
                await saveSubscriptionToServer(subscription);
            }
        }
    } catch (error) {
        console.error('Failed to update subscription on server:', error);
    }
}

// Get user's push subscriptions
async function getUserPushSubscriptions() {
    try {
        const response = await fetch(`${PushConfig.apiBaseUrl}/push/subscriptions`, {
            method: 'GET',
            headers: {
                'X-CSRF-Token': getCSRFToken()
            }
        });

        if (response.ok) {
            const data = await response.json();
            return data.subscriptions || [];
        } else {
            throw new Error(`Server responded with ${response.status}`);
        }
    } catch (error) {
        console.error('Failed to get user subscriptions:', error);
        return [];
    }
}

// Send test push notification
async function sendTestPushNotification(message = 'Test notification from Indico') {
    try {
        const response = await fetch(`${PushConfig.apiBaseUrl}/test/push`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRF-Token': getCSRFToken()
            },
            body: JSON.stringify({ message: message })
        });

        if (!response.ok) {
            throw new Error(`Server responded with ${response.status}`);
        }

        const data = await response.json();

        if (data.success) {
            alert('Test push notification sent successfully!');
        } else {
            alert('Failed to send test push notification: ' + (data.message || 'Unknown error'));
        }

        return data.success;
    } catch (error) {
        console.error('Failed to send test push notification:', error);
        alert('Failed to send test push notification: ' + error.message);
        return false;
    }
}

// Utility functions

// Convert subscription to plain object
function subscriptionToObject(subscription) {
    return {
        endpoint: subscription.endpoint,
        keys: {
            p256dh: arrayBufferToBase64(subscription.getKey('p256dh')),
            auth: arrayBufferToBase64(subscription.getKey('auth'))
        },
        browser: getBrowserInfo(),
        platform: navigator.platform,
        userAgent: navigator.userAgent,
        created: new Date().toISOString()
    };
}

// Convert base64 string to Uint8Array
function urlBase64ToUint8Array(base64String) {
    const padding = '='.repeat((4 - base64String.length % 4) % 4);
    const base64 = (base64String + padding)
        .replace(/\-/g, '+')
        .replace(/_/g, '/');

    const rawData = window.atob(base64);
    const outputArray = new Uint8Array(rawData.length);

    for (let i = 0; i < rawData.length; ++i) {
        outputArray[i] = rawData.charCodeAt(i);
    }

    return outputArray;
}

// Convert ArrayBuffer to base64
function arrayBufferToBase64(buffer) {
    let binary = '';
    const bytes = new Uint8Array(buffer);
    const len = bytes.byteLength;

    for (let i = 0; i < len; i++) {
        binary += String.fromCharCode(bytes[i]);
    }

    return window.btoa(binary);
}

// Get browser information
function getBrowserInfo() {
    const userAgent = navigator.userAgent;

    if (userAgent.indexOf('Chrome') > -1) return 'Chrome';
    if (userAgent.indexOf('Firefox') > -1) return 'Firefox';
    if (userAgent.indexOf('Safari') > -1) return 'Safari';
    if (userAgent.indexOf('Edge') > -1) return 'Edge';
    if (userAgent.indexOf('Opera') > -1 || userAgent.indexOf('OPR') > -1) return 'Opera';

    return 'Unknown';
}

// Get CSRF token from meta tag
function getCSRFToken() {
    const metaTag = document.querySelector('meta[name="csrf-token"]');
    return metaTag ? metaTag.getAttribute('content') : '';
}

// Update UI based on push subscription state
function updatePushUI(isSubscribed) {
    const subscribeBtn = document.getElementById('subscribe-push-btn');
    const unsubscribeBtn = document.getElementById('unsubscribe-push-btn');
    const pushEnabledCheckbox = document.getElementById('push-enabled');
    const statusElement = document.querySelector('.webpush-status');

    if (subscribeBtn) {
        subscribeBtn.style.display = isSubscribed ? 'none' : 'block';
    }

    if (unsubscribeBtn) {
        unsubscribeBtn.style.display = isSubscribed ? 'block' : 'none';
    }

    if (pushEnabledCheckbox) {
        pushEnabledCheckbox.disabled = !isSubscribed;
        if (!isSubscribed) {
            pushEnabledCheckbox.checked = false;
        }
    }

    if (statusElement) {
        if (isSubscribed) {
            statusElement.classList.remove('not-enabled');
            statusElement.classList.add('enabled');
        } else {
            statusElement.classList.remove('enabled');
            statusElement.classList.add('not-enabled');
        }
    }
}

// Load and display push subscriptions
async function loadAndDisplaySubscriptions() {
    const container = document.getElementById('subscriptions-container');

    if (!container) {
        return;
    }

    try {
        const subscriptions = await getUserPushSubscriptions();

        if (subscriptions.length === 0) {
            container.innerHTML = '<div class="no-data">No devices registered</div>';
            return;
        }

        let html = '<div class="subscriptions-table">';
        html += '<table class="i-table">';
        html += '<thead><tr><th>Browser</th><th>Platform</th><th>Registered</th><th>Actions</th></tr></thead>';
        html += '<tbody>';

        subscriptions.forEach(sub => {
            const browser = sub.browser || 'Unknown';
            const platform = sub.platform || 'Unknown';
            const registered = sub.created ? new Date(sub.created).toLocaleDateString() : 'Unknown';

            html += '<tr>';
            html += `<td>${browser}</td>`;
            html += `<td>${platform}</td>`;
            html += `<td>${registered}</td>`;
            html += `<td><button class="i-button small warning unsubscribe-device-btn" data-endpoint="${sub.endpoint}">Remove</button></td>`;
            html += '</tr>';
        });

        html += '</tbody></table></div>';
        container.innerHTML = html;

        // Add event listeners to remove buttons
        document.querySelectorAll('.unsubscribe-device-btn').forEach(button => {
            button.addEventListener('click', async function() {
                const endpoint = this.getAttribute('data-endpoint');
                if (confirm('Are you sure you want to remove this device?')) {
                    try {
                        await deleteSubscriptionFromServer(endpoint);
                        await loadAndDisplaySubscriptions();

                        // If this was the current subscription, update UI
                        if (pushSubscription && pushSubscription.endpoint === endpoint) {
                            pushSubscription = null;
                            updatePushUI(false);
                        }
                    } catch (error) {
                        console.error('Failed to remove device:', error);
                        alert('Failed to remove device: ' + error.message);
                    }
                }
            });
        });
    } catch (error) {
        console.error('Failed to load subscriptions:', error);
        container.innerHTML = '<div class="no-data error">Failed to load devices</div>';
    }
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', async function() {
    // Check push support
    if (!PushConfig.isPushSupported) {
        console.warn('Push notifications not supported');
        const pushSection = document.querySelector('.webpush-section');
        if (pushSection) {
            pushSection.innerHTML = '<div class="warning-message">Push notifications are not supported in your browser.</div>';
        }
        return;
    }

    // Initialize push notifications
    await initializePushNotifications();

    // Load subscriptions if container exists
    if (document.getElementById('subscriptions-container')) {
        await loadAndDisplaySubscriptions();
    }

    // Set up event listeners
    const subscribeBtn = document.getElementById('subscribe-push-btn');
    const unsubscribeBtn = document.getElementById('unsubscribe-push-btn');
    const testPushBtn = document.getElementById('test-push-btn');

    if (subscribeBtn) {
        subscribeBtn.addEventListener('click', subscribeToPushNotifications);
    }

    if (unsubscribeBtn) {
        unsubscribeBtn.addEventListener('click', unsubscribeFromPushNotifications);
    }

    if (testPushBtn) {
        testPushBtn.addEventListener('click', () => sendTestPushNotification());
    }
});

// Export functions for use in other scripts
window.PushNotifications = {
    initialize: initializePushNotifications,
    subscribe: subscribeToPushNotifications,
    unsubscribe: unsubscribeFromPushNotifications,
    sendTest: sendTestPushNotification,
    getSubscriptions: getUserPushSubscriptions,
    isSupported: PushConfig.isPushSupported
};
