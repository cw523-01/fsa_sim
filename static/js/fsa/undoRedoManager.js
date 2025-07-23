/**
 * Undo/Redo Manager for FSA Editor
 * Implements command pattern to provide undo/redo functionality
 */

import { fsaSerializationManager } from './fsaSerializationManager.js';
import { notificationManager } from './notificationManager.js';
import { updateFSAPropertiesDisplay } from './fsaPropertyChecker.js';
import { updateAlphabetDisplay } from './alphabetManager.js';
import { getEdgeSymbolMap, getEpsilonTransitionMap } from './edgeManager.js';
import { nfaResultsManager } from './nfaResultsManager.js';
import { getStartingStateId, createStartingStateIndicator } from './stateManager.js';

/**
 * Base Command class - all undoable operations inherit from this
 */
class Command {
    constructor(description) {
        this.description = description;
        this.timestamp = Date.now();
    }

    /**
     * Execute the command
     */
    execute() {
        throw new Error('Execute method must be implemented');
    }

    /**
     * Undo the command
     */
    undo() {
        throw new Error('Undo method must be implemented');
    }

    /**
     * Redo the command (default implementation re-executes)
     */
    redo() {
        this.execute();
    }

    /**
     * Get description of the command for UI
     */
    getDescription() {
        return this.description;
    }
}

/**
 * FSA State Snapshot Command - captures entire FSA state for complex operations
 */
class FSASnapshotCommand extends Command {
    constructor(description, jsPlumbInstance, beforeSnapshot = null) {
        super(description);
        this.jsPlumbInstance = jsPlumbInstance;
        this.beforeSnapshot = beforeSnapshot || this.captureSnapshot();
        this.afterSnapshot = null;
    }

    /**
     * Capture current FSA state
     */
    captureSnapshot() {
        try {
            return fsaSerializationManager.serializeFSA(this.jsPlumbInstance);
        } catch (error) {
            console.error('Error capturing FSA snapshot:', error);
            return null;
        }
    }

    /**
     * Execute - capture after state
     */
    execute() {
        // This is called after the operation to capture the "after" state
        this.afterSnapshot = this.captureSnapshot();
    }

    /**
     * Undo - restore before state
     */
    async undo() {
        if (!this.beforeSnapshot) {
            console.error('No before snapshot available for undo');
            return false;
        }

        try {
            // Use exact position restoration for undo/redo
            await this.deserializeWithExactPositions(this.beforeSnapshot);
            this.updateDisplays();
            return true;
        } catch (error) {
            console.error('Error during undo:', error);
            return false;
        }
    }

    /**
     * Redo - restore after state
     */
    async redo() {
        if (!this.afterSnapshot) {
            console.error('No after snapshot available for redo');
            return false;
        }

        try {
            // Use exact position restoration for undo/redo
            await this.deserializeWithExactPositions(this.afterSnapshot);
            this.updateDisplays();
            return true;
        } catch (error) {
            console.error('Error during redo:', error);
            return false;
        }
    }

    /**
     * Deserialize FSA data with exact position preservation (no optimization)
     * This prevents states from being repositioned during undo/redo
     */
    async deserializeWithExactPositions(data) {
        // Clear current FSA
        await fsaSerializationManager.clearCurrentFSA(this.jsPlumbInstance);

        // Load states with EXACT positions (skip optimization)
        await this.deserializeStatesExactPositions(data.states);

        // Load transitions
        await fsaSerializationManager.deserializeTransitions(data.transitions, this.jsPlumbInstance);

        // Set starting state
        if (data.startingState) {
            createStartingStateIndicator(this.jsPlumbInstance, data.startingState);
        }

        // Force repaint
        this.jsPlumbInstance.repaintEverything();
    }

    /**
     * Deserialize states with exact positions (copied from fsaSerialisationManager but without optimization)
     */
    async deserializeStatesExactPositions(statesData) {
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

            // Use EXACT positions from the snapshot
            state.style.left = `${stateData.position.x}px`;
            state.style.top = `${stateData.position.y}px`;

            // Add GPU acceleration hints
            state.style.willChange = 'transform';
            state.style.transform = 'translate3d(0, 0, 0)';

            // Add any additional visual properties
            if (stateData.visual && stateData.visual.zIndex) {
                state.style.zIndex = stateData.visual.zIndex;
            }

            // Add to canvas
            document.getElementById('fsa-canvas').appendChild(state);

            // Capture jsPlumbInstance reference for use in callbacks
            const jsPlumbInstance = this.jsPlumbInstance;

            // Make state draggable with exact same configuration as createState
            $(state).draggable({
                containment: "parent",
                stack: ".state, .accepting-state",
                zIndex: 100,
                start: function(event, ui) {
                    if (window.isStateDragging !== undefined) {
                        window.isStateDragging = true;
                    }
                    document.body.classList.add('no-animation');
                    this.style.willChange = 'transform';
                    const rect = this.getBoundingClientRect();
                    const parentRect = this.parentElement.getBoundingClientRect();
                    this._originalLeft = rect.left - parentRect.left;
                    this._originalTop = rect.top - parentRect.top;
                },
                drag: function(event, ui) {
                    // Update starting state arrow if this is the starting state - REAL TIME
                    if (getStartingStateId() === this.id) {
                        const startSource = document.getElementById('start-source');
                        if (startSource) {
                            const stateHeight = this.offsetHeight;
                            const newLeft = ui.position.left - 50;
                            const newTop = ui.position.top + (stateHeight / 2) - 5;
                            startSource.style.left = newLeft + 'px';
                            startSource.style.top = newTop + 'px';
                        }
                    }

                    jsPlumbInstance.revalidate(this.id);
                    if (getStartingStateId() === this.id) {
                        jsPlumbInstance.revalidate('start-source');
                    }

                    if (callbacks.onStateDrag) {
                        callbacks.onStateDrag(this, event, ui);
                    }
                },
                stop: function(event, ui) {
                    document.body.classList.remove('no-animation');
                    setTimeout(() => {
                        this.style.willChange = 'auto';
                    }, 100);
                    jsPlumbInstance.repaintEverything();
                    setTimeout(() => {
                        if (window.isStateDragging !== undefined) {
                            window.isStateDragging = false;
                        }
                    }, 10);
                }
            });

            // Register with JSPlumb
            setTimeout(() => {
                jsPlumbInstance.revalidate(state.id);

                try {
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
                } catch (error) {
                    console.error(`Error registering state ${state.id} with JSPlumb:`, error);
                }
            }, 25);

            // Add click event handler
            state.addEventListener('click', function(e) {
                if (callbacks.onStateClick) {
                    callbacks.onStateClick(this, e);
                }
                e.stopPropagation();
            });
        }
    }

    updateDisplays() {
        updateAlphabetDisplay(getEdgeSymbolMap(), getEpsilonTransitionMap());
        updateFSAPropertiesDisplay(this.jsPlumbInstance);
        if (nfaResultsManager) {
            nfaResultsManager.clearStoredPaths();
        }
    }
}

/**
 * Create State Command with state tracking
 */
class CreateStateCommand extends Command {
    constructor(jsPlumbInstance, stateId, x, y, isAccepting) {
        super(`Create ${isAccepting ? 'accepting ' : ''}state ${stateId}`);
        this.jsPlumbInstance = jsPlumbInstance;
        this.stateId = stateId;
        this.x = x;
        this.y = y;
        this.isAccepting = isAccepting;
        this.wasFirstState = false;
    }

    execute() {
        // State was already created, just track it
    }

    async undo() {
        const stateElement = document.getElementById(this.stateId);
        if (!stateElement) return false;

        try {
            // Import deleteState function
            const { deleteState } = await import('./stateManager.js');
            const { getEdgeSymbolMap } = await import('./edgeManager.js');

            deleteState(this.jsPlumbInstance, stateElement, getEdgeSymbolMap());

            this.updateDisplays();
            return true;
        } catch (error) {
            console.error('Error undoing state creation:', error);
            return false;
        }
    }

    async redo() {
        try {
            // Import createState function
            const { createState } = await import('./stateManager.js');

            const callbacks = {
                onStateClick: window.handleStateClick || (() => {}),
                onStateDrag: window.handleStateDrag || (() => {})
            };

            // Pass the original stateId to preserve state names during redo
            const recreatedState = createState(
                this.jsPlumbInstance,
                this.x,
                this.y,
                this.isAccepting,
                callbacks,
                this.stateId
            );

            if (!recreatedState) {
                console.error(`Failed to recreate state with ID ${this.stateId}`);
                return false;
            }

            this.updateDisplays();
            return true;
        } catch (error) {
            console.error('Error redoing state creation:', error);
            return false;
        }
    }

    updateDisplays() {
        updateFSAPropertiesDisplay(this.jsPlumbInstance);
        if (nfaResultsManager) {
            nfaResultsManager.clearStoredPaths();
        }
    }
}

/**
 * Undo/Redo Manager Class
 */
class UndoRedoManager {
    constructor() {
        this.undoStack = [];
        this.redoStack = [];
        this.maxStackSize = 50;
        this.jsPlumbInstance = null;
        this.isUndoRedoInProgress = false;
        this.eventListenersSetup = false;

        // Command batching and debouncing
        this.pendingCommands = new Map(); // Key -> Command for debouncing
        this.debouncedCommands = new Map(); // Key -> timeout
        this.commandInProgress = new Set(); // Track operations in progress
        this.batchedCommands = []; // Commands to be batched together
        this.batchTimeout = null;
    }

    /**
     * Initialise with JSPlumb instance
     */
    initialise(jsPlumbInstance) {
        this.jsPlumbInstance = jsPlumbInstance;
        this.setupEventListeners();
        this.updateMenuStates();
    }

    /**
     * Setup event listeners for undo/redo
     */
    setupEventListeners() {
        if (this.eventListenersSetup) return;
        this.eventListenersSetup = true;

        // Wait for DOM to be ready and setup menu listeners
        // Use a small delay to ensure menu elements are ready
        setTimeout(() => {
            this.setupMenuEventListeners();
        }, 100);

        // Setup keyboard shortcuts immediately
        this.setupKeyboardShortcuts();
    }

    /**
     * Setup menu event listeners with proper dropdown integration
     */
    setupMenuEventListeners() {
        if (window.menuManager) {
            window.menuManager.registerMenuItems({
                'menu-undo': () => this.undo(),
                'menu-redo': () => this.redo()
            }, {
                validateUnlocked: true,
                clone: false
            });
        }
    }

    /**
     * Setup keyboard shortcuts
     */
    setupKeyboardShortcuts() {
        // Keyboard shortcuts
        document.addEventListener('keydown', (e) => {
            // Don't trigger if typing in input fields or if controls are locked
            if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') {
                return;
            }

            if (window.controlLockManager && window.controlLockManager.isControlsLocked()) {
                return;
            }

            // Undo
            if ((e.ctrlKey || e.metaKey) && e.key === 'z' && !e.shiftKey) {
                e.preventDefault();
                console.log('Undo keyboard shortcut triggered');
                this.undo();
            }

            // Redo
            if (((e.ctrlKey || e.metaKey) && e.key === 'y') ||
                ((e.ctrlKey || e.metaKey) && e.shiftKey && e.key === 'z')) {
                e.preventDefault();
                this.redo();
            }
        });
    }

    /**
     * Check if an operation type is already in progress
     */
    isOperationInProgress(operationType) {
        return this.commandInProgress.has(operationType) || this.isUndoRedoInProgress;
    }

    /**
     * Mark an operation as in progress
     */
    markOperationInProgress(operationType) {
        this.commandInProgress.add(operationType);
    }

    /**
     * Mark an operation as completed
     */
    markOperationComplete(operationType) {
        this.commandInProgress.delete(operationType);
    }

    /**
     * Create a debounced snapshot command for rapid operations like typing
     */
    createDebouncedSnapshotCommand(operationType, description, delay = 1000) {
        if (this.isUndoRedoInProgress) return null;

        // Clear any existing debounced command for this operation type
        if (this.debouncedCommands.has(operationType)) {
            clearTimeout(this.debouncedCommands.get(operationType));
        }

        // If this is the first command for this operation type, capture the before state
        if (!this.pendingCommands.has(operationType)) {
            const beforeSnapshot = new FSASnapshotCommand(description, this.jsPlumbInstance).captureSnapshot();
            this.pendingCommands.set(operationType, { description, beforeSnapshot });
        }

        // Set up debounced execution
        const timeoutId = setTimeout(() => {
            this.finaliseDebouncedCommand(operationType);
        }, delay);

        this.debouncedCommands.set(operationType, timeoutId);

        return { operationType, description };
    }

    /**
     * Finalise a debounced command
     */
    finaliseDebouncedCommand(operationType) {
        const pendingCommand = this.pendingCommands.get(operationType);
        if (!pendingCommand) return;

        // Create final command with before and after states
        const command = new FSASnapshotCommand(
            pendingCommand.description,
            this.jsPlumbInstance,
            pendingCommand.beforeSnapshot
        );

        // Capture after state and add to stack
        command.execute();
        this.addToUndoStack(command);

        // Clean up
        this.pendingCommands.delete(operationType);
        this.debouncedCommands.delete(operationType);
    }

    /**
     * Cancel a debounced command (for when operation is cancelled)
     */
    cancelDebouncedCommand(operationType) {
        if (this.debouncedCommands.has(operationType)) {
            clearTimeout(this.debouncedCommands.get(operationType));
            this.debouncedCommands.delete(operationType);
        }

        this.pendingCommands.delete(operationType);
    }

    /**
     * CreateSnapshotCommand with operation tracking
     */
    createSnapshotCommand(description, beforeSnapshot = null) {
        if (this.isUndoRedoInProgress) {
            console.log('Cannot create snapshot command during undo/redo operation');
            return null;
        }

        const operationType = `snapshot_${Date.now()}_${Math.random()}`;
        this.markOperationInProgress(operationType);

        const command = new FSASnapshotCommand(description, this.jsPlumbInstance, beforeSnapshot);
        command.operationType = operationType;

        return command;
    }

    /**
     * Finish a snapshot command by capturing the after state and adding to stack
     */
    finishSnapshotCommand(command) {
        if (!command || this.isUndoRedoInProgress) return;

        try {
            // Mark operation as complete
            if (command.operationType) {
                this.markOperationComplete(command.operationType);
            }

            // Capture the after state
            command.execute();

            // Add to stack
            this.addToUndoStack(command);

            console.log(`Snapshot command completed: ${command.getDescription()}`);

        } catch (error) {
            console.error('Error finishing snapshot command:', error);
            if (command.operationType) {
                this.markOperationComplete(command.operationType);
            }
        }
    }

    /**
     * RecordStateCreation with operation tracking
     */
    recordStateCreation(stateId, x, y, isAccepting) {
        if (this.isUndoRedoInProgress) return;

        const command = new CreateStateCommand(this.jsPlumbInstance, stateId, x, y, isAccepting);
        this.addToUndoStack(command);

        console.log(`State creation recorded: ${command.getDescription()}`);
    }

    /**
     * Centralised method to add commands to undo stack
     */
    addToUndoStack(command) {
        this.undoStack.push(command);
        this.redoStack = []; // Clear redo stack

        // Limit stack size
        if (this.undoStack.length > this.maxStackSize) {
            this.undoStack.shift();
        }

        this.updateMenuStates();
    }

    /**
     * Undo the last command
     */
    async undo() {
        if (this.undoStack.length === 0) {
            console.log('Nothing to undo');
            return;
        }

        if (window.controlLockManager && window.controlLockManager.isControlsLocked()) {
            console.log('Cannot undo while controls are locked');
            return;
        }

        // Finalise any pending debounced commands first
        this.finaliseAllDebouncedCommands();

        this.isUndoRedoInProgress = true;

        try {
            const command = this.undoStack.pop();
            console.log(`Undoing: ${command.getDescription()}`);

            const success = await command.undo();

            if (success) {
                this.redoStack.push(command);

                // Limit redo stack size
                if (this.redoStack.length > this.maxStackSize) {
                    this.redoStack.shift();
                }

                console.log(`Successfully undid: ${command.getDescription()}`);

            } else {
                // If undo failed, put the command back
                this.undoStack.push(command);
                console.error(`Failed to undo: ${command.getDescription()}`);
            }

        } catch (error) {
            console.error('Error during undo:', error);
        } finally {
            this.isUndoRedoInProgress = false;
            this.updateMenuStates();
        }
    }

    /**
     * Redo the last undone command
     */
    async redo() {
        if (this.redoStack.length === 0) {
            console.log('Nothing to redo');
            return;
        }

        if (window.controlLockManager && window.controlLockManager.isControlsLocked()) {
            console.log('Cannot redo while controls are locked');
            return;
        }

        this.isUndoRedoInProgress = true;

        try {
            const command = this.redoStack.pop();
            console.log(`Redoing: ${command.getDescription()}`);

            const success = await command.redo();

            if (success) {
                this.undoStack.push(command);

                // Limit undo stack size
                if (this.undoStack.length > this.maxStackSize) {
                    this.undoStack.shift();
                }

                console.log(`Successfully redid: ${command.getDescription()}`);

            } else {
                // If redo failed, put the command back
                this.redoStack.push(command);
                console.error(`Failed to redo: ${command.getDescription()}`);
            }

        } catch (error) {
            console.error('Error during redo:', error);
        } finally {
            this.isUndoRedoInProgress = false;
            this.updateMenuStates();
        }
    }

    /**
     * Finalise all pending debounced commands
     */
    finaliseAllDebouncedCommands() {
        for (const [operationType] of this.pendingCommands) {
            if (this.debouncedCommands.has(operationType)) {
                clearTimeout(this.debouncedCommands.get(operationType));
                this.finaliseDebouncedCommand(operationType);
            }
        }
    }

    /**
     * Clear all undo/redo history
     */
    clearHistory() {
        // Clear all debounced commands
        for (const [operationType, timeoutId] of this.debouncedCommands) {
            clearTimeout(timeoutId);
        }

        this.undoStack = [];
        this.redoStack = [];
        this.pendingCommands.clear();
        this.debouncedCommands.clear();
        this.commandInProgress.clear();

        this.updateMenuStates();
        console.log('Undo/Redo history cleared');
    }

    /**
     * Update menu item states (enabled/disabled)
     */
    updateMenuStates() {
        const menuUndo = document.getElementById('menu-undo');
        const menuRedo = document.getElementById('menu-redo');

        if (menuUndo) {
            if (this.undoStack.length > 0) {
                menuUndo.classList.remove('disabled');
                const lastCommand = this.undoStack[this.undoStack.length - 1];
                menuUndo.title = `Undo: ${lastCommand.getDescription()}`;
            } else {
                menuUndo.classList.add('disabled');
                menuUndo.title = 'Nothing to undo';
            }
        }

        if (menuRedo) {
            if (this.redoStack.length > 0) {
                menuRedo.classList.remove('disabled');
                const nextCommand = this.redoStack[this.redoStack.length - 1];
                menuRedo.title = `Redo: ${nextCommand.getDescription()}`;
            } else {
                menuRedo.classList.add('disabled');
                menuRedo.title = 'Nothing to redo';
            }
        }
    }

    /**
     * Check if currently processing undo/redo
     */
    isProcessing() {
        return this.isUndoRedoInProgress;
    }

    /**
     * Cancel a snapshot command without adding it to the undo stack
     * Used when an operation determines no changes were made
     */
    cancelSnapshotCommand(command) {
        if (!command || this.isUndoRedoInProgress) return;

        try {
            if (command.operationType) {
                this.markOperationComplete(command.operationType);
            }

            console.log(`Snapshot command cancelled: ${command.getDescription()}`);

            // Command is simply discarded - no need to add to any stack
            // The snapshot command object will be garbage collected

            // Update menu states in case they were waiting for this command
            this.updateMenuStates();

        } catch (error) {
            console.error('Error cancelling snapshot command:', error);
        }
    }

    // Getters for debugging/monitoring
    getUndoStackSize() { return this.undoStack.length; }
    getRedoStackSize() { return this.redoStack.length; }
    getNextUndoDescription() {
        return this.undoStack.length > 0 ? this.undoStack[this.undoStack.length - 1].getDescription() : null;
    }
    getNextRedoDescription() {
        return this.redoStack.length > 0 ? this.redoStack[this.redoStack.length - 1].getDescription() : null;
    }
}

// Create and export singleton instance
export const undoRedoManager = new UndoRedoManager();

// Export classes for extension
export { UndoRedoManager, Command, FSASnapshotCommand, CreateStateCommand };

// Make globally available
window.undoRedoManager = undoRedoManager;