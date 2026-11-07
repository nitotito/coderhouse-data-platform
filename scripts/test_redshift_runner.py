"""Local checks of Data API result handling and failed-query behavior. No AWS."""
import importlib.util
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('runner', Path(__file__).with_name('redshift-checkpoint6.py'))
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)


class DataApiRunnerTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.folder_patch = patch.object(runner, 'EVIDENCE', Path(self.temp.name))
        self.folder_patch.start()
        self.client = runner.Runner(types.SimpleNamespace(profile='unused',region='us-east-1',workgroup='test'))

    def tearDown(self):
        self.folder_patch.stop()
        self.temp.cleanup()

    def test_paginated_results_preserve_decimals_and_nulls(self):
        pages = [
            {'Id':'statement-id'}, {'Status':'FINISHED','HasResultSet':True},
            {'ColumnMetadata':[{'name':'amount'},{'name':'note'}],
             'Records':[[{'stringValue':'30.30'},{'isNull':True}]], 'NextToken':'page-two'},
            {'ColumnMetadata':[{'name':'amount'},{'name':'note'}],
             'Records':[[{'stringValue':'15.150000'},{'stringValue':'second'}]]},
        ]
        with patch.object(self.client,'aws',side_effect=pages) as aws:
            result = self.client.query('SELECT amount,note FROM example','pagination')
        self.assertEqual(result,[{'amount':'30.30','note':None},{'amount':'15.150000','note':'second'}])
        self.assertIn('page-two',aws.call_args.args)

    def test_failed_statement_is_saved_and_never_reported_successful(self):
        with patch.object(self.client,'aws',side_effect=[{'Id':'failed-id'},
                          {'Status':'FAILED','Error':'permission denied'}]):
            with self.assertRaisesRegex(RuntimeError,'permission denied'):
                self.client.query('CREATE SCHEMA example','failure')
        self.assertIn('FAILED',(Path(self.temp.name)/'001-failure-execution.json').read_text())

    def test_timeout_cancels_statement(self):
        with patch.object(self.client,'aws',side_effect=[{'Id':'slow-id'},{}]) as aws:
            with patch.object(runner.time,'monotonic',side_effect=[0,181]):
                with self.assertRaises(TimeoutError):
                    self.client.query('SELECT 1','timeout')
        self.assertEqual(aws.call_args.args,('redshift-data','cancel-statement','--id','slow-id'))


if __name__ == '__main__':
    unittest.main()
