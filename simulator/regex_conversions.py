from typing import Dict, List, Set, Optional, Tuple
from collections import defaultdict
import re
from .fsa_properties import validate_fsa_structure
from .minimise_nfa import minimise_nfa
from .fsa_equivalence import are_automata_equivalent


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

        # Check for invalid start patterns
        if self.regex[0] in ['*', '+', '?']:
            raise ValueError(
                f"Regex cannot start with '{self.regex[0]}' - postfix operators require a preceding element")

        result = self.parse_union()
        if self.pos < len(self.regex):
            raise ValueError(f"Unexpected character '{self.regex[self.pos]}' at position {self.pos}")
        return result

    def parse_union(self) -> Tuple[str, str]:
        """Parse union (|) - lowest precedence."""
        left_start, left_accept = self.parse_concat()

        if self.peek() == '|':
            self.consume()  # consume '|'

            # Check for invalid patterns like "|+" (union followed by postfix operator)
            if self.peek() in ['*', '+', '?']:
                raise ValueError(f"Unexpected '{self.peek()}' after '|' at position {self.pos}")

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
        first_start, first_accept = self.parse_postfix()

        # Check if there's more to concatenate
        next_char = self.peek()
        if (next_char is not None and
                next_char not in ['|', ')'] and
                self.pos < len(self.regex)):
            second_start, second_accept = self.parse_concat()

            # Thompson construction for concatenation
            self.nfa.add_transition(first_accept, '', second_start)
            return first_start, second_accept

        return first_start, first_accept

    def parse_postfix(self) -> Tuple[str, str]:
        """Parse postfix operators (*, +, ?) - highest precedence."""
        inner_start, inner_accept = self.parse_atom()

        # Handle postfix operators
        while self.peek() in ['*', '+', '?']:
            operator = self.consume()

            if operator == '*':
                # Thompson construction for Kleene star
                new_start = self.nfa.new_state()
                new_accept = self.nfa.new_state()

                self.nfa.add_transition(new_start, '', new_accept)  # bypass
                self.nfa.add_transition(new_start, '', inner_start)  # enter
                self.nfa.add_transition(inner_accept, '', new_accept)  # exit
                self.nfa.add_transition(inner_accept, '', inner_start)  # loop

                inner_start, inner_accept = new_start, new_accept

            elif operator == '+':
                # Thompson construction for plus (one or more)
                new_start = self.nfa.new_state()
                new_accept = self.nfa.new_state()

                self.nfa.add_transition(new_start, '', inner_start)  # enter (must go through once)
                self.nfa.add_transition(inner_accept, '', new_accept)  # exit
                self.nfa.add_transition(inner_accept, '', inner_start)  # loop back for more

                inner_start, inner_accept = new_start, new_accept

            elif operator == '?':
                # Thompson construction for optional (zero or one)
                new_start = self.nfa.new_state()
                new_accept = self.nfa.new_state()

                self.nfa.add_transition(new_start, '', new_accept)  # bypass (zero occurrences)
                self.nfa.add_transition(new_start, '', inner_start)  # enter (one occurrence)
                self.nfa.add_transition(inner_accept, '', new_accept)  # exit

                inner_start, inner_accept = new_start, new_accept

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

        elif char and char not in ['|', ')', '*', '+', '?']:
            self.consume()
            # Single character
            start = self.nfa.new_state()
            accept = self.nfa.new_state()
            self.nfa.add_transition(start, char, accept)
            return start, accept

        elif char in ['*', '+', '?']:
            # Invalid: postfix operators at start or with no preceding element
            raise ValueError(
                f"Unexpected '{char}' at position {self.pos} - postfix operators require a preceding element")

        else:
            # Empty/epsilon case
            start = self.nfa.new_state()
            accept = self.nfa.new_state()
            self.nfa.add_transition(start, '', accept)
            return start, accept


class GNFA:
    """Generalized NFA for state elimination algorithm."""

    def __init__(self):
        self.states = set()
        self.transitions = defaultdict(lambda: defaultdict(str))  # state -> state -> regex
        self.start_state = None
        self.accept_state = None

    def add_state(self, state: str):
        """Add a state to the GNFA."""
        self.states.add(state)

    def add_transition(self, from_state: str, to_state: str, regex: str):
        """Add a transition labeled with a regex."""
        if regex:  # Only add non-empty transitions
            if self.transitions[from_state][to_state]:
                # Union with existing transition
                existing = self.transitions[from_state][to_state]
                self.transitions[from_state][to_state] = f"({existing}|{regex})"
            else:
                self.transitions[from_state][to_state] = regex

    def remove_state(self, state: str):
        """Remove a state and update transitions using state elimination."""
        if state == self.start_state or state == self.accept_state:
            return  # Never remove start or accept state

        # Get all transitions involving this state
        incoming = []  # (from_state, regex_to_state)
        outgoing = []  # (to_state, regex_from_state)
        self_loop = ""

        # Find incoming transitions
        for from_state in self.states:
            if from_state != state and self.transitions[from_state][state]:
                incoming.append((from_state, self.transitions[from_state][state]))

        # Find outgoing transitions
        for to_state in self.states:
            if to_state != state and self.transitions[state][to_state]:
                outgoing.append((to_state, self.transitions[state][to_state]))

        # Find self-loop
        if self.transitions[state][state]:
            self_loop = self.transitions[state][state]

        # Create new transitions for all combinations of incoming and outgoing
        for from_state, in_regex in incoming:
            for to_state, out_regex in outgoing:
                # Build new regex: incoming + (self_loop)* + outgoing
                parts = []

                # Add incoming part
                if in_regex == "ε":
                    pass  # Don't add epsilon to concatenation
                else:
                    parts.append(in_regex)

                # Add self-loop part with Kleene star
                if self_loop:
                    if self_loop == "ε":
                        pass  # ε* = ε, which doesn't affect concatenation
                    else:
                        # Need to parenthesize if it's a complex expression
                        if '|' in self_loop or len(self_loop) > 1:
                            parts.append(f"({self_loop})*")
                        else:
                            parts.append(f"{self_loop}*")

                # Add outgoing part
                if out_regex == "ε":
                    pass  # Don't add epsilon to concatenation
                else:
                    parts.append(out_regex)

                # Combine parts
                if not parts:
                    new_regex = "ε"
                else:
                    new_regex = "".join(parts)

                # Add to existing transition or create new one
                self.add_transition(from_state, to_state, new_regex)

        # Remove the state
        self.states.remove(state)

        # Remove all transitions involving this state
        for from_state in list(self.transitions.keys()):
            if from_state == state:
                del self.transitions[from_state]
            else:
                if state in self.transitions[from_state]:
                    del self.transitions[from_state][state]


def fsa_to_gnfa(fsa: Dict) -> GNFA:
    """Convert an FSA to a GNFA for state elimination."""
    gnfa = GNFA()

    # Add new start and accept states
    new_start = "gnfa_start"
    new_accept = "gnfa_accept"
    gnfa.add_state(new_start)
    gnfa.add_state(new_accept)
    gnfa.start_state = new_start
    gnfa.accept_state = new_accept

    # Add all original states
    for state in fsa['states']:
        gnfa.add_state(state)

    # Add epsilon transition from new start to original start
    gnfa.add_transition(new_start, fsa['startingState'], "ε")

    # Add epsilon transitions from all original accepting states to new accept
    for accept_state in fsa['acceptingStates']:
        gnfa.add_transition(accept_state, new_accept, "ε")

    # Add all original transitions
    for from_state in fsa['states']:
        if from_state in fsa['transitions']:
            for symbol in fsa['transitions'][from_state]:
                for to_state in fsa['transitions'][from_state][symbol]:
                    if symbol == '':
                        gnfa.add_transition(from_state, to_state, "ε")
                    else:
                        gnfa.add_transition(from_state, to_state, symbol)

    return gnfa


def simplify_regex(regex: str) -> str:
    """
    Simplify a regular expression by removing redundant patterns and applying optimizations.

    Handles some advanced cases like:
    - (|ba+) → (ba)*  (empty alternative with R+ becomes R*)
    - a(ba)*b → (ab)+  (alternating sequence pattern)
    - R*|R+ → R*      (star subsumes plus in unions)
    - R?? → R?        (double optional becomes single optional)
    - (|a) → a?       (empty alternative becomes optional)
    - a?|a → a?       (optional union with itself)
    - ba(ba)* → (ba)+ (multi-character repetition)
    - (R)*|(S)+ → (R)*|(S)* (union with star and plus)
    """
    if not regex:
        return "ε"

    # Handle the empty language symbol specifically
    if regex == "∅":
        return "∅"

    # Apply simplifications iteratively until no more changes
    prev_regex = None
    iterations = 0
    max_iterations = 100  # Prevent infinite loops

    while prev_regex != regex and iterations < max_iterations:
        print(regex)
        prev_regex = regex
        iterations += 1

        # Apply simplifications in order
        simplifications = [
            # Basic cleanup
            (r'\(\)\*', ''),  # ()* -> delete
            (r'\(\)\+', ''),  # ()+ -> delete
            (r'\(\)\?', ''),  # ()? -> delete
            (r'\(\)', ''),  # () → delete

            # Epsilon handling
            (r'ε\*', 'ε'),  # ε* -> ε
            (r'ε\+', 'ε'),  # ε+ -> ε
            (r'ε\?', 'ε'),  # ε? -> ε
            #(r'ε(?![*+?])', ''),  # ε -> delete

            # Multiple operators
            (r'\*\*+', '*'),  # collapse multiple stars
            (r'\+\++', '+'),  # collapse multiple pluses
            (r'\?\?+', '?'),  # collapse multiple question marks
            (r'\*\+', '*'),  # *+ -> * (star dominates plus)
            (r'\+\*', '*'),  # +* -> * (star dominates plus)
            (r'\*\?', '*'),  # *? -> * (star dominates optional)
            (r'\?\*', '*'),  # ?* -> * (star dominates optional)
            (r'\+\?', '*'),  # +? -> * (plus optional becomes star)
            (r'\?\+', '*'),  # ?+ -> * (optional plus becomes star)

            # Union flattening
            (r'\(\(([^|()]+)\|([^|()]+)\)\|([^|()]+)\)', r'(\1|\2|\3)'),  # ((A|B)|C) -> (A|B|C)
            (r'\(([^|()]+)\|\(([^|()]+)\|([^|()]+)\)\)', r'(\1|\2|\3)'),  # (A|(B|C)) -> (A|B|C)

            # Empty alternative simplifications
            (r'\(\|([a-zA-Z0-9ε])\)', r'\1?'),  # (|R) -> R?
            (r'\(\|([^|)]{2,})\)', r'(\1)?'),  # (|R) -> (R)? for multi-character R like (|ab) -> (ab)?

            # Optional union simplifications
            (r'([a-zA-Z0-9ε])\?\|\1(?![*+?])', r'\1?'),  # R?|R -> R?
            (r'([a-zA-Z0-9ε])\|\1\?(?![*+?])', r'\1?'),  # R|R? -> R?

            # Empty alternative patterns (existing)
            (r'\(\|(.+?)\+\)',  r'(\1)*'),  # (|R+) -> R*
            (r'\(ε\|(.+?)\+\)', r'(\1)*'),  # (ε|R+) -> R*
            (r'\((.+?)\+\|ε\)', r'(\1)*'),  # (R+|ε) -> R*
            (r'\(\|([^|)]+)\?\)', r'(\1)?'),  # (|R?) -> R?
            (r'\(ε\|([^|)]+)\?\)', r'(\1)?'),  # (ε|R?) -> R?
            (r'\(([^|)]+)\?\|ε\)', r'(\1)?'),  # (R?|ε) -> R?

            # (ε|R) -> R?
            (r'\(ε\|((?:[^|()]|\([^)]*\))*)\)', r'(\1)?'),    # (ε|R) -> (R)? - handles nested parens
            (r'\(((?:[^|()]|\([^)]*\))*)\|ε\)', r'(\1)?'),    # (R|ε) -> (R)? - handles nested parens
            (r'\(\|([^|]+)\)', r'(\1)?'),  # shorthand (|R)

            # Multi-character empty alternative
            (r'\(\|\(([^)]+)\)\+\)', r'(\1)*'),  # (|(R)+) -> R*

            # Union simplifications where * already includes empty string
            (r'\(([^|)]+)\)\*\|\(([^|)]+)\)\+', r'(\1)*|(\2)*'),  # (R)*|(S)+ -> (R)*|(S)*
            (r'\(([^|)]+)\)\+\|\(([^|)]+)\)\*', r'(\1)*|(\2)*'),  # (R)+|(S)* -> (R)*|(S)*
            (r'\(([a-zA-Z0-9]+)\?\|([a-zA-Z0-9]+)\+\1\?\)', r'\2*\1?'),  # (a?|b+a?) -> b*a?
            (r'\(\(([^|()]+)\)\+\)\?\|\(([^|()]+)\)\+', r'(\1)*|(\2)*'), # ((X)+)?|(Y)+ -> (X)*|(Y)*

            # Pattern recognition for S*R pattern in unions
            (r'\(([a-zA-Z0-9])\|([a-zA-Z0-9])\1\|([a-zA-Z0-9]+)\2\1\|\3\+\1\)', r'\2*\1'),  # (a|ba|bba|bbb+a) -> b*a

            # Union pattern simplifications - (X|YX) → Y?X and (YX|X) -> Y?X
            (r'\(([^|()?\ε*+]+)\|([^|()]+)\1\)', r'\2?\1'),  # (X|YX) -> Y?X where X doesn't contain * ? or ε
            (r'\(([^|()]+)([^|()]+)\|\2\)', r'\1?\2'),  # (YX|X) -> Y?X where Y is non-empty

            # Parentheses removal for single characters
            (r'\(([^|*+?()∅ε])\)\*', r'\1*'),  # (a)* -> a*
            (r'\(([^|*+?()∅ε])\)\+', r'\1+'),  # (a)+ -> a+
            (r'\(([^|*+?()∅ε])\)\?', r'\1?'),  # (a)? -> a?
            (r'\(([^|*+?()∅ε])\)', r'\1'),  # (a) -> a

            # Nested parentheses
            (r'\(\(([^()]+)\)\)', r'(\1)'),  # ((R)) -> (R)

            # Safe concatenation patterns
            (r'([a-zA-Z0-9])\1\*', r'\1+'),  # aa* -> a+
            (r'([a-zA-Z0-9]+)\(\1\)\*', r'(\1)+'),  # ba(ba)* -> (ba)+
            (r'([a-zA-Z0-9]+)\(([a-zA-Z0-9]+)\1\)\*\2', r'(\1\2)+'),  # a(ba)*b -> (ab)+
            (r'\(([^()]+?)\)\(\1\)\*', r'(\1)+'), # (R)(R)* -> (R)+

            # Duplicate alternatives
            (r'(^|\(|\|)([a-zA-Z0-9ε]+)\|\2(?=\)|\||$)', r'\1\2'),  # whole‑alternative duplicate, keep surrounding delimiter

            # Basic repetition cleanup
            (r'([a-zA-Z0-9])\*\*', r'\1*'),  # a** -> a*

            # Epsilon concatenation cleanup
            (r'(?<![|(])ε(?=[a-zA-Z0-9(])', ''),  # εa -> a (but NOT when ε follows | or ()
            (r'(?<=[a-zA-Z0-9)])ε(?![|)])', ''),  # aε -> a (but NOT when ε precedes | or ))
        ]

        # Apply all simplifications
        for pattern, replacement in simplifications:
            try:
                new_regex = re.sub(pattern, replacement, regex)
                regex = new_regex
            except re.error:
                continue

    # Final cleanup - if the result is empty, return epsilon
    if not regex:
        return 'ε'

    return regex


def eliminate_states(gnfa: GNFA) -> str:
    """Eliminate states from GNFA until only start and accept remain."""
    # Continue until only start and accept states remain
    while len(gnfa.states) > 2:
        # Choose a state to eliminate (not start or accept)
        # Strategy: eliminate states with fewer transitions first
        best_state = None
        min_transitions = float('inf')

        for state in gnfa.states:
            if state != gnfa.start_state and state != gnfa.accept_state:
                # Count transitions involving this state
                transition_count = 0
                for from_state in gnfa.states:
                    if gnfa.transitions[from_state][state]:
                        transition_count += 1
                    if gnfa.transitions[state][from_state]:
                        transition_count += 1

                if transition_count < min_transitions:
                    min_transitions = transition_count
                    best_state = state

        if best_state is None:
            break

        gnfa.remove_state(best_state)

    # Get the final regex from start to accept
    final_regex = gnfa.transitions[gnfa.start_state][gnfa.accept_state]

    if not final_regex:
        return "∅"  # Empty language

    return simplify_regex(final_regex)


def fsa_to_regex(fsa: Dict) -> Dict:
    """
    Convert a finite state automaton to a regular expression.
    Now with improved verification that falls back to original regex if simplification fails.
    """
    result = {
        'regex': '',
        'valid': False,
        'original_states': len(fsa.get('states', [])),
        'minimized_states': 0,
        'verification': {},
        'error': None
    }

    try:
        # Step 1: Validation
        validation = validate_fsa_structure(fsa)
        if not validation['valid']:
            result['error'] = f"Invalid FSA structure: {validation['error']}"
            return result

        # Step 2: Handle empty FSA early
        if not fsa.get('states'):
            result['regex'] = '∅'
            result['valid'] = True
            result['minimized_states'] = 0
            result['verification'] = {'equivalent': True, 'empty_language': True}
            return result

        # Step 3: Minimise the automaton
        try:
            minimisation_result = minimise_nfa(fsa)
            minimised_fsa = minimisation_result.nfa
            result['minimized_states'] = len(minimised_fsa.get('states', []))
        except Exception as e:
            # If minimisation fails, use original FSA
            minimised_fsa = fsa
            result['minimized_states'] = len(fsa.get('states', []))

        # Handle FSA that became empty after minimisation
        if not minimised_fsa.get('states'):
            result['regex'] = '∅'
            result['valid'] = True
            result['verification'] = {'equivalent': True, 'empty_language': True}
            return result

        # Handle single state FSA
        if len(minimised_fsa['states']) == 1:
            state = minimised_fsa['states'][0]
            result['minimized_states'] = 1

            # Build original regex
            if state in minimised_fsa.get('acceptingStates', []):
                # Check for self-loops
                self_loop_symbols = []
                if state in minimised_fsa.get('transitions', {}):
                    for symbol in minimised_fsa['transitions'][state]:
                        if state in minimised_fsa['transitions'][state][symbol]:
                            self_loop_symbols.append(symbol)

                if self_loop_symbols:
                    if len(self_loop_symbols) == 1:
                        original_regex = f"({self_loop_symbols[0]})*"
                    else:
                        union = '|'.join(self_loop_symbols)
                        original_regex = f"({union})*"
                else:
                    original_regex = 'ε'
            else:
                original_regex = '∅'

            # Create simplified version
            simplified_regex = simplify_regex(original_regex)

            # Verify with fallback strategy
            final_regex, verification_result = verify(
                fsa, original_regex, simplified_regex
            )

            result['regex'] = final_regex
            result['valid'] = True
            result['verification'] = verification_result

            return result

        # Step 4: Convert to GNFA
        gnfa = fsa_to_gnfa(minimised_fsa)

        # Step 5: Eliminate states to get original regex
        original_regex = eliminate_states(gnfa)

        # Step 6: Create simplified version
        simplified_regex = simplify_regex(original_regex)

        # Step 7: Verify with fallback strategy
        final_regex, verification_result = verify(
            fsa, original_regex, simplified_regex
        )

        result['regex'] = final_regex
        result['valid'] = True
        result['verification'] = verification_result

        return result

    except Exception as e:
        result['error'] = str(e)
        return result


def verify(fsa: Dict, original_regex: str, simplified_regex: str) -> tuple:
    """
    Verify regex conversion with fallback strategy.

    Args:
        fsa: Original FSA
        original_regex: Regex before simplification
        simplified_regex: Regex after simplification

    Returns:
        tuple: (final_regex, verification_dict)
    """

    # Try to verify simplified regex first
    try:
        converted_back_simplified = regex_to_epsilon_nfa(simplified_regex)
        is_equivalent_simplified, equiv_details_simplified = are_automata_equivalent(
            fsa, converted_back_simplified
        )

        if is_equivalent_simplified:
            # Simplified version is correct, use it
            return simplified_regex, {
                'equivalent': True,
                'details': equiv_details_simplified,
                'used_simplified': True,
                'strategy': 'simplified_passed'
            }

    except Exception as e_simplified:
        # Simplified regex failed to convert to NFA
        pass

    # Simplified failed, try original regex
    try:
        converted_back_original = regex_to_epsilon_nfa(original_regex)
        is_equivalent_original, equiv_details_original = are_automata_equivalent(
            fsa, converted_back_original
        )

        if is_equivalent_original:
            # Original passes verification, use it instead of simplified
            verification_result = {
                'equivalent': True,
                'details': equiv_details_original,
                'used_simplified': False,
                'strategy': 'fallback_to_original',
                'simplification_issue': True
            }

            # Add details about why we fell back
            try:
                converted_back_simplified = regex_to_epsilon_nfa(simplified_regex)
                is_equivalent_simplified, equiv_details_simplified = are_automata_equivalent(
                    fsa, converted_back_simplified
                )
                verification_result['simplified_verification'] = {
                    'equivalent': is_equivalent_simplified,
                    'details': equiv_details_simplified
                }
            except Exception as e_simplified:
                verification_result['simplified_conversion_error'] = str(e_simplified)

            return original_regex, verification_result
        else:
            # Both failed equivalence check
            verification_result = {
                'equivalent': False,
                'strategy': 'both_failed_equivalence',
                'used_simplified': False,
                'original_details': equiv_details_original
            }

            # Try to add simplified details if possible
            try:
                converted_back_simplified = regex_to_epsilon_nfa(simplified_regex)
                is_equivalent_simplified, equiv_details_simplified = are_automata_equivalent(
                    fsa, converted_back_simplified
                )
                verification_result['simplified_details'] = equiv_details_simplified
            except Exception as e_simplified:
                verification_result['simplified_conversion_error'] = str(e_simplified)

            # Return simplified since both failed (keep existing behavior)
            return simplified_regex, verification_result

    except Exception as e_original:
        # Original regex also failed to convert
        verification_result = {
            'equivalent': False,
            'strategy': 'both_failed_conversion',
            'used_simplified': False,
            'original_conversion_error': str(e_original)
        }

        # Try to add simplified error details
        try:
            converted_back_simplified = regex_to_epsilon_nfa(simplified_regex)
            is_equivalent_simplified, equiv_details_simplified = are_automata_equivalent(
                fsa, converted_back_simplified
            )
            verification_result['simplified_details'] = equiv_details_simplified
        except Exception as e_simplified:
            verification_result['simplified_conversion_error'] = str(e_simplified)

        # Return simplified since both failed
        return simplified_regex, verification_result


def regex_to_epsilon_nfa(regex: str) -> Dict:
    """
    Convert a regular expression to an ε-NFA using Thompson's construction.

    Args:
        regex (str): The regular expression to convert. Supports:
            - Single characters: a, b, c, 0, 1, etc.
            - Epsilon: ε
            - Union: | (e.g., "a|b")
            - Concatenation: implicit (e.g., "ab")
            - Kleene star: * (e.g., "a*")
            - Plus: + (e.g., "a+") - one or more
            - Optional: ? (e.g., "a?") - zero or one
            - Parentheses: () for grouping
            - Consecutive postfix operators: *, +, ? (e.g., "a*+", "a+*", "a??")
              Note: Consecutive operators are mathematically valid but may be redundant

    Returns:
        Dict: An ε-NFA in the standard FSA format

    Examples:
        regex_to_epsilon_nfa("a?")     # Zero or one 'a'
        regex_to_epsilon_nfa("(ab)?")  # Optional "ab" sequence
        regex_to_epsilon_nfa("a?b*")   # Optional 'a' followed by zero or more 'b's
        regex_to_epsilon_nfa("a+?")    # One or more 'a's, optionally (equivalent to a*)
        regex_to_epsilon_nfa("a??")    # Zero or one 'a' (redundant but valid)
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