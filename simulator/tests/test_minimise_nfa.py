from django.test import TestCase
from simulator.minimise_nfa import minimise_nfa, MinimisationResult
from simulator.fsa_simulation import simulate_nondeterministic_fsa, simulate_deterministic_fsa
from simulator.fsa_properties import is_deterministic


class TestMinimiseNFA(TestCase):
    """Test cases for NFA minimisation function"""

    def test_simple_nfa_minimisation(self):
        """Test minimisation of a simple NFA"""
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

        result = minimise_nfa(nfa)

        # Check result structure
        self.assertIsInstance(result, MinimisationResult)
        self.assertEqual(result.original_states, 3)
        self.assertLessEqual(result.final_states, result.original_states)
        self.assertIsInstance(result.nfa, dict)
        self.assertIsInstance(result.stages, list)
        self.assertIsInstance(result.candidate_results, list)

        # Test language equivalence
        test_strings = ['', 'a', 'b', 'ab', 'ba', 'aab', 'abb', 'abab']
        for test_string in test_strings:
            original_result = simulate_nondeterministic_fsa(nfa, test_string)
            minimised_result = simulate_nondeterministic_fsa(result.nfa, test_string)

            original_accepted = isinstance(original_result, list)
            minimised_accepted = isinstance(minimised_result, list)

            self.assertEqual(original_accepted, minimised_accepted,
                             f"Disagreement on string '{test_string}'")

    def test_nfa_with_epsilon_transitions(self):
        """Test minimisation of NFA with epsilon transitions"""
        # NFA with epsilon transitions
        nfa = {
            'states': ['S0', 'S1', 'S2', 'S3'],
            'alphabet': ['a', 'b'],
            'transitions': {
                'S0': {'': ['S1'], 'a': ['S0']},
                'S1': {'': ['S2']},
                'S2': {'b': ['S3']},
                'S3': {}
            },
            'startingState': 'S0',
            'acceptingStates': ['S3']
        }

        result = minimise_nfa(nfa)

        # Check result structure
        self.assertIsInstance(result, MinimisationResult)
        self.assertEqual(result.original_states, 4)
        self.assertLessEqual(result.final_states, result.original_states)

        # Test language equivalence
        test_strings = ['', 'a', 'b', 'ab', 'aab', 'aaab', 'bb', 'aba']
        for test_string in test_strings:
            original_result = simulate_nondeterministic_fsa(nfa, test_string)
            minimised_result = simulate_nondeterministic_fsa(result.nfa, test_string)

            original_accepted = isinstance(original_result, list)
            minimised_accepted = isinstance(minimised_result, list)

            self.assertEqual(original_accepted, minimised_accepted,
                             f"Disagreement on string '{test_string}'")

    def test_nfa_with_unreachable_states(self):
        """Test minimisation of NFA with unreachable states"""
        # NFA with unreachable state S3
        nfa = {
            'states': ['S0', 'S1', 'S2', 'S3'],
            'alphabet': ['a', 'b'],
            'transitions': {
                'S0': {'a': ['S1'], 'b': ['S0']},
                'S1': {'a': ['S2'], 'b': ['S0']},
                'S2': {'a': ['S2'], 'b': ['S2']},
                'S3': {'a': ['S3'], 'b': ['S3']}  # Unreachable
            },
            'startingState': 'S0',
            'acceptingStates': ['S2']
        }

        result = minimise_nfa(nfa)

        # Should remove unreachable state
        self.assertIsInstance(result, MinimisationResult)
        self.assertEqual(result.original_states, 4)
        self.assertLess(result.final_states, result.original_states)
        self.assertGreater(result.reduction, 0)

        # Test language equivalence
        test_strings = ['', 'a', 'aa', 'ab', 'ba', 'aaa', 'aab']
        for test_string in test_strings:
            original_result = simulate_nondeterministic_fsa(nfa, test_string)
            minimised_result = simulate_nondeterministic_fsa(result.nfa, test_string)

            original_accepted = isinstance(original_result, list)
            minimised_accepted = isinstance(minimised_result, list)

            self.assertEqual(original_accepted, minimised_accepted,
                             f"Disagreement on string '{test_string}'")

    def test_nfa_with_dead_states(self):
        """Test minimisation of NFA with dead states"""
        # NFA with dead states that can't reach accepting states
        nfa = {
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

        result = minimise_nfa(nfa)

        # Should remove dead state S1
        self.assertIsInstance(result, MinimisationResult)
        self.assertEqual(result.original_states, 4)
        self.assertLess(result.final_states, result.original_states)

        # Test language equivalence
        test_strings = ['', 'a', 'b', 'ba', 'baa', 'bb', 'bba']
        for test_string in test_strings:
            original_result = simulate_nondeterministic_fsa(nfa, test_string)
            minimised_result = simulate_nondeterministic_fsa(result.nfa, test_string)

            original_accepted = isinstance(original_result, list)
            minimised_accepted = isinstance(minimised_result, list)

            self.assertEqual(original_accepted, minimised_accepted,
                             f"Disagreement on string '{test_string}'")

    def test_already_minimal_nfa(self):
        """Test minimisation of an already minimal NFA"""
        # Simple NFA that should be hard to minimise further
        nfa = {
            'states': ['S0', 'S1'],
            'alphabet': ['a', 'b'],
            'transitions': {
                'S0': {'a': ['S1'], 'b': ['S0']},
                'S1': {'a': ['S0'], 'b': ['S1']}
            },
            'startingState': 'S0',
            'acceptingStates': ['S1']
        }

        result = minimise_nfa(nfa)

        # Should not increase size
        self.assertIsInstance(result, MinimisationResult)
        self.assertEqual(result.original_states, 2)
        self.assertLessEqual(result.final_states, result.original_states)

        # Test language equivalence
        test_strings = ['', 'a', 'b', 'ab', 'ba', 'aa', 'bb']
        for test_string in test_strings:
            original_result = simulate_nondeterministic_fsa(nfa, test_string)
            minimised_result = simulate_nondeterministic_fsa(result.nfa, test_string)

            original_accepted = isinstance(original_result, list)
            minimised_accepted = isinstance(minimised_result, list)

            self.assertEqual(original_accepted, minimised_accepted,
                             f"Disagreement on string '{test_string}'")

    def test_complex_nfa_minimisation(self):
        """Test minimisation of a complex NFA"""
        # NFA that accepts strings containing 'aba' as substring
        nfa = {
            'states': ['S0', 'S1', 'S2', 'S3', 'S4'],
            'alphabet': ['a', 'b'],
            'transitions': {
                'S0': {'a': ['S0', 'S1'], 'b': ['S0']},
                'S1': {'a': ['S1'], 'b': ['S2']},
                'S2': {'a': ['S1', 'S3'], 'b': ['S0']},
                'S3': {'a': ['S3'], 'b': ['S3']},
                'S4': {'a': ['S4'], 'b': ['S4']}  # Unreachable
            },
            'startingState': 'S0',
            'acceptingStates': ['S3']
        }

        result = minimise_nfa(nfa)

        # Should reduce size due to unreachable state
        self.assertIsInstance(result, MinimisationResult)
        self.assertEqual(result.original_states, 5)
        self.assertLess(result.final_states, result.original_states)

        # Test language equivalence
        test_strings = ['', 'a', 'ab', 'aba', 'abab', 'baba', 'aaba', 'abaa']
        for test_string in test_strings:
            original_result = simulate_nondeterministic_fsa(nfa, test_string)
            minimised_result = simulate_nondeterministic_fsa(result.nfa, test_string)

            original_accepted = isinstance(original_result, list)
            minimised_accepted = isinstance(minimised_result, list)

            self.assertEqual(original_accepted, minimised_accepted,
                             f"Disagreement on string '{test_string}'")

    def test_empty_nfa(self):
        """Test minimisation of empty NFA"""
        nfa = {
            'states': [],
            'alphabet': ['a', 'b'],
            'transitions': {},
            'startingState': '',
            'acceptingStates': []
        }

        result = minimise_nfa(nfa)

        # Should handle empty NFA gracefully
        self.assertIsInstance(result, MinimisationResult)
        self.assertEqual(result.original_states, 0)
        self.assertEqual(result.final_states, 0)
        self.assertEqual(result.reduction, 0)
        self.assertEqual(result.reduction_percent, 0)
        self.assertTrue(result.is_optimal)

    def test_nfa_becomes_empty_after_preprocessing(self):
        """Test NFA that becomes empty after removing dead/unreachable states"""
        # NFA where start state is dead (can't reach accepting states)
        nfa = {
            'states': ['S0', 'S1'],
            'alphabet': ['a'],
            'transitions': {
                'S0': {'a': ['S0']},  # Loops on itself, can't reach S1
                'S1': {'a': ['S1']}  # Accepting but unreachable
            },
            'startingState': 'S0',
            'acceptingStates': ['S1']
        }

        result = minimise_nfa(nfa)

        # Should result in empty NFA
        self.assertIsInstance(result, MinimisationResult)
        self.assertEqual(result.original_states, 2)
        self.assertEqual(result.final_states, 0)
        self.assertEqual(result.reduction, 2)
        self.assertEqual(result.reduction_percent, 100.0)
        self.assertTrue(result.is_optimal)

    def test_single_state_nfa(self):
        """Test minimisation of single-state NFA"""
        # Single accepting state
        nfa = {
            'states': ['S0'],
            'alphabet': ['a', 'b'],
            'transitions': {
                'S0': {'a': ['S0'], 'b': ['S0']}
            },
            'startingState': 'S0',
            'acceptingStates': ['S0']
        }

        result = minimise_nfa(nfa)

        # Should remain single state
        self.assertIsInstance(result, MinimisationResult)
        self.assertEqual(result.original_states, 1)
        self.assertEqual(result.final_states, 1)
        self.assertEqual(result.reduction, 0)

        # Test language equivalence
        test_strings = ['', 'a', 'b', 'ab', 'ba', 'aabb']
        for test_string in test_strings:
            original_result = simulate_nondeterministic_fsa(nfa, test_string)
            minimised_result = simulate_nondeterministic_fsa(result.nfa, test_string)

            original_accepted = isinstance(original_result, list)
            minimised_accepted = isinstance(minimised_result, list)

            self.assertEqual(original_accepted, minimised_accepted,
                             f"Disagreement on string '{test_string}'")

    def test_nfa_no_accepting_states(self):
        """Test minimisation of NFA with no accepting states"""
        nfa = {
            'states': ['S0', 'S1', 'S2'],
            'alphabet': ['a', 'b'],
            'transitions': {
                'S0': {'a': ['S1'], 'b': ['S2']},
                'S1': {'a': ['S0'], 'b': ['S2']},
                'S2': {'a': ['S2'], 'b': ['S2']}
            },
            'startingState': 'S0',
            'acceptingStates': []
        }

        result = minimise_nfa(nfa)

        # Should minimise effectively
        self.assertIsInstance(result, MinimisationResult)
        self.assertEqual(result.original_states, 3)
        self.assertEqual(result.nfa['acceptingStates'], [])

        # All strings should be rejected
        test_strings = ['', 'a', 'b', 'ab', 'ba']
        for test_string in test_strings:
            minimised_result = simulate_nondeterministic_fsa(result.nfa, test_string)
            self.assertIsInstance(minimised_result, dict)
            self.assertFalse(minimised_result.get('accepted', True))

    def test_nfa_multiple_accepting_states(self):
        """Test minimisation of NFA with multiple accepting states"""
        nfa = {
            'states': ['S0', 'S1', 'S2', 'S3'],
            'alphabet': ['a', 'b'],
            'transitions': {
                'S0': {'a': ['S1'], 'b': ['S2']},
                'S1': {'a': ['S3'], 'b': ['S1']},
                'S2': {'a': ['S2'], 'b': ['S3']},
                'S3': {'a': ['S3'], 'b': ['S3']}
            },
            'startingState': 'S0',
            'acceptingStates': ['S1', 'S2', 'S3']
        }

        result = minimise_nfa(nfa)

        # Should handle multiple accepting states
        self.assertIsInstance(result, MinimisationResult)
        self.assertEqual(result.original_states, 4)
        self.assertTrue(len(result.nfa['acceptingStates']) > 0)

        # Test language equivalence
        test_strings = ['', 'a', 'b', 'ab', 'ba', 'aa', 'bb']
        for test_string in test_strings:
            original_result = simulate_nondeterministic_fsa(nfa, test_string)
            minimised_result = simulate_nondeterministic_fsa(result.nfa, test_string)

            original_accepted = isinstance(original_result, list)
            minimised_accepted = isinstance(minimised_result, list)

            self.assertEqual(original_accepted, minimised_accepted,
                             f"Disagreement on string '{test_string}'")

    def test_minimisation_result_properties(self):
        """Test properties of MinimisationResult"""
        nfa = {
            'states': ['S0', 'S1', 'S2', 'S3'],
            'alphabet': ['a', 'b'],
            'transitions': {
                'S0': {'a': ['S1'], 'b': ['S0']},
                'S1': {'a': ['S2'], 'b': ['S0']},
                'S2': {'a': ['S2'], 'b': ['S2']},
                'S3': {'a': ['S3'], 'b': ['S3']}  # Unreachable
            },
            'startingState': 'S0',
            'acceptingStates': ['S2']
        }

        result = minimise_nfa(nfa)

        # Check all properties are present and correct types
        self.assertIsInstance(result.nfa, dict)
        self.assertIsInstance(result.original_states, int)
        self.assertIsInstance(result.final_states, int)
        self.assertIsInstance(result.reduction, int)
        self.assertIsInstance(result.reduction_percent, float)
        self.assertIsInstance(result.is_optimal, bool)
        self.assertIsInstance(result.method_used, str)
        self.assertIsInstance(result.stages, list)
        self.assertIsInstance(result.candidate_results, list)

        # Check mathematical relationships
        self.assertEqual(result.reduction, result.original_states - result.final_states)
        if result.original_states > 0:
            expected_percent = (result.reduction / result.original_states) * 100
            self.assertAlmostEqual(result.reduction_percent, expected_percent, places=1)

        # Check that stages and candidate_results are populated
        self.assertGreater(len(result.stages), 0)
        self.assertGreater(len(result.candidate_results), 0)

    def test_minimisation_with_epsilon_loops(self):
        """Test minimisation of NFA with epsilon loops"""
        nfa = {
            'states': ['S0', 'S1', 'S2'],
            'alphabet': ['a'],
            'transitions': {
                'S0': {'': ['S1']},
                'S1': {'': ['S1'], 'a': ['S2']},  # Epsilon self-loop
                'S2': {}
            },
            'startingState': 'S0',
            'acceptingStates': ['S2']
        }

        result = minimise_nfa(nfa)

        # Should handle epsilon loops correctly
        self.assertIsInstance(result, MinimisationResult)
        self.assertEqual(result.original_states, 3)

        # Test language equivalence
        test_strings = ['', 'a', 'aa', 'aaa']
        for test_string in test_strings:
            original_result = simulate_nondeterministic_fsa(nfa, test_string)
            minimised_result = simulate_nondeterministic_fsa(result.nfa, test_string)

            original_accepted = isinstance(original_result, list)
            minimised_accepted = isinstance(minimised_result, list)

            self.assertEqual(original_accepted, minimised_accepted,
                             f"Disagreement on string '{test_string}'")

    def test_candidate_results_structure(self):
        """Test that candidate_results contains proper information"""
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

        result = minimise_nfa(nfa)

        # Check candidate_results structure
        self.assertGreater(len(result.candidate_results), 0)

        for candidate in result.candidate_results:
            self.assertIsInstance(candidate, dict)
            self.assertIn('nfa', candidate)
            self.assertIn('method', candidate)
            self.assertIn('states', candidate)
            self.assertIsInstance(candidate['nfa'], dict)
            self.assertIsInstance(candidate['method'], str)
            self.assertIsInstance(candidate['states'], int)

    def test_empty_alphabet_nfa(self):
        """Test minimisation of NFA with empty alphabet"""
        nfa = {
            'states': ['S0', 'S1'],
            'alphabet': [],
            'transitions': {
                'S0': {},
                'S1': {}
            },
            'startingState': 'S0',
            'acceptingStates': ['S1']
        }

        result = minimise_nfa(nfa)

        # Should handle empty alphabet
        self.assertIsInstance(result, MinimisationResult)
        self.assertEqual(result.nfa['alphabet'], [])

    def test_minimisation_stages_tracking(self):
        """Test that minimisation tracks stages properly"""
        nfa = {
            'states': ['S0', 'S1', 'S2', 'S3'],
            'alphabet': ['a', 'b'],
            'transitions': {
                'S0': {'a': ['S1'], 'b': ['S0']},
                'S1': {'a': ['S2'], 'b': ['S0']},
                'S2': {'a': ['S2'], 'b': ['S2']},
                'S3': {'a': ['S3'], 'b': ['S3']}  # Unreachable
            },
            'startingState': 'S0',
            'acceptingStates': ['S2']
        }

        result = minimise_nfa(nfa)

        # Check that stages are tracked
        self.assertIsInstance(result.stages, list)
        self.assertGreater(len(result.stages), 0)

        # Should include preprocessing stage
        self.assertIn("Preprocessing", result.stages)

        # All stages should be strings
        for stage in result.stages:
            self.assertIsInstance(stage, str)

    def test_large_nfa_minimisation(self):
        """Test minimisation of larger NFA"""
        # Create larger NFA with redundant states
        states = [f'S{i}' for i in range(8)]
        transitions = {
            'S0': {'a': ['S1'], 'b': ['S0']},
            'S1': {'a': ['S2'], 'b': ['S0']},
            'S2': {'a': ['S3'], 'b': ['S0']},
            'S3': {'a': ['S3'], 'b': ['S3']},
            'S4': {'a': ['S4'], 'b': ['S4']},  # Unreachable
            'S5': {'a': ['S5'], 'b': ['S5']},  # Unreachable
            'S6': {'a': ['S6'], 'b': ['S6']},  # Unreachable
            'S7': {'a': ['S7'], 'b': ['S7']}  # Unreachable
        }

        nfa = {
            'states': states,
            'alphabet': ['a', 'b'],
            'transitions': transitions,
            'startingState': 'S0',
            'acceptingStates': ['S3']
        }

        result = minimise_nfa(nfa)

        # Should significantly reduce size
        self.assertIsInstance(result, MinimisationResult)
        self.assertEqual(result.original_states, 8)
        self.assertLess(result.final_states, result.original_states)
        self.assertGreater(result.reduction, 0)

        # Test basic language equivalence
        test_strings = ['', 'a', 'aa', 'aaa', 'b', 'ab']
        for test_string in test_strings:
            original_result = simulate_nondeterministic_fsa(nfa, test_string)
            minimised_result = simulate_nondeterministic_fsa(result.nfa, test_string)

            original_accepted = isinstance(original_result, list)
            minimised_accepted = isinstance(minimised_result, list)

            self.assertEqual(original_accepted, minimised_accepted,
                             f"Disagreement on string '{test_string}'")

    def test_nfa_structure_preservation(self):
        """Test that minimised NFA preserves required structure"""
        nfa = {
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

        result = minimise_nfa(nfa)

        # Check required structure
        required_keys = ['states', 'alphabet', 'transitions', 'startingState', 'acceptingStates']
        for key in required_keys:
            self.assertIn(key, result.nfa)

        # Check types
        self.assertIsInstance(result.nfa['states'], list)
        self.assertIsInstance(result.nfa['alphabet'], list)
        self.assertIsInstance(result.nfa['transitions'], dict)
        self.assertIsInstance(result.nfa['startingState'], str)
        self.assertIsInstance(result.nfa['acceptingStates'], list)

        # Check consistency
        if result.nfa['states']:
            self.assertIn(result.nfa['startingState'], result.nfa['states'])
            for accepting_state in result.nfa['acceptingStates']:
                self.assertIn(accepting_state, result.nfa['states'])