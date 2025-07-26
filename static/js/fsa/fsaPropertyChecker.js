import {
    convertFSAToBackendFormat,
    checkFSAProperties,
    checkFSADeterministic,
    checkFSAComplete,
    checkFSAConnected
} from './backendIntegration.js';

/**
 * Property states for consistent UI updates
 */
const PROPERTY_STATES = {
    TRUE: {
        html: '<img src="static/img/success.png" alt="✓" class="property-icon success-icon">',
        className: 'checkmark'
    },
    FALSE: {
        html: '<img src="static/img/error.png" alt="✗" class="property-icon error-icon">',
        className: 'crossmark'
    },
    ERROR: {
        html: '<img src="static/img/error.png" alt="?" class="property-icon error-icon">',
        className: 'error'
    }
};

/**
 * Property manager class for robust property updates
 */
class FSAPropertyManager {
    constructor() {
        this.isUpdating = false;
        this.pendingUpdate = false;
        this.lastUpdateTime = 0;
        this.debounceTime = 100; // Prevent rapid successive updates
    }

    /**
     * Update a specific property value in the UI
     * @param {string} propertyName - Name of the property (connected, deterministic, complete)
     * @param {boolean|null} value - Property value (true/false/null for error)
     */
    updatePropertyValue(propertyName, value) {
        const element = document.querySelector(`[data-property-value="${propertyName}"]`);

        if (!element) {
            console.error(`Property element not found for: ${propertyName}`);
            return false;
        }

        let state;
        if (value === null || value === undefined) {
            state = PROPERTY_STATES.ERROR;
        } else if (value === true) {
            state = PROPERTY_STATES.TRUE;
        } else if (value === false) {
            state = PROPERTY_STATES.FALSE;
        } else {
            console.error(`Invalid property value for ${propertyName}:`, value);
            state = PROPERTY_STATES.ERROR;
        }

        // Update the element
        element.innerHTML = state.html;
        element.className = `property-value ${state.className}`;

        // Also set data attribute for potential CSS styling
        element.setAttribute('data-property-state', value === true ? 'true' : value === false ? 'false' : 'error');

        console.log(`Updated property ${propertyName}: ${value} (${state.html})`);
        return true;
    }



    /**
     * Update all properties to error state
     */
    setAllPropertiesError() {
        const properties = ['connected', 'deterministic', 'complete'];
        properties.forEach(prop => {
            this.updatePropertyValue(prop, null);
        });
    }

    /**
     * Update all properties with given values
     * @param {Object} properties - Object with property values
     */
    updateAllProperties(properties) {
        if (!properties || typeof properties !== 'object') {
            console.error('Invalid properties object:', properties);
            this.setAllPropertiesError();
            return false;
        }

        // Update each property individually
        const results = {
            connected: this.updatePropertyValue('connected', properties.connected),
            deterministic: this.updatePropertyValue('deterministic', properties.deterministic),
            complete: this.updatePropertyValue('complete', properties.complete)
        };

        // Log the results
        const successful = Object.values(results).every(result => result === true);
        if (successful) {
            console.log('All properties updated successfully:', properties);
        } else {
            console.warn('Some properties failed to update:', results);
        }

        return successful;
    }

    /**
     * Get current property values from the UI
     * @returns {Object} - Current property values
     */
    getCurrentPropertyValues() {
        const properties = {};

        ['connected', 'deterministic', 'complete'].forEach(prop => {
            const element = document.querySelector(`[data-property-value="${prop}"]`);
            if (element) {
                const state = element.getAttribute('data-property-state');
                properties[prop] = state === 'true' ? true : state === 'false' ? false : null;
            } else {
                properties[prop] = null;
            }
        });

        return properties;
    }

    /**
     * Check if properties are currently being updated
     */
    isCurrentlyUpdating() {
        return this.isUpdating;
    }
}

// Create singleton instance
const propertyManager = new FSAPropertyManager();

/**
 * Updates the FSA properties display using backend property checks
 * @param {Object} jsPlumbInstance - The JSPlumb instance
 * @param {boolean} force - Force update even if currently updating
 * @returns {Promise<boolean>} - Success status
 */
export async function updateFSAPropertiesDisplay(jsPlumbInstance, force = false) {
    // Prevent rapid successive updates unless forced
    const now = Date.now();
    if (!force && propertyManager.isUpdating) {
        propertyManager.pendingUpdate = true;
        console.log('Property update already in progress, marking as pending');
        return false;
    }

    if (!force && (now - propertyManager.lastUpdateTime) < propertyManager.debounceTime) {
        console.log('Property update debounced');
        return false;
    }

    propertyManager.isUpdating = true;
    propertyManager.pendingUpdate = false;
    propertyManager.lastUpdateTime = now;

    try {
        // Convert FSA to backend format
        const fsa = convertFSAToBackendFormat(jsPlumbInstance);

        if (!fsa) {
            console.error('Failed to convert FSA to backend format');
            propertyManager.setAllPropertiesError();
            return false;
        }

        // Check all properties at once
        const propertiesResult = await checkFSAProperties(fsa);

        if (!propertiesResult || !propertiesResult.properties) {
            console.error('Invalid properties result from backend:', propertiesResult);
            propertyManager.setAllPropertiesError();
            return false;
        }

        const properties = propertiesResult.properties;

        // Validate that we have all required properties
        const requiredProps = ['connected', 'deterministic', 'complete'];
        const missingProps = requiredProps.filter(prop => !(prop in properties));

        if (missingProps.length > 0) {
            console.error('Missing required properties from backend:', missingProps);
            propertyManager.setAllPropertiesError();
            return false;
        }

        // Update all properties directly to final values
        const success = propertyManager.updateAllProperties(properties);

        console.log('FSA properties update completed:', {
            success,
            properties,
            timestamp: new Date().toISOString()
        });

        return success;

    } catch (error) {
        console.error('Error updating FSA properties display:', error);
        propertyManager.setAllPropertiesError();
        return false;
    } finally {
        propertyManager.isUpdating = false;

        // Handle any pending updates
        if (propertyManager.pendingUpdate) {
            console.log('Executing pending property update');
            setTimeout(() => {
                if (propertyManager.pendingUpdate) {
                    updateFSAPropertiesDisplay(jsPlumbInstance, true);
                }
            }, 50);
        }
    }
}

/**
 * Force an immediate property update (bypasses debouncing)
 * @param {Object} jsPlumbInstance - The JSPlumb instance
 * @returns {Promise<boolean>} - Success status
 */
export async function forceUpdateFSAPropertiesDisplay(jsPlumbInstance) {
    return updateFSAPropertiesDisplay(jsPlumbInstance, true);
}

/**
 * Set properties to a specific state (for testing or manual control)
 * @param {Object} properties - Property values to set
 */
export function setFSAProperties(properties) {
    return propertyManager.updateAllProperties(properties);
}

/**
 * Reset all properties to default state
 */
export function resetFSAProperties() {
    return propertyManager.updateAllProperties({
        connected: true,
        deterministic: true,
        complete: true
    });
}

/**
 * Get current property values from UI
 * @returns {Object} - Current property values
 */
export function getCurrentFSAProperties() {
    return propertyManager.getCurrentPropertyValues();
}

/**
 * Check if FSA is deterministic using backend
 * @param {Object} jsPlumbInstance - The JSPlumb instance
 * @returns {Promise<boolean>} - Whether the FSA is deterministic
 */
export async function isDeterministic(jsPlumbInstance) {
    try {
        const fsa = convertFSAToBackendFormat(jsPlumbInstance);
        if (!fsa) return false;

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
        if (!fsa) return false;

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
        if (!fsa) return false;

        const result = await checkFSAConnected(fsa);
        return result.connected;
    } catch (error) {
        console.error('Error checking connectivity via backend:', error);
        return false; // Default to disconnected on error
    }
}

// Export the property manager for advanced usage
export { propertyManager };

// Make the update function globally available
window.updateFSAPropertiesDisplay = updateFSAPropertiesDisplay;
window.forceUpdateFSAPropertiesDisplay = forceUpdateFSAPropertiesDisplay;
window.propertyManager = propertyManager;