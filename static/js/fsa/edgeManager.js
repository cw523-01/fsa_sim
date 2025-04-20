import { updateAlphabetDisplay } from './alphabetManager.js';
import { updateFSAPropertiesDisplay } from './fsaPropertyChecker.js';

// Map to store edge symbols
const edgeSymbolMap = new Map();
// Map to track epsilon transitions
const epsilonTransitionMap = new Map();
// Map to store all connections
const connectionMap = new Map();
// Flag to track if we're using curved edges
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
 * @param {Object} callbacks - Object with callback functions
 * @returns {Object} - The created connection
 */
export function createConnection(jsPlumbInstance, source, target, symbolsString, hasEpsilon, callbacks) {
    // Determine connector type based on current setting and if it's a self-loop
    const connectorType = determineConnectorType(source, target);

    const connection = jsPlumbInstance.connect({
        source: source,
        target: target,
        type: "basic",
        connector: connectorType,
        anchors: source === target ? ["Top", "Left"] : ["Continuous", "Continuous"]
    });

    // Store the connection in our map
    connectionMap.set(connection.id, connection);

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
            if (callbacks.onEdgeClick) {
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

    connection.getOverlay("label").setLabel(label);
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
 * Determines the connector type based on source, target, and current edge style preference
 * @param {string} source - Source state ID
 * @param {string} target - Target state ID
 * @returns {Array} - JSPlumb connector configuration
 */
function determineConnectorType(source, target) {
    const isSelfLoop = source === target;

    if (isSelfLoop) {
        // Self-loops are always curved
        return ["Bezier", { curviness: 60 }];
    } else if (useCurvedEdges) {
        // Use StateMachine for curved edges (better for FSA diagrams)
        return ["StateMachine", { curviness: 100 }];
    } else {
        // Use Straight for straight edges
        return "Straight";
    }
}

/**
 * Toggles between straight and curved edges
 * @param {Object} jsPlumbInstance - The JSPlumb instance
 * @param {boolean} curved - Whether to use curved edges
 */
export function toggleEdgeStyle(jsPlumbInstance, curved) {
    useCurvedEdges = curved;

    // Update all existing connections
    if (jsPlumbInstance) {
        // Make a snapshot of all connections before modifying anything
        const connections = jsPlumbInstance.getAllConnections();

        // Store connection details for recreation
        const connectionDetails = [];

        // First, gather all connection details
        for (let i = 0; i < connections.length; i++) {
            const connection = connections[i];

            // Skip the starting state connection
            if (connection.canvas && connection.canvas.classList.contains('starting-connection')) {
                continue;
            }

            // Store connection properties
            connectionDetails.push({
                sourceId: connection.sourceId,
                targetId: connection.targetId,
                connectionId: connection.id,
                symbols: edgeSymbolMap.get(connection.id) || [],
                hasEpsilon: epsilonTransitionMap.get(connection.id) || false,
                sourceAnchor: connection.endpoints[0].anchor.type,
                targetAnchor: connection.endpoints[1].anchor.type
            });
        }

        // Now remove all non-starting connections
        for (let i = connections.length - 1; i >= 0; i--) {
            const connection = connections[i];
            if (connection.canvas && !connection.canvas.classList.contains('starting-connection')) {
                deleteEdge(jsPlumbInstance, connection);
            }
        }

        // Recreate all connections with the new style
        connectionDetails.forEach(detail => {
            const connectorType = determineConnectorType(detail.sourceId, detail.targetId);

            // Create a new connection with the desired connector type
            const newConnection = jsPlumbInstance.connect({
                source: detail.sourceId,
                target: detail.targetId,
                connector: connectorType,
                anchors: [detail.sourceAnchor, detail.targetAnchor],
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

            // Update the maps with the new connection
            connectionMap.set(newConnection.id, newConnection);
            edgeSymbolMap.set(newConnection.id, detail.symbols);
            epsilonTransitionMap.set(newConnection.id, detail.hasEpsilon);

            // Update the label
            updateConnectionLabel(newConnection, detail.symbols, detail.hasEpsilon);

            // Add epsilon class if needed
            if (detail.hasEpsilon && newConnection.canvas) {
                newConnection.canvas.classList.add('has-epsilon');
            }

            // Add click handlers to the new connection
            if (newConnection.canvas) {
                newConnection.canvas.addEventListener('click', function(e) {
                    if (window.handleEdgeClick) {
                        window.handleEdgeClick(newConnection, e);
                    } else {
                        const currentTool = window.getCurrentTool ? window.getCurrentTool() : null;
                        if (currentTool === 'delete') {
                            deleteEdge(jsPlumbInstance, newConnection);
                        } else if (window.openInlineEdgeEditor) {
                            window.openInlineEdgeEditor(newConnection, jsPlumbInstance);
                        }
                    }
                    e.stopPropagation();
                });
            }

            // Add click handler for the label
            const labelOverlay = newConnection.getOverlay("label");
            if (labelOverlay && labelOverlay.canvas) {
                $(labelOverlay.canvas).on('click', function(e) {
                    if (window.handleEdgeClick) {
                        window.handleEdgeClick(newConnection, e);
                    } else {
                        const currentTool = window.getCurrentTool ? window.getCurrentTool() : null;
                        if (currentTool === 'delete') {
                            deleteEdge(jsPlumbInstance, newConnection);
                        } else if (window.openInlineEdgeEditor) {
                            window.openInlineEdgeEditor(newConnection, jsPlumbInstance);
                        }
                    }
                    e.stopPropagation();
                    e.preventDefault();
                });
            }

        });

        // Repaint everything to apply changes
        jsPlumbInstance.repaintEverything();

        updateAlphabetDisplay(edgeSymbolMap, epsilonTransitionMap);
    }
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