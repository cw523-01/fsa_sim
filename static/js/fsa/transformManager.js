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
 * Safe state name generator that prevents collisions
 * Used by both transform and regex conversion managers
 */
class SafeStateNameGenerator {
    constructor() {
        this.usedNames = new Set();
    }

    /**
     * Reset the used names tracking (call this at the start of each conversion)
     */
    reset() {
        this.usedNames.clear();
    }

    /**
     * Generate a safe, unique state name from a potentially merged state ID
     * @param {string} stateId - Original state ID (potentially merged like "S0_S1_S3_S5_S6_S7_S8")
     * @returns {string} - Safe, unique state name
     */
    generateSafeStateName(stateId) {
        // If no underscore, it's not a merged state - check for uniqueness anyway
        if (!stateId.includes('_')) {
            return this.ensureUnique(stateId);
        }

        const parts = stateId.split('_');

        // If only 2-3 parts, keep the full name
        if (parts.length <= 3) {
            return this.ensureUnique(stateId);
        }

        // Try the first_last approach first
        const first = parts[0];
        const last = parts[parts.length - 1];
        const firstLastName = `${first}_${last}`;

        if (!this.usedNames.has(firstLastName)) {
            this.usedNames.add(firstLastName);
            return firstLastName;
        }

        // If first_last is taken, try progressively longer names
        for (let endIndex = parts.length - 2; endIndex >= 1; endIndex--) {
            const candidateName = `${first}_${parts.slice(endIndex).join('_')}`;
            if (!this.usedNames.has(candidateName)) {
                this.usedNames.add(candidateName);
                return candidateName;
            }
        }

        // If we still have conflicts, try adding from the beginning
        for (let startIndex = 1; startIndex < parts.length - 1; startIndex++) {
            const candidateName = `${parts.slice(0, startIndex + 1).join('_')}_${last}`;
            if (!this.usedNames.has(candidateName)) {
                this.usedNames.add(candidateName);
                return candidateName;
            }
        }

        // Last resort: use the full original name
        return this.ensureUnique(stateId);
    }

    /**
     * Ensure a name is unique by adding a counter if needed
     * @param {string} baseName - The base name to make unique
     * @returns {string} - Unique name
     */
    ensureUnique(baseName) {
        if (!this.usedNames.has(baseName)) {
            this.usedNames.add(baseName);
            return baseName;
        }

        // Add counter suffix until we find a unique name
        let counter = 1;
        let candidateName;
        do {
            candidateName = `${baseName}_${counter}`;
            counter++;
        } while (this.usedNames.has(candidateName));

        this.usedNames.add(candidateName);
        return candidateName;
    }

    /**
     * Batch process all state names to ensure no collisions
     * @param {Array} stateIds - Array of original state IDs
     * @returns {Object} - Mapping from original ID to safe name
     */
    generateSafeMapping(stateIds) {
        this.reset();
        const mapping = {};

        stateIds.forEach(stateId => {
            mapping[stateId] = this.generateSafeStateName(stateId);
        });

        return mapping;
    }
}

/**
 * FSA Transform Manager - handles FSA transformation operations with unified menu system
 */
class FSATransformManager {
    constructor() {
        this.jsPlumbInstance = null;
        this.currentTransformData = null;
        this.currentTransformType = null;
        this.stateNameGenerator = new SafeStateNameGenerator();

        // NFA minimisation threshold
        this.NFA_MINIMISATION_THRESHOLD = 25;

        // Transform configurations
        this.transformConfigs = {
            minimise: {
                name: 'Minimise DFA',
                apiEndpoint: '/api/minimise-dfa/',
                popupClass: 'minimise',
                headerGradient: 'var(--primary-colour) 0%, var(--primary-hover) 100%',
                buttonColor: 'var(--primary-colour)',
                hoverColor: 'var(--primary-hover)',
                undoLabel: 'Minimise DFA',
                requiresDeterministic: true,
                requiresConnected: true,
                tags: ['minimised']
            },
            convert: {
                name: 'Convert to DFA',
                apiEndpoint: '/api/nfa-to-dfa/',
                popupClass: 'convert',
                headerGradient: 'var(--secondary-colour) 0%, var(--secondary-hover) 100%',
                buttonColor: 'var(--secondary-colour)',
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
                headerGradient: 'var(--accent-colour) 0%, #ef6c00 100%',
                buttonColor: 'var(--accent-colour)',
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
                headerGradient: 'var(--error-colour) 0%, var(--error-hover) 100%',
                buttonColor: 'var(--error-colour)',
                hoverColor: 'var(--error-hover)',
                undoLabel: 'Complement DFA',
                requiresDeterministic: true,
                requiresConnected: true,
                tags: ['complement', 'complemented']
            },
            minimiseNfa: {
                name: 'Minimise NFA',
                apiEndpoint: '/api/minimise-nfa/',
                popupClass: 'minimise-nfa',
                headerGradient: 'var(--secondary-colour) 0%, #1565C0 100%',
                buttonColor: 'var(--secondary-colour)',
                hoverColor: '#1565C0',
                undoLabel: 'Minimise NFA',
                requiresDeterministic: false,
                requiresConnected: true,
                tags: ['minimised', 'nfa']
            },
        };
    }

    /**
     * Initialise with JSPlumb instance
     */
    initialise(jsPlumbInstance) {
        this.jsPlumbInstance = jsPlumbInstance;

        if (!menuManager.initialised) {
            menuManager.initialise();
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
            'menu-minimise-dfa': () => this.executeTransform('minimise'),
            'menu-nfa-to-dfa': () => this.executeTransform('convert'),
            'menu-complete-dfa': () => this.executeTransform('complete'),
            'menu-complement-dfa': () => this.executeTransform('complement'),
            'menu-minimise-nfa': () => this.executeTransform('minimiseNfa')
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
                'm': 'minimise',
                'd': 'convert',
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
            notificationManager.showError(`${config.name} Error`, 'FSA not initialised');
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
     * Show transform popup with modal overlay
     */
    showTransformPopup(type, fsa, propertiesResult) {
        const config = this.transformConfigs[type];
        const summary = propertiesResult.summary;
        const properties = propertiesResult.properties;

        // Remove any existing popup and overlay
        const existingPopup = document.getElementById('transform-operation-popup');
        if (existingPopup) existingPopup.remove();

        const existingOverlay = document.getElementById('transform-modal-overlay');
        if (existingOverlay) existingOverlay.remove();

        // Create modal overlay
        const overlay = document.createElement('div');
        overlay.id = 'transform-modal-overlay';
        overlay.className = 'modal-overlay';
        overlay.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background-color: rgba(0, 0, 0, 0.6);
            z-index: var(--z-modals);
            display: flex;
            align-items: center;
            justify-content: center;
            opacity: 0;
            transition: opacity 0.3s ease;
        `;

        // Generate popup content based on type
        const popupContent = this.generatePopupContent(type, summary, properties);

        const popup = document.createElement('div');
        popup.id = 'transform-operation-popup';
        popup.className = `file-operation-popup ${config.popupClass}`;
        popup.style.cssText = `
            position: relative;
            transform: scale(0.9);
            transition: transform 0.3s ease;
            margin: 20px;
            max-height: calc(100vh - 40px);
            overflow: hidden;
            display: flex;
            flex-direction: column;
        `;

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
            <div class="file-operation-content scrollable-content">
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

        // Add popup to overlay
        overlay.appendChild(popup);

        // Add overlay to body
        document.body.appendChild(overlay);

        // Setup event handlers for chaining options if present
        this.setupTransformPopupHandlers(type);

        // Close modal when clicking overlay (but not popup)
        overlay.addEventListener('click', (e) => {
            if (e.target === overlay) {
                this.hideTransformPopup();
            }
        });

        // Prevent popup clicks from closing modal
        popup.addEventListener('click', (e) => {
            e.stopPropagation();
        });

        // Show with animation
        setTimeout(() => {
            overlay.classList.add('show');
            overlay.style.opacity = '1';
            popup.style.opacity = '1';
        }, 10);
    }

    /**
     * Setup event handlers for transform popup chaining options
     */
    setupTransformPopupHandlers(type) {
        if (type === 'convert') {
            const minimiseCheckbox = document.getElementById('minimise-after-convert-option');
            const confirmBtn = document.getElementById('transform-confirm-btn');

            if (minimiseCheckbox && confirmBtn) {
                minimiseCheckbox.addEventListener('change', () => {
                    this.updateTransformButtonText(type);
                });

                // Initialise button text
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
            const minimiseCheckbox = document.getElementById('minimise-after-convert-option');
            if (minimiseCheckbox && minimiseCheckbox.checked) {
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
            minimise: () => ({
                description: `<div class="file-operation-description">
                    Minimising the DFA will replace the current automaton with an equivalent minimal DFA using Hopcroft's algorithm.
                </div>`,
                statesInfo: baseStatesInfo,
                warningSection: this.generateWarningSection(
                    'This operation will permanently replace the current DFA with its minimal equivalent. ' +
                    'The minimised DFA will have the same behavior but potentially fewer states.'
                ),
                confirmButtonText: 'Minimise DFA'
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
                                    <input type="checkbox" id="minimise-after-convert-option" class="chain-checkbox">
                                    <label for="minimise-after-convert-option">
                                        <span class="option-title">Minimise DFA</span>
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
            },

            minimiseNfa: () => {
                const isDeterministic = properties.deterministic;
                const hasEpsilon = summary.has_epsilon_transitions;
                const stateCount = summary.total_states;

                let typeDesc = isDeterministic && !hasEpsilon ? 'DFA (deterministic)' :
                              isDeterministic && hasEpsilon ? 'Deterministic automaton with ε-transitions' :
                              'NFA (non-deterministic)';

                let description = `
                    <div class="file-operation-description">
                        Minimising the NFA will create an equivalent automaton with potentially fewer states using advanced algorithms.
                        
                        <div class="limitation-highlight">
                            <div class="limitation-header">
                                <span>Important Algorithm Limitation</span>
                            </div>
                            <div class="limitation-content">
                                <strong>NFA minimisation is a computationally difficult problem.</strong> Unlike DFA minimisation, which guarantees an optimal result, this NFA minimisation technique uses heuristic approaches that may not always find the absolute minimum.
                            </div>
                            <ul class="limitation-points">
                                <li>The result <strong>may not be the smallest possible</strong> equivalent NFA</li>
                                <li>The algorithm provides a <strong>good approximation</strong> in most practical cases</li>
                                <li>Some reduction is usually achieved, but <strong>optimality is not guaranteed</strong></li>
                                <li>Larger NFAs may see more variation in results</li>
                            </ul>
                        </div>
            
                        <div class="algorithm-explanation">
                            <h4>Algorithm Details</h4>
                            <p>Uses a hybrid approach combining the Kameda-Weiner algorithm with determinisation and DFA minimisation techniques. The method adapts based on automaton size and complexity for improved practical results.</p>
                        </div>
                    </div>
                `;

                // Add size-specific warnings for larger NFAs
                let sizeWarningSection = '';
                if (stateCount > this.NFA_MINIMISATION_THRESHOLD) {
                    sizeWarningSection = `
                        <div class="size-threshold-warning">
                            <div class="size-threshold-content">
                                <div class="size-threshold-title">Large NFA Detected</div>
                                <div class="size-threshold-text">
                                    With ${stateCount} states, this NFA is above the optimal threshold (${this.NFA_MINIMISATION_THRESHOLD} states). 
                                    A simplified approach may be used, which could provide less optimal results.
                                </div>
                            </div>
                        </div>
                    `;
                }

                let statesInfo = `
                    <div class="states-info">
                        Current FSA: <span class="states-count">${typeDesc}</span><br>
                        <span class="states-count">${summary.total_states} states</span> 
                        and <span class="states-count">${transitionCount} transitions</span>
                    </div>
                `;

                let warningText = `This operation will permanently replace the current automaton with a minimised equivalent. 
                                 The minimised NFA will have the same behavior but potentially fewer states.
                                 <br><br>
                                 <strong>Due to the theoretical complexity of NFA minimisation</strong>, the result may not be the absolute minimum possible, 
                                 but significant reduction is often achieved in practice.`;

                return {
                    description: description,
                    statesInfo: statesInfo + sizeWarningSection,
                    warningSection: this.generateWarningSection(warningText),
                    confirmButtonText: 'Minimise NFA'
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
                <div class="info-text">
                    <strong>Info:</strong> ${text}
                </div>
            </div>
        `;
    }

    /**
     * Hide transform popup and overlay
     */
    hideTransformPopup() {
        const overlay = document.getElementById('transform-modal-overlay');
        const popup = document.getElementById('transform-operation-popup');

        if (overlay && popup) {
            // Animate out
            overlay.classList.remove('show');
            overlay.style.opacity = '0';

            setTimeout(() => {
                if (overlay.parentNode) {
                    overlay.parentNode.removeChild(overlay);
                }
            }, 300);
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
        let shouldMinimise = false;
        if (this.currentTransformType === 'convert') {
            const minimiseCheckbox = document.getElementById('minimise-after-convert-option');
            shouldMinimise = minimiseCheckbox && minimiseCheckbox.checked;
        }

        // Show loading state
        confirmBtn.textContent = 'Processing...';
        confirmBtn.disabled = true;

        try {
            // Create snapshot for undo/redo
            let snapshotCommand = null;
            if (undoRedoManager && !undoRedoManager.isProcessing()) {
                const operationLabel = shouldMinimise ? 'Convert NFA to Minimal DFA' : config.undoLabel;
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
            let primaryHasChanges = this.checkForChanges(this.currentTransformType, result);
            let minimisationPerformed = false;
            let minimisationHasChanges = false;

            // Chain minimisation if requested for convert operation
            if (this.currentTransformType === 'convert' && shouldMinimise) {
                confirmBtn.textContent = 'Minimising DFA...';

                const minimiseResponse = await fetch('/api/minimise-dfa/', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ fsa: result.converted_dfa })
                });

                if (!minimiseResponse.ok) {
                    const errorData = await minimiseResponse.json();
                    throw new Error(errorData.error || `DFA minimisation failed: ${minimiseResponse.status}`);
                }

                const minimiseResult = await minimiseResponse.json();
                result.minimised_dfa = minimiseResult.minimised_fsa;
                result.minimisation_statistics = minimiseResult.statistics;
                minimisationPerformed = true;

                // Check if minimisation made changes
                minimisationHasChanges = !minimiseResult.statistics.reduction.is_already_minimal;
            }

            // Determine overall changes: either primary operation OR minimization made changes
            const hasOverallChanges = primaryHasChanges || minimisationHasChanges ||
                                    (this.currentTransformType === 'complement'); // Complement always makes changes

            // Hide popup
            this.hideTransformPopup();

            // Replace FSA if there are any changes from either operation
            if (hasOverallChanges) {
                // Replace FSA
                await this.replaceWithTransformedFSA(this.currentTransformType, result, shouldMinimise && minimisationPerformed);
            }

            // Show results with detailed change information
            this.showTransformResults(this.currentTransformType, result, shouldMinimise, minimisationPerformed, {
                primaryHasChanges,
                minimisationHasChanges,
                hasOverallChanges
            });

            // Finish undo/redo snapshot only if there were overall changes
            if (snapshotCommand) {
                if (hasOverallChanges) {
                    undoRedoManager.finishSnapshotCommand(snapshotCommand);
                } else {
                    // Cancel the snapshot since no changes were made
                    undoRedoManager.cancelSnapshotCommand(snapshotCommand);
                }
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
     * Check if the transform operation resulted in actual changes
     * @param {string} type - Transform type
     * @param {Object} result - Transform result
     * @returns {boolean} - Whether there are actual changes
     */
    checkForChanges(type, result) {
        switch (type) {
            case 'minimise':
                return result.statistics && !result.statistics.reduction.is_already_minimal;

            case 'convert':
                // Check if it was already deterministic and had no epsilon transitions
                return result.statistics &&
                       (!result.statistics.conversion.was_already_deterministic ||
                        result.statistics.conversion.epsilon_transitions_removed);

            case 'complete':
                return result.statistics && !result.statistics.completion.was_already_complete;

            case 'complement':
                // Complement always makes changes (swaps accepting states)
                return true;

            case 'minimiseNfa':
                return result.statistics && !result.statistics.reduction.is_already_minimal;

            default:
                return true; // Default to assuming changes for unknown types
        }
    }

    /**
     * Replace current FSA with transformed version
     */
    async replaceWithTransformedFSA(type, result, shouldMinimise = false) {
        const originalPositions = this.getOriginalStatePositions();

        await fsaSerializationManager.clearCurrentFSA(this.jsPlumbInstance);

        // Get the transformed FSA data based on type and chaining
        let transformedFSA;
        let description;
        let tags;

        if (type === 'convert' && shouldMinimise && result.minimised_dfa) {
            transformedFSA = result.minimised_dfa;
            description = 'Minimal DFA generated by NFA to DFA conversion followed by minimisation';
            tags = ['converted', 'minimised', 'dfa'];
        } else {
            const fsaDataMap = {
                minimise: result.minimised_fsa,
                convert: result.converted_dfa,
                complete: result.completed_fsa,
                complement: result.complement_fsa,
                minimiseNfa: result.minimised_fsa
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
            shouldMinimise ? 'Minimal DFA from Conversion' : `${this.transformConfigs[type].name} Result`,
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
     * Generate safe state name with collision detection
     * @param {string} stateId - Original state ID (potentially merged like "S0_S1_S3_S5_S6_S7_S8")
     * @param {Array} allStateIds - All state IDs to check for collisions
     * @returns {string} - Safe state name
     */
    generateSmartStateName(stateId, allStateIds = null) {
        // If we have all state IDs, use batch processing for complete safety
        if (allStateIds) {
            const mapping = this.stateNameGenerator.generateSafeMapping(allStateIds);
            return mapping[stateId];
        }

        // Fallback for single state processing
        return this.stateNameGenerator.generateSafeStateName(stateId);
    }

    /**
     * Create serialized FSA data
     */
    createSerializedFSA(fsa, positions, name, description, tags) {
        // Reset the name generator and create safe mapping for all states
        this.stateNameGenerator.reset();
        const stateNameMapping = this.stateNameGenerator.generateSafeMapping(fsa.states);

        const statesData = fsa.states.map(stateId => {
            // Use the safe name from the mapping
            const safeName = stateNameMapping[stateId];

            return {
                id: safeName,
                label: safeName,
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
                    targets.forEach(targetId => {  // Process ALL targets, not just the first one
                        // Apply safe naming to source and target using the mapping
                        const smartSourceId = stateNameMapping[sourceId];
                        const smartTargetId = stateNameMapping[targetId];

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
                                id: `${smartSourceId}-${smartTargetId}-${symbol || 'epsilon'}`,
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
                    });
                }
            });
        });

        return {
            version: "1.0.0",
            timestamp: new Date().toISOString(),
            metadata: { name, description, creator: "FSA Simulator", tags },
            states: statesData,
            transitions: transitionsData,
            startingState: stateNameMapping[fsa.startingState],
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
    showTransformResults(type, result, shouldMinimise = false, minimisationPerformed = false, changeInfo = null) {
        if (type === 'convert' && shouldMinimise && minimisationPerformed) {
            this.showChainedConversionResults(result, changeInfo);
        } else {
            const resultHandlers = {
                minimise: () => this.showMinimisationResults(result),
                convert: () => this.showConversionResults(result),
                complete: () => this.showCompletionResults(result),
                complement: () => this.showComplementResults(result),
                minimiseNfa: () => this.showNfaMinimisationResults(result)
            };

            resultHandlers[type]();
        }
    }

    /**
     * Show results for chained conversion + minimisation
     */
    showChainedConversionResults(result, changeInfo = null) {
        const conversionStats = result.statistics;
        const minimisationStats = result.minimisation_statistics;

        // Determine what actually happened
        const conversionMadeChanges = changeInfo ? changeInfo.primaryHasChanges :
                                     !conversionStats.conversion.was_already_deterministic ||
                                     conversionStats.conversion.epsilon_transitions_removed;

        const minimisationMadeChanges = changeInfo ? changeInfo.minimisationHasChanges :
                                       !minimisationStats.reduction.is_already_minimal;

        let title, message;

        if (!conversionMadeChanges && !minimisationMadeChanges) {
            title = 'Already Optimal DFA';
            message = 'The FSA was already a minimal DFA. No changes were made.';
            notificationManager.showInfo(title, message);
        } else if (conversionMadeChanges && !minimisationMadeChanges) {
            title = 'Conversion Complete, Already Minimal';
            message = `Converted to DFA (${conversionStats.original.states_count} → ${conversionStats.converted.states_count} states). ` +
                     `The resulting DFA was already minimal.`;
            notificationManager.showSuccess(title, message);
        } else if (!conversionMadeChanges && minimisationMadeChanges) {
            title = 'Minimisation Applied to DFA';
            message = `The FSA was already deterministic, but minimisation reduced it from ` +
                     `${minimisationStats.original.states_count} → ${minimisationStats.minimised.states_count} states ` +
                     `(${minimisationStats.reduction.states_reduction_percentage}% reduction).`;
            notificationManager.showSuccess(title, message);
        } else {
            title = 'NFA to Minimal DFA Complete';
            message = `Successfully converted NFA to DFA and minimised.\n` +
                     `Conversion: ${conversionStats.original.states_count} → ${conversionStats.converted.states_count} states\n` +
                     `Minimisation: ${conversionStats.converted.states_count} → ${minimisationStats.minimised.states_count} states\n` +
                     `Final result: ${minimisationStats.minimised.states_count} states, ${minimisationStats.minimised.transitions_count} transitions`;
            notificationManager.showSuccess(title, message);
        }
    }

    /**
     * Result display methods
     */
    showMinimisationResults(result) {
        const stats = result.statistics;
        if (stats.reduction.is_already_minimal) {
            notificationManager.showInfo(
                'DFA Already Minimal',
                'The DFA was already in minimal form. No changes were made.'
            );
        } else {
            notificationManager.showSuccess(
                'DFA Minimised Successfully',
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
     * Show results for NFA minimisation
     */
    showNfaMinimisationResults(result) {
        const details = result.minimisation_details;
        const stats = result.statistics;

        if (stats.reduction.is_already_minimal) {
            notificationManager.showInfo(
                'Could not minimise NFA',
                'A smaller form of the NFA could not be found. NFA may already be minimal.'
            );
        } else {
            let message = `Reduced from ${stats.original.states_count} to ${stats.minimised.states_count} states (${stats.reduction.states_reduction_percentage}% reduction).`;

            // Add method information
            if (details.method_used.includes('optimal')) {
                message += ' Optimal result achieved.';
            } else {
                message += ' Heuristic minimisation applied.';
            }

            notificationManager.showSuccess(
                'NFA Minimised Successfully',
                message
            );
        }
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
}


// Create and export singleton instance
export const fsaTransformManager = new FSATransformManager();

// Export the SafeStateNameGenerator class for use in other managers
export { SafeStateNameGenerator };

// Make globally available
window.fsaTransformManager = fsaTransformManager;

// Export class for potential multiple instances
export { FSATransformManager };