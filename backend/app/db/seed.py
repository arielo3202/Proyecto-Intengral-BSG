from __future__ import annotations

from app.db.database import db_manager

if __name__ == "__main__":
    db_manager.seed_defaults()
    print("[DB SEED OK] Usuarios corporativos (empleado@techcorp.latam y admin@techcorp.latam) listos.")
