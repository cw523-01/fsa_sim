import { getConnectionBetween } from './utils.js';
import { updateAlphabetDisplay } from './alphabetManager.js';
import {
    createState,
    deleteState,
    createStartingStateIndicator,
    getStartingStateId
} from './stateManager.js';
import {
    createConnection,
    deleteEdge,
    getEdgeSymbols,
    getEdgeSymbolMap,
    getEpsilonTransitionMap,
    hasEpsilonTransition
} from './edgeManager.js';
import {
    selectTool,
    resetToolSelection,
    getCurrentTool,
    openInlineStateEditor,
    closeInlineStateEditor,
    openInlineEdgeEditor,
    closeInlineEdgeEditor,
    openEdgeSymbolModal,
    closeEdgeSymbolModal,
    getCurrentEditingState,
    getCurrentEditingEdge,
    getSourceState,
    setSourceState,
    getSourceId,
    resetSourceState
} from './uiManager.js';

// Global variables
let jsPlumbInstance;

/**
 * Initialize the FSA simulator
 */
export function initializeSimulator() {
    // Initialize JSPlumb
    jsPlumbInstance = jsPlumb.getInstance({
        Endpoint: ["Dot", { radius: 2 }],
        Connector: "Straight",
        HoverPaintStyle: { stroke: "#1e8151", strokeWidth: 2 },
        ConnectionOverlays: [
            ["Arrow", { location: 1, id: "arrow", width: 10, length: 10 }],
            ["Label", {
                id: "label",
                cssClass: "edge-label",
                location: 0.3,
                labelStyle: {
                    cssClass: "edge-label-style"
                }
            }]
        ],
        Container: "fsa-canvas"
    });

    // Initial alphabet display
    updateAlphabetDisplay(getEdgeSymbolMap(), getEpsilonTransitionMap());

    // Setup JSPlumb connection event binding
    setupConnectionEvents();
}

/**
 * Setup all event listeners
 */
export function setupEventListeners() {
    // Tool selection
    document.getElementById('state-tool').addEventListener('click', function() {
        closeInlineStateEditor();
        closeInlineEdgeEditor();
        selectTool('state');
    });

    document.getElementById('accepting-state-tool').addEventListener('click', function() {
        closeInlineStateEditor();
        closeInlineEdgeEditor();
        selectTool('accepting-state');
    });

    document.getElementById('edge-tool').addEventListener('click', function() {
        closeInlineStateEditor();
        closeInlineEdgeEditor();
        selectTool('edge');
    });

    document.getElementById('delete-tool').addEventListener('click', function() {
        closeInlineStateEditor();
        closeInlineEdgeEditor();
        selectTool('delete');
    });

    // Canvas click event
    document.getElementById('fsa-canvas').addEventListener('click', function(e) {
        if (e.target.id === 'fsa-canvas') {
            const currentTool = getCurrentTool();
            if (currentTool === 'state') {
                handleStateCreation(e.offsetX, e.offsetY, false);
            } else if (currentTool === 'accepting-state') {
                handleStateCreation(e.offsetX, e.offsetY, true);
            }

            // Close the inline editors if they're open and we click on the canvas
            closeInlineStateEditor();
            closeInlineEdgeEditor();
        }
    });

    // Handle edge label deletion clicks
    document.addEventListener('click', function(e) {
        if (getCurrentTool() === 'delete') {
            // Check if we clicked on an edge label
            const connections = jsPlumbInstance.getAllConnections();
            for (let i = 0; i < connections.length; i++) {
                const conn = connections[i];

                // Skip if this is the starting state connection
                if (conn.canvas && conn.canvas.classList.contains('starting-connection')) {
                    continue;
                }

                const labelOverlay = conn.getOverlay("label");

                if (labelOverlay && labelOverlay.canvas &&
                   (labelOverlay.canvas === e.target || labelOverlay.canvas.contains(e.target))) {
                    deleteEdge(jsPlumbInstance, conn);
                    e.stopPropagation();
                    return;
                }
            }
        }
    });

    // Modal and inline editor close buttons
    document.getElementById('close-inline-editor').addEventListener('click', closeInlineStateEditor);
    document.getElementById('close-edge-editor').addEventListener('click', closeInlineEdgeEditor);
    document.getElementById('cancel-symbol-btn').addEventListener('click', closeEdgeSymbolModal);

    // Non-functional buttons (placeholders)
    setupPlaceholderButtons();

    // Make tools draggable
    setupDraggableTools();

    // Window resize event
    window.addEventListener('resize', function() {
        jsPlumbInstance.repaintEverything();
    });
}

/**
 * Setup JSPlumb connection events
 */
function setupConnectionEvents() {
    // Handle connection events
    jsPlumbInstance.bind('connection', function(info) {
        // Skip processing for starting state connections
        if (info.connection && info.connection.source && info.connection.source.id === 'start-source') {
            // Ensure no label for starting connections
            if (info.connection.getOverlay('label')) {
                info.connection.removeOverlay('label');
            }

            // Add the special class
            if (info.connection.canvas) {
                info.connection.canvas.classList.add('starting-connection');
            }
            return;
        }

        // Make sure we're getting the actual connection element
        if (info.connection && info.connection.canvas) {
            // Add z-index to make sure connection is clickable
            info.connection.canvas.style.zIndex = '20';

            // Add a more robust click handler
            $(info.connection.canvas).on('click', function(e) {
                e.stopPropagation();
                e.preventDefault();

                // Skip if this is the starting state connection
                if (info.connection.canvas.classList.contains('starting-connection')) {
                    return;
                }

                const currentTool = getCurrentTool();
                if (currentTool === 'delete') {
                    deleteEdge(jsPlumbInstance, info.connection);
                } else {
                    openInlineEdgeEditor(info.connection, jsPlumbInstance);
                }
            });
        }

        // Add a separate event handler for the label overlay
        const labelOverlay = info.connection.getOverlay('label');
        if (labelOverlay && labelOverlay.canvas) {
            // Make sure the label is clickable
            labelOverlay.canvas.style.zIndex = '25';

            $(labelOverlay.canvas).on('click', function(e) {
                e.stopPropagation();
                e.preventDefault();

                // Skip if this is the starting state connection
                if (info.connection.canvas.classList.contains('starting-connection')) {
                    return;
                }

                const currentTool = getCurrentTool();
                if (currentTool === 'delete') {
                    deleteEdge(jsPlumbInstance, info.connection);
                } else {
                    openInlineEdgeEditor(info.connection, jsPlumbInstance);
                }
            });
        }
    });
}

/**
 * Handle state creation based on position and type
 * @param {number} x - X position
 * @param {number} y - Y position
 * @param {boolean} isAccepting - Whether it's an accepting state
 */
function handleStateCreation(x, y, isAccepting) {
    const callbacks = {
        onStateClick: handleStateClick,
        onStateDrag: handleStateDrag
    };
    createState(jsPlumbInstance, x, y, isAccepting, callbacks);
}

/**
 * Handle click events on states
 * @param {HTMLElement} stateElement - The clicked state
 * @param {Event} e - The click event
 */
function handleStateClick(stateElement, e) {
    const currentTool = getCurrentTool();

    if (currentTool === 'delete'){
        if (stateElement.classList.contains('state') || stateElement.classList.contains('accepting-state')) {
            deleteState(jsPlumbInstance, stateElement, getEdgeSymbolMap());
        }
    }
    else if (currentTool === 'edge') {
        if (!getSourceState()) {
            setSourceState(stateElement);
        } else {
            const existingConnection = getConnectionBetween(jsPlumbInstance, getSourceId(), stateElement.id);
            if (existingConnection) {
                openInlineEdgeEditor(existingConnection, jsPlumbInstance);
            } else {
                openEdgeSymbolModal(getSourceId(), stateElement.id, (source, target, symbolsString, hasEpsilon) => {
                    createConnection(jsPlumbInstance, source, target, symbolsString, hasEpsilon, {
                        onEdgeClick: handleEdgeClick
                    });
                });
            }
            resetSourceState();
        }
    } else {
        resetToolSelection();
        // If not using edge tool, open edit modal when clicking a state
        openInlineStateEditor(stateElement, jsPlumbInstance);
    }
}

/**
 * Handle drag events on states
 * @param {HTMLElement} stateElement - The dragged state
 * @param {Event} event - The drag event
 * @param {Object} ui - The drag UI object
 */
function handleStateDrag(stateElement, event, ui) {
    // Close inline editors if open while dragging
    if (getCurrentEditingState() === stateElement) {
        closeInlineStateEditor();
    }
    if (getCurrentEditingEdge()) {
        closeInlineEdgeEditor();
    }
}

/**
 * Handle click events on edges
 * @param {Object} connection - The clicked connection
 * @param {Event} e - The click event
 */
function handleEdgeClick(connection, e) {
    const currentTool = getCurrentTool();
    if (currentTool === 'delete') {
        deleteEdge(jsPlumbInstance, connection);
    } else {
        openInlineEdgeEditor(connection, jsPlumbInstance);
    }
}

/**
 * Setup placeholder buttons that are not yet implemented
 */
function setupPlaceholderButtons() {
    document.getElementById('play-btn').addEventListener('click', function() {
        alert('Play functionality is not implemented yet.');
    });

    document.getElementById('stop-btn').addEventListener('click', function() {
        alert('Stop functionality is not implemented yet.');
    });

    document.getElementById('fast-forward-btn').addEventListener('click', function() {
        alert('Fast forward functionality is not implemented yet.');
    });

    document.getElementById('show-table-btn').addEventListener('click', function() {
        alert('Transition table functionality is not implemented yet.');
    });
}

/**
 * Setup draggable tools
 */
function setupDraggableTools() {
    $('.tool').draggable({
        helper: 'clone',
        cursor: 'move',
        cursorAt: { left: 25, top: 25 },
        helper: function() {
            // Create a custom helper with high z-index
            const clone = $(this).clone();
            clone.css('z-index', '1000'); // High z-index to stay on top
            return clone;
        },
        stop: function(event, ui) {
            const tool = $(this).attr('id');
            const canvas = document.getElementById('fsa-canvas');
            const canvasRect = canvas.getBoundingClientRect();

            // Check if dropped on canvas
            if (
                ui.offset.left >= canvasRect.left &&
                ui.offset.left <= canvasRect.right &&
                ui.offset.top >= canvasRect.top &&
                ui.offset.top <= canvasRect.bottom
            ) {
                const x = ui.offset.left - canvasRect.left;
                const y = ui.offset.top - canvasRect.top;

                if (tool === 'state-tool') {
                    handleStateCreation(x, y, false);
                    selectTool('state');
                } else if (tool === 'accepting-state-tool') {
                    handleStateCreation(x, y, true);
                    selectTool('accepting-state');
                }
            }
        }
    });
}