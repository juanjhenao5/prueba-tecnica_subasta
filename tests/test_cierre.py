"""
Pruebas automáticas de la lógica de cierre (HU-5, HU-7 y HU-11).
"""
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from models import Subasta, Puja
from extensions import db

def test_cierre_automatico_con_ganador_y_precio_final(app, client):
    """Al expirar la subasta se registra el ganador y el precio final."""
    with app.app_context():
        sub = Subasta(
            titulo="Subasta por cerrar",
            precio_inicial=Decimal("200.00"),
            incremento_minimo=Decimal("20.00"),
            fecha_fin=datetime.now(timezone.utc) - timedelta(seconds=5)
        )
        db.session.add(sub)
        db.session.commit()
        sid = sub.id

        puja1 = Puja(subasta_id=sid, nombre_postor="PostorInicial", monto=Decimal("200.00"))
        puja2 = Puja(subasta_id=sid, nombre_postor="GanadorFinal", monto=Decimal("250.00"))
        db.session.add_all([puja1, puja2])
        db.session.commit()

    # Consultar detalle (ejecuta el cierre lazy)
    res = client.get(f"/api/subastas/{sid}")
    assert res.status_code == 200
    data = res.get_json()["data"]

    assert data["esta_abierta"] is False
    assert data["estado"] == "cerrada"
    assert data["ganador"] == "GanadorFinal"
    assert data["precio_final"] == "250.00"
    assert data["tiempo_restante_segundos"] == 0

def test_cierre_subasta_sin_pujas_queda_desierta(app, client):
    """Si la subasta expira sin ninguna puja, queda declarada DESIERTA."""
    with app.app_context():
        sub = Subasta(
            titulo="Subasta no ofertada",
            precio_inicial=Decimal("500.00"),
            incremento_minimo=Decimal("50.00"),
            fecha_fin=datetime.now(timezone.utc) - timedelta(minutes=1)
        )
        db.session.add(sub)
        db.session.commit()
        sid = sub.id

    res = client.get(f"/api/subastas/{sid}")
    data = res.get_json()["data"]
    assert data["estado"] == "cerrada"
    assert data["ganador"] == "DESIERTA"
    assert data["precio_final"] is None

def test_rechazo_puja_en_subasta_cerrada(app, client):
    """No se aceptan pujas una vez cerrada la subasta."""
    with app.app_context():
        sub = Subasta(
            titulo="Subasta cerrada",
            precio_inicial=Decimal("100.00"),
            incremento_minimo=Decimal("10.00"),
            fecha_fin=datetime.now(timezone.utc) - timedelta(seconds=1)
        )
        db.session.add(sub)
        db.session.commit()
        sid = sub.id

    res = client.post(f"/api/subastas/{sid}/pujas", json={
        "nombre": "Tardio",
        "monto": "150.00"
    })
    assert res.status_code == 400
    assert any(palabra in res.get_json()["error"].lower() for palabra in ["finalizado", "cerrada"])

def test_anti_sniping_extension_en_ultimos_60s(app, client):
    """Si entra puja faltando <= 60s, el vencimiento se extiende a 60s (HU-11)."""
    with app.app_context():
        sub = Subasta(
            titulo="Subasta anti-sniping",
            precio_inicial=Decimal("100.00"),
            incremento_minimo=Decimal("10.00"),
            fecha_fin=datetime.now(timezone.utc) + timedelta(seconds=25), # Faltan 25s
            extensiones_aplicadas=0
        )
        db.session.add(sub)
        db.session.commit()
        sid = sub.id

    # Puja válida
    res = client.post(f"/api/subastas/{sid}/pujas", json={
        "nombre": "SniperA",
        "monto": "100.00"
    })
    assert res.status_code == 201
    data_puja = res.get_json()["data"]
    assert data_puja["se_extendio"] is True
    assert data_puja["extensiones_aplicadas"] == 1

    # Comprobar que el detalle refleja los ~60 segundos restantes
    det = client.get(f"/api/subastas/{sid}").get_json()["data"]
    assert 58 <= det["tiempo_restante_segundos"] <= 60
    assert det["extensiones_aplicadas"] == 1

def test_anti_sniping_limite_maximo_10_extensiones(app, client):
    """El tope de extensiones anti-sniping es 10."""
    with app.app_context():
        sub = Subasta(
            titulo="Subasta con 9 extensiones",
            precio_inicial=Decimal("100.00"),
            incremento_minimo=Decimal("10.00"),
            fecha_fin=datetime.now(timezone.utc) + timedelta(seconds=20),
            extensiones_aplicadas=9
        )
        db.session.add(sub)
        db.session.commit()
        sid = sub.id

    # 10ma extensión (válida)
    r10 = client.post(f"/api/subastas/{sid}/pujas", json={"nombre": "User1", "monto": "100.00"})
    assert r10.status_code == 201
    assert r10.get_json()["data"]["se_extendio"] is True
    assert r10.get_json()["data"]["extensiones_aplicadas"] == 10

    # Forzar que resten 15s e intentar 11ma puja
    with app.app_context():
        sub_db = db.session.get(Subasta, sid)
        sub_db.fecha_fin = datetime.now(timezone.utc) + timedelta(seconds=15)
        db.session.commit()

    r11 = client.post(f"/api/subastas/{sid}/pujas", json={"nombre": "User2", "monto": "110.00"})
    assert r11.status_code == 201
    # Se acepta la puja pero NO se vuelve a extender
    assert r11.get_json()["data"]["se_extendio"] is False
    assert r11.get_json()["data"]["extensiones_aplicadas"] == 10

    det = client.get(f"/api/subastas/{sid}").get_json()["data"]
    assert det["max_extensiones_alcanzadas"] is True
    assert det["tiempo_restante_segundos"] <= 16

def test_anti_sniping_atomicidad_ante_puja_invalida(app, client):
    """Si la puja en los últimos 60s es inválida, el tiempo NO se extiende (atomicidad)."""
    with app.app_context():
        sub = Subasta(
            titulo="Subasta atómica",
            precio_inicial=Decimal("100.00"),
            incremento_minimo=Decimal("10.00"),
            fecha_fin=datetime.now(timezone.utc) + timedelta(seconds=30),
            extensiones_aplicadas=0
        )
        db.session.add(sub)
        db.session.commit()
        sid = sub.id

    # Intento de puja inválida (monto menor)
    res = client.post(f"/api/subastas/{sid}/pujas", json={
        "nombre": "Invalido",
        "monto": "50.00"
    })
    assert res.status_code == 400

    det = client.get(f"/api/subastas/{sid}").get_json()["data"]
    assert det["extensiones_aplicadas"] == 0
    assert det["tiempo_restante_segundos"] <= 30
