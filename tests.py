import unittest
import os

class TestPyxargs(unittest.TestCase):
    def test_stdin(self):
        cmd = "echo hello world | python pyxargs.py -m stdin \"echo out {}\""
        with os.popen(cmd) as result:
            result = result.readlines()
            self.assertEqual(result, ['out hello\n', 'out world\n'])

    def test_join_command_args(self):
        cmd = "echo hello world | python pyxargs.py -m stdin echo out {}"
        with os.popen(cmd) as result:
            result = result.readlines()
            self.assertEqual(result, ['out hello\n', 'out world\n'])

    def test_multiple_commands(self):
        cmd = "echo hello world | python pyxargs.py -m stdin -s \"echo out1 {}\" \"echo out2 {}\""
        with os.popen(cmd) as result:
            result = result.readlines()
            self.assertEqual(result, ['out1 hello\n', 'out2 hello\n', 'out1 world\n', 'out2 world\n'])

    def test_read_files(self):
        cmd = "python pyxargs.py -r \"\.git\" -o \"echo out {}\""
        with os.popen(cmd) as result:
            result = result.readlines()
            self.assertEqual(result, ['out LICENSE\n', 'out README.md\n', 'out pyxargs.py\n', 'out tests.py\n'])

    def test_re_filter_file_path(self):
        cmd = "python pyxargs.py -r \"\Aconfig\" \"echo out {}\""
        with os.popen(cmd) as result:
            result = result.readlines()
            self.assertEqual(result, [])

    def test_re_filter_file_name(self):
        cmd = "python pyxargs.py -r \"\Aconfig\" -f \"echo out {}\""
        with os.popen(cmd) as result:
            result = result.readlines()
            self.assertEqual(result, ['out config\n'])

    def test_mode_path(self):
        cmd = "python pyxargs.py -m path -r \"\Aconfig\" -f \"echo out {}\""
        with os.popen(cmd) as result:
            result = result.readlines()
            self.assertEqual(result, ['out .git\\config\n'])

    def test_filter_file_extension(self):
        cmd = "python pyxargs.py -r \".+\.py\" \"echo out {}\""
        with os.popen(cmd) as result:
            result = result.readlines()
            self.assertEqual(result, ['out pyxargs.py\n', 'out tests.py\n'])

    def test_resub(self):
        cmd = "python pyxargs.py -r \".+\.py\" --resub \"\.py\" \".txt\" \"{}\" \"echo out {}\""
        with os.popen(cmd) as result:
            result = result.readlines()
            self.assertEqual(result, ['out pyxargs.txt\n', 'out tests.txt\n'])

    def test_re_omit(self):
        cmd = "python pyxargs.py -r \"(.+\.py)|(\.git)\" -o \"echo out {}\""
        with os.popen(cmd) as result:
            result = result.readlines()
            self.assertEqual(result, ['out LICENSE\n', 'out README.md\n'])

    def test_stdin_delimiter(self):
        cmd = "echo hello,world,bye,world | python pyxargs.py --delim , \"echo out {}\""
        with os.popen(cmd) as result:
            result = result.readlines()
            self.assertEqual(result, ['out hello\n', 'out world\n', 'out bye\n', 'out world\n'])

    def test_stdin_delimiter_py(self):
        cmd = "echo hello,world,bye,world | python pyxargs.py --delim , --py \"print('{}')\""
        with os.popen(cmd) as result:
            result = result.readlines()
            self.assertEqual(result, ['hello\n', 'world\n', 'bye\n', 'world\n'])

    def test_trailing_chars_removed(self):
        cmd = "echo hello,world,bye,world | python pyxargs.py --delim , --norun --py \"print('{}')\""
        with os.popen(cmd) as result:
            result = result.readlines()
            self.assertEqual(result, ["print('hello')\n", "print('world')\n", "print('bye')\n", "print('world')\n"])

    def test_extra_delimiter(self):
        cmd = "echo hello,world,bye,world , | python pyxargs.py --delim , --py \"print('{}')\""
        with os.popen(cmd) as result:
            result = result.readlines()
            self.assertEqual(result, ['hello\n', 'world\n', 'bye\n', 'world \n'])

    def test_delimiter_space(self):
        cmd = "echo hello world bye world | python pyxargs.py --delim \" \" --py \"print('{}')\""
        with os.popen(cmd) as result:
            result = result.readlines()
            self.assertEqual(result, ['hello\n', 'world\n', 'bye\n', 'world\n'])

    def test_delimiter_whitespace(self):
        cmd = "echo hello world bye world | python pyxargs.py -m stdin --py \"print('{}')\""
        with os.popen(cmd) as result:
            result = result.readlines()
            self.assertEqual(result, ['hello\n', 'world\n', 'bye\n', 'world\n'])

    def test_pre_post_exec(self):
        cmd = "echo hello world bye world | python pyxargs.py -m stdin --pre \"counter = 0\" --py -s \"print('{}')\" \"counter += 1\" --post \"print(counter)\""
        with os.popen(cmd) as result:
            result = result.readlines()
            self.assertEqual(result, ['hello\n', 'world\n', 'bye\n', 'world\n', '4\n'])

    def test_norun(self):
        cmd = "echo hello world | python pyxargs.py -m stdin --norun \"echo out {}\""
        with os.popen(cmd) as result:
            result = result.readlines()
            self.assertEqual(result, ['echo out hello\n', 'echo out world\n'])

if __name__ == '__main__':
    unittest.main()
