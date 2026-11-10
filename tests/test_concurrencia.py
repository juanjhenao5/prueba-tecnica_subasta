"""
Prueba automática de concurrencia: 50 pujas simultáneas (HU-6).
"""
import concurrent.futures
import threading
import time
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import requests
from werkzeug.serving import make_server

from app import create_app

class ServerThread(threading.Thread):
    def __init__(self, app, host='127.0.0.1', port=5005):
        super().__init__()
        self.server = make_server(host, port, app, threaded=True)
        self.ctx = app.app_context()
        self.ctx.push()

    def run(self):
        self.server.serve_forever()

    def shutdown(self):
        self.server.shutdown()

def test_concurrencia_50_pujas_simultaneas():
    """HU-6: 50 pujas simultáneas con resultado estrictamente consistente."""
    port = 5005
    base_url = f"http://127.0.0.1:{port}/api/subastas"

    app = create_app("config.DevelopmentConfig")
    server = ServerThread(app, port=port)
    server.start()
    time.sleep(1.0)

    try:
        # 1. Crear subasta
        fecha_fin = (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat()
        resp = requests.post(base_url, json={
            "titulo": "Prueba Automatizada de Concurrencia",
            "descripcion": "Test con 50 hilos simultaneos",
            "precio_inicial": "100.00",
            "incremento_minimo": "1.00",
            "fecha_fin": fecha_fin
        }, timeout=10)
        assert resp.status_code == 201
        subasta_id = resp.json()["data"]["id"]

        # 2. Enviar 50 pujas simultáneas
        def enviar_puja(i):
            postor = "Postor_Alfa" if i % 2 == 0 else "Postor_Beta"
            monto = f"{100 + i}.00"
            r = requests.post(
                f"{base_url}/{subasta_id}/pujas",
                json={"nombre": postor, "monto": monto},
                timeout=30
            )
            return {"status": r.status_code, "monto": monto, "postor": postor}

        resultados = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=50) as executor:
            futuros = [executor.submit(enviar_puja, i) for i in range(1, 51)]
            for f in concurrent.futures.as_completed(futuros):
                resultados.append(f.result())

        exitosas = [r for r in resultados if r["status"] == 201]
        rechazadas = [r for r in resultados if r["status"] == 400]
        errores = [r for r in resultados if r["status"] not in (201, 400)]

        # Verificaciones fundamentales de concurrencia:
        # 1. Cero caídas o errores de servidor (500)
        assert len(errores) == 0, f"Hubo errores inesperados: {errores}"
        assert len(exitosas) > 0, "Al menos algunas pujas deben haber sido aceptadas"

        # 2. Consultar el estado final registrado en la base de datos
        detalle = requests.get(f"{base_url}/{subasta_id}", timeout=10).json()["data"]
        pujas_aceptadas = detalle["pujas"]

        # Invertir para orden cronológico ascendente
        montos_cronologicos = [Decimal(p["monto"]) for p in reversed(pujas_aceptadas)]

        # 3. Montos estrictamente crecientes
        es_estrictamente_creciente = all(
            montos_cronologicos[i] < montos_cronologicos[i + 1]
            for i in range(len(montos_cronologicos) - 1)
        )
        assert es_estrictamente_creciente is True, "Los montos aceptados no fueron estrictamente crecientes"

        # 4. Sin montos duplicados
        assert len(montos_cronologicos) == len(set(montos_cronologicos)), "Hay montos duplicados aceptados"

        # 5. El precio actual coincide con la última puja aceptada
        assert Decimal(detalle["precio_actual"]) == montos_cronologicos[-1]

    finally:
        server.shutdown()
        server.join()
