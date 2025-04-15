/**
 * Returns a connection between two states if it exists
 * @param {Object} jsPlumbInstance - The JSPlumb instance
 * @param {string} sourceId - Source state ID
 * @param {string} targetId - Target state ID
 * @returns {Object|null} - The connection object or null
 */
export function getConnectionBetween(jsPlumbInstance, sourceId, targetId) {
    const allConnections = jsPlumbInstance.getAllConnections();
    return allConnections.find(conn =>
        conn.sourceId === sourceId && conn.targetId === targetId
    );
}

/**
 * Creates a unique ID for a state
 * @param {number} counter - The current state counter
 * @returns {string} - The state ID
 */
export function createStateId(counter) {
    return 'S' + counter;
}