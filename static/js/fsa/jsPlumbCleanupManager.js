/**
 * JSPlumb Cleanup Manager
 * Handles proper cleanup of JSPlumb references to prevent ID reuse issues
 */

class JSPlumbCleanupManager {
    constructor() {
        this.jsPlumbInstance = null;
    }

    /**
     * Initialize with JSPlumb instance
     * @param {Object} jsPlumbInstance - The JSPlumb instance
     */
    initialize(jsPlumbInstance) {
        this.jsPlumbInstance = jsPlumbInstance;
    }

    /**
     * Completely remove all traces of an element from JSPlumb
     * This is critical when IDs will be reused
     * @param {string} elementId - The ID of the element to clean up
     * @returns {boolean} - Success status
     */
    completelyRemoveElement(elementId) {
        if (!this.jsPlumbInstance || !elementId) return false;

        try {
            console.log(`Starting complete removal of element: ${elementId}`);

            // 1. Remove all connections involving this element
            const connections = this.jsPlumbInstance.getConnections({
                source: elementId
            }).concat(this.jsPlumbInstance.getConnections({
                target: elementId
            }));

            connections.forEach(conn => {
                try {
                    this.jsPlumbInstance.deleteConnection(conn);
                } catch (error) {
                    console.warn(`Error deleting connection:`, error);
                }
            });

            // 2. Remove all endpoints for this element
            try {
                this.jsPlumbInstance.removeAllEndpoints(elementId);
            } catch (error) {
                console.warn(`Error removing endpoints for ${elementId}:`, error);
            }

            // 3. Remove the element from JSPlumb's management
            try {
                this.jsPlumbInstance.remove(elementId);
            } catch (error) {
                console.warn(`Error removing element ${elementId} from JSPlumb:`, error);
            }

            // 4. CRITICAL: Clean up managed elements cache manually
            // This is the key fix from the JSPlumb issues
            try {
                const managedElements = this.jsPlumbInstance.getManagedElements();
                if (managedElements && managedElements[elementId]) {
                    delete managedElements[elementId];
                    console.log(`Manually deleted ${elementId} from managed elements cache`);
                }
            } catch (error) {
                console.warn(`Error cleaning managed elements cache for ${elementId}:`, error);
            }

            // 5. Force repaint to ensure visual consistency
            setTimeout(() => {
                try {
                    this.jsPlumbInstance.repaintEverything();
                } catch (error) {
                    console.warn(`Error during repaint:`, error);
                }
            }, 10);

            console.log(`Successfully completed removal of element: ${elementId}`);
            return true;

        } catch (error) {
            console.error(`Error during complete element removal for ${elementId}:`, error);
            return false;
        }
    }

    /**
     * Prepare an element for safe reuse of its ID
     * @param {string} elementId - The ID that will be reused
     */
    prepareForIdReuse(elementId) {
        console.log(`Preparing for ID reuse: ${elementId}`);
        
        // Suspend drawing during cleanup for performance
        this.jsPlumbInstance.setSuspendDrawing(true);
        
        try {
            this.completelyRemoveElement(elementId);
        } finally {
            this.jsPlumbInstance.setSuspendDrawing(false);
        }
        
        console.log(`ID ${elementId} is now safe for reuse`);
    }

    /**
     * Handle state renaming by updating all references
     * @param {string} oldId - The old state ID
     * @param {string} newId - The new state ID
     * @param {HTMLElement} stateElement - The state element (already renamed in DOM)
     */
    handleStateRename(oldId, newId, stateElement) {
        if (!this.jsPlumbInstance || !oldId || !newId || !stateElement) return false;

        console.log(`Handling state rename: ${oldId} -> ${newId}`);

        try {
            // Suspend drawing during the rename process
            this.jsPlumbInstance.setSuspendDrawing(true);

            // 1. Get all connections that involve the old ID
            const oldConnections = this.jsPlumbInstance.getConnections({
                source: oldId
            }).concat(this.jsPlumbInstance.getConnections({
                target: oldId
            }));

            // 2. Store connection data for recreation
            const connectionData = oldConnections.map(conn => ({
                sourceId: conn.sourceId === oldId ? newId : conn.sourceId,
                targetId: conn.targetId === oldId ? newId : conn.targetId,
                connector: conn.connector ? conn.connector.type : 'Straight',
                overlays: conn.overlays || [],
                paintStyle: conn.getPaintStyle(),
                // Store any additional connection properties you need
            }));

            // 3. Remove all old connections and endpoints
            this.completelyRemoveElement(oldId);

            // 4. Force JSPlumb to recognize the renamed element
            this.jsPlumbInstance.revalidate(stateElement);

            // 5. Re-register the element as source and target
            this.jsPlumbInstance.makeSource(stateElement, {
                filter: ".edge-source",
                anchor: "Continuous",
                connectorStyle: { stroke: "black", strokeWidth: 2 },
                connectionType: "basic"
            });

            this.jsPlumbInstance.makeTarget(stateElement, {
                anchor: "Continuous",
                connectionType: "basic"
            });

            // 6. Recreate connections with the new ID
            setTimeout(() => {
                connectionData.forEach(connData => {
                    try {
                        // Only recreate if both source and target still exist
                        if (document.getElementById(connData.sourceId) && 
                            document.getElementById(connData.targetId)) {
                            
                            const newConnection = this.jsPlumbInstance.connect({
                                source: connData.sourceId,
                                target: connData.targetId,
                                connector: connData.connector,
                                paintStyle: connData.paintStyle,
                                overlays: connData.overlays
                            });

                            console.log(`Recreated connection: ${connData.sourceId} -> ${connData.targetId}`);
                        }
                    } catch (error) {
                        console.error(`Error recreating connection:`, error);
                    }
                });

                this.jsPlumbInstance.setSuspendDrawing(false);
                this.jsPlumbInstance.repaintEverything();
            }, 50);

            console.log(`Successfully handled state rename: ${oldId} -> ${newId}`);
            return true;

        } catch (error) {
            console.error(`Error during state rename:`, error);
            this.jsPlumbInstance.setSuspendDrawing(false);
            return false;
        }
    }

    /**
     * Nuclear option: reset JSPlumb completely
     * Use this when other cleanup methods fail
     */
    resetJSPlumb() {
        if (!this.jsPlumbInstance) return;

        console.warn('Performing JSPlumb reset - this will clear all connections');
        
        try {
            this.jsPlumbInstance.reset();
            console.log('JSPlumb reset completed');
        } catch (error) {
            console.error('Error during JSPlumb reset:', error);
        }
    }

    /**
     * Diagnostic function to check JSPlumb internal state
     * @returns {Object} - Diagnostic information
     */
    diagnoseJSPlumbState() {
        if (!this.jsPlumbInstance) return { error: 'No JSPlumb instance' };

        try {
            const managedElements = this.jsPlumbInstance.getManagedElements();
            const allConnections = this.jsPlumbInstance.getAllConnections();
            
            const report = {
                managedElementsCount: Object.keys(managedElements || {}).length,
                managedElementIds: Object.keys(managedElements || {}),
                connectionsCount: allConnections.length,
                statesInDOM: [],
                orphanedReferences: []
            };

            // Check for states in DOM
            const stateElements = document.querySelectorAll('.state, .accepting-state');
            stateElements.forEach(element => {
                report.statesInDOM.push(element.id);
            });

            // Check for orphaned references (managed elements not in DOM)
            report.managedElementIds.forEach(id => {
                if (!document.getElementById(id)) {
                    report.orphanedReferences.push(id);
                }
            });

            console.log('JSPlumb State Diagnosis:', report);
            return report;

        } catch (error) {
            console.error('Error during JSPlumb diagnosis:', error);
            return { error: error.message };
        }
    }

    /**
     * Auto-fix orphaned references in JSPlumb
     * @returns {Object} - Fix results
     */
    autoFixOrphanedReferences() {
        const diagnosis = this.diagnoseJSPlumbState();
        const results = { fixed: [], failed: [] };

        if (diagnosis.orphanedReferences && diagnosis.orphanedReferences.length > 0) {
            console.log(`Found ${diagnosis.orphanedReferences.length} orphaned references, cleaning up...`);

            diagnosis.orphanedReferences.forEach(orphanedId => {
                try {
                    this.completelyRemoveElement(orphanedId);
                    results.fixed.push(orphanedId);
                } catch (error) {
                    console.error(`Failed to clean up orphaned reference ${orphanedId}:`, error);
                    results.failed.push(orphanedId);
                }
            });
        }

        console.log('Auto-fix orphaned references completed:', results);
        return results;
    }
}

// Create singleton instance
const jsPlumbCleanupManager = new JSPlumbCleanupManager();

// Make globally available for debugging
if (typeof window !== 'undefined') {
    window.jsPlumbCleanupManager = jsPlumbCleanupManager;
}

// Export for module systems
export { JSPlumbCleanupManager, jsPlumbCleanupManager };