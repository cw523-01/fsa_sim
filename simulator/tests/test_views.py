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