from django.urls import path
from . import views

urlpatterns = [
    # Main page
    path('', views.index, name='index'),

    # Auto-detect FSA type and simulate accordingly
    path('api/simulate-fsa/', views.simulate_fsa, name='simulate_fsa'),

    # Specific FSA type simulators
    path('api/simulate-dfa/', views.simulate_dfa, name='simulate_dfa'),
    path('api/simulate-nfa/', views.simulate_nfa, name='simulate_nfa'),
    path('api/simulate-nfa-stream/', views.simulate_nfa_stream, name='simulate_nfa_stream'),

    # Utility endpoint to check FSA type
    path('api/check-fsa-type/', views.check_fsa_type, name='check_fsa_type'),

    # Utility endpoint to check if NFA has epsilon loops
    path('api/check-epsilon-loops/', views.check_epsilon_loops, name='check_epsilon_loops'),

    # Depth-limited NFA simulators
    path('api/simulate-nfa-depth-limit/', views.simulate_nfa_with_depth_limit, name='simulate_nfa_depth_limit'),
    path('api/simulate-nfa-stream-depth-limit/', views.simulate_nfa_stream_with_depth_limit, name='simulate_nfa_stream_depth_limit'),

    # Property checking endpoints
    path('api/check-fsa-properties/', views.check_fsa_properties, name='check_fsa_properties'),
    path('api/check-deterministic/', views.check_deterministic, name='check_deterministic'),
    path('api/check-complete/', views.check_complete, name='check_complete'),
    path('api/check-connected/', views.check_connected, name='check_connected'),

    # FSA Transformation endpoints
    path('api/minimise-dfa/', views.min_dfa, name='minimise_dfa'),
    path('api/nfa-to-dfa/', views.convert_nfa_to_dfa, name='nfa_to_dfa'),
    path('api/complete-dfa/', views.dfa_to_complete, name='complete_dfa'),
    path('api/complement-dfa/', views.dfa_to_complement, name='complement_dfa'),
    path('api/minimise-nfa/', views.min_nfa, name='minimise_nfa'),

    # REGEX conversion endpoints
    path('api/regex-to-epsilon-nfa/', views.regex_to_epsilon_nfa, name='regex_to_epsilon_nfa'),
    path('api/fsa-to-regex/', views.fsa_to_regex, name='fsa_to_regex'),

    # Utility endpoint to check if two FSA are equivalent
    path('api/check-fsa-equivalence/', views.check_fsa_equivalence, name='check_fsa_equivalence'),

    # Utility endpoint to check if two REGEX are equivalent
    path('api/check-regex-equivalence/', views.check_regex_equivalence, name='check_regex_equivalence'),

    # Utility endpoint to check if an FSA and a REGEX are equivalent
    path('api/check-fsa-regex-equivalence/', views.check_fsa_regex_equivalence, name='check_fsa_regex_equivalence'),
]