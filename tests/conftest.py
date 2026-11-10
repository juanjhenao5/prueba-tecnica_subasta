import pytest
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from app import create_app
from extensions import db
from models import Subasta, Puja

@pytest.fixture
def app():
    app = create_app("config.TestingConfig")
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()

@pytest.fixture
def client(app):
    return app.test_client()

@pytest.fixture
def subasta_activa(app):
    """Crea una subasta activa estándar para pruebas."""
    with app.app_context():
        sub = Subasta(
            titulo="Subasta de Prueba Automatizada",
            descripcion="Articulo de prueba con garantias",
            precio_inicial=Decimal("100.00"),
            incremento_minimo=Decimal("10.00"),
            fecha_fin=datetime.now(timezone.utc) + timedelta(days=2),
            extensiones_aplicadas=0
        )
        db.session.add(sub)
        db.session.commit()
        return sub.id
