# Sistema de Subastas Online — Prueba Técnica

Solución completa y robusta para la gestión de subastas en tiempo real desarrollada en Python con Flask y SQLAlchemy.

El sistema implementa y valida de forma estricta los 11 Criterios de Aceptación (**HU-1** a **HU-11**).

---

## 🚀 Características y Cumplimiento de Criterios

* **HU-1: Creación de Subasta**: Título (1-100 caracteres), descripción, precio inicial > 0, incremento mínimo > 0 y fecha de fin futura (máximo 7 días). Retorna HTTP 201 en éxito y HTTP 400 con mensajes legibles ante validaciones fallidas.
* **HU-2: Listado y Detalle**: Visualización de subastas abiertas y cerradas. Detalle con precio actual, mejor postor, tiempo restante dinámico e historial cronológico descendente de pujas.
* **HU-3: Registro de Pujas**: Validación de nombre y monto. El monto debe ser mayor o igual al precio actual más el incremento mínimo (o igual al precio inicial si es la primera puja). Se rechaza con HTTP 400 si el postor intenta pujar contra sí mismo.
* **HU-4: Precisión Monetaria**: Manejo exacto de dinero con dos cifras decimales utilizando `Decimal` y `Numeric(12, 2)` en base de datos para prevenir errores de redondeo de punto flotante.
* **HU-5: Cierre Automático**: Al expirar el tiempo de la subasta, se cierra automáticamente y se registran el ganador y el precio final. Si no hubo pujas, la subasta se declara `DESIERTA`. Persistente ante reinicios del servidor mediante un patrón de verificación lazy.
* **HU-6: Concurrencia**: Soporte para alta concurrencia mediante bloqueo y sincronización atómica por subasta (`threading.Lock` / `expire_all`). Se garantiza que ante 50 pujas simultáneas los montos sean estrictamente crecientes y sin duplicados.
* **HU-7: Persistencia**: Persistencia completa en base de datos SQLite gestionada con SQLAlchemy y migraciones.
* **HU-8: Interfaz Web (SPA)**: Frontend reactivo en HTML5, CSS3 y JavaScript moderno con cuenta regresiva en vivo, formulario de subastas, catálogo de subastas y protección contra doble clic en el botón de pujar.
* **HU-9: Tiempo Real**: Actualización en vivo de nuevas pujas y cierre de la subasta para todos los espectadores **sin recargar la página**.
* **HU-10: Cuenta Regresiva basada en el Servidor**: El temporizador está sincronizado y gobernado estrictamente por el reloj del servidor en UTC, garantizando exactitud absoluta incluso si el reloj del computador del usuario está adelantado o atrasado en 5 minutos.
* **HU-11: Extensión Anti-sniping Atómica**: Si entra una puja válida en los últimos 60 segundos, el vencimiento de la subasta se extiende automáticamente para que resten 60 segundos desde esa puja, hasta un máximo de 10 extensiones. La puja y la extensión son una única operación estrictamente atómica.

---

## 🛠️ Tecnologías

* **Lenguaje:** Python 3.10+
* **Framework Web:** Flask 3.x
* **ORM:** Flask-SQLAlchemy / SQLAlchemy 2.x
* **Migraciones:** Flask-Migrate / Alembic
* **Base de Datos:** SQLite
* **Pruebas:** Unittest, Concurrency ThreadPoolExecutor, Requests

---

## 📋 Instalación y Puesta en Marcha

### 1. Clonar el repositorio
```bash
git clone https://github.com/juanjhenao5/prueba-tecnica_subasta.git
cd prueba-tecnica_subasta
```

### 2. Crear y activar el entorno virtual
```bash
# Windows
python -m venv .venv
.\.venv\Scripts\activate

# Linux / macOS
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Instalar dependencias
```bash
pip install -r requirements.txt
```

### 4. Iniciar el servidor
```bash
python app.py
```
Abre tu navegador en: [http://localhost:5000/](http://localhost:5000/)

---

## 🧪 Pruebas Automatizadas

El proyecto incluye suites completas de pruebas automatizadas:

### 1. Suite Completa de Integración y Reglas de Negocio (HU-1 a HU-8)
Valida todos los casos de éxito, validaciones y códigos de error:
```bash
python test_suite_completo.py
```

### 2. Prueba de Concurrencia — 50 Pujas Simultáneas (HU-6)
Demuestra la consistencia estricta en concurrencia (sin duplicados, montos crecientes):
```bash
python ejecutar_servidor_y_test_concurrencia.py
```
*(O con el servidor `python app.py` ya corriendo, ejecuta `python test_concurrencia.py`)*

### 3. Demostración Interactiva Paso a Paso
Demuestra el ciclo de vida completo en consola con salida formateada:
```bash
python demo_funcionamiento.py
```

---

## 📡 Endpoints de la API REST

| Método | Endpoint | Descripción |
|---|---|---|
| `POST` | `/api/subastas` | Crea una nueva subasta con validaciones |
| `GET` | `/api/subastas` | Lista todas las subastas (abiertas y cerradas) |
| `GET` | `/api/subastas/<id>` | Obtiene el detalle, tiempo restante e historial |
| `POST` | `/api/subastas/<id>/pujas` | Registra una oferta/puja sobre la subasta |
| `GET` | `/` | Interfaz web de usuario (SPA) |
