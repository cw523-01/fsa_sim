from typing import Dict, List, Union, Tuple, Optional, Set
from collections import deque
from .fsa_properties import is_deterministic, validate_fsa_structure


def simulate_deterministic_fsa(fsa: Dict, input_string: str) -> Union[List[Tuple[str, str, str]], Dict]:
    """
    Simulates a deterministic FSA with the given input string.

    :param fsa: A dictionary representing the FSA with keys: states, alphabet, transitions, startingState, acceptingStates
    :type fsa: Dict
    :param input_string: The input string to simulate
    :type input_string: str
    :return: If accepted, returns a list of transitions. If rejected, returns a dictionary with 'accepted', 'path', 'rejection_reason' and 'rejection_position'
    :rtype: Union[List[Tuple[str, str, str]], Dict]
    """
    # Validate the FSA is deterministic
    if not is_deterministic(fsa):
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
        return execution_path  # Return path directly for accepted
    else:
        return {
            'accepted': False,
            'path': execution_path,
            'rejection_reason': f"Final state '{current_state}' is not an accepting state",
            'rejection_position': len(input_string)
        }


def _has_epsilon_transitions(fsa: Dict) -> bool:
    """
    Check if the FSA has any epsilon transitions.

    :param fsa: The FSA dictionary
    :type fsa: Dict
    :return: True if there are epsilon transitions, False otherwise
    :rtype: bool
    """
    for state in fsa['states']:
        if state in fsa['transitions'] and '' in fsa['transitions'][state]:
            if fsa['transitions'][state]['']:  # Non-empty epsilon transitions
                return True
    return False


def simulate_nondeterministic_fsa(fsa: Dict, input_string: str) -> Union[List[List[Tuple[str, str, str]]], Dict]:
    """
    Simulates a non-deterministic FSA with the given input string, finding all possible execution paths.

    :param fsa: A dictionary representing the FSA with keys: states, alphabet, transitions (supports epsilon transitions with ''), startingState, acceptingStates
    :type fsa: Dict
    :param input_string: The input string to simulate
    :type input_string: str
    :return: If accepted, returns a list of all accepting paths. If rejected, returns a dictionary with 'accepted', 'paths_explored', 'rejection_reason' and 'partial_paths'
    :rtype: Union[List[List[Tuple[str, str, str]]], Dict]
    """
    # Validate FSA structure
    validation_result = validate_fsa_structure(fsa)
    if not validation_result['valid']:
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

    :param fsa: The FSA dictionary
    :type fsa: Dict
    :param start_state: The starting state
    :type start_state: str
    :return: List of tuples (state, path_to_state) where path_to_state contains epsilon transitions
    :rtype: List[Tuple[str, List[Tuple[str, str, str]]]]
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

    :param fsa: The FSA dictionary
    :type fsa: Dict
    :param start_state: The state to compute closure for
    :type start_state: str
    :return: List of tuples (state, path_from_start_state) where path contains epsilon transitions
    :rtype: List[Tuple[str, List[Tuple[str, str, str]]]]
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


def _get_transitions(fsa: Dict, state: str, symbol: str) -> List[str]:
    """
    Get all states reachable from given state on given symbol.

    :param fsa: The FSA dictionary
    :type fsa: Dict
    :param state: Current state
    :type state: str
    :param symbol: Input symbol (or empty string for epsilon)
    :type symbol: str
    :return: List of next states
    :rtype: List[str]
    """
    if state not in fsa['transitions']:
        return []

    if symbol not in fsa['transitions'][state]:
        return []

    return fsa['transitions'][state][symbol]


def simulate_nondeterministic_fsa_generator(fsa: Dict, input_string: str):
    """
    Generator version of simulate_nondeterministic_fsa that yields results as they are found.

    :param fsa: A dictionary representing the FSA
    :type fsa: Dict
    :param input_string: The input string to simulate
    :type input_string: str
    :return: Generator yielding dictionaries with information about each result: accepting paths, rejected paths, progress updates and final summary
    :rtype: Generator[Dict, None, None]
    """
    # Validate FSA structure
    validation_result = validate_fsa_structure(fsa)
    if not validation_result['valid']:
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

    :param fsa: The FSA dictionary
    :type fsa: Dict
    :return: Dictionary with 'has_epsilon_loops' boolean and 'loop_details' list containing cycle information
    :rtype: Dict
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

    :param fsa: The FSA dictionary
    :type fsa: Dict
    :param start_state: Starting state
    :type start_state: str
    :return: Set of states reachable via epsilon transitions
    :rtype: Set[str]
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

    :param fsa: The FSA dictionary
    :type fsa: Dict
    :param start_state: Starting state
    :type start_state: str
    :return: Set of all reachable states
    :rtype: Set[str]
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

    :param scc: List of states in the strongly connected component
    :type scc: List[str]
    :param epsilon_graph: Graph of epsilon transitions
    :type epsilon_graph: Dict
    :return: List of states forming a cycle
    :rtype: List[str]
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

    :param fsa: A dictionary representing the FSA with keys: states, alphabet, transitions (supports epsilon transitions with ''), startingState, acceptingStates
    :type fsa: Dict
    :param input_string: The input string to simulate
    :type input_string: str
    :param max_depth: Maximum depth to traverse (positive integer) to prevent infinite epsilon loops
    :type max_depth: int
    :return: If accepted, returns a list of all accepting paths. If rejected, returns a dictionary with 'accepted', 'paths_explored', 'rejection_reason', 'partial_paths' and 'depth_limit_reached'
    :rtype: Union[List[List[Tuple[str, str, str]]], Dict]
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
    validation_result = validate_fsa_structure(fsa)
    if not validation_result['valid']:
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

    :param fsa: A dictionary representing the FSA
    :type fsa: Dict
    :param input_string: The input string to simulate
    :type input_string: str
    :param max_depth: Maximum depth to traverse (positive integer) to prevent infinite epsilon loops
    :type max_depth: int
    :return: Generator yielding dictionaries with information about each result: accepting paths, rejected paths, depth limit reached, progress updates and final summary
    :rtype: Generator[Dict, None, None]
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
    validation_result = validate_fsa_structure(fsa)
    if not validation_result['valid']:
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

    :param fsa: The FSA dictionary
    :type fsa: Dict
    :param start_state: The starting state
    :type start_state: str
    :param max_depth: Maximum total depth to explore
    :type max_depth: int
    :return: List of tuples (state, path_to_state) where path_to_state contains epsilon transitions
    :rtype: List[Tuple[str, List[Tuple[str, str, str]]]]
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

    :param fsa: The FSA dictionary
    :type fsa: Dict
    :param start_state: The state to compute closure for
    :type start_state: str
    :param max_depth: Maximum total depth to explore
    :type max_depth: int
    :return: List of tuples (state, path_from_start_state) where path contains epsilon transitions
    :rtype: List[Tuple[str, List[Tuple[str, str, str]]]]
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