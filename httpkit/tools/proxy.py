"""HTTP proxy module for httpkit.

This module provides a simple HTTP proxy service that forwards requests to a target server.
"""

import httpx
from fastapi import FastAPI, Request, Response, HTTPException
from fastapi.responses import StreamingResponse
import uvicorn
from typing import List, Dict, Any, Optional
import asyncio
from contextlib import asynccontextmanager

# Global httpx client
http_client: Optional[httpx.AsyncClient] = None

# Global concurrency limiter
# Default to 100 concurrent requests, can be adjusted based on system resources
MAX_CONCURRENT_REQUESTS = 100
request_semaphore: Optional[asyncio.Semaphore] = None

# List of hop-by-hop headers that should not be forwarded
HOP_BY_HOP_HEADERS = [
    "connection",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "te",
    "trailers",
    "transfer-encoding",
    "upgrade",
    "host",
]

# Additional headers that should not be forwarded from the response
UNSAFE_RESPONSE_HEADERS = [
    "content-length",  # Will be handled by the streaming response
    "content-encoding",  # Let FastAPI handle this
    "transfer-encoding",  # Let FastAPI handle this
    "connection",
    "server",  # Don't expose upstream server details
]

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for FastAPI app."""
    # Initialize resources on startup
    await startup_event()
    yield
    # Clean up resources on shutdown
    await shutdown_event()

# Create FastAPI app with lifespan
app = FastAPI(
    title="HTTPKit Proxy",
    description="A simple HTTP proxy service that forwards requests to a target server.",
    version="0.1.0",
    lifespan=lifespan,
)

# Keep the on_event handlers for backward compatibility and tests
@app.on_event("startup")
async def startup_event():
    """Initialize global resources on application startup."""
    global http_client, request_semaphore
    
    # Initialize the global HTTP client with HTTP/2 support and increased limits
    http_client = httpx.AsyncClient(
        timeout=30.0,
        # Only enable HTTP/2 if h2 package is installed
        http2=False,  # Changed to False by default to avoid dependency issues
        limits=httpx.Limits(
            max_connections=200,
            max_keepalive_connections=50,
            keepalive_expiry=30.0
        )
    )
    
    # Initialize the request semaphore
    request_semaphore = asyncio.Semaphore(MAX_CONCURRENT_REQUESTS)

@app.on_event("shutdown")
async def shutdown_event():
    """Clean up resources on application shutdown."""
    global http_client
    if http_client:
        await http_client.aclose()


@app.api_route(
    "/proxy/{target_host}:{target_port}/{path:path}",
    methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
)
async def proxy_request(
    request: Request,
    target_host: str,
    target_port: int,
    path: str,
    scheme: str = "http",
):
    """
    Forward the incoming request to the target server and return the response.

    Args:
        request: The incoming request.
        target_host: The host of the target server.
        target_port: The port of the target server.
        path: The path to forward the request to.
        scheme: The scheme to use (http or https). Defaults to http.

    Returns:
        The response from the target server.
    """
    # Use the global client and semaphore
    global http_client, request_semaphore
    
    # Validate scheme
    if scheme.lower() not in ["http", "https"]:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid scheme: {scheme}. Only http and https are supported.",
        )
    
    # Construct the target URL
    target_url = f"{scheme}://{target_host}:{target_port}/{path}"
    if request.query_params:
        query_string = str(request.query_params)
        target_url = f"{target_url}?{query_string}"

    # Get request headers, filtering out hop-by-hop headers
    headers = {
        k: v for k, v in request.headers.items() 
        if k.lower() not in HOP_BY_HOP_HEADERS
    }

    # Get request body
    body = await request.body()

    try:
        # Check if global client is initialized
        if http_client is None:
            # Initialize client if not already done (for tests or direct calls)
            await startup_event()
            
        # Acquire semaphore to limit concurrency
        async with request_semaphore:
            # Forward the request to the target server using the global client
            response = await http_client.request(
                method=request.method,
                url=target_url,
                headers=headers,
                content=body,
            )

            # Filter out unsafe response headers
            filtered_headers = {
                k: v for k, v in response.headers.items()
                if k.lower() not in UNSAFE_RESPONSE_HEADERS
            }

            # Return a streaming response
            return StreamingResponse(
                response.aiter_bytes(),
                status_code=response.status_code,
                headers=filtered_headers,
                media_type=response.headers.get("content-type")
            )
    except httpx.RequestError as e:
        raise HTTPException(
            status_code=502,
            detail=f"Error forwarding request to target server: {str(e)}",
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}",
        )


@app.api_route(
    "/proxy/{scheme}://{target_host}:{target_port}/{path:path}",
    methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
)
async def proxy_request_with_scheme(
    request: Request,
    scheme: str,
    target_host: str,
    target_port: int,
    path: str,
):
    """
    Forward the incoming request to the target server with explicit scheme and return the response.

    Args:
        request: The incoming request.
        scheme: The scheme to use (http or https).
        target_host: The host of the target server.
        target_port: The port of the target server.
        path: The path to forward the request to.

    Returns:
        The response from the target server.
    """
    return await proxy_request(request, target_host, target_port, path, scheme)


@app.get("/")
async def root():
    """Return a welcome message."""
    return {
        "message": "Welcome to HTTPKit Proxy",
        "usage": [
            "Send requests to /proxy/{target_host}:{target_port}/{path}",
            "Or with explicit scheme: /proxy/{scheme}://{target_host}:{target_port}/{path}"
        ],
    }


def main():
    """Run the proxy server."""
    import os
    import importlib.util
    
    # Disable reload in production for better performance
    reload = os.environ.get("HTTPKIT_ENV", "development").lower() == "development"
    
    # Check if h2 is installed to enable HTTP/2
    h2_installed = importlib.util.find_spec("h2") is not None
    
    # Override the global HTTP client with HTTP/2 support if available
    global http_client
    if h2_installed:
        http_client = httpx.AsyncClient(
            timeout=30.0,
            http2=True,
            limits=httpx.Limits(
                max_connections=200,
                max_keepalive_connections=50,
                keepalive_expiry=30.0
            )
        )
    
    uvicorn.run(
        "httpkit.tools.proxy:app", 
        host="0.0.0.0", 
        port=8000, 
        reload=reload,
        # Use multiple workers in production for better performance
        workers=int(os.environ.get("HTTPKIT_WORKERS", "1"))
    )


if __name__ == "__main__":
    main()