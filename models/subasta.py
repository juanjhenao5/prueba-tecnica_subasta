from datetime import datetime, timezone
from extensions import db


class Subasta(db.Model):
    __tablename__ = "subastas"
    id = db.Column(db.Integer, primary_key=True)

    titulo = db.Column(db.String(100), nullable=False)  # HU-1: 1 a 100 caracteres
    descripcion = db.Column(db.Text, nullable=True)

    # HU-4: Numeric(12, 2) asegura 2 decimales exactos en la BD,
    # y en Python SQLAlchemy lo mapea usando Decimal (nunca float).
    precio_inicial = db.Column(db.Numeric(12, 2), nullable=False)
    incremento_minimo = db.Column(db.Numeric(12, 2), nullable=False)

    fecha_fin = db.Column(db.DateTime, nullable=False)  # HU-1: fecha/hora de fin
    creada_en = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    # HU-5: ganador y precio final (se llenan al cerrar la subasta)
    ganador = db.Column(db.String(100), nullable=True)
    precio_final = db.Column(db.Numeric(12, 2), nullable=True)

    # HU-11: conteo de extensiones anti-sniping (máximo 10)
    extensiones_aplicadas = db.Column(db.Integer, default=0, nullable=False)

    # Relación con las pujas
    pujas = db.relationship(
        "Puja", backref="subasta", lazy=True, cascade="all, delete-orphan"
    )

    @property
    def fecha_fin_utc(self):
        """Retorna fecha_fin garantizando que sea timezone-aware en UTC."""
        if self.fecha_fin is None:
            return None
        if self.fecha_fin.tzinfo is None:
            return self.fecha_fin.replace(tzinfo=timezone.utc)
        return self.fecha_fin.astimezone(timezone.utc)

    def esta_abierta(self):
        """Verifica si la subasta sigue abierta según la fecha actual del servidor."""
        if not self.fecha_fin:
            return False
        return datetime.now(timezone.utc) < self.fecha_fin_utc

    def serializar(self):
        """Convierte el modelo a diccionario JSON-serializable."""
        abierta = self.esta_abierta()
        return {
            "id": self.id,
            "titulo": self.titulo,
            "descripcion": self.descripcion,
            "precio_inicial": str(self.precio_inicial),
            "incremento_minimo": str(self.incremento_minimo),
            "fecha_fin": self.fecha_fin_utc.isoformat() if self.fecha_fin else None,
            "creada_en": self.creada_en.isoformat() if self.creada_en else None,
            "esta_abierta": abierta,
            "estado": "abierta" if abierta else "cerrada",
            "ganador": self.ganador,
            "precio_final": str(self.precio_final) if self.precio_final else None,
            "extensiones_aplicadas": self.extensiones_aplicadas or 0,
            "max_extensiones_alcanzadas": (self.extensiones_aplicadas or 0) >= 10,
        }