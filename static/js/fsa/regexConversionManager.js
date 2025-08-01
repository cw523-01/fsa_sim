import { fsaSerializationManager} from './fsaSerializationManager.js';
import { notificationManager } from './notificationManager.js';
import { controlLockManager } from './controlLockManager.js';
import { undoRedoManager } from './undoRedoManager.js';
import { menuManager } from './menuManager.js';
import { updateFSAPropertiesDisplay } from './fsaPropertyChecker.js';
import { calculateTransformLayout } from './positioningUtils.js';
import { SafeStateNameGenerator } from './transformManager.js';
import { convertFSAToBackendFormat } from './backendIntegration.js';

/**
 * REGEX Conversion Manager - handles REGEX to FSA conversion operations and FSA to REGEX conversion
 */
class RegexConversionManager {
    constructor() {
        this.jsPlumbInstance = null;
        this.currentRegexData = null;
        this.currentRegexInput = null;
        this.stateNameGenerator = new SafeStateNameGenerator();

        // Conversion configuration
        this.conversionConfig = {
            name: 'REGEX to FSA',
            apiEndpoint: '/api/regex-to-epsilon-nfa/',
            popupClass: 'regex-convert',
            headerGradient: 'var(--secondary-colour) 0%, var(--secondary-hover) 100%',
            buttonColor: 'var(--secondary-colour)',
            hoverColor: 'var(--secondary-hover)',
            undoLabel: 'Convert REGEX to NFA',
            tags: ['regex-generated', 'epsilon-nfa']
        };

        // FSA to REGEX conversion configuration
        this.fsaToRegexConfig = {
            name: 'FSA to REGEX',
            apiEndpoint: '/api/fsa-to-regex/',
            popupClass: 'fsa-to-regex',
            headerGradient: 'var(--primary-colour) 0%, var(--primary-hover) 100%',
            buttonColor: 'var(--primary-colour)',
            hoverColor: 'var(--primary-hover)',
            undoLabel: 'Convert FSA to REGEX',
            tags: ['regex-result']
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

        // Register REGEX menu with the universal menu manager
        menuManager.registerMenu('regex', {
            buttonId: 'regex-menu-button',
            dropdownId: 'regex-dropdown'
        });

        this.setupRegexEventListeners();
    }

    /**
     * Setup REGEX menu event listeners
     */
    setupRegexEventListeners() {
        menuManager.registerMenuItems({
            'menu-regex-to-fsa': () => this.executeRegexConversion(),
            'menu-fsa-to-regex': () => this.executeFSAToRegexConversion()
        });
    }

    /**
     * Execute REGEX conversion operation
     */
    async executeRegexConversion() {
        if (!this.jsPlumbInstance) {
            notificationManager.showError(`${this.conversionConfig.name} Error`, 'FSA not initialised');
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
     * Execute FSA to REGEX conversion operation
     */
    async executeFSAToRegexConversion() {
        if (!this.jsPlumbInstance) {
            notificationManager.showError(`${this.fsaToRegexConfig.name} Error`, 'FSA not initialised');
            return;
        }

        if (controlLockManager.isControlsLocked()) {
            notificationManager.showWarning(`Cannot ${this.fsaToRegexConfig.name}`, 'Cannot perform operation while simulation is running');
            return;
        }

        // Check if FSA exists
        const states = document.querySelectorAll('.state, .accepting-state');
        if (states.length === 0) {
            notificationManager.showWarning('Nothing to Convert', 'Create an FSA before converting to REGEX');
            return;
        }

        // Show loading modal immediately
        this.showFSAToRegexLoadingModal();

        // Convert FSA and call backend
        try {
            const fsa = convertFSAToBackendFormat(this.jsPlumbInstance);

            // Call backend API
            const response = await fetch(this.fsaToRegexConfig.apiEndpoint, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ fsa: fsa })
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.error || `HTTP error! status: ${response.status}`);
            }

            const result = await response.json();

            // Update modal with results
            this.updateFSAToRegexResultModal(result);

        } catch (error) {
            console.error('FSA to REGEX conversion error:', error);

            // Update modal with error state
            this.updateFSAToRegexErrorModal(error.message);
        }
    }

    /**
     * Show FSA to REGEX loading modal
     */
    showFSAToRegexLoadingModal() {
        const config = this.fsaToRegexConfig;

        // Remove any existing popup and overlay
        const existingPopup = document.getElementById('fsa-to-regex-result-popup');
        if (existingPopup) existingPopup.remove();

        const existingOverlay = document.getElementById('fsa-to-regex-modal-overlay');
        if (existingOverlay) existingOverlay.remove();

        // Create modal overlay
        const overlay = document.createElement('div');
        overlay.id = 'fsa-to-regex-modal-overlay';
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

        const popup = document.createElement('div');
        popup.id = 'fsa-to-regex-result-popup';
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
                        <img src="static/img/alert.png" alt="Processing" style="width: 20px; height: 20px;">
                    </div>
                    <span>FSA to REGEX Conversion</span>
                </div>
                <button class="popup-close" onclick="regexConversionManager.hideFSAToRegexResultModal()">×</button>
            </div>
            
            <div class="file-operation-content">
                <div class="scrollable-content">
                    <div class="conversion-loading-section">
                        <div class="loading-header">
                            <div class="loading-spinner"></div>
                            <h4>Converting FSA to Regular Expression...</h4>
                        </div>
                        <div class="loading-description">
                            <p>Converting your finite state automaton to a regular expression using the <a href="https://www.geeksforgeeks.org/theory-of-computation/state-elimination-method-convert-dfa-nfa-%C9%9B-nfa-into-regular-expression/" target="_blank" rel="noopener noreferrer">state elimination algorithm</a>.</p>
                        </div>
                        
                        <div class="conversion-algorithm-info">
                            <div class="algorithm-header">
                                <span class="algorithm-title">Conversion Algorithm Details</span>
                            </div>
                            <div class="algorithm-content">
                                <p>The conversion uses the <a href="https://www.geeksforgeeks.org/theory-of-computation/state-elimination-method-convert-dfa-nfa-%C9%9B-nfa-into-regular-expression/" target="_blank" rel="noopener noreferrer">state elimination algorithm</a>, which systematically removes states from a <a href="https://en.wikipedia.org/wiki/Generalized_nondeterministic_finite_automaton" target="_blank" rel="noopener noreferrer">Generalized NFA (GNFA)</a> until only the start and accept states remain.</p>
                                <div class="algorithm-steps">
                                    <strong>Process steps:</strong>
                                    <ol>
                                        <li>Convert FSA to GNFA format</li>
                                        <li>Apply state elimination with transition combination</li>
                                        <li>Generate regular expression from final transition</li>
                                        <li>Apply simplification patterns for readability</li>
                                    </ol>
                                </div>
                            </div>
                        </div>
                        
                        <div class="loading-progress">
                            <div class="progress-steps">
                                <div class="progress-step active">
                                    <div class="step-icon">1</div>
                                    <div class="step-text">Converting to GNFA</div>
                                </div>
                                <div class="progress-step active">
                                    <div class="step-icon">2</div>
                                    <div class="step-text">Eliminating states</div>
                                </div>
                                <div class="progress-step processing">
                                    <div class="step-icon">
                                        <div class="step-spinner"></div>
                                    </div>
                                    <div class="step-text">Generating regular expression</div>
                                </div>
                                <div class="progress-step">
                                    <div class="step-icon">4</div>
                                    <div class="step-text">Verifying result</div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
            
            <div class="file-operation-actions">
                <button class="file-action-btn cancel" onclick="regexConversionManager.hideFSAToRegexResultModal()">
                    Cancel
                </button>
            </div>
        `;

        // Add popup to overlay
        overlay.appendChild(popup);

        // Add overlay to body
        document.body.appendChild(overlay);

        // Close modal when clicking overlay (but not popup)
        overlay.addEventListener('click', (e) => {
            if (e.target === overlay) {
                this.hideFSAToRegexResultModal();
            }
        });

        // Prevent popup clicks from closing modal
        popup.addEventListener('click', (e) => {
            e.stopPropagation();
        });

        // Show with animation
        setTimeout(() => {
            overlay.style.opacity = '1';
            popup.style.opacity = '1';
        }, 10);
    }

    /**
     * Update modal with conversion results
     */
    updateFSAToRegexResultModal(result) {
        const popup = document.getElementById('fsa-to-regex-result-popup');
        if (!popup) return;

        const config = this.fsaToRegexConfig;
        const regex = result.regex || '∅';
        const stats = result.statistics || {};
        const verification = result.verification || {};

        // Update the content
        const contentDiv = popup.querySelector('.scrollable-content');
        if (contentDiv) {
            contentDiv.innerHTML = `
                ${verification.equivalent === true ? `
                <div class="regex-result-section">
                    <h4>Generated Regular Expression</h4>
                    <div class="regex-display scrollable-regex">
                        <code class="regex-code">${this.escapeHtml(regex)}</code>
                        <button class="copy-regex-btn" onclick="regexConversionManager.copyRegexToClipboard('${this.escapeHtml(regex)}')">
                            Copy
                        </button>
                    </div>
                    <div class="verification-status verified">
                        <img src="static/img/success.png" alt="✓" class="property-icon success-icon"> The generated REGEX has been verified to be equivalent to the original FSA
                    </div>
                </div>
                ` : `
                <div class="conversion-failed-section">
                    <h4>Conversion Result</h4>
                    <div class="verification-status unverified">
                        The system could not generate a verified regular expression for your FSA
                    </div>
                    ${verification.error ? `
                    <div class="verification-error">
                        <small>Technical details: ${verification.error}</small>
                    </div>
                    ` : ''}
                    <div class="conversion-failed-explanation">
                        <p>This may happen with very complex FSAs or due to limitations in the conversion algorithm. You may want to try:</p>
                        <ul>
                            <li>Simplifying your FSA structure</li>
                            <li>Checking for unreachable states</li>
                            <li>Using manual conversion techniques</li>
                        </ul>
                    </div>
                </div>
                `}
    
                <div class="conversion-algorithm-info">
                    <div class="algorithm-header">
                        <span class="algorithm-title">Conversion Algorithm Details</span>
                    </div>
                    <div class="algorithm-content">
                        <p>The conversion used the <a href="https://www.geeksforgeeks.org/theory-of-computation/state-elimination-method-convert-dfa-nfa-%C9%9B-nfa-into-regular-expression/" target="_blank" rel="noopener noreferrer">state elimination algorithm</a>, which systematically removes states from a <a href="https://en.wikipedia.org/wiki/Generalized_nondeterministic_finite_automaton" target="_blank" rel="noopener noreferrer">Generalized NFA (GNFA)</a> until only the start and accept states remain.</p>
                        <div class="algorithm-steps">
                            <strong>Process completed:</strong>
                            <ol>
                                <li>Converted FSA to GNFA format</li>
                                <li>Applied state elimination with transition combination</li>
                                <li>Generated regular expression from final transition</li>
                                <li>Applied simplification patterns for readability (only applied to REGEX up to a certain size due to complexity).</li>
                            </ol>
                        </div>
                    </div>
                </div>

                <div class="important-notice">
                    <div class="notice-header">
                        <span class="notice-title">Important Notice</span>
                    </div>
                    <div class="notice-content">
                        <p><strong>The generated regular expression may not be the smallest or most optimal possible.</strong></p>
                        <p>Regular expression minimisation is a complex problem, and the state elimination algorithm prioritises correctness over brevity. The resulting expression is guaranteed to be equivalent to your FSA, but there may exist shorter equivalent expressions.</p>
                        <ul class="notice-points">
                            <li>The REGEX is functionally correct and equivalent to your FSA</li>
                            <li>Manual optimisation may be possible for shorter expressions</li>
                            <li>Complex FSAs may produce verbose regular expressions</li>
                        </ul>
                    </div>
                </div>
            `;
        }

        // Update the actions
        const actionsDiv = popup.querySelector('.file-operation-actions');
        if (actionsDiv) {
            actionsDiv.innerHTML = `
                <button class="file-action-btn cancel" onclick="regexConversionManager.hideFSAToRegexResultModal()">
                    Close
                </button>
                ${verification.equivalent === true ? `
                <button class="file-action-btn primary" onclick="regexConversionManager.copyRegexToClipboard('${this.escapeHtml(regex)}')"
                        style="background: ${config.buttonColor};">
                    Copy REGEX
                </button>
                ` : ''}
            `;
        }

        // Add success animation to the progress steps
        this.animateProgressStepsComplete();
    }

    /**
     * Update modal with error state
     */
    updateFSAToRegexErrorModal(errorMessage) {
        const popup = document.getElementById('fsa-to-regex-result-popup');
        if (!popup) return;

        // Update the content with error
        const contentDiv = popup.querySelector('.scrollable-content');
        if (contentDiv) {
            contentDiv.innerHTML = `
                <div class="conversion-error-section">
                    <div class="error-header">
                        <div class="error-icon"><img src="static/img/error.png" alt="✗" class="property-icon error-icon"></div>
                        <h4>Conversion Failed</h4>
                    </div>
                    <div class="error-description">
                        <p>An error occurred while converting your FSA to a regular expression:</p>
                        <div class="error-message">
                            ${this.escapeHtml(errorMessage)}
                        </div>
                    </div>
                    <div class="error-suggestions">
                        <h5>Suggestions:</h5>
                        <ul>
                            <li>Check that your FSA has a valid starting state</li>
                            <li>Ensure all states are reachable from the starting state</li>
                            <li>Verify that transitions are properly defined</li>
                            <li>Try simplifying your FSA structure</li>
                        </ul>
                    </div>
                </div>
            `;
        }

        // Update the actions to only show close
        const actionsDiv = popup.querySelector('.file-operation-actions');
        if (actionsDiv) {
            actionsDiv.innerHTML = `
                <button class="file-action-btn cancel" onclick="regexConversionManager.hideFSAToRegexResultModal()">
                    Close
                </button>
            `;
        }

        // Add error animation to the progress steps
        this.animateProgressStepsError();
    }

    /**
     * Animate progress steps to completion
     */
    animateProgressStepsComplete() {
        const steps = document.querySelectorAll('.progress-step');
        if (steps.length >= 4) {
            // Complete step 3
            setTimeout(() => {
                steps[2].classList.remove('processing');
                steps[2].classList.add('completed');
            }, 500);

            // Complete step 4
            setTimeout(() => {
                steps[3].classList.add('active', 'completed');
            }, 1000);
        }
    }

    /**
     * Animate progress steps to error state
     */
    animateProgressStepsError() {
        const steps = document.querySelectorAll('.progress-step');
        if (steps.length >= 3) {
            setTimeout(() => {
                steps[2].classList.remove('processing');
                steps[2].classList.add('error');
            }, 500);
        }
    }

    /**
     * Show FSA to REGEX result modal with proper scrollable container
     */
    showFSAToRegexResultModal(result) {
        const config = this.fsaToRegexConfig;

        // Remove any existing popup
        const existingPopup = document.getElementById('fsa-to-regex-result-popup');
        if (existingPopup) existingPopup.remove();

        const popup = document.createElement('div');
        popup.id = 'fsa-to-regex-result-popup';
        popup.className = `file-operation-popup ${config.popupClass}`;

        const regex = result.regex || '∅';
        const stats = result.statistics || {};
        const verification = result.verification || {};

        popup.innerHTML = `
            <div class="popup-header" style="background: linear-gradient(135deg, ${config.headerGradient});">
                <div class="popup-title">
                    <div class="popup-icon">
                        <img src="static/img/alert.png" alt="Success" style="width: 20px; height: 20px;">
                    </div>
                    <span>FSA to REGEX Conversion Result</span>
                </div>
                <button class="popup-close" onclick="regexConversionManager.hideFSAToRegexResultModal()">×</button>
            </div>
            
            <div class="file-operation-content">
                <div class="scrollable-content">
                    ${verification.equivalent === true ? `
                    <div class="regex-result-section">
                        <h4>Generated Regular Expression</h4>
                        <div class="regex-display scrollable-regex">
                            <code class="regex-code">${this.escapeHtml(regex)}</code>
                            <button class="copy-regex-btn" onclick="regexConversionManager.copyRegexToClipboard('${this.escapeHtml(regex)}')">
                                Copy
                            </button>
                        </div>
                        <div class="verification-status verified">
                            <img src="static/img/success.png" alt="✓" class="property-icon success-icon"> The generated REGEX has been verified to be equivalent to the original FSA
                        </div>
                    </div>
                    ` : `
                    <div class="conversion-failed-section">
                        <h4>Conversion Result</h4>
                        <div class="verification-status unverified">
                            The system could not generate a verified regular expression for your FSA
                        </div>
                        ${verification.error ? `
                        <div class="verification-error">
                            <small>Technical details: ${verification.error}</small>
                        </div>
                        ` : ''}
                        <div class="conversion-failed-explanation">
                            <p>This may happen with very complex FSAs or due to limitations in the conversion algorithm. You may want to try:</p>
                            <ul>
                                <li>Simplifying your FSA structure</li>
                                <li>Checking for unreachable states</li>
                                <li>Using manual conversion techniques</li>
                            </ul>
                        </div>
                    </div>
                    `}
    
                    <div class="important-notice">
                        <div class="notice-header">
                            <span class="notice-title">Important Notice</span>
                        </div>
                        <div class="notice-content">
                            <p><strong>The generated regular expression may not be the smallest or most optimal possible.</strong></p>
                            <p>Regular expression minimisation is a complex problem, and the conversion algorithm prioritises correctness over brevity. The resulting expression is guaranteed to be equivalent to your FSA, but there may exist shorter equivalent expressions.</p>
                            <ul class="notice-points">
                                <li>The REGEX is functionally correct and equivalent to your FSA</li>
                                <li>Manual optimisation may be possible for shorter expressions</li>
                                <li>Complex FSAs may produce verbose regular expressions</li>
                            </ul>
                        </div>
                    </div>
                </div>
            </div>
            
            <div class="file-operation-actions">
                <button class="file-action-btn cancel" onclick="regexConversionManager.hideFSAToRegexResultModal()">
                    Close
                </button>
                ${verification.equivalent === true ? `
                <button class="file-action-btn primary" onclick="regexConversionManager.copyRegexToClipboard('${this.escapeHtml(regex)}')"
                        style="background: ${config.buttonColor};">
                    Copy REGEX
                </button>
                ` : ''}
            </div>
        `;

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
     * Hide FSA to REGEX result modal and overlay
     */
    hideFSAToRegexResultModal() {
        const overlay = document.getElementById('fsa-to-regex-modal-overlay');
        const popup = document.getElementById('fsa-to-regex-result-popup');

        if (overlay && popup) {
            // Animate out
            overlay.classList.add('show');
            overlay.style.opacity = '0';

            setTimeout(() => {
                if (overlay.parentNode) {
                    overlay.parentNode.removeChild(overlay);
                }
            }, 300);
        }
    }

    /**
     * Copy REGEX to clipboard
     */
    async copyRegexToClipboard(regex) {
        try {
            await navigator.clipboard.writeText(regex);
            notificationManager.showSuccess('REGEX Copied', 'Regular expression copied to clipboard');
        } catch (error) {
            console.error('Failed to copy REGEX:', error);

            // Fallback for older browsers
            const textArea = document.createElement('textarea');
            textArea.value = regex;
            textArea.style.position = 'fixed';
            textArea.style.left = '-9999px';
            document.body.appendChild(textArea);
            textArea.focus();
            textArea.select();

            try {
                document.execCommand('copy');
                notificationManager.showSuccess('REGEX Copied', 'Regular expression copied to clipboard');
            } catch (fallbackError) {
                notificationManager.showError('Copy Failed', 'Could not copy REGEX to clipboard');
            }

            document.body.removeChild(textArea);
        }
    }

    /**
     * Escape HTML characters for safe display
     */
    escapeHtml(text) {
        const map = {
            '&': '&amp;',
            '<': '&lt;',
            '>': '&gt;',
            '"': '&quot;',
            "'": '&#039;'
        };
        return text.replace(/[&<>"']/g, m => map[m]);
    }

    /**
     * Show REGEX input popup with modal overlay
     */
    showRegexInputPopup() {
        const config = this.conversionConfig;

        // Remove any existing popup and overlay
        const existingPopup = document.getElementById('regex-operation-popup');
        if (existingPopup) existingPopup.remove();

        const existingOverlay = document.getElementById('regex-modal-overlay');
        if (existingOverlay) existingOverlay.remove();

        // Create modal overlay
        const overlay = document.createElement('div');
        overlay.id = 'regex-modal-overlay';
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

        const popup = document.createElement('div');
        popup.id = 'regex-operation-popup';
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
                <button class="popup-close" onclick="regexConversionManager.hideRegexPopup()">×</button>
            </div>
            <div class="file-operation-content scrollable-content">
                <div class="file-operation-description">
                    Enter a regular expression to convert it into an equivalent NFA using <a href="https://en.wikipedia.org/wiki/Thompson%27s_construction" target="_blank" rel="noopener noreferrer">Thompson's construction</a> algorithm.
                </div>
                
                <div class="form-group">
                    <label for="regex-input-field">Regular Expression:</label>
                    <input type="text" id="regex-input-field" placeholder="e.g., (a|b)*abb" maxlength="200">
                    <div class="input-help">
                        Supported operators: | (union), * (Kleene star), + (one or more), ? (optional/zero or one), () (grouping), ε (epsilon)
                    </div>
                    <div class="input-error" id="regex-input-error">Please enter a valid regular expression</div>
                </div>
                
                <!-- Error Display Section -->
                <div class="regex-error-section" id="regex-error-section" style="display: none;">
                    <div class="error-header">
                        <h4>Conversion Error</h4>
                    </div>
                    <div class="error-content" id="regex-error-content">
                        <!-- Error message will be populated here -->
                    </div>
                </div>
    
                <div class="examples-section">
                    <div class="examples-dropdown">
                        <label for="examples-select">Examples:</label>
                        <select id="examples-select" class="examples-select">
                            <option value="">Choose an example...</option>
                            <option value="a*">a* - Zero or more 'a's</option>
                            <option value="(a|b)+">&#40;a|b&#41;+ - One or more 'a' or 'b'</option>
                            <option value="a?b">a?b - Optional 'a' followed by 'b'</option>
                            <option value="(ab)?">&#40;ab&#41;? - Optional "ab" sequence</option>
                            <option value="a*b+">a*b+ - Zero or more 'a's, then one or more 'b's</option>
                            <option value="(ab)*|(ba)*">&#40;ab&#41;*|&#40;ba&#41;* - Zero or more "ab" or zero or more "ba"</option>
                            <option value="(a|b)*abb">&#40;a|b&#41;*abb - Strings ending in "abb"</option>
                            <option value="a+b*c?">a+b*c? - One or more 'a's, zero or more 'b's, optional 'c'</option>
                        </select>
                    </div>
                </div>
    
                <div class="chaining-options">
                    <h4>Additional Operations:</h4>
                    <div class="option-group">
                        <div class="checkbox-option">
                            <input type="checkbox" id="convert-to-dfa-option" class="chain-checkbox">
                            <label for="convert-to-dfa-option">
                                <span class="option-title">Convert to DFA</span>
                                <span class="option-description">Remove ε-transitions and make deterministic</span>
                            </label>
                        </div>
                        <div class="checkbox-option dependent disabled" data-depends="convert-to-dfa-option">
                            <input type="checkbox" id="minimise-dfa-option" class="chain-checkbox" disabled>
                            <label for="minimise-dfa-option">
                                <span class="option-title">Minimise DFA</span>
                                <span class="option-description">Remove redundant states (only available if converting to DFA)</span>
                            </label>
                        </div>
                    </div>
                </div>
    
                <div class="warning-section">
                    <div class="warning-text">
                        <strong>Warning:</strong> This operation will replace the current FSA with the generated automaton. 
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
                    Convert to NFA
                </button>
            </div>
        `;

        // Add popup to overlay
        overlay.appendChild(popup);

        // Add overlay to body
        document.body.appendChild(overlay);

        // Setup event handlers
        this.setupRegexPopupHandlers();

        // Close modal when clicking overlay (but not popup)
        overlay.addEventListener('click', (e) => {
            if (e.target === overlay) {
                this.hideRegexPopup();
            }
        });

        // Prevent popup clicks from closing modal
        popup.addEventListener('click', (e) => {
            e.stopPropagation();
        });

        // Show with animation and focus
        setTimeout(() => {
            overlay.classList.add('show');
            popup.style.opacity = '1';
            overlay.style.opacity = '1';

            // Focus on regex input
            const regexInput = document.getElementById('regex-input-field');
            if (regexInput) {
                regexInput.focus();
            }
        }, 10);
    }

    /**
     * Show inline error in the regex modal
     */
    showRegexError(errorMessage) {
        const errorSection = document.getElementById('regex-error-section');
        const errorContent = document.getElementById('regex-error-content');

        if (errorSection && errorContent) {
            errorContent.innerHTML = `
                <div class="result-status error">
                    <div class="result-message">
                        <div class="result-title">Conversion Error</div>
                        <p>${this.escapeHtml(errorMessage)}</p>
                    </div>
                </div>
            `;

            errorSection.style.display = 'block';
            errorSection.scrollIntoView({behavior: 'smooth', block: 'center'});

            // Add error styling to input field
            const regexInput = document.getElementById('regex-input-field');
            const formGroup = regexInput?.closest('.form-group');
            if (formGroup) {
                formGroup.classList.add('invalid');
                formGroup.classList.add('error-state');
            }
        }
    }

    /**
     * Hide inline error in the regex modal
     */
    hideRegexError() {
        const errorSection = document.getElementById('regex-error-section');
        if (errorSection) {
            errorSection.style.display = 'none';
        }

        // Remove error styling from input field
        const regexInput = document.getElementById('regex-input-field');
        const formGroup = regexInput?.closest('.form-group');
        if (formGroup) {
            formGroup.classList.remove('error-state');
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
        const convertToDfaCheckbox = document.getElementById('convert-to-dfa-option');
        const minimiseDfaCheckbox = document.getElementById('minimise-dfa-option');

        // Set initial button state to disabled
        if (convertBtn) {
            convertBtn.disabled = true;
            convertBtn.classList.add('disabled');
        }

        if (regexInput) {
            regexInput.addEventListener('input', () => {
                const value = regexInput.value.trim();
                const formGroup = regexInput.closest('.form-group');

                // Hide any previous error when user starts typing
                this.hideRegexError();

                if (value.length === 0) {
                    formGroup.classList.remove('valid');
                    formGroup.classList.add('invalid');
                    regexError.classList.add('show');

                    // Disable button both visually and functionally
                    convertBtn.classList.add('disabled');
                    convertBtn.disabled = true;
                } else {
                    formGroup.classList.remove('invalid');
                    formGroup.classList.add('valid');
                    regexError.classList.remove('show');

                    // Enable button both visually and functionally
                    convertBtn.classList.remove('disabled');
                    convertBtn.disabled = false;
                }

                // Update button text based on options
                this.updateConvertButtonText();
            });

            // Enter key to convert
            regexInput.addEventListener('keydown', (e) => {
                if (e.key === 'Enter' && !convertBtn.disabled) {
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
                    regexInput.dispatchEvent(new Event('input')); // Trigger validation and hide errors
                    regexInput.focus();
                    // Reset dropdown to placeholder
                    examplesSelect.value = '';
                }
            });
        }

        // Handle chaining options
        if (convertToDfaCheckbox) {
            convertToDfaCheckbox.addEventListener('change', () => {
                // Enable/disable minimise option based on convert to DFA
                if (minimiseDfaCheckbox) {
                    minimiseDfaCheckbox.disabled = !convertToDfaCheckbox.checked;
                    if (!convertToDfaCheckbox.checked) {
                        minimiseDfaCheckbox.checked = false;
                    }

                    // Update dependent option styling
                    const dependentOption = minimiseDfaCheckbox.closest('.checkbox-option');
                    if (dependentOption) {
                        if (convertToDfaCheckbox.checked) {
                            dependentOption.classList.remove('disabled');
                        } else {
                            dependentOption.classList.add('disabled');
                        }
                    }
                }
                this.updateConvertButtonText();
            });
        }

        if (minimiseDfaCheckbox) {
            minimiseDfaCheckbox.addEventListener('change', () => {
                this.updateConvertButtonText();
            });
        }
    }

    /**
     * Update convert button text based on selected options
     */
    updateConvertButtonText() {
        const convertBtn = document.getElementById('regex-convert-btn');
        const convertToDfaCheckbox = document.getElementById('convert-to-dfa-option');
        const minimiseDfaCheckbox = document.getElementById('minimise-dfa-option');

        if (!convertBtn) return;

        if (minimiseDfaCheckbox && minimiseDfaCheckbox.checked) {
            convertBtn.textContent = 'Convert to Minimal DFA';
        } else if (convertToDfaCheckbox && convertToDfaCheckbox.checked) {
            convertBtn.textContent = 'Convert to DFA';
        } else {
            convertBtn.textContent = 'Convert to NFA';
        }
    }

    /**
     * Hide REGEX popup and overlay
     */
    hideRegexPopup() {
        const overlay = document.getElementById('regex-modal-overlay');
        const popup = document.getElementById('regex-operation-popup');

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

        if (!convertBtn || !regexInput || convertBtn.disabled) return;

        const regexString = regexInput.value.trim();
        if (!regexString) {
            this.showRegexError('Please enter a regular expression');
            return;
        }

        // Hide any previous errors
        this.hideRegexError();

        // Get chaining options
        const convertToDfaCheckbox = document.getElementById('convert-to-dfa-option');
        const minimiseDfaCheckbox = document.getElementById('minimise-dfa-option');

        const shouldConvertToDfa = convertToDfaCheckbox && convertToDfaCheckbox.checked;
        const shouldMinimise = minimiseDfaCheckbox && minimiseDfaCheckbox.checked && shouldConvertToDfa;

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
                const operationLabel = shouldMinimise ? 'Convert REGEX to Minimal DFA' :
                                     shouldConvertToDfa ? 'Convert REGEX to DFA' :
                                     'Convert REGEX to NFA';
                snapshotCommand = undoRedoManager.createSnapshotCommand(operationLabel);
            }

            // Call backend API for REGEX conversion
            const response = await fetch(config.apiEndpoint, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ regex: regexString })
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.error || `HTTP error! status: ${response.status}`);
            }

            const regexResult = await response.json();
            let finalResult = regexResult;
            let operationChain = ['REGEX to NFA'];

            // Chain additional operations if requested
            if (shouldConvertToDfa) {
                convertBtn.textContent = 'Converting to DFA...';

                // Convert NFA to DFA
                const nfaToDfaResponse = await fetch('/api/nfa-to-dfa/', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ fsa: regexResult.epsilon_nfa })
                });

                if (!nfaToDfaResponse.ok) {
                    const errorData = await nfaToDfaResponse.json();
                    throw new Error(errorData.error || `NFA to DFA conversion failed: ${nfaToDfaResponse.status}`);
                }

                const dfaResult = await nfaToDfaResponse.json();
                finalResult.converted_dfa = dfaResult.converted_dfa;
                finalResult.conversion_statistics = dfaResult.statistics;
                operationChain.push('NFA to DFA');

                if (shouldMinimise) {
                    convertBtn.textContent = 'Minimising DFA...';

                    // Minimise the DFA
                    const minimiseResponse = await fetch('/api/minimise-dfa/', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ fsa: dfaResult.converted_dfa })
                    });

                    if (!minimiseResponse.ok) {
                        const errorData = await minimiseResponse.json();
                        throw new Error(errorData.error || `DFA minimisation failed: ${minimiseResponse.status}`);
                    }

                    const minimiseResult = await minimiseResponse.json();
                    finalResult.minimised_dfa = minimiseResult.minimised_fsa;
                    finalResult.minimisation_statistics = minimiseResult.statistics;
                    operationChain.push('Minimise DFA');
                }
            }

            // Hide popup
            this.hideRegexPopup();

            // Replace FSA with final result
            await this.replaceWithGeneratedFSA(finalResult, shouldMinimise, shouldConvertToDfa);

            // Show comprehensive results
            this.showChainedConversionResults(finalResult, operationChain, shouldMinimise, shouldConvertToDfa);

            // Finish undo/redo snapshot
            if (snapshotCommand) {
                undoRedoManager.finishSnapshotCommand(snapshotCommand);
            }

            // Clear regex data after successful operation
            this.clearRegexData();

        } catch (error) {
            console.error('REGEX conversion error:', error);

            // Show error inline instead of using notification
            this.showRegexError(error.message);

            // Reset button state
            this.updateConvertButtonText(); // Use existing method to restore correct text
            convertBtn.disabled = false;

            // Don't clear regex data on error - user might retry
        }
    }

    /**
     * Replace current FSA with generated FSA
     */
    async replaceWithGeneratedFSA(result, shouldMinimise, shouldConvertToDfa) {
        // Clear current FSA
        await fsaSerializationManager.clearCurrentFSA(this.jsPlumbInstance);

        // Determine which result to use
        let finalFSA;
        let tags = ['regex-generated'];
        let description = `Generated from regular expression: ${this.currentRegexInput}`;

        if (shouldMinimise && result.minimised_dfa) {
            finalFSA = result.minimised_dfa;
            tags.push('minimal-dfa', 'converted');
            description += ' (converted to minimal DFA)';
        } else if (shouldConvertToDfa && result.converted_dfa) {
            finalFSA = result.converted_dfa;
            tags.push('dfa', 'converted');
            description += ' (converted to DFA)';
        } else {
            finalFSA = result.epsilon_nfa;
            tags.push('epsilon-nfa');
        }

        // Calculate positions using layered positioning algorithm
        const positions = calculateTransformLayout(finalFSA);

        // Create serialized data
        const serializedFSA = this.createSerializedFSA(
            finalFSA,
            positions,
            `REGEX: ${this.currentRegexInput}`,
            description,
            tags
        );

        // Load the generated FSA
        await fsaSerializationManager.deserializeFSA(serializedFSA, this.jsPlumbInstance);
        updateFSAPropertiesDisplay(this.jsPlumbInstance);
    }

    /**
     * Show results for chained conversion operations
     */
    showChainedConversionResults(result, operationChain, shouldMinimise, shouldConvertToDfa) {
        const regexString = this.currentRegexInput || 'regular expression';

        if (shouldMinimise) {
            const originalStats = result.statistics;
            const conversionStats = result.conversion_statistics;
            const minimisationStats = result.minimisation_statistics;

            notificationManager.showSuccess(
                'REGEX Conversion Complete',
                `Successfully converted "${regexString}" through: ${operationChain.join(' → ')}.\n` +
                `Final result: ${minimisationStats.minimised.states_count} states, ` +
                `${minimisationStats.minimised.transitions_count} transitions.`
            );
        } else if (shouldConvertToDfa) {
            const originalStats = result.statistics;
            const conversionStats = result.conversion_statistics;

            notificationManager.showSuccess(
                'REGEX Conversion Complete',
                `Successfully converted "${regexString}" through: ${operationChain.join(' → ')}.\n` +
                `Final result: ${conversionStats.converted.states_count} states, ` +
                `${conversionStats.converted.transitions_count} transitions.`
            );
        } else {
            const stats = result.statistics;
            notificationManager.showSuccess(
                'REGEX Conversion Complete',
                `Successfully converted "${regexString}" to ε-NFA with ${stats.states_count} states and ${stats.transitions_count} transitions.`
            );
        }
    }

    /**
     * Calculate positions for NFA states using layered positioning algorithm
     */
    calculateNFAPositions(fsa) {
        console.log('Using layered hierarchical positioning for REGEX conversion');
        return calculateTransformLayout(fsa);
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
     * Create serialized NFA data
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
                    targets.forEach(targetId => {
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
            metadata: { name, description, creator: "FSA Simulator - REGEX Converter", tags },
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