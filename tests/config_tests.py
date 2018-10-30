import json
import os
import unittest
import uuid

import boto3

from helper import config


class ConfigDefaultTests(unittest.TestCase):

    def setUp(self):
        self.config = config.Config()

    def test_application(self):
        self.assertDictEqual(self.config.application, config.APPLICATION)

    def test_daemon(self):
        self.assertDictEqual(self.config.daemon, config.DAEMON)

    def test_logging(self):
        self.assertDictEqual(self.config.logging, config.LOGGING)


class RemoteConfigTests(unittest.TestCase):

    def setUp(self):
        self.value = {
            'Application': {
                'key': str(uuid.uuid4())
            },
            'Daemon': {
                'user': str(uuid.uuid4()),
                'group': str(uuid.uuid4())
            },
            'Logging':  {
                'disable_existing_loggers': False,
                'incremental': True}
        }
        self.bucket = str(uuid.uuid4())
        client = boto3.client('s3', endpoint_url=os.environ['S3_ENDPOINT'])
        client.create_bucket(Bucket=self.bucket)
        client.put_object(
            Bucket=self.bucket, Key='test.json',
            Body=json.dumps(self.value),
            ACL='public-read')

    def test_loaded_config(self):
        cfg = config.Config('{}/{}/test.json'.format(
            os.environ['S3_ENDPOINT'], self.bucket))
        for key in self.value['Application'].keys():
            self.assertEqual(cfg.application[key],
                             self.value['Application'][key])
        for key in self.value['Daemon'].keys():
            self.assertEqual(cfg.daemon[key],
                             self.value['Daemon'][key])
        for key in self.value['Logging'].keys():
            self.assertEqual(cfg.logging[key],
                             self.value['Logging'][key])

    def test_value_error_raised_for_missing_file(self):
        with self.assertRaises(ValueError):
            config.Config('{}/{}/{}.json'.format(os.environ['S3_ENDPOINT'],
                                                 self.bucket, uuid.uuid4()))


class S3ConfigTests(RemoteConfigTests):

    def test_loaded_config(self):
        cfg = config.Config('s3://{}/test.json'.format(self.bucket))
        for key in self.value['Application'].keys():
            self.assertEqual(cfg.application[key],
                             self.value['Application'][key])
        for key in self.value['Daemon'].keys():
            self.assertEqual(cfg.daemon[key],
                             self.value['Daemon'][key])
        for key in self.value['Logging'].keys():
            self.assertEqual(cfg.logging[key],
                             self.value['Logging'][key])

    def test_value_error_raised_for_missing_file(self):
        with self.assertRaises(ValueError):
            config.Config('s3://{}/{}.json'.format(self.bucket, uuid.uuid4()))
