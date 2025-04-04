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
    const inlineEditor = document.getElementById('state-inline-editor');

    // Tool selection
    document.getElementById('state-tool').addEventListener('click', function() {
        closeInlineStateEditor();
        selectTool('state');
    });

    document.getElementById('accepting-state-tool').addEventListener('click', function() {
        closeInlineStateEditor();
        selectTool('accepting-state');
    });

    document.getElementById('edge-tool').addEventListener('click', function() {
        closeInlineStateEditor();
        selectTool('edge');
    });

    document.getElementById('delete-tool').addEventListener('click', function() {
        closeInlineStateEditor();
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

            // Close the inline editor if it's open and we click on the canvas
            if (inlineEditor.style.display === 'block') {
                closeInlineStateEditor();
            }
        }
    });

    // Edge symbol modal
    function openEdgeSymbolModal(source, target) {
        const symbolInput = document.getElementById('edge-symbol-input');

        document.getElementById('edge-symbol-modal').style.display = 'block';

        // Auto-focus the input when the modal opens
        symbolInput.focus();

        // Add event listener for Enter key
        const handleEnterKey = function(e) {
            if (e.key === 'Enter') {
                const symbol = symbolInput.value;
                if (symbol) {
                    createConnection(source, target, symbol);
                    closeEdgeSymbolModal();
                }
                e.preventDefault();
            }
        };

        symbolInput.addEventListener('keydown', handleEnterKey);

        document.getElementById('confirm-symbol-btn').onclick = function() {
            const symbol = symbolInput.value;
            if (symbol) {
                createConnection(source, target, symbol);
                closeEdgeSymbolModal();
            }
        };

        document.getElementById('cancel-symbol-btn').onclick = closeEdgeSymbolModal;

        // Store the cleanup function
        symbolInput._cleanup = function() {
            symbolInput.removeEventListener('keydown', handleEnterKey);
        };
    }

    function closeEdgeSymbolModal() {
        const symbolInput = document.getElementById('edge-symbol-input');
        document.getElementById('edge-symbol-modal').style.display = 'none';

        // Clean up the event listener
        if (symbolInput._cleanup) {
            symbolInput._cleanup();
            symbolInput._cleanup = null;
        }

        symbolInput.value = '';
    }

    // Create a connection with a label
    function createConnection(source, target, symbol) {
        const connection = jsPlumbInstance.connect({
            source: source,
            target: target,
            type: "basic"
        });

        connection.getOverlay("label").setLabel(symbol);

        // Add click handler for edge deletion
        if (connection.canvas) {
            connection.canvas.addEventListener('click', function(e) {
                if (currentTool === 'delete') {
                    deleteEdge(connection);
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

    // Setup live update event listeners
    function setupLiveUpdates() {
        const labelInput = document.getElementById('inline-state-label-input');
        const acceptingCheckbox = document.getElementById('inline-accepting-state-checkbox');

        labelInput.addEventListener('input', updateStateLabel);
        acceptingCheckbox.addEventListener('change', updateStateType);
    }

    // Remove live update event listeners
    function removeLiveUpdateListeners() {
        const labelInput = document.getElementById('inline-state-label-input');
        const acceptingCheckbox = document.getElementById('inline-accepting-state-checkbox');

        labelInput.removeEventListener('input', updateStateLabel);
        acceptingCheckbox.removeEventListener('change', updateStateType);
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

                // Close inline editor if open while dragging
                if (currentEditingState === this) {
                    closeInlineStateEditor();
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
        jsPlumbInstance.deleteConnection(connection);
    }

    function selectTool(toolName) {
        resetToolSelection();
        currentTool = toolName;
        document.getElementById(toolName + '-tool').style.border = '2px solid red';
    }

    // Add click handlers to existing connections on init
    jsPlumbInstance.bind('connection', function(info) {
        if (info.connection && info.connection.canvas) {
            info.connection.canvas.addEventListener('click', function(e) {
                if (currentTool === 'delete') {
                    deleteEdge(info.connection);
                    e.stopPropagation();
                }
            });
        }

        // Also add click handler to the connection label
        const labelOverlay = info.connection.getOverlay('label');
        if (labelOverlay && labelOverlay.canvas) {
            labelOverlay.canvas.addEventListener('click', function(e) {
                if (currentTool === 'delete') {
                    deleteEdge(info.connection);
                    e.stopPropagation();
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
});