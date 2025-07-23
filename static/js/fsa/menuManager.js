/**
 * Universal Menu Manager - handles all dropdown menus consistently
 */
class MenuManager {
    constructor() {
        this.currentOpenMenu = null;
        this.menuConfigs = new Map();
        this.initialised = false;
    }

    /**
     * Initialise the menu manager
     */
    initialise() {
        if (this.initialised) {
            return;
        }

        this.setupGlobalEventListeners();
        this.initialised = true;
    }

    /**
     * Register a menu with the manager
     * @param {string} menuId - Unique identifier for the menu
     * @param {Object} config - Menu configuration
     * @param {string} config.buttonId - ID of the button that toggles the menu
     * @param {string} config.dropdownId - ID of the dropdown element
     * @param {Function} [config.onOpen] - Callback when menu opens
     * @param {Function} [config.onClose] - Callback when menu closes
     */
    registerMenu(menuId, config) {
        this.menuConfigs.set(menuId, {
            buttonId: config.buttonId,
            dropdownId: config.dropdownId,
            onOpen: config.onOpen || (() => {}),
            onClose: config.onClose || (() => {})
        });

        // Setup event listener for this menu's button
        this.setupMenuButton(menuId);

        console.log(`Registered menu: ${menuId}`);
    }

    /**
     * Setup event listener for a menu button
     * @param {string} menuId - The menu ID to setup
     */
    setupMenuButton(menuId) {
        const config = this.menuConfigs.get(menuId);
        if (!config) return;

        const button = document.getElementById(config.buttonId);
        if (!button) {
            console.warn(`Button not found: ${config.buttonId}`);
            return;
        }

        // Remove any existing listeners by cloning the button
        const newButton = button.cloneNode(true);
        button.parentNode.replaceChild(newButton, button);

        // Add the new listener
        newButton.addEventListener('click', (e) => {
            e.stopPropagation();
            this.toggleMenu(menuId);
        });
    }

    /**
     * Toggle a specific menu
     * @param {string} menuId - The menu to toggle
     */
    toggleMenu(menuId) {
        const config = this.menuConfigs.get(menuId);
        if (!config) {
            console.warn(`Menu not found: ${menuId}`);
            return;
        }

        const dropdown = document.getElementById(config.dropdownId);
        const button = document.getElementById(config.buttonId);

        if (!dropdown || !button) {
            console.warn(`Menu elements not found for: ${menuId}`);
            return;
        }

        const isCurrentlyOpen = this.currentOpenMenu === menuId;

        // Close all menus first
        this.closeAllMenus();

        // If this menu wasn't open, open it now
        if (!isCurrentlyOpen) {
            this.openMenu(menuId);
        }
    }

    /**
     * Open a specific menu
     * @param {string} menuId - The menu to open
     */
    openMenu(menuId) {
        const config = this.menuConfigs.get(menuId);
        if (!config) return;

        const dropdown = document.getElementById(config.dropdownId);
        const button = document.getElementById(config.buttonId);

        if (!dropdown || !button) return;

        // Close any other open menu first
        this.closeAllMenus();

        // Open this menu
        dropdown.classList.add('show');
        button.classList.add('active');
        this.currentOpenMenu = menuId;

        // Call onOpen callback
        config.onOpen();

        console.log(`Opened menu: ${menuId}`);
    }

    /**
     * Close a specific menu
     * @param {string} menuId - The menu to close
     */
    closeMenu(menuId) {
        const config = this.menuConfigs.get(menuId);
        if (!config) return;

        const dropdown = document.getElementById(config.dropdownId);
        const button = document.getElementById(config.buttonId);

        if (!dropdown || !button) return;

        dropdown.classList.remove('show');
        button.classList.remove('active');

        if (this.currentOpenMenu === menuId) {
            this.currentOpenMenu = null;
        }

        // Call onClose callback
        config.onClose();

        console.log(`Closed menu: ${menuId}`);
    }

    /**
     * Close all open menus
     */
    closeAllMenus() {
        this.menuConfigs.forEach((config, menuId) => {
            const dropdown = document.getElementById(config.dropdownId);
            const button = document.getElementById(config.buttonId);

            if (dropdown && button) {
                dropdown.classList.remove('show');
                button.classList.remove('active');

                // Call onClose callback
                config.onClose();
            }
        });

        this.currentOpenMenu = null;
        console.log('Closed all menus');
    }

    /**
     * Check if any menu is currently open
     * @returns {boolean}
     */
    isAnyMenuOpen() {
        return this.currentOpenMenu !== null;
    }

    /**
     * Get the currently open menu ID
     * @returns {string|null}
     */
    getCurrentOpenMenu() {
        return this.currentOpenMenu;
    }

    /**
     * Setup global event listeners
     */
    setupGlobalEventListeners() {
        // Close menus when clicking outside
        document.addEventListener('click', (e) => {
            // Check if click is inside any menu
            let isInsideMenu = false;

            this.menuConfigs.forEach((config) => {
                const button = document.getElementById(config.buttonId);
                const dropdown = document.getElementById(config.dropdownId);

                if ((button && button.contains(e.target)) ||
                    (dropdown && dropdown.contains(e.target))) {
                    isInsideMenu = true;
                }
            });

            if (!isInsideMenu) {
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
     * Update menu states based on control lock status
     * @param {boolean} locked - Whether controls are locked
     */
    updateMenuStates(locked) {
        this.menuConfigs.forEach((config) => {
            const dropdown = document.getElementById(config.dropdownId);
            if (!dropdown) return;

            const menuOptions = dropdown.querySelectorAll('.menu-option');
            menuOptions.forEach(option => {
                if (locked) {
                    option.classList.add('disabled');
                } else {
                    option.classList.remove('disabled');
                }
            });
        });
    }

    /**
     * Destroy the menu manager and clean up
     */
    destroy() {
        this.closeAllMenus();
        this.menuConfigs.clear();
        this.currentOpenMenu = null;
        this.initialised = false;
        console.log('Menu Manager destroyed');
    }

    /**
     * Register a menu item with automatic event handling
     * @param {string} menuItemId - ID of the menu item element
     * @param {Function} handler - Function to call when clicked
     * @param {Object} options - Additional options
     */
    registerMenuItem(menuItemId, handler, options = {}) {
        let menuItem = document.getElementById(menuItemId);
        if (!menuItem) {
            console.warn(`Menu item not found: ${menuItemId}`);
            return;
        }

        // Clone to remove existing handlers if needed
        if (options.clone !== false) {
            const newMenuItem = menuItem.cloneNode(true);
            menuItem.parentNode.replaceChild(newMenuItem, menuItem);
            menuItem = newMenuItem;
        }

        menuItem.addEventListener('click', (e) => {
            e.stopPropagation();

            // Close all menus
            this.closeAllMenus();

            // Check if controls are locked (if validation function provided)
            if (options.validateUnlocked && window.controlLockManager?.isControlsLocked()) {
                console.log(`Cannot execute ${menuItemId} while controls are locked`);
                return;
            }

            // Call the handler
            try {
                handler(e);
            } catch (error) {
                console.error(`Error in menu handler for ${menuItemId}:`, error);
            }
        });

        console.log(`Registered menu item: ${menuItemId}`);
    }

    /**
     * Register multiple menu items at once
     * @param {Object} menuItems - Object mapping IDs to handlers
     * @param {Object} commonOptions - Options applied to all items
     */
    registerMenuItems(menuItems, commonOptions = {}) {
        Object.entries(menuItems).forEach(([menuItemId, handler]) => {
            this.registerMenuItem(menuItemId, handler, commonOptions);
        });
    }
}

// Create and export singleton instance
export const menuManager = new MenuManager();

// Make globally available
window.menuManager = menuManager;

// Export class for potential multiple instances
export { MenuManager };