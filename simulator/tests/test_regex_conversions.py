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
    eliminate_states
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
            'a+b*c?'
        ]

        for original_regex in original_regexes:
            # Convert regex to FSA
            fsa = regex_to_epsilon_nfa(original_regex)

            # Convert FSA back to regex
            result = fsa_to_regex(fsa)

            self.assertTrue(result['valid'], f"Failed to convert FSA back to regex for: {original_regex}")
            print(result)
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