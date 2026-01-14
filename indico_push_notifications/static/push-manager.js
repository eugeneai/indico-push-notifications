// Push Manager for Indico Push Notifications
// This file provides a higher-level API for managing push notifications

class PushNotificationManager {
    constructor(config = {}) {
        this.config = {
            vapidPublicKey: config.vapidPublicKey || '',
            apiBaseUrl: config.apiBaseUrl || '/api',
            userId: config.userId || 0,
            autoInitialize: config.autoInitialize !== false,
            debug: config.debug || false,
            ...config
        };

        this.state = {
            isSupported: 'serviceWorker' in navigator && 'PushManager' in window,
            isSubscribed: false,
            isInitialized: false,
            serviceWorkerRegistration: null,
            pushSubscription: null,
            permissions: {
                notification: Notification.permission,
                push: null
            }
        };

        this.eventHandlers = {
            onSubscribe: [],
            onUnsubscribe: [],
            onError: [],
            onNotificationClick: [],
            onNotificationClose: [],
            onPermissionChange: []
        };

        this.log('PushNotificationManager initialized', this.config);
    }

    // Public API Methods

    async initialize() {
        if (!this.state.isSupported) {
            this.log('Push notifications not supported in this browser');
            return false;
        }

        try {
            // Register service worker
            this.state.serviceWorkerRegistration = await navigator.serviceWorker.register(
                '/static/push-notifications/service-worker.js'
            );

            this.log('Service Worker registered successfully');

            // Check existing subscription
            this.state.pushSubscription = await this.state.serviceWorkerRegistration.pushManager.getSubscription();
            this.state.isSubscribed = !!this.state.pushSubscription;

            if (this.state.isSubscribed) {
                this.log('Existing push subscription found');
                await this.updateSubscriptionOnServer();
            }

            // Set up service worker message handler
            navigator.serviceWorker.addEventListener('message', this.handleServiceWorkerMessage.bind(this));

            // Monitor permission changes
            this.setupPermissionMonitoring();

            this.state.isInitialized = true;
            this.log('Push notifications initialized successfully');

            return true;
        } catch (error) {
            this.handleError('Failed to initialize push notifications', error);
            return false;
        }
    }

    async subscribe() {
        if (!this.state.isInitialized) {
            const initialized = await this.initialize();
            if (!initialized) {
                throw new Error('Failed to initialize push notifications');
            }
        }

        try {
            // Request notification permission
            const permission = await Notification.requestPermission();
            this.state.permissions.notification = permission;

            if (permission !== 'granted') {
                throw new Error('Notification permission not granted');
            }

            // Subscribe to push
            const applicationServerKey = this.urlBase64ToUint8Array(this.config.vapidPublicKey);
            this.state.pushSubscription = await this.state.serviceWorkerRegistration.pushManager.subscribe({
                userVisibleOnly: true,
                applicationServerKey: applicationServerKey
            });

            this.state.isSubscribed = true;

            // Save to server
            await this.saveSubscriptionToServer();

            // Trigger event handlers
            this.triggerEvent('onSubscribe', this.state.pushSubscription);

            this.log('Successfully subscribed to push notifications');
            return this.state.pushSubscription;

        } catch (error) {
            this.handleError('Failed to subscribe to push notifications', error);
            throw error;
        }
    }

    async unsubscribe() {
        if (!this.state.isSubscribed || !this.state.pushSubscription) {
            this.log('No active subscription to unsubscribe from');
            return false;
        }

        try {
            const success = await this.state.pushSubscription.unsubscribe();

            if (success) {
                // Remove from server
                await this.deleteSubscriptionFromServer(this.state.pushSubscription.endpoint);

                // Update state
                this.state.pushSubscription = null;
                this.state.isSubscribed = false;

                // Trigger event handlers
                this.triggerEvent('onUnsubscribe');

                this.log('Successfully unsubscribed from push notifications');
                return true;
            } else {
                throw new Error('Failed to unsubscribe');
            }
        } catch (error) {
            this.handleError('Failed to unsubscribe from push notifications', error);
            throw error;
        }
    }

    async getSubscriptionStatus() {
        if (!this.state.isInitialized) {
            await this.initialize();
        }

        return {
            isSupported: this.state.isSupported,
            isSubscribed: this.state.isSubscribed,
            isInitialized: this.state.isInitialized,
            permissions: this.state.permissions,
            subscription: this.state.pushSubscription ? this.subscriptionToObject(this.state.pushSubscription) : null,
            serviceWorker: this.state.serviceWorkerRegistration ? {
                active: !!this.state.serviceWorkerRegistration.active,
                installing: !!this.state.serviceWorkerRegistration.installing,
                waiting: !!this.state.serviceWorkerRegistration.waiting
            } : null
        };
    }

    async sendTestNotification(message = 'Test notification from Indico Push Manager') {
        try {
            const response = await fetch(`${this.config.apiBaseUrl}/user/${this.config.userId}/push-notifications/test/push`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRF-Token': this.getCSRFToken()
                },
                body: JSON.stringify({ message })
            });

            if (!response.ok) {
                throw new Error(`Server responded with ${response.status}`);
            }

            const data = await response.json();
            return data;
        } catch (error) {
            this.handleError('Failed to send test notification', error);
            throw error;
        }
    }

    async getSubscriptions() {
        try {
            const response = await fetch(`${this.config.apiBaseUrl}/user/${this.config.userId}/push-notifications/push/subscriptions`, {
                method: 'GET',
                headers: {
                    'X-CSRF-Token': this.getCSRFToken()
                }
            });

            if (!response.ok) {
                throw new Error(`Server responded with ${response.status}`);
            }

            const data = await response.json();
            return data.subscriptions || [];
        } catch (error) {
            this.handleError('Failed to get subscriptions', error);
            throw error;
        }
    }

    async removeSubscription(endpoint) {
        try {
            const response = await fetch(`${this.config.apiBaseUrl}/user/${this.config.userId}/push-notifications/push/unsubscribe`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRF-Token': this.getCSRFToken()
                },
                body: JSON.stringify({ endpoint })
            });

            if (!response.ok) {
                throw new Error(`Server responded with ${response.status}`);
            }

            const data = await response.json();

            // If this was the current subscription, update local state
            if (this.state.pushSubscription && this.state.pushSubscription.endpoint === endpoint) {
                this.state.pushSubscription = null;
                this.state.isSubscribed = false;
                this.triggerEvent('onUnsubscribe');
            }

            return data.success;
        } catch (error) {
            this.handleError('Failed to remove subscription', error);
            throw error;
        }
    }

    // Event Handling

    on(event, handler) {
        if (this.eventHandlers[event]) {
            this.eventHandlers[event].push(handler);
        } else {
            this.log(`Unknown event: ${event}`);
        }
        return this;
    }

    off(event, handler) {
        if (this.eventHandlers[event]) {
            const index = this.eventHandlers[event].indexOf(handler);
            if (index > -1) {
                this.eventHandlers[event].splice(index, 1);
            }
        }
        return this;
    }

    // Utility Methods

    subscriptionToObject(subscription) {
        return {
            endpoint: subscription.endpoint,
            keys: {
                p256dh: this.arrayBufferToBase64(subscription.getKey('p256dh')),
                auth: this.arrayBufferToBase64(subscription.getKey('auth'))
            },
            browser: this.getBrowserInfo(),
            platform: navigator.platform,
            userAgent: navigator.userAgent,
            created: new Date().toISOString()
        };
    }

    urlBase64ToUint8Array(base64String) {
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

    arrayBufferToBase64(buffer) {
        let binary = '';
        const bytes = new Uint8Array(buffer);
        const len = bytes.byteLength;

        for (let i = 0; i < len; i++) {
            binary += String.fromCharCode(bytes[i]);
        }

        return window.btoa(binary);
    }

    getBrowserInfo() {
        const userAgent = navigator.userAgent;

        if (userAgent.indexOf('Chrome') > -1) return 'Chrome';
        if (userAgent.indexOf('Firefox') > -1) return 'Firefox';
        if (userAgent.indexOf('Safari') > -1) return 'Safari';
        if (userAgent.indexOf('Edge') > -1) return 'Edge';
        if (userAgent.indexOf('Opera') > -1 || userAgent.indexOf('OPR') > -1) return 'Opera';

        return 'Unknown';
    }

    getCSRFToken() {
        const metaTag = document.querySelector('meta[name="csrf-token"]');
        return metaTag ? metaTag.getAttribute('content') : '';
    }

    // Private Methods

    async saveSubscriptionToServer() {
        try {
            const response = await fetch(`${this.config.apiBaseUrl}/user/${this.config.userId}/push-notifications/push/subscribe`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRF-Token': this.getCSRFToken()
                },
                body: JSON.stringify({
                    subscription: this.subscriptionToObject(this.state.pushSubscription)
                })
            });

            if (!response.ok) {
                throw new Error(`Server responded with ${response.status}`);
            }

            const data = await response.json();
            return data.success;
        } catch (error) {
            this.handleError('Failed to save subscription to server', error);
            throw error;
        }
    }

    async deleteSubscriptionFromServer(endpoint) {
        try {
            const response = await fetch(`${this.config.apiBaseUrl}/user/${this.config.userId}/push-notifications/push/unsubscribe`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRF-Token': this.getCSRFToken()
                },
                body: JSON.stringify({ endpoint })
            });

            if (!response.ok) {
                throw new Error(`Server responded with ${response.status}`);
            }

            const data = await response.json();
            return data.success;
        } catch (error) {
            this.handleError('Failed to delete subscription from server', error);
            throw error;
        }
    }

    async updateSubscriptionOnServer() {
        try {
            const subscriptions = await this.getSubscriptions();
            const currentEndpoint = this.state.pushSubscription.endpoint;

            // Check if this subscription already exists on server
            const exists = subscriptions.some(sub => sub.endpoint === currentEndpoint);

            if (!exists) {
                await this.saveSubscriptionToServer();
            }
        } catch (error) {
            this.log('Failed to update subscription on server', error);
            // Non-critical error, don't throw
        }
    }

    handleServiceWorkerMessage(event) {
        const { type, data } = event.data || {};

        this.log('Message from service worker', { type, data });

        switch (type) {
            case 'NOTIFICATION_CLICKED':
                this.triggerEvent('onNotificationClick', data);
                break;

            case 'NOTIFICATION_CLOSED':
                this.triggerEvent('onNotificationClose', data);
                break;

            case 'PUSH_RECEIVED':
                // You could trigger an event for push received if needed
                break;

            default:
                this.log('Unknown message type from service worker', type);
        }
    }

    setupPermissionMonitoring() {
        // Monitor Notification.permission changes
        let lastPermission = Notification.permission;

        // Check permission periodically (not ideal, but there's no event for permission changes)
        this.permissionCheckInterval = setInterval(() => {
            const currentPermission = Notification.permission;
            if (currentPermission !== lastPermission) {
                lastPermission = currentPermission;
                this.state.permissions.notification = currentPermission;
                this.triggerEvent('onPermissionChange', currentPermission);
                this.log('Notification permission changed to', currentPermission);
            }
        }, 5000); // Check every 5 seconds
    }

    triggerEvent(eventName, data) {
        if (this.eventHandlers[eventName]) {
            this.eventHandlers[eventName].forEach(handler => {
                try {
                    handler(data);
                } catch (error) {
                    this.log(`Error in event handler for ${eventName}`, error);
                }
            });
        }
    }

    handleError(message, error) {
        const errorObj = error instanceof Error ? error : new Error(error);
        this.log(message, errorObj);
        this.triggerEvent('onError', { message, error: errorObj });
    }

    log(...args) {
        if (this.config.debug) {
            console.log('[PushNotificationManager]', ...args);
        }
    }

    // Cleanup

    destroy() {
        if (this.permissionCheckInterval) {
            clearInterval(this.permissionCheckInterval);
        }

        if (navigator.serviceWorker) {
            navigator.serviceWorker.removeEventListener('message', this.handleServiceWorkerMessage.bind(this));
        }

        this.log('PushNotificationManager destroyed');
    }
}

// Factory function for easy initialization
function createPushManager(config = {}) {
    return new PushNotificationManager(config);
}

// Auto-initialize if script is loaded with data attributes
document.addEventListener('DOMContentLoaded', () => {
    const scriptElement = document.querySelector('script[data-push-manager]');
    if (scriptElement) {
        const config = {
            vapidPublicKey: scriptElement.getAttribute('data-vapid-public-key') || '',
            apiBaseUrl: scriptElement.getAttribute('data-api-base-url') || '/api',
            userId: parseInt(scriptElement.getAttribute('data-user-id')) || 0,
            autoInitialize: scriptElement.getAttribute('data-auto-initialize') !== 'false',
            debug: scriptElement.getAttribute('data-debug') === 'true'
        };

        window.indicoPushManager = createPushManager(config);

        if (config.autoInitialize) {
            window.indicoPushManager.initialize().catch(error => {
                console.error('Failed to auto-initialize push manager', error);
            });
        }
    }
});

// Export for module usage
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        PushNotificationManager,
        createPushManager
    };
} else {
    window.PushNotificationManager = PushNotificationManager;
    window.createPushManager = createPushManager;
}
