"""
Suite de pruebas automatizadas para validar los Criterios de Aceptación HU-1 a HU-8.
"""
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import unittest
import os

from app import create_app
from extensions import db
from models.subasta import Subasta
from models.puja import Puja
from services.servicio_subasta import SubastaService

class TestSubastasHU(unittest.TestCase):
    def setUp(self):
        # Crear app en modo test
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        self.client = self.app.test_client()
        with self.app.app_context():
            db.create_all()

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()

    # ── HU-1: Crear subasta ──────────────────────────────────────────
    def test_hu1_crear_subasta_valida(self):
        fecha_fin = (datetime.now(timezone.utc) + timedelta(days=2)).isoformat()
        res = self.client.post('/api/subastas', json={
            "titulo": "Laptop Dell XPS",
            "descripcion": "En perfecto estado",
            "precio_inicial": "500.00",
            "incremento_minimo": "10.00",
            "fecha_fin": fecha_fin
        })
        self.assertEqual(res.status_code, 201)
        data = res.get_json()['data']
        self.assertEqual(data['titulo'], "Laptop Dell XPS")
        self.assertEqual(data['precio_inicial'], "500.00")
        self.assertEqual(data['incremento_minimo'], "10.00")
        self.assertEqual(data['estado'], "abierta")

    def test_hu1_validaciones_invalidas(self):
        # Titulo vacio
        res = self.client.post('/api/subastas', json={"titulo": ""})
        self.assertEqual(res.status_code, 400)

        # Titulo > 100 caracteres
        res = self.client.post('/api/subastas', json={"titulo": "A" * 101})
        self.assertEqual(res.status_code, 400)

        # Precio inicial <= 0
        fecha_fin = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
        res = self.client.post('/api/subastas', json={
            "titulo": "Subasta",
            "precio_inicial": "0.00",
            "incremento_minimo": "1.00",
            "fecha_fin": fecha_fin
        })
        self.assertEqual(res.status_code, 400)

        # Incremento minimo <= 0
        res = self.client.post('/api/subastas', json={
            "titulo": "Subasta",
            "precio_inicial": "10.00",
            "incremento_minimo": "-1.00",
            "fecha_fin": fecha_fin
        })
        self.assertEqual(res.status_code, 400)

        # Fecha en el pasado
        fecha_pasada = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
        res = self.client.post('/api/subastas', json={
            "titulo": "Subasta",
            "precio_inicial": "10.00",
            "incremento_minimo": "1.00",
            "fecha_fin": fecha_pasada
        })
        self.assertEqual(res.status_code, 400)

        # Fecha mayor a 7 dias
        fecha_lejana = (datetime.now(timezone.utc) + timedelta(days=8)).isoformat()
        res = self.client.post('/api/subastas', json={
            "titulo": "Subasta",
            "precio_inicial": "10.00",
            "incremento_minimo": "1.00",
            "fecha_fin": fecha_lejana
        })
        self.assertEqual(res.status_code, 400)

    # ── HU-2: Listar y Detalle ───────────────────────────────────────
    def test_hu2_listar_y_detalle(self):
        fecha_fin = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
        res = self.client.post('/api/subastas', json={
            "titulo": "Pintura al oleo",
            "precio_inicial": "150.00",
            "incremento_minimo": "5.00",
            "fecha_fin": fecha_fin
        })
        subasta_id = res.get_json()['data']['id']

        # Listado
        res_list = self.client.get('/api/subastas')
        self.assertEqual(res_list.status_code, 200)
        self.assertTrue(len(res_list.get_json()['data']) >= 1)

        # Detalle
        res_det = self.client.get(f'/api/subastas/{subasta_id}')
        self.assertEqual(res_det.status_code, 200)
        det = res_det.get_json()['data']
        self.assertEqual(det['precio_actual'], "150.00")
        self.assertIsNone(det['mejor_postor'])
        self.assertIsNotNone(det['tiempo_restante'])
        self.assertEqual(det['pujas'], [])

    # ── HU-3 & HU-4: Pujas y precisión de dinero ─────────────────────
    def test_hu3_hu4_flujo_pujas(self):
        fecha_fin = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
        res = self.client.post('/api/subastas', json={
            "titulo": "Reloj de coleccion",
            "precio_inicial": "100.00",
            "incremento_minimo": "10.00",
            "fecha_fin": fecha_fin
        })
        sid = res.get_json()['data']['id']

        # Primera puja igual a precio inicial es valida
        res_p1 = self.client.post(f'/api/subastas/{sid}/pujas', json={
            "nombre": "Carlos",
            "monto": "100.00"
        })
        self.assertEqual(res_p1.status_code, 201)

        # Mismo postor intenta pujar de nuevo -> Rechazado
        res_p2 = self.client.post(f'/api/subastas/{sid}/pujas', json={
            "nombre": "Carlos",
            "monto": "120.00"
        })
        self.assertEqual(res_p2.status_code, 400)
        self.assertIn("mejor postor", res_p2.get_json()['error'])

        # Monto menor a precio actual + incremento (100 + 10 = 110)
        res_p3 = self.client.post(f'/api/subastas/{sid}/pujas', json={
            "nombre": "Maria",
            "monto": "105.00"
        })
        self.assertEqual(res_p3.status_code, 400)
        self.assertIn("al menos 110.00", res_p3.get_json()['error'])

        # Monto con mas de 2 decimales -> Rechazado (HU-4)
        res_p4 = self.client.post(f'/api/subastas/{sid}/pujas', json={
            "nombre": "Maria",
            "monto": "110.555"
        })
        self.assertEqual(res_p4.status_code, 400)
        self.assertIn("2 decimales", res_p4.get_json()['error'])

        # Puja valida con 2 decimales exactos
        res_p5 = self.client.post(f'/api/subastas/{sid}/pujas', json={
            "nombre": "Maria",
            "monto": "110.50"
        })
        self.assertEqual(res_p5.status_code, 201)

        # Historial de pujas ordenado descendente
        res_det = self.client.get(f'/api/subastas/{sid}')
        det = res_det.get_json()['data']
        self.assertEqual(det['precio_actual'], "110.50")
        self.assertEqual(det['mejor_postor'], "Maria")
        self.assertEqual(len(det['pujas']), 2)
        self.assertEqual(det['pujas'][0]['nombre_postor'], "Maria")
        self.assertEqual(det['pujas'][1]['nombre_postor'], "Carlos")

    # ── HU-5: Cierre de subasta y estado desierta ───────────────────
    def test_hu5_cierre_subasta_con_ganador_y_desierta(self):
        with self.app.app_context():
            # 1. Crear subasta ya expirada sin pujas (desierta)
            sub_desierta = Subasta(
                titulo="Item no deseado",
                precio_inicial=Decimal("50.00"),
                incremento_minimo=Decimal("5.00"),
                fecha_fin=datetime.now(timezone.utc) - timedelta(minutes=5)
            )
            db.session.add(sub_desierta)

            # 2. Crear subasta expirada con pujas (ganador)
            sub_ganada = Subasta(
                titulo="Item popular",
                precio_inicial=Decimal("100.00"),
                incremento_minimo=Decimal("10.00"),
                fecha_fin=datetime.now(timezone.utc) - timedelta(minutes=1)
            )
            db.session.add(sub_ganada)
            db.session.commit()

            puja = Puja(
                subasta_id=sub_ganada.id,
                nombre_postor="Ana",
                monto=Decimal("150.00")
            )
            db.session.add(puja)
            db.session.commit()

            desierta_id = sub_desierta.id
            ganada_id = sub_ganada.id

        # Consultar detalle subasta desierta
        res_d = self.client.get(f'/api/subastas/{desierta_id}')
        data_d = res_d.get_json()['data']
        self.assertEqual(data_d['estado'], 'cerrada')
        self.assertEqual(data_d['ganador'], 'DESIERTA')

        # Consultar detalle subasta con ganador
        res_g = self.client.get(f'/api/subastas/{ganada_id}')
        data_g = res_g.get_json()['data']
        self.assertEqual(data_g['estado'], 'cerrada')
        self.assertEqual(data_g['ganador'], 'Ana')
        self.assertEqual(data_g['precio_final'], '150.00')

        # Intentar pujar en subasta cerrada -> Rechazado
        res_p = self.client.post(f'/api/subastas/{ganada_id}/pujas', json={
            "nombre": "Pedro",
            "monto": "200.00"
        })
        self.assertEqual(res_p.status_code, 400)
        self.assertTrue(any(w in res_p.get_json()['error'].lower() for w in ['cerrada', 'finalizado']))

    # ── HU-7: Persistencia tras reinicio ─────────────────────────────
    def test_hu7_persistencia_disco(self):
        # Crear subasta en la base de datos de test
        fecha_fin = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
        res = self.client.post('/api/subastas', json={
            "titulo": "Subasta Persistente",
            "precio_inicial": "200.00",
            "incremento_minimo": "15.00",
            "fecha_fin": fecha_fin
        })
        sid = res.get_json()['data']['id']

        self.client.post(f'/api/subastas/{sid}/pujas', json={
            "nombre": "Inversionista",
            "monto": "200.00"
        })

        # Simular nueva sesión / reinicio consultando nuevamente
        with self.app.app_context():
            subasta_db = db.session.get(Subasta, sid)
            self.assertIsNotNone(subasta_db)
            self.assertEqual(subasta_db.titulo, "Subasta Persistente")
            self.assertEqual(len(subasta_db.pujas), 1)
            self.assertEqual(subasta_db.pujas[0].nombre_postor, "Inversionista")

    # ── HU-8: Interfaz Web ───────────────────────────────────────────
    def test_hu8_interfaz_frontend(self):
        res = self.client.get('/')
        self.assertEqual(res.status_code, 200)
        html = res.get_data(as_text=True)
        self.assertIn("Subastas Online", html)
        self.assertIn("Nueva Subasta", html)
        self.assertIn("btn-pujar", html)

if __name__ == '__main__':
    unittest.main()
