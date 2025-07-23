import { generateTransitionTable } from './transitionTableManager.js';
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
            if (targets && targets.length > 0) {
                backendTransitions[stateId][symbol] = targets;
            }
        });
    });

    // Create the FSA object in backend expected format
    // Allow empty/null values for incomplete FSAs
    const fsa = {
        states: tableData.states || [],
        alphabet: tableData.alphabet || [],
        transitions: backendTransitions,
        startingState: tableData.startingState || null,
        acceptingStates: tableData.acceptingStates || []
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
        // Convert to backend format (this won't throw anymore)
        const fsa = convertFSAToBackendFormat(jsPlumbInstance);

        // For simulation, we still need these requirements
        if (!fsa.startingState) {
            return {
                success: false,
                message: 'No starting state defined. Please set a starting state.'
            };
        }

        if (fsa.states.length === 0) {
            return {
                success: false,
                message: 'No states defined. Please create at least one state.'
            };
        }

        if (fsa.alphabet.length === 0) {
            return {
                success: false,
                message: 'No alphabet defined. Please create at least one transition with symbols.'
            };
        }

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
 * Check FSA properties (deterministic, complete, connected) using backend
 * @param {Object} fsa - FSA in backend format
 * @returns {Promise<Object>} - Promise resolving to property check results
 */
export async function checkFSAProperties(fsa) {
    const requestData = { fsa: fsa };

    try {
        console.log('Checking FSA properties:', requestData);

        const response = await fetch('/api/check-fsa-properties/', {
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
        console.log('FSA properties result:', result);

        return result;

    } catch (error) {
        console.error('Error during FSA properties check:', error);
        throw error;
    }
}

/**
 * Check if FSA is deterministic using backend
 * @param {Object} fsa - FSA in backend format
 * @returns {Promise<Object>} - Promise resolving to determinism check result
 */
export async function checkFSADeterministic(fsa) {
    const requestData = { fsa: fsa };

    try {
        console.log('Checking FSA determinism:', requestData);

        const response = await fetch('/api/check-deterministic/', {
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
        console.log('FSA determinism result:', result);

        return result;

    } catch (error) {
        console.error('Error during FSA determinism check:', error);
        throw error;
    }
}

/**
 * Check if FSA is complete using backend
 * @param {Object} fsa - FSA in backend format
 * @returns {Promise<Object>} - Promise resolving to completeness check result
 */
export async function checkFSAComplete(fsa) {
    const requestData = { fsa: fsa };

    try {
        console.log('Checking FSA completeness:', requestData);

        const response = await fetch('/api/check-complete/', {
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
        console.log('FSA completeness result:', result);

        return result;

    } catch (error) {
        console.error('Error during FSA completeness check:', error);
        throw error;
    }
}

/**
 * Check if FSA is connected using backend
 * @param {Object} fsa - FSA in backend format
 * @returns {Promise<Object>} - Promise resolving to connectivity check result
 */
export async function checkFSAConnected(fsa) {
    const requestData = { fsa: fsa };

    try {
        console.log('Checking FSA connectivity:', requestData);

        const response = await fetch('/api/check-connected/', {
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
        console.log('FSA connectivity result:', result);

        return result;

    } catch (error) {
        console.error('Error during FSA connectivity check:', error);
        throw error;
    }
}

/**
 * Check for epsilon loops in an FSA
 * @param {Object} fsa - FSA in backend format
 * @returns {Promise<Object>} - Promise resolving to epsilon loop detection result
 */
export async function checkEpsilonLoops(fsa) {
    const requestData = { fsa: fsa };

    try {
        console.log('Checking for epsilon loops:', requestData);

        const response = await fetch('/api/check-epsilon-loops/', {
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
        console.log('Epsilon loops detection result:', result);

        return result;

    } catch (error) {
        console.error('Error during epsilon loops detection:', error);
        throw error;
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

        console.log('Received NFA streaming response:', response.status, response.statusText);
        return response; // Return the streaming response

    } catch (error) {
        console.error('Error during NFA streaming simulation:', error);
        throw error;
    }
}

/**
 * Sends FSA and input string to backend for streaming NFA simulation with depth limit
 * @param {Object} fsa - FSA in backend format
 * @param {string} inputString - Input string to simulate
 * @param {number} maxDepth - Maximum epsilon transition depth
 * @returns {Promise<Object>} - Promise resolving to streaming response
 */
export async function simulateNFAStreamWithDepthLimitOnBackend(fsa, inputString, maxDepth) {
    const requestData = {
        fsa: fsa,
        input: inputString,
        max_depth: maxDepth
    };

    try {
        console.log('Sending NFA depth-limited streaming simulation request:', requestData);

        const response = await fetch('/api/simulate-nfa-stream-depth-limit/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(requestData)
        });

        console.log('Received NFA depth-limited streaming response:', response.status, response.statusText);
        return response; // Return the streaming response

    } catch (error) {
        console.error('Error during NFA depth-limited streaming simulation:', error);
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

        // Check if FSA is deterministic or non-deterministic using backend
        const determinismResult = await checkFSADeterministic(validation.fsa);
        const isDFA = determinismResult.deterministic;

        if (isDFA) {
            // Handle DFA simulation (existing logic)
            return await runDFASimulation(jsPlumbInstance, inputString, visualMode, validation.fsa);
        } else {
            // Handle NFA simulation with epsilon loop detection
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
    // Initialise visual simulation manager with JSPlumb instance
    if (visualMode) {
        visualSimulationManager.initialise(jsPlumbInstance);
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
 * Run NFA simulation with epsilon loop detection
 * @param {Object} jsPlumbInstance - The JSPlumb instance
 * @param {string} inputString - Input string to simulate
 * @param {boolean} visualMode - Whether to show visual animation
 * @param {Object} fsa - FSA in backend format
 * @returns {Promise<Object>} - Promise resolving to simulation result
 */
async function runNFASimulation(jsPlumbInstance, inputString, visualMode, fsa) {
    try {
        // For fast-forward mode, always skip epsilon loops detection
        if (!visualMode) {
            console.log('Fast-forward mode: skipping epsilon loops detection');
            return await executeNFASimulationWithOptions(
                jsPlumbInstance,
                inputString,
                visualMode,
                fsa,
                { action: 'ignore' }
            );
        }

        // For visual mode, perform epsilon loops detection as usual
        const epsilonLoopsResult = await checkEpsilonLoops(fsa);

        if (epsilonLoopsResult.has_epsilon_loops && epsilonLoopsResult.summary.has_reachable_loops) {
            console.log('Detected reachable epsilon loops, showing options popup');

            // Show epsilon loops popup and wait for user decision
            const userDecision = await notificationManager.showEpsilonLoopsPopup(epsilonLoopsResult, fsa, inputString);

            if (userDecision.action === 'cancel') {
                return {
                    success: false,
                    message: 'Simulation cancelled by user',
                    type: 'user_cancelled',
                    isVisual: true
                };
            }

            // Proceed with simulation based on user choice
            return await executeNFASimulationWithOptions(
                jsPlumbInstance,
                inputString,
                visualMode,
                fsa,
                userDecision
            );
        } else {
            // No problematic epsilon loops, proceed normally
            console.log('No reachable epsilon loops detected, proceeding with normal NFA simulation');
            return await executeNFASimulationWithOptions(
                jsPlumbInstance,
                inputString,
                visualMode,
                fsa,
                { action: 'ignore' }
            );
        }

    } catch (error) {
        console.error('Error during epsilon loops detection:', error);

        // If epsilon loop detection fails, proceed with normal simulation but warn user
        console.warn('Epsilon loop detection failed, proceeding with normal simulation');
        return await executeNFASimulationWithOptions(
            jsPlumbInstance,
            inputString,
            visualMode,
            fsa,
            { action: 'ignore' }
        );
    }
}

/**
 * Execute NFA simulation with the given options (depth limit or ignore loops)
 * @param {Object} jsPlumbInstance - The JSPlumb instance
 * @param {string} inputString - Input string to simulate
 * @param {boolean} visualMode - Whether to show visual animation
 * @param {Object} fsa - FSA in backend format
 * @param {Object} options - User decision options
 * @returns {Promise<Object>} - Promise resolving to simulation result
 */
async function executeNFASimulationWithOptions(jsPlumbInstance, inputString, visualMode, fsa, options) {
    if (visualMode) {
        // For visual mode, show NFA results popup with streaming data
        if (options.action === 'depth_limit') {
            await nfaResultsManager.showNFAResultsPopupWithDepthLimit(
                fsa,
                inputString,
                jsPlumbInstance,
                options.maxDepth
            );
        } else {
            await nfaResultsManager.showNFAResultsPopup(fsa, inputString, jsPlumbInstance);
        }

        return {
            success: true,
            message: '',
            type: 'nfa_visual_simulation',
            isVisual: true
        };
    } else {
        // For fast-forward mode, get first accepting path quickly
        try {
            let streamResponse;

            if (options.action === 'depth_limit') {
                streamResponse = await simulateNFAStreamWithDepthLimitOnBackend(fsa, inputString, options.maxDepth);
            } else {
                streamResponse = await simulateNFAStreamOnBackend(fsa, inputString);
            }

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