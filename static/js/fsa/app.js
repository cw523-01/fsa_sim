import { initialiseSimulator, setupEventListeners } from './main.js';

document.addEventListener('DOMContentLoaded', function() {
    // Initialize the simulator components
    initialiseSimulator();

    // Setup all event listeners
    setupEventListeners();
});