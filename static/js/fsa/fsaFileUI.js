// fsaFileUI.js - UI integration for FSA file management with menu bar

import { fsaSerializationManager } from './fsaSerializationManager.js';
import { notificationManager } from './notificationManager.js';
import { controlLockManager } from './controlLockManager.js';
import { undoRedoManager } from './undoRedoManager.js';

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
                // Also close file operation popups
                this.hideSavePopup();
                this.hideNewFilePopup();
                this.hideImportConfirmPopup();
                // Close transform popups if available
                if (window.fsaTransformManager) {
                    window.fsaTransformManager.hideMinimizePopup();
                }
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
            if ((e.ctrlKey || e.metaKey) && e.altKey && e.key === 'n') {
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

        // Also close transform menu if available
        if (window.fsaTransformManager) {
            window.fsaTransformManager.closeTransformMenu();
        }

        // Close edit menu dropdown
        const editDropdown = document.getElementById('edit-dropdown');
        const editButton = document.getElementById('edit-menu-button');

        if (editDropdown) {
            editDropdown.classList.remove('show');
        }
        if (editButton) {
            editButton.classList.remove('active');
        }
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

        // Show custom save popup instead of direct export
        this.showSavePopup(customFilename);
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

        // Check if current FSA exists and show custom popup
        const states = document.querySelectorAll('.state, .accepting-state');
        if (states.length > 0) {
            this.showImportConfirmPopup();
        } else {
            // If no states exist, proceed directly to file selection
            this.triggerFileInput();
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

        // Check if current FSA exists and show custom popup
        const states = document.querySelectorAll('.state, .accepting-state');
        if (states.length > 0) {
            this.showNewFilePopup();
        } else {
            // If no states exist, just clear directly
            this.performNewFSA();
        }
    }

    /**
     * Show custom save popup
     * @param {string} suggestedFilename - Optional suggested filename
     */
    showSavePopup(suggestedFilename = null) {
        // Remove any existing popup
        const existingPopup = document.getElementById('file-operation-popup');
        if (existingPopup) {
            existingPopup.remove();
        }

        // Create popup element
        const popup = document.createElement('div');
        popup.id = 'file-operation-popup';
        popup.className = 'file-operation-popup save';

        const defaultFilename = suggestedFilename || this.generateDefaultFilename();
        const statesCount = document.querySelectorAll('.state, .accepting-state').length;
        const edgesCount = this.jsPlumbInstance ? this.jsPlumbInstance.getAllConnections().filter(conn =>
            !conn.canvas || !conn.canvas.classList.contains('starting-connection')
        ).length : 0;

        popup.innerHTML = `
            <div class="popup-header">
                <div class="popup-title">
                    <div class="popup-icon">
                        <img src="static/img/success.png" alt="Save" style="width: 20px; height: 20px;">
                    </div>
                    <span>Export FSA</span>
                </div>
                <button class="popup-close" onclick="fsaFileUIManager.hideSavePopup()">×</button>
            </div>
            <div class="file-operation-content">
                <div class="file-operation-description">
                    Save your finite state automaton as a JSON file that can be imported later.
                </div>
                
                <div class="states-info">
                    Current FSA: <span class="states-count">${statesCount} states</span> and <span class="states-count">${edgesCount} transitions</span>
                </div>

                <div class="form-group">
                    <label for="save-filename-input">Filename:</label>
                    <input type="text" id="save-filename-input" value="${defaultFilename}" maxlength="100">
                    <div class="input-help">Enter a name for your FSA file (without .json extension)</div>
                    <div class="input-error" id="save-filename-error">Filename cannot be empty</div>
                    <div class="auto-filename-note">Leave empty for auto-generated timestamp filename</div>
                </div>


                <div class="filename-preview">
                    <div class="filename-preview-label">File will be saved as:</div>
                    <div class="filename-preview-value" id="save-filename-preview">${defaultFilename}<span class="filename-extension">.json</span></div>
                </div>
            </div>
            <div class="file-operation-actions">
                <button class="file-action-btn cancel" onclick="fsaFileUIManager.hideSavePopup()">
                    Cancel
                </button>
                <button class="file-action-btn primary" id="save-confirm-btn" onclick="fsaFileUIManager.confirmSave()">
                    Export File
                </button>
            </div>
        `;

        // Add popup to canvas
        const canvas = document.getElementById('fsa-canvas');
        if (canvas) {
            canvas.appendChild(popup);

            // Setup event handlers
            this.setupSavePopupHandlers();

            // Trigger show animation
            setTimeout(() => {
                popup.classList.add('show');
                // Focus on filename input and select text
                const filenameInput = document.getElementById('save-filename-input');
                if (filenameInput) {
                    filenameInput.focus();
                    filenameInput.select();
                }
            }, 100);
        }
    }

    /**
     * Setup event handlers for save popup
     */
    setupSavePopupHandlers() {
        const filenameInput = document.getElementById('save-filename-input');
        const filenamePreview = document.getElementById('save-filename-preview');
        const filenameError = document.getElementById('save-filename-error');
        const saveBtn = document.getElementById('save-confirm-btn');

        if (filenameInput && filenamePreview) {
            filenameInput.addEventListener('input', () => {
                const value = filenameInput.value.trim();
                const cleanValue = this.sanitizeFilename(value);

                if (cleanValue !== value) {
                    filenameInput.value = cleanValue;
                }

                const displayName = cleanValue || this.generateDefaultFilename();
                filenamePreview.innerHTML = `${displayName}<span class="filename-extension">.json</span>`;

                // Validation
                const formGroup = filenameInput.closest('.form-group');
                if (cleanValue.length === 0) {
                    formGroup.classList.remove('valid');
                    formGroup.classList.add('invalid');
                    filenameError.classList.add('show');
                    saveBtn.classList.add('disabled');
                } else {
                    formGroup.classList.remove('invalid');
                    formGroup.classList.add('valid');
                    filenameError.classList.remove('show');
                    saveBtn.classList.remove('disabled');
                }
            });

            // Enter key to save
            filenameInput.addEventListener('keydown', (e) => {
                if (e.key === 'Enter' && !saveBtn.classList.contains('disabled')) {
                    this.confirmSave();
                }
            });
        }
    }

    /**
     * Hide save popup
     */
    hideSavePopup() {
        const popup = document.getElementById('file-operation-popup');
        if (popup) {
            popup.classList.add('hide');
            setTimeout(() => {
                if (popup.parentNode) {
                    popup.parentNode.removeChild(popup);
                }
            }, 300);
        }
    }

    /**
     * Confirm save operation
     */
    confirmSave() {
        const saveBtn = document.getElementById('save-confirm-btn');
        if (saveBtn.classList.contains('disabled')) {
            return;
        }

        const filenameInput = document.getElementById('save-filename-input');
        const filename = filenameInput ? filenameInput.value.trim() : '';
        const finalFilename = filename || this.generateDefaultFilename();

        // Show saving state
        saveBtn.classList.add('saving');
        saveBtn.disabled = true;

        try {
            fsaSerializationManager.exportToFile(this.jsPlumbInstance, finalFilename);

            // Hide popup after successful save
            setTimeout(() => {
                this.hideSavePopup();
            }, 500);

        } catch (error) {
            console.error('Export error:', error);
            notificationManager.showError('Export Failed', error.message);

            // Reset button state
            saveBtn.classList.remove('saving');
            saveBtn.disabled = false;
        }
    }

    /**
     * Show custom new file popup
     */
    showNewFilePopup() {
        // Remove any existing popup
        const existingPopup = document.getElementById('file-operation-popup');
        if (existingPopup) {
            existingPopup.remove();
        }

        // Create popup element
        const popup = document.createElement('div');
        popup.id = 'file-operation-popup';
        popup.className = 'file-operation-popup new';

        const statesCount = document.querySelectorAll('.state, .accepting-state').length;
        const edgesCount = this.jsPlumbInstance ? this.jsPlumbInstance.getAllConnections().filter(conn =>
            !conn.canvas || !conn.canvas.classList.contains('starting-connection')
        ).length : 0;

        popup.innerHTML = `
            <div class="popup-header">
                <div class="popup-title">
                    <div class="popup-icon">
                        <img src="static/img/alert.png" alt="Warning" style="width: 20px; height: 20px;">
                    </div>
                    <span>New FSA</span>
                </div>
                <button class="popup-close" onclick="fsaFileUIManager.hideNewFilePopup()">×</button>
            </div>
            <div class="file-operation-content">
                <div class="file-operation-description">
                    Creating a new FSA will permanently clear the current automaton.
                </div>
                
                <div class="states-info">
                    Current FSA: <span class="states-count">${statesCount} states</span> and <span class="states-count">${edgesCount} transitions</span>
                </div>

                <div class="warning-section">
                    <span class="warning-icon">⚠️</span>
                    <div class="warning-text">
                        <strong>Warning:</strong> This action cannot be undone. All states and transitions will be permanently deleted. 
                        Consider exporting your current FSA first if you want to save it.
                    </div>
                </div>
            </div>
            <div class="file-operation-actions">
                <button class="file-action-btn cancel" onclick="fsaFileUIManager.hideNewFilePopup()">
                    Cancel
                </button>
                <button class="file-action-btn primary" onclick="fsaFileUIManager.confirmNewFile()">
                    Clear and Create New
                </button>
            </div>
        `;

        // Add popup to canvas
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
     * Hide new file popup
     */
    hideNewFilePopup() {
        const popup = document.getElementById('file-operation-popup');
        if (popup) {
            popup.classList.add('hide');
            setTimeout(() => {
                if (popup.parentNode) {
                    popup.parentNode.removeChild(popup);
                }
            }, 300);
        }
    }

    /**
     * Confirm new file operation
     */
    confirmNewFile() {
        this.hideNewFilePopup();
        this.performNewFSA();
    }

    /**
     * Show custom import confirmation popup
     */
    showImportConfirmPopup() {
        // Remove any existing popup
        const existingPopup = document.getElementById('file-operation-popup');
        if (existingPopup) {
            existingPopup.remove();
        }

        // Create popup element
        const popup = document.createElement('div');
        popup.id = 'file-operation-popup';
        popup.className = 'file-operation-popup import';

        const statesCount = document.querySelectorAll('.state, .accepting-state').length;
        const edgesCount = this.jsPlumbInstance ? this.jsPlumbInstance.getAllConnections().filter(conn =>
            !conn.canvas || !conn.canvas.classList.contains('starting-connection')
        ).length : 0;

        popup.innerHTML = `
            <div class="popup-header">
                <div class="popup-title">
                    <div class="popup-icon">
                        <img src="static/img/alert.png" alt="Warning" style="width: 20px; height: 20px;">
                    </div>
                    <span>Import FSA</span>
                </div>
                <button class="popup-close" onclick="fsaFileUIManager.hideImportConfirmPopup()">×</button>
            </div>
            <div class="file-operation-content">
                <div class="file-operation-description">
                    Importing a new FSA will permanently replace the current automaton.
                </div>

                <div class="warning-section">
                    <span class="warning-icon">⚠️</span>
                    <div class="warning-text">
                        <strong>Warning:</strong> All current states and transitions labels will be permanently replaced with the imported FSA. 
                        Consider exporting your current FSA first if you want to save it.
                    </div>
                </div>
            </div>
            <div class="file-operation-actions">
                <button class="file-action-btn cancel" onclick="fsaFileUIManager.hideImportConfirmPopup()">
                    Cancel
                </button>
                <button class="file-action-btn primary" onclick="fsaFileUIManager.confirmImport()">
                    Select File to Import
                </button>
            </div>
        `;

        // Add popup to canvas
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
     * Hide import confirmation popup
     */
    hideImportConfirmPopup() {
        const popup = document.getElementById('file-operation-popup');
        if (popup) {
            popup.classList.add('hide');
            setTimeout(() => {
                if (popup.parentNode) {
                    popup.parentNode.removeChild(popup);
                }
            }, 300);
        }
    }

    /**
     * Confirm import operation and trigger file selection
     */
    confirmImport() {
        this.hideImportConfirmPopup();
        this.triggerFileInput();
    }

    /**
     * Trigger the file input for import
     */
    triggerFileInput() {
        const fileInput = document.getElementById('fsa-file-input');
        if (fileInput) {
            fileInput.click();
        }
    }

    /**
     * Perform the actual new FSA operation
     */
    performNewFSA() {
        try {
            // Create snapshot before clearing for undo/redo
            if (undoRedoManager && !undoRedoManager.isProcessing()) {
                const snapshotCommand = undoRedoManager.createSnapshotCommand('New FSA (clear all)');

                fsaSerializationManager.clearCurrentFSA(this.jsPlumbInstance);

                // Clear any existing NFA results
                if (window.nfaResultsManager) {
                    window.nfaResultsManager.clearStoredPaths();
                }

                undoRedoManager.finishSnapshotCommand(snapshotCommand);
            } else {
                // Fallback without undo/redo
                fsaSerializationManager.clearCurrentFSA(this.jsPlumbInstance);
                if (window.nfaResultsManager) {
                    window.nfaResultsManager.clearStoredPaths();
                }
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
            // Create snapshot before import for undo/redo
            if (undoRedoManager && !undoRedoManager.isProcessing()) {
                const snapshotCommand = undoRedoManager.createSnapshotCommand(`Import FSA from ${file.name}`);

                const success = await fsaSerializationManager.importFromFile(file, this.jsPlumbInstance);

                if (success) {
                    // Clear any existing NFA results since FSA changed
                    if (window.nfaResultsManager) {
                        window.nfaResultsManager.clearStoredPaths();
                    }

                    undoRedoManager.finishSnapshotCommand(snapshotCommand);
                } else {
                    // If import failed, don't save the snapshot
                    console.log('Import failed, not saving undo snapshot');
                }
            } else {
                // Fallback without undo/redo
                const success = await fsaSerializationManager.importFromFile(file, this.jsPlumbInstance);
                if (success && window.nfaResultsManager) {
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
     * Sanitize filename to remove invalid characters
     * @param {string} filename - Raw filename input
     * @returns {string} - Sanitized filename
     */
    sanitizeFilename(filename) {
        // Remove invalid characters for filenames
        return filename.replace(/[<>:"/\\|?*\x00-\x1f]/g, '')
                      .replace(/\.$/, '') // Remove trailing period
                      .substring(0, 100); // Limit length
    }

    /**
     * Update menu states based on control lock status
     * @param {boolean} locked - Whether controls are locked
     */
    updateMenuStates(locked) {
        const menuOptions = document.querySelectorAll('#file-dropdown .menu-option');

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