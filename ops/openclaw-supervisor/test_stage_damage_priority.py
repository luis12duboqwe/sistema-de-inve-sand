"""Verify the scoped pilot damage-priority patch cannot be accidentally widened."""
import unittest
from stage_damage_priority import candidate,ANCHOR,INSERT

def minimal():
    return ("\nPILOT_CONVERSATION_ID = 3\nINBOX_ID = 2\nAUTO_REPLY_LIMIT = 1\n"+
            "    def critical_buyer_intent(t)\n"+
            "      return :payment_safety if secret\n"+
            ANCHOR+"\n"+"    end\n"+"\nif ENV['SM_MODE']=='test'\n")

class StageDamageTests(unittest.TestCase):
    def test_exact_only_one_replacement(self):
        source=minimal()
        patched=candidate(source)
        self.assertEqual(patched.replace(INSERT,"",1),source)
        self.assertEqual(patched.count(INSERT),1)
    def test_no_double_install(self):
        with self.assertRaises(ValueError):candidate(candidate(minimal()))
    def test_no_duplicate_anchor(self):
        with self.assertRaises(ValueError):candidate(minimal()+ANCHOR)
    def test_missing_scope_rejected(self):
        with self.assertRaises(ValueError):candidate(minimal().replace("PILOT_CONVERSATION_ID = 3","PILOT_CONVERSATION_ID = 4"))
    def test_order_payment_safety_before_complaint(self):
        source=candidate(minimal())
        self.assertLess(source.index("return :payment_safety"),source.index(INSERT))
        self.assertLess(source.index(INSERT),source.index(ANCHOR))

if __name__=="__main__":
    unittest.main()
