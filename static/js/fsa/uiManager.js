import { createStartingStateIndicator, getStartingStateId } from './stateManager.js';
import {
    updateEdgeSymbols,
    getEdgeSymbols,
    hasEpsilonTransition,
    updateEdgeCurveStyle,
    getEdgeCurveStyle,
    createConnection,
    deleteEdge,
    getEpsilonTransitionMap,
    getEdgeSymbolMap
} from './edgeManager.js';
import { updateFSAPropertiesDisplay } from './fsaPropertyChecker.js';
import {updateAlphabetDisplay} from "./alphabetManager.js";

import { notificationManager } from './notificationManager.js';

// UI state
let currentTool = null;
let currentEditingState = null;
let currentEditingEdge = null;
let pendingSourceId = null;
let pendingTargetId = null;
let sourceState = null;
let editorJsPlumbInstance = null;

/**
 * Select a tool
 * @param {string} toolName - The name of the tool to select
 */
export function selectTool(toolName) {
    resetToolSelection();
    currentTool = toolName;
    document.getElementById(toolName + '-tool').style.border = '2px solid red';
}

/**
 * Reset tool selection
 */
export function resetToolSelection() {
    currentTool = null;
    document.querySelectorAll('.tool').forEach(tool => {
        tool.style.border = 'none';
    });
}

/**
 * Get the current selected tool
 * @returns {string} - The current tool
 */
export function getCurrentTool() {
    return currentTool;
}

/**
 * Set source state for edge creation
 * @param {HTMLElement} state - The state to set as source
 */
export function setSourceState(state) {
    if (sourceState) {
        $(sourceState).removeClass('selected-source');
    }
    sourceState = state;
    if (state) {
        $(state).addClass('selected-source');
    }
}

/**
 * Get the current source state
 * @returns {HTMLElement} - The current source state
 */
export function getSourceState() {
    return sourceState;
}

/**
 * Get the source state ID
 * @returns {string} - The source state ID
 */
export function getSourceId() {
    return sourceState ? sourceState.id : null;
}

/**
 * Reset source state
 */
export function resetSourceState() {
    if (sourceState) {
        $(sourceState).removeClass('selected-source');
    }
    sourceState = null;
}

/**
 * Open the inline state editor
 * @param {HTMLElement} stateElement - The state element to edit
 * @param {Object} jsPlumbInstance - The JSPlumb instance
 */
export function openInlineStateEditor(stateElement, jsPlumbInstance) {
    const inlineEditor = document.getElementById('state-inline-editor');
    currentEditingState = stateElement;
    const labelInput = document.getElementById('inline-state-label-input');
    const acceptingCheckbox = document.getElementById('inline-accepting-state-checkbox');
    const startingCheckbox = document.getElementById('inline-starting-state-checkbox');

    // Close edge editor if open
    closeInlineEdgeEditor();

    // Position the editor near the state
    inlineEditor.style.left = (stateElement.offsetLeft + 150) + 'px';
    inlineEditor.style.top = (stateElement.offsetTop) + 'px';

    // Set current values
    labelInput.value = stateElement.innerHTML;
    acceptingCheckbox.checked = stateElement.classList.contains('accepting-state');
    startingCheckbox.checked = getStartingStateId() === stateElement.id;

    // Show editor
    inlineEditor.style.display = 'block';

    // Focus on the input
    labelInput.focus();

    // Add live update event listeners
    setupLiveStateUpdates(jsPlumbInstance);
}

/**
 * Close the inline state editor
 */
export function closeInlineStateEditor() {
    const inlineEditor = document.getElementById('state-inline-editor');
    inlineEditor.style.display = 'none';
    currentEditingState = null;

    // Remove live update event listeners
    removeLiveStateUpdateListeners();
}

/**
 * Open the inline edge editor
 * @param {Object} connection - The connection to edit
 * @param {Object} jsPlumbInstance - The JSPlumb instance
 */
export function openInlineEdgeEditor(connection, jsPlumbInstance) {
    const edgeInlineEditor = document.getElementById('edge-inline-editor');
    currentEditingEdge = connection;
    // Store the jsPlumbInstance for use in updateCurrentEdgeLabel
    editorJsPlumbInstance = jsPlumbInstance;

    // Get symbols for this edge
    const currentEditingSymbols = getEdgeSymbols(connection);
    const hasEpsilon = hasEpsilonTransition(connection);
    const isCurved = getEdgeCurveStyle(connection);

    // Close state editor if open
    closeInlineStateEditor();

    // Position the editor near the midpoint of the edge
    const sourceElement = document.getElementById(connection.sourceId);
    const targetElement = document.getElementById(connection.targetId);
    const sourcePos = {
        x: sourceElement.offsetLeft + sourceElement.offsetWidth / 2,
        y: sourceElement.offsetTop + sourceElement.offsetHeight / 2
    };
    const targetPos = {
        x: targetElement.offsetLeft + targetElement.offsetWidth / 2,
        y: targetElement.offsetTop + targetElement.offsetHeight / 2
    };

    const midpointX = (sourcePos.x + targetPos.x) / 2;
    const midpointY = (sourcePos.y + targetPos.y) / 2;

    edgeInlineEditor.style.left = (midpointX + 20) + 'px';
    edgeInlineEditor.style.top = (midpointY - 20) + 'px';
    edgeInlineEditor.style.display = 'block';

    // Populate inputs
    const container = document.getElementById('edge-symbols-edit-container');
    container.innerHTML = '';
    currentEditingSymbols.forEach(symbol => addSymbolEditInput(symbol, container));

    // Set epsilon checkbox
    const epsilonCheckbox = document.getElementById('edge-epsilon-checkbox');
    epsilonCheckbox.checked = hasEpsilon;

    // Set curve style checkbox
    const curveStyleCheckbox = document.getElementById('edge-curve-checkbox');
    curveStyleCheckbox.checked = isCurved;

    // If this is a self-loop, disable the curve checkbox since self-loops are always curved
    if (connection.sourceId === connection.targetId) {
        curveStyleCheckbox.disabled = true;
        curveStyleCheckbox.title = "Self-loops are always curved";
    } else {
        curveStyleCheckbox.disabled = false;
        curveStyleCheckbox.title = "";
    }

    document.getElementById('add-symbol-edit-btn').onclick = function () {
        addSymbolEditInput('', container);
    };

    setupEdgeLiveUpdates();
}

/**
 * Close the inline edge editor
 */
export function closeInlineEdgeEditor() {
    const edgeInlineEditor = document.getElementById('edge-inline-editor');
    edgeInlineEditor.style.display = 'none';
    currentEditingEdge = null;
    editorJsPlumbInstance = null;

    // Remove live update event listener
    removeEdgeLiveUpdateListeners();
}

/**
 * Add a symbol input to the edge editor
 * @param {string} value - The initial value
 * @param {HTMLElement} container - The container to add the input to
 */
export function addSymbolEditInput(value = '', container) {
    const wrapper = document.createElement('div');
    wrapper.className = 'symbol-edit-wrapper';
    wrapper.style.display = 'flex';
    wrapper.style.alignItems = 'center';
    wrapper.style.marginBottom = '4px';

    const input = document.createElement('input');
    input.type = 'text';
    input.className = 'symbol-edit-input form-control';
    input.maxLength = 1;
    input.value = value;
    input.style.marginRight = '8px';

    const removeBtn = document.createElement('button');
    removeBtn.textContent = '❌';
    removeBtn.className = 'remove-symbol-btn';
    removeBtn.type = 'button';
    removeBtn.style.cursor = 'pointer';

    // MODIFIED: Check if this would be the only input left and if epsilon is checked
    removeBtn.onclick = () => {
        const inputsCount = container.querySelectorAll('.symbol-edit-wrapper').length;
        const epsilonCheckbox = document.getElementById('edge-epsilon-checkbox');
        const hasEpsilon = epsilonCheckbox && epsilonCheckbox.checked;

        // Allow removal if there are multiple inputs OR if epsilon is checked
        if (inputsCount > 1 || hasEpsilon) {
            wrapper.remove();
            updateCurrentEdgeLabel();
        }
    };

    wrapper.appendChild(input);
    wrapper.appendChild(removeBtn);
    container.appendChild(wrapper);
    input.focus();
}

/**
 * Open the edge symbol modal
 * @param {string} source - Source state ID
 * @param {string} target - Target state ID
 * @param {Function} onConfirm - Callback when symbols are confirmed
 */
export function openEdgeSymbolModal(source, target, onConfirm) {
    const modal = document.getElementById('edge-symbol-modal');
    pendingSourceId = source;
    pendingTargetId = target;
    modal.style.display = 'block';

    const inputsContainer = document.getElementById('symbol-inputs-container');
    inputsContainer.innerHTML = '';
    addSymbolInput(inputsContainer);

    // Reset epsilon checkbox
    const epsilonCheckbox = document.getElementById('epsilon-transition-checkbox');
    epsilonCheckbox.checked = false;

    // Set the curve checkbox to current default or unchecked
    const curveCheckbox = document.getElementById('curve-transition-checkbox');

    // Check if this is a self-loop, which is always curved
    const isSelfLoop = source === target;
    if (isSelfLoop) {
        curveCheckbox.checked = true;
        curveCheckbox.disabled = true;
        curveCheckbox.title = "Self-loops are always curved";
    } else {
        // For normal edges, use the default from edgeManager (default unchecked)
        curveCheckbox.checked = false; // Default to straight
        curveCheckbox.disabled = false;
        curveCheckbox.title = "";
    }

    document.getElementById('add-symbol-input').onclick = function () {
        addSymbolInput(inputsContainer);
    };

    document.getElementById('confirm-symbol-btn').onclick = function () {
        const wrappers = inputsContainer.querySelectorAll('.symbol-input-wrapper');
        const inputs = inputsContainer.querySelectorAll('.symbol-input');
        const hasEpsilon = epsilonCheckbox.checked;
        const isCurved = curveCheckbox.checked;

        const symbols = [];
        const seen = new Set();
        let hasDuplicates = false;

        inputs.forEach(input => {
            const val = input.value.trim();
            if (val.length === 1 && !seen.has(val)) {
                seen.add(val);
                symbols.push(val);
                input.style.borderColor = '';
            } else if (seen.has(val)) {
                hasDuplicates = true;
                input.style.borderColor = 'red';
            }
        });

        // Allow creation if we have symbols or epsilon is checked
        if ((symbols.length > 0 || hasEpsilon) && !hasDuplicates) {
            if (pendingSourceId && pendingTargetId) {
                // Pass the curve style parameter to the callback
                onConfirm(pendingSourceId, pendingTargetId, symbols.join(','), hasEpsilon, isCurved);
            }
            closeEdgeSymbolModal();
        }
    };

    document.getElementById('cancel-symbol-btn').onclick = closeEdgeSymbolModal;
}

/**
 * Add a symbol input to the edge symbol modal
 * @param {HTMLElement} container - The container to add the input to
 */
export function addSymbolInput(container) {
    const wrapper = document.createElement('div');
    wrapper.className = 'symbol-input-wrapper';

    const input = document.createElement('input');
    input.type = 'text';
    input.className = 'symbol-input';
    input.maxLength = 1;

    const removeBtn = document.createElement('button');
    removeBtn.textContent = '❌';
    removeBtn.className = 'remove-symbol-btn';
    removeBtn.type = 'button';

    // MODIFIED: Check if this would be the only input left and if epsilon is checked
    removeBtn.onclick = () => {
        const inputsCount = container.querySelectorAll('.symbol-input-wrapper').length;
        const epsilonCheckbox = document.getElementById('epsilon-transition-checkbox');
        const hasEpsilon = epsilonCheckbox && epsilonCheckbox.checked;

        // Allow removal if there are multiple inputs OR if epsilon is checked
        if (inputsCount > 1 || hasEpsilon) {
            wrapper.remove();
        }
    };

    wrapper.appendChild(input);
    wrapper.appendChild(removeBtn);
    container.appendChild(wrapper);
    input.focus();
}

/**
 * Close the edge symbol modal
 */
export function closeEdgeSymbolModal() {
    document.getElementById('edge-symbol-modal').style.display = 'none';
    document.getElementById('symbol-inputs-container').innerHTML = '';
    pendingSourceId = null;
    pendingTargetId = null;
}

// Setup live update event listeners for state editor
function setupLiveStateUpdates(jsPlumbInstance) {
    const labelInput = document.getElementById('inline-state-label-input');
    const acceptingCheckbox = document.getElementById('inline-accepting-state-checkbox');
    const startingCheckbox = document.getElementById('inline-starting-state-checkbox');

    labelInput.addEventListener('input', () => updateStateLabel(jsPlumbInstance));
    acceptingCheckbox.addEventListener('change', updateStateType);
    startingCheckbox.addEventListener('change', () => updateStartingState(jsPlumbInstance));
}

// Remove live update event listeners for state editor
function removeLiveStateUpdateListeners() {
    const labelInput = document.getElementById('inline-state-label-input');
    const acceptingCheckbox = document.getElementById('inline-accepting-state-checkbox');
    const startingCheckbox = document.getElementById('inline-starting-state-checkbox');

    labelInput.removeEventListener('input', updateStateLabel);
    acceptingCheckbox.removeEventListener('change', updateStateType);
    startingCheckbox.removeEventListener('change', updateStartingState);
}

// Setup live update event listeners for edge editor
function setupEdgeLiveUpdates() {
    const container = document.getElementById('edge-symbols-edit-container');
    container.addEventListener('input', updateCurrentEdgeLabel);

    // Add epsilon checkbox change listener
    const epsilonCheckbox = document.getElementById('edge-epsilon-checkbox');
    epsilonCheckbox.addEventListener('change', updateCurrentEdgeLabel);

    // Add curve style checkbox change listener
    const curveStyleCheckbox = document.getElementById('edge-curve-checkbox');
    curveStyleCheckbox.addEventListener('change', updateEdgeCurveStyleChange);
}


function updateEdgeCurveStyleChange() {
    if (!currentEditingEdge || !editorJsPlumbInstance) return;

    const curveStyleCheckbox = document.getElementById('edge-curve-checkbox');
    const isCurved = curveStyleCheckbox.checked;

    // Update the curve style for the edge - will return a new connection
    const newConnection = updateEdgeCurveStyle(editorJsPlumbInstance, currentEditingEdge, isCurved);

    // Update the current editing edge reference to the new connection
    if (newConnection) {
        currentEditingEdge = newConnection;
    }

    // Deselect both edge style buttons since we now have a mix of styles
    deselectEdgeStyleButtons();
}

// Remove live update event listeners for edge editor
function removeEdgeLiveUpdateListeners() {
    const container = document.getElementById('edge-symbols-edit-container');
    if (!container) return;

    container.removeEventListener('input', updateCurrentEdgeLabel);

    // Remove epsilon checkbox change listener
    const epsilonCheckbox = document.getElementById('edge-epsilon-checkbox');
    if (epsilonCheckbox) {
        epsilonCheckbox.removeEventListener('change', updateCurrentEdgeLabel);
    }

    // Remove curve style checkbox change listener
    const curveStyleCheckbox = document.getElementById('edge-curve-checkbox');
    if (curveStyleCheckbox) {
        curveStyleCheckbox.removeEventListener('change', updateEdgeCurveStyleChange);
    }
}

// Live update functions
function updateStateLabel(jsPlumbInstance) {
    if (!currentEditingState || !jsPlumbInstance) return;

    const newLabel = document.getElementById('inline-state-label-input').value.trim();
    const oldId = currentEditingState.id;

    // Prevent empty or unchanged label
    if (!newLabel || newLabel === oldId) return;

    // Prevent duplicate ID
    if (document.getElementById(newLabel)) {
        // Use notification system instead of blocking alert
        notificationManager.showError(
            'Duplicate State Name',
            `A state with the name "${newLabel}" already exists. Please choose a different name.`
        );

        // Reset the input field to the old value
        document.getElementById('inline-state-label-input').value = oldId;
        return;
    }

    // Store all connections that need to be recreated
    const connectionsToRecreate = [];

    // Get all connections involving this state
    const allConnections = jsPlumbInstance.getAllConnections();
    allConnections.forEach(conn => {
        if (conn.sourceId === oldId || conn.targetId === oldId) {
            // Skip the starting state connection - handle it separately
            if (conn.canvas && conn.canvas.classList.contains('starting-connection')) {
                return;
            }

            // Store connection data
            connectionsToRecreate.push({
                sourceId: conn.sourceId === oldId ? newLabel : conn.sourceId,
                targetId: conn.targetId === oldId ? newLabel : conn.targetId,
                symbols: getEdgeSymbols(conn),
                hasEpsilon: hasEpsilonTransition(conn),
                isCurved: getEdgeCurveStyle(conn)
            });
        }
    });

    // Update the DOM element ID and label
    currentEditingState.id = newLabel;
    currentEditingState.innerHTML = newLabel;

    // Remove all endpoints and connections for the old element ID
    jsPlumbInstance.removeAllEndpoints(oldId);

    // Re-initialize the state as a JSPlumb source and target with the new ID
    jsPlumbInstance.makeSource(currentEditingState, {
        filter: ".edge-source",
        anchor: "Continuous",
        connectorStyle: { stroke: "black", strokeWidth: 2 },
        connectionType: "basic"
    });

    jsPlumbInstance.makeTarget(currentEditingState, {
        anchor: "Continuous",
        connectionType: "basic"
    });

    // Recreate all the stored connections (without triggering property updates)
    connectionsToRecreate.forEach(connData => {
        // Create connection but temporarily skip property updates during recreation
        const connection = jsPlumbInstance.connect({
            source: connData.sourceId,
            target: connData.targetId,
            type: "basic",
            connector: connData.isCurved ?
                (connData.sourceId === connData.targetId ? ["Bezier", { curviness: 60 }] : ["StateMachine", { curviness: 100 }]) :
                "Straight",
            anchors: connData.sourceId === connData.targetId ? ["Top", "Left"] : ["Continuous", "Continuous"],
            paintStyle: { stroke: "black", strokeWidth: 2 },
            hoverPaintStyle: { stroke: "#1e8151", strokeWidth: 3 },
            overlays: [
                ["Arrow", { location: 1, id: "arrow", width: 10, length: 10 }],
                ["Label", {
                    id: "label",
                    cssClass: "edge-label",
                    location: 0.3,
                    labelStyle: {
                        cssClass: "edge-label-style"
                    }
                }]
            ]
        });

        // Manually update the edge data without triggering property updates
        if (connection) {
            // Update edge symbols and epsilon state
            updateEdgeSymbols(connection, connData.symbols, connData.hasEpsilon, null); // Pass null to skip property update

            // Add epsilon class if needed
            if (connData.hasEpsilon && connection.canvas) {
                connection.canvas.classList.add('has-epsilon');
            }

            // Add click handler
            if (connection.canvas) {
                connection.canvas.addEventListener('click', function (e) {
                    const currentTool = getCurrentTool();
                    if (currentTool === 'delete') {
                        deleteEdge(jsPlumbInstance, connection);
                    } else {
                        openInlineEdgeEditor(connection, jsPlumbInstance);
                    }
                    e.stopPropagation();
                });
            }
        }
    });

    // Handle starting state connection if this state is the starting state
    const wasStartingState = getStartingStateId() === oldId;
    if (wasStartingState) {
        // The createStartingStateIndicator function will handle cleanup and recreation
        createStartingStateIndicator(jsPlumbInstance, newLabel);
    }

    // Repaint everything
    jsPlumbInstance.repaintEverything();

    // Update alphabet display after all connections are recreated
    updateAlphabetDisplay(getEdgeSymbolMap(), getEpsilonTransitionMap());

    // Update FSA properties display after everything is consistent
    updateFSAPropertiesDisplay(jsPlumbInstance);
}

function updateStateType() {
    if (!currentEditingState) return;
    const isAccepting = document.getElementById('inline-accepting-state-checkbox').checked;

    if (isAccepting && !currentEditingState.classList.contains('accepting-state')) {
        currentEditingState.classList.remove('state');
        currentEditingState.classList.add('accepting-state');
    } else if (!isAccepting && currentEditingState.classList.contains('accepting-state')) {
        currentEditingState.classList.remove('accepting-state');
        currentEditingState.classList.add('state');
    }
}

function updateStartingState(jsPlumbInstance) {
    if (!currentEditingState) return;
    const isStarting = document.getElementById('inline-starting-state-checkbox').checked;

    if (isStarting) {
        // Set this state as the new starting state
        createStartingStateIndicator(jsPlumbInstance, currentEditingState.id);
    } else if (getStartingStateId() === currentEditingState.id) {
        // Remove starting state if this was the starting state
        createStartingStateIndicator(jsPlumbInstance, null);
    }

    jsPlumbInstance.repaintEverything();

    // Update FSA properties display
    updateFSAPropertiesDisplay(jsPlumbInstance);
}

function updateCurrentEdgeLabel() {
    if (!currentEditingEdge || !editorJsPlumbInstance) return;

    const container = document.getElementById('edge-symbols-edit-container');
    const inputs = container.querySelectorAll('.symbol-edit-input');
    const hasEpsilon = document.getElementById('edge-epsilon-checkbox').checked;

    const symbols = [];
    const seen = new Set();
    let hasDuplicates = false;

    inputs.forEach(input => {
        const val = input.value.trim();

        if (val.length === 1) {
            if (!seen.has(val)) {
                seen.add(val);
                symbols.push(val);
                input.style.borderColor = '';
            } else {
                hasDuplicates = true;
                input.style.borderColor = 'red';
            }
        } else {
            input.style.borderColor = '';
        }
    });

    if (!hasDuplicates && (symbols.length > 0 || hasEpsilon)) {
        updateEdgeSymbols(currentEditingEdge, symbols, hasEpsilon, editorJsPlumbInstance);
        editorJsPlumbInstance.repaintEverything();
    }
}

/**
 * Get the current editing state
 * @returns {HTMLElement} - The current editing state
 */
export function getCurrentEditingState() {
    return currentEditingState;
}

/**
 * Get the current editing edge
 * @returns {Object} - The current editing edge
 */
export function getCurrentEditingEdge() {
    return currentEditingEdge;
}

/**
 * Deselects both edge style buttons
 */
export function deselectEdgeStyleButtons() {
    document.getElementById('straight-edges-btn').classList.remove('active');
    document.getElementById('curved-edges-btn').classList.remove('active');
}
