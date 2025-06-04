"""Tests for the HTTP proxy module."""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
import httpx
from httpkit.tools.proxy import app


@pytest.fixture
def client():
    """Create a test client for the FastAPI app."""
    return TestClient(app)


def test_root_endpoint(client):
    """Test the root endpoint returns the welcome message."""
    response = client.get("/")
    assert response.status_code == 200
    assert "Welcome to HTTPKit Proxy" in response.json()["message"]
    assert "usage" in response.json()


@patch("httpkit.tools.proxy.httpx.AsyncClient")
def test_proxy_get_request(mock_client, client):
    """Test that GET requests are properly forwarded."""
    # Setup mock response
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.content = b'{"status": "healthy"}'
    mock_response.headers = {"Content-Type": "application/json"}
    
    # Setup mock client
    mock_async_client = MagicMock()
    mock_async_client.__aenter__.return_value.request.return_value = mock_response
    mock_client.return_value = mock_async_client
    
    # Make request to proxy
    response = client.get("/proxy/example.com:80/api/health?param=value", 
                         headers={"X-Custom-Header": "test"})
    
    # Verify response
    assert response.status_code == 200
    assert response.content == b'{"status": "healthy"}'
    
    # Verify the request was forwarded correctly
    mock_async_client.__aenter__.return_value.request.assert_called_once()
    call_args = mock_async_client.__aenter__.return_value.request.call_args[1]
    assert call_args["method"] == "GET"
    assert call_args["url"] == "http://example.com:80/api/health?param=value"
    
    # Check that headers are included in the request (case-insensitive)
    headers_dict = {k.lower(): v for k, v in call_args["headers"].items()}
    assert "x-custom-header" in headers_dict
    assert headers_dict["x-custom-header"] == "test"


@patch("httpkit.tools.proxy.httpx.AsyncClient")
def test_proxy_post_request_with_body(mock_client, client):
    """Test that POST requests with body are properly forwarded."""
    # Setup mock response
    mock_response = MagicMock()
    mock_response.status_code = 201
    mock_response.content = b'{"id": 123}'
    mock_response.headers = {"Content-Type": "application/json"}
    
    # Setup mock client
    mock_async_client = MagicMock()
    mock_async_client.__aenter__.return_value.request.return_value = mock_response
    mock_client.return_value = mock_async_client
    
    # Make request to proxy
    response = client.post(
        "/proxy/example.com:80/api/users",
        json={"name": "Test User", "email": "test@example.com"},
        headers={"Content-Type": "application/json"}
    )
    
    # Verify response
    assert response.status_code == 201
    assert response.content == b'{"id": 123}'
    
    # Verify the request was forwarded correctly
    mock_async_client.__aenter__.return_value.request.assert_called_once()
    call_args = mock_async_client.__aenter__.return_value.request.call_args[1]
    assert call_args["method"] == "POST"
    assert call_args["url"] == "http://example.com:80/api/users"
    
    # Check that headers are included in the request (case-insensitive)
    headers_dict = {k.lower(): v for k, v in call_args["headers"].items()}
    assert "content-type" in headers_dict
    assert headers_dict["content-type"] == "application/json"
    
    # The body should be forwarded (content is passed as bytes)
    assert call_args["content"] is not None


@patch("httpkit.tools.proxy.httpx.AsyncClient")
def test_proxy_request_error(mock_client, client):
    """Test error handling when the target server is unreachable."""
    # Setup mock client to raise an exception
    mock_async_client = MagicMock()
    mock_async_client.__aenter__.return_value.request.side_effect = httpx.RequestError("Connection error")
    mock_client.return_value = mock_async_client
    
    # Make request to proxy
    response = client.get("/proxy/nonexistent.example:80/api/health")
    
    # Verify response
    assert response.status_code == 502
    assert "Error forwarding request" in response.json()["detail"]


@patch("httpkit.tools.proxy.httpx.AsyncClient")
def test_proxy_handles_different_http_methods(mock_client, client):
    """Test that different HTTP methods are properly forwarded."""
    # Setup mock response
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.content = b'{"success": true}'
    mock_response.headers = {"Content-Type": "application/json"}
    
    # Setup mock client
    mock_async_client = MagicMock()
    mock_async_client.__aenter__.return_value.request.return_value = mock_response
    mock_client.return_value = mock_async_client
    
    # Test different HTTP methods
    for method in ["PUT", "DELETE", "PATCH", "OPTIONS"]:
        # Make request to proxy
        request_func = getattr(client, method.lower())
        response = request_func("/proxy/example.com:80/api/resource")
        
        # Verify response
        assert response.status_code == 200
        
        # Verify the request was forwarded with correct method
        call_args = mock_async_client.__aenter__.return_value.request.call_args[1]
        assert call_args["method"] == method
        assert call_args["url"] == "http://example.com:80/api/resource"