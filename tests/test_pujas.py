"""
Pruebas automáticas de la lógica de pujas (HU-3 y HU-4).
"""
from decimal import Decimal
from models import Subasta, Puja
from extensions import db

def test_primera_puja_valida(client, subasta_activa):
    """La primera puja debe ser al menos igual al precio inicial."""
    res = client.post(f"/api/subastas/{subasta_activa}/pujas", json={
        "nombre": "CompradorA",
        "monto": "100.00"
    })
    assert res.status_code == 201
    data = res.get_json()["data"]
    assert data["nombre_postor"] == "CompradorA"
    assert data["monto"] == "100.00"

    # Verificar que el detalle se actualiza
    det = client.get(f"/api/subastas/{subasta_activa}").get_json()["data"]
    assert det["precio_actual"] == "100.00"
    assert det["mejor_postor"] == "CompradorA"
    assert det["total_pujas"] == 1

def test_rechazo_puja_menor_al_minimo(client, subasta_activa):
    """Se rechaza si el monto es menor al precio actual + incremento mínimo."""
    # Primera puja: 100.00
    client.post(f"/api/subastas/{subasta_activa}/pujas", json={
        "nombre": "CompradorA",
        "monto": "100.00"
    })

    # Segunda puja: mínimo requerido es 100 + 10 = 110.00
    res = client.post(f"/api/subastas/{subasta_activa}/pujas", json={
        "nombre": "CompradorB",
        "monto": "105.00"
    })
    assert res.status_code == 400
    json_data = res.get_json()
    assert json_data["success"] is False
    assert "al menos 110.00" in json_data["error"]

def test_rechazo_auto_puja_mismo_postor(client, subasta_activa):
    """Un postor no puede pujar contra sí mismo si ya es el mejor postor."""
    # Primera puja: CompradorA
    client.post(f"/api/subastas/{subasta_activa}/pujas", json={
        "nombre": "CompradorA",
        "monto": "100.00"
    })

    # CompradorA intenta pujar de nuevo
    res = client.post(f"/api/subastas/{subasta_activa}/pujas", json={
        "nombre": "CompradorA",
        "monto": "120.00"
    })
    assert res.status_code == 400
    assert "mejor postor" in res.get_json()["error"].lower()

def test_validacion_dinero_exacto_dos_decimales(client, subasta_activa):
    """El dinero debe manejarse con exactamente dos decimales (sin errores float)."""
    # Pujar con centavos válidos
    res = client.post(f"/api/subastas/{subasta_activa}/pujas", json={
        "nombre": "CompradorA",
        "monto": "100.75"
    })
    assert res.status_code == 201

    det = client.get(f"/api/subastas/{subasta_activa}").get_json()["data"]
    assert det["precio_actual"] == "100.75"

def test_rechazo_puja_tres_decimales(client, subasta_activa):
    """Se rechazan montos con más de dos decimales (HU-4)."""
    res = client.post(f"/api/subastas/{subasta_activa}/pujas", json={
        "nombre": "CompradorA",
        "monto": "100.123"
    })
    assert res.status_code == 400
    assert "2 decimales" in res.get_json()["error"]

def test_rechazo_puja_monto_invalido_o_negativo(client, subasta_activa):
    """Se rechazan montos menores o iguales a cero o no numéricos."""
    res_neg = client.post(f"/api/subastas/{subasta_activa}/pujas", json={
        "nombre": "CompradorA",
        "monto": "-10.00"
    })
    assert res_neg.status_code == 400

    res_texto = client.post(f"/api/subastas/{subasta_activa}/pujas", json={
        "nombre": "CompradorA",
        "monto": "gratis"
    })
    assert res_texto.status_code == 400

def test_rechazo_subasta_inexistente(client):
    """Pujar en una subasta inexistente devuelve 404."""
    res = client.post("/api/subastas/999999/pujas", json={
        "nombre": "Fantasma",
        "monto": "500.00"
    })
    assert res.status_code == 404

def test_historial_pujas_orden_cronologico_inverso(client, subasta_activa):
    """El historial de pujas debe listarse en orden más reciente primero."""
    client.post(f"/api/subastas/{subasta_activa}/pujas", json={"nombre": "User1", "monto": "100.00"})
    client.post(f"/api/subastas/{subasta_activa}/pujas", json={"nombre": "User2", "monto": "115.00"})
    client.post(f"/api/subastas/{subasta_activa}/pujas", json={"nombre": "User1", "monto": "130.00"})

    det = client.get(f"/api/subastas/{subasta_activa}").get_json()["data"]
    pujas = det["pujas"]
    assert len(pujas) == 3
    # El más reciente debe ser User1 con 130.00
    assert pujas[0]["nombre_postor"] == "User1"
    assert pujas[0]["monto"] == "130.00"
    assert pujas[1]["nombre_postor"] == "User2"
    assert pujas[1]["monto"] == "115.00"
    assert pujas[2]["nombre_postor"] == "User1"
    assert pujas[2]["monto"] == "100.00"
