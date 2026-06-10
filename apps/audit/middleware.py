import threading

_thread_locals = threading.local()


def get_current_user():
    request = getattr(_thread_locals, "request", None)
    if request and hasattr(request, "user") and request.user.is_authenticated:
        return request.user
    return None


def get_current_ip():
    request = getattr(_thread_locals, "request", None)
    if not request:
        return None
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        return x_forwarded_for.split(",")[0]
    return request.META.get("REMOTE_ADDR")


class AuditMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        _thread_locals.request = request
        response = self.get_response(request)

        _thread_locals.request = None

        return response
