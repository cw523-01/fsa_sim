document.addEventListener('DOMContentLoaded', function() {
    // Initialize JSPlumb
    const jsPlumbInstance = jsPlumb.getInstance({
        Endpoint: ["Dot", { radius: 2 }],
        Connector: ["Bezier", { curviness: 150 }],
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

    // Tool selection
    document.getElementById('regular-state-tool').addEventListener('click', function() {
        currentTool = 'state';
        resetToolSelection();
        this.style.backgroundColor = '#ddd';
    });

    document.getElementById('accepting-state-tool').addEventListener('click', function() {
        currentTool = 'accepting-state';
        resetToolSelection();
        this.style.backgroundColor = '#ddd';
    });

    document.getElementById('edge-tool').addEventListener('click', function() {
        currentTool = 'edge';
        resetToolSelection();
        this.style.backgroundColor = '#ddd';
    });

    function resetToolSelection() {
        document.querySelectorAll('.tool').forEach(tool => {
            tool.style.backgroundColor = 'transparent';
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
        }
    });

    // Create a state
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
            stack: ".state, .accepting-state", // Stack dragged element above others
            zIndex: 100, // High z-index during drag
            drag: function(event, ui) {
                jsPlumbInstance.repaintEverything();
            }
        });

        // Make state a connection source and target
        jsPlumbInstance.makeSource(state, {
            filter: ".edge-source",
            anchor: "Continuous",
            connectorStyle: { stroke: "#5c96bc", strokeWidth: 2 },
            connectionType: "basic"
        });

        jsPlumbInstance.makeTarget(state, {
            anchor: "Continuous",
            connectionType: "basic"
        });

        // Add click event for edge creation
        state.addEventListener('click', function(e) {
            if (currentTool === 'edge') {
                if (sourceState === null) {
                    sourceState = this;
                    sourceId = this.id;
                    $(this).addClass('selected-source');
                } else if (sourceState !== this) {
                    openEdgeSymbolModal(sourceId, this.id);
                    $(sourceState).removeClass('selected-source');
                    sourceState = null;
                }
            }
        });

        return state;
    }

    // Edge symbol modal
    function openEdgeSymbolModal(source, target) {
        document.getElementById('edge-symbol-modal').style.display = 'block';

        document.getElementById('confirm-symbol-btn').onclick = function() {
            const symbol = document.getElementById('edge-symbol-input').value;
            if (symbol) {
                createConnection(source, target, symbol);
                closeEdgeSymbolModal();
            }
        };

        document.getElementById('cancel-symbol-btn').onclick = closeEdgeSymbolModal;
    }

    function closeEdgeSymbolModal() {
        document.getElementById('edge-symbol-modal').style.display = 'none';
        document.getElementById('edge-symbol-input').value = '';
    }

    // Create a connection with a label
    function createConnection(source, target, symbol) {
        const connection = jsPlumbInstance.connect({
            source: source,
            target: target,
            type: "basic"
        });

        connection.getOverlay("label").setLabel(symbol);
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

                if (tool === 'regular-state-tool') {
                    createState(x, y, false);
                } else if (tool === 'accepting-state-tool') {
                    createState(x, y, true);
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
});