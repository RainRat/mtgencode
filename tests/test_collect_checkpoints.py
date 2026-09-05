import os
import runpy
import sys
import tempfile
import unittest

from scripts.collect_checkpoints import (
    cleanup_dump,
    identify_checkpoints,
    process_dir,
    main,
)


class TestCollectCheckpoints(unittest.TestCase):

    def test_cleanup_dump_short(self):
        self.assertEqual(cleanup_dump("card1\n\ncard2\n\ncard3"), "")

    def test_cleanup_dump_valid(self):
        dumpstr = "header\n\nignored\n\ncard1\n\ncard2\n\ntrailer"
        expected = "card1\n\ncard2\n\n"
        self.assertEqual(cleanup_dump(dumpstr), expected)

    def test_identify_checkpoints(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            valid_dump = os.path.join(tmpdir, "lm_lstm_epoch10_0.2500.t7.output.1.0.txt")
            with open(valid_dump, "w") as f:
                f.write("content")

            os.mkdir(os.path.join(tmpdir, "a_directory"))
            with open(os.path.join(tmpdir, "other.txt"), "w") as f:
                f.write("other")
            with open(os.path.join(tmpdir, "lm_lstm_epoch10_0.2500.txt"), "w") as f:
                f.write("missing_t7")
            with open(os.path.join(tmpdir, "lm_lstm_epoch10_0.2500.t7.other.1.0.txt"), "w") as f:
                f.write("wrong_ident")
            with open(os.path.join(tmpdir, "lm_lstm_epoch10.txt"), "w") as f:
                f.write("bad_split")
            with open(os.path.join(tmpdir, "lm_lstm_epoch10_extra_part_0.2500.t7.output.1.0.txt"), "w") as f:
                f.write("too_many_halves")
            with open(os.path.join(tmpdir, "lm_lstm_epoch10_0.2500.output.1.0.txt"), "w") as f:
                f.write("wrong_part_count")
            with open(os.path.join(tmpdir, "lm_lstm_epochoutput_0.2500.t7.other.1.0.txt"), "w") as f:
                f.write("ident_in_epoch_but_wrong_part")

            cp_infos = identify_checkpoints(tmpdir, "output")
            self.assertEqual(len(cp_infos), 1)

            fullpath, cpname, (epoch, vloss, temp) = cp_infos[0]
            self.assertEqual(fullpath, valid_dump)
            self.assertEqual(cpname, os.path.join(tmpdir, "lm_lstm_epoch10_0.2500.t7"))
            self.assertEqual(epoch, "10")
            self.assertEqual(vloss, "0.2500")
            self.assertEqual(temp, "1.0")

    def test_process_dir_and_main(self):
        with tempfile.TemporaryDirectory() as src_dir, tempfile.TemporaryDirectory() as target_dir:
            subdir = os.path.join(src_dir, "run1")
            os.makedirs(subdir)

            dump_path = os.path.join(subdir, "lm_lstm_epoch10_0.2500.t7.output.1.0.txt")
            cp_path = os.path.join(subdir, "lm_lstm_epoch10_0.2500.t7")
            cmd_path = os.path.join(subdir, "command.txt")

            with open(dump_path, "w") as f:
                f.write("head\n\nign\n\ncardA\n\ncardB\n\ntrail")
            with open(cp_path, "w") as f:
                f.write("model_binary")
            with open(cmd_path, "w") as f:
                f.write("th train.lua")

            main(src_dir, target_dir, ident="output", copy_cp=True, verbose=True)

            out_dump = os.path.join(target_dir, "run1_epoch10_0.2500.output.1.0.txt")
            out_cp = os.path.join(target_dir, "run1_epoch10_0.2500.t7")
            out_cmd = os.path.join(target_dir, "run1.command")

            self.assertTrue(os.path.exists(out_dump))
            self.assertTrue(os.path.exists(out_cp))
            self.assertTrue(os.path.exists(out_cmd))

            with open(out_dump, "r") as f:
                content = f.read()
            self.assertEqual(content, "cardA\n\ncardB\n\n")

    def test_process_dir_trailing_slash_and_missing_checkpoint_file(self):
        with tempfile.TemporaryDirectory() as src_dir, tempfile.TemporaryDirectory() as target_dir:
            subdir = os.path.join(src_dir, "run2") + os.sep
            os.makedirs(subdir)

            dump_path = os.path.join(subdir, "lm_lstm_epoch5_0.1000.t7.output.1.0.txt")
            with open(dump_path, "w") as f:
                f.write("head\n\nign\n\ncardX\n\ncardY\n\ntrail")

            process_dir(subdir, target_dir, ident="output", copy_cp=True, verbose=True)

            out_dump = os.path.join(target_dir, "run2_epoch5_0.1000.output.1.0.txt")
            self.assertTrue(os.path.exists(out_dump))

    def test_cli_execution(self):
        with tempfile.TemporaryDirectory() as src_dir, tempfile.TemporaryDirectory() as target_dir:
            subdir = os.path.join(src_dir, "cli_run")
            os.makedirs(subdir)

            dump_path = os.path.join(subdir, "lm_lstm_epoch1_0.5000.t7.output.1.0.txt")
            with open(dump_path, "w") as f:
                f.write("head\n\nign\n\ncardA\n\ncardB\n\ntrail")

            script_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "scripts", "collect_checkpoints.py"))
            orig_argv = sys.argv
            sys.argv = ["collect_checkpoints.py", src_dir, target_dir, "-c", "-i", "output", "-v"]
            try:
                with self.assertRaises(SystemExit) as cm:
                    runpy.run_path(script_path, run_name="__main__")
                self.assertEqual(cm.exception.code, 0)
            finally:
                sys.argv = orig_argv

            out_dump = os.path.join(target_dir, "cli_run_epoch1_0.5000.output.1.0.txt")
            self.assertTrue(os.path.exists(out_dump))

    def test_alias_identity(self):
        self.assertIs(main, process_dir)


if __name__ == "__main__":
    unittest.main()
