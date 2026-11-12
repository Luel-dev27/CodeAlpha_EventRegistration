import logging

from rest_framework.exceptions import APIException
from rest_framework.pagination import PageNumberPagination
from rest_framework.views import exception_handler as drf_exception_handler
from rest_framework.response import Response

logger = logging.getLogger(__name__)


class Conflict(APIException):
    status_code = 409
    default_detail = "The requested operation conflicts with the current event state."
    default_code = "conflict"


def exception_handler(exc, context):
    response = drf_exception_handler(exc, context)
    if response is not None:
        return response
    # Deliberately do not log request bodies, headers, credentials, or DB exception text.
    logger.error(
        "Unhandled API failure in %s (%s)",
        type(context.get("view")).__name__,
        type(exc).__name__,
    )
    return Response(
        {"detail": "An unexpected server error occurred. Please try again."}, status=500
    )


class OptionalPagination(PageNumberPagination):
    """Keep legacy array responses; explicit page/page_size enables pagination."""

    page_size = 12
    page_size_query_param = "page_size"
    max_page_size = 100

    def paginate_queryset(self, queryset, request, view=None):
        if (
            "page" not in request.query_params
            and "page_size" not in request.query_params
        ):
            return None
        return super().paginate_queryset(queryset, request, view)


class NoStoreAPIMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if request.path.startswith("/api/"):
            response["Cache-Control"] = "no-store"
        return response
