import unittest
import shutil
import os

class TestPyxargs(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        shutil.rmtree("__pycache__", True)
        shutil.rmtree("pyxargs.egg-info", True)
        file_content = ["Hello\n", "World\n", "192.168.0.1\n"]
        with open("test.txt", "w") as f:
            f.writelines(file_content)

    @classmethod
    def tearDownClass(cls):
        os.remove("test.txt")

    def test_stdin(self):
        cmd = "echo hello world | python pyxargs.py -m stdin \"echo out {}\""
        with os.popen(cmd) as result:
            result = result.readlines()
            self.assertEqual(result, ['out hello\n', 'out world\n'])

    def test_invoke_pyxargs_from_install(self):
        cmd = "echo hello world | pyxargs -m stdin \"echo out {}\""
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
            self.assertEqual(result, ['out LICENSE\n', 'out README.md\n', 'out pyxargs.py\n', 'out setup.py\n', 'out test.txt\n', 'out tests.py\n'])

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
            if os.name == "nt":
                self.assertEqual(result, ['out .git\\config\n'])
            else:
                self.assertEqual(result, ['out .git/config\n'])

    def test_filter_file_extension(self):
        cmd = "python pyxargs.py -r \".+\.py\" \"echo out {}\""
        with os.popen(cmd) as result:
            result = result.readlines()
            self.assertEqual(result, ['out pyxargs.py\n', 'out setup.py\n', 'out tests.py\n'])

    def test_resub(self):
        cmd = "python pyxargs.py -r \".+\.py\" --resub \"\.py\" \".txt\" \"{}\" \"echo out {}\""
        with os.popen(cmd) as result:
            result = result.readlines()
            self.assertEqual(result, ['out pyxargs.txt\n', 'out setup.txt\n', 'out tests.txt\n'])

    def test_re_omit(self):
        cmd = "python pyxargs.py -r \"(.+\.py)|(\.git)\" -o \"echo out {}\""
        with os.popen(cmd) as result:
            result = result.readlines()
            self.assertEqual(result, ['out LICENSE\n', 'out README.md\n', 'out test.txt\n'])

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

    def test_exec_namespace(self):
        cmd = "echo hello world bye world | python pyxargs.py -m stdin --pre \"output = 0\" --py -s \"print('{}')\" \"output += 1\" --post \"print(locals())\""
        with os.popen(cmd) as result:
            result = result.readlines()
            self.assertEqual(result, ['hello\n', 'world\n', 'bye\n', 'world\n', "{'output': 4}\n"])

    def test_import(self):
        cmd = "echo hello world bye world | python pyxargs.py -m stdin --import math --importstar math --pre \"output = 0\" --py -s \"print('{}')\" \"output += math.sin(pi/2)\" --post \"print(output)\""
        with os.popen(cmd) as result:
            result = result.readlines()
            self.assertEqual(result, ['hello\n', 'world\n', 'bye\n', 'world\n', '4.0\n'])

    def test_norun(self):
        cmd = "echo hello world | python pyxargs.py -m stdin --norun \"echo out {}\""
        with os.popen(cmd) as result:
            result = result.readlines()
            self.assertEqual(result, ['echo out hello\n', 'echo out world\n'])

    def test_read_items_cat_type(self):
        if os.name == "nt":
            cmd = "type test.txt | pyxargs -m stdin echo out {}"
        elif os.name == "posix":
            cmd = "cat test.txt | pyxargs -m stdin echo out {}"
        else:
            self.assertEqual(True, False, "Unrecognized OS by this test")
        with open("test.txt", "r") as f:
            file_content = f.readlines()
        solution = []
        for line in file_content:
            solution.append("out " + line)
        with os.popen(cmd) as result:
            result = result.readlines()
            self.assertEqual(result, solution)

    def test_read_items_file(self):
        cmd = "python pyxargs.py -a test.txt echo out {}"
        with open("test.txt", "r") as f:
            file_content = f.readlines()
        solution = []
        for line in file_content:
            solution.append("out " + line)
        with os.popen(cmd) as result:
            result = result.readlines()
            self.assertListEqual(result, solution)

if __name__ == '__main__':
    unittest.main()
