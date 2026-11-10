from flask import Blueprint, jsonify, request
from services.servicio_subasta import SubastaService

subasta_bp = Blueprint("subasta_bp", __name__, url_prefix="/api/subastas")


# ── HU-1: Crear subasta ─────────────────────────────────────────────

@subasta_bp.route("", methods=["POST"])
def crear_subasta():
    data = request.get_json() or {}

    campos_requeridos = ["titulo", "precio_inicial", "incremento_minimo", "fecha_fin"]
    faltantes = [c for c in campos_requeridos if c not in data or data[c] is None]
    if faltantes:
        return (
            jsonify({"success": False, "error": f"Faltan campos: {', '.join(faltantes)}"}),
            400,
        )

    try:
        subasta = SubastaService.crear_subasta(
            titulo=data["titulo"],
            descripcion=data.get("descripcion", ""),
            precio_inicial=data["precio_inicial"],
            incremento_minimo=data["incremento_minimo"],
            fecha_fin_str=data["fecha_fin"],
        )
        return (
            jsonify({
                "success": True,
                "mensaje": "Subasta creada exitosamente",
                "data": subasta.serializar(),
            }),
            201,
        )
    except ValueError as e:
        status_code = 404 if "no existe" in str(e).lower() else 400
        return jsonify({"success": False, "error": str(e)}), status_code
    except Exception:
        return jsonify({"success": False, "error": "Error al crear la subasta."}), 500


# ── HU-2: Listar subastas ───────────────────────────────────────────

@subasta_bp.route("", methods=["GET"])
def listar_subastas():
    try:
        subastas = SubastaService.listar_subastas()
        return jsonify({"success": True, "data": subastas}), 200
    except Exception:
        return jsonify({"success": False, "error": "Error al obtener las subastas."}), 500


# ── HU-2: Detalle de subasta ────────────────────────────────────────

@subasta_bp.route("/<int:subasta_id>", methods=["GET"])
def detalle_subasta(subasta_id):
    try:
        detalle = SubastaService.obtener_detalle(subasta_id)
        return jsonify({"success": True, "data": detalle}), 200
    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), 404
    except Exception:
        return jsonify({"success": False, "error": "Error al obtener el detalle."}), 500


# ── HU-3: Realizar puja ─────────────────────────────────────────────

@subasta_bp.route("/<int:subasta_id>/pujas", methods=["POST"])
def pujar(subasta_id):
    data = request.get_json() or {}
    nombre = data.get("nombre")
    monto = data.get("monto")
    idempotency_key = request.headers.get("Idempotency-Key") or data.get("idempotency_key")

    if not nombre or monto is None:
        return (
            jsonify({"success": False, "error": "Faltan campos: nombre, monto"}),
            400,
        )

    try:
        puja = SubastaService.registrar_puja(
            subasta_id, nombre, monto, idempotency_key=idempotency_key
        )
        datos_puja = puja.serializar()
        se_extendio = getattr(puja, "se_extendio", False)
        ext_count = getattr(puja, "extensiones_aplicadas", 0)
        es_idempotente = getattr(puja, "es_idempotente", False)
        datos_puja["se_extendio"] = se_extendio
        datos_puja["extensiones_aplicadas"] = ext_count
        datos_puja["idempotente"] = es_idempotente

        if es_idempotente:
            mensaje = "Puja ya registrada previamente (Idempotente)"
            status_code = 200
        else:
            mensaje = "Puja registrada exitosamente"
            if se_extendio:
                mensaje += f". Tiempo extendido por 60s (Extensión {ext_count}/10)"
            status_code = 201

        return (
            jsonify({
                "success": True,
                "mensaje": mensaje,
                "data": datos_puja,
            }),
            status_code,
        )
    except ValueError as e:
        status_code = 404 if "no existe" in str(e).lower() else 400
        return jsonify({"success": False, "error": str(e)}), status_code
    except Exception:
        return jsonify({"success": False, "error": "Error al registrar la puja."}), 500