import time
import logging
from fastapi import Request

# Set up basic logging configuration
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("spam_detection_logger")

async def log_requests_middleware(request: Request, call_next):
    # 1. Capture request start time and details
    start_time = time.time()
    method = request.method
    url = request.url.path
    client_host = request.client.host if request.client else "unknown"
    
    logger.info(f"Incoming request: {method} {url} from {client_host}")

    # 2. Process the request and get the response from the application
    response = await call_next(request)

    # 3. Calculate processing time and log completion details
    process_time = (time.time() - start_time) * 1000  # in milliseconds
    status_code = response.status_code
    
    logger.info(f"Completed request: {method} {url} | Status: {status_code} | Duration: {process_time:.2f}ms")
    
    # 4. Add a custom header to the response (Good practice for tracking)
    response.headers["X-Process-Time"] = f"{process_time:.2f}ms"
    
    return response