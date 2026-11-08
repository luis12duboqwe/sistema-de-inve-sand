#!/usr/bin/env python3
"""Stage an exact, non-deploying Ruby pilot fix for delivered damaged orders."""
import difflib
import hashlib
import json
from pathlib import Path
import os
import tempfile
from datetime import datetime,timezone

LIVE=Path("/opt/softmobile-waha-test/sales-bot-v2.rb")
STAGE=Path("/opt/softmobile-waha-test/laboratorio-ia/quality/manual-review-candidates")
ANCHOR=r"""      return :complaint if t.match?(/\b(compre|comprado|me vendieron|mi compra|lo recibi|me entregaron|el equipo que compre|despues de comprarlo)\b/) &&"""
INSERT=r"""      # A delivered order with physical damage is a complaint, not tracking.
      # Keep payment safety and explicit cancellation at higher priority.
      return :complaint if t.match?(/\b(?:mi pedido|mi paquete|el pedido|el paquete|la caja|lo que recibi)\b/) &&
        t.match?(/\b(?:llego|recibi|vino|entregaron|recibido)\b/) &&
        t.match?(/\b(?:roto|rota|danado|danada|quebrado|quebrada|golpeado|golpeada|defecto|no funciona|no sirve)\b/)
"""

def candidate(source):
    if not isinstance(source,str) or source.count(ANCHOR)!=1:
        raise ValueError("Ruby critical intent anchor changed")
    if INSERT in source:
        raise ValueError("Fix already installed; no duplicate patch")
    if source.count("    def critical_buyer_intent(t)")!=1:
        raise ValueError("Ambiguous intent method")
    if "PILOT_CONVERSATION_ID = 3" not in source or "\nif ENV['SM_MODE']=='test'\n" not in source:
        raise ValueError("Pilot test boundary absent")
    out=source.replace(ANCHOR,INSERT+ANCHOR,1)
    if out.replace(INSERT,"",1)!=source:
        raise ValueError("Changes outside reviewed statement")
    if not out.index("      return :payment_safety")<out.index(INSERT)<out.index(ANCHOR):
        raise ValueError("Safety routing order invalid")
    return out

def stage():
    source=LIVE.read_text()
    newer=candidate(source)
    STAGE.mkdir(parents=True,exist_ok=True,mode=0o700)
    sha=hashlib.sha256(source.encode()).hexdigest()
    candidate_sha=hashlib.sha256(newer.encode()).hexdigest()
    base="delivered-damage-"+candidate_sha[:16]
    patch="".join(difflib.unified_diff(source.splitlines(True),newer.splitlines(True),
         fromfile="a/sales-bot-v2.rb",tofile="b/sales-bot-v2.rb",n=6))
    metadata={"at":datetime.now(timezone.utc).isoformat(),
              "source_sha256":sha,"candidate_sha256":candidate_sha,
              "candidate_file":base+".rb","diff_file":base+".diff",
              "scope":"PILOT_RUBY_ONLY","status":"staged_not_deployed",
              "automatic_deployment_allowed":False,
              "public_messages_sent":0,"real_inventory_changed":False}
    for fname,content in ((base+".rb",newer),(base+".diff",patch),
                          (base+".json",json.dumps(metadata,ensure_ascii=False,indent=2)+"\n")):
        fd,tmp=tempfile.mkstemp(prefix=".stage-",dir=STAGE)
        try:
            with os.fdopen(fd,"w",encoding="utf8") as stream:
                stream.write(content);stream.flush();os.fsync(stream.fileno())
            os.chmod(tmp,0o600)
            os.replace(tmp,STAGE/fname)
        finally:
            if os.path.exists(tmp):os.unlink(tmp)
    return metadata

if __name__=="__main__":
    result=stage()
    print(json.dumps(result,ensure_ascii=False))
