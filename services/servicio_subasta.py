import threading
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation

from extensions import db
from models.puja import Puja
from models.subasta import Subasta

# HU-6: Sincronización para garantizar concurrencia consistente
_locks_lock = threading.Lock()
_subasta_locks = {}


def _obtener_lock_subasta(subasta_id):
    """Obtiene o crea un Lock específico para la subasta indicada."""
    with _locks_lock:
        if subasta_id not in _subasta_locks:
            _subasta_locks[subasta_id] = threading.Lock()
        return _subasta_locks[subasta_id]


class SubastaService:

    # ── Helpers ──────────────────────────────────────────────────────

    @staticmethod
    def _validar_decimales(valor, nombre_campo):
        """Valida que un valor sea numérico, positivo y con máximo 2 decimales (HU-4)."""
        try:
            d = Decimal(str(valor))
        except (InvalidOperation, ValueError, TypeError):
            raise ValueError(f"{nombre_campo} debe ser un valor numérico válido.")

        if d <= 0:
            raise ValueError(f"{nombre_campo} debe ser mayor a 0.")

        if d.as_tuple().exponent < -2:
            raise ValueError(f"{nombre_campo} debe tener máximo 2 decimales.")

        return d

    @staticmethod
    def _verificar_cierre(subasta):
        """HU-5: si la subasta expiró y no tiene ganador registrado, registrarlo.
        Funciona de forma 'lazy': se ejecuta al consultar la subasta.
        Correcto aunque nadie esté mirando y sobrevive reinicios."""
        if not subasta.esta_abierta() and subasta.ganador is None:
            mejor_puja = (
                Puja.query.filter_by(subasta_id=subasta.id)
                .order_by(Puja.monto.desc())
                .first()
            )
            if mejor_puja:
                subasta.ganador = mejor_puja.nombre_postor
                subasta.precio_final = mejor_puja.monto
            else:
                subasta.ganador = "DESIERTA"
                subasta.precio_final = None

            try:
                db.session.commit()
            except Exception:
                db.session.rollback()

    # ── HU-1: Crear subasta ─────────────────────────────────────────

    @staticmethod
    def crear_subasta(titulo, descripcion, precio_inicial, incremento_minimo, fecha_fin_str):
        # Validar título (1 a 100 caracteres)
        if not titulo or not titulo.strip():
            raise ValueError("El título es obligatorio.")
        titulo = titulo.strip()
        if len(titulo) > 100:
            raise ValueError("El título no puede exceder 100 caracteres.")

        # Validar precios (HU-4: positivos, máx 2 decimales)
        precio_decimal = SubastaService._validar_decimales(precio_inicial, "El precio inicial")
        incremento_decimal = SubastaService._validar_decimales(incremento_minimo, "El incremento mínimo")

        # Validar fecha de fin
        try:
            fecha_fin = datetime.fromisoformat(fecha_fin_str)
        except (ValueError, TypeError):
            raise ValueError("La fecha de fin no tiene un formato válido (use ISO 8601).")

        if fecha_fin.tzinfo is None:
            fecha_fin = fecha_fin.replace(tzinfo=timezone.utc)

        ahora = datetime.now(timezone.utc)

        if fecha_fin <= ahora:
            raise ValueError("La fecha de fin debe ser en el futuro.")

        if fecha_fin > ahora + timedelta(days=7):
            raise ValueError("La fecha de fin no puede ser mayor a 7 días desde ahora.")

        nueva = Subasta(
            titulo=titulo,
            descripcion=descripcion.strip() if descripcion else None,
            precio_inicial=precio_decimal,
            incremento_minimo=incremento_decimal,
            fecha_fin=fecha_fin,
        )
        try:
            db.session.add(nueva)
            db.session.commit()
        except Exception:
            db.session.rollback()
            raise
        return nueva

    # ── HU-2: Listar subastas ───────────────────────────────────────

    @staticmethod
    def listar_subastas():
        subastas = Subasta.query.order_by(Subasta.fecha_fin.desc()).all()
        resultado = []

        for s in subastas:
            SubastaService._verificar_cierre(s)

            mejor_puja = (
                Puja.query.filter_by(subasta_id=s.id)
                .order_by(Puja.monto.desc())
                .first()
            )

            data = s.serializar()
            data["precio_actual"] = str(mejor_puja.monto) if mejor_puja else str(s.precio_inicial)
            data["mejor_postor"] = mejor_puja.nombre_postor if mejor_puja else None
            data["total_pujas"] = Puja.query.filter_by(subasta_id=s.id).count()
            resultado.append(data)

        return resultado

    # ── HU-2: Detalle de subasta ────────────────────────────────────

    @staticmethod
    def obtener_detalle(subasta_id):
        subasta = db.session.get(Subasta, subasta_id)
        if not subasta:
            raise ValueError("La subasta no existe.")

        SubastaService._verificar_cierre(subasta)

        # Historial de pujas (más reciente primero)
        pujas = (
            Puja.query.filter_by(subasta_id=subasta_id)
            .order_by(Puja.creada_en.desc())
            .all()
        )

        mejor_puja = (
            Puja.query.filter_by(subasta_id=subasta_id)
            .order_by(Puja.monto.desc())
            .first()
        )

        data = subasta.serializar()
        data["precio_actual"] = str(mejor_puja.monto) if mejor_puja else str(subasta.precio_inicial)
        data["mejor_postor"] = mejor_puja.nombre_postor if mejor_puja else None
        data["total_pujas"] = len(pujas)
        data["pujas"] = [p.serializar() for p in pujas]

        # Tiempo restante (HU-10: basado estrictamente en el reloj del servidor)
        ahora = datetime.now(timezone.utc)
        data["servidor_hora_utc"] = ahora.isoformat()
        if subasta.esta_abierta():
            delta = subasta.fecha_fin_utc - ahora
            segundos = max(0, int(delta.total_seconds()))
            data["tiempo_restante_segundos"] = segundos
            data["tiempo_restante"] = segundos
        else:
            data["tiempo_restante_segundos"] = 0
            data["tiempo_restante"] = 0

        return data

    # ── HU-3: Registrar puja ────────────────────────────────────────

    @staticmethod
    def registrar_puja(subasta_id, nombre_postor, monto):
        # Validar nombre
        if not nombre_postor or not str(nombre_postor).strip():
            raise ValueError("El nombre del postor es obligatorio.")
        nombre_postor = str(nombre_postor).strip()

        # Validar monto (HU-4)
        monto_decimal = SubastaService._validar_decimales(monto, "El monto")

        # HU-6: Sincronización atómica por subasta para concurrencia consistente
        lock = _obtener_lock_subasta(subasta_id)
        with lock:
            # Forzar recarga desde BD para ver commits de otros hilos
            db.session.expire_all()

            subasta = db.session.get(Subasta, subasta_id)
            if not subasta:
                raise ValueError("La subasta no existe.")

            if not subasta.esta_abierta():
                raise ValueError("La subasta ya ha finalizado.")

            # Obtener mejor puja actual confirmada en la BD
            ultima_puja = (
                Puja.query.filter_by(subasta_id=subasta_id)
                .order_by(Puja.monto.desc())
                .first()
            )

            if ultima_puja:
                # HU-3: el postor no puede ser el mejor postor actual
                if ultima_puja.nombre_postor == nombre_postor:
                    raise ValueError("Ya eres el mejor postor actual. No puedes pujar contra ti mismo.")
                precio_minimo = ultima_puja.monto + subasta.incremento_minimo
            else:
                # Primera puja: al menos el precio inicial
                precio_minimo = subasta.precio_inicial

            if monto_decimal < precio_minimo:
                raise ValueError(f"El monto debe ser al menos {precio_minimo}.")

            # HU-11: Extensión anti-sniping si la puja entra en los últimos 60 segundos
            ahora = datetime.now(timezone.utc)
            segundos_restantes = (subasta.fecha_fin_utc - ahora).total_seconds()
            se_extendio = False

            # Extensión si quedan <= 60s y no se ha superado el máximo de 10 extensiones
            if 0 < segundos_restantes <= 60 and (subasta.extensiones_aplicadas or 0) < 10:
                subasta.fecha_fin = ahora + timedelta(seconds=60)
                subasta.extensiones_aplicadas = (subasta.extensiones_aplicadas or 0) + 1
                se_extendio = True

            nueva_puja = Puja(
                subasta_id=subasta_id,
                nombre_postor=nombre_postor,
                monto=monto_decimal,
            )
            nueva_puja.se_extendio = se_extendio
            nueva_puja.extensiones_aplicadas = subasta.extensiones_aplicadas

            try:
                db.session.add(nueva_puja)
                db.session.commit()
            except Exception:
                db.session.rollback()
                raise

            return nueva_puja