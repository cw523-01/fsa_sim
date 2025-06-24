/**
 * Enhanced Tool Manager
 * Provides unified visual feedback and instructions for all FSA tools
 */

class ToolManager {
    constructor() {
        this.currentTool = null;
        this.canvas = null;
        this.instructionsElement = null;
        this.cancelInstructionsElement = null;
        this.keydownHandler = null;
        this.canvasClickHandler = null;
        this.edgeCreationManager = null;
        this.instructionsTimeout = null;
        this.cancelInstructionsTimeout = null;
        this.originalHoverPaintStyle = null; // Store original JSPlumb hover style
        this.jsPlumbInstance = null; // Store JSPlumb instance reference

        // Tool configurations
        this.toolConfigs = {
            'state': {
                name: 'State Tool',
                instruction: 'Click on canvas to create a state',
                cancelInstruction: 'Press ESC or select another tool to cancel',
                cursorClass: 'state-creation-mode',
                toolClass: 'state-tool-selected'
            },
            'accepting-state': {
                name: 'Accepting State Tool',
                instruction: 'Click on canvas to create an accepting state',
                cancelInstruction: 'Press ESC or select another tool to cancel',
                cursorClass: 'accepting-state-creation-mode',
                toolClass: 'accepting-state-tool-selected'
            },
            'edge': {
                name: 'Edge Tool',
                instruction: 'Click on a state to start creating an edge',
                cancelInstruction: 'Press ESC or click empty space to cancel',
                cursorClass: 'edge-creation-mode',
                toolClass: 'edge-tool-selected'
            },
            'delete': {
                name: 'Delete Tool',
                instruction: 'Click on a state or edge (label) to delete it',
                cancelInstruction: 'Press ESC or select another tool to cancel',
                cursorClass: 'delete-mode',
                toolClass: 'delete-tool-selected'
            }
        };
    }

    /**
     * Initialize the tool manager
     * @param {HTMLElement} canvasElement - The FSA canvas element
     * @param {Object} edgeCreationManager - Reference to the edge creation manager
     * @param {Object} jsPlumbInstance - Reference to the JSPlumb instance
     */
    initialize(canvasElement, edgeCreationManager = null, jsPlumbInstance = null) {
        this.canvas = canvasElement;
        this.edgeCreationManager = edgeCreationManager;
        this.jsPlumbInstance = jsPlumbInstance;
        this.setupGlobalEventListeners();
    }

    /**
     * Setup global event listeners
     */
    setupGlobalEventListeners() {
        // Create and bind the keydown handler
        this.keydownHandler = (e) => {
            if (e.key === 'Escape' && this.currentTool) {
                this.deselectTool();
            }
        };
        document.addEventListener('keydown', this.keydownHandler);
    }

    /**
     * Select a tool with visual feedback
     * @param {string} toolName - The name of the tool to select
     */
    selectTool(toolName) {
        // If the same tool is already selected, deselect it
        if (this.currentTool === toolName) {
            this.deselectTool();
            return;
        }

        // Deselect current tool first
        this.deselectTool();

        // Validate tool
        const config = this.toolConfigs[toolName];
        if (!config) {
            console.error(`Unknown tool: ${toolName}`);
            return;
        }

        this.currentTool = toolName;

        // Special handling for edge tool
        if (toolName === 'edge' && this.edgeCreationManager) {
            this.edgeCreationManager.activateEdgeCreationMode();
            // EdgeCreationManager handles its own instructions, so we return early
            return;
        }

        // Special handling for delete tool - override JSPlumb hover styles
        if (toolName === 'delete') {
            this.activateDeleteMode();
        }

        // Add visual feedback to canvas
        this.canvas.classList.add(config.cursorClass);

        // Add visual feedback to tool button
        const toolElement = document.getElementById(`${toolName}-tool`);
        if (toolElement) {
            toolElement.classList.add('tool-selected');
            toolElement.classList.add(config.toolClass);
        }

        // Show instructions
        this.showInstructions(config.instruction);
        this.showCancelInstructions(config.cancelInstruction);

        console.log(`${config.name} activated`);
    }

    /**
     * Deselect the current tool
     */
    deselectTool() {
        if (!this.currentTool) return;

        const config = this.toolConfigs[this.currentTool];

        // Special handling for edge tool
        if (this.currentTool === 'edge' && this.edgeCreationManager) {
            this.edgeCreationManager.deactivateEdgeCreationMode();
            this.currentTool = null;
            return;
        }

        // Special handling for delete tool - restore JSPlumb hover styles
        if (this.currentTool === 'delete') {
            this.deactivateDeleteMode();
        }

        // Remove visual classes from canvas
        if (config) {
            this.canvas.classList.remove(config.cursorClass);
        }

        // Remove visual classes from tool button
        const toolElement = document.getElementById(`${this.currentTool}-tool`);
        if (toolElement) {
            toolElement.classList.remove('tool-selected');
            if (config) {
                toolElement.classList.remove(config.toolClass);
            }
        }

        // Hide instructions
        this.hideInstructions();
        this.hideCancelInstructions();

        console.log(`${config ? config.name : 'Tool'} deactivated`);
        this.currentTool = null;
    }

    /**
     * Activate delete mode with special JSPlumb hover handling
     */
    activateDeleteMode() {
        // Use the stored JSPlumb instance
        if (this.jsPlumbInstance) {
            // Store original hover paint style
            this.originalHoverPaintStyle = this.jsPlumbInstance.Defaults.HoverPaintStyle;

            // Override hover paint style for delete mode
            this.jsPlumbInstance.Defaults.HoverPaintStyle = {
                stroke: "#f44336",
                strokeWidth: 4
            };

            // Apply to all existing connections
            const connections = this.jsPlumbInstance.getAllConnections();
            connections.forEach(conn => {
                // Skip starting state connections
                if (conn.canvas && conn.canvas.classList.contains('starting-connection')) {
                    return;
                }

                conn.setHoverPaintStyle({ stroke: "#f44336", strokeWidth: 4 });
            });
        }

        console.log('Delete mode activated with enhanced edge highlighting');
    }

    /**
     * Deactivate delete mode and restore original JSPlumb hover styles
     */
    deactivateDeleteMode() {
        // Restore original JSPlumb hover paint style
        if (this.jsPlumbInstance && this.originalHoverPaintStyle) {
            // Restore original hover paint style
            this.jsPlumbInstance.Defaults.HoverPaintStyle = this.originalHoverPaintStyle;

            // Restore to all existing connections
            const connections = this.jsPlumbInstance.getAllConnections();
            connections.forEach(conn => {
                // Skip starting state connections
                if (conn.canvas && conn.canvas.classList.contains('starting-connection')) {
                    return;
                }

                conn.setHoverPaintStyle(this.originalHoverPaintStyle);
            });

            this.originalHoverPaintStyle = null;
        }

        console.log('Delete mode deactivated, JSPlumb hover styles restored');
    }

    /**
     * Get the currently selected tool
     * @returns {string|null} - The current tool name
     */
    getCurrentTool() {
        return this.currentTool;
    }

    /**
     * Update instructions for the current tool
     * @param {string} instruction - New instruction text
     */
    updateInstructions(instruction) {
        if (this.currentTool && this.instructionsElement) {
            this.showInstructions(instruction);
        }
    }

    /**
     * Check if a specific tool is selected
     * @param {string} toolName - Tool name to check
     * @returns {boolean} - True if the tool is selected
     */
    isToolSelected(toolName) {
        return this.currentTool === toolName;
    }

    /**
     * Show instructions at top of canvas
     * @param {string} text - Instruction text
     */
    showInstructions(text) {
        // Clear any pending hide timeout
        if (this.instructionsTimeout) {
            clearTimeout(this.instructionsTimeout);
            this.instructionsTimeout = null;
        }

        if (!this.instructionsElement) {
            this.instructionsElement = document.createElement('div');
            this.instructionsElement.classList.add('tool-instructions');
            this.canvas.appendChild(this.instructionsElement);
        }

        // Remove hidden class if it exists
        this.instructionsElement.classList.remove('hidden');
        this.instructionsElement.textContent = text;
    }

    /**
     * Hide instructions
     */
    hideInstructions() {
        if (this.instructionsElement) {
            this.instructionsElement.classList.add('hidden');

            // Clear any existing timeout
            if (this.instructionsTimeout) {
                clearTimeout(this.instructionsTimeout);
            }

            this.instructionsTimeout = setTimeout(() => {
                if (this.instructionsElement && this.instructionsElement.parentNode) {
                    this.instructionsElement.remove();
                    this.instructionsElement = null;
                }
                this.instructionsTimeout = null;
            }, 300);
        }
    }

    /**
     * Show cancel instructions at bottom of canvas
     * @param {string} text - Cancel instruction text
     */
    showCancelInstructions(text) {
        // Clear any pending hide timeout
        if (this.cancelInstructionsTimeout) {
            clearTimeout(this.cancelInstructionsTimeout);
            this.cancelInstructionsTimeout = null;
        }

        if (!this.cancelInstructionsElement) {
            this.cancelInstructionsElement = document.createElement('div');
            this.cancelInstructionsElement.classList.add('tool-cancel-instructions');
            this.canvas.appendChild(this.cancelInstructionsElement);
        }

        // Remove hidden class if it exists
        this.cancelInstructionsElement.classList.remove('hidden');
        this.cancelInstructionsElement.textContent = text;
    }

    /**
     * Hide cancel instructions
     */
    hideCancelInstructions() {
        if (this.cancelInstructionsElement) {
            this.cancelInstructionsElement.classList.add('hidden');

            // Clear any existing timeout
            if (this.cancelInstructionsTimeout) {
                clearTimeout(this.cancelInstructionsTimeout);
            }

            this.cancelInstructionsTimeout = setTimeout(() => {
                if (this.cancelInstructionsElement && this.cancelInstructionsElement.parentNode) {
                    this.cancelInstructionsElement.remove();
                    this.cancelInstructionsElement = null;
                }
                this.cancelInstructionsTimeout = null;
            }, 300);
        }
    }

    /**
     * Clean up all resources
     */
    destroy() {
        this.deselectTool();

        // Clear any pending timeouts
        if (this.instructionsTimeout) {
            clearTimeout(this.instructionsTimeout);
            this.instructionsTimeout = null;
        }
        if (this.cancelInstructionsTimeout) {
            clearTimeout(this.cancelInstructionsTimeout);
            this.cancelInstructionsTimeout = null;
        }

        // Remove event listeners
        if (this.keydownHandler) {
            document.removeEventListener('keydown', this.keydownHandler);
        }
        if (this.canvasClickHandler && this.canvas) {
            this.canvas.removeEventListener('click', this.canvasClickHandler);
        }

        // Clean up any remaining elements immediately
        if (this.instructionsElement && this.instructionsElement.parentNode) {
            this.instructionsElement.remove();
            this.instructionsElement = null;
        }
        if (this.cancelInstructionsElement && this.cancelInstructionsElement.parentNode) {
            this.cancelInstructionsElement.remove();
            this.cancelInstructionsElement = null;
        }
    }
}

// Create singleton instance
const toolManager = new ToolManager();

// Make globally available
window.toolManager = toolManager;

// Export for module systems
export { ToolManager, toolManager };