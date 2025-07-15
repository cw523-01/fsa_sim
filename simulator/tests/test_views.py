import json
from django.test import TestCase, Client
from django.urls import reverse
from unittest.mock import patch, MagicMock
from django.http import StreamingHttpResponse


class FSAViewTestCase(TestCase):
    """Base test case with common FSA definitions and utilities"""

    def setUp(self):
        self.client = Client()

        # Sample deterministic FSA
        self.sample_dfa = {
            'states': ['S0', 'S1'],
            'alphabet': ['a', 'b'],
            'transitions': {
                'S0': {'a': ['S1'], 'b': ['S0']},
                'S1': {'a': ['S0'], 'b': ['S1']}
            },
            'startingState': 'S0',
            'acceptingStates': ['S1']
        }

        # Sample non-deterministic FSA
        self.sample_nfa = {
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

        # Invalid FSA (missing required keys)
        self.invalid_fsa = {
            'states': ['S0'],
            'alphabet': ['a']
            # Missing transitions, startingState, acceptingStates
        }

    def post_json(self, url, data):
        """Helper method to send JSON POST requests"""
        return self.client.post(
            url,
            data=json.dumps(data),
            content_type='application/json'
        )


class SimulateFSAViewTests(FSAViewTestCase):
    """Tests for the general FSA simulation endpoint"""

    def test_simulate_dfa_accepted(self):
        """Test DFA simulation with accepted input"""
        response = self.post_json('/api/simulate-fsa/', {
            'fsa': self.sample_dfa,
            'input': 'ab'
        })

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['accepted'])
        self.assertEqual(data['type'], 'dfa')
        self.assertIn('path', data)
        self.assertEqual(len(data['path']), 2)  # Two transitions

    def test_simulate_dfa_rejected(self):
        """Test DFA simulation with rejected input"""
        response = self.post_json('/api/simulate-fsa/', {
            'fsa': self.sample_dfa,
            'input': 'b'
        })

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertFalse(data['accepted'])
        self.assertEqual(data['type'], 'dfa')
        self.assertIn('rejection_reason', data)
        self.assertIn('rejection_position', data)

    def test_simulate_nfa_accepted(self):
        """Test NFA simulation with accepted input"""
        response = self.post_json('/api/simulate-fsa/', {
            'fsa': self.sample_nfa,
            'input': 'ab'
        })

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['accepted'])
        self.assertEqual(data['type'], 'nfa')
        self.assertIn('accepting_paths', data)
        self.assertIn('num_paths', data)
        self.assertGreater(data['num_paths'], 0)

    def test_simulate_nfa_rejected(self):
        """Test NFA simulation with rejected input"""
        response = self.post_json('/api/simulate-fsa/', {
            'fsa': self.sample_nfa,
            'input': 'a'
        })

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertFalse(data['accepted'])
        self.assertEqual(data['type'], 'nfa')
        self.assertIn('paths_explored', data)
        self.assertIn('rejection_reason', data)

    def test_missing_fsa(self):
        """Test request without FSA definition"""
        response = self.post_json('/api/simulate-fsa/', {
            'input': 'ab'
        })

        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertIn('error', data)
        self.assertIn('Missing FSA definition', data['error'])

    def test_invalid_fsa_structure(self):
        """Test request with invalid FSA structure"""
        response = self.post_json('/api/simulate-fsa/', {
            'fsa': self.invalid_fsa,
            'input': 'a'
        })

        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertIn('error', data)

    def test_empty_input_string(self):
        """Test simulation with empty input string"""
        # Modify DFA to accept empty string
        accepting_start_dfa = {
            'states': ['S0'],
            'alphabet': ['a'],
            'transitions': {'S0': {'a': ['S0']}},
            'startingState': 'S0',
            'acceptingStates': ['S0']
        }

        response = self.post_json('/api/simulate-fsa/', {
            'fsa': accepting_start_dfa,
            'input': ''
        })

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['accepted'])

    def test_get_request_not_allowed(self):
        """Test that GET requests are not allowed"""
        response = self.client.get('/api/simulate-fsa/')
        self.assertEqual(response.status_code, 405)  # Method Not Allowed

    def test_invalid_json(self):
        """Test request with invalid JSON"""
        response = self.client.post(
            '/api/simulate-fsa/',
            data='invalid json',
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 400)


class SimulateDFAViewTests(FSAViewTestCase):
    """Tests for the specific DFA simulation endpoint"""

    def test_simulate_dfa_specific_endpoint(self):
        """Test the specific DFA endpoint"""
        response = self.post_json('/api/simulate-dfa/', {
            'fsa': self.sample_dfa,
            'input': 'ab'
        })

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['accepted'])
        self.assertIn('path', data)

    def test_simulate_dfa_with_nfa(self):
        """Test DFA endpoint with non-deterministic FSA"""
        response = self.post_json('/api/simulate-dfa/', {
            'fsa': self.sample_nfa,  # This is an NFA
            'input': 'ab'
        })

        # Should still work but will reject due to non-determinism
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertFalse(data['accepted'])
        self.assertIn('rejection_reason', data)


class SimulateNFAViewTests(FSAViewTestCase):
    """Tests for the specific NFA simulation endpoint"""

    def test_simulate_nfa_specific_endpoint(self):
        """Test the specific NFA endpoint"""
        response = self.post_json('/api/simulate-nfa/', {
            'fsa': self.sample_nfa,
            'input': 'ab'
        })

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['accepted'])
        self.assertIn('accepting_paths', data)
        self.assertIn('num_paths', data)

    def test_simulate_nfa_with_dfa(self):
        """Test NFA endpoint with deterministic FSA"""
        response = self.post_json('/api/simulate-nfa/', {
            'fsa': self.sample_dfa,  # This is a DFA
            'input': 'ab'
        })

        # Should work fine - DFAs are valid NFAs
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['accepted'])


class StreamingNFAViewTests(FSAViewTestCase):
    """Tests for the streaming NFA simulation endpoint"""

    def test_streaming_nfa_response_format(self):
        """Test that streaming endpoint returns proper Server-Sent Events format"""
        response = self.client.post(
            '/api/simulate-nfa-stream/',
            data=json.dumps({
                'fsa': self.sample_nfa,
                'input': 'ab'
            }),
            content_type='application/json'
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'text/event-stream')
        self.assertEqual(response['Cache-Control'], 'no-cache')

    def test_streaming_nfa_content(self):
        """Test streaming NFA content"""
        response = self.client.post(
            '/api/simulate-nfa-stream/',
            data=json.dumps({
                'fsa': self.sample_nfa,
                'input': 'ab'
            }),
            content_type='application/json'
        )

        # Collect all streaming content
        content = b''.join(response.streaming_content).decode('utf-8')

        # Should contain data events
        self.assertIn('data:', content)
        # Should end with end marker
        self.assertIn('"type": "end"', content)

    def test_streaming_nfa_error_handling(self):
        """Test streaming endpoint error handling"""
        response = self.client.post(
            '/api/simulate-nfa-stream/',
            data=json.dumps({
                'fsa': self.invalid_fsa,
                'input': 'a'
            }),
            content_type='application/json'
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response['Content-Type'], 'text/event-stream')


class CheckFSATypeViewTests(FSAViewTestCase):
    """Tests for the FSA type checking endpoint"""

    def test_check_dfa_type(self):
        """Test type checking for DFA"""
        response = self.post_json('/api/check-fsa-type/', {
            'fsa': self.sample_dfa
        })

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertFalse(data['is_nondeterministic'])
        self.assertEqual(data['type'], 'DFA')
        self.assertIn('description', data)

    def test_check_nfa_type(self):
        """Test type checking for NFA"""
        response = self.post_json('/api/check-fsa-type/', {
            'fsa': self.sample_nfa
        })

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['is_nondeterministic'])
        self.assertEqual(data['type'], 'NFA')
        self.assertIn('description', data)


class CheckEpsilonLoopsViewTests(FSAViewTestCase):
    """Tests for the epsilon loop detection endpoint"""

    def setUp(self):
        super().setUp()
        # FSA with epsilon loop
        self.epsilon_loop_fsa = {
            'states': ['S0', 'S1'],
            'alphabet': ['a'],
            'transitions': {
                'S0': {'': ['S1'], 'a': ['S0']},
                'S1': {'': ['S0']}
            },
            'startingState': 'S0',
            'acceptingStates': ['S1']
        }

    def test_detect_epsilon_loops(self):
        """Test epsilon loop detection"""
        response = self.post_json('/api/check-epsilon-loops/', {
            'fsa': self.epsilon_loop_fsa
        })

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['has_epsilon_loops'])
        self.assertGreater(data['total_loops_found'], 0)
        self.assertIn('loops', data)
        self.assertIn('summary', data)

    def test_no_epsilon_loops(self):
        """Test FSA without epsilon loops"""
        response = self.post_json('/api/check-epsilon-loops/', {
            'fsa': self.sample_dfa
        })

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertFalse(data['has_epsilon_loops'])
        self.assertEqual(data['total_loops_found'], 0)


class DepthLimitedNFAViewTests(FSAViewTestCase):
    """Tests for the depth-limited NFA simulation endpoints"""

    def test_depth_limited_nfa_valid(self):
        """Test depth-limited NFA with valid parameters"""
        response = self.post_json('/api/simulate-nfa-depth-limit/', {
            'fsa': self.sample_nfa,
            'input': 'ab',
            'max_depth': 10
        })

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['accepted'])
        self.assertIn('max_depth_used', data)
        self.assertEqual(data['max_depth_used'], 10)

    def test_depth_limited_missing_max_depth(self):
        """Test depth-limited NFA without max_depth parameter"""
        response = self.post_json('/api/simulate-nfa-depth-limit/', {
            'fsa': self.sample_nfa,
            'input': 'ab'
        })

        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertIn('error', data)
        self.assertIn('max_depth', data['error'])

    def test_depth_limited_invalid_max_depth(self):
        """Test depth-limited NFA with invalid max_depth"""
        # Test negative max_depth
        response = self.post_json('/api/simulate-nfa-depth-limit/', {
            'fsa': self.sample_nfa,
            'input': 'ab',
            'max_depth': -1
        })

        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertIn('error', data)
        self.assertIn('positive integer', data['error'])

        # Test non-integer max_depth
        response = self.post_json('/api/simulate-nfa-depth-limit/', {
            'fsa': self.sample_nfa,
            'input': 'ab',
            'max_depth': 'invalid'
        })

        self.assertEqual(response.status_code, 400)

    def test_streaming_depth_limited_nfa(self):
        """Test streaming depth-limited NFA endpoint"""
        response = self.client.post(
            '/api/simulate-nfa-stream-depth-limit/',
            data=json.dumps({
                'fsa': self.sample_nfa,
                'input': 'ab',
                'max_depth': 10
            }),
            content_type='application/json'
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'text/event-stream')


class PropertyCheckingViewTests(FSAViewTestCase):
    """Tests for FSA property checking endpoints"""

    def test_check_all_properties(self):
        """Test checking all FSA properties"""
        response = self.post_json('/api/check-fsa-properties/', {
            'fsa': self.sample_dfa
        })

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('properties', data)
        self.assertIn('summary', data)

        properties = data['properties']
        self.assertIn('deterministic', properties)
        self.assertIn('complete', properties)
        self.assertIn('connected', properties)

    def test_check_deterministic_only(self):
        """Test checking deterministic property only"""
        response = self.post_json('/api/check-deterministic/', {
            'fsa': self.sample_dfa
        })

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('deterministic', data)
        self.assertIn('type', data)
        self.assertTrue(data['deterministic'])
        self.assertEqual(data['type'], 'DFA')

    def test_check_complete_only(self):
        """Test checking complete property only"""
        response = self.post_json('/api/check-complete/', {
            'fsa': self.sample_dfa
        })

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('complete', data)

    def test_check_connected_only(self):
        """Test checking connected property only"""
        response = self.post_json('/api/check-connected/', {
            'fsa': self.sample_dfa
        })

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('connected', data)


class JSONParsingErrorTests(FSAViewTestCase):
    """Tests for JSON parsing error scenarios that trigger ValueError exceptions"""

    def test_malformed_json_simulate_fsa(self):
        """Test malformed JSON in simulate_fsa endpoint"""
        response = self.client.post(
            '/api/simulate-fsa/',
            data='{"invalid": json malformed}',
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertIn('error', data)

    def test_malformed_json_simulate_dfa(self):
        """Test malformed JSON in simulate_dfa endpoint"""
        response = self.client.post(
            '/api/simulate-dfa/',
            data='{"invalid": json}',
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 400)

    def test_malformed_json_simulate_nfa(self):
        """Test malformed JSON in simulate_nfa endpoint"""
        response = self.client.post(
            '/api/simulate-nfa/',
            data='{"invalid": json}',
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 400)

    def test_malformed_json_check_fsa_type(self):
        """Test malformed JSON in check_fsa_type endpoint"""
        response = self.client.post(
            '/api/check-fsa-type/',
            data='{"invalid": json}',
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 400)

    def test_malformed_json_check_epsilon_loops(self):
        """Test malformed JSON in check_epsilon_loops endpoint"""
        response = self.client.post(
            '/api/check-epsilon-loops/',
            data='{"invalid": json}',
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 400)

    def test_malformed_json_depth_limit(self):
        """Test malformed JSON in depth limited endpoints"""
        response = self.client.post(
            '/api/simulate-nfa-depth-limit/',
            data='{"invalid": json}',
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 400)

    def test_malformed_json_property_checks(self):
        """Test malformed JSON in property checking endpoints"""
        endpoints = [
            '/api/check-fsa-properties/',
            '/api/check-deterministic/',
            '/api/check-complete/',
            '/api/check-connected/'
        ]

        for endpoint in endpoints:
            response = self.client.post(
                endpoint,
                data='{"invalid": json}',
                content_type='application/json'
            )
            self.assertEqual(response.status_code, 400)


class FunctionExceptionTests(FSAViewTestCase):
    """Tests for triggering exceptions in imported simulation functions"""

    @patch('simulator.views.simulate_deterministic_fsa')
    def test_simulate_fsa_dfa_function_exception(self, mock_simulate):
        """Test exception in simulate_deterministic_fsa within simulate_fsa"""
        mock_simulate.side_effect = Exception("Simulation error")

        response = self.post_json('/api/simulate-fsa/', {
            'fsa': self.sample_dfa,
            'input': 'ab'
        })

        self.assertEqual(response.status_code, 500)
        data = response.json()
        self.assertIn('error', data)
        self.assertIn('Server error', data['error'])

    @patch('simulator.views.simulate_nondeterministic_fsa')
    def test_simulate_fsa_nfa_function_exception(self, mock_simulate):
        """Test exception in simulate_nondeterministic_fsa within simulate_fsa"""
        mock_simulate.side_effect = Exception("NFA simulation error")

        response = self.post_json('/api/simulate-fsa/', {
            'fsa': self.sample_nfa,
            'input': 'ab'
        })

        self.assertEqual(response.status_code, 500)
        data = response.json()
        self.assertIn('error', data)
        self.assertIn('Server error', data['error'])

    @patch('simulator.views.simulate_deterministic_fsa')
    def test_simulate_dfa_function_exception(self, mock_simulate):
        """Test exception in simulate_dfa endpoint"""
        mock_simulate.side_effect = Exception("DFA simulation error")

        response = self.post_json('/api/simulate-dfa/', {
            'fsa': self.sample_dfa,
            'input': 'ab'
        })

        self.assertEqual(response.status_code, 500)
        data = response.json()
        self.assertIn('error', data)
        self.assertIn('Server error', data['error'])

    @patch('simulator.views.simulate_nondeterministic_fsa')
    def test_simulate_nfa_function_exception(self, mock_simulate):
        """Test exception in simulate_nfa endpoint"""
        mock_simulate.side_effect = Exception("NFA simulation error")

        response = self.post_json('/api/simulate-nfa/', {
            'fsa': self.sample_nfa,
            'input': 'ab'
        })

        self.assertEqual(response.status_code, 500)
        data = response.json()
        self.assertIn('error', data)
        self.assertIn('Server error', data['error'])

    @patch('simulator.views.is_nondeterministic')
    def test_check_fsa_type_function_exception(self, mock_check):
        """Test exception in check_fsa_type endpoint"""
        mock_check.side_effect = Exception("Type check error")

        response = self.post_json('/api/check-fsa-type/', {
            'fsa': self.sample_dfa
        })

        self.assertEqual(response.status_code, 500)
        data = response.json()
        self.assertIn('error', data)
        self.assertIn('Server error', data['error'])

    @patch('simulator.views.detect_epsilon_loops')
    def test_check_epsilon_loops_function_exception(self, mock_detect):
        """Test exception in check_epsilon_loops endpoint"""
        mock_detect.side_effect = Exception("Epsilon loop detection error")

        response = self.post_json('/api/check-epsilon-loops/', {
            'fsa': self.sample_dfa
        })

        self.assertEqual(response.status_code, 500)
        data = response.json()
        self.assertIn('error', data)
        self.assertIn('Server error', data['error'])

    @patch('simulator.views.simulate_nondeterministic_fsa_with_depth_limit')
    def test_depth_limit_function_exception(self, mock_simulate):
        """Test exception in simulate_nfa_with_depth_limit endpoint"""
        mock_simulate.side_effect = Exception("Depth limit simulation error")

        response = self.post_json('/api/simulate-nfa-depth-limit/', {
            'fsa': self.sample_nfa,
            'input': 'ab',
            'max_depth': 10
        })

        self.assertEqual(response.status_code, 500)
        data = response.json()
        self.assertIn('error', data)
        self.assertIn('Server error', data['error'])

    @patch('simulator.views.check_all_properties')
    def test_check_all_properties_function_exception(self, mock_check):
        """Test exception in check_fsa_properties endpoint"""
        mock_check.side_effect = Exception("Property check error")

        response = self.post_json('/api/check-fsa-properties/', {
            'fsa': self.sample_dfa
        })

        self.assertEqual(response.status_code, 500)
        data = response.json()
        self.assertIn('error', data)
        self.assertIn('Server error', data['error'])

    @patch('simulator.views.is_deterministic')
    def test_check_deterministic_function_exception(self, mock_check):
        """Test exception in check_deterministic endpoint"""
        mock_check.side_effect = Exception("Deterministic check error")

        response = self.post_json('/api/check-deterministic/', {
            'fsa': self.sample_dfa
        })

        self.assertEqual(response.status_code, 500)
        data = response.json()
        self.assertIn('error', data)
        self.assertIn('Server error', data['error'])

    @patch('simulator.views.is_complete')
    def test_check_complete_function_exception(self, mock_check):
        """Test exception in check_complete endpoint"""
        mock_check.side_effect = Exception("Complete check error")

        response = self.post_json('/api/check-complete/', {
            'fsa': self.sample_dfa
        })

        self.assertEqual(response.status_code, 500)
        data = response.json()
        self.assertIn('error', data)
        self.assertIn('Server error', data['error'])

    @patch('simulator.views.is_connected')
    def test_check_connected_function_exception(self, mock_check):
        """Test exception in check_connected endpoint"""
        mock_check.side_effect = Exception("Connected check error")

        response = self.post_json('/api/check-connected/', {
            'fsa': self.sample_dfa
        })

        self.assertEqual(response.status_code, 500)
        data = response.json()
        self.assertIn('error', data)
        self.assertIn('Server error', data['error'])

    @patch('simulator.views.complete_dfa')
    def test_complete_dfa_function_exception(self, mock_complete):
        """Test exception in complete_dfa endpoint"""
        mock_complete.side_effect = Exception("Complete DFA error")

        response = self.post_json('/api/complete-dfa/', {
            'fsa': self.sample_dfa
        })

        self.assertEqual(response.status_code, 500)
        data = response.json()
        self.assertIn('error', data)
        self.assertIn('Server error', data['error'])

    @patch('simulator.views.complement_dfa')
    def test_complement_dfa_function_exception(self, mock_complement):
        """Test exception in complement_dfa endpoint"""
        mock_complement.side_effect = Exception("Complement DFA error")

        response = self.post_json('/api/complement-dfa/', {
            'fsa': self.sample_dfa
        })

        self.assertEqual(response.status_code, 500)
        data = response.json()
        self.assertIn('error', data)
        self.assertIn('Server error', data['error'])


class StreamingErrorHandlingTests(FSAViewTestCase):
    """Tests for error handling in streaming endpoints"""

    def test_streaming_nfa_missing_fsa_error(self):
        """Test streaming NFA with missing FSA"""
        response = self.client.post(
            '/api/simulate-nfa-stream/',
            data=json.dumps({'input': 'ab'}),
            content_type='application/json'
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response['Content-Type'], 'text/event-stream')

        # Read the streaming content
        content = b''.join(response.streaming_content).decode('utf-8')
        self.assertIn('Missing FSA definition', content)

    def test_streaming_nfa_invalid_fsa_error(self):
        """Test streaming NFA with invalid FSA structure"""
        response = self.client.post(
            '/api/simulate-nfa-stream/',
            data=json.dumps({
                'fsa': self.invalid_fsa,
                'input': 'ab'
            }),
            content_type='application/json'
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response['Content-Type'], 'text/event-stream')

    def test_streaming_nfa_malformed_json_error(self):
        """Test streaming NFA with malformed JSON"""
        response = self.client.post(
            '/api/simulate-nfa-stream/',
            data='{"invalid": json}',
            content_type='application/json'
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response['Content-Type'], 'text/event-stream')

    @patch('simulator.views.simulate_nondeterministic_fsa_generator')
    def test_streaming_nfa_generator_exception(self, mock_generator):
        """Test streaming NFA when generator raises exception"""
        mock_generator.side_effect = Exception("Generator error")

        response = self.client.post(
            '/api/simulate-nfa-stream/',
            data=json.dumps({
                'fsa': self.sample_nfa,
                'input': 'ab'
            }),
            content_type='application/json'
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'text/event-stream')

        # Check that error is reported in streaming content
        content = b''.join(response.streaming_content).decode('utf-8')
        self.assertIn('"type": "error"', content)
        self.assertIn('Generator error', content)

    def test_streaming_depth_limit_missing_fsa_error(self):
        """Test streaming depth-limited NFA with missing FSA"""
        response = self.client.post(
            '/api/simulate-nfa-stream-depth-limit/',
            data=json.dumps({'input': 'ab', 'max_depth': 10}),
            content_type='application/json'
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response['Content-Type'], 'text/event-stream')

    def test_streaming_depth_limit_missing_max_depth_error(self):
        """Test streaming depth-limited NFA with missing max_depth"""
        response = self.client.post(
            '/api/simulate-nfa-stream-depth-limit/',
            data=json.dumps({
                'fsa': self.sample_nfa,
                'input': 'ab'
            }),
            content_type='application/json'
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response['Content-Type'], 'text/event-stream')

    def test_streaming_depth_limit_invalid_max_depth_error(self):
        """Test streaming depth-limited NFA with invalid max_depth"""
        response = self.client.post(
            '/api/simulate-nfa-stream-depth-limit/',
            data=json.dumps({
                'fsa': self.sample_nfa,
                'input': 'ab',
                'max_depth': -1
            }),
            content_type='application/json'
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response['Content-Type'], 'text/event-stream')

    def test_streaming_depth_limit_invalid_max_depth_type_error(self):
        """Test streaming depth-limited NFA with invalid max_depth type"""
        response = self.client.post(
            '/api/simulate-nfa-stream-depth-limit/',
            data=json.dumps({
                'fsa': self.sample_nfa,
                'input': 'ab',
                'max_depth': 'invalid'
            }),
            content_type='application/json'
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response['Content-Type'], 'text/event-stream')

    def test_streaming_depth_limit_invalid_fsa_error(self):
        """Test streaming depth-limited NFA with invalid FSA"""
        response = self.client.post(
            '/api/simulate-nfa-stream-depth-limit/',
            data=json.dumps({
                'fsa': self.invalid_fsa,
                'input': 'ab',
                'max_depth': 10
            }),
            content_type='application/json'
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response['Content-Type'], 'text/event-stream')

    def test_streaming_depth_limit_malformed_json_error(self):
        """Test streaming depth-limited NFA with malformed JSON"""
        response = self.client.post(
            '/api/simulate-nfa-stream-depth-limit/',
            data='{"invalid": json}',
            content_type='application/json'
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response['Content-Type'], 'text/event-stream')

    @patch('json.loads')
    def test_streaming_nfa_json_loads_exception(self, mock_json_loads):
        """Test streaming NFA when json.loads raises exception"""
        mock_json_loads.side_effect = Exception("JSON parsing error")

        response = self.client.post(
            '/api/simulate-nfa-stream/',
            data=json.dumps({
                'fsa': self.sample_nfa,
                'input': 'ab'
            }),
            content_type='application/json'
        )

        self.assertEqual(response.status_code, 500)
        self.assertEqual(response['Content-Type'], 'text/event-stream')

    @patch('json.loads')
    def test_streaming_depth_limit_json_loads_exception(self, mock_json_loads):
        """Test streaming depth-limited NFA when json.loads raises exception"""
        mock_json_loads.side_effect = Exception("JSON parsing error")

        response = self.client.post(
            '/api/simulate-nfa-stream-depth-limit/',
            data=json.dumps({
                'fsa': self.sample_nfa,
                'input': 'ab',
                'max_depth': 10
            }),
            content_type='application/json'
        )

        self.assertEqual(response.status_code, 500)
        self.assertEqual(response['Content-Type'], 'text/event-stream')

    @patch('simulator.views.simulate_nondeterministic_fsa_generator_with_depth_limit')
    def test_streaming_depth_limit_generator_exception(self, mock_generator):
        """Test streaming depth-limited NFA when generator raises exception"""
        mock_generator.side_effect = Exception("Generator error")

        response = self.client.post(
            '/api/simulate-nfa-stream-depth-limit/',
            data=json.dumps({
                'fsa': self.sample_nfa,
                'input': 'ab',
                'max_depth': 10
            }),
            content_type='application/json'
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'text/event-stream')

        # Check that error is reported in streaming content
        content = b''.join(response.streaming_content).decode('utf-8')
        self.assertIn('"type": "error"', content)
        self.assertIn('Generator error', content)


class EdgeCaseValidationTests(FSAViewTestCase):
    """Tests for edge cases in validation and data handling"""

    def test_simulate_fsa_nfa_fallback_result_format(self):
        """Test simulate_fsa with NFA that returns unexpected result format"""
        with patch('simulator.views.simulate_nondeterministic_fsa') as mock_simulate:
            # Return a dict that looks like rejection but doesn't have expected keys
            mock_simulate.return_value = {'unexpected': 'format'}

            response = self.post_json('/api/simulate-fsa/', {
                'fsa': self.sample_nfa,
                'input': 'ab'
            })

            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertFalse(data['accepted'])

    def test_simulate_nfa_with_rejection_dict_missing_keys(self):
        """Test simulate_nfa with rejection dict missing expected keys"""
        with patch('simulator.views.simulate_nondeterministic_fsa') as mock_simulate:
            # Return a dict without expected keys
            mock_simulate.return_value = {'accepted': False}

            response = self.post_json('/api/simulate-nfa/', {
                'fsa': self.sample_nfa,
                'input': 'ab'
            })

            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertFalse(data['accepted'])
            # Should have default values for missing keys
            self.assertEqual(data.get('paths_explored', 0), 0)
            self.assertEqual(data.get('rejection_reason', 'Unknown rejection reason'), 'Unknown rejection reason')

    def test_simulate_dfa_with_rejection_dict_missing_keys(self):
        """Test simulate_dfa with rejection dict missing expected keys"""
        with patch('simulator.views.simulate_deterministic_fsa') as mock_simulate:
            # Return a dict with accepted=False but missing other keys
            mock_simulate.return_value = {'accepted': False}

            response = self.post_json('/api/simulate-dfa/', {
                'fsa': self.sample_dfa,
                'input': 'ab'
            })

            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertFalse(data['accepted'])
            # Should have default values for missing keys
            self.assertEqual(data.get('path', []), [])
            self.assertEqual(data.get('rejection_reason', 'Unknown rejection reason'), 'Unknown rejection reason')
            self.assertEqual(data.get('rejection_position', 0), 0)

    def test_depth_limit_with_rejection_dict_missing_keys(self):
        """Test depth-limited NFA with rejection dict missing expected keys"""
        with patch('simulator.views.simulate_nondeterministic_fsa_with_depth_limit') as mock_simulate:
            # Return a dict without expected keys
            mock_simulate.return_value = {'accepted': False}

            response = self.post_json('/api/simulate-nfa-depth-limit/', {
                'fsa': self.sample_nfa,
                'input': 'ab',
                'max_depth': 10
            })

            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertFalse(data['accepted'])
            # Should have default values for missing keys
            self.assertEqual(data.get('paths_explored', 0), 0)
            self.assertEqual(data.get('rejection_reason', 'Unknown rejection reason'), 'Unknown rejection reason')
            self.assertEqual(data.get('partial_paths', []), [])
            self.assertEqual(data.get('depth_limit_reached', False), False)


class RemainingCoverageTests(FSAViewTestCase):
    """Tests for remaining uncovered edge cases"""

    def test_index_view(self):
        """Test the index view that renders the main page"""
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)

    def test_epsilon_loops_response_with_missing_loop_details(self):
        """Test epsilon loops response formatting edge cases"""
        with patch('simulator.views.detect_epsilon_loops') as mock_detect:
            # Return result with minimal loop details
            mock_detect.return_value = {
                'has_epsilon_loops': True,
                'loop_details': [{
                    'cycle': ['S0'],
                    'transitions': [],
                    'reachable_from_start': True
                }]
            }

            response = self.post_json('/api/check-epsilon-loops/', {
                'fsa': self.sample_dfa
            })

            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertTrue(data['has_epsilon_loops'])
            self.assertEqual(len(data['loops']), 1)

    def test_check_all_properties_response_formatting(self):
        """Test check_all_properties response includes summary with calculated fields"""
        # Use an FSA with known characteristics
        test_fsa = {
            'states': ['S0', 'S1'],
            'alphabet': ['a', 'b'],
            'transitions': {
                'S0': {'': ['S1'], 'a': ['S0']},  # Has epsilon transitions
                'S1': {'b': ['S1']}
            },
            'startingState': 'S0',
            'acceptingStates': ['S1']
        }

        response = self.post_json('/api/check-fsa-properties/', {
            'fsa': test_fsa
        })

        self.assertEqual(response.status_code, 200)
        data = response.json()

        # Check that summary includes calculated fields
        summary = data['summary']
        self.assertEqual(summary['total_states'], 2)
        self.assertEqual(summary['alphabet_size'], 2)
        self.assertEqual(summary['starting_state'], 'S0')
        self.assertEqual(summary['accepting_states_count'], 1)
        self.assertTrue(summary['has_epsilon_transitions'])

    def test_fsa_properties_summary_without_epsilon_transitions(self):
        """Test FSA properties summary for FSA without epsilon transitions"""
        response = self.post_json('/api/check-fsa-properties/', {
            'fsa': self.sample_dfa  # No epsilon transitions
        })

        self.assertEqual(response.status_code, 200)
        data = response.json()
        summary = data['summary']
        self.assertFalse(summary['has_epsilon_transitions'])

    def test_simulate_fsa_edge_case_result_handling(self):
        """Test simulate_fsa with edge case result handling"""
        # Test with an FSA that might have unusual simulation results
        edge_case_fsa = {
            'states': ['S0'],
            'alphabet': ['a'],
            'transitions': {'S0': {'a': ['S0']}},
            'startingState': 'S0',
            'acceptingStates': []  # No accepting states
        }

        response = self.post_json('/api/simulate-fsa/', {
            'fsa': edge_case_fsa,
            'input': 'a'
        })

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertFalse(data['accepted'])


class StreamingExceptionHandlerTests(FSAViewTestCase):
    """Tests for the outer exception handlers in streaming views"""

    @patch('simulator.views.validate_fsa_structure')
    def test_streaming_nfa_validation_exception(self, mock_validate):
        """Test streaming NFA when validation raises non-ValueError exception"""
        mock_validate.side_effect = RuntimeError("Validation runtime error")

        response = self.client.post(
            '/api/simulate-nfa-stream/',
            data=json.dumps({
                'fsa': self.sample_nfa,
                'input': 'ab'
            }),
            content_type='application/json'
        )

        self.assertEqual(response.status_code, 500)
        self.assertEqual(response['Content-Type'], 'text/event-stream')

    @patch('simulator.views.validate_fsa_structure')
    def test_streaming_depth_limit_validation_exception(self, mock_validate):
        """Test streaming depth-limited NFA when validation raises non-ValueError exception"""
        mock_validate.side_effect = RuntimeError("Validation runtime error")

        response = self.client.post(
            '/api/simulate-nfa-stream-depth-limit/',
            data=json.dumps({
                'fsa': self.sample_nfa,
                'input': 'ab',
                'max_depth': 10
            }),
            content_type='application/json'
        )

        self.assertEqual(response.status_code, 500)
        self.assertEqual(response['Content-Type'], 'text/event-stream')


class ValidationErrorScenarioTests(FSAViewTestCase):
    """Tests for specific validation error scenarios"""

    def test_depth_limit_zero_value(self):
        """Test depth limit endpoint with zero max_depth"""
        response = self.post_json('/api/simulate-nfa-depth-limit/', {
            'fsa': self.sample_nfa,
            'input': 'ab',
            'max_depth': 0
        })

        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertIn('positive integer', data['error'])

    def test_depth_limit_float_value(self):
        """Test depth limit endpoint with float max_depth"""
        response = self.post_json('/api/simulate-nfa-depth-limit/', {
            'fsa': self.sample_nfa,
            'input': 'ab',
            'max_depth': 5.5
        })

        self.assertEqual(response.status_code, 200)  # Should convert to int
        data = response.json()
        self.assertEqual(data['max_depth_used'], 5)

    def test_depth_limit_none_value(self):
        """Test depth limit endpoint with None max_depth"""
        response = self.post_json('/api/simulate-nfa-depth-limit/', {
            'fsa': self.sample_nfa,
            'input': 'ab',
            'max_depth': None
        })

        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertIn('max_depth', data['error'])


class ResponseFormatTests(FSAViewTestCase):
    """Tests for ensuring proper response formats in edge cases"""

    def test_simulate_dfa_unexpected_result_format(self):
        """Test DFA simulation with unexpected result format from function"""
        # Create a mock that returns an unexpected format
        with patch('simulator.views.simulate_deterministic_fsa') as mock_simulate:
            mock_simulate.return_value = "unexpected string result"

            response = self.post_json('/api/simulate-dfa/', {
                'fsa': self.sample_dfa,
                'input': 'ab'
            })

            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertFalse(data['accepted'])
            self.assertEqual(data['rejection_reason'], 'Unexpected result format')

    def test_dfa_result_missing_accepted_field(self):
        """Test DFA simulation with dict result missing 'accepted' field"""
        with patch('simulator.views.simulate_deterministic_fsa') as mock_simulate:
            mock_simulate.return_value = {'path': [], 'other_field': 'value'}

            response = self.post_json('/api/simulate-dfa/', {
                'fsa': self.sample_dfa,
                'input': 'ab'
            })

            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertFalse(data['accepted'])
            self.assertEqual(data['rejection_reason'], 'Unexpected result format')


class DepthLimitTypeErrorTests(FSAViewTestCase):
    """Tests for depth limit type conversion errors"""

    def test_depth_limit_type_error_regular_endpoint(self):
        """Test TypeError when converting max_depth in regular endpoint"""

        # Create a mock object that can't be converted to int
        class UnconvertibleType:
            def __int__(self):
                raise TypeError("Cannot convert to int")

        response = self.client.post(
            '/api/simulate-nfa-depth-limit/',
            data=json.dumps({
                'fsa': self.sample_nfa,
                'input': 'ab',
                'max_depth': {'unconvertible': 'object'}
            }),
            content_type='application/json'
        )

        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertIn('positive integer', data['error'])

    def test_depth_limit_type_error_streaming_endpoint(self):
        """Test TypeError when converting max_depth in streaming endpoint"""
        response = self.client.post(
            '/api/simulate-nfa-stream-depth-limit/',
            data=json.dumps({
                'fsa': self.sample_nfa,
                'input': 'ab',
                'max_depth': {'unconvertible': 'object'}
            }),
            content_type='application/json'
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response['Content-Type'], 'text/event-stream')


class ErrorHandlingTests(FSAViewTestCase):
    """Tests for error handling across all endpoints"""

    @patch('simulator.views.simulate_deterministic_fsa')
    def test_simulation_function_exception(self, mock_simulate):
        """Test handling of exceptions from simulation functions"""
        mock_simulate.side_effect = Exception("Simulation error")

        response = self.post_json('/api/simulate-dfa/', {
            'fsa': self.sample_dfa,
            'input': 'ab'
        })

        self.assertEqual(response.status_code, 500)
        data = response.json()
        self.assertIn('error', data)
        self.assertIn('Server error', data['error'])

    def test_malformed_json(self):
        """Test handling of malformed JSON in requests"""
        response = self.client.post(
            '/api/simulate-fsa/',
            data='{"invalid": json}',
            content_type='application/json'
        )

        self.assertEqual(response.status_code, 400)

    def test_missing_content_type(self):
        """Test handling of requests without proper content type"""
        # When no content_type is specified, Django expects form data (dict)
        # but our views expect JSON, so this should fail gracefully
        response = self.client.post(
            '/api/simulate-fsa/',
            data={'fsa': 'not_json', 'input': 'ab'}
            # No content_type specified - defaults to form encoding
        )

        # Should return 400 because our views expect JSON
        self.assertEqual(response.status_code, 400)


class URLRoutingTests(TestCase):
    """Tests for URL routing"""

    def test_all_urls_resolve(self):
        """Test that all defined URLs resolve correctly"""
        urls_to_test = [
            '/api/simulate-fsa/',
            '/api/simulate-dfa/',
            '/api/simulate-nfa/',
            '/api/simulate-nfa-stream/',
            '/api/check-fsa-type/',
            '/api/check-epsilon-loops/',
            '/api/simulate-nfa-depth-limit/',
            '/api/simulate-nfa-stream-depth-limit/',
            '/api/check-fsa-properties/',
            '/api/check-deterministic/',
            '/api/check-complete/',
            '/api/check-connected/',
            '/api/complete-dfa/',
            '/api/complement-dfa/',

        ]

        for url in urls_to_test:
            response = self.client.post(url)
            # Should not get 404 (URL not found)
            self.assertNotEqual(response.status_code, 404, f"URL {url} returned 404")


class IntegrationTests(FSAViewTestCase):
    """Integration tests that test the full request-response cycle"""

    def test_complete_dfa_simulation_workflow(self):
        """Test complete workflow for DFA simulation"""
        # 1. Check FSA type
        type_response = self.post_json('/api/check-fsa-type/', {
            'fsa': self.sample_dfa
        })
        self.assertEqual(type_response.status_code, 200)
        self.assertEqual(type_response.json()['type'], 'DFA')

        # 2. Check properties
        props_response = self.post_json('/api/check-fsa-properties/', {
            'fsa': self.sample_dfa
        })
        self.assertEqual(props_response.status_code, 200)

        # 3. Simulate
        sim_response = self.post_json('/api/simulate-fsa/', {
            'fsa': self.sample_dfa,
            'input': 'ab'
        })
        self.assertEqual(sim_response.status_code, 200)
        self.assertTrue(sim_response.json()['accepted'])

    def test_complete_nfa_simulation_workflow(self):
        """Test complete workflow for NFA simulation"""
        # 1. Check for epsilon loops
        loop_response = self.post_json('/api/check-epsilon-loops/', {
            'fsa': self.sample_nfa
        })
        self.assertEqual(loop_response.status_code, 200)

        # 2. Simulate with depth limit if loops exist
        if loop_response.json()['has_epsilon_loops']:
            sim_response = self.post_json('/api/simulate-nfa-depth-limit/', {
                'fsa': self.sample_nfa,
                'input': 'ab',
                'max_depth': 10
            })
        else:
            sim_response = self.post_json('/api/simulate-nfa/', {
                'fsa': self.sample_nfa,
                'input': 'ab'
            })

        self.assertEqual(sim_response.status_code, 200)


class PerformanceTests(FSAViewTestCase):
    """Basic performance and load tests"""

    def test_large_input_string(self):
        """Test simulation with large input string"""
        large_input = 'a' * 1000 + 'b'

        response = self.post_json('/api/simulate-dfa/', {
            'fsa': self.sample_dfa,
            'input': large_input
        })

        self.assertEqual(response.status_code, 200)
        # Should complete in reasonable time

    def test_complex_fsa_structure(self):
        """Test with complex FSA structure"""
        # Create FSA with many states
        complex_fsa = {
            'states': [f'S{i}' for i in range(50)],
            'alphabet': ['a', 'b'],
            'transitions': {
                f'S{i}': {
                    'a': [f'S{(i + 1) % 50}'],
                    'b': [f'S{(i + 2) % 50}']
                } for i in range(50)
            },
            'startingState': 'S0',
            'acceptingStates': ['S49']
        }

        response = self.post_json('/api/simulate-dfa/', {
            'fsa': complex_fsa,
            'input': 'a' * 49
        })

        self.assertEqual(response.status_code, 200)


class MinimizeDFAViewTests(FSAViewTestCase):
    """Tests for the DFA minimization endpoint"""

    def test_minimize_dfa_successful(self):
        """Test successful DFA minimization"""
        # Create a DFA that can be minimized
        redundant_dfa = {
            'states': ['S0', 'S1', 'S2', 'S3'],
            'alphabet': ['a', 'b'],
            'transitions': {
                'S0': {'a': ['S1'], 'b': ['S2']},
                'S1': {'a': ['S1'], 'b': ['S3']},
                'S2': {'a': ['S1'], 'b': ['S2']},
                'S3': {'a': ['S1'], 'b': ['S3']}
            },
            'startingState': 'S0',
            'acceptingStates': ['S1', 'S3']  # S1 and S3 might be equivalent
        }

        response = self.post_json('/api/minimise-dfa/', {
            'fsa': redundant_dfa
        })

        self.assertEqual(response.status_code, 200)
        data = response.json()

        self.assertTrue(data['success'])
        self.assertIn('minimised_fsa', data)
        self.assertIn('statistics', data)

    def test_minimize_non_deterministic_fsa(self):
        """Test minimization fails for non-deterministic FSA"""
        response = self.post_json('/api/minimise-dfa/', {
            'fsa': self.sample_nfa
        })

        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertIn('error', data)
        self.assertIn('deterministic FSA', data['error'])

    def test_minimize_dfa_missing_fsa(self):
        """Test minimization without FSA definition"""
        response = self.post_json('/api/minimise-dfa/', {})

        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertIn('error', data)
        self.assertIn('Missing FSA definition', data['error'])


class CombinedTransformationTests(FSAViewTestCase):
    """Tests for combining multiple transformations"""

    def test_nfa_to_dfa_then_minimize(self):
        """Test converting NFA to DFA then minimizing the result"""
        # 1. Convert NFA to DFA
        convert_response = self.post_json('/api/nfa-to-dfa/', {
            'fsa': self.sample_nfa
        })
        self.assertEqual(convert_response.status_code, 200)
        converted_dfa = convert_response.json()['converted_dfa']

        # 2. Minimize the resulting DFA
        minimize_response = self.post_json('/api/minimise-dfa/', {
            'fsa': converted_dfa
        })
        self.assertEqual(minimize_response.status_code, 200)
        self.assertTrue(minimize_response.json()['success'])

    def test_conversion_preserves_language(self):
        """Test that NFA to DFA conversion preserves the language"""
        # Convert NFA to DFA
        convert_response = self.post_json('/api/nfa-to-dfa/', {
            'fsa': self.sample_nfa
        })
        self.assertEqual(convert_response.status_code, 200)
        converted_dfa = convert_response.json()['converted_dfa']

        # Test that both accept/reject the same strings
        test_strings = ['', 'a', 'b', 'ab', 'aab', 'abb', 'ba', 'bb']

        for test_string in test_strings:
            # Test original NFA
            nfa_response = self.post_json('/api/simulate-nfa/', {
                'fsa': self.sample_nfa,
                'input': test_string
            })

            # Test converted DFA
            dfa_response = self.post_json('/api/simulate-dfa/', {
                'fsa': converted_dfa,
                'input': test_string
            })

            self.assertEqual(nfa_response.status_code, 200)
            self.assertEqual(dfa_response.status_code, 200)

            nfa_accepted = nfa_response.json()['accepted']
            dfa_accepted = dfa_response.json()['accepted']

            self.assertEqual(nfa_accepted, dfa_accepted,
                             f"Language disagreement on string '{test_string}'")

    def test_complete_then_complement_workflow(self):
        """Test completing a DFA then taking its complement"""
        incomplete_dfa = {
            'states': ['S0', 'S1'],
            'alphabet': ['a', 'b'],
            'transitions': {
                'S0': {'a': ['S1']},  # Missing 'b' transition
                'S1': {'a': ['S0'], 'b': ['S1']}
            },
            'startingState': 'S0',
            'acceptingStates': ['S1']
        }

        # 1. Complete the DFA
        complete_response = self.post_json('/api/complete-dfa/', {
            'fsa': incomplete_dfa
        })
        self.assertEqual(complete_response.status_code, 200)
        completed_dfa = complete_response.json()['completed_fsa']

        # 2. Take complement of completed DFA
        complement_response = self.post_json('/api/complement-dfa/', {
            'fsa': completed_dfa
        })
        self.assertEqual(complement_response.status_code, 200)
        self.assertTrue(complement_response.json()['success'])

    def test_nfa_to_dfa_complete_complement_chain(self):
        """Test full transformation chain: NFA -> DFA -> Complete -> Complement"""
        # 1. Convert NFA to DFA
        convert_response = self.post_json('/api/nfa-to-dfa/', {
            'fsa': self.sample_nfa
        })
        self.assertEqual(convert_response.status_code, 200)
        dfa = convert_response.json()['converted_dfa']

        # 2. Complete the DFA (might already be complete)
        complete_response = self.post_json('/api/complete-dfa/', {
            'fsa': dfa
        })
        self.assertEqual(complete_response.status_code, 200)
        completed_dfa = complete_response.json()['completed_fsa']

        # 3. Take complement
        complement_response = self.post_json('/api/complement-dfa/', {
            'fsa': completed_dfa
        })
        self.assertEqual(complement_response.status_code, 200)
        complement_dfa = complement_response.json()['complement_fsa']

        # 4. Verify the result is still a valid DFA
        type_check_response = self.post_json('/api/check-fsa-type/', {
            'fsa': complement_dfa
        })
        self.assertEqual(type_check_response.status_code, 200)
        self.assertEqual(type_check_response.json()['type'], 'DFA')


class ComprehensiveErrorTests(FSAViewTestCase):
    """Comprehensive error testing for all endpoints"""

    def test_all_endpoints_handle_missing_fsa_or_regex(self):
        """Test that all endpoints properly handle missing required parameters"""
        # FSA endpoints
        fsa_endpoints = [
            '/api/simulate-fsa/',
            '/api/simulate-dfa/',
            '/api/simulate-nfa/',
            '/api/check-fsa-type/',
            '/api/check-epsilon-loops/',
            '/api/check-fsa-properties/',
            '/api/check-deterministic/',
            '/api/check-complete/',
            '/api/check-connected/',
            '/api/minimise-dfa/',
            '/api/nfa-to-dfa/',
            '/api/complete-dfa/',
            '/api/complement-dfa/',
        ]

        for endpoint in fsa_endpoints:
            with self.subTest(endpoint=endpoint):
                response = self.post_json(endpoint, {})
                self.assertEqual(response.status_code, 400)
                data = response.json()
                self.assertIn('error', data)
                self.assertIn('Missing FSA definition', data['error'])

        # Regex endpoint
        response = self.post_json('/api/regex-to-epsilon-nfa/', {})
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertIn('error', data)
        self.assertIn('Missing regex parameter', data['error'])

    def test_all_endpoints_handle_invalid_fsa(self):
        """Test that all endpoints properly handle invalid FSA"""
        endpoints = [
            '/api/simulate-fsa/',
            '/api/simulate-dfa/',
            '/api/simulate-nfa/',
            '/api/check-fsa-type/',
            '/api/check-epsilon-loops/',
            '/api/check-fsa-properties/',
            '/api/check-deterministic/',
            '/api/check-complete/',
            '/api/check-connected/',
            '/api/minimise-dfa/',
            '/api/nfa-to-dfa/',
            '/api/complete-dfa/',
            '/api/complement-dfa/',
        ]

        for endpoint in endpoints:
            with self.subTest(endpoint=endpoint):
                response = self.post_json(endpoint, {
                    'fsa': self.invalid_fsa
                })
                self.assertEqual(response.status_code, 400)

    def test_all_endpoints_reject_get_requests(self):
        """Test that all POST-only endpoints reject GET requests"""
        endpoints = [
            '/api/simulate-fsa/',
            '/api/simulate-dfa/',
            '/api/simulate-nfa/',
            '/api/simulate-nfa-stream/',
            '/api/check-fsa-type/',
            '/api/check-epsilon-loops/',
            '/api/simulate-nfa-depth-limit/',
            '/api/simulate-nfa-stream-depth-limit/',
            '/api/check-fsa-properties/',
            '/api/check-deterministic/',
            '/api/check-complete/',
            '/api/check-connected/',
            '/api/minimise-dfa/',
            '/api/nfa-to-dfa/',
            '/api/complete-dfa/',
            '/api/complement-dfa/',
            '/api/regex-to-epsilon-nfa/',
        ]

        for endpoint in endpoints:
            with self.subTest(endpoint=endpoint):
                response = self.client.get(endpoint)
                self.assertEqual(response.status_code, 405)  # Method Not Allowed


class DataTypeValidationTests(FSAViewTestCase):
    """Tests for data type validation in requests"""

    def test_fsa_must_be_dict(self):
        """Test that FSA parameter must be a dictionary"""
        endpoints_with_fsa = [
            '/api/simulate-fsa/',
            '/api/simulate-dfa/',
            '/api/simulate-nfa/',
            '/api/check-fsa-type/',
            '/api/nfa-to-dfa/',
        ]

        invalid_fsa_values = ["string", 123, [], None, True]

        for endpoint in endpoints_with_fsa:
            for invalid_fsa in invalid_fsa_values:
                with self.subTest(endpoint=endpoint, fsa_type=type(invalid_fsa).__name__):
                    response = self.post_json(endpoint, {
                        'fsa': invalid_fsa,
                        'input': 'a'
                    })
                    # Should return 400 due to validation failure
                    self.assertEqual(response.status_code, 400)

    def test_input_string_types(self):
        """Test different input string types"""
        simulation_endpoints = [
            '/api/simulate-fsa/',
            '/api/simulate-dfa/',
            '/api/simulate-nfa/',
        ]

        # Test with various input types (should all work or be converted to string)
        for endpoint in simulation_endpoints:
            with self.subTest(endpoint=endpoint):
                # Empty string should work
                response = self.post_json(endpoint, {
                    'fsa': self.sample_dfa,
                    'input': ''
                })
                self.assertEqual(response.status_code, 200)

                # Missing input should default to empty string
                response = self.post_json(endpoint, {
                    'fsa': self.sample_dfa
                })
                self.assertEqual(response.status_code, 200)


class SpecialCharacterTests(FSAViewTestCase):
    """Tests for handling special characters in FSA definitions"""

    def test_unicode_state_names(self):
        """Test FSA with Unicode state names"""
        unicode_fsa = {
            'states': ['α', 'β', 'γ'],
            'alphabet': ['a', 'b'],
            'transitions': {
                'α': {'a': ['β'], 'b': ['α']},
                'β': {'a': ['γ'], 'b': ['β']},
                'γ': {}
            },
            'startingState': 'α',
            'acceptingStates': ['γ']
        }

        response = self.post_json('/api/nfa-to-dfa/', {
            'fsa': unicode_fsa
        })
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['success'])

    def test_special_characters_in_alphabet(self):
        """Test FSA with special characters in alphabet"""
        special_char_fsa = {
            'states': ['S0', 'S1'],
            'alphabet': ['α', 'β', '1', '0'],
            'transitions': {
                'S0': {'α': ['S1'], 'β': ['S0'], '1': ['S0'], '0': ['S1']},
                'S1': {'α': ['S0'], 'β': ['S1'], '1': ['S1'], '0': ['S0']}
            },
            'startingState': 'S0',
            'acceptingStates': ['S1']
        }

        response = self.post_json('/api/nfa-to-dfa/', {
            'fsa': special_char_fsa
        })
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['success'])


class BoundaryConditionTests(FSAViewTestCase):
    """Tests for boundary conditions and extreme cases"""

    def test_very_long_state_names(self):
        """Test with very long state names"""
        long_state_name = 'S' + 'x' * 100
        long_name_fsa = {
            'states': [long_state_name, 'S1'],
            'alphabet': ['a'],
            'transitions': {
                long_state_name: {'a': ['S1']},
                'S1': {'a': [long_state_name]}
            },
            'startingState': long_state_name,
            'acceptingStates': ['S1']
        }

        response = self.post_json('/api/nfa-to-dfa/', {
            'fsa': long_name_fsa
        })
        self.assertEqual(response.status_code, 200)

    def test_large_alphabet(self):
        """Test with large alphabet"""
        # Create alphabet with many symbols
        large_alphabet = [chr(i) for i in range(ord('a'), ord('z') + 1)]

        large_alphabet_fsa = {
            'states': ['S0', 'S1'],
            'alphabet': large_alphabet,
            'transitions': {
                'S0': {symbol: ['S1'] for symbol in large_alphabet},
                'S1': {symbol: ['S0'] for symbol in large_alphabet}
            },
            'startingState': 'S0',
            'acceptingStates': ['S1']
        }

        response = self.post_json('/api/nfa-to-dfa/', {
            'fsa': large_alphabet_fsa
        })
        self.assertEqual(response.status_code, 200)

    def test_maximum_transitions_per_state(self):
        """Test state with maximum number of transitions"""
        max_trans_fsa = {
            'states': ['S0', 'S1', 'S2', 'S3', 'S4'],
            'alphabet': ['a'],
            'transitions': {
                'S0': {'a': ['S0', 'S1', 'S2', 'S3', 'S4']},  # Max non-determinism
                'S1': {'a': ['S1']},
                'S2': {'a': ['S2']},
                'S3': {'a': ['S3']},
                'S4': {'a': ['S4']}
            },
            'startingState': 'S0',
            'acceptingStates': ['S4']
        }

        response = self.post_json('/api/nfa-to-dfa/', {
            'fsa': max_trans_fsa
        })
        self.assertEqual(response.status_code, 200)


class StatisticsValidationTests(FSAViewTestCase):
    """Tests to validate statistics calculations"""

    def test_nfa_to_dfa_statistics_zero_division_prevention(self):
        """Test that statistics handle zero division gracefully"""
        # Create minimal FSA to test edge cases
        minimal_fsa = {
            'states': ['S0'],
            'alphabet': [],
            'transitions': {'S0': {}},
            'startingState': 'S0',
            'acceptingStates': []
        }

        response = self.post_json('/api/nfa-to-dfa/', {
            'fsa': minimal_fsa
        })

        if response.status_code == 200:
            data = response.json()
            stats = data['statistics']['conversion']

            # Check that percentages are handled gracefully
            self.assertIsInstance(stats['states_change_percentage'], (int, float))
            self.assertIsInstance(stats['transitions_change_percentage'], (int, float))

    def test_minimize_dfa_statistics_calculations(self):
        """Test DFA minimization statistics calculations"""
        response = self.post_json('/api/minimise-dfa/', {
            'fsa': self.sample_dfa
        })

        if response.status_code == 200:
            data = response.json()
            stats = data['statistics']

            # Check that all required statistics are present
            self.assertIn('original', stats)
            self.assertIn('minimised', stats)
            self.assertIn('reduction', stats)

            # Check calculation accuracy
            original = stats['original']
            minimised = stats['minimised']
            reduction = stats['reduction']

            expected_states_reduced = original['states_count'] - minimised['states_count']
            self.assertEqual(reduction['states_reduced'], expected_states_reduced)


class RegressionTests(FSAViewTestCase):
    """Regression tests for previously found issues"""

    def test_empty_transitions_handling(self):
        """Test FSA with empty transitions dict"""
        empty_transitions_fsa = {
            'states': ['S0'],
            'alphabet': ['a'],
            'transitions': {},
            'startingState': 'S0',
            'acceptingStates': ['S0']
        }

        response = self.post_json('/api/nfa-to-dfa/', {
            'fsa': empty_transitions_fsa
        })

        # Should handle gracefully (might be invalid but shouldn't crash)
        self.assertIn(response.status_code, [200, 400])

    def test_state_not_in_transitions(self):
        """Test state that exists in states list but not in transitions"""
        missing_state_fsa = {
            'states': ['S0', 'S1'],
            'alphabet': ['a'],
            'transitions': {
                'S0': {'a': ['S1']}
                # S1 missing from transitions
            },
            'startingState': 'S0',
            'acceptingStates': ['S1']
        }

        response = self.post_json('/api/nfa-to-dfa/', {
            'fsa': missing_state_fsa
        })
        self.assertEqual(response.status_code, 200)

    def test_transition_to_nonexistent_state(self):
        """Test transition to state not in states list"""
        invalid_target_fsa = {
            'states': ['S0'],
            'alphabet': ['a'],
            'transitions': {
                'S0': {'a': ['S999']}  # S999 doesn't exist
            },
            'startingState': 'S0',
            'acceptingStates': []
        }

        response = self.post_json('/api/nfa-to-dfa/', {
            'fsa': invalid_target_fsa
        })
        # Should be caught by validation
        self.assertEqual(response.status_code, 400)


class DocumentationExampleTests(FSAViewTestCase):
    """Tests using examples that might appear in documentation"""

    def test_simple_binary_string_nfa(self):
        """Test NFA that accepts binary strings ending in '01'"""
        binary_nfa = {
            'states': ['S0', 'S1', 'S2'],
            'alphabet': ['0', '1'],
            'transitions': {
                'S0': {'0': ['S0', 'S1'], '1': ['S0']},
                'S1': {'1': ['S2']},
                'S2': {}
            },
            'startingState': 'S0',
            'acceptingStates': ['S2']
        }

        response = self.post_json('/api/nfa-to-dfa/', {
            'fsa': binary_nfa
        })
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['success'])

        # Test that the conversion preserves the language
        converted_dfa = response.json()['converted_dfa']

        # Test strings that should be accepted
        accept_strings = ['01', '001', '101', '0001', '1001']
        for string in accept_strings:
            sim_response = self.post_json('/api/simulate-dfa/', {
                'fsa': converted_dfa,
                'input': string
            })
            self.assertTrue(sim_response.json()['accepted'],
                            f"Should accept '{string}'")

        # Test strings that should be rejected
        reject_strings = ['', '0', '1', '10', '00', '11', '010']
        for string in reject_strings:
            sim_response = self.post_json('/api/simulate-dfa/', {
                'fsa': converted_dfa,
                'input': string
            })
            self.assertFalse(sim_response.json()['accepted'],
                             f"Should reject '{string}'")

    def test_epsilon_transition_example(self):
        """Test classic epsilon transition example"""
        epsilon_example = {
            'states': ['S0', 'S1', 'S2', 'S3'],
            'alphabet': ['a', 'b'],
            'transitions': {
                'S0': {'': ['S1', 'S3']},  # Epsilon transitions
                'S1': {'a': ['S2']},
                'S2': {'a': ['S2'], 'b': ['S2']},
                'S3': {'b': ['S3']}
            },
            'startingState': 'S0',
            'acceptingStates': ['S2', 'S3']
        }

        response = self.post_json('/api/nfa-to-dfa/', {
            'fsa': epsilon_example
        })
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['success'])

        # Check that epsilon transitions were handled
        stats = response.json()['statistics']
        self.assertTrue(stats['original']['has_epsilon_transitions'])
        self.assertFalse(stats['converted']['has_epsilon_transitions'])


class ConcurrencySimulationTests(FSAViewTestCase):
    """Tests simulating potential concurrency issues"""

    def test_multiple_conversion_requests(self):
        """Test multiple conversion requests don't interfere"""
        responses = []

        # Make multiple requests
        for i in range(3):
            response = self.post_json('/api/nfa-to-dfa/', {
                'fsa': self.sample_nfa
            })
            responses.append(response)

        # All should succeed independently
        for i, response in enumerate(responses):
            with self.subTest(request=i):
                self.assertEqual(response.status_code, 200)
                self.assertTrue(response.json()['success'])

    def test_mixed_endpoint_requests(self):
        """Test mixed requests to different endpoints"""
        endpoints_and_data = [
            ('/api/check-fsa-type/', {'fsa': self.sample_dfa}),
            ('/api/nfa-to-dfa/', {'fsa': self.sample_nfa}),
            ('/api/simulate-dfa/', {'fsa': self.sample_dfa, 'input': 'ab'}),
            ('/api/check-fsa-properties/', {'fsa': self.sample_nfa}),
        ]

        responses = []
        for endpoint, data in endpoints_and_data:
            response = self.post_json(endpoint, data)
            responses.append((endpoint, response))

        # All should succeed
        for endpoint, response in responses:
            with self.subTest(endpoint=endpoint):
                self.assertEqual(response.status_code, 200)


class CompleteDFAViewTests(FSAViewTestCase):
    """Tests for the DFA completion endpoint"""

    def test_complete_dfa_successful(self):
        """Test successful DFA completion"""
        # Create an incomplete DFA
        incomplete_dfa = {
            'states': ['S0', 'S1'],
            'alphabet': ['a', 'b'],
            'transitions': {
                'S0': {'a': ['S1']},  # Missing 'b' transition
                'S1': {'a': ['S0'], 'b': ['S1']}
            },
            'startingState': 'S0',
            'acceptingStates': ['S1']
        }

        response = self.post_json('/api/complete-dfa/', {
            'fsa': incomplete_dfa
        })

        self.assertEqual(response.status_code, 200)
        data = response.json()

        self.assertTrue(data['success'])
        self.assertIn('completed_fsa', data)
        self.assertIn('statistics', data)
        self.assertIn('message', data)

        # Check that a dead state was added
        stats = data['statistics']['completion']
        self.assertTrue(stats['dead_state_added'])
        self.assertGreater(stats['states_added'], 0)
        self.assertGreater(stats['transitions_added'], 0)

    def test_complete_already_complete_dfa(self):
        """Test completion of already complete DFA"""
        response = self.post_json('/api/complete-dfa/', {
            'fsa': self.sample_dfa  # Already complete
        })

        self.assertEqual(response.status_code, 200)
        data = response.json()

        self.assertTrue(data['success'])
        stats = data['statistics']['completion']
        self.assertTrue(stats['was_already_complete'])
        self.assertFalse(stats['dead_state_added'])
        self.assertEqual(stats['states_added'], 0)

    def test_complete_non_deterministic_fsa(self):
        """Test completion fails for non-deterministic FSA"""
        response = self.post_json('/api/complete-dfa/', {
            'fsa': self.sample_nfa
        })

        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertIn('error', data)
        self.assertIn('deterministic FSA', data['error'])

    def test_complete_dfa_missing_fsa(self):
        """Test completion without FSA definition"""
        response = self.post_json('/api/complete-dfa/', {})

        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertIn('error', data)
        self.assertIn('Missing FSA definition', data['error'])

    def test_complete_dfa_invalid_structure(self):
        """Test completion with invalid FSA structure"""
        response = self.post_json('/api/complete-dfa/', {
            'fsa': self.invalid_fsa
        })

        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertIn('error', data)

    def test_complete_dfa_statistics_accuracy(self):
        """Test that completion statistics are calculated correctly"""
        incomplete_dfa = {
            'states': ['S0', 'S1', 'S2'],
            'alphabet': ['a', 'b'],
            'transitions': {
                'S0': {'a': ['S1'], 'b': ['S2']},
                'S1': {'a': ['S0']},  # Missing 'b' transition
                'S2': {'b': ['S2']}   # Missing 'a' transition
            },
            'startingState': 'S0',
            'acceptingStates': ['S2']
        }

        response = self.post_json('/api/complete-dfa/', {
            'fsa': incomplete_dfa
        })

        self.assertEqual(response.status_code, 200)
        data = response.json()

        original_stats = data['statistics']['original']
        completed_stats = data['statistics']['completed']
        completion_stats = data['statistics']['completion']

        # Verify original was incomplete
        self.assertFalse(original_stats['is_complete'])

        # Verify completed is complete
        self.assertTrue(completed_stats['is_complete'])

        # Verify counts are correct
        self.assertEqual(original_stats['states_count'], 3)
        self.assertEqual(completed_stats['states_count'], 4)  # Added one dead state
        self.assertEqual(completion_stats['states_added'], 1)
        self.assertEqual(completion_stats['transitions_added'], 4)  # 2 missing + 2 for dead state


class ComplementDFAViewTests(FSAViewTestCase):
    """Tests for the DFA complement endpoint"""

    def test_complement_dfa_successful(self):
        """Test successful DFA complement"""
        response = self.post_json('/api/complement-dfa/', {
            'fsa': self.sample_dfa
        })

        self.assertEqual(response.status_code, 200)
        data = response.json()

        self.assertTrue(data['success'])
        self.assertIn('complement_fsa', data)
        self.assertIn('statistics', data)
        self.assertIn('message', data)

        # Check that accepting states were flipped
        original_accepting = set(self.sample_dfa['acceptingStates'])
        complement_accepting = set(data['complement_fsa']['acceptingStates'])

        # Should have different accepting states (unless completion added states)
        self.assertNotEqual(original_accepting, complement_accepting)

    def test_complement_incomplete_dfa(self):
        """Test complement of incomplete DFA (should complete first)"""
        incomplete_dfa = {
            'states': ['S0', 'S1'],
            'alphabet': ['a', 'b'],
            'transitions': {
                'S0': {'a': ['S1']},  # Missing 'b' transition
                'S1': {'a': ['S0'], 'b': ['S1']}
            },
            'startingState': 'S0',
            'acceptingStates': ['S1']
        }

        response = self.post_json('/api/complement-dfa/', {
            'fsa': incomplete_dfa
        })

        self.assertEqual(response.status_code, 200)
        data = response.json()

        self.assertTrue(data['success'])
        analysis = data['statistics']['analysis']
        self.assertTrue(analysis['completion_required'])
        self.assertGreater(analysis['states_added_for_completeness'], 0)

    def test_complement_non_deterministic_fsa(self):
        """Test complement fails for non-deterministic FSA"""
        response = self.post_json('/api/complement-dfa/', {
            'fsa': self.sample_nfa
        })

        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertIn('error', data)
        self.assertIn('deterministic FSA', data['error'])

    def test_complement_dfa_missing_fsa(self):
        """Test complement without FSA definition"""
        response = self.post_json('/api/complement-dfa/', {})

        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertIn('error', data)
        self.assertIn('Missing FSA definition', data['error'])

    def test_complement_language_inversion(self):
        """Test that complement actually inverts the language"""
        # Test with a simple DFA
        simple_dfa = {
            'states': ['S0', 'S1'],
            'alphabet': ['a'],
            'transitions': {
                'S0': {'a': ['S1']},
                'S1': {'a': ['S0']}
            },
            'startingState': 'S0',
            'acceptingStates': ['S0']  # Accepts strings with even number of 'a's
        }

        # Get complement
        response = self.post_json('/api/complement-dfa/', {
            'fsa': simple_dfa
        })
        self.assertEqual(response.status_code, 200)
        complement_dfa = response.json()['complement_fsa']

        # Test strings
        test_strings = ['', 'a', 'aa', 'aaa', 'aaaa']

        for test_string in test_strings:
            # Test original DFA
            orig_response = self.post_json('/api/simulate-dfa/', {
                'fsa': simple_dfa,
                'input': test_string
            })

            # Test complement DFA
            comp_response = self.post_json('/api/simulate-dfa/', {
                'fsa': complement_dfa,
                'input': test_string
            })

            orig_accepted = orig_response.json()['accepted']
            comp_accepted = comp_response.json()['accepted']

            # Should be opposite
            self.assertNotEqual(orig_accepted, comp_accepted,
                              f"Complement failed for string '{test_string}'")

    def test_complement_statistics_accuracy(self):
        """Test that complement statistics are calculated correctly"""
        test_dfa = {
            'states': ['S0', 'S1', 'S2'],
            'alphabet': ['a'],
            'transitions': {
                'S0': {'a': ['S1']},
                'S1': {'a': ['S2']},
                'S2': {'a': ['S0']}
            },
            'startingState': 'S0',
            'acceptingStates': ['S1']  # Only S1 is accepting
        }

        response = self.post_json('/api/complement-dfa/', {
            'fsa': test_dfa
        })

        self.assertEqual(response.status_code, 200)
        data = response.json()

        original_stats = data['statistics']['original']
        complement_stats = data['statistics']['complement']
        analysis = data['statistics']['analysis']

        # Check accepting state counts
        self.assertEqual(original_stats['accepting_states_count'], 1)
        self.assertEqual(original_stats['non_accepting_states_count'], 2)

        # In complement, accepting and non-accepting should be flipped
        # (plus potentially a dead state if completion was needed)
        self.assertGreaterEqual(complement_stats['accepting_states_count'], 2)
        self.assertEqual(analysis['original_accepting_became_non_accepting'], 1)
        self.assertEqual(analysis['original_non_accepting_became_accepting'], 2)


class RegexConversionViewTests(FSAViewTestCase):
    """Tests for the regex to epsilon-NFA conversion endpoint"""

    def test_regex_to_epsilon_nfa_successful(self):
        """Test successful regex conversion"""
        response = self.post_json('/api/regex-to-epsilon-nfa/', {
            'regex': 'a*b'
        })

        self.assertEqual(response.status_code, 200)
        data = response.json()

        self.assertTrue(data['success'])
        self.assertIn('epsilon_nfa', data)
        self.assertIn('statistics', data)
        self.assertIn('message', data)
        self.assertEqual(data['regex'], 'a*b')

        # Check that we got a valid NFA structure
        nfa = data['epsilon_nfa']
        required_keys = ['states', 'alphabet', 'transitions', 'startingState', 'acceptingStates']
        for key in required_keys:
            self.assertIn(key, nfa)

        # Check statistics are present
        stats = data['statistics']
        required_stats = ['states_count', 'alphabet_size', 'transitions_count', 'accepting_states_count']
        for stat in required_stats:
            self.assertIn(stat, stats)
            self.assertIsInstance(stats[stat], int)

    def test_regex_to_epsilon_nfa_missing_regex(self):
        """Test conversion without regex parameter"""
        response = self.post_json('/api/regex-to-epsilon-nfa/', {})

        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertIn('error', data)
        self.assertIn('Missing regex parameter', data['error'])

    def test_regex_to_epsilon_nfa_invalid_syntax(self):
        """Test conversion with invalid regex syntax"""
        response = self.post_json('/api/regex-to-epsilon-nfa/', {
            'regex': '((('  # Unbalanced parentheses
        })

        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertIn('error', data)
        self.assertIn('Invalid regex syntax', data['error'])

    def test_regex_to_epsilon_nfa_empty_regex(self):
        """Test conversion with empty regex"""
        response = self.post_json('/api/regex-to-epsilon-nfa/', {
            'regex': ''
        })

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['regex'], '')

        # Empty regex should produce NFA that accepts empty string
        nfa = data['epsilon_nfa']
        self.assertTrue(len(nfa['states']) > 0)

    def test_regex_to_epsilon_nfa_complex_regex(self):
        """Test conversion with complex regex"""
        complex_regex = '(a|b)*abb'

        response = self.post_json('/api/regex-to-epsilon-nfa/', {
            'regex': complex_regex
        })

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['regex'], complex_regex)

        # Check that complex regex produces reasonable number of states
        stats = data['statistics']
        self.assertGreater(stats['states_count'], 1)
        self.assertGreater(stats['transitions_count'], 0)

    def test_regex_to_epsilon_nfa_with_epsilon(self):
        """Test conversion with explicit epsilon in regex"""
        response = self.post_json('/api/regex-to-epsilon-nfa/', {
            'regex': 'aεb'  # Using epsilon symbol
        })

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])

    def test_regex_to_epsilon_nfa_kleene_star(self):
        """Test conversion with Kleene star operations"""
        test_regexes = ['a*', 'a*b*', '(ab)*']

        for regex in test_regexes:
            with self.subTest(regex=regex):
                response = self.post_json('/api/regex-to-epsilon-nfa/', {
                    'regex': regex
                })

                self.assertEqual(response.status_code, 200)
                data = response.json()
                self.assertTrue(data['success'])
                self.assertEqual(data['regex'], regex)

    def test_regex_to_epsilon_nfa_plus_operations(self):
        """Test conversion with plus (+) operations - one or more"""
        test_regexes = ['a+', 'a+b+', '(ab)+', 'a+b*', '(a|b)+']

        for regex in test_regexes:
            with self.subTest(regex=regex):
                response = self.post_json('/api/regex-to-epsilon-nfa/', {
                    'regex': regex
                })

                self.assertEqual(response.status_code, 200)
                data = response.json()
                self.assertTrue(data['success'])
                self.assertEqual(data['regex'], regex)

                # Plus operations should create more states than simple characters
                stats = data['statistics']
                self.assertGreater(stats['states_count'], 2)

    def test_regex_to_epsilon_nfa_mixed_operators(self):
        """Test conversion with mixed * and + operators"""
        test_regexes = ['a*b+', 'a+b*', '(a*b)+', '(a+b)*', 'a*b+c*']

        for regex in test_regexes:
            with self.subTest(regex=regex):
                response = self.post_json('/api/regex-to-epsilon-nfa/', {
                    'regex': regex
                })

                self.assertEqual(response.status_code, 200)
                data = response.json()
                self.assertTrue(data['success'])
                self.assertEqual(data['regex'], regex)

    def test_regex_to_epsilon_nfa_union_operations(self):
        """Test conversion with union (|) operations"""
        test_regexes = ['a|b', 'a|b|c', '(a|b)c', 'a+|b*', '(a+|b)*']

        for regex in test_regexes:
            with self.subTest(regex=regex):
                response = self.post_json('/api/regex-to-epsilon-nfa/', {
                    'regex': regex
                })

                self.assertEqual(response.status_code, 200)
                data = response.json()
                self.assertTrue(data['success'])

    def test_regex_to_epsilon_nfa_concatenation(self):
        """Test conversion with concatenation operations"""
        test_regexes = ['ab', 'abc', 'a(bc)', 'a+b', 'ab+', 'a+b+']

        for regex in test_regexes:
            with self.subTest(regex=regex):
                response = self.post_json('/api/regex-to-epsilon-nfa/', {
                    'regex': regex
                })

                self.assertEqual(response.status_code, 200)
                data = response.json()
                self.assertTrue(data['success'])

    def test_regex_to_epsilon_nfa_nested_parentheses(self):
        """Test conversion with nested parentheses"""
        test_regexes = ['((a|b)*c)', '((a+|b)*c)+', '(a+(b|c)*)+']

        for regex in test_regexes:
            with self.subTest(regex=regex):
                response = self.post_json('/api/regex-to-epsilon-nfa/', {
                    'regex': regex
                })

                self.assertEqual(response.status_code, 200)
                data = response.json()
                self.assertTrue(data['success'])

    def test_regex_to_epsilon_nfa_single_characters(self):
        """Test conversion with single character regexes"""
        test_regexes = ['a', 'b', '0', '1']

        for regex in test_regexes:
            with self.subTest(regex=regex):
                response = self.post_json('/api/regex-to-epsilon-nfa/', {
                    'regex': regex
                })

                self.assertEqual(response.status_code, 200)
                data = response.json()
                self.assertTrue(data['success'])

                # Single character should have minimal states
                stats = data['statistics']
                self.assertGreaterEqual(stats['states_count'], 2)  # At least start and accept
                self.assertEqual(stats['alphabet_size'], 1)

    def test_regex_validation_before_conversion(self):
        """Test that regex validation occurs before conversion attempt"""
        # Test various invalid regex patterns (updated to exclude consecutive operators)
        invalid_regexes = [
            'a(b',      # Unmatched opening parenthesis
            'ab)',      # Unmatched closing parenthesis
            '*a',       # * at start (no preceding element)
            '+a',       # + at start (no preceding element)
            '|*',       # * immediately after |
            '|+',       # + immediately after |
        ]

        for invalid_regex in invalid_regexes:
            with self.subTest(regex=invalid_regex):
                response = self.post_json('/api/regex-to-epsilon-nfa/', {
                    'regex': invalid_regex
                })

                self.assertEqual(response.status_code, 400)
                data = response.json()
                self.assertIn('error', data)
                self.assertIn('Invalid regex syntax', data['error'])

    def test_regex_to_epsilon_nfa_statistics_completeness(self):
        """Test that all expected statistics are provided"""
        response = self.post_json('/api/regex-to-epsilon-nfa/', {
            'regex': 'a+b*'  # Now valid with + support
        })

        self.assertEqual(response.status_code, 200)
        data = response.json()
        stats = data['statistics']

        # Check all expected statistics are non-negative integers
        for key in ['states_count', 'alphabet_size', 'transitions_count', 'accepting_states_count']:
            self.assertIn(key, stats)
            self.assertIsInstance(stats[key], int)
            self.assertGreaterEqual(stats[key], 0)

        # Verify specific values make sense for this regex
        self.assertEqual(stats['alphabet_size'], 2)  # 'a' and 'b'
        self.assertEqual(stats['accepting_states_count'], 1)  # Single accept state
        self.assertGreater(stats['states_count'], 4)  # Should have multiple states for a+b*

    def test_regex_to_epsilon_nfa_malformed_json(self):
        """Test endpoint with malformed JSON"""
        response = self.client.post(
            '/api/regex-to-epsilon-nfa/',
            data='{"regex": invalid json}',
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 400)

    def test_regex_conversion_function_exception(self):
        """Test exception in regex conversion function"""
        # Mock validation to pass first, then make conversion fail
        with patch('simulator.regex_conversions.validate_regex_syntax') as mock_validate, \
                patch('simulator.regex_conversions.regex_to_epsilon_nfa') as mock_convert:
            mock_validate.return_value = {'valid': True}  # Pass validation
            mock_convert.side_effect = Exception("Conversion error")

            response = self.post_json('/api/regex-to-epsilon-nfa/', {
                'regex': 'a*'
            })

            self.assertEqual(response.status_code, 500)
            data = response.json()
            self.assertIn('error', data)
            self.assertIn('Server error', data['error'])

    def test_regex_validation_function_exception(self):
        """Test exception in regex validation function"""
        # Test with a regex that will cause the validation function to fail
        with patch('simulator.regex_conversions.validate_regex_syntax') as mock_validate:
            mock_validate.side_effect = Exception("Validation error")

            response = self.post_json('/api/regex-to-epsilon-nfa/', {
                'regex': 'a*'
            })

            self.assertEqual(response.status_code, 500)
            data = response.json()
            self.assertIn('error', data)
            self.assertIn('Server error', data['error'])

    def test_regex_to_epsilon_nfa_none_regex(self):
        """Test with None as regex value"""
        response = self.post_json('/api/regex-to-epsilon-nfa/', {
            'regex': None
        })

        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertIn('error', data)
        self.assertIn('Missing regex parameter', data['error'])

    def test_regex_to_epsilon_nfa_plus_vs_star_behavior(self):
        """Test that + and * operators behave differently"""
        # Test a+ (one or more 'a')
        response_plus = self.post_json('/api/regex-to-epsilon-nfa/', {
            'regex': 'a+'
        })
        self.assertEqual(response_plus.status_code, 200)

        # Test a* (zero or more 'a')
        response_star = self.post_json('/api/regex-to-epsilon-nfa/', {
            'regex': 'a*'
        })
        self.assertEqual(response_star.status_code, 200)

        # Both should succeed but may have different structures
        plus_nfa = response_plus.json()['epsilon_nfa']
        star_nfa = response_star.json()['epsilon_nfa']

        # Both should be valid NFAs
        for nfa in [plus_nfa, star_nfa]:
            self.assertIn('states', nfa)
            self.assertIn('alphabet', nfa)
            self.assertIn('transitions', nfa)
            self.assertIn('startingState', nfa)
            self.assertIn('acceptingStates', nfa)

    def test_regex_to_epsilon_nfa_multiple_postfix_operators(self):
        """Test regexes with multiple postfix operators (mathematically valid but redundant)"""
        # These are now syntactically and mathematically valid
        test_regexes = ['a*+', 'a+*', '(ab)*+', '(ab)+*']

        for regex in test_regexes:
            with self.subTest(regex=regex):
                response = self.post_json('/api/regex-to-epsilon-nfa/', {
                    'regex': regex
                })

                # These should now be accepted as mathematically valid
                self.assertEqual(response.status_code, 200)
                data = response.json()
                self.assertTrue(data['success'])
                self.assertEqual(data['regex'], regex)

                # Should produce reasonable NFA structure
                stats = data['statistics']
                self.assertGreater(stats['states_count'], 2)
                self.assertGreater(stats['transitions_count'], 0)

    def test_regex_to_epsilon_nfa_real_world_examples(self):
        """Test conversion with realistic regex examples"""
        real_world_regexes = [
            'a+b+',           # One or more a's followed by one or more b's
            '(a|b)+',         # One or more of either a or b
            'a*b+a*',         # Zero or more a's, one or more b's, zero or more a's
            '(ab)+|(ba)+',    # One or more ab's or one or more ba's
            '((a+b)*c)+',     # Complex nested expression
        ]

        for regex in real_world_regexes:
            with self.subTest(regex=regex):
                response = self.post_json('/api/regex-to-epsilon-nfa/', {
                    'regex': regex
                })

                self.assertEqual(response.status_code, 200)
                data = response.json()
                self.assertTrue(data['success'])
                self.assertEqual(data['regex'], regex)

                # Should produce reasonable NFA structure
                stats = data['statistics']
                self.assertGreater(stats['states_count'], 2)
                self.assertGreater(stats['transitions_count'], 0)

    def test_regex_to_epsilon_nfa_edge_cases_with_plus(self):
        """Test edge cases specifically related to the + operator"""
        # These patterns are actually mathematically valid (corrected understanding)
        valid_edge_cases = [
            ('()+', 'One or more empty strings = empty string'),
            ('(a|)+', 'One or more of (a or empty) = accepts "", "a", "aa", etc.'),
        ]

        for regex, description in valid_edge_cases:
            with self.subTest(regex=regex, description=description):
                response = self.post_json('/api/regex-to-epsilon-nfa/', {
                    'regex': regex
                })

                # These should now be accepted as valid (they are mathematically sound)
                self.assertEqual(response.status_code, 200)
                data = response.json()
                self.assertTrue(data['success'])
                self.assertEqual(data['regex'], regex)

        # Test some genuinely problematic patterns
        invalid_edge_cases = [
            '+',        # Just a plus with nothing
            '++',       # Multiple pluses with nothing
            '((',       # Unmatched opening parentheses
            '))',       # Unmatched closing parentheses
        ]

        for regex in invalid_edge_cases:
            with self.subTest(regex=regex):
                response = self.post_json('/api/regex-to-epsilon-nfa/', {
                    'regex': regex
                })

                # These should fail
                self.assertEqual(response.status_code, 400)
                data = response.json()
                self.assertIn('error', data)

    def test_regex_conversion_validates_plus_operator(self):
        """Test that plus operator validation works correctly"""
        # Valid plus usage (including consecutive operators)
        valid_plus_regexes = ['a+', '(ab)+', '(a|b)+', 'a+b*', 'a*+', 'a+*']

        for regex in valid_plus_regexes:
            with self.subTest(regex=regex):
                response = self.post_json('/api/regex-to-epsilon-nfa/', {
                    'regex': regex
                })

                self.assertEqual(response.status_code, 200)
                data = response.json()
                self.assertTrue(data['success'])

        # Invalid plus usage (+ at beginning with nothing to apply to)
        invalid_plus_regexes = ['+a', '+', '|+']

        for regex in invalid_plus_regexes:
            with self.subTest(regex=regex):
                response = self.post_json('/api/regex-to-epsilon-nfa/', {
                    'regex': regex
                })

                self.assertEqual(response.status_code, 400)
                data = response.json()
                self.assertIn('error', data)
                self.assertIn('Invalid regex syntax', data['error'])

    def test_regex_to_epsilon_nfa_consecutive_operator_equivalences(self):
        """Test that consecutive operators produce valid NFAs with expected properties"""
        # Test specific consecutive operator patterns
        consecutive_patterns = [
            ('a*+', 'Should be equivalent to a*'),
            ('a+*', 'Should be equivalent to a*'),
            ('(ab)*+', 'Should be equivalent to (ab)*'),
            ('(ab)+*', 'Should be equivalent to (ab)*'),
        ]

        for regex, description in consecutive_patterns:
            with self.subTest(regex=regex, description=description):
                response = self.post_json('/api/regex-to-epsilon-nfa/', {
                    'regex': regex
                })

                self.assertEqual(response.status_code, 200)
                data = response.json()
                self.assertTrue(data['success'])

                # Verify NFA structure is reasonable
                nfa = data['epsilon_nfa']
                self.assertIn('states', nfa)
                self.assertIn('alphabet', nfa)
                self.assertIn('transitions', nfa)
                self.assertIn('startingState', nfa)
                self.assertIn('acceptingStates', nfa)

                # Should have multiple states due to Thompson construction
                self.assertGreater(len(nfa['states']), 2)


class MinimiseNFAViewTests(FSAViewTestCase):
    """Tests for the NFA minimisation endpoint"""

    def test_minimize_nfa_successful_deterministic(self):
        """Test successful NFA minimisation with deterministic input"""
        response = self.post_json('/api/minimise-nfa/', {
            'fsa': self.sample_dfa  # DFA is also a valid NFA
        })

        self.assertEqual(response.status_code, 200)
        data = response.json()

        self.assertTrue(data['success'])
        self.assertIn('minimised_fsa', data)
        self.assertIn('statistics', data)
        self.assertIn('minimisation_details', data)

        # Check minimization details
        details = data['minimisation_details']
        self.assertIn('method_used', details)
        self.assertIn('is_optimal', details)
        self.assertIn('stages', details)
        self.assertIsInstance(details['stages'], list)

    def test_minimise_nfa_successful_nondeterministic(self):
        """Test successful NFA minimisation with non-deterministic input"""
        response = self.post_json('/api/minimise-nfa/', {
            'fsa': self.sample_nfa
        })

        self.assertEqual(response.status_code, 200)
        data = response.json()

        self.assertTrue(data['success'])
        self.assertIn('minimised_fsa', data)
        self.assertIn('statistics', data)

        # Check that statistics include epsilon transition analysis
        original_stats = data['statistics']['original']
        minimised_stats = data['statistics']['minimised']
        self.assertIn('has_epsilon_transitions', original_stats)
        self.assertIn('is_deterministic', original_stats)
        self.assertIn('has_epsilon_transitions', minimised_stats)
        self.assertIn('is_deterministic', minimised_stats)

    def test_minimise_nfa_missing_fsa(self):
        """Test NFA minimisation without FSA definition"""
        response = self.post_json('/api/minimise-nfa/', {})

        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertIn('error', data)
        self.assertIn('Missing FSA definition', data['error'])

    def test_minimise_nfa_invalid_structure(self):
        """Test NFA minimisation with invalid FSA structure"""
        response = self.post_json('/api/minimise-nfa/', {
            'fsa': self.invalid_fsa
        })

        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertIn('error', data)

    @patch('simulator.views.minimise_nfa')
    def test_minimise_nfa_function_exception(self, mock_minimise):
        """Test exception in NFA minimisation function"""
        mock_minimise.side_effect = Exception("NFA minimization error")

        response = self.post_json('/api/minimise-nfa/', {
            'fsa': self.sample_nfa
        })

        self.assertEqual(response.status_code, 500)
        data = response.json()
        self.assertIn('error', data)
        self.assertIn('Server error', data['error'])

    def test_minimise_nfa_already_minimal(self):
        """Test NFA minimisation when FSA is already minimal"""
        # Create a simple minimal NFA
        minimal_nfa = {
            'states': ['S0'],
            'alphabet': ['a'],
            'transitions': {'S0': {'a': ['S0']}},
            'startingState': 'S0',
            'acceptingStates': ['S0']
        }

        response = self.post_json('/api/minimise-nfa/', {
            'fsa': minimal_nfa
        })

        self.assertEqual(response.status_code, 200)
        data = response.json()

        self.assertTrue(data['success'])
        reduction_stats = data['statistics']['reduction']

        # Should indicate no reduction was possible
        if reduction_stats['is_already_minimal']:
            self.assertEqual(reduction_stats['states_reduced'], 0)
            self.assertIn('already minimal', data['message'])

    def test_minimise_nfa_statistics_accuracy(self):
        """Test that NFA minimisation statistics are calculated correctly"""
        response = self.post_json('/api/minimise-nfa/', {
            'fsa': self.sample_nfa
        })

        self.assertEqual(response.status_code, 200)
        data = response.json()

        original_stats = data['statistics']['original']
        minimised_stats = data['statistics']['minimised']
        reduction_stats = data['statistics']['reduction']
        details = data['minimisation_details']

        # Verify statistics consistency
        self.assertEqual(original_stats['states_count'], details['original_states'])
        self.assertEqual(minimised_stats['states_count'], details['final_states'])
        self.assertEqual(reduction_stats['states_reduced'],
                         original_stats['states_count'] - minimised_stats['states_count'])

        # Verify percentage calculation
        if original_stats['states_count'] > 0:
            expected_percent = (reduction_stats['states_reduced'] / original_stats['states_count']) * 100
            self.assertAlmostEqual(reduction_stats['states_reduction_percentage'], expected_percent, places=2)