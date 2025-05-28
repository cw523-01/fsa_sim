import { generateTransitionTable } from './transitionTableManager.js';
import { isDeterministic, isConnected } from './fsaPropertyChecker.js';
import { getStartingStateId } from './stateManager.js';
import { visualSimulationManager } from './visualSimulationManager.js';

/**
 * Converts the frontend FSA representation to the backend expected format
 * @param {Object} jsPlumbInstance - The JSPlumb instance
 * @returns {Object|null} - FSA in backend format or null if invalid
 */
export function convertFSAToBackendFormat(jsPlumbInstance) {
    // Generate transition table data
    const tableData = generateTransitionTable(jsPlumbInstance);

    // Validate that we have a starting state
    if (!tableData.startingState) {
        throw new Error('No starting state defined. Please set a starting state.');
    }

    // Validate that we have at least one state
    if (tableData.states.length === 0) {
        throw new Error('No states defined. Please create at least one state.');
    }

    // Validate that we have an alphabet
    if (tableData.alphabet.length === 0) {
        throw new Error('No alphabet defined. Please create at least one transition with symbols.');
    }

    // Check for epsilon transitions - backend doesn't support them for deterministic FSA
    if (tableData.hasEpsilon) {
        throw new Error('Epsilon transitions are not supported for deterministic FSA simulation.');
    }

    // Convert transitions to the backend expected format
    const backendTransitions = {};

    tableData.states.forEach(stateId => {
        backendTransitions[stateId] = {};

        tableData.alphabet.forEach(symbol => {
            const targets = tableData.transitions[stateId][symbol];

            // For backend format, we need an array of target states
            // Even for deterministic FSA, the backend expects arrays
            backendTransitions[stateId][symbol] = targets || [];
        });
    });

    // Create the FSA object in backend expected format
    const fsa = {
        states: tableData.states,
        alphabet: tableData.alphabet,
        transitions: backendTransitions,
        startingState: tableData.startingState,
        acceptingStates: tableData.acceptingStates
    };

    return fsa;
}

/**
 * Validates that the FSA meets requirements for simulation
 * @param {Object} jsPlumbInstance - The JSPlumb instance
 * @returns {Object} - Validation result with success flag and message
 */
export function validateFSAForSimulation(jsPlumbInstance) {
    try {
        // Check if FSA is deterministic
        if (!isDeterministic(jsPlumbInstance)) {
            return {
                success: false,
                message: 'FSA must be deterministic for simulation. Please ensure:\n' +
                        '• No epsilon transitions\n' +
                        '• At most one transition per state-symbol pair'
            };
        }

        // Check if FSA is connected
        if (!isConnected(jsPlumbInstance)) {
            return {
                success: false,
                message: 'FSA must be connected for simulation. Please ensure all states are reachable from the starting state.'
            };
        }

        // Try to convert to backend format (this will catch other issues)
        const fsa = convertFSAToBackendFormat(jsPlumbInstance);

        return {
            success: true,
            message: 'FSA is valid for simulation',
            fsa: fsa
        };

    } catch (error) {
        return {
            success: false,
            message: error.message
        };
    }
}

/**
 * Sends FSA and input string to backend for simulation
 * @param {Object} fsa - FSA in backend format
 * @param {string} inputString - Input string to simulate
 * @returns {Promise<Object>} - Promise resolving to simulation result
 */
export async function simulateFSAOnBackend(fsa, inputString) {
    const requestData = {
        fsa: fsa,
        input: inputString
    };

    try {
        console.log('Sending FSA simulation request:', requestData);

        const response = await fetch('/api/simulate-fsa/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(requestData)
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error || `HTTP error! status: ${response.status}`);
        }

        const result = await response.json();
        console.log('Received simulation result:', result);

        return result;

    } catch (error) {
        console.error('Error during FSA simulation:', error);
        throw error;
    }
}

/**
 * Show result popup for any simulation result (visual or fast-forward)
 * @param {Object} result - Result from backend simulation
 * @param {string} inputString - The input string that was simulated
 * @param {boolean} isFastForward - Whether this was a fast-forward simulation
 */
export function showSimulationResultPopup(result, inputString, isFastForward = false) {
    // Use the visual simulation manager's popup system
    const simulationResult = {
        isAccepted: result.accepted,
        executionPath: result.path || [],
        inputString: inputString,
        isFastForward: isFastForward
    };

    // Store the result in the visual simulation manager
    visualSimulationManager.simulationResult = simulationResult;

    // Show the popup directly with custom content for fast-forward
    if (isFastForward) {
        visualSimulationManager.showFastForwardResultPopup();
    } else {
        visualSimulationManager.showResultPopup();
    }
}

/**
 * Show error popup for validation or simulation errors
 * @param {string} errorMessage - The error message to display
 * @param {string} inputString - The input string (if any)
 */
export function showSimulationErrorPopup(errorMessage, inputString = '') {
    // Remove any existing popup
    const existingPopup = document.getElementById('simulation-result-popup');
    if (existingPopup) {
        existingPopup.remove();
    }

    // Create error popup element
    const popup = document.createElement('div');
    popup.id = 'simulation-result-popup';
    popup.className = 'error';

    // Create error-specific styles if they don't exist
    if (!document.querySelector('style[data-error-popup]')) {
        const style = document.createElement('style');
        style.setAttribute('data-error-popup', 'true');
        style.textContent = `
            #simulation-result-popup.error {
                border-left-color: #ff9800;
                background: linear-gradient(135deg, #fff3e0 0%, #fafafa 100%);
            }
            .popup-status.error {
                color: #ef6c00;
            }
            .popup-icon.error {
                background-color: #ff9800;
            }
            .popup-result.error {
                color: #ef6c00;
            }
        `;
        document.head.appendChild(style);
    }

    const inputDisplay = inputString ?
        `<div class="popup-input">Input: <span class="popup-input-string">"${inputString}"</span></div>` : '';

    popup.innerHTML = `
        <div class="popup-header">
            <div class="popup-status error">
                <div class="popup-icon error">⚠</div>
                <span>SIMULATION ERROR</span>
            </div>
            <button class="popup-close" onclick="visualSimulationManager.hideResultPopup()">×</button>
        </div>
        ${inputDisplay}
        <div class="popup-result error">
            Error: Simulation Failed
        </div>
        <div class="popup-details">
            ${errorMessage.replace(/\n/g, '<br>')}
        </div>
        <div class="popup-progress">
            <div class="popup-progress-bar" style="background-color: #ff9800;"></div>
        </div>
    `;

    // Add popup to canvas
    const canvas = document.getElementById('fsa-canvas');
    if (canvas) {
        canvas.appendChild(popup);

        // Trigger show animation
        setTimeout(() => {
            popup.classList.add('show');
        }, 100);

        // Start auto-close timer (longer for error messages)
        visualSimulationManager.startAutoCloseTimer(popup, 7000); // 7 seconds for errors
    }
}

/**
 * Main function to run FSA simulation with visual animation
 * @param {Object} jsPlumbInstance - The JSPlumb instance
 * @param {string} inputString - Input string to simulate
 * @param {boolean} visualMode - Whether to show visual animation (default: true)
 * @returns {Promise<Object>} - Promise resolving to simulation result with formatted message
 */
export async function runFSASimulation(jsPlumbInstance, inputString, visualMode = true) {
    try {
        // Validate the FSA
        const validation = validateFSAForSimulation(jsPlumbInstance);

        if (!validation.success) {
            if (visualMode) {
                // Show error popup instead of alert for visual mode
                showSimulationErrorPopup(validation.message, inputString);
                return {
                    success: false,
                    message: '', // Empty since popup handles display
                    type: 'validation_error',
                    isVisual: true
                };
            } else {
                return {
                    success: false,
                    message: validation.message,
                    type: 'validation_error'
                };
            }
        }

        // Initialize visual simulation manager with JSPlumb instance
        if (visualMode) {
            visualSimulationManager.initialize(jsPlumbInstance);
        }

        // Simulate on backend
        const result = await simulateFSAOnBackend(validation.fsa, inputString);

        if (visualMode && result.path && result.path.length > 0) {
            // Start visual simulation for accepted inputs with execution path
            console.log('Starting visual simulation with path:', result.path);
            visualSimulationManager.startVisualSimulation(result.path, inputString, result.accepted);

            // Return success without showing text alert (visual simulation will handle display)
            return {
                success: true,
                message: '', // Empty message since visual simulation handles display
                rawResult: result,
                type: 'visual_simulation',
                isVisual: true
            };
        } else {
            // For rejected inputs, fast-forward mode, or when visual mode is off
            if (!visualMode) {
                // Fast-forward mode - show popup instead of alert
                showSimulationResultPopup(result, inputString, true);
                return {
                    success: true,
                    message: '', // Empty since popup handles display
                    rawResult: result,
                    type: 'fast_forward_simulation',
                    isVisual: true // Set to true since we're using popup
                };
            } else {
                // Visual mode but rejected - show popup
                showSimulationResultPopup(result, inputString, false);
                return {
                    success: true,
                    message: '', // Empty since popup handles display
                    rawResult: result,
                    type: 'simulation_result',
                    isVisual: true
                };
            }
        }

    } catch (error) {
        console.error('Simulation error:', error);

        if (visualMode) {
            // Show error popup instead of alert
            showSimulationErrorPopup(`An error occurred during simulation:\n${error.message}`, inputString);
            return {
                success: false,
                message: '', // Empty since popup handles display
                type: 'backend_error',
                isVisual: true
            };
        } else {
            return {
                success: false,
                message: `❌ SIMULATION ERROR!\n\n${error.message}`,
                type: 'backend_error',
                isVisual: false
            };
        }
    }
}

/**
 * Run FSA simulation with fast-forward (no visual animation)
 * @param {Object} jsPlumbInstance - The JSPlumb instance
 * @param {string} inputString - Input string to simulate
 * @returns {Promise<Object>} - Promise resolving to simulation result
 */
export async function runFSASimulationFastForward(jsPlumbInstance, inputString) {
    return runFSASimulation(jsPlumbInstance, inputString, false);
}

/**
 * Stop any currently running visual simulation
 */
export function stopVisualSimulation() {
    visualSimulationManager.stopSimulation();
}

/**
 * Check if visual simulation is currently running
 * @returns {boolean} - Whether visual simulation is running
 */
export function isVisualSimulationRunning() {
    return visualSimulationManager.isSimulationRunning();
}

/**
 * Helper function to get input string from the UI
 * @returns {string} - The input string from the input field
 */
export function getInputString() {
    const inputField = document.getElementById('fsa-input');
    return inputField ? inputField.value.trim() : '';
}

/**
 * Helper function to validate input string
 * @param {string} inputString - Input string to validate
 * @param {Array} alphabet - FSA alphabet
 * @returns {Object} - Validation result
 */
export function validateInputString(inputString, alphabet) {
    // Empty string is valid
    if (inputString === '') {
        return { valid: true };
    }

    // Check if all characters in input are in the alphabet
    for (let char of inputString) {
        if (!alphabet.includes(char)) {
            return {
                valid: false,
                message: `Invalid character '${char}' in input. Character not in alphabet {${alphabet.join(', ')}}.`
            };
        }
    }

    return { valid: true };
}

// Make error popup function globally available
window.showSimulationErrorPopup = showSimulationErrorPopup;