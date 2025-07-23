import { getEpsilonTransitionMap } from "./edgeManager.js";
import { updateFSADisplays } from './fsaUpdateUtils.js';

// State management
let stateCounter = 0;
let startingStateId = null;
let startingStateConnection = null;

/**
 * Creates a unique ID for a state
 * @param {number} counter - The current state counter
 * @returns {string} - The state ID
 */
function createStateId(counter) {
    return 'S' + counter;
}

/**
 * JSPlumb cleanup utilities to handle ID reuse issues
 */
const jsPlumbCleanup = {
    /**
     * Completely remove all traces of an element from JSPlumb
     * @param {Object} jsPlumbInstance - The JSPlumb instance
     * @param {string} elementId - The ID of the element to clean up
     * @returns {boolean} - Success status
     */
    completelyRemoveElement(jsPlumbInstance, elementId) {
        if (!jsPlumbInstance || !elementId) return false;

        try {
            console.log(`Starting complete JSPlumb removal of element: ${elementId}`);

            const element = document.getElementById(elementId);
            if (!element) {
                return true; // Element doesn't exist
            }

            // 1. Remove all connections involving this element
            const connections = jsPlumbInstance.getConnections({
                source: elementId
            }).concat(jsPlumbInstance.getConnections({
                target: elementId
            }));

            connections.forEach(conn => {
                try {
                    jsPlumbInstance.deleteConnection(conn);
                } catch (error) {
                    console.warn(`Error deleting connection:`, error);
                }
            });

            // 2. Remove all endpoints for this element
            try {
                jsPlumbInstance.removeAllEndpoints(elementId);
            } catch (error) {
                console.warn(`Error removing endpoints for ${elementId}:`, error);
            }

            // 3. Remove the element from JSPlumb's management
            try {
                // Check if element is managed by JSPlumb before attempting removal
                const managedElements = jsPlumbInstance.getManagedElements();
                if (managedElements && managedElements[elementId]) {
                    jsPlumbInstance.remove(elementId);
                } else {
                    console.log(`Element ${elementId} was not managed by JSPlumb, skipping remove() call`);
                }
            } catch (error) {
                console.warn(`Error removing element ${elementId} from JSPlumb:`, error);
                // Continue with manual cleanup even if remove() failed
            }

            // 4. CRITICAL: Clean up managed elements cache manually
            // This is the key fix for ID reuse issues
            try {
                const managedElements = jsPlumbInstance.getManagedElements();
                if (managedElements && managedElements[elementId]) {
                    delete managedElements[elementId];
                    console.log(`Manually deleted ${elementId} from JSPlumb managed elements cache`);
                }
            } catch (error) {
                console.warn(`Error cleaning managed elements cache for ${elementId}:`, error);
            }

            console.log(`Successfully completed JSPlumb removal of element: ${elementId}`);
            return true;

        } catch (error) {
            console.error(`Error during complete element removal for ${elementId}:`, error);
            return false;
        }
    },

    /**
     * Prepare an element ID for safe reuse
     * @param {Object} jsPlumbInstance - The JSPlumb instance
     * @param {string} elementId - The ID that will be reused
     */
    prepareForIdReuse(jsPlumbInstance, elementId) {
        console.log(`Preparing JSPlumb for ID reuse: ${elementId}`);

        if (!jsPlumbInstance) return;

        // Suspend drawing during cleanup for performance
        jsPlumbInstance.setSuspendDrawing(true);

        try {
            this.completelyRemoveElement(jsPlumbInstance, elementId);
        } finally {
            jsPlumbInstance.setSuspendDrawing(false);
        }

        console.log(`ID ${elementId} is now safe for reuse`);
    }
};

/**
 * Gets the next available state ID that doesn't conflict with existing states
 * Always starts from S0 and finds the first available gap
 * @returns {string} - The next available state ID
 */
function getNextAvailableStateId() {
    let counter = 0;
    let candidateId;

    // Always start from 0 and find the first available ID
    do {
        candidateId = createStateId(counter);
        counter++;
    } while (document.getElementById(candidateId));

    return candidateId;
}

/**
 * Updates the state counter to ensure it doesn't conflict with an existing state ID
 * This is kept for backward compatibility but not used in ID generation
 * @param {string} stateId - The state ID to check against
 */
function ensureCounterIsUpToDate(stateId) {
    // Extract the numeric part from the state ID (e.g., "S0" -> 0, "S12" -> 12)
    const match = stateId.match(/^S(\d+)$/);
    if (match) {
        const stateNumber = parseInt(match[1], 10);
        // Ensure our counter is at least one higher than this state number
        if (stateCounter <= stateNumber) {
            stateCounter = stateNumber + 1;
        }
    }
}

/**
 * Creates a state element on the canvas
 * @param {Object} jsPlumbInstance - The JSPlumb instance
 * @param {number} x - X position
 * @param {number} y - Y position
 * @param {boolean} isAccepting - Whether the state is an accepting state
 * @param {Object} callbacks - Object with callback functions
 * @param {string|null} explicitStateId - Optional explicit state ID to use (for undo/redo)
 * @returns {HTMLElement} - The created state element
 */
export function createState(jsPlumbInstance, x, y, isAccepting, callbacks, explicitStateId = null) {
    let stateId;

    if (explicitStateId) {
        // Use the provided explicit state ID
        stateId = explicitStateId;

        // Check if a state with this ID already exists
        if (document.getElementById(stateId)) {
            console.error(`State with ID ${stateId} already exists!`);
            return null;
        }

        // Update the counter for backward compatibility (but don't use it for generation)
        ensureCounterIsUpToDate(stateId);
    } else {
        // Always find the next available ID starting from S0
        stateId = getNextAvailableStateId();

        // Update the counter for backward compatibility
        ensureCounterIsUpToDate(stateId);
    }

    // Ensure JSPlumb has no lingering references to this ID
    // This prevents the connection issue when IDs are reused
    jsPlumbCleanup.prepareForIdReuse(jsPlumbInstance, stateId);

    const state = document.createElement('div');
    state.id = stateId;
    state.className = isAccepting ? 'accepting-state' : 'state';
    state.innerHTML = stateId;
    state.style.left = (x - 30) + 'px';
    state.style.top = (y - 30) + 'px';

    // Add GPU acceleration hints
    state.style.willChange = 'transform';
    state.style.transform = 'translate3d(0, 0, 0)';

    document.getElementById('fsa-canvas').appendChild(state);

    // Automatically set the first state as the starting state
    if (startingStateId === null) {
        createStartingStateIndicator(jsPlumbInstance, stateId);
    }

    // Make state draggable with performance optimisations
    $(state).draggable({
        containment: "parent",
        stack: ".state, .accepting-state",
        zIndex: 100,
        start: function(event, ui) {
            // Mark that we're starting to drag a state
            if (window.isStateDragging !== undefined) {
                window.isStateDragging = true;
            }

            // Disable animations during drag
            document.body.classList.add('no-animation');

            // Ensure GPU acceleration
            this.style.willChange = 'transform';

            // Store original position for transform calculations
            const rect = this.getBoundingClientRect();
            const parentRect = this.parentElement.getBoundingClientRect();
            this._originalLeft = rect.left - parentRect.left;
            this._originalTop = rect.top - parentRect.top;
        },
        drag: function(event, ui) {
            // Update starting state arrow if this is the starting state - REAL TIME
            if (startingStateId === this.id) {
                const startSource = document.getElementById('start-source');
                if (startSource) {
                    // Update both left/top in real-time during drag
                    const stateHeight = this.offsetHeight;
                    const newLeft = ui.position.left - 50;
                    const newTop = ui.position.top + (stateHeight / 2) - 5;
                    startSource.style.left = newLeft + 'px';
                    startSource.style.top = newTop + 'px';
                }
            }

            // Use transform instead of top/left for better performance
            const deltaX = ui.position.left - this._originalLeft;
            const deltaY = ui.position.top - this._originalTop;

            // Revalidate this state and the start-source
            jsPlumbInstance.revalidate(this.id);
            if (startingStateId === this.id) {
                jsPlumbInstance.revalidate('start-source');
            }

            if (callbacks.onStateDrag) {
                callbacks.onStateDrag(this, event, ui);
            }
        },
        stop: function(event, ui) {
            // Re-enable animations after drag
            document.body.classList.remove('no-animation');

            // Reset will-change after drag completes
            setTimeout(() => {
                this.style.willChange = 'auto';
            }, 100);

            // Final repaint after drag
            jsPlumbInstance.repaintEverything();

            // Set flag to prevent canvas click from creating new state
            setTimeout(() => {
                if (window.isStateDragging !== undefined) {
                    window.isStateDragging = false;
                }
            }, 10); // Small delay to let the click event fire first
        }
    });

    // CRITICAL: Use a more robust approach to JSPlumb registration
    // This ensures proper registration especially after ID reuse
    setTimeout(() => {
        // Force revalidation before registration
        jsPlumbInstance.revalidate(state.id);

        // Make state a connection source and target with error handling
        try {
            jsPlumbInstance.makeSource(state, {
                filter: ".edge-source",
                anchor: "Continuous",
                connectorStyle: { stroke: "black", strokeWidth: 2 },
                connectionType: "basic"
            });

            jsPlumbInstance.makeTarget(state, {
                anchor: "Continuous",
                connectionType: "basic"
            });

            console.log(`State ${stateId} successfully registered with JSPlumb`);

            // Force a repaint to ensure everything is visually correct
            jsPlumbInstance.repaintEverything();

        } catch (error) {
            console.error(`Error registering state ${stateId} with JSPlumb:`, error);

            // Retry registration after cleanup
            setTimeout(() => {
                console.log(`Retrying JSPlumb registration for state ${stateId}`);

                // Clean up any partial registration
                jsPlumbCleanup.completelyRemoveElement(jsPlumbInstance, stateId);

                // Wait a bit for cleanup to complete
                setTimeout(() => {
                    try {
                        jsPlumbInstance.revalidate(state.id);

                        jsPlumbInstance.makeSource(state, {
                            filter: ".edge-source",
                            anchor: "Continuous",
                            connectorStyle: { stroke: "black", strokeWidth: 2 },
                            connectionType: "basic"
                        });

                        jsPlumbInstance.makeTarget(state, {
                            anchor: "Continuous",
                            connectionType: "basic"
                        });

                        jsPlumbInstance.repaintEverything();
                        console.log(`State ${stateId} successfully registered with JSPlumb on retry`);

                    } catch (retryError) {
                        console.error(`Failed to register state ${stateId} with JSPlumb on retry:`, retryError);

                        // Last resort: suggest manual intervention
                        console.warn(`Manual intervention may be required for state ${stateId}. Consider calling window.fixStateConnectionIssues(jsPlumbInstance)`);
                    }
                }, 50);
            }, 100);
        }
    }, 25); // Slightly longer delay to ensure DOM is fully settled

    // Add click event handler
    state.addEventListener('click', function(e) {
        if (callbacks.onStateClick) {
            callbacks.onStateClick(this, e);
        }
        e.stopPropagation();
    });

    return state;
}

/**
 * Deletes a state element and its endpoints
 * @param {Object} jsPlumbInstance - The JSPlumb instance
 * @param {HTMLElement} stateElement - The state element to delete
 * @param {Map} edgeSymbolMap - Map of edge IDs to their symbols
 */
export function deleteState(jsPlumbInstance, stateElement, edgeSymbolMap) {
    const stateId = stateElement.id;

    // If this is the starting state, remove the starting state indicator
    if (startingStateId === stateId) {
        createStartingStateIndicator(jsPlumbInstance, null);
    }

    // Get all connections before removing the state
    const connections = jsPlumbInstance.getConnections({
        source: stateId
    }).concat(jsPlumbInstance.getConnections({
        target: stateId
    }));

    // Get the epsilonTransitionMap
    const epsilonTransitionMap = getEpsilonTransitionMap();

    // Remove connections from both maps before deleting the state
    connections.forEach(conn => {
        edgeSymbolMap.delete(conn.id);
        epsilonTransitionMap.delete(conn.id);
    });

    // Use cleanup to completely remove state from JSPlumb
    jsPlumbCleanup.completelyRemoveElement(jsPlumbInstance, stateId);

    // Remove from DOM
    stateElement.remove();

    // Use centralised update function
    updateFSADisplays(jsPlumbInstance);

    console.log(`State ${stateId} completely removed from JSPlumb and DOM`);
}

/**
 * Creates or updates the starting state indicator with robust connection handling
 * @param {Object} jsPlumbInstance - The JSPlumb instance
 * @param {string|null} stateId - The ID of the state to make starting, or null to remove
 */
export function createStartingStateIndicator(jsPlumbInstance, stateId) {
    console.log(`Creating starting state indicator for: ${stateId}`);

    // Clean up existing starting state connection thoroughly
    cleanupExistingStartingConnection(jsPlumbInstance);

    // Set the new starting state
    startingStateId = stateId;

    if (!stateId) {
        console.log('No starting state specified, indicator removed');
        return; // If null, just removing the previous indicator
    }

    // Verify the target state exists
    const stateElement = document.getElementById(stateId);
    if (!stateElement) {
        console.error(`Target state ${stateId} not found in DOM`);
        startingStateId = null; // Reset since the state doesn't exist
        return;
    }

    // Ensure the state is properly registered with JSPlumb before creating connection
    setTimeout(() => {
        // Double-check the state still exists (in case it was deleted during the timeout)
        const currentStateElement = document.getElementById(stateId);
        if (!currentStateElement) {
            console.warn(`State ${stateId} was removed before starting state indicator could be created`);
            startingStateId = null;
            return;
        }

        // Create or get the hidden source for the starting arrow
        const startSource = ensureStartSource(jsPlumbInstance);

        // Position the start source relative to the target state
        positionStartSource(startSource, currentStateElement);

        // Force JSPlumb to recognise both elements
        jsPlumbInstance.revalidate('start-source');
        jsPlumbInstance.revalidate(stateId);

        // Create the connection with multiple fallback attempts
        createStartingConnection(jsPlumbInstance, startSource, stateId);
    }, 50); // Small delay to ensure DOM and JSPlumb are synchronised
}

/**
 * Thoroughly clean up any existing starting state connections
 * @param {Object} jsPlumbInstance - The JSPlumb instance
 */
function cleanupExistingStartingConnection(jsPlumbInstance) {
    // Remove stored connection reference
    if (startingStateConnection) {
        try {
            const allConnections = jsPlumbInstance.getAllConnections();
            const connectionExists = allConnections.some(conn => conn.id === startingStateConnection.id);

            if (connectionExists) {
                jsPlumbInstance.deleteConnection(startingStateConnection);
            }
        } catch (error) {
            console.warn('Error deleting stored starting state connection:', error);
        }
        startingStateConnection = null;
    }

    // Clean up any starting connections by searching for them
    try {
        const allConnections = jsPlumbInstance.getAllConnections();
        const startingConnections = allConnections.filter(conn =>
            conn.canvas && conn.canvas.classList.contains('starting-connection')
        );

        startingConnections.forEach(conn => {
            try {
                jsPlumbInstance.deleteConnection(conn);
                console.log('Cleaned up stale starting connection:', conn.id);
            } catch (error) {
                console.warn('Error deleting stale starting connection:', error);
            }
        });
    } catch (error) {
        console.warn('Error cleaning up starting connections:', error);
    }

    // Also clean up connections from start-source
    try {
        const startSourceConnections = jsPlumbInstance.getConnections({ source: 'start-source' });
        startSourceConnections.forEach(conn => {
            try {
                jsPlumbInstance.deleteConnection(conn);
                console.log('Cleaned up start-source connection:', conn.id);
            } catch (error) {
                console.warn('Error deleting start-source connection:', error);
            }
        });
    } catch (error) {
        console.warn('Error cleaning up start-source connections:', error);
    }
}

/**
 * Ensure the start-source element exists and is properly configured
 * @param {Object} jsPlumbInstance - The JSPlumb instance
 * @returns {HTMLElement} - The start-source element
 */
function ensureStartSource(jsPlumbInstance) {
    let startSource = document.getElementById('start-source');

    if (!startSource) {
        startSource = document.createElement('div');
        startSource.id = 'start-source';
        startSource.className = 'start-source';
        // Add GPU acceleration but use absolute positioning
        startSource.style.position = 'absolute';
        startSource.style.willChange = 'auto'; // Don't force transform changes
        startSource.style.transform = 'translate3d(0, 0, 0)';
        document.getElementById('fsa-canvas').appendChild(startSource);
        console.log('Created new start-source element');
    }

    // Ensure it's properly configured as a source endpoint
    // Remove any existing endpoints first to avoid duplicates
    try {
        jsPlumbInstance.removeAllEndpoints('start-source');
    } catch (error) {
        // Ignore errors if element wasn't registered
    }

    // Make the start source a source endpoint
    jsPlumbInstance.makeSource(startSource, {
        anchor: "Right",
        connectorStyle: { stroke: "black", strokeWidth: 2 },
        connectionType: "basic"
    });

    return startSource;
}

/**
 * Position the start source relative to the target state
 * @param {HTMLElement} startSource - The start source element
 * @param {HTMLElement} stateElement - The target state element
 */
function positionStartSource(startSource, stateElement) {
    // Calculate center position of the state
    const stateHeight = stateElement.offsetHeight;
    const leftPos = stateElement.offsetLeft - 50;
    const topPos = stateElement.offsetTop + (stateHeight / 2) - 5; // Center vertically, adjust by -10 for visual alignment

    startSource.style.left = leftPos + 'px';
    startSource.style.top = topPos + 'px';
    startSource.style.transform = 'translate3d(0, 0, 0)'; // Just for GPU acceleration

    console.log(`Positioned start-source at (${leftPos}, ${topPos})`);
}

/**
 * Create the starting connection with robust error handling and retries
 * @param {Object} jsPlumbInstance - The JSPlumb instance
 * @param {HTMLElement} startSource - The start source element
 * @param {string} targetStateId - The target state ID
 */
function createStartingConnection(jsPlumbInstance, startSource, targetStateId) {
    // Function to attempt connection creation
    const attemptConnection = (attempt = 1) => {
        try {
            console.log(`Attempting to create starting connection (attempt ${attempt})`);

            // Verify both elements exist and are valid
            const sourceElement = document.getElementById('start-source');
            const targetElement = document.getElementById(targetStateId);

            if (!sourceElement || !targetElement) {
                console.error(`Missing elements - source: ${!!sourceElement}, target: ${!!targetElement}`);
                return false;
            }

            // Force JSPlumb to revalidate both elements
            jsPlumbInstance.revalidate('start-source');
            jsPlumbInstance.revalidate(targetStateId);

            // Create the connection with explicit configuration
            startingStateConnection = jsPlumbInstance.connect({
                source: 'start-source',
                target: targetStateId,
                connector: "Straight",
                anchors: ["Right", "Left"],
                overlays: [
                    ["Arrow", { location: 1, width: 12, length: 12 }]
                ],
                paintStyle: { stroke: "black", strokeWidth: 2 },
                // Prevent this connection from being affected by global settings
                cssClass: "starting-connection-line"
            });

            if (startingStateConnection) {
                // Mark the connection as special
                if (startingStateConnection.canvas) {
                    startingStateConnection.canvas.classList.add('starting-connection');
                }

                // Ensure no label is added
                if (startingStateConnection.getOverlay('label')) {
                    startingStateConnection.removeOverlay('label');
                }

                console.log(`Successfully created starting connection: ${startingStateConnection.id}`);
                return true;
            } else {
                console.error('Failed to create starting connection - connection is null');
                return false;
            }

        } catch (error) {
            console.error(`Error creating starting connection (attempt ${attempt}):`, error);
            return false;
        }
    };

    // Try immediate connection first
    if (attemptConnection(1)) {
        return;
    }

    // If immediate attempt fails, try with a small delay to let DOM settle
    setTimeout(() => {
        if (attemptConnection(2)) {
            return;
        }

        // Final attempt with full revalidation
        setTimeout(() => {
            console.log('Final attempt to create starting connection');
            jsPlumbInstance.repaintEverything();
            attemptConnection(3);
        }, 100);
    }, 50);
}

/**
 * Get the current starting state ID
 * @returns {string|null} - The ID of the starting state or null
 */
export function getStartingStateId() {
    return startingStateId;
}

/**
 * Get the current state counter value (kept for backward compatibility)
 * @returns {number} - The current state counter
 */
export function getStateCounter() {
    return stateCounter;
}

/**
 * Reset the state counter (useful for testing or clearing the canvas)
 */
export function resetStateCounter() {
    stateCounter = 0;
}

/**
 * Validates that a proposed state name doesn't conflict with existing states
 * @param {string} proposedName - The proposed state name
 * @param {string} currentStateId - The current state ID (for renames, can be null for new states)
 * @returns {boolean} - True if the name is valid
 */
export function validateStateName(proposedName, currentStateId = null) {
    // Empty names are not allowed
    if (!proposedName || !proposedName.trim()) {
        return false;
    }

    // If this is a rename and the name hasn't changed, it's valid
    if (currentStateId && proposedName === currentStateId) {
        return true;
    }

    // Check if an element with this ID already exists
    return !document.getElementById(proposedName);
}

/**
 * Force cleanup of JSPlumb references for a specific state ID
 * This helps prevent issues when reusing state IDs after renames
 * @param {Object} jsPlumbInstance - The JSPlumb instance
 * @param {string} stateId - The state ID to clean up
 */
export function forceCleanupStateReferences(jsPlumbInstance, stateId) {
    if (!jsPlumbInstance || !stateId) return;

    console.log(`Force cleaning up JSPlumb references for state: ${stateId}`);
    return jsPlumbCleanup.completelyRemoveElement(jsPlumbInstance, stateId);
}

/**
 * Reinitialise JSPlumb registration for an existing state element
 * Useful after state renames or when registration fails
 * @param {Object} jsPlumbInstance - The JSPlumb instance
 * @param {HTMLElement} stateElement - The state element to reinitialise
 * @returns {boolean} - True if successful
 */
export function reinitialiseStateWithJSPlumb(jsPlumbInstance, stateElement) {
    if (!jsPlumbInstance || !stateElement) return false;

    const stateId = stateElement.id;

    try {
        console.log(`Reinitialising JSPlumb registration for state: ${stateId}`);

        // First, clean up any existing registration
        jsPlumbCleanup.completelyRemoveElement(jsPlumbInstance, stateId);

        // Force revalidation
        jsPlumbInstance.revalidate(stateElement);

        // Re-register as source and target
        jsPlumbInstance.makeSource(stateElement, {
            filter: ".edge-source",
            anchor: "Continuous",
            connectorStyle: { stroke: "black", strokeWidth: 2 },
            connectionType: "basic"
        });

        jsPlumbInstance.makeTarget(stateElement, {
            anchor: "Continuous",
            connectionType: "basic"
        });

        console.log(`Successfully reinitialised JSPlumb registration for state: ${stateId}`);
        return true;

    } catch (error) {
        console.error(`Failed to reinitialise JSPlumb registration for state ${stateId}:`, error);
        return false;
    }
}

/**
 * Handle state ID changes (renames) by updating internal references
 * This should be called when a state is renamed to ensure consistency
 * @param {string} oldStateId - The old state ID
 * @param {string} newStateId - The new state ID
 * @param {Object} jsPlumbInstance - The JSPlumb instance
 */
export function handleStateIdChange(oldStateId, newStateId, jsPlumbInstance) {
    console.log(`Handling state ID change: ${oldStateId} -> ${newStateId}`);

    // Update starting state reference if necessary
    if (startingStateId === oldStateId) {
        console.log(`Updating starting state reference from ${oldStateId} to ${newStateId}`);
        startingStateId = newStateId;

        // Recreate the starting state indicator with the new ID
        // Use a timeout to ensure the state element has been fully updated
        setTimeout(() => {
            createStartingStateIndicator(jsPlumbInstance, newStateId);
        }, 100);
    }

    // Cleanup for the old ID to prevent connection issues
    jsPlumbCleanup.completelyRemoveElement(jsPlumbInstance, oldStateId);

    // Ensure the new state element is properly registered
    const newStateElement = document.getElementById(newStateId);
    if (newStateElement) {
        setTimeout(() => {
            reinitialiseStateWithJSPlumb(jsPlumbInstance, newStateElement);
        }, 150);
    }

    console.log(`State ID change handling completed: ${oldStateId} -> ${newStateId}`);
}
