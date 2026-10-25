from __future__ import annotations

from app.db.database import db_manager

if __name__ == "__main__":
    health = db_manager.check_health()
    print(f"[DB MIGRATE OK] Esquema relacional e índices verificados: {health}")
