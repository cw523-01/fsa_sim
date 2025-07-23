import { visualSimulationManager } from './visualSimulationManager.js';
import { simulateNFAStreamOnBackend, simulateNFAStreamWithDepthLimitOnBackend } from './backendIntegration.js';
import { controlLockManager } from './controlLockManager.js';

/**
 * NFA Results Manager class to handle streaming NFA simulation results
 */
class NFAResultsManager {
    constructor() {
        this.isStreaming = false;
        this.currentReader = null;
        this.currentPopup = null;
        this.acceptingPaths = [];
        this.rejectedPaths = [];
        this.currentFSA = null;
        this.currentInputString = '';
        this.jsPlumbInstance = null;
        this.pathsExplored = 0;
        this.hasAcceptingPaths = false;
        this.isComplete = false;
        this.finalResult = null;
        this.storedPaths = null;
        this.isDepthLimited = false;
        this.maxDepth = null;
        this.depthLimitReached = false;
        this.acceptingPathCounter = 0;
        this.rejectedPathCounter = 0;
    }

    /**
     * Show NFA results popup (unified method for both regular and depth-limited)
     * @param {Object} fsa - FSA in backend format
     * @param {string} inputString - Input string to simulate
     * @param {Object} jsPlumbInstance - JSPlumb instance for visual simulation
     * @param {number|null} maxDepth - Maximum epsilon transition depth (null for unlimited)
     * @param {boolean} useStoredPaths - Whether to use stored paths instead of streaming
     */
    async showNFAResultsPopup(fsa, inputString, jsPlumbInstance, maxDepth = null, useStoredPaths = false) {
        // Store references
        this.currentFSA = fsa;
        this.currentInputString = inputString;
        this.jsPlumbInstance = jsPlumbInstance;
        this.isDepthLimited = maxDepth !== null;
        this.maxDepth = maxDepth;

        // Check if we can use stored paths
        if (useStoredPaths && this.hasStoredResultsFor(fsa, inputString, this.isDepthLimited, maxDepth)) {
            console.log(`Using stored ${this.isDepthLimited ? 'depth-limited' : ''} simulation results`);
            this.loadStoredPaths();
            this.createNFAResultsPopup();
            this.updateUIWithStoredData();
            return;
        }

        // Reset state for new simulation
        this.resetSimulationState();

        // Create and show popup immediately
        this.createNFAResultsPopup();

        // Start streaming after popup is visible
        await this.startStreaming();
    }

    /**
     * Convenience method for showing popup with depth limit
     */
    async showNFAResultsPopupWithDepthLimit(fsa, inputString, jsPlumbInstance, maxDepth, useStoredPaths = false) {
        return this.showNFAResultsPopup(fsa, inputString, jsPlumbInstance, maxDepth, useStoredPaths);
    }

    /**
     * Reset simulation state
     */
    resetSimulationState() {
        this.acceptingPaths = [];
        this.rejectedPaths = [];
        this.pathsExplored = 0;
        this.hasAcceptingPaths = false;
        this.isComplete = false;
        this.finalResult = null;
        this.depthLimitReached = false;
        this.acceptingPathCounter = 0;
        this.rejectedPathCounter = 0;
    }

    /**
     * Load stored paths into current state
     */
    loadStoredPaths() {
        if (!this.storedPaths) return;

        Object.assign(this, {
            acceptingPaths: [...this.storedPaths.acceptingPaths],
            rejectedPaths: [...this.storedPaths.rejectedPaths],
            pathsExplored: this.storedPaths.pathsExplored,
            hasAcceptingPaths: this.storedPaths.hasAcceptingPaths,
            isComplete: this.storedPaths.isComplete,
            finalResult: this.storedPaths.finalResult,
            isDepthLimited: this.storedPaths.isDepthLimited || false,
            maxDepth: this.storedPaths.maxDepth || null,
            depthLimitReached: this.storedPaths.depthLimitReached || false,
            acceptingPathCounter: this.storedPaths.acceptingPathCounter || this.acceptingPaths.length,
            rejectedPathCounter: this.storedPaths.rejectedPathCounter || this.rejectedPaths.length
        });
    }

    /**
     * Store current simulation results for reuse
     */
    storeCurrentPaths() {
        this.storedPaths = {
            fsa: JSON.parse(JSON.stringify(this.currentFSA)),
            inputString: this.currentInputString,
            acceptingPaths: [...this.acceptingPaths],
            rejectedPaths: [...this.rejectedPaths],
            pathsExplored: this.pathsExplored,
            hasAcceptingPaths: this.hasAcceptingPaths,
            isComplete: this.isComplete,
            finalResult: this.finalResult,
            isDepthLimited: this.isDepthLimited,
            maxDepth: this.maxDepth,
            depthLimitReached: this.depthLimitReached,
            acceptingPathCounter: this.acceptingPathCounter,
            rejectedPathCounter: this.rejectedPathCounter
        };
        console.log('Stored simulation results for reuse');
    }

    /**
     * Update UI with stored data
     */
    updateUIWithStoredData() {
        // Update counters
        this.updateCounters();

        // Update status
        this.updateStatus(this.finalResult);

        // Add all paths to UI
        this.addAllPathsToUI();

        // Update buttons
        this.updateButtons();

        // Update progress bar
        this.updateProgressBar(true);
    }

    /**
     * Add all stored paths to UI
     */
    addAllPathsToUI() {
        // Add accepting paths
        const acceptingContainer = document.getElementById('accepting-paths-container');
        if (acceptingContainer) {
            acceptingContainer.innerHTML = this.acceptingPaths.length === 0
                ? '<div class="nfa-no-paths">No accepting paths found...</div>'
                : '';
            this.acceptingPaths.forEach((pathData, index) => {
                this.addPathToUI(pathData, 'accepting', index + 1, true);
            });
        }

        // Add rejected paths
        const rejectedContainer = document.getElementById('rejected-paths-container');
        if (rejectedContainer) {
            rejectedContainer.innerHTML = this.rejectedPaths.length === 0
                ? '<div class="nfa-no-paths">No rejected paths found...</div>'
                : '';
            this.rejectedPaths.forEach((pathData, index) => {
                this.addPathToUI(pathData, 'rejected', index + 1, true);
            });
        }
    }

    /**
     * Update status text
     */
    updateStatus(accepted) {
        const statusText = document.getElementById('nfa-status-text');
        if (statusText && accepted !== null) {
            let statusMessage = accepted ? 'Input ACCEPTED' : 'Input REJECTED';
            if (this.isDepthLimited && this.depthLimitReached) {
                statusMessage += ' (depth limit reached)';
            }
            statusText.textContent = statusMessage;
            statusText.className = `nfa-status-value ${accepted ? 'accepted' : 'rejected'}`;
        }
    }

    /**
     * Update button states
     */
    updateButtons() {
        const stopBtn = document.getElementById('nfa-stop-btn');
        if (stopBtn) {
            stopBtn.textContent = 'Close';
            stopBtn.onclick = () => this.handlePopupClose();
        }

        const visualiseBtn = document.getElementById('nfa-visualise-btn');
        if (visualiseBtn && this.acceptingPaths.length > 0) {
            visualiseBtn.disabled = false;
            visualiseBtn.classList.remove('disabled');
            visualiseBtn.onclick = () => this.visualiseSelectedPath();
        }
    }

    /**
     * Update progress bar
     */
    updateProgressBar(isComplete) {
        const progressBar = document.getElementById('nfa-progress-bar');
        if (progressBar && isComplete && this.finalResult !== null) {
            progressBar.style.width = '100%';
            progressBar.style.backgroundColor = this.finalResult ? '#4CAF50' : '#f44336';
            progressBar.style.opacity = '1';
        }
    }

    /**
     * Create the NFA results popup
     */
    createNFAResultsPopup() {
        // Remove any existing popups
        this.hideNFAResultsPopup();

        // Create popup element
        const popup = document.createElement('div');
        popup.id = 'nfa-results-popup';
        popup.className = 'nfa-results-popup';

        // Build title with depth limit indicator
        let titleText = 'NFA SIMULATION';
        if (this.isDepthLimited) {
            titleText += ` (Depth Limit: ${this.maxDepth})`;
        }

        popup.innerHTML = `
            <div class="nfa-popup-header">
                <div class="nfa-popup-title">
                    <div class="nfa-popup-icon"><img src="static/img/shuffle.png" alt="NFA" style="width: 20px; height: 20px;"></div>
                    <span>${titleText}</span>
                </div>
                <button class="nfa-popup-close" onclick="nfaResultsManager.handlePopupClose()">×</button>
            </div>
            
            <div class="nfa-popup-input">
                Input: <span class="nfa-popup-input-string">"${this.currentInputString}"</span>
            </div>
            
            <div class="nfa-popup-status">
                <div class="nfa-status-item">
                    <span class="nfa-status-label">Status:</span>
                    <span class="nfa-status-value" id="nfa-status-text">Exploring paths...</span>
                </div>
                <div class="nfa-status-item">
                    <span class="nfa-status-label">Accepting paths:</span>
                    <span class="nfa-status-value accepting" id="nfa-accepting-count">0</span>
                </div>
                <div class="nfa-status-item">
                    <span class="nfa-status-label">Rejected paths:</span>
                    <span class="nfa-status-value rejected" id="nfa-rejected-count">0</span>
                </div>
            </div>
            
            <div class="nfa-popup-tabs">
                <button class="nfa-tab-btn active" data-tab="accepting">
                    Accepting Paths (<span id="accepting-tab-count">0</span>)
                </button>
                <button class="nfa-tab-btn" data-tab="rejected">
                    Rejected Paths (<span id="rejected-tab-count">0</span>)
                </button>
            </div>
            
            <div class="nfa-popup-content">
                <div class="nfa-tab-content active" id="accepting-tab">
                    <div class="nfa-paths-container" id="accepting-paths-container">
                        <div class="nfa-no-paths">Searching for accepting paths...</div>
                    </div>
                </div>
                <div class="nfa-tab-content" id="rejected-tab">
                    <div class="nfa-paths-container" id="rejected-paths-container">
                        <div class="nfa-no-paths">Searching for rejected paths...</div>
                    </div>
                </div>
            </div>
            
            <div class="nfa-popup-actions">
                <button class="nfa-action-btn" id="nfa-stop-btn" onclick="nfaResultsManager.stopStreaming()">
                    Stop Simulation
                </button>
                <button class="nfa-action-btn disabled" id="nfa-visualise-btn" disabled>
                    Visualise Path
                </button>
            </div>
            
            <div class="nfa-popup-progress">
                <div class="nfa-progress-bar" id="nfa-progress-bar"></div>
            </div>
        `;

        // Add popup to canvas
        const canvas = document.getElementById('fsa-canvas');
        if (canvas) {
            canvas.appendChild(popup);
            this.currentPopup = popup;

            // Setup tab switching
            this.setupTabSwitching();

            // Trigger show animation
            setTimeout(() => {
                popup.classList.add('show');
            }, 10);
        }
    }

    /**
     * Handle popup close
     */
    handlePopupClose() {
        console.log('NFA popup closed - auto-pressing stop button');

        // Hide the popup first
        this.hideNFAResultsPopup();

        // Auto-press the stop button after a brief delay
        setTimeout(() => {
            const stopButton = document.getElementById('stop-btn');
            if (stopButton && !stopButton.disabled) {
                stopButton.click();
                console.log('Stop button auto-clicked from NFA popup close');
            } else {
                // Fallback: unlock controls manually if stop button unavailable
                controlLockManager.unlockControls();
                console.log('Controls unlocked manually after NFA popup close');
            }
        }, 100);
    }

    /**
     * Setup tab switching functionality
     */
    setupTabSwitching() {
        const tabButtons = this.currentPopup.querySelectorAll('.nfa-tab-btn');
        const tabContents = this.currentPopup.querySelectorAll('.nfa-tab-content');

        tabButtons.forEach(btn => {
            btn.addEventListener('click', () => {
                const targetTab = btn.getAttribute('data-tab');

                // Remove active class from all tabs and contents
                tabButtons.forEach(b => b.classList.remove('active'));
                tabContents.forEach(c => c.classList.remove('active'));

                // Add active class to clicked tab and corresponding content
                btn.classList.add('active');
                const targetContent = document.getElementById(`${targetTab}-tab`);
                if (targetContent) {
                    targetContent.classList.add('active');
                }
            });
        });
    }

    /**
     * Start streaming NFA simulation results
     */
    async startStreaming() {
        if (this.isStreaming) {
            this.stopStreaming();
        }

        this.isStreaming = true;

        try {
            const streamResponse = this.isDepthLimited
                ? await simulateNFAStreamWithDepthLimitOnBackend(this.currentFSA, this.currentInputString, this.maxDepth)
                : await simulateNFAStreamOnBackend(this.currentFSA, this.currentInputString);

            if (!streamResponse.ok) {
                throw new Error(`HTTP ${streamResponse.status}: ${streamResponse.statusText}`);
            }

            const reader = streamResponse.body.getReader();
            const decoder = new TextDecoder();

            this.currentReader = reader;

            // Process streaming data
            this.processStreamingData(reader, decoder);

        } catch (error) {
            console.error('Error during NFA streaming:', error);
            this.handleStreamError(error);
        }
    }

    /**
     * Process streaming data asynchronously
     */
    async processStreamingData(reader, decoder) {
        while (this.isStreaming) {
            try {
                const { done, value } = await reader.read();

                if (done) {
                    this.handleStreamComplete();
                    break;
                }

                const chunk = decoder.decode(value, { stream: true });
                const lines = chunk.split('\n');

                for (const line of lines) {
                    if (line.startsWith('data: ')) {
                        try {
                            const jsonStr = line.slice(6).trim();
                            if (jsonStr) {
                                const data = JSON.parse(jsonStr);
                                setTimeout(() => {
                                    if (this.isStreaming) {
                                        this.handleStreamData(data);
                                    }
                                }, 0);
                            }
                        } catch (parseError) {
                            console.error('Error parsing streaming data:', parseError, 'Raw line:', line);
                        }
                    }
                }

                // Allow UI to update between chunks
                await new Promise(resolve => setTimeout(resolve, 1));

            } catch (error) {
                console.error('Error reading stream:', error);
                this.handleStreamError(error);
                break;
            }
        }
    }

    /**
     * Handle incoming stream data
     */
    handleStreamData(data) {
        const handlers = {
            'accepting_path': () => this.handleAcceptingPath(data),
            'rejected_path': () => this.handleRejectedPath(data),
            'depth_limit_reached': () => this.handleDepthLimitReached(data),
            'progress': () => this.handleProgress(data),
            'summary': () => this.handleSummary(data),
            'end': () => this.handleStreamComplete(),
            'error': () => this.handleStreamError(data)
        };

        const handler = handlers[data.type];
        if (handler) {
            handler();
        }
    }

    /**
     * Handle path result (unified for accepting and rejected)
     */
    handlePathResult(data, type) {
        const isAccepting = type === 'accepting';
        const pathArray = isAccepting ? this.acceptingPaths : this.rejectedPaths;
        const counterProp = isAccepting ? 'acceptingPathCounter' : 'rejectedPathCounter';

        // Increment counter and add path
        this[counterProp]++;
        const pathNumber = this[counterProp];
        pathArray.push(data);

        if (isAccepting) {
            this.hasAcceptingPaths = true;
        }

        // Update UI
        this.updateCounters();
        this.addPathToUI(data, type, pathNumber);

        // Enable visualise button for first accepting path
        if (isAccepting && this.acceptingPaths.length === 1) {
            const visualiseBtn = document.getElementById('nfa-visualise-btn');
            if (visualiseBtn) {
                visualiseBtn.disabled = false;
                visualiseBtn.classList.remove('disabled');
                visualiseBtn.onclick = () => this.visualiseSelectedPath();
            }
        }
    }

    /**
     * Handle accepting path result
     */
    handleAcceptingPath(data) {
        this.handlePathResult(data, 'accepting');
    }

    /**
     * Handle rejected path result
     */
    handleRejectedPath(data) {
        this.handlePathResult(data, 'rejected');
    }

    /**
     * Handle depth limit reached event
     */
    handleDepthLimitReached(data) {
        this.depthLimitReached = true;
        console.log('Depth limit reached:', data);

        const statusText = document.getElementById('nfa-status-text');
        if (statusText && statusText.textContent === 'Exploring paths...') {
            statusText.textContent = 'Exploring paths... (depth limit reached)';
            statusText.className = 'nfa-status-value warning';
        }
    }

    /**
     * Handle progress update
     */
    handleProgress(data) {
        this.pathsExplored = data.paths_explored;

        if (data.depth_limit_reached) {
            this.depthLimitReached = true;
        }

        // Animate progress bar
        const progressBar = document.getElementById('nfa-progress-bar');
        if (progressBar) {
            requestAnimationFrame(() => {
                progressBar.style.width = '100%';
                progressBar.style.opacity = '0.8';
                setTimeout(() => {
                    progressBar.style.width = '0%';
                    progressBar.style.opacity = '0.3';
                }, 300);
            });
        }
    }

    /**
     * Handle simulation summary
     */
    handleSummary(data) {
        this.pathsExplored = data.total_paths_explored;
        this.finalResult = data.accepted;
        this.isComplete = true;

        if (data.depth_limit_reached) {
            this.depthLimitReached = true;
        }

        // Store paths for reuse
        this.storeCurrentPaths();

        // Update UI
        this.updateStatus(data.accepted);
        this.updateCounters();
        this.updateButtons();
        this.updateProgressBar(true);
    }

    /**
     * Handle stream completion
     */
    handleStreamComplete() {
        this.isStreaming = false;
        this.isComplete = true;

        // Store paths for reuse
        this.storeCurrentPaths();

        // Update status if not already updated
        const statusText = document.getElementById('nfa-status-text');
        if (statusText && statusText.textContent.startsWith('Exploring paths...')) {
            this.finalResult = this.hasAcceptingPaths;
            this.updateStatus(this.finalResult);
        }

        // Update buttons
        this.updateButtons();

        console.log('NFA simulation completed');
    }

    /**
     * Handle stream error
     */
    handleStreamError(error) {
        console.error('NFA streaming error:', error);

        const statusText = document.getElementById('nfa-status-text');
        if (statusText) {
            statusText.textContent = 'Error occurred';
            statusText.className = 'nfa-status-value error';
        }

        this.stopStreaming();
    }

    /**
     * Update path counters in the UI
     */
    updateCounters() {
        requestAnimationFrame(() => {
            // Update all counter elements
            const counters = {
                'nfa-accepting-count': this.acceptingPaths.length,
                'nfa-rejected-count': this.rejectedPaths.length,
                'accepting-tab-count': this.acceptingPaths.length,
                'rejected-tab-count': this.rejectedPaths.length
            };

            Object.entries(counters).forEach(([id, value]) => {
                const element = document.getElementById(id);
                if (element) {
                    element.textContent = value;
                }
            });
        });
    }

    /**
     * Add a path to the UI
     */
    addPathToUI(pathData, type, pathNumber, isStored = false) {
        requestAnimationFrame(() => {
            const containerId = `${type}-paths-container`;
            const container = document.getElementById(containerId);

            if (!container) return;

            // Remove "no paths" message if it exists
            const noPathsMsg = container.querySelector('.nfa-no-paths');
            if (noPathsMsg) {
                noPathsMsg.remove();
            }

            // Create path element
            const pathElement = document.createElement('div');
            pathElement.className = `nfa-path-item ${type}`;
            pathElement.setAttribute('data-path-index', pathNumber - 1);

            // Build path display
            const pathDisplay = this.buildPathDisplay(pathData, type);

            pathElement.innerHTML = `
                <div class="nfa-path-header">
                    <span class="nfa-path-number">Path ${pathNumber}</span>
                </div>
                <div class="nfa-path-content">
                    ${pathDisplay}
                </div>
            `;

            // Add click handler
            pathElement.addEventListener('click', () => {
                this.selectPath(pathElement, type);
            });

            // Add with animation for new paths only
            if (!isStored) {
                pathElement.style.opacity = '0';
                pathElement.style.transform = 'translateY(10px)';
            }

            container.appendChild(pathElement);

            if (!isStored) {
                // Trigger fade-in animation
                setTimeout(() => {
                    pathElement.style.transition = 'opacity 0.3s ease, transform 0.3s ease';
                    pathElement.style.opacity = '1';
                    pathElement.style.transform = 'translateY(0)';
                }, 10);

                // Auto-scroll to show new path
                setTimeout(() => {
                    pathElement.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
                }, 100);
            }
        });
    }

    /**
     * Build path display HTML
     */
    buildPathDisplay(pathData, type) {
        let pathDisplay = '';

        if (pathData.path && pathData.path.length > 0) {
            pathDisplay = pathData.path.map(step => {
                const [currentState, symbol, nextState] = step;
                const displaySymbol = symbol === '' ? 'ε' : symbol;
                return `<span class="nfa-path-step">${currentState} --${displaySymbol}--> ${nextState}</span>`;
            }).join('<br>');

            const finalState = pathData.final_state || pathData.path[pathData.path.length - 1][2];
            const finalStateInfo = type === 'accepting' ?
                `<div class="nfa-final-state accepting">Final state: ${finalState} (accepting)</div>` :
                `<div class="nfa-final-state rejected">Final state: ${finalState} (non-accepting)</div>`;

            pathDisplay += finalStateInfo;
        } else {
            const finalState = pathData.final_state || 'S0';
            pathDisplay = `<span class="nfa-path-step">Empty string processed in starting state</span><br>`;
            pathDisplay += type === 'accepting' ?
                `<div class="nfa-final-state accepting">Final state: ${finalState} (accepting)</div>` :
                `<div class="nfa-final-state rejected">Final state: ${finalState} (non-accepting)</div>`;
        }

        // Add rejection reason if applicable
        if (type === 'rejected' && pathData.reason) {
            pathDisplay += `<div class="nfa-rejection-reason">Reason: ${pathData.reason}</div>`;
        }

        // Add depth information if applicable
        if (pathData.depth_used !== undefined) {
            pathDisplay += `<div class="nfa-path-depth">Epsilon depth used: ${pathData.depth_used}</div>`;
        }

        return pathDisplay;
    }

    /**
     * Select a path in the UI
     */
    selectPath(pathElement, type) {
        // Remove previous selection
        const allPaths = document.querySelectorAll('.nfa-path-item');
        allPaths.forEach(p => p.classList.remove('selected'));

        // Select this path
        pathElement.classList.add('selected');

        // Update visualise button
        const visualiseBtn = document.getElementById('nfa-visualise-btn');
        if (visualiseBtn) {
            visualiseBtn.disabled = false;
            visualiseBtn.classList.remove('disabled');

            const pathIndex = parseInt(pathElement.getAttribute('data-path-index'));
            visualiseBtn.onclick = () => this.visualisePath(pathIndex, type);
        }
    }

    /**
     * Visualise a specific path
     */
    visualisePath(pathIndex, type) {
        const pathData = type === 'accepting' ? this.acceptingPaths[pathIndex] : this.rejectedPaths[pathIndex];

        if (!pathData || !this.jsPlumbInstance) {
            console.error('Cannot visualise path: missing data or JSPlumb instance');
            return;
        }

        // Set up callbacks to reopen popup after visualisation
        this.setupVisualisationCallbacks();

        // Hide current popup temporarily
        this.hidePopupTemporarily();

        // Start visual simulation
        visualSimulationManager.initialise(this.jsPlumbInstance);
        const isAccepted = type === 'accepting';
        visualSimulationManager.startVisualSimulation(pathData.path || [], this.currentInputString, isAccepted);

        console.log(`Starting visualisation of ${type} path ${pathIndex + 1}`);
    }

    /**
     * Setup callbacks for visualisation completion
     */
    setupVisualisationCallbacks() {
        const originalStopSimulation = visualSimulationManager.stopSimulation.bind(visualSimulationManager);
        const originalAutoClickStopButton = visualSimulationManager.autoClickStopButton.bind(visualSimulationManager);

        visualSimulationManager.stopSimulation = () => {
            originalStopSimulation();
            // Restore original methods
            visualSimulationManager.stopSimulation = originalStopSimulation;
            visualSimulationManager.autoClickStopButton = originalAutoClickStopButton;

            // Reopen NFA popup with stored data
            setTimeout(() => {
                console.log('Reopening NFA popup after path visualisation');
                this.showNFAResultsPopup(
                    this.currentFSA,
                    this.currentInputString,
                    this.jsPlumbInstance,
                    this.maxDepth,
                    true
                );
            }, 500);
        };

        visualSimulationManager.autoClickStopButton = () => {
            console.log('Path visualisation completed - reopening NFA popup');
            visualSimulationManager.stopSimulation();

            setTimeout(() => {
                visualSimulationManager.showResultPopup();
            }, 800);
        };
    }

    /**
     * Hide popup temporarily for visualisation
     */
    hidePopupTemporarily() {
        if (this.currentPopup) {
            this.currentPopup.classList.add('hide');
            this.currentPopup.classList.remove('show');

            setTimeout(() => {
                if (this.currentPopup && this.currentPopup.parentNode) {
                    this.currentPopup.parentNode.removeChild(this.currentPopup);
                }
                this.currentPopup = null;
            }, 400);
        }
    }

    /**
     * Visualise the first available accepting path (or selected path)
     */
    visualiseSelectedPath() {
        const selectedPath = document.querySelector('.nfa-path-item.selected');

        if (selectedPath) {
            const pathIndex = parseInt(selectedPath.getAttribute('data-path-index'));
            const isAccepting = selectedPath.classList.contains('accepting');
            this.visualisePath(pathIndex, isAccepting ? 'accepting' : 'rejected');
        } else if (this.acceptingPaths.length > 0) {
            // Visualise first accepting path as fallback
            this.visualisePath(0, 'accepting');
        }
    }

    /**
     * Stop streaming simulation
     */
    stopStreaming() {
        this.isStreaming = false;

        if (this.currentReader) {
            try {
                this.currentReader.cancel();
            } catch (error) {
                console.error('Error canceling reader:', error);
            }
            this.currentReader = null;
        }

        // Update UI to show stopped state
        const statusText = document.getElementById('nfa-status-text');
        if (statusText && statusText.textContent.startsWith('Exploring paths...')) {
            statusText.textContent = 'Simulation stopped';
            statusText.className = 'nfa-status-value';
        }

        // Update buttons
        this.updateButtons();

        console.log('NFA streaming stopped');
    }

    /**
     * Hide NFA results popup
     */
    hideNFAResultsPopup() {
        // Stop streaming if still active
        if (this.isStreaming) {
            this.stopStreaming();
        }

        // Hide popup with animation
        if (this.currentPopup) {
            this.currentPopup.classList.add('hide');
            this.currentPopup.classList.remove('show');

            setTimeout(() => {
                if (this.currentPopup && this.currentPopup.parentNode) {
                    this.currentPopup.parentNode.removeChild(this.currentPopup);
                }
                this.currentPopup = null;
            }, 400);
        }
    }

    /**
     * Clear all stored data (call this when FSA structure changes)
     */
    clearStoredPaths() {
        this.storedPaths = null;
        this.resetSimulationState();
        console.log('Cleared stored simulation results');
    }

    /**
     * Check if currently streaming
     * @returns {boolean} - Whether streaming is active
     */
    isStreamingActive() {
        return this.isStreaming;
    }

    /**
     * Check if we have stored results for the given FSA and input
     * @param {Object} fsa - FSA in backend format
     * @param {string} inputString - Input string
     * @param {boolean} isDepthLimited - Whether this is a depth-limited query
     * @param {number} maxDepth - Maximum depth (for depth-limited queries)
     * @returns {boolean} - Whether we have stored results
     */
    hasStoredResultsFor(fsa, inputString, isDepthLimited = false, maxDepth = null) {
        if (!this.storedPaths) {
            return false;
        }

        const sameInputAndFSA = this.storedPaths.inputString === inputString &&
                               JSON.stringify(this.storedPaths.fsa) === JSON.stringify(fsa);

        if (!isDepthLimited) {
            // For non-depth-limited queries, we need stored results that are also non-depth-limited
            return sameInputAndFSA && !this.storedPaths.isDepthLimited;
        } else {
            // For depth-limited queries, we need stored results with the same depth limit
            return sameInputAndFSA &&
                   this.storedPaths.isDepthLimited &&
                   this.storedPaths.maxDepth === maxDepth;
        }
    }
}

// Create and export singleton instance
export const nfaResultsManager = new NFAResultsManager();

// Make globally available
window.nfaResultsManager = nfaResultsManager;

// Export class for potential multiple instances
export { NFAResultsManager };