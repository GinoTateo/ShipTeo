from django.http import HttpResponseForbidden
import geoip2.database


class BlockNonLocalIPMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        self.reader = geoip2.database.Reader('middleware/support/GeoLite2-Country_20240412/GeoLite2-Country.mmdb')

    def __call__(self, request):
        ip_address = request.META.get('REMOTE_ADDR')
        try:
            response = self.reader.country(ip_address)
            if response.country.iso_code != 'US':
                return HttpResponseForbidden("Access Denied")
        except geoip2.errors.AddressNotFoundError:
            pass

        response = self.get_response(request)
        return response

    def close(self):
        self.reader.close()

