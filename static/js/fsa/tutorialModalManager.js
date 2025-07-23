/**
 * Tutorial Modal Manager
 * Handles the quick guide modal with tutorial GIFs
 */

class TutorialModalManager {
    constructor() {
        this.currentTutorial = 0;
        this.currentCategory = 'states';
        this.isOpen = false;

        // Tutorial data with categories and descriptions
        this.tutorials = {
            states: [
                {
                    id: 'add_state',
                    title: 'Add State',
                    description: 'Click on the canvas to create a new state.',
                    gif: 'states/add_state.gif'
                },
                {
                    id: 'add_state_via_drag',
                    title: 'Add State (Drag)',
                    description: 'Drag the state tool from the sidebar onto the canvas.',
                    gif: 'states/add_state_via_drag.gif'
                },
                {
                    id: 'add_accepting_state',
                    title: 'Add Accepting State',
                    description: 'Create an accepting state by clicking the accepting state tool then clicking the canvas.',
                    gif: 'states/add_accepting_state.gif'
                },
                {
                    id: 'add_accepting_state_via_drag',
                    title: 'Add Accepting State (Drag)',
                    description: 'Drag the accepting state tool from the sidebar onto the canvas.',
                    gif: 'states/add_accepting_state_via_drag.gif'
                },
                {
                    id: 'rename_state',
                    title: 'Rename State',
                    description: 'Click on a state to open the editor and change its name.',
                    gif: 'states/rename_state.gif'
                },
                {
                    id: 'starting_state',
                    title: 'Starting State',
                    description: 'Add a state to the canvas when there are no starting states to automatically create the starting state. Or specify which state is the starting state using the state editor.',
                    gif: 'states/starting_state.gif'
                }
            ],
            transitions: [
                {
                    id: 'add_transitions',
                    title: 'Add Transition',
                    description: 'Select the edge tool, then click on a source state and a target state to create a transition.',
                    gif: 'transitions/add_transition.gif'
                },
                {
                    id: 'add_self_loop',
                    title: 'Add Self Loop',
                    description: 'Create a self-loop by clicking the same state twice with the edge tool.',
                    gif: 'transitions/add_self_loop.gif'
                },
                {
                    id: 'add_symbol_to_transition',
                    title: 'Add Symbol to Transition',
                    description: 'Click on an existing transition to add or modify symbols via the editor (tip: you can click the transition label to open the editor).',
                    gif: 'transitions/add_symbol_to_transition.gif'
                },
                {
                    id: 'add_epsilon_transition',
                    title: 'Add Epsilon Transition',
                    description: 'Create epsilon (ε) transitions by checking the epsilon option in the transition dialog.',
                    gif: 'transitions/add_epsilon_transition.gif'
                },
                {
                    id: 'edge_styles',
                    title: 'Edge Styles',
                    description: 'Click the edge style buttons to switch between curved and straight styles for your transition edges, or set them individually in the transition editor.',
                    gif: 'transitions/edge_styles.gif'
                }
            ],
            delete: [
                {
                    id: 'delete_elements',
                    title: 'Delete Elements',
                    description: 'Select the delete tool and click on states or transitions to remove them.',
                    gif: 'delete/delete_elements.gif'
                }
            ],
            simulation: [
                {
                    id: 'simulating_dfa',
                    title: 'Simulate DFA',
                    description: 'Enter an input string and press play to see step-by-step execution through your DFA. Click fast-forward to instantly see if the input is accepted.',
                    gif: 'simulation/simulating_dfa.gif'
                },
                {
                    id: 'simulating_nfa',
                    title: 'Simulate NFA',
                    description: 'Simulate non-deterministic finite automata with multiple possible paths. Click fast-forward to instantly see if the input is accepted.',
                    gif: 'simulation/simulating_nfa.gif'
                }
            ]
        };

        // Flatten tutorials for navigation
        this.allTutorials = [];
        Object.keys(this.tutorials).forEach(category => {
            this.tutorials[category].forEach(tutorial => {
                this.allTutorials.push({
                    ...tutorial,
                    category: category
                });
            });
        });

        this.elements = {};
        this.initialised = false;
    }

    /**
     * Initialise the tutorial modal
     */
    initialise() {
        if (this.initialised) return;

        // Get DOM elements
        this.elements = {
            modal: document.getElementById('tutorial-modal'),
            helpBtn: document.getElementById('help-btn'),
            closeBtn: document.getElementById('close-tutorial-modal'),
            tutorialTitle: document.getElementById('tutorial-title'),
            tutorialDescription: document.getElementById('tutorial-description'),
            tutorialGif: document.getElementById('tutorial-gif'),
            currentTutorial: document.getElementById('current-tutorial'),
            totalTutorials: document.getElementById('total-tutorials'),
            prevBtn: document.getElementById('prev-tutorial'),
            nextBtn: document.getElementById('next-tutorial'),
            categories: document.querySelectorAll('.tutorial-category'),
            tutorialItems: document.querySelectorAll('.tutorial-item')
        };

        this.setupEventListeners();
        this.updateDisplay();
        this.initialised = true;

    }

    /**
     * Setup event listeners
     */
    setupEventListeners() {
        // Open modal
        if (this.elements.helpBtn) {
            this.elements.helpBtn.addEventListener('click', () => this.openModal());
        }

        // Close modal
        if (this.elements.closeBtn) {
            this.elements.closeBtn.addEventListener('click', () => this.closeModal());
        }

        // Close on backdrop click
        if (this.elements.modal) {
            this.elements.modal.addEventListener('click', (e) => {
                if (e.target === this.elements.modal) {
                    this.closeModal();
                }
            });
        }

        // Navigation buttons
        if (this.elements.prevBtn) {
            this.elements.prevBtn.addEventListener('click', () => this.previousTutorial());
        }

        if (this.elements.nextBtn) {
            this.elements.nextBtn.addEventListener('click', () => this.nextTutorial());
        }

        // Category clicks
        this.elements.categories.forEach(category => {
            const categoryName = category.dataset.category;
            const header = category.querySelector('h3');
            if (header) {
                header.addEventListener('click', () => this.selectCategory(categoryName));
            }
        });

        // Tutorial item clicks
        this.elements.tutorialItems.forEach(item => {
            item.addEventListener('click', () => {
                const tutorialId = item.dataset.tutorial;
                this.selectTutorial(tutorialId);
            });
        });

        // Keyboard navigation
        document.addEventListener('keydown', (e) => {
            if (!this.isOpen) return;

            switch (e.key) {
                case 'Escape':
                    this.closeModal();
                    break;
                case 'ArrowLeft':
                    this.previousTutorial();
                    break;
                case 'ArrowRight':
                    this.nextTutorial();
                    break;
            }
        });
    }

    /**
     * Open the tutorial modal
     */
    openModal() {
        if (!this.elements.modal) return;

        this.isOpen = true;
        this.elements.modal.style.display = 'flex';

        // Lock body scroll
        document.body.style.overflow = 'hidden';

        // Load current tutorial GIF
        this.loadCurrentGif();

        console.log('Tutorial modal opened');
    }

    /**
     * Close the tutorial modal
     */
    closeModal() {
        if (!this.elements.modal) return;

        this.isOpen = false;
        this.elements.modal.style.display = 'none';

        // Restore body scroll
        document.body.style.overflow = '';

        console.log('Tutorial modal closed');
    }

    /**
     * Select a category
     */
    selectCategory(categoryName) {
        if (!this.tutorials[categoryName]) return;

        this.currentCategory = categoryName;

        // Update active category
        this.elements.categories.forEach(cat => {
            cat.classList.toggle('active', cat.dataset.category === categoryName);
        });

        // Select first tutorial in category
        const firstTutorial = this.tutorials[categoryName][0];
        if (firstTutorial) {
            this.selectTutorial(firstTutorial.id);
        }
    }

    /**
     * Select a specific tutorial
     */
    selectTutorial(tutorialId) {
        const tutorialIndex = this.allTutorials.findIndex(t => t.id === tutorialId);
        if (tutorialIndex === -1) return;

        this.currentTutorial = tutorialIndex;
        this.updateDisplay();
        this.loadCurrentGif();
    }

    /**
     * Navigate to previous tutorial
     */
    previousTutorial() {
        if (this.currentTutorial > 0) {
            this.currentTutorial--;
            this.updateDisplay();
            this.loadCurrentGif();
        }
    }

    /**
     * Navigate to next tutorial
     */
    nextTutorial() {
        if (this.currentTutorial < this.allTutorials.length - 1) {
            this.currentTutorial++;
            this.updateDisplay();
            this.loadCurrentGif();
        }
    }

    /**
     * Update the display with current tutorial info
     */
    updateDisplay() {
        const tutorial = this.allTutorials[this.currentTutorial];
        if (!tutorial) return;

        // Update tutorial info
        if (this.elements.tutorialTitle) {
            this.elements.tutorialTitle.textContent = tutorial.title;
        }

        if (this.elements.tutorialDescription) {
            this.elements.tutorialDescription.textContent = tutorial.description;
        }

        // Update counter
        if (this.elements.currentTutorial) {
            this.elements.currentTutorial.textContent = this.currentTutorial + 1;
        }

        if (this.elements.totalTutorials) {
            this.elements.totalTutorials.textContent = this.allTutorials.length;
        }

        // Update navigation buttons
        if (this.elements.prevBtn) {
            this.elements.prevBtn.disabled = this.currentTutorial === 0;
        }

        if (this.elements.nextBtn) {
            this.elements.nextBtn.disabled = this.currentTutorial === this.allTutorials.length - 1;
        }

        // Update active category
        this.currentCategory = tutorial.category;
        this.elements.categories.forEach(cat => {
            cat.classList.toggle('active', cat.dataset.category === tutorial.category);
        });

        // Update active tutorial item
        this.elements.tutorialItems.forEach(item => {
            item.classList.toggle('active', item.dataset.tutorial === tutorial.id);
        });
    }

    /**
     * Load the current tutorial GIF
     */
    loadCurrentGif() {
        const tutorial = this.allTutorials[this.currentTutorial];
        if (!tutorial || !this.elements.tutorialGif) return;

        // Show loading state
        const loadingElement = document.querySelector('.tutorial-loading');
        if (loadingElement) {
            loadingElement.style.display = 'block';
        }

        // Hide GIF temporarily
        this.elements.tutorialGif.style.display = 'none';

        // Construct GIF path (assumes Django static file structure)
        const gifPath = `/static/img/tutorials/${tutorial.gif}`;

        // Create a new image to preload
        const img = new Image();
        img.onload = () => {
            // Update src and show GIF when loaded
            this.elements.tutorialGif.src = gifPath;
            this.elements.tutorialGif.style.display = 'block';

            // Hide loading state
            if (loadingElement) {
                loadingElement.style.display = 'none';
            }
        };

        img.onerror = () => {
            console.error(`Failed to load tutorial GIF: ${gifPath}`);

            // Hide loading state and show error
            if (loadingElement) {
                loadingElement.textContent = 'Failed to load tutorial';
                loadingElement.style.display = 'block';
            }
        };

        // Start loading
        img.src = gifPath;
    }

    /**
     * Get total number of tutorials
     */
    getTotalTutorials() {
        return this.allTutorials.length;
    }

    /**
     * Check if modal is open
     */
    isModalOpen() {
        return this.isOpen;
    }
}

// Create singleton instance
const tutorialModalManager = new TutorialModalManager();

// Initialise when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    tutorialModalManager.initialise();
});

// Make globally available
window.tutorialModalManager = tutorialModalManager;

// Export for module systems
export { TutorialModalManager, tutorialModalManager };