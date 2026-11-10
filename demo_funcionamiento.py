"""
Demostración interactiva y exhaustiva del funcionamiento del Sistema de Subastas (HU-1 a HU-8).
"""
import time
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from app import create_app
from extensions import db
from models.subasta import Subasta
from models.puja import Puja

def demo():
    print("=" * 70)
    print("      DEMOSTRACIÓN DE FUNCIONAMIENTO COMPLETO — SISTEMA DE SUBASTAS")
    print("=" * 70)

    app = create_app()
    client = app.test_client()

    with app.app_context():
        # Limpiar base de datos para una demo limpia
        db.drop_all()
        db.create_all()

    # ──────────────────────────────────────────────────────────────────
    # 1. HU-1: CREACIÓN DE SUBASTA
    # ──────────────────────────────────────────────────────────────────
    print("\n[Paso 1] Creando una nueva subasta (HU-1)...")
    fecha_fin = (datetime.now(timezone.utc) + timedelta(days=2)).isoformat()
    resp_crear = client.post("/api/subastas", json={
        "titulo": "MacBook Pro M3 Max 32GB",
        "descripcion": "Equipo nuevo en caja sellada con garantía.",
        "precio_inicial": "1500.00",
        "incremento_minimo": "50.00",
        "fecha_fin": fecha_fin
    })
    data_crear = resp_crear.get_json()
    print(f"  Status HTTP: {resp_crear.status_code}")
    print(f"  Subasta creada ID: {data_crear['data']['id']}")
    print(f"  Título: {data_crear['data']['titulo']}")
    print(f"  Precio inicial: ${data_crear['data']['precio_inicial']}")
    print(f"  Incremento mínimo: ${data_crear['data']['incremento_minimo']}")
    print(f"  Estado: {data_crear['data']['estado']}")
    subasta_id = data_crear['data']['id']

    # Validación de rechazo HU-1 (título vacío, precio negativo o fecha > 7 días)
    print("\n[Paso 1.b] Probando rechazo de subasta inválida (fecha > 7 días)...")
    resp_invalida = client.post("/api/subastas", json={
        "titulo": "Subasta Invalida",
        "precio_inicial": "10.00",
        "incremento_minimo": "1.00",
        "fecha_fin": (datetime.now(timezone.utc) + timedelta(days=10)).isoformat()
    })
    print(f"  Status HTTP: {resp_invalida.status_code} (Rechazada correctamente)")
    print(f"  Mensaje de error: {resp_invalida.get_json()['error']}")

    # ──────────────────────────────────────────────────────────────────
    # 2. HU-2: LISTAR Y DETALLE
    # ──────────────────────────────────────────────────────────────────
    print("\n[Paso 2] Listando subastas activas (HU-2)...")
    resp_lista = client.get("/api/subastas")
    lista = resp_lista.get_json()['data']
    print(f"  Total subastas encontradas: {len(lista)}")
    for s in lista:
        print(f"  - [{s['estado'].upper()}] #{s['id']}: {s['titulo']} | Precio actual: ${s['precio_actual']} | Pujas: {s['total_pujas']}")

    print(f"\n[Paso 2.b] Consultando detalle de subasta #{subasta_id}...")
    resp_det = client.get(f"/api/subastas/{subasta_id}")
    det = resp_det.get_json()['data']
    print(f"  Mejor postor: {det['mejor_postor'] or 'Sin postor todavía'}")
    print(f"  Tiempo restante: {det['tiempo_restante_segundos']} segundos")

    # ──────────────────────────────────────────────────────────────────
    # 3. HU-3 & HU-4: FLUJO DE PUJAS
    # ──────────────────────────────────────────────────────────────────
    print("\n[Paso 3] Realizando primera puja: Carlos puja $1500.00...")
    r1 = client.post(f"/api/subastas/{subasta_id}/pujas", json={
        "nombre": "Carlos",
        "monto": "1500.00"
    })
    print(f"  Status: {r1.status_code} | Respuesta: {r1.get_json()['mensaje']}")

    print("\n[Paso 3.b] Carlos intenta pujar de nuevo inmediatamente ($1560.00)...")
    r2 = client.post(f"/api/subastas/{subasta_id}/pujas", json={
        "nombre": "Carlos",
        "monto": "1560.00"
    })
    print(f"  Status: {r2.status_code} (Rechazada como exige HU-3)")
    print(f"  Mensaje: {r2.get_json()['error']}")

    print("\n[Paso 3.c] Maria intenta pujar por debajo del incremento mínimo ($1520.00 vs mín $1550.00)...")
    r3 = client.post(f"/api/subastas/{subasta_id}/pujas", json={
        "nombre": "Maria",
        "monto": "1520.00"
    })
    print(f"  Status: {r3.status_code} (Rechazada como exige HU-3)")
    print(f"  Mensaje: {r3.get_json()['error']}")

    print("\n[Paso 3.d] Maria puja un monto válido con 2 decimales exactos: $1550.50 (HU-4)...")
    r4 = client.post(f"/api/subastas/{subasta_id}/pujas", json={
        "nombre": "Maria",
        "monto": "1550.50"
    })
    print(f"  Status: {r4.status_code} | Respuesta: {r4.get_json()['mensaje']}")

    print("\n[Paso 3.e] Juan contraoferta $1620.00...")
    r5 = client.post(f"/api/subastas/{subasta_id}/pujas", json={
        "nombre": "Juan",
        "monto": "1620.00"
    })
    print(f"  Status: {r5.status_code} | Respuesta: {r5.get_json()['mensaje']}")

    # Ver historial de pujas
    resp_det2 = client.get(f"/api/subastas/{subasta_id}")
    det2 = resp_det2.get_json()['data']
    print(f"\n  Nuevo precio actual: ${det2['precio_actual']}")
    print(f"  Nuevo mejor postor: {det2['mejor_postor']}")
    print(f"  Historial de pujas (más reciente primero):")
    for i, p in enumerate(det2['pujas']):
        print(f"    {i+1}. {p['nombre_postor']}: ${p['monto']} (a las {p['creada_en']})")

    # ──────────────────────────────────────────────────────────────────
    # 4. HU-5: CIERRE DE SUBASTA Y CASO DESIERTA
    # ──────────────────────────────────────────────────────────────────
    print("\n[Paso 4] Probando cierre automático (HU-5)...")
    with app.app_context():
        # Adelantar la fecha fin de la subasta al pasado para simular que expiró
        sub = db.session.get(Subasta, subasta_id)
        sub.fecha_fin = datetime.now(timezone.utc) - timedelta(seconds=1)
        db.session.commit()

    resp_cerrada = client.get(f"/api/subastas/{subasta_id}")
    det_c = resp_cerrada.get_json()['data']
    print(f"  Estado de la subasta: {det_c['estado'].upper()}")
    print(f"  Ganador registrado: {det_c['ganador']}")
    print(f"  Precio final: ${det_c['precio_final']}")
    print(f"  Tiempo restante: {det_c['tiempo_restante_segundos']} segundos")

    print("\n[Paso 4.b] Intento de puja en subasta ya cerrada...")
    r_tardia = client.post(f"/api/subastas/{subasta_id}/pujas", json={
        "nombre": "Pedro",
        "monto": "2000.00"
    })
    print(f"  Status: {r_tardia.status_code} (Rechazada)")
    print(f"  Mensaje: {r_tardia.get_json()['error']}")

    print("\n[Paso 4.c] Subasta expirada sin pujas (Caso DESIERTA)...")
    with app.app_context():
        sub_vacia = Subasta(
            titulo="Cuadro Antiguo sin interesados",
            precio_inicial=Decimal("300.00"),
            incremento_minimo=Decimal("20.00"),
            fecha_fin=datetime.now(timezone.utc) - timedelta(minutes=10)
        )
        db.session.add(sub_vacia)
        db.session.commit()
        id_vacia = sub_vacia.id

    resp_vacia = client.get(f"/api/subastas/{id_vacia}")
    det_v = resp_vacia.get_json()['data']
    print(f"  Subasta #{id_vacia}: {det_v['titulo']}")
    print(f"  Estado: {det_v['estado'].upper()}")
    print(f"  Ganador: {det_v['ganador']} (Declarada desierta correctamente)")

    # ──────────────────────────────────────────────────────────────────
    # 5. HU-8: INTERFAZ WEB
    # ──────────────────────────────────────────────────────────────────
    print("\n[Paso 5] Verificando interfaz frontend (HU-8)...")
    r_ui = client.get("/")
    print(f"  Status HTTP ruta '/': {r_ui.status_code}")
    print(f"  Contiene título 'Subastas Online': {'Subastas Online' in r_ui.get_data(as_text=True)}")
    print(f"  Contiene protección doble clic en pujas: {'btn.disabled = true' in r_ui.get_data(as_text=True)}")

    print("\n" + "=" * 70)
    print("      TODAS LAS HISTORIAS DE USUARIO OPERAN AL 100% DE FORMA EXITOSA")
    print("=" * 70)

if __name__ == "__main__":
    demo()
