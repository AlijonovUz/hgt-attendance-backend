import threading

_thread_locals = threading.local()


def get_current_user():
    """Joriy HTTP so'rovdan (request) qaysi foydalanuvchi tizimga kirganini aniqlab beradi."""
    request = getattr(_thread_locals, "request", None)
    if request and hasattr(request, "user") and request.user.is_authenticated:
        return request.user
    return None


def get_current_ip():
    """Joriy HTTP so'rovni yuborayotgan qurilmaning IP manzilini topib beradi."""
    request = getattr(_thread_locals, "request", None)
    if not request:
        return None
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        return x_forwarded_for.split(",")[0]
    return request.META.get("REMOTE_ADDR")


class AuditMiddleware:
    """
    Foydalanuvchining har bir so'rovini Thread Locals'da (vaqtinchalik xotira) saqlab turadi.
    Buning natijasida Models va Signals o'zicha mustaqil ravishda User va IP manzilini 
    ko'ra oladi (DB da o'zgartirish qilishganda Audit Logga kim qilganini yozish uchun).
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        _thread_locals.request = request
        response = self.get_response(request)

        _thread_locals.request = None

        return response
