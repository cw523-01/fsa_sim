from django.test import TestCase
from simulator.fsa_equivalence import (
    normalise_automaton,
    find_state_mapping,
    are_dfas_isomorphic,
    are_automata_equivalent
)
from simulator.fsa_simulation import simulate_nondeterministic_fsa, simulate_deterministic_fsa
from simulator.fsa_properties import is_deterministic


class TestFSAEquivalence(TestCase):
    """Test cases for FSA equivalence checking functions"""

    def test_normalise_automaton_nfa_to_dfa(self):
        """Test normalising NFA to minimal DFA"""
        # Simple NFA that accepts strings ending with 'ab'
        nfa = {
            'states': ['S0', 'S1', 'S2'],
            'alphabet': ['a', 'b'],
            'transitions': {
                'S0': {'a': ['S0', 'S1'], 'b': ['S0']},
                'S1': {'b': ['S2']},
                'S2': {}
            },
            'startingState': 'S0',
            'acceptingStates': ['S2']
        }

        result = normalise_automaton(nfa)

        # Should return a DFA
        self.assertTrue(is_deterministic(result))
        self.assertIsInstance(result, dict)
        self.assertIn('states', result)
        self.assertIn('alphabet', result)
        self.assertIn('transitions', result)
        self.assertIn('startingState', result)
        self.assertIn('acceptingStates', result)

        # Test language equivalence
        test_strings = ['', 'a', 'b', 'ab', 'ba', 'aab', 'abb', 'abab']
        for test_string in test_strings:
            original_result = simulate_nondeterministic_fsa(nfa, test_string)
            normalized_result = simulate_deterministic_fsa(result, test_string)

            original_accepted = isinstance(original_result, list)
            normalized_accepted = isinstance(normalized_result, list)

            self.assertEqual(original_accepted, normalized_accepted,
                             f"Disagreement on string '{test_string}'")

    def test_normalise_automaton_dfa_minimisation(self):
        """Test normalising DFA performs minimisation"""
        # DFA with redundant states
        dfa = {
            'states': ['S0', 'S1', 'S2', 'S3'],
            'alphabet': ['a', 'b'],
            'transitions': {
                'S0': {'a': ['S1'], 'b': ['S0']},
                'S1': {'a': ['S2'], 'b': ['S0']},
                'S2': {'a': ['S2'], 'b': ['S2']},  # Accepting
                'S3': {'a': ['S2'], 'b': ['S2']}  # Equivalent to S2
            },
            'startingState': 'S0',
            'acceptingStates': ['S2', 'S3']
        }

        result = normalise_automaton(dfa)

        # Should be minimised
        self.assertTrue(is_deterministic(result))
        self.assertLessEqual(len(result['states']), len(dfa['states']))

        # Test language equivalence
        test_strings = ['', 'a', 'aa', 'ab', 'ba', 'aaa']
        for test_string in test_strings:
            original_result = simulate_deterministic_fsa(dfa, test_string)
            normalized_result = simulate_deterministic_fsa(result, test_string)

            original_accepted = isinstance(original_result, list)
            normalized_accepted = isinstance(normalized_result, list)

            self.assertEqual(original_accepted, normalized_accepted,
                             f"Disagreement on string '{test_string}'")

    def test_find_state_mapping_identical_dfas(self):
        """Test finding state mapping for identical DFAs"""
        dfa1 = {
            'states': ['S0', 'S1', 'S2'],
            'alphabet': ['a', 'b'],
            'transitions': {
                'S0': {'a': ['S1'], 'b': ['S0']},
                'S1': {'a': ['S2'], 'b': ['S0']},
                'S2': {'a': ['S2'], 'b': ['S2']}
            },
            'startingState': 'S0',
            'acceptingStates': ['S2']
        }

        dfa2 = {
            'states': ['S0', 'S1', 'S2'],
            'alphabet': ['a', 'b'],
            'transitions': {
                'S0': {'a': ['S1'], 'b': ['S0']},
                'S1': {'a': ['S2'], 'b': ['S0']},
                'S2': {'a': ['S2'], 'b': ['S2']}
            },
            'startingState': 'S0',
            'acceptingStates': ['S2']
        }

        mapping = find_state_mapping(dfa1, dfa2)

        # Should find identity mapping
        self.assertIsNotNone(mapping)
        self.assertEqual(mapping['S0'], 'S0')
        self.assertEqual(mapping['S1'], 'S1')
        self.assertEqual(mapping['S2'], 'S2')

    def test_find_state_mapping_renamed_states(self):
        """Test finding state mapping for DFAs with renamed states"""
        dfa1 = {
            'states': ['S0', 'S1', 'S2'],
            'alphabet': ['a', 'b'],
            'transitions': {
                'S0': {'a': ['S1'], 'b': ['S0']},
                'S1': {'a': ['S2'], 'b': ['S0']},
                'S2': {'a': ['S2'], 'b': ['S2']}
            },
            'startingState': 'S0',
            'acceptingStates': ['S2']
        }

        dfa2 = {
            'states': ['A', 'B', 'C'],
            'alphabet': ['a', 'b'],
            'transitions': {
                'A': {'a': ['B'], 'b': ['A']},
                'B': {'a': ['C'], 'b': ['A']},
                'C': {'a': ['C'], 'b': ['C']}
            },
            'startingState': 'A',
            'acceptingStates': ['C']
        }

        mapping = find_state_mapping(dfa1, dfa2)

        # Should find correct mapping
        self.assertIsNotNone(mapping)
        self.assertEqual(mapping['S0'], 'A')
        self.assertEqual(mapping['S1'], 'B')
        self.assertEqual(mapping['S2'], 'C')

    def test_find_state_mapping_different_structure(self):
        """Test that no mapping is found for DFAs with different structure"""
        dfa1 = {
            'states': ['S0', 'S1'],
            'alphabet': ['a', 'b'],
            'transitions': {
                'S0': {'a': ['S1'], 'b': ['S0']},
                'S1': {'a': ['S0'], 'b': ['S1']}
            },
            'startingState': 'S0',
            'acceptingStates': ['S1']
        }

        dfa2 = {
            'states': ['A', 'B'],
            'alphabet': ['a', 'b'],
            'transitions': {
                'A': {'a': ['A'], 'b': ['B']},
                'B': {'a': ['B'], 'b': ['B']}
            },
            'startingState': 'A',
            'acceptingStates': ['B']
        }

        mapping = find_state_mapping(dfa1, dfa2)

        # Should not find mapping (different transition structure)
        self.assertIsNone(mapping)

    def test_find_state_mapping_different_accepting_states(self):
        """Test that no mapping is found for DFAs with different accepting states"""
        dfa1 = {
            'states': ['S0', 'S1'],
            'alphabet': ['a'],
            'transitions': {
                'S0': {'a': ['S1']},
                'S1': {'a': ['S0']}
            },
            'startingState': 'S0',
            'acceptingStates': ['S1']
        }

        dfa2 = {
            'states': ['A', 'B'],
            'alphabet': ['a'],
            'transitions': {
                'A': {'a': ['B']},
                'B': {'a': ['A']}
            },
            'startingState': 'A',
            'acceptingStates': ['A']
        }

        mapping = find_state_mapping(dfa1, dfa2)

        # Should not find mapping (different accepting states)
        self.assertIsNone(mapping)

    def test_find_state_mapping_different_alphabet(self):
        """Test that no mapping is found for DFAs with different alphabets"""
        dfa1 = {
            'states': ['S0', 'S1'],
            'alphabet': ['a', 'b'],
            'transitions': {
                'S0': {'a': ['S1'], 'b': ['S0']},
                'S1': {'a': ['S0'], 'b': ['S1']}
            },
            'startingState': 'S0',
            'acceptingStates': ['S1']
        }

        dfa2 = {
            'states': ['A', 'B'],
            'alphabet': ['x', 'y'],
            'transitions': {
                'A': {'x': ['B'], 'y': ['A']},
                'B': {'x': ['A'], 'y': ['B']}
            },
            'startingState': 'A',
            'acceptingStates': ['B']
        }

        mapping = find_state_mapping(dfa1, dfa2)

        # Should not find mapping (different alphabet)
        self.assertIsNone(mapping)

    def test_find_state_mapping_different_number_of_states(self):
        """Test that no mapping is found for DFAs with different number of states"""
        dfa1 = {
            'states': ['S0', 'S1'],
            'alphabet': ['a'],
            'transitions': {
                'S0': {'a': ['S1']},
                'S1': {'a': ['S0']}
            },
            'startingState': 'S0',
            'acceptingStates': ['S1']
        }

        dfa2 = {
            'states': ['A', 'B', 'C'],
            'alphabet': ['a'],
            'transitions': {
                'A': {'a': ['B']},
                'B': {'a': ['C']},
                'C': {'a': ['A']}
            },
            'startingState': 'A',
            'acceptingStates': ['C']
        }

        mapping = find_state_mapping(dfa1, dfa2)

        # Should not find mapping (different number of states)
        self.assertIsNone(mapping)

    def test_are_dfas_isomorphic_true(self):
        """Test isomorphism check for isomorphic DFAs"""
        dfa1 = {
            'states': ['S0', 'S1', 'S2'],
            'alphabet': ['a', 'b'],
            'transitions': {
                'S0': {'a': ['S1'], 'b': ['S0']},
                'S1': {'a': ['S2'], 'b': ['S0']},
                'S2': {'a': ['S2'], 'b': ['S2']}
            },
            'startingState': 'S0',
            'acceptingStates': ['S2']
        }

        dfa2 = {
            'states': ['A', 'B', 'C'],
            'alphabet': ['a', 'b'],
            'transitions': {
                'A': {'a': ['B'], 'b': ['A']},
                'B': {'a': ['C'], 'b': ['A']},
                'C': {'a': ['C'], 'b': ['C']}
            },
            'startingState': 'A',
            'acceptingStates': ['C']
        }

        self.assertTrue(are_dfas_isomorphic(dfa1, dfa2))

    def test_are_dfas_isomorphic_false(self):
        """Test isomorphism check for non-isomorphic DFAs"""
        dfa1 = {
            'states': ['S0', 'S1'],
            'alphabet': ['a', 'b'],
            'transitions': {
                'S0': {'a': ['S1'], 'b': ['S0']},
                'S1': {'a': ['S0'], 'b': ['S1']}
            },
            'startingState': 'S0',
            'acceptingStates': ['S1']
        }

        dfa2 = {
            'states': ['A', 'B'],
            'alphabet': ['a', 'b'],
            'transitions': {
                'A': {'a': ['A'], 'b': ['B']},
                'B': {'a': ['B'], 'b': ['B']}
            },
            'startingState': 'A',
            'acceptingStates': ['B']
        }

        self.assertFalse(are_dfas_isomorphic(dfa1, dfa2))

    def test_are_automata_equivalent_identical_nfas(self):
        """Test equivalence of identical NFAs"""
        nfa1 = {
            'states': ['S0', 'S1', 'S2'],
            'alphabet': ['a', 'b'],
            'transitions': {
                'S0': {'a': ['S0', 'S1'], 'b': ['S0']},
                'S1': {'b': ['S2']},
                'S2': {}
            },
            'startingState': 'S0',
            'acceptingStates': ['S2']
        }

        nfa2 = {
            'states': ['S0', 'S1', 'S2'],
            'alphabet': ['a', 'b'],
            'transitions': {
                'S0': {'a': ['S0', 'S1'], 'b': ['S0']},
                'S1': {'b': ['S2']},
                'S2': {}
            },
            'startingState': 'S0',
            'acceptingStates': ['S2']
        }

        is_equivalent, details = are_automata_equivalent(nfa1, nfa2)

        self.assertTrue(is_equivalent)
        self.assertIsInstance(details, dict)
        self.assertIn('automaton1_type', details)
        self.assertIn('automaton2_type', details)
        self.assertIn('reason', details)
        self.assertEqual(details['automaton1_type'], 'NFA')
        self.assertEqual(details['automaton2_type'], 'NFA')

    def test_are_automata_equivalent_different_nfas_same_language(self):
        """Test equivalence of different NFAs accepting the same language"""
        # Both NFAs accept strings ending with 'ab'
        nfa1 = {
            'states': ['S0', 'S1', 'S2'],
            'alphabet': ['a', 'b'],
            'transitions': {
                'S0': {'a': ['S0', 'S1'], 'b': ['S0']},
                'S1': {'b': ['S2']},
                'S2': {}
            },
            'startingState': 'S0',
            'acceptingStates': ['S2']
        }

        nfa2 = {
            'states': ['Q0', 'Q1', 'Q2', 'Q3'],
            'alphabet': ['a', 'b'],
            'transitions': {
                'Q0': {'a': ['Q0', 'Q1'], 'b': ['Q0']},
                'Q1': {'b': ['Q2']},
                'Q2': {'a': ['Q0'], 'b': ['Q0']},
                'Q3': {}  # Unreachable state
            },
            'startingState': 'Q0',
            'acceptingStates': ['Q2']
        }

        is_equivalent, details = are_automata_equivalent(nfa1, nfa2)

        self.assertTrue(is_equivalent)
        self.assertIn('minimal_dfa1_states', details)
        self.assertIn('minimal_dfa2_states', details)
        self.assertEqual(details['reason'], 'Complete minimal DFAs are isomorphic')

    def test_are_automata_equivalent_different_languages(self):
        """Test non-equivalence of automata accepting different languages"""
        # NFA1 accepts strings ending with 'ab'
        nfa1 = {
            'states': ['S0', 'S1', 'S2'],
            'alphabet': ['a', 'b'],
            'transitions': {
                'S0': {'a': ['S0', 'S1'], 'b': ['S0']},
                'S1': {'b': ['S2']},
                'S2': {}
            },
            'startingState': 'S0',
            'acceptingStates': ['S2']
        }

        # NFA2 accepts strings ending with 'ba'
        nfa2 = {
            'states': ['Q0', 'Q1', 'Q2'],
            'alphabet': ['a', 'b'],
            'transitions': {
                'Q0': {'a': ['Q0'], 'b': ['Q0', 'Q1']},
                'Q1': {'a': ['Q2']},
                'Q2': {}
            },
            'startingState': 'Q0',
            'acceptingStates': ['Q2']
        }

        is_equivalent, details = are_automata_equivalent(nfa1, nfa2)

        self.assertFalse(is_equivalent)
        self.assertIn('reason', details)
        self.assertIn('not isomorphic', details['reason'])

    def test_are_automata_equivalent_nfa_vs_dfa(self):
        """Test equivalence of NFA and equivalent DFA"""
        # NFA that accepts strings ending with 'ab'
        nfa = {
            'states': ['S0', 'S1', 'S2'],
            'alphabet': ['a', 'b'],
            'transitions': {
                'S0': {'a': ['S0', 'S1'], 'b': ['S0']},
                'S1': {'b': ['S2']},
                'S2': {}
            },
            'startingState': 'S0',
            'acceptingStates': ['S2']
        }

        # Equivalent DFA
        dfa = {
            'states': ['D0', 'D1', 'D2'],
            'alphabet': ['a', 'b'],
            'transitions': {
                'D0': {'a': ['D1'], 'b': ['D0']},
                'D1': {'a': ['D1'], 'b': ['D2']},
                'D2': {'a': ['D1'], 'b': ['D0']}
            },
            'startingState': 'D0',
            'acceptingStates': ['D2']
        }

        is_equivalent, details = are_automata_equivalent(nfa, dfa)

        self.assertTrue(is_equivalent)
        self.assertEqual(details['automaton1_type'], 'NFA')
        self.assertEqual(details['automaton2_type'], 'DFA')

    def test_are_automata_equivalent_with_epsilon_transitions(self):
        """Test equivalence of automata with epsilon transitions"""
        # NFA with epsilon transitions
        nfa1 = {
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

        # Equivalent NFA without epsilon transitions
        nfa2 = {
            'states': ['Q0', 'Q1'],
            'alphabet': ['a', 'b'],
            'transitions': {
                'Q0': {'a': ['Q0'], 'b': ['Q1']},
                'Q1': {}
            },
            'startingState': 'Q0',
            'acceptingStates': ['Q1']
        }

        is_equivalent, details = are_automata_equivalent(nfa1, nfa2)

        self.assertTrue(is_equivalent)

    def test_are_automata_equivalent_empty_language(self):
        """Test equivalence of automata accepting empty language"""
        # NFA with no accepting states
        nfa1 = {
            'states': ['S0', 'S1'],
            'alphabet': ['a', 'b'],
            'transitions': {
                'S0': {'a': ['S1'], 'b': ['S0']},
                'S1': {'a': ['S0'], 'b': ['S1']}
            },
            'startingState': 'S0',
            'acceptingStates': []
        }

        # Another NFA with no accepting states
        nfa2 = {
            'states': ['Q0', 'Q1', 'Q2'],
            'alphabet': ['a', 'b'],
            'transitions': {
                'Q0': {'a': ['Q1'], 'b': ['Q2']},
                'Q1': {'a': ['Q0'], 'b': ['Q1']},
                'Q2': {'a': ['Q2'], 'b': ['Q0']}
            },
            'startingState': 'Q0',
            'acceptingStates': []
        }

        is_equivalent, details = are_automata_equivalent(nfa1, nfa2)

        self.assertTrue(is_equivalent)

    def test_are_automata_equivalent_universal_language(self):
        """Test equivalence of automata accepting universal language"""
        # NFA that accepts all strings
        nfa1 = {
            'states': ['S0'],
            'alphabet': ['a', 'b'],
            'transitions': {
                'S0': {'a': ['S0'], 'b': ['S0']}
            },
            'startingState': 'S0',
            'acceptingStates': ['S0']
        }

        # Another NFA that accepts all strings
        nfa2 = {
            'states': ['Q0', 'Q1'],
            'alphabet': ['a', 'b'],
            'transitions': {
                'Q0': {'a': ['Q1'], 'b': ['Q1']},
                'Q1': {'a': ['Q1'], 'b': ['Q1']}
            },
            'startingState': 'Q0',
            'acceptingStates': ['Q0', 'Q1']
        }

        is_equivalent, details = are_automata_equivalent(nfa1, nfa2)

        self.assertTrue(is_equivalent)

    def test_are_automata_equivalent_single_state(self):
        """Test equivalence of single-state automata"""
        # Single accepting state
        nfa1 = {
            'states': ['S0'],
            'alphabet': ['a'],
            'transitions': {
                'S0': {'a': ['S0']}
            },
            'startingState': 'S0',
            'acceptingStates': ['S0']
        }

        # Another single accepting state
        nfa2 = {
            'states': ['Q0'],
            'alphabet': ['a'],
            'transitions': {
                'Q0': {'a': ['Q0']}
            },
            'startingState': 'Q0',
            'acceptingStates': ['Q0']
        }

        is_equivalent, details = are_automata_equivalent(nfa1, nfa2)

        self.assertTrue(is_equivalent)

    def test_are_automata_equivalent_different_alphabets(self):
        """Test non-equivalence of automata with different alphabets"""
        nfa1 = {
            'states': ['S0', 'S1'],
            'alphabet': ['a', 'b'],
            'transitions': {
                'S0': {'a': ['S1'], 'b': ['S0']},
                'S1': {'a': ['S0'], 'b': ['S1']}
            },
            'startingState': 'S0',
            'acceptingStates': ['S1']
        }

        nfa2 = {
            'states': ['Q0', 'Q1'],
            'alphabet': ['x', 'y'],
            'transitions': {
                'Q0': {'x': ['Q1'], 'y': ['Q0']},
                'Q1': {'x': ['Q0'], 'y': ['Q1']}
            },
            'startingState': 'Q0',
            'acceptingStates': ['Q1']
        }

        is_equivalent, details = are_automata_equivalent(nfa1, nfa2)

        self.assertFalse(is_equivalent)

    def test_are_automata_equivalent_with_dead_states(self):
        """Test equivalence with dead states"""
        # NFA with dead states
        nfa1 = {
            'states': ['S0', 'S1', 'S2', 'S3'],
            'alphabet': ['a', 'b'],
            'transitions': {
                'S0': {'a': ['S1'], 'b': ['S2']},
                'S1': {'a': ['S1'], 'b': ['S1']},  # Dead state
                'S2': {'a': ['S3'], 'b': ['S2']},
                'S3': {'a': ['S3'], 'b': ['S3']}
            },
            'startingState': 'S0',
            'acceptingStates': ['S3']
        }

        # Equivalent NFA without dead states
        nfa2 = {
            'states': ['Q0', 'Q1', 'Q2'],
            'alphabet': ['a', 'b'],
            'transitions': {
                'Q0': {'b': ['Q1']},
                'Q1': {'a': ['Q2'], 'b': ['Q1']},
                'Q2': {'a': ['Q2'], 'b': ['Q2']}
            },
            'startingState': 'Q0',
            'acceptingStates': ['Q2']
        }

        is_equivalent, details = are_automata_equivalent(nfa1, nfa2)

        self.assertTrue(is_equivalent)

    def test_are_automata_equivalent_complex_case(self):
        """Test equivalence of complex automata"""
        # NFA that accepts strings containing 'aba' as substring
        nfa1 = {
            'states': ['S0', 'S1', 'S2', 'S3'],
            'alphabet': ['a', 'b'],
            'transitions': {
                'S0': {'a': ['S0', 'S1'], 'b': ['S0']},
                'S1': {'a': ['S1'], 'b': ['S2']},
                'S2': {'a': ['S1', 'S3'], 'b': ['S0']},
                'S3': {'a': ['S3'], 'b': ['S3']}
            },
            'startingState': 'S0',
            'acceptingStates': ['S3']
        }

        # Different NFA accepting the same language
        nfa2 = {
            'states': ['Q0', 'Q1', 'Q2', 'Q3'],
            'alphabet': ['a', 'b'],
            'transitions': {
                'Q0': {'a': ['Q1'], 'b': ['Q0']},
                'Q1': {'a': ['Q1'], 'b': ['Q2']},
                'Q2': {'a': ['Q3'], 'b': ['Q0']},
                'Q3': {'a': ['Q3'], 'b': ['Q3']},
            },
            'startingState': 'Q0',
            'acceptingStates': ['Q3']
        }

        is_equivalent, details = are_automata_equivalent(nfa1, nfa2)

        self.assertTrue(is_equivalent)

    def test_find_state_mapping_missing_transitions(self):
        """Test state mapping with missing transitions"""
        dfa1 = {
            'states': ['S0', 'S1'],
            'alphabet': ['a', 'b'],
            'transitions': {
                'S0': {'a': ['S1']},  # Missing 'b' transition
                'S1': {'a': ['S0'], 'b': ['S1']}
            },
            'startingState': 'S0',
            'acceptingStates': ['S1']
        }

        dfa2 = {
            'states': ['A', 'B'],
            'alphabet': ['a', 'b'],
            'transitions': {
                'A': {'a': ['B']},  # Missing 'b' transition
                'B': {'a': ['A'], 'b': ['B']}
            },
            'startingState': 'A',
            'acceptingStates': ['B']
        }

        mapping = find_state_mapping(dfa1, dfa2)

        # Should find mapping despite missing transitions
        self.assertIsNotNone(mapping)
        self.assertEqual(mapping['S0'], 'A')
        self.assertEqual(mapping['S1'], 'B')

    def test_find_state_mapping_inconsistent_transitions(self):
        """Test state mapping with inconsistent transitions"""
        dfa1 = {
            'states': ['S0', 'S1'],
            'alphabet': ['a', 'b'],
            'transitions': {
                'S0': {'a': ['S1'], 'b': ['S0']},
                'S1': {'a': ['S0'], 'b': ['S1']}
            },
            'startingState': 'S0',
            'acceptingStates': ['S1']
        }

        dfa2 = {
            'states': ['A', 'B'],
            'alphabet': ['a', 'b'],
            'transitions': {
                'A': {'a': ['B'], 'b': ['A']},
                'B': {'a': ['A'], 'b': ['A']}  # Different from dfa1
            },
            'startingState': 'A',
            'acceptingStates': ['B']
        }

        mapping = find_state_mapping(dfa1, dfa2)

        # Should not find mapping due to inconsistent transitions
        self.assertIsNone(mapping)

    def test_are_automata_equivalent_performance_tracking(self):
        """Test that equivalence checking provides performance details"""
        nfa1 = {
            'states': ['S0', 'S1', 'S2'],
            'alphabet': ['a', 'b'],
            'transitions': {
                'S0': {'a': ['S0', 'S1'], 'b': ['S0']},
                'S1': {'b': ['S2']},
                'S2': {}
            },
            'startingState': 'S0',
            'acceptingStates': ['S2']
        }

        nfa2 = {
            'states': ['Q0', 'Q1', 'Q2'],
            'alphabet': ['a', 'b'],
            'transitions': {
                'Q0': {'a': ['Q0', 'Q1'], 'b': ['Q0']},
                'Q1': {'b': ['Q2']},
                'Q2': {}
            },
            'startingState': 'Q0',
            'acceptingStates': ['Q2']
        }

        is_equivalent, details = are_automata_equivalent(nfa1, nfa2)

        # Check that performance details are provided
        self.assertIn('automaton1_states', details)
        self.assertIn('automaton2_states', details)
        self.assertIn('minimal_dfa1_states', details)
        self.assertIn('minimal_dfa2_states', details)
        self.assertIn('automaton1_type', details)
        self.assertIn('automaton2_type', details)
        self.assertIn('reason', details)

        # Check values make sense
        self.assertEqual(details['automaton1_states'], 3)
        self.assertEqual(details['automaton2_states'], 3)
        self.assertEqual(details['automaton1_type'], 'NFA')
        self.assertEqual(details['automaton2_type'], 'NFA')

    def test_normalise_automaton_with_epsilon_transitions(self):
        """Test normalisation of automaton with epsilon transitions"""
        nfa_with_epsilon = {
            'states': ['S0', 'S1', 'S2'],
            'alphabet': ['a', 'b'],
            'transitions': {
                'S0': {'': ['S1'], 'a': ['S0']},
                'S1': {'': ['S2']},
                'S2': {'b': ['S0']}
            },
            'startingState': 'S0',
            'acceptingStates': ['S2']
        }

        result = normalise_automaton(nfa_with_epsilon)

        # Should be deterministic and have no epsilon transitions
        self.assertTrue(is_deterministic(result))
        self.assertNotIn('', result['alphabet'])

        # Should preserve language
        test_strings = ['', 'a', 'b', 'ab', 'aab', 'abb', 'ba']
        for test_string in test_strings:
            original_result = simulate_nondeterministic_fsa(nfa_with_epsilon, test_string)
            normalized_result = simulate_deterministic_fsa(result, test_string)

            original_accepted = isinstance(original_result, list)
            normalized_accepted = isinstance(normalized_result, list)

            self.assertEqual(original_accepted, normalized_accepted,
                             f"Disagreement on string '{test_string}'")

    def test_are_automata_equivalent_with_state_mapping_details(self):
        """Test that equivalence checking provides state mapping details when equivalent"""
        # Simple equivalent DFAs
        dfa1 = {
            'states': ['S0', 'S1'],
            'alphabet': ['a', 'b'],
            'transitions': {
                'S0': {'a': ['S1'], 'b': ['S0']},
                'S1': {'a': ['S0'], 'b': ['S1']}
            },
            'startingState': 'S0',
            'acceptingStates': ['S1']
        }

        dfa2 = {
            'states': ['A', 'B'],
            'alphabet': ['a', 'b'],
            'transitions': {
                'A': {'a': ['B'], 'b': ['A']},
                'B': {'a': ['A'], 'b': ['B']}
            },
            'startingState': 'A',
            'acceptingStates': ['B']
        }

        is_equivalent, details = are_automata_equivalent(dfa1, dfa2)

        self.assertTrue(is_equivalent)
        self.assertIn('state_mapping', details)
        self.assertIsInstance(details['state_mapping'], dict)
        self.assertEqual(details['reason'], 'Complete minimal DFAs are isomorphic')

    def test_find_state_mapping_single_state_dfas(self):
        """Test state mapping with single state DFAs"""
        dfa1 = {
            'states': ['S0'],
            'alphabet': ['a'],
            'transitions': {
                'S0': {'a': ['S0']}
            },
            'startingState': 'S0',
            'acceptingStates': ['S0']
        }

        dfa2 = {
            'states': ['Q0'],
            'alphabet': ['a'],
            'transitions': {
                'Q0': {'a': ['Q0']}
            },
            'startingState': 'Q0',
            'acceptingStates': ['Q0']
        }

        mapping = find_state_mapping(dfa1, dfa2)

        # Should find single state mapping
        self.assertIsNotNone(mapping)
        self.assertEqual(len(mapping), 1)
        self.assertEqual(mapping['S0'], 'Q0')

    def test_normalise_automaton_already_minimal_dfa(self):
        """Test normalisation of already minimal DFA"""
        minimal_dfa = {
            'states': ['S0', 'S1'],
            'alphabet': ['a', 'b'],
            'transitions': {
                'S0': {'a': ['S1'], 'b': ['S0']},
                'S1': {'a': ['S0'], 'b': ['S1']}
            },
            'startingState': 'S0',
            'acceptingStates': ['S1']
        }

        result = normalise_automaton(minimal_dfa)

        # Should remain the same size or smaller
        self.assertTrue(is_deterministic(result))
        self.assertLessEqual(len(result['states']), len(minimal_dfa['states']))

        # Should preserve language
        test_strings = ['', 'a', 'b', 'ab', 'ba', 'aa', 'bb']
        for test_string in test_strings:
            original_result = simulate_deterministic_fsa(minimal_dfa, test_string)
            normalized_result = simulate_deterministic_fsa(result, test_string)

            original_accepted = isinstance(original_result, list)
            normalized_accepted = isinstance(normalized_result, list)

            self.assertEqual(original_accepted, normalized_accepted,
                             f"Disagreement on string '{test_string}'")

    def test_comprehensive_language_equivalence_verification(self):
        """Comprehensive test verifying language equivalence across multiple string lengths"""
        # Create two different NFAs that should accept the same language
        nfa1 = {
            'states': ['S0', 'S1', 'S2'],
            'alphabet': ['a', 'b'],
            'transitions': {
                'S0': {'a': ['S0', 'S1'], 'b': ['S0']},
                'S1': {'b': ['S2']},
                'S2': {}
            },
            'startingState': 'S0',
            'acceptingStates': ['S2']
        }

        nfa2 = {
            'states': ['Q0', 'Q1', 'Q2', 'Q3'],
            'alphabet': ['a', 'b'],
            'transitions': {
                'Q0': {'a': ['Q0', 'Q1'], 'b': ['Q0']},
                'Q1': {'b': ['Q2']},
                'Q2': {'a': ['Q0'], 'b': ['Q0']},
                'Q3': {}  # Unreachable
            },
            'startingState': 'Q0',
            'acceptingStates': ['Q2']
        }

        # Test equivalence
        is_equivalent, details = are_automata_equivalent(nfa1, nfa2)
        self.assertTrue(is_equivalent)

        # Verify language equivalence with comprehensive string testing
        alphabet = ['a', 'b']

        # Test all strings up to length 4
        def generate_strings(alphabet, max_length):
            strings = ['']  # Empty string
            for length in range(1, max_length + 1):
                from itertools import product
                for combo in product(alphabet, repeat=length):
                    strings.append(''.join(combo))
            return strings

        test_strings = generate_strings(alphabet, 4)

        for test_string in test_strings:
            result1 = simulate_nondeterministic_fsa(nfa1, test_string)
            result2 = simulate_nondeterministic_fsa(nfa2, test_string)

            accepted1 = isinstance(result1, list)
            accepted2 = isinstance(result2, list)

            self.assertEqual(accepted1, accepted2,
                             f"Language disagreement on string '{test_string}'")

    def test_edge_cases_with_complex_alphabets(self):
        """Test equivalence with complex alphabets"""
        # Automata with larger alphabets
        nfa1 = {
            'states': ['S0', 'S1'],
            'alphabet': ['0', '1', '2', '3', '4'],
            'transitions': {
                'S0': {'0': ['S0'], '1': ['S1'], '2': ['S0'], '3': ['S0'], '4': ['S0']},
                'S1': {'0': ['S0'], '1': ['S0'], '2': ['S0'], '3': ['S0'], '4': ['S0']}
            },
            'startingState': 'S0',
            'acceptingStates': ['S1']
        }

        nfa2 = {
            'states': ['A', 'B'],
            'alphabet': ['0', '1', '2', '3', '4'],
            'transitions': {
                'A': {'0': ['A'], '1': ['B'], '2': ['A'], '3': ['A'], '4': ['A']},
                'B': {'0': ['A'], '1': ['A'], '2': ['A'], '3': ['A'], '4': ['A']}
            },
            'startingState': 'A',
            'acceptingStates': ['B']
        }

        is_equivalent, details = are_automata_equivalent(nfa1, nfa2)
        self.assertTrue(is_equivalent)