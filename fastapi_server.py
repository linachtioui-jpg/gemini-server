#!/usr/bin/env python3
"""
Production-ready FastAPI Server for UE5 VaRest Plugin with Gemini AI
Listens on 0.0.0.0:6000, handles JSON requests, integrates with Google Gemini API.
Designed for router port forwarding and multiple concurrent clients.
"""

import json
import logging
import sys
import os
from datetime import datetime
from typing import Optional, Dict, Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import uvicorn
import google.generativeai as genai

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

# Gemini API configuration
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    # Use gemini-2.0-flash (latest) or gemini-1.5-pro as fallback
    try:
        GEMINI_MODEL = genai.GenerativeModel('gemini-2.0-flash')
        logger.info("Gemini API configured successfully with gemini-2.0-flash")
    except Exception:
        try:
            GEMINI_MODEL = genai.GenerativeModel('gemini-1.5-pro')
            logger.info("Gemini API configured successfully with gemini-1.5-pro")
        except Exception:
            GEMINI_MODEL = genai.GenerativeModel('gemini-pro')
            logger.info("Gemini API configured with gemini-pro (legacy)")
else:
    logger.warning("GEMINI_API_KEY environment variable not set - Gemini features disabled")

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


@app.post("/ai")
async def ai_prompt(request: Request) -> JSONResponse:
    """
    Send a prompt to Gemini AI and get a response.
    Endpoint: POST /ai
    
    Expected JSON body:
    {
        "prompt": "Your question or prompt here",
        "id": "optional_message_id"
    }
    
    Args:
        request: FastAPI request object containing JSON payload
    
    Returns:
        JSONResponse with AI response
    """
    try:
        if not GEMINI_API_KEY:
            return JSONResponse(
                status_code=503,
                content={
                    "type": "error",
                    "status": "gemini_not_configured",
                    "message": "Gemini API is not configured"
                }
            )
        
        client_host = request.client.host if request.client else "unknown"
        client_port = request.client.port if request.client else 0
        
        try:
            payload = await request.json()
        except json.JSONDecodeError:
            logger.warning(f"Invalid JSON from {client_host}:{client_port}")
            return JSONResponse(
                status_code=400,
                content={"type": "error", "status": "invalid_json"}
            )
        
        # Extract prompt
        prompt = payload.get("prompt")
        if not prompt or not isinstance(prompt, str):
            logger.warning(f"No valid prompt from {client_host}:{client_port}")
            return JSONResponse(
                status_code=400,
                content={"type": "error", "status": "missing_prompt"}
            )
        
        message_id = payload.get("id")
        
        logger.info(f"AI Request from {client_host}:{client_port}: {prompt[:100]}")
        
        # Send to Gemini API
        try:
            response = GEMINI_MODEL.generate_content(prompt)
            ai_response = response.text if response.text else "No response generated"
        except Exception as e:
            logger.error(f"Gemini API error: {e}", exc_info=True)
            return JSONResponse(
                status_code=500,
                content={
                    "type": "error",
                    "status": "ai_error",
                    "message": str(e)
                }
            )
        
        ack = {
            "type": "ai_response",
            "status": "ok",
            "response": ai_response,
            "timestamp": datetime.utcnow().isoformat() + 'Z'
        }
        
        if message_id:
            ack["message_id"] = message_id
        
        logger.info(f"AI Response sent to {client_host}:{client_port}")
        
        return JSONResponse(status_code=200, content=ack)
    
    except Exception as e:
        logger.error(f"Error in /ai endpoint: {e}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"type": "error", "status": "server_error"}
        )


@app.get("/ai")
async def ai_prompt_get(prompt: Optional[str] = None, id: Optional[str] = None, request: Request = None) -> JSONResponse:
    """
    Convenience GET endpoint for testing the AI endpoint from browsers/health checks.
    Use query parameters: ?prompt=...&id=...
    Returns same payload as POST /ai.
    """
    try:
        if not GEMINI_API_KEY:
            return JSONResponse(
                status_code=503,
                content={
                    "type": "error",
                    "status": "gemini_not_configured",
                    "message": "Gemini API is not configured"
                }
            )

        client_host = request.client.host if request and request.client else "unknown"
        client_port = request.client.port if request and request.client else 0

        if not prompt:
            logger.warning(f"No prompt provided for GET /ai from {client_host}:{client_port}")
            return JSONResponse(
                status_code=400,
                content={"type": "error", "status": "missing_prompt"}
            )

        logger.info(f"AI GET Request from {client_host}:{client_port}: {prompt[:100]}")

        try:
            response = GEMINI_MODEL.generate_content(prompt)
            ai_response = response.text if response.text else "No response generated"
        except Exception as e:
            logger.error(f"Gemini API error (GET): {e}", exc_info=True)
            return JSONResponse(
                status_code=500,
                content={"type": "error", "status": "ai_error", "message": str(e)}
            )

        ack = {
            "type": "ai_response",
            "status": "ok",
            "response": ai_response,
            "timestamp": datetime.utcnow().isoformat() + 'Z'
        }

        if id:
            ack["message_id"] = id

        logger.info(f"AI GET Response sent to {client_host}:{client_port}")
        return JSONResponse(status_code=200, content=ack)

    except Exception as e:
        logger.error(f"Error in GET /ai endpoint: {e}", exc_info=True)
        return JSONResponse(status_code=500, content={"type": "error", "status": "server_error"})


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
async def root() -> JSONResponse:
    """
    Root endpoint with API information.
    
    Returns:
        JSON response with server information
    """
    return JSONResponse(
        status_code=200,
        content={
            "name": "UE5 VaRest Server",
            "version": "1.0.0",
            "endpoints": {
                "POST /message": "Main message receiver",
                "POST /data": "Alternative data receiver",
                "POST /ai": "Send prompt to Gemini AI",
                "GET /health": "Health check",
                "GET /": "API info"
            }
        }
    )


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
    logger.info("  POST /ai      - Send prompt to Gemini AI")
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
