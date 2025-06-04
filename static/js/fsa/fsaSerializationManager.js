import {
    getEdgeSymbolMap,
    getEpsilonTransitionMap,
    getEdgeCurveStyleMap,
    createConnection 
} from './edgeManager.js';
import {
  createState,
  createStartingStateIndicator,
  getStartingStateId
} from './stateManager.js';
import { updateAlphabetDisplay } from './alphabetManager.js';
import { updateFSAPropertiesDisplay } from './fsaPropertyChecker.js';
import { notificationManager } from './notificationManager.js';

/**
 * FSA Serialization Manager class
 */
class FSASerializationManager {
    constructor() {
        this.version = "1.0.0";
    }

    /**
     * Serialize the current FSA to a JSON object
     * @param {Object} jsPlumbInstance - The JSPlumb instance
     * @returns {Object} - Serialized FSA data
     */
    serializeFSA(jsPlumbInstance) {
        try {
            const serializedData = {
                version: this.version,
                timestamp: new Date().toISOString(),
                metadata: {
                    name: "Untitled FSA",
                    description: "",
                    creator: "FSA Simulator",
                    tags: []
                },
                states: this.serializeStates(),
                transitions: this.serializeTransitions(jsPlumbInstance),
                startingState: getStartingStateId(),
                canvasProperties: this.serializeCanvasProperties()
            };

            console.log('FSA serialized successfully');
            return serializedData;

        } catch (error) {
            console.error('Error serializing FSA:', error);
            throw new Error(`Failed to serialize FSA: ${error.message}`);
        }
    }

    /**
     * Serialize all states in the FSA
     * @returns {Array} - Array of serialized state objects
     */
    serializeStates() {
        const states = [];
        const stateElements = document.querySelectorAll('.state, .accepting-state');

        stateElements.forEach(stateElement => {
            const state = {
                id: stateElement.id,
                label: stateElement.textContent.trim(),
                isAccepting: stateElement.classList.contains('accepting-state'),
                position: {
                    x: parseInt(stateElement.style.left) || 0,
                    y: parseInt(stateElement.style.top) || 0
                },
                // Store visual properties
                visual: {
                    className: stateElement.className,
                    zIndex: stateElement.style.zIndex || 'auto'
                }
            };
            states.push(state);
        });

        return states;
    }

    /**
     * Serialize all transitions in the FSA
     * @param {Object} jsPlumbInstance - The JSPlumb instance
     * @returns {Array} - Array of serialized transition objects
     */
    serializeTransitions(jsPlumbInstance) {
        const transitions = [];
        const connections = jsPlumbInstance.getAllConnections();
        const edgeSymbolMap = getEdgeSymbolMap();
        const epsilonTransitionMap = getEpsilonTransitionMap();

        connections.forEach(connection => {
            // Skip starting state connections
            if (connection.canvas && connection.canvas.classList.contains('starting-connection')) {
                return;
            }

            const transition = {
                id: connection.id,
                sourceId: connection.sourceId,
                targetId: connection.targetId,
                symbols: edgeSymbolMap.get(connection.id) || [],
                hasEpsilon: epsilonTransitionMap.get(connection.id) || false,
                visual: {
                    connectorType: this.getConnectorType(connection),
                    isCurved: this.getConnectionCurveStyle(connection),
                    paintStyle: connection.getPaintStyle(),
                    // Store label position and styling
                    labelLocation: this.getLabelLocation(connection),
                    anchors: this.getConnectionAnchors(connection)
                }
            };

            transitions.push(transition);
        });

        return transitions;
    }

    /**
     * Serialize canvas and viewport properties
     * @returns {Object} - Canvas properties
     */
    serializeCanvasProperties() {
        const canvas = document.getElementById('fsa-canvas');

        return {
            dimensions: {
                width: canvas.offsetWidth,
                height: canvas.offsetHeight
            },
            viewport: {
                scrollLeft: canvas.scrollLeft || 0,
                scrollTop: canvas.scrollTop || 0
            },
            zoom: 1.0, // For future zoom functionality
            backgroundColor: window.getComputedStyle(canvas).backgroundColor || '#ffffff'
        };
    }

    /**
     * Get the connector type for a connection
     * @param {Object} connection - JSPlumb connection
     * @returns {string} - Connector type
     */
    getConnectorType(connection) {
        if (connection.connector) {
            return connection.connector.type || 'Straight';
        }
        return 'Straight';
    }

    /**
     * Get curve style for a connection
     * @param {Object} connection - JSPlumb connection
     * @returns {boolean} - Whether the connection is curved
     */
    getConnectionCurveStyle(connection) {
        // Check if it's a self-loop (always curved)
        if (connection.sourceId === connection.targetId) {
            return true;
        }

        // Check connector type
        const connectorType = this.getConnectorType(connection);
        return connectorType !== 'Straight';
    }

    /**
     * Get label location for a connection
     * @param {Object} connection - JSPlumb connection
     * @returns {number} - Label location (0-1)
     */
    getLabelLocation(connection) {
        const labelOverlay = connection.getOverlay('label');
        return labelOverlay ? (labelOverlay.location || 0.3) : 0.3;
    }

    /**
     * Get connection anchors
     * @param {Object} connection - JSPlumb connection
     * @returns {Array} - Array of anchor specifications
     */
    getConnectionAnchors(connection) {
        return connection.endpoints ?
            connection.endpoints.map(ep => ep.anchor ? ep.anchor.type || 'Continuous' : 'Continuous') :
            ['Continuous', 'Continuous'];
    }

    /**
     * Deserialize and load an FSA from JSON data
     * @param {Object} data - Serialized FSA data
     * @param {Object} jsPlumbInstance - The JSPlumb instance
     * @returns {Promise<boolean>} - Whether loading was successful
     */
    async deserializeFSA(data, jsPlumbInstance) {
        try {
            // Validate the data structure
            if (!this.validateSerializedData(data)) {
                throw new Error('Invalid FSA file format');
            }

            // Clear current FSA
            await this.clearCurrentFSA(jsPlumbInstance);

            // Load states first
            await this.deserializeStates(data.states, jsPlumbInstance);

            // Then load transitions
            await this.deserializeTransitions(data.transitions, jsPlumbInstance);

            // Set starting state
            if (data.startingState) {
                createStartingStateIndicator(jsPlumbInstance, data.startingState);
            }

            // Restore canvas properties if available
            if (data.canvasProperties) {
                this.restoreCanvasProperties(data.canvasProperties);
            }

            // Update displays
            updateAlphabetDisplay(getEdgeSymbolMap(), getEpsilonTransitionMap());
            updateFSAPropertiesDisplay(jsPlumbInstance);

            // Repaint everything
            jsPlumbInstance.repaintEverything();

            console.log('FSA loaded successfully');
            return true;

        } catch (error) {
            console.error('Error deserializing FSA:', error);
            notificationManager.showError(
                'Load Failed',
                `Failed to load FSA: ${error.message}`
            );
            return false;
        }
    }

    /**
     * Validate serialized data structure
     * @param {Object} data - Data to validate
     * @returns {boolean} - Whether data is valid
     */
    validateSerializedData(data) {
        if (!data || typeof data !== 'object') {
            return false;
        }

        // Check required properties
        const requiredProps = ['states', 'transitions'];
        for (const prop of requiredProps) {
            if (!Array.isArray(data[prop])) {
                console.error(`Missing or invalid property: ${prop}`);
                return false;
            }
        }

        // Validate states
        for (const state of data.states) {
            if (!state.id || !state.position ||
                typeof state.position.x !== 'number' ||
                typeof state.position.y !== 'number') {
                console.error('Invalid state data:', state);
                return false;
            }
        }

        // Validate transitions
        for (const transition of data.transitions) {
            if (!transition.sourceId || !transition.targetId ||
                !Array.isArray(transition.symbols)) {
                console.error('Invalid transition data:', transition);
                return false;
            }
        }

        return true;
    }

    /**
     * Clear the current FSA completely
     * @param {Object} jsPlumbInstance - The JSPlumb instance
     */
    async clearCurrentFSA(jsPlumbInstance) {
        // Remove all connections
        jsPlumbInstance.deleteEveryConnection();

        // Remove all endpoints
        jsPlumbInstance.deleteEveryEndpoint();

        // Remove all state elements
        const stateElements = document.querySelectorAll('.state, .accepting-state');
        stateElements.forEach(state => state.remove());

        // Remove starting state indicator
        const startSource = document.getElementById('start-source');
        if (startSource) {
            startSource.remove();
        }

        // Clear maps
        getEdgeSymbolMap().clear();
        getEpsilonTransitionMap().clear();

        // Reset starting state
        createStartingStateIndicator(jsPlumbInstance, null);

        console.log('Current FSA cleared');
    }

    /**
     * Deserialize and create states
     * @param {Array} statesData - Array of state data
     * @param {Object} jsPlumbInstance - The JSPlumb instance
     */
    async deserializeStates(statesData, jsPlumbInstance) {
        const callbacks = {
            onStateClick: window.handleStateClick || (() => {}),
            onStateDrag: window.handleStateDrag || (() => {})
        };

        for (const stateData of statesData) {
            // Create state element
            const state = document.createElement('div');
            state.id = stateData.id;
            state.className = stateData.isAccepting ? 'accepting-state' : 'state';
            state.innerHTML = stateData.label || stateData.id;

            // Position the state
            state.style.left = `${stateData.position.x}px`;
            state.style.top = `${stateData.position.y}px`;

            // Add any additional visual properties
            if (stateData.visual && stateData.visual.zIndex) {
                state.style.zIndex = stateData.visual.zIndex;
            }

            // Add to canvas
            document.getElementById('fsa-canvas').appendChild(state);

            // Make state draggable
            $(state).draggable({
                containment: "parent",
                stack: ".state, .accepting-state",
                zIndex: 100,
                drag: function(event, ui) {
                    jsPlumbInstance.repaintEverything();

                    // Keep the start arrow glued to the starting state while it’s dragged
                    if (getStartingStateId() === this.id) {
                        const startSource = document.getElementById('start-source');
                        if (startSource) {
                            startSource.style.left = (ui.position.left - 50) + 'px';
                            startSource.style.top  = (ui.position.top  + 25) + 'px'; // 25 = centre-offset of 30 px circle – 5 px tweak
                            jsPlumbInstance.revalidate('start-source');              // optional but makes it extra-snappy
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
        }
    }

    /**
     * Deserialize and create transitions
     * @param {Array} transitionsData - Array of transition data
     * @param {Object} jsPlumbInstance - The JSPlumb instance
     */
    async deserializeTransitions(transitionsData, jsPlumbInstance) {
        for (const transitionData of transitionsData) {
            try {
                // Determine connector type
                let connectorType = 'Straight';
                if (transitionData.visual) {
                    if (transitionData.visual.isCurved ||
                        transitionData.sourceId === transitionData.targetId) {
                        connectorType = transitionData.sourceId === transitionData.targetId ?
                            ["Bezier", { curviness: 60 }] :
                            ["StateMachine", { curviness: 100 }];
                    }
                }

                // Determine anchors
                const anchors = transitionData.sourceId === transitionData.targetId ?
                    ["Top", "Left"] :
                    (transitionData.visual && transitionData.visual.anchors ?
                        transitionData.visual.anchors :
                        ["Continuous", "Continuous"]);

                // Create the connection
                const connection = jsPlumbInstance.connect({
                    source: transitionData.sourceId,
                    target: transitionData.targetId,
                    connector: connectorType,
                    anchors: anchors,
                    paintStyle: transitionData.visual && transitionData.visual.paintStyle ?
                        transitionData.visual.paintStyle :
                        { stroke: "black", strokeWidth: 2 },
                    hoverPaintStyle: { stroke: "#1e8151", strokeWidth: 3 },
                    overlays: [
                        ["Arrow", { location: 1, id: "arrow", width: 10, length: 10 }],
                        ["Label", {
                            id: "label",
                            cssClass: "edge-label",
                            location: transitionData.visual && transitionData.visual.labelLocation ?
                                transitionData.visual.labelLocation : 0.3,
                            labelStyle: {
                                cssClass: "edge-label-style"
                            }
                        }]
                    ]
                });

                if (connection) {
                    // Store symbols and epsilon data
                    getEdgeSymbolMap().set(connection.id, transitionData.symbols || []);
                    getEpsilonTransitionMap().set(connection.id, transitionData.hasEpsilon || false);

                    // Update label
                    this.updateConnectionLabel(connection,
                        transitionData.symbols || [],
                        transitionData.hasEpsilon || false);

                    // Add epsilon class if needed
                    if (transitionData.hasEpsilon && connection.canvas) {
                        connection.canvas.classList.add('has-epsilon');
                    }

                    // Add click handlers
                    this.setupConnectionHandlers(connection, jsPlumbInstance);
                }

            } catch (error) {
                console.error('Error creating transition:', error, transitionData);
            }
        }
    }

    /**
     * Update connection label with symbols and epsilon
     * @param {Object} connection - JSPlumb connection
     * @param {Array} symbols - Array of symbols
     * @param {boolean} hasEpsilon - Whether transition has epsilon
     */
    updateConnectionLabel(connection, symbols, hasEpsilon) {
        let label = symbols.join(',');

        if (hasEpsilon) {
            const epsilon = 'ε';
            if (label.length > 0) {
                label = epsilon + ',' + label;
            } else {
                label = epsilon;
            }
        }

        const labelOverlay = connection.getOverlay("label");
        if (labelOverlay) {
            labelOverlay.setLabel(label);
        }
    }

    /**
     * Setup event handlers for a connection
     * @param {Object} connection - JSPlumb connection
     * @param {Object} jsPlumbInstance - JSPlumb instance
     */
    setupConnectionHandlers(connection, jsPlumbInstance) {
        // Add click handler to the connection
        if (connection.canvas) {
            $(connection.canvas).on('click', function(e) {
                e.stopPropagation();
                e.preventDefault();

                // Get current tool if available
                const currentTool = window.getCurrentTool ? window.getCurrentTool() : null;
                if (currentTool === 'delete') {
                    // Delete edge function
                    if (window.deleteEdge) {
                        window.deleteEdge(jsPlumbInstance, connection);
                    }
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
                    if (window.deleteEdge) {
                        window.deleteEdge(jsPlumbInstance, connection);
                    }
                } else if (window.openInlineEdgeEditor) {
                    window.openInlineEdgeEditor(connection, jsPlumbInstance);
                }
            });
        }
    }

    /**
     * Restore canvas properties
     * @param {Object} canvasProps - Canvas properties
     */
    restoreCanvasProperties(canvasProps) {
        const canvas = document.getElementById('fsa-canvas');
        if (!canvas || !canvasProps) return;

        // Restore scroll position
        if (canvasProps.viewport) {
            canvas.scrollLeft = canvasProps.viewport.scrollLeft || 0;
            canvas.scrollTop = canvasProps.viewport.scrollTop || 0;
        }

        // Additional canvas restoration could go here
        console.log('Canvas properties restored');
    }

    /**
     * Export FSA to JSON file
     * @param {Object} jsPlumbInstance - The JSPlumb instance
     * @param {string} filename - Optional filename
     */
    exportToFile(jsPlumbInstance, filename = null) {
        try {
            const fsaData = this.serializeFSA(jsPlumbInstance);

            // Add metadata
            fsaData.metadata.name = filename || `FSA_${new Date().toISOString().split('T')[0]}`;

            const jsonString = JSON.stringify(fsaData, null, 2);
            const blob = new Blob([jsonString], { type: 'application/json' });

            // Create download link
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `${fsaData.metadata.name}.json`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);

            notificationManager.showSuccess(
                'Export Successful',
                `FSA exported as "${a.download}"`
            );

            return true;

        } catch (error) {
            console.error('Export failed:', error);
            notificationManager.showError(
                'Export Failed',
                `Failed to export FSA: ${error.message}`
            );
            return false;
        }
    }

    /**
     * Import FSA from file
     * @param {File} file - The file to import
     * @param {Object} jsPlumbInstance - The JSPlumb instance
     * @returns {Promise<boolean>} - Whether import was successful
     */
    async importFromFile(file, jsPlumbInstance) {
        return new Promise((resolve) => {
            const reader = new FileReader();

            reader.onload = async (e) => {
                try {
                    const jsonData = JSON.parse(e.target.result);
                    const success = await this.deserializeFSA(jsonData, jsPlumbInstance);

                    if (success) {
                        notificationManager.showSuccess(
                            'Import Successful',
                            `FSA loaded from "${file.name}"`
                        );
                    }

                    resolve(success);

                } catch (error) {
                    console.error('Import failed:', error);
                    notificationManager.showError(
                        'Import Failed',
                        `Failed to parse file: ${error.message}`
                    );
                    resolve(false);
                }
            };

            reader.onerror = () => {
                notificationManager.showError(
                    'File Read Error',
                    'Failed to read the selected file'
                );
                resolve(false);
            };

            reader.readAsText(file);
        });
    }

    /**
     * Create a quick save of the current FSA
     * @param {Object} jsPlumbInstance - The JSPlumb instance
     * @returns {string} - JSON string of the FSA
     */
    quickSave(jsPlumbInstance) {
        try {
            const fsaData = this.serializeFSA(jsPlumbInstance);
            return JSON.stringify(fsaData);
        } catch (error) {
            console.error('Quick save failed:', error);
            return null;
        }
    }

    /**
     * Load from a quick save string
     * @param {string} jsonString - JSON string of saved FSA
     * @param {Object} jsPlumbInstance - The JSPlumb instance
     * @returns {Promise<boolean>} - Whether load was successful
     */
    async quickLoad(jsonString, jsPlumbInstance) {
        try {
            const fsaData = JSON.parse(jsonString);
            return await this.deserializeFSA(fsaData, jsPlumbInstance);
        } catch (error) {
            console.error('Quick load failed:', error);
            return false;
        }
    }
}

// Create and export singleton instance
export const fsaSerializationManager = new FSASerializationManager();

// Export class for potential multiple instances
export { FSASerializationManager };