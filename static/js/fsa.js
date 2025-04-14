document.addEventListener('DOMContentLoaded', function() {
    // Initialize JSPlumb
    const jsPlumbInstance = jsPlumb.getInstance({
        Endpoint: ["Dot", { radius: 2 }],
        Connector: "Straight",
        HoverPaintStyle: { stroke: "#1e8151", strokeWidth: 2 },
        ConnectionOverlays: [
            ["Arrow", { location: 1, id: "arrow", width: 10, length: 10 }],
            ["Label", {
                id: "label",
                cssClass: "edge-label",
                location: 0.3,
                labelStyle: {
                    cssClass: "edge-label-style"
                }
            }]
        ],
        Container: "fsa-canvas"
    });

    let stateCounter = 0;
    let currentTool = null;
    let sourceState = null;
    let sourceId = null;
    let tempConnection = null;
    let currentEditingState = null;
    let currentEditingEdge = null;
    const inlineEditor = document.getElementById('state-inline-editor');
    const edgeInlineEditor = document.getElementById('edge-inline-editor');
    let currentEditingSymbols = [];

    const edgeSymbolMap = new Map(); // Map<connection.id, Array of symbols>

    let pendingSourceId = null;
    let pendingTargetId = null;

    // Tool selection
    document.getElementById('state-tool').addEventListener('click', function() {
        closeInlineStateEditor();
        closeInlineEdgeEditor();
        selectTool('state');
    });

    document.getElementById('accepting-state-tool').addEventListener('click', function() {
        closeInlineStateEditor();
        closeInlineEdgeEditor();
        selectTool('accepting-state');
    });

    document.getElementById('edge-tool').addEventListener('click', function() {
        closeInlineStateEditor();
        closeInlineEdgeEditor();
        selectTool('edge');
    });

    document.getElementById('delete-tool').addEventListener('click', function() {
        closeInlineStateEditor();
        closeInlineEdgeEditor();
        selectTool('delete');
    });

    function resetToolSelection() {
        currentTool = "";
        document.querySelectorAll('.tool').forEach(tool => {
            tool.style.border = 'none';
        });
    }

    // Canvas click event
    document.getElementById('fsa-canvas').addEventListener('click', function(e) {
        if (e.target.id === 'fsa-canvas') {
            if (currentTool === 'state') {
                createState(e.offsetX, e.offsetY, false);
            } else if (currentTool === 'accepting-state') {
                createState(e.offsetX, e.offsetY, true);
            }

            // Close the inline editors if they're open and we click on the canvas
            if (inlineEditor.style.display === 'block') {
                closeInlineStateEditor();
            }
            if (edgeInlineEditor.style.display === 'block') {
                closeInlineEdgeEditor();
            }
        }
    });

    // Edge symbol modal
    function openEdgeSymbolModal(source, target) {
        const modal = document.getElementById('edge-symbol-modal');
        pendingSourceId = source;
        pendingTargetId = target;
        document.getElementById('edge-symbol-modal').style.display = 'block';

        const inputsContainer = document.getElementById('symbol-inputs-container');
        modal.style.display = 'block';

        // Clear previous inputs and add one input field
        inputsContainer.innerHTML = '';
        addSymbolInput();

        // Handler to add new input field
        document.getElementById('add-symbol-input').onclick = function () {
            addSymbolInput();
        };

        // Confirm button handler
        document.getElementById('confirm-symbol-btn').onclick = function () {
            const inputs = inputsContainer.querySelectorAll('.symbol-input');

            const symbols = [];
            const seen = new Set();
            inputs.forEach(input => {
                const val = input.value.trim();
                const upper = val.toUpperCase();

                if (val.length === 1 && !seen.has(upper)) {
                    seen.add(upper);
                    symbols.push(val);
                    input.style.borderColor = '';
                } else if (seen.has(upper)) {
                    input.style.borderColor = 'red';
                }
            });

            if (symbols.length > 0) {
                if (pendingSourceId && pendingTargetId) {
                    createConnection(pendingSourceId, pendingTargetId, symbols.join(','));
                }
                closeEdgeSymbolModal();
            }
        };

        // Cancel button handler
        document.getElementById('cancel-symbol-btn').onclick = closeEdgeSymbolModal;
    }

    function addSymbolInput() {
        const input = document.createElement('input');
        input.type = 'text';
        input.className = 'symbol-input';
        input.maxLength = 1;
        document.getElementById('symbol-inputs-container').appendChild(input);
        input.focus();
    }


    function closeEdgeSymbolModal() {
        document.getElementById('edge-symbol-modal').style.display = 'none';
        document.getElementById('symbol-inputs-container').innerHTML = '';
        pendingSourceId = null;
        pendingTargetId = null;
    }

    // Create a connection with a label
    function createConnection(source, target, symbolsString) {
        const connection = jsPlumbInstance.connect({
            source: source,
            target: target,
            type: "basic"
        });

        // Parse and save symbols
        const symbols = symbolsString.split(',').map(s => s.trim()).filter(s => s.length === 1);
        edgeSymbolMap.set(connection.id, symbols);

        // Set label
        edgeSymbolMap.set(connection.id, symbols);
        connection.getOverlay("label").setLabel(symbols.join(','));


        // Add click handler
        if (connection.canvas) {
            connection.canvas.addEventListener('click', function (e) {
                if (currentTool === 'delete') {
                    deleteEdge(connection);
                    e.stopPropagation();
                } else {
                    openInlineEdgeEditor(connection);
                    e.stopPropagation();
                }
            });
        }
    }

    // Inline state editor functions
    function openInlineStateEditor(stateElement) {
        currentEditingState = stateElement;
        const labelInput = document.getElementById('inline-state-label-input');
        const acceptingCheckbox = document.getElementById('inline-accepting-state-checkbox');

        // Close edge editor if open
        closeInlineEdgeEditor();

        // Position the editor near the state
        inlineEditor.style.left = (stateElement.offsetLeft + 150) + 'px';
        inlineEditor.style.top = (stateElement.offsetTop) + 'px';

        // Set current values
        labelInput.value = stateElement.innerHTML;
        acceptingCheckbox.checked = stateElement.classList.contains('accepting-state');

        // Show editor
        inlineEditor.style.display = 'block';

        // Focus on the input
        labelInput.focus();

        // Add live update event listeners
        setupLiveUpdates();
    }

    function closeInlineStateEditor() {
        inlineEditor.style.display = 'none';
        currentEditingState = null;

        // Remove live update event listeners
        removeLiveUpdateListeners();
    }

    // Inline edge editor functions
    function openInlineEdgeEditor(connection) {
        currentEditingEdge = connection;

        // Get label text and split into symbols array
        currentEditingSymbols = edgeSymbolMap.get(connection.id) || [];

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
        currentEditingSymbols.forEach(symbol => addSymbolEditInput(symbol));

        document.getElementById('add-symbol-edit-btn').onclick = function () {
            addSymbolEditInput('');
        };

        setupEdgeLiveUpdates();
    }

    function closeInlineEdgeEditor() {
        edgeInlineEditor.style.display = 'none';
        currentEditingEdge = null;

        // Remove live update event listener
        removeEdgeLiveUpdateListeners();
    }

    // Setup live update event listeners for state editor
    function setupLiveUpdates() {
        const labelInput = document.getElementById('inline-state-label-input');
        const acceptingCheckbox = document.getElementById('inline-accepting-state-checkbox');

        labelInput.addEventListener('input', updateStateLabel);
        acceptingCheckbox.addEventListener('change', updateStateType);
    }

    // Remove live update event listeners for state editor
    function removeLiveUpdateListeners() {
        const labelInput = document.getElementById('inline-state-label-input');
        const acceptingCheckbox = document.getElementById('inline-accepting-state-checkbox');

        labelInput.removeEventListener('input', updateStateLabel);
        acceptingCheckbox.removeEventListener('change', updateStateType);
    }

    // Setup live update event listeners for edge editor
    function setupEdgeLiveUpdates() {
        const container = document.getElementById('edge-symbols-edit-container');
        container.addEventListener('input', updateEdgeLabel);
    }

    // Remove live update event listeners for edge editor
    function removeEdgeLiveUpdateListeners() {
        const container = document.getElementById('edge-symbols-edit-container');
        if (!container) return;

        const inputs = container.querySelectorAll('.symbol-edit-input');
        inputs.forEach(input => {
            input.removeEventListener('input', updateEdgeLabel);
        });
    }

    // Live update functions
    function updateStateLabel() {
        if (!currentEditingState) return;
        const newLabel = document.getElementById('inline-state-label-input').value;
        if (newLabel) {
            currentEditingState.innerHTML = newLabel;
            jsPlumbInstance.repaintEverything();
        }
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

        jsPlumbInstance.repaintEverything();
    }

    function updateEdgeLabel() {
        if (!currentEditingEdge) return;

        const container = document.getElementById('edge-symbols-edit-container');
        const inputs = container.querySelectorAll('.symbol-edit-input');

        const symbols = [];
        const seen = new Set();
        let hasDuplicates = false;

        inputs.forEach(input => {
            const val = input.value.trim();
            const upper = val.toUpperCase(); // For duplicate checking only

            if (val.length === 1) {
                if (!seen.has(upper)) {
                    seen.add(upper);
                    symbols.push(val); // Keep original casing
                    input.style.borderColor = '';
                } else {
                    hasDuplicates = true;
                    input.style.borderColor = 'red';
                }
            } else {
                input.style.borderColor = '';
            }
        });

        if (!hasDuplicates) {
            edgeSymbolMap.set(currentEditingEdge.id, symbols);
            currentEditingEdge.getOverlay("label").setLabel(symbols.join(','));
            jsPlumbInstance.repaintEverything();
        }
    }

    // Handle drag and drop from tools panel
    $('.tool').draggable({
        helper: 'clone',
        cursor: 'move',
        cursorAt: { left: 25, top: 25 },
        helper: function() {
            // Create a custom helper with high z-index
            const clone = $(this).clone();
            clone.css('z-index', '1000'); // High z-index to stay on top
            return clone;
        },
        stop: function(event, ui) {
            const tool = $(this).attr('id');
            const canvas = document.getElementById('fsa-canvas');
            const canvasRect = canvas.getBoundingClientRect();

            // Check if dropped on canvas
            if (
                ui.offset.left >= canvasRect.left &&
                ui.offset.left <= canvasRect.right &&
                ui.offset.top >= canvasRect.top &&
                ui.offset.top <= canvasRect.bottom
            ) {
                const x = ui.offset.left - canvasRect.left;
                const y = ui.offset.top - canvasRect.top;

                if (tool === 'state-tool') {
                    createState(x, y, false);
                    selectTool('state');
                } else if (tool === 'accepting-state-tool') {
                    createState(x, y, true);
                    selectTool('accepting-state');
                }
            }
        }
    });

    // Non-functional buttons
    document.getElementById('play-btn').addEventListener('click', function() {
        alert('Play functionality is not implemented yet.');
    });

    document.getElementById('stop-btn').addEventListener('click', function() {
        alert('Stop functionality is not implemented yet.');
    });

    document.getElementById('fast-forward-btn').addEventListener('click', function() {
        alert('Fast forward functionality is not implemented yet.');
    });

    document.getElementById('show-table-btn').addEventListener('click', function() {
        alert('Transition table functionality is not implemented yet.');
    });

    // Window resize event
    window.addEventListener('resize', function() {
        jsPlumbInstance.repaintEverything();
    });

    // Create a state element
    function createState(x, y, isAccepting) {
        const stateId = 'S' + stateCounter++;
        const state = document.createElement('div');
        state.id = stateId;
        state.className = isAccepting ? 'accepting-state' : 'state';
        state.innerHTML = stateId;
        state.style.left = (x - 30) + 'px';
        state.style.top = (y - 30) + 'px';

        document.getElementById('fsa-canvas').appendChild(state);

        // Make state draggable
        $(state).draggable({
            containment: "parent",
            stack: ".state, .accepting-state",
            zIndex: 100,
            drag: function(event, ui) {
                jsPlumbInstance.repaintEverything();

                // Close inline editors if open while dragging
                if (currentEditingState === this) {
                    closeInlineStateEditor();
                }
                if (currentEditingEdge) {
                    closeInlineEdgeEditor();
                }
            }
        });

        // Make state a connection source and target
        jsPlumbInstance.makeSource(state, {
            filter: ".edge-source",
            anchor: "Continuous",
            connectorStyle: { stroke: "black", strokeWidth: 2 },
            connectionType: "basic"
        });

        jsPlumbInstance.makeTarget(state, {
            anchor: "Continuous",
            connectionType: "basic"
        });

        // Add click event for both edge creation and state editing
        state.addEventListener('click', function(e) {
            if (currentTool === 'delete'){
                if (e.target.classList.contains('state') || e.target.classList.contains('accepting-state')) {
                    deleteState(e.target);
                }
            }
            else if (currentTool === 'edge') {
                if (sourceState === null) {
                    sourceState = this;
                    sourceId = this.id;
                    $(this).addClass('selected-source');
                } else if (sourceState !== this) {
                    openEdgeSymbolModal(sourceId, this.id);
                    $(sourceState).removeClass('selected-source');
                    sourceState = null;
                }
            } else {
                resetToolSelection()
                // If not using edge tool, open edit modal when clicking a state
                openInlineStateEditor(this);
            }

            // Stop event propagation to prevent canvas click handler from firing
            e.stopPropagation();
        });

        return state;
    }

    function deleteState(stateElement) {
        jsPlumbInstance.removeAllEndpoints(stateElement.id);
        stateElement.remove();
    }

    function deleteEdge(connection) {
        edgeSymbolMap.delete(connection.id);
        jsPlumbInstance.deleteConnection(connection);
    }

    function selectTool(toolName) {
        resetToolSelection();
        currentTool = toolName;
        document.getElementById(toolName + '-tool').style.border = '2px solid red';
    }

    // Add click handlers to existing connections on init
    jsPlumbInstance.bind('connection', function(info) {
        // Make sure we're getting the actual connection element
        if (info.connection && info.connection.canvas) {
            // Add z-index to make sure connection is clickable
            info.connection.canvas.style.zIndex = '20';

            // Add a more robust click handler
            $(info.connection.canvas).on('click', function(e) {
                e.stopPropagation();
                e.preventDefault();

                if (currentTool === 'delete') {
                    deleteEdge(info.connection);
                } else {
                    openInlineEdgeEditor(info.connection);
                }
            });
        }

        // Add a separate event handler for the label overlay
        const labelOverlay = info.connection.getOverlay('label');
        if (labelOverlay && labelOverlay.canvas) {
            // Make sure the label is clickable
            labelOverlay.canvas.style.zIndex = '25';

            $(labelOverlay.canvas).on('click', function(e) {
                e.stopPropagation();
                e.preventDefault();

                if (currentTool === 'delete') {
                    deleteEdge(info.connection);
                } else {
                    openInlineEdgeEditor(info.connection);
                }
            });
        }
    });

    // Add click handlers for edge label deletion
    document.addEventListener('click', function(e) {
        if (currentTool === 'delete') {
            // Check if we clicked on an edge label
            const connections = jsPlumbInstance.getAllConnections();
            for (let i = 0; i < connections.length; i++) {
                const conn = connections[i];
                const labelOverlay = conn.getOverlay("label");

                if (labelOverlay && labelOverlay.canvas &&
                   (labelOverlay.canvas === e.target || labelOverlay.canvas.contains(e.target))) {
                    deleteEdge(conn);
                    e.stopPropagation();
                    return;
                }
            }
        }
    });

    document.getElementById('close-inline-editor').addEventListener('click', function() {
        closeInlineStateEditor();
    });

    document.getElementById('close-edge-editor').addEventListener('click', function() {
        closeInlineEdgeEditor();
    });

    function addSymbolEditInput(value = '') {
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

        removeBtn.onclick = () => {
            wrapper.remove();
            updateEdgeLabel();
        };

        wrapper.appendChild(input);
        wrapper.appendChild(removeBtn);
        document.getElementById('edge-symbols-edit-container').appendChild(wrapper);
        input.focus();
    }
});