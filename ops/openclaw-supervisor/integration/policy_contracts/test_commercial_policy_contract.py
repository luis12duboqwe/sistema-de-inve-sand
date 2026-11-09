"""Versioned commercial test contract replacing FIVE obsolete, unsafe assertions.

All other inherited checks from the 47-test legacy suite run unchanged.
The original test_dialogos_aprobados.py stays intact and readable for audit.
This test module is copied from a root-owned contract file into each isolated
snapshot and cannot be changed by the coding agent.
"""
import test_dialogos_aprobados as _legacy
from sales_ai_agent import Conversation, respond
from test_sales_ai_agent import fake, x
from reference_inventory import ReferenceCatalog
from agent_public_pilot import reply_to
from unittest.mock import patch

CONTRACT_VERSION = "reference-only-no-quote-or-unconfirmed-handoff-v2"
SUPERSEDED = (
    "test_ai_untrusted_price",
    "test_ai_multi_turn_payment",
    "test_provider_outage_keeps_commercial_context",
    "test_unknown_outage_handoff",
    "test_pilot_unknown_outage_handoff",
)

class Contract(_legacy.Conversaciones):
    """All unchanged legacy checks still run through inheritance."""

    def test_ai_untrusted_price(self):
        result=respond("¿Cuánto cuesta el iPhone 14 Pro Max de 256 GB negro?",
                       Conversation(),fake(x(intent="price"),"Sí hay, cuesta L 1."),
                       ReferenceCatalog())
        answer=result["reply"].lower()
        self.assertNotIn("16,700",answer)  # historical list price is unverified
        self.assertNotIn("sí hay",answer)
        self.assertNotIn("l 1.",answer)
        self.assertRegex(answer,r"verific|confirm|pendiente")

    def test_ai_multi_turn_payment(self):
        state=Conversation()
        model=fake(x(intent="price"),"Un asesor debe confirmar el precio.")
        for msg in ["iPhone 14 Pro Max 256 GB negro",
                    "¿Cuánto cuesta a 12 meses con Atlántida?"]:
            respond(msg,state,model,ReferenceCatalog())
        answer=respond("Mejor un solo pago con tarjeta, ¿cuánto cuesta?",
                       state,model,ReferenceCatalog())["reply"].lower()
        self.assertNotIn("17,368",answer)  # no validated merchant price
        self.assertNotIn("al mes",answer)   # should not promise installments
        self.assertRegex(answer,r"verific|confirm|condiciones|banco")

    def test_provider_outage_keeps_commercial_context(self):
        def offline(*args):raise RuntimeError("provider unavailable")
        state=Conversation()
        for msg in ["Precio del iPhone 14 Pro Max","256 GB","¿Y con tarjeta?"]:
            result=respond(msg,state,offline,ReferenceCatalog())
        self.assertEqual(result["provider_status"],"unavailable")
        self.assertEqual(len(state.commercial_history),3)
        answer=result["reply"].lower()
        self.assertNotIn("17,368",answer)
        self.assertRegex(answer,r"verific|confirm|condiciones|precio")

    def test_unknown_outage_handoff(self):
        def offline(*args):raise RuntimeError("provider unavailable")
        result=respond("Venden repuestos para drones?",Conversation(),
                       offline,ReferenceCatalog())
        self.assertEqual(result["provider_status"],"unavailable")
        self.assertNotEqual(result["reply"],"En un momento, el encargado te responderá.")
        self.assertRegex(result["reply"].lower(),r"verific|confirm|revis")
        self.assertNotIn("ya asignado",result["reply"].lower())

    def test_pilot_unknown_outage_handoff(self):
        with patch("agent_public_pilot.groq_caller",
                   side_effect=RuntimeError("offline")):
            answer,source=reply_to("Venden repuestos para drones?",[])
        self.assertEqual(source,"approved_commercial")
        self.assertNotEqual(answer,"En un momento, el encargado te responderá.")
        self.assertRegex(answer.lower(),r"verific|confirm|revis")
        self.assertNotIn("ya asignado",answer.lower())