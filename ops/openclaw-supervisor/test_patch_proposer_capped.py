"""Unit tests for AI development token budget isolation."""
import unittest
from patch_proposer_capped import cap, MAX_DAILY

class PatchBudgetTests(unittest.TestCase):
    def test_normal_four(self):
        self.assertEqual(cap(4),4)
    def test_unlimited_is_capped(self):
        self.assertEqual(cap(1000000000000),MAX_DAILY)
    def test_small_cap_remains_small(self):
        self.assertEqual(cap(1),1)
    def test_bad_inputs_rejected(self):
        for value in (0,-1,"4",True,None,4.5):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):cap(value)

if __name__=='__main__':unittest.main()
