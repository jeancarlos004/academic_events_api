"""
Seeder — pobla la base de datos con datos iniciales.
Uso: python scripts/seed.py

Crea:
  - 1 usuario administrador
  - 1 usuario regular
  - 3 eventos de ejemplo
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from datetime import date
from app.core.database import SessionLocal, Base, engine
from app.core.security import hash_password
from app.models.user import User
from app.models.event import Event


def seed():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    try:
        # ── Usuarios ─────────────────────────────────────────────────────────
        if not db.query(User).filter(User.email == "admin@eventos.com").first():
            admin = User(
                nombre="Administrador",
                email="admin@eventos.com",
                password_hash=hash_password("Admin1234"),
                rol="admin"
            )
            db.add(admin)
            print("✓ Admin creado: admin@eventos.com / Admin1234")

        if not db.query(User).filter(User.email == "usuario@eventos.com").first():
            user = User(
                nombre="Juan Pérez",
                email="usuario@eventos.com",
                password_hash=hash_password("Usuario1234"),
                rol="usuario"
            )
            db.add(user)
            print("✓ Usuario creado: usuario@eventos.com / Usuario1234")

        # ── Eventos ──────────────────────────────────────────────────────────
        eventos = [
            Event(
                titulo="Taller de Inteligencia Artificial",
                descripcion="Introducción práctica a Machine Learning y redes neuronales",
                fecha=date(2026, 4, 10),
                hora="10:00",
                lugar="Auditorio Principal",
                cupos=100,
                tipo="taller",
                estado="activo"
            ),
            Event(
                titulo="Conferencia: Futuro del Software",
                descripcion="Tendencias y tecnologías emergentes en el desarrollo de software",
                fecha=date(2026, 4, 15),
                hora="14:00",
                lugar="Sala de Conferencias B",
                cupos=50,
                tipo="conferencia",
                estado="activo"
            ),
            Event(
                titulo="Seminario de Ciberseguridad Institucional",
                descripcion="Buenas prácticas y protocolos de seguridad para organizaciones",
                fecha=date(2026, 5, 3),
                hora="09:00",
                lugar="Laboratorio de Redes",
                cupos=30,
                tipo="seminario",
                estado="activo"
            ),
        ]

        if db.query(Event).count() == 0:
            for evento in eventos:
                db.add(evento)
            print(f"✓ {len(eventos)} eventos de ejemplo creados")

        db.commit()
        print("\n✅ Seed completado exitosamente.")

    except Exception as e:
        db.rollback()
        print(f"\n❌ Error durante el seed: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed()
