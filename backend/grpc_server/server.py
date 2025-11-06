"""
gRPC Server for Terminal Service

Runs alongside FastAPI server to provide HTTP/2 bidirectional streaming.
"""

import asyncio
import logging
from concurrent import futures

import grpc

from ..proto import terminal_pb2_grpc
from .terminal_service import TerminalService

logger = logging.getLogger(__name__)


async def serve_grpc(pty_manager, host: str = "0.0.0.0", port: int = 50051):
    """
    Start gRPC server for terminal service.

    Args:
        pty_manager: PTY session manager instance
        host: Host to bind to
        port: Port to bind to (default: 50051)
    """
    server = grpc.aio.server(
        futures.ThreadPoolExecutor(max_workers=10),
        options=[
            ('grpc.max_send_message_length', 10 * 1024 * 1024),  # 10MB
            ('grpc.max_receive_message_length', 10 * 1024 * 1024),  # 10MB
        ]
    )

    # Add terminal service
    terminal_service = TerminalService(pty_manager)
    terminal_pb2_grpc.add_TerminalServicer_to_server(terminal_service, server)

    # Bind to address
    server.add_insecure_port(f"{host}:{port}")

    logger.info(f"Starting gRPC server on {host}:{port}")
    await server.start()

    logger.info(f"✓ gRPC server listening on {host}:{port}")

    try:
        await server.wait_for_termination()
    except KeyboardInterrupt:
        logger.info("Stopping gRPC server...")
        await server.stop(grace=5)
        logger.info("gRPC server stopped")


def start_grpc_server_background(pty_manager, host: str = "0.0.0.0", port: int = 50051):
    """
    Start gRPC server in background thread.

    Returns:
        asyncio.Task: Background task running the gRPC server
    """
    loop = asyncio.get_event_loop()
    task = loop.create_task(serve_grpc(pty_manager, host, port))
    return task
