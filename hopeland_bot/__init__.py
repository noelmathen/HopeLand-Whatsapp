from flask import Flask
from .config import init_logging, warn_if_missing_secrets
from .routes import bp as routes_bp
from .media import init_media_cache

def create_app() -> Flask:
    init_logging()
    warn_if_missing_secrets()
    init_media_cache()
    app = Flask(__name__)
    app.register_blueprint(routes_bp)

    @app.errorhandler(Exception)
    def _unhandled(e):
        import logging
        logging.exception("Unhandled error: %s", e)
        return {"status": "error", "detail": str(e)}, 200

    return app
