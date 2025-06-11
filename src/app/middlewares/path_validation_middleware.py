import os
from pathlib import Path

from fastapi import HTTPException, Request, Response, status
from starlette.middleware.base import BaseHTTPMiddleware


class PathValidationMiddleware(BaseHTTPMiddleware):
    """
    Middleware to validate paths and prevent path traversal attacks.
    """
    
    DANGEROUS_PATTERNS = [
        "..",
        "~",
        "/etc/",
        "/proc/",
        "/sys/",
        "/dev/",
        "/var/",
        "/tmp/",
        "/usr/",
        "/bin/",
        "/sbin/"
    ]
    
    async def dispatch(self, request: Request, call_next):
        # Debug logging
        print(f"\n🔍 PathValidationMiddleware received:")
        print(f"   Method: {request.method}")
        print(f"   URL: {request.url}")
        print(f"   Headers: {dict(request.headers)}")
        
        # Skip validation for OPTIONS requests (CORS preflight)
        if request.method == "OPTIONS":
            print(f"   ✅ Skipping validation for OPTIONS request")
            response = await call_next(request)
            print(f"   ✅ OPTIONS response status: {response.status_code}")
            return response
            
        # Only validate POST requests that might contain codebase_path
        if request.method == "POST" and "context-gather" in str(request.url):
            print(f"   🔍 Validating POST request to context-gather")
            try:
                # Get request body
                body = await request.body()
                if body:
                    import json
                    try:
                        data = json.loads(body)
                        if isinstance(data, dict) and "codebase_path" in data:
                            self._validate_path_security(data["codebase_path"])
                    except json.JSONDecodeError:
                        pass  # Let the endpoint handle invalid JSON
                
                # Reconstruct request with body for downstream processing
                async def receive():
                    return {"type": "http.request", "body": body}
                
                request._receive = receive
                
            except Exception as e:
                if isinstance(e, HTTPException):
                    raise e
                # Continue processing for other errors
                pass
        
        response = await call_next(request)
        print(f"   📤 Final response status: {response.status_code}")
        return response
    
    def _validate_path_security(self, path: str) -> None:
        """
        Validate path for security concerns.
        
        Args:
            path: The path to validate
            
        Raises:
            HTTPException: 400 if path contains dangerous patterns
        """
        if not path:
            return
        
        # Normalize the path
        normalized_path = os.path.normpath(path)
        
        # Check for dangerous patterns
        for pattern in self.DANGEROUS_PATTERNS:
            if pattern in normalized_path.lower():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Path contains potentially dangerous pattern: '{pattern}'"
                )
        
        # Check for absolute paths that might be system directories
        if os.path.isabs(normalized_path):
            path_obj = Path(normalized_path)
            # Allow common development directories
            allowed_prefixes = [
                "/Users/",  # macOS user directories
                "/home/",   # Linux user directories
                "/opt/",    # Optional software
                "/workspace/",  # Common container workspace
                "/app/",    # Common app directory
            ]
            
            if not any(normalized_path.startswith(prefix) for prefix in allowed_prefixes):
                # Check if it's trying to access system directories
                system_dirs = ["/etc", "/proc", "/sys", "/dev", "/var", "/usr", "/bin", "/sbin", "/root"]
                if any(normalized_path.startswith(sys_dir) for sys_dir in system_dirs):
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Access to system directories is not allowed"
                    )
