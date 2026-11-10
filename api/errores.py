from flask import jsonify


def registrar_manejadores_errores(app):
    """Manejadores de errores globales (HU-8): mensajes claros, sin datos técnicos."""

    @app.errorhandler(400)
    def solicitud_invalida(error):
        return jsonify({"success": False, "error": "Solicitud inválida."}), 400

    @app.errorhandler(404)
    def no_encontrado(error):
        return jsonify({"success": False, "error": "Recurso no encontrado."}), 404

    @app.errorhandler(405)
    def metodo_no_permitido(error):
        return jsonify({"success": False, "error": "Método no permitido."}), 405

    @app.errorhandler(500)
    def error_interno(error):
        return jsonify({"success": False, "error": "Error interno del servidor."}), 500
