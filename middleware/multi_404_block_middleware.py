import logging

from MerchManagerV1 import settings

logger = logging.getLogger(__name__)

from django.http import HttpResponse
from django.utils.deprecation import MiddlewareMixin
import redis
import os

BLOCKED_STATUS_CODES = [400, 401, 403, 404]

class IPBlockMiddleware(MiddlewareMixin):
    def __init__(self, get_response=None):
        self.get_response = get_response
        self.redis = redis.from_url(os.environ['REDIS_URL'], ssl=True, db=0)
        self.threshold = getattr(settings, 'IP_BLOCK_THRESHOLD', 10)
        self.expire_time = getattr(settings, 'IP_BLOCK_EXPIRE', 600)

    def process_response(self, request, response):
        if response.status_code in BLOCKED_STATUS_CODES:
            ip = request.META.get('REMOTE_ADDR')
            count_key = f"{ip}_{response.status_code}"
            count = self.redis.incr(count_key)
            self.redis.expire(count_key, 600)
            logger.info(f"Request from IP {ip} resulted in {response.status_code}")
            if count > self.threshold:
                logger.error(f"IP {ip} has been blocked after exceeding threshold. Count: {count}")

                return HttpResponse("Access Denied", status=403)
        return self.get_response(request)

