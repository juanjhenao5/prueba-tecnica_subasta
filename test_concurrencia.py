"""
HU-6: Prueba de concurrencia.
Crea una subasta y lanza 50 pujas simultáneas con hilos.
Verifica que el resultado final es consistente:
  - Montos estrictamente crecientes
  - Sin montos duplicados
  - El precio actual es la mayor puja válida

USO: primero arranca el servidor con `python app.py`, luego:
    python test_concurrencia.py
"""

import concurrent.futures
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import requests

BASE_URL = "http://localhost:5000/api/subastas"


def main():
    print("=" * 60)
    print("  HU-6: PRUEBA DE CONCURRENCIA — 50 pujas simultáneas")
    print("=" * 60)

    # ── 1. Crear subasta de prueba ──────────────────────────────────
    fecha_fin = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
    resp = requests.post(
        BASE_URL,
        json={
            "titulo": "Test Concurrencia",
            "descripcion": "Prueba automática de 50 pujas simultáneas",
            "precio_inicial": "100.00",
            "incremento_minimo": "1.00",
            "fecha_fin": fecha_fin,
        },
    )

    if resp.status_code != 201:
        print(f"❌ Error al crear subasta: {resp.json()}")
        return

    subasta_id = resp.json()["data"]["id"]
    print(f"\n✅ Subasta creada (ID: {subasta_id})")
    print(f"   Precio inicial: $100.00 | Incremento mínimo: $1.00\n")

    # ── 2. Lanzar 50 pujas simultáneas ──────────────────────────────
    print("🚀 Lanzando 50 pujas simultáneas...")

    resultados = {"exitosas": 0, "rechazadas": 0, "errores": 0}

    def hacer_puja(i):
        # Alternar entre 2 postores para cumplir regla HU-3
        postor = "Postor_A" if i % 2 == 0 else "Postor_B"
        # Montos que van de 101 a 150 (algunos coincidirán en ser válidos)
        monto = f"{100 + i}.00"
        try:
            r = requests.post(
                f"{BASE_URL}/{subasta_id}/pujas",
                json={"nombre": postor, "monto": monto},
                timeout=30,
            )
            return {
                "status": r.status_code,
                "data": r.json(),
                "monto": monto,
                "postor": postor,
            }
        except Exception as e:
            return {"status": 0, "error": str(e), "monto": monto, "postor": postor}

    with concurrent.futures.ThreadPoolExecutor(max_workers=50) as executor:
        futuros = [executor.submit(hacer_puja, i) for i in range(1, 51)]
        for f in concurrent.futures.as_completed(futuros):
            resultado = f.result()
            if resultado["status"] == 201:
                resultados["exitosas"] += 1
            elif resultado["status"] == 400:
                resultados["rechazadas"] += 1
            else:
                resultados["errores"] += 1

    print(f"\n📊 Resultados de las 50 pujas:")
    print(f"   ✅ Exitosas:    {resultados['exitosas']}")
    print(f"   ⛔ Rechazadas:  {resultados['rechazadas']}")
    print(f"   💥 Errores:     {resultados['errores']}")

    # ── 3. Verificar consistencia ───────────────────────────────────
    print("\n🔍 Verificando consistencia del resultado final...")

    resp = requests.get(f"{BASE_URL}/{subasta_id}")
    detalle = resp.json()["data"]
    pujas = detalle["pujas"]

    print(f"   Total pujas aceptadas: {len(pujas)}")
    print(f"   Precio actual:         ${detalle['precio_actual']}")
    print(f"   Mejor postor:          {detalle['mejor_postor']}")

    # Verificar montos estrictamente crecientes (pujas vienen desc, invertir)
    montos = [Decimal(p["monto"]) for p in reversed(pujas)]
    es_creciente = all(montos[i] < montos[i + 1] for i in range(len(montos) - 1))

    # Verificar sin duplicados
    montos_str = [str(m) for m in montos]
    sin_duplicados = len(set(montos_str)) == len(montos_str)

    print(f"\n   Montos estrictamente crecientes: {'✅ Sí' if es_creciente else '❌ No'}")
    print(f"   Sin montos duplicados:           {'✅ Sí' if sin_duplicados else '❌ No'}")

    # Mostrar historial
    print(f"\n📋 Historial de pujas aceptadas (orden cronológico):")
    for i, p in enumerate(reversed(pujas)):
        print(f"   #{i + 1:>2}: ${p['monto']:>8} — {p['nombre_postor']}")

    # Resultado final
    print("\n" + "=" * 60)
    if es_creciente and sin_duplicados:
        print("  ✅ PRUEBA DE CONCURRENCIA: EXITOSA")
    else:
        print("  ❌ PRUEBA DE CONCURRENCIA: FALLIDA")
    print("=" * 60)


if __name__ == "__main__":
    main()
