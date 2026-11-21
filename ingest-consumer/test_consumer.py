import unittest
from decimal import Decimal
from consumer import parse
import json

class ValidationTests(unittest.TestCase):
    def event(self,**changes):
        e=dict(transaction_id="id",payment_method="card",status="approved",amount="10.01",timestamp="2026-11-20T22:00:00-03:00")
        e.update(changes)
        return json.dumps(e)
    def test_iso_and_epoch_converge_in_utc(self):
        iso=parse(self.event())
        epoch=parse(self.event(timestamp=str(int(iso[1].timestamp()*1000))))
        self.assertEqual(iso[1],epoch[1])
        self.assertEqual(iso[2],Decimal("10.01"))
    def test_bad_dates_missing_timezone_and_fractional_cents_are_rejected(self):
        for override in (dict(timestamp="2026-02-30T01:00:00Z"),dict(timestamp="2026-11-20T22:00:00"),dict(amount=".001"),dict(amount="NaN"),dict(amount="1e16"),dict(transaction_id="")):
            with self.subTest(override=override):
                self.assertIsNone(parse(self.event(**override)))
    def test_unknown_metadata_does_not_break_valid_event(self):
        self.assertIsNotNone(parse(self.event(produced_at="metadata")))

if __name__=="__main__":
    unittest.main()
