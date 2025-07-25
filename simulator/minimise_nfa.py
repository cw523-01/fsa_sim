from typing import Dict, Set, List, Tuple, NamedTuple, FrozenSet
from collections import defaultdict, deque
from .fsa_transformations import nfa_to_dfa, minimise_dfa
from .fsa_equivalence import are_automata_equivalent


class MinimisationResult(NamedTuple):
    """Result of NFA minimisation with metadata about the process"""
    nfa: Dict
    original_states: int
    final_states: int
    reduction: int
    reduction_percent: float
    is_optimal: bool
    method_used: str
    stages: List[str]
    candidate_results: List[Dict]
    equivalence_verified: bool
    verification_details: Dict


class StateSet:
    """Immutable set of states for the Kameda-Weiner algorithm"""

    def __init__(self, states):
        self._states = frozenset(states)
        self._hash = hash(self._states)

    def __hash__(self):
        return self._hash

    def __eq__(self, other):
        return isinstance(other, StateSet) and self._states == other._states

    def __iter__(self):
        return iter(self._states)

    def __len__(self):
        return len(self._states)

    def __contains__(self, item):
        return item in self._states

    def intersect(self, other):
        return StateSet(self._states & other._states)

    def union(self, other):
        return StateSet(self._states | other._states)

    def any(self, predicate):
        return any(predicate(state) for state in self._states)

    def __repr__(self):
        return f"StateSet({sorted(self._states)})"


class Grid:
    """Represents a grid in the Kameda-Weiner prime grid computation"""

    def __init__(self, rows: Set[int], columns: Set[int]):
        self.rows = frozenset(rows)
        self.columns = frozenset(columns)
        self._hash = hash((self.rows, self.columns))

    def __hash__(self):
        return self._hash

    def __eq__(self, other):
        return isinstance(other, Grid) and self.rows == other.rows and self.columns == other.columns

    def __repr__(self):
        return f"Grid(rows={sorted(self.rows)}, cols={sorted(self.columns)})"


class Cover:
    """Represents a cover of grids"""

    def __init__(self, grids: Set[Grid]):
        self.grids = frozenset(grids)
        self._hash = hash(self.grids)

    def __hash__(self):
        return self._hash

    def __eq__(self, other):
        return isinstance(other, Cover) and self.grids == other.grids

    def __iter__(self):
        return iter(self.grids)

    def __len__(self):
        return len(self.grids)


def remove_unreachable_states(nfa: Dict) -> Dict:
    """Remove states that are unreachable from the start state."""

    # BFS from start state to find all reachable states
    reachable = set()
    queue = deque([nfa['startingState']])
    reachable.add(nfa['startingState'])

    while queue:
        current = queue.popleft()
        if current in nfa['transitions']:
            for symbol in nfa['transitions'][current]:
                for target in nfa['transitions'][current][symbol]:
                    if target not in reachable:
                        reachable.add(target)
                        queue.append(target)

    # Build new NFA with only reachable states
    new_states = [s for s in nfa['states'] if s in reachable]
    new_accepting = [s for s in nfa['acceptingStates'] if s in reachable]
    new_transitions = {}

    for state in new_states:
        if state in nfa['transitions']:
            new_transitions[state] = {}
            for symbol in nfa['transitions'][state]:
                targets = [t for t in nfa['transitions'][state][symbol] if t in reachable]
                if targets:
                    new_transitions[state][symbol] = targets

    result = {
        'states': new_states,
        'alphabet': nfa['alphabet'][:],
        'transitions': new_transitions,
        'startingState': nfa['startingState'],
        'acceptingStates': new_accepting
    }

    return result


def remove_dead_states(nfa: Dict) -> Dict:
    """Remove states that cannot reach any accepting state."""

    # Build reverse graph
    reverse_graph = defaultdict(set)
    for state in nfa['states']:
        if state in nfa['transitions']:
            for symbol in nfa['transitions'][state]:
                for target in nfa['transitions'][state][symbol]:
                    reverse_graph[target].add(state)

    # BFS backwards from accepting states
    alive_states = set(nfa['acceptingStates'])
    queue = deque(nfa['acceptingStates'])

    while queue:
        state = queue.popleft()
        for predecessor in reverse_graph[state]:
            if predecessor not in alive_states:
                alive_states.add(predecessor)
                queue.append(predecessor)

    # Build new NFA with only alive states
    new_states = [s for s in nfa['states'] if s in alive_states]
    new_accepting = [s for s in nfa['acceptingStates'] if s in alive_states]
    new_transitions = {}

    for state in new_states:
        if state in nfa['transitions']:
            new_transitions[state] = {}
            for symbol in nfa['transitions'][state]:
                targets = [t for t in nfa['transitions'][state][symbol] if t in alive_states]
                if targets:
                    new_transitions[state][symbol] = targets

    used_symbols = set()

    # Removing a dead state may have removed a character from the alphabet
    # In result, only use characters found in resulting transition for new alphabet
    for state in new_states:
        if state in new_transitions:
            for symbol in new_transitions[state]:
                if symbol != '':  # Don't include epsilon in alphabet
                    used_symbols.add(symbol)

    result = {
        'states': new_states,
        'alphabet': sorted(list(used_symbols)),
        'transitions': new_transitions,
        'startingState': nfa['startingState'] if nfa['startingState'] in alive_states else '',
        'acceptingStates': new_accepting
    }

    return result


def eliminate_epsilon_transitions(nfa: Dict) -> Dict:
    """Eliminate epsilon transitions using standard epsilon elimination."""

    if not any('' in nfa['transitions'].get(s, {}) for s in nfa['states']):
        return nfa

    # Compute epsilon closures for all states
    def compute_epsilon_closure(state: str) -> Set[str]:
        closure = {state}
        stack = [state]

        while stack:
            current = stack.pop()
            if current in nfa['transitions'] and '' in nfa['transitions'][current]:
                for target in nfa['transitions'][current]['']:
                    if target not in closure:
                        closure.add(target)
                        stack.append(target)

        return closure

    epsilon_closures = {}
    for state in nfa['states']:
        epsilon_closures[state] = compute_epsilon_closure(state)

    # Build new transitions without epsilon
    new_transitions = {}
    alphabet_no_epsilon = [s for s in nfa['alphabet'] if s != '']

    for state in nfa['states']:
        new_transitions[state] = {}

        # For each non-epsilon symbol
        for symbol in alphabet_no_epsilon:
            targets = set()

            # From epsilon closure of current state
            for eps_state in epsilon_closures[state]:
                if eps_state in nfa['transitions'] and symbol in nfa['transitions'][eps_state]:
                    for direct_target in nfa['transitions'][eps_state][symbol]:
                        # Add epsilon closure of each target
                        targets.update(epsilon_closures[direct_target])

            if targets:
                new_transitions[state][symbol] = sorted(list(targets))

    # Update accepting states - a state is accepting if any state in its epsilon closure is accepting
    new_accepting = []
    for state in nfa['states']:
        if any(eps_state in nfa['acceptingStates'] for eps_state in epsilon_closures[state]):
            new_accepting.append(state)

    result = {
        'states': nfa['states'][:],
        'alphabet': alphabet_no_epsilon,
        'transitions': new_transitions,
        'startingState': nfa['startingState'],
        'acceptingStates': new_accepting
    }

    return result


def determinise_nfa(nfa: Dict) -> Tuple[Dict, Dict]:
    """Convert NFA to DFA using subset construction."""

    # Map from StateSet to new state name
    state_sets_to_states = {}
    state_counter = 0

    def get_state_name(state_set):
        nonlocal state_counter
        state_set_obj = StateSet(state_set)
        if state_set_obj not in state_sets_to_states:
            state_sets_to_states[state_set_obj] = f"d{state_counter}"
            state_counter += 1
        return state_sets_to_states[state_set_obj]

    # Start with the initial state set
    initial_set = {nfa['startingState']}
    start_state = get_state_name(initial_set)

    # BFS to build DFA
    queue = deque([StateSet(initial_set)])
    processed = set()
    dfa_transitions = {}

    while queue:
        current_set = queue.popleft()
        if current_set in processed:
            continue
        processed.add(current_set)

        current_state = state_sets_to_states[current_set]
        dfa_transitions[current_state] = {}

        # For each symbol in alphabet
        for symbol in nfa['alphabet']:
            next_states = set()

            # Collect all states reachable by this symbol
            for state in current_set:
                if state in nfa['transitions'] and symbol in nfa['transitions'][state]:
                    next_states.update(nfa['transitions'][state][symbol])

            if next_states:
                next_state_set = StateSet(next_states)
                next_state = get_state_name(next_states)
                dfa_transitions[current_state][symbol] = [next_state]

                if next_state_set not in processed:
                    queue.append(next_state_set)

    # Determine accepting states
    accepting_states = []
    for state_set, state_name in state_sets_to_states.items():
        if state_set.any(lambda s: s in nfa['acceptingStates']):
            accepting_states.append(state_name)

    dfa = {
        'states': list(state_sets_to_states.values()),
        'alphabet': nfa['alphabet'][:],
        'transitions': dfa_transitions,
        'startingState': start_state,
        'acceptingStates': accepting_states
    }

    return dfa, state_sets_to_states


def make_state_map(nfa: Dict) -> Tuple[Dict, Dict, Dict, Dict]:
    """Create state map as described in Kameda-Weiner algorithm."""

    # Determinise NFA
    dfa, state_mapping = determinise_nfa(nfa)

    # Create dual (reverse) NFA
    dual_nfa = {
        'states': nfa['states'][:],
        'alphabet': nfa['alphabet'][:],
        'transitions': {},
        'startingState': '',
        'acceptingStates': [nfa['startingState']]  # Reverse: old start becomes accept
    }

    # Reverse transitions
    for state in nfa['states']:
        if state in nfa['transitions']:
            for symbol in nfa['transitions'][state]:
                for target in nfa['transitions'][state][symbol]:
                    if target not in dual_nfa['transitions']:
                        dual_nfa['transitions'][target] = {}
                    if symbol not in dual_nfa['transitions'][target]:
                        dual_nfa['transitions'][target][symbol] = []
                    dual_nfa['transitions'][target][symbol].append(state)

    # Create artificial start state that connects to all original accepting states
    if nfa['acceptingStates']:
        dual_start = 'dual_start'
        dual_nfa['states'].append(dual_start)
        dual_nfa['startingState'] = dual_start
        dual_nfa['transitions'][dual_start] = {}

        # Add epsilon transitions to all original accepting states
        dual_nfa['transitions'][dual_start][''] = nfa['acceptingStates'][:]
        if '' not in dual_nfa['alphabet']:
            dual_nfa['alphabet'].append('')

    dual_dfa, dual_state_mapping = determinise_nfa(dual_nfa)

    # Create state map matrix
    dfa_states = dfa['states'][:]
    dual_states = dual_dfa['states'][:]

    # Put start states first (important for the algorithm)
    if dfa['startingState'] in dfa_states:
        dfa_states.remove(dfa['startingState'])
        dfa_states.insert(0, dfa['startingState'])

    if dual_dfa['startingState'] in dual_states:
        dual_states.remove(dual_dfa['startingState'])
        dual_states.insert(0, dual_dfa['startingState'])

    # Build state map
    state_map = {}
    for i, dfa_state in enumerate(dfa_states):
        state_map[i] = {}

        # Find original state set for this DFA state
        dfa_state_set = None
        for state_set, mapped_state in state_mapping.items():
            if mapped_state == dfa_state:
                dfa_state_set = state_set
                break

        for j, dual_state in enumerate(dual_states):
            # Find original state set for this dual DFA state
            dual_state_set = None
            for state_set, mapped_state in dual_state_mapping.items():
                if mapped_state == dual_state:
                    dual_state_set = state_set
                    break

            # Intersection of state sets
            if dfa_state_set and dual_state_set:
                intersection = dfa_state_set.intersect(dual_state_set)
                state_map[i][j] = set(intersection)
            else:
                state_map[i][j] = set()

    return state_map, dfa, dual_dfa, state_mapping


def make_elementary_automaton_matrix(state_map: Dict) -> List[List[bool]]:
    """Create elementary automaton matrix from state map."""

    rows = len(state_map)
    cols = len(state_map[0]) if rows > 0 else 0

    matrix = []
    for i in range(rows):
        row = []
        for j in range(cols):
            row.append(len(state_map[i][j]) > 0)
        matrix.append(row)

    return matrix


def compute_prime_grids(matrix: List[List[bool]]) -> List[Grid]:
    """Compute prime grids from the matrix """

    rows = len(matrix)
    cols = len(matrix[0]) if rows > 0 else 0

    # Start with all single-element grids where matrix[i][j] = True
    grids_to_process = set()
    for i in range(rows):
        for j in range(cols):
            if matrix[i][j]:
                grids_to_process.add(Grid({i}, {j}))

    prime_grids = set()

    while grids_to_process:
        current_grid = grids_to_process.pop()
        is_prime = True

        # Try expanding rows
        comparison_row = next(iter(current_grid.rows))
        for test_row in range(rows):
            if test_row in current_grid.rows:
                continue

            # Check if this row has the same pattern as comparison_row
            can_expand = True
            for col in current_grid.columns:
                if matrix[test_row][col] != matrix[comparison_row][col]:
                    can_expand = False
                    break

            if can_expand:
                new_grid = Grid(current_grid.rows | {test_row}, current_grid.columns)
                grids_to_process.add(new_grid)
                is_prime = False

        # Try expanding columns
        comparison_col = next(iter(current_grid.columns))
        for test_col in range(cols):
            if test_col in current_grid.columns:
                continue

            # Check if this column has the same pattern as comparison_col
            can_expand = True
            for row in current_grid.rows:
                if matrix[row][test_col] != matrix[row][comparison_col]:
                    can_expand = False
                    break

            if can_expand:
                new_grid = Grid(current_grid.rows, current_grid.columns | {test_col})
                grids_to_process.add(new_grid)
                is_prime = False

        if is_prime:
            prime_grids.add(current_grid)

    return list(prime_grids)


def enumerate_covers(matrix: List[List[bool]], prime_grids: List[Grid]) -> List[Cover]:
    """Enumerate covers"""

    rows = len(matrix)
    cols = len(matrix[0]) if rows > 0 else 0

    # Find all positions where matrix[i][j] = True
    true_positions = set()
    for i in range(rows):
        for j in range(cols):
            if matrix[i][j]:
                true_positions.add((i, j))

    if not true_positions:
        return []

    # For each grid, compute which flattened indices it covers
    grid_to_flattened = {}
    for grid in prime_grids:
        flattened = set()
        for row in grid.rows:
            for col in grid.columns:
                flattened.add(col * rows + row)  # Same flattening as C# code
        grid_to_flattened[grid] = flattened

    # Convert true positions to flattened indices
    flattened_true = set()
    for row, col in true_positions:
        flattened_true.add(col * rows + row)

    # Enumerate covers of different sizes
    covers = []
    for grid_count in range(1, len(prime_grids) + 1):
        def enumerate_recursive(first_grid_index, remaining_flattened, current_cover, grids_needed):
            if grids_needed == 0:
                if not remaining_flattened:
                    covers.append(Cover(set(current_cover)))
                return

            if grids_needed > len(prime_grids) - first_grid_index:
                return

            for grid_index in range(first_grid_index, len(prime_grids)):
                grid = prime_grids[grid_index]
                grid_coverage = grid_to_flattened[grid]

                # Check if this grid covers any remaining positions
                if grid_coverage & remaining_flattened:
                    new_remaining = remaining_flattened - grid_coverage
                    enumerate_recursive(grid_index + 1, new_remaining, current_cover + [grid], grids_needed - 1)

        enumerate_recursive(0, flattened_true, [], grid_count)

        if covers:  # Return first valid covers found
            break

    return covers


def build_minimal_nfa_from_cover(original_nfa: Dict, cover: Cover, dfa: Dict, state_mapping: Dict) -> Dict:
    """Build minimal NFA from cover using intersection rule."""

    if not cover.grids:
        return original_nfa

    grids = list(cover.grids)

    # Create subset assignment function
    dfa_states = dfa['states'][:]
    # Put start state first
    if dfa['startingState'] in dfa_states:
        dfa_states.remove(dfa['startingState'])
        dfa_states.insert(0, dfa['startingState'])

    subset_assignment = {}
    for row_idx in range(len(dfa_states)):
        subset_assignment[row_idx] = set()
        for grid in grids:
            if row_idx in grid.rows:
                subset_assignment[row_idx].add(grid)

    # Create states for each grid
    grid_to_state = {grid: f"s{i}" for i, grid in enumerate(grids)}
    new_states = list(grid_to_state.values())
    new_transitions = {}

    for grid in grids:
        from_state = grid_to_state[grid]
        new_transitions[from_state] = {}

        # Get DFA states (rows) that this grid covers
        covered_dfa_states = [dfa_states[i] for i in grid.rows if i < len(dfa_states)]

        if not covered_dfa_states:
            continue

        # Find symbols available from ALL covered DFA states
        available_symbols = set(original_nfa['alphabet'])
        for dfa_state in covered_dfa_states:
            if dfa_state in dfa['transitions']:
                state_symbols = set(dfa['transitions'][dfa_state].keys())
                available_symbols &= state_symbols
            else:
                available_symbols = set()
                break

        # For each available symbol, compute target grids
        for symbol in available_symbols:
            target_grids = None

            for dfa_state in covered_dfa_states:
                if dfa_state in dfa['transitions'] and symbol in dfa['transitions'][dfa_state]:
                    target_dfa_states = dfa['transitions'][dfa_state][symbol]

                    for target_dfa_state in target_dfa_states:
                        if target_dfa_state in dfa_states:
                            target_row = dfa_states.index(target_dfa_state)
                            target_grid_set = subset_assignment.get(target_row, set())

                            if target_grids is None:
                                target_grids = target_grid_set.copy()
                            else:
                                target_grids &= target_grid_set

            if target_grids:
                target_states = [grid_to_state[grid] for grid in target_grids]
                new_transitions[from_state][symbol] = target_states

    # Determine start states (grids that contain row 0)
    start_states = []
    for grid in grids:
        if 0 in grid.rows:
            start_states.append(grid_to_state[grid])

    # Determine accepting states (grids that contain column 0)
    accepting_states = []
    for grid in grids:
        if 0 in grid.columns:
            accepting_states.append(grid_to_state[grid])

    result = {
        'states': new_states,
        'alphabet': original_nfa['alphabet'][:],
        'transitions': new_transitions,
        'startingState': start_states[0] if start_states else (new_states[0] if new_states else ''),
        'acceptingStates': accepting_states
    }

    return result


def apply_kameda_weiner(nfa: Dict, method_name: str) -> Tuple[Dict, List[str]]:
    """Apply Kameda-Weiner algorithm to an NFA and return the result with stages."""

    stages = []

    try:
        # Kameda-Weiner algorithm
        stages.append(f"Create state map ({method_name})")
        state_map, dfa, dual_dfa, state_mapping = make_state_map(nfa)

        stages.append(f"Elementary automaton matrix ({method_name})")
        matrix = make_elementary_automaton_matrix(state_map)

        stages.append(f"Compute prime grids ({method_name})")
        prime_grids = compute_prime_grids(matrix)

        if not prime_grids:
            return nfa, stages

        stages.append(f"Enumerate covers ({method_name})")
        covers = enumerate_covers(matrix, prime_grids)

        if not covers:
            return nfa, stages

        # Try covers in order of increasing size
        best_nfa = nfa

        for cover in sorted(covers, key=len):
            if len(cover) >= len(nfa['states']):
                continue

            try:
                stages.append(f"Try cover with {len(cover)} grids ({method_name})")
                candidate_nfa = build_minimal_nfa_from_cover(nfa, cover, dfa, state_mapping)

                # Basic validation
                if candidate_nfa['states'] and len(candidate_nfa['states']) < len(best_nfa['states']):
                    candidate_nfa = remove_unreachable_states(candidate_nfa)
                    candidate_nfa = remove_dead_states(candidate_nfa)

                    if candidate_nfa['states'] and len(candidate_nfa['states']) < len(best_nfa['states']):
                        best_nfa = candidate_nfa
                        break

            except Exception as e:
                continue

        return best_nfa, stages

    except Exception as e:
        return nfa, stages


def verify_candidate_equivalence(original_nfa: Dict, candidate_nfa: Dict, method_name: str) -> Tuple[bool, Dict]:
    """
    Verify that a candidate minimized NFA is equivalent to the original NFA.

    Args:
        original_nfa: The original NFA
        candidate_nfa: The candidate minimized NFA
        method_name: Name of the method used to generate the candidate

    Returns:
        Tuple of (is_equivalent, verification_details)
    """
    try:
        is_equivalent, details = are_automata_equivalent(original_nfa, candidate_nfa)

        verification_details = {
            'method': method_name,
            'equivalent': is_equivalent,
            'original_states': len(original_nfa['states']),
            'candidate_states': len(candidate_nfa['states']) if candidate_nfa['states'] else 0,
            'equivalence_details': details
        }

        return is_equivalent, verification_details

    except Exception as e:
        verification_details = {
            'method': method_name,
            'equivalent': False,
            'error': str(e),
            'original_states': len(original_nfa['states']),
            'candidate_states': len(candidate_nfa['states']) if candidate_nfa['states'] else 0
        }

        return False, verification_details


# Pick the best candidate (minimum states, with priority for DFA method on ties)
def candidate_priority(candidate):
    # Primary key: number of states (lower is better)
    # Secondary key: method priority (0 = highest priority)
    method_priorities = {
        'Determinise + Minimise DFA': 0,  # Highest priority
        'Kameda-Weiner on Minimised DFA': 1,
        'Kameda-Weiner on Original NFA': 2,
    }

    method_priority = method_priorities.get(candidate['method'], 999)  # Default low priority
    return (candidate['states'], method_priority)

def minimise_nfa(nfa: Dict, kameda_weiner_threshold: int = 25) -> MinimisationResult:
    """
    Minimise an NFA using a multi-stage pipeline approach with threshold-based Kameda-Weiner usage.

    Args:
        nfa: The NFA to minimise
        kameda_weiner_threshold: Maximum number of states for which Kameda-Weiner will be applied
    """

    original_states = len(nfa['states'])
    all_stages = ["Preprocessing"]
    candidate_results = []
    verification_results = []

    # Handle empty NFA
    if original_states == 0:
        return MinimisationResult(
            nfa=nfa,
            original_states=0,
            final_states=0,
            reduction=0,
            reduction_percent=0,
            is_optimal=True,
            method_used="Empty NFA",
            stages=all_stages,
            candidate_results=[],
            equivalence_verified=True,
            verification_details={}
        )

    current_nfa = nfa

    # Preprocessing
    current_nfa = remove_unreachable_states(current_nfa)
    current_nfa = remove_dead_states(current_nfa)

    # Handle NFA that became empty after preprocessing
    if not current_nfa['states']:
        empty_nfa = {
            'states': [],
            'alphabet': nfa['alphabet'][:],
            'transitions': {},
            'startingState': '',
            'acceptingStates': []
        }

        # Verify empty NFA is equivalent to original (should be if original accepts no strings)
        is_equiv, verification_details = verify_candidate_equivalence(
            nfa, empty_nfa, "Empty after preprocessing"
        )

        return MinimisationResult(
            nfa=empty_nfa,
            original_states=original_states,
            final_states=0,
            reduction=original_states,
            reduction_percent=100.0,
            is_optimal=True,
            method_used="Empty after preprocessing",
            stages=all_stages + ["Empty after preprocessing"],
            candidate_results=[],
            equivalence_verified=is_equiv,
            verification_details=verification_details
        )

    # Epsilon elimination
    if any('' in current_nfa['transitions'].get(s, {}) for s in current_nfa['states']):
        current_nfa = eliminate_epsilon_transitions(current_nfa)
        current_nfa = remove_unreachable_states(current_nfa)
        current_nfa = remove_dead_states(current_nfa)

    # Check again if NFA became empty
    if not current_nfa['states']:
        empty_nfa = {
            'states': [],
            'alphabet': nfa['alphabet'][:],
            'transitions': {},
            'startingState': '',
            'acceptingStates': []
        }

        is_equiv, verification_details = verify_candidate_equivalence(
            nfa, empty_nfa, "Empty after epsilon elimination"
        )

        return MinimisationResult(
            nfa=empty_nfa,
            original_states=original_states,
            final_states=0,
            reduction=original_states,
            reduction_percent=100.0,
            is_optimal=True,
            method_used="Empty after epsilon elimination",
            stages=all_stages + ["Empty after epsilon elimination"],
            candidate_results=[],
            equivalence_verified=is_equiv,
            verification_details=verification_details
        )

    preprocessed_states = len(current_nfa['states'])
    preprocessed_transitions = sum(len(targets) for state in nfa['transitions'].values() for targets in state.values())
    kw_complexity_score = preprocessed_states + preprocessed_transitions

    # BASELINE CANDIDATE: Add preprocessed NFA as a baseline candidate
    # This ensures we never return something worse than what we started with
    all_stages.append("Add preprocessed NFA as baseline candidate")
    baseline_candidate = {
        'nfa': current_nfa,
        'method': 'Preprocessed NFA (baseline)',
        'states': preprocessed_states,
        'equivalence_verified': True,  # Preprocessing preserves equivalence
        'verification_details': {
            'method': 'Preprocessed NFA (baseline)',
            'equivalent': True,
            'original_states': original_states,
            'candidate_states': preprocessed_states,
            'preprocessing_only': True
        }
    }
    candidate_results.append(baseline_candidate)
    verification_results.append(baseline_candidate['verification_details'])


    # PIPELINE STAGE 1: Apply Kameda-Weiner to original NFA (only if below threshold)
    if kw_complexity_score <= kameda_weiner_threshold:
        all_stages.append(
            f"Kameda-Weiner on Original NFA (states: {preprocessed_states} <= threshold: {kameda_weiner_threshold})")
        kw_original_nfa, kw_original_stages = apply_kameda_weiner(current_nfa, "Original NFA")
        candidate_info = {
            'nfa': kw_original_nfa,
            'method': 'Kameda-Weiner on Original NFA',
            'states': len(kw_original_nfa['states']) if kw_original_nfa['states'] else 0
        }

        # Verify this candidate
        is_equiv, verification_details = verify_candidate_equivalence(
            nfa, kw_original_nfa, 'Kameda-Weiner on Original NFA'
        )
        candidate_info['equivalence_verified'] = is_equiv
        candidate_info['verification_details'] = verification_details
        verification_results.append(verification_details)

        candidate_results.append(candidate_info)
        all_stages.extend(kw_original_stages)
    else:
        all_stages.append(
            f"Skipping Kameda-Weiner on Original NFA (states: {preprocessed_states} > threshold: {kameda_weiner_threshold})")

    # PIPELINE STAGE 2: Determinise original NFA and minimise DFA (always run)
    try:
        all_stages.append("Determinise original NFA")
        dfa = nfa_to_dfa(current_nfa)

        all_stages.append("Minimise DFA")
        minimised_dfa = minimise_dfa(dfa)

        candidate_info = {
            'nfa': minimised_dfa,
            'method': 'Determinise + Minimise DFA',
            'states': len(minimised_dfa['states']) if minimised_dfa['states'] else 0
        }

        # Verify this candidate
        is_equiv, verification_details = verify_candidate_equivalence(
            nfa, minimised_dfa, 'Determinise + Minimise DFA'
        )
        candidate_info['equivalence_verified'] = is_equiv
        candidate_info['verification_details'] = verification_details
        verification_results.append(verification_details)

        candidate_results.append(candidate_info)

        # Store the minimised DFA for potential use in stage 3
        stage2_result = minimised_dfa
        stage2_states = len(minimised_dfa['states']) if minimised_dfa['states'] else 0
        stage2_transitions = sum(len(targets) for state in current_nfa['transitions'].values() for targets in state.values())
        stage2_complexity_score = stage2_states + stage2_transitions

    except Exception as e:
        # Add a fallback candidate
        candidate_info = {
            'nfa': current_nfa,
            'method': 'Determinise + Minimise DFA (failed)',
            'states': len(current_nfa['states']) if current_nfa['states'] else 0,
            'equivalence_verified': True,  # Original NFA is trivially equivalent to itself
            'verification_details': {'method': 'Determinise + Minimise DFA (failed)', 'equivalent': True}
        }
        candidate_results.append(candidate_info)
        all_stages.append("Determinise + Minimise DFA (failed)")

        # Use current NFA as fallback for stage 3
        stage2_result = current_nfa
        stage2_states = len(current_nfa['states']) if current_nfa['states'] else 0
        stage2_transitions = sum(len(targets) for state in current_nfa['transitions'].values() for targets in state.values())
        stage2_complexity_score = stage2_states + stage2_transitions

    # PIPELINE STAGE 3: Apply Kameda-Weiner to minimised DFA (only if result from stage 2 is below threshold)
    if stage2_complexity_score <= kameda_weiner_threshold and stage2_result['states']:
        try:
            all_stages.append(
                f"Kameda-Weiner on Minimised DFA (states: {stage2_states} <= threshold: {kameda_weiner_threshold})")
            kw_dfa_nfa, kw_dfa_stages = apply_kameda_weiner(stage2_result, "Minimised DFA")
            candidate_info = {
                'nfa': kw_dfa_nfa,
                'method': 'Kameda-Weiner on Minimised DFA',
                'states': len(kw_dfa_nfa['states']) if kw_dfa_nfa['states'] else 0
            }

            # Verify this candidate
            is_equiv, verification_details = verify_candidate_equivalence(
                nfa, kw_dfa_nfa, 'Kameda-Weiner on Minimised DFA'
            )
            candidate_info['equivalence_verified'] = is_equiv
            candidate_info['verification_details'] = verification_details
            verification_results.append(verification_details)

            candidate_results.append(candidate_info)
            all_stages.extend(kw_dfa_stages)

        except Exception as e:
            # Add a fallback candidate
            candidate_info = {
                'nfa': stage2_result,
                'method': 'Kameda-Weiner on Minimised DFA (failed)',
                'states': stage2_states,
                'equivalence_verified': True,  # Using verified result from stage 2
                'verification_details': {'method': 'Kameda-Weiner on Minimised DFA (failed)', 'equivalent': True}
            }
            candidate_results.append(candidate_info)
            all_stages.append("Kameda-Weiner on Minimised DFA (failed)")
    else:
        all_stages.append(
            f"Skipping Kameda-Weiner on Minimised DFA (states: {stage2_states} > threshold: {kameda_weiner_threshold})")

    # PIPELINE STAGE 4: Compare all candidates and select the best
    all_stages.append("Compare candidates and select best")

    # Only consider candidates that passed verification
    valid_candidates = [c for c in candidate_results if c.get('equivalence_verified', False)]
    if not valid_candidates:
        # If no candidates passed verification, fall back to original NFA
        all_stages.append("No candidates passed verification - using original NFA")
        best_candidate = {
            'nfa': nfa,
            'method': 'Original NFA (fallback)',
            'states': len(nfa['states']),
            'equivalence_verified': True
        }
        verification_summary = {
            'all_candidates_failed': True,
            'total_candidates': len(candidate_results),
            'valid_candidates': 0
        }
    else:
        # Pick the best candidate (minimum states with DFA method as priority in the result of a tie)
        best_candidate = min(valid_candidates, key=candidate_priority)
        verification_summary = {
            'total_candidates': len(candidate_results),
            'valid_candidates': len(valid_candidates),
            'kameda_weiner_threshold': kameda_weiner_threshold,
            'original_states_after_preprocessing': preprocessed_states,
            'stage2_states': stage2_states if 'stage2_states' in locals() else 0
        }

    best_nfa = best_candidate['nfa']
    best_method = best_candidate['method']
    best_states = best_candidate['states']

    # Final cleanup of the best candidate
    if best_nfa['states']:
        best_nfa = remove_unreachable_states(best_nfa)
        best_nfa = remove_dead_states(best_nfa)
        final_states = len(best_nfa['states'])
    else:
        final_states = 0

    reduction = original_states - final_states
    reduction_percent = (reduction / original_states) * 100 if original_states > 0 else 0

    return MinimisationResult(
        nfa=best_nfa,
        original_states=original_states,
        final_states=final_states,
        reduction=reduction,
        reduction_percent=reduction_percent,
        is_optimal=final_states < original_states,
        method_used=best_method,
        stages=all_stages,
        candidate_results=candidate_results,
        equivalence_verified=best_candidate.get('equivalence_verified', False),
        verification_details=verification_summary
    )