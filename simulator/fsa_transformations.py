from typing import Dict, Set, Tuple, List
from collections import defaultdict
from .fsa_properties import is_deterministic


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