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
            await fsaSerializationManager.deserializeFSA(this.beforeSnapshot, this.jsPlumbInstance);
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
            await fsaSerializationManager.deserializeFSA(this.afterSnapshot, this.jsPlumbInstance);
            this.updateDisplays();
            return true;
        } catch (error) {
            console.error('Error during redo:', error);
            return false;
        }
    }

    /**
     * Update displays after undo/redo
     */
    updateDisplays() {
        updateAlphabetDisplay(getEdgeSymbolMap(), getEpsilonTransitionMap());
        updateFSAPropertiesDisplay(this.jsPlumbInstance);
        nfaResultsManager.clearStoredPaths();
    }
}

/**
 * Create State Command
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
        // This would be called by the undo system, but state creation is handled elsewhere
        // We just need to track it for undo
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

            // CRITICAL FIX: Pass the original stateId to preserve state names during redo
            const recreatedState = createState(
                this.jsPlumbInstance,
                this.x,
                this.y,
                this.isAccepting,
                callbacks,
                this.stateId  // Pass the original state ID explicitly
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
        nfaResultsManager.clearStoredPaths();
    }
}

/**
 * Undo/Redo Manager Class
 */
class UndoRedoManager {
    constructor() {
        this.undoStack = [];
        this.redoStack = [];
        this.maxStackSize = 50; // Limit memory usage
        this.jsPlumbInstance = null;
        this.isUndoRedoInProgress = false; // Prevent recursive operations
        this.eventListenersSetup = false;
    }

    /**
     * Initialize with JSPlumb instance
     */
    initialize(jsPlumbInstance) {
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
        const menuUndo = document.getElementById('menu-undo');
        const menuRedo = document.getElementById('menu-redo');

        if (menuUndo) {
            menuUndo.addEventListener('click', (e) => {
                e.stopPropagation();

                // Close the edit dropdown
                this.closeEditDropdown();

                // Check if controls are locked
                if (window.controlLockManager && window.controlLockManager.isControlsLocked()) {
                    console.log('Cannot undo while simulation is running');
                    return;
                }

                // Perform undo
                console.log('Undo menu clicked');
                this.undo();
            });
        }

        if (menuRedo) {
            menuRedo.addEventListener('click', (e) => {
                e.stopPropagation();

                // Close the edit dropdown
                this.closeEditDropdown();

                // Check if controls are locked
                if (window.controlLockManager && window.controlLockManager.isControlsLocked()) {
                    console.log('Cannot redo while simulation is running');
                    return;
                }

                // Perform redo
                console.log('Redo menu clicked');
                this.redo();
            });
        }

        console.log('Undo/Redo menu event listeners setup complete');
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

            // Ctrl+Z or Cmd+Z - Undo
            if ((e.ctrlKey || e.metaKey) && e.key === 'z' && !e.shiftKey) {
                e.preventDefault();
                console.log('Undo keyboard shortcut triggered');
                this.undo();
            }

            // Ctrl+Y or Cmd+Y or Ctrl+Shift+Z - Redo
            if (((e.ctrlKey || e.metaKey) && e.key === 'y') ||
                ((e.ctrlKey || e.metaKey) && e.shiftKey && e.key === 'z')) {
                e.preventDefault();
                console.log('Redo keyboard shortcut triggered');
                this.redo();
            }
        });
    }

    /**
     * Close the edit dropdown menu
     */
    closeEditDropdown() {
        const editDropdown = document.getElementById('edit-dropdown');
        const editButton = document.getElementById('edit-menu-button');

        if (editDropdown) {
            editDropdown.classList.remove('show');
        }
        if (editButton) {
            editButton.classList.remove('active');
        }
    }

    /**
     * Execute a command and add it to the undo stack
     */
    executeCommand(command) {
        if (this.isUndoRedoInProgress) return;

        try {
            // Execute the command
            command.execute();

            // Add to undo stack
            this.undoStack.push(command);

            // Clear redo stack since we're creating a new branch
            this.redoStack = [];

            // Limit stack size
            if (this.undoStack.length > this.maxStackSize) {
                this.undoStack.shift();
            }

            this.updateMenuStates();
            console.log(`Command executed: ${command.getDescription()}`);

        } catch (error) {
            console.error('Error executing command:', error);
        }
    }

    /**
     * Create and execute an FSA snapshot command for complex operations
     */
    createSnapshotCommand(description, beforeSnapshot = null) {
        if (this.isUndoRedoInProgress) return null;

        const command = new FSASnapshotCommand(description, this.jsPlumbInstance, beforeSnapshot);
        return command;
    }

    /**
     * Finish a snapshot command by capturing the after state and adding to stack
     */
    finishSnapshotCommand(command) {
        if (!command || this.isUndoRedoInProgress) return;

        try {
            // Capture the after state
            command.execute();

            // Add to undo stack
            this.undoStack.push(command);

            // Clear redo stack
            this.redoStack = [];

            // Limit stack size
            if (this.undoStack.length > this.maxStackSize) {
                this.undoStack.shift();
            }

            this.updateMenuStates();
            console.log(`Snapshot command completed: ${command.getDescription()}`);

        } catch (error) {
            console.error('Error finishing snapshot command:', error);
        }
    }

    /**
     * Record a state creation for undo/redo
     */
    recordStateCreation(stateId, x, y, isAccepting) {
        if (this.isUndoRedoInProgress) return;

        const command = new CreateStateCommand(this.jsPlumbInstance, stateId, x, y, isAccepting);

        // Don't execute - the state was already created
        // Just add to undo stack
        this.undoStack.push(command);
        this.redoStack = [];

        if (this.undoStack.length > this.maxStackSize) {
            this.undoStack.shift();
        }

        this.updateMenuStates();
        console.log(`State creation recorded: ${command.getDescription()}`);
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
     * Clear all undo/redo history
     */
    clearHistory() {
        this.undoStack = [];
        this.redoStack = [];
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
     * Get undo stack size
     */
    getUndoStackSize() {
        return this.undoStack.length;
    }

    /**
     * Get redo stack size
     */
    getRedoStackSize() {
        return this.redoStack.length;
    }

    /**
     * Get description of next undo action
     */
    getNextUndoDescription() {
        if (this.undoStack.length === 0) return null;
        return this.undoStack[this.undoStack.length - 1].getDescription();
    }

    /**
     * Get description of next redo action
     */
    getNextRedoDescription() {
        if (this.redoStack.length === 0) return null;
        return this.redoStack[this.redoStack.length - 1].getDescription();
    }
}

// Create and export singleton instance
export const undoRedoManager = new UndoRedoManager();

// Export classes for potential extension
export { UndoRedoManager, Command, FSASnapshotCommand, CreateStateCommand };

// Make globally available
window.undoRedoManager = undoRedoManager;