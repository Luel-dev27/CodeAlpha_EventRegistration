from rest_framework.throttling import AnonRateThrottle, UserRateThrottle


class LoginThrottle(AnonRateThrottle):
    scope = "login"

    def get_cache_key(self, request, view):
        return self.cache_format % {
            "scope": self.scope,
            "ident": self.get_ident(request),
        }


class SignupThrottle(LoginThrottle):
    scope = "signup"


class RegistrationThrottle(UserRateThrottle):
    scope = "registration"
