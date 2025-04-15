/**
 * Updates the alphabet display with unique symbols from all edges
 * @param {Map} edgeSymbolMap - Map of edge IDs to their symbols
 * @param {Map} epsilonTransitionMap - Map of edge IDs to boolean indicating epsilon transition
 */
export function updateAlphabetDisplay(edgeSymbolMap, epsilonTransitionMap) {
    // Get all unique symbols from all edges
    const allSymbols = new Set();
    edgeSymbolMap.forEach(symbols => {
        symbols.forEach(symbol => {
            allSymbols.add(symbol);
        });
    });

    // Sort the symbols alphabetically
    const sortedSymbols = Array.from(allSymbols).sort();

    // Check if we have any epsilon transitions
    let hasEpsilon = false;
    if (epsilonTransitionMap) {
        epsilonTransitionMap.forEach(hasEpsilon => {
            if (hasEpsilon) {
                hasEpsilon = true;
            }
        });
    }

    // Update the alphabet display
    const alphabetDisplay = document.querySelector('.alphabet-info p');
    if (alphabetDisplay) {
        let displayText = 'Σ = {';

        if (sortedSymbols.length > 0) {
            displayText += sortedSymbols.join(',');
        }

        displayText += '}';

        // Add epsilon information if needed
        if (hasEpsilon) {
            displayText += ' ∪ {ε}';
        }

        alphabetDisplay.textContent = displayText;
    }
}