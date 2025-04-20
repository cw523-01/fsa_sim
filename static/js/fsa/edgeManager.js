import { updateAlphabetDisplay } from './alphabetManager.js';
import { updateFSAPropertiesDisplay } from './fsaPropertyChecker.js';

// Map to store edge symbols
const edgeSymbolMap = new Map();
// Map to track epsilon transitions
const epsilonTransitionMap = new Map();

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
    const connection = jsPlumbInstance.connect({
        source: source,
        target: target,
        type: "basic",
        connector: source === target ? ["Bezier", { curviness: 60 }] : "Straight",
        anchors: source === target ? ["Top", "Left"] : ["Continuous", "Continuous"]
    });

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

    edgeSymbolMap.delete(connection.id);
    epsilonTransitionMap.delete(connection.id);
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
 * Get the epsilon symbol
 * @returns {string} - The epsilon symbol
 */
export function getEpsilonSymbol() {
    return EPSILON;
}