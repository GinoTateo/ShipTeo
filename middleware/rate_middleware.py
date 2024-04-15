import time
from django.core.cache import cache
from django.http import HttpResponse


class RateLimitMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        ip = request.META.get('REMOTE_ADDR')  # Get client IP address
        ident = f"ratelimit_{ip}"
        allowed_requests = 10  # Number of requests
        period = 60  # Period in seconds

        if cache.get(ident):
            cache.incr(ident)
        else:
            cache.set(ident, 1, timeout=period)

        if cache.get(ident) > allowed_requests:
            return HttpResponse("Too many requests", status=429)

        response = self.get_response(request)
        return response
