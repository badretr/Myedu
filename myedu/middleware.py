from django.http import HttpResponse


class CanonicalHostMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.get_host().split(':')[0] == 'localhost':
            port = request.get_port()
            canonical_host = '127.0.0.1'
            if port:
                canonical_host = f'{canonical_host}:{port}'
            response = HttpResponse(status=308)
            response['Location'] = f'{request.scheme}://{canonical_host}{request.get_full_path()}'
            return response

        return self.get_response(request)
