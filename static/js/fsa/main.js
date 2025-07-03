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
    hasEpsilonTransition,
    toggleEdgeStyle, setAllEdgeStyles
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
import { edgeCreationManager } from './edgeCreationManager.js';
import { toolManager } from './toolManager.js';
import { undoRedoManager } from './undoRedoManager.js';
import { propertyInfoManager } from './propertyInfoManager.js';

// Make managers globally available
window.nfaResultsManager = nfaResultsManager;
window.toolManager = toolManager;
window.isStateDragging = false; // Make dragging state available globally

// Global variables
let jsPlumbInstance;

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
    controlLockManager.initialize(jsPlumbInstance);

    // Initialise enhanced edge creation manager
    initialiseEdgeCreationManager();

    // Initialise enhanced tool manager
    initialiseToolManager();

    // Initialise undo/redo system FIRST (before any menu setup)
    initialiseUndoRedoSystem();

    // Initialise FSA serialization system with menu bar
    initializeFSASerialization();

    // Initialise FSA transformation system
    initializeFSATransformation();

    // Initialise property info manager
    initialisePropertyInfoManager();

    // Setup performance monitoring
    setupPerformanceMonitoring();

    // Initial alphabet display
    updateAlphabetDisplay(getEdgeSymbolMap(), getEpsilonTransitionMap());

    // Setup JSPlumb connection event binding
    setupConnectionEvents();

    // Initial properties display update
    updateFSAPropertiesDisplay(jsPlumbInstance);

    // Make sure the correct button is highlighted (Straight is default)
    document.getElementById('straight-edges-btn').classList.add('active');
    document.getElementById('curved-edges-btn').classList.remove('active');
}

/**
 * Setup performance monitoring for drag operations
 */
function setupPerformanceMonitoring() {
    let dragPerformanceWarningShown = false;

    // Monitor for potential performance issues
    const observer = new MutationObserver((mutations) => {
        let hasDragMutations = false;

        mutations.forEach((mutation) => {
            if (mutation.target && mutation.target.classList) {
                if (mutation.target.classList.contains('ui-draggable-dragging') ||
                    mutation.target.classList.contains('state') ||
                    mutation.target.classList.contains('accepting-state')) {
                    hasDragMutations = true;
                }
            }
        });

        // If we detect excessive mutations during drag, log a warning
        if (hasDragMutations && !dragPerformanceWarningShown) {
            console.log('Performance: Drag mutations detected - monitoring for issues');
            dragPerformanceWarningShown = true;
        }
    });

    observer.observe(document.getElementById('fsa-canvas'), {
        attributes: true,
        childList: true,
        subtree: true,
        attributeFilter: ['style', 'class']
    });

    // Monitor frame rate during drag operations
    let lastFrameTime = performance.now();
    let frameCount = 0;
    let dragStartTime = null;

    function monitorFrameRate() {
        const now = performance.now();
        frameCount++;

        // Check if we're currently dragging
        const isDragging = document.querySelector('.ui-draggable-dragging') !== null;

        if (isDragging && !dragStartTime) {
            dragStartTime = now;
            frameCount = 0;
        } else if (!isDragging && dragStartTime) {
            const dragDuration = now - dragStartTime;
            const fps = frameCount / (dragDuration / 1000);

            if (fps < 30) {
                console.warn(`Performance: Low FPS during drag: ${fps.toFixed(1)} fps`);
            } else {
                console.log(`Performance: Drag completed at ${fps.toFixed(1)} fps`);
            }

            dragStartTime = null;
        }

        lastFrameTime = now;
        requestAnimationFrame(monitorFrameRate);
    }

    // Start monitoring
    requestAnimationFrame(monitorFrameRate);
}

/**
 * Initialize enhanced edge creation manager
 */
function initialiseEdgeCreationManager() {
    const canvas = document.getElementById('fsa-canvas');
    if (canvas && edgeCreationManager) {
        edgeCreationManager.initialize(canvas);
        console.log('Enhanced edge creation manager initialized');
    }
}

/**
 * Initialize enhanced tool manager
 */
function initialiseToolManager() {
    const canvas = document.getElementById('fsa-canvas');
    if (canvas && toolManager) {
        toolManager.initialize(canvas, edgeCreationManager, jsPlumbInstance);
        console.log('Enhanced tool manager initialized');
    }
}

/**
 * Initialize FSA transformation system
 */
function initializeFSATransformation() {
    // Initialize transform manager with JSPlumb instance
    fsaTransformManager.initialize(jsPlumbInstance);

    // Make transform functions globally available
    window.fsaTransformManager = fsaTransformManager;

    console.log('FSA transformation system initialized');
}

/**
 * Initialize property info manager
 */
function initialisePropertyInfoManager() {
    // Initialize property info manager
    propertyInfoManager.initialize();

    // Make property info manager globally available
    window.propertyInfoManager = propertyInfoManager;

    console.log('Property info system initialized');
}

/**
 * Initialize undo/redo system
 */
function initialiseUndoRedoSystem() {
    // Initialize undo/redo manager with JSPlumb instance
    undoRedoManager.initialize(jsPlumbInstance);

    // Make undo/redo functions globally available
    window.undoRedoManager = undoRedoManager;

    console.log('Undo/Redo system initialized');
}

/**
 * Initialize FSA serialization system with menu bar
 */
function initializeFSASerialization() {
    // Initialize file UI manager with JSPlumb instance
    fsaFileUIManager.initialize(jsPlumbInstance);

    // Setup simple menu debug for testing (FILE MENU ONLY - undo/redo handled by undoRedoManager)
    setupSimpleMenuDebug();

    // Setup drag and drop for file import (minimal visual feedback)
    setupFileDragAndDrop();

    // Integrate with control lock manager
    integrateWithControlLockManager();

    // Setup unsaved changes warning
    setupUnsavedChangesWarning();

    // Make serialization functions globally available
    window.fsaSerializationManager = fsaSerializationManager;
    window.fsaFileUIManager = fsaFileUIManager;

    // Show auto-save restore prompt if available (delayed to ensure UI is ready)
    setTimeout(() => {
//         fsaFileUIManager.showAutoSavePrompt();
    }, 1000);

    console.log('FSA serialization system with menu bar initialized');
}

/**
 * Simple debug menu setup to ensure dropdown works (FILE MENU ONLY)
 * NOTE: Undo/Redo is handled entirely by undoRedoManager.js
 */
function setupSimpleMenuDebug() {
    console.log('Setting up menu functionality...');

    // File menu button
    const fileMenuButton = document.getElementById('file-menu-button');
    const fileDropdown = document.getElementById('file-dropdown');

    if (!fileMenuButton || !fileDropdown) {
        console.error('Menu elements not found:', {
            button: !!fileMenuButton,
            dropdown: !!fileDropdown
        });
        return;
    }

    // Remove any existing event listeners by cloning the button
    const newFileMenuButton = fileMenuButton.cloneNode(true);
    fileMenuButton.parentNode.replaceChild(newFileMenuButton, fileMenuButton);

    newFileMenuButton.addEventListener('click', function(e) {
        console.log('File menu clicked');
        e.stopPropagation();

        // Toggle dropdown
        const isOpen = fileDropdown.classList.contains('show');

        if (isOpen) {
            fileDropdown.classList.remove('show');
            newFileMenuButton.classList.remove('active');
        } else {
            fileDropdown.classList.add('show');
            newFileMenuButton.classList.add('active');
        }
    });

    // Close menu when clicking outside
    document.addEventListener('click', function(e) {
        if (!e.target.closest('#file-menu')) {
            fileDropdown.classList.remove('show');
            newFileMenuButton.classList.remove('active');
        }
    });

    // Menu option handlers - ensure only one handler per element
    const menuNew = document.getElementById('menu-new');
    const menuOpen = document.getElementById('menu-open');
    const menuSave = document.getElementById('menu-save');

    if (menuNew) {
        // Clone to remove existing handlers
        const newMenuNew = menuNew.cloneNode(true);
        menuNew.parentNode.replaceChild(newMenuNew, menuNew);

        newMenuNew.addEventListener('click', function(e) {
            e.stopPropagation();
            fileDropdown.classList.remove('show');
            newFileMenuButton.classList.remove('active');
            fsaFileUIManager.newFSA();
        });
    }

    if (menuOpen) {
        // Clone to remove existing handlers
        const newMenuOpen = menuOpen.cloneNode(true);
        menuOpen.parentNode.replaceChild(newMenuOpen, menuOpen);

        newMenuOpen.addEventListener('click', function(e) {
            e.stopPropagation();
            fileDropdown.classList.remove('show');
            newFileMenuButton.classList.remove('active');
            fsaFileUIManager.importFSA();
        });
    }

    if (menuSave) {
        // Clone to remove existing handlers
        const newMenuSave = menuSave.cloneNode(true);
        menuSave.parentNode.replaceChild(newMenuSave, menuSave);

        newMenuSave.addEventListener('click', function(e) {
            e.stopPropagation();
            fileDropdown.classList.remove('show');
            newFileMenuButton.classList.remove('active');
            console.log('Save menu clicked - calling exportFSA');
            fsaFileUIManager.exportFSA();
        });
    }

    // Edit menu setup (DROPDOWN ONLY - actual undo/redo handled by undoRedoManager)
    const editMenuButton = document.getElementById('edit-menu-button');
    const editDropdown = document.getElementById('edit-dropdown');

    if (!editMenuButton || !editDropdown) {
        console.error('Edit menu elements not found:', {
            button: !!editMenuButton,
            dropdown: !!editDropdown
        });
    } else {
        // Remove any existing event listeners by cloning the button
        const newEditMenuButton = editMenuButton.cloneNode(true);
        editMenuButton.parentNode.replaceChild(newEditMenuButton, editMenuButton);

        newEditMenuButton.addEventListener('click', function(e) {
            console.log('Edit menu clicked');
            e.stopPropagation();

            // Use the existing fsaFileUIManager method to close other menus
            if (window.fsaFileUIManager) {
                window.fsaFileUIManager.closeAllMenus();
            }

            // Toggle edit dropdown
            const isOpen = editDropdown.classList.contains('show');

            if (isOpen) {
                editDropdown.classList.remove('show');
                newEditMenuButton.classList.remove('active');
            } else {
                editDropdown.classList.add('show');
                newEditMenuButton.classList.add('active');
            }
        });

        // Add edit menu to the global close menu handler
        document.addEventListener('click', function(e) {
            if (!e.target.closest('#edit-menu')) {
                editDropdown.classList.remove('show');
                newEditMenuButton.classList.remove('active');
            }
        });

        // IMPORTANT: Do NOT set up undo/redo click handlers here!
        // They are handled entirely by undoRedoManager.js
        console.log('Edit menu dropdown setup complete - undo/redo handled by undoRedoManager');
    }
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
                    clearNFAStoredResults();
                }
            } catch (error) {
                console.error('Drop import error:', error);
            }
        }
    }
}

/**
 * Integrate with control lock manager for menu states
 */
function integrateWithControlLockManager() {
    // Store original lock/unlock methods
    const originalLockControls = controlLockManager.lockControls.bind(controlLockManager);
    const originalUnlockControls = controlLockManager.unlockControls.bind(controlLockManager);

    // Override to also handle menu option states
    controlLockManager.lockControls = function() {
        originalLockControls();
        fsaFileUIManager.updateMenuStates(true);
        fsaTransformManager.updateMenuStates(true);
    };

    controlLockManager.unlockControls = function() {
        originalUnlockControls();
        fsaFileUIManager.updateMenuStates(false);
        fsaTransformManager.updateMenuStates(false);
    };
}

/**
 * Setup unsaved changes warning
 */
function setupUnsavedChangesWarning() {
    let hasUnsavedChanges = false;

    // Track changes through existing event system
    function markAsChanged() {
        hasUnsavedChanges = true;
    }

    // Reset when saved
    function markAsSaved() {
        hasUnsavedChanges = false;
    }

    // Override export functions to mark as saved
    const originalExportFSA = fsaFileUIManager.exportFSA.bind(fsaFileUIManager);
    fsaFileUIManager.exportFSA = function(...args) {
        const result = originalExportFSA.apply(this, args);
        markAsSaved();
        return result;
    };

    // Warn before leaving page with unsaved changes
    window.addEventListener('beforeunload', (e) => {
        const states = document.querySelectorAll('.state, .accepting-state');
        if (states.length > 0 && hasUnsavedChanges) {
            const message = 'You have unsaved changes. Are you sure you want to leave?';
            e.returnValue = message;
            return message;
        }
    });

    // Make functions available globally
    window.markFSAAsChanged = markAsChanged;
    window.markFSAAsSaved = markAsSaved;

    // Connect to existing change events
    if (jsPlumbInstance) {
        jsPlumbInstance.bind('connection', markAsChanged);
        jsPlumbInstance.bind('connectionDetached', markAsChanged);
    }
}

/**
 * Clear stored NFA results when FSA structure changes
 */
function clearNFAStoredResults() {
    if (window.nfaResultsManager) {
        window.nfaResultsManager.clearStoredPaths();
        console.log('Cleared NFA stored results due to FSA structure change');
    }
}

/**
 * Setup all event listeners
 */
export function setupEventListeners() {
    // Enhanced tool selection with unified tool manager
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

    // Enhanced edge tool event listener with unified tool manager
    document.getElementById('edge-tool').addEventListener('click', function() {
        if (controlLockManager.isControlsLocked()) return;

        closeInlineStateEditor();
        closeInlineEdgeEditor();

        // Use the unified tool manager to handle edge tool selection
        selectTool('edge');
    });

    // Enhanced delete tool event listener with unified tool manager
    document.getElementById('delete-tool').addEventListener('click', function() {
        if (controlLockManager.isControlsLocked()) return;
        closeInlineStateEditor();
        closeInlineEdgeEditor();
        selectTool('delete');
    });

    // Edge style buttons with
    document.getElementById('straight-edges-btn').addEventListener('click', function() {
        if (controlLockManager.isControlsLocked()) return;

        // Close any open inline editors or modals
        closeInlineStateEditor();
        closeInlineEdgeEditor();
        closeEdgeSymbolModal();

        console.log("Setting all edges to straight");

        // Create snapshot before bulk edge style change for undo/redo
        if (undoRedoManager && !undoRedoManager.isProcessing()) {
            const snapshotCommand = undoRedoManager.createSnapshotCommand('Set all edges to straight');

            // Add performance mode during edge style changes
            document.body.classList.add('performance-mode');

            // Apply straight edges to all connections with our improved function
            setAllEdgeStyles(jsPlumbInstance, false);

            // Clear stored NFA results since FSA structure changed
            clearNFAStoredResults();

            // Update FSA properties display
            updateFSAPropertiesDisplay(jsPlumbInstance);

            // Update button styling
            this.classList.add('active');
            document.getElementById('curved-edges-btn').classList.remove('active');

            // Remove performance mode after a brief delay
            setTimeout(() => {
                document.body.classList.remove('performance-mode');
            }, 100);

            undoRedoManager.finishSnapshotCommand(snapshotCommand);
        } else {
            // Fallback without undo/redo
            document.body.classList.add('performance-mode');
            setAllEdgeStyles(jsPlumbInstance, false);
            clearNFAStoredResults();
            updateFSAPropertiesDisplay(jsPlumbInstance);
            this.classList.add('active');
            document.getElementById('curved-edges-btn').classList.remove('active');
            setTimeout(() => {
                document.body.classList.remove('performance-mode');
            }, 100);
        }
    });

    document.getElementById('curved-edges-btn').addEventListener('click', function() {
        if (controlLockManager.isControlsLocked()) return;

        // Close any open inline editors or modals
        closeInlineStateEditor();
        closeInlineEdgeEditor();
        closeEdgeSymbolModal();

        console.log("Setting all edges to curved");

        // Create snapshot before bulk edge style change for undo/redo
        if (undoRedoManager && !undoRedoManager.isProcessing()) {
            const snapshotCommand = undoRedoManager.createSnapshotCommand('Set all edges to curved');

            // Add performance mode during edge style changes
            document.body.classList.add('performance-mode');

            // Apply curved edges to all connections with our improved function
            setAllEdgeStyles(jsPlumbInstance, true);

            // Clear stored NFA results since FSA structure changed
            clearNFAStoredResults();

            // Update FSA properties display
            updateFSAPropertiesDisplay(jsPlumbInstance);

            // Update button styling
            this.classList.add('active');
            document.getElementById('straight-edges-btn').classList.remove('active');

            // Remove performance mode after a brief delay
            setTimeout(() => {
                document.body.classList.remove('performance-mode');
            }, 100);

            undoRedoManager.finishSnapshotCommand(snapshotCommand);
        } else {
            // Fallback without undo/redo
            document.body.classList.add('performance-mode');
            setAllEdgeStyles(jsPlumbInstance, true);
            clearNFAStoredResults();
            updateFSAPropertiesDisplay(jsPlumbInstance);
            this.classList.add('active');
            document.getElementById('straight-edges-btn').classList.remove('active');
            setTimeout(() => {
                document.body.classList.remove('performance-mode');
            }, 100);
        }
    });

    // Set initial active state for straight edges (default)
    document.getElementById('straight-edges-btn').classList.add('active');

    // Enhanced canvas click event
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
            closeInlineStateEditor();
            closeInlineEdgeEditor();
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

        // Clear stored NFA results since FSA structure changed
        clearNFAStoredResults();

        // Update properties display
        updateFSAPropertiesDisplay(jsPlumbInstance);
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

    const callbacks = {
        onStateClick: handleStateClick,
        onStateDrag: handleStateDrag
    };

    const stateElement = createState(jsPlumbInstance, x, y, isAccepting, callbacks);

    // Record state creation for undo/redo
    if (stateElement && undoRedoManager) {
        undoRedoManager.recordStateCreation(stateElement.id, x, y, isAccepting);
    }

    // Clear stored NFA results since FSA structure changed
    clearNFAStoredResults();

    // Update properties display
    updateFSAPropertiesDisplay(jsPlumbInstance);
}

/**
 * Enhanced state click handler with edge creation visual feedback
 * @param {HTMLElement} stateElement - The clicked state
 * @param {Event} e - The click event
 */
function handleStateClick(stateElement, e) {
    if (controlLockManager.isControlsLocked()) return;

    const currentTool = getCurrentTool();

    if (currentTool === 'delete') {
        if (stateElement.classList.contains('state') || stateElement.classList.contains('accepting-state')) {
            // Create snapshot before deletion for undo/redo
            if (undoRedoManager && !undoRedoManager.isProcessing()) {
                const snapshotCommand = undoRedoManager.createSnapshotCommand(`Delete state ${stateElement.id}`);
                deleteState(jsPlumbInstance, stateElement, getEdgeSymbolMap());
                clearNFAStoredResults();
                updateFSAPropertiesDisplay(jsPlumbInstance);
                undoRedoManager.finishSnapshotCommand(snapshotCommand);
            } else {
                deleteState(jsPlumbInstance, stateElement, getEdgeSymbolMap());
                clearNFAStoredResults();
                updateFSAPropertiesDisplay(jsPlumbInstance);
            }
        }
    }
    else if (currentTool === 'edge') {
        // Use enhanced edge creation manager
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
                        // Check if connection already exists
                        const existingConnection = getConnectionBetween(jsPlumbInstance, sourceId, targetId);
                        if (existingConnection) {
                            openInlineEdgeEditor(existingConnection, jsPlumbInstance);
                        } else {
                            // Open edge symbol modal for new connection
                            openEdgeSymbolModal(sourceId, targetId, (source, target, symbolsString, hasEpsilon, isCurved) => {
                                // Create snapshot before edge creation for undo/redo
                                if (undoRedoManager && !undoRedoManager.isProcessing()) {
                                    const snapshotCommand = undoRedoManager.createSnapshotCommand(`Create edge ${source} → ${target}`);
                                    createConnection(jsPlumbInstance, source, target, symbolsString, hasEpsilon, isCurved, {
                                        onEdgeClick: handleEdgeClick
                                    });
                                    clearNFAStoredResults();
                                    updateFSAPropertiesDisplay(jsPlumbInstance);
                                    undoRedoManager.finishSnapshotCommand(snapshotCommand);
                                } else {
                                    createConnection(jsPlumbInstance, source, target, symbolsString, hasEpsilon, isCurved, {
                                        onEdgeClick: handleEdgeClick
                                    });
                                    clearNFAStoredResults();
                                    updateFSAPropertiesDisplay(jsPlumbInstance);
                                }

                                if (isCurved !== undefined) {
                                    deselectEdgeStyleButtons();
                                }
                            });
                        }
                    });
                } else if (sourceState === stateElement) {
                    // Clicking on the same state – create OR edit self-loop
                    edgeCreationManager.completeEdgeCreation(stateElement, (sourceId, targetId) => {
                        // Check if a self-loop already exists
                        const existingConnection = getConnectionBetween(jsPlumbInstance, sourceId, targetId);
                        if (existingConnection) {
                            // Self-loop exists → open inline editor instead of creating another
                            openInlineEdgeEditor(existingConnection, jsPlumbInstance);
                        } else {
                            // No existing self-loop → create a new curved one
                            openEdgeSymbolModal(sourceId, targetId, (source, target, symbolsString, hasEpsilon) => {
                                // Create snapshot before edge creation for undo/redo
                                if (undoRedoManager && !undoRedoManager.isProcessing()) {
                                    const snapshotCommand = undoRedoManager.createSnapshotCommand(`Create self-loop on ${source}`);
                                    createConnection(jsPlumbInstance, source, target, symbolsString, hasEpsilon, true, {  // Self-loops are always curved
                                        onEdgeClick: handleEdgeClick
                                    });
                                    clearNFAStoredResults();
                                    updateFSAPropertiesDisplay(jsPlumbInstance);
                                    undoRedoManager.finishSnapshotCommand(snapshotCommand);
                                } else {
                                    createConnection(jsPlumbInstance, source, target, symbolsString, hasEpsilon, true, {  // Self-loops are always curved
                                        onEdgeClick: handleEdgeClick
                                    });
                                    clearNFAStoredResults();
                                    updateFSAPropertiesDisplay(jsPlumbInstance);
                                }
                            });
                        }
                    });
                }
            }
        }
    } else {
        resetToolSelection();
        // If not using any specific tool, open edit modal when clicking a state
        openInlineStateEditor(stateElement, jsPlumbInstance);
    }
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
    if (currentTool === 'delete') {
        // Create snapshot before edge deletion for undo/redo
        if (undoRedoManager && !undoRedoManager.isProcessing()) {
            const snapshotCommand = undoRedoManager.createSnapshotCommand(`Delete edge ${connection.sourceId} → ${connection.targetId}`);
            deleteEdge(jsPlumbInstance, connection);
            undoRedoManager.finishSnapshotCommand(snapshotCommand);
        } else {
            deleteEdge(jsPlumbInstance, connection);
        }
        // Clear stored NFA results since FSA structure changed (deleteEdge already handles this)
        // Update properties display is called inside deleteEdge
    } else {
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
        cursorAt: { left: 30, top: 30 }, // Center the helper on cursor
        helper: function() {
            // Create a custom helper with high z-index
            const clone = $(this).clone();
            clone.css({
                'z-index': '9999', // Very high z-index to stay on top of canvas
                'position': 'fixed', // Use fixed positioning to avoid canvas interference
                'pointer-events': 'none' // Prevent interference with drop detection
            });
            return clone;
        },
        appendTo: 'body', // Append to body to avoid canvas clipping
        start: function(event, ui) {
            // Check if controls are locked before allowing drag
            if (controlLockManager.isControlsLocked()) {
                return false; // Cancel the drag
            }

            // Add performance optimisation class during tool drag
            document.body.classList.add('no-animation');
        },
        stop: function(event, ui) {
            if (controlLockManager.isControlsLocked()) return;

            // Remove performance optimisation class
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
 * Cleanup function for enhanced managers
 */
function cleanupEnhancedManagers() {
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
}

// Add cleanup event listener
window.addEventListener('beforeunload', cleanupEnhancedManagers);

// Make functions available globally for the serialization system
window.handleStateClick = handleStateClick;
window.handleStateDrag = handleStateDrag;