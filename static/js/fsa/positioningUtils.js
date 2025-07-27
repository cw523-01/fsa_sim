/**
 * Calculate optimal positions for FSA states using hierarchical layout with force-directed refinement
 * @param {Object} fsa - FSA object with states, transitions, etc.
 * @param {Object} existingPositions - Optional existing state positions to preserve
 * @param {Object} options - Configuration options
 * @returns {Object} - Map of state IDs to {x, y} positions
 */
export function calculateStatePositions(fsa, existingPositions = {}, options = {}) {
    const config = {
        canvasWidth: getCanvasWidth(),
        canvasHeight: getCanvasHeight(),
        minDistance: 110,
        levelSpacing: 150,
        nodeSpacing: 130,
        maxNodesPerLevel: Math.floor(getCanvasWidth() / 90),
        preserveExisting: false,
        useHierarchical: true,
        useClusters: true,
        ...options
    };

    if (!fsa || !fsa.states || fsa.states.length === 0) {
        return {};
    }

    const states = fsa.states;
    let positions = {};

    if (config.preserveExisting && Object.keys(existingPositions).length > 0) {
        // Preserve existing positions where possible
        states.forEach(stateId => {
            if (existingPositions[stateId]) {
                positions[stateId] = { ...existingPositions[stateId] };
            }
        });

        // Position new states using non-overlapping placement
        const newStates = states.filter(id => !positions[id]);
        if (newStates.length > 0) {
            const newPositions = findNonOverlappingPositions(positions, newStates);
            Object.assign(positions, newPositions);
        }
    } else {
        // Use hierarchical layout based on FSA structure
        if (config.useHierarchical) {
            positions = calculateHierarchicalLayout(fsa, config);
        } else {
            positions = calculateGridLayout(states, config);
        }

        // Apply clustering for strongly connected components
        if (config.useClusters) {
            positions = applyClustering(fsa, positions, config);
        }

        // Refine with force-directed positioning
        positions = refineWithForceDirected(fsa, positions, config);
    }

    // Final cleanup
    resolveOverlaps(positions, config.minDistance);
    constrainToCanvas(positions, config);

    return positions;
}

/**
 * NEW: Hierarchical layer-based positioning for transformations and conversions
 * Places starting state top-left, then layers states horizontally based on reachability
 * @param {Object} fsa - FSA object with states, transitions, etc.
 * @param {Object} options - Configuration options
 * @returns {Object} - Map of state IDs to {x, y} positions
 */
export function calculateLayeredHierarchicalPositions(fsa, options = {}) {
    const config = {
        canvasWidth: getCanvasWidth(),
        canvasHeight: getCanvasHeight(),
        startX: 80,           // Top-left starting position
        startY: 80,
        layerSpacingX: 200,   // Horizontal spacing between layers
        nodeSpacingY: 100,    // Vertical spacing between nodes in same layer
        maxNodesPerLayer: Math.floor((getCanvasHeight() - 160) / 100), // Max nodes per layer
        ...options
    };

    if (!fsa || !fsa.states || fsa.states.length === 0) {
        return {};
    }

    console.log(`Starting layered positioning for FSA with ${fsa.states.length} states`);

    // Step 1: Build adjacency list for forward connections
    const adjacencyList = buildAdjacencyList(fsa);

    // Step 2: Create layers using BFS from starting state
    const layers = createLayersFromStartingState(fsa, adjacencyList);

    // Step 3: Handle layers that are too tall by splitting them
    const splitLayers = splitOversizedLayers(layers, config.maxNodesPerLayer);

    // Step 4: Position states layer by layer
    const positions = positionStatesInLayers(splitLayers, config);

    // Step 5: Handle any isolated states (unreachable from start)
    const positionedStates = new Set(Object.keys(positions));
    const isolatedStates = fsa.states.filter(id => !positionedStates.has(id));

    if (isolatedStates.length > 0) {
        const isolatedPositions = positionIsolatedStates(isolatedStates, positions, config);
        Object.assign(positions, isolatedPositions);
    }

    console.log(`Layered positioning complete: ${Object.keys(positions).length} states positioned`);

    return positions;
}

/**
 * Create layers using BFS from starting state
 * @param {Object} fsa - FSA object
 * @param {Map} adjacencyList - Adjacency list of connections
 * @returns {Array} - Array of layers, each containing state IDs
 */
function createLayersFromStartingState(fsa, adjacencyList) {
    const layers = [];
    const visited = new Set();
    const queue = [];

    // Start from the starting state if it exists
    if (fsa.startingState && fsa.states.includes(fsa.startingState)) {
        queue.push({ state: fsa.startingState, layer: 0 });
        visited.add(fsa.startingState);

        console.log(`Starting layered positioning from state: ${fsa.startingState}`);
    } else {
        // Fallback: start from first state if no starting state defined
        if (fsa.states.length > 0) {
            queue.push({ state: fsa.states[0], layer: 0 });
            visited.add(fsa.states[0]);

            console.log(`No starting state found, using first state: ${fsa.states[0]}`);
        }
    }

    // BFS to create layers
    while (queue.length > 0) {
        const { state, layer } = queue.shift();

        // Ensure layer array exists
        while (layers.length <= layer) {
            layers.push([]);
        }

        layers[layer].push(state);

        // Add connected states to next layer
        const neighbors = adjacencyList.get(state) || [];
        neighbors.forEach(neighbor => {
            if (!visited.has(neighbor)) {
                visited.add(neighbor);
                queue.push({ state: neighbor, layer: layer + 1 });
            }
        });
    }

    console.log(`Created ${layers.length} layers:`, layers.map((layer, i) => `Layer ${i}: ${layer.length} states`));

    return layers;
}

/**
 * Split layers that have too many nodes vertically
 * @param {Array} layers - Original layers
 * @param {number} maxNodesPerLayer - Maximum nodes per layer
 * @returns {Array} - Split layers
 */
function splitOversizedLayers(layers, maxNodesPerLayer) {
    const splitLayers = [];

    layers.forEach((layer, layerIndex) => {
        if (layer.length <= maxNodesPerLayer) {
            splitLayers.push([...layer]);
        } else {
            // Split large layers into multiple sub-layers
            console.log(`Splitting layer ${layerIndex} with ${layer.length} states into sublayers`);

            for (let i = 0; i < layer.length; i += maxNodesPerLayer) {
                const subLayer = layer.slice(i, i + maxNodesPerLayer);
                splitLayers.push(subLayer);
            }
        }
    });

    return splitLayers;
}

/**
 * Position states within their assigned layers with even vertical distribution
 * @param {Array} layers - Array of layers with state IDs
 * @param {Object} config - Configuration object
 * @returns {Object} - Positions map
 */
function positionStatesInLayers(layers, config) {
    const positions = {};

    layers.forEach((layer, layerIndex) => {
        const x = config.startX + (layerIndex * config.layerSpacingX);

        if (layer.length === 1) {
            // Single state - centre it vertically
            const y = config.canvasHeight / 2;
            positions[layer[0]] = { x, y };
        } else {
            // Multiple states - distribute evenly across canvas height
            const topMargin = 80; // Keep states away from top edge
            const bottomMargin = 80; // Keep states away from bottom edge
            const availableHeight = config.canvasHeight - topMargin - bottomMargin;

            layer.forEach((stateId, stateIndex) => {
                // Calculate Y position: distribute evenly across available height
                // Formula: y = topMargin + (stateIndex / (totalStates - 1)) * availableHeight
                const y = topMargin + (stateIndex / (layer.length - 1)) * availableHeight;

                positions[stateId] = { x, y };

                console.log(`Positioned state ${stateId} at layer ${layerIndex}, position (${x}, ${y}) - state ${stateIndex + 1} of ${layer.length}`);
            });
        }
    });

    return positions;
}

/**
 * Position isolated states that aren't reachable from the starting state
 * @param {Array} isolatedStates - Array of isolated state IDs
 * @param {Object} existingPositions - Already positioned states
 * @param {Object} config - Configuration object
 * @returns {Object} - Positions for isolated states
 */
function positionIsolatedStates(isolatedStates, existingPositions, config) {
    const positions = {};

    // Find the rightmost position to place isolated states
    let maxX = config.startX;
    Object.values(existingPositions).forEach(pos => {
        maxX = Math.max(maxX, pos.x);
    });

    const isolatedStartX = maxX + config.layerSpacingX;
    const isolatedStartY = config.startY;

    console.log(`Positioning ${isolatedStates.length} isolated states starting at (${isolatedStartX}, ${isolatedStartY})`);

    isolatedStates.forEach((stateId, index) => {
        const x = isolatedStartX;
        const y = isolatedStartY + (index * config.nodeSpacingY);

        positions[stateId] = { x, y };

        console.log(`Positioned isolated state ${stateId} at (${x}, ${y})`);
    });

    return positions;
}

/**
 * Calculate hierarchical layout based on reachability from start state
 * Uses a modified Sugiyama algorithm approach with better level management
 */
function calculateHierarchicalLayout(fsa, config) {
    const positions = {};
    const adjacencyList = buildAdjacencyList(fsa);

    // Find levels using BFS from start state
    const levels = calculateLevels(fsa, adjacencyList);

    // Redistribute levels if they're too wide
    const redistributedLevels = redistributeLevels(levels, config.maxNodesPerLevel);

    // Position states level by level
    const centreX = config.canvasWidth / 2;
    const startY = 80;

    redistributedLevels.forEach((levelStates, levelIndex) => {
        const y = startY + levelIndex * config.levelSpacing;

        if (levelStates.length === 1) {
            // Single state - centre it
            positions[levelStates[0]] = { x: centreX, y: y };
        } else {
            // Multiple states - distribute evenly but not too wide
            const maxWidth = Math.min(config.canvasWidth * 0.8, levelStates.length * config.nodeSpacing);
            const spacing = maxWidth / Math.max(1, levelStates.length - 1);
            const startX = centreX - maxWidth / 2;

            levelStates.forEach((stateId, index) => {
                positions[stateId] = {
                    x: levelStates.length === 1 ? centreX : startX + index * spacing,
                    y: y
                };
            });
        }
    });

    // Handle states not reachable from start (isolated components)
    const positionedStates = new Set(Object.keys(positions));
    const unpositioned = fsa.states.filter(id => !positionedStates.has(id));

    if (unpositioned.length > 0) {
        const isolatedY = startY + redistributedLevels.length * config.levelSpacing;
        const isolatedPositions = calculateCompactGrid(unpositioned, {
            centerX: centreX,
            startY: isolatedY,
            nodeSpacing: config.nodeSpacing,
            canvasWidth: config.canvasWidth
        });
        Object.assign(positions, isolatedPositions);
    }

    return positions;
}

/**
 * Calculate levels for hierarchical layout using BFS
 */
function calculateLevels(fsa, adjacencyList) {
    const levels = [];
    const visited = new Set();
    const queue = [];

    // Start from the starting state if it exists
    if (fsa.startingState && fsa.states.includes(fsa.startingState)) {
        queue.push({ state: fsa.startingState, level: 0 });
        visited.add(fsa.startingState);
    }

    // Process queue
    while (queue.length > 0) {
        const { state, level } = queue.shift();

        // Ensure level array exists
        while (levels.length <= level) {
            levels.push([]);
        }

        levels[level].push(state);

        // Add neighbors to next level
        const neighbors = adjacencyList.get(state) || [];
        neighbors.forEach(neighbor => {
            if (!visited.has(neighbor)) {
                visited.add(neighbor);
                queue.push({ state: neighbor, level: level + 1 });
            }
        });
    }

    // Add any unvisited states to a final level
    const unvisited = fsa.states.filter(id => !visited.has(id));
    if (unvisited.length > 0) {
        levels.push(unvisited);
    }

    return levels;
}

/**
 * Apply clustering to group strongly connected components
 */
function applyClustering(fsa, positions, config) {
    const clusters = findConnectedComponents(fsa); // Use regular connected components
    const newPositions = { ...positions };

    clusters.forEach((cluster, clusterIndex) => {
        if (cluster.length > 1) {
            // Calculate cluster centroid
            let totalX = 0, totalY = 0;
            cluster.forEach(stateId => {
                totalX += positions[stateId].x;
                totalY += positions[stateId].y;
            });
            const centroidX = totalX / cluster.length;
            const centroidY = totalY / cluster.length;

            // Arrange cluster states more compactly
            const radius = Math.min(60, Math.max(30, cluster.length * 12));
            cluster.forEach((stateId, index) => {
                if (cluster.length === 2) {
                    // For pairs, place them side by side
                    const offset = index === 0 ? -radius/2 : radius/2;
                    newPositions[stateId] = {
                        x: centroidX + offset,
                        y: centroidY
                    };
                } else if (cluster.length === 3) {
                    // For triplets, use triangle arrangement
                    const angles = [0, 2*Math.PI/3, 4*Math.PI/3];
                    const angle = angles[index];
                    newPositions[stateId] = {
                        x: centroidX + Math.cos(angle) * radius,
                        y: centroidY + Math.sin(angle) * radius
                    };
                } else {
                    // For larger clusters, use circle arrangement
                    const angle = (2 * Math.PI * index) / cluster.length;
                    newPositions[stateId] = {
                        x: centroidX + Math.cos(angle) * radius,
                        y: centroidY + Math.sin(angle) * radius
                    };
                }
            });
        }
    });

    return newPositions;
}

/**
 * Find strongly connected components using Tarjan's algorithm
 */
function findStronglyConnectedComponents(fsa) {
    const adjacencyList = buildAdjacencyList(fsa);
    const visited = new Set();
    const stack = [];
    const components = [];

    function dfs(state, component) {
        if (visited.has(state)) return;
        visited.add(state);
        component.push(state);

        const neighbors = adjacencyList.get(state) || [];
        neighbors.forEach(neighbor => {
            if (!visited.has(neighbor)) {
                dfs(neighbor, component);
            }
        });
    }

    fsa.states.forEach(state => {
        if (!visited.has(state)) {
            const component = [];
            dfs(state, component);
            if (component.length > 0) {
                components.push(component);
            }
        }
    });

    return components;
}

/**
 * Refine layout using force-directed positioning with better component separation
 */
function refineWithForceDirected(fsa, positions, config) {
    const newPositions = JSON.parse(JSON.stringify(positions));
    const adjacencyList = buildAdjacencyList(fsa);
    const iterations = 30;

    // Calculate component clusters first
    const components = findConnectedComponents(fsa);

    for (let iter = 0; iter < iterations; iter++) {
        const forces = {};

        // Initialise forces
        fsa.states.forEach(state => {
            forces[state] = { x: 0, y: 0 };
        });

        // Inter-component repulsion (stronger)
        components.forEach((comp1, i) => {
            components.forEach((comp2, j) => {
                if (i !== j) {
                    // Calculate component centroids
                    const centroid1 = calculateCentroid(comp1, newPositions);
                    const centroid2 = calculateCentroid(comp2, newPositions);

                    const dx = centroid2.x - centroid1.x;
                    const dy = centroid2.y - centroid1.y;
                    const distance = Math.sqrt(dx * dx + dy * dy) || 1;

                    const repulsiveForce = 8000 / (distance * distance);
                    const fx = (dx / distance) * repulsiveForce;
                    const fy = (dy / distance) * repulsiveForce;

                    // Apply force to all states in each component
                    comp1.forEach(state => {
                        forces[state].x -= fx / comp1.length;
                        forces[state].y -= fy / comp1.length;
                    });
                    comp2.forEach(state => {
                        forces[state].x += fx / comp2.length;
                        forces[state].y += fy / comp2.length;
                    });
                }
            });
        });

        // Intra-component forces (weaker repulsion, stronger attraction)
        components.forEach(component => {
            component.forEach(state1 => {
                component.forEach(state2 => {
                    if (state1 !== state2) {
                        const pos1 = newPositions[state1];
                        const pos2 = newPositions[state2];
                        const dx = pos1.x - pos2.x;
                        const dy = pos1.y - pos2.y;
                        const distance = Math.sqrt(dx * dx + dy * dy) || 1;

                        // Weak repulsion within component
                        const repulsiveForce = 1000 / (distance * distance);
                        const fx = (dx / distance) * repulsiveForce;
                        const fy = (dy / distance) * repulsiveForce;

                        forces[state1].x += fx;
                        forces[state1].y += fy;
                    }
                });
            });
        });

        // Attractive forces between directly connected states
        adjacencyList.forEach((neighbors, state) => {
            neighbors.forEach(neighbor => {
                const pos1 = newPositions[state];
                const pos2 = newPositions[neighbor];
                const dx = pos2.x - pos1.x;
                const dy = pos2.y - pos1.y;
                const distance = Math.sqrt(dx * dx + dy * dy) || 1;

                const attractiveForce = distance * 0.01; // Much stronger attraction
                const fx = (dx / distance) * attractiveForce;
                const fy = (dy / distance) * attractiveForce;

                forces[state].x += fx;
                forces[state].y += fy;
                forces[neighbor].x -= fx;
                forces[neighbor].y -= fy;
            });
        });

        // Canvas boundary repulsion to prevent edge clustering
        fsa.states.forEach(state => {
            const pos = newPositions[state];
            const margin = 100;

            // Left boundary
            if (pos.x < margin) {
                forces[state].x += (margin - pos.x) * 2;
            }
            // Right boundary
            if (pos.x > config.canvasWidth - margin) {
                forces[state].x -= (pos.x - (config.canvasWidth - margin)) * 2;
            }
            // Top boundary
            if (pos.y < margin) {
                forces[state].y += (margin - pos.y) * 2;
            }
            // Bottom boundary
            if (pos.y > config.canvasHeight - margin) {
                forces[state].y -= (pos.y - (config.canvasHeight - margin)) * 2;
            }
        });

        // Apply forces with cooling
        const temperature = Math.max(0.1, 1 - iter / iterations);
        fsa.states.forEach(state => {
            const force = forces[state];
            const forceLength = Math.sqrt(force.x * force.x + force.y * force.y) || 1;
            const maxDisplacement = 20 * temperature;
            const displacement = Math.min(forceLength, maxDisplacement);

            newPositions[state].x += (force.x / forceLength) * displacement;
            newPositions[state].y += (force.y / forceLength) * displacement;
        });
    }

    return newPositions;
}

/**
 * Find connected components (not strongly connected)
 */
function findConnectedComponents(fsa) {
    const adjacencyList = buildUndirectedAdjacencyList(fsa);
    const visited = new Set();
    const components = [];

    function dfs(state, component) {
        if (visited.has(state)) return;
        visited.add(state);
        component.push(state);

        const neighbors = adjacencyList.get(state) || [];
        neighbors.forEach(neighbor => {
            if (!visited.has(neighbor)) {
                dfs(neighbor, component);
            }
        });
    }

    fsa.states.forEach(state => {
        if (!visited.has(state)) {
            const component = [];
            dfs(state, component);
            if (component.length > 0) {
                components.push(component);
            }
        }
    });

    return components;
}

/**
 * Build undirected adjacency list for finding connected components
 */
function buildUndirectedAdjacencyList(fsa) {
    const adjacencyList = new Map();

    // Initialise
    fsa.states.forEach(state => {
        adjacencyList.set(state, []);
    });

    // Build connections (undirected)
    if (fsa.transitions) {
        Object.entries(fsa.transitions).forEach(([sourceId, transitions]) => {
            Object.entries(transitions).forEach(([symbol, targets]) => {
                if (targets && targets.length > 0) {
                    targets.forEach(targetId => {
                        const sourceList = adjacencyList.get(sourceId) || [];
                        const targetList = adjacencyList.get(targetId) || [];

                        if (!sourceList.includes(targetId)) {
                            sourceList.push(targetId);
                        }
                        if (!targetList.includes(sourceId)) {
                            targetList.push(sourceId);
                        }

                        adjacencyList.set(sourceId, sourceList);
                        adjacencyList.set(targetId, targetList);
                    });
                }
            });
        });
    }

    return adjacencyList;
}

/**
 * Calculate centroid of a group of states
 */
function calculateCentroid(states, positions) {
    let totalX = 0, totalY = 0;
    states.forEach(state => {
        totalX += positions[state].x;
        totalY += positions[state].y;
    });
    return {
        x: totalX / states.length,
        y: totalY / states.length
    };
}

/**
 * Redistribute levels to prevent overcrowding
 */
function redistributeLevels(levels, maxNodesPerLevel) {
    const newLevels = [];

    levels.forEach(level => {
        if (level.length <= maxNodesPerLevel) {
            newLevels.push([...level]);
        } else {
            // Split large levels into multiple sub-levels
            for (let i = 0; i < level.length; i += maxNodesPerLevel) {
                const subLevel = level.slice(i, i + maxNodesPerLevel);
                newLevels.push(subLevel);
            }
        }
    });

    return newLevels;
}

/**
 * Calculate compact grid layout for isolated states
 */
function calculateCompactGrid(states, config) {
    const positions = {};
    const cols = Math.min(states.length, Math.floor(config.canvasWidth * 0.8 / config.nodeSpacing));
    const rows = Math.ceil(states.length / cols);

    const totalWidth = (cols - 1) * config.nodeSpacing;
    const startX = config.centerX - totalWidth / 2;

    states.forEach((stateId, index) => {
        const row = Math.floor(index / cols);
        const col = index % cols;

        // Centre the last row if it's not full
        let x = startX + col * config.nodeSpacing;
        if (row === rows - 1) {
            const statesInLastRow = states.length - row * cols;
            if (statesInLastRow < cols) {
                const lastRowWidth = (statesInLastRow - 1) * config.nodeSpacing;
                const lastRowStartX = config.centerX - lastRowWidth / 2;
                x = lastRowStartX + col * config.nodeSpacing;
            }
        }

        positions[stateId] = {
            x: x,
            y: config.startY + row * (config.nodeSpacing * 0.8)
        };
    });

    return positions;
}

/**
 * Build adjacency list from FSA transitions
 */
function buildAdjacencyList(fsa) {
    const adjacencyList = new Map();

    // Initialize
    fsa.states.forEach(state => {
        adjacencyList.set(state, []);
    });

    // Build connections
    if (fsa.transitions) {
        Object.entries(fsa.transitions).forEach(([sourceId, transitions]) => {
            Object.entries(transitions).forEach(([symbol, targets]) => {
                if (targets && targets.length > 0) {
                    targets.forEach(targetId => {
                        const sourceList = adjacencyList.get(sourceId) || [];
                        if (!sourceList.includes(targetId)) {
                            sourceList.push(targetId);
                        }
                        adjacencyList.set(sourceId, sourceList);
                    });
                }
            });
        });
    }

    return adjacencyList;
}

/**
 * Resolve overlapping positions by adjusting nearby states
 */
function resolveOverlaps(positions, minDistance) {
    const states = Object.keys(positions);
    const maxIterations = 8;

    for (let iteration = 0; iteration < maxIterations; iteration++) {
        let hasOverlaps = false;

        for (let i = 0; i < states.length; i++) {
            for (let j = i + 1; j < states.length; j++) {
                const state1 = states[i];
                const state2 = states[j];
                const pos1 = positions[state1];
                const pos2 = positions[state2];

                const dx = pos2.x - pos1.x;
                const dy = pos2.y - pos1.y;
                const distance = Math.sqrt(dx * dx + dy * dy);

                if (distance < minDistance) {
                    hasOverlaps = true;

                    const separation = minDistance - distance;
                    let separationX, separationY;

                    if (distance > 0) {
                        separationX = (dx / distance) * separation * 0.5;
                        separationY = (dy / distance) * separation * 0.5;
                    } else {
                        const angle = Math.random() * 2 * Math.PI;
                        separationX = Math.cos(angle) * minDistance * 0.5;
                        separationY = Math.sin(angle) * minDistance * 0.5;
                    }

                    pos1.x -= separationX;
                    pos1.y -= separationY;
                    pos2.x += separationX;
                    pos2.y += separationY;
                }
            }
        }

        if (!hasOverlaps) break;
    }
}

/**
 * Constrain positions to canvas boundaries with better margin handling
 */
function constrainToCanvas(positions, config) {
    const margin = 100;
    const effectiveWidth = config.canvasWidth - 2 * margin;
    const effectiveHeight = config.canvasHeight - 2 * margin;

    // Find current bounds
    const bounds = {
        minX: Math.min(...Object.values(positions).map(p => p.x)),
        maxX: Math.max(...Object.values(positions).map(p => p.x)),
        minY: Math.min(...Object.values(positions).map(p => p.y)),
        maxY: Math.max(...Object.values(positions).map(p => p.y))
    };

    const currentWidth = bounds.maxX - bounds.minX;
    const currentHeight = bounds.maxY - bounds.minY;

    // Scale if necessary
    let scaleX = 1, scaleY = 1;
    if (currentWidth > effectiveWidth) {
        scaleX = effectiveWidth / currentWidth;
    }
    if (currentHeight > effectiveHeight) {
        scaleY = effectiveHeight / currentHeight;
    }

    const scale = Math.min(scaleX, scaleY, 1); // Don't scale up

    // Apply scaling and centring
    const centreX = config.canvasWidth / 2;
    const centreY = config.canvasHeight / 2;
    const boundsCentreX = (bounds.minX + bounds.maxX) / 2;
    const boundsCentreY = (bounds.minY + bounds.maxY) / 2;

    Object.values(positions).forEach(pos => {
        // Scale around centre
        pos.x = boundsCentreX + (pos.x - boundsCentreX) * scale;
        pos.y = boundsCentreY + (pos.y - boundsCentreY) * scale;

        // Translate to canvas centre
        pos.x = centreX + (pos.x - boundsCentreX);
        pos.y = centreY + (pos.y - boundsCentreY);

        // Final constraint
        pos.x = Math.max(margin, Math.min(config.canvasWidth - margin, pos.x));
        pos.y = Math.max(margin, Math.min(config.canvasHeight - margin, pos.y));
    });
}

/**
 * Get canvas dimensions with fallbacks
 */
function getCanvasWidth() {
    const canvas = document.getElementById('fsa-canvas');
    return canvas ? canvas.offsetWidth : 1200;
}

function getCanvasHeight() {
    const canvas = document.getElementById('fsa-canvas');
    return canvas ? canvas.offsetHeight : 800;
}

/**
 * Calculate positions for states preserving existing positions where possible
 */
export function calculatePositionsPreserving(fsa, existingPositions) {
    return calculateStatePositions(fsa, existingPositions, {
        preserveExisting: true,
        useHierarchical: false,
        useClusters: false
    });
}

/**
 * Calculate positions for completely new FSA layout using the old algorithm
 */
export function calculateFreshLayout(fsa) {
    return calculateStatePositions(fsa, {}, {
        preserveExisting: false,
        useHierarchical: true,
        useClusters: true
    });
}

/**
 * NEW: Calculate positions for transformations and conversions using hierarchical layers
 * This is the main function to use for transform operations and regex conversions
 */
export function calculateTransformLayout(fsa) {
    console.log('Using layered hierarchical positioning for transform/conversion');
    return calculateLayeredHierarchicalPositions(fsa);
}

/**
 * Find position for new states that don't overlap with existing ones
 */
export function findNonOverlappingPositions(existingPositions, newStateIds) {
    const positions = {};
    const config = {
        canvasWidth: getCanvasWidth(),
        canvasHeight: getCanvasHeight(),
        minDistance: 80
    };

    newStateIds.forEach((stateId, index) => {
        let attempts = 0;
        let position;

        do {
            const angle = (index * 2 * Math.PI) / newStateIds.length + (attempts * 0.3);
            const radius = 150 + attempts * 40;

            position = {
                x: config.canvasWidth / 2 + Math.cos(angle) * radius,
                y: config.canvasHeight / 2 + Math.sin(angle) * radius
            };

            attempts++;
        } while (hasOverlapWithExisting(position, existingPositions, config.minDistance) && attempts < 12);

        // Constrain to canvas
        position.x = Math.max(80, Math.min(config.canvasWidth - 80, position.x));
        position.y = Math.max(80, Math.min(config.canvasHeight - 80, position.y));

        positions[stateId] = position;
        existingPositions[stateId] = position;
    });

    return positions;
}

/**
 * Check if position overlaps with existing positions
 */
function hasOverlapWithExisting(position, existingPositions, minDistance) {
    return Object.values(existingPositions).some(existing => {
        const dx = position.x - existing.x;
        const dy = position.y - existing.y;
        const distance = Math.sqrt(dx * dx + dy * dy);
        return distance < minDistance;
    });
}