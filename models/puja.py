from datetime import datetime, timezone
from extensions import db


class Puja(db.Model):
    __tablename__ = "pujas"
    id = db.Column(db.Integer, primary_key=True)
    subasta_id = db.Column(db.Integer, db.ForeignKey("subastas.id"), nullable=False)
    nombre_postor = db.Column(db.String(100), nullable=False)
    monto = db.Column(db.Numeric(12, 2), nullable=False)
    creada_en = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def serializar(self):
        """Convierte el modelo a diccionario JSON-serializable."""
        return {
            "id": self.id,
            "nombre_postor": self.nombre_postor,
            "monto": str(self.monto),
            "creada_en": self.creada_en.isoformat() if self.creada_en else None,
        }
