from django.test import TestCase
from simulator.fsa_properties import (
    is_deterministic,
    is_complete,
    is_connected,
    check_all_properties,
    validate_fsa_structure
)

class TestFsaProperties(TestCase):
    """Test cases for FSA property checking functions"""

    def test_deterministic_property(self):
        """Test is_deterministic function"""
        # Deterministic FSA
        deterministic_fsa = {
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
        self.assertTrue(is_deterministic(deterministic_fsa))

        # Non-deterministic FSA (multiple transitions)
        nondeterministic_fsa = {
            'states': ['S0', 'S1', 'S2'],
            'alphabet': ['a', 'b'],
            'transitions': {
                'S0': {'a': ['S1', 'S2'], 'b': ['S0']},  # Multiple transitions on 'a'
                'S1': {'a': ['S2'], 'b': ['S0']},
                'S2': {'a': ['S2'], 'b': ['S2']}
            },
            'startingState': 'S0',
            'acceptingStates': ['S2']
        }
        self.assertFalse(is_deterministic(nondeterministic_fsa))

        # FSA with epsilon transitions
        epsilon_fsa = {
            'states': ['S0', 'S1'],
            'alphabet': ['a'],
            'transitions': {
                'S0': {'': ['S1'], 'a': ['S0']},  # Epsilon transition
                'S1': {'a': ['S1']}
            },
            'startingState': 'S0',
            'acceptingStates': ['S1']
        }
        self.assertFalse(is_deterministic(epsilon_fsa))

        # FSA with empty epsilon transitions (should be deterministic)
        empty_epsilon_fsa = {
            'states': ['S0', 'S1'],
            'alphabet': ['a'],
            'transitions': {
                'S0': {'': [], 'a': ['S1']},  # Empty epsilon transitions
                'S1': {'a': ['S0']}
            },
            'startingState': 'S0',
            'acceptingStates': ['S1']
        }
        self.assertTrue(is_deterministic(empty_epsilon_fsa))

    def test_deterministic_property_edge_cases(self):
        """Test edge cases for is_deterministic"""
        # Empty alphabet
        empty_alphabet_fsa = {
            'states': ['S0'],
            'alphabet': [],
            'transitions': {'S0': {}},
            'startingState': 'S0',
            'acceptingStates': ['S0']
        }
        self.assertTrue(is_deterministic(empty_alphabet_fsa))

        # Missing transitions for some states
        incomplete_fsa = {
            'states': ['S0', 'S1'],
            'alphabet': ['a', 'b'],
            'transitions': {
                'S0': {'a': ['S1']},  # Missing 'b' transition
                'S1': {'a': ['S0'], 'b': ['S1']}
            },
            'startingState': 'S0',
            'acceptingStates': ['S1']
        }
        self.assertTrue(is_deterministic(incomplete_fsa))  # Still deterministic

    def test_complete_property(self):
        """Test is_complete function"""
        # Complete FSA
        complete_fsa = {
            'states': ['S0', 'S1'],
            'alphabet': ['a', 'b'],
            'transitions': {
                'S0': {'a': ['S1'], 'b': ['S0']},
                'S1': {'a': ['S0'], 'b': ['S1']}
            },
            'startingState': 'S0',
            'acceptingStates': ['S1']
        }
        self.assertTrue(is_complete(complete_fsa))

        # Incomplete FSA (missing transition)
        incomplete_fsa = {
            'states': ['S0', 'S1'],
            'alphabet': ['a', 'b'],
            'transitions': {
                'S0': {'a': ['S1']},  # Missing 'b' transition
                'S1': {'a': ['S0'], 'b': ['S1']}
            },
            'startingState': 'S0',
            'acceptingStates': ['S1']
        }
        self.assertFalse(is_complete(incomplete_fsa))

        # FSA with empty transitions
        empty_transitions_fsa = {
            'states': ['S0', 'S1'],
            'alphabet': ['a', 'b'],
            'transitions': {
                'S0': {'a': [], 'b': ['S0']},  # Empty transition list
                'S1': {'a': ['S0'], 'b': ['S1']}
            },
            'startingState': 'S0',
            'acceptingStates': ['S1']
        }
        self.assertFalse(is_complete(empty_transitions_fsa))

        # FSA with multiple transitions (non-deterministic but complete)
        nondeterministic_complete_fsa = {
            'states': ['S0', 'S1'],
            'alphabet': ['a', 'b'],
            'transitions': {
                'S0': {'a': ['S0', 'S1'], 'b': ['S0']},  # Multiple transitions
                'S1': {'a': ['S0'], 'b': ['S1']}
            },
            'startingState': 'S0',
            'acceptingStates': ['S1']
        }
        self.assertTrue(is_complete(nondeterministic_complete_fsa))

    def test_complete_property_edge_cases(self):
        """Test edge cases for is_complete"""
        # Empty states
        empty_states_fsa = {
            'states': [],
            'alphabet': ['a'],
            'transitions': {},
            'startingState': '',
            'acceptingStates': []
        }
        self.assertTrue(is_complete(empty_states_fsa))  # Trivially complete

        # Empty alphabet
        empty_alphabet_fsa = {
            'states': ['S0'],
            'alphabet': [],
            'transitions': {'S0': {}},
            'startingState': 'S0',
            'acceptingStates': ['S0']
        }
        self.assertTrue(is_complete(empty_alphabet_fsa))  # Trivially complete

        # State not in transitions
        missing_state_transitions = {
            'states': ['S0', 'S1'],
            'alphabet': ['a'],
            'transitions': {
                'S0': {'a': ['S1']}
                # S1 missing from transitions
            },
            'startingState': 'S0',
            'acceptingStates': ['S1']
        }
        self.assertFalse(is_complete(missing_state_transitions))

    def test_connected_property(self):
        """Test is_connected function"""
        # Connected FSA
        connected_fsa = {
            'states': ['S0', 'S1', 'S2'],
            'alphabet': ['a', 'b'],
            'transitions': {
                'S0': {'a': ['S1'], 'b': ['S0']},
                'S1': {'a': ['S2'], 'b': ['S0']},
                'S2': {'a': ['S2'], 'b': ['S1']}
            },
            'startingState': 'S0',
            'acceptingStates': ['S2']
        }
        self.assertTrue(is_connected(connected_fsa))

        # Disconnected FSA (unreachable state)
        disconnected_fsa = {
            'states': ['S0', 'S1', 'S2'],
            'alphabet': ['a', 'b'],
            'transitions': {
                'S0': {'a': ['S1'], 'b': ['S0']},
                'S1': {'a': ['S1'], 'b': ['S0']},
                'S2': {'a': ['S2'], 'b': ['S2']}  # S2 is unreachable
            },
            'startingState': 'S0',
            'acceptingStates': ['S1']
        }
        self.assertFalse(is_connected(disconnected_fsa))

        # FSA with epsilon transitions making states reachable
        epsilon_connected_fsa = {
            'states': ['S0', 'S1', 'S2'],
            'alphabet': ['a'],
            'transitions': {
                'S0': {'': ['S1'], 'a': ['S0']},  # Epsilon transition to S1
                'S1': {'': ['S2']},  # Epsilon transition to S2
                'S2': {'a': ['S0']}
            },
            'startingState': 'S0',
            'acceptingStates': ['S2']
        }
        self.assertTrue(is_connected(epsilon_connected_fsa))

    def test_connected_property_edge_cases(self):
        """Test edge cases for is_connected"""
        # Empty states
        empty_states_fsa = {
            'states': [],
            'alphabet': ['a'],
            'transitions': {},
            'startingState': '',
            'acceptingStates': []
        }
        self.assertTrue(is_connected(empty_states_fsa))  # Trivially connected

        # Single state
        single_state_fsa = {
            'states': ['S0'],
            'alphabet': ['a'],
            'transitions': {'S0': {'a': ['S0']}},
            'startingState': 'S0',
            'acceptingStates': ['S0']
        }
        self.assertTrue(is_connected(single_state_fsa))

        # No starting state
        no_start_fsa = {
            'states': ['S0', 'S1'],
            'alphabet': ['a'],
            'transitions': {
                'S0': {'a': ['S1']},
                'S1': {'a': ['S0']}
            },
            'startingState': '',
            'acceptingStates': ['S1']
        }
        self.assertFalse(is_connected(no_start_fsa))

        # Starting state not in states list
        invalid_start_fsa = {
            'states': ['S0', 'S1'],
            'alphabet': ['a'],
            'transitions': {
                'S0': {'a': ['S1']},
                'S1': {'a': ['S0']}
            },
            'startingState': 'S2',  # S2 not in states
            'acceptingStates': ['S1']
        }
        self.assertFalse(is_connected(invalid_start_fsa))

        # No transitions
        no_transitions_fsa = {
            'states': ['S0', 'S1'],
            'alphabet': ['a'],
            'transitions': {},
            'startingState': 'S0',
            'acceptingStates': ['S1']
        }
        self.assertFalse(is_connected(no_transitions_fsa))

    def test_check_all_properties(self):
        """Test check_all_properties function"""
        # Complete, deterministic, connected FSA
        perfect_fsa = {
            'states': ['S0', 'S1'],
            'alphabet': ['a', 'b'],
            'transitions': {
                'S0': {'a': ['S1'], 'b': ['S0']},
                'S1': {'a': ['S0'], 'b': ['S1']}
            },
            'startingState': 'S0',
            'acceptingStates': ['S1']
        }

        result = check_all_properties(perfect_fsa)
        self.assertTrue(result['deterministic'])
        self.assertTrue(result['complete'])
        self.assertTrue(result['connected'])

        # Incomplete, non-deterministic, disconnected FSA
        problematic_fsa = {
            'states': ['S0', 'S1', 'S2'],
            'alphabet': ['a', 'b'],
            'transitions': {
                'S0': {'a': ['S0', 'S1']},  # Non-deterministic, missing 'b'
                'S1': {'a': ['S1'], 'b': ['S1']},
                'S2': {'a': ['S2'], 'b': ['S2']}  # Unreachable
            },
            'startingState': 'S0',
            'acceptingStates': ['S1']
        }

        result = check_all_properties(problematic_fsa)
        self.assertFalse(result['deterministic'])  # Multiple transitions on 'a'
        self.assertFalse(result['complete'])  # Missing 'b' transition from S0
        self.assertFalse(result['connected'])  # S2 is unreachable

    def test_validate_fsa_structure(self):
        """Test validate_fsa_structure function"""
        # Valid FSA structure
        valid_fsa = {
            'states': ['S0', 'S1'],
            'alphabet': ['a', 'b'],
            'transitions': {
                'S0': {'a': ['S1'], 'b': ['S0']},
                'S1': {'a': ['S0'], 'b': ['S1']}
            },
            'startingState': 'S0',
            'acceptingStates': ['S1']
        }

        result = validate_fsa_structure(valid_fsa)
        self.assertTrue(result['valid'])
        self.assertNotIn('error', result)

        # Missing required key
        missing_key_fsa = {
            'states': ['S0', 'S1'],
            'alphabet': ['a', 'b'],
            'transitions': {
                'S0': {'a': ['S1'], 'b': ['S0']},
                'S1': {'a': ['S0'], 'b': ['S1']}
            },
            'startingState': 'S0'
            # Missing acceptingStates
        }

        result = validate_fsa_structure(missing_key_fsa)
        self.assertFalse(result['valid'])
        self.assertIn('error', result)
        self.assertIn('acceptingStates', result['error'])

        # Wrong type for states
        wrong_type_fsa = {
            'states': 'S0',  # Should be list
            'alphabet': ['a', 'b'],
            'transitions': {},
            'startingState': 'S0',
            'acceptingStates': []
        }

        result = validate_fsa_structure(wrong_type_fsa)
        self.assertFalse(result['valid'])
        self.assertIn('error', result)
        self.assertIn('states must be a list', result['error'])

        # Starting state not in states list
        invalid_start_fsa = {
            'states': ['S0', 'S1'],
            'alphabet': ['a'],
            'transitions': {},
            'startingState': 'S2',  # Not in states
            'acceptingStates': []
        }

        result = validate_fsa_structure(invalid_start_fsa)
        self.assertFalse(result['valid'])
        self.assertIn('error', result)
        self.assertIn('Starting state not in states list', result['error'])

        # Accepting state not in states list
        invalid_accepting_fsa = {
            'states': ['S0', 'S1'],
            'alphabet': ['a'],
            'transitions': {},
            'startingState': 'S0',
            'acceptingStates': ['S2']  # S2 not in states
        }

        result = validate_fsa_structure(invalid_accepting_fsa)
        self.assertFalse(result['valid'])
        self.assertIn('error', result)
        self.assertIn('Accepting state S2 not in states list', result['error'])

        # Not a dictionary
        not_dict = "not a dictionary"

        result = validate_fsa_structure(not_dict)
        self.assertFalse(result['valid'])
        self.assertIn('error', result)
        self.assertIn('FSA must be a dictionary', result['error'])

    def test_validate_fsa_structure_lenient(self):
        """Test that validate_fsa_structure is lenient with empty values"""
        # Empty states (should be valid)
        empty_states_fsa = {
            'states': [],
            'alphabet': ['a'],
            'transitions': {},
            'startingState': '',
            'acceptingStates': []
        }

        result = validate_fsa_structure(empty_states_fsa)
        self.assertTrue(result['valid'])

        # Empty alphabet (should be valid)
        empty_alphabet_fsa = {
            'states': ['S0'],
            'alphabet': [],
            'transitions': {},
            'startingState': 'S0',
            'acceptingStates': []
        }

        result = validate_fsa_structure(empty_alphabet_fsa)
        self.assertTrue(result['valid'])

        # Empty transitions (should be valid)
        empty_transitions_fsa = {
            'states': ['S0'],
            'alphabet': ['a'],
            'transitions': {},
            'startingState': 'S0',
            'acceptingStates': ['S0']
        }

        result = validate_fsa_structure(empty_transitions_fsa)
        self.assertTrue(result['valid'])

    def test_properties_with_epsilon_transitions(self):
        """Test property functions with epsilon transitions"""
        epsilon_fsa = {
            'states': ['S0', 'S1', 'S2'],
            'alphabet': ['a', 'b'],
            'transitions': {
                'S0': {'': ['S1'], 'a': ['S0']},  # Epsilon transition
                'S1': {'b': ['S2']},
                'S2': {'': ['S0']}  # Epsilon back to start
            },
            'startingState': 'S0',
            'acceptingStates': ['S2']
        }

        # Should be non-deterministic due to epsilon transitions
        self.assertFalse(is_deterministic(epsilon_fsa))

        # Should be incomplete (missing some regular transitions)
        self.assertFalse(is_complete(epsilon_fsa))

        # Should be connected via epsilon transitions
        self.assertTrue(is_connected(epsilon_fsa))

    def test_properties_with_complex_fsa(self):
        """Test properties with a more complex FSA"""
        complex_fsa = {
            'states': ['S0', 'S1', 'S2', 'S3', 'S4'],
            'alphabet': ['a', 'b', 'c'],
            'transitions': {
                'S0': {'a': ['S1'], 'b': ['S2'], 'c': ['S0']},
                'S1': {'a': ['S3'], 'b': ['S1'], 'c': ['S4']},
                'S2': {'a': ['S2'], 'b': ['S3'], 'c': ['S1']},
                'S3': {'a': ['S4'], 'b': ['S3'], 'c': ['S2']},
                'S4': {'a': ['S0'], 'b': ['S4'], 'c': ['S3']}
            },
            'startingState': 'S0',
            'acceptingStates': ['S3', 'S4']
        }

        result = check_all_properties(complex_fsa)

        # Should be deterministic (exactly one transition per state-symbol pair)
        self.assertTrue(result['deterministic'])

        # Should be complete (all states have transitions for all symbols)
        self.assertTrue(result['complete'])

        # Should be connected (all states reachable from S0)
        self.assertTrue(result['connected'])

    def test_properties_consistency(self):
        """Test that property functions are consistent with each other"""
        test_fsas = [
            # Simple deterministic complete connected FSA
            {
                'states': ['S0', 'S1'],
                'alphabet': ['a'],
                'transitions': {
                    'S0': {'a': ['S1']},
                    'S1': {'a': ['S0']}
                },
                'startingState': 'S0',
                'acceptingStates': ['S1']
            },
            # Non-deterministic FSA
            {
                'states': ['S0', 'S1'],
                'alphabet': ['a'],
                'transitions': {
                    'S0': {'a': ['S0', 'S1']},  # Multiple transitions
                    'S1': {'a': ['S1']}
                },
                'startingState': 'S0',
                'acceptingStates': ['S1']
            },
            # Incomplete FSA
            {
                'states': ['S0', 'S1'],
                'alphabet': ['a', 'b'],
                'transitions': {
                    'S0': {'a': ['S1']},  # Missing 'b' transition
                    'S1': {'a': ['S0'], 'b': ['S1']}
                },
                'startingState': 'S0',
                'acceptingStates': ['S1']
            }
        ]

        for fsa in test_fsas:
            # Individual property checks
            det = is_deterministic(fsa)
            comp = is_complete(fsa)
            conn = is_connected(fsa)

            # All properties check
            all_props = check_all_properties(fsa)

            # Should be consistent
            self.assertEqual(det, all_props['deterministic'])
            self.assertEqual(comp, all_props['complete'])
            self.assertEqual(conn, all_props['connected'])