import { fsaSerializationManager } from './fsaSerializationManager.js';
import { notificationManager } from './notificationManager.js';
import { controlLockManager } from './controlLockManager.js';
import { undoRedoManager } from './undoRedoManager.js';
import { menuManager } from './menuManager.js';
import { convertFSAToBackendFormat } from './backendIntegration.js';

/**
 * Equivalence Manager - handles equivalence checking operations
 */
class EquivalenceManager {
    constructor() {
        this.jsPlumbInstance = null;
        this.currentOperationType = null;

        // Equivalence checking configurations
        this.equivalenceConfigs = {
            fsaFsa: {
                name: 'Compare Two FSA',
                popupClass: 'fsa-fsa-equiv',
                headerGradient: 'var(--primary-colour) 0%, var(--primary-hover) 100%',
                buttonColor: 'var(--primary-colour)',
                hoverColor: 'var(--primary-hover)',
                description: 'Compare two FSAs to check if they accept the same language. You can upload files or use the current FSA on the canvas.',
                endpoint: '/api/check-fsa-equivalence/'
            },
            regexFsa: {
                name: 'Compare REGEX with FSA',
                popupClass: 'regex-fsa-equiv',
                headerGradient: 'var(--secondary-colour) 0%, var(--secondary-hover) 100%',
                buttonColor: 'var(--secondary-colour)',
                hoverColor: 'var(--secondary-hover)',
                description: 'Enter a regular expression and compare it with an FSA.',
                endpoint: '/api/check-fsa-regex-equivalence/'
            },
            regexRegex: {
                name: 'Compare Two REGEX',
                popupClass: 'regex-regex-equiv',
                headerGradient: 'var(--accent-colour) 0%, #ef6c00 100%',
                buttonColor: 'var(--accent-colour)',
                hoverColor: '#ef6c00',
                description: 'Enter two regular expressions to check if they represent the same language.',
                endpoint: '/api/check-regex-equivalence/'
            }
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

        // Register equivalence menu with the universal menu manager
        menuManager.registerMenu('equivalence', {
            buttonId: 'equivalence-menu-button',
            dropdownId: 'equivalence-dropdown'
        });

        this.setupEquivalenceEventListeners();
    }

    /**
     * Setup equivalence menu event listeners
     */
    setupEquivalenceEventListeners() {
        menuManager.registerMenuItems({
            'menu-fsa-fsa-equiv': () => this.executeEquivalenceCheck('fsaFsa'),
            'menu-regex-fsa-equiv': () => this.executeEquivalenceCheck('regexFsa'),
            'menu-regex-regex-equiv': () => this.executeEquivalenceCheck('regexRegex')
        });
    }

    /**
     * Execute equivalence check operation
     */
    async executeEquivalenceCheck(type) {
        const config = this.equivalenceConfigs[type];
        if (!config) {
            console.error(`Unknown equivalence check type: ${type}`);
            return;
        }

        if (!this.jsPlumbInstance) {
            notificationManager.showError(`${config.name} Error`, 'FSA not initialised');
            return;
        }

        if (controlLockManager.isControlsLocked()) {
            notificationManager.showWarning(`Cannot ${config.name}`, 'Cannot perform operation while simulation is running');
            return;
        }

        this.currentOperationType = type;
        this.showEquivalencePopup(type);
    }

    /**
     * Get current FSA info for display
     */
    getCurrentFSAInfo() {
        const statesCount = document.querySelectorAll('.state, .accepting-state').length;
        const edgesCount = this.jsPlumbInstance ?
            this.jsPlumbInstance.getAllConnections().filter(conn =>
                !conn.canvas || !conn.canvas.classList.contains('starting-connection')
            ).length : 0;

        return { statesCount, edgesCount, hasStates: statesCount > 0 };
    }

    /**
     * Show equivalence checking popup
     */
    showEquivalencePopup(type) {
        const config = this.equivalenceConfigs[type];

        // Remove any existing popup
        const existingPopup = document.getElementById('equivalence-operation-popup');
        if (existingPopup) existingPopup.remove();

        const popup = document.createElement('div');
        popup.id = 'equivalence-operation-popup';
        popup.className = `file-operation-popup ${config.popupClass}`;

        const popupContent = this.generatePopupContent(type);

        popup.innerHTML = `
            <div class="popup-header" style="background: linear-gradient(135deg, ${config.headerGradient});">
                <div class="popup-title">
                    <div class="popup-icon">
                        <img src="static/img/alert.png" alt="Compare" style="width: 20px; height: 20px;">
                    </div>
                    <span>${config.name}</span>
                </div>
                <button class="popup-close" onclick="equivalenceManager.hideEquivalencePopup()">×</button>
            </div>
            <div class="file-operation-content scrollable-content">
                ${popupContent.description}
                ${popupContent.formContent}
                ${popupContent.infoSection || ''}
                
                <!-- Results Section -->
                <div class="equivalence-results-section" id="equivalence-results" style="display: none;">
                    <div class="results-header">
                        <h4 id="results-title">Equivalence Check Result</h4>
                    </div>
                    <div class="results-content" id="results-content">
                        <!-- Results will be populated here -->
                    </div>
                </div>
            </div>
            <div class="file-operation-actions">
                <button class="file-action-btn cancel" onclick="equivalenceManager.hideEquivalencePopup()">
                    Close
                </button>
                <button class="file-action-btn primary" id="equivalence-check-btn" 
                        onclick="equivalenceManager.confirmEquivalenceCheck()"
                        style="background: ${config.buttonColor};" disabled>
                    ${popupContent.confirmButtonText}
                </button>
            </div>
        `;

        const canvas = document.getElementById('fsa-canvas');
        if (canvas) {
            canvas.appendChild(popup);

            // Setup event handlers
            this.setupEquivalencePopupHandlers(type);

            setTimeout(() => popup.classList.add('show'), 100);
        }
    }

    /**
     * Generate popup content based on equivalence check type
     */
    generatePopupContent(type) {
        const config = this.equivalenceConfigs[type];
        const fsaInfo = this.getCurrentFSAInfo();

        const contentGenerators = {
            fsaFsa: () => {
                const currentFSAOption = fsaInfo.hasStates ?
                    `<div class="fsa-source-option">
                        <input type="radio" id="fsa1-current" name="fsa1-source" value="current" class="fsa-source-radio">
                        <label for="fsa1-current" class="fsa-source-label">
                            <span class="option-title">Use Current FSA</span>
                            <span class="option-description">${fsaInfo.statesCount} states, ${fsaInfo.edgesCount} transitions</span>
                        </label>
                    </div>` :
                    `<div class="fsa-source-option disabled">
                        <input type="radio" id="fsa1-current" name="fsa1-source" value="current" class="fsa-source-radio" disabled>
                        <label for="fsa1-current" class="fsa-source-label">
                            <span class="option-title">Use Current FSA</span>
                            <span class="option-description">No FSA on canvas</span>
                        </label>
                    </div>`;

                // FSA2 can only be from file (no current FSA option)
                return {
                    description: `<div class="file-operation-description">${config.description}</div>`,
                    formContent: `
                        <div class="form-group">
                            <label>First FSA:</label>
                            <div class="fsa-source-options">
                                <div class="fsa-source-option">
                                    <input type="radio" id="fsa1-file" name="fsa1-source" value="file" class="fsa-source-radio" checked>
                                    <label for="fsa1-file" class="fsa-source-label">
                                        <span class="option-title">Upload File</span>
                                        <span class="option-description">Choose a JSON FSA file</span>
                                    </label>
                                </div>
                                ${currentFSAOption}
                            </div>
                            <div class="file-upload-section" id="fsa1-file-section">
                                <input type="file" id="fsa1-file-input" accept=".json" class="file-input">
                                <div class="file-input-wrapper">
                                    <button type="button" class="file-input-btn" onclick="document.getElementById('fsa1-file-input').click()">
                                        Choose File
                                    </button>
                                    <span class="file-input-label" id="fsa1-file-label">No file selected</span>
                                </div>
                            </div>
                        </div>
                        <div class="form-group">
                            <label>Second FSA:</label>
                            <div class="fsa-source-options">
                                <div class="fsa-source-option">
                                    <input type="radio" id="fsa2-file" name="fsa2-source" value="file" class="fsa-source-radio" checked>
                                    <label for="fsa2-file" class="fsa-source-label">
                                        <span class="option-title">Upload File</span>
                                        <span class="option-description">Choose a JSON FSA file</span>
                                    </label>
                                </div>
                            </div>
                            <div class="file-upload-section" id="fsa2-file-section">
                                <input type="file" id="fsa2-file-input" accept=".json" class="file-input">
                                <div class="file-input-wrapper">
                                    <button type="button" class="file-input-btn" onclick="document.getElementById('fsa2-file-input').click()">
                                        Choose File
                                    </button>
                                    <span class="file-input-label" id="fsa2-file-label">No file selected</span>
                                </div>
                            </div>
                        </div>
                        <div class="validation-note" id="fsa-fsa-validation">
                            <span class="warning-icon">⚠️</span>
                            The second FSA must be from a file. Please select a file for the second FSA.
                        </div>
                    `,
                    confirmButtonText: 'Compare FSAs'
                };
            },

            regexFsa: () => {
                const currentFSAOption = fsaInfo.hasStates ?
                    `<div class="fsa-source-option">
                        <input type="radio" id="regex-fsa-current" name="regex-fsa-source" value="current" class="fsa-source-radio" checked>
                        <label for="regex-fsa-current" class="fsa-source-label">
                            <span class="option-title">Use Current FSA</span>
                            <span class="option-description">${fsaInfo.statesCount} states, ${fsaInfo.edgesCount} transitions</span>
                        </label>
                    </div>` : '';

                const defaultSelection = fsaInfo.hasStates ? '' : 'checked';

                return {
                    description: `<div class="file-operation-description">${config.description}</div>`,
                    formContent: `
                        <div class="form-group">
                            <label for="regex-input">Regular Expression:</label>
                            <input type="text" id="regex-input" placeholder="e.g., (a|b)*abb" maxlength="200" class="regex-input-field">
                            <div class="input-help">
                                Supported operators: | (union), * (Kleene star), + (one or more), ? (optional/zero or one), () (grouping), ε (epsilon)
                            </div>
                            <div class="input-error" id="regex-input-error">Please enter a regular expression</div>
                        </div>
                        <div class="form-group">
                            <label>FSA to Compare:</label>
                            <div class="fsa-source-options">
                                ${currentFSAOption}
                                <div class="fsa-source-option">
                                    <input type="radio" id="regex-fsa-file" name="regex-fsa-source" value="file" class="fsa-source-radio" ${defaultSelection}>
                                    <label for="regex-fsa-file" class="fsa-source-label">
                                        <span class="option-title">Upload File</span>
                                        <span class="option-description">Choose a JSON FSA file</span>
                                    </label>
                                </div>
                            </div>
                            <div class="file-upload-section" id="regex-fsa-file-section" ${fsaInfo.hasStates ? 'style="display: none;"' : ''}>
                                <input type="file" id="regex-fsa-file-input" accept=".json" class="file-input">
                                <div class="file-input-wrapper">
                                    <button type="button" class="file-input-btn" onclick="document.getElementById('regex-fsa-file-input').click()">
                                        Choose File
                                    </button>
                                    <span class="file-input-label" id="regex-fsa-file-label">No file selected</span>
                                </div>
                            </div>
                        </div>
                    `,
                    confirmButtonText: 'Compare REGEX with FSA'
                };
            },

            regexRegex: () => ({
                description: `<div class="file-operation-description">${config.description}</div>`,
                formContent: `
                    <div class="form-group">
                        <label for="regex1-input">First Regular Expression:</label>
                        <input type="text" id="regex1-input" placeholder="e.g., (a|b)*" maxlength="200" class="regex-input-field">
                        <div class="input-help">
                            Supported operators: | (union), * (Kleene star), + (one or more), ? (optional/zero or one), () (grouping), ε (epsilon)
                        </div>
                        <div class="input-error" id="regex1-input-error">Please enter the first regular expression</div>
                    </div>
                    <div class="form-group">
                        <label for="regex2-input">Second Regular Expression:</label>
                        <input type="text" id="regex2-input" placeholder="e.g., (a+b+)*" maxlength="200" class="regex-input-field">
                        <div class="input-help">
                            Supported operators: | (union), * (Kleene star), + (one or more), ? (optional/zero or one), () (grouping), ε (epsilon)
                        </div>
                        <div class="input-error" id="regex2-input-error">Please enter the second regular expression</div>
                    </div>
                `,
                infoSection: `
                    <div class="info-section">
                        <span class="info-icon">ℹ️</span>
                        <div class="info-text">
                            <strong>Note:</strong> The equivalence check converts both regular expressions to FSAs 
                            and compares their minimal DFAs. This process is computationally intensive for complex expressions.
                        </div>
                    </div>
                `,
                confirmButtonText: 'Compare REGEX'
            })
        };

        return contentGenerators[type]();
    }

    /**
     * Setup event handlers for equivalence popup
     */
    setupEquivalencePopupHandlers(type) {
        const checkBtn = document.getElementById('equivalence-check-btn');

        if (type === 'fsaFsa') {
            // Setup radio button handlers
            const fsa1Radios = document.querySelectorAll('input[name="fsa1-source"]');
            const fsa2Radios = document.querySelectorAll('input[name="fsa2-source"]');
            const fsa1FileSection = document.getElementById('fsa1-file-section');
            const fsa2FileSection = document.getElementById('fsa2-file-section');
            const fsa1Input = document.getElementById('fsa1-file-input');
            const fsa2Input = document.getElementById('fsa2-file-input');
            const fsa1Label = document.getElementById('fsa1-file-label');
            const fsa2Label = document.getElementById('fsa2-file-label');
            const validationNote = document.getElementById('fsa-fsa-validation');

            // Handle FSA1 source change
            fsa1Radios.forEach(radio => {
                radio.addEventListener('change', () => {
                    if (radio.value === 'file') {
                        fsa1FileSection.style.display = 'block';
                    } else {
                        fsa1FileSection.style.display = 'none';
                    }
                    this.updateFSAFSAValidation();
                    this.hideResults();
                });
            });

            // FSA2 is always from file, so no radio change handlers needed
            // Handle file input changes
            fsa1Input.addEventListener('change', (e) => {
                const file = e.target.files[0];
                fsa1Label.textContent = file ? file.name : 'No file selected';
                this.updateFSAFSAValidation();
                this.hideResults();
            });

            fsa2Input.addEventListener('change', (e) => {
                const file = e.target.files[0];
                fsa2Label.textContent = file ? file.name : 'No file selected';
                this.updateFSAFSAValidation();
                this.hideResults();
            });

            // Initial validation
            this.updateFSAFSAValidation();

        } else if (type === 'regexFsa') {
            const regexInput = document.getElementById('regex-input');
            const regexError = document.getElementById('regex-input-error');
            const fsaRadios = document.querySelectorAll('input[name="regex-fsa-source"]');
            const fsaFileSection = document.getElementById('regex-fsa-file-section');
            const fsaInput = document.getElementById('regex-fsa-file-input');
            const fsaLabel = document.getElementById('regex-fsa-file-label');

            // Handle FSA source change
            fsaRadios.forEach(radio => {
                radio.addEventListener('change', () => {
                    if (radio.value === 'file') {
                        fsaFileSection.style.display = 'block';
                    } else {
                        fsaFileSection.style.display = 'none';
                    }
                    this.updateRegexFSAValidation();
                    this.hideResults();
                });
            });

            // Handle regex input
            regexInput.addEventListener('input', () => {
                this.updateRegexFSAValidation();
                this.hideResults();
            });

            // Handle file input
            fsaInput.addEventListener('change', (e) => {
                const file = e.target.files[0];
                fsaLabel.textContent = file ? file.name : 'No file selected';
                this.updateRegexFSAValidation();
                this.hideResults();
            });

            // Enter key to check
            regexInput.addEventListener('keydown', (e) => {
                if (e.key === 'Enter' && !checkBtn.disabled) {
                    this.confirmEquivalenceCheck();
                }
            });

            // Initial validation
            this.updateRegexFSAValidation();

        } else if (type === 'regexRegex') {
            const regex1Input = document.getElementById('regex1-input');
            const regex2Input = document.getElementById('regex2-input');
            const regex1Error = document.getElementById('regex1-input-error');
            const regex2Error = document.getElementById('regex2-input-error');

            const updateButtonState = () => {
                const value1 = regex1Input.value.trim();
                const value2 = regex2Input.value.trim();

                // Validate first regex
                const formGroup1 = regex1Input.closest('.form-group');
                if (value1.length === 0) {
                    formGroup1.classList.remove('valid');
                    formGroup1.classList.add('invalid');
                    regex1Error.classList.add('show');
                } else {
                    formGroup1.classList.remove('invalid');
                    formGroup1.classList.add('valid');
                    regex1Error.classList.remove('show');
                }

                // Validate second regex
                const formGroup2 = regex2Input.closest('.form-group');
                if (value2.length === 0) {
                    formGroup2.classList.remove('valid');
                    formGroup2.classList.add('invalid');
                    regex2Error.classList.add('show');
                } else {
                    formGroup2.classList.remove('invalid');
                    formGroup2.classList.add('valid');
                    regex2Error.classList.remove('show');
                }

                // Enable button only if both are valid
                if (value1.length > 0 && value2.length > 0) {
                    checkBtn.disabled = false;
                    checkBtn.classList.remove('disabled');
                } else {
                    checkBtn.disabled = true;
                    checkBtn.classList.add('disabled');
                }

                this.hideResults();
            };

            regex1Input.addEventListener('input', updateButtonState);
            regex2Input.addEventListener('input', updateButtonState);

            // Enter key to check
            [regex1Input, regex2Input].forEach(input => {
                input.addEventListener('keydown', (e) => {
                    if (e.key === 'Enter' && !checkBtn.disabled) {
                        this.confirmEquivalenceCheck();
                    }
                });
            });
        }
    }

    /**
     * Update FSA-FSA validation
     */
    updateFSAFSAValidation() {
        const checkBtn = document.getElementById('equivalence-check-btn');
        const validationNote = document.getElementById('fsa-fsa-validation');
        const fsa1Source = document.querySelector('input[name="fsa1-source"]:checked')?.value;
        const fsa2Source = 'file'; // FSA2 is always from file
        const fsa1File = document.getElementById('fsa1-file-input')?.files[0];
        const fsa2File = document.getElementById('fsa2-file-input')?.files[0];

        let isValid = false;
        let message = '';

        // Check if file sources have files selected
        const fsa1Valid = fsa1Source === 'current' || (fsa1Source === 'file' && fsa1File);
        const fsa2Valid = fsa2File; // FSA2 must have a file

        if (fsa1Valid && fsa2Valid) {
            isValid = true;
            message = 'Ready to compare FSAs.';
            validationNote.classList.remove('error');
        } else {
            if (!fsa2Valid) {
                message = 'Please select a file for the second FSA.';
            } else {
                message = 'Please select a file for the first FSA.';
            }
            validationNote.classList.add('error');
        }

        if (checkBtn) {
            checkBtn.disabled = !isValid;
            if (isValid) {
                checkBtn.classList.remove('disabled');
            } else {
                checkBtn.classList.add('disabled');
            }
        }

        if (validationNote) {
            validationNote.innerHTML = `<span class="warning-icon">${isValid ? '✓' : '⚠️'}</span> ${message}`;
        }
    }

    /**
     * Update REGEX-FSA validation
     */
    updateRegexFSAValidation() {
        const checkBtn = document.getElementById('equivalence-check-btn');
        const regexInput = document.getElementById('regex-input');
        const regexError = document.getElementById('regex-input-error');
        const fsaSource = document.querySelector('input[name="regex-fsa-source"]:checked')?.value;
        const fsaFile = document.getElementById('regex-fsa-file-input')?.files[0];

        const regexValue = regexInput ? regexInput.value.trim() : '';
        const regexValid = regexValue.length > 0;
        const fsaValid = fsaSource === 'current' || (fsaSource === 'file' && fsaFile);

        // Update regex validation display
        if (regexInput) {
            const formGroup = regexInput.closest('.form-group');
            if (regexValid) {
                formGroup.classList.remove('invalid');
                formGroup.classList.add('valid');
                regexError.classList.remove('show');
            } else {
                formGroup.classList.remove('valid');
                formGroup.classList.add('invalid');
                regexError.classList.add('show');
            }
        }

        // Update button state
        const isValid = regexValid && fsaValid;
        if (checkBtn) {
            checkBtn.disabled = !isValid;
            if (isValid) {
                checkBtn.classList.remove('disabled');
            } else {
                checkBtn.classList.add('disabled');
            }
        }
    }

    /**
     * Hide results section
     */
    hideResults() {
        const resultsSection = document.getElementById('equivalence-results');
        if (resultsSection) {
            resultsSection.style.display = 'none';
        }
    }

    /**
     * Hide equivalence popup
     */
    hideEquivalencePopup() {
        const popup = document.getElementById('equivalence-operation-popup');
        if (popup) {
            popup.classList.add('hide');
            setTimeout(() => popup.parentNode?.removeChild(popup), 300);
        }
        this.currentOperationType = null;
    }

    /**
     * Confirm and execute equivalence check
     */
    async confirmEquivalenceCheck() {
        const checkBtn = document.getElementById('equivalence-check-btn');
        if (!checkBtn || checkBtn.disabled || !this.currentOperationType) return;

        const config = this.equivalenceConfigs[this.currentOperationType];
        const originalButtonText = checkBtn.textContent;

        // Show loading state
        checkBtn.textContent = 'Checking Equivalence...';
        checkBtn.disabled = true;
        checkBtn.classList.add('loading');

        try {
            let result;

            if (this.currentOperationType === 'fsaFsa') {
                result = await this.performFSAFSAEquivalenceCheck();
            } else if (this.currentOperationType === 'regexFsa') {
                result = await this.performREGEXFSAEquivalenceCheck();
            } else if (this.currentOperationType === 'regexRegex') {
                result = await this.performREGEXREGEXEquivalenceCheck();
            }

            // Show results inline in the modal
            this.showEquivalenceResults(this.currentOperationType, result);

            // Reset button state
            checkBtn.textContent = originalButtonText;
            checkBtn.disabled = false;
            checkBtn.classList.remove('loading');

        } catch (error) {
            console.error('Equivalence check error:', error);

            // Show error in the results section
            this.showEquivalenceError(error.message);

            // Reset button state
            checkBtn.textContent = originalButtonText;
            checkBtn.disabled = false;
            checkBtn.classList.remove('loading');
        }
    }

    /**
     * Show equivalence error in the modal
     */
    showEquivalenceError(errorMessage) {
        const resultsSection = document.getElementById('equivalence-results');
        const resultsTitle = document.getElementById('results-title');
        const resultsContent = document.getElementById('results-content');

        if (resultsSection && resultsTitle && resultsContent) {
            resultsTitle.textContent = 'Error';
            resultsContent.innerHTML = `
                <div class="result-status error">
                    <div class="result-icon">❌</div>
                    <div class="result-message">
                        <strong>Equivalence check failed:</strong><br>
                        ${errorMessage}
                    </div>
                </div>
            `;

            resultsSection.style.display = 'block';
            resultsSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }
    }

    /**
     * Show equivalence check results inline in the modal
     */
    showEquivalenceResults(type, result) {
        const resultsSection = document.getElementById('equivalence-results');
        const resultsTitle = document.getElementById('results-title');
        const resultsContent = document.getElementById('results-content');

        if (!resultsSection || !resultsTitle || !resultsContent) return;

        const equivalent = result.equivalent;
        const icon = equivalent ? '✅' : '❌';
        const statusClass = equivalent ? 'equivalent' : 'not-equivalent';

        let comparisonText;
        if (type === 'fsaFsa') {
            comparisonText = `"${result.fsa1Name || 'Current FSA'}" vs "${result.fsa2Name || 'Current FSA'}"`;
        } else if (type === 'regexFsa') {
            comparisonText = `"${result.regex}" vs ${result.fsaName || 'Current FSA'}`;
        } else if (type === 'regexRegex') {
            comparisonText = `"${result.regex1}" vs "${result.regex2}"`;
        }

        let message;
        if (type === 'fsaFsa') {
            message = equivalent ?
                `The FSAs accept the same language.` :
                `The FSAs accept different languages.`;
        } else if (type === 'regexFsa') {
            message = equivalent ?
                `The regular expression is equivalent to the FSA.` :
                `The regular expression is not equivalent to the FSA.`;
        } else if (type === 'regexRegex') {
            message = equivalent ?
                `The regular expressions represent the same language.` :
                `The regular expressions represent different languages.`;
        }

        // Technical details
        let technicalDetails = '';
        if (result.comparison_details && result.comparison_details.reason) {
            technicalDetails = `
                <div class="technical-details">
                    <h5>Technical Details:</h5>
                    <p>${result.comparison_details.reason}</p>
                </div>
            `;
        } else if (result.equivalence_details && result.equivalence_details.reason) {
            technicalDetails = `
                <div class="technical-details">
                    <h5>Technical Details:</h5>
                    <p>${result.equivalence_details.reason}</p>
                </div>
            `;
        }

        // Suggested REGEXes for non-equivalent cases
        let suggestedRegexes = '';
        if (!equivalent) {
            if (type === 'regexFsa' && result.suggestedFsaRegex) {
                suggestedRegexes = `
                    <div class="suggested-regexes">
                        <h5>Equivalent REGEX for FSA:</h5>
                        <div class="suggested-regex-item">
                            <span class="regex-label">${result.fsaName}:</span>
                            <code class="regex-code">${result.suggestedFsaRegex}</code>
                        </div>
                        <p class="suggestion-note">The FSA above is equivalent to this regular expression.</p>
                    </div>
                `;
            } else if (type === 'fsaFsa') {
                let regexItems = '';
                if (result.suggestedFsa1Regex) {
                    regexItems += `
                        <div class="suggested-regex-item">
                            <span class="regex-label">${result.fsa1Name}:</span>
                            <code class="regex-code">${result.suggestedFsa1Regex}</code>
                        </div>
                    `;
                }
                if (result.suggestedFsa2Regex) {
                    regexItems += `
                        <div class="suggested-regex-item">
                            <span class="regex-label">${result.fsa2Name}:</span>
                            <code class="regex-code">${result.suggestedFsa2Regex}</code>
                        </div>
                    `;
                }
                if (regexItems) {
                    suggestedRegexes = `
                        <div class="suggested-regexes">
                            <h5>Equivalent REGEXes for FSAs:</h5>
                            ${regexItems}
                            <p class="suggestion-note">These regular expressions are equivalent to their respective FSAs.</p>
                        </div>
                    `;
                }
            }
        }

        resultsTitle.textContent = 'Equivalence Check Result';
        resultsContent.innerHTML = `
            <div class="result-status ${statusClass}">
                <div class="result-icon">${icon}</div>
                <div class="result-message">
                    <div class="result-title">${equivalent ? 'Equivalent!' : 'Not Equivalent'}</div>
                    <div class="comparison-info">${comparisonText}</div>
                    <p>${message}</p>
                </div>
            </div>
            ${technicalDetails}
            ${suggestedRegexes}
        `;

        resultsSection.style.display = 'block';
        resultsSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }

    /**
     * Perform FSA-FSA equivalence check
     */
    async performFSAFSAEquivalenceCheck() {
        const fsa1Source = document.querySelector('input[name="fsa1-source"]:checked').value;
        const fsa2Source = 'file'; // FSA2 is always from file

        let fsa1, fsa1Name;
        let fsa2, fsa2Name;

        // Get first FSA
        if (fsa1Source === 'current') {
            fsa1 = convertFSAToBackendFormat(this.jsPlumbInstance);
            fsa1Name = 'Current FSA';
        } else {
            const fsa1File = document.getElementById('fsa1-file-input').files[0];
            const fsa1Data = await this.readJSONFile(fsa1File);
            fsa1 = this.convertSerialisedFSAToBackendFormat(fsa1Data);
            fsa1Name = fsa1File.name;
        }

        // Get second FSA (always from file)
        const fsa2File = document.getElementById('fsa2-file-input').files[0];
        const fsa2Data = await this.readJSONFile(fsa2File);
        fsa2 = this.convertSerialisedFSAToBackendFormat(fsa2Data);
        fsa2Name = fsa2File.name;

        // Call backend API
        const response = await fetch('/api/check-fsa-equivalence/', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ fsa1: fsa1, fsa2: fsa2 })
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error || `HTTP error! status: ${response.status}`);
        }

        const result = await response.json();
        result.operationType = 'fsaFsa';
        result.fsa1Name = fsa1Name;
        result.fsa2Name = fsa2Name;

        // If not equivalent, try to generate equivalent REGEXes for both FSAs
        if (!result.equivalent) {
            // Try to generate REGEX for FSA1
            try {
                const fsa1ToRegexResponse = await fetch('/api/fsa-to-regex/', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ fsa: fsa1 })
                });

                if (fsa1ToRegexResponse.ok) {
                    const fsa1ToRegexResult = await fsa1ToRegexResponse.json();
                    if (fsa1ToRegexResult.success && fsa1ToRegexResult.verification && fsa1ToRegexResult.verification.equivalent) {
                        result.suggestedFsa1Regex = fsa1ToRegexResult.regex;
                    }
                }
            } catch (error) {
                console.warn('Failed to generate equivalent REGEX for FSA1:', error);
            }

            // Try to generate REGEX for FSA2
            try {
                const fsa2ToRegexResponse = await fetch('/api/fsa-to-regex/', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ fsa: fsa2 })
                });

                if (fsa2ToRegexResponse.ok) {
                    const fsa2ToRegexResult = await fsa2ToRegexResponse.json();
                    if (fsa2ToRegexResult.success && fsa2ToRegexResult.verification && fsa2ToRegexResult.verification.equivalent) {
                        result.suggestedFsa2Regex = fsa2ToRegexResult.regex;
                    }
                }
            } catch (error) {
                console.warn('Failed to generate equivalent REGEX for FSA2:', error);
            }
        }

        return result;
    }

    /**
     * Perform REGEX-FSA equivalence check
     */
    async performREGEXFSAEquivalenceCheck() {
        const regex = document.getElementById('regex-input').value.trim();
        const fsaSource = document.querySelector('input[name="regex-fsa-source"]:checked').value;

        let fsa, fsaName;

        // Get FSA
        if (fsaSource === 'current') {
            fsa = convertFSAToBackendFormat(this.jsPlumbInstance);
            fsaName = 'Current FSA';
        } else {
            const fsaFile = document.getElementById('regex-fsa-file-input').files[0];
            const fsaData = await this.readJSONFile(fsaFile);
            fsa = this.convertSerialisedFSAToBackendFormat(fsaData);
            fsaName = fsaFile.name;
        }

        // Call backend API
        const response = await fetch('/api/check-fsa-regex-equivalence/', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ fsa: fsa, regex: regex })
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error || `HTTP error! status: ${response.status}`);
        }

        const result = await response.json();
        result.operationType = 'regexFsa';
        result.regex = regex;
        result.fsaName = fsaName;

        // If not equivalent, try to generate equivalent REGEX for the FSA
        if (!result.equivalent) {
            try {
                const fsaToRegexResponse = await fetch('/api/fsa-to-regex/', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ fsa: fsa })
                });

                if (fsaToRegexResponse.ok) {
                    const fsaToRegexResult = await fsaToRegexResponse.json();
                    if (fsaToRegexResult.success && fsaToRegexResult.verification && fsaToRegexResult.verification.equivalent) {
                        result.suggestedFsaRegex = fsaToRegexResult.regex;
                    }
                }
            } catch (error) {
                console.warn('Failed to generate equivalent REGEX for FSA:', error);
            }
        }

        return result;
    }

    /**
     * Perform REGEX-REGEX equivalence check
     */
    async performREGEXREGEXEquivalenceCheck() {
        const regex1 = document.getElementById('regex1-input').value.trim();
        const regex2 = document.getElementById('regex2-input').value.trim();

        // Call backend API
        const response = await fetch('/api/check-regex-equivalence/', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ regex1: regex1, regex2: regex2 })
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error || `HTTP error! status: ${response.status}`);
        }

        const result = await response.json();
        result.operationType = 'regexRegex';
        result.regex1 = regex1;
        result.regex2 = regex2;
        return result;
    }

    /**
     * Read and parse a JSON file
     */
    async readJSONFile(file) {
        return new Promise((resolve, reject) => {
            const reader = new FileReader();
            reader.onload = (e) => {
                try {
                    const data = JSON.parse(e.target.result);
                    resolve(data);
                } catch (error) {
                    reject(new Error(`Invalid JSON in file ${file.name}: ${error.message}`));
                }
            };
            reader.onerror = () => reject(new Error(`Failed to read file ${file.name}`));
            reader.readAsText(file);
        });
    }

    /**
     * Convert serialised FSA data to backend format
     */
    convertSerialisedFSAToBackendFormat(serialisedFSA) {
        const backendTransitions = {};

        // Initialise transitions object for all states
        serialisedFSA.states.forEach(state => {
            backendTransitions[state.id] = {};
        });

        // Process transitions
        serialisedFSA.transitions.forEach(transition => {
            const sourceId = transition.sourceId;

            // Handle epsilon transitions
            if (transition.hasEpsilon) {
                if (!backendTransitions[sourceId]['']) {
                    backendTransitions[sourceId][''] = [];
                }
                backendTransitions[sourceId][''].push(transition.targetId);
            }

            // Handle symbol transitions
            transition.symbols.forEach(symbol => {
                if (!backendTransitions[sourceId][symbol]) {
                    backendTransitions[sourceId][symbol] = [];
                }
                backendTransitions[sourceId][symbol].push(transition.targetId);
            });
        });

        // Create alphabet from all transition symbols
        const alphabet = new Set();
        serialisedFSA.transitions.forEach(transition => {
            transition.symbols.forEach(symbol => {
                if (symbol !== '') alphabet.add(symbol);
            });
        });

        return {
            states: serialisedFSA.states.map(state => state.id),
            alphabet: Array.from(alphabet),
            transitions: backendTransitions,
            startingState: serialisedFSA.startingState,
            acceptingStates: serialisedFSA.states.filter(state => state.isAccepting).map(state => state.id)
        };
    }

    /**
     * Update menu states based on control lock status
     */
    updateMenuStates(locked) {
        menuManager.updateMenuStates(locked);
    }
}

// Create and export singleton instance
export const equivalenceManager = new EquivalenceManager();

// Make globally available
window.equivalenceManager = equivalenceManager;

// Export class for potential multiple instances
export { EquivalenceManager };