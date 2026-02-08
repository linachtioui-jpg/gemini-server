#!/usr/bin/env python3
"""
Production-ready FastAPI Server for UE5 VaRest Plugin
Listens on 0.0.0.0:6000, handles JSON requests, and sends responses.
Designed for router port forwarding and multiple concurrent clients.
"""

import json
import logging
import sys
from datetime import datetime
from typing import Optional, Dict, Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import uvicorn

# Configure logging for production use
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('fastapi_server.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Server configuration
HOST = '0.0.0.0'  # Binds to all interfaces for router port forwarding
PORT = 6000  # HTTP port
WORKERS = 4  # Number of worker processes

# Create FastAPI application
app = FastAPI(
    title="UE5 VaRest Server",
    description="REST API for UE5 VaRest Plugin",
    version="1.0.0"
)


def create_acknowledgment(
    message_id: Optional[str] = None,
    status: str = "ok",
    timestamp: Optional[str] = None,
    data: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Create a JSON acknowledgment response.
    
    Args:
        message_id: Optional ID from the received message
        status: Response status (default: "ok")
        timestamp: Optional timestamp (generated if not provided)
        data: Optional additional response data
    
    Returns:
        Dictionary ready for JSON response
    """
    if timestamp is None:
        timestamp = datetime.utcnow().isoformat() + 'Z'
    
    ack = {
        "type": "acknowledgment",
        "status": status,
        "timestamp": timestamp,
    }
    
    if message_id:
        ack["message_id"] = message_id
    
    if data:
        ack["data"] = data
    
    return ack


@app.post("/message")
async def receive_message(request: Request) -> JSONResponse:
    """
    Receive JSON message from UE5 VaRest plugin.
    Endpoint: POST /message
    
    Args:
        request: FastAPI request object containing JSON payload
    
    Returns:
        JSONResponse with acknowledgment
    """
    try:
        # Extract client information
        client_host = request.client.host if request.client else "unknown"
        client_port = request.client.port if request.client else 0
        
        # Get request body as JSON
        try:
            payload = await request.json()
        except json.JSONDecodeError:
            logger.warning(f"Invalid JSON from {client_host}:{client_port}")
            return JSONResponse(
                status_code=400,
                content={
                    "type": "error",
                    "status": "invalid_json",
                    "message": "Request body must be valid JSON"
                }
            )
        
        # Log incoming message
        logger.info(f"Received POST /message from {client_host}:{client_port}")
        logger.info(f"Payload: {json.dumps(payload)}")
        
        # Extract message ID if present
        message_id = payload.get("id") or payload.get("message_id")
        
        # Process the message (add your business logic here)
        # Example: extract specific fields
        message_type = payload.get("type", "unknown")
        
        # Send acknowledgment
        ack = create_acknowledgment(
            message_id=message_id,
            status="received",
            data={"processed_type": message_type}
        )
        
        logger.info(f"Sent acknowledgment to {client_host}:{client_port}")
        
        return JSONResponse(
            status_code=200,
            content=ack
        )
    
    except Exception as e:
        logger.error(f"Error processing request: {e}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={
                "type": "error",
                "status": "server_error",
                "message": str(e)
            }
        )


@app.post("/data")
async def receive_data(request: Request) -> JSONResponse:
    """
    Alternative endpoint for receiving data.
    Endpoint: POST /data
    
    Args:
        request: FastAPI request object containing JSON payload
    
    Returns:
        JSONResponse with acknowledgment
    """
    try:
        client_host = request.client.host if request.client else "unknown"
        client_port = request.client.port if request.client else 0
        
        payload = await request.json()
        
        logger.info(f"Received POST /data from {client_host}:{client_port}")
        logger.info(f"Data: {json.dumps(payload)}")
        
        message_id = payload.get("id")
        
        ack = create_acknowledgment(
            message_id=message_id,
            status="ok"
        )
        
        return JSONResponse(status_code=200, content=ack)
    
    except json.JSONDecodeError:
        return JSONResponse(
            status_code=400,
            content={"type": "error", "status": "invalid_json"}
        )
    except Exception as e:
        logger.error(f"Error in /data endpoint: {e}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"type": "error", "status": "server_error"}
        )


@app.get("/health")
async def health_check() -> JSONResponse:
    """
    Health check endpoint for monitoring.
    Endpoint: GET /health
    
    Returns:
        JSON response indicating server status
    """
    return JSONResponse(
        status_code=200,
        content={
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat() + 'Z'
        }
    )


@app.get("/")
async def root() -> Dict[str, str]:
    """
    Root endpoint with API information.
    
    Returns:
        Dictionary with server information
    """
    return {
        "name": "UE5 VaRest Server",
        "version": "1.0.0",
        "endpoints": {
            "POST /message": "Main message receiver",
            "POST /data": "Alternative data receiver",
            "GET /health": "Health check",
            "GET /": "API info"
        }
    }


def run_server() -> None:
    """
    Start the FastAPI server with uvicorn.
    """
    logger.info("=" * 60)
    logger.info("FastAPI Server Initialization")
    logger.info(f"Binding to: {HOST}:{PORT}")
    logger.info(f"Workers: {WORKERS}")
    logger.info("Endpoints:")
    logger.info("  POST /message - Receive JSON messages")
    logger.info("  POST /data    - Receive data")
    logger.info("  GET /health   - Health check")
    logger.info("=" * 60)
    
    try:
        # Configure uvicorn server
        config = uvicorn.Config(
            app=app,
            host=HOST,
            port=PORT,
            log_level="info",
            access_log=True
        )
        server = uvicorn.Server(config)
        
        # Run server (blocks until interrupted)
        import asyncio
        asyncio.run(server.serve())
    
    except OSError as e:
        logger.error(f"Socket error: {e}")
        if "Address already in use" in str(e):
            logger.error(f"Port {PORT} is already in use. Check for other instances.")
    except Exception as e:
        logger.error(f"Server error: {e}", exc_info=True)
    finally:
        logger.info("FastAPI Server shutdown complete")


if __name__ == "__main__":
    run_server()
