import { updateAlphabetDisplay } from './alphabetManager.js';
import { updateFSAPropertiesDisplay } from './fsaPropertyChecker.js';

// Export functions to window for global access
window.getCurrentTool = function() {
    // Import from uiManager.js if available
    if (typeof getCurrentTool === 'function') {
        return getCurrentTool();
    }
    return null;
};

window.openInlineEdgeEditor = function(connection, jsPlumbInstance) {
    // Import from uiManager.js if available
    if (typeof openInlineEdgeEditor === 'function') {
        openInlineEdgeEditor(connection, jsPlumbInstance);
    }
};

// Map to store edge symbols
const edgeSymbolMap = new Map();
// Map to track epsilon transitions
const epsilonTransitionMap = new Map();
// Map to store all connections
const connectionMap = new Map();
// Map to store edge curve styles (true = curved, false = straight)
const edgeCurveStyleMap = new Map();
// Flag to track if we're using curved edges by default
let useCurvedEdges = false;

// Epsilon symbol
const EPSILON = 'ε';

/**
 * Creates a connection with a label
 * @param {Object} jsPlumbInstance - The JSPlumb instance
 * @param {string} source - Source state ID
 * @param {string} target - Target state ID
 * @param {string} symbolsString - Comma-separated string of symbols
 * @param {boolean} hasEpsilon - Whether the edge has an epsilon transition
 * @param {boolean} isCurved - Whether the edge should be curved
 * @param {Object} callbacks - Object with callback functions
 * @returns {Object} - The created connection
 */
export function createConnection(jsPlumbInstance, source, target, symbolsString, hasEpsilon, isCurved = null, callbacks) {
    // If curve style not specified, use the global default
    const curveStyle = isCurved !== null ? isCurved : useCurvedEdges;

    // Determine connector type based on curve style and if it's a self-loop
    const connectorType = determineConnectorType(source, target, curveStyle);

    const connection = jsPlumbInstance.connect({
        source: source,
        target: target,
        type: "basic",
        connector: connectorType,
        anchors: source === target ? ["Top", "Left"] : ["Continuous", "Continuous"],
        paintStyle: { stroke: "black", strokeWidth: 2 },
        hoverPaintStyle: { stroke: "#1e8151", strokeWidth: 3 },
        overlays: [
            ["Arrow", { location: 1, id: "arrow", width: 10, length: 10 }],
            ["Label", {
                id: "label",
                cssClass: "edge-label",
                location: 0.3,
                labelStyle: {
                    cssClass: "edge-label-style"
                }
            }]
        ]
    });

    // Store the connection in our map
    connectionMap.set(connection.id, connection);

    // Store the curve style in our map
    edgeCurveStyleMap.set(connection.id, curveStyle);

    // Parse and save symbols
    const symbols = symbolsString.split(',')
        .map(s => s.trim())
        .filter(s => s.length === 1);

    edgeSymbolMap.set(connection.id, symbols);
    epsilonTransitionMap.set(connection.id, hasEpsilon);

    // Set label with epsilon if needed
    updateConnectionLabel(connection, symbols, hasEpsilon);

    // Add epsilon class if needed
    if (hasEpsilon) {
        if (connection.canvas) {
            connection.canvas.classList.add('has-epsilon');
        }
    }

    // Add click handler
    if (connection.canvas) {
        connection.canvas.addEventListener('click', function (e) {
            if (callbacks && callbacks.onEdgeClick) {
                callbacks.onEdgeClick(connection, e);
            }
            e.stopPropagation();
        });
    }

    // Update the alphabet display with the new symbols
    updateAlphabetDisplay(edgeSymbolMap, epsilonTransitionMap);

    // Update FSA properties display
    updateFSAPropertiesDisplay(jsPlumbInstance);

    return connection;
}

/**
 * Updates the connection label
 * @param {Object} connection - The connection to update
 * @param {Array} symbols - Array of symbols
 * @param {boolean} hasEpsilon - Whether the edge has an epsilon transition
 */
function updateConnectionLabel(connection, symbols, hasEpsilon) {
    let label = symbols.join(',');

    if (hasEpsilon) {
        if (label.length > 0) {
            label = EPSILON + ',' + label;
        } else {
            label = EPSILON;
        }
    }

    const labelOverlay = connection.getOverlay("label");
    if (labelOverlay) {
        labelOverlay.setLabel(label);
    }
}

/**
 * Deletes an edge and its symbols
 * @param {Object} jsPlumbInstance - The JSPlumb instance
 * @param {Object} connection - The connection to delete
 */
export function deleteEdge(jsPlumbInstance, connection) {
    // Don't delete the starting state connection
    if (connection.canvas && connection.canvas.classList.contains('starting-connection')) {
        return;
    }

    // Remove from our maps
    edgeSymbolMap.delete(connection.id);
    epsilonTransitionMap.delete(connection.id);
    edgeCurveStyleMap.delete(connection.id);
    connectionMap.delete(connection.id);

    jsPlumbInstance.deleteConnection(connection);

    // Update alphabet display after removing an edge
    updateAlphabetDisplay(edgeSymbolMap, epsilonTransitionMap);

    // Update FSA properties display
    updateFSAPropertiesDisplay(jsPlumbInstance);
}

/**
 * Updates the symbols for an edge
 * @param {Object} connection - The connection to update
 * @param {Array} symbols - Array of symbols
 * @param {boolean} hasEpsilon - Whether the edge has an epsilon transition
 * @param {Object} jsPlumbInstance - Optional JSPlumb instance for updating properties
 */
export function updateEdgeSymbols(connection, symbols, hasEpsilon, jsPlumbInstance) {
    if (!connection) return;

    edgeSymbolMap.set(connection.id, symbols);
    epsilonTransitionMap.set(connection.id, hasEpsilon);

    // Update label with epsilon if needed
    updateConnectionLabel(connection, symbols, hasEpsilon);

    // Update epsilon class
    if (connection.canvas) {
        if (hasEpsilon) {
            connection.canvas.classList.add('has-epsilon');
        } else {
            connection.canvas.classList.remove('has-epsilon');
        }
    }

    // Update alphabet display
    updateAlphabetDisplay(edgeSymbolMap, epsilonTransitionMap);

    // Update FSA properties display if jsPlumbInstance is provided
    if (jsPlumbInstance) {
        updateFSAPropertiesDisplay(jsPlumbInstance);
    }
}

/**
 * Helper function to add event handlers to a connection
 * @param {Object} connection - The connection to add handlers to
 * @param {Object} jsPlumbInstance - The JSPlumb instance
 */
function setupConnectionHandlers(connection, jsPlumbInstance) {
    // Skip if this is a starting state connection
    if (connection.canvas && connection.canvas.classList.contains('starting-connection')) {
        return;
    }

    // Add click handler to the connection
    if (connection.canvas) {
        $(connection.canvas).on('click', function(e) {
            e.stopPropagation();
            e.preventDefault();

            const currentTool = window.getCurrentTool ? window.getCurrentTool() : null;
            if (currentTool === 'delete') {
                deleteEdge(jsPlumbInstance, connection);
            } else if (window.openInlineEdgeEditor) {
                window.openInlineEdgeEditor(connection, jsPlumbInstance);
            }
        });
    }

    // Add click handler for the label
    const labelOverlay = connection.getOverlay('label');
    if (labelOverlay && labelOverlay.canvas) {
        $(labelOverlay.canvas).on('click', function(e) {
            e.stopPropagation();
            e.preventDefault();

            const currentTool = window.getCurrentTool ? window.getCurrentTool() : null;
            if (currentTool === 'delete') {
                deleteEdge(jsPlumbInstance, connection);
            } else if (window.openInlineEdgeEditor) {
                window.openInlineEdgeEditor(connection, jsPlumbInstance);
            }
        });
    }
}

/**
 * Updates the curve style for an individual edge by completely recreating it
 * @param {Object} jsPlumbInstance - The JSPlumb instance
 * @param {Object} connection - The connection to update
 * @param {boolean} curved - Whether the edge should be curved
 * @returns {Object} - The new connection
 */
export function updateEdgeCurveStyle(jsPlumbInstance, connection, curved) {
    if (!connection) return null;

    // If the source and target are the same (self-loop), always use curved
    const isSelfLoop = connection.sourceId === connection.targetId;
    if (isSelfLoop) {
        curved = true; // Force curved for self-loops
    }

    // If the current style is already what we want, do nothing
    const currentStyle = edgeCurveStyleMap.get(connection.id);
    if (currentStyle === curved && !isSelfLoop) {
        return connection; // No change needed
    }

    // Store all current connection parameters
    const sourceId = connection.sourceId;
    const targetId = connection.targetId;
    const symbols = edgeSymbolMap.get(connection.id) || [];
    const hasEpsilon = epsilonTransitionMap.get(connection.id) || false;

    // Clean up maps before deleting
    edgeSymbolMap.delete(connection.id);
    epsilonTransitionMap.delete(connection.id);
    edgeCurveStyleMap.delete(connection.id);
    connectionMap.delete(connection.id);

    // Delete the old connection without firing events
    jsPlumbInstance.deleteConnection(connection, {fireEvent: false});

    // Create a new connection with the desired connector type
    const connectorType = determineConnectorType(sourceId, targetId, curved);

    // Recreate the connection with proper overlays
    const newConnection = jsPlumbInstance.connect({
        source: sourceId,
        target: targetId,
        connector: connectorType,
        anchors: sourceId === targetId ? ["Top", "Left"] : ["Continuous", "Continuous"],
        paintStyle: { stroke: "black", strokeWidth: 2 },
        hoverPaintStyle: { stroke: "#1e8151", strokeWidth: 3 },
        overlays: [
            ["Arrow", { location: 1, id: "arrow", width: 10, length: 10 }],
            ["Label", {
                id: "label",
                cssClass: "edge-label",
                location: 0.3,
                labelStyle: {
                    cssClass: "edge-label-style"
                }
            }]
        ]
    });

    // Update our maps with the new connection
    connectionMap.set(newConnection.id, newConnection);
    edgeSymbolMap.set(newConnection.id, symbols);
    epsilonTransitionMap.set(newConnection.id, hasEpsilon);
    edgeCurveStyleMap.set(newConnection.id, curved);

    // Set the label with proper symbols
    updateConnectionLabel(newConnection, symbols, hasEpsilon);

    // Add epsilon class if needed
    if (hasEpsilon && newConnection.canvas) {
        newConnection.canvas.classList.add('has-epsilon');
    }

    // Add click handlers
    setupConnectionHandlers(newConnection, jsPlumbInstance);

    return newConnection;
}


/**
 * Determines the connector type based on source, target, and specified curve style
 * @param {string} source - Source state ID
 * @param {string} target - Target state ID
 * @param {boolean} curved - Whether to use a curved edge
 * @returns {Array} - JSPlumb connector configuration
 */
function determineConnectorType(source, target, curved) {
    const isSelfLoop = source === target;

    if (isSelfLoop) {
        // Self-loops are always curved
        return ["Bezier", { curviness: 60 }];
    } else if (curved) {
        // Use StateMachine for curved edges (better for FSA diagrams)
        return ["StateMachine", { curviness: 100 }];
    } else {
        // Use Straight for straight edges
        return "Straight";
    }
}

/**
 * Applies a curve style to all edges
 * @param {Object} jsPlumbInstance - The JSPlumb instance
 * @param {boolean} curved - Whether to use curved edges
 */
export function setAllEdgeStyles(jsPlumbInstance, curved) {
    // Set the default for new edges
    useCurvedEdges = curved;

    if (!jsPlumbInstance) return;

    // Get ALL connections as an array (to avoid issues with changing collections)
    const allConnections = Array.from(jsPlumbInstance.getAllConnections());

    // First collect all the connection data we'll need
    const connectionsToUpdate = [];

    for (let i = 0; i < allConnections.length; i++) {
        const connection = allConnections[i];

        // Skip the starting state connection
        if (connection.canvas && connection.canvas.classList.contains('starting-connection')) {
            continue;
        }

        // Self-loops are always curved, so skip if trying to make straight
        if (connection.sourceId === connection.targetId && !curved) {
            continue;
        }

        // Get current curve style
        const currentStyle = edgeCurveStyleMap.get(connection.id) || false;

        // Only update if style is different
        if (currentStyle !== curved) {
            connectionsToUpdate.push({
                sourceId: connection.sourceId,
                targetId: connection.targetId,
                originalConnection: connection,
                symbols: edgeSymbolMap.get(connection.id) || [],
                hasEpsilon: epsilonTransitionMap.get(connection.id) || false
            });
        }
    }

    // Log how many connections we're updating
    console.log(`Updating ${connectionsToUpdate.length} connections to ${curved ? 'curved' : 'straight'}`);

    // Now process each connection one by one
    connectionsToUpdate.forEach(connData => {
        // Remove the old connection
        jsPlumbInstance.deleteConnection(connData.originalConnection);

        // Delete from our maps
        const oldId = connData.originalConnection.id;
        edgeSymbolMap.delete(oldId);
        epsilonTransitionMap.delete(oldId);
        edgeCurveStyleMap.delete(oldId);
        connectionMap.delete(oldId);

        // Determine connector type
        const connectorType = determineConnectorType(connData.sourceId, connData.targetId, curved);

        // Create a new connection
        const newConnection = jsPlumbInstance.connect({
            source: connData.sourceId,
            target: connData.targetId,
            connector: connectorType,
            anchors: connData.sourceId === connData.targetId ? ["Top", "Left"] : ["Continuous", "Continuous"],
            paintStyle: { stroke: "black", strokeWidth: 2 },
            hoverPaintStyle: { stroke: "#1e8151", strokeWidth: 3 },
            overlays: [
                ["Arrow", { location: 1, id: "arrow", width: 10, length: 10 }],
                ["Label", {
                    id: "label",
                    cssClass: "edge-label",
                    location: 0.3,
                    labelStyle: {
                        cssClass: "edge-label-style"
                    }
                }]
            ]
        });

        // Update our maps with the new connection
        connectionMap.set(newConnection.id, newConnection);
        edgeSymbolMap.set(newConnection.id, connData.symbols);
        epsilonTransitionMap.set(newConnection.id, connData.hasEpsilon);
        edgeCurveStyleMap.set(newConnection.id, curved);

        // Set the label with proper symbols
        updateConnectionLabel(newConnection, connData.symbols, connData.hasEpsilon);

        // Add epsilon class if needed
        if (connData.hasEpsilon && newConnection.canvas) {
            newConnection.canvas.classList.add('has-epsilon');
        }

        // Setup event handlers for the new connection
        setupConnectionHandlers(newConnection, jsPlumbInstance);
    });

    // Force a complete repaint
    jsPlumbInstance.repaintEverything();
}

/**
 * Gets the curve style for an edge
 * @param {Object} connection - The connection to check
 * @returns {boolean} - Whether the edge is curved
 */
export function getEdgeCurveStyle(connection) {
    return edgeCurveStyleMap.get(connection.id) || false;
}

/**
 * Gets the symbols for an edge
 * @param {Object} connection - The connection to get symbols for
 * @returns {Array} - Array of symbols
 */
export function getEdgeSymbols(connection) {
    return edgeSymbolMap.get(connection.id) || [];
}

/**
 * Checks if an edge has an epsilon transition
 * @param {Object} connection - The connection to check
 * @returns {boolean} - Whether the edge has an epsilon transition
 */
export function hasEpsilonTransition(connection) {
    return epsilonTransitionMap.get(connection.id) || false;
}

/**
 * Get the edge symbol map
 * @returns {Map} - The edge symbol map
 */
export function getEdgeSymbolMap() {
    return edgeSymbolMap;
}

/**
 * Get the epsilon transition map
 * @returns {Map} - The epsilon transition map
 */
export function getEpsilonTransitionMap() {
    return epsilonTransitionMap;
}

/**
 * Get the connection map
 * @returns {Map} - The connection map
 */
export function getConnectionMap() {
    return connectionMap;
}

/**
 * Get the epsilon symbol
 * @returns {string} - The epsilon symbol
 */
export function getEpsilonSymbol() {
    return EPSILON;
}

// For backward compatibility
export const toggleEdgeStyle = setAllEdgeStyles;