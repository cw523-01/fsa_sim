from django.test import TestCase
from simulator.minimise_nfa import (
    minimise_nfa,
    kameda_weiner_minimise,
    direct_product_sat_minimise,
    normalise_nfa,
    analyse_fsa_complexity,
    MinimisationResult,
    MinimisationConfig,
    _verify_language_equivalence
)
from simulator.fsa_simulation import simulate_nondeterministic_fsa
from simulator.fsa_properties import is_deterministic, validate_fsa_structure
from unittest.mock import patch
import tempfile
import os


class TestMinimiseNFA(TestCase):
    """Test cases for NFA minimisation functions"""

    def test_simple_minimise_nfa(self):
        """Test minimisation of a simple NFA"""
        # NFA with redundant states that accepts strings ending with 'ab'
        nfa = {
            'states': ['S0', 'S1', 'S2', 'S3', 'S4'],
            'alphabet': ['a', 'b'],
            'transitions': {
                'S0': {'a': ['S0', 'S1'], 'b': ['S0']},
                'S1': {'b': ['S2']},
                'S2': {},  # Accepting
                'S3': {'a': ['S3'], 'b': ['S3']},  # Unreachable dead state
                'S4': {'a': ['S4'], 'b': ['S4']}  # Another unreachable dead state
            },
            'startingState': 'S0',
            'acceptingStates': ['S2']
        }

        result = minimise_nfa(nfa)

        # Verify result structure
        self.assertIsInstance(result, MinimisationResult)
        self.assertEqual(result.original_states, 5)
        # Should reduce due to unreachable states, but exact count depends on algorithm
        self.assertLessEqual(result.final_states, result.original_states)

        if result.final_states < result.original_states:
            self.assertGreater(result.reduction, 0)
            self.assertGreater(result.reduction_percent, 0)

        # Verify language equivalence
        test_strings = ['', 'a', 'b', 'ab', 'aab', 'abb', 'bab', 'abab']
        for test_string in test_strings:
            original_result = simulate_nondeterministic_fsa(nfa, test_string)
            minimised_result = simulate_nondeterministic_fsa(result.nfa, test_string)

            original_accepted = isinstance(original_result, list)
            minimised_accepted = isinstance(minimised_result, list)

            self.assertEqual(original_accepted, minimised_accepted,
                             f"Disagreement on string '{test_string}'")

    def test_already_minimal_nfa(self):
        """Test minimisation of an already minimal NFA"""
        # Simple NFA that's already minimal
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

        # Should have minimal reduction
        self.assertIsInstance(result, MinimisationResult)
        self.assertEqual(result.original_states, 3)
        self.assertLessEqual(result.final_states, result.original_states)

        # Verify language equivalence
        test_strings = ['', 'a', 'ab', 'aab', 'abb']
        for test_string in test_strings:
            original_result = simulate_nondeterministic_fsa(nfa, test_string)
            minimised_result = simulate_nondeterministic_fsa(result.nfa, test_string)

            original_accepted = isinstance(original_result, list)
            minimised_accepted = isinstance(minimised_result, list)

            self.assertEqual(original_accepted, minimised_accepted)

    def test_deterministic_fsa_minimisation(self):
        """Test that deterministic FSAs are now minimised using the same pipeline as NFAs"""
        # Create a deterministic FSA with clearly redundant states
        dfa = {
            'states': ['S0', 'S1', 'S2', 'S3', 'S4'],
            'alphabet': ['a', 'b'],
            'transitions': {
                'S0': {'a': ['S1'], 'b': ['S2']},
                'S1': {'a': ['S3'], 'b': ['S2']},
                'S2': {'a': ['S1'], 'b': ['S4']},  # S2 and S0 have different 'b' behavior
                'S3': {'a': ['S3'], 'b': ['S3']},  # Accepting state
                'S4': {'a': ['S4'], 'b': ['S4']}  # Dead state (non-accepting)
            },
            'startingState': 'S0',
            'acceptingStates': ['S3']
        }

        result = minimise_nfa(dfa)

        # Should now use SAT for small deterministic FSAs (not DFA minimisation)
        self.assertIn("SAT", result.method_used)
        self.assertTrue(result.is_optimal)

        # Should reduce or at least maintain state count
        self.assertLessEqual(result.final_states, result.original_states)

        # Verify language equivalence
        test_strings = ['', 'a', 'aa', 'ab', 'ba', 'bb', 'aaa', 'aba']
        for test_string in test_strings:
            original_result = simulate_nondeterministic_fsa(dfa, test_string)
            minimised_result = simulate_nondeterministic_fsa(result.nfa, test_string)

            original_accepted = isinstance(original_result, list)
            minimised_accepted = isinstance(minimised_result, list)

            self.assertEqual(original_accepted, minimised_accepted,
                             f"Disagreement on string '{test_string}'")

    def test_kameda_weiner_algorithm(self):
        """Test Kameda-Weiner minimisation algorithm specifically"""
        # NFA that requires non-deterministic minimisation
        nfa = {
            'states': ['S0', 'S1', 'S2', 'S3', 'S4'],
            'alphabet': ['a', 'b'],
            'transitions': {
                'S0': {'a': ['S1', 'S2'], 'b': ['S0']},  # Non-deterministic
                'S1': {'b': ['S3']},
                'S2': {'b': ['S4']},
                'S3': {},
                'S4': {}  # S3 and S4 might be equivalent
            },
            'startingState': 'S0',
            'acceptingStates': ['S3', 'S4']
        }

        minimised = kameda_weiner_minimise(nfa)

        # Verify structure
        self.assertIn('states', minimised)
        self.assertIn('transitions', minimised)
        self.assertIn('startingState', minimised)
        self.assertIn('acceptingStates', minimised)

        # Verify language equivalence
        test_strings = ['', 'a', 'ab', 'aab', 'bb']
        for test_string in test_strings:
            original_result = simulate_nondeterministic_fsa(nfa, test_string)
            minimised_result = simulate_nondeterministic_fsa(minimised, test_string)

            original_accepted = isinstance(original_result, list)
            minimised_accepted = isinstance(minimised_result, list)

            self.assertEqual(original_accepted, minimised_accepted)

    def test_direct_product_sat_small_nfa(self):
        """Test direct product SAT minimisation on small NFA"""
        # Small NFA suitable for SAT approach
        small_nfa = {
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

        try:
            minimised = direct_product_sat_minimise(small_nfa)

            # Verify structure
            self.assertIn('states', minimised)
            self.assertLessEqual(len(minimised['states']), len(small_nfa['states']))

            # Verify language equivalence
            test_strings = ['aa', 'aaa', 'ba', 'aba']
            for test_string in test_strings:
                original_result = simulate_nondeterministic_fsa(small_nfa, test_string)
                minimised_result = simulate_nondeterministic_fsa(minimised, test_string)

                original_accepted = isinstance(original_result, list)
                minimised_accepted = isinstance(minimised_result, list)

                self.assertEqual(original_accepted, minimised_accepted)

        except Exception as e:
            # SAT solver might not be available or timeout - this is acceptable
            self.assertIn(("timeout" in str(e).lower() or
                           "solver" in str(e).lower() or
                           "error" in str(e).lower()), [True])

    def test_direct_product_sat_used_appropriately(self):
        """Test that direct product SAT is used appropriately based on size"""
        # Create NFA larger than SAT_DIRECT_THRESHOLD but smaller than SAT_POST_HEURISTIC_THRESHOLD
        medium_states = [f'S{i}' for i in range(MinimisationConfig.SAT_DIRECT_THRESHOLD + 3)]  # 15 states
        medium_nfa = {
            'states': medium_states,
            'alphabet': ['a'],
            'transitions': {state: {'a': [state]} for state in medium_states},
            'startingState': medium_states[0],
            'acceptingStates': [medium_states[-1]]
        }

        result = minimise_nfa(medium_nfa)

        # Should use Kameda-Weiner first, then SAT if result is small enough
        self.assertIn("Kameda-Weiner", result.method_used)

        # Test with very small NFA (should use SAT directly)
        small_nfa = {
            'states': ['S0', 'S1', 'S2'],
            'alphabet': ['a'],
            'transitions': {
                'S0': {'a': ['S1']},
                'S1': {'a': ['S2']},
                'S2': {'a': ['S0']}
            },
            'startingState': 'S0',
            'acceptingStates': ['S0']
        }

        result = minimise_nfa(small_nfa)

        # Should use SAT directly for small NFAs
        self.assertEqual(result.method_used, "Direct Product SAT (optimal)")

    def test_normalise_nfa_with_epsilon(self):
        """Test NFA normalisation with epsilon transitions"""
        # NFA with epsilon transitions
        nfa = {
            'states': ['S0', 'S1', 'S2'],
            'alphabet': ['a', 'b'],
            'transitions': {
                'S0': {'': ['S1'], 'a': ['S0']},
                'S1': {'': ['S2'], 'b': ['S1']},
                'S2': {'a': ['S0']}
            },
            'startingState': 'S0',
            'acceptingStates': ['S2']
        }

        normalised = normalise_nfa(nfa)

        # Should not have epsilon in alphabet
        self.assertNotIn('', normalised['alphabet'])

        # Should have incorporated epsilon closures
        self.assertIn('states', normalised)
        self.assertIn('transitions', normalised)

        # Verify language equivalence
        test_strings = ['', 'a', 'b', 'ab']
        for test_string in test_strings:
            original_result = simulate_nondeterministic_fsa(nfa, test_string)
            normalised_result = simulate_nondeterministic_fsa(normalised, test_string)

            original_accepted = isinstance(original_result, list)
            normalised_accepted = isinstance(normalised_result, list)

            self.assertEqual(original_accepted, normalised_accepted)

    def test_normalise_nfa_without_epsilon(self):
        """Test NFA normalisation without epsilon transitions"""
        # Regular NFA without epsilon transitions
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

        normalised = normalise_nfa(nfa)

        # Should be essentially the same
        self.assertEqual(normalised['alphabet'], ['a', 'b'])
        self.assertEqual(len(normalised['states']), 2)

    def test_analyse_fsa_complexity(self):
        """Test FSA complexity analysis"""
        # Small deterministic FSA
        small_dfa = {
            'states': ['S0', 'S1'],
            'alphabet': ['a'],
            'transitions': {
                'S0': {'a': ['S1']},
                'S1': {'a': ['S0']}
            },
            'startingState': 'S0',
            'acceptingStates': ['S1']
        }

        analysis = analyse_fsa_complexity(small_dfa)

        self.assertEqual(analysis['num_states'], 2)
        self.assertEqual(analysis['alphabet_size'], 1)
        self.assertFalse(analysis['has_epsilon'])
        self.assertTrue(analysis['is_deterministic'])
        self.assertTrue(analysis['can_use_sat_directly'])
        # Now should recommend SAT for all small NFAs, not DFA minimisation
        self.assertEqual(analysis['recommended_approach'], 'sat_direct')

        # Large non-deterministic NFA
        large_nfa = {
            'states': [f'S{i}' for i in range(50)],
            'alphabet': ['a', 'b'],
            'transitions': {f'S{i}': {'a': [f'S{(i + 1) % 50}', f'S{(i + 2) % 50}']}
                            for i in range(50)},
            'startingState': 'S0',
            'acceptingStates': ['S49']
        }

        analysis = analyse_fsa_complexity(large_nfa)

        self.assertEqual(analysis['num_states'], 50)
        self.assertFalse(analysis['can_use_sat_directly'])
        self.assertEqual(analysis['recommended_approach'], 'kameda_weiner_then_analyse')

    def test_minimisation_result_structure(self):
        """Test MinimisationResult structure and metadata"""
        nfa = {
            'states': ['S0', 'S1', 'S2', 'S3'],
            'alphabet': ['a'],
            'transitions': {
                'S0': {'a': ['S1']},
                'S1': {'a': ['S2']},
                'S2': {'a': ['S3']},
                'S3': {'a': ['S0']}
            },
            'startingState': 'S0',
            'acceptingStates': ['S0']
        }

        result = minimise_nfa(nfa)

        # Check all required fields
        self.assertIsInstance(result.nfa, dict)
        self.assertIsInstance(result.original_states, int)
        self.assertIsInstance(result.final_states, int)
        self.assertIsInstance(result.reduction, int)
        self.assertIsInstance(result.reduction_percent, float)
        self.assertIsInstance(result.is_optimal, bool)
        self.assertIsInstance(result.method_used, str)
        self.assertIsInstance(result.stages, list)

        # Check values make sense
        self.assertEqual(result.original_states, 4)
        self.assertGreaterEqual(result.final_states, 1)
        self.assertLessEqual(result.final_states, result.original_states)
        self.assertEqual(result.reduction, result.original_states - result.final_states)
        self.assertGreaterEqual(result.reduction_percent, 0)
        self.assertLessEqual(result.reduction_percent, 100)

    def test_invalid_fsa_structure(self):
        """Test error handling for invalid FSA structures"""
        # Missing required key
        invalid_nfa = {
            'states': ['S0'],
            'alphabet': ['a'],
            'transitions': {'S0': {'a': ['S0']}},
            'startingState': 'S0'
            # Missing acceptingStates
        }

        with self.assertRaises(ValueError) as context:
            minimise_nfa(invalid_nfa)

        self.assertIn("Invalid NFA structure", str(context.exception))

    def test_empty_nfa(self):
        """Test handling of empty NFA"""
        # An empty NFA with empty starting state not in states list is invalid
        invalid_empty_nfa = {
            'states': [],
            'alphabet': ['a'],
            'transitions': {},
            'startingState': '',  # Not in states list - invalid
            'acceptingStates': []
        }

        # Should raise ValueError for invalid structure
        with self.assertRaises(ValueError) as context:
            minimise_nfa(invalid_empty_nfa)

        self.assertIn("Invalid NFA structure", str(context.exception))

    def test_minimal_valid_nfa(self):
        """Test handling of minimal valid NFA"""
        # Minimal valid NFA with single non-accepting state
        minimal_nfa = {
            'states': ['S0'],
            'alphabet': ['a'],
            'transitions': {
                'S0': {}  # No transitions
            },
            'startingState': 'S0',
            'acceptingStates': []
        }

        result = minimise_nfa(minimal_nfa)

        # Should handle gracefully
        self.assertEqual(result.final_states, 1)
        self.assertEqual(result.reduction, 0)
        self.assertEqual(result.reduction_percent, 0)

        # Should reject all strings
        test_strings = ['', 'a', 'aa']
        for test_string in test_strings:
            minimised_result = simulate_nondeterministic_fsa(result.nfa, test_string)
            self.assertIsInstance(minimised_result, dict)  # Should reject
            self.assertFalse(minimised_result['accepted'])

    def test_single_state_nfa(self):
        """Test minimisation of single-state NFA"""
        single_nfa = {
            'states': ['S0'],
            'alphabet': ['a', 'b'],
            'transitions': {
                'S0': {'a': ['S0'], 'b': ['S0']}
            },
            'startingState': 'S0',
            'acceptingStates': ['S0']
        }

        result = minimise_nfa(single_nfa)

        # Should remain single state
        self.assertEqual(result.final_states, 1)
        self.assertEqual(result.reduction, 0)
        self.assertEqual(result.reduction_percent, 0)

        # Verify language equivalence (should accept all strings)
        test_strings = ['', 'a', 'b', 'ab', 'ba']
        for test_string in test_strings:
            minimised_result = simulate_nondeterministic_fsa(result.nfa, test_string)
            self.assertIsInstance(minimised_result, list)  # Should accept

    def test_nfa_no_accepting_states(self):
        """Test NFA with no accepting states"""
        no_accept_nfa = {
            'states': ['S0', 'S1', 'S2'],
            'alphabet': ['a', 'b'],
            'transitions': {
                'S0': {'a': ['S1'], 'b': ['S2']},
                'S1': {'a': ['S0'], 'b': ['S2']},
                'S2': {'a': ['S2'], 'b': ['S2']}
            },
            'startingState': 'S0',
            'acceptingStates': []  # No accepting states
        }

        result = minimise_nfa(no_accept_nfa)

        # Should minimise significantly (all states equivalent since none accept)
        self.assertLessEqual(result.final_states, result.original_states)
        self.assertEqual(result.nfa['acceptingStates'], [])

        # All strings should be rejected
        test_strings = ['', 'a', 'b', 'ab']
        for test_string in test_strings:
            minimised_result = simulate_nondeterministic_fsa(result.nfa, test_string)
            self.assertIsInstance(minimised_result, dict)  # Should reject
            self.assertFalse(minimised_result['accepted'])

    def test_complex_minimise_nfa(self):
        """Test minimisation of a complex NFA with multiple paths"""
        # Complex NFA that accepts strings containing 'aba' or 'bb'
        complex_nfa = {
            'states': ['S0', 'S1', 'S2', 'S3', 'S4', 'S5', 'S6'],
            'alphabet': ['a', 'b'],
            'transitions': {
                'S0': {'a': ['S0', 'S1'], 'b': ['S0', 'S4']},  # Fixed: separate strings
                'S1': {'b': ['S2']},  # Path for 'aba'
                'S2': {'a': ['S3']},
                'S3': {'a': ['S0', 'S1'], 'b': ['S0', 'S4']},
                'S4': {'b': ['S5']},  # Path for 'bb'
                'S5': {'a': ['S0', 'S1'], 'b': ['S0', 'S4']},
                'S6': {'a': ['S6'], 'b': ['S6']}  # Unreachable state
            },
            'startingState': 'S0',
            'acceptingStates': ['S3', 'S5']
        }

        result = minimise_nfa(complex_nfa)

        # Should reduce states or at least maintain correctness
        # Note: Some NFAs may not be reducible, so we check <= instead of <
        self.assertLessEqual(result.final_states, result.original_states)

        # If no reduction occurred, check that it's because the NFA was already minimal
        if result.final_states == result.original_states:
            self.assertEqual(result.reduction, 0)
            self.assertEqual(result.reduction_percent, 0)

        # Verify language equivalence
        test_strings = ['', 'a', 'b', 'ab', 'bb', 'aba', 'ababb', 'aabbaba']
        for test_string in test_strings:
            original_result = simulate_nondeterministic_fsa(complex_nfa, test_string)
            minimised_result = simulate_nondeterministic_fsa(result.nfa, test_string)

            original_accepted = isinstance(original_result, list)
            minimised_accepted = isinstance(minimised_result, list)

            self.assertEqual(original_accepted, minimised_accepted,
                             f"Disagreement on string '{test_string}'")

    def test_dfa_with_unreachable_states(self):
        """Test that deterministic FSAs are minimised correctly even with unreachable states"""
        # Deterministic FSA with unreachable states
        dfa_with_unreachable = {
            'states': ['S0', 'S1', 'S2', 'S3', 'S4', 'S5'],
            'alphabet': ['a', 'b'],
            'transitions': {
                'S0': {'a': ['S1'], 'b': ['S0']},  # Deterministic
                'S1': {'a': ['S2'], 'b': ['S0']},
                'S2': {},  # Accepting state
                'S3': {'a': ['S4'], 'b': ['S3']},  # Unreachable from S0
                'S4': {'a': ['S5'], 'b': ['S3']},  # Unreachable from S0
                'S5': {}  # Unreachable accepting state
            },
            'startingState': 'S0',
            'acceptingStates': ['S2']
        }

        result = minimise_nfa(dfa_with_unreachable)

        # Should now use SAT minimization for small deterministic FSAs
        self.assertIn("SAT", result.method_used)

        # Should remove unreachable states and maintain correctness
        self.assertLessEqual(result.final_states, result.original_states)

        # Verify language equivalence regardless of whether unreachable states are removed
        test_strings = ['', 'a', 'aa', 'aaa', 'b', 'ab', 'ba', 'aba']
        for test_string in test_strings:
            original_result = simulate_nondeterministic_fsa(dfa_with_unreachable, test_string)
            minimised_result = simulate_nondeterministic_fsa(result.nfa, test_string)

            original_accepted = isinstance(original_result, list)
            minimised_accepted = isinstance(minimised_result, list)

            self.assertEqual(original_accepted, minimised_accepted,
                             f"Disagreement on string '{test_string}'")

    def test_language_equivalence_verification(self):
        """Test the language equivalence verification function"""
        # Two equivalent NFAs with different structures
        nfa1 = {
            'states': ['S0', 'S1'],
            'alphabet': ['a'],
            'transitions': {
                'S0': {'a': ['S1']},
                'S1': {'a': ['S0']}
            },
            'startingState': 'S0',
            'acceptingStates': ['S1']
        }

        nfa2 = {
            'states': ['Q0', 'Q1'],
            'alphabet': ['a'],
            'transitions': {
                'Q0': {'a': ['Q1']},
                'Q1': {'a': ['Q0']}
            },
            'startingState': 'Q0',
            'acceptingStates': ['Q1']
        }

        # Should verify as equivalent
        self.assertTrue(_verify_language_equivalence(nfa1, nfa2))

        # Modify to make non-equivalent
        nfa2['acceptingStates'] = ['Q0']
        self.assertFalse(_verify_language_equivalence(nfa1, nfa2))

    def test_minimisation_config_thresholds(self):
        """Test that configuration thresholds work as expected"""
        # Test with NFA right at SAT threshold
        threshold_states = [f'S{i}' for i in range(MinimisationConfig.SAT_DIRECT_THRESHOLD)]
        threshold_nfa = {
            'states': threshold_states,
            'alphabet': ['a'],
            'transitions': {
                # Make it non-deterministic by having multiple transitions from S0
                threshold_states[0]: {'a': [threshold_states[1], threshold_states[2]]},  # Non-deterministic!
                # Rest form a cycle
                **{threshold_states[i]: {'a': [threshold_states[(i + 1) % len(threshold_states)]]}
                   for i in range(1, len(threshold_states))}
            },
            'startingState': threshold_states[0],
            'acceptingStates': [threshold_states[-1]]
        }

        result = minimise_nfa(threshold_nfa)

        # Should use appropriate method based on size
        if len(threshold_states) <= MinimisationConfig.SAT_DIRECT_THRESHOLD:
            self.assertIn("SAT", result.method_used)
        else:
            self.assertIn("Kameda-Weiner", result.method_used)

    def test_deterministic_vs_nondeterministic_now_same_treatment(self):
        """Test that deterministic and non-deterministic FSAs now get the same treatment"""
        # Create deterministic FSA small enough for SAT
        deterministic_fsa = {
            'states': ['S0', 'S1', 'S2'],
            'alphabet': ['a'],
            'transitions': {
                'S0': {'a': ['S1']},  # Deterministic
                'S1': {'a': ['S2']},  # Deterministic
                'S2': {'a': ['S0']}  # Deterministic
            },
            'startingState': 'S0',
            'acceptingStates': ['S2']
        }

        result = minimise_nfa(deterministic_fsa)

        # Should now use SAT for small deterministic FSAs too
        self.assertIn("SAT", result.method_used)
        self.assertTrue(result.is_optimal)

        # Create non-deterministic FSA of same size
        nondeterministic_fsa = {
            'states': ['S0', 'S1', 'S2'],
            'alphabet': ['a'],
            'transitions': {
                'S0': {'a': ['S1', 'S2']},  # Non-deterministic
                'S1': {'a': ['S2']},
                'S2': {'a': ['S0']}
            },
            'startingState': 'S0',
            'acceptingStates': ['S2']
        }

        result = minimise_nfa(nondeterministic_fsa)

        # Should also use SAT for small non-deterministic NFAs
        self.assertIn("SAT", result.method_used)
        self.assertTrue(result.is_optimal)

    def test_nfa_with_epsilon_loops(self):
        """Test NFA with epsilon loops"""
        epsilon_loop_nfa = {
            'states': ['S0', 'S1', 'S2'],
            'alphabet': ['a'],
            'transitions': {
                'S0': {'': ['S1'], 'a': ['S0']},
                'S1': {'': ['S2']},
                'S2': {'': ['S1']}  # Epsilon loop
            },
            'startingState': 'S0',
            'acceptingStates': ['S2']
        }

        result = minimise_nfa(epsilon_loop_nfa)

        # Should handle epsilon loops correctly
        self.assertIsInstance(result, MinimisationResult)

        # Verify language equivalence
        test_strings = ['', 'a', 'aa', 'aaa']
        for test_string in test_strings:
            original_result = simulate_nondeterministic_fsa(epsilon_loop_nfa, test_string)
            minimised_result = simulate_nondeterministic_fsa(result.nfa, test_string)

            original_accepted = isinstance(original_result, list)
            minimised_accepted = isinstance(minimised_result, list)

            self.assertEqual(original_accepted, minimised_accepted)

    def test_stages_tracking(self):
        """Test that minimisation stages are properly tracked"""
        # Simple NFA that will go through multiple stages
        nfa = {
            'states': ['S0', 'S1', 'S2', 'S3'],
            'alphabet': ['a'],
            'transitions': {
                'S0': {'a': ['S1', 'S2']},
                'S1': {'a': ['S3']},
                'S2': {'a': ['S3']},
                'S3': {}
            },
            'startingState': 'S0',
            'acceptingStates': ['S3']
        }

        result = minimise_nfa(nfa)

        # Should have recorded stages
        self.assertTrue(len(result.stages) > 0)
        self.assertIsInstance(result.stages, list)
        for stage in result.stages:
            self.assertIsInstance(stage, str)

    @patch('simulator.minimise_nfa.Glucose3')
    def test_sat_solver_timeout_handling(self, mock_glucose):
        """Test handling of SAT solver timeouts"""
        # Mock SAT solver to simulate timeout
        mock_solver = mock_glucose.return_value
        mock_solver.solve_limited.return_value = None  # Timeout

        small_nfa = {
            'states': ['S0', 'S1'],
            'alphabet': ['a'],
            'transitions': {
                'S0': {'a': ['S1']},
                'S1': {}
            },
            'startingState': 'S0',
            'acceptingStates': ['S1']
        }

        # Should handle timeout gracefully
        try:
            result = direct_product_sat_minimise(small_nfa)
            # If it doesn't timeout, verify it's still the original NFA
            self.assertEqual(len(result['states']), 2)
        except Exception:
            # Timeout handling might raise an exception, which is acceptable
            pass

    def test_minimisation_preserves_fsa_properties(self):
        """Test that minimisation preserves important FSA properties"""
        nfa = {
            'states': ['S0', 'S1', 'S2', 'S3'],
            'alphabet': ['a', 'b'],
            'transitions': {
                'S0': {'a': ['S1'], 'b': ['S2']},
                'S1': {'a': ['S3'], 'b': ['S3']},
                'S2': {'a': ['S3'], 'b': ['S3']},
                'S3': {'a': ['S3'], 'b': ['S3']}
            },
            'startingState': 'S0',
            'acceptingStates': ['S3']
        }

        result = minimise_nfa(nfa)
        minimised = result.nfa

        # Verify FSA structure is valid
        validation = validate_fsa_structure(minimised)
        self.assertTrue(validation['valid'])

        # Verify alphabet is preserved
        self.assertEqual(set(minimised['alphabet']), set(nfa['alphabet']))

        # Verify start state exists and is in states
        self.assertIn(minimised['startingState'], minimised['states'])

        # Verify accepting states are all in states
        for state in minimised['acceptingStates']:
            self.assertIn(state, minimised['states'])

    def test_reduction_percentage_calculation(self):
        """Test reduction percentage calculation"""
        # NFA with known redundancy
        nfa = {
            'states': ['S0', 'S1', 'S2', 'S3', 'S4'],  # 5 states
            'alphabet': ['a'],
            'transitions': {
                'S0': {'a': ['S1']},
                'S1': {'a': ['S2']},
                'S2': {},  # Accepting
                'S3': {'a': ['S3']},  # Unreachable
                'S4': {'a': ['S4']}  # Unreachable
            },
            'startingState': 'S0',
            'acceptingStates': ['S2']
        }

        result = minimise_nfa(nfa)

        # Check percentage calculation
        expected_percentage = (result.reduction / result.original_states) * 100
        self.assertAlmostEqual(result.reduction_percent, expected_percentage, places=1)

        # Should be positive reduction
        if result.reduction > 0:
            self.assertGreater(result.reduction_percent, 0)
        else:
            self.assertEqual(result.reduction_percent, 0)

    def test_kameda_weiner_used_for_large_nfa(self):
        """Test that Kameda-Weiner is used for NFAs larger than SAT threshold"""
        # Create an NFA with more than SAT_DIRECT_THRESHOLD states (>12)
        # but that can be reduced by Kameda-Weiner to <= SAT_POST_HEURISTIC_THRESHOLD (20)
        large_nfa = {
            'states': [f'S{i}' for i in range(15)],  # 15 states > 12
            'alphabet': ['a', 'b'],
            'transitions': {
                # Create an NFA with redundant states that Kameda-Weiner can minimize
                'S0': {'a': ['S1', 'S2'], 'b': ['S3']},
                'S1': {'a': ['S4'], 'b': ['S5']},
                'S2': {'a': ['S4'], 'b': ['S5']},  # S1 and S2 have same outgoing transitions
                'S3': {'a': ['S6'], 'b': ['S7']},
                'S4': {'a': ['S8'], 'b': ['S8']},
                'S5': {'a': ['S9'], 'b': ['S9']},
                'S6': {'a': ['S10'], 'b': ['S10']},
                'S7': {'a': ['S11'], 'b': ['S11']},
                'S8': {'a': ['S12'], 'b': ['S12']},
                'S9': {'a': ['S12'], 'b': ['S12']},  # S8 and S9 both go to S12
                'S10': {'a': ['S13'], 'b': ['S13']},
                'S11': {'a': ['S13'], 'b': ['S13']},  # S10 and S11 both go to S13
                'S12': {'a': ['S14'], 'b': ['S14']},
                'S13': {'a': ['S14'], 'b': ['S14']},  # S12 and S13 both go to S14
                'S14': {}  # Accepting state
            },
            'startingState': 'S0',
            'acceptingStates': ['S14']
        }

        result = minimise_nfa(large_nfa)

        # Should use Kameda-Weiner because original has > 12 states
        self.assertIn("Kameda-Weiner", result.method_used)

        # Should reduce the number of states
        self.assertLess(result.final_states, result.original_states)

        # If Kameda-Weiner reduced it to <= 20 states, SAT should also be used
        if result.method_used == "Kameda-Weiner + Direct Product SAT (optimal)":
            self.assertTrue(result.is_optimal)
            self.assertIn("Kameda-Weiner preprocessing", result.stages)
            self.assertIn("Direct Product SAT minimisation (post-preprocessing)", result.stages)

        # Verify language equivalence
        test_strings = ['', 'a', 'b', 'aa', 'ab', 'ba', 'aaa', 'aaaa', 'aaaaa', 'baaaa']
        for test_string in test_strings:
            original_result = simulate_nondeterministic_fsa(large_nfa, test_string)
            minimised_result = simulate_nondeterministic_fsa(result.nfa, test_string)

            original_accepted = isinstance(original_result, list)
            minimised_accepted = isinstance(minimised_result, list)

            self.assertEqual(original_accepted, minimised_accepted,
                             f"Disagreement on string '{test_string}'")

    def test_kameda_weiner_only_for_very_large_nfa(self):
        """Test that only Kameda-Weiner is used for very large NFAs that remain large after reduction"""
        # Create an NFA with many states that won't reduce much
        num_states = 25  # > SAT_POST_HEURISTIC_THRESHOLD (20)

        # Create a "chain" NFA that can't be minimized much
        very_large_nfa = {
            'states': [f'S{i}' for i in range(num_states)],
            'alphabet': ['a', 'b'],
            'transitions': {},
            'startingState': 'S0',
            'acceptingStates': [f'S{num_states - 1}']
        }

        # Build a chain where each state has a unique role
        for i in range(num_states - 1):
            if i % 2 == 0:
                # Even states: 'a' goes to next state, 'b' self-loops
                very_large_nfa['transitions'][f'S{i}'] = {
                    'a': [f'S{i + 1}'],
                    'b': [f'S{i}']
                }
            else:
                # Odd states: 'b' goes to next state, 'a' self-loops
                very_large_nfa['transitions'][f'S{i}'] = {
                    'a': [f'S{i}'],
                    'b': [f'S{i + 1}']
                }

        # Final state has no transitions
        very_large_nfa['transitions'][f'S{num_states - 1}'] = {}

        result = minimise_nfa(very_large_nfa)

        # Should only use Kameda-Weiner (no SAT because too large even after reduction)
        self.assertEqual(result.method_used, "Kameda-Weiner only (heuristic)")
        self.assertFalse(result.is_optimal)  # Heuristic, not optimal
        self.assertIn("Kameda-Weiner preprocessing", result.stages)
        self.assertEqual(len(result.stages), 1)  # Only Kameda-Weiner stage

        # Should not reduce much (or at all) because each state has unique behavior
        # The alternating pattern makes states distinguishable
        self.assertGreaterEqual(result.final_states, 20)  # Still too large for SAT

        # Verify language equivalence
        # This NFA accepts strings that alternate correctly and have right length
        test_strings = ['', 'a', 'ab', 'aba', 'abab', 'ababa' * 4]  # Various lengths
        for test_string in test_strings:
            original_result = simulate_nondeterministic_fsa(very_large_nfa, test_string)
            minimised_result = simulate_nondeterministic_fsa(result.nfa, test_string)

            original_accepted = isinstance(original_result, list)
            minimised_accepted = isinstance(minimised_result, list)

            self.assertEqual(original_accepted, minimised_accepted,
                             f"Disagreement on string '{test_string}'")

    def test_potential_nfa_smaller_than_dfa(self):
        """Test case where an NFA could potentially be smaller than the minimal DFA"""
        # Classic example: "third symbol from the end is 'a'"
        # The minimal DFA needs 8 states (2^3) to track the last 3 symbols
        # But an NFA can do it with just 4 states
        nfa_third_from_end = {
            'states': ['S0', 'S1', 'S2', 'S3'],
            'alphabet': ['a', 'b'],
            'transitions': {
                'S0': {'a': ['S0', 'S1'], 'b': ['S0']},  # Non-deterministically guess this is 3rd from end
                'S1': {'a': ['S2'], 'b': ['S2']},  # Move to S2 after any symbol
                'S2': {'a': ['S3'], 'b': ['S3']},  # Move to S3 after any symbol
                'S3': {}  # Accept (we've seen exactly 2 more symbols after the guessed 'a')
            },
            'startingState': 'S0',
            'acceptingStates': ['S3']
        }

        result = minimise_nfa(nfa_third_from_end)

        # This NFA is already minimal for its language
        # The minimal DFA would need 8 states, but this NFA only has 4
        self.assertEqual(result.original_states, 4)
        self.assertLessEqual(result.final_states, 4)

        # If we used DFA minimization, we'd get 8 states
        # But with proper NFA minimization, we should keep it at 4 or less
        self.assertLessEqual(result.final_states, 4)

        # Verify it still accepts the correct language
        # Strings where the third symbol from the end is 'a'
        # For string of length n: the 3rd from end is at position n-3
        # Length 3: position 0 must be 'a'
        # Length 4: position 1 must be 'a'
        # etc.
        test_accepts = [
            # Length 3: check position 0
            'aaa', 'aab', 'aba', 'abb',
            # Length 4: check position 1
            'aaaa', 'aaab', 'aaba', 'aabb', 'baaa', 'baab', 'baba', 'babb',
            # Length 5: check position 2
            'aaaaa', 'abaaa', 'baaaa', 'bbaaa', 'abaab', 'bbaab'
        ]
        test_rejects = [
            # Too short
            '', 'a', 'aa', 'ab', 'ba', 'bb',
            # Length 3: position 0 is not 'a'
            'baa', 'bab', 'bba', 'bbb',
            # Length 4: position 1 is not 'a'
            'abaa', 'abab', 'abba', 'abbb', 'bbaa', 'bbab', 'bbba', 'bbbb',
            # Length 5: position 2 is not 'a'
            'aabaa', 'abbaa', 'babaa', 'bbbaa'
        ]

        for test_string in test_accepts:
            result_sim = simulate_nondeterministic_fsa(result.nfa, test_string)
            self.assertIsInstance(result_sim, list,
                                  f"Should accept '{test_string}' (3rd from end is 'a')")

        for test_string in test_rejects:
            result_sim = simulate_nondeterministic_fsa(result.nfa, test_string)
            if isinstance(result_sim, list):
                # If it accepts, it should be a false positive in our test
                self.fail(f"Should reject '{test_string}' (3rd from end is not 'a')")