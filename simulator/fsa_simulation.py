from typing import Dict, List, Union, Tuple, Optional


def simulate_deterministic_fsa(fsa: Dict, input_string: str) -> Union[List[Tuple[str, str, str]], bool]:
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
        If the input is rejected, returns False.
    """
    # Validate the FSA is deterministic
    if not _is_deterministic(fsa):
        raise ValueError("FSA must be deterministic")

    current_state = fsa['startingState']
    execution_path = []

    # Process each symbol in the input string
    for symbol in input_string:
        # Check if the symbol is in the alphabet
        if symbol not in fsa['alphabet']:
            return False

        # Get the next state for this symbol (if any)
        if symbol not in fsa['transitions'][current_state] or not fsa['transitions'][current_state][symbol]:
            return False  # No transition defined for this symbol from current state

        next_states = fsa['transitions'][current_state][symbol]

        # In a deterministic FSA, there should be at most one next state
        if len(next_states) != 1:
            return False  # This should not happen if FSA is truly deterministic

        next_state = next_states[0]

        # Record this transition in our execution path
        execution_path.append((current_state, symbol, next_state))

        # Update current state
        current_state = next_state

    # Check if we ended in an accepting state
    if current_state in fsa['acceptingStates']:
        return execution_path
    else:
        return False


def _is_deterministic(fsa: Dict) -> bool:
    """
    Checks if the FSA is deterministic.

    An FSA is deterministic if:
    1. For each state and each symbol, there is at most one transition
    2. There are no epsilon transitions
    """
    # We're assuming no epsilon transitions since they aren't in the transition table format

    for state in fsa['states']:
        for symbol in fsa['alphabet']:
            # Check if there's a transition for this symbol
            if symbol in fsa['transitions'][state]:
                # If there's a transition, ensure it leads to at most one state
                if len(fsa['transitions'][state][symbol]) > 1:
                    return False  # Not deterministic (multiple possible next states)

    return True