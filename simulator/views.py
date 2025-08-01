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
from .minimise_nfa import minimise_nfa

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

@csrf_exempt
@require_POST
def min_nfa(request):
    """
    Django view to handle NFA minimisation requests.

    Expects a POST request with a JSON body containing:
    - fsa: The FSA definition in the proper format (can be deterministic or non-deterministic)

    Returns a JSON response with the minimised (not necessarily optimal) NFA.
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

        # Minimise the NFA
        minimisation_result = minimise_nfa(fsa)
        minimised_fsa = minimisation_result.nfa

        # Calculate minimised FSA statistics
        minimised_stats = {
            'states_count': len(minimised_fsa['states']),
            'alphabet_size': len(minimised_fsa['alphabet']),
            'transitions_count': sum(
                len(transitions) for state_transitions in minimised_fsa['transitions'].values()
                for transitions in state_transitions.values()
            ),
            'accepting_states_count': len(minimised_fsa['acceptingStates']),
            'has_epsilon_transitions': any(
                '' in minimised_fsa['transitions'].get(state, {}) and minimised_fsa['transitions'][state]['']
                for state in minimised_fsa['states']
            ),
            'is_deterministic': is_deterministic(minimised_fsa)
        }

        # Calculate reduction statistics
        reduction_stats = {
            'states_reduced': minimisation_result.reduction,
            'states_reduction_percentage': round(minimisation_result.reduction_percent, 2),
            'transitions_reduced': original_stats['transitions_count'] - minimised_stats['transitions_count'],
            'transitions_reduction_percentage': round(
                ((original_stats['transitions_count'] - minimised_stats['transitions_count']) /
                 original_stats['transitions_count']) * 100, 2
            ) if original_stats['transitions_count'] > 0 else 0,
            'is_already_minimal': minimisation_result.reduction == 0
        }

        # Build response message
        if reduction_stats['is_already_minimal']:
            message = 'NFA was already minimal'
        else:
            message = f'NFA minimised successfully using {minimisation_result.method_used}'
            if minimisation_result.is_optimal:
                message += ' (optimal result)'
            else:
                message += ' (heuristic result)'

        return JsonResponse({
            'success': True,
            'original_fsa': fsa,
            'minimised_fsa': minimised_fsa,
            'statistics': {
                'original': original_stats,
                'minimised': minimised_stats,
                'reduction': reduction_stats
            },
            'minimisation_details': {
                'method_used': minimisation_result.method_used,
                'is_optimal': minimisation_result.is_optimal,
                'stages': minimisation_result.stages,
                'original_states': minimisation_result.original_states,
                'final_states': minimisation_result.final_states
            },
            'message': message
        })

    except ValueError as e:
        return JsonResponse({'error': str(e)}, status=400)
    except Exception as e:
        return JsonResponse({'error': f'Server error: {str(e)}'}, status=500)


@csrf_exempt
@require_POST
def check_fsa_equivalence(request):
    """
    Django view to check if two FSAs are language-equivalent.

    Expects a POST request with a JSON body containing:
    - fsa1: First FSA definition in the proper format
    - fsa2: Second FSA definition in the proper format

    Returns a JSON response with equivalence check results.
    """
    try:
        # Parse the request body
        data = json.loads(request.body)
        fsa1 = data.get('fsa1')
        fsa2 = data.get('fsa2')

        if not fsa1:
            return JsonResponse({'error': 'Missing fsa1 definition'}, status=400)

        if not fsa2:
            return JsonResponse({'error': 'Missing fsa2 definition'}, status=400)

        # Validate both FSA structures
        validation1 = validate_fsa_structure(fsa1)
        if not validation1['valid']:
            return JsonResponse({
                'error': f'Invalid fsa1 structure: {validation1["error"]}'
            }, status=400)

        validation2 = validate_fsa_structure(fsa2)
        if not validation2['valid']:
            return JsonResponse({
                'error': f'Invalid fsa2 structure: {validation2["error"]}'
            }, status=400)

        # Import the equivalence checking function
        from .fsa_equivalence import are_automata_equivalent

        # Check equivalence
        is_equivalent, details = are_automata_equivalent(fsa1, fsa2)

        # Calculate statistics for both FSAs
        fsa1_stats = {
            'states_count': len(fsa1['states']),
            'alphabet_size': len(fsa1['alphabet']),
            'transitions_count': sum(
                len(transitions) for state_transitions in fsa1['transitions'].values()
                for transitions in state_transitions.values()
            ),
            'accepting_states_count': len(fsa1['acceptingStates']),
            'has_epsilon_transitions': any(
                '' in fsa1['transitions'].get(state, {}) and fsa1['transitions'][state]['']
                for state in fsa1['states']
            ),
            'is_deterministic': is_deterministic(fsa1)
        }

        fsa2_stats = {
            'states_count': len(fsa2['states']),
            'alphabet_size': len(fsa2['alphabet']),
            'transitions_count': sum(
                len(transitions) for state_transitions in fsa2['transitions'].values()
                for transitions in state_transitions.values()
            ),
            'accepting_states_count': len(fsa2['acceptingStates']),
            'has_epsilon_transitions': any(
                '' in fsa2['transitions'].get(state, {}) and fsa2['transitions'][state]['']
                for state in fsa2['states']
            ),
            'is_deterministic': is_deterministic(fsa2)
        }

        # Build response
        response_data = {
            'equivalent': is_equivalent,
            'fsa1_stats': fsa1_stats,
            'fsa2_stats': fsa2_stats,
            'comparison_details': details
        }

        # Add helpful analysis
        analysis = {
            'both_deterministic': fsa1_stats['is_deterministic'] and fsa2_stats['is_deterministic'],
            'both_nondeterministic': not fsa1_stats['is_deterministic'] and not fsa2_stats['is_deterministic'],
            'mixed_types': fsa1_stats['is_deterministic'] != fsa2_stats['is_deterministic'],
            'same_alphabet': set(fsa1['alphabet']) == set(fsa2['alphabet']),
            'alphabet_compatible': set(fsa1['alphabet']).issubset(set(fsa2['alphabet'])) or set(
                fsa2['alphabet']).issubset(set(fsa1['alphabet']))
        }

        response_data['analysis'] = analysis

        # Generate appropriate message
        if is_equivalent:
            if 'state_mapping' in details:
                message = f'FSAs are equivalent. {details["reason"]}'
            else:
                message = f'FSAs are equivalent. {details["reason"]}'
        else:
            if 'error' in details:
                message = f'Equivalence check failed: {details["error"]}'
            else:
                message = f'FSAs are not equivalent. {details["reason"]}'

        response_data['message'] = message

        # Add minimal DFA information if available
        if 'minimal_dfa1_states' in details:
            response_data['minimal_dfa_info'] = {
                'fsa1_minimal_states': details['minimal_dfa1_states'],
                'fsa2_minimal_states': details['minimal_dfa2_states'],
                'fsa1_complete_states': details.get('complete_dfa1_states', 'N/A'),
                'fsa2_complete_states': details.get('complete_dfa2_states', 'N/A')
            }

        return JsonResponse(response_data)

    except ValueError as e:
        return JsonResponse({'error': str(e)}, status=400)
    except Exception as e:
        return JsonResponse({'error': f'Server error: {str(e)}'}, status=500)

@csrf_exempt
@require_POST
def fsa_to_regex(request):
    """
    Django view to handle FSA to regular expression conversion requests.

    Expects a POST request with a JSON body containing:
    - fsa: The FSA definition in the proper format (can be deterministic or non-deterministic)

    Returns a JSON response with the generated regular expression plus detailed
    statistics and verification results.
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

        from .regex_conversions import fsa_to_regex as convert_fsa_to_regex
        result = convert_fsa_to_regex(fsa)

        # Check if conversion was successful
        if not result['valid']:
            return JsonResponse({
                'error': f'FSA to regex conversion failed: {result["error"]}'
            }, status=400)

        # Calculate FSA statistics for the response
        fsa_stats = {
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

        # Prepare response data
        response_data = {
            'success': True,
            'fsa': fsa,
            'regex': result['regex'],
            'statistics': {
                'original_fsa': fsa_stats,
                'original_states': result['original_states'],
                'minimized_states': result['minimized_states'],
                'states_reduction': result['original_states'] - result['minimized_states'],
                'states_reduction_percentage': round(
                    ((result['original_states'] - result['minimized_states']) / result['original_states']) * 100, 2
                ) if result['original_states'] > 0 else 0
            },
            'verification': result['verification']
        }

        # Generate appropriate message
        if result['minimized_states'] == 0:
            message = 'FSA represents the empty language, converted to regex: ∅'
        elif result['original_states'] == 1:
            message = 'Single-state FSA converted to regex successfully'
        elif result['original_states'] == result['minimized_states']:
            message = 'FSA was already minimal, converted to regex successfully'
        else:
            message = f'FSA minimized from {result["original_states"]} to {result["minimized_states"]} states, then converted to regex successfully'

        # Add verification details to message
        if result['verification'].get('equivalent'):
            message += ' (verified equivalent)'
        elif 'error' in result['verification']:
            message += f' (verification failed: {result["verification"]["error"]})'
        else:
            message += ' (verification inconclusive)'

        response_data['message'] = message

        return JsonResponse(response_data)

    except ValueError as e:
        return JsonResponse({'error': str(e)}, status=400)
    except Exception as e:
        return JsonResponse({'error': f'Server error: {str(e)}'}, status=500)


@csrf_exempt
@require_POST
def check_regex_equivalence(request):
    """
    Django view to check if two regular expressions are equivalent.

    Expects a POST request with a JSON body containing:
    - regex1: First regular expression string
    - regex2: Second regular expression string

    Returns a JSON response with equivalence check results.
    """
    try:
        # Parse the request body
        data = json.loads(request.body)
        regex1 = data.get('regex1')
        regex2 = data.get('regex2')

        if regex1 is None:
            return JsonResponse({'error': 'Missing regex1 parameter'}, status=400)

        if regex2 is None:
            return JsonResponse({'error': 'Missing regex2 parameter'}, status=400)

        # Step 1: Validate both regex patterns
        from .regex_conversions import validate_regex_syntax
        validation1 = validate_regex_syntax(regex1)
        if not validation1['valid']:
            return JsonResponse({
                'error': f'Invalid regex1 syntax: {validation1["error"]}'
            }, status=400)

        validation2 = validate_regex_syntax(regex2)
        if not validation2['valid']:
            return JsonResponse({
                'error': f'Invalid regex2 syntax: {validation2["error"]}'
            }, status=400)

        # If both regexes are identical, they are equivalent, other checks aren't needed
        if regex1 == regex2:
            # Create minimal FSA stats for identical regexes
            from .regex_conversions import regex_to_epsilon_nfa
            fsa1 = regex_to_epsilon_nfa(regex1)

            fsa_stats = {
                'states_count': len(fsa1['states']),
                'alphabet_size': len(fsa1['alphabet']),
                'transitions_count': sum(
                    len(transitions) for state_transitions in fsa1['transitions'].values()
                    for transitions in state_transitions.values()
                ),
                'accepting_states_count': len(fsa1['acceptingStates']),
                'has_epsilon_transitions': any(
                    '' in fsa1['transitions'].get(state, {}) and fsa1['transitions'][state]['']
                    for state in fsa1['states']
                )
            }

            return JsonResponse({
                'equivalent': True,
                'regex1': regex1,
                'regex2': regex2,
                'fsa1_stats': fsa_stats,
                'fsa2_stats': fsa_stats,
                'fsa_equivalence_details': {'reason': 'Regexes are identical'},
                'analysis': {
                    'both_alphabets_same': True,
                    'alphabet_union': sorted(list(fsa1['alphabet'])),
                    'regex1_length': len(regex1),
                    'regex2_length': len(regex2),
                    'fsa1_complexity': fsa_stats['states_count'] * fsa_stats['alphabet_size'],
                    'fsa2_complexity': fsa_stats['states_count'] * fsa_stats['alphabet_size']
                },
                'message': f'Regular expressions are equivalent. {"Both regexes are empty." if regex1 == "" else "Regexes are identical."}',
                'generated_fsas': {
                    'fsa1': fsa1,
                    'fsa2': fsa1  # Same FSA since regexes are identical
                }
            })

        # Step 2: Convert both regex to FSAs
        from .regex_conversions import regex_to_epsilon_nfa
        try:
            fsa1 = regex_to_epsilon_nfa(regex1)
        except Exception as e:
            return JsonResponse({
                'error': f'Failed to convert regex1 to FSA: {str(e)}'
            }, status=400)

        try:
            fsa2 = regex_to_epsilon_nfa(regex2)
        except Exception as e:
            return JsonResponse({
                'error': f'Failed to convert regex2 to FSA: {str(e)}'
            }, status=400)

        # Step 3: Check equivalence of both FSAs
        from .fsa_equivalence import are_automata_equivalent
        is_equivalent, details = are_automata_equivalent(fsa1, fsa2)

        # Calculate statistics for both FSAs
        fsa1_stats = {
            'states_count': len(fsa1['states']),
            'alphabet_size': len(fsa1['alphabet']),
            'transitions_count': sum(
                len(transitions) for state_transitions in fsa1['transitions'].values()
                for transitions in state_transitions.values()
            ),
            'accepting_states_count': len(fsa1['acceptingStates']),
            'has_epsilon_transitions': any(
                '' in fsa1['transitions'].get(state, {}) and fsa1['transitions'][state]['']
                for state in fsa1['states']
            )
        }

        fsa2_stats = {
            'states_count': len(fsa2['states']),
            'alphabet_size': len(fsa2['alphabet']),
            'transitions_count': sum(
                len(transitions) for state_transitions in fsa2['transitions'].values()
                for transitions in state_transitions.values()
            ),
            'accepting_states_count': len(fsa2['acceptingStates']),
            'has_epsilon_transitions': any(
                '' in fsa2['transitions'].get(state, {}) and fsa2['transitions'][state]['']
                for state in fsa2['states']
            )
        }

        # Build response
        response_data = {
            'equivalent': is_equivalent,
            'regex1': regex1,
            'regex2': regex2,
            'fsa1_stats': fsa1_stats,
            'fsa2_stats': fsa2_stats,
            'fsa_equivalence_details': details
        }

        # Add analysis of the regex patterns
        analysis = {
            'both_alphabets_same': set(fsa1['alphabet']) == set(fsa2['alphabet']),
            'alphabet_union': sorted(list(set(fsa1['alphabet']) | set(fsa2['alphabet']))),
            'regex1_length': len(regex1),
            'regex2_length': len(regex2),
            'fsa1_complexity': fsa1_stats['states_count'] * fsa1_stats['alphabet_size'],
            'fsa2_complexity': fsa2_stats['states_count'] * fsa2_stats['alphabet_size']
        }

        response_data['analysis'] = analysis

        # Generate appropriate message
        if is_equivalent:
            message = f'Regular expressions are equivalent. {details.get("reason", "")}'
            if fsa1_stats['states_count'] != fsa2_stats['states_count']:
                message += f' (FSA1: {fsa1_stats["states_count"]} states, FSA2: {fsa2_stats["states_count"]} states)'
        else:
            if 'error' in details:
                message = f'Equivalence check failed: {details["error"]}'
            else:
                message = f'Regular expressions are not equivalent. {details.get("reason", "")}'

        response_data['message'] = message

        # Include the generated FSAs in the response for debugging/visualization
        response_data['generated_fsas'] = {
            'fsa1': fsa1,
            'fsa2': fsa2
        }

        # Add minimal DFA information if available
        if 'minimal_dfa1_states' in details:
            response_data['minimal_dfa_info'] = {
                'fsa1_minimal_states': details['minimal_dfa1_states'],
                'fsa2_minimal_states': details['minimal_dfa2_states'],
                'fsa1_complete_states': details.get('complete_dfa1_states', 'N/A'),
                'fsa2_complete_states': details.get('complete_dfa2_states', 'N/A')
            }

        return JsonResponse(response_data)

    except ValueError as e:
        return JsonResponse({'error': str(e)}, status=400)
    except Exception as e:
        return JsonResponse({'error': f'Server error: {str(e)}'}, status=500)

@csrf_exempt
@require_POST
def check_fsa_regex_equivalence(request):
    """
    Django view to check if an FSA and a regular expression are equivalent.

    Expects a POST request with a JSON body containing:
    - fsa: FSA definition in the proper format
    - regex: Regular expression string

    Returns a JSON response with equivalence check results.
    """
    try:
        # Parse the request body
        data = json.loads(request.body)
        fsa = data.get('fsa')
        regex = data.get('regex')

        if not fsa:
            return JsonResponse({'error': 'Missing fsa definition'}, status=400)

        if regex is None:
            return JsonResponse({'error': 'Missing regex parameter'}, status=400)

        # Validate FSA structure
        validation = validate_fsa_structure(fsa)
        if not validation['valid']:
            return JsonResponse({
                'error': f'Invalid FSA structure: {validation["error"]}'
            }, status=400)

        # Validate regex syntax
        from .regex_conversions import validate_regex_syntax
        regex_validation = validate_regex_syntax(regex)
        if not regex_validation['valid']:
            return JsonResponse({
                'error': f'Invalid regex syntax: {regex_validation["error"]}'
            }, status=400)

        # Convert regex to FSA
        from .regex_conversions import regex_to_epsilon_nfa
        try:
            regex_fsa = regex_to_epsilon_nfa(regex)
        except Exception as e:
            return JsonResponse({
                'error': f'Failed to convert regex to FSA: {str(e)}'
            }, status=400)

        # Check equivalence between the original FSA and the regex-derived FSA
        from .fsa_equivalence import are_automata_equivalent
        is_equivalent, details = are_automata_equivalent(fsa, regex_fsa)

        # Calculate statistics for both FSAs
        fsa_stats = {
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

        regex_fsa_stats = {
            'states_count': len(regex_fsa['states']),
            'alphabet_size': len(regex_fsa['alphabet']),
            'transitions_count': sum(
                len(transitions) for state_transitions in regex_fsa['transitions'].values()
                for transitions in state_transitions.values()
            ),
            'accepting_states_count': len(regex_fsa['acceptingStates']),
            'has_epsilon_transitions': any(
                '' in regex_fsa['transitions'].get(state, {}) and regex_fsa['transitions'][state]['']
                for state in regex_fsa['states']
            ),
            'is_deterministic': is_deterministic(regex_fsa)
        }

        # Build response
        response_data = {
            'equivalent': is_equivalent,
            'fsa': fsa,
            'regex': regex,
            'fsa_stats': fsa_stats,
            'regex_fsa_stats': regex_fsa_stats,
            'equivalence_details': details
        }

        # Add analysis comparing the FSA and regex-derived FSA
        analysis = {
            'both_alphabets_same': set(fsa['alphabet']) == set(regex_fsa['alphabet']),
            'alphabet_union': sorted(list(set(fsa['alphabet']) | set(regex_fsa['alphabet']))),
            'alphabet_intersection': sorted(list(set(fsa['alphabet']) & set(regex_fsa['alphabet']))),
            'fsa_complexity': fsa_stats['states_count'] * fsa_stats['alphabet_size'],
            'regex_fsa_complexity': regex_fsa_stats['states_count'] * regex_fsa_stats['alphabet_size'],
            'regex_length': len(regex),
            'both_deterministic': fsa_stats['is_deterministic'] and regex_fsa_stats['is_deterministic'],
            'both_nondeterministic': not fsa_stats['is_deterministic'] and not regex_fsa_stats['is_deterministic'],
            'mixed_types': fsa_stats['is_deterministic'] != regex_fsa_stats['is_deterministic']
        }

        response_data['analysis'] = analysis

        # Generate appropriate message
        if is_equivalent:
            message = f'FSA and regular expression are equivalent. {details.get("reason", "")}'
            if fsa_stats['states_count'] != regex_fsa_stats['states_count']:
                message += f' (Original FSA: {fsa_stats["states_count"]} states, Regex FSA: {regex_fsa_stats["states_count"]} states)'
        else:
            if 'error' in details:
                message = f'Equivalence check failed: {details["error"]}'
            else:
                message = f'FSA and regular expression are not equivalent. {details.get("reason", "")}'

        response_data['message'] = message

        # Include the regex-derived FSA in the response for debugging/visualization
        response_data['regex_derived_fsa'] = regex_fsa

        # Add minimal DFA information if available
        if 'minimal_dfa1_states' in details:
            response_data['minimal_dfa_info'] = {
                'original_fsa_minimal_states': details['minimal_dfa1_states'],
                'regex_fsa_minimal_states': details['minimal_dfa2_states'],
                'original_fsa_complete_states': details.get('complete_dfa1_states', 'N/A'),
                'regex_fsa_complete_states': details.get('complete_dfa2_states', 'N/A')
            }

        return JsonResponse(response_data)

    except ValueError as e:
        return JsonResponse({'error': str(e)}, status=400)
    except Exception as e:
        return JsonResponse({'error': f'Server error: {str(e)}'}, status=500)