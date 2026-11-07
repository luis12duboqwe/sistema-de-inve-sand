"""Offline safety regression suite: no WAHA, Chatwoot or buyer messages required."""
import unittest
from dataclasses import replace
from followup_policy import Evidence, decide, propose

class FollowupSafety(unittest.TestCase):
    def valid(self, **change):
        base = dict(conversation_id=3, quote_id=101, minutes_since_quote=121,
                    open=True, explicit_consent=True, opted_out=False,
                    human_takeover=False, human_replied_since_quote=False,
                    incoming_after_quote_other_than_consent=False,
                    followed_quote_id=None, transport_online=True)
        return Evidence(**(base | change))

    def test_valid_is_manual_review_only(self):
        self.assertEqual(decide(self.valid()),"ready_for_manual_review")

    def test_missing_quote(self):
        self.assertEqual(decide(self.valid(quote_id=None)),"no_verified_quote")

    def test_closed(self):
        self.assertEqual(decide(self.valid(open=False)),"closed")

    def test_optout_wins_over_consent(self):
        self.assertEqual(decide(self.valid(opted_out=True)),"blocked_optout")

    def test_human_takeover(self):
        self.assertEqual(decide(self.valid(human_takeover=True)),"blocked_human")

    def test_human_replied_since_quote(self):
        self.assertEqual(decide(self.valid(human_replied_since_quote=True)),"blocked_human")

    def test_no_repeat_quote(self):
        self.assertEqual(decide(self.valid(followed_quote_id=101)),"blocked_duplicate")

    def test_new_quote_can_be_reviewed(self):
        self.assertEqual(decide(self.valid(followed_quote_id=100)),"ready_for_manual_review")

    def test_customer_replied(self):
        self.assertEqual(decide(self.valid(incoming_after_quote_other_than_consent=True)),
                         "blocked_customer_replied")

    def test_consent_required(self):
        self.assertEqual(decide(self.valid(explicit_consent=False)),"needs_consent")

    def test_early(self):
        self.assertEqual(decide(self.valid(minutes_since_quote=119.9)),"not_due")

    def test_stale(self):
        self.assertEqual(decide(self.valid(minutes_since_quote=1441)),"expired")

    def test_offline_channel(self):
        self.assertEqual(decide(self.valid(transport_online=False)),"blocked_test_transport")

    def test_typecheck_denies_truthy_strings(self):
        fields=self.valid().__dict__.copy()
        fields.pop("transport_online")
        fields["explicit_consent"]="true"
        with self.assertRaises(ValueError):
            Evidence.from_mapping(fields,True)

    def test_missing_fields_deny(self):
        fields=self.valid().__dict__.copy()
        fields.pop("transport_online")
        del fields["opted_out"]
        with self.assertRaises(ValueError):
            Evidence.from_mapping(fields,True)

    def test_malformed_quote_denied(self):
        fields=self.valid().__dict__.copy()
        fields.pop("transport_online")
        fields["quote_id"]="101"
        with self.assertRaises(ValueError):
            Evidence.from_mapping(fields,True)

    def test_aggregation_never_sends(self):
        data = self.valid().__dict__.copy()
        data.pop("transport_online")
        p=propose([data],True)
        self.assertEqual(p["public_messages_sent"],0)
        self.assertEqual(p["eligible_to_send_automatically"],0)
        self.assertTrue(p["cases"][0]["requires_human_approval"])

    def test_pilot_offline_proposal_not_send(self):
        data=self.valid().__dict__.copy()
        data.pop("transport_online")
        p=propose([data],False)
        self.assertEqual(p["by_status"],{"blocked_test_transport":1})
        self.assertEqual(p["public_messages_sent"],0)

    def test_consentless_cannot_contact(self):
        data=self.valid(explicit_consent=False).__dict__.copy()
        data.pop("transport_online")
        p=propose([data],True)
        self.assertEqual(p["by_status"],{"needs_consent":1})
        self.assertEqual(p["eligible_to_send_automatically"],0)

if __name__=="__main__":
    unittest.main()
