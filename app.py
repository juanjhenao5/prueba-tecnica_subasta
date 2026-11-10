from api import registrar_manejadores_errores, subasta_bp
from extensions import db, migrate
from flask import Flask, render_template
from models import Puja, Subasta


def create_app(config_name="config.DevelopmentConfig"):
    app = Flask(__name__)
    app.config.from_object(config_name)

    db.init_app(app)
    migrate.init_app(app, db)

    app.register_blueprint(subasta_bp)
    registrar_manejadores_errores(app)

    # Crear tablas en el contexto de la aplicación
    with app.app_context():
        db.create_all()

    # HU-8: Ruta para servir la interfaz web
    @app.route("/")
    def index():
        return render_template("index.html")

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(debug=True, port=5000)