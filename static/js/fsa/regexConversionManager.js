import { fsaSerializationManager} from './fsaSerializationManager.js';
import { notificationManager } from './notificationManager.js';
import { controlLockManager } from './controlLockManager.js';
import { undoRedoManager } from './undoRedoManager.js';
import { menuManager } from './menuManager.js';
import { updateFSAPropertiesDisplay } from './fsaPropertyChecker.js';
import { calculateTransformLayout } from './positioningUtils.js';

/**
 * REGEX Conversion Manager - handles REGEX to FSA conversion operations
 */
class RegexConversionManager {
    constructor() {
        this.jsPlumbInstance = null;
        this.currentRegexData = null;
        this.currentRegexInput = null;

        // Conversion configuration
        this.conversionConfig = {
            name: 'REGEX to FSA',
            apiEndpoint: '/api/regex-to-epsilon-nfa/',
            popupClass: 'regex-convert',
            headerGradient: 'var(--secondary-color) 0%, var(--secondary-hover) 100%',
            buttonColor: 'var(--secondary-color)',
            hoverColor: 'var(--secondary-hover)',
            undoLabel: 'Convert REGEX to ε-NFA',
            tags: ['regex-generated', 'epsilon-nfa']
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

        // Register REGEX menu with the universal menu manager
        menuManager.registerMenu('regex', {
            buttonId: 'regex-menu-button',
            dropdownId: 'regex-dropdown'
        });

        this.setupRegexEventListeners();
        this.setupKeyboardShortcuts();
    }

    /**
     * Setup REGEX menu event listeners
     */
    setupRegexEventListeners() {
        menuManager.registerMenuItems({
            'menu-regex-to-fsa': () => this.executeRegexConversion()
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

            // Ctrl+R for REGEX conversion
            if ((e.ctrlKey || e.metaKey) && e.key === 'r') {
                e.preventDefault();
                this.executeRegexConversion();
            }
        });
    }

    /**
     * Execute REGEX conversion operation
     */
    async executeRegexConversion() {
        if (!this.jsPlumbInstance) {
            notificationManager.showError(`${this.conversionConfig.name} Error`, 'FSA not initialized');
            return;
        }

        if (controlLockManager.isControlsLocked()) {
            notificationManager.showWarning(`Cannot ${this.conversionConfig.name}`, 'Cannot perform operation while simulation is running');
            return;
        }

        // Show REGEX input popup
        this.showRegexInputPopup();
    }

    /**
     * Show REGEX input popup
     */
    showRegexInputPopup() {
        const config = this.conversionConfig;

        // Remove any existing popup
        const existingPopup = document.getElementById('regex-operation-popup');
        if (existingPopup) existingPopup.remove();

        const popup = document.createElement('div');
        popup.id = 'regex-operation-popup';
        popup.className = `file-operation-popup ${config.popupClass}`;

        popup.innerHTML = `
            <div class="popup-header" style="background: linear-gradient(135deg, ${config.headerGradient});">
                <div class="popup-title">
                    <div class="popup-icon">
                        <img src="static/img/alert.png" alt="Warning" style="width: 20px; height: 20px;">
                    </div>
                    <span>${config.name}</span>
                </div>
                <button class="popup-close" onclick="regexConversionManager.hideRegexPopup()">×</button>
            </div>
            <div class="file-operation-content">
                <div class="file-operation-description">
                    Enter a regular expression to convert it into an equivalent ε-NFA using Thompson's construction algorithm.
                </div>
                
                <div class="form-group">
                    <label for="regex-input-field">Regular Expression:</label>
                    <input type="text" id="regex-input-field" placeholder="e.g., (a|b)*abb" maxlength="200">
                    <div class="input-help">
                        Supported operators: | (union), * (Kleene star), + (one or more), () (grouping), ε (epsilon)
                    </div>
                    <div class="input-error" id="regex-input-error">Please enter a valid regular expression</div>
                </div>
    
                <div class="examples-section">
                    <div class="examples-dropdown">
                        <label for="examples-select">Examples:</label>
                        <select id="examples-select" class="examples-select">
                            <option value="">Choose an example...</option>
                            <option value="a*">a* - Zero or more 'a's</option>
                            <option value="(a|b)+">&#40;a|b&#41;+ - One or more 'a' or 'b'</option>
                            <option value="a*b+">a*b+ - Zero or more 'a's, then one or more 'b's</option>
                            <option value="(ab)*|(ba)*">&#40;ab&#41;*|&#40;ba&#41;* - Zero or more "ab" or zero or more "ba"</option>
                            <option value="(a|b)*abb">&#40;a|b&#41;*abb - Strings ending in "abb"</option>
                            <option value="a+b*">a+b* - One or more 'a's, then zero or more 'b's</option>
                        </select>
                    </div>
                </div>
    
                <div class="warning-section">
                    <span class="warning-icon">⚠️</span>
                    <div class="warning-text">
                        <strong>Warning:</strong> This operation will replace the current FSA with the generated ε-NFA. 
                        Consider exporting your current FSA first if you want to save it.
                    </div>
                </div>
            </div>
            <div class="file-operation-actions">
                <button class="file-action-btn cancel" onclick="regexConversionManager.hideRegexPopup()">
                    Cancel
                </button>
                <button class="file-action-btn primary" id="regex-convert-btn" 
                        onclick="regexConversionManager.confirmRegexConversion()"
                        style="background: ${config.buttonColor};">
                    Convert to ε-NFA
                </button>
            </div>
        `;

        const canvas = document.getElementById('fsa-canvas');
        if (canvas) {
            canvas.appendChild(popup);

            // Setup event handlers
            this.setupRegexPopupHandlers();

            // Trigger show animation
            setTimeout(() => {
                popup.classList.add('show');
                // Focus on regex input
                const regexInput = document.getElementById('regex-input-field');
                if (regexInput) {
                    regexInput.focus();
                }
            }, 100);
        }
    }

    /**
     * Setup event handlers for REGEX popup
     */
    setupRegexPopupHandlers() {
        const regexInput = document.getElementById('regex-input-field');
        const regexError = document.getElementById('regex-input-error');
        const convertBtn = document.getElementById('regex-convert-btn');
        const examplesSelect = document.getElementById('examples-select');

        if (regexInput) {
            regexInput.addEventListener('input', () => {
                const value = regexInput.value.trim();
                const formGroup = regexInput.closest('.form-group');

                if (value.length === 0) {
                    formGroup.classList.remove('valid');
                    formGroup.classList.add('invalid');
                    regexError.classList.add('show');
                    convertBtn.classList.add('disabled');
                } else {
                    formGroup.classList.remove('invalid');
                    formGroup.classList.add('valid');
                    regexError.classList.remove('show');
                    convertBtn.classList.remove('disabled');
                }
            });

            // Enter key to convert
            regexInput.addEventListener('keydown', (e) => {
                if (e.key === 'Enter' && !convertBtn.classList.contains('disabled')) {
                    this.confirmRegexConversion();
                }
            });
        }

        // Handle examples dropdown
        if (examplesSelect) {
            examplesSelect.addEventListener('change', (e) => {
                const selectedValue = e.target.value;
                if (selectedValue && regexInput) {
                    regexInput.value = selectedValue;
                    regexInput.dispatchEvent(new Event('input')); // Trigger validation
                    regexInput.focus();
                    // Reset dropdown to placeholder
                    examplesSelect.value = '';
                }
            });
        }
    }

    /**
     * Hide REGEX popup
     */
    hideRegexPopup() {
        const popup = document.getElementById('regex-operation-popup');
        if (popup) {
            popup.classList.add('hide');
            setTimeout(() => popup.parentNode?.removeChild(popup), 300);
        }
        // Clear any stored data
        this.clearRegexData();
    }

    /**
     * Clear regex data after operation
     */
    clearRegexData() {
        this.currentRegexData = null;
        this.currentRegexInput = null;
    }

    /**
     * Confirm and execute REGEX conversion
     */
    async confirmRegexConversion() {
        const convertBtn = document.getElementById('regex-convert-btn');
        const regexInput = document.getElementById('regex-input-field');

        if (!convertBtn || !regexInput || convertBtn.classList.contains('disabled')) return;

        const regexString = regexInput.value.trim();
        if (!regexString) {
            notificationManager.showError('Invalid Input', 'Please enter a regular expression');
            return;
        }

        const config = this.conversionConfig;

        // Show loading state
        convertBtn.textContent = 'Converting...';
        convertBtn.disabled = true;

        try {
            // Store regex input for later use
            this.currentRegexInput = regexString;

            // Create snapshot for undo/redo
            let snapshotCommand = null;
            if (undoRedoManager && !undoRedoManager.isProcessing()) {
                snapshotCommand = undoRedoManager.createSnapshotCommand(config.undoLabel);
            }

            // Call backend API
            const response = await fetch(config.apiEndpoint, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ regex: regexString })
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.error || `HTTP error! status: ${response.status}`);
            }

            const result = await response.json();

            // Hide popup
            this.hideRegexPopup();

            // Replace FSA with generated ε-NFA
            await this.replaceWithGeneratedNFA(result);

            // Show results
            this.showConversionResults(result);

            // Finish undo/redo snapshot
            if (snapshotCommand) {
                undoRedoManager.finishSnapshotCommand(snapshotCommand);
            }

            // Clear regex data after successful operation
            this.clearRegexData();

        } catch (error) {
            console.error('REGEX conversion error:', error);
            notificationManager.showError(`${config.name} Failed`, error.message);

            // Reset button state
            convertBtn.textContent = 'Convert to ε-NFA';
            convertBtn.disabled = false;

            // Don't clear regex data on error - user might retry
        }
    }

    /**
     * Replace current FSA with generated ε-NFA
     */
    async replaceWithGeneratedNFA(result) {
        // Clear current FSA
        await fsaSerializationManager.clearCurrentFSA(this.jsPlumbInstance);

        const epsilonNFA = result.epsilon_nfa;
        const config = this.conversionConfig;

        // Calculate positions using NEW layered positioning algorithm
        const positions = this.calculateNFAPositions(epsilonNFA);

        // Create serialized data
        const serializedFSA = this.createSerializedNFA(
            epsilonNFA,
            positions,
            `REGEX: ${this.currentRegexInput}`,
            `ε-NFA generated from regular expression: ${this.currentRegexInput}`,
            config.tags
        );

        // Load the generated ε-NFA
        await fsaSerializationManager.deserializeFSA(serializedFSA, this.jsPlumbInstance);
        updateFSAPropertiesDisplay(this.jsPlumbInstance);
    }

    /**
     * Calculate positions for NFA states using NEW layered positioning algorithm
     */
    calculateNFAPositions(epsilonNFA) {
        console.log('Using layered hierarchical positioning for REGEX conversion');

        // Use the new layered hierarchical layout for consistent, readable positioning
        return calculateTransformLayout(epsilonNFA);

        // OLD CODE - Keep commented for reference:
        // return calculateFreshLayout(epsilonNFA);
    }

    /**
     * Create serialized NFA data
     */
    createSerializedNFA(epsilonNFA, positions, name, description, tags) {
        const statesData = epsilonNFA.states.map(stateId => ({
            id: stateId,
            label: stateId,
            isAccepting: epsilonNFA.acceptingStates.includes(stateId),
            position: positions[stateId] || { x: 100, y: 100 },
            visual: {
                className: epsilonNFA.acceptingStates.includes(stateId) ? 'accepting-state' : 'state',
                zIndex: 'auto'
            }
        }));

        const transitionsData = [];
        Object.entries(epsilonNFA.transitions).forEach(([sourceId, transitions]) => {
            Object.entries(transitions).forEach(([symbol, targets]) => {
                if (targets && targets.length > 0) {
                    targets.forEach(targetId => {
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
                                id: `${sourceId}-${targetId}-${symbol || 'epsilon'}`,
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
                    });
                }
            });
        });

        return {
            version: "1.0.0",
            timestamp: new Date().toISOString(),
            metadata: { name, description, creator: "FSA Simulator - REGEX Converter", tags },
            states: statesData,
            transitions: transitionsData,
            startingState: epsilonNFA.startingState,
            canvasProperties: {
                dimensions: { width: 800, height: 600 },
                viewport: { scrollLeft: 0, scrollTop: 0 },
                zoom: 1.0,
                backgroundColor: '#ffffff'
            }
        };
    }

    /**
     * Show conversion results
     */
    showConversionResults(result) {
        const stats = result.statistics;
        const regexString = this.currentRegexInput || 'regular expression';

        notificationManager.showSuccess(
            'REGEX Conversion Complete',
            `Successfully converted "${regexString}" to ε-NFA with ${stats.states_count} states and ${stats.transitions_count} transitions.`
        );
    }

    /**
     * Update menu states based on control lock status
     */
    updateMenuStates(locked) {
        menuManager.updateMenuStates(locked);
    }
}

// Create and export singleton instance
export const regexConversionManager = new RegexConversionManager();

// Make globally available
window.regexConversionManager = regexConversionManager;

// Export class for potential multiple instances
export { RegexConversionManager };