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
        # Salvaguarda de migración en SQLite para columnas añadidas
        try:
            from sqlalchemy import inspect, text
            inspector = inspect(db.engine)
            tablas = inspector.get_table_names()
            if "pujas" in tablas:
                cols = [c["name"] for c in inspector.get_columns("pujas")]
                if "idempotency_key" not in cols:
                    db.session.execute(text("ALTER TABLE pujas ADD COLUMN idempotency_key VARCHAR(64)"))
                    db.session.commit()
            if "subastas" in tablas:
                cols = [c["name"] for c in inspector.get_columns("subastas")]
                if "extensiones_aplicadas" not in cols:
                    db.session.execute(text("ALTER TABLE subastas ADD COLUMN extensiones_aplicadas INTEGER DEFAULT 0 NOT NULL"))
                    db.session.commit()
        except Exception:
            pass

    # HU-8: Ruta para servir la interfaz web
    @app.route("/")
    def index():
        return render_template("index.html")

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(debug=True, port=5000)