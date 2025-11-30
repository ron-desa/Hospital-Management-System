from flask import Flask
import os

def create_app():
    app = Flask(__name__)
    app.config["SECRET_KEY"] = "change-this-secret-key"
    base_dir = os.path.dirname(__file__)
    app.config["DATABASE"] = os.path.join(base_dir, "instance", "hospital.db")

    from controllers.routes import main_bp
    app.register_blueprint(main_bp)

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(debug=True)
