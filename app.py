from api.errores import registrar_manejadores_errores
from api.ruta_de_subastas import subasta_bp
from extensions import db, migrate
from flask import Flask, render_template


def create_app(config_name="config.DevelopmentConfig"):
    app = Flask(__name__)
    app.config.from_object(config_name)

    db.init_app(app)
    migrate.init_app(app, db)

    app.register_blueprint(subasta_bp)
    registrar_manejadores_errores(app)

    # Importar modelos para que SQLAlchemy los registre y crear tablas
    with app.app_context():
        from models.subasta import Subasta  # noqa: F401
        from models.puja import Puja  # noqa: F401
        db.create_all()

    # HU-8: Ruta para servir la interfaz web
    @app.route("/")
    def index():
        return render_template("index.html")

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(debug=True, port=5000)