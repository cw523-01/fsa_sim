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


def _has_epsilon_transitions(fsa: Dict) -> bool:
    """
    Check if the FSA has any epsilon transitions.

    Args:
        fsa: The FSA dictionary

    Returns:
        True if there are epsilon transitions, False otherwise
    """
    for state in fsa['states']:
        if state in fsa['transitions'] and '' in fsa['transitions'][state]:
            if fsa['transitions'][state]['']:  # Non-empty epsilon transitions
                return True
    return False


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

    # Check if FSA has epsilon transitions
    has_epsilon_transitions = _has_epsilon_transitions(fsa)

    # Get epsilon closure of starting state and build proper initial paths
    start_states_with_paths = _get_initial_states_with_paths(fsa, fsa['startingState'])

    # Configuration: (current_state, input_position, path_so_far)
    queue = deque()
    for state, path in start_states_with_paths:
        queue.append((state, 0, path))

    all_accepting_paths = []
    all_partial_paths = []

    # Track configurations to prevent infinite loops
    # We can revisit (state, input_pos) as long as we've made progress
    # Progress = either consumed input OR we're exploring a different epsilon path
    seen_configurations = set()
    paths_explored = 0

    while queue:
        current_state, pos, path = queue.popleft()
        paths_explored += 1

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
            if has_epsilon_transitions:
                # Get all states reachable via epsilon transitions and their paths
                epsilon_states_with_paths = _get_epsilon_closure_with_paths(fsa, next_state)

                # Build path for this transition
                transition_path = path + [(current_state, next_symbol, next_state)]

                # Create separate configurations for each state in epsilon closure
                for eps_state, eps_path_from_next in epsilon_states_with_paths:
                    final_path = transition_path + eps_path_from_next
                    queue.append((eps_state, pos + 1, final_path))
            else:
                # For NFAs without epsilon transitions, use simpler processing
                transition_path = path + [(current_state, next_symbol, next_state)]
                queue.append((next_state, pos + 1, transition_path))

    # Return results
    if all_accepting_paths:
        return all_accepting_paths
    else:
        return {
            'accepted': False,
            'paths_explored': paths_explored,
            'rejection_reason': 'No accepting paths found',
            'partial_paths': all_partial_paths
        }


def _get_initial_states_with_paths(fsa: Dict, start_state: str) -> List[Tuple[str, List[Tuple[str, str, str]]]]:
    """
    Get initial states and their corresponding epsilon paths from the starting state.
    Uses simple cycle detection: don't revisit a state we've already seen in current epsilon-only path.

    Args:
        fsa: The FSA dictionary
        start_state: The starting state

    Returns:
        List of tuples (state, path_to_state) where path_to_state contains epsilon transitions
    """
    # Use BFS to find all reachable states via epsilon transitions
    result = []
    queue = deque([(start_state, [], set([start_state]))])  # (state, path, states_visited_in_this_path)

    while queue:
        current_state, path_to_current, visited_in_path = queue.popleft()

        # Add this state and its path to results
        result.append((current_state, path_to_current))

        # Get epsilon transitions from current state
        epsilon_transitions = _get_transitions(fsa, current_state, '')

        for next_state in epsilon_transitions:
            # Only follow epsilon transition if we haven't visited this state in current path
            if next_state not in visited_in_path:
                new_path = path_to_current + [(current_state, 'ε', next_state)]
                new_visited = visited_in_path | {next_state}
                queue.append((next_state, new_path, new_visited))

    return result


def _get_epsilon_closure_with_paths(fsa: Dict, start_state: str) -> List[Tuple[str, List[Tuple[str, str, str]]]]:
    """
    Get epsilon closure of a state along with the paths to reach each state.
    Uses simple cycle detection: don't revisit a state we've already seen in current epsilon-only path.

    Args:
        fsa: The FSA dictionary
        start_state: The state to compute closure for

    Returns:
        List of tuples (state, path_from_start_state) where path contains epsilon transitions
    """
    result = []
    queue = deque([(start_state, [], set([start_state]))])  # (state, path, states_visited_in_this_path)

    while queue:
        current_state, path_to_current, visited_in_path = queue.popleft()

        # Add this state and its path to results
        result.append((current_state, path_to_current))

        # Get epsilon transitions from current state
        epsilon_transitions = _get_transitions(fsa, current_state, '')

        for next_state in epsilon_transitions:
            # Only follow epsilon transition if we haven't visited this state in current path
            if next_state not in visited_in_path:
                new_path = path_to_current + [(current_state, 'ε', next_state)]
                new_visited = visited_in_path | {next_state}
                queue.append((next_state, new_path, new_visited))

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

    # Check if FSA has epsilon transitions
    has_epsilon_transitions = _has_epsilon_transitions(fsa)

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
            if has_epsilon_transitions:
                # Get all states reachable via epsilon transitions and their paths
                epsilon_states_with_paths = _get_epsilon_closure_with_paths(fsa, next_state)

                # Build path for this transition
                transition_path = path + [(current_state, next_symbol, next_state)]

                # Create separate configurations for each state in epsilon closure
                for eps_state, eps_path_from_next in epsilon_states_with_paths:
                    final_path = transition_path + eps_path_from_next
                    queue.append((eps_state, pos + 1, final_path))
            else:
                # For NFAs without epsilon transitions, use simpler processing
                transition_path = path + [(current_state, next_symbol, next_state)]
                queue.append((next_state, pos + 1, transition_path))

    # Final summary
    yield {
        'type': 'summary',
        'total_accepting_paths': accepting_path_count,
        'total_paths_explored': paths_explored,
        'accepted': accepting_path_count > 0
    }


def detect_epsilon_loops(fsa: Dict) -> Dict:
    """
    Detects if the FSA contains infinite epsilon loops.

    An epsilon loop exists if there's a cycle of epsilon transitions that can be
    traversed infinitely without consuming any input symbols.

    Args:
        fsa: The FSA dictionary

    Returns:
        Dictionary with:
        {
            'has_epsilon_loops': bool,
            'loop_details': [
                {
                    'cycle': [state1, state2, ..., state1],  # States in the cycle
                    'transitions': [(state1, 'ε', state2), ...],  # Epsilon transitions forming the cycle
                    'reachable_from_start': bool  # Whether this loop is reachable from start state
                }
            ]
        }
    """
    if not _has_epsilon_transitions(fsa):
        return {
            'has_epsilon_loops': False,
            'loop_details': []
        }

    # Build epsilon-only transition graph
    epsilon_graph = {}
    for state in fsa['states']:
        epsilon_graph[state] = []
        if state in fsa['transitions'] and '' in fsa['transitions'][state]:
            epsilon_graph[state] = fsa['transitions'][state][''][:]

    # Find all strongly connected components using Tarjan's algorithm
    # This will identify all cycles in the epsilon transition graph
    index_counter = [0]
    stack = []
    lowlinks = {}
    index = {}
    on_stack = {}
    sccs = []

    def strongconnect(state):
        index[state] = index_counter[0]
        lowlinks[state] = index_counter[0]
        index_counter[0] += 1
        stack.append(state)
        on_stack[state] = True

        for successor in epsilon_graph.get(state, []):
            if successor not in index:
                strongconnect(successor)
                lowlinks[state] = min(lowlinks[state], lowlinks[successor])
            elif on_stack[successor]:
                lowlinks[state] = min(lowlinks[state], index[successor])

        if lowlinks[state] == index[state]:
            component = []
            while True:
                w = stack.pop()
                on_stack[w] = False
                component.append(w)
                if w == state:
                    break
            if len(component) > 1 or (len(component) == 1 and state in epsilon_graph.get(state, [])):
                # This is a non-trivial SCC (cycle) or a self-loop
                sccs.append(component)

    for state in fsa['states']:
        if state not in index:
            strongconnect(state)

    # Check if any epsilon loops are reachable from the start state
    reachable_states = _get_all_reachable_states(fsa, fsa['startingState'])

    # Build detailed information about each loop
    loop_details = []
    has_loops = False

    for scc in sccs:
        if len(scc) > 1:
            # Multi-state cycle
            has_loops = True
            cycle_transitions = []

            # Find the actual cycle path through the SCC
            cycle_path = _find_cycle_path_in_scc(scc, epsilon_graph)

            # Build transitions for this cycle
            for i in range(len(cycle_path)):
                current_state = cycle_path[i]
                next_state = cycle_path[(i + 1) % len(cycle_path)]
                cycle_transitions.append((current_state, 'ε', next_state))

            # Check if any state in this cycle is reachable from start
            reachable_from_start = any(state in reachable_states for state in scc)

            loop_details.append({
                'cycle': cycle_path + [cycle_path[0]],  # Close the cycle for display
                'transitions': cycle_transitions,
                'reachable_from_start': reachable_from_start
            })

        elif len(scc) == 1 and scc[0] in epsilon_graph.get(scc[0], []):
            # Self-loop
            has_loops = True
            state = scc[0]
            reachable_from_start = state in reachable_states

            loop_details.append({
                'cycle': [state, state],
                'transitions': [(state, 'ε', state)],
                'reachable_from_start': reachable_from_start
            })

    return {
        'has_epsilon_loops': has_loops,
        'loop_details': loop_details
    }


def _get_epsilon_reachable_states(fsa: Dict, start_state: str) -> Set[str]:
    """
    Get all states reachable from start_state via epsilon transitions only.

    Args:
        fsa: The FSA dictionary
        start_state: Starting state

    Returns:
        Set of states reachable via epsilon transitions
    """
    reachable = set()
    stack = [start_state]

    while stack:
        current = stack.pop()
        if current in reachable:
            continue

        reachable.add(current)

        # Add epsilon transitions
        if current in fsa['transitions'] and '' in fsa['transitions'][current]:
            for next_state in fsa['transitions'][current]['']:
                if next_state not in reachable:
                    stack.append(next_state)

    return reachable


def _get_all_reachable_states(fsa: Dict, start_state: str) -> Set[str]:
    """
    Get all states reachable from start_state via any transitions (regular and epsilon).

    Args:
        fsa: The FSA dictionary
        start_state: Starting state

    Returns:
        Set of all reachable states
    """
    reachable = set()
    stack = [start_state]

    while stack:
        current = stack.pop()
        if current in reachable:
            continue

        reachable.add(current)

        # Add all transitions (both regular and epsilon)
        if current in fsa['transitions']:
            for symbol, next_states in fsa['transitions'][current].items():
                for next_state in next_states:
                    if next_state not in reachable:
                        stack.append(next_state)

    return reachable


def _find_cycle_path_in_scc(scc: List[str], epsilon_graph: Dict) -> List[str]:
    """
    Find a simple cycle path through the strongly connected component.

    Args:
        scc: List of states in the strongly connected component
        epsilon_graph: Graph of epsilon transitions

    Returns:
        List of states forming a cycle
    """
    if len(scc) == 1:
        return scc

    # Use DFS to find a cycle through all states in the SCC
    start_state = scc[0]
    visited = set()
    path = []

    def dfs(state):
        if state in visited:
            # Found a cycle, extract it
            cycle_start_idx = path.index(state)
            return path[cycle_start_idx:]

        visited.add(state)
        path.append(state)

        for next_state in epsilon_graph.get(state, []):
            if next_state in scc:  # Only follow edges within the SCC
                result = dfs(next_state)
                if result:
                    return result

        path.pop()
        visited.remove(state)
        return None

    cycle = dfs(start_state)
    return cycle if cycle else scc  # Fallback to the SCC itself


def simulate_nondeterministic_fsa_with_depth_limit(fsa: Dict, input_string: str, max_depth: int) -> Union[
    List[List[Tuple[str, str, str]]], Dict]:
    """
    Simulates a non-deterministic FSA with the given input string, with depth limiting to handle infinite epsilon loops.

    Args:
        fsa: A dictionary representing the FSA with the following keys:
            - states: List of all states
            - alphabet: List of symbols in the alphabet
            - transitions: Dictionary of transitions (supports epsilon transitions with empty string '')
            - startingState: The starting state
            - acceptingStates: List of accepting states
        input_string: The input string to simulate
        max_depth: Maximum depth to traverse (positive integer) to prevent infinite epsilon loops

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
            'partial_paths': [...],  # Any partial paths that were explored
            'depth_limit_reached': bool  # Whether depth limit was reached
        }
    """
    # Validate input parameters
    if max_depth <= 0:
        return {
            'accepted': False,
            'paths_explored': 0,
            'rejection_reason': 'max_depth must be a positive integer',
            'partial_paths': [],
            'depth_limit_reached': False
        }

    # Validate FSA structure
    if not _is_valid_nfa_structure(fsa):
        return {
            'accepted': False,
            'paths_explored': 0,
            'rejection_reason': 'Invalid FSA structure',
            'partial_paths': [],
            'depth_limit_reached': False
        }

    # Check if FSA has epsilon transitions
    has_epsilon_transitions = _has_epsilon_transitions(fsa)

    # Get epsilon closure of starting state with depth limiting
    start_states_with_paths = _get_initial_states_with_paths_total_depth_limited(fsa, fsa['startingState'], max_depth)

    # Configuration: (current_state, input_position, path_so_far, current_total_depth)
    queue = deque()
    for state, path in start_states_with_paths:
        current_depth = len(path)  # Total transitions (both epsilon and regular)
        queue.append((state, 0, path, current_depth))

    all_accepting_paths = []
    all_partial_paths = []
    paths_explored = 0
    depth_limit_reached = False

    while queue:
        current_state, pos, path, current_depth = queue.popleft()
        paths_explored += 1

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
            # Build path for this transition
            transition_path = path + [(current_state, next_symbol, next_state)]
            new_depth = current_depth + 1  # Count this regular transition

            # Check if we've reached depth limit
            if new_depth > max_depth:
                depth_limit_reached = True
                continue

            if has_epsilon_transitions:
                # Get all states reachable via epsilon transitions with remaining depth
                epsilon_states_with_paths = _get_epsilon_closure_with_paths_total_depth_limited(
                    fsa, next_state, max_depth - new_depth
                )

                # Create separate configurations for each state in epsilon closure
                for eps_state, eps_path_from_next in epsilon_states_with_paths:
                    final_path = transition_path + eps_path_from_next
                    final_depth = new_depth + len(eps_path_from_next)

                    # Check if we've reached depth limit with epsilon transitions
                    if final_depth > max_depth:
                        depth_limit_reached = True
                        continue

                    queue.append((eps_state, pos + 1, final_path, final_depth))
            else:
                # For NFAs without epsilon transitions, use simpler processing
                queue.append((next_state, pos + 1, transition_path, new_depth))

    # Return results
    if all_accepting_paths:
        return all_accepting_paths
    else:
        return {
            'accepted': False,
            'paths_explored': paths_explored,
            'rejection_reason': 'No accepting paths found' + (' (depth limit reached)' if depth_limit_reached else ''),
            'partial_paths': all_partial_paths,
            'depth_limit_reached': depth_limit_reached
        }


def simulate_nondeterministic_fsa_generator_with_depth_limit(fsa: Dict, input_string: str, max_depth: int):
    """
    Generator version of simulate_nondeterministic_fsa with depth limiting that yields results as they are found.

    Args:
        fsa: A dictionary representing the FSA
        input_string: The input string to simulate
        max_depth: Maximum depth to traverse (positive integer) to prevent infinite epsilon loops

    Yields:
        Dictionary with information about each result:
        - For accepting paths: {'type': 'accepting_path', 'path': [...], 'path_number': int, 'final_state': str, 'total_depth': int}
        - For rejected paths: {'type': 'rejected_path', 'path': [...], 'reason': str, 'total_depth': int}
        - For depth limit reached: {'type': 'depth_limit_reached', 'path': [...], 'current_depth': int}
        - For progress updates: {'type': 'progress', 'paths_explored': int, 'queue_size': int, 'depth_limit_reached': bool}
        - For final summary: {'type': 'summary', 'total_accepting_paths': int, 'total_paths_explored': int, 'accepted': bool, 'depth_limit_reached': bool}
    """
    # Validate input parameters
    if max_depth <= 0:
        yield {
            'type': 'error',
            'message': 'max_depth must be a positive integer',
            'accepted': False
        }
        return

    # Validate FSA structure
    if not _is_valid_nfa_structure(fsa):
        yield {
            'type': 'error',
            'message': 'Invalid FSA structure',
            'accepted': False
        }
        return

    # Check if FSA has epsilon transitions
    has_epsilon_transitions = _has_epsilon_transitions(fsa)

    # Get epsilon closure of starting state with depth limiting
    start_states_with_paths = _get_initial_states_with_paths_total_depth_limited(fsa, fsa['startingState'], max_depth)

    # Configuration: (current_state, input_position, path_so_far, current_total_depth)
    queue = deque()
    for state, path in start_states_with_paths:
        current_depth = len(path)  # Total transitions
        queue.append((state, 0, path, current_depth))

    accepting_path_count = 0
    paths_explored = 0
    progress_interval = 25  # Yield progress every 25 paths
    depth_limit_reached = False

    while queue:
        current_state, pos, path, current_depth = queue.popleft()
        paths_explored += 1

        # Yield progress updates periodically
        if paths_explored % progress_interval == 0:
            yield {
                'type': 'progress',
                'paths_explored': paths_explored,
                'queue_size': len(queue),
                'current_state': current_state,
                'input_position': pos,
                'current_depth': current_depth,
                'depth_limit_reached': depth_limit_reached
            }

        # If we've consumed all input
        if pos >= len(input_string):
            if current_state in fsa['acceptingStates']:
                accepting_path_count += 1
                yield {
                    'type': 'accepting_path',
                    'path': path.copy(),
                    'path_number': accepting_path_count,
                    'final_state': current_state,
                    'total_depth': current_depth
                }
            else:
                yield {
                    'type': 'rejected_path',
                    'path': path.copy(),
                    'reason': f"Final state '{current_state}' is not an accepting state",
                    'final_state': current_state,
                    'total_depth': current_depth
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
                'rejection_position': pos,
                'total_depth': current_depth
            }
            continue

        # Get transitions for this symbol from current state
        next_states = _get_transitions(fsa, current_state, next_symbol)

        if not next_states:
            yield {
                'type': 'rejected_path',
                'path': path.copy(),
                'reason': f"No transition for symbol '{next_symbol}' from state '{current_state}'",
                'rejection_position': pos,
                'total_depth': current_depth
            }
            continue

        for next_state in next_states:
            # Build path for this transition
            transition_path = path + [(current_state, next_symbol, next_state)]
            new_depth = current_depth + 1  # Count this regular transition

            # Check if we've reached depth limit
            if new_depth > max_depth:
                depth_limit_reached = True
                yield {
                    'type': 'depth_limit_reached',
                    'path': transition_path,
                    'current_depth': new_depth,
                    'max_depth': max_depth,
                    'state': next_state,
                    'input_position': pos + 1
                }
                continue

            if has_epsilon_transitions:
                # Get all states reachable via epsilon transitions with remaining depth
                epsilon_states_with_paths = _get_epsilon_closure_with_paths_total_depth_limited(
                    fsa, next_state, max_depth - new_depth
                )

                # Create separate configurations for each state in epsilon closure
                for eps_state, eps_path_from_next in epsilon_states_with_paths:
                    final_path = transition_path + eps_path_from_next
                    final_depth = new_depth + len(eps_path_from_next)

                    # Check if we've reached depth limit with epsilon transitions
                    if final_depth > max_depth:
                        depth_limit_reached = True
                        yield {
                            'type': 'depth_limit_reached',
                            'path': final_path,
                            'current_depth': final_depth,
                            'max_depth': max_depth,
                            'state': eps_state,
                            'input_position': pos + 1
                        }
                        continue

                    queue.append((eps_state, pos + 1, final_path, final_depth))
            else:
                # For NFAs without epsilon transitions, use simpler processing
                queue.append((next_state, pos + 1, transition_path, new_depth))

    # Final summary
    yield {
        'type': 'summary',
        'total_accepting_paths': accepting_path_count,
        'total_paths_explored': paths_explored,
        'accepted': accepting_path_count > 0,
        'depth_limit_reached': depth_limit_reached,
        'max_depth_used': max_depth
    }


def _get_initial_states_with_paths_total_depth_limited(fsa: Dict, start_state: str, max_depth: int) -> List[
    Tuple[str, List[Tuple[str, str, str]]]]:
    """
    Get initial states and their corresponding epsilon paths from the starting state with total depth limiting.

    Args:
        fsa: The FSA dictionary
        start_state: The starting state
        max_depth: Maximum total depth to explore

    Returns:
        List of tuples (state, path_to_state) where path_to_state contains epsilon transitions
    """
    result = []
    queue = deque([(start_state, [], 0)])  # (state, path, total_depth)

    while queue:
        current_state, path_to_current, depth = queue.popleft()

        # Add this state and its path to results
        if len(path_to_current) <= max_depth:
            result.append((current_state, path_to_current))

        # Check total depth limit
        if depth >= max_depth:
            continue

        # Get epsilon transitions from current state
        epsilon_transitions = _get_transitions(fsa, current_state, '')

        for next_state in epsilon_transitions:
            new_path = path_to_current + [(current_state, 'ε', next_state)]
            queue.append((next_state, new_path, depth + 1))

    return result


def _get_epsilon_closure_with_paths_total_depth_limited(fsa: Dict, start_state: str, max_depth: int) -> List[
    Tuple[str, List[Tuple[str, str, str]]]]:
    """
    Get epsilon closure of a state along with the paths to reach each state, with total depth limiting.

    Args:
        fsa: The FSA dictionary
        start_state: The state to compute closure for
        max_depth: Maximum total depth to explore

    Returns:
        List of tuples (state, path_from_start_state) where path contains epsilon transitions
    """
    result = []
    queue = deque([(start_state, [], 0)])  # (state, path, total_depth)

    while queue:
        current_state, path_to_current, depth = queue.popleft()

        # Add this state and its path to results
        if len(path_to_current) <= max_depth:
            result.append((current_state, path_to_current))

        # Check total depth limit
        if depth >= max_depth:
            continue

        # Get epsilon transitions from current state
        epsilon_transitions = _get_transitions(fsa, current_state, '')

        for next_state in epsilon_transitions:
            new_path = path_to_current + [(current_state, 'ε', next_state)]
            queue.append((next_state, new_path, depth + 1))

    return result