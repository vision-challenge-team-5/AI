from flask import Flask
from flask_cors import CORS  # Import the CORS extension

def create_app():
    app = Flask(__name__)
    CORS(app)  # Enable CORS for all routes

    from .views import main_views  # Import your blueprint
    app.register_blueprint(main_views.bp)  # Register the blueprint

    return app
