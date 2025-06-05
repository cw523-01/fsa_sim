import { generateTransitionTable } from './transitionTableManager.js';
import { isDeterministic, isConnected } from './fsaPropertyChecker.js';
import { getStartingStateId } from './stateManager.js';
import { visualSimulationManager } from './visualSimulationManager.js';
import { nfaResultsManager } from './nfaResultsManager.js';
import { notificationManager } from './notificationManager.js';

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

    // Convert transitions to the backend expected format
    const backendTransitions = {};

    tableData.states.forEach(stateId => {
        backendTransitions[stateId] = {};

        // Include epsilon transitions if they exist
        const allSymbols = [...tableData.alphabet];
        if (tableData.hasEpsilon) {
            allSymbols.push(''); // Empty string for epsilon
        }

        allSymbols.forEach(symbol => {
            const targets = tableData.transitions[stateId][symbol];
            // For backend format, we need an array of target states
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
 * Sends FSA and input string to backend for streaming NFA simulation
 * @param {Object} fsa - FSA in backend format
 * @param {string} inputString - Input string to simulate
 * @returns {Promise<Object>} - Promise resolving to streaming response
 */
export async function simulateNFAStreamOnBackend(fsa, inputString) {
    const requestData = {
        fsa: fsa,
        input: inputString
    };

    try {
        console.log('Sending NFA streaming simulation request:', requestData);

        const response = await fetch('/api/simulate-nfa-stream/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(requestData)
        });

        // Don't throw for HTTP errors here, let the streaming handler deal with them
        // The response might have error data in the stream even if status is not 200

        console.log('Received NFA streaming response:', response.status, response.statusText);
        return response; // Return the streaming response

    } catch (error) {
        console.error('Error during NFA streaming simulation:', error);
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
    // Use the notification manager's simulation popup system
    notificationManager.showSimulationResultPopup(result, inputString, isFastForward, result.path);
}

/**
 * Show error popup for validation or simulation errors
 * @param {string} errorMessage - The error message to display
 * @param {string} inputString - The input string (if any)
 */
export function showSimulationErrorPopup(errorMessage, inputString = '') {
    // Use the notification manager's error popup system
    notificationManager.showSimulationErrorPopup(errorMessage, inputString);
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

        // Check if FSA is deterministic or non-deterministic
        const isDFA = isDeterministic(jsPlumbInstance);

        if (isDFA) {
            // Handle DFA simulation (existing logic)
            return await runDFASimulation(jsPlumbInstance, inputString, visualMode, validation.fsa);
        } else {
            // Handle NFA simulation
            return await runNFASimulation(jsPlumbInstance, inputString, visualMode, validation.fsa);
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
 * Run DFA simulation (existing logic)
 * @param {Object} jsPlumbInstance - The JSPlumb instance
 * @param {string} inputString - Input string to simulate
 * @param {boolean} visualMode - Whether to show visual animation
 * @param {Object} fsa - FSA in backend format
 * @returns {Promise<Object>} - Promise resolving to simulation result
 */
async function runDFASimulation(jsPlumbInstance, inputString, visualMode, fsa) {
    // Initialize visual simulation manager with JSPlumb instance
    if (visualMode) {
        visualSimulationManager.initialize(jsPlumbInstance);
    }

    // Simulate on backend
    const result = await simulateFSAOnBackend(fsa, inputString);

    if (visualMode) {
        // Always start visual simulation in visual mode (handles both empty and non-empty strings)
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
        // Fast-forward mode - show popup instead of alert
        showSimulationResultPopup(result, inputString, true);
        return {
            success: true,
            message: '', // Empty since popup handles display
            rawResult: result,
            type: 'fast_forward_simulation',
            isVisual: true // Set to true since we're using popup
        };
    }
}

/**
 * Run NFA simulation
 * @param {Object} jsPlumbInstance - The JSPlumb instance
 * @param {string} inputString - Input string to simulate
 * @param {boolean} visualMode - Whether to show visual animation
 * @param {Object} fsa - FSA in backend format
 * @returns {Promise<Object>} - Promise resolving to simulation result
 */
async function runNFASimulation(jsPlumbInstance, inputString, visualMode, fsa) {
    if (visualMode) {
        // For visual mode, show NFA results popup with streaming data
        await nfaResultsManager.showNFAResultsPopup(fsa, inputString, jsPlumbInstance);

        return {
            success: true,
            message: '',
            type: 'nfa_visual_simulation',
            isVisual: true
        };
    } else {
        // For fast-forward mode, try to get first accepting path quickly
        try {
            const streamResponse = await simulateNFAStreamOnBackend(fsa, inputString);
            const reader = streamResponse.body.getReader();
            const decoder = new TextDecoder();

            let firstAcceptingPath = null;
            let hasResults = false;

            while (true) {
                const { done, value } = await reader.read();

                if (done) break;

                const chunk = decoder.decode(value, { stream: true });
                const lines = chunk.split('\n');

                for (const line of lines) {
                    if (line.startsWith('data: ')) {
                        try {
                            const data = JSON.parse(line.slice(6));
                            hasResults = true;

                            if (data.type === 'accepting_path' && !firstAcceptingPath) {
                                firstAcceptingPath = data.path;
                                // Close the reader early since we found what we need
                                reader.cancel();

                                // Show result popup with the first accepting path
                                const simulationResult = {
                                    accepted: true,
                                    path: firstAcceptingPath
                                };

                                showSimulationResultPopup(simulationResult, inputString, true);

                                return {
                                    success: true,
                                    message: '',
                                    type: 'nfa_fast_forward_simulation',
                                    isVisual: true
                                };
                            }

                            if (data.type === 'summary') {
                                // If we reach the summary and haven't found accepting paths
                                if (data.total_accepting_paths === 0) {
                                    // Show rejection result
                                    const simulationResult = {
                                        accepted: false,
                                        path: []
                                    };

                                    showSimulationResultPopup(simulationResult, inputString, true);

                                    return {
                                        success: true,
                                        message: '',
                                        type: 'nfa_fast_forward_simulation',
                                        isVisual: true
                                    };
                                }
                                break;
                            }
                        } catch (parseError) {
                            console.error('Error parsing streaming data:', parseError);
                        }
                    }
                }
            }

            // If we get here without finding results, show error
            if (!hasResults) {
                showSimulationErrorPopup('No simulation results received from server', inputString);
            }

            return {
                success: hasResults,
                message: hasResults ? '' : 'No results received',
                type: 'nfa_fast_forward_simulation',
                isVisual: true
            };

        } catch (error) {
            console.error('Error during NFA fast-forward simulation:', error);
            showSimulationErrorPopup(`Error during NFA simulation:\n${error.message}`, inputString);

            return {
                success: false,
                message: '',
                type: 'nfa_backend_error',
                isVisual: true
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

    // Also stop NFA results manager if it's running
    if (typeof nfaResultsManager !== 'undefined' && nfaResultsManager.stopStreaming) {
        nfaResultsManager.stopStreaming();
    }
}

/**
 * Check if visual simulation is currently running
 * @returns {boolean} - Whether visual simulation is running
 */
export function isVisualSimulationRunning() {
    const visualRunning = visualSimulationManager.isSimulationRunning();
    const nfaRunning = (typeof nfaResultsManager !== 'undefined' &&
                       nfaResultsManager.isStreamingActive &&
                       nfaResultsManager.isStreamingActive());

    return visualRunning || nfaRunning;
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

// Make error popup function globally available (now uses notification manager)
window.showSimulationErrorPopup = showSimulationErrorPopup;