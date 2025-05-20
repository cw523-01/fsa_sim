from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('api/simulate-fsa/', views.simulate_fsa, name='simulate_fsa'),
]