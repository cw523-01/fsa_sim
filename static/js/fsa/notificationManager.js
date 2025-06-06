/**
 * Notification system for showing non-blocking error and success messages
 * Also handles simulation popups, error popups, and epsilon loops detection popups
 * Reuses existing popup CSS from simulation-popup.css
 */
class NotificationManager {
    constructor() {
        this.notifications = new Set();
        this.notificationCounter = 0;
        this.autoCloseTimeouts = new Map();
        this.epsilonLoopsResolver = null; // For handling epsilon loops popup promises
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
     * Show epsilon loops detection popup with options
     * @param {Object} epsilonLoopsResult - Result from epsilon loops detection
     * @param {Object} fsa - FSA object
     * @param {string} inputString - Input string
     * @returns {Promise<Object>} - Promise resolving to user decision
     */
    async showEpsilonLoopsPopup(epsilonLoopsResult, fsa, inputString) {
        return new Promise((resolve) => {
            // Store resolver for button handlers
            this.epsilonLoopsResolver = resolve;

            // Remove any existing epsilon loops popup
            const existingPopup = document.getElementById('epsilon-loops-popup');
            if (existingPopup) {
                existingPopup.remove();
            }

            // Create popup element
            const popup = document.createElement('div');
            popup.id = 'epsilon-loops-popup';
            popup.className = 'epsilon-loops-popup';

            // Build loop details
            let loopDetails = '';
            if (epsilonLoopsResult.loops && epsilonLoopsResult.loops.length > 0) {
                const reachableLoops = epsilonLoopsResult.loops.filter(loop => loop.reachable_from_start);

                loopDetails = `
                    <div class="epsilon-loops-details">
                        <div class="loops-summary">
                            <strong>⚠️ ${reachableLoops.length} reachable epsilon loop(s) detected!</strong>
                        </div>
                        <div class="loops-explanation">
                            Epsilon loops can cause infinite execution paths during simulation, 
                            potentially making the simulation run forever or consume excessive resources.
                        </div>
                `;

                if (reachableLoops.length > 0) {
                    loopDetails += '<div class="loops-list">';
                    reachableLoops.forEach((loop, index) => {
                        const loopType = loop.loop_type === 'self_loop' ? 'Self-loop' : 'Multi-state cycle';
                        const states = loop.states_in_cycle.join(' → ');
                        loopDetails += `
                            <div class="loop-item">
                                <div class="loop-header">${loopType} ${index + 1}:</div>
                                <div class="loop-states">${states}</div>
                            </div>
                        `;
                    });
                    loopDetails += '</div>';
                }

                loopDetails += '</div>';
            }

            popup.innerHTML = `
                <div class="popup-header">
                    <div class="popup-status warning">
                        <div class="popup-icon warning">
                            <img src="static/img/alert.png" alt="Warning" style="width: 20px; height: 20px;">
                        </div>
                        <span>EPSILON LOOPS DETECTED</span>
                    </div>
                    <button class="popup-close" onclick="notificationManager.handleEpsilonLoopsCancel()">×</button>
                </div>
                <div class="popup-input">
                    Input: <span class="popup-input-string">"${inputString}"</span>
                </div>
                ${loopDetails}
                <div class="epsilon-loops-options">
                    <div class="option-section">
                        <h4>Choose how to proceed:</h4>
                        
                        <div class="option-item">
                            <input type="radio" id="ignore-loops" name="loop-option" value="ignore" checked>
                            <label for="ignore-loops">
                                <strong>Ignore epsilon loops</strong>
                                <span class="option-description">Proceed with normal simulation but skip over epsilon loops</span>
                            </label>
                        </div>
                        
                        <div class="option-item">
                            <input type="radio" id="set-depth-limit" name="loop-option" value="depth_limit">
                            <label for="set-depth-limit">
                                <strong>Set depth limit</strong>
                                <span class="option-description">Limit epsilon transition depth to prevent infinite loops</span>
                            </label>
                        </div>
                        
                        <div class="depth-limit-section" id="depth-limit-section" style="display: none;">
                            <label for="depth-limit-input">Maximum epsilon transition depth:</label>
                            <input type="number" id="depth-limit-input" min="1" max="1000" value="15" step="1">
                            <span class="depth-limit-help">Recommended: lenght of input + number of ε-transitions</span>
                        </div>
                    </div>
                </div>
                <div class="popup-actions">
                    <button class="popup-action-btn cancel" onclick="notificationManager.handleEpsilonLoopsCancel()">
                        Cancel
                    </button>
                    <button class="popup-action-btn proceed" onclick="notificationManager.handleEpsilonLoopsProceed()">
                        Proceed with Simulation
                    </button>
                </div>
                <div class="popup-progress">
                    <div class="popup-progress-bar warning"></div>
                </div>
            `;

            // Add popup to canvas
            const canvas = document.getElementById('fsa-canvas');
            if (canvas) {
                canvas.appendChild(popup);

                // Setup event handlers for radio buttons
                this.setupEpsilonLoopsEventHandlers();

                // Trigger show animation
                setTimeout(() => {
                    popup.classList.add('show');
                }, 100);
            }
        });
    }

    /**
     * Setup event handlers for epsilon loops popup
     */
    setupEpsilonLoopsEventHandlers() {
        const radioButtons = document.querySelectorAll('input[name="loop-option"]');
        const depthLimitSection = document.getElementById('depth-limit-section');

        radioButtons.forEach(radio => {
            radio.addEventListener('change', () => {
                if (radio.value === 'depth_limit' && radio.checked) {
                    depthLimitSection.style.display = 'block';
                    // Focus on the input field
                    const depthInput = document.getElementById('depth-limit-input');
                    if (depthInput) {
                        setTimeout(() => depthInput.focus(), 100);
                    }
                } else {
                    depthLimitSection.style.display = 'none';
                }
            });
        });

        // Validate depth limit input
        const depthInput = document.getElementById('depth-limit-input');
        if (depthInput) {
            depthInput.addEventListener('input', () => {
                const value = parseInt(depthInput.value);
                if (isNaN(value) || value < 1) {
                    depthInput.value = 1;
                } else if (value > 1000) {
                    depthInput.value = 1000;
                }
            });
        }
    }

    /**
     * Handle epsilon loops popup cancel
     */
    handleEpsilonLoopsCancel() {
        this.hideEpsilonLoopsPopup();
        if (this.epsilonLoopsResolver) {
            this.epsilonLoopsResolver({ action: 'cancel' });
            this.epsilonLoopsResolver = null;
        }
    }

    /**
     * Handle epsilon loops popup proceed
     */
    handleEpsilonLoopsProceed() {
        const selectedOption = document.querySelector('input[name="loop-option"]:checked');

        if (!selectedOption) {
            this.showError('Selection Required', 'Please select an option to proceed.');
            return;
        }

        let result = { action: selectedOption.value };

        if (selectedOption.value === 'depth_limit') {
            const depthInput = document.getElementById('depth-limit-input');
            if (depthInput) {
                const maxDepth = parseInt(depthInput.value);
                if (isNaN(maxDepth) || maxDepth < 1) {
                    this.showError('Invalid Depth', 'Please enter a valid depth limit (1 or greater).');
                    return;
                }
                result.maxDepth = maxDepth;
            } else {
                result.maxDepth = 100; // fallback default
            }
        }

        this.hideEpsilonLoopsPopup();

        if (this.epsilonLoopsResolver) {
            this.epsilonLoopsResolver(result);
            this.epsilonLoopsResolver = null;
        }
    }

    /**
     * Hide epsilon loops popup
     */
    hideEpsilonLoopsPopup() {
        const popup = document.getElementById('epsilon-loops-popup');
        if (popup) {
            popup.classList.add('hide');

            setTimeout(() => {
                if (popup.parentNode) {
                    popup.parentNode.removeChild(popup);
                }
            }, 400);
        }
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

        // Also hide epsilon loops popup
        this.hideEpsilonLoopsPopup();
    }

    /**
     * Check if there are any active notifications
     * @returns {boolean} - Whether there are active notifications
     */
    hasActiveNotifications() {
        const hasRegularNotifications = this.notifications.size > 0;
        const hasSimulationPopup = document.getElementById('simulation-result-popup') !== null;
        const hasEpsilonLoopsPopup = document.getElementById('epsilon-loops-popup') !== null;
        return hasRegularNotifications || hasSimulationPopup || hasEpsilonLoopsPopup;
    }

    /**
     * Get count of active notifications
     * @returns {number} - Number of active notifications
     */
    getActiveNotificationCount() {
        const regularCount = this.notifications.size;
        const simulationCount = document.getElementById('simulation-result-popup') ? 1 : 0;
        const epsilonLoopsCount = document.getElementById('epsilon-loops-popup') ? 1 : 0;
        return regularCount + simulationCount + epsilonLoopsCount;
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

        // Clear epsilon loops popup
        const epsilonLoopsPopup = document.getElementById('epsilon-loops-popup');
        if (epsilonLoopsPopup && epsilonLoopsPopup.parentNode) {
            epsilonLoopsPopup.parentNode.removeChild(epsilonLoopsPopup);
        }

        // Clear all timeouts
        this.autoCloseTimeouts.forEach(timeoutId => clearTimeout(timeoutId));
        this.autoCloseTimeouts.clear();

        // Clear epsilon loops resolver
        if (this.epsilonLoopsResolver) {
            this.epsilonLoopsResolver({ action: 'cancel' });
            this.epsilonLoopsResolver = null;
        }
    }
}

// Create and export singleton instance
export const notificationManager = new NotificationManager();

// Make globally available
window.notificationManager = notificationManager;

// Export class for potential multiple instances
export { NotificationManager };