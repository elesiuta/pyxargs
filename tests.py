import os
import shutil
import unittest

class TestPyxargs(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        shutil.rmtree("pyxargs.egg-info", True)
        file_content = ["Hello\n", "World\n", "192.168.0.1\n"]
        with open("test.txt", "w") as f:
            f.writelines(file_content)

    @classmethod
    def tearDownClass(cls):
        os.remove("test.txt")
        shutil.rmtree("__pycache__", True)

    def test_stdin(self):
        cmd = "echo hello world | python pyxargs.py -m stdin echo out {}"
        with os.popen(cmd) as result:
            result = result.readlines()
            self.assertEqual(result, ['out hello\n', 'out world\n'])

    def test_join_command_args(self):
        cmd = "echo hello world | python pyxargs.py -m stdin echo out {}"
        with os.popen(cmd) as result:
            result = result.readlines()
            self.assertEqual(result, ['out hello\n', 'out world\n'])

    def test_read_files(self):
        cmd = "python pyxargs.py -r \"(\.git|__pycache__)\" -o echo out {}"
        with os.popen(cmd) as result:
            result = result.readlines()
            self.assertEqual(result, ['out LICENSE\n', 'out README.md\n', 'out pyxargs.py\n', 'out setup.py\n', 'out test.txt\n', 'out tests.py\n'])

    def test_re_filter_file_path(self):
        cmd = "python pyxargs.py -r \"\Aconfig\" echo out {}"
        with os.popen(cmd) as result:
            result = result.readlines()
            self.assertEqual(result, [])

    def test_re_filter_file_name(self):
        cmd = "python pyxargs.py -r \"\\Aconfig\" -b echo out {}"
        with os.popen(cmd) as result:
            result = result.readlines()
            self.assertEqual(result, ['out config\n'])

    def test_mode_path(self):
        cmd = "python pyxargs.py -m path -r \"\\Aconfig\" -b echo out {}"
        with os.popen(cmd) as result:
            result = result.readlines()
            if os.name == "nt":
                self.assertEqual(result, ["out '.git\\config'\n"])
            else:
                self.assertEqual(result, ['out .git/config\n'])

    def test_filter_file_extension(self):
        cmd = "python pyxargs.py -r \".+\.py$\" echo out {}"
        with os.popen(cmd) as result:
            result = result.readlines()
            self.assertEqual(result, ['out pyxargs.py\n', 'out setup.py\n', 'out tests.py\n'])

    def test_resub(self):
        cmd = "python pyxargs.py -r \".+\.py$\" --resub \"\.py\" \".txt\" \"{}\" echo out {}"
        with os.popen(cmd) as result:
            result = result.readlines()
            self.assertEqual(result, ['out pyxargs.txt\n', 'out setup.txt\n', 'out tests.txt\n'])

    def test_re_omit(self):
        cmd = "python pyxargs.py -r \"(.+\.py)|(\.git)\" -o echo out {}"
        with os.popen(cmd) as result:
            result = result.readlines()
            self.assertEqual(result, ['out LICENSE\n', 'out README.md\n', 'out test.txt\n'])

    def test_stdin_delimiter(self):
        cmd = "echo hello,world,bye,world | python pyxargs.py -d , echo out {}"
        with os.popen(cmd) as result:
            result = result.readlines()
            self.assertEqual(result, ['out hello\n', 'out world\n', 'out bye\n', 'out world\n'])

    def test_stdin_delimiter_py(self):
        cmd = "echo hello,world,bye,world | python pyxargs.py -d , -x \"print('{}')\""
        with os.popen(cmd) as result:
            result = result.readlines()
            self.assertEqual(result, ['hello\n', 'world\n', 'bye\n', 'world\n'])

    def test_trailing_chars_removed(self):
        cmd = "echo hello,world,bye,world | python pyxargs.py -d , --dry-run -x \"print('{}')\""
        with os.popen(cmd) as result:
            result = result.readlines()
            self.assertEqual(result, ["print('hello')\n", "print('world')\n", "print('bye')\n", "print('world')\n"])

    def test_extra_delimiter(self):
        cmd = "echo hello,world,bye,world , | python pyxargs.py -d , -x \"print('{}')\""
        with os.popen(cmd) as result:
            result = result.readlines()
            self.assertEqual(result, ['hello\n', 'world\n', 'bye\n', 'world \n', '\n'])

    def test_delimiter_space(self):
        cmd = "echo hello world bye world | python pyxargs.py -d \" \" -x \"print('{}')\""
        with os.popen(cmd) as result:
            result = result.readlines()
            self.assertEqual(result, ['hello\n', 'world\n', 'bye\n', 'world\n'])

    def test_delimiter_whitespace(self):
        cmd = "echo hello world bye world | python pyxargs.py -m stdin -x \"print('{}')\""
        with os.popen(cmd) as result:
            result = result.readlines()
            self.assertEqual(result, ['hello\n', 'world\n', 'bye\n', 'world\n'])

    def test_pre_post_exec(self):
        cmd = "echo hello world bye world | python pyxargs.py -m stdin --pre \"counter = 0\" --post \"print(counter)\" -x \"print('{}'); counter += 1\""
        with os.popen(cmd) as result:
            result = result.readlines()
            self.assertEqual(result, ['hello\n', 'world\n', 'bye\n', 'world\n', '4\n'])

    def test_exec_namespace(self):
        cmd = "echo hello world bye world | python pyxargs.py -m stdin --pre \"output = 0\"  --post \"print(locals())\" -x \"print('{}'); output += 1\""
        with os.popen(cmd) as result:
            result = result.readlines()
            self.assertEqual(result, ['hello\n', 'world\n', 'bye\n', 'world\n', "{'output': 4}\n"])

    def test_import(self):
        cmd = "echo hello world bye world | python pyxargs.py -m stdin --import math --importstar math --pre \"output = 0\" --post \"print(output)\" -x \"print('{}'); output += math.sin(pi/2)\""
        with os.popen(cmd) as result:
            result = result.readlines()
            self.assertEqual(result, ['hello\n', 'world\n', 'bye\n', 'world\n', '4.0\n'])

    def test_dryrun(self):
        cmd = "echo hello world | python pyxargs.py -m stdin --dry-run echo out {}"
        with os.popen(cmd) as result:
            result = result.readlines()
            self.assertEqual(result, ["['echo', 'out', 'hello']\n", "['echo', 'out', 'world']\n"])

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

    def test_read_items_cat_type(self):
        if os.name == "nt":
            cmd = "type test.txt | python pyxargs.py -m stdin echo out {}"
        elif os.name == "posix":
            cmd = "cat test.txt | python pyxargs.py -m stdin echo out {}"
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

if __name__ == '__main__':
    unittest.main()
