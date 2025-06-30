/**
 * Enhanced Edge Creation Visual Feedback Manager
 * Optimized to prevent interference with state dragging
 */

class EdgeCreationManager {
    constructor() {
        this.isEdgeCreationMode = false;
        this.sourceState = null;
        this.previewEdge = null;
        this.instructionsElement = null;
        this.cancelInstructionsElement = null;
        this.cursorFollower = null;
        this.connectionDot = null;
        this.canvas = null;
        this.mouseMoveHandler = null;
        this.keydownHandler = null;

        // Performance optimization: throttle mouse move events
        this.mouseThrottleTimeout = null;
        this.lastMouseUpdate = 0;
        this.mouseUpdateInterval = 16; // ~60fps

        // Cache for expensive DOM operations
        this.canvasRect = null;
        this.statePositions = new Map();
        this.cacheUpdateTime = 0;
        this.cacheTimeout = 100; // Cache for 100ms

        // Performance tracking
        this.isDragInProgress = false;
        this.dragCheckInterval = null;

        // Don't bind methods here - bind them when they're used
    }

    /**
     * Initialize the edge creation manager
     * @param {HTMLElement} canvasElement - The FSA canvas element
     */
    initialize(canvasElement) {
        this.canvas = canvasElement;
        this.setupEventListeners();
        this.setupDragDetection();
    }

    /**
     * Setup drag detection to prevent mouse tracking during state dragging
     */
    setupDragDetection() {
        // Monitor for drag state changes
        this.dragCheckInterval = setInterval(() => {
            const wasDragging = this.isDragInProgress;
            this.isDragInProgress = document.querySelector('.ui-draggable-dragging') !== null;

            // If drag state changed, update mouse tracking accordingly
            if (wasDragging !== this.isDragInProgress) {
                if (this.isDragInProgress) {
                    console.log('Drag detected - pausing edge creation mouse tracking');
                    this.pauseMouseTracking();
                } else {
                    console.log('Drag ended - resuming edge creation mouse tracking');
                    this.resumeMouseTracking();
                }
            }
        }, 16); // Check every frame
    }

    /**
     * Pause mouse tracking temporarily
     */
    pauseMouseTracking() {
        if (this.mouseMoveHandler && this.canvas) {
            this.canvas.removeEventListener('mousemove', this.mouseMoveHandler);
        }
    }

    /**
     * Resume mouse tracking if edge creation is active
     */
    resumeMouseTracking() {
        if (this.isEdgeCreationMode && this.sourceState && this.mouseMoveHandler && this.canvas) {
            this.canvas.addEventListener('mousemove', this.mouseMoveHandler, { passive: true });
        }
    }

    /**
     * Setup global event listeners
     */
    setupEventListeners() {
        // Create and bind the keydown handler when setting up
        this.keydownHandler = (e) => {
            if (e.key === 'Escape' && this.isEdgeCreationMode) {
                this.cancelEdgeCreation();
            }
        };
        document.addEventListener('keydown', this.keydownHandler);

        // Create and bind the canvas click handler when setting up
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

        console.log('Edge creation mode activated');
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

        console.log('Edge creation mode deactivated');
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

        // Start optimized mouse tracking
        this.startOptimizedMouseTracking();

        // Update instructions
        this.showInstructions('Click on a target state to create the edge');
        this.showCancelInstructions('Press ESC or click empty space to cancel');

        console.log('Edge creation started from state:', sourceStateElement.id);
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

        // Clean up visual elements
        this.cleanupEdgeCreation();

        // Call the completion callback
        if (onComplete) {
            onComplete(sourceId, targetId);
        }

        // Reset state but keep edge creation mode active for potential next edge
        this.sourceState = null;
        this.canvas.classList.remove('edge-creation-active');
        this.showInstructions('Click on a state to start creating another edge');
        this.hideCancelInstructions();
    }

    /**
     * Cancel current edge creation
     */
    cancelEdgeCreation() {
        console.log('Edge creation cancelled');

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

        // Remove connection dot
        this.removeConnectionDot();

        // Stop mouse tracking
        this.stopMouseTracking();

        // Hide instructions
        this.hideInstructions();
        this.hideCancelInstructions();

        // Clear caches
        this.clearCache();
    }

    /**
     * Create preview edge SVG element with performance optimizations
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
        // Add GPU acceleration
        svg.style.willChange = 'transform';
        svg.style.transform = 'translate3d(0, 0, 0)';

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
     * Create cursor follower element with performance optimizations
     */
    createCursorFollower() {
        if (this.cursorFollower) return;

        const follower = document.createElement('div');
        follower.classList.add('edge-creation-cursor');
        // Add GPU acceleration
        follower.style.willChange = 'transform';
        follower.style.transform = 'translate3d(0, 0, 0)';
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
     * Update connection dot position efficiently
     * @param {HTMLElement} dot - The dot element
     * @param {HTMLElement} stateElement - The state element
     */
    updateConnectionDotPosition(dot, stateElement) {
        const rect = this.getCachedElementRect(stateElement);
        const canvasRect = this.getCachedCanvasRect();

        // Use transform for better performance
        const left = rect.left - canvasRect.left + rect.width - 4;
        const top = rect.top - canvasRect.top + rect.height / 2 - 4;
        dot.style.transform = `translate(${left}px, ${top}px)`;
    }

    /**
     * Remove connection dot
     */
    removeConnectionDot() {
        if (this.connectionDot) {
            this.connectionDot.remove();
            this.connectionDot = null;
        }
    }

    /**
     * Start mouse tracking
     */
    startOptimizedMouseTracking() {
        if (this.mouseMoveHandler) return;

        // Create throttled mouse move handler with enhanced drag detection
        this.mouseMoveHandler = (e) => {
            // Enhanced drag detection - check multiple indicators
            if (this.isDragInProgress ||
                document.querySelector('.ui-draggable-dragging') ||
                document.body.classList.contains('no-animation')) {
                return;
            }

            // Additional check: if any state is currently being dragged
            const states = document.querySelectorAll('.state, .accepting-state');
            for (const state of states) {
                if (state.classList.contains('ui-draggable-dragging')) {
                    return;
                }
            }

            const now = performance.now();
            if (now - this.lastMouseUpdate < this.mouseUpdateInterval) {
                // Clear any pending throttle timeout
                if (this.mouseThrottleTimeout) {
                    clearTimeout(this.mouseThrottleTimeout);
                }

                // Schedule update for next frame
                this.mouseThrottleTimeout = setTimeout(() => {
                    this.handleMouseMove(e);
                    this.lastMouseUpdate = performance.now();
                }, this.mouseUpdateInterval);
                return;
            }

            this.handleMouseMove(e);
            this.lastMouseUpdate = now;
        };

        // Only add listener if not currently dragging
        if (!this.isDragInProgress) {
            this.canvas.addEventListener('mousemove', this.mouseMoveHandler, { passive: true });
        }
        console.log('Optimized mouse tracking started');
    }

    /**
     * Stop mouse tracking
     */
    stopMouseTracking() {
        if (this.mouseMoveHandler) {
            this.canvas.removeEventListener('mousemove', this.mouseMoveHandler);
            this.mouseMoveHandler = null;
        }

        if (this.mouseThrottleTimeout) {
            clearTimeout(this.mouseThrottleTimeout);
            this.mouseThrottleTimeout = null;
        }

        console.log('Optimized mouse tracking stopped');
    }

    /**
     * Handle mouse move events
     * @param {MouseEvent} e - Mouse move event
     */
    handleMouseMove(e) {
        if (!this.sourceState || !this.previewEdge) return;

        const canvasRect = this.getCachedCanvasRect();
        const mouseX = e.clientX - canvasRect.left;
        const mouseY = e.clientY - canvasRect.top;

        // Update cursor follower position using transform for better performance
        if (this.cursorFollower) {
            this.cursorFollower.style.transform = `translate(${mouseX - 6}px, ${mouseY - 6}px)`;

            // Optimized state proximity check
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

        const sourceRect = this.getCachedElementRect(this.sourceState);
        const canvasRect = this.getCachedCanvasRect();

        const sourceX = sourceRect.left - canvasRect.left + sourceRect.width / 2;
        const sourceY = sourceRect.top - canvasRect.top + sourceRect.height / 2;

        // Calculate edge points (from edge of circle, not center)
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
     * Check if mouse is near a state element using cached positions
     * @param {number} mouseX - Mouse X coordinate
     * @param {number} mouseY - Mouse Y coordinate
     * @returns {boolean} - True if mouse is near a state
     */
    isMouseNearState(mouseX, mouseY) {
        const threshold = 40; // Distance threshold
        const states = this.getCachedStatePositions();

        for (const [stateId, position] of states) {
            const distance = Math.sqrt(
                Math.pow(mouseX - position.x, 2) + Math.pow(mouseY - position.y, 2)
            );

            if (distance < threshold) {
                return true;
            }
        }

        return false;
    }

    /**
     * Get cached canvas rect to avoid expensive getBoundingClientRect calls
     * @returns {DOMRect} - Canvas bounding rect
     */
    getCachedCanvasRect() {
        const now = performance.now();
        if (!this.canvasRect || (now - this.cacheUpdateTime) > this.cacheTimeout) {
            this.canvasRect = this.canvas.getBoundingClientRect();
            this.cacheUpdateTime = now;
        }
        return this.canvasRect;
    }

    /**
     * Get cached element rect
     * @param {HTMLElement} element - The element
     * @returns {DOMRect} - Element bounding rect
     */
    getCachedElementRect(element) {
        // For source state, we can cache more aggressively since it's not moving during edge creation
        if (element === this.sourceState && this.sourceStateRect) {
            return this.sourceStateRect;
        }

        const rect = element.getBoundingClientRect();

        if (element === this.sourceState) {
            this.sourceStateRect = rect;
        }

        return rect;
    }

    /**
     * Get cached state positions for proximity checking
     * @returns {Map} - Map of state IDs to positions
     */
    getCachedStatePositions() {
        const now = performance.now();
        if (this.statePositions.size === 0 || (now - this.cacheUpdateTime) > this.cacheTimeout) {
            this.updateStatePositionsCache();
        }
        return this.statePositions;
    }

    /**
     * Update the cache of state positions
     */
    updateStatePositionsCache() {
        this.statePositions.clear();
        const canvasRect = this.getCachedCanvasRect();
        const states = this.canvas.querySelectorAll('.state, .accepting-state');

        states.forEach(state => {
            const rect = state.getBoundingClientRect();
            this.statePositions.set(state.id, {
                x: rect.left - canvasRect.left + rect.width / 2,
                y: rect.top - canvasRect.top + rect.height / 2
            });
        });
    }

    /**
     * Clear all caches
     */
    clearCache() {
        this.canvasRect = null;
        this.sourceStateRect = null;
        this.statePositions.clear();
        this.cacheUpdateTime = 0;
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

        // Stop drag detection
        if (this.dragCheckInterval) {
            clearInterval(this.dragCheckInterval);
            this.dragCheckInterval = null;
        }

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