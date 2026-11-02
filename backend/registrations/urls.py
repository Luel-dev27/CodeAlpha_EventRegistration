from django.urls import path

from .views import RegistrationCancelView, RegistrationDetailView, RegistrationListCreateView

app_name = 'registrations'

urlpatterns = [
    path('', RegistrationListCreateView.as_view(), name='registration-list-create'),
    path('<int:pk>/', RegistrationDetailView.as_view(), name='registration-detail'),
    path('<int:pk>/cancel/', RegistrationCancelView.as_view(), name='registration-cancel'),
]
