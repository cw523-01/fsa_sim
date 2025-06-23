from typing import Dict, List, Set
from collections import deque


def is_deterministic(fsa: Dict) -> bool:
    """
    Checks if the FSA is deterministic.

    An FSA is deterministic if:
    1. It has no epsilon transitions
    2. For each state and each symbol, there is exactly one transition

    Args:
        fsa: A dictionary representing the FSA with the following keys:
            - states: List of all states
            - alphabet: List of symbols in the alphabet
            - transitions: Dictionary of transitions
            - startingState: The starting state
            - acceptingStates: List of accepting states

    Returns:
        bool: True if the FSA is deterministic, False otherwise
    """
    # Handle empty alphabet case - trivially deterministic
    if not fsa.get('alphabet') or len(fsa['alphabet']) == 0:
        return True

    # Check for epsilon transitions
    for state in fsa.get('states', []):
        if state in fsa.get('transitions', {}) and '' in fsa['transitions'][state]:
            if fsa['transitions'][state]['']:  # Non-empty epsilon transitions
                return False

    # For each state and each symbol, check if there is exactly one transition
    for state in fsa.get('states', []):
        if state not in fsa.get('transitions', {}):
            continue

        for symbol in fsa['alphabet']:
            if symbol in fsa['transitions'][state]:
                transitions = fsa['transitions'][state][symbol]
                # If there is more than one transition, the FSA is not deterministic
                if len(transitions) > 1:
                    return False

    return True


def is_complete(fsa: Dict) -> bool:
    """
    Checks if the FSA is complete.

    An FSA is complete if for each state and each symbol, there is at least one transition.
    Epsilon transitions are ignored for completeness check.

    Args:
        fsa: A dictionary representing the FSA

    Returns:
        bool: True if the FSA is complete, False otherwise
    """
    # Handle empty cases
    if not fsa.get('states') or len(fsa['states']) == 0:
        return True  # Trivially complete if no states

    if not fsa.get('alphabet') or len(fsa['alphabet']) == 0:
        return True  # Trivially complete if no alphabet

    # For each state and each symbol, check if there is at least one transition
    for state in fsa['states']:
        if state not in fsa.get('transitions', {}):
            return False

        for symbol in fsa['alphabet']:
            if symbol not in fsa['transitions'][state]:
                return False

            transitions = fsa['transitions'][state][symbol]
            # If there are no transitions, the FSA is not complete
            if len(transitions) == 0:
                return False

    return True


def is_connected(fsa: Dict) -> bool:
    """
    Checks if the FSA is connected.

    An FSA is connected if all states are reachable from the starting state.

    Args:
        fsa: A dictionary representing the FSA

    Returns:
        bool: True if the FSA is connected, False otherwise
    """
    # Handle empty states case
    if not fsa.get('states') or len(fsa['states']) == 0:
        return True  # Trivially connected if no states

    # If there's no starting state, the FSA can't be connected (unless only one state)
    if not fsa.get('startingState'):
        return len(fsa['states']) <= 1

    # If starting state is not in states list, not connected
    if fsa['startingState'] not in fsa['states']:
        return False

    # If there's only one state, it's trivially connected
    if len(fsa['states']) <= 1:
        return True

    # Handle case where transitions don't exist
    if not fsa.get('transitions'):
        return len(fsa['states']) <= 1

    # Use BFS to find all reachable states from the starting state
    reachable_states = set()
    queue = deque([fsa['startingState']])
    reachable_states.add(fsa['startingState'])

    while queue:
        current_state = queue.popleft()

        # Safety check: make sure currentState exists in transitions
        if current_state not in fsa['transitions']:
            continue

        # Create symbols array including epsilon transitions
        symbols_to_check = list(fsa.get('alphabet', []))
        if '' in fsa['transitions'][current_state]:
            symbols_to_check.append('')  # Add epsilon transitions

        # Check all possible transitions from this state
        for symbol in symbols_to_check:
            if symbol not in fsa['transitions'][current_state]:
                continue

            transitions = fsa['transitions'][current_state][symbol]

            for next_state in transitions:
                if next_state not in reachable_states:
                    reachable_states.add(next_state)
                    queue.append(next_state)

    # If all states are reachable, the FSA is connected
    return len(reachable_states) == len(fsa['states'])


def check_all_properties(fsa: Dict) -> Dict:
    """
    Check all FSA properties at once.

    Args:
        fsa: A dictionary representing the FSA

    Returns:
        Dict: Dictionary containing all property check results:
        {
            'deterministic': bool,
            'complete': bool,
            'connected': bool
        }
    """
    return {
        'deterministic': is_deterministic(fsa),
        'complete': is_complete(fsa),
        'connected': is_connected(fsa)
    }


def validate_fsa_structure(fsa: Dict) -> Dict:
    """
    Validates that the FSA has the required structure for property checking.
    This is more lenient than before to allow partial FSAs.

    Args:
        fsa: The FSA dictionary to validate

    Returns:
        Dict: Validation result with 'valid' boolean and optional 'error' message
    """
    if not isinstance(fsa, dict):
        return {'valid': False, 'error': 'FSA must be a dictionary'}

    required_keys = ['states', 'alphabet', 'transitions', 'startingState', 'acceptingStates']

    # Check all required keys exist
    for key in required_keys:
        if key not in fsa:
            return {'valid': False, 'error': f'Missing required key: {key}'}

    # Check that values are the right type, but allow empty values
    if not isinstance(fsa['states'], list):
        return {'valid': False, 'error': 'states must be a list'}

    if not isinstance(fsa['alphabet'], list):
        return {'valid': False, 'error': 'alphabet must be a list'}

    if not isinstance(fsa['transitions'], dict):
        return {'valid': False, 'error': 'transitions must be a dictionary'}

    if not isinstance(fsa['acceptingStates'], list):
        return {'valid': False, 'error': 'acceptingStates must be a list'}

    # Only check starting state if it exists and there are states
    if fsa.get('startingState') and fsa.get('states'):
        if fsa['startingState'] not in fsa['states']:
            return {'valid': False, 'error': 'Starting state not in states list'}

    # Only check accepting states if there are states
    if fsa.get('states'):
        for state in fsa.get('acceptingStates', []):
            if state not in fsa['states']:
                return {'valid': False, 'error': f'Accepting state {state} not in states list'}

    return {'valid': True}

def is_nondeterministic(fsa: Dict) -> bool:
    """
    Checks if the FSA is non-deterministic.

    An FSA is non-deterministic if:
    1. For any state and symbol, there are multiple possible next states
    2. There are epsilon transitions (empty string '')

    Args:
        fsa: The FSA dictionary

    Returns:
        True if non-deterministic, False if deterministic
    """
    # Check for epsilon transitions
    for state in fsa['states']:
        if state in fsa['transitions'] and '' in fsa['transitions'][state]:
            if fsa['transitions'][state]['']:  # Non-empty epsilon transitions
                return True

    # Check for multiple transitions on same symbol
    alphabet_with_epsilon = fsa['alphabet'] + ['']

    for state in fsa['states']:
        if state not in fsa['transitions']:
            continue

        for symbol in alphabet_with_epsilon:
            if symbol in fsa['transitions'][state]:
                if len(fsa['transitions'][state][symbol]) > 1:
                    return True

    return False