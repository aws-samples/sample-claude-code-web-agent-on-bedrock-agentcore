"""
gRPC Terminal Service Implementation

Provides bidirectional streaming for terminal I/O over gRPC/HTTP2.
"""

import asyncio
import logging
from typing import AsyncIterator

import grpc

from ..proto import terminal_pb2, terminal_pb2_grpc

logger = logging.getLogger(__name__)


class TerminalService(terminal_pb2_grpc.TerminalServicer):
    """gRPC service for terminal operations with bidirectional streaming."""

    def __init__(self, pty_manager):
        self.pty_manager = pty_manager

    async def CreateSession(
        self, request: terminal_pb2.CreateSessionRequest, context: grpc.aio.ServicerContext
    ) -> terminal_pb2.CreateSessionResponse:
        """Create a new terminal session."""
        try:
            session = await self.pty_manager.create_session(
                rows=request.rows,
                cols=request.cols,
                cwd=request.cwd or "/workspace",
                shell=request.shell or "bash"
            )

            logger.info(f"Created terminal session: {session.session_id}")

            return terminal_pb2.CreateSessionResponse(
                session_id=session.session_id,
                status="running"
            )
        except Exception as e:
            logger.error(f"Failed to create session: {e}")
            await context.abort(grpc.StatusCode.INTERNAL, str(e))

    async def CloseSession(
        self, request: terminal_pb2.CloseSessionRequest, context: grpc.aio.ServicerContext
    ) -> terminal_pb2.CloseSessionResponse:
        """Close a terminal session."""
        try:
            success = await self.pty_manager.close_session(request.session_id)
            logger.info(f"Closed terminal session: {request.session_id}")
            return terminal_pb2.CloseSessionResponse(success=success)
        except Exception as e:
            logger.error(f"Failed to close session: {e}")
            return terminal_pb2.CloseSessionResponse(success=False)

    async def ResizeTerminal(
        self, request: terminal_pb2.ResizeRequest, context: grpc.aio.ServicerContext
    ) -> terminal_pb2.ResizeResponse:
        """Resize terminal window."""
        try:
            session = self.pty_manager.get_session(request.session_id)
            if not session:
                await context.abort(grpc.StatusCode.NOT_FOUND, "Session not found")
                return

            await session.resize(request.rows, request.cols)
            return terminal_pb2.ResizeResponse(success=True)
        except Exception as e:
            logger.error(f"Failed to resize terminal: {e}")
            return terminal_pb2.ResizeResponse(success=False)

    async def Stream(
        self,
        request_iterator: AsyncIterator[terminal_pb2.TerminalRequest],
        context: grpc.aio.ServicerContext
    ) -> AsyncIterator[terminal_pb2.TerminalResponse]:
        """
        Bidirectional streaming for terminal I/O.

        Client sends: input data, resize commands
        Server sends: output data, errors, exit notifications
        """
        session_id = None
        session = None
        output_seq = 0
        output_task = None

        try:
            # Process incoming requests
            async for request in request_iterator:
                if not session_id:
                    session_id = request.session_id
                    session = self.pty_manager.get_session(session_id)

                    if not session:
                        yield terminal_pb2.TerminalResponse(
                            session_id=session_id,
                            error=terminal_pb2.ErrorData(message="Session not found")
                        )
                        return

                    logger.info(f"Started gRPC stream for session: {session_id}")

                    # Start output streaming task
                    output_task = asyncio.create_task(
                        self._stream_output(session, session_id, context)
                    )

                # Handle input
                if request.HasField('input'):
                    try:
                        await session.write_input(request.input.data)
                    except Exception as e:
                        logger.error(f"Failed to write input: {e}")
                        yield terminal_pb2.TerminalResponse(
                            session_id=session_id,
                            error=terminal_pb2.ErrorData(message=str(e))
                        )

                # Handle resize
                elif request.HasField('resize'):
                    try:
                        await session.resize(request.resize.rows, request.resize.cols)
                    except Exception as e:
                        logger.error(f"Failed to resize: {e}")

            # Wait for output task to complete
            if output_task:
                async for response in output_task:
                    yield response

        except asyncio.CancelledError:
            logger.info(f"Stream cancelled for session: {session_id}")
        except Exception as e:
            logger.error(f"Stream error: {e}")
            if session_id:
                yield terminal_pb2.TerminalResponse(
                    session_id=session_id,
                    error=terminal_pb2.ErrorData(message=str(e))
                )
        finally:
            if output_task and not output_task.done():
                output_task.cancel()
            logger.info(f"Stream ended for session: {session_id}")

    async def _stream_output(
        self, session, session_id: str, context: grpc.aio.ServicerContext
    ) -> AsyncIterator[terminal_pb2.TerminalResponse]:
        """Stream output from terminal session."""
        seq = 0

        try:
            while session.is_alive() and not context.cancelled():
                # Get output since last sequence
                output, new_seq = session.get_output_since(seq)

                if output:
                    yield terminal_pb2.TerminalResponse(
                        session_id=session_id,
                        output=terminal_pb2.OutputData(
                            data=output,
                            seq=new_seq
                        )
                    )
                    seq = new_seq

                # Small delay to avoid busy-waiting
                await asyncio.sleep(0.05)

            # Send exit notification
            if session.exit_code is not None:
                yield terminal_pb2.TerminalResponse(
                    session_id=session_id,
                    exit=terminal_pb2.ExitData(exit_code=session.exit_code)
                )

        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Output stream error: {e}")
            yield terminal_pb2.TerminalResponse(
                session_id=session_id,
                error=terminal_pb2.ErrorData(message=str(e))
            )
