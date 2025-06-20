import {
    convertFSAToBackendFormat,
    checkFSAProperties,
    checkFSADeterministic,
    checkFSAComplete,
    checkFSAConnected
} from './backendIntegration.js';

/**
 * Updates the FSA properties display using backend property checks
 * @param {Object} jsPlumbInstance - The JSPlumb instance
 */
export async function updateFSAPropertiesDisplay(jsPlumbInstance) {
    try {
        // Convert FSA to backend format
        const fsa = convertFSAToBackendFormat(jsPlumbInstance);

        // Check all properties at once
        const propertiesResult = await checkFSAProperties(fsa);
        const properties = propertiesResult.properties;

        // Update the deterministic property display
        const deterministicDisplay = document.querySelector('.fsa-properties .property:nth-child(2) span:last-child');
        if (deterministicDisplay) {
            deterministicDisplay.textContent = properties.deterministic ? '✓' : '✗';
            deterministicDisplay.className = properties.deterministic ? 'checkmark' : 'crossmark';
        }

        // Update the complete property display
        const completeDisplay = document.querySelector('.fsa-properties .property:nth-child(3) span:last-child');
        if (completeDisplay) {
            completeDisplay.textContent = properties.complete ? '✓' : '✗';
            completeDisplay.className = properties.complete ? 'checkmark' : 'crossmark';
        }

        // Update the connected property display
        const connectedDisplay = document.querySelector('.fsa-properties .property:nth-child(1) span:last-child');
        if (connectedDisplay) {
            connectedDisplay.textContent = properties.connected ? '✓' : '✗';
            connectedDisplay.className = properties.connected ? 'checkmark' : 'crossmark';
        }

        console.log('Updated FSA properties display:', properties);

    } catch (error) {
        console.error('Error updating FSA properties display:', error);

        // Fallback: show error indicators
        const displays = document.querySelectorAll('.fsa-properties .property span:last-child');
        displays.forEach(display => {
            display.textContent = '?';
            display.className = 'error';
        });
    }
}

/**
 * Check if FSA is deterministic using backend
 * @param {Object} jsPlumbInstance - The JSPlumb instance
 * @returns {Promise<boolean>} - Whether the FSA is deterministic
 */
export async function isDeterministic(jsPlumbInstance) {
    try {
        const fsa = convertFSAToBackendFormat(jsPlumbInstance);
        const result = await checkFSADeterministic(fsa);
        return result.deterministic;
    } catch (error) {
        console.error('Error checking determinism via backend:', error);
        return false; // Default to non-deterministic on error
    }
}

/**
 * Check if FSA is complete using backend
 * @param {Object} jsPlumbInstance - The JSPlumb instance
 * @returns {Promise<boolean>} - Whether the FSA is complete
 */
export async function isComplete(jsPlumbInstance) {
    try {
        const fsa = convertFSAToBackendFormat(jsPlumbInstance);
        const result = await checkFSAComplete(fsa);
        return result.complete;
    } catch (error) {
        console.error('Error checking completeness via backend:', error);
        return false; // Default to incomplete on error
    }
}

/**
 * Check if FSA is connected using backend
 * @param {Object} jsPlumbInstance - The JSPlumb instance
 * @returns {Promise<boolean>} - Whether the FSA is connected
 */
export async function isConnected(jsPlumbInstance) {
    try {
        const fsa = convertFSAToBackendFormat(jsPlumbInstance);
        const result = await checkFSAConnected(fsa);
        return result.connected;
    } catch (error) {
        console.error('Error checking connectivity via backend:', error);
        return false; // Default to disconnected on error
    }
}

// Make the update function globally available
window.updateFSAPropertiesDisplay = updateFSAPropertiesDisplay;