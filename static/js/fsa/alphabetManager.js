/**
 * Updates the alphabet display with unique symbols from all edges
 * @param {Map} edgeSymbolMap - Map of edge IDs to their symbols
 * @param {Map} epsilonTransitionMap - Map of edge IDs to boolean indicating epsilon transition
 */
export function updateAlphabetDisplay(edgeSymbolMap, epsilonTransitionMap) {
    // Get all unique symbols from all edges
    const allSymbols = new Set();
    if (edgeSymbolMap) {
        edgeSymbolMap.forEach(symbols => {
            if (symbols && symbols.length) {
                symbols.forEach(symbol => {
                    allSymbols.add(symbol);
                });
            }
        });
    }

    // Sort the symbols alphabetically
    const sortedSymbols = Array.from(allSymbols).sort();

    // Update the alphabet display
    const alphabetDisplay = document.querySelector('.alphabet-info p');
    if (alphabetDisplay) {
        let displayText = 'Σ = {';

        if (sortedSymbols.length > 0) {
            // Add spaces after commas to help with wrapping
            displayText += sortedSymbols.join(', ');
        }

        displayText += '}';

        alphabetDisplay.textContent = displayText;

        // Class for long alphabets to enable scrolling if needed
        const alphabetContainer = document.querySelector('.alphabet-info');
        if (alphabetContainer) {
            if (sortedSymbols.length > 10) {
                alphabetContainer.classList.add('long-alphabet');
            } else {
                alphabetContainer.classList.remove('long-alphabet');
            }
        }
    }
}