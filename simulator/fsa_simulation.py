from typing import Dict, List, Union, Tuple, Optional, Set
from collections import deque


def simulate_deterministic_fsa(fsa: Dict, input_string: str) -> Union[List[Tuple[str, str, str]], Dict]:
    """
    Simulates a deterministic FSA with the given input string.

    Args:
        fsa: A dictionary representing the FSA with the following keys:
            - states: List of all states
            - alphabet: List of symbols in the alphabet
            - transitions: Dictionary of transitions
            - startingState: The starting state
            - acceptingStates: List of accepting states
        input_string: The input string to simulate

    Returns:
        If the input is accepted, returns a list of transitions in the format:
        [(current_state, symbol, next_state), ...].
        If the input is rejected, returns a dictionary with:
        {
            'accepted': False,
            'path': [(current_state, symbol, next_state), ...],  # Path up to rejection
            'rejection_reason': str,  # Why rejected
            'rejection_position': int  # Position where rejection occurred
        }
    """
    # Validate the FSA is deterministic
    if not _is_deterministic(fsa):
        return {
            'accepted': False,
            'path': [],
            'rejection_reason': 'FSA must be deterministic',
            'rejection_position': 0
        }

    current_state = fsa['startingState']
    execution_path = []

    # Process each symbol in the input string
    for position, symbol in enumerate(input_string):
        # Check if the symbol is in the alphabet
        if symbol not in fsa['alphabet']:
            return {
                'accepted': False,
                'path': execution_path,
                'rejection_reason': f"Symbol '{symbol}' not in alphabet",
                'rejection_position': position
            }

        # Get the next state for this symbol (if any)
        if symbol not in fsa['transitions'][current_state] or not fsa['transitions'][current_state][symbol]:
            return {
                'accepted': False,
                'path': execution_path,
                'rejection_reason': f"No transition defined for symbol '{symbol}' from state '{current_state}'",
                'rejection_position': position
            }

        next_states = fsa['transitions'][current_state][symbol]

        # In a deterministic FSA, there should be at most one next state
        if len(next_states) != 1:
            return {
                'accepted': False,
                'path': execution_path,
                'rejection_reason': f"Non-deterministic transition: multiple states for symbol '{symbol}' from state '{current_state}'",
                'rejection_position': position
            }

        next_state = next_states[0]

        # Record this transition in our execution path
        execution_path.append((current_state, symbol, next_state))

        # Update current state
        current_state = next_state

    # Check if we ended in an accepting state
    if current_state in fsa['acceptingStates']:
        return execution_path  # Return path directly for accepted (backwards compatibility)
    else:
        return {
            'accepted': False,
            'path': execution_path,
            'rejection_reason': f"Final state '{current_state}' is not an accepting state",
            'rejection_position': len(input_string)
        }


def _is_deterministic(fsa: Dict) -> bool:
    """
    Checks if the FSA is deterministic.

    An FSA is deterministic if:
    1. For each state and each symbol, there is at most one transition
    2. There are no epsilon transitions (this is assumed)
    """
    # Assuming no epsilon transitions

    for state in fsa['states']:
        for symbol in fsa['alphabet']:
            # Check if there's a transition for this symbol
            if symbol in fsa['transitions'][state]:
                # If there's a transition, ensure it leads to at most one state
                if len(fsa['transitions'][state][symbol]) > 1:
                    return False  # Not deterministic (multiple possible next states)

    return True


def simulate_nondeterministic_fsa(fsa: Dict, input_string: str) -> Union[List[List[Tuple[str, str, str]]], Dict]:
    """
    Simulates a non-deterministic FSA with the given input string, finding all possible execution paths.

    Args:
        fsa: A dictionary representing the FSA with the following keys:
            - states: List of all states
            - alphabet: List of symbols in the alphabet
            - transitions: Dictionary of transitions (supports epsilon transitions with empty string '')
            - startingState: The starting state
            - acceptingStates: List of accepting states
        input_string: The input string to simulate

    Returns:
        If the input is accepted, returns a list of all accepting paths:
        [
            [(current_state, symbol, next_state), ...],  # Path 1
            [(current_state, symbol, next_state), ...],  # Path 2
            ...
        ]
        If the input is rejected, returns a dictionary with:
        {
            'accepted': False,
            'paths_explored': int,  # Number of paths explored
            'rejection_reason': str,  # Why rejected
            'partial_paths': [...]  # Any partial paths that were explored
        }
    """
    # Validate FSA structure
    if not _is_valid_nfa_structure(fsa):
        return {
            'accepted': False,
            'paths_explored': 0,
            'rejection_reason': 'Invalid FSA structure',
            'partial_paths': []
        }

    # Get epsilon closure of starting state and build proper initial paths
    start_states_with_paths = _get_initial_states_with_paths(fsa, fsa['startingState'])

    # Configuration: (current_state, input_position, path_so_far)
    queue = deque()
    for state, path in start_states_with_paths:
        queue.append((state, 0, path))

    all_accepting_paths = []
    all_partial_paths = []
    seen_configurations = set()
    paths_explored = 0

    while queue:
        current_state, pos, path = queue.popleft()
        paths_explored += 1

        # Create configuration signature for cycle detection
        config_sig = (current_state, pos, tuple(path))

        # Skip if we've seen this exact configuration before (prevents infinite loops)
        if config_sig in seen_configurations:
            continue
        seen_configurations.add(config_sig)

        # Store partial path for debugging
        all_partial_paths.append(path.copy())

        # If we've consumed all input
        if pos >= len(input_string):
            # Check if current state is accepting
            if current_state in fsa['acceptingStates']:
                all_accepting_paths.append(path.copy())
            continue

        # Process next input symbol
        next_symbol = input_string[pos]

        # Check if symbol is in alphabet
        if next_symbol not in fsa['alphabet']:
            continue

        # Get transitions for this symbol from current state
        next_states = _get_transitions(fsa, current_state, next_symbol)

        for next_state in next_states:
            # Get all states reachable via epsilon transitions and their paths
            epsilon_states_with_paths = _get_epsilon_closure_with_paths(fsa, next_state)

            # Build path for this transition
            transition_path = path + [(current_state, next_symbol, next_state)]

            # Create separate configurations for each state in epsilon closure
            for eps_state, eps_path_from_next in epsilon_states_with_paths:
                final_path = transition_path + eps_path_from_next
                queue.append((eps_state, pos + 1, final_path))

    # Return results
    if all_accepting_paths:
        return all_accepting_paths
    else:
        return {
            'accepted': False,
            'paths_explored': paths_explored,
            'rejection_reason': 'No accepting paths found',
            'partial_paths': all_partial_paths[:10]  # Limit to first 10 for readability
        }


def _get_initial_states_with_paths(fsa: Dict, start_state: str) -> List[Tuple[str, List[Tuple[str, str, str]]]]:
    """
    Get initial states and their corresponding epsilon paths from the starting state.

    Args:
        fsa: The FSA dictionary
        start_state: The starting state

    Returns:
        List of tuples (state, path_to_state) where path_to_state contains epsilon transitions
    """
    # Use BFS to find all reachable states via epsilon transitions
    result = []
    visited = set()
    queue = deque([(start_state, [])])  # (state, path_to_reach_state)

    while queue:
        current_state, path_to_current = queue.popleft()

        if current_state in visited:
            continue
        visited.add(current_state)

        # Add this state and its path to results
        result.append((current_state, path_to_current))

        # Get epsilon transitions from current state
        epsilon_transitions = _get_transitions(fsa, current_state, '')

        for next_state in epsilon_transitions:
            if next_state not in visited:
                new_path = path_to_current + [(current_state, 'ε', next_state)]
                queue.append((next_state, new_path))

    return result


def _get_epsilon_closure_with_paths(fsa: Dict, start_state: str) -> List[Tuple[str, List[Tuple[str, str, str]]]]:
    """
    Get epsilon closure of a state along with the paths to reach each state.

    Args:
        fsa: The FSA dictionary
        start_state: The state to compute closure for

    Returns:
        List of tuples (state, path_from_start_state) where path contains epsilon transitions
    """
    result = []
    visited = set()
    queue = deque([(start_state, [])])  # (state, path_from_start_state)

    while queue:
        current_state, path_to_current = queue.popleft()

        if current_state in visited:
            continue
        visited.add(current_state)

        # Add this state and its path to results
        result.append((current_state, path_to_current))

        # Get epsilon transitions from current state
        epsilon_transitions = _get_transitions(fsa, current_state, '')

        for next_state in epsilon_transitions:
            if next_state not in visited:
                new_path = path_to_current + [(current_state, 'ε', next_state)]
                queue.append((next_state, new_path))

    return result


def _epsilon_closure(fsa: Dict, states: Set[str]) -> Set[str]:
    """
    Compute epsilon closure of a set of states.

    Args:
        fsa: The FSA dictionary
        states: Set of states to compute closure for

    Returns:
        Set of states reachable via epsilon transitions
    """
    closure = set(states)
    stack = list(states)

    while stack:
        current = stack.pop()
        epsilon_transitions = _get_transitions(fsa, current, '')  # Empty string for epsilon

        for next_state in epsilon_transitions:
            if next_state not in closure:
                closure.add(next_state)
                stack.append(next_state)

    return closure


def _get_transitions(fsa: Dict, state: str, symbol: str) -> List[str]:
    """
    Get all states reachable from given state on given symbol.

    Args:
        fsa: The FSA dictionary
        state: Current state
        symbol: Input symbol (or empty string for epsilon)

    Returns:
        List of next states
    """
    if state not in fsa['transitions']:
        return []

    if symbol not in fsa['transitions'][state]:
        return []

    return fsa['transitions'][state][symbol]


def _is_valid_nfa_structure(fsa: Dict) -> bool:
    """
    Validates that the FSA has the required structure for NFA simulation.

    Args:
        fsa: The FSA dictionary to validate

    Returns:
        True if structure is valid, False otherwise
    """
    required_keys = ['states', 'alphabet', 'transitions', 'startingState', 'acceptingStates']

    # Check all required keys exist
    for key in required_keys:
        if key not in fsa:
            return False

    # Check starting state is in states
    if fsa['startingState'] not in fsa['states']:
        return False

    # Check accepting states are in states
    for state in fsa['acceptingStates']:
        if state not in fsa['states']:
            return False

    # Check transitions structure
    if not isinstance(fsa['transitions'], dict):
        return False

    return True


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


def simulate_nondeterministic_fsa_generator(fsa: Dict, input_string: str):
    """
    Generator version of simulate_nondeterministic_fsa that yields results as they are found.

    Args:
        fsa: A dictionary representing the FSA
        input_string: The input string to simulate

    Yields:
        Dictionary with information about each result:
        - For accepting paths: {'type': 'accepting_path', 'path': [...], 'path_number': int}
        - For rejected paths: {'type': 'rejected_path', 'path': [...], 'reason': str}
        - For progress updates: {'type': 'progress', 'paths_explored': int, 'queue_size': int}
        - For final summary: {'type': 'summary', 'total_accepting_paths': int, 'total_paths_explored': int}
    """
    # Validate FSA structure
    if not _is_valid_nfa_structure(fsa):
        yield {
            'type': 'error',
            'message': 'Invalid FSA structure',
            'accepted': False
        }
        return

    # Get epsilon closure of starting state and build proper initial paths
    start_states_with_paths = _get_initial_states_with_paths(fsa, fsa['startingState'])

    # Configuration: (current_state, input_position, path_so_far)
    queue = deque()
    for state, path in start_states_with_paths:
        queue.append((state, 0, path))

    accepting_path_count = 0
    seen_configurations = set()
    paths_explored = 0
    progress_interval = 25  # Yield progress every 25 paths

    while queue:
        current_state, pos, path = queue.popleft()
        paths_explored += 1

        # Yield progress updates periodically
        if paths_explored % progress_interval == 0:
            yield {
                'type': 'progress',
                'paths_explored': paths_explored,
                'queue_size': len(queue),
                'current_state': current_state,
                'input_position': pos
            }

        # Create configuration signature for cycle detection
        config_sig = (current_state, pos, tuple(path))

        # Skip if we've seen this exact configuration before
        if config_sig in seen_configurations:
            continue
        seen_configurations.add(config_sig)

        # If we've consumed all input
        if pos >= len(input_string):
            if current_state in fsa['acceptingStates']:
                accepting_path_count += 1
                yield {
                    'type': 'accepting_path',
                    'path': path.copy(),
                    'path_number': accepting_path_count,
                    'final_state': current_state
                }
            else:
                yield {
                    'type': 'rejected_path',
                    'path': path.copy(),
                    'reason': f"Final state '{current_state}' is not an accepting state",
                    'final_state': current_state
                }
            continue

        # Process next input symbol
        next_symbol = input_string[pos]

        # Check if symbol is in alphabet
        if next_symbol not in fsa['alphabet']:
            yield {
                'type': 'rejected_path',
                'path': path.copy(),
                'reason': f"Symbol '{next_symbol}' not in alphabet",
                'rejection_position': pos
            }
            continue

        # Get transitions for this symbol from current state
        next_states = _get_transitions(fsa, current_state, next_symbol)

        if not next_states:
            yield {
                'type': 'rejected_path',
                'path': path.copy(),
                'reason': f"No transition for symbol '{next_symbol}' from state '{current_state}'",
                'rejection_position': pos
            }
            continue

        for next_state in next_states:
            # Get all states reachable via epsilon transitions and their paths
            epsilon_states_with_paths = _get_epsilon_closure_with_paths(fsa, next_state)

            # Build path for this transition
            transition_path = path + [(current_state, next_symbol, next_state)]

            # Create separate configurations for each state in epsilon closure
            for eps_state, eps_path_from_next in epsilon_states_with_paths:
                final_path = transition_path + eps_path_from_next
                queue.append((eps_state, pos + 1, final_path))

    # Final summary
    yield {
        'type': 'summary',
        'total_accepting_paths': accepting_path_count,
        'total_paths_explored': paths_explored,
        'accepted': accepting_path_count > 0
    }