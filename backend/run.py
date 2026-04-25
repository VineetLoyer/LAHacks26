import os
import uvicorn

if __name__ == "__main__":
    # Import socket_events to register handlers
    import app.socket_events  # noqa: F401
    from app.main import sio_app

    port = int(os.getenv("PORT", 8000))
    uvicorn.run(sio_app, host="0.0.0.0", port=port, reload=False)
