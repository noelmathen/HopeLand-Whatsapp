# hopeland_bot/__init__.py
from flask import Flask
from .config import init_logging, warn_if_missing_secrets
from .routes import bp as routes_bp
from .scheduler import start_scheduler

def create_app() -> Flask:
    init_logging()
    warn_if_missing_secrets()
    app = Flask(__name__)
    app.register_blueprint(routes_bp)

    # start digest scheduler (no-op if disabled)
    start_scheduler()

    @app.errorhandler(Exception)
    def _unhandled(e):
        import logging
        logging.exception("Unhandled error: %s", e)
        return {"status": "error", "detail": str(e)}, 200

    return app
