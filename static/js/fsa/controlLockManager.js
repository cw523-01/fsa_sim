/**
 * Control lock manager class to handle disabling/enabling UI during simulation
 */
class ControlLockManager {
    constructor() {
        this.isLocked = false;
        this.jsPlumbInstance = null;
        this.originalMakeSource = null;
        this.originalMakeTarget = null;
        this.originalConnect = null;
        this.originalAddEndpoint = null;
        this.originalSettings = null;
    }

    /**
     * Initialize the control lock manager with JSPlumb instance
     * @param {Object} jsPlumbInstance - The JSPlumb instance to lock/unlock
     */
    initialize(jsPlumbInstance) {
        this.jsPlumbInstance = jsPlumbInstance;

        // Store original JSPlumb methods so we can restore them later
        if (jsPlumbInstance) {
            this.originalMakeSource = jsPlumbInstance.makeSource.bind(jsPlumbInstance);
            this.originalMakeTarget = jsPlumbInstance.makeTarget.bind(jsPlumbInstance);
            this.originalConnect = jsPlumbInstance.connect.bind(jsPlumbInstance);
        }
    }

    /**
     * Lock all controls to prevent user interaction during simulation
     */
    lockControls() {
        if (this.isLocked) return; // Already locked

        this.isLocked = true;
        console.log('Locking all controls...');

        // 1. Disable input field
        this.lockInputField();

        // 2. Disable tool selection
        this.lockToolPanel();

        // 3. Disable canvas interactions (but preserve popup interactions)
        this.lockCanvasInteractions();

        // 4. Disable JSPlumb interactions
        this.lockJSPlumbInteractions();

        // 5. Disable state and edge interactions
        this.lockStateAndEdgeInteractions();

        // 6. Close any open editors/modals
        this.closeOpenEditors();

        // 7. Update button states
        this.updateButtonStates(true);

        // 8. Lock undo/redo functionality
        this.lockUndoRedo();

        // 9. Add visual indicator that controls are locked
        this.addLockedIndicator();
    }

    /**
     * Unlock all controls to restore user interaction
     */
    unlockControls() {
        if (!this.isLocked) return; // Already unlocked

        this.isLocked = false;
        console.log('Unlocking all controls...');

        // 1. Enable input field
        this.unlockInputField();

        // 2. Enable tool selection
        this.unlockToolPanel();

        // 3. Enable canvas interactions
        this.unlockCanvasInteractions();

        // 4. Enable JSPlumb interactions
        this.unlockJSPlumbInteractions();

        // 5. Enable state and edge interactions
        this.unlockStateAndEdgeInteractions();

        // 6. Update button states
        this.updateButtonStates(false);

        // 7. Unlock undo/redo functionality
        this.unlockUndoRedo();

        // 8. Remove visual indicator
        this.removeLockedIndicator();
    }

    /**
     * Check if controls are currently locked
     * @returns {boolean} - Whether controls are locked
     */
    isControlsLocked() {
        return this.isLocked;
    }

    /**
     * Lock undo/redo functionality during simulation
     */
    lockUndoRedo() {
        const menuUndo = document.getElementById('menu-undo');
        const menuRedo = document.getElementById('menu-redo');

        if (menuUndo) {
            menuUndo.classList.add('simulation-disabled');
            menuUndo.title = 'Undo disabled during simulation';
        }

        if (menuRedo) {
            menuRedo.classList.add('simulation-disabled');
            menuRedo.title = 'Redo disabled during simulation';
        }

        console.log('Undo/Redo functionality locked during simulation');
    }

    /**
     * Unlock undo/redo functionality after simulation
     */
    unlockUndoRedo() {
        const menuUndo = document.getElementById('menu-undo');
        const menuRedo = document.getElementById('menu-redo');

        if (menuUndo) {
            menuUndo.classList.remove('simulation-disabled');
            // Restore original title from undo/redo manager
            if (window.undoRedoManager) {
                const nextUndoDescription = window.undoRedoManager.getNextUndoDescription();
                menuUndo.title = nextUndoDescription ? `Undo: ${nextUndoDescription}` : 'Nothing to undo';
            } else {
                menuUndo.title = 'Undo last action';
            }
        }

        if (menuRedo) {
            menuRedo.classList.remove('simulation-disabled');
            // Restore original title from undo/redo manager
            if (window.undoRedoManager) {
                const nextRedoDescription = window.undoRedoManager.getNextRedoDescription();
                menuRedo.title = nextRedoDescription ? `Redo: ${nextRedoDescription}` : 'Nothing to redo';
            } else {
                menuRedo.title = 'Redo last action';
            }
        }

        console.log('Undo/Redo functionality unlocked after simulation');
    }

    // Private methods for locking specific components

    lockInputField() {
        const inputField = document.getElementById('fsa-input');
        if (inputField) {
            inputField.disabled = true;
            inputField.classList.add('locked-input');
        }
    }

    unlockInputField() {
        const inputField = document.getElementById('fsa-input');
        if (inputField) {
            inputField.disabled = false;
            inputField.classList.remove('locked-input');
        }
    }

    lockToolPanel() {
        const toolsPanel = document.querySelector('.tools-panel');
        if (toolsPanel) {
            toolsPanel.classList.add('locked-panel');

            // Disable all tools
            const tools = toolsPanel.querySelectorAll('.tool');
            tools.forEach(tool => {
                tool.classList.add('locked-tool');
                tool.style.pointerEvents = 'none';
                tool.style.opacity = '0.5';
            });

            // Disable edge style buttons
            const edgeStyleButtons = toolsPanel.querySelectorAll('.edge-style-buttons button');
            edgeStyleButtons.forEach(button => {
                button.disabled = true;
                button.classList.add('locked-button');
            });

            // Disable show table button
            const showTableBtn = document.getElementById('show-table-btn');
            if (showTableBtn) {
                showTableBtn.disabled = true;
                showTableBtn.classList.add('locked-button');
            }
        }
    }

    unlockToolPanel() {
        const toolsPanel = document.querySelector('.tools-panel');
        if (toolsPanel) {
            toolsPanel.classList.remove('locked-panel');

            // Enable all tools
            const tools = toolsPanel.querySelectorAll('.tool');
            tools.forEach(tool => {
                tool.classList.remove('locked-tool');
                tool.style.pointerEvents = 'auto';
                tool.style.opacity = '1';
            });

            // Enable edge style buttons
            const edgeStyleButtons = toolsPanel.querySelectorAll('.edge-style-buttons button');
            edgeStyleButtons.forEach(button => {
                button.disabled = false;
                button.classList.remove('locked-button');
            });

            // Enable show table button
            const showTableBtn = document.getElementById('show-table-btn');
            if (showTableBtn) {
                showTableBtn.disabled = false;
                showTableBtn.classList.remove('locked-button');
            }
        }
    }

    lockCanvasInteractions() {
        const canvas = document.getElementById('fsa-canvas');
        if (canvas) {
            canvas.classList.add('locked-canvas');

            // Instead of disabling all pointer events on the canvas,
            // we'll use CSS to selectively disable interaction with FSA elements
            // while preserving popup interactions
            this.addCanvasLockStyles();
        }
    }

    unlockCanvasInteractions() {
        const canvas = document.getElementById('fsa-canvas');
        if (canvas) {
            canvas.classList.remove('locked-canvas');
            this.removeCanvasLockStyles();
        }
    }

    /**
     * Add CSS styles to selectively lock canvas interactions while preserving popups
     */
    addCanvasLockStyles() {
        if (document.getElementById('canvas-lock-styles')) return;

        const style = document.createElement('style');
        style.id = 'canvas-lock-styles';
        style.textContent = `
            /* Disable interactions with FSA elements during simulation */
            .locked-canvas .state,
            .locked-canvas .accepting-state,
            .locked-canvas .jsplumb-connector,
            .locked-canvas .jsplumb-endpoint,
            .locked-canvas .edge-label,
            .locked-canvas ._jsPlumb_connector,
            .locked-canvas ._jsPlumb_endpoint,
            .locked-canvas .starting-connection {
                pointer-events: none !important;
            }
            
            /* Preserve popup interactions */
            .locked-canvas .nfa-results-popup,
            .locked-canvas .nfa-results-popup *,
            .locked-canvas #simulation-result-popup,
            .locked-canvas #simulation-result-popup *,
            .locked-canvas .notification-popup,
            .locked-canvas .notification-popup *,
            .locked-canvas #lock-indicator,
            .locked-canvas #lock-indicator * {
                pointer-events: auto !important;
            }
            
            /* Ensure canvas background doesn't interfere with popups */
            .locked-canvas {
                pointer-events: auto;
            }
        `;
        document.head.appendChild(style);
    }

    /**
     * Remove CSS styles for canvas lock
     */
    removeCanvasLockStyles() {
        const style = document.getElementById('canvas-lock-styles');
        if (style) {
            style.remove();
        }
    }

    lockJSPlumbInteractions() {
        if (!this.jsPlumbInstance) return;

        // Store current settings so we can restore them later
        this.originalSettings = {
            ConnectionsDetachable: this.jsPlumbInstance.Defaults.ConnectionsDetachable,
            ReattachConnections: this.jsPlumbInstance.Defaults.ReattachConnections,
            ConnectorsDetachable: this.jsPlumbInstance.Defaults.ConnectorsDetachable
        };

        // Disable drag for all elements
        this.jsPlumbInstance.setDraggable(this.jsPlumbInstance.getSelector('.state, .accepting-state'), false);

        // Override JSPlumb methods to prevent new connections
        this.jsPlumbInstance.makeSource = () => {};
        this.jsPlumbInstance.makeTarget = () => {};
        this.jsPlumbInstance.connect = () => null;

        // Disable connection dragging/detaching completely
        this.jsPlumbInstance.importDefaults({
            ConnectionsDetachable: false,
            ReattachConnections: false,
            ConnectorsDetachable: false
        });

        // Get all existing connections and make them non-detachable
        const allConnections = this.jsPlumbInstance.getAllConnections();
        allConnections.forEach(connection => {
            // Make this specific connection non-detachable
            connection.setDetachable(false);

            // Disable endpoint dragging for this connection
            if (connection.endpoints) {
                connection.endpoints.forEach(endpoint => {
                    if (endpoint) {
                        endpoint.setEnabled(false);
                        // Also disable the endpoint's drag capability
                        if (endpoint.endpoint) {
                            endpoint.endpoint.enabled = false;
                        }
                    }
                });
            }

            // Add CSS class to visually indicate locked state
            if (connection.canvas) {
                connection.canvas.classList.add('jsplumb-locked');
            }
        });

        // Disable all endpoints globally
        const allEndpoints = this.jsPlumbInstance.selectEndpoints();
        allEndpoints.each(function(endpoint) {
            endpoint.setEnabled(false);
        });

        // Prevent new endpoint creation by overriding addEndpoint
        this.originalAddEndpoint = this.jsPlumbInstance.addEndpoint;
        this.jsPlumbInstance.addEndpoint = () => null;
    }

    unlockJSPlumbInteractions() {
        if (!this.jsPlumbInstance) return;

        // Re-enable drag for all elements
        this.jsPlumbInstance.setDraggable(this.jsPlumbInstance.getSelector('.state, .accepting-state'), true);

        // Restore original JSPlumb methods
        if (this.originalMakeSource) {
            this.jsPlumbInstance.makeSource = this.originalMakeSource;
        }
        if (this.originalMakeTarget) {
            this.jsPlumbInstance.makeTarget = this.originalMakeTarget;
        }
        if (this.originalConnect) {
            this.jsPlumbInstance.connect = this.originalConnect;
        }

        // Restore original connection settings
        if (this.originalSettings) {
            this.jsPlumbInstance.importDefaults({
                ConnectionsDetachable: this.originalSettings.ConnectionsDetachable,
                ReattachConnections: this.originalSettings.ReattachConnections,
                ConnectorsDetachable: this.originalSettings.ConnectorsDetachable
            });
        }

        // Re-enable all existing connections
        const allConnections = this.jsPlumbInstance.getAllConnections();
        allConnections.forEach(connection => {
            // Make this specific connection detachable again (unless it's the starting connection)
            if (!connection.canvas || !connection.canvas.classList.contains('starting-connection')) {
                connection.setDetachable(true);
            }

            // Re-enable endpoint dragging for this connection
            if (connection.endpoints) {
                connection.endpoints.forEach(endpoint => {
                    if (endpoint) {
                        endpoint.setEnabled(true);
                        // Re-enable the endpoint's drag capability
                        if (endpoint.endpoint) {
                            endpoint.endpoint.enabled = true;
                        }
                    }
                });
            }

            // Remove locked CSS class
            if (connection.canvas) {
                connection.canvas.classList.remove('jsplumb-locked');
            }
        });

        // Re-enable all endpoints globally
        const allEndpoints = this.jsPlumbInstance.selectEndpoints();
        allEndpoints.each(function(endpoint) {
            endpoint.setEnabled(true);
        });

        // Restore original addEndpoint method
        if (this.originalAddEndpoint) {
            this.jsPlumbInstance.addEndpoint = this.originalAddEndpoint;
        }
    }

    lockStateAndEdgeInteractions() {
        // Disable all state click handlers
        const states = document.querySelectorAll('.state, .accepting-state');
        states.forEach(state => {
            state.classList.add('locked-state');
            // Don't disable pointer events here - let CSS handle it
            state.style.opacity = '0.7';
        });

        // Disable all connection click handlers
        if (this.jsPlumbInstance) {
            const connections = this.jsPlumbInstance.getAllConnections();
            connections.forEach(conn => {
                if (conn.canvas) {
                    conn.canvas.classList.add('locked-connection');
                    // Don't disable pointer events here - let CSS handle it
                    conn.canvas.style.opacity = '0.7';
                }

                // Disable label clicks too
                const labelOverlay = conn.getOverlay('label');
                if (labelOverlay && labelOverlay.canvas) {
                    // Don't disable pointer events here - let CSS handle it
                    labelOverlay.canvas.style.opacity = '0.7';
                }
            });
        }
    }

    unlockStateAndEdgeInteractions() {
        // Re-enable all state click handlers
        const states = document.querySelectorAll('.state, .accepting-state');
        states.forEach(state => {
            state.classList.remove('locked-state');
            state.style.pointerEvents = 'auto';
            state.style.opacity = '1';
        });

        // Re-enable all connection click handlers
        if (this.jsPlumbInstance) {
            const connections = this.jsPlumbInstance.getAllConnections();
            connections.forEach(conn => {
                if (conn.canvas) {
                    conn.canvas.classList.remove('locked-connection');
                    conn.canvas.style.pointerEvents = 'auto';
                    conn.canvas.style.opacity = '1';
                }

                // Re-enable label clicks too
                const labelOverlay = conn.getOverlay('label');
                if (labelOverlay && labelOverlay.canvas) {
                    labelOverlay.canvas.style.pointerEvents = 'auto';
                    labelOverlay.canvas.style.opacity = '1';
                }
            });
        }
    }

    closeOpenEditors() {
        // Close inline state editor
        const stateEditor = document.getElementById('state-inline-editor');
        if (stateEditor) {
            stateEditor.style.display = 'none';
        }

        // Close inline edge editor
        const edgeEditor = document.getElementById('edge-inline-editor');
        if (edgeEditor) {
            edgeEditor.style.display = 'none';
        }

        // Close edge symbol modal
        const edgeModal = document.getElementById('edge-symbol-modal');
        if (edgeModal) {
            edgeModal.style.display = 'none';
        }

        // Close transition table modal
        const tableModal = document.getElementById('transition-table-modal');
        if (tableModal) {
            tableModal.style.display = 'none';
        }
    }

    updateButtonStates(locked) {
        const playBtn = document.getElementById('play-btn');
        const stopBtn = document.getElementById('stop-btn');
        const fastForwardBtn = document.getElementById('fast-forward-btn');

        if (locked) {
            // During simulation: disable play and fast-forward, enable stop
            if (playBtn) {
                playBtn.disabled = true;
                playBtn.classList.add('locked-button');
            }
            if (fastForwardBtn) {
                fastForwardBtn.disabled = true;
                fastForwardBtn.classList.add('locked-button');
            }
            if (stopBtn) {
                stopBtn.disabled = false;
                stopBtn.classList.remove('locked-button');
                stopBtn.classList.add('active-button');
            }
        } else {
            // Not simulating: enable play and fast-forward, disable stop
            if (playBtn) {
                playBtn.disabled = false;
                playBtn.classList.remove('locked-button');
            }
            if (fastForwardBtn) {
                fastForwardBtn.disabled = false;
                fastForwardBtn.classList.remove('locked-button');
            }
            if (stopBtn) {
                stopBtn.disabled = false; // Keep enabled but not active
                stopBtn.classList.remove('active-button');
            }
        }
    }

    addLockedIndicator() {
        // Add a subtle overlay or border to indicate locked state
        const canvas = document.getElementById('fsa-canvas');
        if (canvas && !document.getElementById('lock-indicator')) {
            const indicator = document.createElement('div');
            indicator.id = 'lock-indicator';
            indicator.innerHTML = `
                <div class="lock-message">
                    <div class="lock-icon">🔒</div>
                    <div class="lock-text">Simulation Running...</div>
                </div>
            `;
            indicator.style.cssText = `
                position: absolute;
                top: 10px;
                right: 10px;
                background-color: rgba(255, 193, 7, 0.9);
                color: #000;
                padding: 8px 12px;
                border-radius: 5px;
                font-size: 12px;
                font-weight: bold;
                z-index: 1000;
                box-shadow: 0 2px 4px rgba(0,0,0,0.2);
                display: flex;
                align-items: center;
                gap: 5px;
                pointer-events: auto;
            `;
            canvas.appendChild(indicator);
        }
    }

    removeLockedIndicator() {
        const indicator = document.getElementById('lock-indicator');
        if (indicator) {
            indicator.remove();
        }
    }
}

// Create and export a singleton instance
export const controlLockManager = new ControlLockManager();

// Export the class as well for potential multiple instances
export { ControlLockManager };