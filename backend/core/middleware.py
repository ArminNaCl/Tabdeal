import logging
import time

logger = logging.getLogger('accounts')

class RequestLoggingMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        start_time = time.time()

        method = request.method
        path = request.path
        remote_addr = request.META.get('REMOTE_ADDR')
        user_agent = request.META.get('HTTP_USER_AGENT', 'Unknown')

        request_body = None
        if request.method in ['POST', 'PUT', 'PATCH']:
            try:
                request_body = request.body.decode('utf-8')
            except Exception:
                request_body = "[Unable to decode request body]"

        logger.info(
            f"Incoming Request: Method={method}, Path={path}, IP={remote_addr}, UserAgent='{user_agent}'"
            f"{f', Body={request_body}' if request_body else ''}"
        )

        response = self.get_response(request)

        duration = time.time() - start_time
        status_code = response.status_code

        logger.info(
            f"Outgoing Response: Method={method}, Path={path}, Status={status_code}, Duration={duration:.4f}s"
        )

        return response