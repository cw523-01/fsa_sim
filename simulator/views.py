from django.shortcuts import render
from django.http import JsonResponse, StreamingHttpResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
import json
from .fsa_simulation import (
    simulate_deterministic_fsa,
    simulate_nondeterministic_fsa,
    simulate_nondeterministic_fsa_generator,
    is_nondeterministic
)


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
        required_keys = ['states', 'alphabet', 'transitions', 'startingState', 'acceptingStates']
        missing_keys = [key for key in required_keys if key not in fsa]

        if missing_keys:
            return JsonResponse({
                'error': f'FSA definition is missing required keys: {", ".join(missing_keys)}'
            }, status=400)

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

        # Check if the required keys are present in the FSA
        required_keys = ['states', 'alphabet', 'transitions', 'startingState', 'acceptingStates']
        missing_keys = [key for key in required_keys if key not in fsa]

        if missing_keys:
            return JsonResponse({
                'error': f'FSA definition is missing required keys: {", ".join(missing_keys)}'
            }, status=400)

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
        required_keys = ['states', 'alphabet', 'transitions', 'startingState', 'acceptingStates']
        missing_keys = [key for key in required_keys if key not in fsa]

        if missing_keys:
            return JsonResponse({
                'error': f'FSA definition is missing required keys: {", ".join(missing_keys)}'
            }, status=400)

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

            return StreamingHttpResponse(error_generator(), content_type='text/event-stream')

        # Validate FSA structure
        required_keys = ['states', 'alphabet', 'transitions', 'startingState', 'acceptingStates']
        missing_keys = [key for key in required_keys if key not in fsa]

        if missing_keys:
            def error_generator():
                yield f"data: {json.dumps({'error': f'FSA definition is missing required keys: {', '.join(missing_keys)}'})}\n\n"

            return StreamingHttpResponse(error_generator(), content_type='text/event-stream')

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

        response = StreamingHttpResponse(result_generator(), content_type='text/event-stream')
        response['Cache-Control'] = 'no-cache'
        response['Connection'] = 'keep-alive'
        return response

    except ValueError as e:
        def error_generator():
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

        return StreamingHttpResponse(error_generator(), content_type='text/event-stream')
    except Exception as e:
        def error_generator():
            yield f"data: {json.dumps({'error': f'Server error: {str(e)}'})}\n\n"

        return StreamingHttpResponse(error_generator(), content_type='text/event-stream')


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
        required_keys = ['states', 'alphabet', 'transitions', 'startingState', 'acceptingStates']
        missing_keys = [key for key in required_keys if key not in fsa]

        if missing_keys:
            return JsonResponse({
                'error': f'FSA definition is missing required keys: {", ".join(missing_keys)}'
            }, status=400)

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