import unittest
from unittest.mock import patch
import urllib.error

# Import the module to be tested
import xray_tg

class TestXrayTg(unittest.TestCase):
    @patch('urllib.request.urlopen')
    def test_send_success(self, mock_urlopen):
        # Mocking a successful urlopen response
        mock_urlopen.return_value = True

        # Call the function
        result = xray_tg.send("fake_token", "fake_chat", "fake_text")

        # Verify the result is True
        self.assertTrue(result)

        # Verify urlopen was called once
        self.assertEqual(mock_urlopen.call_count, 1)

    @patch('urllib.request.urlopen')
    @patch('builtins.print') # Mock print to avoid cluttering test output
    def test_send_network_failure(self, mock_print, mock_urlopen):
        # Mocking urlopen to raise an exception
        mock_urlopen.side_effect = Exception("Simulated network error")

        # Call the function
        result = xray_tg.send("fake_token", "fake_chat", "fake_text")

        # Verify the result is False
        self.assertFalse(result)

        # Verify urlopen was called once
        self.assertEqual(mock_urlopen.call_count, 1)

        # Verify print was called to log the failure
        mock_print.assert_called_once()

if __name__ == '__main__':
    unittest.main()
