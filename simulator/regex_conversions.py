from abc import abstractmethod, ABC
from dataclasses import dataclass
from typing import Dict, List, Set, Optional, Tuple
from collections import defaultdict
import re
from .fsa_properties import validate_fsa_structure
from .minimise_nfa import minimise_nfa, remove_unreachable_states, remove_dead_states
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
    """Generalised NFA for state elimination algorithm."""

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


def nodes_equivalent(node1: 'RegexNode', node2: 'RegexNode') -> bool:
    """
    Checks semantic equivalence between regex nodes.
    This is the single source of truth for node equivalence.
    """
    # Quick identity checks
    if node1 is node2:
        return True

    # Type must match
    if type(node1) != type(node2):
        return False

    # Type-specific equivalence
    if isinstance(node1, CharNode):
        return node1.char == node2.char
    elif isinstance(node1, (EpsilonNode, EmptySetNode, EmptyGroupNode)):
        return True  # Same type = equivalent
    elif isinstance(node1, ConcatNode):
        return (nodes_equivalent(node1.left, node2.left) and
                nodes_equivalent(node1.right, node2.right))
    elif isinstance(node1, UnionNode):
        # Better union equivalence checking
        # First try the standard left-right comparison
        if (nodes_equivalent(node1.left, node2.left) and
                nodes_equivalent(node1.right, node2.right)):
            return True
        # Then try the swapped comparison (A|B == B|A)
        if (nodes_equivalent(node1.left, node2.right) and
                nodes_equivalent(node1.right, node2.left)):
            return True
        # For more complex cases, we could implement union flattening here
        # but let's keep it simple for now
        return False
    elif isinstance(node1, StarNode):
        return nodes_equivalent(node1.inner, node2.inner)
    elif isinstance(node1, PlusNode):
        return nodes_equivalent(node1.inner, node2.inner)
    elif isinstance(node1, OptionalNode):
        return nodes_equivalent(node1.inner, node2.inner)
    elif isinstance(node1, MultiOperatorNode):
        return (nodes_equivalent(node1.inner, node2.inner) and
                node1.operators == node2.operators)
    else:
        # Fallback: try string comparison for unknown types
        try:
            return node1.to_string() == node2.to_string()
        except:
            return False


def simplify_regex(regex: str, max_complexity: int = 5000) -> str:
    """
    Simplify a regular expression using AST-based approach.
    """
    if not regex:
        return 'ε'

    if regex == '∅':
        return '∅'

    if len(regex) > max_complexity:
        return regex

    try:
        # Parse to AST
        parser = RegexASTParser(regex)
        ast = parser.parse()

        # Use structural equivalence for termination
        prev_ast = None
        iterations = 0
        max_iterations = 50

        while iterations < max_iterations:
            # Stop if no structural changes
            if prev_ast is not None and nodes_equivalent(prev_ast, ast):
                break

            prev_ast = ast

            # Primary simplification
            ast = ast.simplify()

            # More aggressive pattern detection with re-simplification
            for pattern_round in range(5):
                # Apply pattern detection with re-simplification
                new_ast = _detect_char_star_patterns(ast)
                new_ast = _detect_union_patterns(new_ast)
                new_ast = _detect_concat_patterns(new_ast)
                new_ast = _detect_epsilon_patterns(new_ast)
                new_ast = _detect_nested_patterns(new_ast)

                # If no structural changes in this round, break
                if new_ast.to_string() == ast.to_string():
                    break
                ast = new_ast

            iterations += 1

        # Convert back to string
        result = ast.to_string()

        # Final cleanup - if result is empty, return epsilon
        return result if result else 'ε'

    except Exception as e:
        # If parsing fails, return original (graceful fallback)
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

    return final_regex


def fsa_to_regex(fsa: Dict, skip_simplification_threshold: int = 2500) -> Dict:
    """
    Convert a finite state automaton to a regular expression.
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

        # Step 1: Remove unreachable states
        fsa = remove_unreachable_states(fsa)

        # Step 2: Remove dead states
        fsa = remove_dead_states(fsa)

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

        # Estimate complexity before conversion
        num_states = len(minimised_fsa.get('states', []))
        num_symbols = len(minimised_fsa.get('alphabet', []))
        num_transitions = sum(
            len(dests)
            for state in minimised_fsa.get('transitions', {})
            for symbol in minimised_fsa['transitions'][state]
            for dests in [minimised_fsa['transitions'][state][symbol]]
        )

        estimated_complexity = num_states * num_symbols * num_transitions

        if estimated_complexity > skip_simplification_threshold:
            # Skip state elimination optimization for very large FSAs
            result['simplification_skipped'] = True

        # Step 4: Convert to GNFA
        gnfa = fsa_to_gnfa(minimised_fsa)

        # Step 5: Eliminate states to get original regex
        original_regex = eliminate_states(gnfa)

        # Apply complexity-aware simplification
        if not result.get('simplification_skipped', False):
            # Step 6 (optional): Create simplified version
            simplified_regex = simplify_regex(original_regex)

        else:
            simplified_regex = original_regex  # Skip simplification

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
        # preprocess the converted FSA
        converted_back_simplified = remove_unreachable_states(converted_back_simplified)
        converted_back_simplified = remove_dead_states(converted_back_simplified)

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
        #  Also preprocess the converted FSA
        converted_back_original = remove_unreachable_states(converted_back_original)
        converted_back_original = remove_dead_states(converted_back_original)

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

def _flatten_concatenation(node: 'RegexNode') -> List['RegexNode']:
    """
    Flatten a concatenation tree into a list of nodes.
    This enables pattern detection across multiple concatenated elements.

    Example: ConcatNode(ConcatNode(a, b), c) → [a, b, c]
    """
    if isinstance(node, ConcatNode):
        left_items = _flatten_concatenation(node.left)
        right_items = _flatten_concatenation(node.right)
        return left_items + right_items
    else:
        return [node]


def _detect_flattened_concat_patterns(nodes: List['RegexNode']) -> List['RegexNode']:
    """
    Apply pattern detection on flattened concatenation lists.
    Detects patterns like aaa* → aa+ that binary trees miss.

    Patterns detected:
    - [..., R, R*] → [..., R+]  (e.g., [a, a, StarNode(a)] → [a, PlusNode(a)])
    - [..., R*, R] → [..., R+]  (e.g., [StarNode(a), a] → [PlusNode(a)])
    """
    if len(nodes) < 2:
        return nodes

    result = []
    i = 0

    while i < len(nodes):
        # Pattern: [..., R, R*] → [..., R+]
        # Example: [a, a, StarNode(a)] → [a, PlusNode(a)]
        if (i + 1 < len(nodes) and
                isinstance(nodes[i + 1], StarNode) and
                nodes_equivalent(nodes[i], nodes[i + 1].inner)):
            result.append(PlusNode(nodes[i]).simplify())
            i += 2  # Skip both R and R*
            continue

        # Pattern: [..., R*, R] → [..., R+]
        # Example: [StarNode(a), a] → [PlusNode(a)]
        if (i + 1 < len(nodes) and
                isinstance(nodes[i], StarNode) and
                nodes_equivalent(nodes[i].inner, nodes[i + 1])):
            result.append(PlusNode(nodes[i + 1]).simplify())
            i += 2  # Skip both R* and R
            continue

        # No pattern matched, keep the node
        result.append(nodes[i])
        i += 1

    return result


def _rebuild_concatenation(nodes: List['RegexNode']) -> 'RegexNode':
    """
    Rebuild a concatenation tree from a flattened list.
    Uses right-associative structure for better pattern detection.

    Example: [a, b, c] → ConcatNode(a, ConcatNode(b, c))
    """
    if len(nodes) == 0:
        return EpsilonNode()
    elif len(nodes) == 1:
        return nodes[0]
    else:
        # Right-associative: a(b(cd...))
        return ConcatNode(nodes[0], _rebuild_concatenation(nodes[1:]))


def _detect_union_patterns(node: 'RegexNode') -> 'RegexNode':
    """Detect union patterns with re-simplification."""
    if isinstance(node, UnionNode):
        left = _detect_union_patterns(node.left)
        right = _detect_union_patterns(node.right)

        # Pattern: (ε|R*) → R*
        if isinstance(left, EpsilonNode) and isinstance(right, StarNode):
            return right
        if isinstance(right, EpsilonNode) and isinstance(left, StarNode):
            return left

        # Pattern: (ε|R+) → R*
        if isinstance(left, EpsilonNode) and isinstance(right, PlusNode):
            return StarNode(right.inner).simplify()
        if isinstance(right, EpsilonNode) and isinstance(left, PlusNode):
            return StarNode(left.inner).simplify()

        # Re-simplify the result
        result = UnionNode(left, right)
        return result.simplify()

    elif isinstance(node, ConcatNode):
        left = _detect_union_patterns(node.left)
        right = _detect_union_patterns(node.right)
        result = ConcatNode(left, right)
        return result.simplify()

    elif isinstance(node, StarNode):
        inner = _detect_union_patterns(node.inner)
        result = StarNode(inner)
        return result.simplify()

    elif isinstance(node, PlusNode):
        inner = _detect_union_patterns(node.inner)
        result = PlusNode(inner)
        return result.simplify()

    elif isinstance(node, OptionalNode):
        inner = _detect_union_patterns(node.inner)
        result = OptionalNode(inner)
        return result.simplify()

    else:
        return node


def _detect_concat_patterns(node: 'RegexNode') -> 'RegexNode':
    """Detect concatenation patterns with flattening support."""
    if isinstance(node, ConcatNode):
        left = _detect_concat_patterns(node.left)
        right = _detect_concat_patterns(node.right)

        # First apply standard binary patterns
        # VALID RULE: RR* → R+ (R followed by 0+ Rs = 1+ Rs)
        if isinstance(right, StarNode) and nodes_equivalent(left, right.inner):
            return PlusNode(left).simplify()

        # VALID RULE: R*R → R+ (0+ Rs followed by R = 1+ Rs)
        if isinstance(left, StarNode) and nodes_equivalent(right, left.inner):
            return PlusNode(right).simplify()

        # Create result with simplified children
        result = ConcatNode(left, right)

        # Apply flattened pattern detection
        # This catches patterns like aaa* → aa+ that binary trees miss
        flattened = _flatten_concatenation(result)
        if len(flattened) > 2:  # Only apply to multi-element concatenations
            simplified_flat = _detect_flattened_concat_patterns(flattened)
            if len(simplified_flat) != len(flattened):  # Pattern was detected
                result = _rebuild_concatenation(simplified_flat)

        return result.simplify()

    elif isinstance(node, UnionNode):
        left = _detect_concat_patterns(node.left)
        right = _detect_concat_patterns(node.right)
        result = UnionNode(left, right)
        return result.simplify()

    elif isinstance(node, StarNode):
        inner = _detect_concat_patterns(node.inner)
        result = StarNode(inner)
        return result.simplify()

    elif isinstance(node, PlusNode):
        inner = _detect_concat_patterns(node.inner)
        result = PlusNode(inner)
        return result.simplify()

    elif isinstance(node, OptionalNode):
        inner = _detect_concat_patterns(node.inner)
        result = OptionalNode(inner)
        return result.simplify()

    else:
        return node


def _detect_epsilon_patterns(node: 'RegexNode') -> 'RegexNode':
    """Detect epsilon-related patterns with re-simplification."""
    if isinstance(node, UnionNode):
        left = _detect_epsilon_patterns(node.left)
        right = _detect_epsilon_patterns(node.right)

        # Epsilon absorption patterns
        if isinstance(left, EpsilonNode):
            if isinstance(right, StarNode):
                return right.simplify()  # ε|R* → R*
            elif isinstance(right, PlusNode):
                return StarNode(right.inner).simplify()  # ε|R+ → R*
            else:
                return OptionalNode(right).simplify()  # ε|R → R?

        if isinstance(right, EpsilonNode):
            if isinstance(left, StarNode):
                return left.simplify()  # R*|ε → R*
            elif isinstance(left, PlusNode):
                return StarNode(left.inner).simplify()  # R+|ε → R*
            else:
                return OptionalNode(left).simplify()  # R|ε → R?

        # Re-simplify the result
        result = UnionNode(left, right)
        return result.simplify()

    elif isinstance(node, ConcatNode):
        left = _detect_epsilon_patterns(node.left)
        right = _detect_epsilon_patterns(node.right)

        # Epsilon elimination in concatenation
        if isinstance(left, EpsilonNode):
            return right.simplify()
        if isinstance(right, EpsilonNode):
            return left.simplify()

        # Re-simplify the result
        result = ConcatNode(left, right)
        return result.simplify()

    elif isinstance(node, StarNode):
        inner = _detect_epsilon_patterns(node.inner)
        result = StarNode(inner)
        return result.simplify()

    elif isinstance(node, PlusNode):
        inner = _detect_epsilon_patterns(node.inner)
        result = PlusNode(inner)
        return result.simplify()

    elif isinstance(node, OptionalNode):
        inner = _detect_epsilon_patterns(node.inner)
        result = OptionalNode(inner)
        return result.simplify()

    else:
        return node


def _detect_nested_patterns(node: 'RegexNode') -> 'RegexNode':
    """Detect patterns in nested structures with re-simplification."""
    if isinstance(node, ConcatNode):
        left = _detect_nested_patterns(node.left)
        right = _detect_nested_patterns(node.right)

        # If either side changed, simplify the whole thing again
        if not nodes_equivalent(left, node.left) or not nodes_equivalent(right, node.right):
            result = ConcatNode(left, right)
            return result.simplify()

        return node

    elif isinstance(node, UnionNode):
        left = _detect_nested_patterns(node.left)
        right = _detect_nested_patterns(node.right)

        if not nodes_equivalent(left, node.left) or not nodes_equivalent(right, node.right):
            result = UnionNode(left, right)
            return result.simplify()

        return node

    elif isinstance(node, StarNode):
        inner = _detect_nested_patterns(node.inner)
        if not nodes_equivalent(inner, node.inner):
            result = StarNode(inner)
            return result.simplify()
        return node

    elif isinstance(node, PlusNode):
        inner = _detect_nested_patterns(node.inner)
        if not nodes_equivalent(inner, node.inner):
            result = PlusNode(inner)
            return result.simplify()
        return node

    elif isinstance(node, OptionalNode):
        inner = _detect_nested_patterns(node.inner)
        if not nodes_equivalent(inner, node.inner):
            result = OptionalNode(inner)
            return result.simplify()
        return node

    else:
        return node


class RegexNode(ABC):
    """Base class for regex AST nodes."""

    @abstractmethod
    def to_string(self) -> str:
        """Convert node back to regex string."""
        pass

    @abstractmethod
    def simplify(self) -> 'RegexNode':
        """Return a simplified version of this node."""
        pass

    def __eq__(self, other) -> bool:
        """Use nodes_equivalent for equality."""
        if not isinstance(other, RegexNode):
            return False
        return nodes_equivalent(self, other)


@dataclass
class CharNode(RegexNode):
    """Single character node (a, b, 0, 1, etc.)."""
    char: str

    def to_string(self) -> str:
        return self.char

    def simplify(self) -> 'RegexNode':
        return self


@dataclass
class EpsilonNode(RegexNode):
    """Epsilon (empty string) node."""

    def to_string(self) -> str:
        return 'ε'

    def simplify(self) -> 'RegexNode':
        return self


@dataclass
class EmptySetNode(RegexNode):
    """Empty language node (∅)."""

    def to_string(self) -> str:
        return '∅'

    def simplify(self) -> 'RegexNode':
        return self


@dataclass
class EmptyGroupNode(RegexNode):
    """Empty group node () - represents an empty regex that should be eliminated."""

    def to_string(self) -> str:
        return ''  # Empty groups produce empty strings

    def simplify(self) -> 'RegexNode':
        return EpsilonNode()  # () becomes ε


@dataclass
class UnionNode(RegexNode):
    """Union node (R|S) with rule ordering."""
    left: RegexNode
    right: RegexNode

    def to_string(self) -> str:
        left_str = self.left.to_string()
        right_str = self.right.to_string()

        if not left_str:
            return f"|{right_str}" if right_str else ""
        if not right_str:
            return f"{left_str}|" if left_str else ""

        return f"{left_str}|{right_str}"

    def simplify(self) -> 'RegexNode':
        left = self.left.simplify()
        right = self.right.simplify()

        # Rule: R|R → R (idempotent)
        if nodes_equivalent(left, right):
            return left

        # Rule: ∅|R → R, R|∅ → R (empty set identity)
        if isinstance(left, EmptySetNode):
            return right
        if isinstance(right, EmptySetNode):
            return left

        # PRIORITY RULES: Handle star/plus relationships first

        # Rule: R*|R+ → R* (star subsumes plus)
        if (isinstance(left, StarNode) and isinstance(right, PlusNode) and
                nodes_equivalent(left.inner, right.inner)):
            return left
        if (isinstance(right, StarNode) and isinstance(left, PlusNode) and
                nodes_equivalent(right.inner, left.inner)):
            return right

        # RULE: R*|S+ → R*|S* (when R* accepts ε, S+ can become S*)
        if isinstance(left, StarNode) and isinstance(right, PlusNode):
            return UnionNode(left, StarNode(right.inner).simplify()).simplify()
        if isinstance(right, StarNode) and isinstance(left, PlusNode):
            return UnionNode(StarNode(left.inner).simplify(), right).simplify()

        # RULE: (ε|R*) → R*
        if isinstance(left, EpsilonNode) and isinstance(right, StarNode):
            return right
        if isinstance(right, EpsilonNode) and isinstance(left, StarNode):
            return left

        # Rule: (ε|R+) → R*
        if isinstance(left, EpsilonNode) and isinstance(right, PlusNode):
            return StarNode(right.inner).simplify()
        if isinstance(right, EpsilonNode) and isinstance(left, PlusNode):
            return StarNode(left.inner).simplify()

        # RULE: X|YX → Y?X (factor out common suffix)
        if isinstance(right, ConcatNode):
            # Check if left matches the right side of the concatenation
            if nodes_equivalent(left, right.right):
                # X|YX → Y?X
                Y = right.left
                X = left
                return ConcatNode(OptionalNode(Y).simplify(), X).simplify()

        # Also check the reverse: YX|X → Y?X
        if isinstance(left, ConcatNode):
            # Check if right matches the right side of the concatenation
            if nodes_equivalent(right, left.right):
                # YX|X → Y?X
                Y = left.left
                X = right
                return ConcatNode(OptionalNode(Y).simplify(), X).simplify()

        # Rule: R|R? → R?, R?|R → R? (union with optional)
        if isinstance(right, OptionalNode) and nodes_equivalent(right.inner, left):
            return right
        if isinstance(left, OptionalNode) and nodes_equivalent(left.inner, right):
            return left

        # LOWER PRIORITY: General epsilon rules
        # Rule: ε|R → R? (only for non-star/plus R)
        if isinstance(left, EpsilonNode):
            if not isinstance(right, (StarNode, PlusNode)):
                return OptionalNode(right).simplify()
        if isinstance(right, EpsilonNode):
            if not isinstance(left, (StarNode, PlusNode)):
                return OptionalNode(left).simplify()

        return UnionNode(left, right)


@dataclass
class ConcatNode(RegexNode):
    """Concatenation node (RS)"""
    left: RegexNode
    right: RegexNode

    def to_string(self) -> str:
        left_str = self.left.to_string()
        right_str = self.right.to_string()

        # Handle empty parts
        if not left_str:
            return right_str
        if not right_str:
            return left_str

        # Add parentheses for unions to preserve precedence
        if isinstance(self.left, UnionNode):
            left_str = f"({left_str})"
        if isinstance(self.right, UnionNode):
            right_str = f"({right_str})"

        return f"{left_str}{right_str}"

    def simplify(self) -> 'RegexNode':
        left = self.left.simplify()
        right = self.right.simplify()

        # Rule: ∅R → ∅, R∅ → ∅ (empty set annihilator)
        if isinstance(left, EmptySetNode) or isinstance(right, EmptySetNode):
            return EmptySetNode()

        # Rule: εR → R, Rε → R (epsilon identity)
        if isinstance(left, (EpsilonNode, EmptyGroupNode)):
            return right
        if isinstance(right, (EpsilonNode, EmptyGroupNode)):
            return left

        # VALID RULE: RR* → R+ (R followed by 0+ Rs = 1+ Rs)
        if isinstance(right, StarNode) and nodes_equivalent(left, right.inner):
            return PlusNode(left).simplify()

        # VALID RULE: R*R → R+ (0+ Rs followed by R = 1+ Rs)
        if isinstance(left, StarNode) and nodes_equivalent(right, left.inner):
            return PlusNode(right).simplify()

        # RULE: X(YX)*Y → (XY)+
        # Example: b(ab)*a → (ba)+
        if (isinstance(left, CharNode) and isinstance(right, ConcatNode) and
                isinstance(right.left, StarNode) and isinstance(right.right, CharNode)):

            X = left  # b
            star_node = right.left  # (ab)*
            Y = right.right  # a

            # Check if the star contains YX (i.e., ab where Y=a, X=b)
            if (isinstance(star_node.inner, ConcatNode) and
                    isinstance(star_node.inner.left, CharNode) and
                    isinstance(star_node.inner.right, CharNode)):

                star_Y = star_node.inner.left  # a from (ab)*
                star_X = star_node.inner.right  # b from (ab)*

                # Check if we have X(YX)*Y pattern: b(ab)*a
                if (X.char == star_X.char and Y.char == star_Y.char):
                    # Transform to (XY)+: (ba)+
                    xy_concat = ConcatNode(X, Y)
                    return PlusNode(xy_concat).simplify()

        # Handle nested concatenation patterns like a(b(ab)*) → (ab)+
        if (isinstance(left, CharNode) and isinstance(right, ConcatNode) and
                isinstance(right.right, StarNode)):
            right_left = right.left
            star_inner = right.right.inner

            if (isinstance(right_left, CharNode) and isinstance(star_inner, ConcatNode) and
                    isinstance(star_inner.left, CharNode) and isinstance(star_inner.right, CharNode)):
                X = left
                Y = right_left
                star_X = star_inner.left
                star_Y = star_inner.right

                if (X.char == star_X.char and Y.char == star_Y.char):
                    xy_concat = ConcatNode(X, Y)
                    return PlusNode(xy_concat).simplify()

        # Nested concatenation like a(bb*) → ab+
        if isinstance(right, ConcatNode):
            right_simplified = right.simplify()
            if not nodes_equivalent(right_simplified, right):
                return ConcatNode(left, right_simplified).simplify()

        return ConcatNode(left, right)


@dataclass
class StarNode(RegexNode):
    """Kleene star node (R*)."""
    inner: RegexNode

    def to_string(self) -> str:
        inner_str = self.inner.to_string()

        # Handle empty groups
        if isinstance(self.inner, EmptyGroupNode):
            return ""  # ()* → delete

        # Add parentheses for complex expressions
        if isinstance(self.inner, (UnionNode, ConcatNode)):
            inner_str = f"({inner_str})"

        return f"{inner_str}*"

    def simplify(self) -> 'RegexNode':
        inner = self.inner.simplify()

        # Rule: ()* → ε (empty group star)
        if isinstance(inner, EmptyGroupNode):
            return EpsilonNode()

        # Rule: ε* → ε
        if isinstance(inner, EpsilonNode):
            return inner

        # Rule: ∅* → ε (empty set star is epsilon)
        if isinstance(inner, EmptySetNode):
            return EpsilonNode()

        # Multiple operator collapsing - (R*)* → R*
        if isinstance(inner, StarNode):
            return inner

        # Rule: (R+)* → R* (plus star becomes star)
        if isinstance(inner, PlusNode):
            return StarNode(inner.inner).simplify()

        # Rule: (R?)* → R* (optional star becomes star)
        if isinstance(inner, OptionalNode):
            return StarNode(inner.inner).simplify()

        return StarNode(inner)


@dataclass
class PlusNode(RegexNode):
    """Plus node (R+)."""
    inner: RegexNode

    def to_string(self) -> str:
        inner_str = self.inner.to_string()

        # Handle empty groups
        if isinstance(self.inner, EmptyGroupNode):
            return ""  # ()+ → delete

        # Add parentheses for complex expressions
        if isinstance(self.inner, (UnionNode, ConcatNode)):
            inner_str = f"({inner_str})"

        return f"{inner_str}+"

    def simplify(self) -> 'RegexNode':
        inner = self.inner.simplify()

        # Rule: ()+ → ε (empty group plus)
        if isinstance(inner, EmptyGroupNode):
            return EpsilonNode()

        # Rule: ε+ → ε
        if isinstance(inner, EpsilonNode):
            return inner

        # Rule: ∅+ → ∅ (empty set plus is empty set)
        if isinstance(inner, EmptySetNode):
            return inner

        # Rule: (R*)+ → R* (star plus becomes star)
        if isinstance(inner, StarNode):
            return inner

        # Multiple operator collapsing - (R+)+ → R+
        if isinstance(inner, PlusNode):
            return inner

        # Rule: (R?)+ → R* (optional plus becomes star)
        if isinstance(inner, OptionalNode):
            return StarNode(inner.inner).simplify()

        return PlusNode(inner)


@dataclass
class OptionalNode(RegexNode):
    """Optional node (R?)."""
    inner: RegexNode

    def to_string(self) -> str:
        inner_str = self.inner.to_string()

        # Handle empty groups
        if isinstance(self.inner, EmptyGroupNode):
            return ""  # ()? → delete

        # Add parentheses for complex expressions
        if isinstance(self.inner, (UnionNode, ConcatNode)):
            inner_str = f"({inner_str})"

        return f"{inner_str}?"

    def simplify(self) -> 'RegexNode':
        inner = self.inner.simplify()

        # Rule: ()? → ε (empty group optional)
        if isinstance(inner, EmptyGroupNode):
            return EpsilonNode()

        # Rule: ε? → ε
        if isinstance(inner, EpsilonNode):
            return inner

        # Rule: ∅? → ε (optional empty set is epsilon)
        if isinstance(inner, EmptySetNode):
            return EpsilonNode()

        # Rule: (R*)? → R* (optional star becomes star)
        if isinstance(inner, StarNode):
            return inner

        # Rule: (R+)? → R* (optional plus becomes star)
        if isinstance(inner, PlusNode):
            return StarNode(inner.inner).simplify()

        # Rule: Multiple operator collapsing - (R?)? → R?
        if isinstance(inner, OptionalNode):
            return inner

        return OptionalNode(inner)


@dataclass
class MultiOperatorNode(RegexNode):
    """Node to handle consecutive operators like a*+, a+*, etc."""
    inner: RegexNode
    operators: List[str]

    def to_string(self) -> str:
        inner_str = self.inner.to_string()
        if isinstance(self.inner, (UnionNode, ConcatNode)):
            inner_str = f"({inner_str})"
        return inner_str + "".join(self.operators)

    def simplify(self) -> 'RegexNode':
        inner = self.inner.simplify()

        # Collapse consecutive identical operators: a** → a*, a++ → a+, a?? → a?
        unique_operators = []
        for op in self.operators:
            if not unique_operators or unique_operators[-1] != op:
                unique_operators.append(op)

        # Apply operator precedence and dominance rules
        has_star = '*' in unique_operators
        has_plus = '+' in unique_operators
        has_optional = '?' in unique_operators

        # If there's a star anywhere, it dominates everything
        if has_star:
            return StarNode(inner).simplify()

        # If there's both plus and optional, it becomes star
        if has_plus and has_optional:
            return StarNode(inner).simplify()

        # If there's just plus(es), collapse to single plus
        if has_plus:
            return PlusNode(inner).simplify()

        # If there's just optional(s), collapse to single optional
        if has_optional:
            return OptionalNode(inner).simplify()

        # Fallback
        return inner


class RegexASTParser:
    """Parser that converts regex string to AST with operator handling."""

    def __init__(self, regex: str):
        self.regex = regex
        self.pos = 0

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

    def parse(self) -> RegexNode:
        """Parse regex and return AST root."""
        if not self.regex:
            return EpsilonNode()

        # Check for invalid start patterns
        if self.regex[0] in ['*', '+', '?']:
            raise ValueError(f"Regex cannot start with '{self.regex[0]}'")

        result = self.parse_union()
        if self.pos < len(self.regex):
            raise ValueError(f"Unexpected character '{self.regex[self.pos]}' at position {self.pos}")
        return result

    def parse_union(self) -> RegexNode:
        """Parse union (|) - lowest precedence."""
        left = self.parse_concat()

        if self.peek() == '|':
            self.consume()  # consume '|'

            if self.peek() in ['*', '+', '?']:
                raise ValueError(f"Unexpected '{self.peek()}' after '|'")

            right = self.parse_union()
            return UnionNode(left, right)

        return left

    def parse_concat(self) -> RegexNode:
        """Parse concatenation - implicit, higher precedence than union."""
        left = self.parse_postfix()

        # Check if there's more to concatenate
        next_char = self.peek()
        if (next_char is not None and
                next_char not in ['|', ')'] and
                self.pos < len(self.regex)):
            right = self.parse_concat()
            return ConcatNode(left, right)

        return left

    def parse_postfix(self) -> RegexNode:
        """Parse postfix operators (*, +, ?) with consecutive operator handling."""
        inner = self.parse_atom()

        # Collect all consecutive operators
        operators = []
        while self.peek() in ['*', '+', '?']:
            operators.append(self.consume())

        if not operators:
            return inner

        # If there's only one operator, handle normally
        if len(operators) == 1:
            op = operators[0]
            if op == '*':
                return StarNode(inner)
            elif op == '+':
                return PlusNode(inner)
            elif op == '?':
                return OptionalNode(inner)

        # Multiple operators - use MultiOperatorNode for proper simplification
        return MultiOperatorNode(inner, operators)

    def parse_atom(self) -> RegexNode:
        """Parse atomic expressions."""
        char = self.peek()

        if char == '(':
            self.consume()  # consume '('

            # Check for empty group
            if self.peek() == ')':
                self.consume()  # consume ')'
                return EmptyGroupNode()

            inner = self.parse_union()
            if self.peek() != ')':
                raise ValueError(f"Expected ')' at position {self.pos}")
            self.consume()  # consume ')'
            return inner

        elif char == 'ε':
            self.consume()
            return EpsilonNode()

        elif char == '∅':
            self.consume()
            return EmptySetNode()

        elif char and char not in ['|', ')', '*', '+', '?']:
            self.consume()
            return CharNode(char)

        elif char in ['*', '+', '?']:
            raise ValueError(f"Unexpected '{char}' at position {self.pos}")

        else:
            return EpsilonNode()


def _detect_char_star_patterns(node: RegexNode) -> RegexNode:
    """
    Helper function to detect and simplify aa* patterns throughout the AST.
    """
    if isinstance(node, ConcatNode):
        left = _detect_char_star_patterns(node.left)
        right = _detect_char_star_patterns(node.right)

        # Pattern: any element followed by its star
        if isinstance(right, StarNode) and nodes_equivalent(left, right.inner):
            return PlusNode(left).simplify()

        # The original key pattern: a followed by a*
        if isinstance(left, CharNode) and isinstance(right, StarNode):
            if isinstance(right.inner, CharNode) and left.char == right.inner.char:
                return PlusNode(left).simplify()

        # Re-simplify the result
        result = ConcatNode(left, right)
        return result.simplify()

    elif isinstance(node, UnionNode):
        left = _detect_char_star_patterns(node.left)
        right = _detect_char_star_patterns(node.right)
        result = UnionNode(left, right)
        return result.simplify()

    elif isinstance(node, StarNode):
        inner = _detect_char_star_patterns(node.inner)
        result = StarNode(inner)
        return result.simplify()

    elif isinstance(node, PlusNode):
        inner = _detect_char_star_patterns(node.inner)
        result = PlusNode(inner)
        return result.simplify()

    elif isinstance(node, OptionalNode):
        inner = _detect_char_star_patterns(node.inner)
        result = OptionalNode(inner)
        return result.simplify()

    elif isinstance(node, MultiOperatorNode):
        inner = _detect_char_star_patterns(node.inner)
        result = MultiOperatorNode(inner, node.operators)
        return result.simplify()

    else:
        # Leaf nodes
        return node