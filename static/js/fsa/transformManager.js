import { fsaSerializationManager} from './fsaSerializationManager.js';
import { notificationManager } from './notificationManager.js';
import { controlLockManager } from './controlLockManager.js';
import { undoRedoManager } from './undoRedoManager.js';
import { menuManager } from './menuManager.js';
import { calculateStatePositions, calculatePositionsPreserving, findNonOverlappingPositions, calculateTransformLayout } from './positioningUtils.js';
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
                ${popupContent.chainingOptions || ''}
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

            // Setup event handlers for chaining options if present
            this.setupTransformPopupHandlers(type);

            setTimeout(() => popup.classList.add('show'), 100);
        }
    }

    /**
     * Setup event handlers for transform popup chaining options
     */
    setupTransformPopupHandlers(type) {
        if (type === 'convert') {
            const minimizeCheckbox = document.getElementById('minimize-after-convert-option');
            const confirmBtn = document.getElementById('transform-confirm-btn');

            if (minimizeCheckbox && confirmBtn) {
                minimizeCheckbox.addEventListener('change', () => {
                    this.updateTransformButtonText(type);
                });

                // Initialize button text
                this.updateTransformButtonText(type);
            }
        }
    }

    /**
     * Update transform button text based on selected options
     */
    updateTransformButtonText(type) {
        const confirmBtn = document.getElementById('transform-confirm-btn');
        if (!confirmBtn) return;

        if (type === 'convert') {
            const minimizeCheckbox = document.getElementById('minimize-after-convert-option');
            if (minimizeCheckbox && minimizeCheckbox.checked) {
                confirmBtn.textContent = 'Convert to Minimal DFA';
            } else {
                confirmBtn.textContent = 'Convert to DFA';
            }
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
                    chainingOptions: `
                        <div class="chaining-options">
                            <h4>Additional Operations:</h4>
                            <div class="option-group">
                                <div class="checkbox-option">
                                    <input type="checkbox" id="minimize-after-convert-option" class="chain-checkbox">
                                    <label for="minimize-after-convert-option">
                                        <span class="option-title">Minimize DFA</span>
                                        <span class="option-description">Remove redundant states after conversion</span>
                                    </label>
                                </div>
                            </div>
                        </div>
                    `,
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

        // Get chaining options for convert operation
        let shouldMinimize = false;
        if (this.currentTransformType === 'convert') {
            const minimizeCheckbox = document.getElementById('minimize-after-convert-option');
            shouldMinimize = minimizeCheckbox && minimizeCheckbox.checked;
        }

        // Show loading state
        confirmBtn.textContent = 'Processing...';
        confirmBtn.disabled = true;

        try {
            // Create snapshot for undo/redo
            let snapshotCommand = null;
            if (undoRedoManager && !undoRedoManager.isProcessing()) {
                const operationLabel = shouldMinimize ? 'Convert NFA to Minimal DFA' : config.undoLabel;
                snapshotCommand = undoRedoManager.createSnapshotCommand(operationLabel);
            }

            // Call backend API for primary operation
            const response = await fetch(config.apiEndpoint, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ fsa: this.currentTransformData })
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.error || `HTTP error! status: ${response.status}`);
            }

            let result = await response.json();

            // Chain minimization if requested for convert operation
            if (this.currentTransformType === 'convert' && shouldMinimize) {
                confirmBtn.textContent = 'Minimizing DFA...';

                const minimizeResponse = await fetch('/api/minimise-dfa/', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ fsa: result.converted_dfa })
                });

                if (!minimizeResponse.ok) {
                    const errorData = await minimizeResponse.json();
                    throw new Error(errorData.error || `DFA minimization failed: ${minimizeResponse.status}`);
                }

                const minimizeResult = await minimizeResponse.json();
                result.minimised_dfa = minimizeResult.minimised_fsa;
                result.minimization_statistics = minimizeResult.statistics;
            }

            // Hide popup
            this.hideTransformPopup();

            // Replace FSA
            await this.replaceWithTransformedFSA(this.currentTransformType, result, shouldMinimize);

            // Show results
            this.showTransformResults(this.currentTransformType, result, shouldMinimize);

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
    async replaceWithTransformedFSA(type, result, shouldMinimize = false) {
        const originalPositions = this.getOriginalStatePositions();

        await fsaSerializationManager.clearCurrentFSA(this.jsPlumbInstance);

        // Get the transformed FSA data based on type and chaining
        let transformedFSA;
        let description;
        let tags;

        if (type === 'convert' && shouldMinimize && result.minimised_dfa) {
            transformedFSA = result.minimised_dfa;
            description = 'Minimal DFA generated by NFA to DFA conversion followed by minimization';
            tags = ['converted', 'minimized', 'dfa'];
        } else {
            const fsaDataMap = {
                minimize: result.minimised_fsa,
                convert: result.converted_dfa,
                complete: result.completed_fsa,
                complement: result.complement_fsa
            };

            transformedFSA = fsaDataMap[type];
            const config = this.transformConfigs[type];
            description = `FSA generated by ${config.name.toLowerCase()}`;
            tags = config.tags;
        }

        // Calculate positions using layered positioning algorithm
        const newPositions = calculateTransformLayout(transformedFSA);

        // Create serialized data
        const serializedFSA = this.createSerializedFSA(
            transformedFSA,
            newPositions,
            shouldMinimize ? 'Minimal DFA from Conversion' : `${this.transformConfigs[type].name} Result`,
            description,
            tags
        );

        // Load the transformed FSA
        await fsaSerializationManager.deserializeFSA(serializedFSA, this.jsPlumbInstance);
        updateFSAPropertiesDisplay(this.jsPlumbInstance);
    }

    /**
     * Calculate state positions for transformed FSA using layered algorithm
     */
    calculateTransformPositions(type, originalFSA, transformedFSA, originalPositions) {
        console.log(`Calculating positions for ${type} transformation`);
        return calculateTransformLayout(transformedFSA);
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
     * Generate smart state name using first and last approach
     * @param {string} stateId - Original state ID (potentially merged like "S0_S1_S3_S5_S6_S7_S8")
     * @returns {string} - Smart state name
     */
    generateSmartStateName(stateId) {
        // If no underscore, it's not a merged state
        if (!stateId.includes('_')) {
            return stateId;
        }

        const parts = stateId.split('_');

        // If only 2-3 parts, keep the full name
        if (parts.length <= 3) {
            return stateId;
        }

        // Use first and last with underscore
        const first = parts[0];
        const last = parts[parts.length - 1];
        return `${first}_${last}`;
    }

    /**
     * Create serialized FSA data
     */
    createSerializedFSA(fsa, positions, name, description, tags) {
        const statesData = fsa.states.map(stateId => {
            // Apply smart naming for merged states
            const displayName = this.generateSmartStateName(stateId);

            return {
                id: displayName,
                label: displayName,
                isAccepting: fsa.acceptingStates.includes(stateId),
                position: positions[stateId] || { x: 100, y: 100 },
                visual: {
                    className: fsa.acceptingStates.includes(stateId) ? 'accepting-state' : 'state',
                    zIndex: 'auto'
                }
            };
        });

        const transitionsData = [];
        Object.entries(fsa.transitions).forEach(([sourceId, transitions]) => {
            Object.entries(transitions).forEach(([symbol, targets]) => {
                if (targets && targets.length > 0) {
                    const targetId = targets[0];

                    // Apply smart naming to source and target
                    const smartSourceId = this.generateSmartStateName(sourceId);
                    const smartTargetId = this.generateSmartStateName(targetId);

                    const existingTransition = transitionsData.find(t =>
                        t.sourceId === smartSourceId && t.targetId === smartTargetId
                    );

                    if (existingTransition) {
                        if (symbol === '') {
                            existingTransition.hasEpsilon = true;
                        } else {
                            existingTransition.symbols.push(symbol);
                        }
                    } else {
                        transitionsData.push({
                            id: `${smartSourceId}-${smartTargetId}-${symbol}`,
                            sourceId: smartSourceId,
                            targetId: smartTargetId,
                            symbols: symbol === '' ? [] : [symbol],
                            hasEpsilon: symbol === '',
                            visual: {
                                connectorType: smartSourceId === smartTargetId ? 'Bezier' : 'Straight',
                                isCurved: smartSourceId === smartTargetId,
                                labelLocation: 0.3,
                                anchors: smartSourceId === smartTargetId ? ['Top', 'Left'] : ['Continuous', 'Continuous']
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
            startingState: this.generateSmartStateName(fsa.startingState),
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
    showTransformResults(type, result, shouldMinimize = false) {
        if (type === 'convert' && shouldMinimize) {
            this.showChainedConversionResults(result);
        } else {
            const resultHandlers = {
                minimize: () => this.showMinimizationResults(result),
                convert: () => this.showConversionResults(result),
                complete: () => this.showCompletionResults(result),
                complement: () => this.showComplementResults(result)
            };

            resultHandlers[type]();
        }
    }

    /**
     * Show results for chained conversion + minimization
     */
    showChainedConversionResults(result) {
        const conversionStats = result.statistics;
        const minimizationStats = result.minimization_statistics;

        notificationManager.showSuccess(
            'NFA to Minimal DFA Complete',
            `Successfully converted NFA to DFA and minimized.\n` +
            `Conversion: ${conversionStats.original.states_count} → ${conversionStats.converted.states_count} states\n` +
            `Minimization: ${conversionStats.converted.states_count} → ${minimizationStats.minimised.states_count} states\n` +
            `Final result: ${minimizationStats.minimised.states_count} states, ${minimizationStats.minimised.transitions_count} transitions`
        );
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