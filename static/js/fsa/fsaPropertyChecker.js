import { generateTransitionTable } from './transitionTableManager.js';
import { getEpsilonSymbol } from './edgeManager.js';

/**
 * Checks if the FSA is deterministic
 * An FSA is deterministic if:
 * 1. It has no epsilon transitions
 * 2. For each state and each symbol, there is exactly one transition
 * @param {Object} jsPlumbInstance - The JSPlumb instance
 * @returns {boolean} - Whether the FSA is deterministic
 */
export function isDeterministic(jsPlumbInstance) {
    // Get the transition table data
    const tableData = generateTransitionTable(jsPlumbInstance);

    // If there are epsilon transitions, the FSA is not deterministic
    if (tableData.hasEpsilon) {
        return false;
    }


    // For each state and each symbol, check if there is exactly one transition
    for (const stateId of tableData.states) {
        for (const symbol of tableData.alphabet) {
            // Get the transitions for this state and symbol
            const transitions = tableData.transitions[stateId][symbol];

            // If there is not exactly one transition, the FSA is not deterministic
            if (transitions.length > 1) {
                return false;
            }
        }
    }

    // If we get here, the FSA is deterministic
    return true;
}

/**
 * Checks if the FSA is complete
 * An FSA is complete if for each state and each symbol, there is at least one transition
 * @param {Object} jsPlumbInstance - The JSPlumb instance
 * @returns {boolean} - Whether the FSA is complete
 */
export function isComplete(jsPlumbInstance) {
    // Get the transition table data
    const tableData = generateTransitionTable(jsPlumbInstance);

    // Ignore epsilon transitions for completeness check

    // For each state and each symbol, check if there is at least one transition
    for (const stateId of tableData.states) {
        for (const symbol of tableData.alphabet) {
            // Get the transitions for this state and symbol
            const transitions = tableData.transitions[stateId][symbol];

            // If there are no transitions, the FSA is not complete
            if (transitions.length === 0) {
                return false;
            }
        }
    }

    // If we get here, the FSA is complete
    return true;
}

/**
 * Checks if the FSA is connected
 * An FSA is connected if all states are reachable from the starting state
 * @param {Object} jsPlumbInstance - The JSPlumb instance
 * @returns {boolean} - Whether the FSA is connected
 */
export function isConnected(jsPlumbInstance) {
    // Get the transition table data
    const tableData = generateTransitionTable(jsPlumbInstance);

    // If there's no starting state, the FSA can't be connected
    if (!tableData.startingState) {
        return false;
    }

    // If there's only one state, it's trivially connected
    if (tableData.states.length <= 1) {
        return true;
    }

    // Use BFS to find all reachable states from the starting state
    const reachableStates = new Set();
    const queue = [tableData.startingState];
    reachableStates.add(tableData.startingState);

    const epsilon = getEpsilonSymbol();

    while (queue.length > 0) {
        const currentState = queue.shift();

        // Check all possible transitions from this state
        for (const symbol of [...tableData.alphabet, ...(tableData.hasEpsilon ? [epsilon] : [])]) {
            const transitions = tableData.transitions[currentState][symbol];

            for (const nextState of transitions) {
                if (!reachableStates.has(nextState)) {
                    reachableStates.add(nextState);
                    queue.push(nextState);
                }
            }
        }
    }

    // If all states are reachable, the FSA is connected
    return reachableStates.size === tableData.states.length;
}

/**
 * Updates the FSA properties display
 * @param {Object} jsPlumbInstance - The JSPlumb instance
 */
export function updateFSAPropertiesDisplay(jsPlumbInstance) {
    const isDeterministicResult = isDeterministic(jsPlumbInstance);
    const isCompleteResult = isComplete(jsPlumbInstance);
    const isConnectedResult = isConnected(jsPlumbInstance);

    // Update the deterministic property display
    const deterministicDisplay = document.querySelector('.fsa-properties .property:nth-child(2) span:last-child');
    if (deterministicDisplay) {
        deterministicDisplay.textContent = isDeterministicResult ? '✓' : '✗';
        deterministicDisplay.className = isDeterministicResult ? 'checkmark' : 'crossmark';
    }

    // Update the complete property display
    const completeDisplay = document.querySelector('.fsa-properties .property:nth-child(3) span:last-child');
    if (completeDisplay) {
        completeDisplay.textContent = isCompleteResult ? '✓' : '✗';
        completeDisplay.className = isCompleteResult ? 'checkmark' : 'crossmark';
    }

    // Update the connected property display
    const connectedDisplay = document.querySelector('.fsa-properties .property:nth-child(1) span:last-child');
    if (connectedDisplay) {
        connectedDisplay.textContent = isConnectedResult ? '✓' : '✗';
        connectedDisplay.className = isConnectedResult ? 'checkmark' : 'crossmark';
    }
}