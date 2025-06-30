from typing import Dict, Set, Tuple, List, FrozenSet
from collections import defaultdict, deque
from .fsa_properties import is_deterministic, validate_fsa_structure


def minimise_dfa(fsa: Dict) -> Dict:
    """
    Minimises a deterministic finite automaton (DFA) using Hopcroft's algorithm.

    Args:
        fsa (Dict): A dictionary representing the DFA.

    Returns:
        Dict: A minimised DFA in the same format.
    """
    if not is_deterministic(fsa):
        raise ValueError("DFA minimisation requires a deterministic FSA.")

    states = set(fsa['states'])
    alphabet = set(fsa['alphabet'])
    accepting = set(fsa['acceptingStates'])
    non_accepting = states - accepting

    # Create initial partition, filtering out empty sets
    initial_partition = []
    if accepting:
        initial_partition.append(accepting)
    if non_accepting:
        initial_partition.append(non_accepting)

    partition: List[Set[str]] = initial_partition
    worklist: List[Set[str]] = [group.copy() for group in initial_partition]

    transition = fsa['transitions']

    def get_reverse_transitions() -> Dict[str, Dict[str, Set[str]]]:
        reverse = {symbol: defaultdict(set) for symbol in alphabet}
        for state in transition:
            for symbol in transition[state]:
                for target in transition[state][symbol]:
                    reverse[symbol][target].add(state)
        return reverse

    reverse_transitions = get_reverse_transitions()

    while worklist:
        splitter = worklist.pop()
        for symbol in alphabet:
            involved = set()
            for state in splitter:
                involved |= reverse_transitions[symbol].get(state, set())
            new_partition = []
            for group in partition:
                inter = group & involved
                diff = group - involved
                if inter and diff:
                    new_partition.extend([inter, diff])
                    if group in worklist:
                        worklist.remove(group)
                        worklist.extend([inter, diff])
                    else:
                        worklist.append(inter if len(inter) <= len(diff) else diff)
                else:
                    new_partition.append(group)
            partition = new_partition

    # Map old states to new states, filtering out empty groups
    state_map = {}
    new_states = []
    for i, group in enumerate(partition):
        if group:  # Only process non-empty groups
            name = "_".join(sorted(group))
            for state in group:
                state_map[state] = name
            new_states.append(name)

    new_start = state_map[fsa['startingState']]
    new_accepting = sorted(set(state_map[s] for s in accepting if s in state_map))
    new_transitions = defaultdict(lambda: defaultdict(list))

    for state in fsa['states']:
        if state in state_map:  # Only process states that are in the final partition
            mapped_state = state_map[state]
            for symbol in fsa['alphabet']:
                targets = fsa['transitions'].get(state, {}).get(symbol, [])
                if targets:
                    target = targets[0]  # deterministic: only one
                    if target in state_map:  # Ensure target is also in final partition
                        new_transitions[mapped_state][symbol] = [state_map[target]]

    return {
        "states": sorted(set(new_states)),
        "alphabet": fsa['alphabet'],
        "transitions": new_transitions,
        "startingState": new_start,
        "acceptingStates": new_accepting
    }


def nfa_to_dfa(nfa: Dict) -> Dict:
    """
    Converts a non-deterministic finite automaton (NFA) to a deterministic finite automaton (DFA)
    using subset construction algorithm.

    Args:
        nfa (Dict): A dictionary representing the NFA with the following keys:
            - states: List of all states
            - alphabet: List of symbols in the alphabet (excluding epsilon)
            - transitions: Dictionary of transitions (may include epsilon transitions with '')
            - startingState: The starting state
            - acceptingStates: List of accepting states

    Returns:
        Dict: A DFA in the same format where each state represents a subset of NFA states

    Raises:
        ValueError: If the input is not a valid NFA structure
    """
    # Validate NFA structure
    validation_result = validate_fsa_structure(nfa)
    if not validation_result['valid']:
        raise ValueError(f"Invalid NFA structure: {validation_result.get('error', 'Unknown error')}")

    # Memorisation cache for epsilon closures
    epsilon_closure_cache: Dict[FrozenSet[str], FrozenSet[str]] = {}

    def epsilon_closure(states: FrozenSet[str]) -> FrozenSet[str]:
        """Compute epsilon closure of a set of states with memoization"""
        if states in epsilon_closure_cache:
            return epsilon_closure_cache[states]

        closure = set(states)
        stack = list(states)

        while stack:
            state = stack.pop()
            # Get epsilon transitions from this state
            if state in nfa['transitions'] and '' in nfa['transitions'][state]:
                for epsilon_target in nfa['transitions'][state]['']:
                    if epsilon_target not in closure:
                        closure.add(epsilon_target)
                        stack.append(epsilon_target)

        result = frozenset(closure)
        epsilon_closure_cache[states] = result
        return result

    def move(states: FrozenSet[str], symbol: str) -> FrozenSet[str]:
        """Compute all states reachable from given states on given symbol"""
        result = set()
        for state in states:
            if state in nfa['transitions'] and symbol in nfa['transitions'][state]:
                result.update(nfa['transitions'][state][symbol])
        return frozenset(result)

    def frozenset_to_state_name(state_set: FrozenSet[str]) -> str:
        """Convert a frozenset of states to a canonical state name"""
        if not state_set:
            return "EMPTY"  # Empty set state

        # Use a more robust naming scheme to avoid collisions
        # Sort states and join with a delimiter that can't appear in state names
        sorted_states = sorted(state_set)
        # Use a hash-based approach for very large state sets to keep names manageable
        if len(sorted_states) > 10:
            # For large state sets, use a hash-based name with first few states for readability
            first_states = sorted_states[:3]
            state_hash = abs(hash(state_set)) % 10000
            return f"{'_'.join(first_states)}_PLUS_{len(sorted_states) - 3}more_H{state_hash}"
        else:
            return "_".join(sorted_states)

    # Start with epsilon closure of the starting state
    start_state_set = frozenset({nfa['startingState']})
    start_closure = epsilon_closure(start_state_set)
    start_state_name = frozenset_to_state_name(start_closure)

    # Use frozensets as keys for better performance and unambiguous identification
    dfa_state_map: Dict[FrozenSet[str], str] = {}  # Maps frozenset to state name
    dfa_transitions = defaultdict(lambda: defaultdict(list))

    # Queue of subsets to process: frozenset of NFA states
    queue = deque([start_closure])
    dfa_state_map[start_closure] = start_state_name
    processed_states: Set[FrozenSet[str]] = set()

    # Pre-compute NFA accepting states as frozenset for faster membership testing
    nfa_accepting = frozenset(nfa.get('acceptingStates', []))

    while queue:
        current_nfa_states = queue.popleft()

        # Skip if already processed (avoid redundant work)
        if current_nfa_states in processed_states:
            continue
        processed_states.add(current_nfa_states)

        current_dfa_state = dfa_state_map[current_nfa_states]

        # For each symbol in the alphabet
        for symbol in nfa['alphabet']:
            # Compute move(current_nfa_states, symbol)
            moved_states = move(current_nfa_states, symbol)

            # Early pruning: skip if no states are reachable
            if not moved_states:
                # Only create empty state if we need to maintain completeness
                # In many cases, we can avoid this by not requiring complete DFAs
                continue

            # Compute epsilon closure of the moved states
            new_state_set = epsilon_closure(moved_states)

            # Early pruning: skip empty states unless they're actually needed
            if not new_state_set:
                continue

            # Generate state name if not already exists
            if new_state_set not in dfa_state_map:
                new_state_name = frozenset_to_state_name(new_state_set)
                dfa_state_map[new_state_set] = new_state_name
                # Add to queue only if not already processed
                if new_state_set not in processed_states:
                    queue.append(new_state_set)

            # Add transition
            target_state_name = dfa_state_map[new_state_set]
            dfa_transitions[current_dfa_state][symbol] = [target_state_name]

    # Handle missing transitions by adding them to a dead state only if necessary
    all_dfa_states = list(dfa_state_map.values())
    dead_state_needed = False

    # Check if we need a dead state for completeness
    for dfa_state in all_dfa_states:
        for symbol in nfa['alphabet']:
            if symbol not in dfa_transitions[dfa_state]:
                dead_state_needed = True
                break
        if dead_state_needed:
            break

    # Add dead state only if needed
    if dead_state_needed:
        dead_state_name = "DEAD"
        # Ensure dead state name doesn't conflict
        counter = 1
        while dead_state_name in all_dfa_states:
            dead_state_name = f"DEAD_{counter}"
            counter += 1

        all_dfa_states.append(dead_state_name)

        # Add missing transitions to dead state
        for dfa_state in all_dfa_states[:-1]:  # Exclude the dead state itself
            for symbol in nfa['alphabet']:
                if symbol not in dfa_transitions[dfa_state]:
                    dfa_transitions[dfa_state][symbol] = [dead_state_name]

        # Dead state transitions to itself
        for symbol in nfa['alphabet']:
            dfa_transitions[dead_state_name][symbol] = [dead_state_name]

    # Determine accepting states: any DFA state that contains an NFA accepting state
    dfa_accepting = []
    for state_set, state_name in dfa_state_map.items():
        if state_set & nfa_accepting:  # Fast intersection check with frozensets
            dfa_accepting.append(state_name)

    # Build the final DFA
    dfa = {
        'states': sorted(all_dfa_states),
        'alphabet': nfa['alphabet'][:],
        'transitions': dict(dfa_transitions),
        'startingState': start_state_name,
        'acceptingStates': sorted(dfa_accepting)
    }

    return dfa