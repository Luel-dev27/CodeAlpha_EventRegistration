from django.contrib import admin
from django.urls import include, path

from registrations.auth_views import LoginView, LogoutView, RegisterView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/auth/register/', RegisterView.as_view(), name='auth-register'),
    path('api/auth/login/', LoginView.as_view(), name='auth-login'),
    path('api/auth/logout/', LogoutView.as_view(), name='auth-logout'),
    path('api/events/', include('events.urls', namespace='events')),
    path('api/registrations/', include('registrations.urls', namespace='registrations')),
]
