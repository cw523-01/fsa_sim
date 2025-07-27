/**
 * Edge Creation Visual Feedback Manager
 */

class EdgeCreationManager {
    constructor() {
        this.isEdgeCreationMode = false;
        this.sourceState = null;
        this.previewEdge = null;
        this.instructionsElement = null;
        this.cancelInstructionsElement = null;
        this.cursorFollower = null;
        this.canvas = null;
        this.mouseMoveHandler = null;
        this.keydownHandler = null;
        this.canvasClickHandler = null;
    }

    /**
     * Initialize the edge creation manager
     * @param {HTMLElement} canvasElement - The FSA canvas element
     */
    initialise(canvasElement) {
        this.canvas = canvasElement;
        this.setupEventListeners();
    }

    /**
     * Setup global event listeners
     */
    setupEventListeners() {
        this.keydownHandler = (e) => {
            if (e.key === 'Escape' && this.isEdgeCreationMode) {
                this.cancelEdgeCreation();
            }
        };
        document.addEventListener('keydown', this.keydownHandler);

        this.canvasClickHandler = (e) => {
            if (this.isEdgeCreationMode && e.target === this.canvas) {
                this.cancelEdgeCreation();
            }
        };
        this.canvas.addEventListener('click', this.canvasClickHandler);
    }

    /**
     * Activate edge creation mode
     */
    activateEdgeCreationMode() {
        if (this.isEdgeCreationMode) return;

        this.isEdgeCreationMode = true;

        // Add visual class to canvas
        this.canvas.classList.add('edge-creation-mode');

        // Add class to edge tool for visual feedback
        const edgeTool = document.getElementById('edge-tool');
        if (edgeTool) {
            edgeTool.classList.add('tool-selected');
        }

        // Show instructions
        this.showInstructions('Click on a state to start creating an edge');

    }

    /**
     * Deactivate edge creation mode
     */
    deactivateEdgeCreationMode() {
        if (!this.isEdgeCreationMode) return;

        this.isEdgeCreationMode = false;

        // Remove visual classes
        this.canvas.classList.remove('edge-creation-mode', 'edge-creation-active');

        // Remove edge tool selection
        const edgeTool = document.getElementById('edge-tool');
        if (edgeTool) {
            edgeTool.classList.remove('tool-selected');
        }

        // Clean up any active edge creation
        this.cancelEdgeCreation();

    }

    /**
     * Start edge creation from a source state
     * @param {HTMLElement} sourceStateElement - The source state element
     */
    startEdgeCreation(sourceStateElement) {
        if (!this.isEdgeCreationMode) return;

        this.sourceState = sourceStateElement;

        // Add visual feedback to source state
        sourceStateElement.classList.add('selected-source');

        // Add active class to canvas
        this.canvas.classList.add('edge-creation-active');

        // Create preview edge
        this.createPreviewEdge();

        // Create cursor follower
        this.createCursorFollower();

        // Start mouse tracking
        this.startMouseTracking();

        // Update instructions
        this.showInstructions('Click on a target state to create the edge');
        this.showCancelInstructions('Press ESC or click empty space to cancel');

    }

    /**
     * Complete edge creation to a target state
     * @param {HTMLElement} targetStateElement - The target state element
     * @param {Function} onComplete - Callback function to handle edge creation
     */
    completeEdgeCreation(targetStateElement, onComplete) {
        if (!this.sourceState || !this.isEdgeCreationMode) return;

        const sourceId = this.sourceState.id;
        const targetId = targetStateElement.id;

        console.log('Edge creation completed:', sourceId, '->', targetId);

        // Stop mouse tracking and clean up
        this.stopMouseTracking();
        this.cleanupEdgeCreation();

        // Call the completion callback
        if (onComplete) {
            onComplete(sourceId, targetId);
        }

        // Reset state but keep edge creation mode active
        this.sourceState = null;
        this.canvas.classList.remove('edge-creation-active');
        this.showInstructions('Click on a state to start creating another edge');
        this.hideCancelInstructions();
    }

    /**
     * Cancel current edge creation
     */
    cancelEdgeCreation() {
        this.stopMouseTracking();
        this.cleanupEdgeCreation();
        this.sourceState = null;
        this.canvas.classList.remove('edge-creation-active');

        if (this.isEdgeCreationMode) {
            this.showInstructions('Click on a state to start creating an edge');
            this.hideCancelInstructions();
        }
    }

    /**
     * Clean up all visual elements from edge creation
     */
    cleanupEdgeCreation() {
        // Remove source state visual feedback
        if (this.sourceState) {
            this.sourceState.classList.remove('selected-source');
        }

        // Remove preview edge
        this.removePreviewEdge();

        // Remove cursor follower
        this.removeCursorFollower();

        // Hide instructions
        this.hideInstructions();
        this.hideCancelInstructions();
    }

    /**
     * Create preview edge SVG element
     */
    createPreviewEdge() {
        if (this.previewEdge) return;

        const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
        svg.classList.add('preview-edge');
        svg.style.position = 'absolute';
        svg.style.top = '0';
        svg.style.left = '0';
        svg.style.width = '100%';
        svg.style.height = '100%';
        svg.style.pointerEvents = 'none';
        svg.style.zIndex = '5';

        // Create line element
        const line = document.createElementNS('http://www.w3.org/2000/svg', 'line');
        line.classList.add('preview-edge-line');
        line.setAttribute('x1', '0');
        line.setAttribute('y1', '0');
        line.setAttribute('x2', '0');
        line.setAttribute('y2', '0');

        // Create arrow marker
        const defs = document.createElementNS('http://www.w3.org/2000/svg', 'defs');
        const marker = document.createElementNS('http://www.w3.org/2000/svg', 'marker');
        marker.setAttribute('id', 'preview-arrow');
        marker.setAttribute('markerWidth', '10');
        marker.setAttribute('markerHeight', '10');
        marker.setAttribute('refX', '9');
        marker.setAttribute('refY', '3');
        marker.setAttribute('orient', 'auto');
        marker.setAttribute('markerUnits', 'strokeWidth');

        const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
        path.setAttribute('d', 'M0,0 L0,6 L9,3 z');
        path.classList.add('preview-edge-arrow');

        marker.appendChild(path);
        defs.appendChild(marker);
        svg.appendChild(defs);

        line.setAttribute('marker-end', 'url(#preview-arrow)');
        svg.appendChild(line);

        this.canvas.appendChild(svg);
        this.previewEdge = { svg, line };
    }

    /**
     * Remove preview edge
     */
    removePreviewEdge() {
        if (this.previewEdge && this.previewEdge.svg) {
            this.previewEdge.svg.remove();
            this.previewEdge = null;
        }
    }

    /**
     * Create cursor follower element
     */
    createCursorFollower() {
        if (this.cursorFollower) return;

        const follower = document.createElement('div');
        follower.classList.add('edge-creation-cursor');
        this.canvas.appendChild(follower);
        this.cursorFollower = follower;
    }

    /**
     * Remove cursor follower
     */
    removeCursorFollower() {
        if (this.cursorFollower) {
            this.cursorFollower.remove();
            this.cursorFollower = null;
        }
    }

    /**
     * Start mouse tracking
     */
    startMouseTracking() {
        if (this.mouseMoveHandler) return;

        this.mouseMoveHandler = (e) => {
            this.handleMouseMove(e);
        };

        this.canvas.addEventListener('mousemove', this.mouseMoveHandler);
    }

    /**
     * Stop mouse tracking
     */
    stopMouseTracking() {
        if (this.mouseMoveHandler) {
            this.canvas.removeEventListener('mousemove', this.mouseMoveHandler);
            this.mouseMoveHandler = null;
        }
    }

    /**
     * Handle mouse move events
     * @param {MouseEvent} e - Mouse move event
     */
    handleMouseMove(e) {
        if (!this.sourceState || !this.previewEdge) return;

        const canvasRect = this.canvas.getBoundingClientRect();
        const mouseX = e.clientX - canvasRect.left;
        const mouseY = e.clientY - canvasRect.top;

        // Update cursor follower position
        if (this.cursorFollower) {
            this.cursorFollower.style.left = (mouseX - 6) + 'px';
            this.cursorFollower.style.top = (mouseY - 6) + 'px';

            // Check if near a state for visual feedback
            const isNearState = this.isMouseNearState(mouseX, mouseY);
            this.cursorFollower.classList.toggle('large', isNearState);
        }

        // Update preview edge
        this.updatePreviewEdge(mouseX, mouseY);
    }

    /**
     * Update preview edge position
     * @param {number} mouseX - Mouse X coordinate
     * @param {number} mouseY - Mouse Y coordinate
     */
    updatePreviewEdge(mouseX, mouseY) {
        if (!this.sourceState || !this.previewEdge) return;

        const sourceRect = this.sourceState.getBoundingClientRect();
        const canvasRect = this.canvas.getBoundingClientRect();

        const sourceX = sourceRect.left - canvasRect.left + sourceRect.width / 2;
        const sourceY = sourceRect.top - canvasRect.top + sourceRect.height / 2;

        // Calculate edge points (from edge of circle, not centre)
        const dx = mouseX - sourceX;
        const dy = mouseY - sourceY;
        const distance = Math.sqrt(dx * dx + dy * dy);

        if (distance > 0) {
            const radius = 30; // Half of state size
            const startX = sourceX + (dx / distance) * radius;
            const startY = sourceY + (dy / distance) * radius;

            // End point is slightly before cursor for arrow visibility
            const endX = mouseX - (dx / distance) * 15;
            const endY = mouseY - (dy / distance) * 15;

            this.previewEdge.line.setAttribute('x1', startX);
            this.previewEdge.line.setAttribute('y1', startY);
            this.previewEdge.line.setAttribute('x2', endX);
            this.previewEdge.line.setAttribute('y2', endY);
        }
    }

    /**
     * Check if mouse is near a state element
     * @param {number} mouseX - Mouse X coordinate
     * @param {number} mouseY - Mouse Y coordinate
     * @returns {boolean} - True if mouse is near a state
     */
    isMouseNearState(mouseX, mouseY) {
        const threshold = 40;
        const canvasRect = this.canvas.getBoundingClientRect();
        const states = this.canvas.querySelectorAll('.state, .accepting-state');

        for (const state of states) {
            const rect = state.getBoundingClientRect();
            const stateX = rect.left - canvasRect.left + rect.width / 2;
            const stateY = rect.top - canvasRect.top + rect.height / 2;

            const distance = Math.sqrt(
                Math.pow(mouseX - stateX, 2) + Math.pow(mouseY - stateY, 2)
            );

            if (distance < threshold) {
                return true;
            }
        }

        return false;
    }

    /**
     * Show instructions at top of canvas
     * @param {string} text - Instruction text
     */
    showInstructions(text) {
        if (!this.instructionsElement) {
            this.instructionsElement = document.createElement('div');
            this.instructionsElement.classList.add('edge-creation-instructions');
            this.canvas.appendChild(this.instructionsElement);
        }

        this.instructionsElement.textContent = text;
        this.instructionsElement.classList.remove('hidden');
    }

    /**
     * Hide instructions
     */
    hideInstructions() {
        if (this.instructionsElement) {
            this.instructionsElement.classList.add('hidden');
            setTimeout(() => {
                if (this.instructionsElement && this.instructionsElement.parentNode) {
                    this.instructionsElement.remove();
                    this.instructionsElement = null;
                }
            }, 300);
        }
    }

    /**
     * Show cancel instructions at bottom of canvas
     * @param {string} text - Cancel instruction text
     */
    showCancelInstructions(text) {
        if (!this.cancelInstructionsElement) {
            this.cancelInstructionsElement = document.createElement('div');
            this.cancelInstructionsElement.classList.add('edge-creation-cancel');
            this.canvas.appendChild(this.cancelInstructionsElement);
        }

        this.cancelInstructionsElement.textContent = text;
        this.cancelInstructionsElement.classList.remove('hidden');
    }

    /**
     * Hide cancel instructions
     */
    hideCancelInstructions() {
        if (this.cancelInstructionsElement) {
            this.cancelInstructionsElement.classList.add('hidden');
            setTimeout(() => {
                if (this.cancelInstructionsElement && this.cancelInstructionsElement.parentNode) {
                    this.cancelInstructionsElement.remove();
                    this.cancelInstructionsElement = null;
                }
            }, 300);
        }
    }

    /**
     * Check if edge creation mode is active
     * @returns {boolean}
     */
    isActive() {
        return this.isEdgeCreationMode;
    }

    /**
     * Check if currently creating an edge (source selected)
     * @returns {boolean}
     */
    isCreatingEdge() {
        return this.isEdgeCreationMode && this.sourceState !== null;
    }

    /**
     * Get current source state
     * @returns {HTMLElement|null}
     */
    getSourceState() {
        return this.sourceState;
    }

    /**
     * Clean up all resources
     */
    destroy() {
        this.deactivateEdgeCreationMode();

        // Remove event listeners
        if (this.keydownHandler) {
            document.removeEventListener('keydown', this.keydownHandler);
        }
        if (this.canvasClickHandler && this.canvas) {
            this.canvas.removeEventListener('click', this.canvasClickHandler);
        }

        // Clean up any remaining elements
        this.cleanupEdgeCreation();
    }
}

// Create singleton instance
const edgeCreationManager = new EdgeCreationManager();

// Make globally available
window.edgeCreationManager = edgeCreationManager;

// Export for module systems
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { EdgeCreationManager, edgeCreationManager };
}

export { EdgeCreationManager, edgeCreationManager };