import { createStateId } from './utils.js';
import { updateAlphabetDisplay } from './alphabetManager.js';
import { getEpsilonTransitionMap } from "./edgeManager.js";

// State management
let stateCounter = 0;
let startingStateId = null;
let startingStateConnection = null;

/**
 * Gets the next available state ID that doesn't conflict with existing states
 * @returns {string} - The next available state ID
 */
function getNextAvailableStateId() {
    let candidateId;
    let counter = stateCounter;

    do {
        candidateId = createStateId(counter);
        counter++;
    } while (document.getElementById(candidateId));

    // Update the state counter to be one past the ID we're using
    stateCounter = counter;

    return candidateId;
}

/**
 * Creates a state element on the canvas
 * @param {Object} jsPlumbInstance - The JSPlumb instance
 * @param {number} x - X position
 * @param {number} y - Y position
 * @param {boolean} isAccepting - Whether the state is an accepting state
 * @param {Object} callbacks - Object with callback functions
 * @returns {HTMLElement} - The created state element
 */
export function createState(jsPlumbInstance, x, y, isAccepting, callbacks) {
    // Use the smart state ID generation
    const stateId = getNextAvailableStateId();

    const state = document.createElement('div');
    state.id = stateId;
    state.className = isAccepting ? 'accepting-state' : 'state';
    state.innerHTML = stateId;
    state.style.left = (x - 30) + 'px';
    state.style.top = (y - 30) + 'px';

    document.getElementById('fsa-canvas').appendChild(state);

    // Automatically set the first state as the starting state
    if (startingStateId === null) {
        createStartingStateIndicator(jsPlumbInstance, stateId);
    }

    // Make state draggable
    $(state).draggable({
        containment: "parent",
        stack: ".state, .accepting-state",
        zIndex: 100,
        drag: function(event, ui) {
            jsPlumbInstance.repaintEverything();

            // Update starting state arrow if this is the starting state
            if (startingStateId === this.id) {
                const startSource = document.getElementById('start-source');
                if (startSource) {
                    startSource.style.left = (ui.position.left - 50) + 'px';
                    startSource.style.top = (ui.position.top + 30 - 5) + 'px';
                }
            }

            if (callbacks.onStateDrag) {
                callbacks.onStateDrag(this, event, ui);
            }
        }
    });

    // Make state a connection source and target
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
    // If this is the starting state, remove the starting state indicator
    if (startingStateId === stateElement.id) {
        createStartingStateIndicator(jsPlumbInstance, null);
    }

    // Get all connections before removing the state
    const connections = jsPlumbInstance.getConnections({
        source: stateElement.id
    }).concat(jsPlumbInstance.getConnections({
        target: stateElement.id
    }));

    // Get the epsilonTransitionMap
    const epsilonTransitionMap = getEpsilonTransitionMap();

    // Remove connections from both maps before deleting the state
    connections.forEach(conn => {
        edgeSymbolMap.delete(conn.id);
        epsilonTransitionMap.delete(conn.id);
    });

    // Remove the state and its endpoints
    jsPlumbInstance.removeAllEndpoints(stateElement.id);
    stateElement.remove();

    // Update the alphabet display after removing connections
    updateAlphabetDisplay(edgeSymbolMap, epsilonTransitionMap);
}

/**
 * Creates or updates the starting state indicator
 * @param {Object} jsPlumbInstance - The JSPlumb instance
 * @param {string|null} stateId - The ID of the state to make starting, or null to remove
 */
export function createStartingStateIndicator(jsPlumbInstance, stateId) {
    // Remove existing starting state connection if it exists
    if (startingStateConnection) {
        try {
            // Check if the connection still exists in JSPlumb before trying to delete it
            const allConnections = jsPlumbInstance.getAllConnections();
            const connectionExists = allConnections.some(conn => conn.id === startingStateConnection.id);

            if (connectionExists) {
                jsPlumbInstance.deleteConnection(startingStateConnection);
            }
        } catch (error) {
            console.warn('Error deleting starting state connection:', error);
            // Continue anyway - the connection might already be gone
        }
        startingStateConnection = null;
    }

    // Also remove any existing starting connections by searching for them
    // This is a safety measure in case the stored reference is stale
    try {
        const allConnections = jsPlumbInstance.getAllConnections();
        const startingConnections = allConnections.filter(conn =>
            conn.canvas && conn.canvas.classList.contains('starting-connection')
        );

        startingConnections.forEach(conn => {
            try {
                jsPlumbInstance.deleteConnection(conn);
            } catch (error) {
                console.warn('Error deleting stale starting connection:', error);
            }
        });
    } catch (error) {
        console.warn('Error cleaning up starting connections:', error);
    }

    // Set the new starting state
    startingStateId = stateId;

    if (!stateId) return; // If null, just removing the previous indicator

    // Create a hidden source point
    const stateElement = document.getElementById(stateId);
    if (!stateElement) return;

    // Create hidden source for the starting arrow if it doesn't exist
    let startSource = document.getElementById('start-source');
    if (!startSource) {
        startSource = document.createElement('div');
        startSource.id = 'start-source';
        startSource.className = 'start-source';
        document.getElementById('fsa-canvas').appendChild(startSource);

        // Make the start source a source endpoint
        jsPlumbInstance.makeSource(startSource, {
            anchor: "Right",
            connectorStyle: { stroke: "black", strokeWidth: 2 },
            connectionType: "basic"
        });
    }

    // Position the start source to the left of the state
    requestAnimationFrame(() => {
        startSource.style.left = (stateElement.offsetLeft - 50) + 'px';
        startSource.style.top = (stateElement.offsetTop + 25) + 'px';
        jsPlumbInstance.revalidate('start-source');

        // Create the connection after positioning
        try {
            // Always use straight connector for starting state connection
            startingStateConnection = jsPlumbInstance.connect({
                source: 'start-source',
                target: stateId,
                connector: "Straight",  // Always straight for starting arrow
                anchors: ["Right", "Left"],
                // Only include the arrow overlay, no label
                overlays: [
                    ["Arrow", { location: 1, width: 12, length: 12 }]
                ],
                // Custom paint style to avoid inheritance of default styles
                paintStyle: { stroke: "black", strokeWidth: 2 }
            });

            // Make the connection not deletable and not editable
            if (startingStateConnection && startingStateConnection.canvas) {
                startingStateConnection.canvas.classList.add('starting-connection');

                // Make sure no label is added
                if (startingStateConnection.getOverlay('label')) {
                    startingStateConnection.removeOverlay('label');
                }
            }
        } catch (error) {
            console.error('Error creating starting state connection:', error);
        }
    });
}

/**
 * Get the current starting state ID
 * @returns {string|null} - The ID of the starting state or null
 */
export function getStartingStateId() {
    return startingStateId;
}

/**
 * Get the current state counter value
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