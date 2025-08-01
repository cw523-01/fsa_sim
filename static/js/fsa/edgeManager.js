import { updateFSADisplays } from './fsaUpdateUtils.js';

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
 * Validates symbols and prevents manual epsilon entry with comprehensive checks
 * @param {Array} symbols - Array of symbols to validate
 * @returns {Object} - Object with cleanedSymbols array, hasManualEpsilon boolean, and isEmpty boolean
 */
function validateAndCleanSymbols(symbols) {
    const cleanedSymbols = [];
    let hasManualEpsilon = false;

    for (const symbol of symbols) {
        if (symbol === EPSILON) {
            hasManualEpsilon = true;
            // Skip adding epsilon to cleaned symbols
            continue;
        }
        cleanedSymbols.push(symbol);
    }

    return {
        cleanedSymbols,
        hasManualEpsilon,
        isEmpty: cleanedSymbols.length === 0
    };
}

/**
 * Comprehensive validation for symbol strings with UI feedback
 * @param {string} symbolsString - Comma-separated string of symbols
 * @param {boolean} isNewTransition - Whether this is for a new transition (prevents empty)
 * @returns {Object} - Comprehensive validation result
 */
export function validateSymbolsInput(symbolsString, isNewTransition = false) {
    const rawSymbols = symbolsString.split(',')
        .map(s => s.trim())
        .filter(s => s.length === 1);

    const validation = validateAndCleanSymbols(rawSymbols);

    // Check for various validation issues
    const hasManualEpsilon = validation.hasManualEpsilon;
    const wouldBeEmpty = validation.isEmpty;
    const isValidForCreation = !wouldBeEmpty || !isNewTransition;

    return {
        isValid: !hasManualEpsilon && isValidForCreation,
        hasManualEpsilon,
        wouldBeEmpty,
        cleanedSymbols: validation.cleanedSymbols,
        cleanedString: validation.cleanedSymbols.join(','),
        errorMessage: hasManualEpsilon
            ? 'Manual epsilon entry not allowed. Use the epsilon checkbox instead.'
            : wouldBeEmpty && isNewTransition
            ? 'Transition must have at least one symbol or use epsilon checkbox.'
            : null
    };
}

/**
 * Shows appropriate notification for validation errors
 * @param {Object} validationResult - Result from validateSymbolsInput
 */
function showValidationNotification(validationResult) {
    if (!validationResult.errorMessage) return;

    if (window.notificationManager) {
        if (validationResult.hasManualEpsilon) {
            window.notificationManager.showWarning(
                'Manual Epsilon Not Allowed',
                'Please use the epsilon transition checkbox instead of manually entering "ε" as a symbol.'
            );
        } else if (validationResult.wouldBeEmpty) {
            window.notificationManager.showWarning(
                'Empty Transition Not Allowed',
                'Transition must have at least one symbol or use the epsilon checkbox.'
            );
        }
    }
}

/**
 * Function for UI to check if input should be highlighted red (for real-time validation)
 * @param {string} symbolsString - Comma-separated string of symbols
 * @param {boolean} hasEpsilon - Whether epsilon checkbox is checked
 * @param {boolean} isNewTransition - Whether this is for a new transition
 * @returns {boolean} - Whether the input should be highlighted red
 */
export function shouldHighlightInputRed(symbolsString, hasEpsilon = false, isNewTransition = false) {
    const validation = validateSymbolsInput(symbolsString, isNewTransition);

    // Highlight red if:
    // 1. Manual epsilon is entered, OR
    // 2. Would be empty without epsilon checkbox (for existing transitions)
    return validation.hasManualEpsilon || (validation.wouldBeEmpty && !hasEpsilon && !isNewTransition);
}

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
    // Validate symbols before creating connection
    const validation = validateSymbolsInput(symbolsString, true);

    // If validation fails and it would result in empty transition, prevent creation
    if (!validation.isValid && validation.wouldBeEmpty && !hasEpsilon) {
        showValidationNotification(validation);
        return null; // Prevent connection creation
    }

    // Show notification for manual epsilon but continue with cleaned symbols
    if (validation.hasManualEpsilon) {
        showValidationNotification(validation);
    }

    // If curve style not specified, use the global default
    const curveStyle = isCurved !== null ? isCurved : useCurvedEdges;

    // Check if this is a self-loop
    const isSelfLoop = source === target;

    // Determine connector type based on curve style and if it's a self-loop
    const connectorType = determineConnectorType(source, target, curveStyle);

    // Determine the CSS class for the label based on whether it's a self-loop
    const labelCssClass = isSelfLoop ? "edge-label-style self-loop-label" : "edge-label-style";

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
                    cssClass: labelCssClass
                }
            }]
        ]
    });

    // Store the connection in our map
    connectionMap.set(connection.id, connection);

    // Store the curve style in our map
    edgeCurveStyleMap.set(connection.id, curveStyle);

    // Use cleaned symbols
    const symbols = validation.cleanedSymbols;

    edgeSymbolMap.set(connection.id, symbols);
    epsilonTransitionMap.set(connection.id, hasEpsilon);

    // Set label with epsilon if needed
    updateConnectionLabel(connection, symbols, hasEpsilon);

    // Add self-loop-label class manually if this is a self-loop
    if (isSelfLoop) {
        const labelOverlay = connection.getOverlay('label');
        if (labelOverlay && labelOverlay.canvas) {
            labelOverlay.canvas.classList.add('self-loop-label');
        }
    }

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

    // Use centralised update function
    updateFSADisplays(jsPlumbInstance);

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

    // Use centralised update function
    updateFSADisplays(jsPlumbInstance);
}

/**
 * Updates the symbols for an edge with enhanced validation
 * @param {Object} connection - The connection to update
 * @param {Array} symbols - Array of symbols
 * @param {boolean} hasEpsilon - Whether the edge has an epsilon transition
 * @param {Object} jsPlumbInstance - Optional JSPlumb instance for updating properties
 */
export function updateEdgeSymbols(connection, symbols, hasEpsilon, jsPlumbInstance) {
    if (!connection) return;

    // Validate symbols and check for manual epsilon entry
    const validation = validateAndCleanSymbols(symbols);

    // Check if this would result in empty transition without epsilon
    const wouldBeEmpty = validation.isEmpty && !hasEpsilon;

    if (validation.hasManualEpsilon) {
        window.notificationManager.showWarning(
            'Manual Epsilon Not Allowed',
            'Please use the epsilon transition checkbox instead of manually entering "ε" as a symbol.'
        );
    }

    // Prevent empty transitions
    if (wouldBeEmpty) {
        window.notificationManager.showWarning(
            'Empty Transition Not Allowed',
            'Transition must have at least one symbol or use the epsilon checkbox.'
        );
        return; // Don't update if it would create empty transition
    }

    // Use cleaned symbols
    const cleanedSymbols = validation.cleanedSymbols;

    edgeSymbolMap.set(connection.id, cleanedSymbols);
    epsilonTransitionMap.set(connection.id, hasEpsilon);

    // Update label with epsilon if needed
    updateConnectionLabel(connection, cleanedSymbols, hasEpsilon);

    // Update epsilon class
    if (connection.canvas) {
        if (hasEpsilon) {
            connection.canvas.classList.add('has-epsilon');
        } else {
            connection.canvas.classList.remove('has-epsilon');
        }
    }

    // Use centralised update function if jsPlumbInstance is provided
    if (jsPlumbInstance) {
        updateFSADisplays(jsPlumbInstance);
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

    // Add self-loop-label class manually if this is a self-loop
    if (isSelfLoop) {
        const labelOverlay = newConnection.getOverlay('label');
        if (labelOverlay && labelOverlay.canvas) {
            labelOverlay.canvas.classList.add('self-loop-label');
        }
    }

    // Add epsilon class if needed
    if (hasEpsilon && newConnection.canvas) {
        newConnection.canvas.classList.add('has-epsilon');
    }

    // Add click handlers
    setupConnectionHandlers(newConnection, jsPlumbInstance);

    jsPlumbInstance.repaintEverything();

    updateFSADisplays(jsPlumbInstance);

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

        // Check if this is a self-loop
        const isSelfLoop = connection.sourceId === connection.targetId;

        // Self-loops are always curved, so skip if trying to make straight
        if (isSelfLoop && !curved) {
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
                hasEpsilon: epsilonTransitionMap.get(connection.id) || false,
                isSelfLoop: isSelfLoop
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

        // Add self-loop-label class manually if this is a self-loop
        if (connData.isSelfLoop) {
            const labelOverlay = newConnection.getOverlay('label');
            if (labelOverlay && labelOverlay.canvas) {
                labelOverlay.canvas.classList.add('self-loop-label');
            }
        }

        // Add epsilon class if needed
        if (connData.hasEpsilon && newConnection.canvas) {
            newConnection.canvas.classList.add('has-epsilon');
        }

        // Setup event handlers for the new connection
        setupConnectionHandlers(newConnection, jsPlumbInstance);
    });

    // Force a complete repaint
    jsPlumbInstance.repaintEverything();

    updateFSADisplays(jsPlumbInstance);
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

/**
 * Make getEdgeSymbols available globally for visual simulation
 */
window.getEdgeSymbols = getEdgeSymbols;

/**
 * Get the edge curve style map
 * @returns {Map} - The edge curve style map
 */
export function getEdgeCurveStyleMap() {
    return edgeCurveStyleMap;
}