import { visualSimulationManager } from './visualSimulationManager.js';
import { simulateNFAStreamOnBackend } from './backendIntegration.js';

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
    }

    /**
     * Show NFA results popup with streaming data
     * @param {Object} fsa - FSA in backend format
     * @param {string} inputString - Input string to simulate
     * @param {Object} jsPlumbInstance - JSPlumb instance for visual simulation
     */
    async showNFAResultsPopup(fsa, inputString, jsPlumbInstance) {
        // Store references
        this.currentFSA = fsa;
        this.currentInputString = inputString;
        this.jsPlumbInstance = jsPlumbInstance;

        // Reset state
        this.acceptingPaths = [];
        this.rejectedPaths = [];
        this.pathsExplored = 0;
        this.hasAcceptingPaths = false;

        // Create and show popup
        this.createNFAResultsPopup();

        // Start streaming
        await this.startStreaming();
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

        popup.innerHTML = `
            <div class="nfa-popup-header">
                <div class="nfa-popup-title">
                    <div class="nfa-popup-icon">🔀</div>
                    <span>NFA SIMULATION</span>
                </div>
                <button class="nfa-popup-close" onclick="nfaResultsManager.hideNFAResultsPopup()">×</button>
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
                    <span class="nfa-status-label">Paths explored:</span>
                    <span class="nfa-status-value" id="nfa-paths-explored">0</span>
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
                        <div class="nfa-no-paths">No accepting paths found yet...</div>
                    </div>
                </div>
                <div class="nfa-tab-content" id="rejected-tab">
                    <div class="nfa-paths-container" id="rejected-paths-container">
                        <div class="nfa-no-paths">No rejected paths found yet...</div>
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

            // Trigger show animation
            setTimeout(() => {
                popup.classList.add('show');
            }, 100);
        }
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

            while (this.isStreaming) {
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
                                this.handleStreamData(data);
                            }
                        } catch (parseError) {
                            console.error('Error parsing streaming data:', parseError, 'Raw line:', line);
                            // Continue processing other lines instead of failing completely
                        }
                    }
                }
            }

        } catch (error) {
            console.error('Error during NFA streaming:', error);
            this.handleStreamError(error);
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

        // Update counters
        this.updateCounters();

        // Add path to UI
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

        // Update counters
        this.updateCounters();

        // Add path to UI
        this.addPathToUI(data, 'rejected');
    }

    /**
     * Handle progress update
     * @param {Object} data - Progress data
     */
    handleProgress(data) {
        this.pathsExplored = data.paths_explored;

        // Update progress display
        const pathsExploredEl = document.getElementById('nfa-paths-explored');
        if (pathsExploredEl) {
            pathsExploredEl.textContent = this.pathsExplored;
        }

        // Update progress bar (visual indicator)
        const progressBar = document.getElementById('nfa-progress-bar');
        if (progressBar) {
            // Animate progress bar to show activity
            progressBar.style.width = '100%';
            progressBar.style.opacity = '0.8';
            setTimeout(() => {
                progressBar.style.width = '0%';
                progressBar.style.opacity = '0.3';
            }, 300);
        }
    }

    /**
     * Handle simulation summary
     * @param {Object} data - Summary data
     */
    handleSummary(data) {
        this.pathsExplored = data.total_paths_explored;

        // Update final status
        const statusText = document.getElementById('nfa-status-text');
        if (statusText) {
            if (data.accepted) {
                statusText.textContent = 'Input ACCEPTED';
                statusText.className = 'nfa-status-value accepted';
            } else {
                statusText.textContent = 'Input REJECTED';
                statusText.className = 'nfa-status-value rejected';
            }
        }

        // Update final counters
        this.updateCounters();

        // Change stop button to close button
        const stopBtn = document.getElementById('nfa-stop-btn');
        if (stopBtn) {
            stopBtn.textContent = 'Close';
            stopBtn.onclick = () => this.hideNFAResultsPopup();
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

        // If no summary was received but stream ended, update UI
        const statusText = document.getElementById('nfa-status-text');
        if (statusText && statusText.textContent === 'Exploring paths...') {
            if (this.hasAcceptingPaths) {
                statusText.textContent = 'Input ACCEPTED';
                statusText.className = 'nfa-status-value accepted';
            } else {
                statusText.textContent = 'Input REJECTED';
                statusText.className = 'nfa-status-value rejected';
            }
        }

        // Change stop button to close button
        const stopBtn = document.getElementById('nfa-stop-btn');
        if (stopBtn) {
            stopBtn.textContent = 'Close';
            stopBtn.onclick = () => this.hideNFAResultsPopup();
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
     * Update path counters in the UI
     */
    updateCounters() {
        // Update main status counters
        const acceptingCountEl = document.getElementById('nfa-accepting-count');
        const rejectedCountEl = document.getElementById('nfa-rejected-count');
        const pathsExploredEl = document.getElementById('nfa-paths-explored');

        if (acceptingCountEl) {
            acceptingCountEl.textContent = this.acceptingPaths.length;
        }
        if (rejectedCountEl) {
            rejectedCountEl.textContent = this.rejectedPaths.length;
        }
        if (pathsExploredEl) {
            pathsExploredEl.textContent = this.pathsExplored;
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
    }

    /**
     * Add a path to the UI
     * @param {Object} pathData - Path data from stream
     * @param {string} type - 'accepting' or 'rejected'
     */
    addPathToUI(pathData, type) {
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

        pathElement.innerHTML = `
            <div class="nfa-path-header">
                <span class="nfa-path-number">Path ${type === 'accepting' ? this.acceptingPaths.length : this.rejectedPaths.length}</span>
                ${type === 'accepting' ? '<button class="nfa-visualize-path-btn" onclick="nfaResultsManager.visualizePath(' + (this.acceptingPaths.length - 1) + ', \'accepting\')">Visualize</button>' : ''}
            </div>
            <div class="nfa-path-content">
                ${pathDisplay}
                ${reasonDisplay}
            </div>
        `;

        // Add click handler for path selection
        pathElement.addEventListener('click', (e) => {
            if (!e.target.classList.contains('nfa-visualize-path-btn')) {
                this.selectPath(pathElement, type);
            }
        });

        container.appendChild(pathElement);

        // Auto-scroll to show new path
        pathElement.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
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

        // Update visualize button for accepting paths
        if (type === 'accepting') {
            const visualizeBtn = document.getElementById('nfa-visualize-btn');
            if (visualizeBtn) {
                visualizeBtn.disabled = false;
                visualizeBtn.classList.remove('disabled');

                const pathIndex = parseInt(pathElement.getAttribute('data-path-index'));
                visualizeBtn.onclick = () => this.visualizePath(pathIndex, 'accepting');
            }
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

        // Hide NFA results popup
        this.hideNFAResultsPopup();

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
        if (statusText && statusText.textContent === 'Exploring paths...') {
            statusText.textContent = 'Simulation stopped';
            statusText.className = 'nfa-status-value';
        }

        // Change stop button to close button
        const stopBtn = document.getElementById('nfa-stop-btn');
        if (stopBtn) {
            stopBtn.textContent = 'Close';
            stopBtn.onclick = () => this.hideNFAResultsPopup();
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

        // Reset state
        this.acceptingPaths = [];
        this.rejectedPaths = [];
        this.pathsExplored = 0;
        this.hasAcceptingPaths = false;
    }

    /**
     * Check if currently streaming
     * @returns {boolean} - Whether streaming is active
     */
    isStreamingActive() {
        return this.isStreaming;
    }
}

// Create and export singleton instance
export const nfaResultsManager = new NFAResultsManager();

// Make globally available
window.nfaResultsManager = nfaResultsManager;

// Export class for potential multiple instances
export { NFAResultsManager };