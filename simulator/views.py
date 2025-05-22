from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
import json
from .fsa_simulation import simulate_deterministic_fsa
# Create your views here.

def index(request):
    return render(request, 'simulator/index.html')


@csrf_exempt
@require_POST
def simulate_fsa(request):
    """
    Django view to handle FSA simulation requests.

    Expects a POST request with a JSON body containing:
    - fsa: The FSA definition in the proper format
      {
        'states': List of state IDs
        'alphabet': List of symbols
        'transitions': Dictionary mapping states to symbol-target pairs
        'startingState': Starting state ID
        'acceptingStates': List of accepting state IDs
      }
    - input: The input string to simulate

    Returns a JSON response with:
    - accepted: Boolean indicating if the input is accepted
    - path: The execution path if accepted, or path up to rejection if rejected
    - rejection_reason: Reason for rejection (only for rejected inputs)
    - rejection_position: Position where rejection occurred (only for rejected inputs)
    - error: Error message if any
    """
    try:
        # Parse the request body
        data = json.loads(request.body)

        # Extract FSA and input
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

        # Simulate the FSA
        result = simulate_deterministic_fsa(fsa, input_string)

        # Handle both response formats from the updated function
        if isinstance(result, list):
            # Input was accepted - result is the execution path (backwards compatibility)
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
            # Fallback for unexpected result (shouldn't happen)
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