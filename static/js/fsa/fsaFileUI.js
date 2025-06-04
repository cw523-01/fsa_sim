// fsaFileUI.js - UI integration for FSA file management with menu bar

import { fsaSerializationManager } from './fsaSerializationManager.js';
import { notificationManager } from './notificationManager.js';
import { controlLockManager } from './controlLockManager.js';

/**
 * FSA File UI Manager - handles file operations UI with menu bar
 */
class FSAFileUIManager {
    constructor() {
        this.jsPlumbInstance = null;
        this.currentOpenMenu = null;
        this.autoSaveInterval = null;
        this.eventListenersSetup = false; // Track if event listeners are already set up
        this.setupFileInput();
    }

    /**
     * Initialize with JSPlumb instance
     * @param {Object} jsPlumbInstance - The JSPlumb instance
     */
    initialize(jsPlumbInstance) {
        this.jsPlumbInstance = jsPlumbInstance;
        this.setupMenuEventListeners();
        this.setupKeyboardShortcuts();
    }

    /**
     * Setup the hidden file input for importing
     */
    setupFileInput() {
        // File input should already exist in HTML
        const fileInput = document.getElementById('fsa-file-input');
        if (fileInput) {
            fileInput.addEventListener('change', (e) => this.handleFileImport(e));
        }
    }

    /**
     * Setup menu event listeners (only once)
     */
    setupMenuEventListeners() {
        // Prevent duplicate event listeners
        if (this.eventListenersSetup) {
            return;
        }
        this.eventListenersSetup = true;

        // File menu button
        const fileMenuButton = document.getElementById('file-menu-button');
        if (fileMenuButton) {
            fileMenuButton.addEventListener('click', (e) => {
                e.stopPropagation();
                this.toggleMenu('file-dropdown');
            });
        }

        // Menu options
        const menuNew = document.getElementById('menu-new');
        const menuOpen = document.getElementById('menu-open');
        const menuSave = document.getElementById('menu-save');

        if (menuNew) {
            menuNew.addEventListener('click', () => {
                this.closeAllMenus();
                this.newFSA();
            });
        }

        if (menuOpen) {
            menuOpen.addEventListener('click', () => {
                this.closeAllMenus();
                this.importFSA();
            });
        }

        if (menuSave) {
            menuSave.addEventListener('click', () => {
                this.closeAllMenus();
                this.exportFSA();
            });
        }

        // Close menus when clicking outside
        document.addEventListener('click', (e) => {
            if (!e.target.closest('.menu-item')) {
                this.closeAllMenus();
            }
        });

        // Close menus on escape key
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                this.closeAllMenus();
            }
        });
    }

    /**
     * Setup keyboard shortcuts
     */
    setupKeyboardShortcuts() {
        document.addEventListener('keydown', (e) => {
            // Don't trigger if controls are locked or if typing in an input
            if (controlLockManager.isControlsLocked() ||
                e.target.tagName === 'INPUT' ||
                e.target.tagName === 'TEXTAREA') {
                return;
            }

            // Ctrl+S or Cmd+S - Save/Export
            if ((e.ctrlKey || e.metaKey) && e.key === 's') {
                e.preventDefault();
                this.exportFSA();
            }

            // Ctrl+O or Cmd+O - Open/Import
            if ((e.ctrlKey || e.metaKey) && e.key === 'o') {
                e.preventDefault();
                this.importFSA();
            }

            // Ctrl+N or Cmd+N - New (clear)
            if ((e.ctrlKey || e.metaKey) && e.key === 'n') {
                e.preventDefault();
                this.newFSA();
            }
        });
    }

    /**
     * Toggle menu dropdown
     * @param {string} menuId - ID of menu dropdown to toggle
     */
    toggleMenu(menuId) {
        const menu = document.getElementById(menuId);
        const button = document.getElementById(menuId.replace('-dropdown', '-button'));

        if (!menu || !button) return;

        // Close other menus first
        if (this.currentOpenMenu && this.currentOpenMenu !== menuId) {
            this.closeAllMenus();
        }

        // Toggle current menu
        const isOpen = menu.classList.contains('show');

        if (isOpen) {
            this.closeMenu(menuId);
        } else {
            this.openMenu(menuId);
        }
    }

    /**
     * Open a specific menu
     * @param {string} menuId - ID of menu dropdown to open
     */
    openMenu(menuId) {
        const menu = document.getElementById(menuId);
        const button = document.getElementById(menuId.replace('-dropdown', '-button'));

        if (!menu || !button) return;

        menu.classList.add('show');
        button.classList.add('active');
        this.currentOpenMenu = menuId;
    }

    /**
     * Close a specific menu
     * @param {string} menuId - ID of menu dropdown to close
     */
    closeMenu(menuId) {
        const menu = document.getElementById(menuId);
        const button = document.getElementById(menuId.replace('-dropdown', '-button'));

        if (!menu || !button) return;

        menu.classList.remove('show');
        button.classList.remove('active');

        if (this.currentOpenMenu === menuId) {
            this.currentOpenMenu = null;
        }
    }

    /**
     * Close all open menus
     */
    closeAllMenus() {
        const allDropdowns = document.querySelectorAll('.menu-dropdown');
        const allButtons = document.querySelectorAll('.menu-button');

        allDropdowns.forEach(menu => menu.classList.remove('show'));
        allButtons.forEach(button => button.classList.remove('active'));

        this.currentOpenMenu = null;
    }

    /**
     * Export current FSA to file
     * @param {string} customFilename - Optional custom filename
     */
    exportFSA(customFilename = null) {
        if (!this.jsPlumbInstance) {
            notificationManager.showError('Export Error', 'FSA not initialized');
            return;
        }

        if (controlLockManager.isControlsLocked()) {
            notificationManager.showWarning('Cannot Export', 'Cannot export while simulation is running');
            return;
        }

        // Check if there's anything to export
        const states = document.querySelectorAll('.state, .accepting-state');
        if (states.length === 0) {
            notificationManager.showWarning('Nothing to Export', 'Create some states before exporting');
            return;
        }

        try {
            const filename = customFilename || this.generateDefaultFilename();
            fsaSerializationManager.exportToFile(this.jsPlumbInstance, filename);
        } catch (error) {
            console.error('Export error:', error);
            notificationManager.showError('Export Failed', error.message);
        }
    }

    /**
     * Import FSA from file
     */
    importFSA() {
        if (!this.jsPlumbInstance) {
            notificationManager.showError('Import Error', 'FSA not initialized');
            return;
        }

        if (controlLockManager.isControlsLocked()) {
            notificationManager.showWarning('Cannot Import', 'Cannot import while simulation is running');
            return;
        }

        // Check if current FSA exists and warn user
        const states = document.querySelectorAll('.state, .accepting-state');
        if (states.length > 0) {
            if (!confirm('Importing will replace the current FSA. Continue?')) {
                return;
            }
        }

        // Trigger file input
        const fileInput = document.getElementById('fsa-file-input');
        if (fileInput) {
            fileInput.click();
        }
    }

    /**
     * Create a new FSA (clear current)
     */
    newFSA() {
        if (!this.jsPlumbInstance) {
            notificationManager.showError('Error', 'FSA not initialized');
            return;
        }

        if (controlLockManager.isControlsLocked()) {
            notificationManager.showWarning('Cannot Clear', 'Cannot clear while simulation is running');
            return;
        }

        // Check if current FSA exists and warn user
        const states = document.querySelectorAll('.state, .accepting-state');
        if (states.length > 0) {
            if (!confirm('This will clear the current FSA. Continue?')) {
                return;
            }
        }

        try {
            fsaSerializationManager.clearCurrentFSA(this.jsPlumbInstance);

            // Clear any existing NFA results
            if (window.nfaResultsManager) {
                window.nfaResultsManager.clearStoredPaths();
            }

            notificationManager.showSuccess('New FSA', 'Canvas cleared successfully');

        } catch (error) {
            console.error('Clear error:', error);
            notificationManager.showError('Clear Failed', error.message);
        }
    }

    /**
     * Handle file import from input
     * @param {Event} e - File input change event
     */
    async handleFileImport(e) {
        const file = e.target.files[0];
        if (!file) return;

        // Validate file type
        if (!file.name.toLowerCase().endsWith('.json')) {
            notificationManager.showError(
                'Invalid File Type',
                'Please select a JSON file (.json)'
            );
            return;
        }

        // Validate file size (max 10MB)
        const maxSize = 10 * 1024 * 1024; // 10MB
        if (file.size > maxSize) {
            notificationManager.showError(
                'File Too Large',
                'Please select a file smaller than 10MB'
            );
            return;
        }

        try {
            const success = await fsaSerializationManager.importFromFile(file, this.jsPlumbInstance);

            if (success) {
                // Clear any existing NFA results since FSA changed
                if (window.nfaResultsManager) {
                    window.nfaResultsManager.clearStoredPaths();
                }
            }

        } catch (error) {
            console.error('Import error:', error);
            notificationManager.showError('Import Failed', error.message);
        } finally {
            // Clear the file input
            e.target.value = '';
        }
    }

    /**
     * Generate a default filename based on current date/time
     * @returns {string} - Default filename
     */
    generateDefaultFilename() {
        const now = new Date();
        const dateStr = now.toISOString().split('T')[0]; // YYYY-MM-DD
        const timeStr = now.toTimeString().split(' ')[0].replace(/:/g, '-'); // HH-MM-SS
        return `FSA_${dateStr}_${timeStr}`;
    }

    /**
     * Setup auto-save functionality
     * @param {number} intervalMs - Auto-save interval in milliseconds (default: 30 seconds)
     */
    setupAutoSave(intervalMs = 30000) {
        // Clear any existing auto-save interval
        if (this.autoSaveInterval) {
            clearInterval(this.autoSaveInterval);
        }

        // Set up new auto-save interval
        this.autoSaveInterval = setInterval(() => {
            // Only auto-save if there are states and controls aren't locked
            const states = document.querySelectorAll('.state, .accepting-state');
            if (states.length > 0 && !controlLockManager.isControlsLocked()) {
                this.quickSave();
            }
        }, intervalMs);

        console.log(`Auto-save enabled with ${intervalMs / 1000}s interval`);
        this.updateAutoSaveStatus('Auto-save: On');
    }

    /**
     * Disable auto-save
     */
    disableAutoSave() {
        if (this.autoSaveInterval) {
            clearInterval(this.autoSaveInterval);
            this.autoSaveInterval = null;
            console.log('Auto-save disabled');
            this.updateAutoSaveStatus('Auto-save: Off');
        }
    }

    /**
     * Quick save to localStorage (for auto-save functionality)
     */
    quickSave() {
        if (!this.jsPlumbInstance) return false;

        try {
            const fsaData = fsaSerializationManager.quickSave(this.jsPlumbInstance);
            if (fsaData) {
                localStorage.setItem('fsa_autosave', fsaData);
                localStorage.setItem('fsa_autosave_timestamp', new Date().toISOString());
                this.updateAutoSaveStatus('Auto-save: Saved', 'saving');

                // Reset status after 2 seconds
                setTimeout(() => {
                    this.updateAutoSaveStatus('Auto-save: On');
                }, 2000);

                return true;
            }
        } catch (error) {
            console.error('Quick save failed:', error);
            this.updateAutoSaveStatus('Auto-save: Error', 'error');

            // Reset status after 5 seconds
            setTimeout(() => {
                this.updateAutoSaveStatus('Auto-save: On');
            }, 5000);
        }
        return false;
    }

    /**
     * Quick load from localStorage
     */
    async quickLoad() {
        if (!this.jsPlumbInstance) return false;

        try {
            const fsaData = localStorage.getItem('fsa_autosave');
            if (fsaData) {
                const success = await fsaSerializationManager.quickLoad(fsaData, this.jsPlumbInstance);
                if (success) {
                    const timestamp = localStorage.getItem('fsa_autosave_timestamp');
                    const savedTime = timestamp ? new Date(timestamp).toLocaleString() : 'Unknown';
                    notificationManager.showSuccess(
                        'Auto-save Restored',
                        `Restored FSA from ${savedTime}`
                    );
                }
                return success;
            }
        } catch (error) {
            console.error('Quick load failed:', error);
        }
        return false;
    }

    /**
     * Check if auto-save data exists
     * @returns {boolean} - Whether auto-save data exists
     */
    hasAutoSave() {
        return localStorage.getItem('fsa_autosave') !== null;
    }

    /**
     * Clear auto-save data
     */
    clearAutoSave() {
        localStorage.removeItem('fsa_autosave');
        localStorage.removeItem('fsa_autosave_timestamp');
    }

    /**
     * Update auto-save status indicator
     * @param {string} text - Status text
     * @param {string} type - Status type ('saving', 'error', or normal)
     */
    updateAutoSaveStatus(text, type = '') {
        const statusElement = document.getElementById('auto-save-status');
        if (statusElement) {
            statusElement.textContent = text;
            statusElement.className = 'auto-save-status';
            if (type) {
                statusElement.classList.add(type);
            }
        }
    }

    /**
     * Show auto-save restore prompt on page load
     */
    showAutoSavePrompt() {
        if (this.hasAutoSave()) {
            const timestamp = localStorage.getItem('fsa_autosave_timestamp');
            const savedTime = timestamp ? new Date(timestamp).toLocaleString() : 'Unknown time';

            // Create a custom notification with restore option
            const notificationId = notificationManager.showInfo(
                'Auto-save Found',
                `An auto-saved FSA from ${savedTime} was found. Would you like to restore it?`,
                0 // Don't auto-hide
            );

            // Add restore button to the notification
            setTimeout(() => {
                const notification = document.getElementById(notificationId);
                if (notification) {
                    const buttonContainer = document.createElement('div');
                    buttonContainer.style.marginTop = '10px';
                    buttonContainer.style.textAlign = 'center';

                    const restoreBtn = document.createElement('button');
                    restoreBtn.textContent = 'Restore';
                    restoreBtn.className = 'btn btn-sm btn-primary';
                    restoreBtn.style.marginRight = '10px';
                    restoreBtn.onclick = async () => {
                        await this.quickLoad();
                        notificationManager.hideNotification(notificationId);
                    };

                    const ignoreBtn = document.createElement('button');
                    ignoreBtn.textContent = 'Ignore';
                    ignoreBtn.className = 'btn btn-sm btn-secondary';
                    ignoreBtn.onclick = () => {
                        notificationManager.hideNotification(notificationId);
                    };

                    buttonContainer.appendChild(restoreBtn);
                    buttonContainer.appendChild(ignoreBtn);

                    const detailsDiv = notification.querySelector('.popup-details');
                    if (detailsDiv) {
                        detailsDiv.appendChild(buttonContainer);
                    }
                }
            }, 200);
        }
    }

    /**
     * Update menu states based on control lock status
     * @param {boolean} locked - Whether controls are locked
     */
    updateMenuStates(locked) {
        const menuOptions = document.querySelectorAll('.menu-option');

        menuOptions.forEach(option => {
            if (locked) {
                option.classList.add('disabled');
            } else {
                option.classList.remove('disabled');
            }
        });
    }
}

// Create and export singleton instance
export const fsaFileUIManager = new FSAFileUIManager();

// Make globally available
window.fsaFileUIManager = fsaFileUIManager;

// Export class for potential multiple instances
export { FSAFileUIManager };