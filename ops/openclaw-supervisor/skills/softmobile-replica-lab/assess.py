#!/usr/bin/env python3
"""Read-only baseline diagnostic for Replica Skill + SoftMobile.

Uses only published local supervisor reports. Does not connect to CRM,
WhatsApp, inventory, models, or the network. Writes only to lab-runs.
"""
from __future__ import annotations
import csv
import hashlib
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parents[2]
REPORT = WORKSPACE / "softmobile-supervisor" / "CERTIFICATION.md"
SALES = WORKSPACE / "softmobile-supervisor" / "SALES_REVIEW.md"
SNAPSHOT = WORKSPACE / "softmobile-bot-snapshot" / "sales-bot-v2.rb"
OUT = WORKSPACE / "lab-runs" / "replica-skill" / "baseline"

def parse_gates(body: str) -> list[tuple[str, str]]:
    section = body.split("## Comprobaciones\n", 1)
    if len(section) != 2:
        raise ValueError("Falta seccion de comprobaciones")
    lines = section[1].split("\n## ", 1)[0].splitlines()
    gates = []
    for line in lines:
        m = re.fullmatch(r"- \[(OK|PENDIENTE)\] ([a-z0-9_]+)", line.strip())
        if m:
            gates.append((m.group(2), m.group(1)))
    if len(gates) != 15 or len({name for name, _ in gates}) != 15:
        raise ValueError("Numero de compuertas inesperado; revisar reporte a mano")
    return gates

def main() -> int:
    cert = REPORT.read_text(encoding="utf-8")
    sales = SALES.read_text(encoding="utf-8")
    gates = parse_gates(cert)
    done = sum(status == "OK" for _, status in gates)
    snapsha = hashlib.sha256(SNAPSHOT.read_bytes()).hexdigest()
    source_hashes = re.findall(r"\b[a-f0-9]{64}\b", sales)
    source_sha = source_hashes[0] if source_hashes else ""
    if not source_sha:
        raise ValueError("No hay SHA de fuente en SALES_REVIEW.md")
    OUT.mkdir(parents=True, exist_ok=True)
    matrix = OUT / "release_gates.csv"
    with matrix.open("w", newline="", encoding="utf-8") as fh:
        wr = csv.writer(fh)
        wr.writerow(["feature", "area", "priority", "original", "clone", "notes"])
        for name, status in gates:
            wr.writerow([name, "prelaunch requirement", "must", "yes",
                        "yes" if status == "OK" else "no",
                        "CERTIFICATION.md; cumplimiento de control, no paridad funcional"])
    tool = WORKSPACE / "skills" / "replica-diff" / "parity.py"
    probe = subprocess.run([sys.executable, str(tool), str(matrix), "--markdown"],
                           capture_output=True, text=True, check=True)
    stamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
    warnings = [
        "Reporte documentado, NO validacion end-to-end del cliente real.",
        "La puntuacion de parity.py representa exclusivamente compuertas de certificacion, no calidad del producto.",
        "Salida publica y modificaciones en produccion bloqueadas.",
    ]
    if snapsha != source_sha:
        warnings.append("SHA del snapshot Ruby es distinto al SHA de la fuente reportada: snapshot no es evidencia de codigo activo.")
    text = (
        f"# Diagnostico inicial Replica Skill + SoftMobile\n\n"
        f"Generado UTC: {stamp}\n\n"
        f"- Controles de prelanzamiento aprobados: **{done}/{len(gates)}**.\n"
        f"- SHA Ruby reportado: `{source_sha}`.\n"
        f"- SHA Ruby del snapshot: `{snapsha}`.\n"
        f"- Fuente: `softmobile-supervisor/CERTIFICATION.md`, `SALES_REVIEW.md` y snapshot offline.\n"
        f"- Prueba real WhatsApp/Chatwoot: **NO VERIFICADA**.\n"
        f"- Candidato: **SIN DESPLEGAR**, requiere SHA y evaluacion independiente actualizados.\n\n"
        "## Prueba ejecutada de replica-diff\n\n"
        + probe.stdout + "\n\n## Limites\n\n"
        + "\n".join("- " + item for item in warnings) + "\n\n"
        "## Siguiente prioridad tecnica\n\n"
        "1. Revisar las deficiencias comprobadas de negociacion, reserva y envio en un clon offline con datos ficticios.\n"
        "2. Volver a ejecutar los mismos escenarios en Ruby activo y candidato con hash actual.\n"
        "3. Someter los casos nuevos a QA independiente sin confirmar precio, stock, financiamiento o reserva no verificados.\n"
    )
    (OUT / "baseline.md").write_text(text, encoding="utf-8")
    print(f"READY: controls={done}/{len(gates)}; snapshot_sha_matches={snapsha == source_sha}; files={matrix},{OUT / 'baseline.md'}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())