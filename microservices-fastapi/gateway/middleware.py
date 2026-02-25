from fastapi import Request
import time
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def logging_middleware(request: Request, call_next):
    """Log all requests and responses"""
    start_time = time.time()
    
    # Log request
    logger.info(f"Request: {request.method} {request.url.path}")
    logger.info(f"Client: {request.client.host if request.client else 'Unknown'}")
    
    # Process request
    try:
        response = await call_next(request)
        
        # Log response
        process_time = time.time() - start_time
        logger.info(f"Response: {response.status_code} - Time: {process_time:.3f}s")
        
        # Add processing time header
        response.headers["X-Process-Time"] = str(process_time)
        
        return response
        
    except Exception as e:
        # Log errors
        process_time = time.time() - start_time
        logger.error(f"Error: {str(e)} - Time: {process_time:.3f}s")
        raise