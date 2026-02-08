#!/usr/bin/env python3
"""
Production-ready UDP Server for UE5 Clients
Listens on 0.0.0.0:6000, handles JSON messages, and sends acknowledgments.
Designed for router port forwarding and multiple concurrent clients.
"""

import socket
import json
import sys
import signal
import logging
from datetime import datetime
from typing import Optional, Dict, Any

# Configure logging for production use
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('udp_server.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Server configuration
HOST = '0.0.0.0'  # Binds to all interfaces for router port forwarding
PORT = 6000  # UDP port
BUFFER_SIZE = 4096  # Maximum UDP packet size
TIMEOUT = 30.0  # Socket timeout in seconds
HEARTBEAT_INTERVAL = 60  # Optional heartbeat interval in seconds

# Global server instance for clean shutdown
server_socket: Optional[socket.socket] = None
running = True


def create_acknowledgment(
    message_id: Optional[str] = None,
    status: str = "ok",
    timestamp: Optional[str] = None
) -> str:
    """
    Create a JSON acknowledgment message.
    
    Args:
        message_id: Optional ID from the received message
        status: Response status (default: "ok")
        timestamp: Optional timestamp (generated if not provided)
    
    Returns:
        JSON-formatted acknowledgment string
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
    
    return json.dumps(ack)


def parse_message(data: bytes) -> Optional[Dict[str, Any]]:
    """
    Parse incoming UTF-8 JSON message.
    
    Args:
        data: Raw bytes from UDP packet
    
    Returns:
        Parsed JSON dictionary or None if parsing fails
    """
    try:
        text = data.decode('utf-8')
        return json.loads(text)
    except UnicodeDecodeError:
        logger.error("Failed to decode message as UTF-8")
        return None
    except json.JSONDecodeError:
        logger.error("Received invalid JSON format")
        return None


def handle_client_message(
    data: bytes,
    client_addr: tuple,
    client_socket: socket.socket
) -> None:
    """
    Process a single message from a client.
    
    Args:
        data: Raw message bytes
        client_addr: Tuple of (client_ip, client_port)
        client_socket: The UDP socket for sending responses
    """
    client_ip, client_port = client_addr
    
    # Log incoming message
    logger.info(f"Received {len(data)} bytes from {client_ip}:{client_port}")
    
    # Parse JSON message
    message = parse_message(data)
    if message is None:
        logger.warning(f"Failed to parse message from {client_ip}:{client_port}")
        try:
            error_ack = json.dumps({"type": "error", "status": "invalid_json"})
            client_socket.sendto(error_ack.encode('utf-8'), client_addr)
        except Exception as e:
            logger.error(f"Failed to send error acknowledgment: {e}")
        return
    
    # Log message content
    logger.info(f"Message from {client_ip}:{client_port}: {json.dumps(message)}")
    
    # Extract message ID if present
    message_id = message.get("id") or message.get("message_id")
    
    # Send acknowledgment
    try:
        ack_message = create_acknowledgment(
            message_id=message_id,
            status="ok"
        )
        client_socket.sendto(ack_message.encode('utf-8'), client_addr)
        logger.info(f"Sent acknowledgment to {client_ip}:{client_port}")
    except Exception as e:
        logger.error(f"Failed to send acknowledgment to {client_ip}:{client_port}: {e}")


def signal_handler(signum: int, frame: Any) -> None:
    """
    Handle Ctrl+C (SIGINT) for graceful shutdown.
    
    Args:
        signum: Signal number
        frame: Current stack frame
    """
    global running
    logger.info("Shutdown signal received (SIGINT)")
    running = False


def start_server() -> None:
    """
    Initialize and start the UDP server.
    Listens for incoming JSON messages from UE5 clients.
    """
    global server_socket, running
    
    try:
        # Create UDP socket
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        
        # Allow reusing the address to avoid "Address already in use" errors
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        # Set socket timeout for non-blocking behavior
        server_socket.settimeout(TIMEOUT)
        
        # Bind to all interfaces on configured port
        server_socket.bind((HOST, PORT))
        
        logger.info(f"UDP Server started on {HOST}:{PORT}")
        logger.info("Waiting for client messages (Ctrl+C to shutdown)...")
        
        # Register signal handler for clean shutdown
        signal.signal(signal.SIGINT, signal_handler)
        
        # Main server loop
        while running:
            try:
                # Receive data and sender address (non-blocking with timeout)
                data, client_addr = server_socket.recvfrom(BUFFER_SIZE)
                
                if data:
                    handle_client_message(data, client_addr, server_socket)
            
            except socket.timeout:
                # Timeout is expected; allows checking the 'running' flag
                continue
            
            except Exception as e:
                logger.error(f"Error receiving data: {e}")
                continue
    
    except OSError as e:
        logger.error(f"Socket error: {e}")
        if "Address already in use" in str(e):
            logger.error(f"Port {PORT} is already in use. Check for other instances.")
    
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
    
    finally:
        shutdown_server()


def shutdown_server() -> None:
    """
    Clean shutdown of the UDP server.
    Closes the socket and logs final status.
    """
    global server_socket
    
    if server_socket:
        try:
            server_socket.close()
            logger.info("Server socket closed successfully")
        except Exception as e:
            logger.error(f"Error closing socket: {e}")
    
    logger.info("UDP Server shutdown complete")


def main() -> None:
    """
    Main entry point for the UDP server.
    """
    logger.info("=" * 60)
    logger.info("UDP Server Initialization")
    logger.info(f"Binding to: {HOST}:{PORT}")
    logger.info(f"Buffer size: {BUFFER_SIZE} bytes")
    logger.info(f"Socket timeout: {TIMEOUT} seconds")
    logger.info("=" * 60)
    
    start_server()


if __name__ == "__main__":
    main()
