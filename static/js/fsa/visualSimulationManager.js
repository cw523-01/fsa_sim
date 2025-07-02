import {hasEpsilonTransition} from "./edgeManager.js";
import { notificationManager } from './notificationManager.js';

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
        this.simulationResult = null; // Store simulation result for popup
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

        const newInputValue = this.inputField ? this.inputField.value : '';

        if (this.isRunning) {
            this.stopSimulation();
        }

        this.originalInputValue = newInputValue;

        this.isRunning = true;
        this.currentStep = 0;
        this.executionPath = executionPath;
        this.inputString = inputString;
        this.originalInputValue = this.inputField ? this.inputField.value : '';

        // Store simulation result for later popup display
        this.simulationResult = {
            isAccepted: isAccepted,
            executionPath: executionPath,
            inputString: inputString
        };

        console.log('Starting visual simulation with path:', executionPath);

        // Clear any previous highlights
        this.clearAllHighlights();

        // Clear input field and setup character highlighting
        this.setupInputHighlighting();

        try {
            // Handle empty string case
            if (executionPath.length === 0) {
                const startingStateId = this.getStartingStateId();

                if (startingStateId) {
                    await this.highlightStartingTransition(startingStateId);
                    this.highlightState(startingStateId, 'current');
                    await this.waitForAnimation(this.animationSpeed);
                    this.showFinalResult(isAccepted);

                    setTimeout(() => {
                        if (this.isRunning) {
                            this.autoClickStopButton();
                        }
                    }, 2000);
                }
            } else {
                // Normal case with non-empty execution path
                const startingState = executionPath[0][0];

                await this.highlightStartingTransition(startingState);
                this.highlightState(startingState, 'current');

                // FIXED: Track input position separately from step index for epsilon transitions
                let inputPosition = 0;

                // Execute each step in the path
                for (let i = 0; i < executionPath.length; i++) {
                    if (!this.isRunning) break;

                    const [currentState, symbol, nextState] = executionPath[i];
                    const isEpsilonTransition = symbol === 'ε' || symbol === '';

                    // Update input highlighting based on input position, not step index
                    if (!isEpsilonTransition) {
                        this.updateInputHighlight(inputPosition);
                        inputPosition++; // Only increment for non-epsilon transitions
                    }

                    this.highlightTransition(currentState, nextState, symbol);

                    // Wait for animation
                    await new Promise((resolve) => {
                        this.currentTimeout = setTimeout(() => {
                            if (!this.isRunning) {
                                resolve();
                                return;
                            }

                            this.clearStateHighlight(currentState);
                            this.highlightState(nextState, 'current');

                            const nextStep = executionPath[i + 1];
                            const isSelfLoop = nextStep &&
                                nextStep[0] === currentState &&
                                nextStep[2] === nextState &&
                                currentState === nextState;

                            if (!isSelfLoop) {
                                setTimeout(() => {
                                    this.dimTransition(currentState, nextState, symbol);
                                }, 200);
                            }

                            resolve();
                        }, this.animationSpeed);

                        this.animationTimeouts.push(this.currentTimeout);
                    });

                    if (!this.isRunning) break;
                }

                // Show final result if simulation completed
                if (this.isRunning) {
                    this.showFinalResult(isAccepted);

                    setTimeout(() => {
                        if (this.isRunning) {
                            this.autoClickStopButton();
                        }
                    }, 2000);
                }
            }

        } catch (error) {
            console.error('Error during visual simulation:', error);
            this.stopSimulation();
        }
    }

    /**
     * Get the starting state ID from the DOM or backend data
     * @returns {string|null} - The starting state ID
     */
    getStartingStateId() {
        // Try to get starting state from the state manager
        if (typeof getStartingStateId === 'function') {
            return getStartingStateId();
        }

        // Fallback: look for starting state indicator in DOM
        const startingConnections = document.querySelectorAll('.starting-connection');
        if (startingConnections.length > 0) {
            // Get the target of the starting connection
            const startingConnection = startingConnections[0];
            if (this.jsPlumbInstance) {
                const allConnections = this.jsPlumbInstance.getAllConnections();
                const connection = allConnections.find(conn =>
                    conn.canvas === startingConnection
                );
                if (connection) {
                    return connection.targetId;
                }
            }
        }

        // Final fallback: get first state element
        const stateElements = document.querySelectorAll('.state, .accepting-state');
        if (stateElements.length > 0) {
            return stateElements[0].id;
        }

        return null;
    }

    /**
     * Wait for animation timing
     * @param {number} duration - Duration to wait in milliseconds
     * @returns {Promise} - Promise that resolves after the duration
     */
    waitForAnimation(duration) {
        return new Promise((resolve) => {
            this.currentTimeout = setTimeout(() => {
                if (this.isRunning) {
                    resolve();
                } else {
                    resolve(); // Always resolve to avoid hanging
                }
            }, duration);

            this.animationTimeouts.push(this.currentTimeout);
        });
    }

    /**
     * Hide the result popup (now uses notification manager)
     */
    hideResultPopup() {
        notificationManager.hideSimulationResultPopup();
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

            // Only update input highlight for non-epsilon transitions
            const isEpsilonTransition = symbol === 'ε' || symbol === '';
            if (!isEpsilonTransition) {
                this.updateInputHighlight(stepIndex);
            }

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
        // Handle epsilon transitions
        const isEpsilonSymbol = symbol === 'ε' || symbol === '';

        // Import the edge manager functions
        if (typeof getEdgeSymbols === 'function' && typeof hasEpsilonTransition === 'function') {
            // Check for epsilon transition
            if (isEpsilonSymbol) {
                return hasEpsilonTransition(connection);
            }

            // Check for regular symbols
            const symbols = getEdgeSymbols(connection);
            return symbols.includes(symbol);
        }

        // Fallback: check the label text
        const labelOverlay = connection.getOverlay('label');
        if (labelOverlay) {
            const labelText = labelOverlay.getLabel();

            // Check for epsilon in label
            if (isEpsilonSymbol) {
                return labelText.includes('ε');
            }

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
        } else {
            // For empty string, highlight the starting state as final
            const startingStateId = this.getStartingStateId();
            if (startingStateId) {
                this.highlightState(startingStateId, isAccepted ? 'final' : 'rejected');
            }
        }

        // Calculate the final input position based on non-epsilon transitions
        let finalInputPosition = 0;
        if (this.executionPath.length > 0) {
            // Count only non-epsilon transitions to get the correct input position
            for (const [currentState, symbol, nextState] of this.executionPath) {
                const isEpsilonTransition = symbol === 'ε' || symbol === '';
                if (!isEpsilonTransition) {
                    finalInputPosition++;
                }
            }
        }

        // Update input field to show completion with correct position
        this.updateInputHighlight(finalInputPosition, isAccepted);
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

        // Handle empty string case
        if (this.inputString.length === 0) {
            if (stepIndex === -1) {
                // Initial state for empty string
                overlay.innerHTML = '<span style="color: #666; font-style: italic;">ε (empty string)</span>';
            } else if (isComplete !== null) {
                // Completion state for empty string
                if (isComplete) {
                    overlay.innerHTML = '<span style="color: #4CAF50; font-weight: bold; font-style: italic;">ε (empty string)</span>';
                    overlay.style.backgroundColor = 'rgba(76, 175, 80, 0.1)';
                    overlay.style.borderColor = '#4CAF50';
                } else {
                    overlay.innerHTML = '<span style="color: #f44336; font-weight: bold; font-style: italic;">ε (empty string)</span>';
                    overlay.style.backgroundColor = 'rgba(244, 67, 54, 0.1)';
                    overlay.style.borderColor = '#f44336';
                }
            }
            return;
        }

        // Build highlighted version character by character for non-empty strings
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
     * Automatically click the stop button to end the simulation
     */
    autoClickStopButton() {
        console.log('Auto-clicking stop button after simulation completion');

        const stopButton = document.getElementById('stop-btn');
        if (stopButton && !stopButton.disabled) {
            // Trigger the stop button click event
            stopButton.click();

            // Show result popup after a brief delay to allow stop processing
            setTimeout(() => {
                this.showResultPopup();
            }, 300);
        } else {
            // Fallback: stop simulation manually and show popup
            this.stopSimulation();
            this.showResultPopup();
        }
    }

    /**
     * Show the simulation result popup (now uses notification manager)
     */
    showResultPopup() {
        if (!this.simulationResult) return;

        // Create result object for notification manager
        const result = {
            accepted: this.simulationResult.isAccepted,
            path: this.simulationResult.executionPath || []
        };

        // Use notification manager to show popup
        notificationManager.showSimulationResultPopup(
            result,
            this.simulationResult.inputString,
            false, // not fast-forward
            this.simulationResult.executionPath
        );
    }

    /**
     * Show the simulation result popup with fast-forward indicator (now uses notification manager)
     */
    showFastForwardResultPopup() {
        if (!this.simulationResult) return;

        // Create result object for notification manager
        const result = {
            accepted: this.simulationResult.isAccepted,
            path: this.simulationResult.executionPath || []
        };

        // Use notification manager to show popup
        notificationManager.showSimulationResultPopup(
            result,
            this.simulationResult.inputString,
            true, // is fast-forward
            this.simulationResult.executionPath
        );
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

// Make it globally accessible for popup interactions
window.visualSimulationManager = visualSimulationManager;

// Export the class as well for potential multiple instances
export { VisualSimulationManager };