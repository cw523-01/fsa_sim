/**
 * Notification system for showing non-blocking error and success messages
 * Also handles simulation popups, error popups, and other popup types
 * Reuses existing popup CSS from simulation-popup.css
 */
class NotificationManager {
    constructor() {
        this.notifications = new Set();
        this.notificationCounter = 0;
        this.autoCloseTimeouts = new Map();
    }

    /**
     * Show an error notification
     * @param {string} title - The error title
     * @param {string} message - The error message
     * @param {number} duration - Auto-hide duration in milliseconds (default: 5000)
     */
    showError(title, message, duration = 5000) {
        return this.showNotification('error', title, message, duration);
    }

    /**
     * Show a warning notification
     * @param {string} title - The warning title
     * @param {string} message - The warning message
     * @param {number} duration - Auto-hide duration in milliseconds (default: 4000)
     */
    showWarning(title, message, duration = 4000) {
        return this.showNotification('warning', title, message, duration);
    }

    /**
     * Show a success notification
     * @param {string} title - The success title
     * @param {string} message - The success message
     * @param {number} duration - Auto-hide duration in milliseconds (default: 3000)
     */
    showSuccess(title, message, duration = 3000) {
        return this.showNotification('success', title, message, duration);
    }

    /**
     * Show an info notification
     * @param {string} title - The info title
     * @param {string} message - The info message
     * @param {number} duration - Auto-hide duration in milliseconds (default: 4000)
     */
    showInfo(title, message, duration = 4000) {
        return this.showNotification('info', title, message, duration);
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
     * Show simulation result popup (for DFA visual and fast-forward)
     * @param {Object} result - Result from backend simulation
     * @param {string} inputString - The input string that was simulated
     * @param {boolean} isFastForward - Whether this was a fast-forward simulation
     * @param {Array} executionPath - Execution path for display
     */
    showSimulationResultPopup(result, inputString, isFastForward = false, executionPath = null) {
        // Remove any existing popup
        const existingPopup = document.getElementById('simulation-result-popup');
        if (existingPopup) {
            existingPopup.remove();
        }

        // Create popup element
        const popup = document.createElement('div');
        popup.id = 'simulation-result-popup';
        popup.className = result.accepted ? 'accepted' : 'rejected';

        // Build popup content
        const statusText = result.accepted ? 'ACCEPTED' : 'REJECTED';
        const statusIcon = result.accepted ?
            '<img src="static/img/success.png" alt="Accepted" style="width: 20px; height: 20px;">' :
            '<img src="static/img/error.png" alt="Rejected" style="width: 20px; height: 20px;">';

        const statusClass = result.accepted ? 'accepted' : 'rejected';

        // Use execution path from parameter if provided, otherwise from result
        const pathToDisplay = executionPath || result.path || [];

        let pathDetails = '';
        if (pathToDisplay && pathToDisplay.length > 0) {
            pathDetails = `
                <div class="popup-path">
                    ${pathToDisplay.map((step, index) => {
                        const [currentState, symbol, nextState] = step;
                        return `<div class="popup-path-step">${index + 1}. ${currentState} --${symbol}--> ${nextState}</div>`;
                    }).join('')}
                </div>
            `;

            const finalState = pathToDisplay[pathToDisplay.length - 1][2];
            const finalStateText = result.accepted ?
                `Final state: ${finalState} (accepting)` :
                `Final state: ${finalState} (non-accepting)`;

            pathDetails += `<div class="popup-final-state ${statusClass}">${finalStateText}</div>`;
        } else {
            // Handle empty string case
            const startingStateId = this.getStartingStateId();
            if (startingStateId) {
                const finalStateText = result.accepted ?
                    `Final state: ${startingStateId} (accepting)` :
                    `Final state: ${startingStateId} (non-accepting)`;

                pathDetails = `
                    <div class="popup-path">
                        <div class="popup-path-step">Empty string processed in starting state</div>
                    </div>
                    <div class="popup-final-state ${statusClass}">${finalStateText}</div>
                `;
            }
        }

        popup.innerHTML = `
            <div class="popup-header">
                <div class="popup-status ${statusClass}">
                    <div class="popup-icon ${statusClass}">${statusIcon}</div>
                    <span>INPUT ${statusText}</span>
                </div>
                <button class="popup-close" onclick="notificationManager.hideSimulationResultPopup()">×</button>
            </div>
            <div class="popup-input">
                Input: <span class="popup-input-string">"${inputString}"</span>
            </div>
            <div class="popup-result ${statusClass}">
                Result: ${statusText}
            </div>
            ${pathDetails}
            <div class="popup-progress">
                <div class="popup-progress-bar ${statusClass}"></div>
            </div>
        `;

        // Add popup to canvas
        const canvas = document.getElementById('fsa-canvas');
        if (canvas) {
            canvas.appendChild(popup);

            // Trigger show animation
            setTimeout(() => {
                popup.classList.add('show');
            }, 100);

            // Start auto-close timer
            this.startSimulationPopupAutoCloseTimer(popup);
        }

        return popup;
    }

    /**
     * Show simulation error popup
     * @param {string} errorMessage - The error message to display
     * @param {string} inputString - The input string (if any)
     */
    showSimulationErrorPopup(errorMessage, inputString = '') {
        // Remove any existing popup
        const existingPopup = document.getElementById('simulation-result-popup');
        if (existingPopup) {
            existingPopup.remove();
        }

        // Create error popup element
        const popup = document.createElement('div');
        popup.id = 'simulation-result-popup';
        popup.className = 'error';

        const inputDisplay = inputString ?
            `<div class="popup-input">Input: <span class="popup-input-string">"${inputString}"</span></div>` : '';

        popup.innerHTML = `
            <div class="popup-header">
                <div class="popup-status error">
                    <div class="popup-icon error"><img src="static/img/alert.png" alt="Error" style="width: 20px; height: 20px;"></div>
                    <span>SIMULATION ERROR</span>
                </div>
                <button class="popup-close" onclick="notificationManager.hideSimulationResultPopup()">×</button>
            </div>
            ${inputDisplay}
            <div class="popup-result error">
                Error: Simulation Failed
            </div>
            <div class="popup-details">
                ${errorMessage.replace(/\n/g, '<br>')}
            </div>
            <div class="popup-progress">
                <div class="popup-progress-bar" style="background-color: #ff9800;"></div>
            </div>
        `;

        // Add popup to canvas
        const canvas = document.getElementById('fsa-canvas');
        if (canvas) {
            canvas.appendChild(popup);

            // Trigger show animation
            setTimeout(() => {
                popup.classList.add('show');
            }, 100);

            // Start auto-close timer (longer for error messages)
            this.startSimulationPopupAutoCloseTimer(popup, 7000); // 7 seconds for errors
        }

        return popup;
    }

    /**
     * Hide simulation result popup
     */
    hideSimulationResultPopup() {
        const popup = document.getElementById('simulation-result-popup');
        if (popup) {
            popup.classList.add('hide');

            setTimeout(() => {
                if (popup.parentNode) {
                    popup.parentNode.removeChild(popup);
                }
            }, 400);
        }

        // Clear auto-close timeout
        const timeoutId = this.autoCloseTimeouts.get('simulation-result-popup');
        if (timeoutId) {
            clearTimeout(timeoutId);
            this.autoCloseTimeouts.delete('simulation-result-popup');
        }
    }

    /**
     * Get starting state ID (helper function)
     * @returns {string|null} - Starting state ID
     */
    getStartingStateId() {
        // Try to get starting state from the state manager
        if (typeof getStartingStateId === 'function') {
            return getStartingStateId();
        }

        // Fallback: look for starting state indicator in DOM
        const startingConnections = document.querySelectorAll('.starting-connection');
        if (startingConnections.length > 0) {
            // Look for a connection from 'start-source'
            if (window.jsPlumbInstance) {
                const allConnections = window.jsPlumbInstance.getAllConnections();
                const connection = allConnections.find(conn =>
                    conn.canvas && conn.canvas.classList.contains('starting-connection')
                );
                if (connection) {
                    return connection.targetId;
                }
            }
        }

        // Final fallback: get first state element
        const stateElements = document.querySelectorAll('.state, .accepting-state');
        if (stateElements.length > 0) {
            return stateElements[0].id;
        }

        return null;
    }

    /**
     * Start auto-close timer for simulation popup
     * @param {HTMLElement} popup - The popup element
     * @param {number} customDelay - Custom delay in milliseconds (optional)
     */
    startSimulationPopupAutoCloseTimer(popup, customDelay = null) {
        const autoCloseDelay = customDelay || 5000; // Default 5 seconds, or custom delay

        // Animate progress bar
        const progressBar = popup.querySelector('.popup-progress-bar');
        if (progressBar) {
            progressBar.style.width = '100%';
            progressBar.style.transition = `width ${autoCloseDelay}ms linear`;

            // Start with 0 width, then animate to full
            setTimeout(() => {
                progressBar.style.width = '0%';
            }, 100);
        }

        // Set auto-close timeout
        const timeoutId = setTimeout(() => {
            this.hideSimulationResultPopup();
        }, autoCloseDelay);

        this.autoCloseTimeouts.set('simulation-result-popup', timeoutId);
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

        // Clear auto-close timeout
        const timeoutId = this.autoCloseTimeouts.get(notificationId);
        if (timeoutId) {
            clearTimeout(timeoutId);
            this.autoCloseTimeouts.delete(notificationId);
        }

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
        const timeoutId = setTimeout(() => {
            this.hideNotification(notification.id);
        }, duration);

        this.autoCloseTimeouts.set(notification.id, timeoutId);
    }

    /**
     * Hide all notifications
     */
    hideAllNotifications() {
        const allNotifications = Array.from(this.notifications);
        allNotifications.forEach(n => {
            this.hideNotification(n.id);
        });

        // Also hide simulation result popup
        this.hideSimulationResultPopup();
    }

    /**
     * Check if there are any active notifications
     * @returns {boolean} - Whether there are active notifications
     */
    hasActiveNotifications() {
        const hasRegularNotifications = this.notifications.size > 0;
        const hasSimulationPopup = document.getElementById('simulation-result-popup') !== null;
        return hasRegularNotifications || hasSimulationPopup;
    }

    /**
     * Get count of active notifications
     * @returns {number} - Number of active notifications
     */
    getActiveNotificationCount() {
        const regularCount = this.notifications.size;
        const simulationCount = document.getElementById('simulation-result-popup') ? 1 : 0;
        return regularCount + simulationCount;
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

        // Clear simulation popup
        const simulationPopup = document.getElementById('simulation-result-popup');
        if (simulationPopup && simulationPopup.parentNode) {
            simulationPopup.parentNode.removeChild(simulationPopup);
        }

        // Clear all timeouts
        this.autoCloseTimeouts.forEach(timeoutId => clearTimeout(timeoutId));
        this.autoCloseTimeouts.clear();
    }
}

// Create and export singleton instance
export const notificationManager = new NotificationManager();

// Make globally available
window.notificationManager = notificationManager;

// Export class for potential multiple instances
export { NotificationManager };