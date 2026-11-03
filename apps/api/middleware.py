import logging
from time import perf_counter


logger = logging.getLogger("api.requests")
API_PATHS = ("/register", "/login", "/documents", "/query", "/queries", "/api/schema/")


class ApiRequestLoggingMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if not any(
            request.path_info == path or request.path_info.startswith(f"{path}/")
            for path in API_PATHS
        ):
            return self.get_response(request)

        start_time = perf_counter()
        try:
            response = self.get_response(request)
        except Exception:
            duration_ms = (perf_counter() - start_time) * 1000
            logger.exception(
                "API request failed method=%s path=%s duration_ms=%.2f",
                request.method,
                request.path_info,
                duration_ms,
            )
            raise

        duration_ms = (perf_counter() - start_time) * 1000
        log = logger.warning if response.status_code >= 400 else logger.info
        log(
            "API request method=%s path=%s status=%s duration_ms=%.2f",
            request.method,
            request.path_info,
            response.status_code,
            duration_ms,
        )
        return response
