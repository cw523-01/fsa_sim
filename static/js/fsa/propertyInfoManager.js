/**
 * Property Info Manager
 * Handles showing/hiding property information popups
 */

class PropertyInfoManager {
    constructor() {
        this.backdrop = null;
        this.popup = null;
        this.currentProperty = null;
        this.hideTimeout = null;

        // Property descriptions
        this.propertyDescriptions = {
            connected: {
                title: 'Connected',
                description: 'A finite state automaton is connected if there is a path from the starting state to every other state in the automaton. This ensures that all states are reachable and no states are isolated.'
            },
            deterministic: {
                title: 'Deterministic',
                description: 'A finite state automaton is deterministic (DFA) if for each state and input symbol, there is at most one transition. Non-deterministic (NFA) allows multiple transitions for the same state-symbol pair or epsilon transitions.'
            },
            complete: {
                title: 'Complete',
                description: 'A finite state automaton is complete if for every state and every symbol in the alphabet, there exists at least one outgoing transition. Complete automata have no undefined transitions.'
            },
            alphabet: {
                title: 'Alphabet (Σ)',
                description: 'The alphabet is the finite set of symbols that the automaton can read as input. It contains all unique symbols used in the transitions of the automaton. The Greek letter Σ (sigma) is conventionally used to denote the alphabet in formal language theory.'
            },
            'transition-table': {
                title: 'Transition Table',
                description: 'A transition table (T-table) is a tabular representation of the automaton that shows all possible state transitions for each input symbol. Each row represents a state, each column represents an input symbol, and each cell contains the resulting state(s) after reading that symbol.'
            },
            'epsilon-transition': {
                title: 'Epsilon (ε) Transition',
                description: 'An epsilon transition (also called lambda transition) allows the automaton to change states without consuming any input symbol. It represents a "free move" between states and will make an automaton non-deterministic (NFA). Epsilon transitions are often used to combine multiple automata or create optional paths.'
            }
        };
    }

    /**
     * Initialize the property info manager
     */
    initialize() {
        this.backdrop = document.getElementById('property-info-backdrop');
        this.popup = document.getElementById('property-info-popup');
        this.setupEventListeners();
        console.log('Property Info Manager initialized');
    }

    /**
     * Setup event listeners for property info icons
     */
    setupEventListeners() {
        // Add click listeners to all property info icons
        const infoIcons = document.querySelectorAll('.property-info-icon');

        infoIcons.forEach(icon => {
            icon.addEventListener('click', (e) => {
                e.stopPropagation();
                const property = icon.getAttribute('data-property');
                this.showPropertyInfo(property, icon);
            });
        });

        // Close button event listener
        const closeButton = document.getElementById('close-property-info');
        if (closeButton) {
            closeButton.addEventListener('click', () => {
                this.hidePropertyInfo();
            });
        }

        // Close popup when clicking outside (on backdrop)
        if (this.backdrop) {
            this.backdrop.addEventListener('click', (e) => {
                if (e.target === this.backdrop) {
                    this.hidePropertyInfo();
                }
            });
        }

        // Close popup on Escape key
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && this.backdrop && this.backdrop.classList.contains('show')) {
                this.hidePropertyInfo();
            }
        });
    }

    /**
     * Show property information popup
     * @param {string} property - The property type (connected, deterministic, complete)
     * @param {HTMLElement} iconElement - The clicked icon element (not used for positioning anymore)
     */
    showPropertyInfo(property, iconElement) {
        if (!this.backdrop || !this.popup || !this.propertyDescriptions[property]) {
            console.error('Property info popup elements or property description not found:', property);
            return;
        }

        // Clear any existing hide timeout
        if (this.hideTimeout) {
            clearTimeout(this.hideTimeout);
            this.hideTimeout = null;
        }

        // Hide current popup if showing a different property
        if (this.currentProperty && this.currentProperty !== property) {
            this.hidePropertyInfo(false); // Don't animate, we'll show new one immediately
        }

        this.currentProperty = property;
        const info = this.propertyDescriptions[property];

        // Update popup content
        const titleElement = document.getElementById('property-info-title');
        const descriptionElement = document.getElementById('property-info-description');

        if (titleElement) titleElement.textContent = info.title;
        if (descriptionElement) descriptionElement.textContent = info.description;

        // Update popup styling based on property type
        this.popup.className = `property-info-popup ${property}`;

        // Show the backdrop and popup (now always centered)
        this.backdrop.classList.add('show');

        console.log(`Showing property info for: ${property}`);

        // Note: Removed auto-hide timeout - popup will stay open until manually closed
    }

    /**
     * Hide the property information popup
     * @param {boolean} animate - Whether to animate the hiding (default: true)
     */
    hidePropertyInfo(animate = true) {
        if (!this.backdrop) return;

        // Clear any existing timeout
        if (this.hideTimeout) {
            clearTimeout(this.hideTimeout);
            this.hideTimeout = null;
        }

        if (animate) {
            // Add fade out class for animation
            this.backdrop.style.transition = 'opacity var(--transition-normal)';
            this.backdrop.style.opacity = '0';

            // Hide backdrop after animation completes
            setTimeout(() => {
                this.backdrop.classList.remove('show');
                this.backdrop.style.opacity = '';
                this.backdrop.style.transition = '';
                this.currentProperty = null;
            }, 300);
        } else {
            this.backdrop.classList.remove('show');
            this.currentProperty = null;
        }

        console.log('Property info popup hidden');
    }

    /**
     * Check if a property info popup is currently showing
     * @returns {boolean} - True if a popup is showing
     */
    isShowing() {
        return this.backdrop && this.backdrop.classList.contains('show');
    }

    /**
     * Get the currently displayed property
     * @returns {string|null} - The current property name or null
     */
    getCurrentProperty() {
        return this.currentProperty;
    }

    /**
     * Clean up the property info manager
     */
    destroy() {
        if (this.hideTimeout) {
            clearTimeout(this.hideTimeout);
            this.hideTimeout = null;
        }

        // Remove event listeners
        const infoIcons = document.querySelectorAll('.property-info-icon');
        infoIcons.forEach(icon => {
            icon.removeEventListener('click', this.handleIconClick);
        });

        console.log('Property Info Manager destroyed');
    }
}

// Create singleton instance
const propertyInfoManager = new PropertyInfoManager();

// Make globally available
window.propertyInfoManager = propertyInfoManager;

// Export for module systems
export { PropertyInfoManager, propertyInfoManager };