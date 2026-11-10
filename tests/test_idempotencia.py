"""
Pruebas automáticas de Idempotencia en pujas (mala red y reintentos / doble envío).
"""
import uuid
from decimal import Decimal
from models import Subasta, Puja
from extensions import db

def test_idempotencia_con_clave_idempotency_key(client, subasta_activa):
    """Si el cliente reintenta con la misma Idempotency-Key, no se duplica la puja."""
    key = str(uuid.uuid4())

    # Primer intento (cliente envía puja)
    res1 = client.post(
        f"/api/subastas/{subasta_activa}/pujas",
        headers={"Idempotency-Key": key},
        json={"nombre": "PostorRedLenta", "monto": "100.00"}
    )
    assert res1.status_code == 201
    puja_id_1 = res1.get_json()["data"]["id"]

    # Segundo intento (cliente sufrió timeout de red y reintenta la misma petición con la misma clave)
    res2 = client.post(
        f"/api/subastas/{subasta_activa}/pujas",
        headers={"Idempotency-Key": key},
        json={"nombre": "PostorRedLenta", "monto": "100.00"}
    )
    assert res2.status_code == 200  # Idempotente OK
    data2 = res2.get_json()
    assert data2["success"] is True
    assert "Idempotente" in data2["mensaje"]
    assert data2["data"]["id"] == puja_id_1  # Misma puja original

    # Verificar en base de datos: solo existe 1 puja registrada
    det = client.get(f"/api/subastas/{subasta_activa}").get_json()["data"]
    assert det["total_pujas"] == 1
    assert len(det["pujas"]) == 1

def test_idempotencia_natural_reintento_sin_header(client, subasta_activa):
    """Si el cliente reenvía la misma puja (mismo postor y monto) sin header, no se duplica."""
    # Primer intento
    res1 = client.post(f"/api/subastas/{subasta_activa}/pujas", json={
        "nombre": "PostorReintento",
        "monto": "100.00"
    })
    assert res1.status_code == 201
    puja_id_1 = res1.get_json()["data"]["id"]

    # Reintento por doble clic o mala red (mismo postor y mismo monto)
    res2 = client.post(f"/api/subastas/{subasta_activa}/pujas", json={
        "nombre": "PostorReintento",
        "monto": "100.00"
    })
    # Se detecta como reintento idempotente sin duplicar
    assert res2.status_code in (200, 201)
    assert res2.get_json()["data"]["id"] == puja_id_1

    det = client.get(f"/api/subastas/{subasta_activa}").get_json()["data"]
    assert det["total_pujas"] == 1

def test_reintentos_multiples_en_bucle(client, subasta_activa):
    """Simular 5 reintentos seguidos por mala red: nunca se registra más de 1 vez."""
    key = "reintento-bucle-12345"
    for i in range(5):
        res = client.post(
            f"/api/subastas/{subasta_activa}/pujas",
            headers={"Idempotency-Key": key},
            json={"nombre": "PostorInsistente", "monto": "100.00"}
        )
        assert res.status_code in (200, 201)

    det = client.get(f"/api/subastas/{subasta_activa}").get_json()["data"]
    assert det["total_pujas"] == 1
    assert det["precio_actual"] == "100.00"
    assert det["mejor_postor"] == "PostorInsistente"
