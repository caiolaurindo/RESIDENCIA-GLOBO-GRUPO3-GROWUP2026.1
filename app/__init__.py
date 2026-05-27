from flask import Flask
from flask_cors import CORS

from app.routes.srt_routes import srt_bp
from app.routes.validacao_routes import validacao_bp


def create_app():

    app = Flask(__name__)

    CORS(app)

    app.register_blueprint(srt_bp)
    app.register_blueprint(validacao_bp)

    return app