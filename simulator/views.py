from django.shortcuts import render
from django.http import JsonResponse, StreamingHttpResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
import json
from .fsa_simulation import (
    simulate_deterministic_fsa,
    simulate_nondeterministic_fsa,
    simulate_nondeterministic_fsa_generator,
    detect_epsilon_loops,
    simulate_nondeterministic_fsa_with_depth_limit,
    simulate_nondeterministic_fsa_generator_with_depth_limit
)
from .fsa_properties import (
    is_deterministic,
    is_complete,
    is_connected,
    check_all_properties,
    validate_fsa_structure,
    is_nondeterministic
)
from .fsa_transformations import minimise_dfa, nfa_to_dfa, complete_dfa, complement_dfa
from .regex_conversions import regex_to_epsilon_nfa

def index(request):
    return render(request, 'simulator/index.html')


@csrf_exempt
@require_POST
def simulate_fsa(request):
    """
    Django view to handle FSA simulation requests.
    Automatically detects if FSA is deterministic or non-deterministic.

    Expects a POST request with a JSON body containing:
    - fsa: The FSA definition in the proper format
    - input: The input string to simulate

    Returns a JSON response with simulation results.
    """
    try:
        # Parse the request body
        data = json.loads(request.body)
        fsa = data.get('fsa')
        input_string = data.get('input', '')

        if not fsa:
            return JsonResponse({'error': 'Missing FSA definition'}, status=400)

        # Validate FSA structure
        validation = validate_fsa_structure(fsa)
        if not validation['valid']:
            return JsonResponse({'error': validation['error']}, status=400)

        # Check if FSA is non-deterministic
        if is_nondeterministic(fsa):
            # Use NFA simulation
            result = simulate_nondeterministic_fsa(fsa, input_string)

            if isinstance(result, list):
                # Input was accepted - result is list of accepting paths
                return JsonResponse({
                    'accepted': True,
                    'type': 'nfa',
                    'accepting_paths': result,
                    'num_paths': len(result)
                })
            else:
                # Input was rejected
                return JsonResponse({
                    'accepted': False,
                    'type': 'nfa',
                    'paths_explored': result.get('paths_explored', 0),
                    'rejection_reason': result.get('rejection_reason', 'Unknown rejection reason'),
                    'partial_paths': result.get('partial_paths', [])
                })
        else:
            # Use DFA simulation
            result = simulate_deterministic_fsa(fsa, input_string)

            if isinstance(result, list):
                # Input was accepted - result is the execution path
                return JsonResponse({
                    'accepted': True,
                    'type': 'dfa',
                    'path': result
                })
            else:
                # Input was rejected
                return JsonResponse({
                    'accepted': False,
                    'type': 'dfa',
                    'path': result.get('path', []),
                    'rejection_reason': result.get('rejection_reason', 'Unknown rejection reason'),
                    'rejection_position': result.get('rejection_position', 0)
                })

    except ValueError as e:
        return JsonResponse({'error': str(e)}, status=400)
    except Exception as e:
        return JsonResponse({'error': f'Server error: {str(e)}'}, status=500)


@csrf_exempt
@require_POST
def simulate_dfa(request):
    """
    Django view to handle deterministic FSA simulation requests specifically.
    """
    try:
        # Parse the request body
        data = json.loads(request.body)
        fsa = data.get('fsa')
        input_string = data.get('input', '')

        if not fsa:
            return JsonResponse({'error': 'Missing FSA definition'}, status=400)

        # Validate FSA structure
        validation = validate_fsa_structure(fsa)
        if not validation['valid']:
            return JsonResponse({'error': validation['error']}, status=400)

        # Simulate the DFA
        result = simulate_deterministic_fsa(fsa, input_string)

        # Handle both response formats from the function
        if isinstance(result, list):
            # Input was accepted - result is the execution path
            return JsonResponse({
                'accepted': True,
                'path': result
            })
        elif isinstance(result, dict) and 'accepted' in result and not result['accepted']:
            # Input was rejected - result contains detailed rejection info
            return JsonResponse({
                'accepted': False,
                'path': result.get('path', []),
                'rejection_reason': result.get('rejection_reason', 'Unknown rejection reason'),
                'rejection_position': result.get('rejection_position', 0)
            })
        else:
            # Fallback for unexpected result
            return JsonResponse({
                'accepted': False,
                'path': [],
                'rejection_reason': 'Unexpected result format',
                'rejection_position': 0
            })

    except ValueError as e:
        return JsonResponse({'error': str(e)}, status=400)
    except Exception as e:
        return JsonResponse({'error': f'Server error: {str(e)}'}, status=500)


@csrf_exempt
@require_POST
def simulate_nfa(request):
    """
    Django view to handle non-deterministic FSA simulation requests.
    """
    try:
        # Parse the request body
        data = json.loads(request.body)
        fsa = data.get('fsa')
        input_string = data.get('input', '')

        if not fsa:
            return JsonResponse({'error': 'Missing FSA definition'}, status=400)

        # Validate FSA structure
        validation = validate_fsa_structure(fsa)
        if not validation['valid']:
            return JsonResponse({'error': validation['error']}, status=400)

        # Simulate the NFA
        result = simulate_nondeterministic_fsa(fsa, input_string)

        if isinstance(result, list):
            # Input was accepted - result is list of accepting paths
            return JsonResponse({
                'accepted': True,
                'accepting_paths': result,
                'num_paths': len(result)
            })
        else:
            # Input was rejected
            return JsonResponse({
                'accepted': False,
                'paths_explored': result.get('paths_explored', 0),
                'rejection_reason': result.get('rejection_reason', 'Unknown rejection reason'),
                'partial_paths': result.get('partial_paths', [])
            })

    except ValueError as e:
        return JsonResponse({'error': str(e)}, status=400)
    except Exception as e:
        return JsonResponse({'error': f'Server error: {str(e)}'}, status=500)


@csrf_exempt
@require_POST
def simulate_nfa_stream(request):
    """
    Django view to handle streaming non-deterministic FSA simulation requests.
    Returns results as they are generated using Server-Sent Events format.
    """
    try:
        # Parse the request body
        data = json.loads(request.body)
        fsa = data.get('fsa')
        input_string = data.get('input', '')

        if not fsa:
            def error_generator():
                yield f"data: {json.dumps({'error': 'Missing FSA definition'})}\n\n"

            return StreamingHttpResponse(
                error_generator(),
                content_type='text/event-stream',
                status=400
            )

        # Validate FSA structure
        validation = validate_fsa_structure(fsa)
        if not validation['valid']:
            def error_generator():
                yield f"data: {json.dumps({'error': validation['error']})}\n\n"

            return StreamingHttpResponse(
                error_generator(),
                content_type='text/event-stream',
                status=400
            )

        def result_generator():
            """Generator to stream NFA simulation results as Server-Sent Events"""
            try:
                for result in simulate_nondeterministic_fsa_generator(fsa, input_string):
                    # Format as Server-Sent Event
                    yield f"data: {json.dumps(result)}\n\n"

                # Send end-of-stream marker
                yield f"data: {json.dumps({'type': 'end'})}\n\n"

            except Exception as e:
                yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

        # Create the streaming response
        response = StreamingHttpResponse(result_generator(), content_type='text/event-stream')

        # Set only the headers that are allowed (no hop-by-hop headers)
        response['Cache-Control'] = 'no-cache'
        response['X-Accel-Buffering'] = 'no'  # Disable nginx buffering

        # DO NOT set Connection: keep-alive - it's handled automatically by HTTP/1.1
        # The browser will maintain the connection for streaming

        return response

    except ValueError as e:
        def error_generator():
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

        return StreamingHttpResponse(
            error_generator(),
            content_type='text/event-stream',
            status=400
        )
    except Exception as e:
        def error_generator():
            yield f"data: {json.dumps({'error': f'Server error: {str(e)}'})}\n\n"

        return StreamingHttpResponse(
            error_generator(),
            content_type='text/event-stream',
            status=500
        )


@csrf_exempt
@require_POST
def check_fsa_type(request):
    """
    Django view to check if an FSA is deterministic or non-deterministic.
    """
    try:
        # Parse the request body
        data = json.loads(request.body)
        fsa = data.get('fsa')

        if not fsa:
            return JsonResponse({'error': 'Missing FSA definition'}, status=400)

        # Validate FSA structure
        validation = validate_fsa_structure(fsa)
        if not validation['valid']:
            return JsonResponse({'error': validation['error']}, status=400)

        # Check FSA type
        is_nfa = is_nondeterministic(fsa)

        return JsonResponse({
            'is_nondeterministic': is_nfa,
            'type': 'NFA' if is_nfa else 'DFA',
            'description': 'Non-deterministic Finite Automaton' if is_nfa else 'Deterministic Finite Automaton'
        })

    except ValueError as e:
        return JsonResponse({'error': str(e)}, status=400)
    except Exception as e:
        return JsonResponse({'error': f'Server error: {str(e)}'}, status=500)


@csrf_exempt
@require_POST
def check_epsilon_loops(request):
    """
    Django view to detect epsilon loops in an FSA.

    Expects a POST request with a JSON body containing:
    - fsa: The FSA definition in the proper format

    Returns a JSON response with epsilon loop detection results.
    """
    try:
        # Parse the request body
        data = json.loads(request.body)
        fsa = data.get('fsa')

        if not fsa:
            return JsonResponse({'error': 'Missing FSA definition'}, status=400)

        # Validate FSA structure
        validation = validate_fsa_structure(fsa)
        if not validation['valid']:
            return JsonResponse({'error': validation['error']}, status=400)

        # Detect epsilon loops
        result = detect_epsilon_loops(fsa)

        # Enhance the response with additional analysis
        response_data = {
            'has_epsilon_loops': result['has_epsilon_loops'],
            'total_loops_found': len(result['loop_details']),
            'loops': []
        }

        # Process each loop for better client understanding
        for i, loop in enumerate(result['loop_details']):
            loop_info = {
                'loop_id': i + 1,
                'states_in_cycle': loop['cycle'][:-1] if len(loop['cycle']) > 1 else loop['cycle'],
                # Remove duplicate end state
                'cycle_length': len(loop['cycle']) - 1 if len(loop['cycle']) > 1 else 1,
                'epsilon_transitions': loop['transitions'],
                'reachable_from_start': loop['reachable_from_start'],
                'loop_type': 'self_loop' if len(set(loop['cycle'])) <= 1 else 'multi_state_cycle',
                'full_cycle_path': loop['cycle']  # Include full path for visualization
            }
            response_data['loops'].append(loop_info)

        # Add summary information
        reachable_loops = [loop for loop in result['loop_details'] if loop['reachable_from_start']]
        unreachable_loops = [loop for loop in result['loop_details'] if not loop['reachable_from_start']]

        response_data['summary'] = {
            'reachable_loops_count': len(reachable_loops),
            'unreachable_loops_count': len(unreachable_loops),
            'has_reachable_loops': len(reachable_loops) > 0,
            'potential_infinite_loops': len(reachable_loops) > 0,
            'analysis': {
                'epsilon_transitions_present': any(
                    '' in fsa['transitions'].get(state, {}) and fsa['transitions'][state]['']
                    for state in fsa['states']
                ),
                'warning': 'Reachable epsilon loops may cause infinite execution during simulation' if len(
                    reachable_loops) > 0 else None
            }
        }

        return JsonResponse(response_data)

    except ValueError as e:
        return JsonResponse({'error': str(e)}, status=400)
    except Exception as e:
        return JsonResponse({'error': f'Server error: {str(e)}'}, status=500)


@csrf_exempt
@require_POST
def simulate_nfa_with_depth_limit(request):
    """
    Django view to handle non-deterministic FSA simulation with depth limiting.

    Expects a POST request with a JSON body containing:
    - fsa: The FSA definition in the proper format
    - input: The input string to simulate
    - max_depth: Maximum epsilon transition depth (positive integer)

    Returns a JSON response with simulation results.
    """
    try:
        # Parse the request body
        data = json.loads(request.body)
        fsa = data.get('fsa')
        input_string = data.get('input', '')
        max_depth = data.get('max_depth')

        if not fsa:
            return JsonResponse({'error': 'Missing FSA definition'}, status=400)

        if max_depth is None:
            return JsonResponse({'error': 'Missing max_depth parameter'}, status=400)

        # Validate max_depth
        try:
            max_depth = int(max_depth)
            if max_depth <= 0:
                return JsonResponse({'error': 'max_depth must be a positive integer'}, status=400)
        except (ValueError, TypeError):
            return JsonResponse({'error': 'max_depth must be a positive integer'}, status=400)

        # Validate FSA structure
        validation = validate_fsa_structure(fsa)
        if not validation['valid']:
            return JsonResponse({'error': validation['error']}, status=400)

        # Simulate the NFA with depth limit
        result = simulate_nondeterministic_fsa_with_depth_limit(fsa, input_string, max_depth)

        if isinstance(result, list):
            # Input was accepted - result is list of accepting paths
            return JsonResponse({
                'accepted': True,
                'accepting_paths': result,
                'num_paths': len(result),
                'max_depth_used': max_depth,
                'depth_limit_reached': False
            })
        else:
            # Input was rejected
            return JsonResponse({
                'accepted': False,
                'paths_explored': result.get('paths_explored', 0),
                'rejection_reason': result.get('rejection_reason', 'Unknown rejection reason'),
                'partial_paths': result.get('partial_paths', []),
                'depth_limit_reached': result.get('depth_limit_reached', False),
                'max_depth_used': max_depth
            })

    except ValueError as e:
        return JsonResponse({'error': str(e)}, status=400)
    except Exception as e:
        return JsonResponse({'error': f'Server error: {str(e)}'}, status=500)


@csrf_exempt
@require_POST
def simulate_nfa_stream_with_depth_limit(request):
    """
    Django view to handle streaming non-deterministic FSA simulation with depth limiting.
    Returns results as they are generated using Server-Sent Events format.

    Expects a POST request with a JSON body containing:
    - fsa: The FSA definition in the proper format
    - input: The input string to simulate
    - max_depth: Maximum epsilon transition depth (positive integer)
    """
    try:
        # Parse the request body
        data = json.loads(request.body)
        fsa = data.get('fsa')
        input_string = data.get('input', '')
        max_depth = data.get('max_depth')

        if not fsa:
            def error_generator():
                yield f"data: {json.dumps({'error': 'Missing FSA definition'})}\n\n"

            return StreamingHttpResponse(
                error_generator(),
                content_type='text/event-stream',
                status=400
            )

        if max_depth is None:
            def error_generator():
                yield f"data: {json.dumps({'error': 'Missing max_depth parameter'})}\n\n"

            return StreamingHttpResponse(
                error_generator(),
                content_type='text/event-stream',
                status=400
            )

        # Validate max_depth
        try:
            max_depth = int(max_depth)
            if max_depth <= 0:
                def error_generator():
                    yield f"data: {json.dumps({'error': 'max_depth must be a positive integer'})}\n\n"

                return StreamingHttpResponse(
                    error_generator(),
                    content_type='text/event-stream',
                    status=400
                )
        except (ValueError, TypeError):
            def error_generator():
                yield f"data: {json.dumps({'error': 'max_depth must be a positive integer'})}\n\n"

            return StreamingHttpResponse(
                error_generator(),
                content_type='text/event-stream',
                status=400
            )

        # Validate FSA structure
        validation = validate_fsa_structure(fsa)
        if not validation['valid']:
            def error_generator():
                yield f"data: {json.dumps({'error': validation['error']})}\n\n"

            return StreamingHttpResponse(
                error_generator(),
                content_type='text/event-stream',
                status=400
            )

        def result_generator():
            """Generator to stream depth-limited NFA simulation results as Server-Sent Events"""
            try:
                for result in simulate_nondeterministic_fsa_generator_with_depth_limit(fsa, input_string, max_depth):
                    # Format as Server-Sent Event
                    yield f"data: {json.dumps(result)}\n\n"

                # Send end-of-stream marker
                yield f"data: {json.dumps({'type': 'end'})}\n\n"

            except Exception as e:
                yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

        # Create the streaming response
        response = StreamingHttpResponse(result_generator(), content_type='text/event-stream')

        # Set headers for streaming
        response['Cache-Control'] = 'no-cache'
        response['X-Accel-Buffering'] = 'no'  # Disable nginx buffering

        return response

    except ValueError as e:
        def error_generator():
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

        return StreamingHttpResponse(
            error_generator(),
            content_type='text/event-stream',
            status=400
        )
    except Exception as e:
        def error_generator():
            yield f"data: {json.dumps({'error': f'Server error: {str(e)}'})}\n\n"

        return StreamingHttpResponse(
            error_generator(),
            content_type='text/event-stream',
            status=500
        )


@csrf_exempt
@require_POST
def check_fsa_properties(request):
    """
    Django view to check FSA properties (deterministic, complete, connected).

    Expects a POST request with a JSON body containing:
    - fsa: The FSA definition in the proper format

    Returns a JSON response with property check results.
    """
    try:
        # Parse the request body
        data = json.loads(request.body)
        fsa = data.get('fsa')

        if not fsa:
            return JsonResponse({'error': 'Missing FSA definition'}, status=400)

        # Validate FSA structure
        validation = validate_fsa_structure(fsa)
        if not validation['valid']:
            return JsonResponse({'error': validation['error']}, status=400)

        # Check all properties
        properties = check_all_properties(fsa)

        return JsonResponse({
            'properties': properties,
            'summary': {
                'total_states': len(fsa['states']),
                'alphabet_size': len(fsa['alphabet']),
                'starting_state': fsa['startingState'],
                'accepting_states_count': len(fsa['acceptingStates']),
                'has_epsilon_transitions': any(
                    '' in fsa['transitions'].get(state, {}) and fsa['transitions'][state]['']
                    for state in fsa['states']
                )
            }
        })

    except ValueError as e:
        return JsonResponse({'error': str(e)}, status=400)
    except Exception as e:
        return JsonResponse({'error': f'Server error: {str(e)}'}, status=500)


@csrf_exempt
@require_POST
def check_deterministic(request):
    """
    Django view to check if an FSA is deterministic.

    Expects a POST request with a JSON body containing:
    - fsa: The FSA definition in the proper format

    Returns a JSON response with determinism check result.
    """
    try:
        # Parse the request body
        data = json.loads(request.body)
        fsa = data.get('fsa')

        if not fsa:
            return JsonResponse({'error': 'Missing FSA definition'}, status=400)

        # Validate FSA structure
        validation = validate_fsa_structure(fsa)
        if not validation['valid']:
            return JsonResponse({'error': validation['error']}, status=400)

        # Check determinism
        deterministic = is_deterministic(fsa)

        return JsonResponse({
            'deterministic': deterministic,
            'type': 'DFA' if deterministic else 'NFA'
        })

    except ValueError as e:
        return JsonResponse({'error': str(e)}, status=400)
    except Exception as e:
        return JsonResponse({'error': f'Server error: {str(e)}'}, status=500)


@csrf_exempt
@require_POST
def check_complete(request):
    """
    Django view to check if an FSA is complete.

    Expects a POST request with a JSON body containing:
    - fsa: The FSA definition in the proper format

    Returns a JSON response with completeness check result.
    """
    try:
        # Parse the request body
        data = json.loads(request.body)
        fsa = data.get('fsa')

        if not fsa:
            return JsonResponse({'error': 'Missing FSA definition'}, status=400)

        # Validate FSA structure
        validation = validate_fsa_structure(fsa)
        if not validation['valid']:
            return JsonResponse({'error': validation['error']}, status=400)

        # Check completeness
        complete = is_complete(fsa)

        return JsonResponse({
            'complete': complete
        })

    except ValueError as e:
        return JsonResponse({'error': str(e)}, status=400)
    except Exception as e:
        return JsonResponse({'error': f'Server error: {str(e)}'}, status=500)


@csrf_exempt
@require_POST
def check_connected(request):
    """
    Django view to check if an FSA is connected.

    Expects a POST request with a JSON body containing:
    - fsa: The FSA definition in the proper format

    Returns a JSON response with connectivity check result.
    """
    try:
        # Parse the request body
        data = json.loads(request.body)
        fsa = data.get('fsa')

        if not fsa:
            return JsonResponse({'error': 'Missing FSA definition'}, status=400)

        # Validate FSA structure
        validation = validate_fsa_structure(fsa)
        if not validation['valid']:
            return JsonResponse({'error': validation['error']}, status=400)

        # Check connectivity
        connected = is_connected(fsa)

        return JsonResponse({
            'connected': connected
        })

    except ValueError as e:
        return JsonResponse({'error': str(e)}, status=400)
    except Exception as e:
        return JsonResponse({'error': f'Server error: {str(e)}'}, status=500)

@csrf_exempt
@require_POST
def min_dfa(request):
    """
    Django view to handle DFA minimisation requests.

    Expects a POST request with a JSON body containing:
    - fsa: The FSA definition in the proper format (must be deterministic)

    Returns a JSON response with the minimised DFA.
    """
    try:
        # Parse the request body
        data = json.loads(request.body)
        fsa = data.get('fsa')

        if not fsa:
            return JsonResponse({'error': 'Missing FSA definition'}, status=400)

        # Validate FSA structure
        validation = validate_fsa_structure(fsa)
        if not validation['valid']:
            return JsonResponse({'error': validation['error']}, status=400)

        # Check if FSA is deterministic (required for minimisation)
        if not is_deterministic(fsa):
            return JsonResponse({
                'error': 'DFA minimisation requires a deterministic FSA. '
                        'The provided FSA is non-deterministic.'
            }, status=400)

        # Store original FSA statistics for comparison
        original_stats = {
            'states_count': len(fsa['states']),
            'alphabet_size': len(fsa['alphabet']),
            'transitions_count': sum(
                len(transitions) for state_transitions in fsa['transitions'].values()
                for transitions in state_transitions.values()
            ),
            'accepting_states_count': len(fsa['acceptingStates'])
        }

        # Minimise the DFA
        minimised_fsa = minimise_dfa(fsa)

        # Calculate minimised FSA statistics
        minimised_stats = {
            'states_count': len(minimised_fsa['states']),
            'alphabet_size': len(minimised_fsa['alphabet']),
            'transitions_count': sum(
                len(transitions) for state_transitions in minimised_fsa['transitions'].values()
                for transitions in state_transitions.values()
            ),
            'accepting_states_count': len(minimised_fsa['acceptingStates'])
        }

        # Calculate reduction statistics
        reduction_stats = {
            'states_reduced': original_stats['states_count'] - minimised_stats['states_count'],
            'states_reduction_percentage': round(
                ((original_stats['states_count'] - minimised_stats['states_count']) /
                 original_stats['states_count']) * 100, 2
            ) if original_stats['states_count'] > 0 else 0,
            'transitions_reduced': original_stats['transitions_count'] - minimised_stats['transitions_count'],
            'transitions_reduction_percentage': round(
                ((original_stats['transitions_count'] - minimised_stats['transitions_count']) /
                 original_stats['transitions_count']) * 100, 2
            ) if original_stats['transitions_count'] > 0 else 0,
            'is_already_minimal': original_stats['states_count'] == minimised_stats['states_count']
        }

        return JsonResponse({
            'success': True,
            'original_fsa': fsa,
            'minimised_fsa': minimised_fsa,
            'statistics': {
                'original': original_stats,
                'minimised': minimised_stats,
                'reduction': reduction_stats
            },
            'message': 'DFA minimised successfully' if not reduction_stats['is_already_minimal']
                      else 'DFA was already minimal'
        })

    except ValueError as e:
        return JsonResponse({'error': str(e)}, status=400)
    except Exception as e:
        return JsonResponse({'error': f'Server error: {str(e)}'}, status=500)


@csrf_exempt
@require_POST
def convert_nfa_to_dfa(request):
    """
    Django view to handle NFA to DFA conversion requests.

    Expects a POST request with a JSON body containing:
    - fsa: The FSA definition in the proper format (can be deterministic or non-deterministic)

    Returns a JSON response with the converted DFA.
    """
    try:
        # Parse the request body
        data = json.loads(request.body)
        fsa = data.get('fsa')

        if not fsa:
            return JsonResponse({'error': 'Missing FSA definition'}, status=400)

        # Validate FSA structure
        validation = validate_fsa_structure(fsa)
        if not validation['valid']:
            return JsonResponse({'error': validation['error']}, status=400)

        # Store original FSA statistics for comparison
        original_stats = {
            'states_count': len(fsa['states']),
            'alphabet_size': len(fsa['alphabet']),
            'transitions_count': sum(
                len(transitions) for state_transitions in fsa['transitions'].values()
                for transitions in state_transitions.values()
            ),
            'accepting_states_count': len(fsa['acceptingStates']),
            'has_epsilon_transitions': any(
                '' in fsa['transitions'].get(state, {}) and fsa['transitions'][state]['']
                for state in fsa['states']
            ),
            'is_deterministic': is_deterministic(fsa)
        }

        # Convert the NFA to DFA
        converted_dfa = nfa_to_dfa(fsa)

        # Calculate converted DFA statistics
        converted_stats = {
            'states_count': len(converted_dfa['states']),
            'alphabet_size': len(converted_dfa['alphabet']),
            'transitions_count': sum(
                len(transitions) for state_transitions in converted_dfa['transitions'].values()
                for transitions in state_transitions.values()
            ),
            'accepting_states_count': len(converted_dfa['acceptingStates']),
            'has_epsilon_transitions': False,  # DFAs don't have epsilon transitions
            'is_deterministic': True  # Result is always deterministic
        }

        # Calculate conversion statistics
        conversion_stats = {
            'states_added': converted_stats['states_count'] - original_stats['states_count'],
            'states_change_percentage': round(
                ((converted_stats['states_count'] - original_stats['states_count']) /
                 original_stats['states_count']) * 100, 2
            ) if original_stats['states_count'] > 0 else 0,
            'transitions_added': converted_stats['transitions_count'] - original_stats['transitions_count'],
            'transitions_change_percentage': round(
                ((converted_stats['transitions_count'] - original_stats['transitions_count']) /
                 original_stats['transitions_count']) * 100, 2
            ) if original_stats['transitions_count'] > 0 else 0,
            'epsilon_transitions_removed': original_stats['has_epsilon_transitions'],
            'was_already_deterministic': original_stats['is_deterministic']
        }

        # Determine appropriate message
        if original_stats['is_deterministic'] and not original_stats['has_epsilon_transitions']:
            message = 'Input was already a DFA, returned equivalent DFA'
        elif original_stats['is_deterministic'] and original_stats['has_epsilon_transitions']:
            message = 'Input was deterministic but had epsilon transitions, converted to proper DFA'
        else:
            message = 'NFA successfully converted to DFA'

        return JsonResponse({
            'success': True,
            'original_fsa': fsa,
            'converted_dfa': converted_dfa,
            'statistics': {
                'original': original_stats,
                'converted': converted_stats,
                'conversion': conversion_stats
            },
            'message': message
        })

    except ValueError as e:
        return JsonResponse({'error': str(e)}, status=400)
    except Exception as e:
        return JsonResponse({'error': f'Server error: {str(e)}'}, status=500)

@csrf_exempt
@require_POST
def dfa_to_complete(request):
    """
    Django view to handle DFA completion requests.

    Expects a POST request with a JSON body containing:
    - fsa: The FSA definition in the proper format (must be deterministic)

    Returns a JSON response with the completed DFA.
    """
    try:
        # Parse the request body
        data = json.loads(request.body)
        fsa = data.get('fsa')

        if not fsa:
            return JsonResponse({'error': 'Missing FSA definition'}, status=400)

        # Validate FSA structure
        validation = validate_fsa_structure(fsa)
        if not validation['valid']:
            return JsonResponse({'error': validation['error']}, status=400)

        # Check if FSA is deterministic (required for completion)
        if not is_deterministic(fsa):
            return JsonResponse({
                'error': 'DFA completion requires a deterministic FSA. '
                        'The provided FSA is non-deterministic.'
            }, status=400)

        # Store original FSA statistics for comparison
        original_stats = {
            'states_count': len(fsa['states']),
            'alphabet_size': len(fsa['alphabet']),
            'transitions_count': sum(
                len(transitions) for state_transitions in fsa['transitions'].values()
                for transitions in state_transitions.values()
            ),
            'accepting_states_count': len(fsa['acceptingStates']),
            'is_complete': is_complete(fsa)
        }

        # Complete the DFA
        completed_fsa = complete_dfa(fsa)

        # Calculate completed FSA statistics
        completed_stats = {
            'states_count': len(completed_fsa['states']),
            'alphabet_size': len(completed_fsa['alphabet']),
            'transitions_count': sum(
                len(transitions) for state_transitions in completed_fsa['transitions'].values()
                for transitions in state_transitions.values()
            ),
            'accepting_states_count': len(completed_fsa['acceptingStates']),
            'is_complete': True  # Result is always complete
        }

        # Calculate completion statistics
        completion_stats = {
            'states_added': completed_stats['states_count'] - original_stats['states_count'],
            'transitions_added': completed_stats['transitions_count'] - original_stats['transitions_count'],
            'dead_state_added': completed_stats['states_count'] > original_stats['states_count'],
            'was_already_complete': original_stats['is_complete']
        }

        # Determine appropriate message
        message = ('DFA was already complete, no changes needed' if original_stats['is_complete']
                  else f'DFA completed successfully by adding {completion_stats["states_added"]} dead state(s) '
                       f'and {completion_stats["transitions_added"]} transition(s)')

        return JsonResponse({
            'success': True,
            'original_fsa': fsa,
            'completed_fsa': completed_fsa,
            'statistics': {
                'original': original_stats,
                'completed': completed_stats,
                'completion': completion_stats
            },
            'message': message
        })

    except ValueError as e:
        return JsonResponse({'error': str(e)}, status=400)
    except Exception as e:
        return JsonResponse({'error': f'Server error: {str(e)}'}, status=500)


@csrf_exempt
@require_POST
def dfa_to_complement(request):
    """
    Django view to handle DFA complement requests.

    Expects a POST request with a JSON body containing:
    - fsa: The FSA definition in the proper format (must be deterministic)

    Returns a JSON response with the complement DFA.
    """
    try:
        # Parse the request body
        data = json.loads(request.body)
        fsa = data.get('fsa')

        if not fsa:
            return JsonResponse({'error': 'Missing FSA definition'}, status=400)

        # Validate FSA structure
        validation = validate_fsa_structure(fsa)
        if not validation['valid']:
            return JsonResponse({'error': validation['error']}, status=400)

        # Check if FSA is deterministic (required for complement)
        if not is_deterministic(fsa):
            return JsonResponse({
                'error': 'DFA complement requires a deterministic FSA. '
                        'The provided FSA is non-deterministic.'
            }, status=400)

        # Store original FSA statistics for comparison
        original_stats = {
            'states_count': len(fsa['states']),
            'alphabet_size': len(fsa['alphabet']),
            'transitions_count': sum(
                len(transitions) for state_transitions in fsa['transitions'].values()
                for transitions in state_transitions.values()
            ),
            'accepting_states_count': len(fsa['acceptingStates']),
            'non_accepting_states_count': len(fsa['states']) - len(fsa['acceptingStates']),
            'is_complete': is_complete(fsa)
        }

        # Get the complement DFA
        complement_fsa = complement_dfa(fsa)

        # Calculate complement FSA statistics
        complement_stats = {
            'states_count': len(complement_fsa['states']),
            'alphabet_size': len(complement_fsa['alphabet']),
            'transitions_count': sum(
                len(transitions) for state_transitions in complement_fsa['transitions'].values()
                for transitions in state_transitions.values()
            ),
            'accepting_states_count': len(complement_fsa['acceptingStates']),
            'non_accepting_states_count': len(complement_fsa['states']) - len(complement_fsa['acceptingStates']),
            'is_complete': True  # Complement always ensures completeness
        }

        # Calculate complement statistics
        complement_analysis = {
            'states_added_for_completeness': complement_stats['states_count'] - original_stats['states_count'],
            'accepting_states_flipped': True,
            'original_accepting_became_non_accepting': original_stats['accepting_states_count'],
            'original_non_accepting_became_accepting': original_stats['non_accepting_states_count'],
            'completion_required': not original_stats['is_complete']
        }

        # Determine appropriate message
        completion_message = (f' (completion required: added {complement_analysis["states_added_for_completeness"]} dead state(s))'
                             if complement_analysis['completion_required'] else '')
        message = f'DFA complement computed successfully. {original_stats["accepting_states_count"]} accepting states became non-accepting, ' \
                 f'{original_stats["non_accepting_states_count"]} non-accepting states became accepting{completion_message}'

        return JsonResponse({
            'success': True,
            'original_fsa': fsa,
            'complement_fsa': complement_fsa,
            'statistics': {
                'original': original_stats,
                'complement': complement_stats,
                'analysis': complement_analysis
            },
            'message': message
        })

    except ValueError as e:
        return JsonResponse({'error': str(e)}, status=400)
    except Exception as e:
        return JsonResponse({'error': f'Server error: {str(e)}'}, status=500)


@csrf_exempt
@require_POST
def regex_to_epsilon_nfa(request):
    """
    Django view to handle **regex → ε‑NFA** conversion requests.

    Expects a POST request with a JSON body containing:
    - regex: The regular expression to convert.

    Returns a JSON response with the generated NFA plus some useful
    statistics so the client can display summary information.
    """
    try:
        # Parse request body
        data = json.loads(request.body)
        regex = data.get('regex')

        if regex is None:
            return JsonResponse({'error': 'Missing regex parameter'}, status=400)

        # Validate regex syntax before attempting conversion
        from .regex_conversions import validate_regex_syntax
        validation_result = validate_regex_syntax(regex)
        if not validation_result['valid']:
            return JsonResponse({
                'error': f'Invalid regex syntax: {validation_result["error"]}'
            }, status=400)

        # Perform the conversion
        from .regex_conversions import regex_to_epsilon_nfa
        epsilon_nfa = regex_to_epsilon_nfa(regex)

        # Collect simple stats for the response payload
        stats = {
            'states_count': len(epsilon_nfa['states']),
            'alphabet_size': len(epsilon_nfa['alphabet']),
            'transitions_count': sum(
                len(transitions)
                for state_transitions in epsilon_nfa['transitions'].values()
                for transitions in state_transitions.values()
            ),
            'accepting_states_count': len(epsilon_nfa['acceptingStates'])
        }

        return JsonResponse({
            'success': True,
            'regex': regex,
            'epsilon_nfa': epsilon_nfa,
            'statistics': stats,
            'message': 'Regex converted to ε‑NFA successfully'
        })

    except ValueError as e:
        # Validation / parsing error in the regex
        return JsonResponse({'error': str(e)}, status=400)
    except Exception as e:
        # Unexpected server‑side error
        return JsonResponse({'error': f'Server error: {str(e)}'}, status=500)
