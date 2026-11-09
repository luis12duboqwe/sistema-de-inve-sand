#!/usr/bin/env python3
"""Replica Skill review of existing offline sales autofix proposals; never deploys."""
from __future__ import annotations
import csv
from datetime import datetime, timezone
import difflib
import fcntl
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

BASE = Path("/opt/softmobile-waha-test")
LAB = BASE / "laboratorio-ia"
INPUT = LAB / "quality/autonomous-sales/latest.json"
SOURCE = BASE / "sales-bot-v2.rb"
EXPECTED_SOURCE_SHA = "1336f52fdf4d8e447af1816f705fc24ecb4de78a84f50ebf88f368eaaa363bc1"
CERT = Path("/opt/openclaw-lab/workspace/softmobile-supervisor/CERTIFICATION.json")
ROOT = Path("/opt/openclaw-lab/workspace/lab-runs/replica-skill")
PARITY = Path("/opt/openclaw-lab/workspace/skills/replica-diff/parity.py")
PROBE = Path("/opt/openclaw-lab/supervisor/replica_qa_probe.py")
ALLOWED_DIR = LAB / "quality/autonomous-sales/candidates"

class Blocked(Exception):
    pass

def digest(raw):
    return hashlib.sha256(raw).hexdigest()

def write_atomic(path: Path, content: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=".replica-")
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(content)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)

def to_json(x):
    return json.dumps(x, ensure_ascii=False, indent=2, sort_keys=True) + "\n"

def check_file(path, expected):
    if not isinstance(path, str) or not expected or not isinstance(expected, str):
        raise Blocked("candidate metadata invalid")
    p = Path(path)
    if p.parent != ALLOWED_DIR or p.name != f"candidate-{expected[:16]}.rb":
        raise Blocked("candidate path not allowlisted")
    if p.is_symlink() or not p.is_file() or p.stat().st_size > 250000:
        raise Blocked("candidate missing, linked or oversized")
    if digest(p.read_bytes()) != expected:
        raise Blocked("candidate hash mismatch")
    return p

def preflight():
    cert = json.loads(CERT.read_text())
    if cert.get("public_release_permitted") is not False or cert.get("scope") != "sales_only":
        raise Blocked("certification unexpectedly allows public or scope is wrong")
    report = json.loads(INPUT.read_text())
    safety = dict(environment="OFFLINE_AUTONOMOUS_SALES", scope="sales_only",
                  status="qa_passed_review_required", source_pinned=True,
                  candidate_staged=True, candidate_integrated=False,
                  candidate_deployed=False, deployment_authorized=False,
                  manual_review_required=True, public_messages_sent=0,
                  real_sales=0, payments_initiated=0,
                  real_inventory_modified=False, real_customer_data_loaded=False,
                  active_ruby_modified=False)
    for k, expected in safety.items():
        if report.get(k) != expected or type(report.get(k)) != type(expected):
            raise Blocked(f"untrusted autofix flag: {k}")
    done = datetime.fromisoformat(report["completed_at"].replace("Z", "+00:00"))
    age = (datetime.now(timezone.utc) - done).total_seconds()
    if not 0 <= age <= 9 * 3600:
        raise Blocked("autofix evidence stale or from future")
    if SOURCE.is_symlink():
        raise Blocked("linked source")
    original = SOURCE.read_bytes()
    if digest(original) != EXPECTED_SOURCE_SHA or report.get("source_sha256") != digest(original):
        raise Blocked("live source drift: needs re-audit before candidate generation")
    item = report.get("winning_candidate") or {}
    expected = item.get("sha256")
    if not isinstance(expected, str) or len(expected) != 64:
        raise Blocked("candidate digest invalid")
    candidate = check_file(item.get("candidate_file"), expected)
    patch = Path(item.get("patch_file", ""))
    if (patch.parent != ALLOWED_DIR or patch.name != f"candidate-{expected[:16]}.patch"
        or patch.is_symlink() or not patch.is_file() or patch.stat().st_size > 16500
        or item.get("auto_deploy") is not False):
        raise Blocked("patch metadata or path invalid")
    # Strict byte-for-byte, reproducible patch: only approved candidate may pass.
    predicted = "".join(difflib.unified_diff(
        original.decode("utf-8").splitlines(True),
        candidate.read_text(encoding="utf-8").splitlines(True),
        fromfile="a/sales-bot-v2.rb", tofile="b/sales-bot-v2.rb"))
    if not predicted or predicted != patch.read_text(encoding="utf-8"):
        raise Blocked("patch does not reproduce live source comparison")
    evaluations = report.get("evaluations")
    if (not isinstance(evaluations, list) or not evaluations or
        not isinstance(evaluations[-1], dict) or
        evaluations[-1].get("status") != "qa_passed_review_required"):
        raise Blocked("final candidate not QA-approved by generator")
    return report, original, candidate

def qa_again(candidate):
    result = subprocess.run([sys.executable, str(PROBE), "--candidate", str(candidate)],
        capture_output=True, text=True, timeout=190, check=False,
        env={"PATH": "/usr/local/bin:/usr/bin:/bin", "HOME": "/tmp",
             "PYTHONDONTWRITEBYTECODE": "1"})
    if result.returncode or not result.stdout.strip():
        raise Blocked("offline QA probe failed (no candidate approved)")
    try:
        value = json.loads(result.stdout.strip())
    except ValueError as err:
        raise Blocked("offline QA output invalid") from err
    if (value.get("mode") != "REPLICA_OFFLINE_QA" or
        value.get("source_sha256") != digest(candidate.read_bytes()) or
        value.get("passed") is not True or
        value.get("network_allowed") is not False or
        value.get("public_messages_sent") != 0 or
        value.get("production_modified") is not False or
        value.get("deployment_allowed") is not False):
        raise Blocked("offline QA safety or counts rejected")
    return value

def make_artifacts(report, qa, folder):
    matrix = folder / "features.csv"
    matrix.parent.mkdir(parents=True, exist_ok=True)
    with matrix.open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["feature", "area", "priority", "original", "clone", "notes"])
        for family, values in qa["dialogue"]["by_family"].items():
            passed, total = values["passed"], values["tested"]
            state = "yes" if total == 12 and passed == total else "partial" if passed else "no"
            w.writerow([family, "synthetic sales dialogues", "must", "yes", state,
                        f"offline Ruby answers {passed}/{total}; not a real sale"])
    parity = subprocess.run([sys.executable, str(PARITY), str(matrix), "--markdown"],
                            text=True, capture_output=True, timeout=25, check=True)
    write_atomic(folder / "recon.md",
        "# Reconocimiento Replica Skill: SoftMobile\n\n"
        "Alcance autorizado: venta de celulares, preguntas de compra, financiamiento, "
        "negociacion, reserva, envio y garantia/accesorios.\n\n"
        "Fuente: Ruby original fijado por SHA; candidato generado por el autocorrector "
        "existente. Sin aplicaciones externas copiadas, sin clientes reales ni despliegue.\n"
        "Habilidades empleadas: replica-recon, replica-test y replica-diff; "
        "replica-build es la receta acotada del autofix existente.\n")
    write_atomic(folder / "parity.md", "# Replica-diff: cobertura sintetica (NO preparacion para publico)\n\n" + parity.stdout)
    write_atomic(folder / "test_results.json", to_json(qa))
    write_atomic(folder / "issues.md",
        "# Brechas actuales\n\n"
        "- QA con rubricas independientes de la implementacion de las pruebas: **pendiente**. "
        "La segunda ejecucion repite evaluadores del mismo laboratorio.\n"
        "- Confirmar catalogo, stock y precios autorizados por los aliados: **pendiente**.\n"
        "- Revisar SHA y diff del parche comercial por un desarrollador: **pendiente**.\n"
        "- Conciliar ordenes reales y datos publicitarios: **pendiente**.\n"
        "- Canal WhatsApp/Chatwoot real: **aplazado para ultima fase**.\n"
        "- El porcentaje de parity.py mide exclusivamente las seis familias "
        "sinteticas; NO mide la calidad comercial global.\n")
    candidate_sha = report["winning_candidate"]["sha256"]
    write_atomic(folder / "decision.md",
        f"# Dictamen Replica Skill\n\n"
        f"**RESULTADO: CANDIDATO APROBADO SOLO PARA REVISION HUMANA, NO PARA PUBLICO**\n\n"
        f"Ruby de origen: `{EXPECTED_SOURCE_SHA}`\n\n"
        f"Candidato SHA256: `{candidate_sha}`\n\n"
        f"Parche (ruta interna; no aplicado): `{report['winning_candidate']['patch_file']}`\n\n"
        f"- Dialogos: {qa['dialogue']['passed']}/{qa['dialogue']['total']}\n"
        f"- Reformulaciones: {qa['heldout']['passed']}/{qa['heldout']['total']}\n"
        f"- Ataques simulados: {qa['adversarial']['passed']}/{qa['adversarial']['total']}\n"
        f"- Casos rotativos: {qa['rotating']['passed']}/{qa['rotating']['total']}\n"
        f"- Compra ficticia: {qa['checkout']['passed']}/{qa['checkout']['total']}\n"
        f"- Pruebas unitarias: {qa['unit_tests_passed']}\n\n"
        "Ninguna accion productiva ni mensaje publico. "
        "No autoriza fusionar, instalar, enviar mensajes o realizar cobros.\n")
    return str(folder / "decision.md")

def one_cycle():
    report, original, candidate = preflight()
    qa = qa_again(candidate)
    # Check after long QA, fail closed if source or candidate changed.
    if digest(SOURCE.read_bytes()) != EXPECTED_SOURCE_SHA:
        raise Blocked("source changed during QA")
    if digest(candidate.read_bytes()) != qa["source_sha256"]:
        raise Blocked("candidate changed during QA")
    if json.loads(INPUT.read_text()).get("winning_candidate", {}).get("sha256") != qa["source_sha256"]:
        raise Blocked("autofix proposal changed during QA")
    day = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    folder = ROOT / "runs" / (day + "-" + qa["source_sha256"][:10])
    decision = make_artifacts(report, qa, folder)
    return {"schema_version": 1, "at": datetime.now(timezone.utc).isoformat(),
        "mode": "REPLICA_AUTONOMOUS_SALES_REVIEW", "status": "qa_passed_review_required",
        "scope": "sales_only", "source_sha256": EXPECTED_SOURCE_SHA,
        "candidate_sha256": qa["source_sha256"],
        "replica_tools": ["replica-recon", "replica-test", "replica-diff"],
        "generator": "bounded_existing_autofix",
        "qa_repeated": True, "independent_rubric_converged": False,
        "qa": {"dialogues": qa["dialogue"]["passed"], "heldout": qa["heldout"]["passed"],
               "adversarial": qa["adversarial"]["passed"], "rotating": qa["rotating"]["passed"],
               "checkout": qa["checkout"]["passed"], "units": qa["unit_tests_passed"]},
        "decision_file": decision, "manual_review_required": True,
        "public_release_permitted": False, "public_messages_sent": 0,
        "production_modified": False, "auto_deployed": False, "ai_api_calls": 0}

def main():
    ROOT.mkdir(parents=True, exist_ok=True)
    with (ROOT / "review.lock").open("a+") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            print("replica review already running")
            return 0
        try:
            result = one_cycle()
        except (OSError, KeyError, TypeError, ValueError, Blocked,
                subprocess.SubprocessError, UnicodeError) as err:
            result = {"schema_version": 1, "at": datetime.now(timezone.utc).isoformat(),
                      "mode": "REPLICA_AUTONOMOUS_SALES_REVIEW",
                      "status": "blocked", "reason": str(err)[:160],
                      "manual_review_required": True,
                      "public_release_permitted": False,
                      "public_messages_sent": 0, "production_modified": False,
                      "auto_deployed": False, "ai_api_calls": 0}
        write_atomic(ROOT / "latest.json", to_json(result))
        write_atomic(ROOT / "latest.md",
            "# Replica Skill + SoftMobile: automatic lab review\n\n"
            + "Estado: **" + result["status"] + "**\n\n"
            + "Motivo: " + str(result.get("reason", "QA sintética repetida, pendiente revision independiente")) + "\n\n"
            + "Publico: bloqueado; mensajes enviados: 0; cambios productivos: 0.\n")
        print(json.dumps({"status": result["status"], "candidate_sha256": result.get("candidate_sha256"),
                          "reason": result.get("reason"),
                          "auto_deployed": False, "public_messages_sent": 0}))
        return 0 if result["status"] == "qa_passed_review_required" else 2

if __name__ == "__main__":
    raise SystemExit(main())