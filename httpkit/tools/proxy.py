"""HTTP proxy module for httpkit.

This module provides a simple HTTP proxy service that forwards requests to a target server.
"""

import httpx
from fastapi import FastAPI, Request, Response, HTTPException
from fastapi.responses import StreamingResponse
import uvicorn
from typing import List, Dict, Any, Optional
import asyncio

# Create FastAPI app
app = FastAPI(
    title="HTTPKit Proxy",
    description="A simple HTTP proxy service that forwards requests to a target server.",
    version="0.1.0",
)

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


@app.api_route(
    "/proxy/{target_host}:{target_port}/{path:path}",
    methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
)
async def proxy_request(
    request: Request,
    target_host: str,
    target_port: int,
    path: str,
):
    """
    Forward the incoming request to the target server and return the response.

    Args:
        request: The incoming request.
        target_host: The host of the target server.
        target_port: The port of the target server.
        path: The path to forward the request to.

    Returns:
        The response from the target server.
    """
    # Construct the target URL
    target_url = f"http://{target_host}:{target_port}/{path}"
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
        # Create httpx client with timeout
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Forward the request to the target server
            response = await client.request(
                method=request.method,
                url=target_url,
                headers=headers,
                content=body,
            )

            # Return the response from the target server
            return Response(
                content=response.content,
                status_code=response.status_code,
                headers=dict(response.headers),
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


@app.get("/")
async def root():
    """Return a welcome message."""
    return {
        "message": "Welcome to HTTPKit Proxy",
        "usage": "Send requests to /proxy/{target_host}:{target_port}/{path}",
    }


def main():
    """Run the proxy server."""
    uvicorn.run("httpkit.tools.proxy:app", host="0.0.0.0", port=8000, reload=True)


if __name__ == "__main__":
    main()