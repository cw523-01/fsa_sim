from typing import Dict, List, Set, Optional, Tuple
from collections import defaultdict


class NFABuilder:
    """Helper class to build NFAs."""

    def __init__(self):
        self.state_counter = 0
        self.states = set()
        self.alphabet = set()
        self.transitions = defaultdict(lambda: defaultdict(list))

    def new_state(self) -> str:
        """Generate a new unique state."""
        state = f"q{self.state_counter}"
        self.state_counter += 1
        self.states.add(state)
        return state

    def add_transition(self, from_state: str, symbol: str, to_state: str):
        """Add a transition."""
        self.transitions[from_state][symbol].append(to_state)
        if symbol != '':  # Don't add epsilon to alphabet
            self.alphabet.add(symbol)

    def to_dict(self, start_state: str, accept_states: List[str]) -> Dict:
        """Convert to FSA dictionary format."""
        return {
            'states': sorted(list(self.states)),
            'alphabet': sorted(list(self.alphabet)),
            'transitions': dict(self.transitions),
            'startingState': start_state,
            'acceptingStates': sorted(accept_states)
        }


class RegexParser:
    """Regex parser that builds an NFA."""

    def __init__(self, regex: str, nfa: NFABuilder):
        self.regex = regex
        self.pos = 0
        self.nfa = nfa

    def peek(self) -> Optional[str]:
        """Look at current character without consuming."""
        return self.regex[self.pos] if self.pos < len(self.regex) else None

    def consume(self) -> Optional[str]:
        """Consume and return current character."""
        if self.pos < len(self.regex):
            char = self.regex[self.pos]
            self.pos += 1
            return char
        return None

    def parse(self) -> Tuple[str, str]:
        """Parse regex and return (start_state, accept_state)."""
        if not self.regex:
            # Empty regex = epsilon
            start = self.nfa.new_state()
            accept = self.nfa.new_state()
            self.nfa.add_transition(start, '', accept)
            return start, accept

        result = self.parse_union()
        if self.pos < len(self.regex):
            raise ValueError(f"Unexpected character at position {self.pos}")
        return result

    def parse_union(self) -> Tuple[str, str]:
        """Parse union (|) - lowest precedence."""
        left_start, left_accept = self.parse_concat()

        if self.peek() == '|':
            self.consume()  # consume '|'
            right_start, right_accept = self.parse_union()

            # Thompson construction for union
            new_start = self.nfa.new_state()
            new_accept = self.nfa.new_state()

            self.nfa.add_transition(new_start, '', left_start)
            self.nfa.add_transition(new_start, '', right_start)
            self.nfa.add_transition(left_accept, '', new_accept)
            self.nfa.add_transition(right_accept, '', new_accept)

            return new_start, new_accept

        return left_start, left_accept

    def parse_concat(self) -> Tuple[str, str]:
        """Parse concatenation - implicit, higher precedence than union."""
        first_start, first_accept = self.parse_star()

        # Check if there's more to concatenate
        if (self.peek() is not None and
                self.peek() not in ['|', ')'] and
                self.pos < len(self.regex)):
            second_start, second_accept = self.parse_concat()

            # Thompson construction for concatenation
            self.nfa.add_transition(first_accept, '', second_start)
            return first_start, second_accept

        return first_start, first_accept

    def parse_star(self) -> Tuple[str, str]:
        """Parse Kleene star (*) - highest precedence."""
        inner_start, inner_accept = self.parse_atom()

        if self.peek() == '*':
            self.consume()  # consume '*'

            # Thompson construction for star
            new_start = self.nfa.new_state()
            new_accept = self.nfa.new_state()

            self.nfa.add_transition(new_start, '', new_accept)  # bypass
            self.nfa.add_transition(new_start, '', inner_start)  # enter
            self.nfa.add_transition(inner_accept, '', new_accept)  # exit
            self.nfa.add_transition(inner_accept, '', inner_start)  # loop

            return new_start, new_accept

        return inner_start, inner_accept

    def parse_atom(self) -> Tuple[str, str]:
        """Parse atomic expressions."""
        char = self.peek()

        if char == '(':
            self.consume()  # consume '('
            inner_start, inner_accept = self.parse_union()
            if self.peek() != ')':
                raise ValueError(f"Expected ')' at position {self.pos}")
            self.consume()  # consume ')'
            return inner_start, inner_accept

        elif char == 'ε':
            self.consume()
            # Epsilon transition
            start = self.nfa.new_state()
            accept = self.nfa.new_state()
            self.nfa.add_transition(start, '', accept)
            return start, accept

        elif char and char not in ['|', ')', '*']:
            self.consume()
            # Single character
            start = self.nfa.new_state()
            accept = self.nfa.new_state()
            self.nfa.add_transition(start, char, accept)
            return start, accept

        else:
            # Empty/epsilon case
            start = self.nfa.new_state()
            accept = self.nfa.new_state()
            self.nfa.add_transition(start, '', accept)
            return start, accept


def regex_to_epsilon_nfa(regex: str) -> Dict:
    """
    Convert a regular expression to an ε-NFA using Thompson's construction.
    No AST required - builds NFA directly during parsing.

    Args:
        regex (str): The regular expression to convert. Supports:
            - Single characters: a, b, c, 0, 1, etc.
            - Epsilon: ε
            - Union: | (e.g., "a|b")
            - Concatenation: implicit (e.g., "ab")
            - Kleene star: * (e.g., "a*")
            - Parentheses: () for grouping

    Returns:
        Dict: An ε-NFA in the standard FSA format

    Examples:
    """
    nfa_builder = NFABuilder()
    parser = RegexParser(regex, nfa_builder)

    try:
        start_state, accept_state = parser.parse()
        return nfa_builder.to_dict(start_state, [accept_state])
    except Exception as e:
        raise ValueError(f"Invalid regex '{regex}': {str(e)}")


def validate_regex_syntax(regex: str) -> Dict[str, any]:
    """
    Validate regex syntax without building the full NFA.

    Args:
        regex (str): The regular expression to validate

    Returns:
        Dict with 'valid' (bool) and optional 'error' (str) keys
    """
    try:
        regex_to_epsilon_nfa(regex)
        return {'valid': True}
    except Exception as e:
        return {'valid': False, 'error': str(e)}

def regex_to_dfa(regex: str) -> Dict:
    """Convert regex to DFA (via ε-NFA)."""
    nfa = regex_to_epsilon_nfa(regex)
    from .fsa_transformations import nfa_to_dfa
    return nfa_to_dfa(nfa)


def regex_to_minimal_dfa(regex: str) -> Dict:
    """Convert regex to minimal DFA."""
    dfa = regex_to_dfa(regex)
    from .fsa_transformations import minimise_dfa
    return minimise_dfa(dfa)