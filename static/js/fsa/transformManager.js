import { fsaSerializationManager} from './fsaSerializationManager.js';
import { notificationManager } from './notificationManager.js';
import { controlLockManager } from './controlLockManager.js';
import { undoRedoManager } from './undoRedoManager.js';
import { menuManager } from './menuManager.js';
import {
    convertFSAToBackendFormat,
    checkFSAProperties
} from './backendIntegration.js';
import { updateFSAPropertiesDisplay } from './fsaPropertyChecker.js';

/**
 * FSA Transform Manager - handles FSA transformation operations with unified menu system
 */
class FSATransformManager {
    constructor() {
        this.jsPlumbInstance = null;
        this.currentTransformData = null;
        this.currentTransformType = null;

        // Transform configurations
        this.transformConfigs = {
            minimize: {
                name: 'Minimize DFA',
                apiEndpoint: '/api/minimise-dfa/',
                popupClass: 'minimize',
                headerGradient: 'var(--primary-color) 0%, var(--primary-hover) 100%',
                buttonColor: 'var(--primary-color)',
                hoverColor: 'var(--primary-hover)',
                undoLabel: 'Minimize DFA',
                requiresDeterministic: true,
                requiresConnected: true,
                tags: ['minimized']
            },
            convert: {
                name: 'Convert to DFA',
                apiEndpoint: '/api/nfa-to-dfa/',
                popupClass: 'convert',
                headerGradient: 'var(--secondary-color) 0%, var(--secondary-hover) 100%',
                buttonColor: 'var(--secondary-color)',
                hoverColor: 'var(--secondary-hover)',
                undoLabel: 'Convert NFA to DFA',
                requiresDeterministic: false,
                requiresConnected: true,
                tags: ['converted', 'dfa']
            },
            complete: {
                name: 'Complete DFA',
                apiEndpoint: '/api/complete-dfa/',
                popupClass: 'complete',
                headerGradient: 'var(--accent-color) 0%, #ef6c00 100%',
                buttonColor: 'var(--accent-color)',
                hoverColor: '#ef6c00',
                undoLabel: 'Complete DFA',
                requiresDeterministic: true,
                requiresConnected: true,
                tags: ['completed', 'complete']
            },
            complement: {
                name: 'Complement DFA',
                apiEndpoint: '/api/complement-dfa/',
                popupClass: 'complement',
                headerGradient: 'var(--error-color) 0%, var(--error-hover) 100%',
                buttonColor: 'var(--error-color)',
                hoverColor: 'var(--error-hover)',
                undoLabel: 'Complement DFA',
                requiresDeterministic: true,
                requiresConnected: true,
                tags: ['complement', 'complemented']
            }
        };
    }

    /**
     * Initialize with JSPlumb instance
     */
    initialize(jsPlumbInstance) {
        this.jsPlumbInstance = jsPlumbInstance;

        if (!menuManager.initialized) {
            menuManager.initialize();
        }

        menuManager.registerMenu('transform', {
            buttonId: 'transform-menu-button',
            dropdownId: 'transform-dropdown'
        });

        this.setupTransformEventListeners();
        this.setupKeyboardShortcuts();
    }

    /**
     * Setup Transform menu event listeners
     */
    setupTransformEventListeners() {
        menuManager.registerMenuItems({
            'menu-minimise-dfa': () => this.executeTransform('minimize'),
            'menu-nfa-to-dfa': () => this.executeTransform('convert'),
            'menu-complete-dfa': () => this.executeTransform('complete'),
            'menu-complement-dfa': () => this.executeTransform('complement')
        });
    }

    /**
     * Setup keyboard shortcuts
     */
    setupKeyboardShortcuts() {
        document.addEventListener('keydown', (e) => {
            if (controlLockManager.isControlsLocked() ||
                e.target.tagName === 'INPUT' ||
                e.target.tagName === 'TEXTAREA') {
                return;
            }

            const shortcuts = {
                'm': 'minimize',
                'd': 'convert'
            };

            if ((e.ctrlKey || e.metaKey) && shortcuts[e.key]) {
                e.preventDefault();
                this.executeTransform(shortcuts[e.key]);
            }
        });
    }

    /**
     * Execute any transform operation
     */
    async executeTransform(type) {
        const config = this.transformConfigs[type];
        if (!config) {
            console.error(`Unknown transform type: ${type}`);
            return;
        }

        // Common validation
        const validation = await this.validateTransform(config);
        if (!validation.isValid) return;

        // Store current transform data
        this.currentTransformType = type;
        this.currentTransformData = validation.fsa;

        // Show appropriate popup
        this.showTransformPopup(type, validation.fsa, validation.propertiesResult);
    }

    /**
     * Common validation for all transforms
     */
    async validateTransform(config) {
        if (!this.jsPlumbInstance) {
            notificationManager.showError(`${config.name} Error`, 'FSA not initialized');
            return { isValid: false };
        }

        if (controlLockManager.isControlsLocked()) {
            notificationManager.showWarning(`Cannot ${config.name}`, 'Cannot perform operation while simulation is running');
            return { isValid: false };
        }

        const states = document.querySelectorAll('.state, .accepting-state');
        if (states.length === 0) {
            notificationManager.showWarning('Nothing to Transform', 'Create an FSA before transforming');
            return { isValid: false };
        }

        try {
            const fsa = convertFSAToBackendFormat(this.jsPlumbInstance);
            const propertiesResult = await checkFSAProperties(fsa);
            const properties = propertiesResult.properties;

            // Check common requirements
            if (config.requiresDeterministic && !properties.deterministic) {
                notificationManager.showError(
                    `Cannot ${config.name}`,
                    `${config.name} requires a deterministic automaton. The current FSA is non-deterministic (NFA).`
                );
                return { isValid: false };
            }

            if (config.requiresConnected && !properties.connected) {
                notificationManager.showError(
                    `Cannot ${config.name}`,
                    `${config.name} requires a connected automaton. Some states are unreachable from the starting state.`
                );
                return { isValid: false };
            }

            return { isValid: true, fsa, propertiesResult };

        } catch (error) {
            console.error('Error validating FSA:', error);
            notificationManager.showError('Validation Error', `Failed to validate FSA: ${error.message}`);
            return { isValid: false };
        }
    }

    /**
     * Unified popup display method
     */
    showTransformPopup(type, fsa, propertiesResult) {
        const config = this.transformConfigs[type];
        const summary = propertiesResult.summary;
        const properties = propertiesResult.properties;

        // Remove any existing popup
        const existingPopup = document.getElementById('transform-operation-popup');
        if (existingPopup) existingPopup.remove();

        // Generate popup content based on type
        const popupContent = this.generatePopupContent(type, summary, properties);

        const popup = document.createElement('div');
        popup.id = 'transform-operation-popup';
        popup.className = `file-operation-popup ${config.popupClass}`;

        popup.innerHTML = `
            <div class="popup-header" style="background: linear-gradient(135deg, ${config.headerGradient});">
                <div class="popup-title">
                    <div class="popup-icon">
                        <img src="static/img/alert.png" alt="Warning" style="width: 20px; height: 20px;">
                    </div>
                    <span>${config.name}</span>
                </div>
                <button class="popup-close" onclick="fsaTransformManager.hideTransformPopup()">×</button>
            </div>
            <div class="file-operation-content">
                ${popupContent.description}
                ${popupContent.statesInfo}
                ${popupContent.warningSection}
            </div>
            <div class="file-operation-actions">
                <button class="file-action-btn cancel" onclick="fsaTransformManager.hideTransformPopup()">
                    Cancel
                </button>
                <button class="file-action-btn primary" id="transform-confirm-btn" 
                        onclick="fsaTransformManager.confirmTransform()"
                        style="background: ${config.buttonColor};">
                    ${popupContent.confirmButtonText}
                </button>
            </div>
        `;

        const canvas = document.getElementById('fsa-canvas');
        if (canvas) {
            canvas.appendChild(popup);
            setTimeout(() => popup.classList.add('show'), 100);
        }
    }

    /**
     * Generate popup content based on transform type
     */
    generatePopupContent(type, summary, properties) {
        const transitionCount = this.getTransitionCount();
        const baseStatesInfo = `
            <div class="states-info">
                Current FSA: <span class="states-count">${summary.total_states} states</span> 
                and <span class="states-count">${transitionCount} transitions</span>
            </div>
        `;

        const contentGenerators = {
            minimize: () => ({
                description: `<div class="file-operation-description">
                    Minimizing the DFA will replace the current automaton with an equivalent minimal DFA using Hopcroft's algorithm.
                </div>`,
                statesInfo: baseStatesInfo,
                warningSection: this.generateWarningSection(
                    'This operation will permanently replace the current DFA with its minimal equivalent. ' +
                    'The minimized DFA will have the same behavior but potentially fewer states.'
                ),
                confirmButtonText: 'Minimize DFA'
            }),

            convert: () => {
                const isDeterministic = properties.deterministic;
                const hasEpsilon = summary.has_epsilon_transitions;
                let typeDesc = isDeterministic && !hasEpsilon ? 'DFA (already deterministic)' :
                              isDeterministic && hasEpsilon ? 'Deterministic automaton with ε-transitions' :
                              'NFA (non-deterministic)';

                return {
                    description: `<div class="file-operation-description">
                        ${this.getConversionDescription(isDeterministic, hasEpsilon)}
                    </div>`,
                    statesInfo: `<div class="states-info">
                        Current FSA: <span class="states-count">${typeDesc}</span><br>
                        <span class="states-count">${summary.total_states} states</span> 
                        and <span class="states-count">${transitionCount} transitions</span>
                    </div>`,
                    warningSection: this.generateWarningSection(
                        'This operation will permanently replace the current automaton with an equivalent DFA. ' +
                        (isDeterministic ? 'The resulting DFA may have a similar number of states.' :
                                          'The resulting DFA may have significantly more states due to subset construction.')
                    ),
                    confirmButtonText: 'Convert to DFA'
                };
            },

            complete: () => {
                const isComplete = properties.complete;
                return {
                    description: `<div class="file-operation-description">
                        ${isComplete ? 'The DFA is already complete. No changes will be made.' :
                                      'Completing the DFA will add missing transitions by introducing a dead state and routing undefined transitions to it.'}
                    </div>`,
                    statesInfo: `<div class="states-info">
                        Current DFA: <span class="states-count">${isComplete ? 'Complete' : 'Incomplete'}</span><br>
                        <span class="states-count">${summary.total_states} states</span> 
                        and <span class="states-count">${transitionCount} transitions</span>
                    </div>`,
                    warningSection: isComplete ?
                        this.generateInfoSection('The DFA is already complete. All states have transitions defined for every symbol in the alphabet.') :
                        this.generateWarningSection(
                            'This operation will permanently add a dead state and missing transitions to make the DFA complete. ' +
                            'The completed DFA will explicitly reject strings that lead to undefined transitions.'
                        ),
                    confirmButtonText: isComplete ? 'Confirm (No Changes)' : 'Complete DFA'
                };
            },

            complement: () => {
                const isComplete = properties.complete;
                const acceptingCount = summary.accepting_states_count;
                const nonAcceptingCount = summary.total_states - acceptingCount;

                return {
                    description: `<div class="file-operation-description">
                        ${isComplete ? 
                            `Taking the complement will swap accepting and non-accepting states. ${acceptingCount} accepting states will become non-accepting, and ${nonAcceptingCount} non-accepting states will become accepting.` :
                            `Taking the complement will first complete the DFA (adding dead states for missing transitions), then swap accepting and non-accepting states. The result accepts exactly the strings that the original DFA rejects.`}
                    </div>`,
                    statesInfo: `<div class="states-info">
                        Current DFA: <span class="states-count">${isComplete ? 'Complete' : 'Incomplete'}</span><br>
                        <span class="states-count">${summary.total_states} states</span> 
                        and <span class="states-count">${transitionCount} transitions</span><br>
                        <span class="states-count">${acceptingCount} accepting</span>, 
                        <span class="states-count">${nonAcceptingCount} non-accepting</span>
                    </div>`,
                    warningSection: this.generateWarningSection(
                        'This operation will permanently replace the current DFA with its complement. ' +
                        (!isComplete ? 'The DFA will be completed first, which may add dead states. ' : '') +
                        'The complement DFA accepts exactly the strings that the original DFA rejects.'
                    ),
                    confirmButtonText: 'Complement DFA'
                };
            }
        };

        return contentGenerators[type]();
    }

    /**
     * Helper methods for content generation
     */
    getConversionDescription(isDeterministic, hasEpsilon) {
        if (isDeterministic && !hasEpsilon) {
            return 'The conversion will ensure the automaton is in proper DFA format.';
        } else if (isDeterministic && hasEpsilon) {
            return 'The conversion will remove epsilon transitions while maintaining determinism.';
        }
        return 'The conversion will create an equivalent deterministic automaton (DFA) using subset construction.';
    }

    generateWarningSection(text) {
        return `
            <div class="warning-section">
                <span class="warning-icon">⚠️</span>
                <div class="warning-text">
                    <strong>Warning:</strong> ${text} 
                    Consider exporting your current FSA first if you want to save it.
                </div>
            </div>
        `;
    }

    generateInfoSection(text) {
        return `
            <div class="info-section">
                <span class="info-icon">ℹ️</span>
                <div class="info-text">
                    <strong>Info:</strong> ${text}
                </div>
            </div>
        `;
    }

    /**
     * Hide transform popup
     */
    hideTransformPopup() {
        const popup = document.getElementById('transform-operation-popup');
        if (popup) {
            popup.classList.add('hide');
            setTimeout(() => popup.parentNode?.removeChild(popup), 300);
        }
        // Don't clear the transform data here as it's needed for the operation
        // It will be cleared after the operation completes or fails
    }

    /**
     * Clear transform data after operation
     */
    clearTransformData() {
        this.currentTransformData = null;
        this.currentTransformType = null;
    }

    /**
     * Confirm and execute transform
     */
    async confirmTransform() {
        const confirmBtn = document.getElementById('transform-confirm-btn');
        if (!confirmBtn || !this.currentTransformData || !this.currentTransformType) return;

        const config = this.transformConfigs[this.currentTransformType];

        // Show loading state
        confirmBtn.textContent = 'Processing...';
        confirmBtn.disabled = true;

        try {
            // Create snapshot for undo/redo
            let snapshotCommand = null;
            if (undoRedoManager && !undoRedoManager.isProcessing()) {
                snapshotCommand = undoRedoManager.createSnapshotCommand(config.undoLabel);
            }

            // Call backend API
            const response = await fetch(config.apiEndpoint, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ fsa: this.currentTransformData })
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.error || `HTTP error! status: ${response.status}`);
            }

            const result = await response.json();

            // Hide popup
            this.hideTransformPopup();

            // Replace FSA
            await this.replaceWithTransformedFSA(this.currentTransformType, result);

            // Show results
            this.showTransformResults(this.currentTransformType, result);

            // Finish undo/redo snapshot
            if (snapshotCommand) {
                undoRedoManager.finishSnapshotCommand(snapshotCommand);
            }

            // Clear transform data after successful operation
            this.clearTransformData();

        } catch (error) {
            console.error('Transform error:', error);
            notificationManager.showError(`${config.name} Failed`, error.message);

            // Reset button state
            confirmBtn.textContent = config.name;
            confirmBtn.disabled = false;

            // Don't clear transform data on error - user might retry
        }
    }

    /**
     * Replace current FSA with transformed version
     */
    async replaceWithTransformedFSA(type, result) {
        const originalPositions = this.getOriginalStatePositions();

        await fsaSerializationManager.clearCurrentFSA(this.jsPlumbInstance);

        // Get the transformed FSA data based on type
        const fsaDataMap = {
            minimize: result.minimised_fsa,
            convert: result.converted_dfa,
            complete: result.completed_fsa,
            complement: result.complement_fsa
        };

        const transformedFSA = fsaDataMap[type];
        const config = this.transformConfigs[type];

        // Calculate positions
        const newPositions = this.calculateStatePositions(
            type, result.original_fsa, transformedFSA, originalPositions
        );

        // Create serialized data
        const serializedFSA = this.createSerializedFSA(
            transformedFSA,
            newPositions,
            `${config.name} Result`,
            `FSA generated by ${config.name.toLowerCase()}`,
            config.tags
        );

        // Load the transformed FSA
        await fsaSerializationManager.deserializeFSA(serializedFSA, this.jsPlumbInstance);
        updateFSAPropertiesDisplay(this.jsPlumbInstance);
    }

    /**
     * Calculate state positions for transformed FSA
     */
    calculateStatePositions(type, originalFSA, transformedFSA, originalPositions) {
        // Define strategies as functions to be called when needed
        const positionStrategies = {
            minimize: () => this.calculateCentroidPositions(transformedFSA, originalPositions),
            convert: () => this.calculateCentroidPositions(transformedFSA, originalPositions),
            complete: () => this.preservePositionsWithNew(transformedFSA, originalPositions),
            complement: () => this.preservePositionsWithNew(transformedFSA, originalPositions)
        };

        // Call the appropriate strategy function
        const strategy = positionStrategies[type];
        if (!strategy) {
            console.error(`Unknown transform type: ${type}`);
            return this.getDefaultPositions(transformedFSA);
        }

        const positions = strategy();
        this.adjustOverlappingPositions(positions);
        return positions;
    }

    /**
     * Get default positions for all states when strategy fails
     */
    getDefaultPositions(transformedFSA) {
        const positions = {};
        if (!transformedFSA || !transformedFSA.states) {
            console.error('Invalid transformedFSA:', transformedFSA);
            return positions;
        }

        transformedFSA.states.forEach((stateId, index) => {
            positions[stateId] = this.getDefaultPosition(stateId, transformedFSA.states);
        });

        return positions;
    }

    /**
     * Calculate centroid positions for merged states
     */
    calculateCentroidPositions(transformedFSA, originalPositions) {
        const newPositions = {};

        transformedFSA.states.forEach(stateId => {
            // Try to parse original states from the new state ID
            const originalIds = this.parseOriginalStates(stateId);

            if (originalIds.length > 0) {
                let totalX = 0, totalY = 0, validCount = 0;

                originalIds.forEach(originalId => {
                    if (originalPositions[originalId]) {
                        totalX += originalPositions[originalId].x;
                        totalY += originalPositions[originalId].y;
                        validCount++;
                    }
                });

                if (validCount > 0) {
                    newPositions[stateId] = {
                        x: Math.round(totalX / validCount),
                        y: Math.round(totalY / validCount)
                    };
                }
            }

            // Fallback for states without valid positions
            if (!newPositions[stateId]) {
                newPositions[stateId] = this.getDefaultPosition(stateId, transformedFSA.states);
            }
        });

        return newPositions;
    }

    /**
     * Preserve original positions and add new states
     */
    preservePositionsWithNew(transformedFSA, originalPositions) {
        const newPositions = {};

        transformedFSA.states.forEach(stateId => {
            if (originalPositions[stateId]) {
                newPositions[stateId] = originalPositions[stateId];
            } else {
                // Place new states (like dead states) away from existing ones
                newPositions[stateId] = this.findNonOverlappingPosition(originalPositions);
            }
        });

        return newPositions;
    }

    /**
     * Parse original state IDs from transformed state name
     */
    parseOriginalStates(stateName) {
        if (stateName === 'EMPTY' || stateName.startsWith('DEAD')) {
            return [];
        }

        if (stateName.includes('_PLUS_') && stateName.includes('more_H')) {
            const firstPart = stateName.split('_PLUS_')[0];
            return firstPart.split('_');
        }

        return stateName.split('_').filter(id => id && id !== 'EMPTY');
    }

    /**
     * Get default position for states without calculated positions
     */
    getDefaultPosition(stateId, allStates) {
        const canvas = document.getElementById('fsa-canvas');
        const centerX = canvas ? canvas.offsetWidth / 2 : 400;
        const centerY = canvas ? canvas.offsetHeight / 2 : 300;
        const stateIndex = allStates.indexOf(stateId);

        if (stateId.includes('DEAD')) {
            return { x: centerX + 200, y: centerY + 200 };
        }

        // Grid layout for other states
        const gridSize = Math.ceil(Math.sqrt(allStates.length));
        const row = Math.floor(stateIndex / gridSize);
        const col = stateIndex % gridSize;

        return {
            x: centerX + (col - gridSize/2) * 120,
            y: centerY + (row - gridSize/2) * 120
        };
    }

    /**
     * Find non-overlapping position for new states
     */
    findNonOverlappingPosition(existingPositions) {
        const canvas = document.getElementById('fsa-canvas');
        const centerX = canvas ? canvas.offsetWidth / 2 : 400;
        const centerY = canvas ? canvas.offsetHeight / 2 : 300;

        let x = centerX + 200;
        let y = centerY + 200;
        let attempts = 0;

        while (attempts < 10) {
            let hasOverlap = false;

            Object.values(existingPositions).forEach(pos => {
                const distance = Math.sqrt((x - pos.x) ** 2 + (y - pos.y) ** 2);
                if (distance < 80) hasOverlap = true;
            });

            if (!hasOverlap) break;

            x += 50;
            y += 50;
            attempts++;
        }

        return { x, y };
    }

    /**
     * Get current state positions
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
     * Adjust overlapping positions
     */
    adjustOverlappingPositions(positions) {
        const minDistance = 80;
        const positionArray = Object.entries(positions);

        for (let i = 0; i < positionArray.length; i++) {
            for (let j = i + 1; j < positionArray.length; j++) {
                const [id1, pos1] = positionArray[i];
                const [id2, pos2] = positionArray[j];

                const dx = pos2.x - pos1.x;
                const dy = pos2.y - pos1.y;
                const distance = Math.sqrt(dx * dx + dy * dy);

                if (distance < minDistance) {
                    const angle = Math.atan2(dy, dx);
                    pos2.x = Math.round(pos1.x + Math.cos(angle) * minDistance);
                    pos2.y = Math.round(pos1.y + Math.sin(angle) * minDistance);
                }
            }
        }
    }

    /**
     * Create serialized FSA data
     */
    createSerializedFSA(fsa, positions, name, description, tags) {
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

        const transitionsData = [];
        Object.entries(fsa.transitions).forEach(([sourceId, transitions]) => {
            Object.entries(transitions).forEach(([symbol, targets]) => {
                if (targets && targets.length > 0) {
                    const targetId = targets[0];

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
            metadata: { name, description, creator: "FSA Simulator", tags },
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
     * Show transform results
     */
    showTransformResults(type, result) {
        const resultHandlers = {
            minimize: () => this.showMinimizationResults(result),
            convert: () => this.showConversionResults(result),
            complete: () => this.showCompletionResults(result),
            complement: () => this.showComplementResults(result)
        };

        resultHandlers[type]();
    }

    /**
     * Result display methods
     */
    showMinimizationResults(result) {
        const stats = result.statistics;
        if (stats.reduction.is_already_minimal) {
            notificationManager.showInfo(
                'DFA Already Minimal',
                'The DFA was already in minimal form. No changes were made.'
            );
        } else {
            notificationManager.showSuccess(
                'DFA Minimized Successfully',
                `Reduced from ${stats.original.states_count} to ${stats.minimised.states_count} states (${stats.reduction.states_reduction_percentage}% reduction).`
            );
        }
    }

    showConversionResults(result) {
        const stats = result.statistics;
        const wasDeterm = stats.conversion.was_already_deterministic;
        const epsRemoved = stats.conversion.epsilon_transitions_removed;

        if (wasDeterm && !epsRemoved) {
            notificationManager.showInfo('Already a DFA', 'The input was already a deterministic finite automaton.');
        } else if (wasDeterm && epsRemoved) {
            notificationManager.showSuccess('DFA Conversion Complete', 'Removed epsilon transitions to create a proper DFA.');
        } else {
            const changePercent = Math.abs(stats.conversion.states_change_percentage);
            const statesAdded = stats.conversion.states_added;
            let message = `Converted NFA to DFA: ${stats.original.states_count} → ${stats.converted.states_count} states`;
            message += statesAdded > 0 ? ` (+${changePercent}% states)` : statesAdded < 0 ? ` (-${changePercent}% states)` : '';
            notificationManager.showSuccess('NFA to DFA Conversion Complete', message);
        }
    }

    showCompletionResults(result) {
        const stats = result.statistics;
        if (stats.completion.was_already_complete) {
            notificationManager.showInfo('DFA Already Complete', 'The DFA was already complete. No changes were made.');
        } else {
            const message = stats.completion.dead_state_added ?
                `DFA completed successfully. Added ${stats.completion.states_added} dead state(s) and ${stats.completion.transitions_added} transition(s).` :
                `DFA completed successfully. Added ${stats.completion.transitions_added} missing transition(s).`;
            notificationManager.showSuccess('DFA Completion Complete', message);
        }
    }

    showComplementResults(result) {
        const stats = result.statistics;
        const analysis = stats.analysis;
        let message = `DFA complement computed successfully. `;
        message += `${analysis.original_accepting_became_non_accepting} accepting states became non-accepting, `;
        message += `${analysis.original_non_accepting_became_accepting} non-accepting states became accepting.`;

        if (analysis.completion_required) {
            message += ` The DFA was made complete first (added ${analysis.states_added_for_completeness} dead state(s)).`;
        }

        notificationManager.showSuccess('DFA Complement Complete', message);
    }

    /**
     * Get current transition count
     */
    getTransitionCount() {
        if (!this.jsPlumbInstance) return 0;
        const connections = this.jsPlumbInstance.getAllConnections();
        return connections.filter(conn =>
            !conn.canvas || !conn.canvas.classList.contains('starting-connection')
        ).length;
    }

    /**
     * Update menu states based on control lock status
     */
    updateMenuStates(locked) {
        menuManager.updateMenuStates(locked);
    }

    /**
     * Public methods for backward compatibility
     */
    minimiseDFA() {
        this.executeTransform('minimize');
    }

    convertNFAToDFA() {
        this.executeTransform('convert');
    }

    completeDFA() {
        this.executeTransform('complete');
    }

    complementDFA() {
        this.executeTransform('complement');
    }
}


// Create and export singleton instance
export const fsaTransformManager = new FSATransformManager();

// Make globally available
window.fsaTransformManager = fsaTransformManager;

// Export class for potential multiple instances
export { FSATransformManager };