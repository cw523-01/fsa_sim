import { updateFSADisplays } from './fsaUpdateUtils.js';
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
    hasEpsilonTransition,
    setAllEdgeStyles
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
    resetSourceState,
    deselectEdgeStyleButtons
} from './uiManager.js';
import { showTransitionTable, generateTransitionTable } from './transitionTableManager.js';
import { updateFSAPropertiesDisplay, isDeterministic } from './fsaPropertyChecker.js';
import { controlLockManager } from './controlLockManager.js';
import {
    runFSASimulation,
    runFSASimulationFastForward,
    getInputString,
    validateInputString,
    convertFSAToBackendFormat,
    stopVisualSimulation,
    isVisualSimulationRunning
} from './backendIntegration.js';
import { nfaResultsManager } from './nfaResultsManager.js';
import { fsaSerializationManager } from './fsaSerializationManager.js';
import { fsaFileUIManager } from './fsaFileUI.js';
import { fsaTransformManager } from './transformManager.js';
import { regexConversionManager } from './regexConversionManager.js';
import { edgeCreationManager } from './edgeCreationManager.js';
import { toolManager } from './toolManager.js';
import { undoRedoManager } from './undoRedoManager.js';
import { propertyInfoManager } from './propertyInfoManager.js';
import { menuManager } from './menuManager.js';
import { calculateStatePositions, findNonOverlappingPositions } from './positioningUtils.js';

import { tutorialModalManager } from './tutorialModalManager.js';

import { equivalenceManager } from './equivalenceManager.js';

// Make managers globally available
window.nfaResultsManager = nfaResultsManager;
window.toolManager = toolManager;
window.isStateDragging = false; // Make dragging state available globally

// Global variables
let jsPlumbInstance;

/**
 * Returns a connection between two states if it exists
 * @param {Object} jsPlumbInstance - The JSPlumb instance
 * @param {string} sourceId - Source state ID
 * @param {string} targetId - Target state ID
 * @returns {Object|null} - The connection object or null
 */
function getConnectionBetween(jsPlumbInstance, sourceId, targetId) {
    const allConnections = jsPlumbInstance.getAllConnections();
    return allConnections.find(conn =>
        conn.sourceId === sourceId && conn.targetId === targetId
    );
}

/**
 * Initialise the FSA simulator
 */
export function initialiseSimulator() {
    // Initialise JSPlumb
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

    // Initialise the control lock manager with the JSPlumb instance
    controlLockManager.initialise(jsPlumbInstance);

    // Initialise edge creation manager
    initialiseEdgeCreationManager();

    // Initialise tool manager
    initialiseToolManager();

    // Initialise undo/redo system FIRST (before any menu setup)
    initialiseUndoRedoSystem();

    // Initialise FSA serialization system with unified menu bar
    initialiseFSASerialization();

    // Initialise FSA transformation system
    initialiseFSATransformation();

    // Initialise REGEX conversion system
    initialiseRegexConversion();

    // Initialise property info manager
    initialisePropertyInfoManager();

    // Initialise equivalence checking system
    initialiseEquivalenceChecking();


    // Initial displays update using centralised function
    updateFSADisplays(jsPlumbInstance);

    // Setup JSPlumb connection event binding
    setupConnectionEvents();

    // Make sure the correct button is highlighted (Straight is default)
    document.getElementById('straight-edges-btn').classList.add('active');
    document.getElementById('curved-edges-btn').classList.remove('active');
}

/**
 * Initialise edge creation manager
 */
function initialiseEdgeCreationManager() {
    const canvas = document.getElementById('fsa-canvas');
    if (canvas && edgeCreationManager) {
        edgeCreationManager.initialise(canvas);
    }
}

/**
 * Initialise tool manager
 */
function initialiseToolManager() {
    const canvas = document.getElementById('fsa-canvas');
    if (canvas && toolManager) {
        toolManager.initialise(canvas, edgeCreationManager, jsPlumbInstance);
    }
}

/**
 * Initialise FSA transformation system
 */
function initialiseFSATransformation() {
    // Initialise transform manager with JSPlumb instance
    fsaTransformManager.initialise(jsPlumbInstance);

    // Make transform functions globally available
    window.fsaTransformManager = fsaTransformManager;
}

/**
 * Initialise REGEX conversion system
 */
function initialiseRegexConversion() {
    // Initialise REGEX conversion manager with JSPlumb instance
    regexConversionManager.initialise(jsPlumbInstance);

    // Make REGEX conversion functions globally available
    window.regexConversionManager = regexConversionManager;
}

/**
 * Initialise property info manager
 */
function initialisePropertyInfoManager() {
    // Initialise property info manager
    propertyInfoManager.initialise();

    // Make property info manager globally available
    window.propertyInfoManager = propertyInfoManager;

    console.log('Property info system initialised');
}

/**
 * Initialise equivalence checking system
 */
function initialiseEquivalenceChecking() {
    // Initialise equivalence manager with JSPlumb instance
    equivalenceManager.initialise(jsPlumbInstance);

    // Make equivalence checking functions globally available
    window.equivalenceManager = equivalenceManager;
}

/**
 * Initialise undo/redo system
 */
function initialiseUndoRedoSystem() {
    // Initialise undo/redo manager with JSPlumb instance
    undoRedoManager.initialise(jsPlumbInstance);

    // Make undo/redo functions globally available
    window.undoRedoManager = undoRedoManager;

    console.log('Undo/Redo system initialised');
}

/**
 * Initialise FSA serialization system with unified menu bar
 */
function initialiseFSASerialization() {
    // Initialise menu manager first
    menuManager.initialise();

    // Initialise file UI manager with JSPlumb instance
    fsaFileUIManager.initialise(jsPlumbInstance);

    // Setup edit menu with universal menu manager
    setupEditMenu();

    // Setup drag and drop for file import (minimal visual feedback)
    setupFileDragAndDrop();

    // Integrate with control lock manager
    integrateWithControlLockManager();

    // Make serialisation and conversion functions globally available
    window.fsaSerializationManager = fsaSerializationManager;
    window.fsaFileUIManager = fsaFileUIManager;
    window.menuManager = menuManager;

}

/**
 * Setup edit menu with universal menu manager
 */
function setupEditMenu() {
    // Register edit menu with the universal menu manager
    menuManager.registerMenu('edit', {
        buttonId: 'edit-menu-button',
        dropdownId: 'edit-dropdown'
    });

    // Setup edit menu items
    setupEditMenuItems();

    console.log('Edit menu registered with universal menu manager');
}

/**
 * Setup edit menu items (undo/redo)
 */
function setupEditMenuItems() {
    const menuUndo = document.getElementById('menu-undo');
    const menuRedo = document.getElementById('menu-redo');
}

/**
 * Setup drag and drop functionality for file import
 */
function setupFileDragAndDrop() {
    const canvas = document.getElementById('fsa-canvas');
    if (!canvas) return;

    // Create drop overlay
    const dropOverlay = document.createElement('div');
    dropOverlay.className = 'fsa-drop-overlay';
    dropOverlay.innerHTML = '<div class="drop-message">Drop FSA JSON file here to import</div>';
    canvas.appendChild(dropOverlay);

    // Prevent default drag behaviors
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        canvas.addEventListener(eventName, preventDefaults, false);
        document.body.addEventListener(eventName, preventDefaults, false);
    });

    // Highlight drop area when item is dragged over it
    ['dragenter', 'dragover'].forEach(eventName => {
        canvas.addEventListener(eventName, highlight, false);
    });

    ['dragleave', 'drop'].forEach(eventName => {
        canvas.addEventListener(eventName, unhighlight, false);
    });

    // Handle dropped files
    canvas.addEventListener('drop', handleDrop, false);

    function preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }

    function highlight(e) {
        if (controlLockManager.isControlsLocked()) return;

        // Only show overlay for JSON files
        const items = e.dataTransfer.items;
        let hasJsonFile = false;

        for (let i = 0; i < items.length; i++) {
            if (items[i].type === 'application/json' ||
                (items[i].kind === 'file' && items[i].type === '')) {
                hasJsonFile = true;
                break;
            }
        }

        if (hasJsonFile) {
            dropOverlay.classList.add('active');
        }
    }

    function unhighlight(e) {
        dropOverlay.classList.remove('active');
    }

    async function handleDrop(e) {
        if (controlLockManager.isControlsLocked()) {
            if (window.notificationManager) {
                window.notificationManager.showWarning('Cannot Import', 'Cannot import while simulation is running');
            }
            return;
        }

        const dt = e.dataTransfer;
        const files = dt.files;

        if (files.length > 0) {
            const file = files[0];

            // Validate file type
            if (!file.name.toLowerCase().endsWith('.json')) {
                if (window.notificationManager) {
                    window.notificationManager.showError(
                        'Invalid File Type',
                        'Please drop a JSON file (.json)'
                    );
                }
                return;
            }

            // Check if current FSA exists and warn user
            const states = document.querySelectorAll('.state, .accepting-state');
            if (states.length > 0) {
                if (!confirm('Importing will replace the current FSA. Continue?')) {
                    return;
                }
            }

            // Import the file
            try {
                const success = await fsaSerializationManager.importFromFile(file, jsPlumbInstance);

                if (success) {
                    // Clear any existing NFA results since FSA changed
                    if (nfaResultsManager) {
                        nfaResultsManager.clearStoredPaths();
                    }
                }
            } catch (error) {
                console.error('Drop import error:', error);
            }
        }
    }
}

/**
 * Integrate with control lock manager for menu states using universal menu manager
 */
function integrateWithControlLockManager() {
    // Store original lock/unlock methods
    const originalLockControls = controlLockManager.lockControls.bind(controlLockManager);
    const originalUnlockControls = controlLockManager.unlockControls.bind(controlLockManager);

    // Override to also handle menu option states using the universal menu manager
    controlLockManager.lockControls = function() {
        originalLockControls();
        menuManager.updateMenuStates(true);

        if (equivalenceManager) {
            equivalenceManager.updateMenuStates(true);
        }
    };

    controlLockManager.unlockControls = function() {
        originalUnlockControls();
        menuManager.updateMenuStates(false);

        if (equivalenceManager) {
            equivalenceManager.updateMenuStates(false);
        }
    };
}

/**
 * Setup all event listeners
 */
export function setupEventListeners() {
    // Tool selection with tool manager
    document.getElementById('state-tool').addEventListener('click', function() {
        if (controlLockManager.isControlsLocked()) return;
        closeInlineStateEditor();
        closeInlineEdgeEditor();
        selectTool('state');
    });

    document.getElementById('accepting-state-tool').addEventListener('click', function() {
        if (controlLockManager.isControlsLocked()) return;
        closeInlineStateEditor();
        closeInlineEdgeEditor();
        selectTool('accepting-state');
    });

    // Edge tool event listener with tool manager
    document.getElementById('edge-tool').addEventListener('click', function() {
        if (controlLockManager.isControlsLocked()) return;

        closeInlineStateEditor();
        closeInlineEdgeEditor();

        // Use the unified tool manager to handle edge tool selection
        selectTool('edge');
    });

    // Delete tool event listener with tool manager
    document.getElementById('delete-tool').addEventListener('click', function() {
        if (controlLockManager.isControlsLocked()) return;
        closeInlineStateEditor();
        closeInlineEdgeEditor();
        selectTool('delete');
    });

    // Edge style buttons with centralised updates
    document.getElementById('straight-edges-btn').addEventListener('click', function() {
        if (controlLockManager.isControlsLocked()) return;

        const operationType = 'bulk_edge_style_straight';

        // Close any open inline editors or modals and finalise pending commands
        if (window.closeInlineEditorsSafely) {
            window.closeInlineEditorsSafely();
        }
        closeEdgeSymbolModal();

        console.log("Setting all edges to straight");

        // Create snapshot before bulk edge style change for undo/redo
        if (undoRedoManager && !undoRedoManager.isOperationInProgress(operationType)) {
            undoRedoManager.markOperationInProgress(operationType);

            const snapshotCommand = undoRedoManager.createSnapshotCommand('Set all edges to straight');

            // Apply straight edges to all connections
            setAllEdgeStyles(jsPlumbInstance, false);

            // Update button styling
            this.classList.add('active');
            document.getElementById('curved-edges-btn').classList.remove('active');

            if (snapshotCommand) {
                undoRedoManager.finishSnapshotCommand(snapshotCommand);
            }

            undoRedoManager.markOperationComplete(operationType);
        }
    });

    document.getElementById('curved-edges-btn').addEventListener('click', function() {
        if (controlLockManager.isControlsLocked()) return;

        const operationType = 'bulk_edge_style_curved';

        // Close any open inline editors or modals and finalise pending commands
        if (window.closeInlineEditorsSafely) {
            window.closeInlineEditorsSafely();
        }
        closeEdgeSymbolModal();

        console.log("Setting all edges to curved");

        // Create snapshot before bulk edge style change for undo/redo
        if (undoRedoManager && !undoRedoManager.isOperationInProgress(operationType)) {
            undoRedoManager.markOperationInProgress(operationType);

            const snapshotCommand = undoRedoManager.createSnapshotCommand('Set all edges to curved');

            // Apply curved edges to all connections
            setAllEdgeStyles(jsPlumbInstance, true);

            // Update button styling
            this.classList.add('active');
            document.getElementById('straight-edges-btn').classList.remove('active');

            if (snapshotCommand) {
                undoRedoManager.finishSnapshotCommand(snapshotCommand);
            }

            undoRedoManager.markOperationComplete(operationType);
        }
    });

    // Set initial active state for straight edges (default)
    document.getElementById('straight-edges-btn').classList.add('active');

    // Canvas click event
    document.getElementById('fsa-canvas').addEventListener('click', function(e) {
        if (controlLockManager.isControlsLocked()) return;

        // Don't create states if we just finished dragging a state
        if (window.isStateDragging) {
            window.isStateDragging = false; // Reset the flag
            return;
        }

        if (e.target.id === 'fsa-canvas') {
            const currentTool = getCurrentTool();

            // Handle edge creation cancellation
            if (currentTool === 'edge' && edgeCreationManager && edgeCreationManager.isCreatingEdge()) {
                edgeCreationManager.cancelEdgeCreation();
                return; // Don't create states when cancelling edge creation
            }

            // Normal state creation behavior
            if (currentTool === 'state') {
                handleStateCreation(e.offsetX, e.offsetY, false);
            } else if (currentTool === 'accepting-state') {
                handleStateCreation(e.offsetX, e.offsetY, true);
            }

            // Close the inline editors if they're open and we click on the canvas
            // This will also finalise any pending debounced commands
            if (window.closeInlineEditorsSafely) {
                window.closeInlineEditorsSafely();
            }
        }
    });

    // Handle edge label deletion clicks
    document.addEventListener('click', function(e) {
        if (controlLockManager.isControlsLocked()) return;

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

    // Setup functional buttons
    setupFunctionalButtons();

    // Make tools draggable
    setupDraggableTools();

    // Window resize event
    window.addEventListener('resize', function() {
        if (!controlLockManager.isControlsLocked()) {
            // Throttle resize events to avoid excessive repaints
            clearTimeout(this.resizeTimeout);
            this.resizeTimeout = setTimeout(() => {
                jsPlumbInstance.repaintEverything();
            }, 150);
        }
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

            const conn = info.connection;

            // ALWAYS ensure the arrow overlay is present
            if (!conn.getOverlay("arrow")) {
                conn.addOverlay(["Arrow", { location: 1, id: "arrow", width: 10, length: 10 }]);
            }

            // Apply base styles (if not already styled)
            conn.setPaintStyle({ stroke: "black", strokeWidth: 2 });
            conn.setHoverPaintStyle({ stroke: "#1e8151", strokeWidth: 3 });

            // Update properties display
            updateFSAPropertiesDisplay(jsPlumbInstance);
            return;
        }

        // ALWAYS ensure arrow overlay is present for all connections
        if (!info.connection.getOverlay("arrow")) {
            info.connection.addOverlay(["Arrow", { location: 1, id: "arrow", width: 10, length: 10 }]);
        }

        // Make sure we're getting the actual connection element
        if (info.connection && info.connection.canvas) {
            // Add z-index to make sure connection is clickable
            info.connection.canvas.style.zIndex = '20';

            // Add a more robust click handler
            $(info.connection.canvas).on('click', function(e) {
                if (controlLockManager.isControlsLocked()) return;

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
                if (controlLockManager.isControlsLocked()) return;

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

        // Use centralised update function
        updateFSADisplays(jsPlumbInstance);
    });
}

/**
 * Handle state creation based on position and type
 * @param {number} x - X position
 * @param {number} y - Y position
 * @param {boolean} isAccepting - Whether it's an accepting state
 */
function handleStateCreation(x, y, isAccepting) {
    if (controlLockManager.isControlsLocked()) return;

    const operationType = `state_creation_${x}_${y}_${Date.now()}`;

    // Prevent multiple state creations in rapid succession
    if (undoRedoManager && undoRedoManager.isOperationInProgress(operationType)) {
        return;
    }

    const callbacks = {
        onStateClick: handleStateClick,
        onStateDrag: handleStateDrag
    };

    const stateElement = createState(jsPlumbInstance, x, y, isAccepting, callbacks);

    // Record state creation for undo/redo only if successful
    if (stateElement && undoRedoManager) {
        undoRedoManager.recordStateCreation(stateElement.id, x, y, isAccepting);
    }

    // Use centralised update function
    updateFSADisplays(jsPlumbInstance);
}

/**
 * State click handler with edge creation visual feedback
 * @param {HTMLElement} stateElement - The clicked state
 * @param {Event} e - The click event
 */
function handleStateClick(stateElement, e) {
    if (controlLockManager.isControlsLocked()) return;

    const currentTool = getCurrentTool();
    const operationType = `state_click_${stateElement.id}_${currentTool}`;

    if (currentTool === 'delete') {
        if (stateElement.classList.contains('state') || stateElement.classList.contains('accepting-state')) {
            // Create snapshot before deletion for undo/redo
            if (undoRedoManager && !undoRedoManager.isOperationInProgress(operationType)) {
                undoRedoManager.markOperationInProgress(operationType);

                const snapshotCommand = undoRedoManager.createSnapshotCommand(`Delete state ${stateElement.id}`);
                deleteState(jsPlumbInstance, stateElement, getEdgeSymbolMap());

                if (snapshotCommand) {
                    undoRedoManager.finishSnapshotCommand(snapshotCommand);
                }

                undoRedoManager.markOperationComplete(operationType);
            }
        }
    }
    else if (currentTool === 'edge') {
        // Use edge creation manager (no undo needed here - handled in edge creation)
        if (edgeCreationManager && edgeCreationManager.isActive()) {
            if (!edgeCreationManager.isCreatingEdge()) {
                // Start edge creation from this state
                edgeCreationManager.startEdgeCreation(stateElement);
            } else {
                // Complete edge creation to this state
                const sourceState = edgeCreationManager.getSourceState();

                if (sourceState && sourceState !== stateElement) {
                    // Complete the edge creation to a different state
                    edgeCreationManager.completeEdgeCreation(stateElement, (sourceId, targetId) => {
                        handleEdgeCreationCompletion(sourceId, targetId);
                    });
                } else if (sourceState === stateElement) {
                    // Self-loop creation/editing
                    edgeCreationManager.completeEdgeCreation(stateElement, (sourceId, targetId) => {
                        handleSelfLoopCreation(sourceId, targetId);
                    });
                }
            }
        }
    } else {
        resetToolSelection();
        // Close any open editors and finalise pending commands before opening new one
        if (window.closeInlineEditorsSafely) {
            window.closeInlineEditorsSafely();
        }
        openInlineStateEditor(stateElement, jsPlumbInstance);
    }
}

/**
 * Handle edge creation completion with undo tracking
 */
function handleEdgeCreationCompletion(sourceId, targetId) {
    const operationType = `edge_creation_${sourceId}_${targetId}`;

    // Check if connection already exists
    const existingConnection = getConnectionBetween(jsPlumbInstance, sourceId, targetId);
    if (existingConnection) {
        openInlineEdgeEditor(existingConnection, jsPlumbInstance);
        return;
    }

    // Open edge symbol modal for new connection
    openEdgeSymbolModal(sourceId, targetId, (source, target, symbolsString, hasEpsilon, isCurved) => {
        // Create snapshot before edge creation for undo/redo
        if (undoRedoManager && !undoRedoManager.isOperationInProgress(operationType)) {
            undoRedoManager.markOperationInProgress(operationType);

            const snapshotCommand = undoRedoManager.createSnapshotCommand(`Create edge ${source} → ${target}`);

            createConnection(jsPlumbInstance, source, target, symbolsString, hasEpsilon, isCurved, {
                onEdgeClick: handleEdgeClick
            });

            if (isCurved !== undefined) {
                deselectEdgeStyleButtons();
            }

            if (snapshotCommand) {
                undoRedoManager.finishSnapshotCommand(snapshotCommand);
            }

            undoRedoManager.markOperationComplete(operationType);
        }
    });
}

/**
 * Handle self-loop creation with proper undo tracking
 */
function handleSelfLoopCreation(sourceId, targetId) {
    const operationType = `self_loop_${sourceId}`;

    // Check if a self-loop already exists
    const existingConnection = getConnectionBetween(jsPlumbInstance, sourceId, targetId);
    if (existingConnection) {
        // Self-loop exists -> open inline editor instead of creating another
        openInlineEdgeEditor(existingConnection, jsPlumbInstance);
        return;
    }

    // No existing self-loop -> create a new curved one
    openEdgeSymbolModal(sourceId, targetId, (source, target, symbolsString, hasEpsilon) => {
        // Create snapshot before edge creation for undo/redo
        if (undoRedoManager && !undoRedoManager.isOperationInProgress(operationType)) {
            undoRedoManager.markOperationInProgress(operationType);

            const snapshotCommand = undoRedoManager.createSnapshotCommand(`Create self-loop on ${source}`);

            createConnection(jsPlumbInstance, source, target, symbolsString, hasEpsilon, true, {  // Self-loops are always curved
                onEdgeClick: handleEdgeClick
            });

            if (snapshotCommand) {
                undoRedoManager.finishSnapshotCommand(snapshotCommand);
            }

            undoRedoManager.markOperationComplete(operationType);
        }
    });
}

/**
 * Handle drag events on states with
 * @param {HTMLElement} stateElement - The dragged state
 * @param {Event} event - The drag event
 * @param {Object} ui - The drag UI object
 */
function handleStateDrag(stateElement, event, ui) {
    if (controlLockManager.isControlsLocked()) return;

    // Close inline editors if open while dragging
    if (getCurrentEditingState() === stateElement) {
        closeInlineStateEditor();
    }
    if (getCurrentEditingEdge()) {
        closeInlineEdgeEditor();
    }

    // Mark FSA as changed for unsaved changes tracking
    if (window.markFSAAsChanged) {
        window.markFSAAsChanged();
    }
}

/**
 * Handle click events on edges
 * @param {Object} connection - The clicked connection
 * @param {Event} e - The click event
 */
function handleEdgeClick(connection, e) {
    if (controlLockManager.isControlsLocked()) return;

    const currentTool = getCurrentTool();
    const operationType = `edge_click_${connection.sourceId}_${connection.targetId}_${currentTool}`;

    if (currentTool === 'delete') {
        // Create snapshot before edge deletion for undo/redo
        if (undoRedoManager && !undoRedoManager.isOperationInProgress(operationType)) {
            undoRedoManager.markOperationInProgress(operationType);

            const snapshotCommand = undoRedoManager.createSnapshotCommand(
                `Delete edge ${connection.sourceId} → ${connection.targetId}`
            );

            deleteEdge(jsPlumbInstance, connection);

            if (snapshotCommand) {
                undoRedoManager.finishSnapshotCommand(snapshotCommand);
            }

            undoRedoManager.markOperationComplete(operationType);
        }
    } else {
        // Close any open editors and finalise pending commands before opening new one
        if (window.closeInlineEditorsSafely) {
            window.closeInlineEditorsSafely();
        }
        openInlineEdgeEditor(connection, jsPlumbInstance);
    }
}

/**
 * Setup functional buttons
 */
function setupFunctionalButtons() {
    // Play button - locks controls and starts visual simulation
    document.getElementById('play-btn').addEventListener('click', async function() {
        if (controlLockManager.isControlsLocked()) return;

        // Deselect any selected tool
        resetToolSelection();

        console.log('Play button pressed - starting visual simulation');

        // Get input string
        const inputString = getInputString();

        // Check if FSA is deterministic to provide appropriate feedback
        const isDFA = isDeterministic(jsPlumbInstance);

        // Lock controls immediately for all simulation types
        controlLockManager.lockControls();

        try {
            // Quick validation of input string format
            const tableData = generateTransitionTable(jsPlumbInstance);
            if (tableData.alphabet.length > 0) {
                const inputValidation = validateInputString(inputString, tableData.alphabet);
                if (!inputValidation.valid) {
                    // Show error popup instead of alert
                    if (window.showSimulationErrorPopup) {
                        window.showSimulationErrorPopup(`INPUT ERROR!\n\n${inputValidation.message}`, inputString);
                    }
                    controlLockManager.unlockControls();
                    return;
                }
            }

            console.log(`Simulating ${isDFA ? 'DFA' : 'NFA'} with input: "${inputString}"`);

            // Run the simulation with visual animation (default)
            const simulationResult = await runFSASimulation(jsPlumbInstance, inputString, true);

            // Log detailed result for debugging
            if (simulationResult.success && simulationResult.rawResult) {
                console.log('Simulation completed successfully:', simulationResult.rawResult);
            } else if (!simulationResult.success) {
                console.log('Simulation failed:', simulationResult);
            }

            // For DFA visual simulations, don't unlock controls immediately -
            // they'll be unlocked when simulation ends or stop is pressed
            // For NFA simulations, controls remain locked until popup is closed
            // For error cases where popup is shown, unlock controls
            if (!simulationResult.success || (!simulationResult.isVisual && simulationResult.type !== 'nfa_visual_simulation')) {
                controlLockManager.unlockControls();
            }

        } catch (error) {
            console.error('Unexpected error during simulation:', error);
            if (window.showSimulationErrorPopup) {
                window.showSimulationErrorPopup(`UNEXPECTED ERROR!\n\nAn unexpected error occurred during simulation:\n${error.message}`, inputString);
            }
            controlLockManager.unlockControls();
        }
    });

    // Stop button - stops visual simulation and unlocks controls
    document.getElementById('stop-btn').addEventListener('click', function() {
        console.log('Stop button pressed - stopping simulation');

        // Stop any running visual simulation (DFA or NFA)
        stopVisualSimulation();

        // Hide NFA popup if it's open
        if (nfaResultsManager && nfaResultsManager.currentPopup) {
            nfaResultsManager.hideNFAResultsPopup();
        }

        // Unlock controls
        controlLockManager.unlockControls();

        console.log('Simulation stopped and controls unlocked');
    });

    // Fast forward button - runs simulation without animation
    document.getElementById('fast-forward-btn').addEventListener('click', async function() {
        if (controlLockManager.isControlsLocked()) return;

        // Deselect any selected tool
        resetToolSelection();

        console.log('Fast forward button pressed - running simulation without animation');

        // Get input string
        const inputString = getInputString();

        // Check if FSA is deterministic to provide appropriate feedback
        const isDFA = isDeterministic(jsPlumbInstance);

        // Lock controls briefly for fast simulation
        controlLockManager.lockControls();

        try {
            // Quick validation of input string format
            const tableData = generateTransitionTable(jsPlumbInstance);
            if (tableData.alphabet.length > 0) {
                const inputValidation = validateInputString(inputString, tableData.alphabet);
                if (!inputValidation.valid) {
                    // Show error popup instead of alert
                    if (window.showSimulationErrorPopup) {
                        window.showSimulationErrorPopup(`INPUT ERROR!\n\n${inputValidation.message}`, inputString);
                    }
                    controlLockManager.unlockControls();
                    return;
                }
            }

            console.log(`Fast-forward simulating ${isDFA ? 'DFA' : 'NFA'} with input: "${inputString}"`);

            // Run the simulation without visual animation
            const simulationResult = await runFSASimulationFastForward(jsPlumbInstance, inputString);

            // Log detailed result for debugging
            if (simulationResult.success && simulationResult.rawResult) {
                console.log('Fast-forward simulation completed successfully:', simulationResult.rawResult);
            } else if (!simulationResult.success) {
                console.log('Fast-forward simulation failed:', simulationResult);
            }

            // Note: No alert needed anymore as the popup system handles display

        } catch (error) {
            console.error('Unexpected error during fast-forward simulation:', error);
            if (window.showSimulationErrorPopup) {
                window.showSimulationErrorPopup(`UNEXPECTED ERROR!\n\nAn unexpected error occurred during simulation:\n${error.message}`, inputString);
            }
        } finally {
            // Always unlock controls after fast-forward simulation
            controlLockManager.unlockControls();
        }
    });

    // Show table button - implement the show table button functionality
    document.getElementById('show-table-btn').addEventListener('click', function() {
        if (controlLockManager.isControlsLocked()) return;

        showTransitionTable(jsPlumbInstance);
    });
}

/**
 * Setup draggable tools
 */
function setupDraggableTools() {
    $('.tool').draggable({
        cursor: 'move',
        cursorAt: { left: 30, top: 30 },
        helper: function() {
            const clone = $(this).clone();
            clone.css({
                'z-index': '9999',
                'position': 'fixed',
                'pointer-events': 'none'
            });
            return clone;
        },
        appendTo: 'body',
        start: function(event, ui) {
            if (controlLockManager.isControlsLocked()) {
                return false;
            }

            // Disable animations during tool drag for smooth performance
            document.body.classList.add('no-animation');
        },
        stop: function(event, ui) {
            if (controlLockManager.isControlsLocked()) return;

            // KEEP: Re-enable animations after drag
            document.body.classList.remove('no-animation');

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

/**
 * Cleanup function for managers
 */
function cleanupManagers() {
    if (edgeCreationManager) {
        edgeCreationManager.destroy();
        console.log('Edge creation manager cleaned up');
    }

    if (toolManager) {
        toolManager.destroy();
        console.log('Tool manager cleaned up');
    }

    if (propertyInfoManager) {
        propertyInfoManager.destroy();
        console.log('Property info manager cleaned up');
    }

    if (menuManager) {
        menuManager.destroy();
        console.log('Menu manager cleaned up');
    }
}

/**
 * Cleanup function to handle pending operations
 */
function cleanupPendingOperations() {
    if (undoRedoManager) {
        // Finalise all pending debounced commands
        undoRedoManager.finaliseAllDebouncedCommands();

        // Clear any operations marked as in progress
        undoRedoManager.commandInProgress.clear();

        console.log('Cleaned up pending undo/redo operations');
    }
}

// Add cleanup event listener
window.addEventListener('beforeunload', cleanupManagers);

// Make functions available globally for the serialization system
window.handleStateClick = handleStateClick;
window.handleStateDrag = handleStateDrag;

// Add cleanup on window unload
window.addEventListener('beforeunload', cleanupPendingOperations);

// Export functions for use in other modules
export { cleanupPendingOperations, handleEdgeCreationCompletion, handleSelfLoopCreation };