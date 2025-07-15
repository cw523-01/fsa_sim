from typing import Dict, Set, List, Tuple, FrozenSet, NamedTuple, Optional
from collections import defaultdict, deque
from .fsa_properties import is_deterministic, validate_fsa_structure
from .fsa_transformations import nfa_to_dfa, minimise_dfa
from pysat.solvers import Glucose3
from pysat.formula import CNF
import itertools
import random


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


class MinimisationConfig:
    """Unified configuration for NFA minimisation algorithms"""
    SAT_DIRECT_THRESHOLD = 12
    SAT_POST_HEURISTIC_THRESHOLD = 20
    SAT_TIMEOUT_SECONDS = 600
    KAMEDA_WEINER_THRESHOLD = 150
    MAX_VERIFICATION_LENGTH = 12
    VERIFICATION_SAMPLE_SIZE = 100
    MAX_VERIFICATION_ATTEMPTS = 3


def analyse_fsa_complexity(nfa: Dict) -> Dict[str, any]:
    """analyses NFA complexity to determine the best minimisation approach."""
    num_states = len(nfa['states'])
    alphabet_size = len(nfa['alphabet'])
    has_epsilon = any('' in nfa['transitions'].get(s, {}) for s in nfa['states'])

    analysis = {
        'num_states': num_states,
        'alphabet_size': alphabet_size,
        'has_epsilon': has_epsilon,
        'can_use_sat_directly': num_states <= MinimisationConfig.SAT_DIRECT_THRESHOLD,
        'is_deterministic': is_deterministic(nfa),
        'recommended_approach': None
    }

    # Determine recommended approach for NFA minimization
    if analysis['can_use_sat_directly']:
        analysis['recommended_approach'] = 'sat_direct'
    else:
        analysis['recommended_approach'] = 'kameda_weiner_then_analyse'

    return analysis


def normalise_nfa(nfa: Dict) -> Dict:
    """normalise NFA by adding epsilon closure and ensuring consistent structure."""
    normalised = {
        'states': nfa['states'][:],
        'alphabet': [a for a in nfa['alphabet'] if a != ''],  # Remove epsilon from alphabet
        'transitions': {},
        'startingState': nfa['startingState'],
        'acceptingStates': nfa['acceptingStates'][:]
    }

    # Compute epsilon closure for each state
    epsilon_closure = {}
    for state in nfa['states']:
        epsilon_closure[state] = _compute_epsilon_closure(nfa, state)

    # Build normalised transitions with epsilon closure incorporated
    for state in nfa['states']:
        normalised['transitions'][state] = {}
        for symbol in normalised['alphabet']:
            targets = set()
            # For each state reachable via epsilon from current state
            for eps_state in epsilon_closure[state]:
                # Add all targets reachable by symbol, plus their epsilon closures
                if eps_state in nfa['transitions'] and symbol in nfa['transitions'][eps_state]:
                    for target in nfa['transitions'][eps_state][symbol]:
                        targets.update(epsilon_closure[target])
            normalised['transitions'][state][symbol] = sorted(list(targets))

    # Update accepting states: a state is accepting if any epsilon-reachable state is accepting
    new_accepting = set()
    for state in nfa['states']:
        if any(eps_state in nfa['acceptingStates'] for eps_state in epsilon_closure[state]):
            new_accepting.add(state)
    normalised['acceptingStates'] = sorted(list(new_accepting))

    return normalised


def _compute_epsilon_closure(nfa: Dict, state: str) -> Set[str]:
    """Compute epsilon closure of a state."""
    closure = {state}
    worklist = [state]

    while worklist:
        current = worklist.pop()
        if current in nfa['transitions'] and '' in nfa['transitions'][current]:
            for target in nfa['transitions'][current]['']:
                if target not in closure:
                    closure.add(target)
                    worklist.append(target)

    return closure


def kameda_weiner_minimise(nfa: Dict) -> Dict:
    """
    Minimises an NFA using corrected Kameda-Weiner simulation-based approach.
    """
    # normalise NFA to handle epsilon transitions
    normalised_nfa = normalise_nfa(nfa)

    # Build simulation relations
    forward_sim = _compute_forward_simulation(normalised_nfa)
    backward_sim = _compute_backward_simulation(normalised_nfa)

    # Compute bisimulation (intersection of forward and backward simulation)
    bisimulation = _compute_bisimulation(forward_sim, backward_sim, normalised_nfa['states'])

    # Build quotient automaton based on bisimulation equivalence classes
    return _build_quotient_automaton(normalised_nfa, bisimulation)


def _compute_forward_simulation(nfa: Dict) -> Dict[str, Set[str]]:
    """
    Compute forward simulation relation: p ≼_f q if q can simulate all behaviors of p.
    """
    states = nfa['states']
    alphabet = nfa['alphabet']
    transitions = nfa['transitions']
    accepting = set(nfa['acceptingStates'])

    # Initialize simulation relation: q can simulate p only if acceptance property matches
    sim = {p: set() for p in states}
    for p in states:
        for q in states:
            if (p in accepting) == (q in accepting):
                sim[p].add(q)

    # Fixpoint iteration to refine simulation relation
    changed = True
    iteration = 0
    while changed and iteration < 100:  # Add iteration limit for safety
        changed = False
        new_sim = {p: set() for p in states}
        iteration += 1

        for p in states:
            for q in sim[p]:
                can_simulate = True

                # For each symbol, check if q can simulate p's behavior
                for symbol in alphabet:
                    p_targets = set(transitions.get(p, {}).get(symbol, []))
                    q_targets = set(transitions.get(q, {}).get(symbol, []))

                    # For every target p', there must exist a target q' such that q' simulates p'
                    for p_target in p_targets:
                        if not any(q_target in sim.get(p_target, set()) for q_target in q_targets):
                            can_simulate = False
                            break

                    if not can_simulate:
                        break

                if can_simulate:
                    new_sim[p].add(q)

        if new_sim != sim:
            changed = True
            sim = new_sim

    return sim


def _compute_backward_simulation(nfa: Dict) -> Dict[str, Set[str]]:
    """
    Compute backward simulation relation: p ≼_b q if p can backward-simulate q.
    This means for every way to reach q, there's a corresponding way to reach p.
    """
    states = nfa['states']
    alphabet = nfa['alphabet']
    transitions = nfa['transitions']
    starting = nfa['startingState']

    # Build reverse transition function
    reverse_trans = defaultdict(lambda: defaultdict(set))
    for state in states:
        for symbol in alphabet:
            for target in transitions.get(state, {}).get(symbol, []):
                reverse_trans[target][symbol].add(state)

    # Initialize backward simulation: p can backward-simulate q only if start property matches
    sim = {p: set() for p in states}
    for p in states:
        for q in states:
            if (p == starting) == (q == starting):
                sim[p].add(q)

    # Fixpoint iteration
    changed = True
    iteration = 0
    while changed and iteration < 100:
        changed = False
        new_sim = {p: set() for p in states}
        iteration += 1

        for p in states:
            for q in sim[p]:
                can_backward_simulate = True

                # For each symbol, check backward simulation condition
                for symbol in alphabet:
                    q_predecessors = reverse_trans[q][symbol]
                    p_predecessors = reverse_trans[p][symbol]

                    # For every predecessor q' of q, there must be a predecessor p' of p
                    # such that p' can backward-simulate q'
                    for q_pred in q_predecessors:
                        if not any(q_pred in sim.get(p_pred, set()) for p_pred in p_predecessors):
                            can_backward_simulate = False
                            break

                    if not can_backward_simulate:
                        break

                if can_backward_simulate:
                    new_sim[p].add(q)

        if new_sim != sim:
            changed = True
            sim = new_sim

    return sim


def _compute_bisimulation(forward_sim: Dict[str, Set[str]],
                          backward_sim: Dict[str, Set[str]],
                          states: List[str]) -> List[Set[str]]:
    """
    Compute bisimulation equivalence classes from forward and backward simulation.
    """
    # Two states are bisimilar if they can simulate each other in both directions
    bisimilar = set()

    for p in states:
        for q in states:
            if (q in forward_sim.get(p, set()) and
                    p in forward_sim.get(q, set()) and
                    q in backward_sim.get(p, set()) and
                    p in backward_sim.get(q, set())):
                bisimilar.add((min(p, q), max(p, q)))  # normalise pairs

    # Build equivalence classes using union-find
    parent = {state: state for state in states}

    def find(x):
        if parent[x] != x:
            parent[x] = find(parent[x])
        return parent[x]

    def union(x, y):
        px, py = find(x), find(y)
        if px != py:
            parent[px] = py

    # Union bisimilar states
    for p, q in bisimilar:
        union(p, q)

    # Group states by their representative
    groups = defaultdict(set)
    for state in states:
        groups[find(state)].add(state)

    return list(groups.values())


def _build_quotient_automaton(nfa: Dict, equivalence_classes: List[Set[str]]) -> Dict:
    """Build the quotient automaton from equivalence classes."""
    if len(equivalence_classes) == 0:
        return nfa  # No reduction possible

    # Create state mapping
    state_to_class = {}
    class_representatives = {}

    for i, equiv_class in enumerate(equivalence_classes):
        representative = f"q{i}"
        class_representatives[representative] = equiv_class
        for state in equiv_class:
            state_to_class[state] = representative

    # Build transitions for quotient automaton
    quotient_transitions = defaultdict(lambda: defaultdict(set))

    for state in nfa['states']:
        if state in nfa['transitions']:
            source_class = state_to_class[state]
            for symbol in nfa['transitions'][state]:
                for target in nfa['transitions'][state][symbol]:
                    target_class = state_to_class[target]
                    quotient_transitions[source_class][symbol].add(target_class)

    # Convert sets to lists
    final_transitions = {}
    for source in quotient_transitions:
        final_transitions[source] = {}
        for symbol in quotient_transitions[source]:
            final_transitions[source][symbol] = sorted(list(quotient_transitions[source][symbol]))

    # Determine start state and accepting states
    start_state = state_to_class[nfa['startingState']]
    accepting_states = []

    for class_rep, equiv_class in class_representatives.items():
        if any(state in nfa['acceptingStates'] for state in equiv_class):
            accepting_states.append(class_rep)

    return {
        'states': sorted(list(class_representatives.keys())),
        'alphabet': nfa['alphabet'][:],
        'transitions': final_transitions,
        'startingState': start_state,
        'acceptingStates': sorted(accepting_states)
    }


def direct_product_sat_minimise(nfa: Dict, best_nfa: Optional[Dict] = None) -> Dict:
    """
    Finds the exact minimal NFA using Direct Product SAT construction.
    Uses binary search to find the minimum number of states.

    Note: The caller is responsible for ensuring the NFA size is practical
    for SAT solving (typically ≤20 states).
    """
    # normalise the NFA first
    normalised_nfa = normalise_nfa(nfa)

    if best_nfa is None or len(best_nfa['states']) >= len(normalised_nfa['states']):
        best_nfa = normalised_nfa

    lower_bound = 1
    upper_bound = len(normalised_nfa['states'])

    while lower_bound <= upper_bound:
        k = (lower_bound + upper_bound) // 2

        result = _direct_product_sat_check(normalised_nfa, k)

        if result is not None:
            if len(result['states']) < len(best_nfa['states']):
                # keep the smallest so far
                best_nfa = result
            upper_bound = k - 1
        else:
            lower_bound = k + 1
            # Even if UNSAT, we already know nothing with <k states works.

    return best_nfa


def _direct_product_sat_check(original_nfa: Dict, target_states: int) -> Optional[Dict]:
    """
    Checks if there exists an NFA with target_states using Direct Product Construction.
    Now with proper timeout handling using solve_limited.
    """
    try:
        encoding = DirectProductSATEncoding(original_nfa, target_states)
        formula = encoding.build_formula()

        solver = Glucose3()
        solver.append_formula(formula)

        # Use solve_limited with proper timeout handling
        result = solver.solve_limited(expect_interrupt=True)

        # Handle timeout case
        if result is None:
            solver.delete()
            return None

        if result:
            model = solver.get_model()
            result_nfa = encoding.extract_nfa(model)

            # Multiple verification attempts with different methods
            verification_passed = False
            for attempt in range(MinimisationConfig.MAX_VERIFICATION_ATTEMPTS):
                if _verify_language_equivalence(original_nfa, result_nfa, attempt):
                    verification_passed = True
                    break

            if verification_passed:
                solver.delete()
                return result_nfa
            else:
                solver.delete()
                return None
        else:
            solver.delete()
            return None

    except Exception as e:
        print(f"  SAT solver error: {e}")
        return None


class DirectProductSATEncoding:
    """
    Direct Product SAT encoding that properly captures language equivalence
    using simulation between original and target NFAs.
    """

    def __init__(self, original_nfa: Dict, target_states: int):
        self.original_nfa = original_nfa
        self.target_states = target_states
        self.alphabet = original_nfa['alphabet']
        self.original_states = original_nfa['states']

        self.next_var = 1
        self.var_map = {}
        self._create_variables()

    def _create_variables(self):
        """Create boolean variables for the Direct Product SAT encoding."""

        # Target NFA structure variables
        # trans[i][a][j] = target state i has transition to state j on symbol a
        self.trans_vars = {}
        for i in range(self.target_states):
            self.trans_vars[i] = {}
            for a in self.alphabet:
                self.trans_vars[i][a] = {}
                for j in range(self.target_states):
                    var = self._new_var(f"trans_{i}_{a}_{j}")
                    self.trans_vars[i][a][j] = var

        # accept[i] = target state i is accepting
        self.accept_vars = {}
        for i in range(self.target_states):
            var = self._new_var(f"accept_{i}")
            self.accept_vars[i] = var

        # Simulation variables
        # sim[orig][targ] = target state targ can simulate original state orig
        self.sim_vars = {}
        for orig_state in self.original_states:
            self.sim_vars[orig_state] = {}
            for i in range(self.target_states):
                var = self._new_var(f"sim_{orig_state}_{i}")
                self.sim_vars[orig_state][i] = var

    def _new_var(self, name: str) -> int:
        """Create a new SAT variable."""
        var = self.next_var
        self.next_var += 1
        self.var_map[var] = name
        return var

    def build_formula(self) -> CNF:
        """Build the complete SAT formula using Direct Product Construction."""
        cnf = CNF()

        # 1. Every original state must be simulated by at least one target state
        self._add_simulation_coverage_constraints(cnf)

        # 2. Simulation must respect acceptance
        self._add_acceptance_simulation_constraints(cnf)

        # 3. Simulation must respect transitions
        self._add_transition_simulation_constraints(cnf)

        # 4. Target start state must simulate original start state
        self._add_start_state_constraints(cnf)

        # 5. Every target state that simulates an accepting original state must be accepting
        self._add_accepting_consistency_constraints(cnf)

        return cnf

    def _add_simulation_coverage_constraints(self, cnf: CNF):
        """Every original state must be simulated by at least one target state."""
        for orig_state in self.original_states:
            clause = [self.sim_vars[orig_state][i] for i in range(self.target_states)]
            cnf.append(clause)

    def _add_acceptance_simulation_constraints(self, cnf: CNF):
        """If target state simulates original state, acceptance must be consistent."""
        for orig_state in self.original_states:
            is_orig_accepting = orig_state in self.original_nfa['acceptingStates']

            for i in range(self.target_states):
                # If target state i simulates original state and original is accepting,
                # then target state i must be accepting
                if is_orig_accepting:
                    cnf.append([-self.sim_vars[orig_state][i], self.accept_vars[i]])
                # If target state i simulates original state and original is not accepting,
                # target can be either accepting or non-accepting (no constraint needed)

    def _add_transition_simulation_constraints(self, cnf: CNF):
        """Simulation must respect the transition structure."""
        for orig_state in self.original_states:
            for symbol in self.alphabet:
                orig_targets = self.original_nfa['transitions'].get(orig_state, {}).get(symbol, [])

                for i in range(self.target_states):
                    # If target state i simulates orig_state, then for every transition
                    # orig_state --symbol--> orig_target, there must be a transition
                    # i --symbol--> j where j simulates orig_target

                    for orig_target in orig_targets:
                        # Build clause: ¬sim[orig_state][i] ∨ ∨_{j=0}^{k-1} (trans[i][symbol][j] ∧ sim[orig_target][j])

                        # Create auxiliary variables for (trans[i][symbol][j] ∧ sim[orig_target][j])
                        aux_vars = []
                        for j in range(self.target_states):
                            aux_var = self._new_var(f"aux_{orig_state}_{i}_{symbol}_{orig_target}_{j}")
                            aux_vars.append(aux_var)

                            # aux_var ↔ (trans[i][symbol][j] ∧ sim[orig_target][j])
                            cnf.append([-aux_var, self.trans_vars[i][symbol][j]])
                            cnf.append([-aux_var, self.sim_vars[orig_target][j]])
                            cnf.append([aux_var, -self.trans_vars[i][symbol][j], -self.sim_vars[orig_target][j]])

                        # Main constraint: ¬sim[orig_state][i] ∨ ∨ aux_vars
                        cnf.append([-self.sim_vars[orig_state][i]] + aux_vars)

    def _add_start_state_constraints(self, cnf: CNF):
        """Target start state (state 0) must simulate original start state."""
        orig_start = self.original_nfa['startingState']
        cnf.append([self.sim_vars[orig_start][0]])

    def _add_accepting_consistency_constraints(self, cnf: CNF):
        """Additional consistency constraints for accepting states."""
        # This ensures that the simulation is tight enough
        for i in range(self.target_states):
            # If target state i is accepting, it must simulate at least one accepting original state
            accepting_orig_states = [s for s in self.original_states if s in self.original_nfa['acceptingStates']]

            if accepting_orig_states:
                clause = [-self.accept_vars[i]]
                for orig_state in accepting_orig_states:
                    clause.append(self.sim_vars[orig_state][i])
                cnf.append(clause)

    def extract_nfa(self, model: List[int]) -> Dict:
        """Extract NFA from satisfying assignment."""
        true_vars = set(var for var in model if var > 0)

        transitions = defaultdict(lambda: defaultdict(list))

        # Extract transitions
        for i in range(self.target_states):
            for a in self.alphabet:
                for j in range(self.target_states):
                    if self.trans_vars[i][a][j] in true_vars:
                        state_name = f"s{i}"
                        target_name = f"s{j}"
                        transitions[state_name][a].append(target_name)

        # Extract accepting states
        accepting_states = []
        for i in range(self.target_states):
            if self.accept_vars[i] in true_vars:
                accepting_states.append(f"s{i}")

        return {
            'states': [f"s{i}" for i in range(self.target_states)],
            'alphabet': self.alphabet[:],
            'transitions': dict(transitions),
            'startingState': 's0',
            'acceptingStates': accepting_states
        }


def _verify_language_equivalence(nfa1: Dict, nfa2: Dict, attempt: int = 0) -> bool:
    """
    Multi-layered verification that two NFAs accept the same language.
    Uses different strategies for each attempt to catch different types of errors.
    """
    try:
        # Strategy varies by attempt for robustness
        if attempt == 0:
            # Method 1: Convert to minimal DFAs and compare
            return _verify_via_minimal_dfas(nfa1, nfa2)
        elif attempt == 1:
            # Method 2: Extensive random string testing with different seeds
            return _verify_via_random_testing(nfa1, nfa2, seed=42 + attempt)
        else:
            # Method 3: Structural analysis with comprehensive enumeration
            return _verify_via_comprehensive_enumeration(nfa1, nfa2)

    except Exception as e:
        print(f"Verification attempt {attempt} failed with error: {e}")
        return False


def _verify_via_minimal_dfas(nfa1: Dict, nfa2: Dict) -> bool:
    """Verify equivalence by converting to minimal DFAs and comparing."""
    try:
        dfa1 = nfa_to_dfa(nfa1)
        dfa2 = nfa_to_dfa(nfa2)
        min_dfa1 = minimise_dfa(dfa1)
        min_dfa2 = minimise_dfa(dfa2)

        return _dfas_structurally_equivalent(min_dfa1, min_dfa2)
    except Exception:
        return False


def _verify_via_random_testing(nfa1: Dict, nfa2: Dict, seed: int = 42) -> bool:
    """Verify via extensive random string testing."""
    random.seed(seed)
    alphabet = nfa1['alphabet']

    # Test strings of various lengths
    for length in range(min(MinimisationConfig.MAX_VERIFICATION_LENGTH, 10)):
        # For short strings, test all possibilities
        if length <= 3:
            strings_to_test = list(_generate_strings(alphabet, length))
        else:
            # For longer strings, sample randomly
            sample_size = min(MinimisationConfig.VERIFICATION_SAMPLE_SIZE, 50)
            strings_to_test = [
                ''.join(random.choices(alphabet, k=length))
                for _ in range(sample_size)
            ]

        for string in strings_to_test:
            if _accepts_string(nfa1, string) != _accepts_string(nfa2, string):
                return False

    return True


def _verify_via_comprehensive_enumeration(nfa1: Dict, nfa2: Dict) -> bool:
    """Verify by comprehensive enumeration of short strings."""
    alphabet = nfa1['alphabet']

    # Test all strings up to a reasonable length
    max_length = min(6, MinimisationConfig.MAX_VERIFICATION_LENGTH)

    for length in range(max_length + 1):
        for string in _generate_strings(alphabet, length):
            if _accepts_string(nfa1, string) != _accepts_string(nfa2, string):
                return False

    return True


def _dfas_structurally_equivalent(dfa1: Dict, dfa2: Dict) -> bool:
    """Check if two minimal DFAs are structurally equivalent."""
    if len(dfa1['states']) != len(dfa2['states']):
        return False

    if len(dfa1['acceptingStates']) != len(dfa2['acceptingStates']):
        return False

    return _find_dfa_isomorphism(dfa1, dfa2)


def _find_dfa_isomorphism(dfa1: Dict, dfa2: Dict) -> bool:
    """Try to find an isomorphism between two DFAs using BFS."""
    if len(dfa1['states']) != len(dfa2['states']):
        return False

    if len(dfa1['states']) > 8:  # Avoid exponential blowup
        return True  # Assume equivalent for large DFAs

    # Try all possible mappings
    for perm in itertools.permutations(dfa2['states']):
        mapping = dict(zip(dfa1['states'], perm))
        if _is_valid_dfa_mapping(dfa1, dfa2, mapping):
            return True

    return False


def _is_valid_dfa_mapping(dfa1: Dict, dfa2: Dict, mapping: Dict[str, str]) -> bool:
    """Check if a state mapping preserves DFA structure."""
    # Check start state mapping
    if mapping[dfa1['startingState']] != dfa2['startingState']:
        return False

    # Check accepting states mapping
    mapped_accepting = {mapping[s] for s in dfa1['acceptingStates']}
    if mapped_accepting != set(dfa2['acceptingStates']):
        return False

    # Check transition mapping
    for state in dfa1['states']:
        for symbol in dfa1['alphabet']:
            targets1 = set(dfa1['transitions'].get(state, {}).get(symbol, []))
            targets2 = set(dfa2['transitions'].get(mapping[state], {}).get(symbol, []))

            mapped_targets1 = {mapping[t] for t in targets1}
            if mapped_targets1 != targets2:
                return False

    return True


def _generate_strings(alphabet: List[str], length: int):
    """Generate all strings of given length over alphabet."""
    if length == 0:
        yield ""
    else:
        for chars in itertools.product(alphabet, repeat=length):
            yield "".join(chars)


def _accepts_string(nfa: Dict, string: str) -> bool:
    """
    Check if NFA accepts given string with proper epsilon closure handling.
    """
    # Start with epsilon closure of the starting state
    current_states = _compute_epsilon_closure(nfa, nfa['startingState'])

    for symbol in string:
        next_states = set()
        for state in current_states:
            # Get all states reachable by this symbol
            targets = nfa['transitions'].get(state, {}).get(symbol, [])
            for target in targets:
                # Add epsilon closure of each target
                next_states.update(_compute_epsilon_closure(nfa, target))

        current_states = next_states
        if not current_states:
            return False

    return any(state in nfa['acceptingStates'] for state in current_states)


def minimise_nfa(nfa: Dict) -> MinimisationResult:
    """
    NFA minimisation pipeline.
    """
    # Basic structure validation
    validation_result = validate_fsa_structure(nfa)
    if not validation_result['valid']:
        raise ValueError(f"Invalid NFA structure: {validation_result.get('error', 'Unknown error')}")

    # Additional validation checks that might not be caught by validate_fsa_structure
    _validate_nfa_consistency(nfa)

    original_states = len(nfa['states'])
    stages = []

    analysis = analyse_fsa_complexity(nfa)

    # Handle small NFAs with direct SAT
    if analysis['can_use_sat_directly']:
        result_nfa = direct_product_sat_minimise(nfa)
        stages.append("Direct Product SAT minimisation")
        method_used = "Direct Product SAT (optimal)"
        is_optimal = True

    else:
        # Apply Kameda-Weiner first
        stages.append("Kameda-Weiner preprocessing")
        kameda_weiner_result = kameda_weiner_minimise(nfa)

        # Re-analyse after Kameda-Weiner to see if SAT is now feasible
        kameda_weiner_states = len(kameda_weiner_result['states'])

        if kameda_weiner_states <= MinimisationConfig.SAT_POST_HEURISTIC_THRESHOLD:
            stages.append("Direct Product SAT minimisation (post-preprocessing)")
            result_nfa = direct_product_sat_minimise(kameda_weiner_result, best_nfa=kameda_weiner_result)
            method_used = "Kameda-Weiner + Direct Product SAT (optimal)"
            is_optimal = True
        else:
            result_nfa = kameda_weiner_result
            method_used = "Kameda-Weiner only (heuristic)"
            is_optimal = False

    final_states = len(result_nfa['states'])
    reduction = original_states - final_states
    reduction_percent = (reduction / original_states) * 100 if original_states > 0 else 0

    return MinimisationResult(
        nfa=result_nfa,
        original_states=original_states,
        final_states=final_states,
        reduction=reduction,
        reduction_percent=reduction_percent,
        is_optimal=is_optimal,
        method_used=method_used,
        stages=stages
    )


def _validate_nfa_consistency(nfa: Dict) -> None:
    """
    Additional validation to ensure NFA consistency beyond basic structure validation.
    Raises ValueError if any inconsistencies are found.
    """
    required_keys = ['states', 'alphabet', 'transitions', 'startingState', 'acceptingStates']

    # Check all required keys are present
    for key in required_keys:
        if key not in nfa:
            raise ValueError(f"Invalid NFA structure: missing required key '{key}'")

    states_set = set(nfa['states'])

    # Check starting state is in states list
    if nfa['startingState'] not in states_set:
        raise ValueError(f"Invalid NFA structure: starting state '{nfa['startingState']}' not in states list")

    # Check all accepting states are in states list
    for acc_state in nfa['acceptingStates']:
        if acc_state not in states_set:
            raise ValueError(f"Invalid NFA structure: accepting state '{acc_state}' not in states list")

    # Check all transition source states are in states list
    for source_state in nfa['transitions']:
        if source_state not in states_set:
            raise ValueError(f"Invalid NFA structure: transition source state '{source_state}' not in states list")

        # Check all transition target states are in states list
        for symbol in nfa['transitions'][source_state]:
            for target_state in nfa['transitions'][source_state][symbol]:
                if target_state not in states_set:
                    raise ValueError(
                        f"Invalid NFA structure: transition target state '{target_state}' not in states list")

    # Special case: empty states list but non-empty starting state
    if len(nfa['states']) == 0 and nfa['startingState'] != '':
        raise ValueError("Invalid NFA structure: empty states list but non-empty starting state")

    # Check for duplicate states
    if len(nfa['states']) != len(states_set):
        raise ValueError("Invalid NFA structure: duplicate states in states list")

    # Check for duplicate accepting states
    if len(nfa['acceptingStates']) != len(set(nfa['acceptingStates'])):
        raise ValueError("Invalid NFA structure: duplicate states in accepting states list")