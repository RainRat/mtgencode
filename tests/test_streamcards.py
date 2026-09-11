import unittest
from unittest.mock import patch, MagicMock, mock_open
import os
import sys
import signal
import runpy

sys.path.append(os.path.join(os.path.dirname(__file__), '../scripts'))
sys.path.append(os.path.join(os.path.dirname(__file__), '../lib'))

import streamcards

class TestStreamCards(unittest.TestCase):

    def test_spawn_stream_threads(self):
        target_mock = MagicMock()
        fds = [10, 20]
        threads = streamcards.spawn_stream_threads(fds, target_mock)
        self.assertEqual(len(threads), 2)
        for t in threads:
            t.join()
        self.assertEqual(target_mock.call_count, 2)
        target_mock.assert_any_call(0, 10)
        target_mock.assert_any_call(1, 20)

    @patch('psutil.Process')
    @patch('os.getpid', return_value=1234)
    def test_force_kill_self_noreturn(self, mock_getpid, mock_process_cls):
        mock_child = MagicMock()
        mock_self = MagicMock()
        mock_self.children.return_value = [mock_child]
        mock_process_cls.return_value = mock_self

        streamcards.force_kill_self_noreturn()

        mock_process_cls.assert_called_once_with(1234)
        mock_self.children.assert_called_once_with(recursive=True)
        mock_child.terminate.assert_called_once()
        mock_self.terminate.assert_called_once()

    @patch('streamcards.force_kill_self_noreturn')
    def test_handler_kill_self(self, mock_force_kill):
        streamcards.handler_kill_self(signal.SIGQUIT, None)
        mock_force_kill.assert_called_once()

        mock_force_kill.reset_mock()
        with patch('traceback.print_stack'):
            streamcards.handler_kill_self(signal.SIGINT, None)
        mock_force_kill.assert_called_once()

    @patch('signal.signal')
    def test_install_suicide_handlers(self, mock_signal):
        streamcards.install_suicide_handlers()
        expected_signals = [signal.SIGHUP, signal.SIGINT, signal.SIGQUIT]
        self.assertEqual(mock_signal.call_count, 3)
        for sig in expected_signals:
            mock_signal.assert_any_call(sig, streamcards.handler_kill_self)

    @patch('streamcards.force_kill_self_noreturn')
    @patch('time.sleep')
    def test_wait_and_kill_self_noreturn_threads_done(self, mock_sleep, mock_force_kill):
        mock_thread = MagicMock()
        mock_thread.is_alive.return_value = False
        streamcards.wait_and_kill_self_noreturn([mock_thread])
        mock_force_kill.assert_called_once()

    @patch('streamcards.force_kill_self_noreturn')
    @patch('os.getppid', return_value=1)
    @patch('time.sleep')
    def test_wait_and_kill_self_noreturn_reparented(self, mock_sleep, mock_getppid, mock_force_kill):
        mock_thread = MagicMock()
        mock_thread.is_alive.return_value = True
        streamcards.wait_and_kill_self_noreturn([mock_thread])
        mock_force_kill.assert_called_once()

    @patch('streamcards.wait_and_kill_self_noreturn')
    @patch('streamcards.spawn_stream_threads')
    @patch('streamcards.install_suicide_handlers')
    def test_streaming_noreturn(self, mock_install, mock_spawn, mock_wait):
        mock_spawn.return_value = ['dummy_thread']
        fds = [3]
        target = MagicMock()
        with self.assertRaises(AssertionError) as ctx:
            streamcards.streaming_noreturn(fds, target)
        self.assertIn('should not return from streaming', str(ctx.exception))
        mock_install.assert_called_once()
        mock_spawn.assert_called_once_with(fds, target)
        mock_wait.assert_called_once_with(['dummy_thread'])

    @patch('builtins.open', new_callable=mock_open)
    @patch('jdecode.mtg_open_file')
    @patch('streamcards.streaming_noreturn')
    def test_main_and_write_stream(self, mock_streaming, mock_mtg_open, mock_file):
        card_mock = MagicMock()
        card_mock.encode.return_value = "encoded_card"
        mock_mtg_open.return_value = [card_mock]

        def fake_streaming(fds, write_stream_fn):
            write_stream_fn(0, 3)

        mock_streaming.side_effect = fake_streaming

        args = MagicMock()
        args.fds = [3]
        args.fname = 'fake_file.json'
        args.block_size = 10000
        args.seed = 42

        # Make write loop terminate after 1 card write
        side_effects = [None, Exception("break loop")]
        card_mock.encode.side_effect = side_effects

        with self.assertRaises(Exception) as ctx:
            streamcards.main(args)
        self.assertIn("break loop", str(ctx.exception))

        mock_mtg_open.assert_called_once_with('fake_file.json', verbose=True, linetrans=True)
        mock_file.assert_called_once_with('/proc/self/fd/3', 'wt')

    @patch('builtins.open', new_callable=mock_open)
    @patch('jdecode.mtg_open_file')
    @patch('streamcards.streaming_noreturn')
    def test_main_and_write_stream_default_seed(self, mock_streaming, mock_mtg_open, mock_file):
        card_mock = MagicMock()
        card_mock.encode.return_value = "encoded_card"
        mock_mtg_open.return_value = [card_mock]

        def fake_streaming(fds, write_stream_fn):
            write_stream_fn(0, 4)

        mock_streaming.side_effect = fake_streaming

        args = MagicMock()
        args.fds = [4]
        args.fname = 'fake_file.json'
        args.block_size = 10000
        args.seed = 0

        card_mock.encode.side_effect = [None, Exception("break loop")]

        with self.assertRaises(Exception) as ctx:
            streamcards.main(args)
        self.assertIn("break loop", str(ctx.exception))

    @patch('builtins.open', new_callable=mock_open)
    @patch('psutil.Process')
    @patch('os.getppid', return_value=1)
    @patch('jdecode.mtg_open_file')
    @patch('sys.argv', ['streamcards.py', '3', '4', '-s', '123'])
    def test_cli_execution(self, mock_mtg_open, mock_getppid, mock_psutil, mock_file):
        mock_mtg_open.return_value = []
        script_path = os.path.join(os.path.dirname(__file__), '../scripts/streamcards.py')
        with self.assertRaises(AssertionError) as ctx:
            runpy.run_path(script_path, run_name='__main__')
        self.assertIn('should not return from streaming', str(ctx.exception))

if __name__ == '__main__':
    unittest.main()
