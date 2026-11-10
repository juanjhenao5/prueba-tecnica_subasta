"""
Arranca el servidor Flask en un hilo/proceso y ejecuta la prueba de 50 pujas concurrentes (HU-6).
"""
import threading
import time
import requests
from werkzeug.serving import make_server

from app import create_app
import test_concurrencia

class ServerThread(threading.Thread):
    def __init__(self, app, port=5000):
        super().__init__()
        self.server = make_server('127.0.0.1', port, app, threaded=True)
        self.ctx = app.app_context()
        self.ctx.push()

    def run(self):
        self.server.serve_forever()

    def shutdown(self):
        self.server.shutdown()

def main():
    print("Iniciando servidor de pruebas en http://127.0.0.1:5000...")
    app = create_app()
    server = ServerThread(app, port=5000)
    server.start()

    # Esperar a que el servidor esté listo
    time.sleep(1.5)

    try:
        # Verificar endpoint de salud
        r = requests.get("http://127.0.0.1:5000/")
        assert r.status_code == 200, f"Error iniciando servidor: {r.status_code}"
        print("Servidor listo y respondiendo correctamente.\n")

        # Ejecutar prueba de concurrencia
        test_concurrencia.BASE_URL = "http://127.0.0.1:5000/api/subastas"
        test_concurrencia.main()
    finally:
        print("\nDeteniendo servidor de pruebas...")
        server.shutdown()
        server.join()
        print("Servidor detenido.")

if __name__ == '__main__':
    main()
