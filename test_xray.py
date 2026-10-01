import unittest
from unittest.mock import patch, mock_open
import json

import xray

class TestXrayLoad(unittest.TestCase):
    @patch('builtins.open', new_callable=mock_open, read_data='{"key": "value"}')
    def test_load_success(self, mock_file):
        result = xray.load('dummy.json')
        self.assertEqual(result, {"key": "value"})
        mock_file.assert_called_once_with('dummy.json')

    @patch('builtins.open', side_effect=FileNotFoundError)
    def test_load_file_not_found_default_none(self, mock_file):
        result = xray.load('dummy.json')
        self.assertEqual(result, {})

    @patch('builtins.open', side_effect=FileNotFoundError)
    def test_load_file_not_found_with_default(self, mock_file):
        result = xray.load('dummy.json', default={"default": True})
        self.assertEqual(result, {"default": True})

    @patch('builtins.open', new_callable=mock_open, read_data='invalid json')
    def test_load_invalid_json(self, mock_file):
        result = xray.load('dummy.json')
        self.assertEqual(result, {})

    @patch('builtins.open', new_callable=mock_open, read_data='invalid json')
    def test_load_invalid_json_with_default(self, mock_file):
        result = xray.load('dummy.json', default=[])
        self.assertEqual(result, [])

if __name__ == '__main__':
    unittest.main()
