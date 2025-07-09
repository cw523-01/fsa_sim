import { updateAlphabetDisplay } from './alphabetManager.js';
import { updateFSAPropertiesDisplay } from './fsaPropertyChecker.js';
import { getEdgeSymbolMap, getEpsilonTransitionMap } from './edgeManager.js';
import { nfaResultsManager } from './nfaResultsManager.js';

/**
 * FSA update utility functions
 */

/**
 * Perform all standard updates after FSA structure changes
 * @param {Object} jsPlumbInstance - The JSPlumb instance
 */
export function updateFSADisplays(jsPlumbInstance) {
    // Update alphabet display
    updateAlphabetDisplay(getEdgeSymbolMap(), getEpsilonTransitionMap());

    // Update FSA properties display
    updateFSAPropertiesDisplay(jsPlumbInstance);

    // Clear stored NFA results since FSA structure changed
    if (nfaResultsManager) {
        nfaResultsManager.clearStoredPaths();
    }
}

/**
 * Perform updates after edge-related changes (includes repaint)
 * @param {Object} jsPlumbInstance - The JSPlumb instance
 */
export function updateFSADisplaysWithRepaint(jsPlumbInstance) {
    updateFSADisplays(jsPlumbInstance);

    // Force repaint for visual consistency
    if (jsPlumbInstance) {
        jsPlumbInstance.repaintEverything();
    }
}