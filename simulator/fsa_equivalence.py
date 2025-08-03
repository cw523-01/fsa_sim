from typing import Dict, Tuple, Set, Optional
from .fsa_transformations import nfa_to_dfa, minimise_dfa, complete_dfa, remove_unreachable_states, remove_dead_states
from .fsa_properties import is_deterministic


def preprocess_automaton(automaton: Dict) -> Dict:
    """
    Preprocess an automaton by removing unreachable and dead states,
    and cleaning up the alphabet to remove unused symbols.

    :param automaton: An FSA (either NFA or DFA)
    :type automaton: Dict
    :return: A preprocessed automaton equivalent to the input
    :rtype: Dict
    """
    # Remove unreachable states first
    processed = remove_unreachable_states(automaton)

    # Then remove dead states (which also cleans up the alphabet)
    processed = remove_dead_states(processed)

    return processed


def normalise_automaton(automaton: Dict) -> Dict:
    """
    Convert an automaton to its canonical minimal DFA form.

    :param automaton: An FSA (either NFA or DFA)
    :type automaton: Dict
    :return: A minimal DFA equivalent to the input automaton
    :rtype: Dict
    """
    # First preprocess to remove unreachable/dead states and clean alphabet
    preprocessed = preprocess_automaton(automaton)

    # Convert to DFA if needed
    if is_deterministic(preprocessed):
        dfa = preprocessed
    else:
        dfa = nfa_to_dfa(preprocessed)

    # Minimise the DFA
    minimal_dfa = minimise_dfa(dfa)

    return minimal_dfa


def find_state_mapping(dfa1: Dict, dfa2: Dict) -> Optional[Dict[str, str]]:
    """
    Find a bijective mapping between states of two DFAs if they are isomorphic.

    :param dfa1: First DFA
    :type dfa1: Dict
    :param dfa2: Second DFA
    :type dfa2: Dict
    :return: A dictionary mapping states from dfa1 to dfa2, or None if no mapping exists
    :rtype: Optional[Dict[str, str]]
    """
    # Quick checks
    if len(dfa1['states']) != len(dfa2['states']):
        return None
    if len(dfa1['acceptingStates']) != len(dfa2['acceptingStates']):
        return None
    if set(dfa1['alphabet']) != set(dfa2['alphabet']):
        return None

    # Special case: both DFAs are empty
    if len(dfa1['states']) == 0 and len(dfa2['states']) == 0:
        return {}  # Empty mapping for empty DFAs

    # Try to find a mapping starting from the start states
    mapping = {}
    queue = [(dfa1['startingState'], dfa2['startingState'])]

    while queue:
        state1, state2 = queue.pop(0)

        # Check if we've already mapped this state
        if state1 in mapping:
            if mapping[state1] != state2:
                return None  # Inconsistent mapping
            continue

        # Add to mapping
        mapping[state1] = state2

        # Check if accepting state status matches
        is_accepting1 = state1 in dfa1['acceptingStates']
        is_accepting2 = state2 in dfa2['acceptingStates']
        if is_accepting1 != is_accepting2:
            return None

        # Check transitions
        for symbol in dfa1['alphabet']:
            # Get transitions for this symbol
            targets1 = dfa1['transitions'].get(state1, {}).get(symbol, [])
            targets2 = dfa2['transitions'].get(state2, {}).get(symbol, [])

            # DFAs should have exactly one target per symbol (or none)
            if len(targets1) != len(targets2):
                return None

            if targets1 and targets2:
                target1 = targets1[0]
                target2 = targets2[0]

                # Check if this creates a consistent mapping
                if target1 in mapping:
                    if mapping[target1] != target2:
                        return None
                else:
                    queue.append((target1, target2))

    # Verify we've mapped all states
    if len(mapping) != len(dfa1['states']):
        return None

    return mapping


def are_dfas_isomorphic(dfa1: Dict, dfa2: Dict) -> bool:
    """
    Check if two DFAs are isomorphic (structurally identical up to state renaming).

    :param dfa1: First DFA
    :type dfa1: Dict
    :param dfa2: Second DFA
    :type dfa2: Dict
    :return: True if the DFAs are isomorphic, False otherwise
    :rtype: bool
    """
    mapping = find_state_mapping(dfa1, dfa2)
    return mapping is not None


def are_automata_equivalent(automaton1: Dict, automaton2: Dict) -> Tuple[bool, Dict]:
    """
    Check if two automata (NFAs or DFAs) are language-equivalent.

    This uses the DFA minimisation method: two automata are equivalent if and only if
    their minimal DFAs are isomorphic.

    :param automaton1: First automaton (NFA or DFA)
    :type automaton1: Dict
    :param automaton2: Second automaton (NFA or DFA)
    :type automaton2: Dict
    :return: A tuple of (is_equivalent, details) where is_equivalent is True if the automata accept the same language, and details is a dictionary containing additional information about the comparison
    :rtype: Tuple[bool, Dict]
    """
    details = {
        'automaton1_type': 'DFA' if is_deterministic(automaton1) else 'NFA',
        'automaton2_type': 'DFA' if is_deterministic(automaton2) else 'NFA',
        'automaton1_states': len(automaton1['states']),
        'automaton2_states': len(automaton2['states']),
    }

    try:
        # Preprocess both automata before normalisation
        preprocessed1 = preprocess_automaton(automaton1)
        preprocessed2 = preprocess_automaton(automaton2)

        details['preprocessed1_states'] = len(preprocessed1['states'])
        details['preprocessed2_states'] = len(preprocessed2['states'])
        details['preprocessed1_alphabet'] = len(preprocessed1['alphabet'])
        details['preprocessed2_alphabet'] = len(preprocessed2['alphabet'])

        # Normalise both automata to minimal DFAs
        minimal_dfa1 = normalise_automaton(preprocessed1)
        minimal_dfa2 = normalise_automaton(preprocessed2)

        details['minimal_dfa1_states'] = len(minimal_dfa1['states'])
        details['minimal_dfa2_states'] = len(minimal_dfa2['states'])

        # Make both DFAs complete before checking isomorphism
        complete_dfa1 = complete_dfa(minimal_dfa1)
        complete_dfa2 = complete_dfa(minimal_dfa2)

        details['complete_dfa1_states'] = len(complete_dfa1['states'])
        details['complete_dfa2_states'] = len(complete_dfa2['states'])

        # Quick check: complete minimal DFAs must have same number of states
        if len(complete_dfa1['states']) != len(complete_dfa2['states']):
            details['reason'] = 'Complete minimal DFAs have different number of states'
            return False, details

        # Check if the complete minimal DFAs are isomorphic
        is_equivalent = are_dfas_isomorphic(complete_dfa1, complete_dfa2)

        if is_equivalent:
            details['reason'] = 'Complete minimal DFAs are isomorphic'
            details['state_mapping'] = find_state_mapping(complete_dfa1, complete_dfa2)
        else:
            details['reason'] = 'Complete minimal DFAs are not isomorphic'

        return is_equivalent, details

    except Exception as e:
        details['error'] = str(e)
        details['reason'] = 'Error during equivalence checking'
        return False, details