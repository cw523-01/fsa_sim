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
    path('api/detect-epsilon-loops/', views.detect_epsilon_loops, name='detect_epsilon_loops'),
]