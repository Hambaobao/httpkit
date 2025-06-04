# HTTPKit

A collection of HTTP-related utilities and tools.

## Installation

```bash
pip install httpkit
```

## Tools

### HTTP Proxy

A simple HTTP proxy service that forwards requests to a target server.

#### Usage

You can run the proxy server in several ways:

1. Using the module directly:

```bash
python -m httpkit.proxy
```

2. Using the entry point:

```bash
httpkit-proxy
```

3. Using uvicorn directly:

```bash
uvicorn httpkit.proxy:app --host 0.0.0.0 --port 8000
```

#### Making Requests

Once the proxy server is running, you can make requests to it using the following URL pattern:

```
http://localhost:8000/proxy/{target_host}:{target_port}/{path}
```

For example, to forward a request to `http://localhost:9000/health`:

```
http://localhost:8000/proxy/localhost:9000/health
```

The proxy will preserve:
- HTTP method
- Headers (except hop-by-hop ones)
- Query parameters
- Request body

## Development

### Setup

```bash
pip install -e .
```

### Running Tests

```bash
pytest
```