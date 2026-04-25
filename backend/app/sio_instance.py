"""Shared Socket.IO server instance to avoid circular imports."""
import socketio

sio = socketio.AsyncServer(async_mode="asgi", cors_allowed_origins="*")
