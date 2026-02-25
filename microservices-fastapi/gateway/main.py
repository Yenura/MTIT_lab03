from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import httpx
from typing import Any, Dict, List, Optional
import time
import logging
from auth import create_token, verify_token
from middleware import logging_middleware

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Pydantic models for request/response
class LoginRequest(BaseModel):
    username: str
    password: str

class LoginResponse(BaseModel):
    access_token: str
    token_type: str
    username: str
    role: str

class ErrorResponse(BaseModel):
    error: str
    message: str
    available_services: Optional[List[str]] = None
    path: Optional[str] = None

class HealthCheckResponse(BaseModel):
    gateway: str
    timestamp: float
    services: Dict[str, Dict[str, str]]

app = FastAPI(
    title="API Gateway", 
    version="1.0.0",
    description="API Gateway for Student and Course Microservices",
    docs_url="/docs"
)

# Add logging middleware
app.middleware("http")(logging_middleware)

# Service URLs
SERVICES = {
    "student": "http://localhost:8001",
    "course": "http://localhost:8002"
}

# Mock users for authentication
USERS = {
    "admin": {"password": "admin123", "role": "admin"},
    "user": {"password": "user123", "role": "user"}
}

async def forward_request(service: str, path: str, method: str, **kwargs) -> Any:
    """Forward request to the appropriate microservice with enhanced error handling"""
    if service not in SERVICES:
        raise HTTPException(
            status_code=404, 
            detail={
                "error": "Service not found",
                "message": f"The service '{service}' is not available",
                "available_services": list(SERVICES.keys())
            }
        )
    
    url = f"{SERVICES[service]}{path}"
    
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            if method == "GET":
                response = await client.get(url, **kwargs)
            elif method == "POST":
                response = await client.post(url, **kwargs)
            elif method == "PUT":
                response = await client.put(url, **kwargs)
            elif method == "DELETE":
                response = await client.delete(url, **kwargs)
            else:
                raise HTTPException(
                    status_code=405, 
                    detail={
                        "error": "Method not allowed",
                        "message": f"HTTP method '{method}' is not supported"
                    }
                )
            
            # Handle different response types
            try:
                content = response.json() if response.text else None
            except:
                content = {"message": "Response received", "status": response.status_code}
            
            return JSONResponse(
                content=content,
                status_code=response.status_code,
                headers=dict(response.headers)
            )
            
        except httpx.TimeoutException:
            raise HTTPException(
                status_code=504,
                detail={
                    "error": "Gateway Timeout",
                    "message": f"The {service} service is taking too long to respond"
                }
            )
        except httpx.ConnectionError:
            raise HTTPException(
                status_code=503,
                detail={
                    "error": "Service Unavailable",
                    "message": f"Cannot connect to {service} service. Make sure it's running on port {SERVICES[service].split(':')[-1]}"
                }
            )
        except httpx.RequestError as e:
            raise HTTPException(
                status_code=500,
                detail={
                    "error": "Internal Server Error",
                    "message": f"Error communicating with {service} service: {str(e)}"
                }
            )

@app.get("/", response_model=Dict[str, Any])
def read_root():
    """Root endpoint with gateway information"""
    return {
        "message": "API Gateway is running", 
        "available_services": list(SERVICES.keys()),
        "version": "1.0.0",
        "endpoints": {
            "gateway": "/gateway/{service}",
            "docs": "/docs",
            "login": "/gateway/login",
            "health": "/gateway/health"
        }
    }

# Authentication endpoints
@app.post("/gateway/login", response_model=LoginResponse)
async def login(login_data: LoginRequest):
    """Login to get access token
    
    - **username**: admin or user
    - **password**: admin123 or user123
    """
    username = login_data.username
    password = login_data.password
    
    if username in USERS and USERS[username]["password"] == password:
        token = create_token(username)
        return {
            "access_token": token, 
            "token_type": "bearer",
            "username": username,
            "role": USERS[username]["role"]
        }
    
    raise HTTPException(
        status_code=401, 
        detail={
            "error": "Unauthorized",
            "message": "Invalid username or password"
        }
    )

@app.get("/gateway/protected")
async def protected_route(user=Depends(verify_token)):
    """Example of protected route - requires valid JWT token"""
    return {
        "message": "You have access to protected route!",
        "user": user,
        "timestamp": time.time()
    }

# Student Service Routes (Protected)
@app.get("/gateway/students")
async def get_all_students(user=Depends(verify_token)):
    """Get all students through gateway (protected)"""
    logger.info(f"User {user.get('username')} accessed all students")
    return await forward_request("student", "/api/students", "GET")

@app.get("/gateway/students/{student_id}")
async def get_student(student_id: int, user=Depends(verify_token)):
    """Get a student by ID through gateway (protected)"""
    logger.info(f"User {user.get('username')} accessed student {student_id}")
    return await forward_request("student", f"/api/students/{student_id}", "GET")

@app.post("/gateway/students")
async def create_student(request: Request, user=Depends(verify_token)):
    """Create a new student through gateway (protected)
    
    Example request body:
    {
        "name": "New Student",
        "age": 20,
        "email": "student@example.com",
        "course": "Computer Science"
    }
    """
    logger.info(f"User {user.get('username')} creating a new student")
    body = await request.json()
    return await forward_request("student", "/api/students", "POST", json=body)

@app.put("/gateway/students/{student_id}")
async def update_student(student_id: int, request: Request, user=Depends(verify_token)):
    """Update a student through gateway (protected)
    
    Example request body:
    {
        "name": "Updated Name",
        "age": 21
    }
    """
    logger.info(f"User {user.get('username')} updating student {student_id}")
    body = await request.json()
    return await forward_request("student", f"/api/students/{student_id}", "PUT", json=body)

@app.delete("/gateway/students/{student_id}")
async def delete_student(student_id: int, user=Depends(verify_token)):
    """Delete a student through gateway (protected)"""
    logger.info(f"User {user.get('username')} deleting student {student_id}")
    return await forward_request("student", f"/api/students/{student_id}", "DELETE")

# Course Service Routes (Protected)
@app.get("/gateway/courses")
async def get_all_courses(user=Depends(verify_token)):
    """Get all courses through gateway (protected)"""
    logger.info(f"User {user.get('username')} accessed all courses")
    return await forward_request("course", "/api/courses", "GET")

@app.get("/gateway/courses/{course_id}")
async def get_course(course_id: int, user=Depends(verify_token)):
    """Get a course by ID through gateway (protected)"""
    logger.info(f"User {user.get('username')} accessed course {course_id}")
    return await forward_request("course", f"/api/courses/{course_id}", "GET")

@app.post("/gateway/courses")
async def create_course(request: Request, user=Depends(verify_token)):
    """Create a new course through gateway (protected)
    
    Example request body:
    {
        "name": "New Course",
        "code": "CS401",
        "credits": 3,
        "instructor": "Dr. Smith",
        "department": "Computer Science"
    }
    """
    logger.info(f"User {user.get('username')} creating a new course")
    body = await request.json()
    return await forward_request("course", "/api/courses", "POST", json=body)

@app.put("/gateway/courses/{course_id}")
async def update_course(course_id: int, request: Request, user=Depends(verify_token)):
    """Update a course through gateway (protected)
    
    Example request body:
    {
        "name": "Updated Course",
        "credits": 4
    }
    """
    logger.info(f"User {user.get('username')} updating course {course_id}")
    body = await request.json()
    return await forward_request("course", f"/api/courses/{course_id}", "PUT", json=body)

@app.delete("/gateway/courses/{course_id}")
async def delete_course(course_id: int, user=Depends(verify_token)):
    """Delete a course through gateway (protected)"""
    logger.info(f"User {user.get('username')} deleting course {course_id}")
    return await forward_request("course", f"/api/courses/{course_id}", "DELETE")

# Health check endpoints
@app.get("/gateway/health", response_model=HealthCheckResponse)
async def health_check():
    """Check health of all services"""
    health_status = {}
    
    for service_name, service_url in SERVICES.items():
        try:
            async with httpx.AsyncClient(timeout=2.0) as client:
                response = await client.get(f"{service_url}/")
                health_status[service_name] = {
                    "status": "healthy" if response.status_code == 200 else "unhealthy",
                    "url": service_url,
                    "response_time": "available"
                }
        except:
            health_status[service_name] = {
                "status": "unhealthy",
                "url": service_url,
                "response_time": "unavailable"
            }
    
    return {
        "gateway": "healthy",
        "timestamp": time.time(),
        "services": health_status
    }

# Error handler for 404
@app.exception_handler(404)
async def custom_404_handler(request: Request, exc):
    return JSONResponse(
        status_code=404,
        content={
            "error": "Not Found",
            "message": f"The requested endpoint '{request.url.path}' was not found",
            "available_endpoints": [
                "/gateway/students",
                "/gateway/courses",
                "/gateway/login",
                "/gateway/protected",
                "/gateway/health",
                "/docs"
            ]
        }
    )

# Error handler for 500
@app.exception_handler(500)
async def custom_500_handler(request: Request, exc):
    logger.error(f"Internal server error on {request.url.path}: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal Server Error",
            "message": "An unexpected error occurred on the gateway",
            "path": request.url.path
        }
    )