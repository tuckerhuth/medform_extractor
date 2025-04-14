import unittest
from unittest.mock import patch, MagicMock, call
import queue
import sys
from pathlib import Path
import os

# Add the parent directory to the path to import launch
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Need to mock dpg before importing launch as it tries to setup context
# We don't need DPG for testing _execute_script logic
mock_dpg = MagicMock()
sys.modules['dearpygui.dearpygui'] = mock_dpg
sys.modules['dearpygui'] = mock_dpg

from launch import ImageProcessorUI, BASE_PATH # Import after mocking DPG

class TestImageProcessorUI(unittest.TestCase):

    def setUp(self):
        """Set up for test methods."""
        # Mock DPG functions that might be called indirectly or during init
        mock_dpg.does_item_exist.return_value = True # Assume items exist for simplicity
        mock_dpg.get_item_width.return_value = 800
        mock_dpg.set_item_width = MagicMock()
        mock_dpg.set_value = MagicMock()
        mock_dpg.configure_item = MagicMock()
        
        self.app = ImageProcessorUI()
        # Clear queue before each test
        while not self.app.queue.empty():
            try:
                self.app.queue.get_nowait()
            except queue.Empty:
                break

    @patch('launch.subprocess.Popen')
    def test_execute_script_success(self, mock_popen):
        """Test successful script execution and queue messages."""
        # Configure the mock Popen object
        mock_process = MagicMock()
        mock_process.stdout.readline.side_effect = ['PROGRESS:1/2\n', 'PROGRESS:2/2\n', ''] # Simulate stdout
        mock_process.stderr.readline.side_effect = [''] # Simulate empty stderr
        mock_process.wait.return_value = 0 # Simulate successful exit code
        mock_popen.return_value = mock_process

        # Define command and process type
        command = ['python', 'dummy_script.py']
        process_type = 'test_success'

        # Execute the script method (runs in the same thread for testing)
        self.app._execute_script(command, process_type)

        # Check if Popen was called correctly
        mock_popen.assert_called_once()
        args, kwargs = mock_popen.call_args
        self.assertEqual(args[0], command)
        self.assertTrue(kwargs.get('text'))
        self.assertEqual(kwargs.get('bufsize'), 1)
        self.assertTrue(kwargs.get('universal_newlines'))

        # Check the messages put into the queue
        expected_messages = [
            {"type": "stdout", "line": "PROGRESS:1/2", "process_type": process_type},
            {"type": "stdout", "line": "PROGRESS:2/2", "process_type": process_type},
            {"type": "finished", "exit_code": 0, "process_type": process_type},
        ]
        
        actual_messages = []
        while not self.app.queue.empty():
            try:
                actual_messages.append(self.app.queue.get_nowait())
            except queue.Empty:
                break

        self.assertEqual(len(actual_messages), len(expected_messages), "Number of messages mismatch")
        for i, expected in enumerate(expected_messages):
            self.assertDictEqual(actual_messages[i], expected, f"Message {i} mismatch")

    @patch('launch.subprocess.Popen')
    def test_execute_script_filenotfound(self, mock_popen):
        """Test script execution when the script file is not found."""
        # Configure mock Popen to raise FileNotFoundError
        mock_popen.side_effect = FileNotFoundError("Script not found")

        command = ['python', 'non_existent_script.py']
        process_type = 'test_fnf'

        # Execute the script method
        self.app._execute_script(command, process_type)

        # Check the messages put into the queue
        expected_messages = [
            {"type": "error", "message": f"Error: Script not found. Command: {' '.join(command)}", "process_type": process_type},
            {"type": "finished", "exit_code": -1, "process_type": process_type},
        ]
        
        actual_messages = []
        while not self.app.queue.empty():
            try:
                actual_messages.append(self.app.queue.get_nowait())
            except queue.Empty:
                break
                
        self.assertEqual(len(actual_messages), len(expected_messages), "Number of messages mismatch")
        for i, expected in enumerate(expected_messages):
             self.assertDictEqual(actual_messages[i], expected, f"Message {i} mismatch")

    @patch('launch.subprocess.Popen')
    def test_execute_script_stderr(self, mock_popen):
        """Test script execution with stderr output."""
        mock_process = MagicMock()
        mock_process.stdout.readline.side_effect = [''] # No stdout
        mock_process.stderr.readline.side_effect = ['Error line 1\n', 'Error line 2\n', ''] # Simulate stderr
        mock_process.wait.return_value = 1 # Simulate error exit code
        mock_popen.return_value = mock_process

        command = ['python', 'error_script.py']
        process_type = 'test_stderr'

        self.app._execute_script(command, process_type)

        expected_messages = [
            {"type": "stderr", "line": "Error line 1", "process_type": process_type},
            {"type": "stderr", "line": "Error line 2", "process_type": process_type},
            {"type": "finished", "exit_code": 1, "process_type": process_type},
        ]
        
        actual_messages = []
        while not self.app.queue.empty():
            try:
                 actual_messages.append(self.app.queue.get_nowait())
            except queue.Empty:
                 break

        self.assertEqual(len(actual_messages), len(expected_messages), "Number of messages mismatch")
        for i, expected in enumerate(expected_messages):
             self.assertDictEqual(actual_messages[i], expected, f"Message {i} mismatch")

if __name__ == '__main__':
    unittest.main() 