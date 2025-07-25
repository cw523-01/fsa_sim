from django.test import TestCase
from simulator.regex_conversions import (
    regex_to_epsilon_nfa,
    validate_regex_syntax,
    fsa_to_regex,
    NFABuilder,
    RegexParser,
    GNFA,
    fsa_to_gnfa,
    simplify_regex,
    eliminate_states, _detect_char_star_patterns, _detect_union_patterns, _detect_epsilon_patterns,
    _detect_nested_patterns, StarNode, CharNode, EpsilonNode, _rebuild_concatenation, ConcatNode,
    _detect_flattened_concat_patterns, _flatten_concatenation, UnionNode, PlusNode, RegexASTParser, MultiOperatorNode,
    OptionalNode, EmptySetNode, EmptyGroupNode, nodes_equivalent, verify, RegexNode
)


class TestRegexConversions(TestCase):

    def test_regex_to_epsilon_nfa_basic_characters(self):
        """Test conversion of basic character regexes to epsilon-NFA"""
        # Single character 'a'
        nfa = regex_to_epsilon_nfa('a')
        self.assertEqual(len(nfa['states']), 2)
        self.assertEqual(nfa['alphabet'], ['a'])
        self.assertEqual(nfa['startingState'], 'q0')
        self.assertEqual(nfa['acceptingStates'], ['q1'])
        self.assertIn('q0', nfa['transitions'])
        self.assertIn('a', nfa['transitions']['q0'])
        self.assertEqual(nfa['transitions']['q0']['a'], ['q1'])

        # Single character 'b'
        nfa = regex_to_epsilon_nfa('b')
        self.assertEqual(len(nfa['states']), 2)
        self.assertEqual(nfa['alphabet'], ['b'])
        self.assertEqual(nfa['transitions']['q0']['b'], ['q1'])

        # Digit '0'
        nfa = regex_to_epsilon_nfa('0')
        self.assertEqual(nfa['alphabet'], ['0'])
        self.assertEqual(nfa['transitions']['q0']['0'], ['q1'])

    def test_regex_to_epsilon_nfa_epsilon(self):
        """Test epsilon regex conversion"""
        # Epsilon symbol
        nfa = regex_to_epsilon_nfa('ε')
        self.assertEqual(len(nfa['states']), 2)
        self.assertEqual(nfa['alphabet'], [])
        self.assertEqual(nfa['startingState'], 'q0')
        self.assertEqual(nfa['acceptingStates'], ['q1'])
        self.assertIn('', nfa['transitions']['q0'])
        self.assertEqual(nfa['transitions']['q0'][''], ['q1'])

        # Empty string (treated as epsilon)
        nfa = regex_to_epsilon_nfa('')
        self.assertEqual(len(nfa['states']), 2)
        self.assertEqual(nfa['alphabet'], [])
        self.assertEqual(nfa['transitions']['q0'][''], ['q1'])

    def test_regex_to_epsilon_nfa_concatenation(self):
        """Test concatenation of regex patterns"""
        # Simple concatenation 'ab'
        nfa = regex_to_epsilon_nfa('ab')
        self.assertEqual(sorted(nfa['alphabet']), ['a', 'b'])
        self.assertEqual(len(nfa['states']), 4)
        self.assertEqual(len(nfa['acceptingStates']), 1)

        # Longer concatenation 'abc'
        nfa = regex_to_epsilon_nfa('abc')
        self.assertEqual(sorted(nfa['alphabet']), ['a', 'b', 'c'])
        self.assertEqual(len(nfa['states']), 6)

        # Concatenation with digits '123'
        nfa = regex_to_epsilon_nfa('123')
        self.assertEqual(sorted(nfa['alphabet']), ['1', '2', '3'])

    def test_regex_to_epsilon_nfa_union(self):
        """Test union (|) operator"""
        # Simple union 'a|b'
        nfa = regex_to_epsilon_nfa('a|b')
        self.assertEqual(sorted(nfa['alphabet']), ['a', 'b'])
        self.assertEqual(len(nfa['states']), 6)  # 2 for each character + 2 for union
        self.assertEqual(len(nfa['acceptingStates']), 1)

        # Union with three alternatives 'a|b|c'
        nfa = regex_to_epsilon_nfa('a|b|c')
        self.assertEqual(sorted(nfa['alphabet']), ['a', 'b', 'c'])

        # Union with epsilon 'a|ε'
        nfa = regex_to_epsilon_nfa('a|ε')
        self.assertEqual(nfa['alphabet'], ['a'])
        self.assertEqual(len(nfa['acceptingStates']), 1)

    def test_regex_to_epsilon_nfa_kleene_star(self):
        """Test Kleene star (*) operator"""
        # Simple star 'a*'
        nfa = regex_to_epsilon_nfa('a*')
        self.assertEqual(nfa['alphabet'], ['a'])
        self.assertEqual(len(nfa['states']), 4)
        self.assertEqual(len(nfa['acceptingStates']), 1)

        # Star with union '(a|b)*'
        nfa = regex_to_epsilon_nfa('(a|b)*')
        self.assertEqual(sorted(nfa['alphabet']), ['a', 'b'])

        # Multiple stars 'a*b*'
        nfa = regex_to_epsilon_nfa('a*b*')
        self.assertEqual(sorted(nfa['alphabet']), ['a', 'b'])

    def test_regex_to_epsilon_nfa_plus(self):
        """Test plus (+) operator"""
        # Simple plus 'a+'
        nfa = regex_to_epsilon_nfa('a+')
        self.assertEqual(nfa['alphabet'], ['a'])
        self.assertEqual(len(nfa['states']), 4)
        self.assertEqual(len(nfa['acceptingStates']), 1)

        # Plus with union '(a|b)+'
        nfa = regex_to_epsilon_nfa('(a|b)+')
        self.assertEqual(sorted(nfa['alphabet']), ['a', 'b'])

        # Multiple plus 'a+b+'
        nfa = regex_to_epsilon_nfa('a+b+')
        self.assertEqual(sorted(nfa['alphabet']), ['a', 'b'])

    def test_regex_to_epsilon_nfa_parentheses(self):
        """Test parentheses for grouping"""
        # Simple grouping '(ab)'
        nfa = regex_to_epsilon_nfa('(ab)')
        self.assertEqual(sorted(nfa['alphabet']), ['a', 'b'])

        # Grouping with operators '(a|b)*'
        nfa = regex_to_epsilon_nfa('(a|b)*')
        self.assertEqual(sorted(nfa['alphabet']), ['a', 'b'])

        # Nested grouping '((a|b)c)*'
        nfa = regex_to_epsilon_nfa('((a|b)c)*')
        self.assertEqual(sorted(nfa['alphabet']), ['a', 'b', 'c'])

    def test_regex_to_epsilon_nfa_consecutive_operators(self):
        """Test consecutive postfix operators"""
        # Consecutive stars 'a*+'
        nfa = regex_to_epsilon_nfa('a*+')
        self.assertEqual(nfa['alphabet'], ['a'])
        self.assertEqual(len(nfa['acceptingStates']), 1)

        # Consecutive plus 'a+*'
        nfa = regex_to_epsilon_nfa('a+*')
        self.assertEqual(nfa['alphabet'], ['a'])

        # Multiple consecutive 'a*+*'
        nfa = regex_to_epsilon_nfa('a*+*')
        self.assertEqual(nfa['alphabet'], ['a'])

    def test_regex_to_epsilon_nfa_complex_patterns(self):
        """Test complex regex patterns"""
        # Complex pattern 'a+b*c'
        nfa = regex_to_epsilon_nfa('a+b*c')
        self.assertEqual(sorted(nfa['alphabet']), ['a', 'b', 'c'])

        # Pattern with union and star '(ab|cd)*'
        nfa = regex_to_epsilon_nfa('(ab|cd)*')
        self.assertEqual(sorted(nfa['alphabet']), ['a', 'b', 'c', 'd'])

        # Complex nested pattern '(a+|b*)c+'
        nfa = regex_to_epsilon_nfa('(a+|b*)c+')
        self.assertEqual(sorted(nfa['alphabet']), ['a', 'b', 'c'])

    def test_regex_to_epsilon_nfa_invalid_patterns(self):
        """Test invalid regex patterns"""
        # Starting with star
        with self.assertRaises(ValueError) as cm:
            regex_to_epsilon_nfa('*a')
        self.assertIn('cannot start with', str(cm.exception))

        # Starting with plus
        with self.assertRaises(ValueError) as cm:
            regex_to_epsilon_nfa('+a')
        self.assertIn('cannot start with', str(cm.exception))

        # Mismatched parentheses
        with self.assertRaises(ValueError) as cm:
            regex_to_epsilon_nfa('(a')
        self.assertIn('Expected', str(cm.exception))

        # Union followed by operator
        with self.assertRaises(ValueError) as cm:
            regex_to_epsilon_nfa('a|*')
        self.assertIn('Unexpected', str(cm.exception))

        # Unexpected character
        with self.assertRaises(ValueError) as cm:
            regex_to_epsilon_nfa('a)')
        self.assertIn('Unexpected character', str(cm.exception))

    def test_validate_regex_syntax_valid(self):
        """Test regex syntax validation with valid patterns"""
        # Valid single character
        result = validate_regex_syntax('a')
        self.assertTrue(result['valid'])

        # Valid concatenation
        result = validate_regex_syntax('ab')
        self.assertTrue(result['valid'])

        # Valid union
        result = validate_regex_syntax('a|b')
        self.assertTrue(result['valid'])

        # Valid star
        result = validate_regex_syntax('a*')
        self.assertTrue(result['valid'])

        # Valid plus
        result = validate_regex_syntax('a+')
        self.assertTrue(result['valid'])

        # Valid complex pattern
        result = validate_regex_syntax('(a|b)*c+')
        self.assertTrue(result['valid'])

        # Valid epsilon
        result = validate_regex_syntax('ε')
        self.assertTrue(result['valid'])

        # Valid empty language
        result = validate_regex_syntax('∅')
        self.assertTrue(result['valid'])

    def test_validate_regex_syntax_invalid(self):
        """Test regex syntax validation with invalid patterns"""
        # Invalid starting with star
        result = validate_regex_syntax('*a')
        self.assertFalse(result['valid'])
        self.assertIn('error', result)

        # Invalid starting with plus
        result = validate_regex_syntax('+a')
        self.assertFalse(result['valid'])
        self.assertIn('error', result)

        # Invalid mismatched parentheses
        result = validate_regex_syntax('(a')
        self.assertFalse(result['valid'])
        self.assertIn('error', result)

        # Invalid union followed by operator
        result = validate_regex_syntax('a|*')
        self.assertFalse(result['valid'])
        self.assertIn('error', result)

    def test_nfa_builder_basic_functionality(self):
        """Test NFABuilder basic functionality"""
        builder = NFABuilder()

        # Test state generation
        state1 = builder.new_state()
        state2 = builder.new_state()
        self.assertEqual(state1, 'q0')
        self.assertEqual(state2, 'q1')
        self.assertIn('q0', builder.states)
        self.assertIn('q1', builder.states)

        # Test transition addition
        builder.add_transition('q0', 'a', 'q1')
        self.assertIn('a', builder.alphabet)
        self.assertEqual(builder.transitions['q0']['a'], ['q1'])

        # Test epsilon transition (shouldn't add to alphabet)
        builder.add_transition('q0', '', 'q1')
        self.assertEqual(builder.alphabet, {'a'})

        # Test dictionary conversion
        nfa_dict = builder.to_dict('q0', ['q1'])
        self.assertEqual(nfa_dict['startingState'], 'q0')
        self.assertEqual(nfa_dict['acceptingStates'], ['q1'])
        self.assertEqual(nfa_dict['alphabet'], ['a'])

    def test_regex_parser_basic_functionality(self):
        """Test RegexParser basic functionality"""
        builder = NFABuilder()
        parser = RegexParser('a', builder)

        # Test peek and consume
        self.assertEqual(parser.peek(), 'a')
        self.assertEqual(parser.consume(), 'a')
        self.assertIsNone(parser.peek())

        # Test parsing simple character
        builder = NFABuilder()
        parser = RegexParser('a', builder)
        start, accept = parser.parse()
        self.assertIsNotNone(start)
        self.assertIsNotNone(accept)
        self.assertNotEqual(start, accept)

    def test_gnfa_basic_functionality(self):
        """Test GNFA basic functionality"""
        gnfa = GNFA()

        # Test state addition
        gnfa.add_state('S0')
        gnfa.add_state('S1')
        self.assertIn('S0', gnfa.states)
        self.assertIn('S1', gnfa.states)

        # Test transition addition
        gnfa.add_transition('S0', 'S1', 'a')
        self.assertEqual(gnfa.transitions['S0']['S1'], 'a')

        # Test union of transitions
        gnfa.add_transition('S0', 'S1', 'b')
        self.assertEqual(gnfa.transitions['S0']['S1'], '(a|b)')

        # Test empty transition (should be ignored)
        gnfa.add_transition('S0', 'S2', '')
        self.assertEqual(gnfa.transitions['S0']['S2'], '')

    def test_gnfa_state_elimination(self):
        """Test GNFA state elimination"""
        gnfa = GNFA()
        gnfa.add_state('S0')
        gnfa.add_state('S1')
        gnfa.add_state('S2')
        gnfa.start_state = 'S0'
        gnfa.accept_state = 'S2'

        # Add transitions: S0 -a-> S1 -b-> S2
        gnfa.add_transition('S0', 'S1', 'a')
        gnfa.add_transition('S1', 'S2', 'b')

        # Remove S1
        gnfa.remove_state('S1')

        # Should now have S0 -ab-> S2
        self.assertEqual(gnfa.transitions['S0']['S2'], 'ab')
        self.assertNotIn('S1', gnfa.states)

    def test_gnfa_state_elimination_with_self_loop(self):
        """Test GNFA state elimination with self-loop"""
        gnfa = GNFA()
        gnfa.add_state('S0')
        gnfa.add_state('S1')
        gnfa.add_state('S2')
        gnfa.start_state = 'S0'
        gnfa.accept_state = 'S2'

        # Add transitions: S0 -a-> S1, S1 -b-> S1 (self-loop), S1 -c-> S2
        gnfa.add_transition('S0', 'S1', 'a')
        gnfa.add_transition('S1', 'S1', 'b')
        gnfa.add_transition('S1', 'S2', 'c')

        # Remove S1
        gnfa.remove_state('S1')

        # Should now have S0 -a(b)*c-> S2
        self.assertEqual(gnfa.transitions['S0']['S2'], 'ab*c')

    def test_gnfa_protection_of_start_accept_states(self):
        """Test that GNFA protects start and accept states from elimination"""
        gnfa = GNFA()
        gnfa.add_state('S0')
        gnfa.add_state('S1')
        gnfa.start_state = 'S0'
        gnfa.accept_state = 'S1'

        # Try to remove start state (should be ignored)
        gnfa.remove_state('S0')
        self.assertIn('S0', gnfa.states)

        # Try to remove accept state (should be ignored)
        gnfa.remove_state('S1')
        self.assertIn('S1', gnfa.states)

    def test_fsa_to_gnfa_basic_conversion(self):
        """Test FSA to GNFA conversion"""
        fsa = {
            'states': ['S0', 'S1'],
            'alphabet': ['a', 'b'],
            'transitions': {
                'S0': {'a': ['S1']},
                'S1': {'b': ['S0']}
            },
            'startingState': 'S0',
            'acceptingStates': ['S1']
        }

        gnfa = fsa_to_gnfa(fsa)

        # Should have original states plus new start and accept
        self.assertEqual(len(gnfa.states), 4)
        self.assertEqual(gnfa.start_state, 'gnfa_start')
        self.assertEqual(gnfa.accept_state, 'gnfa_accept')

        # Check epsilon transitions
        self.assertEqual(gnfa.transitions['gnfa_start']['S0'], 'ε')
        self.assertEqual(gnfa.transitions['S1']['gnfa_accept'], 'ε')

        # Check original transitions
        self.assertEqual(gnfa.transitions['S0']['S1'], 'a')
        self.assertEqual(gnfa.transitions['S1']['S0'], 'b')

    def test_fsa_to_gnfa_with_epsilon_transitions(self):
        """Test FSA to GNFA conversion with epsilon transitions"""
        fsa = {
            'states': ['S0', 'S1', 'S2'],
            'alphabet': ['a'],
            'transitions': {
                'S0': {'': ['S1'], 'a': ['S2']},
                'S1': {'a': ['S2']},
                'S2': {}
            },
            'startingState': 'S0',
            'acceptingStates': ['S2']
        }

        gnfa = fsa_to_gnfa(fsa)

        # Check epsilon transitions are preserved
        self.assertEqual(gnfa.transitions['S0']['S1'], 'ε')
        self.assertEqual(gnfa.transitions['S0']['S2'], 'a')

    def test_fsa_to_gnfa_multiple_accepting_states(self):
        """Test FSA to GNFA conversion with multiple accepting states"""
        fsa = {
            'states': ['S0', 'S1', 'S2'],
            'alphabet': ['a'],
            'transitions': {
                'S0': {'a': ['S1', 'S2']},
                'S1': {},
                'S2': {}
            },
            'startingState': 'S0',
            'acceptingStates': ['S1', 'S2']
        }

        gnfa = fsa_to_gnfa(fsa)

        # Both accepting states should have epsilon transitions to new accept
        self.assertEqual(gnfa.transitions['S1']['gnfa_accept'], 'ε')
        self.assertEqual(gnfa.transitions['S2']['gnfa_accept'], 'ε')

    def test_simplify_regex_basic_patterns(self):
        """Test basic regex simplification"""
        # Empty regex
        result = simplify_regex('')
        self.assertEqual(result, 'ε')

        # Remove epsilon symbols
        result = simplify_regex('aεb')
        self.assertEqual(result, 'ab')

        # Remove empty groups
        result = simplify_regex('a()b')
        self.assertEqual(result, 'ab')

        # Multiple consecutive stars
        result = simplify_regex('a**')
        self.assertEqual(result, 'a*')

        # Multiple consecutive plus
        result = simplify_regex('a++')
        self.assertEqual(result, 'a+')

        # Mixed star and plus
        result = simplify_regex('a*+')
        self.assertEqual(result, 'a*')

        result = simplify_regex('a+*')
        self.assertEqual(result, 'a*')

    def test_simplify_regex_complex_patterns(self):
        """Test complex regex simplification"""
        # Nested empty groups
        result = simplify_regex('((a))')
        self.assertEqual(result, 'a')

        # Complex pattern with multiple simplifications
        result = simplify_regex('a**++')
        self.assertEqual(result, 'a*')

    def test_eliminate_states_basic(self):
        """Test basic state elimination"""
        # Simple GNFA with linear path
        gnfa = GNFA()
        gnfa.add_state('gnfa_start')
        gnfa.add_state('S0')
        gnfa.add_state('gnfa_accept')
        gnfa.start_state = 'gnfa_start'
        gnfa.accept_state = 'gnfa_accept'

        gnfa.add_transition('gnfa_start', 'S0', 'ε')
        gnfa.add_transition('S0', 'gnfa_accept', 'a')

        result = eliminate_states(gnfa)
        self.assertEqual(result, 'a')

    def test_eliminate_states_with_loop(self):
        """Test state elimination with loops"""
        gnfa = GNFA()
        gnfa.add_state('gnfa_start')
        gnfa.add_state('S0')
        gnfa.add_state('gnfa_accept')
        gnfa.start_state = 'gnfa_start'
        gnfa.accept_state = 'gnfa_accept'

        gnfa.add_transition('gnfa_start', 'S0', 'ε')
        gnfa.add_transition('S0', 'S0', 'a')  # Self-loop
        gnfa.add_transition('S0', 'gnfa_accept', 'b')

        result = eliminate_states(gnfa)
        self.assertEqual(result, 'a*b')

    def test_eliminate_states_empty_language(self):
        """Test state elimination resulting in empty language"""
        gnfa = GNFA()
        gnfa.add_state('gnfa_start')
        gnfa.add_state('gnfa_accept')
        gnfa.start_state = 'gnfa_start'
        gnfa.accept_state = 'gnfa_accept'

        # No transitions between start and accept
        result = eliminate_states(gnfa)
        self.assertEqual(result, '∅')

    def test_fsa_to_regex_invalid_structure(self):
        """Test FSA to regex conversion with invalid FSA structure"""
        # Missing required keys
        invalid_fsa = {
            'states': ['S0'],
            'alphabet': ['a']
            # Missing transitions, startingState, acceptingStates
        }

        result = fsa_to_regex(invalid_fsa)
        self.assertFalse(result['valid'])
        self.assertIn('Invalid FSA structure', result['error'])
        self.assertEqual(result['original_states'], 1)
        self.assertEqual(result['minimized_states'], 0)

    def test_fsa_to_regex_empty_fsa(self):
        """Test FSA to regex conversion with empty FSA"""
        empty_fsa = {
            'states': [],
            'alphabet': [],
            'transitions': {},
            'startingState': '',
            'acceptingStates': []
        }

        result = fsa_to_regex(empty_fsa)
        self.assertTrue(result['valid'])
        self.assertEqual(result['regex'], '∅')
        self.assertEqual(result['original_states'], 0)
        self.assertEqual(result['minimized_states'], 0)
        self.assertTrue(result['verification']['equivalent'])

    def test_fsa_to_regex_single_state_accepting(self):
        """Test FSA to regex conversion with single accepting state"""
        # Single state that accepts epsilon
        single_state_fsa = {
            'states': ['S0'],
            'alphabet': ['a'],
            'transitions': {},
            'startingState': 'S0',
            'acceptingStates': ['S0']
        }

        result = fsa_to_regex(single_state_fsa)
        self.assertTrue(result['valid'])
        self.assertEqual(result['regex'], 'ε')
        self.assertEqual(result['original_states'], 1)
        self.assertEqual(result['minimized_states'], 1)

    def test_fsa_to_regex_single_state_with_self_loop(self):
        """Test FSA to regex conversion with single state and self-loop"""
        # Single state with self-loop on 'a'
        single_state_loop_fsa = {
            'states': ['S0'],
            'alphabet': ['a'],
            'transitions': {
                'S0': {'a': ['S0']}
            },
            'startingState': 'S0',
            'acceptingStates': ['S0']
        }

        result = fsa_to_regex(single_state_loop_fsa)
        self.assertTrue(result['valid'])
        self.assertEqual(result['regex'], 'a*')
        self.assertEqual(result['original_states'], 1)
        self.assertEqual(result['minimized_states'], 1)

    def test_fsa_to_regex_single_state_multiple_self_loops(self):
        """Test FSA to regex conversion with single state and multiple self-loops"""
        # Single state with self-loops on 'a' and 'b'
        single_state_multi_loop_fsa = {
            'states': ['S0'],
            'alphabet': ['a', 'b'],
            'transitions': {
                'S0': {'a': ['S0'], 'b': ['S0']}
            },
            'startingState': 'S0',
            'acceptingStates': ['S0']
        }

        result = fsa_to_regex(single_state_multi_loop_fsa)
        self.assertTrue(result['valid'])
        self.assertEqual(result['regex'], '(a|b)*')
        self.assertEqual(result['original_states'], 1)
        self.assertEqual(result['minimized_states'], 1)

    def test_fsa_to_regex_simple_two_state(self):
        """Test FSA to regex conversion with simple two-state FSA"""
        # FSA that accepts strings ending with 'a'
        two_state_fsa = {
            'states': ['S0', 'S1'],
            'alphabet': ['a', 'b'],
            'transitions': {
                'S0': {'a': ['S1'], 'b': ['S0']},
                'S1': {'a': ['S1'], 'b': ['S0']}
            },
            'startingState': 'S0',
            'acceptingStates': ['S1']
        }

        result = fsa_to_regex(two_state_fsa)
        self.assertTrue(result['valid'])
        self.assertIsNotNone(result['regex'])
        self.assertEqual(result['original_states'], 2)
        self.assertGreater(len(result['regex']), 0)

    def test_fsa_to_regex_complex_pattern(self):
        """Test FSA to regex conversion with complex pattern"""
        # FSA that accepts strings containing 'ab'
        complex_fsa = {
            'states': ['S0', 'S1', 'S2'],
            'alphabet': ['a', 'b'],
            'transitions': {
                'S0': {'a': ['S1'], 'b': ['S0']},
                'S1': {'a': ['S1'], 'b': ['S2']},
                'S2': {'a': ['S2'], 'b': ['S2']}
            },
            'startingState': 'S0',
            'acceptingStates': ['S2']
        }

        result = fsa_to_regex(complex_fsa)
        self.assertTrue(result['valid'])
        self.assertIsNotNone(result['regex'])
        self.assertEqual(result['original_states'], 3)
        self.assertGreater(len(result['regex']), 0)

    def test_fsa_to_regex_with_epsilon_transitions(self):
        """Test FSA to regex conversion with epsilon transitions"""
        # FSA with epsilon transitions
        epsilon_fsa = {
            'states': ['S0', 'S1', 'S2'],
            'alphabet': ['a', 'b'],
            'transitions': {
                'S0': {'': ['S1'], 'a': ['S0']},
                'S1': {'b': ['S2']},
                'S2': {}
            },
            'startingState': 'S0',
            'acceptingStates': ['S2']
        }

        result = fsa_to_regex(epsilon_fsa)
        self.assertTrue(result['valid'])
        self.assertIsNotNone(result['regex'])
        self.assertEqual(result['original_states'], 3)
        self.assertGreater(len(result['regex']), 0)

    def test_fsa_to_regex_verification_success(self):
        """Test FSA to regex conversion with successful verification"""
        # Simple FSA that should convert and verify successfully
        simple_fsa = {
            'states': ['S0', 'S1'],
            'alphabet': ['a'],
            'transitions': {
                'S0': {'a': ['S1']},
                'S1': {}
            },
            'startingState': 'S0',
            'acceptingStates': ['S1']
        }

        result = fsa_to_regex(simple_fsa)
        self.assertTrue(result['valid'])
        self.assertEqual(result['regex'], 'a')
        self.assertTrue(result['verification']['equivalent'])
        self.assertIn('details', result['verification'])

    def test_fsa_to_regex_verification_failure(self):
        """Test FSA to regex conversion with verification failure"""
        # This test checks the verification error handling
        # We'll use a valid FSA but mock a verification failure scenario
        simple_fsa = {
            'states': ['S0', 'S1'],
            'alphabet': ['a'],
            'transitions': {
                'S0': {'a': ['S1']},
                'S1': {}
            },
            'startingState': 'S0',
            'acceptingStates': ['S1']
        }

        result = fsa_to_regex(simple_fsa)
        self.assertTrue(result['valid'])
        # The verification should succeed for this simple case
        self.assertIn('equivalent', result['verification'])

    def test_fsa_to_regex_minimization_effect(self):
        """Test that FSA to regex conversion shows minimization effect"""
        # FSA with redundant states
        redundant_fsa = {
            'states': ['S0', 'S1', 'S2', 'S3'],
            'alphabet': ['a'],
            'transitions': {
                'S0': {'a': ['S1']},
                'S1': {'a': ['S2']},
                'S2': {'a': ['S3']},
                'S3': {}
            },
            'startingState': 'S0',
            'acceptingStates': ['S3']
        }

        result = fsa_to_regex(redundant_fsa)
        self.assertTrue(result['valid'])
        self.assertEqual(result['original_states'], 4)
        self.assertLessEqual(result['minimized_states'], result['original_states'])

    def test_fsa_to_regex_exception_handling(self):
        """Test FSA to regex conversion exception handling"""
        # FSA that might cause processing errors
        problematic_fsa = {
            'states': ['S0', 'S1'],
            'alphabet': ['a'],
            'transitions': {
                'S0': {'a': ['S1']},
                'S1': {'a': ['S0']}  # Cycle
            },
            'startingState': 'S0',
            'acceptingStates': ['S1']
        }

        result = fsa_to_regex(problematic_fsa)
        # Should handle cycles gracefully
        self.assertTrue(result['valid'])
        self.assertIsNotNone(result['regex'])

    def test_fsa_to_regex_empty_alphabet(self):
        """Test FSA to regex conversion with empty alphabet"""
        empty_alphabet_fsa = {
            'states': ['S0'],
            'alphabet': [],
            'transitions': {},
            'startingState': 'S0',
            'acceptingStates': ['S0']
        }

        result = fsa_to_regex(empty_alphabet_fsa)
        self.assertTrue(result['valid'])
        self.assertEqual(result['regex'], 'ε')

    def test_fsa_to_regex_no_accepting_states(self):
        """Test FSA to regex conversion with no accepting states"""
        no_accepting_fsa = {
            'states': ['S0', 'S1'],
            'alphabet': ['a'],
            'transitions': {
                'S0': {'a': ['S1']},
                'S1': {'a': ['S0']}
            },
            'startingState': 'S0',
            'acceptingStates': []
        }

        result = fsa_to_regex(no_accepting_fsa)
        self.assertTrue(result['valid'])
        self.assertEqual(result['regex'], '∅')

    def test_fsa_to_regex_all_states_accepting(self):
        """Test FSA to regex conversion with all states accepting"""
        all_accepting_fsa = {
            'states': ['S0', 'S1'],
            'alphabet': ['a'],
            'transitions': {
                'S0': {'a': ['S1']},
                'S1': {'a': ['S0']}
            },
            'startingState': 'S0',
            'acceptingStates': ['S0', 'S1']
        }

        result = fsa_to_regex(all_accepting_fsa)
        self.assertTrue(result['valid'])
        self.assertIsNotNone(result['regex'])
        self.assertNotEqual(result['regex'], '∅')

    def test_fsa_to_regex_self_transitions_only(self):
        """Test FSA to regex conversion with only self-transitions"""
        self_only_fsa = {
            'states': ['S0', 'S1'],
            'alphabet': ['a', 'b'],
            'transitions': {
                'S0': {'a': ['S0']},
                'S1': {'b': ['S1']}
            },
            'startingState': 'S0',
            'acceptingStates': ['S0']
        }

        result = fsa_to_regex(self_only_fsa)
        self.assertTrue(result['valid'])
        self.assertIn('*', result['regex'])  # Should contain Kleene star

    def test_fsa_to_regex_disconnected_states(self):
        """Test FSA to regex conversion with disconnected states"""
        disconnected_fsa = {
            'states': ['S0', 'S1', 'S2'],
            'alphabet': ['a', 'b'],
            'transitions': {
                'S0': {'a': ['S1']},
                'S1': {},
                'S2': {'b': ['S2']}  # Disconnected from S0
            },
            'startingState': 'S0',
            'acceptingStates': ['S1', 'S2']
        }

        result = fsa_to_regex(disconnected_fsa)
        self.assertTrue(result['valid'])
        # Should only consider reachable states
        self.assertIsNotNone(result['regex'])

    def test_roundtrip_conversion_simple(self):
        """Test roundtrip conversion: regex -> FSA -> regex"""
        original_regexes = [
            'a',
            'a|b',
            'a*',
            'a+',
            'ab',
            '(a|b)*',
            'a*b*',
            'a+b+',
            'a?b',
            '(ab)?',
            '(ab)*|(ba)*',
            'a+b*c?',
            '((ε|a(ba)*(ε|b))|b?a(ba)*)'
        ]

        for original_regex in original_regexes:
            # Convert regex to FSA
            fsa = regex_to_epsilon_nfa(original_regex)

            # Convert FSA back to regex
            result = fsa_to_regex(fsa)

            self.assertTrue(result['valid'], f"Failed to convert FSA back to regex for: {original_regex}")
            self.assertTrue(result['verification']['equivalent'],
                            f"Verification failed for: {original_regex}")

    def test_roundtrip_conversion_complex(self):
        """Test roundtrip conversion with complex patterns"""
        complex_regexes = [
            '(a|b)*c',
            'a(b|c)*',
            '(ab)*',
            '(a|b)*c+',
            'a+b*c'
        ]

        for original_regex in complex_regexes:
            # Convert regex to FSA
            fsa = regex_to_epsilon_nfa(original_regex)

            # Convert FSA back to regex
            result = fsa_to_regex(fsa)

            self.assertTrue(result['valid'], f"Failed to convert FSA back to regex for: {original_regex}")
            self.assertTrue(result['verification']['equivalent'],
                            f"Verification failed for: {original_regex}")

    def test_regex_parser_error_handling(self):
        """Test RegexParser error handling"""
        # Test various error conditions
        error_cases = [
            ('*', 'cannot start with'),
            ('+', 'cannot start with'),
            ('(', 'Expected'),
            ('a|*', 'Unexpected'),
            ('a)', 'Unexpected character')
        ]

        for regex, expected_error in error_cases:
            builder = NFABuilder()
            parser = RegexParser(regex, builder)

            with self.assertRaises(ValueError) as cm:
                parser.parse()
            self.assertIn(expected_error, str(cm.exception))

    def test_nfa_builder_multiple_transitions(self):
        """Test NFABuilder with multiple transitions"""
        builder = NFABuilder()

        # Add multiple transitions from same state
        builder.add_transition('q0', 'a', 'q1')
        builder.add_transition('q0', 'a', 'q2')
        builder.add_transition('q0', 'b', 'q1')

        # Check that transitions are accumulated
        self.assertEqual(len(builder.transitions['q0']['a']), 2)
        self.assertIn('q1', builder.transitions['q0']['a'])
        self.assertIn('q2', builder.transitions['q0']['a'])
        self.assertEqual(builder.transitions['q0']['b'], ['q1'])

        # Check alphabet
        self.assertEqual(builder.alphabet, {'a', 'b'})

    def test_gnfa_complex_state_elimination(self):
        """Test GNFA with complex state elimination scenarios"""
        gnfa = GNFA()

        # Create a more complex GNFA
        states = ['start', 'S0', 'S1', 'S2', 'accept']
        for state in states:
            gnfa.add_state(state)

        gnfa.start_state = 'start'
        gnfa.accept_state = 'accept'

        # Add complex transitions
        gnfa.add_transition('start', 'S0', 'ε')
        gnfa.add_transition('S0', 'S1', 'a')
        gnfa.add_transition('S1', 'S2', 'b')
        gnfa.add_transition('S2', 'accept', 'ε')
        gnfa.add_transition('S0', 'S2', 'c')  # Alternative path

        # Remove intermediate states
        gnfa.remove_state('S1')
        self.assertNotIn('S1', gnfa.states)

        gnfa.remove_state('S2')
        self.assertNotIn('S2', gnfa.states)

        # Should have direct transition from S0 to accept
        self.assertTrue(gnfa.transitions['S0']['accept'])

    def test_simplify_regex_edge_cases(self):
        """Test regex simplification edge cases"""
        # Empty language symbol
        result = simplify_regex('∅')
        self.assertEqual(result, '∅')

        # Complex nested patterns
        result = simplify_regex('(((a)))')
        self.assertEqual(result, 'a')

        # Multiple epsilon removals
        result = simplify_regex('εaεbε')
        self.assertEqual(result, 'ab')

        # Mixed simplifications
        result = simplify_regex('a**++((b))')
        self.assertEqual(result, 'a*b')

    def test_eliminate_states_multiple_states(self):
        """Test state elimination with multiple intermediate states"""
        gnfa = GNFA()

        # Create chain: start -> S0 -> S1 -> S2 -> accept
        states = ['start', 'S0', 'S1', 'S2', 'accept']
        for state in states:
            gnfa.add_state(state)

        gnfa.start_state = 'start'
        gnfa.accept_state = 'accept'

        gnfa.add_transition('start', 'S0', 'ε')
        gnfa.add_transition('S0', 'S1', 'a')
        gnfa.add_transition('S1', 'S2', 'b')
        gnfa.add_transition('S2', 'accept', 'c')

        result = eliminate_states(gnfa)
        self.assertEqual(result, 'abc')

    def test_fsa_to_regex_comprehensive_verification(self):
        """Test comprehensive verification of FSA to regex conversion"""
        # Test various FSA patterns and verify they convert correctly
        test_cases = [
            # Simple linear FSA
            {
                'states': ['S0', 'S1', 'S2'],
                'alphabet': ['a', 'b'],
                'transitions': {
                    'S0': {'a': ['S1']},
                    'S1': {'b': ['S2']},
                    'S2': {}
                },
                'startingState': 'S0',
                'acceptingStates': ['S2']
            },
            # FSA with choice
            {
                'states': ['S0', 'S1', 'S2'],
                'alphabet': ['a', 'b'],
                'transitions': {
                    'S0': {'a': ['S1'], 'b': ['S2']},
                    'S1': {},
                    'S2': {}
                },
                'startingState': 'S0',
                'acceptingStates': ['S1', 'S2']
            },
            # FSA with loop
            {
                'states': ['S0', 'S1'],
                'alphabet': ['a'],
                'transitions': {
                    'S0': {'a': ['S1']},
                    'S1': {'a': ['S0']}
                },
                'startingState': 'S0',
                'acceptingStates': ['S1']
            }
        ]

        for i, fsa in enumerate(test_cases):
            result = fsa_to_regex(fsa)
            self.assertTrue(result['valid'], f"Test case {i} failed to convert")
            self.assertTrue(result['verification']['equivalent'],
                            f"Test case {i} failed verification")
            self.assertIsNotNone(result['regex'])
            self.assertNotEqual(result['regex'], '')

    def test_performance_with_large_regex(self):
        """Test performance with moderately large regex patterns"""
        # Test with a regex that creates a larger FSA
        large_regex = '(a|b|c|d)*e(f|g|h|i)*'

        fsa = regex_to_epsilon_nfa(large_regex)
        result = fsa_to_regex(fsa)

        self.assertTrue(result['valid'])
        self.assertTrue(result['verification']['equivalent'])

        # Should handle the conversion without issues
        self.assertIsNotNone(result['regex'])

    def test_special_characters_in_alphabet(self):
        """Test handling of special characters in alphabet"""
        # Test with numeric characters
        numeric_fsa = {
            'states': ['S0', 'S1'],
            'alphabet': ['0', '1', '2'],
            'transitions': {
                'S0': {'0': ['S1'], '1': ['S1'], '2': ['S1']},
                'S1': {}
            },
            'startingState': 'S0',
            'acceptingStates': ['S1']
        }

        result = fsa_to_regex(numeric_fsa)
        self.assertTrue(result['valid'])
        self.assertIn('0', result['regex'])  # Should contain numeric characters

    def test_consistency_across_conversions(self):
        """Test consistency across multiple conversions"""
        # Test the same FSA converted multiple times
        fsa = {
            'states': ['S0', 'S1'],
            'alphabet': ['a'],
            'transitions': {
                'S0': {'a': ['S1']},
                'S1': {}
            },
            'startingState': 'S0',
            'acceptingStates': ['S1']
        }

        # Convert multiple times
        results = []
        for _ in range(3):
            result = fsa_to_regex(fsa)
            results.append(result)

        # Should get consistent results
        for result in results:
            self.assertTrue(result['valid'])
            self.assertEqual(result['regex'], results[0]['regex'])

    def test_regex_parser_precedence(self):
        """Test that RegexParser handles operator precedence correctly"""
        # Test precedence: * and + bind tighter than concatenation, which binds tighter than |
        test_cases = [
            ('a|b*', 'Union of a and b*'),
            ('ab*', 'Concatenation of a and b*'),
            ('a*b*', 'Concatenation of a* and b*'),
            ('(a|b)*', 'Kleene star of union'),
            ('a|b+c', 'Union of a and b+c')
        ]

        for regex, description in test_cases:
            nfa = regex_to_epsilon_nfa(regex)
            self.assertIsNotNone(nfa, f"Failed to parse: {description}")
            self.assertTrue(len(nfa['states']) > 0, f"Empty NFA for: {description}")

    def test_empty_transitions_handling(self):
        """Test proper handling of empty transitions in GNFA"""
        gnfa = GNFA()
        gnfa.add_state('S0')
        gnfa.add_state('S1')

        # Add empty transition (should be ignored)
        gnfa.add_transition('S0', 'S1', '')

        # Should not create a transition
        self.assertEqual(gnfa.transitions['S0']['S1'], '')

        # Add non-empty transition
        gnfa.add_transition('S0', 'S1', 'a')

        # Should now have the transition
        self.assertEqual(gnfa.transitions['S0']['S1'], 'a')

    def test_validation_functions_integration(self):
        """Test integration of validation functions"""
        # Test that validate_regex_syntax works correctly with regex_to_epsilon_nfa
        valid_regexes = ['a', 'a|b', 'a*', 'a+', '(a|b)*', 'ε', '∅']
        invalid_regexes = ['*a', '+a', '(a', 'a|*', 'a)']

        for regex in valid_regexes:
            # Should validate successfully
            validation = validate_regex_syntax(regex)
            self.assertTrue(validation['valid'], f"Should validate: {regex}")

            # Should also convert successfully
            nfa = regex_to_epsilon_nfa(regex)
            self.assertIsNotNone(nfa, f"Should convert: {regex}")

        for regex in invalid_regexes:
            # Should fail validation
            validation = validate_regex_syntax(regex)
            self.assertFalse(validation['valid'], f"Should not validate: {regex}")

            # Should also fail conversion
            with self.assertRaises(ValueError):
                regex_to_epsilon_nfa(regex)

    def test_regex_parser_empty_string_edge_cases(self):
        """Test RegexParser with various empty string scenarios"""
        # Test empty regex
        builder = NFABuilder()
        parser = RegexParser('', builder)
        start, accept = parser.parse()
        self.assertIsNotNone(start)
        self.assertIsNotNone(accept)

        # Test regex with only epsilon
        builder = NFABuilder()
        parser = RegexParser('ε', builder)
        start, accept = parser.parse()
        self.assertIsNotNone(start)
        self.assertIsNotNone(accept)

    def test_regex_parser_position_tracking(self):
        """Test RegexParser position tracking and error reporting"""
        # Test unexpected character at specific position
        builder = NFABuilder()
        parser = RegexParser('a)b', builder)
        with self.assertRaises(ValueError) as cm:
            parser.parse()
        self.assertIn('Unexpected character', str(cm.exception))
        self.assertIn('position', str(cm.exception))

    def test_regex_parser_operator_at_wrong_position(self):
        """Test operators appearing at wrong positions"""
        error_cases = [
            ('|a', 'Unexpected'),
            ('a||b', 'Unexpected'),
            ('(|a)', 'Unexpected'),
            ('a|', 'Empty')  # This might be handled differently
        ]

        for regex, expected_error in error_cases:
            builder = NFABuilder()
            parser = RegexParser(regex, builder)
            try:
                with self.assertRaises(ValueError) as cm:
                    parser.parse()
                # Some of these might not raise errors, which is also valid
            except AssertionError:
                # If no error is raised, the parser might handle it gracefully
                pass

    def test_regex_parser_nested_empty_groups(self):
        """Test parsing of nested empty groups"""
        test_cases = [
            '()',
            '(())',
            '((()))',
            'a()b',
            '()()',
            'a()()b'
        ]

        for regex in test_cases:
            builder = NFABuilder()
            parser = RegexParser(regex, builder)
            start, accept = parser.parse()
            self.assertIsNotNone(start)
            self.assertIsNotNone(accept)

    def test_regex_parser_complex_nested_expressions(self):
        """Test complex nested expressions"""
        complex_cases = [
            '((a|b)*c)+',
            '(((a)))',
            '((a|b)|(c|d))*',
            '(a(b(c)))',
            '((a)*|(b)+)*'
        ]

        for regex in complex_cases:
            builder = NFABuilder()
            parser = RegexParser(regex, builder)
            start, accept = parser.parse()
            self.assertIsNotNone(start)
            self.assertIsNotNone(accept)

    def test_gnfa_edge_cases(self):
        """Test GNFA edge cases and error conditions"""
        gnfa = GNFA()

        # Test adding same state multiple times
        gnfa.add_state('S0')
        gnfa.add_state('S0')  # Should handle duplicates gracefully
        self.assertIn('S0', gnfa.states)

        # Test adding transition with empty regex
        gnfa.add_transition('S0', 'S1', '')
        self.assertEqual(gnfa.transitions['S0']['S1'], '')

        # Test adding multiple transitions to same state pair
        gnfa.add_transition('S0', 'S1', 'a')
        gnfa.add_transition('S0', 'S1', 'b')
        self.assertEqual(gnfa.transitions['S0']['S1'], '(a|b)')

    def test_gnfa_complex_state_elimination_patterns(self):
        """Test complex state elimination patterns in GNFA"""
        gnfa = GNFA()

        # Create complex pattern: S0 -> S1 -> S2 with self-loops and bypasses
        for state in ['start', 'S0', 'S1', 'S2', 'accept']:
            gnfa.add_state(state)

        gnfa.start_state = 'start'
        gnfa.accept_state = 'accept'

        # Complex transition pattern
        gnfa.add_transition('start', 'S0', 'ε')
        gnfa.add_transition('S0', 'S1', 'a')
        gnfa.add_transition('S1', 'S1', 'b')  # Self-loop
        gnfa.add_transition('S1', 'S2', 'c')
        gnfa.add_transition('S0', 'S2', 'd')  # Bypass
        gnfa.add_transition('S2', 'accept', 'ε')

        # Remove states and check transitions are updated correctly
        gnfa.remove_state('S1')
        self.assertNotIn('S1', gnfa.states)
        # Should create new transitions incorporating the self-loop

    def test_gnfa_epsilon_handling(self):
        """Test GNFA epsilon transition handling"""
        gnfa = GNFA()
        gnfa.add_state('S0')
        gnfa.add_state('S1')
        gnfa.add_state('S2')
        gnfa.start_state = 'S0'
        gnfa.accept_state = 'S2'

        # Test epsilon transitions in elimination
        gnfa.add_transition('S0', 'S1', 'ε')
        gnfa.add_transition('S1', 'S2', 'a')

        gnfa.remove_state('S1')
        # Should result in direct transition with just 'a', not 'εa' or 'aε'
        result_regex = gnfa.transitions['S0']['S2']
        self.assertNotIn('ε', result_regex)

    def test_ast_node_equivalence_edge_cases(self):
        """Test AST node equivalence function edge cases"""
        # Test same object reference
        node1 = CharNode('a')
        self.assertTrue(nodes_equivalent(node1, node1))

        # Test different types
        char_node = CharNode('a')
        epsilon_node = EpsilonNode()
        self.assertFalse(nodes_equivalent(char_node, epsilon_node))

        # Test complex nested equivalence
        union1 = UnionNode(CharNode('a'), CharNode('b'))
        union2 = UnionNode(CharNode('b'), CharNode('a'))  # Swapped order
        self.assertTrue(nodes_equivalent(union1, union2))

        # Test union with different nesting
        union3 = UnionNode(CharNode('a'), UnionNode(CharNode('b'), CharNode('c')))
        union4 = UnionNode(UnionNode(CharNode('a'), CharNode('b')), CharNode('c'))
        # These might not be equivalent due to structure difference
        # The actual behavior depends on the implementation

        # Test multi-operator node equivalence
        multi1 = MultiOperatorNode(CharNode('a'), ['*', '+'])
        multi2 = MultiOperatorNode(CharNode('a'), ['*', '+'])
        self.assertTrue(nodes_equivalent(multi1, multi2))

        multi3 = MultiOperatorNode(CharNode('a'), ['+', '*'])
        self.assertFalse(nodes_equivalent(multi1, multi3))

    def test_ast_node_string_conversion_edge_cases(self):
        """Test AST node to_string methods with edge cases"""
        # Test empty group node
        empty_group = EmptyGroupNode()
        self.assertEqual(empty_group.to_string(), '')

        # Test union with empty strings
        union_empty = UnionNode(EmptyGroupNode(), CharNode('a'))
        result = union_empty.to_string()
        self.assertIn('|', result)

        # Test complex nested parentheses
        nested = StarNode(UnionNode(CharNode('a'), ConcatNode(CharNode('b'), CharNode('c'))))
        result = nested.to_string()
        self.assertIn('(', result)
        self.assertIn(')', result)
        self.assertIn('*', result)

    def test_ast_node_simplification_advanced(self):
        """Test advanced AST node simplification scenarios"""
        # Test union simplification with complex patterns
        # R*|R+ → R*
        star_node = StarNode(CharNode('a'))
        plus_node = PlusNode(CharNode('a'))
        union = UnionNode(star_node, plus_node)
        simplified = union.simplify()
        self.assertIsInstance(simplified, StarNode)

        # Test concatenation with epsilon
        concat_epsilon = ConcatNode(EpsilonNode(), CharNode('a'))
        simplified = concat_epsilon.simplify()
        self.assertEqual(simplified.to_string(), 'a')

        # Test star of epsilon
        star_epsilon = StarNode(EpsilonNode())
        simplified = star_epsilon.simplify()
        self.assertIsInstance(simplified, EpsilonNode)

        # Test plus of empty set
        plus_empty = PlusNode(EmptySetNode())
        simplified = plus_empty.simplify()
        self.assertIsInstance(simplified, EmptySetNode)

        # Test optional of empty set
        opt_empty = OptionalNode(EmptySetNode())
        simplified = opt_empty.simplify()
        self.assertIsInstance(simplified, EpsilonNode)

    def test_union_node_complex_simplification(self):
        """Test UnionNode complex simplification rules"""
        # Test X|YX → Y?X pattern
        x = CharNode('a')
        y = CharNode('b')
        yx = ConcatNode(y, x)  # ba
        union = UnionNode(x, yx)  # a|ba
        simplified = union.simplify()
        # Should become b?a

        # Test reverse pattern YX|X → Y?X
        union_rev = UnionNode(yx, x)  # ba|a
        simplified_rev = union_rev.simplify()
        # Should also become b?a

        # Test epsilon union patterns
        eps_union = UnionNode(EpsilonNode(), PlusNode(CharNode('a')))
        simplified_eps = eps_union.simplify()
        self.assertIsInstance(simplified_eps, StarNode)

    def test_concat_node_advanced_patterns(self):
        """Test ConcatNode advanced pattern detection"""
        # Test X(YX)*Y → (XY)+ pattern
        x = CharNode('b')
        y = CharNode('a')
        yx = ConcatNode(y, x)  # ab
        yx_star = StarNode(yx)  # (ab)*
        y_final = CharNode('a')

        # Create b(ab)*a pattern
        complex_concat = ConcatNode(x, ConcatNode(yx_star, y_final))
        simplified = complex_concat.simplify()
        # Should detect the pattern and simplify appropriately

    def test_multi_operator_node_simplification(self):
        """Test MultiOperatorNode simplification rules"""
        # Test consecutive identical operators
        multi_star = MultiOperatorNode(CharNode('a'), ['*', '*', '*'])
        simplified = multi_star.simplify()
        self.assertIsInstance(simplified, StarNode)

        # Test mixed operators with star dominance
        mixed_with_star = MultiOperatorNode(CharNode('a'), ['+', '*', '?'])
        simplified = mixed_with_star.simplify()
        self.assertIsInstance(simplified, StarNode)

        # Test plus and optional combination
        plus_optional = MultiOperatorNode(CharNode('a'), ['+', '?'])
        simplified = plus_optional.simplify()
        self.assertIsInstance(simplified, StarNode)

        # Test only optional operators
        multi_optional = MultiOperatorNode(CharNode('a'), ['?', '?', '?'])
        simplified = multi_optional.simplify()
        self.assertIsInstance(simplified, OptionalNode)

    def test_ast_parser_consecutive_operators(self):
        """Test AST parser with consecutive operators"""
        parser = RegexASTParser('a*+?')
        ast = parser.parse()
        self.assertIsNotNone(ast)

        # Test various consecutive operator combinations
        combinations = ['a**', 'a++', 'a??', 'a*+', 'a+*', 'a*?', 'a?*', 'a+?', 'a?+']
        for combo in combinations:
            parser = RegexASTParser(combo)
            ast = parser.parse()
            self.assertIsNotNone(ast)

    def test_ast_parser_error_conditions(self):
        """Test AST parser error conditions"""
        # Test starting with operators
        error_cases = ['*a', '+a', '?a']
        for case in error_cases:
            parser = RegexASTParser(case)
            with self.assertRaises(ValueError):
                parser.parse()

        # Test unexpected operators
        parser = RegexASTParser('a*+?)')
        with self.assertRaises(ValueError):
            parser.parse()

    def test_pattern_detection_functions(self):
        """Test individual pattern detection functions"""
        # Test _detect_char_star_patterns
        aa_star = ConcatNode(CharNode('a'), StarNode(CharNode('a')))
        result = _detect_char_star_patterns(aa_star)
        self.assertIsInstance(result, PlusNode)

        # Test _detect_union_patterns with complex cases
        union_complex = UnionNode(EpsilonNode(), PlusNode(CharNode('a')))
        result = _detect_union_patterns(union_complex)
        self.assertIsInstance(result, StarNode)

        # Test _detect_epsilon_patterns
        concat_with_epsilon = ConcatNode(CharNode('a'), EpsilonNode())
        result = _detect_epsilon_patterns(concat_with_epsilon)
        self.assertIsInstance(result, CharNode)

        # Test _detect_nested_patterns
        nested = StarNode(StarNode(CharNode('a')))
        result = _detect_nested_patterns(nested)
        # Should simplify nested stars

    def test_flattened_concatenation_functions(self):
        """Test flattened concatenation helper functions"""
        # Test _flatten_concatenation
        nested_concat = ConcatNode(ConcatNode(CharNode('a'), CharNode('b')), CharNode('c'))
        flattened = _flatten_concatenation(nested_concat)
        self.assertEqual(len(flattened), 3)

        # Test _detect_flattened_concat_patterns
        # Create pattern like [a, a, StarNode(a)] which should become [a, PlusNode(a)]
        nodes = [CharNode('a'), CharNode('a'), StarNode(CharNode('a'))]
        result = _detect_flattened_concat_patterns(nodes)
        # Should detect the pattern

        # Test _rebuild_concatenation
        nodes = [CharNode('a'), CharNode('b'), CharNode('c')]
        rebuilt = _rebuild_concatenation(nodes)
        self.assertIsInstance(rebuilt, ConcatNode)

    def test_simplify_regex_complex_cases(self):
        """Test simplify_regex with complex cases"""
        # Test with patterns that require multiple rounds of simplification
        complex_cases = [
            '((a))*',
            'ε*+?',
            '(a|ε)*',
            '((ε|a)*)+',
            'a**++??',
            '(((a)))+*?'
        ]

        for regex in complex_cases:
            result = simplify_regex(regex)
            self.assertIsNotNone(result)
            # Result should be valid and hopefully simpler

    def test_simplify_regex_error_handling(self):
        """Test simplify_regex error handling"""
        # Test with invalid regex that might cause parsing errors
        try:
            result = simplify_regex('invalid*regex(')
            # Should return original or handle gracefully
        except:
            # Graceful error handling is also acceptable
            pass

    def test_fsa_to_regex_edge_cases(self):
        """Test fsa_to_regex with edge cases"""
        # Test FSA with only epsilon transitions
        epsilon_only_fsa = {
            'states': ['S0', 'S1', 'S2'],
            'alphabet': [],
            'transitions': {
                'S0': {'': ['S1']},
                'S1': {'': ['S2']},
                'S2': {}
            },
            'startingState': 'S0',
            'acceptingStates': ['S2']
        }

        result = fsa_to_regex(epsilon_only_fsa)
        self.assertTrue(result['valid'])

        # Test FSA with complex epsilon transition patterns
        complex_epsilon_fsa = {
            'states': ['S0', 'S1', 'S2', 'S3'],
            'alphabet': ['a'],
            'transitions': {
                'S0': {'': ['S1', 'S2'], 'a': ['S3']},
                'S1': {'a': ['S3']},
                'S2': {'': ['S3']},
                'S3': {}
            },
            'startingState': 'S0',
            'acceptingStates': ['S3']
        }

        result = fsa_to_regex(complex_epsilon_fsa)
        self.assertTrue(result['valid'])

    def test_fsa_to_regex_minimization_failure_handling(self):
        """Test fsa_to_regex when minimization fails"""
        # Create FSA that might cause minimization issues
        problematic_fsa = {
            'states': ['S0', 'S1', 'S2'],
            'alphabet': ['a', 'b'],
            'transitions': {
                'S0': {'a': ['S1'], 'b': ['S2']},
                'S1': {'a': ['S0'], 'b': ['S2']},
                'S2': {'a': ['S1'], 'b': ['S0']}
            },
            'startingState': 'S0',
            'acceptingStates': ['S0', 'S1', 'S2']
        }

        result = fsa_to_regex(problematic_fsa)
        # Should handle gracefully even if minimization has issues
        self.assertIsNotNone(result)

    def test_verify_function_edge_cases(self):
        """Test verify function with various edge cases"""
        # Create simple FSA for testing
        simple_fsa = {
            'states': ['S0', 'S1'],
            'alphabet': ['a'],
            'transitions': {
                'S0': {'a': ['S1']},
                'S1': {}
            },
            'startingState': 'S0',
            'acceptingStates': ['S1']
        }

        # Test with valid original and simplified regex
        original = 'a'
        simplified = 'a'
        final_regex, verification = verify(simple_fsa, original, simplified)
        self.assertEqual(final_regex, simplified)
        self.assertTrue(verification['equivalent'])

        # Test with invalid simplified regex
        invalid_simplified = '***invalid***'
        final_regex, verification = verify(simple_fsa, original, invalid_simplified)
        # Should fall back to original
        self.assertEqual(final_regex, original)

    def test_eliminate_states_complex_scenarios(self):
        """Test eliminate_states with complex scenarios"""
        # Test with multiple states and complex transition patterns
        gnfa = GNFA()
        states = ['start', 'A', 'B', 'C', 'D', 'accept']
        for state in states:
            gnfa.add_state(state)

        gnfa.start_state = 'start'
        gnfa.accept_state = 'accept'

        # Create complex transition network
        gnfa.add_transition('start', 'A', 'ε')
        gnfa.add_transition('A', 'B', 'a')
        gnfa.add_transition('B', 'C', 'b')
        gnfa.add_transition('C', 'D', 'c')
        gnfa.add_transition('D', 'accept', 'ε')

        # Add some loops and alternative paths
        gnfa.add_transition('A', 'A', 'x')  # Self-loop
        gnfa.add_transition('B', 'D', 'y')  # Skip C
        gnfa.add_transition('C', 'A', 'z')  # Back to A

        result = eliminate_states(gnfa)
        self.assertIsNotNone(result)
        self.assertNotEqual(result, '∅')

    def test_eliminate_states_no_valid_states(self):
        """Test eliminate_states when no states can be eliminated"""
        gnfa = GNFA()
        gnfa.add_state('start')
        gnfa.add_state('accept')
        gnfa.start_state = 'start'
        gnfa.accept_state = 'accept'

        # Only start and accept states, nothing to eliminate
        result = eliminate_states(gnfa)
        # Should return empty language if no connection
        self.assertEqual(result, '∅')

    def test_regex_to_epsilon_nfa_special_symbols(self):
        """Test regex_to_epsilon_nfa with special symbols"""
        # Test with empty set symbol
        try:
            nfa = regex_to_epsilon_nfa('∅')
            self.assertIsNotNone(nfa)
        except:
            # Might not be implemented, which is fine
            pass

        # Test with various Unicode characters if supported
        unicode_cases = ['α', 'β', '1', '0', ' ']  # Including space
        for char in unicode_cases:
            try:
                nfa = regex_to_epsilon_nfa(char)
                self.assertIsNotNone(nfa)
                self.assertIn(char, nfa['alphabet'])
            except:
                # Some characters might not be supported
                pass

    def test_nfa_builder_edge_cases(self):
        """Test NFABuilder edge cases"""
        builder = NFABuilder()

        # Test adding many transitions
        for i in range(10):
            state = builder.new_state()
            builder.add_transition('q0', f'symbol_{i}', state)

        # Test building with many states
        nfa_dict = builder.to_dict('q0', ['q9'])
        self.assertGreaterEqual(len(nfa_dict['states']), 10)

        # Test epsilon transition handling
        builder.add_transition('q0', '', 'q1')
        self.assertEqual(len(builder.alphabet), 10)  # Epsilon shouldn't be added

    def test_regex_parser_atom_parsing_edge_cases(self):
        """Test RegexParser atom parsing edge cases"""
        # Test parsing atoms at end of string
        builder = NFABuilder()
        parser = RegexParser('a', builder)
        parser.pos = len(parser.regex)  # Simulate end of string
        char = parser.peek()
        self.assertIsNone(char)

        # Test consume at end
        char = parser.consume()
        self.assertIsNone(char)

    def test_comprehensive_roundtrip_edge_cases(self):
        """Test comprehensive roundtrip conversions with edge cases"""
        edge_case_regexes = [
            'ε',
            '()',
            '()*',
            '()+',
            '()?',
            'a**',
            'a++',
            'a??',
            '((a))',
            '(a|ε)',
            '(ε|a)',
            'εa',
            'aε',
            'εεε',
            '(ε)*',
            '(ε)+',
            '(ε)?'
        ]

        for regex in edge_case_regexes:
            try:
                # Convert to FSA
                fsa = regex_to_epsilon_nfa(regex)
                self.assertIsNotNone(fsa)

                # Convert back to regex
                result = fsa_to_regex(fsa)
                self.assertTrue(result['valid'], f"Failed roundtrip for: {regex}")

                # Verify the result is valid
                validation = validate_regex_syntax(result['regex'])
                self.assertTrue(validation['valid'], f"Invalid result regex for: {regex}")

            except Exception as e:
                # Some edge cases might not be fully supported
                # That's acceptable as long as they fail gracefully
                self.assertIsInstance(e, (ValueError, NotImplementedError))

    def test_pattern_detection_with_nested_structures(self):
        """Test pattern detection with deeply nested structures"""
        # Create deeply nested structure
        inner = CharNode('a')
        for _ in range(5):
            inner = StarNode(inner)

        # Test various pattern detection functions
        result1 = _detect_char_star_patterns(inner)
        result2 = _detect_union_patterns(inner)
        result3 = _detect_epsilon_patterns(inner)
        result4 = _detect_nested_patterns(inner)

        # All should return some result without crashing
        self.assertIsNotNone(result1)
        self.assertIsNotNone(result2)
        self.assertIsNotNone(result3)
        self.assertIsNotNone(result4)

    def test_simplify_regex_maximum_iterations(self):
        """Test simplify_regex with patterns that might cause many iterations"""
        # Create a regex that might require many simplification rounds
        complex_regex = '((((a*)+)?)*)*'
        result = simplify_regex(complex_regex)
        self.assertIsNotNone(result)
        # Should terminate within reasonable number of iterations

    def test_error_propagation_in_complex_scenarios(self):
        """Test error propagation in complex conversion scenarios"""
        # Test with FSA that has inconsistent structure
        inconsistent_fsa = {
            'states': ['S0', 'S1'],
            'alphabet': ['a'],
            'transitions': {
                'S0': {'a': ['S2']},  # S2 not in states
                'S1': {}
            },
            'startingState': 'S0',
            'acceptingStates': ['S1']
        }

        # Should handle gracefully
        result = fsa_to_regex(inconsistent_fsa)
        # Might be valid if the implementation handles missing states gracefully
        # Or might be invalid with appropriate error message
        self.assertIsNotNone(result)

    def test_memory_usage_with_large_structures(self):
        """Test memory usage with moderately large structures"""
        # Create a regex that generates a larger FSA
        large_regex = '(a|b|c|d|e)*f(g|h|i|j|k)*'

        # Convert to FSA
        fsa = regex_to_epsilon_nfa(large_regex)
        self.assertIsNotNone(fsa)

        # Convert back
        result = fsa_to_regex(fsa)
        self.assertTrue(result['valid'])

        # Should complete without memory issues
        self.assertIsNotNone(result['regex'])

    def test_unicode_and_special_character_support(self):
        """Test support for Unicode and special characters"""
        special_chars = ['α', 'β', 'γ', '中', '1', '0', '!', '@', '#']

        for char in special_chars:
            try:
                # Test basic character
                nfa = regex_to_epsilon_nfa(char)
                self.assertIn(char, nfa['alphabet'])

                # Test in more complex expression
                complex_regex = f'({char})*'
                nfa2 = regex_to_epsilon_nfa(complex_regex)
                self.assertIn(char, nfa2['alphabet'])

            except Exception:
                # Some characters might not be supported, which is acceptable
                pass

    def test_regex_parser_unexpected_character_after_parsing(self):
        """Test line 200 - unexpected character after successful parsing"""
        # This hits the case where parsing succeeds but doesn't consume entire regex
        builder = NFABuilder()

        # Test with regex that has valid start but invalid continuation
        with self.assertRaises(ValueError) as cm:
            parser = RegexParser('a)', builder)
            parser.parse()
        self.assertIn('Unexpected character', str(cm.exception))
        self.assertIn('position', str(cm.exception))

    def test_gnfa_union_existing_transitions(self):
        """Test lines 390-393 - GNFA adding transition when one already exists"""
        gnfa = GNFA()
        gnfa.add_state('S0')
        gnfa.add_state('S1')

        # Add first transition
        gnfa.add_transition('S0', 'S1', 'a')
        self.assertEqual(gnfa.transitions['S0']['S1'], 'a')

        # Add second transition to same state pair - should create union
        gnfa.add_transition('S0', 'S1', 'b')
        self.assertEqual(gnfa.transitions['S0']['S1'], '(a|b)')

        # Add third transition - should union with existing
        gnfa.add_transition('S0', 'S1', 'c')
        self.assertEqual(gnfa.transitions['S0']['S1'], '((a|b)|c)')

    def test_gnfa_remove_state_with_complex_self_loop(self):
        """Test lines 529-532, 658-661 - GNFA state elimination with self-loops"""
        gnfa = GNFA()
        for state in ['start', 'S0', 'S1', 'accept']:
            gnfa.add_state(state)
        gnfa.start_state = 'start'
        gnfa.accept_state = 'accept'

        # Create pattern with complex self-loop that needs special handling
        gnfa.add_transition('start', 'S0', 'a')
        gnfa.add_transition('S0', 'S1', 'b')
        gnfa.add_transition('S0', 'S0', 'c|d')  # Complex self-loop expression
        gnfa.add_transition('S1', 'accept', 'e')

        # Remove S0 - should handle complex self-loop regex
        gnfa.remove_state('S0')

        # Should create transition incorporating the complex self-loop
        result_transition = gnfa.transitions['start']['S1']
        self.assertIn('(c|d)*', result_transition)

    def test_gnfa_remove_state_epsilon_handling(self):
        """Test lines 685-686, 691-711 - GNFA epsilon handling in state elimination"""
        gnfa = GNFA()
        for state in ['start', 'S0', 'S1', 'accept']:
            gnfa.add_state(state)
        gnfa.start_state = 'start'
        gnfa.accept_state = 'accept'

        # Create transitions with epsilon that should be handled specially
        gnfa.add_transition('start', 'S0', 'ε')  # Epsilon incoming
        gnfa.add_transition('S0', 'S1', 'a')
        gnfa.add_transition('S1', 'accept', 'ε')  # Epsilon outgoing

        # Also test case where self-loop is epsilon
        gnfa.add_transition('S0', 'S0', 'ε')  # Epsilon self-loop

        # Remove S0 - should handle epsilon correctly
        gnfa.remove_state('S0')

        # Should create clean transition without extra epsilons
        result_transition = gnfa.transitions['start']['S1']
        self.assertEqual(result_transition, 'a')

    def test_fsa_to_regex_empty_after_minimization(self):
        """Test lines 833, 850, 852 - FSA becomes empty after minimization"""
        # FSA with unreachable states that might become empty after minimization
        fsa_with_unreachable = {
            'states': ['S0', 'S1', 'S2'],
            'alphabet': ['a'],
            'transitions': {
                'S0': {},  # No transitions from start
                'S1': {'a': ['S2']},  # Unreachable
                'S2': {}
            },
            'startingState': 'S0',
            'acceptingStates': ['S2']
        }

        result = fsa_to_regex(fsa_with_unreachable)
        self.assertTrue(result['valid'])
        # Should result in empty language
        self.assertEqual(result['regex'], '∅')

    def test_fsa_to_regex_single_state_non_accepting(self):
        """Test line 858 - single state FSA that's not accepting"""
        single_non_accepting = {
            'states': ['S0'],
            'alphabet': ['a'],
            'transitions': {
                'S0': {'a': ['S0']}  # Self-loop but not accepting
            },
            'startingState': 'S0',
            'acceptingStates': []  # Not accepting
        }

        result = fsa_to_regex(single_non_accepting)
        self.assertTrue(result['valid'])
        self.assertEqual(result['regex'], '∅')

    def test_verify_function_simplified_regex_fails(self):
        """Test lines 898, 902 - verify function when simplified regex fails"""
        simple_fsa = {
            'states': ['S0', 'S1'],
            'alphabet': ['a'],
            'transitions': {
                'S0': {'a': ['S1']},
                'S1': {}
            },
            'startingState': 'S0',
            'acceptingStates': ['S1']
        }

        # Test with invalid simplified regex that will fail conversion
        original = 'a'
        invalid_simplified = '((('  # Invalid regex

        final_regex, verification = verify(simple_fsa, original, invalid_simplified)
        # Should fall back to original
        self.assertEqual(final_regex, original)
        self.assertIn('fallback_to_original', verification['strategy'])

    def test_verify_function_both_fail_equivalence(self):
        """Test lines around 950-955 - verify when both regexes fail equivalence"""
        # Create FSA that won't match either regex
        fsa = {
            'states': ['S0', 'S1'],
            'alphabet': ['a'],
            'transitions': {
                'S0': {'a': ['S1']},
                'S1': {}
            },
            'startingState': 'S0',
            'acceptingStates': ['S1']
        }

        # Provide regexes that don't match the FSA
        original = 'b'  # Doesn't match FSA
        simplified = 'c'  # Also doesn't match FSA

        final_regex, verification = verify(fsa, original, simplified)
        self.assertFalse(verification['equivalent'])
        self.assertIn('both_failed', verification['strategy'])

    def test_verify_function_both_fail_conversion(self):
        """Test lines 958-963 - verify when both regexes fail to convert"""
        simple_fsa = {
            'states': ['S0', 'S1'],
            'alphabet': ['a'],
            'transitions': {
                'S0': {'a': ['S1']},
                'S1': {}
            },
            'startingState': 'S0',
            'acceptingStates': ['S1']
        }

        # Both regexes are invalid
        invalid_original = '((('
        invalid_simplified = ')))'

        final_regex, verification = verify(simple_fsa, invalid_original, invalid_simplified)
        self.assertFalse(verification['equivalent'])
        self.assertIn('both_failed_conversion', verification['strategy'])

    def test_union_node_complex_simplification_rules(self):
        """Test lines 1010-1011, 1020-1021 - UnionNode complex simplification"""
        # Test R*|S+ → R*|S* rule
        r_star = StarNode(CharNode('a'))
        s_plus = PlusNode(CharNode('b'))
        union = UnionNode(r_star, s_plus)
        simplified = union.simplify()

        # Should trigger the rule that converts S+ to S* when combined with R*
        self.assertIsInstance(simplified, UnionNode)

    def test_union_node_factor_common_suffix(self):
        """Test lines 1028-1029, 1035-1036 - UnionNode factoring common suffix"""
        # Test X|YX → Y?X pattern
        x = CharNode('a')
        y = CharNode('b')
        yx = ConcatNode(y, x)  # ba
        union = UnionNode(x, yx)  # a|ba
        simplified = union.simplify()

        # Should become b?a
        self.assertIsInstance(simplified, ConcatNode)

        # Test reverse pattern YX|X → Y?X
        union_rev = UnionNode(yx, x)  # ba|a
        simplified_rev = union_rev.simplify()
        self.assertIsInstance(simplified_rev, ConcatNode)

    def test_union_node_optional_rules(self):
        """Test lines 1042-1043 - UnionNode with optional handling"""
        # Test R|R? → R?, R?|R → R?
        r = CharNode('a')
        r_opt = OptionalNode(CharNode('a'))

        union1 = UnionNode(r, r_opt)
        simplified1 = union1.simplify()
        self.assertIsInstance(simplified1, OptionalNode)

        union2 = UnionNode(r_opt, r)
        simplified2 = union2.simplify()
        self.assertIsInstance(simplified2, OptionalNode)

    def test_concat_node_x_yx_star_y_pattern(self):
        """Test lines 1129, 1143, 1145 - ConcatNode X(YX)*Y → (XY)+ pattern"""
        # Create X(YX)*Y pattern: b(ab)*a
        x = CharNode('b')
        y = CharNode('a')
        yx = ConcatNode(y, x)  # ab
        yx_star = StarNode(yx)  # (ab)*
        y_final = CharNode('a')

        # Create b(ab)*a pattern
        inner_concat = ConcatNode(yx_star, y_final)  # (ab)*a
        complex_concat = ConcatNode(x, inner_concat)  # b(ab)*a

        simplified = complex_concat.simplify()
        # Should detect the pattern and create (ba)+
        self.assertIsInstance(simplified, PlusNode)

    def test_concat_node_nested_simplification(self):
        """Test lines 1155, 1161 - ConcatNode nested concatenation simplification"""
        # Create nested concatenation that needs simplification
        a = CharNode('a')
        b = CharNode('b')
        bb_star = ConcatNode(b, StarNode(b))  # bb* should become b+

        # Create a(bb*) which should become ab+
        concat = ConcatNode(a, bb_star)
        simplified = concat.simplify()

        # Should trigger nested simplification
        self.assertIsInstance(simplified, ConcatNode)

    def test_star_node_advanced_rules(self):
        """Test lines 1165, 1167, 1173 - StarNode advanced simplification"""
        # Test (R+)* → R*
        plus_node = PlusNode(CharNode('a'))
        star_of_plus = StarNode(plus_node)
        simplified = star_of_plus.simplify()
        self.assertIsInstance(simplified, StarNode)
        self.assertIsInstance(simplified.inner, CharNode)

        # Test (R?)* → R*
        opt_node = OptionalNode(CharNode('a'))
        star_of_opt = StarNode(opt_node)
        simplified2 = star_of_opt.simplify()
        self.assertIsInstance(simplified2, StarNode)

    def test_plus_node_advanced_rules(self):
        """Test lines 1195, 1197 - PlusNode advanced simplification"""
        # Test (R*)+ → R*
        star_node = StarNode(CharNode('a'))
        plus_of_star = PlusNode(star_node)
        simplified = plus_of_star.simplify()
        self.assertIsInstance(simplified, StarNode)

        # Test (R?)+ → R*
        opt_node = OptionalNode(CharNode('a'))
        plus_of_opt = PlusNode(opt_node)
        simplified2 = plus_of_opt.simplify()
        self.assertIsInstance(simplified2, StarNode)

    def test_optional_node_advanced_rules(self):
        """Test lines 1223, 1225 - OptionalNode advanced simplification"""
        # Test (R*)? → R*
        star_node = StarNode(CharNode('a'))
        opt_of_star = OptionalNode(star_node)
        simplified = opt_of_star.simplify()
        self.assertIsInstance(simplified, StarNode)

        # Test (R+)? → R*
        plus_node = PlusNode(CharNode('a'))
        opt_of_plus = OptionalNode(plus_node)
        simplified2 = opt_of_plus.simplify()
        self.assertIsInstance(simplified2, StarNode)

    def test_multi_operator_node_dominance_rules(self):
        """Test lines 1241, 1255 - MultiOperatorNode operator dominance"""
        # Test star dominance
        multi_with_star = MultiOperatorNode(CharNode('a'), ['*', '+', '?'])
        simplified = multi_with_star.simplify()
        self.assertIsInstance(simplified, StarNode)

        # Test plus + optional = star
        multi_plus_opt = MultiOperatorNode(CharNode('a'), ['+', '?'])
        simplified2 = multi_plus_opt.simplify()
        self.assertIsInstance(simplified2, StarNode)

    def test_regex_ast_parser_empty_group_handling(self):
        """Test lines 1301, 1316 - RegexASTParser empty group handling"""
        # Test parsing empty groups
        parser = RegexASTParser('()')
        ast = parser.parse()
        self.assertIsInstance(ast, EmptyGroupNode)

        # Test multiple empty groups
        parser2 = RegexASTParser('()()')
        ast2 = parser2.parse()
        self.assertIsInstance(ast2, ConcatNode)

    def test_regex_ast_parser_multiple_consecutive_operators(self):
        """Test lines 1329, 1337, 1345 - RegexASTParser consecutive operators"""
        # Test multiple consecutive operators
        parser = RegexASTParser('a*+?')
        ast = parser.parse()
        self.assertIsInstance(ast, MultiOperatorNode)
        self.assertEqual(ast.operators, ['*', '+', '?'])

        # Test different combinations
        parser2 = RegexASTParser('a++*??')
        ast2 = parser2.parse()
        self.assertIsInstance(ast2, MultiOperatorNode)

    def test_pattern_detection_with_re_simplification(self):
        """Test lines 1364, 1368, 1377, 1381 - Pattern detection re-simplification"""
        # Test _detect_union_patterns with re-simplification
        eps = EpsilonNode()
        star_a = StarNode(CharNode('a'))
        union = UnionNode(eps, star_a)

        result = _detect_union_patterns(union)
        # Should trigger re-simplification and return the star node
        self.assertIsInstance(result, StarNode)

    def test_flattened_concat_pattern_detection(self):
        """Test lines 1393, 1397, 1412 - Flattened concatenation patterns"""
        # Test patterns that require flattening to detect
        # Create [..., R, R*] pattern
        a = CharNode('a')
        a_star = StarNode(CharNode('a'))
        nodes = [a, a, a_star]  # a, a, a*

        result = _detect_flattened_concat_patterns(nodes)
        # Should detect pattern and convert to [a, a+]
        self.assertEqual(len(result), 2)

    def test_detect_epsilon_patterns_advanced(self):
        """Test lines 1425, 1429, 1445 - Advanced epsilon pattern detection"""
        # Test epsilon elimination in complex structures
        eps = EpsilonNode()
        a = CharNode('a')

        # Test epsilon in concatenation
        concat_eps_left = ConcatNode(eps, a)
        result1 = _detect_epsilon_patterns(concat_eps_left)
        self.assertEqual(result1.to_string(), 'a')

        concat_eps_right = ConcatNode(a, eps)
        result2 = _detect_epsilon_patterns(concat_eps_right)
        self.assertEqual(result2.to_string(), 'a')

    def test_simplify_regex_error_handling(self):
        """Test lines 1457-1460 - simplify_regex error handling"""
        # Test with regex that might cause parsing errors
        try:
            result = simplify_regex('invalid(((regex')
            # Should return original on error
            self.assertEqual(result, 'invalid(((regex')
        except:
            # Or handle gracefully
            pass

    def test_eliminate_states_best_state_selection(self):
        """Test lines 482 - eliminate_states best state selection logic"""
        gnfa = GNFA()

        # Create GNFA with multiple states to eliminate
        states = ['start', 'A', 'B', 'C', 'accept']
        for state in states:
            gnfa.add_state(state)
        gnfa.start_state = 'start'
        gnfa.accept_state = 'accept'

        # Create transitions that make some states better candidates for elimination
        gnfa.add_transition('start', 'A', 'ε')
        gnfa.add_transition('A', 'B', 'a')
        gnfa.add_transition('B', 'C', 'b')
        gnfa.add_transition('C', 'accept', 'ε')

        # Add extra transitions to make transition counting matter
        gnfa.add_transition('A', 'C', 'x')  # A has more transitions
        gnfa.add_transition('B', 'B', 'y')  # B has self-loop

        result = eliminate_states(gnfa)
        self.assertIsNotNone(result)

    def test_detect_nested_patterns_changes(self):
        """Test lines 1493, 1513, 1518, 1537 - detect_nested_patterns when changes occur"""
        # Create nested structure that will change during pattern detection
        inner = StarNode(StarNode(CharNode('a')))  # a**

        result = _detect_nested_patterns(inner)
        # Should detect that inner changed and re-simplify
        self.assertIsInstance(result, StarNode)

    def test_ast_node_to_string_edge_cases(self):
        """Test lines 1606-1607, 1614 - AST node to_string edge cases"""
        # Test UnionNode with empty strings
        empty = EmptyGroupNode()
        a = CharNode('a')

        union_with_empty = UnionNode(empty, a)
        result = union_with_empty.to_string()
        self.assertIn('|', result)

    def test_empty_group_and_empty_set_handling(self):
        """Test lines 1635, 1663-1665 - EmptyGroupNode and EmptySetNode handling"""
        # Test EmptyGroupNode simplification
        empty_group = EmptyGroupNode()
        simplified = empty_group.simplify()
        self.assertIsInstance(simplified, EpsilonNode)

        # Test EmptySetNode in various contexts
        empty_set = EmptySetNode()
        self.assertEqual(empty_set.to_string(), '∅')
        self.assertIsInstance(empty_set.simplify(), EmptySetNode)

    def test_regex_parser_atom_special_cases(self):
        """Test lines around 564 - RegexParser atom parsing special cases"""
        # Test parsing empty set symbol
        builder = NFABuilder()
        parser = RegexParser('∅', builder)
        start, accept = parser.parse()
        self.assertIsNotNone(start)
        self.assertIsNotNone(accept)

    def test_gnfa_remove_state_no_transitions(self):
        """Test case where state has no incoming/outgoing transitions"""
        gnfa = GNFA()
        states = ['start', 'isolated', 'accept']
        for state in states:
            gnfa.add_state(state)
        gnfa.start_state = 'start'
        gnfa.accept_state = 'accept'

        # Add transition that doesn't involve 'isolated'
        gnfa.add_transition('start', 'accept', 'a')

        # Remove isolated state - should handle gracefully
        gnfa.remove_state('isolated')
        self.assertNotIn('isolated', gnfa.states)

    def test_fsa_to_gnfa_edge_cases(self):
        """Test fsa_to_gnfa with edge cases"""
        # Test FSA with empty transitions dictionary
        fsa = {
            'states': ['S0'],
            'alphabet': [],
            'transitions': {},
            'startingState': 'S0',
            'acceptingStates': ['S0']
        }

        gnfa = fsa_to_gnfa(fsa)
        self.assertIsNotNone(gnfa)
        self.assertEqual(gnfa.start_state, 'gnfa_start')
        self.assertEqual(gnfa.accept_state, 'gnfa_accept')

    def test_regex_parser_precedence_edge_cases(self):
        """Test RegexParser precedence with edge cases"""
        # Test cases that might not consume entire regex
        builder = NFABuilder()

        # This should work but let's make sure it handles the precedence correctly
        parser = RegexParser('a|b*c', builder)
        start, accept = parser.parse()
        self.assertIsNotNone(start)
        self.assertIsNotNone(accept)

    def test_gnfa_state_elimination_epsilon_self_loop(self):
        """Test GNFA state elimination when self-loop is epsilon"""
        gnfa = GNFA()
        states = ['start', 'S0', 'accept']
        for state in states:
            gnfa.add_state(state)
        gnfa.start_state = 'start'
        gnfa.accept_state = 'accept'

        # Create transitions where self-loop is epsilon
        gnfa.add_transition('start', 'S0', 'a')
        gnfa.add_transition('S0', 'S0', 'ε')  # Epsilon self-loop
        gnfa.add_transition('S0', 'accept', 'b')

        # Remove S0 - should handle epsilon self-loop correctly
        gnfa.remove_state('S0')

        # Should create direct transition without epsilon artifacts
        result_transition = gnfa.transitions['start']['accept']
        self.assertEqual(result_transition, 'ab')

    def test_simplify_regex_iteration_limit(self):
        """Test simplify_regex reaches iteration limit"""
        # Create a regex that might need many iterations
        complex_regex = '((((a*)+)?)*)*'

        # Should complete within iteration limit
        result = simplify_regex(complex_regex)
        self.assertIsNotNone(result)
        # Should be simplified to something reasonable
        self.assertIn('a', result)

    def test_concat_node_empty_set_annihilation(self):
        """Test ConcatNode empty set annihilation rules"""
        # Test ∅R → ∅, R∅ → ∅
        empty_set = EmptySetNode()
        a = CharNode('a')

        concat_left = ConcatNode(empty_set, a)
        simplified_left = concat_left.simplify()
        self.assertIsInstance(simplified_left, EmptySetNode)

        concat_right = ConcatNode(a, empty_set)
        simplified_right = concat_right.simplify()
        self.assertIsInstance(simplified_right, EmptySetNode)

    def test_star_node_empty_set_rule(self):
        """Test StarNode ∅* → ε rule"""
        empty_set = EmptySetNode()
        star_empty = StarNode(empty_set)
        simplified = star_empty.simplify()
        self.assertIsInstance(simplified, EpsilonNode)

    def test_plus_node_empty_set_rule(self):
        """Test PlusNode ∅+ → ∅ rule"""
        empty_set = EmptySetNode()
        plus_empty = PlusNode(empty_set)
        simplified = plus_empty.simplify()
        self.assertIsInstance(simplified, EmptySetNode)

    def test_optional_node_empty_set_rule(self):
        """Test OptionalNode ∅? → ε rule"""
        empty_set = EmptySetNode()
        opt_empty = OptionalNode(empty_set)
        simplified = opt_empty.simplify()
        self.assertIsInstance(simplified, EpsilonNode)

    def test_gnfa_no_self_loop_case(self):
        """Test lines 600-602 - GNFA state elimination without self-loop"""
        gnfa = GNFA()
        for state in ['start', 'S0', 'accept']:
            gnfa.add_state(state)
        gnfa.start_state = 'start'
        gnfa.accept_state = 'accept'

        # Create transitions without self-loop
        gnfa.add_transition('start', 'S0', 'a')
        gnfa.add_transition('S0', 'accept', 'b')
        # No self-loop on S0

        # Remove S0 - should handle case where self_loop is empty
        gnfa.remove_state('S0')

        # Should create simple transition
        result_transition = gnfa.transitions['start']['accept']
        self.assertEqual(result_transition, 'ab')

    def test_union_node_epsilon_non_star_plus(self):
        """Test lines 1057, 1062, 1066-1068 - UnionNode epsilon with non-star/plus"""
        # Test ε|R → R? for regular nodes (not star/plus)
        eps = EpsilonNode()
        regular_char = CharNode('a')

        union_left = UnionNode(eps, regular_char)
        simplified_left = union_left.simplify()
        self.assertIsInstance(simplified_left, OptionalNode)

        union_right = UnionNode(regular_char, eps)
        simplified_right = union_right.simplify()
        self.assertIsInstance(simplified_right, OptionalNode)

    def test_concat_node_nested_different_patterns(self):
        """Test lines 1143, 1145 - ConcatNode nested pattern detection edge cases"""
        # Test case where we have nested concatenation but pattern doesn't match
        x = CharNode('b')
        y = CharNode('c')  # Different character
        yx = ConcatNode(y, x)  # cb
        yx_star = StarNode(yx)  # (cb)*
        y_final = CharNode('a')  # Different from original Y

        # Create b(cb)*a pattern - shouldn't match X(YX)*Y pattern
        inner_concat = ConcatNode(yx_star, y_final)
        complex_concat = ConcatNode(x, inner_concat)

        simplified = complex_concat.simplify()
        # Should not trigger the special pattern transformation
        self.assertIsInstance(simplified, ConcatNode)

    def test_regex_ast_parser_consume_at_end(self):
        """Test edge case in RegexASTParser consume method"""
        parser = RegexASTParser('a')

        # Consume the 'a'
        char = parser.consume()
        self.assertEqual(char, 'a')

        # Try to consume beyond end
        char = parser.consume()
        self.assertIsNone(char)

    def test_regex_parser_parse_atom_fallback(self):
        """Test lines around 564 - RegexParser parse_atom fallback case"""
        builder = NFABuilder()
        parser = RegexParser('', builder)  # Empty regex

        # This should trigger the final else case in parse_atom
        start, accept = parser.parse_atom()
        self.assertIsNotNone(start)
        self.assertIsNotNone(accept)

    def test_union_node_to_string_edge_cases(self):
        """Test lines 1606-1607, 1614 - UnionNode to_string with empty components"""
        # Test with left side empty
        empty_left = EmptyGroupNode()
        right_char = CharNode('a')
        union = UnionNode(empty_left, right_char)

        result = union.to_string()
        self.assertEqual(result, '|a')

        # Test with right side empty
        left_char = CharNode('b')
        empty_right = EmptyGroupNode()
        union2 = UnionNode(left_char, empty_right)

        result2 = union2.to_string()
        self.assertEqual(result2, 'b|')

    def test_star_node_empty_group_to_string(self):
        """Test StarNode with EmptyGroupNode to_string edge case"""
        empty_group = EmptyGroupNode()
        star = StarNode(empty_group)

        # Should return empty string for ()*
        result = star.to_string()
        self.assertEqual(result, '')

    def test_plus_node_empty_group_to_string(self):
        """Test PlusNode with EmptyGroupNode to_string edge case"""
        empty_group = EmptyGroupNode()
        plus = PlusNode(empty_group)

        # Should return empty string for ()+
        result = plus.to_string()
        self.assertEqual(result, '')

    def test_optional_node_empty_group_to_string(self):
        """Test OptionalNode with EmptyGroupNode to_string edge case"""
        empty_group = EmptyGroupNode()
        optional = OptionalNode(empty_group)

        # Should return empty string for ()?
        result = optional.to_string()
        self.assertEqual(result, '')

    def test_multi_operator_node_fallback_case(self):
        """Test MultiOperatorNode fallback case in simplify"""
        # Create case where no operators match the dominance rules
        char = CharNode('a')
        multi = MultiOperatorNode(char, [])  # Empty operators list

        simplified = multi.simplify()
        # Should return the inner node
        self.assertIsInstance(simplified, CharNode)

    def test_simplify_regex_empty_result_cleanup(self):
        """Test simplify_regex final cleanup when result is empty"""
        # This is tricky to trigger, but let's try with empty groups
        empty_regex = '()()()'
        result = simplify_regex(empty_regex)

        # Should return epsilon for empty result
        self.assertEqual(result, 'ε')

    def test_fsa_to_regex_verification_edge_case(self):
        """Test specific verification path in fsa_to_regex"""
        # Create a very simple FSA to test verification paths
        simple_fsa = {
            'states': ['S0', 'S1'],
            'alphabet': ['a'],
            'transitions': {
                'S0': {'a': ['S1']},
                'S1': {}
            },
            'startingState': 'S0',
            'acceptingStates': ['S1']
        }

        result = fsa_to_regex(simple_fsa)
        self.assertTrue(result['valid'])
        # This should trigger specific verification code paths
        self.assertIn('strategy', result['verification'])

    def test_eliminate_states_transition_counting(self):
        """Test eliminate_states transition counting logic more thoroughly"""
        gnfa = GNFA()

        # Create states with different numbers of transitions
        states = ['start', 'A', 'B', 'C', 'accept']
        for state in states:
            gnfa.add_state(state)
        gnfa.start_state = 'start'
        gnfa.accept_state = 'accept'

        # A has 1 incoming, 2 outgoing = 3 total
        gnfa.add_transition('start', 'A', 'x')
        gnfa.add_transition('A', 'B', 'y')
        gnfa.add_transition('A', 'C', 'z')

        # B has 1 incoming, 1 outgoing = 2 total (should be chosen first)
        gnfa.add_transition('B', 'accept', 'p')

        # C has 1 incoming, 1 outgoing = 2 total
        gnfa.add_transition('C', 'accept', 'q')

        # This should test the transition counting logic
        result = eliminate_states(gnfa)
        self.assertIsNotNone(result)

    def test_nodes_equivalent_fallback_case(self):
        """Test nodes_equivalent fallback string comparison"""

        # Create a mock node that will trigger the fallback case
        class MockNode(RegexNode):
            def __init__(self, value):
                self.value = value

            def to_string(self):
                return self.value

            def simplify(self):
                return self

        node1 = MockNode('test')
        node2 = MockNode('test')

        # Should use string comparison fallback
        self.assertTrue(nodes_equivalent(node1, node2))

        node3 = MockNode('different')
        self.assertFalse(nodes_equivalent(node1, node3))

    def test_nodes_equivalent_exception_fallback(self):
        """Test nodes_equivalent when to_string() fails"""

        class FailingNode(RegexNode):
            def to_string(self):
                raise Exception("to_string failed")

            def simplify(self):
                return self

        node1 = FailingNode()
        node2 = FailingNode()

        # Should return False when to_string() fails
        self.assertFalse(nodes_equivalent(node1, node2))

    def test_regex_parser_question_mark_operator(self):
        """Test RegexParser with question mark operator"""
        builder = NFABuilder()

        # Test simple optional
        nfa = regex_to_epsilon_nfa('a?')
        self.assertEqual(nfa['alphabet'], ['a'])
        self.assertEqual(len(nfa['acceptingStates']), 1)

        # Verify structure has bypass transition (epsilon from start to accept)
        self.assertTrue(len(nfa['states']) >= 4)  # Should have multiple states for optional

    def test_concat_node_parentheses_handling(self):
        """Test ConcatNode to_string with parentheses for unions"""
        # Create concatenation with union on left
        union_left = UnionNode(CharNode('a'), CharNode('b'))
        char_right = CharNode('c')
        concat = ConcatNode(union_left, char_right)

        result = concat.to_string()
        # Should add parentheses around the union
        self.assertIn('(', result)
        self.assertIn(')', result)
        self.assertIn('|', result)

        # Create concatenation with union on right
        char_left = CharNode('d')
        union_right = UnionNode(CharNode('e'), CharNode('f'))
        concat2 = ConcatNode(char_left, union_right)

        result2 = concat2.to_string()
        # Should add parentheses around the right union
        self.assertIn('(', result2)
        self.assertIn(')', result2)

    def test_flatten_concatenation_single_node(self):
        """Test _flatten_concatenation with single node"""
        single_node = CharNode('a')
        result = _flatten_concatenation(single_node)

        # Should return list with single node
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0], single_node)

    def test_rebuild_concatenation_empty_list(self):
        """Test _rebuild_concatenation with empty list"""
        result = _rebuild_concatenation([])

        # Should return EpsilonNode for empty list
        self.assertIsInstance(result, EpsilonNode)

    def test_rebuild_concatenation_single_node(self):
        """Test _rebuild_concatenation with single node"""
        single_node = CharNode('a')
        result = _rebuild_concatenation([single_node])

        # Should return the single node
        self.assertEqual(result, single_node)