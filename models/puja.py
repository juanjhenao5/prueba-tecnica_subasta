from datetime import datetime, timezone
from extensions import db


class Puja(db.Model):
    __tablename__ = "pujas"
    __table_args__ = (
        db.Index("idx_pujas_subasta_monto", "subasta_id", "monto"),
    )

    id = db.Column(db.Integer, primary_key=True)
    subasta_id = db.Column(db.Integer, db.ForeignKey("subastas.id"), nullable=False, index=True)
    nombre_postor = db.Column(db.String(100), nullable=False)
    monto = db.Column(db.Numeric(12, 2), nullable=False)
    creada_en = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    # Clave de idempotencia para prevenir duplicados por mala red o reintentos
    idempotency_key = db.Column(db.String(64), unique=True, nullable=True, index=True)

    def serializar(self):
        """Convierte el modelo a diccionario JSON-serializable."""
        return {
            "id": self.id,
            "nombre_postor": self.nombre_postor,
            "monto": str(self.monto),
            "creada_en": self.creada_en.isoformat() if self.creada_en else None,
            "idempotency_key": self.idempotency_key,
        }
