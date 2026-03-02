# 🎓 API de Gestión de Eventos Académicos

API REST completa construida con **FastAPI + SQLAlchemy + Alembic**.  
Autenticación JWT con access/refresh tokens, roles, paginación y reportes.

---

## 🚀 Inicio rápido

```bash
# 1. Entorno virtual
python -m venv venv
source venv/bin/activate        # Linux/Mac
venv\Scripts\activate           # Windows

# 2. Instalar dependencias
pip install -r requirements.txt

# 3. Variables de entorno
cp .env .env.local   # Editar SECRET_KEY y REFRESH_SECRET_KEY en producción

# 4. Ejecutar migraciones
alembic upgrade head

# 5. Poblar datos iniciales (opcional)
python scripts/seed.py

# 6. Arrancar servidor
uvicorn main:app --reload
```

**Docs interactivas:** http://localhost:8000/docs  
**Redoc:** http://localhost:8000/redoc

---

## 🐳 Docker

```bash
docker-compose up --build
```

---

## 🧪 Tests

```bash
pytest tests/ -v
```

---

## 📁 Estructura

```
academic_events_api/
├── main.py                        # Entrada, CORS, error handlers
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
├── alembic.ini
├── alembic/
│   ├── env.py
│   └── versions/
│       └── 0001_initial_schema.py
├── scripts/
│   └── seed.py                    # Datos iniciales
├── tests/
│   ├── conftest.py                # Fixtures, DB en memoria
│   ├── test_auth.py
│   └── test_events.py
└── app/
    ├── core/
    │   ├── config.py              # Settings (pydantic-settings)
    │   ├── database.py            # Engine, SessionLocal, Base
    │   └── security.py            # JWT, bcrypt, blacklist, deps
    ├── exceptions/
    │   └── app_exceptions.py      # HTTPException tipadas
    ├── middleware/
    │   └── error_handler.py       # Handlers globales
    ├── models/
    │   ├── user.py
    │   ├── event.py
    │   └── registration.py
    ├── schemas/
    │   ├── auth.py
    │   ├── event.py
    │   ├── registration.py
    │   └── report.py
    ├── services/                  # Lógica de negocio
    │   ├── auth_service.py
    │   ├── event_service.py
    │   ├── registration_service.py
    │   └── report_service.py
    └── routers/                   # Endpoints HTTP
        ├── auth.py
        ├── users.py
        ├── events.py
        ├── registrations.py
        └── reports.py
```

---

## 🔐 Endpoints

### Autenticación
| Método | Ruta | Descripción |
|--------|------|-------------|
| POST | `/api/v1/auth/register` | Registrar usuario |
| POST | `/api/v1/auth/login` | Login → access + refresh token |
| POST | `/api/v1/auth/refresh` | Renovar access token |
| POST | `/api/v1/auth/logout` | Revocar token |

### Usuarios
| Método | Ruta | Auth | Rol |
|--------|------|------|-----|
| GET | `/api/v1/users/me` | ✅ | usuario |

### Eventos
| Método | Ruta | Auth | Rol |
|--------|------|------|-----|
| GET | `/api/v1/events` | ❌ | — |
| GET | `/api/v1/events/{id}` | ❌ | — |
| POST | `/api/v1/events` | ✅ | admin |
| PUT | `/api/v1/events/{id}` | ✅ | admin |
| DELETE | `/api/v1/events/{id}` | ✅ | admin |

### Inscripciones
| Método | Ruta | Auth | Rol |
|--------|------|------|-----|
| POST | `/api/v1/events/{id}/register` | ✅ | usuario |
| DELETE | `/api/v1/events/{id}/register` | ✅ | usuario |
| GET | `/api/v1/events/{id}/registrations` | ✅ | admin |
| GET | `/api/v1/registrations/me` | ✅ | usuario |
| PATCH | `/api/v1/registrations/{id}/attendance` | ✅ | admin |

### Reportes
| Método | Ruta | Auth | Rol |
|--------|------|------|-----|
| GET | `/api/v1/reports/events` | ✅ | admin |
| GET | `/api/v1/reports/events/{id}` | ✅ | admin |

---

## 🗄️ Base de datos

Por defecto usa **SQLite** (desarrollo).  
Para producción cambiar en `.env`:

```
DATABASE_URL=postgresql://user:password@localhost/academic_events
```

---

## ⚠️ Variables de entorno en producción

```env
SECRET_KEY=<min 32 caracteres aleatorios>
REFRESH_SECRET_KEY=<min 32 caracteres aleatorios distintos>
DATABASE_URL=postgresql://...
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7
```

> La blacklist de tokens usa memoria por defecto.  
> En producción reemplazar por **Redis** en `app/core/security.py`.
