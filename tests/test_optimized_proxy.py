"""Test the optimized proxy implementation."""

import asyncio
import httpx
import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient
from httpkit.tools.proxy import app, startup_event, shutdown_event

client = TestClient(app)

@patch("httpkit.tools.proxy.httpx.AsyncClient")
def test_app_startup_initializes_globals(mock_client):
    """Test that the app startup event initializes global variables."""
    # Setup mock client
    mock_async_client = mock_client.return_value
    
    # Create a mock aclose coroutine
    async def mock_aclose():
        pass
    
    mock_async_client.aclose = mock_aclose
    
    # Call the startup event handler directly
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(startup_event())
    
    # Import after initialization to get the updated values
    from httpkit.tools.proxy import http_client, request_semaphore
    
    # Check that the global variables are initialized
    assert http_client is not None
    assert request_semaphore is not None
    assert request_semaphore._value == 100  # Default value
    
    # Clean up
    loop.run_until_complete(shutdown_event())
    loop.close()

def test_root_endpoint():
    """Test the root endpoint."""
    response = client.get("/")
    assert response.status_code == 200
    assert "Welcome to HTTPKit Proxy" in response.json()["message"]
    assert isinstance(response.json()["usage"], list)
    assert len(response.json()["usage"]) == 2

def test_scheme_validation():
    """Test that invalid schemes are rejected."""
    # This should fail with a 400 error
    response = client.get("/proxy/ftp://example.com:80/path")
    assert response.status_code == 400
    assert "Invalid scheme" in response.json()["detail"]

if __name__ == "__main__":
    pytest.main(["-xvs", __file__])