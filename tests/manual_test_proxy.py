"""Test helper script to verify the proxy functionality."""

import asyncio
import httpx
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import uvicorn
import threading
import time
import sys

# Create a simple target server
target_app = FastAPI()

@target_app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy"}

@target_app.post("/echo")
async def echo(request: Request):
    """Echo the request body."""
    body = await request.json()
    return {"echo": body}

@target_app.get("/headers")
async def headers(request: Request):
    """Return the request headers."""
    return {"headers": dict(request.headers)}

def run_target_server():
    """Run the target server."""
    uvicorn.run(target_app, host="localhost", port=9000)

def test_proxy():
    """Test the proxy functionality."""
    # Start the target server in a separate thread
    target_thread = threading.Thread(target=run_target_server)
    target_thread.daemon = True
    target_thread.start()
    
    # Wait for the server to start
    time.sleep(2)
    
    # Test the proxy
    try:
        # Test GET request
        response = httpx.get("http://localhost:8000/proxy/localhost:9000/health")
        print(f"GET /health: {response.status_code} - {response.text}")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"
        
        # Test POST request with body
        response = httpx.post(
            "http://localhost:8000/proxy/localhost:9000/echo",
            json={"message": "Hello, world!"}
        )
        print(f"POST /echo: {response.status_code} - {response.text}")
        assert response.status_code == 200
        assert response.json()["echo"]["message"] == "Hello, world!"
        
        # Test headers
        response = httpx.get(
            "http://localhost:8000/proxy/localhost:9000/headers",
            headers={"X-Custom-Header": "test-value"}
        )
        print(f"GET /headers: {response.status_code} - {response.text}")
        assert response.status_code == 200
        assert response.json()["headers"]["x-custom-header"] == "test-value"
        
        print("All tests passed!")
        return True
    except Exception as e:
        print(f"Error: {e}")
        return False

if __name__ == "__main__":
    success = test_proxy()
    sys.exit(0 if success else 1)