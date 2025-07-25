import { getStartingStateId } from './stateManager.js';
import { getEdgeSymbolMap, getEpsilonTransitionMap, getEpsilonSymbol } from './edgeManager.js';

/**
 * Generates a transition table from the current automaton
 * @param {Object} jsPlumbInstance - The JSPlumb instance
 * @returns {Object} - The transition table data
 */
export function generateTransitionTable(jsPlumbInstance) {
    // Get all data needed
    const stateElements = document.querySelectorAll('.state, .accepting-state');
    const startingStateId = getStartingStateId();
    const edgeSymbolMap = getEdgeSymbolMap();
    const epsilonTransitionMap = getEpsilonTransitionMap();
    const epsilon = getEpsilonSymbol(); // This is 'ε' for display purposes

    // Get all connections
    const connections = jsPlumbInstance.getAllConnections();

    // Get all unique symbols (alphabet)
    const alphabet = new Set();

    edgeSymbolMap.forEach((symbols) => {
        if (symbols && symbols.length) {
            symbols.forEach(symbol => alphabet.add(symbol));
        }
    });

    // Sort the alphabet for consistent display
    const sortedAlphabet = Array.from(alphabet).sort();

    // Initialise the transition table
    const table = {
        states: [],
        alphabet: sortedAlphabet,
        hasEpsilon: false,
        transitions: {},
        startingState: startingStateId,
        acceptingStates: []
    };

    // Check if we have epsilon transitions
    epsilonTransitionMap.forEach(isEpsilon => {
        if (isEpsilon) {
            table.hasEpsilon = true;
        }
    });

    // Add states to the table
    stateElements.forEach(state => {
        const stateId = state.id;
        table.states.push(stateId);

        // Check if this is an accepting state
        if (state.classList.contains('accepting-state')) {
            table.acceptingStates.push(stateId);
        }

        // Initialise empty transitions for this state
        table.transitions[stateId] = {};

        // Initialise for all symbols in alphabet
        sortedAlphabet.forEach(symbol => {
            table.transitions[stateId][symbol] = [];
        });

        // Initialise for epsilon using empty string ''
        if (table.hasEpsilon) {
            table.transitions[stateId][''] = []; // Use empty string for backend compatibility
        }
    });

    // Fill in the transitions
    connections.forEach(connection => {
        // Skip the starting state indicator connection
        if (connection.canvas && connection.canvas.classList.contains('starting-connection')) {
            return;
        }

        const sourceId = connection.sourceId;
        const targetId = connection.targetId;

        // Get the symbols for this connection
        const symbols = edgeSymbolMap.get(connection.id) || [];
        const isEpsilon = epsilonTransitionMap.get(connection.id) || false;

        // Add each symbol transition
        symbols.forEach(symbol => {
            if (table.transitions[sourceId] && table.transitions[sourceId][symbol]) {
                if (!table.transitions[sourceId][symbol].includes(targetId)) {
                    table.transitions[sourceId][symbol].push(targetId);
                }
            }
        });

        // Add epsilon transition using empty string '' instead of epsilon symbol
        if (isEpsilon && table.hasEpsilon) {
            if (table.transitions[sourceId] && table.transitions[sourceId]['']) { // Use empty string
                if (!table.transitions[sourceId][''].includes(targetId)) {
                    table.transitions[sourceId][''].push(targetId);
                }
            }
        }
    });

    // Sort state IDs for consistent display
    table.states.sort();
    table.acceptingStates.sort();

    return table;
}

/**
 * Creates an HTML table element from the transition table data
 * @param {Object} tableData - The transition table data
 * @returns {HTMLElement} - The HTML table element
 */
export function createTransitionTableElement(tableData) {
    // Create container for the table
    const container = document.createElement('div');
    container.className = 'transition-table-container';

    // Add a title
    const title = document.createElement('h3');
    title.textContent = 'Transition Table';
    container.appendChild(title);

    // Create scrollable wrapper for the table
    const tableWrapper = document.createElement('div');
    tableWrapper.className = 'transition-table-wrapper';

    // Create the table element
    const table = document.createElement('table');
    table.className = 'transition-table';

    // Create the header section
    const thead = document.createElement('thead');
    const headerRow = document.createElement('tr');

    // Add empty cell for state column
    const stateHeaderCell = document.createElement('th');
    stateHeaderCell.textContent = 'State';
    headerRow.appendChild(stateHeaderCell);

    // Add column for each symbol in the alphabet
    tableData.alphabet.forEach(symbol => {
        const th = document.createElement('th');
        th.textContent = symbol;
        headerRow.appendChild(th);
    });

    // Add epsilon column if needed
    if (tableData.hasEpsilon) {
        const epsilonTh = document.createElement('th');
        epsilonTh.textContent = getEpsilonSymbol(); // Display as 'ε'
        headerRow.appendChild(epsilonTh);
    }

    // Add the header row to thead and thead to table
    thead.appendChild(headerRow);
    table.appendChild(thead);

    // Create the body section
    const tbody = document.createElement('tbody');

    // Add rows for each state
    tableData.states.forEach(stateId => {
        const row = document.createElement('tr');

        // Add the state cell with appropriate styling
        const stateCell = document.createElement('td');

        // Start with the base state ID
        let stateCellContent = stateId;

        // Mark starting state
        if (stateId === tableData.startingState) {
            stateCell.classList.add('starting-state-cell');
            // Add an arrow indicator
            const startingIndicator = document.createElement('span');
            startingIndicator.textContent = '→ ';
            startingIndicator.className = 'starting-indicator';
            stateCell.appendChild(startingIndicator);
        }

        // Add the state ID text
        const stateText = document.createElement('span');
        stateText.textContent = stateCellContent;
        stateCell.appendChild(stateText);

        // Mark accepting state (add the symbol after the text)
        if (tableData.acceptingStates.includes(stateId)) {
            stateCell.classList.add('accepting-state-cell');
            const acceptingIndicator = document.createElement('span');
            acceptingIndicator.textContent = ' ⊛';
            stateCell.appendChild(acceptingIndicator);
        }

        row.appendChild(stateCell);

        // Add transition cells for each symbol
        tableData.alphabet.forEach(symbol => {
            const cell = document.createElement('td');
            if (tableData.transitions[stateId] && tableData.transitions[stateId][symbol]) {
                const targets = tableData.transitions[stateId][symbol];
                if (targets.length > 0) {
                    cell.textContent = targets.join(', ');
                } else {
                    cell.textContent = '∅'; // Empty set symbol for no transition
                }
            } else {
                cell.textContent = '∅';
            }
            row.appendChild(cell);
        });

        // Add epsilon transition cell using empty string '' as key but display as ε
        if (tableData.hasEpsilon) {
            const epsilonCell = document.createElement('td');
            // Use empty string '' as the key to access epsilon transitions
            if (tableData.transitions[stateId] && tableData.transitions[stateId]['']) {
                const targets = tableData.transitions[stateId][''];
                if (targets.length > 0) {
                    epsilonCell.textContent = targets.join(', ');
                } else {
                    epsilonCell.textContent = '∅';
                }
            } else {
                epsilonCell.textContent = '∅';
            }
            row.appendChild(epsilonCell);
        }

        // Add the row to tbody
        tbody.appendChild(row);
    });

    // Add tbody to table
    table.appendChild(tbody);

    // Add the table to the wrapper
    tableWrapper.appendChild(table);

    // Add the wrapper to the container
    container.appendChild(tableWrapper);

    // Add a button container
    const buttonContainer = document.createElement('div');
    buttonContainer.className = 'transition-table-button-container';

    // Create close button
    const closeButton = document.createElement('button');
    closeButton.textContent = 'Close';
    closeButton.className = 'close-table-btn';
    closeButton.addEventListener('click', function() {
        const modalContainer = document.getElementById('transition-table-modal');
        if (modalContainer) {
            modalContainer.style.display = 'none';
        }
    });

    // Add button to container
    buttonContainer.appendChild(closeButton);
    container.appendChild(buttonContainer);

    return container;
}

/**
 * Displays the transition table in a modal
 * @param {Object} jsPlumbInstance - The JSPlumb instance
 */
export function showTransitionTable(jsPlumbInstance) {
    // Generate the transition table data
    const tableData = generateTransitionTable(jsPlumbInstance);

    // Create the table element
    const tableElement = createTransitionTableElement(tableData);

    // Create or get the modal container
    let modalContainer = document.getElementById('transition-table-modal');
    if (!modalContainer) {
        modalContainer = document.createElement('div');
        modalContainer.id = 'transition-table-modal';
        modalContainer.className = 'modal';
        document.body.appendChild(modalContainer);
    }

    // Clear the modal and add the table
    modalContainer.innerHTML = '';
    modalContainer.appendChild(tableElement);

    // Show the modal
    modalContainer.style.display = 'block';
}