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
        this.finalResult = null; // Store final result (accepted/rejected)
        this.storedPaths = null; // Store complete simulation results to avoid re-streaming
        this.isDepthLimited = false; // Track if using depth limit
        this.maxDepth = null; // Store depth limit
        this.depthLimitReached = false; // Track if depth limit was reached
    }

    /**
     * Show NFA results popup with streaming data or stored data
     * @param {Object} fsa - FSA in backend format
     * @param {string} inputString - Input string to simulate
     * @param {Object} jsPlumbInstance - JSPlumb instance for visual simulation
     * @param {boolean} useStoredPaths - Whether to use stored paths instead of streaming
     */
    async showNFAResultsPopup(fsa, inputString, jsPlumbInstance, useStoredPaths = false) {
        // Store references
        this.currentFSA = fsa;
        this.currentInputString = inputString;
        this.jsPlumbInstance = jsPlumbInstance;
        this.isDepthLimited = false;
        this.maxDepth = null;

        // If we have stored paths for the same FSA and input, use them
        if (useStoredPaths && this.storedPaths &&
            this.storedPaths.inputString === inputString &&
            JSON.stringify(this.storedPaths.fsa) === JSON.stringify(fsa) &&
            !this.storedPaths.isDepthLimited) {

            console.log('Using stored simulation results');
            this.loadStoredPaths();
            this.createNFAResultsPopup();
            this.updateUIWithStoredData();
            return;
        }

        // Reset state for new simulation
        this.resetSimulationState();

        // Create and show popup IMMEDIATELY - don't wait for any results
        this.createNFAResultsPopup();

        // Start streaming AFTER popup is visible
        await this.startStreaming();
    }

    /**
     * Show NFA results popup with depth limit
     * @param {Object} fsa - FSA in backend format
     * @param {string} inputString - Input string to simulate
     * @param {Object} jsPlumbInstance - JSPlumb instance for visual simulation
     * @param {number} maxDepth - Maximum epsilon transition depth
     * @param {boolean} useStoredPaths - Whether to use stored paths instead of streaming
     */
    async showNFAResultsPopupWithDepthLimit(fsa, inputString, jsPlumbInstance, maxDepth, useStoredPaths = false) {
        // Store references
        this.currentFSA = fsa;
        this.currentInputString = inputString;
        this.jsPlumbInstance = jsPlumbInstance;
        this.isDepthLimited = true;
        this.maxDepth = maxDepth;

        // If we have stored paths for the same FSA, input, and depth limit, use them
        if (useStoredPaths && this.storedPaths &&
            this.storedPaths.inputString === inputString &&
            JSON.stringify(this.storedPaths.fsa) === JSON.stringify(fsa) &&
            this.storedPaths.isDepthLimited &&
            this.storedPaths.maxDepth === maxDepth) {

            console.log('Using stored depth-limited simulation results');
            this.loadStoredPaths();
            this.createNFAResultsPopup();
            this.updateUIWithStoredData();
            return;
        }

        // Reset state for new simulation
        this.resetSimulationState();

        // Create and show popup IMMEDIATELY - don't wait for any results
        this.createNFAResultsPopup();

        // Start streaming with depth limit AFTER popup is visible
        await this.startStreamingWithDepthLimit();
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
    }

    /**
     * Load stored paths into current state
     */
    loadStoredPaths() {
        if (!this.storedPaths) return;

        this.acceptingPaths = [...this.storedPaths.acceptingPaths];
        this.rejectedPaths = [...this.storedPaths.rejectedPaths];
        this.pathsExplored = this.storedPaths.pathsExplored;
        this.hasAcceptingPaths = this.storedPaths.hasAcceptingPaths;
        this.isComplete = this.storedPaths.isComplete;
        this.finalResult = this.storedPaths.finalResult;
        this.isDepthLimited = this.storedPaths.isDepthLimited || false;
        this.maxDepth = this.storedPaths.maxDepth || null;
        this.depthLimitReached = this.storedPaths.depthLimitReached || false;
    }

    /**
     * Store current simulation results for reuse
     */
    storeCurrentPaths() {
        this.storedPaths = {
            fsa: JSON.parse(JSON.stringify(this.currentFSA)), // Deep clone
            inputString: this.currentInputString,
            acceptingPaths: [...this.acceptingPaths], // Clone arrays
            rejectedPaths: [...this.rejectedPaths],
            pathsExplored: this.pathsExplored,
            hasAcceptingPaths: this.hasAcceptingPaths,
            isComplete: this.isComplete,
            finalResult: this.finalResult,
            isDepthLimited: this.isDepthLimited,
            maxDepth: this.maxDepth,
            depthLimitReached: this.depthLimitReached
        };
        console.log('Stored simulation results for reuse');
    }

    /**
     * Update UI with stored data (for when reloading popup)
     */
    updateUIWithStoredData() {
        // Update counters
        this.updateCounters();

        // Update status
        const statusText = document.getElementById('nfa-status-text');
        if (statusText && this.finalResult !== null) {
            let statusMessage = this.finalResult ? 'Input ACCEPTED' : 'Input REJECTED';
            if (this.isDepthLimited && this.depthLimitReached) {
                statusMessage += ' (depth limit reached)';
            }
            statusText.textContent = statusMessage;
            statusText.className = `nfa-status-value ${this.finalResult ? 'accepted' : 'rejected'}`;
        }

        // Add all accepting paths to UI
        const acceptingContainer = document.getElementById('accepting-paths-container');
        if (acceptingContainer) {
            acceptingContainer.innerHTML = '';
            if (this.acceptingPaths.length === 0) {
                acceptingContainer.innerHTML = '<div class="nfa-no-paths">No accepting paths found...</div>';
            } else {
                this.acceptingPaths.forEach((pathData, index) => {
                    this.addStoredPathToUI(pathData, 'accepting', index);
                });
            }
        }

        // Add all rejected paths to UI
        const rejectedContainer = document.getElementById('rejected-paths-container');
        if (rejectedContainer) {
            rejectedContainer.innerHTML = '';
            if (this.rejectedPaths.length === 0) {
                rejectedContainer.innerHTML = '<div class="nfa-no-paths">No rejected paths found...</div>';
            } else {
                this.rejectedPaths.forEach((pathData, index) => {
                    this.addStoredPathToUI(pathData, 'rejected', index);
                });
            }
        }

        // Update buttons
        const stopBtn = document.getElementById('nfa-stop-btn');
        if (stopBtn) {
            stopBtn.textContent = 'Close';
            stopBtn.onclick = () => this.handlePopupClose();
        }

        const visualizeBtn = document.getElementById('nfa-visualize-btn');
        if (visualizeBtn && this.acceptingPaths.length > 0) {
            visualizeBtn.disabled = false;
            visualizeBtn.classList.remove('disabled');
            visualizeBtn.onclick = () => this.visualizeSelectedPath();
        }

        // Update progress bar
        const progressBar = document.getElementById('nfa-progress-bar');
        if (progressBar && this.finalResult !== null) {
            progressBar.style.width = '100%';
            progressBar.style.backgroundColor = this.finalResult ? '#4CAF50' : '#f44336';
            progressBar.style.opacity = '1';
        }
    }

    /**
     * Add a stored path to the UI (similar to addPathToUI but for stored data)
     */
    addStoredPathToUI(pathData, type, index) {
        const containerId = `${type}-paths-container`;
        const container = document.getElementById(containerId);

        if (!container) return;

        // Create path element
        const pathElement = document.createElement('div');
        pathElement.className = `nfa-path-item ${type}`;
        pathElement.setAttribute('data-path-index', index);

        // Build path display
        let pathDisplay = '';
        if (pathData.path && pathData.path.length > 0) {
            pathDisplay = pathData.path.map((step, stepIndex) => {
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

        let reasonDisplay = '';
        if (type === 'rejected' && pathData.reason) {
            reasonDisplay = `<div class="nfa-rejection-reason">Reason: ${pathData.reason}</div>`;
        }

        // Add depth information if applicable
        let depthDisplay = '';
        if (pathData.depth_used !== undefined) {
            depthDisplay = `<div class="nfa-path-depth">Epsilon depth used: ${pathData.depth_used}</div>`;
        }

        // Remove individual visualize buttons - use only path number for all paths
        pathElement.innerHTML = `
            <div class="nfa-path-header">
                <span class="nfa-path-number">Path ${index + 1}</span>
            </div>
            <div class="nfa-path-content">
                ${pathDisplay}
                ${reasonDisplay}
                ${depthDisplay}
            </div>
        `;

        // Add click handler for path selection
        pathElement.addEventListener('click', (e) => {
            this.selectPath(pathElement, type);
        });

        container.appendChild(pathElement);
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
                <button class="nfa-action-btn disabled" id="nfa-visualize-btn" disabled>
                    Visualize Path
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

            // Trigger show animation immediately
            setTimeout(() => {
                popup.classList.add('show');
            }, 10); // Much shorter delay for immediate display
        }
    }

    /**
     * Handle popup close - automatically press stop button
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
            const streamResponse = await simulateNFAStreamOnBackend(this.currentFSA, this.currentInputString);

            // Check if response is ok
            if (!streamResponse.ok) {
                throw new Error(`HTTP ${streamResponse.status}: ${streamResponse.statusText}`);
            }

            const reader = streamResponse.body.getReader();
            const decoder = new TextDecoder();

            this.currentReader = reader;

            // Process streaming data in real-time without blocking
            this.processStreamingData(reader, decoder);

        } catch (error) {
            console.error('Error during NFA streaming:', error);
            this.handleStreamError(error);
        }
    }

    /**
     * Start streaming NFA simulation results with depth limit
     */
    async startStreamingWithDepthLimit() {
        if (this.isStreaming) {
            this.stopStreaming();
        }

        this.isStreaming = true;

        try {
            const streamResponse = await simulateNFAStreamWithDepthLimitOnBackend(
                this.currentFSA,
                this.currentInputString,
                this.maxDepth
            );

            // Check if response is ok
            if (!streamResponse.ok) {
                throw new Error(`HTTP ${streamResponse.status}: ${streamResponse.statusText}`);
            }

            const reader = streamResponse.body.getReader();
            const decoder = new TextDecoder();

            this.currentReader = reader;

            // Process streaming data in real-time without blocking
            this.processStreamingData(reader, decoder);

        } catch (error) {
            console.error('Error during NFA depth-limited streaming:', error);
            this.handleStreamError(error);
        }
    }

    /**
     * Process streaming data asynchronously and non-blocking
     * @param {ReadableStreamDefaultReader} reader - Stream reader
     * @param {TextDecoder} decoder - Text decoder
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

                // Process each line immediately and asynchronously
                for (const line of lines) {
                    if (line.startsWith('data: ')) {
                        try {
                            const jsonStr = line.slice(6).trim();
                            if (jsonStr) {
                                const data = JSON.parse(jsonStr);

                                // Use setTimeout to make this truly non-blocking
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
     * @param {Object} data - Parsed stream data
     */
    handleStreamData(data) {
        switch (data.type) {
            case 'accepting_path':
                this.handleAcceptingPath(data);
                break;
            case 'rejected_path':
                this.handleRejectedPath(data);
                break;
            case 'depth_limit_reached':
                this.handleDepthLimitReached(data);
                break;
            case 'progress':
                this.handleProgress(data);
                break;
            case 'summary':
                this.handleSummary(data);
                break;
            case 'end':
                this.handleStreamComplete();
                break;
            case 'error':
                this.handleStreamError(data);
                break;
        }
    }

    /**
     * Handle accepting path result
     * @param {Object} data - Accepting path data
     */
    handleAcceptingPath(data) {
        this.acceptingPaths.push(data);
        this.hasAcceptingPaths = true;

        // Update counters immediately
        this.updateCounters();

        // Add path to UI immediately with smooth animation
        this.addPathToUI(data, 'accepting');

        // Enable visualize button if this is the first accepting path
        if (this.acceptingPaths.length === 1) {
            const visualizeBtn = document.getElementById('nfa-visualize-btn');
            if (visualizeBtn) {
                visualizeBtn.disabled = false;
                visualizeBtn.classList.remove('disabled');
                visualizeBtn.onclick = () => this.visualizeSelectedPath();
            }
        }
    }

    /**
     * Handle rejected path result
     * @param {Object} data - Rejected path data
     */
    handleRejectedPath(data) {
        this.rejectedPaths.push(data);

        // Update counters immediately
        this.updateCounters();

        // Add path to UI immediately with smooth animation
        this.addPathToUI(data, 'rejected');
    }

    /**
     * Handle depth limit reached event
     * @param {Object} data - Depth limit data
     */
    handleDepthLimitReached(data) {
        this.depthLimitReached = true;
        console.log('Depth limit reached:', data);

        // Show depth limit warning in status if needed
        const statusText = document.getElementById('nfa-status-text');
        if (statusText && statusText.textContent === 'Exploring paths...') {
            statusText.textContent = 'Exploring paths... (depth limit reached)';
            statusText.className = 'nfa-status-value warning';
        }
    }

    /**
     * Handle progress update
     * @param {Object} data - Progress data
     */
    handleProgress(data) {
        this.pathsExplored = data.paths_explored;

        // Track depth limit reached from progress updates
        if (data.depth_limit_reached) {
            this.depthLimitReached = true;
        }

        // Update progress bar (visual indicator) - smooth animation
        const progressBar = document.getElementById('nfa-progress-bar');
        if (progressBar) {
            // Animate progress bar to show activity without blocking
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
     * @param {Object} data - Summary data
     */
    handleSummary(data) {
        this.pathsExplored = data.total_paths_explored;
        this.finalResult = data.accepted;
        this.isComplete = true;

        // Track depth limit reached from summary
        if (data.depth_limit_reached) {
            this.depthLimitReached = true;
        }

        // Store paths for reuse
        this.storeCurrentPaths();

        // Update final status
        const statusText = document.getElementById('nfa-status-text');
        if (statusText) {
            let statusMessage;
            if (data.accepted) {
                statusMessage = 'Input ACCEPTED';
            } else {
                statusMessage = 'Input REJECTED';
            }

            if (this.depthLimitReached) {
                statusMessage += ' (depth limit reached)';
            }

            statusText.textContent = statusMessage;
            statusText.className = `nfa-status-value ${data.accepted ? 'accepted' : 'rejected'}`;
        }

        // Update final counters
        this.updateCounters();

        // Change stop button to close button
        const stopBtn = document.getElementById('nfa-stop-btn');
        if (stopBtn) {
            stopBtn.textContent = 'Close';
            stopBtn.onclick = () => this.handlePopupClose();
        }

        // Show completion indicator
        const progressBar = document.getElementById('nfa-progress-bar');
        if (progressBar) {
            progressBar.style.width = '100%';
            progressBar.style.backgroundColor = data.accepted ? '#4CAF50' : '#f44336';
            progressBar.style.opacity = '1';
        }
    }

    /**
     * Handle stream completion
     */
    handleStreamComplete() {
        this.isStreaming = false;
        this.isComplete = true;

        // Store paths for reuse
        this.storeCurrentPaths();

        // If no summary was received but stream ended, update UI
        const statusText = document.getElementById('nfa-status-text');
        if (statusText && statusText.textContent.startsWith('Exploring paths...')) {
            let statusMessage;
            if (this.hasAcceptingPaths) {
                statusMessage = 'Input ACCEPTED';
                this.finalResult = true;
            } else {
                statusMessage = 'Input REJECTED';
                this.finalResult = false;
            }

            if (this.depthLimitReached) {
                statusMessage += ' (depth limit reached)';
            }

            statusText.textContent = statusMessage;
            statusText.className = `nfa-status-value ${this.finalResult ? 'accepted' : 'rejected'}`;
        }

        // Change stop button to close button
        const stopBtn = document.getElementById('nfa-stop-btn');
        if (stopBtn) {
            stopBtn.textContent = 'Close';
            stopBtn.onclick = () => this.handlePopupClose();
        }

        console.log('NFA simulation completed');
    }

    /**
     * Handle stream error
     * @param {Object|Error} error - Error data or object
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
     * Update path counters in the UI (removed paths explored counter)
     */
    updateCounters() {
        // Use requestAnimationFrame for smooth UI updates
        requestAnimationFrame(() => {
            // Update main status counters
            const acceptingCountEl = document.getElementById('nfa-accepting-count');
            const rejectedCountEl = document.getElementById('nfa-rejected-count');

            if (acceptingCountEl) {
                acceptingCountEl.textContent = this.acceptingPaths.length;
            }
            if (rejectedCountEl) {
                rejectedCountEl.textContent = this.rejectedPaths.length;
            }

            // Update tab counters
            const acceptingTabCount = document.getElementById('accepting-tab-count');
            const rejectedTabCount = document.getElementById('rejected-tab-count');

            if (acceptingTabCount) {
                acceptingTabCount.textContent = this.acceptingPaths.length;
            }
            if (rejectedTabCount) {
                rejectedTabCount.textContent = this.rejectedPaths.length;
            }
        });
    }

    /**
     * Add a path to the UI with smooth animation
     * @param {Object} pathData - Path data from stream
     * @param {string} type - 'accepting' or 'rejected'
     */
    addPathToUI(pathData, type) {
        // Use requestAnimationFrame for smooth UI updates
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
            pathElement.setAttribute('data-path-index', type === 'accepting' ? this.acceptingPaths.length - 1 : this.rejectedPaths.length - 1);

            // Build path display
            let pathDisplay = '';
            if (pathData.path && pathData.path.length > 0) {
                pathDisplay = pathData.path.map((step, index) => {
                    const [currentState, symbol, nextState] = step;
                    const displaySymbol = symbol === '' ? 'ε' : symbol;
                    return `<span class="nfa-path-step">${currentState} --${displaySymbol}--> ${nextState}</span>`;
                }).join('<br>');

                // Add final state info
                const finalState = pathData.final_state || pathData.path[pathData.path.length - 1][2];
                const finalStateInfo = type === 'accepting' ?
                    `<div class="nfa-final-state accepting">Final state: ${finalState} (accepting)</div>` :
                    `<div class="nfa-final-state rejected">Final state: ${finalState} (non-accepting)</div>`;

                pathDisplay += finalStateInfo;
            } else {
                // Handle empty path (empty string case)
                const finalState = pathData.final_state || 'S0'; // fallback
                pathDisplay = `<span class="nfa-path-step">Empty string processed in starting state</span><br>`;
                pathDisplay += type === 'accepting' ?
                    `<div class="nfa-final-state accepting">Final state: ${finalState} (accepting)</div>` :
                    `<div class="nfa-final-state rejected">Final state: ${finalState} (non-accepting)</div>`;
            }

            // Add reason for rejected paths
            let reasonDisplay = '';
            if (type === 'rejected' && pathData.reason) {
                reasonDisplay = `<div class="nfa-rejection-reason">Reason: ${pathData.reason}</div>`;
            }

            // Add depth information if applicable
            let depthDisplay = '';
            if (pathData.depth_used !== undefined) {
                depthDisplay = `<div class="nfa-path-depth">Epsilon depth used: ${pathData.depth_used}</div>`;
            }

            // Remove individual visualize buttons - use only path number for all paths
            pathElement.innerHTML = `
                <div class="nfa-path-header">
                    <span class="nfa-path-number">Path ${type === 'accepting' ? this.acceptingPaths.length : this.rejectedPaths.length}</span>
                </div>
                <div class="nfa-path-content">
                    ${pathDisplay}
                    ${reasonDisplay}
                    ${depthDisplay}
                </div>
            `;

            // Add click handler for path selection
            pathElement.addEventListener('click', (e) => {
                this.selectPath(pathElement, type);
            });

            // Add with smooth fade-in animation
            pathElement.style.opacity = '0';
            pathElement.style.transform = 'translateY(10px)';
            container.appendChild(pathElement);

            // Trigger fade-in animation
            setTimeout(() => {
                pathElement.style.transition = 'opacity 0.3s ease, transform 0.3s ease';
                pathElement.style.opacity = '1';
                pathElement.style.transform = 'translateY(0)';
            }, 10);

            // Auto-scroll to show new path smoothly
            setTimeout(() => {
                pathElement.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
            }, 100);
        });
    }

    /**
     * Select a path in the UI
     * @param {HTMLElement} pathElement - Path element to select
     * @param {string} type - 'accepting' or 'rejected'
     */
    selectPath(pathElement, type) {
        // Remove previous selection
        const allPaths = document.querySelectorAll('.nfa-path-item');
        allPaths.forEach(p => p.classList.remove('selected'));

        // Select this path
        pathElement.classList.add('selected');

        // Update visualize button - enable for any selected path (accepting or rejected)
        const visualizeBtn = document.getElementById('nfa-visualize-btn');
        if (visualizeBtn) {
            visualizeBtn.disabled = false;
            visualizeBtn.classList.remove('disabled');

            const pathIndex = parseInt(pathElement.getAttribute('data-path-index'));
            visualizeBtn.onclick = () => this.visualizePath(pathIndex, type);
        }
    }

    /**
     * Visualize a specific path
     * @param {number} pathIndex - Index of path to visualize
     * @param {string} type - 'accepting' or 'rejected'
     */
    visualizePath(pathIndex, type) {
        const pathData = type === 'accepting' ? this.acceptingPaths[pathIndex] : this.rejectedPaths[pathIndex];

        if (!pathData || !this.jsPlumbInstance) {
            console.error('Cannot visualize path: missing data or JSPlumb instance');
            return;
        }

        // Set up a callback to reopen the NFA popup after visualization ends
        const originalStopSimulation = visualSimulationManager.stopSimulation.bind(visualSimulationManager);
        const originalAutoClickStopButton = visualSimulationManager.autoClickStopButton.bind(visualSimulationManager);

        // Override stop simulation to reopen popup
        visualSimulationManager.stopSimulation = () => {
            originalStopSimulation();
            // Restore original methods
            visualSimulationManager.stopSimulation = originalStopSimulation;
            visualSimulationManager.autoClickStopButton = originalAutoClickStopButton;

            // Reopen NFA popup with stored data after a brief delay
            setTimeout(() => {
                console.log('Reopening NFA popup after path visualization');
                if (this.isDepthLimited) {
                    this.showNFAResultsPopupWithDepthLimit(
                        this.currentFSA,
                        this.currentInputString,
                        this.jsPlumbInstance,
                        this.maxDepth,
                        true
                    );
                } else {
                    this.showNFAResultsPopup(this.currentFSA, this.currentInputString, this.jsPlumbInstance, true);
                }
            }, 500);
        };

        // Override auto-click stop button to prevent automatic stop button pressing
        // Only reopen the popup, don't press stop button
        visualSimulationManager.autoClickStopButton = () => {
            console.log('Path visualization completed - reopening NFA popup instead of auto-clicking stop');

            // Just call stopSimulation directly (which will reopen popup)
            visualSimulationManager.stopSimulation();

            // Show result popup after a brief delay
            setTimeout(() => {
                visualSimulationManager.showResultPopup();
            }, 800); // Slightly longer delay to allow popup to open first
        };

        // Hide current NFA results popup temporarily
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

        // Initialize visual simulation manager
        visualSimulationManager.initialize(this.jsPlumbInstance);

        // Start visual simulation with the selected path
        const isAccepted = type === 'accepting';
        visualSimulationManager.startVisualSimulation(pathData.path || [], this.currentInputString, isAccepted);

        console.log(`Starting visualization of ${type} path ${pathIndex + 1}`);
    }

    /**
     * Visualize the first available accepting path (or selected path)
     */
    visualizeSelectedPath() {
        // Find selected path
        const selectedPath = document.querySelector('.nfa-path-item.selected');

        if (selectedPath) {
            const pathIndex = parseInt(selectedPath.getAttribute('data-path-index'));
            const isAccepting = selectedPath.classList.contains('accepting');
            this.visualizePath(pathIndex, isAccepting ? 'accepting' : 'rejected');
        } else if (this.acceptingPaths.length > 0) {
            // Visualize first accepting path as fallback
            this.visualizePath(0, 'accepting');
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

        // Change stop button to close button
        const stopBtn = document.getElementById('nfa-stop-btn');
        if (stopBtn) {
            stopBtn.textContent = 'Close';
            stopBtn.onclick = () => this.handlePopupClose();
        }

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

        // Note: Don't reset stored paths here - keep them for reuse
        // Only reset current popup state
    }

    /**
     * Clear all stored data (call this when FSA structure changes)
     */
    clearStoredPaths() {
        this.storedPaths = null;
        this.acceptingPaths = [];
        this.rejectedPaths = [];
        this.pathsExplored = 0;
        this.hasAcceptingPaths = false;
        this.isComplete = false;
        this.finalResult = null;
        this.isDepthLimited = false;
        this.maxDepth = null;
        this.depthLimitReached = false;
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
