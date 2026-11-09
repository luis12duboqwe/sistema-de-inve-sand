#!/usr/bin/env python3
"""Offline rotating sales challenge bank, wholly fictitious and deterministic.

These utterances are independent of the original 72/18 development scenarios.
The bank rotates by UTC day. New families may be added by reviewed commits;
the validator fails closed on malformed fixtures.
"""
from datetime import datetime,timezone
import inventory_training_lab as inventory
import sales_heldout_challenges as held
BANKS=(
 (
  ("negotiation","¿Podría ajustar el precio?",
     "Si lo autorizan, cerramos la compra",""),
  ("negotiation","¿Me mejoran el precio?",
     "Si me lo bajas, seguimos con la compra",""),
  ("reservation","¿Puedo reservar?",
     "¿Me lo reservas para el lunes?","lunes"),
  ("reservation","¿Puedo reservarlo?",
     "¿Me lo reservas para mañana?","manana"),
  ("shipping","¿Hacen envíos a Choloma?",
     "¿En cuánto tiempo llega?","choloma"),
  ("shipping","¿Se puede enviar a Tegucigalpa?",
     "¿Cuánto demora el envío?","tegucigalpa"),
 ),
 (
  ("negotiation","¿Hay posibilidad de descuento?",
     "Si es posible, sigo con la compra",""),
  ("negotiation","¿Me podrían hacer un mejor precio?",
     "De ser posible, hacemos trato",""),
  ("reservation","¿Aceptan reservas de teléfonos?",
     "¿Puedo apartarlo para el domingo?","domingo"),
  ("reservation","¿Sería posible separarlo?",
     "¿Me lo guardan hasta mañana?","manana"),
  ("shipping","¿Hay envío a Choloma?",
     "¿En cuántos días llegaría?","choloma"),
  ("shipping","¿Se puede mandar a Tegucigalpa?",
     "¿Cuánto cuesta el envío?","tegucigalpa"),
 ),
)
def tasks(now=None):
 now=now or datetime.now(timezone.utc)
 bank=BANKS[(now.timetuple().tm_yday+1)%len(BANKS)]
 output=[]
 for i,(family,prior,follow,dest) in enumerate(bank):
  output.append({"id":f"rotation-{i:02d}","family":family,
    "messages":["Busco iPhone 14 Pro Max de 256 GB negro",prior,follow],
    "destination":held.fold(dest),"expected":"not_found"})
 if len(output)!=6 or [x["family"] for x in output].count("negotiation")!=2:
  raise ValueError("rotating family counts invalid")
 inventory.validate_scenarios([
    {"id":t["id"],"messages":t["messages"],"expected":t["expected"]}
    for t in output])
 return output
