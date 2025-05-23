/**
 * Visual simulation manager class to handle step-by-step animation of FSA execution
 */
class VisualSimulationManager {
    constructor() {
        this.isRunning = false;
        this.currentStep = 0;
        this.executionPath = [];
        this.inputString = '';
        this.jsPlumbInstance = null;
        this.animationSpeed = 1000; // milliseconds between steps
        this.highlightedElements = new Set(); // Track highlighted elements for cleanup
        this.animationTimeouts = []; // Track timeouts for cleanup
        this.currentTimeout = null;
        this.inputField = null; // Reference to the input field for highlighting
        this.originalInputValue = ''; // Store original input value
    }

    /**
     * Initialize the visual simulator with JSPlumb instance
     * @param {Object} jsPlumbInstance - The JSPlumb instance
     */
    initialize(jsPlumbInstance) {
        this.jsPlumbInstance = jsPlumbInstance;
        this.inputField = document.getElementById('fsa-input');
    }

    /**
     * Start visual simulation of the execution path
     * @param {Array} executionPath - Array of [currentState, symbol, nextState] tuples
     * @param {string} inputString - The input string being processed
     * @param {boolean} isAccepted - Whether the input is accepted
     */
    async startVisualSimulation(executionPath, inputString, isAccepted) {
        if (this.isRunning) {
            this.stopSimulation();
        }

        this.isRunning = true;
        this.currentStep = 0;
        this.executionPath = executionPath;
        this.inputString = inputString;
        this.originalInputValue = this.inputField ? this.inputField.value : ''; // Store original value

        console.log('Starting visual simulation with path:', executionPath);

        // Clear any previous highlights
        this.clearAllHighlights();

        // Clear input field and setup character highlighting
        this.setupInputHighlighting();

        try {
            // First, highlight the starting state transition if we have execution steps
            if (executionPath.length > 0) {
                const startingState = executionPath[0][0];

                // Highlight the starting state connection first
                await this.highlightStartingTransition(startingState);

                // Then highlight the starting state as current
                this.highlightState(startingState, 'current');
            }

            // Execute each step in the path
            for (let i = 0; i < executionPath.length; i++) {
                if (!this.isRunning) break;

                await this.executeStep(i);

                if (!this.isRunning) break;
            }

            // Show final result if simulation completed
            if (this.isRunning) {
                this.showFinalResult(isAccepted);
            }

        } catch (error) {
            console.error('Error during visual simulation:', error);
            this.stopSimulation();
        }
    }

    /**
     * Highlight the starting state transition (arrow pointing to starting state)
     * @param {string} startingStateId - ID of the starting state
     */
    async highlightStartingTransition(startingStateId) {
        return new Promise((resolve) => {
            // Find the starting state connection
            const startingConnection = this.findStartingStateConnection(startingStateId);

            if (startingConnection) {
                // Highlight the starting connection
                if (startingConnection.canvas) {
                    startingConnection.canvas.classList.add('sim-active-transition');
                    this.highlightedElements.add(startingConnection.canvas);
                }

                console.log(`Highlighted starting transition to ${startingStateId}`);

                // Wait for a moment to show the starting transition
                this.currentTimeout = setTimeout(() => {
                    if (!this.isRunning) {
                        resolve();
                        return;
                    }

                    // Dim the starting transition after highlighting
                    if (startingConnection.canvas) {
                        startingConnection.canvas.classList.remove('sim-active-transition');
                        startingConnection.canvas.classList.add('sim-used-transition');
                    }

                    resolve();
                }, this.animationSpeed * 0.7); // Slightly shorter duration for starting transition

                this.animationTimeouts.push(this.currentTimeout);
            } else {
                // If no starting connection found, just resolve immediately
                resolve();
            }
        });
    }

    /**
     * Find the starting state connection
     * @param {string} startingStateId - ID of the starting state
     * @returns {Object|null} - The starting state connection or null
     */
    findStartingStateConnection(startingStateId) {
        if (!this.jsPlumbInstance) return null;

        const allConnections = this.jsPlumbInstance.getAllConnections();

        // Look for connection from 'start-source' to the starting state
        return allConnections.find(conn =>
            conn.sourceId === 'start-source' &&
            conn.targetId === startingStateId &&
            conn.canvas &&
            conn.canvas.classList.contains('starting-connection')
        );
    }

    /**
     * Execute a single step in the simulation
     * @param {number} stepIndex - Index of the step to execute
     */
    async executeStep(stepIndex) {
        return new Promise((resolve, reject) => {
            if (!this.isRunning) {
                resolve();
                return;
            }

            const step = this.executionPath[stepIndex];
            const [currentState, symbol, nextState] = step;

            this.updateInputHighlight(stepIndex);
            this.highlightTransition(currentState, nextState, symbol);

            this.currentTimeout = setTimeout(() => {
                if (!this.isRunning) {
                    resolve();
                    return;
                }

                this.clearStateHighlight(currentState);
                this.highlightState(nextState, 'current');

                const nextStep = this.executionPath[stepIndex + 1];
                const isSelfLoop = nextStep &&
                    nextStep[0] === currentState &&
                    nextStep[1] === symbol &&
                    nextStep[2] === nextState;

                if (!isSelfLoop) {
                    setTimeout(() => {
                        this.dimTransition(currentState, nextState, symbol);
                    }, 200);
                }

                this.currentStep = stepIndex + 1;
                resolve();
            }, this.animationSpeed);

            this.animationTimeouts.push(this.currentTimeout);
        });
    }

    /**
     * Highlight a state with a specific style
     * @param {string} stateId - ID of the state to highlight
     * @param {string} type - Type of highlight ('current', 'visited', 'final')
     */
    highlightState(stateId, type = 'current') {
        const stateElement = document.getElementById(stateId);
        if (!stateElement) return;

        // Remove existing highlight classes
        stateElement.classList.remove('sim-current', 'sim-visited', 'sim-final', 'sim-rejected');

        // Add appropriate highlight class
        stateElement.classList.add(`sim-${type}`);
        this.highlightedElements.add(stateElement);

        console.log(`Highlighted state ${stateId} as ${type}`);
    }

    /**
     * Clear highlight from a specific state
     * @param {string} stateId - ID of the state to clear
     */
    clearStateHighlight(stateId) {
        const stateElement = document.getElementById(stateId);
        if (!stateElement) return;

        // Change to visited state instead of completely removing
        stateElement.classList.remove('sim-current');
        stateElement.classList.add('sim-visited');
    }

    /**
     * Highlight a transition between two states
     * @param {string} sourceId - Source state ID
     * @param {string} targetId - Target state ID
     * @param {string} symbol - Symbol for this transition
     */
    highlightTransition(sourceId, targetId, symbol) {
        if (!this.jsPlumbInstance) return;

        // Find the connection between these states
        const connections = this.jsPlumbInstance.getAllConnections();
        const connection = connections.find(conn =>
            conn.sourceId === sourceId &&
            conn.targetId === targetId &&
            this.connectionHasSymbol(conn, symbol)
        );

        if (connection) {
            // Highlight the connection - ALWAYS remove used class first and add active
            if (connection.canvas) {
                connection.canvas.classList.remove('sim-used-transition'); // Remove any previous "used" state
                connection.canvas.classList.add('sim-active-transition');
                this.highlightedElements.add(connection.canvas);
            }

            // Highlight the label - ALWAYS remove used class first and add active
            const labelOverlay = connection.getOverlay('label');
            if (labelOverlay && labelOverlay.canvas) {
                labelOverlay.canvas.classList.remove('sim-used-label'); // Remove any previous "used" state
                labelOverlay.canvas.classList.add('sim-active-label');
                this.highlightedElements.add(labelOverlay.canvas);
            }

            console.log(`Highlighted transition ${sourceId} --${symbol}--> ${targetId}`);
        }
    }

    /**
     * Dim a transition after it's been used
     * @param {string} sourceId - Source state ID
     * @param {string} targetId - Target state ID
     * @param {string} symbol - Symbol for this transition
     */
    dimTransition(sourceId, targetId, symbol) {
        if (!this.jsPlumbInstance) return;

        const connections = this.jsPlumbInstance.getAllConnections();
        const connection = connections.find(conn =>
            conn.sourceId === sourceId &&
            conn.targetId === targetId &&
            this.connectionHasSymbol(conn, symbol)
        );

        if (connection) {
            // Remove active highlight and add used class
            if (connection.canvas) {
                connection.canvas.classList.remove('sim-active-transition');
                connection.canvas.classList.add('sim-used-transition');
            }

            const labelOverlay = connection.getOverlay('label');
            if (labelOverlay && labelOverlay.canvas) {
                labelOverlay.canvas.classList.remove('sim-active-label');
                labelOverlay.canvas.classList.add('sim-used-label');
            }
        }
    }

    /**
     * Check if a connection has a specific symbol
     * @param {Object} connection - JSPlumb connection object
     * @param {string} symbol - Symbol to check for
     * @returns {boolean} - Whether the connection has this symbol
     */
    connectionHasSymbol(connection, symbol) {
        // Import the edge manager functions
        if (typeof getEdgeSymbols === 'function') {
            const symbols = getEdgeSymbols(connection);
            return symbols.includes(symbol);
        }

        // Fallback: check the label text
        const labelOverlay = connection.getOverlay('label');
        if (labelOverlay) {
            const labelText = labelOverlay.getLabel();
            return labelText.includes(symbol);
        }

        return false;
    }

    /**
     * Show the final result of the simulation
     * @param {boolean} isAccepted - Whether the input was accepted
     */
    showFinalResult(isAccepted) {
        // Find the final state
        if (this.executionPath.length > 0) {
            const finalStep = this.executionPath[this.executionPath.length - 1];
            const finalState = finalStep[2];

            // Highlight final state appropriately
            this.highlightState(finalState, isAccepted ? 'final' : 'rejected');
        }

        // Update input field to show completion
        this.updateInputHighlight(this.executionPath.length, isAccepted);

        // Auto-stop simulation after showing result
        setTimeout(() => {
            if (this.isRunning) {
                this.stopSimulation();
            }
        }, 2000);
    }

    /**
     * Setup input field highlighting by clearing text and creating overlay
     */
    setupInputHighlighting() {
        if (!this.inputField) return;

        // Store original value and clear the input field
        this.inputField.value = '';

        // Add simulation active class for border highlighting
        this.inputField.classList.add('simulation-active');

        // Create the character overlay
        this.updateInputHighlight(-1);
    }

    /**
     * Highlight the input field and show current character being processed
     * @param {number} stepIndex - Current step index (-1 for initial state)
     * @param {boolean} isComplete - Whether simulation is complete
     */
    updateInputHighlight(stepIndex = -1, isComplete = null) {
        if (!this.inputField) return;

        // Create a span-based highlighting system that overlays the input field
        let overlay = document.getElementById('input-character-overlay');
        if (!overlay) {
            overlay = document.createElement('div');
            overlay.id = 'input-character-overlay';

            // Position it exactly over the input field
            this.inputField.parentNode.style.position = 'relative';
            this.inputField.parentNode.appendChild(overlay);
        }

        // Get the exact positioning and styling from the input field
        const inputStyles = window.getComputedStyle(this.inputField);
        const inputRect = this.inputField.getBoundingClientRect();
        const parentRect = this.inputField.parentNode.getBoundingClientRect();

        // Position overlay exactly over the input field
        overlay.style.position = 'absolute';
        overlay.style.left = (inputRect.left - parentRect.left) + 'px';
        overlay.style.top = (inputRect.top - parentRect.top) + 'px';
        overlay.style.width = inputRect.width + 'px';
        overlay.style.height = inputRect.height + 'px';
        overlay.style.padding = inputStyles.padding;
        overlay.style.border = '2px solid transparent';
        overlay.style.borderRadius = inputStyles.borderRadius;
        overlay.style.fontSize = inputStyles.fontSize;
        overlay.style.fontFamily = inputStyles.fontFamily;
        overlay.style.lineHeight = inputStyles.lineHeight;
        overlay.style.display = 'flex';
        overlay.style.alignItems = 'center';
        overlay.style.pointerEvents = 'none';
        overlay.style.background = 'white';
        overlay.style.whiteSpace = 'nowrap';
        overlay.style.overflow = 'hidden';
        overlay.style.zIndex = '10';
        overlay.style.boxSizing = 'border-box';
        overlay.style.paddingLeft = '8px'; // Match input field padding

        // Build highlighted version character by character
        let highlightedHTML = '';

        for (let i = 0; i < this.inputString.length; i++) {
            const char = this.inputString[i];

            if (stepIndex === -1) {
                // Initial state - all characters are unprocessed
                highlightedHTML += `<span style="color: #666;">${char}</span>`;
            } else if (i < stepIndex) {
                // Characters already processed - green
                highlightedHTML += `<span style="color: #4CAF50; font-weight: bold;">${char}</span>`;
            } else if (i === stepIndex && isComplete === null) {
                // Current character being processed - orange with highlight
                highlightedHTML += `<span style="color: #FF9800; font-weight: bold; background-color: rgba(255, 152, 0, 0.3); padding: 1px 2px; border-radius: 2px; animation: character-blink 1s infinite;">${char}</span>`;
            } else {
                // Remaining characters - gray
                highlightedHTML += `<span style="color: #666;">${char}</span>`;
            }
        }

        // Update the overlay content
        overlay.innerHTML = highlightedHTML;
        overlay.style.display = 'flex';

        // Add completion styling if needed
        if (isComplete !== null) {
            if (isComplete) {
                // All characters green for accepted
                highlightedHTML = '';
                for (let i = 0; i < this.inputString.length; i++) {
                    highlightedHTML += `<span style="color: #4CAF50; font-weight: bold;">${this.inputString[i]}</span>`;
                }
                overlay.innerHTML = highlightedHTML;
                overlay.style.backgroundColor = 'rgba(76, 175, 80, 0.1)';
                overlay.style.borderColor = '#4CAF50';
            } else {
                // All characters red for rejected
                highlightedHTML = '';
                for (let i = 0; i < this.inputString.length; i++) {
                    highlightedHTML += `<span style="color: #f44336; font-weight: bold;">${this.inputString[i]}</span>`;
                }
                overlay.innerHTML = highlightedHTML;
                overlay.style.backgroundColor = 'rgba(244, 67, 54, 0.1)';
                overlay.style.borderColor = '#f44336';
            }
        }
    }

    /**
     * Highlight the input field container to show simulation is active
     */
    highlightInputField() {
        if (this.inputField) {
            this.inputField.classList.add('simulation-active');
        }
    }

    /**
     * Clear input field highlighting and restore normal appearance
     */
    clearInputHighlight() {
        if (this.inputField) {
            this.inputField.classList.remove('simulation-active');
            // Restore the original input value
            if (this.originalInputValue !== undefined) {
                this.inputField.value = this.originalInputValue;
            }
        }

        // Remove the character overlay
        const overlay = document.getElementById('input-character-overlay');
        if (overlay) {
            overlay.remove();
        }
    }

    /**
     * Stop the simulation and clean up
     */
    stopSimulation() {
        console.log('Stopping visual simulation');

        this.isRunning = false;

        // Clear all timeouts
        this.animationTimeouts.forEach(timeout => clearTimeout(timeout));
        this.animationTimeouts = [];

        if (this.currentTimeout) {
            clearTimeout(this.currentTimeout);
            this.currentTimeout = null;
        }

        // Clear all visual highlights
        this.clearAllHighlights();

        // Clear input field highlighting
        this.clearInputHighlight();

        // Reset state
        this.currentStep = 0;
        this.executionPath = [];
        this.inputString = '';
    }

    /**
     * Clear all visual highlights from states and transitions
     */
    clearAllHighlights() {
        // Clear highlights from tracked elements
        this.highlightedElements.forEach(element => {
            if (element && element.classList) {
                element.classList.remove(
                    'sim-current', 'sim-visited', 'sim-final', 'sim-rejected',
                    'sim-active-transition', 'sim-used-transition',
                    'sim-active-label', 'sim-used-label'
                );
            }
        });

        this.highlightedElements.clear();

        // Also clear any remaining highlights that might have been missed
        const canvas = document.getElementById('fsa-canvas');
        if (canvas) {
            const highlightedElements = canvas.querySelectorAll(
                '.sim-current, .sim-visited, .sim-final, .sim-rejected, ' +
                '.sim-active-transition, .sim-used-transition, ' +
                '.sim-active-label, .sim-used-label'
            );

            highlightedElements.forEach(element => {
                element.classList.remove(
                    'sim-current', 'sim-visited', 'sim-final', 'sim-rejected',
                    'sim-active-transition', 'sim-used-transition',
                    'sim-active-label', 'sim-used-label'
                );
            });
        }
    }

    /**
     * Check if simulation is currently running
     * @returns {boolean} - Whether simulation is running
     */
    isSimulationRunning() {
        return this.isRunning;
    }
}

// Create and export a singleton instance
export const visualSimulationManager = new VisualSimulationManager();

// Export the class as well for potential multiple instances
export { VisualSimulationManager };