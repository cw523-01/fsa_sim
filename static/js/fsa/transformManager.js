import { fsaSerializationManager } from './fsaSerializationManager.js';
import { notificationManager } from './notificationManager.js';
import { controlLockManager } from './controlLockManager.js';
import { undoRedoManager } from './undoRedoManager.js';
import {
    convertFSAToBackendFormat,
    checkFSAProperties
} from './backendIntegration.js';
import { updateFSAPropertiesDisplay } from './fsaPropertyChecker.js';

/**
 * FSA Transform Manager - handles FSA transformation operations
 */
class FSATransformManager {
    constructor() {
        this.jsPlumbInstance = null;
        this.eventListenersSetup = false;
        this.currentFSAForMinimization = null;
        this.currentFSAForConversion = null;
    }

    /**
     * Initialize with JSPlumb instance
     * @param {Object} jsPlumbInstance - The JSPlumb instance
     */
    initialize(jsPlumbInstance) {
        this.jsPlumbInstance = jsPlumbInstance;
        this.setupTransformEventListeners();
        this.setupKeyboardShortcuts();
    }

    /**
     * Setup Transform menu event listeners
     */
    setupTransformEventListeners() {
        if (this.eventListenersSetup) {
            return;
        }
        this.eventListenersSetup = true;

        // Transform menu button
        const transformMenuButton = document.getElementById('transform-menu-button');
        if (transformMenuButton) {
            transformMenuButton.addEventListener('click', (e) => {
                e.stopPropagation();
                this.toggleTransformMenu();
            });
        }

        // Menu options
        const menuMinimiseDFA = document.getElementById('menu-minimise-dfa');
        if (menuMinimiseDFA) {
            menuMinimiseDFA.addEventListener('click', () => {
                this.closeTransformMenu();
                this.minimiseDFA();
            });
        }

        const menuNFAToDFA = document.getElementById('menu-nfa-to-dfa');
        if (menuNFAToDFA) {
            menuNFAToDFA.addEventListener('click', () => {
                this.closeTransformMenu();
                this.convertNFAToDFA();
            });
        }

        // Close menus when clicking outside (integrate with existing system)
        document.addEventListener('click', (e) => {
            if (!e.target.closest('#transform-menu')) {
                this.closeTransformMenu();
            }
        });
    }

    /**
     * Setup keyboard shortcuts for transform operations
     */
    setupKeyboardShortcuts() {
        document.addEventListener('keydown', (e) => {
            // Don't trigger if controls are locked or if typing in an input
            if (controlLockManager.isControlsLocked() ||
                e.target.tagName === 'INPUT' ||
                e.target.tagName === 'TEXTAREA') {
                return;
            }

            // Ctrl+M or Cmd+M - Minimise DFA
            if ((e.ctrlKey || e.metaKey) && e.key === 'm') {
                e.preventDefault();
                this.minimiseDFA();
            }

            // Ctrl+D or Cmd+D - Convert NFA to DFA
            if ((e.ctrlKey || e.metaKey) && e.key === 'd') {
                e.preventDefault();
                this.convertNFAToDFA();
            }
        });
    }

    /**
     * Toggle Transform menu dropdown
     */
    toggleTransformMenu() {
        const dropdown = document.getElementById('transform-dropdown');
        const button = document.getElementById('transform-menu-button');

        if (!dropdown || !button) return;

        const isOpen = dropdown.classList.contains('show');

        if (isOpen) {
            this.closeTransformMenu();
        } else {
            this.openTransformMenu();
        }
    }

    /**
     * Open Transform menu
     */
    openTransformMenu() {
        const dropdown = document.getElementById('transform-dropdown');
        const button = document.getElementById('transform-menu-button');

        if (!dropdown || !button) return;

        dropdown.classList.add('show');
        button.classList.add('active');
    }

    /**
     * Close Transform menu
     */
    closeTransformMenu() {
        const dropdown = document.getElementById('transform-dropdown');
        const button = document.getElementById('transform-menu-button');

        if (!dropdown || !button) return;

        dropdown.classList.remove('show');
        button.classList.remove('active');
    }

    /**
     * Minimise DFA - main function
     */
    async minimiseDFA() {
        if (!this.jsPlumbInstance) {
            notificationManager.showError('Minimization Error', 'FSA not initialized');
            return;
        }

        if (controlLockManager.isControlsLocked()) {
            notificationManager.showWarning('Cannot Minimize', 'Cannot minimize while simulation is running');
            return;
        }

        // Check if there's an FSA to minimize
        const states = document.querySelectorAll('.state, .accepting-state');
        if (states.length === 0) {
            notificationManager.showWarning('Nothing to Minimize', 'Create an FSA before minimizing');
            return;
        }

        // Step 1: Validate FSA properties
        try {
            const fsa = convertFSAToBackendFormat(this.jsPlumbInstance);
            const propertiesResult = await checkFSAProperties(fsa);
            const properties = propertiesResult.properties;

            // Check if FSA is deterministic
            if (!properties.deterministic) {
                notificationManager.showError(
                    'Cannot Minimize',
                    'DFA minimization requires a deterministic automaton. The current FSA is non-deterministic (NFA).'
                );
                return;
            }

            // Check if FSA is connected
            if (!properties.connected) {
                notificationManager.showError(
                    'Cannot Minimize',
                    'DFA minimization requires a connected automaton. Some states are unreachable from the starting state.'
                );
                return;
            }

            // Show confirmation popup
            this.showMinimizeConfirmPopup(fsa, propertiesResult.summary);

        } catch (error) {
            console.error('Error validating FSA for minimization:', error);
            notificationManager.showError(
                'Validation Error',
                `Failed to validate FSA: ${error.message}`
            );
        }
    }

    /**
     * Convert NFA to DFA - main function
     */
    async convertNFAToDFA() {
        if (!this.jsPlumbInstance) {
            notificationManager.showError('Conversion Error', 'FSA not initialized');
            return;
        }

        if (controlLockManager.isControlsLocked()) {
            notificationManager.showWarning('Cannot Convert', 'Cannot convert while simulation is running');
            return;
        }

        // Check if there's an FSA to convert
        const states = document.querySelectorAll('.state, .accepting-state');
        if (states.length === 0) {
            notificationManager.showWarning('Nothing to Convert', 'Create an FSA before converting');
            return;
        }

        // Step 1: Validate FSA properties
        try {
            const fsa = convertFSAToBackendFormat(this.jsPlumbInstance);
            const propertiesResult = await checkFSAProperties(fsa);
            const properties = propertiesResult.properties;

            // Check if FSA is connected
            if (!properties.connected) {
                notificationManager.showError(
                    'Cannot Convert',
                    'NFA to DFA conversion requires a connected automaton. Some states are unreachable from the starting state.'
                );
                return;
            }

            // Show confirmation popup
            this.showConvertConfirmPopup(fsa, propertiesResult.summary, properties);

        } catch (error) {
            console.error('Error validating FSA for conversion:', error);
            notificationManager.showError(
                'Validation Error',
                `Failed to validate FSA: ${error.message}`
            );
        }
    }

    /**
     * Show confirmation popup for DFA minimization
     * @param {Object} fsa - The FSA to minimize
     * @param {Object} summary - FSA summary information
     */
    showMinimizeConfirmPopup(fsa, summary) {
        // Remove any existing popup
        const existingPopup = document.getElementById('transform-operation-popup');
        if (existingPopup) {
            existingPopup.remove();
        }

        // Create popup element
        const popup = document.createElement('div');
        popup.id = 'transform-operation-popup';
        popup.className = 'file-operation-popup minimize';

        popup.innerHTML = `
            <div class="popup-header">
                <div class="popup-title">
                    <div class="popup-icon">
                        <img src="static/img/alert.png" alt="Warning" style="width: 20px; height: 20px;">
                    </div>
                    <span>Minimize DFA</span>
                </div>
                <button class="popup-close" onclick="fsaTransformManager.hideMinimizePopup()">×</button>
            </div>
            <div class="file-operation-content">
                <div class="file-operation-description">
                    Minimizing the DFA will replace the current automaton with an equivalent minimal DFA.
                </div>
                
                <div class="states-info">
                    Current DFA: <span class="states-count">${summary.total_states} states</span> and <span class="states-count">${this.getTransitionCount()} transitions</span>
                </div>

                <div class="warning-section">
                    <span class="warning-icon">⚠️</span>
                    <div class="warning-text">
                        <strong>Warning:</strong> This operation will permanently replace the current DFA with its minimal equivalent. 
                        The minimized DFA will have the same behavior but potentially fewer states. Consider exporting your current DFA first if you want to save it.
                    </div>
                </div>
            </div>
            <div class="file-operation-actions">
                <button class="file-action-btn cancel" onclick="fsaTransformManager.hideMinimizePopup()">
                    Cancel
                </button>
                <button class="file-action-btn primary" id="minimize-confirm-btn" onclick="fsaTransformManager.confirmMinimize()">
                    Minimize DFA
                </button>
            </div>
        `;

        // Store FSA data for later use
        this.currentFSAForMinimization = fsa;

        // Add popup to canvas
        const canvas = document.getElementById('fsa-canvas');
        if (canvas) {
            canvas.appendChild(popup);

            // Trigger show animation
            setTimeout(() => {
                popup.classList.add('show');
            }, 100);
        }
    }

    /**
     * Show confirmation popup for NFA to DFA conversion
     * @param {Object} fsa - The FSA to convert
     * @param {Object} summary - FSA summary information
     * @param {Object} properties - FSA properties
     */
    showConvertConfirmPopup(fsa, summary, properties) {
        // Remove any existing popup
        const existingPopup = document.getElementById('transform-operation-popup');
        if (existingPopup) {
            existingPopup.remove();
        }

        // Determine current FSA type and appropriate messaging
        const isDeterministic = properties.deterministic;
        const hasEpsilonTransitions = summary.has_epsilon_transitions;

        let currentTypeDescription;
        let conversionDescription;

        if (isDeterministic && !hasEpsilonTransitions) {
            currentTypeDescription = 'DFA (already deterministic)';
            conversionDescription = 'The conversion will ensure the automaton is in proper DFA format.';
        } else if (isDeterministic && hasEpsilonTransitions) {
            currentTypeDescription = 'Deterministic automaton with ε-transitions';
            conversionDescription = 'The conversion will remove epsilon transitions while maintaining determinism.';
        } else {
            currentTypeDescription = 'NFA (non-deterministic)';
            conversionDescription = 'The conversion will create an equivalent deterministic automaton (DFA) using subset construction.';
        }

        // Create popup element
        const popup = document.createElement('div');
        popup.id = 'transform-operation-popup';
        popup.className = 'file-operation-popup convert';

        popup.innerHTML = `
            <div class="popup-header">
                <div class="popup-title">
                    <div class="popup-icon">
                        <img src="static/img/alert.png" alt="Warning" style="width: 20px; height: 20px;">
                    </div>
                    <span>Convert to DFA</span>
                </div>
                <button class="popup-close" onclick="fsaTransformManager.hideConvertPopup()">×</button>
            </div>
            <div class="file-operation-content">
                <div class="file-operation-description">
                    ${conversionDescription}
                </div>
                
                <div class="states-info">
                    Current FSA: <span class="states-count">${currentTypeDescription}</span><br>
                    <span class="states-count">${summary.total_states} states</span> and <span class="states-count">${this.getTransitionCount()} transitions</span>
                </div>

                <div class="warning-section">
                    <span class="warning-icon">⚠️</span>
                    <div class="warning-text">
                        <strong>Warning:</strong> This operation will permanently replace the current automaton with an equivalent DFA. 
                        ${isDeterministic ? 'The resulting DFA may have a similar number of states.' : 'The resulting DFA may have significantly more states due to subset construction.'} 
                        Consider exporting your current FSA first if you want to save it.
                    </div>
                </div>
            </div>
            <div class="file-operation-actions">
                <button class="file-action-btn cancel" onclick="fsaTransformManager.hideConvertPopup()">
                    Cancel
                </button>
                <button class="file-action-btn primary" id="convert-confirm-btn" onclick="fsaTransformManager.confirmConvert()">
                    Convert to DFA
                </button>
            </div>
        `;

        // Store FSA data for later use
        this.currentFSAForConversion = fsa;

        // Add popup to canvas
        const canvas = document.getElementById('fsa-canvas');
        if (canvas) {
            canvas.appendChild(popup);

            // Trigger show animation
            setTimeout(() => {
                popup.classList.add('show');
            }, 100);
        }
    }

    /**
     * Hide minimize confirmation popup
     */
    hideMinimizePopup() {
        const popup = document.getElementById('transform-operation-popup');
        if (popup) {
            popup.classList.add('hide');
            setTimeout(() => {
                if (popup.parentNode) {
                    popup.parentNode.removeChild(popup);
                }
            }, 300);
        }
        this.currentFSAForMinimization = null;
    }

    /**
     * Hide convert confirmation popup
     */
    hideConvertPopup() {
        const popup = document.getElementById('transform-operation-popup');
        if (popup) {
            popup.classList.add('hide');
            setTimeout(() => {
                if (popup.parentNode) {
                    popup.parentNode.removeChild(popup);
                }
            }, 300);
        }
        this.currentFSAForConversion = null;
    }

    /**
     * Confirm and execute DFA minimization
     */
    async confirmMinimize() {
        const confirmBtn = document.getElementById('minimize-confirm-btn');
        if (!confirmBtn || !this.currentFSAForMinimization) return;

        // Show loading state
        confirmBtn.textContent = 'Minimizing...';
        confirmBtn.disabled = true;

        try {
            // Create snapshot before minimization for undo/redo
            let snapshotCommand = null;
            if (undoRedoManager && !undoRedoManager.isProcessing()) {
                snapshotCommand = undoRedoManager.createSnapshotCommand('Minimize DFA');
            }

            // Call backend minimization API
            const response = await fetch('/api/minimise-dfa/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ fsa: this.currentFSAForMinimization })
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.error || `HTTP error! status: ${response.status}`);
            }

            const result = await response.json();

            // Hide popup
            this.hideMinimizePopup();

            // Replace current FSA with minimized version
            await this.replaceWithMinimizedFSA(result);

            // Show success message with statistics
            this.showMinimizationResults(result);

            // Finish undo/redo snapshot
            if (snapshotCommand) {
                undoRedoManager.finishSnapshotCommand(snapshotCommand);
            }

        } catch (error) {
            console.error('Minimization error:', error);
            notificationManager.showError('Minimization Failed', error.message);

            // Reset button state
            confirmBtn.textContent = 'Minimize DFA';
            confirmBtn.disabled = false;
        }
    }

    /**
     * Confirm and execute NFA to DFA conversion
     */
    async confirmConvert() {
        const confirmBtn = document.getElementById('convert-confirm-btn');
        if (!confirmBtn || !this.currentFSAForConversion) return;

        // Show loading state
        confirmBtn.textContent = 'Converting...';
        confirmBtn.disabled = true;

        try {
            // Create snapshot before conversion for undo/redo
            let snapshotCommand = null;
            if (undoRedoManager && !undoRedoManager.isProcessing()) {
                snapshotCommand = undoRedoManager.createSnapshotCommand('Convert NFA to DFA');
            }

            // Call backend conversion API
            const response = await fetch('/api/nfa-to-dfa/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ fsa: this.currentFSAForConversion })
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.error || `HTTP error! status: ${response.status}`);
            }

            const result = await response.json();

            // Hide popup
            this.hideConvertPopup();

            // Replace current FSA with converted version
            await this.replaceWithConvertedFSA(result);

            // Show success message with statistics
            this.showConversionResults(result);

            // Finish undo/redo snapshot
            if (snapshotCommand) {
                undoRedoManager.finishSnapshotCommand(snapshotCommand);
            }

        } catch (error) {
            console.error('Conversion error:', error);
            notificationManager.showError('Conversion Failed', error.message);

            // Reset button state
            confirmBtn.textContent = 'Convert to DFA';
            confirmBtn.disabled = false;
        }
    }

    /**
     * Replace current FSA with minimized version
     * @param {Object} result - Minimization result from backend
     */
    async replaceWithMinimizedFSA(result) {
        const originalFSA = result.original_fsa;
        const minimizedFSA = result.minimised_fsa;

        // Store original state positions for interpolation
        const originalPositions = this.getOriginalStatePositions();

        // Clear current FSA
        await fsaSerializationManager.clearCurrentFSA(this.jsPlumbInstance);

        // Calculate positions for new states based on original state groups
        const newStatePositions = this.calculateMinimizedStatePositions(
            originalFSA, minimizedFSA, originalPositions
        );

        // Create serialized data for the minimized FSA with calculated positions
        const serializedMinimizedFSA = this.createSerializedMinimizedFSA(
            minimizedFSA, newStatePositions
        );

        // Load the minimized FSA
        await fsaSerializationManager.deserializeFSA(serializedMinimizedFSA, this.jsPlumbInstance);

        // Update properties display
        updateFSAPropertiesDisplay(this.jsPlumbInstance);

        console.log('Successfully replaced FSA with minimized version');
    }

    /**
     * Replace current FSA with converted DFA version
     * @param {Object} result - Conversion result from backend
     */
    async replaceWithConvertedFSA(result) {
        const originalFSA = result.original_fsa;
        const convertedDFA = result.converted_dfa;

        // Store original state positions for interpolation
        const originalPositions = this.getOriginalStatePositions();

        // Clear current FSA
        await fsaSerializationManager.clearCurrentFSA(this.jsPlumbInstance);

        // Calculate positions for new states based on original states and subset construction
        const newStatePositions = this.calculateConvertedStatePositions(
            originalFSA, convertedDFA, originalPositions
        );

        // Create serialized data for the converted DFA with calculated positions
        const serializedConvertedDFA = this.createSerializedConvertedDFA(
            convertedDFA, newStatePositions
        );

        // Load the converted DFA
        await fsaSerializationManager.deserializeFSA(serializedConvertedDFA, this.jsPlumbInstance);

        // Update properties display
        updateFSAPropertiesDisplay(this.jsPlumbInstance);

        console.log('Successfully replaced FSA with converted DFA version');
    }

    /**
     * Get current state positions before transformation
     * @returns {Object} - Map of state IDs to their positions
     */
    getOriginalStatePositions() {
        const positions = {};
        const states = document.querySelectorAll('.state, .accepting-state');

        states.forEach(state => {
            positions[state.id] = {
                x: parseInt(state.style.left) || 0,
                y: parseInt(state.style.top) || 0
            };
        });

        return positions;
    }

    /**
     * Calculate positions for minimized states based on original state groups
     * @param {Object} originalFSA - Original FSA structure
     * @param {Object} minimizedFSA - Minimized FSA structure
     * @param {Object} originalPositions - Original state positions
     * @returns {Object} - Map of new state IDs to their calculated positions
     */
    calculateMinimizedStatePositions(originalFSA, minimizedFSA, originalPositions) {
        const newPositions = {};

        minimizedFSA.states.forEach(newStateId => {
            // Parse the new state ID to get the original states it represents
            // New state names are created by joining original state names with underscores
            const originalStateIds = newStateId.split('_');

            // Calculate centroid of original states
            let totalX = 0, totalY = 0, validCount = 0;

            originalStateIds.forEach(originalId => {
                if (originalPositions[originalId]) {
                    totalX += originalPositions[originalId].x;
                    totalY += originalPositions[originalId].y;
                    validCount++;
                }
            });

            if (validCount > 0) {
                newPositions[newStateId] = {
                    x: Math.round(totalX / validCount),
                    y: Math.round(totalY / validCount)
                };
            } else {
                // Fallback: place at canvas center with some offset
                const canvas = document.getElementById('fsa-canvas');
                const centerX = canvas ? canvas.offsetWidth / 2 : 400;
                const centerY = canvas ? canvas.offsetHeight / 2 : 300;
                const stateIndex = minimizedFSA.states.indexOf(newStateId);

                newPositions[newStateId] = {
                    x: centerX + (stateIndex * 100) - 200,
                    y: centerY + (Math.sin(stateIndex) * 100)
                };
            }
        });

        // Ensure no overlapping states
        this.adjustOverlappingPositions(newPositions);

        return newPositions;
    }

    /**
     * Calculate positions for converted DFA states based on subset construction
     * @param {Object} originalFSA - Original FSA structure
     * @param {Object} convertedDFA - Converted DFA structure
     * @param {Object} originalPositions - Original state positions
     * @returns {Object} - Map of new state IDs to their calculated positions
     */
    calculateConvertedStatePositions(originalFSA, convertedDFA, originalPositions) {
        const newPositions = {};

        convertedDFA.states.forEach(newStateId => {
            // For NFA to DFA conversion, state names represent subsets of original states
            // Try to parse the subset from the state name
            const originalStateIds = this.parseSubsetFromStateName(newStateId);

            // Calculate centroid of original states that this DFA state represents
            let totalX = 0, totalY = 0, validCount = 0;

            originalStateIds.forEach(originalId => {
                if (originalPositions[originalId]) {
                    totalX += originalPositions[originalId].x;
                    totalY += originalPositions[originalId].y;
                    validCount++;
                }
            });

            if (validCount > 0) {
                newPositions[newStateId] = {
                    x: Math.round(totalX / validCount),
                    y: Math.round(totalY / validCount)
                };
            } else {
                // Fallback: place in a grid layout for new states
                const canvas = document.getElementById('fsa-canvas');
                const centerX = canvas ? canvas.offsetWidth / 2 : 400;
                const centerY = canvas ? canvas.offsetHeight / 2 : 300;
                const stateIndex = convertedDFA.states.indexOf(newStateId);

                // Arrange in a rough grid
                const gridSize = Math.ceil(Math.sqrt(convertedDFA.states.length));
                const row = Math.floor(stateIndex / gridSize);
                const col = stateIndex % gridSize;

                newPositions[newStateId] = {
                    x: centerX + (col - gridSize/2) * 120,
                    y: centerY + (row - gridSize/2) * 120
                };
            }
        });

        // Ensure no overlapping states
        this.adjustOverlappingPositions(newPositions);

        return newPositions;
    }

    /**
     * Parse subset information from DFA state name
     * @param {string} stateName - The DFA state name
     * @returns {Array} - Array of original state IDs
     */
    parseSubsetFromStateName(stateName) {
        // Handle different naming conventions for DFA states
        if (stateName === 'EMPTY' || stateName.startsWith('DEAD')) {
            return [];
        }

        // Handle hash-based names for large subsets
        if (stateName.includes('_PLUS_') && stateName.includes('more_H')) {
            // Extract the first few states from hash-based names
            const firstPart = stateName.split('_PLUS_')[0];
            return firstPart.split('_');
        }

        // Standard underscore-separated state names
        return stateName.split('_').filter(id => id && id !== 'EMPTY');
    }

    /**
     * Adjust positions to avoid overlapping states
     * @param {Object} positions - State positions to adjust
     */
    adjustOverlappingPositions(positions) {
        const minDistance = 80; // Minimum distance between state centers
        const positionArray = Object.entries(positions);

        for (let i = 0; i < positionArray.length; i++) {
            for (let j = i + 1; j < positionArray.length; j++) {
                const [id1, pos1] = positionArray[i];
                const [id2, pos2] = positionArray[j];

                const dx = pos2.x - pos1.x;
                const dy = pos2.y - pos1.y;
                const distance = Math.sqrt(dx * dx + dy * dy);

                if (distance < minDistance) {
                    // Move second state away from first
                    const angle = Math.atan2(dy, dx);
                    const newDistance = minDistance;

                    pos2.x = Math.round(pos1.x + Math.cos(angle) * newDistance);
                    pos2.y = Math.round(pos1.y + Math.sin(angle) * newDistance);
                }
            }
        }
    }

    /**
     * Create serialized FSA data for the minimized FSA
     * @param {Object} minimizedFSA - Minimized FSA from backend
     * @param {Object} positions - Calculated positions for states
     * @returns {Object} - Serialized FSA data
     */
    createSerializedMinimizedFSA(minimizedFSA, positions) {
        return this.createSerializedFSA(minimizedFSA, positions, 'Minimized DFA', 'DFA generated by minimization', ['minimized']);
    }

    /**
     * Create serialized FSA data for the converted DFA
     * @param {Object} convertedDFA - Converted DFA from backend
     * @param {Object} positions - Calculated positions for states
     * @returns {Object} - Serialized FSA data
     */
    createSerializedConvertedDFA(convertedDFA, positions) {
        return this.createSerializedFSA(convertedDFA, positions, 'Converted DFA', 'DFA generated by NFA to DFA conversion', ['converted', 'dfa']);
    }

    /**
     * Create serialized FSA data for any transformed FSA
     * @param {Object} fsa - FSA from backend
     * @param {Object} positions - Calculated positions for states
     * @param {string} name - Name for the FSA
     * @param {string} description - Description for the FSA
     * @param {Array} tags - Tags for the FSA
     * @returns {Object} - Serialized FSA data
     */
    createSerializedFSA(fsa, positions, name, description, tags) {
        // Create states data
        const statesData = fsa.states.map(stateId => ({
            id: stateId,
            label: stateId,
            isAccepting: fsa.acceptingStates.includes(stateId),
            position: positions[stateId] || { x: 100, y: 100 },
            visual: {
                className: fsa.acceptingStates.includes(stateId) ? 'accepting-state' : 'state',
                zIndex: 'auto'
            }
        }));

        // Create transitions data
        const transitionsData = [];
        Object.entries(fsa.transitions).forEach(([sourceId, transitions]) => {
            Object.entries(transitions).forEach(([symbol, targets]) => {
                if (targets && targets.length > 0) {
                    const targetId = targets[0]; // DFA has only one target per symbol

                    // Group symbols going to the same target
                    const existingTransition = transitionsData.find(t =>
                        t.sourceId === sourceId && t.targetId === targetId
                    );

                    if (existingTransition) {
                        if (symbol === '') {
                            existingTransition.hasEpsilon = true;
                        } else {
                            existingTransition.symbols.push(symbol);
                        }
                    } else {
                        transitionsData.push({
                            id: `${sourceId}-${targetId}-${symbol}`,
                            sourceId: sourceId,
                            targetId: targetId,
                            symbols: symbol === '' ? [] : [symbol],
                            hasEpsilon: symbol === '',
                            visual: {
                                connectorType: sourceId === targetId ? 'Bezier' : 'Straight',
                                isCurved: sourceId === targetId,
                                labelLocation: 0.3,
                                anchors: sourceId === targetId ? ['Top', 'Left'] : ['Continuous', 'Continuous']
                            }
                        });
                    }
                }
            });
        });

        return {
            version: "1.0.0",
            timestamp: new Date().toISOString(),
            metadata: {
                name: name,
                description: description,
                creator: "FSA Simulator",
                tags: tags
            },
            states: statesData,
            transitions: transitionsData,
            startingState: fsa.startingState,
            canvasProperties: {
                dimensions: { width: 800, height: 600 },
                viewport: { scrollLeft: 0, scrollTop: 0 },
                zoom: 1.0,
                backgroundColor: '#ffffff'
            }
        };
    }

    /**
     * Show minimization results with statistics
     * @param {Object} result - Minimization result from backend
     */
    showMinimizationResults(result) {
        const stats = result.statistics;
        const isAlreadyMinimal = stats.reduction.is_already_minimal;

        if (isAlreadyMinimal) {
            notificationManager.showInfo(
                'DFA Already Minimal',
                'The DFA was already in minimal form. No changes were made.'
            );
        } else {
            const statesReduced = stats.reduction.states_reduced;
            const reductionPercentage = stats.reduction.states_reduction_percentage;

            notificationManager.showSuccess(
                'DFA Minimized Successfully',
                `Reduced from ${stats.original.states_count} to ${stats.minimised.states_count} states (${reductionPercentage}% reduction).`
            );
        }
    }

    /**
     * Show conversion results with statistics
     * @param {Object} result - Conversion result from backend
     */
    showConversionResults(result) {
        const stats = result.statistics;
        const wasAlreadyDeterministic = stats.conversion.was_already_deterministic;
        const epsilonTransitionsRemoved = stats.conversion.epsilon_transitions_removed;

        if (wasAlreadyDeterministic && !epsilonTransitionsRemoved) {
            notificationManager.showInfo(
                'Already a DFA',
                'The input was already a deterministic finite automaton.'
            );
        } else if (wasAlreadyDeterministic && epsilonTransitionsRemoved) {
            notificationManager.showSuccess(
                'DFA Conversion Complete',
                'Removed epsilon transitions to create a proper DFA.'
            );
        } else {
            const statesAdded = stats.conversion.states_added;
            const changePercentage = Math.abs(stats.conversion.states_change_percentage);

            let message = `Converted NFA to DFA: ${stats.original.states_count} → ${stats.converted.states_count} states`;

            if (statesAdded > 0) {
                message += ` (+${changePercentage}% states)`;
            } else if (statesAdded < 0) {
                message += ` (-${changePercentage}% states)`;
            }

            notificationManager.showSuccess('NFA to DFA Conversion Complete', message);
        }
    }

    /**
     * Get current transition count
     * @returns {number} - Number of transitions
     */
    getTransitionCount() {
        if (!this.jsPlumbInstance) return 0;

        const connections = this.jsPlumbInstance.getAllConnections();
        // Filter out starting state connections
        return connections.filter(conn =>
            !conn.canvas || !conn.canvas.classList.contains('starting-connection')
        ).length;
    }

    /**
     * Update menu states based on control lock status
     * @param {boolean} locked - Whether controls are locked
     */
    updateMenuStates(locked) {
        const transformOptions = document.querySelectorAll('#transform-dropdown .menu-option');

        transformOptions.forEach(option => {
            if (locked) {
                option.classList.add('disabled');
            } else {
                option.classList.remove('disabled');
            }
        });
    }
}

// Create and export singleton instance
export const fsaTransformManager = new FSATransformManager();

// Make globally available
window.fsaTransformManager = fsaTransformManager;

// Export class for potential multiple instances
export { FSATransformManager };