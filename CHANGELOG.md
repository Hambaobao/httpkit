# Changelog

## [Unreleased]

### Added
- Support for explicit HTTP/HTTPS scheme in proxy URL
- Environment variable configuration for production settings
- HTTP/2 support for improved performance
- Concurrency limiting via semaphore to prevent resource exhaustion

### Changed
- Reuse httpx.AsyncClient globally instead of creating a new one per request
- Use StreamingResponse instead of buffering the entire response
- Filter out unsafe or conflicting response headers
- Improved error handling and response streaming
- Disabled auto-reload in production for better performance

### Fixed
- Memory usage issues with large responses
- Connection pooling and reuse
- Header handling to prevent conflicts