"""Test the fixture oracle and publication guards without AWS access."""
import datetime as dt
import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch
from decimal import Decimal

spec=importlib.util.spec_from_file_location('capstone',Path(__file__).with_name('capstone.py'))
capstone=importlib.util.module_from_spec(spec);spec.loader.exec_module(capstone)

class FixtureTests(unittest.TestCase):
    def test_equivalent_metrics_preserve_duplicates_and_exclude_only_late(self):
        f=capstone.fixture('test',dt.datetime(2026,1,1,tzinfo=dt.timezone.utc))
        approved=[e for e in f['initial'] if isinstance(e,dict) and e.get('status')=='approved']
        self.assertEqual(len(approved),3)
        self.assertEqual(approved[1]['transaction_id'],approved[2]['transaction_id'])
        total=sum(Decimal(e['amount']) for e in approved)
        self.assertEqual(total,Decimal('30.01'))
        self.assertEqual((total/3).quantize(Decimal('.000001')),Decimal('10.003333'))
        self.assertEqual(total+Decimal(f['after_commit'][0]['amount']),Decimal('1030.01'))
        self.assertEqual(len(f['initial'])+len(f['after_commit']),10)

    def test_dry_run_never_checks_credentials_or_sends_events(self):
        import argparse
        with patch.object(capstone,'context',side_effect=AssertionError('AWS accessed')):
            capstone.e2e(argparse.Namespace(execute=False,manifest='unused'))

if __name__=='__main__':unittest.main()
