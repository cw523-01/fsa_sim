/**
 * Notification system for showing non-blocking error and success messages
 * Reuses existing popup CSS from simulation-popup.css
 */
class NotificationManager {
    constructor() {
        this.notifications = new Set();
        this.notificationCounter = 0;
    }

    /**
     * Show an error notification
     * @param {string} title - The error title
     * @param {string} message - The error message
     * @param {number} duration - Auto-hide duration in milliseconds (default: 5000)
     */
    showError(title, message, duration = 5000) {
        this.showNotification('error', title, message, duration);
    }

    /**
     * Show a warning notification
     * @param {string} title - The warning title
     * @param {string} message - The warning message
     * @param {number} duration - Auto-hide duration in milliseconds (default: 4000)
     */
    showWarning(title, message, duration = 4000) {
        this.showNotification('warning', title, message, duration);
    }

    /**
     * Show a success notification
     * @param {string} title - The success title
     * @param {string} message - The success message
     * @param {number} duration - Auto-hide duration in milliseconds (default: 3000)
     */
    showSuccess(title, message, duration = 3000) {
        this.showNotification('success', title, message, duration);
    }

    /**
     * Show an info notification
     * @param {string} title - The info title
     * @param {string} message - The info message
     * @param {number} duration - Auto-hide duration in milliseconds (default: 4000)
     */
    showInfo(title, message, duration = 4000) {
        this.showNotification('info', title, message, duration);
    }

    /**
     * Show a notification with specified type
     * @param {string} type - Type of notification ('error', 'warning', 'success', 'info')
     * @param {string} title - The notification title
     * @param {string} message - The notification message
     * @param {number} duration - Auto-hide duration in milliseconds
     */
    showNotification(type, title, message, duration) {
        // Create unique ID for this notification
        const notificationId = `notification-${++this.notificationCounter}`;

        // Remove any existing notifications of the same type and message to prevent duplicates
        this.removeExistingNotification(type, title, message);

        // Create notification element
        const notification = document.createElement('div');
        notification.id = notificationId;
        notification.className = `notification-popup ${type}`;

        // Get icon and colors based on type
        const config = this.getNotificationConfig(type);

        notification.innerHTML = `
            <div class="popup-header">
                <div class="popup-status ${type}">
                    <div class="popup-icon ${type}">${config.icon}</div>
                    <span>${title}</span>
                </div>
                <button class="popup-close" onclick="notificationManager.hideNotification('${notificationId}')">×</button>
            </div>
            <div class="popup-details">
                ${message.replace(/\n/g, '<br>')}
            </div>
            <div class="popup-progress">
                <div class="popup-progress-bar ${type}"></div>
            </div>
        `;

        // Add to canvas (same as simulation popups)
        const canvas = document.getElementById('fsa-canvas');
        if (canvas) {
            canvas.appendChild(notification);
        } else {
            document.body.appendChild(notification);
        }

        // Position multiple notifications in a stack
        this.positionNotification(notification);

        // Add to tracking set
        this.notifications.add({
            id: notificationId,
            element: notification,
            type: type,
            title: title,
            message: message
        });

        // Trigger show animation
        setTimeout(() => {
            notification.classList.add('show');
        }, 100);

        // Start auto-hide timer if duration is specified
        if (duration > 0) {
            this.startAutoHideTimer(notification, duration);
        }

        return notificationId;
    }

    /**
     * Get configuration for notification type
     * @param {string} type - Notification type
     * @returns {Object} Configuration object with icon and other settings
     */
    getNotificationConfig(type) {
        const configs = {
            error: {
                icon: '<img src="static/img/error.png" alt="Error" style="width: 16px; height: 16px;">',
                className: 'error'
            },
            warning: {
                icon: '<img src="static/img/alert.png" alt="Warning" style="width: 16px; height: 16px;">',
                className: 'warning'
            },
            success: {
                icon: '<img src="static/img/success.png" alt="Success" style="width: 16px; height: 16px;">',
                className: 'success'
            },
            info: {
                icon: '<img src="static/img/info.png" alt="Info" style="width: 16px; height: 16px;">',
                className: 'info'
            }
        };
        return configs[type] || configs.info;
    }

    /**
     * Position notification in a stack with other notifications
     * @param {HTMLElement} notification - The notification element
     */
    positionNotification(notification) {
        const existingNotifications = document.querySelectorAll('.notification-popup.show');
        const index = existingNotifications.length - 1; // -1 because current one isn't shown yet

        // Stack notifications with offset, starting below the header
        const baseOffset = 60; // Base offset to clear header
        const stackOffset = 20; // Initial spacing from top of canvas
        const notificationSpacing = 80; // Spacing between notifications

        const topOffset = baseOffset + stackOffset + (index * notificationSpacing);
        notification.style.top = `${topOffset}px`;
    }

    /**
     * Remove existing notification with same type and message to prevent duplicates
     * @param {string} type - Notification type
     * @param {string} title - Notification title
     * @param {string} message - Notification message
     */
    removeExistingNotification(type, title, message) {
        const existing = Array.from(this.notifications).find(n =>
            n.type === type && n.title === title && n.message === message
        );

        if (existing) {
            this.hideNotification(existing.id);
        }
    }

    /**
     * Hide a specific notification
     * @param {string} notificationId - ID of notification to hide
     */
    hideNotification(notificationId) {
        const notification = document.getElementById(notificationId);
        if (!notification) return;

        // Remove from tracking set
        this.notifications.forEach(n => {
            if (n.id === notificationId) {
                this.notifications.delete(n);
            }
        });

        // Trigger hide animation
        notification.classList.add('hide');
        notification.classList.remove('show');

        // Remove from DOM after animation
        setTimeout(() => {
            if (notification.parentNode) {
                notification.parentNode.removeChild(notification);
            }
            // Reposition remaining notifications
            this.repositionNotifications();
        }, 400);
    }

    /**
     * Reposition remaining notifications after one is removed
     */
    repositionNotifications() {
        const remainingNotifications = document.querySelectorAll('.notification-popup.show');
        remainingNotifications.forEach((notification, index) => {
            const baseOffset = 60; // Base offset to clear header
            const stackOffset = 20; // Initial spacing from top of canvas
            const notificationSpacing = 80; // Spacing between notifications

            const topOffset = baseOffset + stackOffset + (index * notificationSpacing);
            notification.style.top = `${topOffset}px`;
        });
    }

    /**
     * Start auto-hide timer for notification
     * @param {HTMLElement} notification - The notification element
     * @param {number} duration - Duration in milliseconds
     */
    startAutoHideTimer(notification, duration) {
        // Animate progress bar
        const progressBar = notification.querySelector('.popup-progress-bar');
        if (progressBar) {
            progressBar.style.width = '100%';
            progressBar.style.transition = `width ${duration}ms linear`;

            // Start with full width, then animate to 0
            setTimeout(() => {
                progressBar.style.width = '0%';
            }, 100);
        }

        // Set auto-hide timeout
        setTimeout(() => {
            this.hideNotification(notification.id);
        }, duration);
    }

    /**
     * Hide all notifications
     */
    hideAllNotifications() {
        const allNotifications = Array.from(this.notifications);
        allNotifications.forEach(n => {
            this.hideNotification(n.id);
        });
    }

    /**
     * Check if there are any active notifications
     * @returns {boolean} - Whether there are active notifications
     */
    hasActiveNotifications() {
        return this.notifications.size > 0;
    }

    /**
     * Get count of active notifications
     * @returns {number} - Number of active notifications
     */
    getActiveNotificationCount() {
        return this.notifications.size;
    }

    /**
     * Clear all notifications immediately (no animation)
     */
    clearAllNotifications() {
        this.notifications.forEach(n => {
            const element = document.getElementById(n.id);
            if (element && element.parentNode) {
                element.parentNode.removeChild(element);
            }
        });
        this.notifications.clear();
    }
}

// Create and export singleton instance
export const notificationManager = new NotificationManager();

// Make globally available
window.notificationManager = notificationManager;

// Export class for potential multiple instances
export { NotificationManager };