"""Integration test for the HTTP proxy module.

This script starts both a target server and the proxy server,
then makes requests through the proxy to verify functionality.
"""

import asyncio
import subprocess
import time
import sys
import requests
import threading
import uvicorn
from fastapi import FastAPI, Request

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

def run_proxy_server():
    """Run the proxy server."""
    subprocess.Popen(["uvicorn", "httpkit.proxy:app", "--host", "0.0.0.0", "--port", "8000"])

def main():
    """Run the integration test."""
    print("Starting target server...")
    target_thread = threading.Thread(target=run_target_server)
    target_thread.daemon = True
    target_thread.start()
    
    print("Starting proxy server...")
    run_proxy_server()
    
    # Wait for servers to start
    time.sleep(3)
    
    print("Running tests...")
    try:
        # Test GET request
        response = requests.get("http://localhost:8000/proxy/localhost:9000/health")
        print(f"GET /health: {response.status_code} - {response.text}")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"
        
        # Test POST request with body
        response = requests.post(
            "http://localhost:8000/proxy/localhost:9000/echo",
            json={"message": "Hello, world!"}
        )
        print(f"POST /echo: {response.status_code} - {response.text}")
        assert response.status_code == 200
        assert response.json()["echo"]["message"] == "Hello, world!"
        
        # Test headers
        response = requests.get(
            "http://localhost:8000/proxy/localhost:9000/headers",
            headers={"X-Custom-Header": "test-value"}
        )
        print(f"GET /headers: {response.status_code} - {response.text}")
        assert response.status_code == 200
        assert response.json()["headers"]["x-custom-header"] == "test-value"
        
        print("All tests passed!")
        return 0
    except Exception as e:
        print(f"Error: {e}")
        return 1
    finally:
        # Kill the proxy server
        subprocess.run(["pkill", "-f", "uvicorn httpkit.proxy:app"])

if __name__ == "__main__":
    sys.exit(main())