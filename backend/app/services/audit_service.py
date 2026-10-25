from __future__ import annotations

import csv
import hashlib
import io
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from app.core.config import settings
from app.core.observability import log_structured_event
from app.db.database import db_manager

GENESIS_HASH = "0" * 64


class ImmutableAuditService:
    """
    Servicio de Auditoría Inmutable (JSONL + PostgreSQL) con cadena criptográfica SHA-256.
    Incluye exportación verificada en formatos CSV y PDF para el Rol Administrador.
    """

    def __init__(self, jsonl_path: str | None = None) -> None:
        self.jsonl_path = Path(jsonl_path or settings.audit_jsonl_path)
        self.jsonl_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.jsonl_path.exists():
            self.jsonl_path.write_text("", encoding="utf-8")

    @staticmethod
    def compute_record_hash(
        prev_hash: str,
        event_timestamp: str,
        event_type: str,
        user_id: str,
        session_id: str,
        provider_used: str,
        model_used: str,
        total_tokens: int,
        cost_usd: float,
    ) -> str:
        canonical = (
            f"{prev_hash}|{event_timestamp}|{event_type}|{user_id}|{session_id}|"
            f"{provider_used}|{model_used}|{total_tokens}|{cost_usd:.6f}"
        )
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    def record_event(
        self,
        event_type: str,
        user_id: str,
        user_role: str,
        session_id: str,
        provider_used: str,
        model_used: str,
        total_tokens: int,
        cost_usd: float,
        latency_ms: float,
        circuit_breaker_state: str,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        now_utc = datetime.now(timezone.utc).isoformat()
        safe_meta = metadata or {}

        with db_manager._get_conn() as conn:
            last_row = conn.execute(
                "SELECT record_hash FROM immutable_audit_logs ORDER BY id DESC LIMIT 1"
            ).fetchone()
            prev_hash = str(last_row["record_hash"]) if last_row else GENESIS_HASH

            record_hash = self.compute_record_hash(
                prev_hash=prev_hash,
                event_timestamp=now_utc,
                event_type=event_type,
                user_id=user_id,
                session_id=session_id,
                provider_used=provider_used,
                model_used=model_used,
                total_tokens=total_tokens,
                cost_usd=cost_usd,
            )

            conn.execute(
                """
                INSERT INTO immutable_audit_logs (
                    event_timestamp, event_type, user_id, user_role, session_id,
                    provider_used, model_used, total_tokens, cost_usd, latency_ms,
                    circuit_breaker_state, metadata_json, prev_hash, record_hash
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    now_utc,
                    event_type,
                    user_id,
                    user_role,
                    session_id,
                    provider_used,
                    model_used,
                    total_tokens,
                    round(cost_usd, 6),
                    round(latency_ms, 2),
                    circuit_breaker_state,
                    json.dumps(safe_meta, ensure_ascii=False),
                    prev_hash,
                    record_hash,
                ),
            )

        jsonl_entry = {
            "event_timestamp": now_utc,
            "event_type": event_type,
            "user_id": user_id,
            "user_role": user_role,
            "session_id": session_id,
            "provider_used": provider_used,
            "model_used": model_used,
            "total_tokens": total_tokens,
            "cost_usd": round(cost_usd, 6),
            "latency_ms": round(latency_ms, 2),
            "circuit_breaker_state": circuit_breaker_state,
            "metadata": safe_meta,
            "prev_hash": prev_hash,
            "record_hash": record_hash,
        }
        with self.jsonl_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(jsonl_entry, ensure_ascii=False) + "\n")

        log_structured_event(
            "AUDIT_RECORD_SEALED",
            f"Registro inmutable sellado con SHA-256: {record_hash[:16]}...",
            severity="INFO",
            event_type_audited=event_type,
            record_hash=record_hash,
        )
        return jsonl_entry

    def list_records(self, limit: int = 100) -> list[dict[str, Any]]:
        with db_manager._get_conn() as conn:
            rows = conn.execute(
                """
                SELECT id, event_timestamp, event_type, user_id, user_role, session_id,
                       provider_used, model_used, total_tokens, cost_usd, latency_ms,
                       circuit_breaker_state, metadata_json, prev_hash, record_hash
                FROM immutable_audit_logs
                ORDER BY id DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
            return [dict(r) for r in rows]

    def verify_chain_integrity(self) -> dict[str, Any]:
        """Recorre toda la cadena de auditoría desde el bloque génesis y verifica cada hash SHA-256."""
        with db_manager._get_conn() as conn:
            rows = conn.execute(
                "SELECT * FROM immutable_audit_logs ORDER BY id ASC"
            ).fetchall()

        expected_prev = GENESIS_HASH
        verified_count = 0
        for row in rows:
            recomputed = self.compute_record_hash(
                prev_hash=str(row["prev_hash"]),
                event_timestamp=str(row["event_timestamp"]),
                event_type=str(row["event_type"]),
                user_id=str(row["user_id"]),
                session_id=str(row["session_id"]),
                provider_used=str(row["provider_used"]),
                model_used=str(row["model_used"]),
                total_tokens=int(row["total_tokens"]),
                cost_usd=float(row["cost_usd"]),
            )
            if row["prev_hash"] != expected_prev or recomputed != row["record_hash"]:
                return {
                    "is_valid": False,
                    "verified_records": verified_count,
                    "corrupted_record_id": row["id"],
                    "status": "TAMPER_DETECTED",
                }
            expected_prev = str(row["record_hash"])
            verified_count += 1

        return {
            "is_valid": True,
            "verified_records": verified_count,
            "latest_hash": expected_prev,
            "status": "CHAIN_INTACT_SHA256_VERIFIED",
        }

    def export_csv_bytes(self) -> bytes:
        records = self.list_records(limit=500)
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(
            [
                "id",
                "event_timestamp",
                "event_type",
                "user_id",
                "user_role",
                "session_id",
                "provider_used",
                "model_used",
                "total_tokens",
                "cost_usd",
                "latency_ms",
                "circuit_breaker_state",
                "prev_hash",
                "record_hash",
            ]
        )
        for r in records:
            writer.writerow(
                [
                    r["id"],
                    r["event_timestamp"],
                    r["event_type"],
                    r["user_id"],
                    r["user_role"],
                    r["session_id"],
                    r["provider_used"],
                    r["model_used"],
                    r["total_tokens"],
                    f"{float(r['cost_usd']):.6f}",
                    f"{float(r['latency_ms']):.2f}",
                    r["circuit_breaker_state"],
                    r["prev_hash"],
                    r["record_hash"],
                ]
            )
        return output.getvalue().encode("utf-8")

    def export_pdf_bytes(self, cost_summary: dict[str, Any]) -> bytes:
        """Genera un documento PDF corporativo auditable con ReportLab incluyendo cadena SHA-256 y costos E6."""
        records = self.list_records(limit=40)
        integrity = self.verify_chain_integrity()

        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            leftMargin=36,
            rightMargin=36,
            topMargin=36,
            bottomMargin=36,
        )
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            "TechCorpTitle",
            parent=styles["Heading1"],
            fontSize=15,
            leading=19,
            textColor=colors.HexColor("#0F172A"),
            spaceAfter=8,
        )
        subtitle_style = ParagraphStyle(
            "TechCorpSub",
            parent=styles["Normal"],
            fontSize=9.5,
            leading=13,
            textColor=colors.HexColor("#334155"),
            spaceAfter=12,
        )
        section_style = ParagraphStyle(
            "TechCorpSection",
            parent=styles["Heading2"],
            fontSize=11.5,
            leading=15,
            textColor=colors.HexColor("#1E3A8A"),
            spaceBefore=10,
            spaceAfter=6,
        )

        story: list[Any] = []
        story.append(
            Paragraph(
                "TechCorp LATAM — Reporte Oficial de Auditoría Inmutable y Costos (E6)",
                title_style,
            )
        )
        story.append(
            Paragraph(
                f"Generado UTC: {datetime.now(timezone.utc).isoformat()} | "
                f"Modalidad 2.2: Google ADK + GCP | "
                f"Estado Cadena SHA-256: {integrity['status']} ({integrity['verified_records']} bloques)",
                subtitle_style,
            )
        )

        # Tabla 1: Resumen de Costos E6 y Comparativa de Modalidades
        story.append(
            Paragraph("1. Estimación Mensual de Costos (800 Empleados) y Comparativa E6", section_style)
        )
        mod_rows = [["Modalidad Arquitectónica", "Tokens/Mes", "Cómputo/Mes", "BD + Red/Mes", "Total Mensual (USD)"]]
        for m in cost_summary.get("modalities_comparison", []):
            mod_rows.append(
                [
                    m["name"],
                    f"${m['tokens_usd']:.2f}",
                    f"${m['compute_usd']:.2f}",
                    f"${m['storage_network_usd']:.2f}",
                    f"${m['total_usd']:.2f}",
                ]
            )
        t_mod = Table(mod_rows, colWidths=[195, 75, 80, 85, 105])
        t_mod.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1E293B")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 8.5),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8FAFC")]),
                    ("PADDING", (0, 0), (-1, -1), 5),
                ]
            )
        )
        story.append(t_mod)
        story.append(Spacer(1, 12))

        # Tabla 2: Registros de Auditoría Criptográfica
        story.append(
            Paragraph("2. Últimos Registros de Auditoría Inmutable (JSONL + SHA-256)", section_style)
        )
        audit_rows = [["ID", "Timestamp UTC", "Usuario", "Modelo / Proveedor", "Tokens", "Costo USD", "Hash SHA-256 (Prefijo)"]]
        for r in records[:25]:
            audit_rows.append(
                [
                    str(r["id"]),
                    str(r["event_timestamp"])[:19],
                    str(r["user_id"]),
                    f"{r['model_used']} ({r['provider_used']})",
                    str(r["total_tokens"]),
                    f"${float(r['cost_usd']):.5f}",
                    f"{str(r['record_hash'])[:16]}...",
                ]
            )
        t_audit = Table(audit_rows, colWidths=[28, 95, 75, 135, 45, 58, 104])
        t_audit.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0F766E")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 7.5),
                    ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#CBD5E1")),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F0FDFA")]),
                    ("PADDING", (0, 0), (-1, -1), 4),
                ]
            )
        )
        story.append(t_audit)

        doc.build(story)
        return buffer.getvalue()


immutable_audit_service = ImmutableAuditService()
