"""
Custom exception classes for the application
"""
from fastapi import HTTPException, status

class AppException(Exception):
    """Base application exception"""
    def __init__(self, message: str, status_code: int = 500):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)

class AuthenticationError(AppException):
    """Authentication failed"""
    def __init__(self, message: str = "Authentication failed"):
        super().__init__(message, status.HTTP_401_UNAUTHORIZED)

class AuthorizationError(AppException):
    """Authorization failed"""
    def __init__(self, message: str = "Insufficient permissions"):
        super().__init__(message, status.HTTP_403_FORBIDDEN)

class ResourceNotFoundError(AppException):
    """Resource not found"""
    def __init__(self, resource: str, resource_id: str = None):
        message = f"{resource} not found"
        if resource_id:
            message = f"{resource} with id '{resource_id}' not found"
        super().__init__(message, status.HTTP_404_NOT_FOUND)

class ValidationError(AppException):
    """Data validation error"""
    def __init__(self, message: str):
        super().__init__(message, status.HTTP_422_UNPROCESSABLE_ENTITY)

class CameraError(AppException):
    """Camera-related errors"""
    def __init__(self, message: str):
        super().__init__(message, status.HTTP_500_INTERNAL_SERVER_ERROR)

class DetectionError(AppException):
    """AI detection errors"""
    def __init__(self, message: str):
        super().__init__(message, status.HTTP_500_INTERNAL_SERVER_ERROR)

class BlockchainError(AppException):
    """Blockchain integration errors"""
    def __init__(self, message: str):
        super().__init__(message, status.HTTP_503_SERVICE_UNAVAILABLE)

class StorageError(AppException):
    """Storage (IPFS, local) errors"""
    def __init__(self, message: str):
        super().__init__(message, status.HTTP_500_INTERNAL_SERVER_ERROR)

class FederatedLearningError(AppException):
    """FL-related errors"""
    def __init__(self, message: str):
        super().__init__(message, status.HTTP_500_INTERNAL_SERVER_ERROR)


# Exception handlers for FastAPI
def create_exception_handlers():
    """Create exception handlers for FastAPI app"""
    from fastapi import Request
    from fastapi.responses import JSONResponse
    
    async def app_exception_handler(request: Request, exc: AppException):
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.message, "type": exc.__class__.__name__}
        )
    
    return {AppException: app_exception_handler}