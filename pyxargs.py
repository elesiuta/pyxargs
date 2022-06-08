#!/usr/bin/env python3

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

# https://github.com/elesiuta/pyxargs

import argparse
import os
import re
import shlex
import signal
import subprocess
import sys
import textwrap
import typing


__version__: typing.Final[str] = "2.0.0"


def replace_surrogates(string: str) -> str:
    return string.encode('utf16', 'surrogatepass').decode('utf16', 'replace')


def colour_print(string: str, colour: str) -> None:
    colours = {
        "R": "\033[91m",
        "G": "\033[92m",
        "Y": "\033[93m",
        "B": "\033[94m",
    }
    string = replace_surrogates(string)
    print(colours[colour] + string + "\033[0m")


def safe_print(string: str) -> None:
    print(replace_surrogates(string))


def build_commands(args: argparse.Namespace, stdin: str) -> list:
    command_dicts = []
    append_input = not (args.pyex or args.pyev or args.resub) and args.replace_str == "{}" and all("{}" not in arg for arg in args.command)
    # build commands using standard input mode or by walking the directory tree
    if args.input_mode == "stdin":
        # remove trailing whitespace and split stdin
        stdin = stdin.rstrip()
        arg_input_list = stdin.split(args.delim)
        # build commands from stdin
        for arg_input in arg_input_list:
            command = build_command(args, "", "", arg_input, append_input)
            if command:
                command_dicts.append({"dir": args.base_dir, "cmd": command})
    elif args.input_mode in ['file', 'path', 'abspath']:
        for dir_path, folder_list, file_list in os.walk(args.base_dir, topdown=True, followlinks=args.symlinks):
            folder_list.sort()
            if args.folders:
                # build commands from directory names
                for folder_name in sorted(folder_list):
                    command = build_command(args, dir_path, folder_name, "", append_input)
                    if command:
                        command_dicts.append({"dir": dir_path, "cmd": command})
            else:
                # build commands from filenames or file paths
                for file_name in sorted(file_list):
                    command = build_command(args, dir_path, file_name, "", append_input)
                    if command:
                        command_dicts.append({"dir": dir_path, "cmd": command})
            if args.top_level:
                break
    return command_dicts


def execute_commands(args: argparse.Namespace, command_dicts: list) -> int:
    user_namespace = {}
    # pre execution tasks
    for i in args.imprt:
        exec(f"import {i}", globals(), user_namespace)
    for i in args.imprtstar:
        exec(f"from {i} import *", globals(), user_namespace)
    if args.pre:
        exec(args.pre, globals(), user_namespace)
    # execute commands
    if args.interactive:
        for command_dict in command_dicts:
            if len(command_dict["cmd"]) == 1:
                colour_print(command_dict["cmd"][0], "G")
            else:
                colour_print(shlex.join(command_dict["cmd"]), "G")
            print("Run command (Yes/No/QUIT)?")
            run = input("> ")
            if run.lower().startswith("y"):
                execute_command(args, command_dict, user_namespace)
            elif run.lower().startswith("n"):
                pass
            else:
                return 4
    else:
        for command_dict in command_dicts:
            execute_command(args, command_dict, user_namespace)
    # post execution tasks
    if args.post:
        exec(args.post, globals(), user_namespace)
    return 0


def build_command(args: argparse.Namespace, dir_path: str, basename: str, arg_input: str, append_input: bool) -> list:
    # mode
    if args.input_mode == "file":
        arg_input = basename
    elif args.input_mode == "path":
        arg_input = os.path.join(dir_path, basename)
        arg_input = os.path.relpath(arg_input, args.base_dir)
    elif args.input_mode == "abspath":
        arg_input = os.path.join(dir_path, basename)
    # check re match
    if args.input_mode == "stdin":
        if (re.search(args.regex, arg_input) is not None) == args.regex_omit:
            return []
    elif args.regex_basename:
        if (re.search(args.regex, basename) is not None) == args.regex_omit:
            return []
    else:
        relpath = os.path.join(dir_path, basename)
        relpath = os.path.relpath(relpath, args.base_dir)
        if (re.search(args.regex, relpath) is not None) == args.regex_omit:
            return []
    # copy command
    command = [cmd for cmd in args.command]
    # re.sub input into command
    if args.resub is not None:
        for i in range(len(command)):
            command[i] = command[i].replace(args.resub[2], re.sub(args.resub[0], args.resub[1], arg_input))
    # sub input into command or append
    if append_input:
        command.append(arg_input)
    else:
        for i in range(len(command)):
            command[i] = command[i].replace(args.replace_str, arg_input)
    # check length of command
    if args.max_chars is not None:
        if len(shlex.join(command)) > args.max_chars:
            if args.verbose:
                colour_print(f"Command too long for: {arg_input}", "Y")
            return []
    # join command
    if args.pyex or args.pyev or args.subprocess_shell:
        if len(command) > 1:
            command = [shlex.join(command)]
    # and finally
    return command


def execute_command(args: argparse.Namespace, command_dict: dict, user_namespace: dict) -> None:
    dir_path = command_dict["dir"]
    cmd = command_dict["cmd"]
    if args.input_mode == "file":
        os.chdir(dir_path)
    if args.dry_run:
        if len(cmd) == 1:
            safe_print(cmd[0])
        else:
            safe_print(shlex.join(cmd))
    else:
        if args.verbose:
            if len(cmd) == 1:
                colour_print(cmd[0], "B")
            else:
                colour_print(shlex.join(cmd), "B")
        if args.pyex:
            try:
                exec(cmd[0], globals(), user_namespace)
            except Exception as e:
                print(str(e), file=sys.stderr)
        elif args.pyev:
            try:
                result = eval(cmd[0], globals(), user_namespace)
                print(result)
            except Exception as e:
                print(str(e), file=sys.stderr)
        elif args.subprocess_shell:
            subprocess.run(cmd[0], shell=True)
        else:
            subprocess.run(cmd, shell=False)


def main() -> int:
    signal.signal(signal.SIGINT, lambda *args: sys.exit(128 + signal.SIGINT))
    signal.signal(signal.SIGTERM, lambda *args: sys.exit(128 + signal.SIGTERM))
    class ArgparseCustomFormatter(argparse.HelpFormatter):
        def _split_lines(self, text, width):
            if text[:2] == 'F!':
                return text.splitlines()[1:]
            return argparse.HelpFormatter._split_lines(self, text, width)
    readme = ("Build and execute command lines or python code from standard input or file paths, "
              "a partial and opinionated implementation of xargs in python with some added features. "
              "The file input mode (default if stdin is empty) builds commands using filenames only and executes them in their respective directories, "
              "this is useful when dealing with file paths containing multiple character encodings.")
    examples = textwrap.dedent(r"""
    by default, pyxargs will use filenames and run commands in each directory
        pyxargs echo
    instead of appending inputs, you can specify a location with {}
        pyxargs echo spam {} spam
    and like xargs, you can also specify the replace-str with -I
        pyxargs -I eggs echo spam eggs spam literal {}
    if stdin is not empty, it will be used instead of filenames by default
        echo bacon eggs | pyxargs echo spam
    python code can be used in place of a command
        pyxargs --py "print(f'input file: {{}} executed in: {os.getcwd()}')"
    python code can also run before or after all the commands
        pyxargs --pre "n=0" --post "print(n,'files')" --py "n+=1"
    regular expressions can be used to filter and modify inputs
        pyxargs -r \.py --resub \.py .txt {} echo {}
    the original inputs can easily be used with the substituted versions
        pyxargs -r \.py --resub \.py .txt new echo {} new

    comparing usage with find & xargs (these commands produce the same output)
        find ./ -name "*" -type f -print0 | xargs -0 -I {} echo {}
        find ./ -name "*" -type f -print0 | pyxargs -0 -I {} echo {}
    pyxargs does not require '-I' to specify a replace-str (default: {})
        find ./ -name "*" -type f -print0 | pyxargs -0 echo {}
    and in the absence of a replace-str, exactly one input is appended
        find ./ -name "*" -type f -print0 | pyxargs -0 echo
        find ./ -name "*" -type f -print0 | xargs -0 --max-args=1 echo
        find ./ -name "*" -type f -print0 | xargs -0 --max-lines=1 echo
    pyxargs can use file paths as input without piping from another program
        pyxargs -m path echo ./{}
    and now for something completely different, python code for the command
        pyxargs -m path --py "print('./{}')"
    """)
    parser = argparse.ArgumentParser(description=readme,
                                     formatter_class=lambda prog: ArgparseCustomFormatter(prog, max_help_position=24),
                                     usage="%(prog)s [options] command [initial-arguments ...]\n"
                                           "       %(prog)s -h | --help | --examples | --version")
    group0 = parser.add_mutually_exclusive_group()
    group1 = parser.add_mutually_exclusive_group()
    parser.add_argument("command", action="store", type=str, nargs=argparse.REMAINDER,
                        help=argparse.SUPPRESS)
    parser.add_argument("--examples", action="store_true", dest="examples",
                        help="print example usage")
    parser.add_argument("--version", action="version", version=__version__)
    parser.add_argument("--base-directory", type=str, default=os.getcwd(), metavar="base-directory", dest="base_dir",
                        help=argparse.SUPPRESS)
    parser.add_argument("-m", type=str, default=None, metavar="input-mode", choices=['file', 'path', 'abspath', 'stdin'], dest="input_mode",
                        help="F!\n"
                             "options are:\n"
                             "file    = build commands from filenames and execute in\n"
                             "          each subdirectory respectively\n"
                             "path    = build commands from file paths relative to\n"
                             "          the current directory and execute in the\n"
                             "          current directory\n"
                             "abspath = build commands from absolute file paths and \n"
                             "          execute in the current directory\n"
                             "stdin   = build commands from standard input and\n"
                             "          execute in the current directory\n"
                             "default: stdin unless empty, then file")
    parser.add_argument("--folders", action="store_true", dest="folders",
                        help="use folders instead files (for input modes: file, path, abspath)")
    parser.add_argument("-t", "--top", action="store_true", dest="top_level",
                        help="do not recurse into subdirectories (for input modes: file, path, abspath)")
    parser.add_argument("--sym", "--symlinks", action="store_true", dest="symlinks",
                        help="follow symlinks when scanning directories (for input modes: file, path, abspath)")
    group0.add_argument("-0", "--null", action="store_true", dest="null",
                        help="input items are separated by a null character instead of whitespace (for input mode: stdin)")
    group0.add_argument("-d", "--delimiter", type=str, default=None, metavar="delim", dest="delim",
                        help="input items are separated by the specified delimiter instead of whitespace (for input mode: stdin)")
    parser.add_argument("--max-chars", type=int, metavar="n", dest="max_chars",
                        help="omits any command line exceeding n characters, no limit by default")
    parser.add_argument("-I", action="store", type=str, default="{}", metavar="replace-str", dest="replace_str",
                        help="replace occurrences of replace-str in command with input, default: {}")
    parser.add_argument("--resub", nargs=3, type=str, metavar=("pattern", "substitution", "replace-str"), dest="resub",
                        help="replace occurrences of replace-str in command with re.sub(patten, substitution, input)")
    parser.add_argument("-r", type=str, default=".", metavar="regex", dest="regex",
                        help="only build commands from inputs matching regex for input mode stdin, and matching relative paths for all other input modes, uses re.search")
    parser.add_argument("-o", action="store_true", dest="regex_omit",
                        help="omit inputs matching regex instead")
    parser.add_argument("-b", action="store_true", dest="regex_basename",
                        help="only match regex against basename of input (for input modes: file, path, abspath)")
    group1.add_argument("-s", "--shell", action="store_true", dest="subprocess_shell",
                        help="executes commands through the shell (subprocess shell=True) (no effect on Windows)")
    group1.add_argument("--py", "--pyex", action="store_true", dest="pyex",
                        help="executes commands as python code using exec()")
    group1.add_argument("--pyev", action="store_true", dest="pyev",
                        help="evaluates commands as python expressions using eval()")
    parser.add_argument("--import", action="append", type=str, default=[], metavar=("library"), dest="imprt",
                        help="executes 'import <library>' for each library")
    parser.add_argument("--im", "--importstar", action="append", type=str, default=[], metavar=("library"), dest="imprtstar",
                        help="executes 'from <library> import *' for each library")
    parser.add_argument("--pre", type=str, default="", metavar=("\"code\""), dest="pre",
                        help="runs exec(code) before execution")
    parser.add_argument("--post", type=str, default="", metavar=("\"code\""), dest="post",
                        help="runs exec(code) after execution")
    parser.add_argument("-i", "--interactive", action="store_true", dest="interactive",
                        help="prompt the user before executing each command, only proceeds if response starts with 'y' or 'Y'")
    parser.add_argument("-n", "--dry-run", action="store_true", dest="dry_run",
                        help="prints commands without executing them")
    parser.add_argument("-v", "--verbose", action="store_true", dest="verbose",
                        help="prints commands before executing them")
    args = parser.parse_args()
    if args.examples:
        print(examples)
        return 0
    # determine input mode and read stdin available or required
    stdin = ""
    if args.input_mode is None:
        if not sys.stdin.isatty():
            stdin = sys.stdin.read()
        if stdin:
            args.input_mode = "stdin"
        else:
            args.input_mode = "file"
    elif args.input_mode == "stdin":
        stdin = sys.stdin.read()
    # set delimiter
    if args.null:
        args.delim = "\0"
    # enable shell on windows
    if sys.platform.startswith("win32"):
        args.subprocess_shell = True
    # check for invalid arguments
    assert os.path.isdir(args.base_dir) and os.getcwd() == args.base_dir
    if args.input_mode == "stdin":
        assert not args.folders, "invalid option for input mode: stdin"
        assert not args.top_level, "invalid option for input mode: stdin"
        assert not args.symlinks, "invalid option for input mode: stdin"
        assert not args.regex_basename, "invalid option for input mode: stdin"
    else:
        assert not args.null, f"invalid option for input mode: {args.input_mode}"
        assert not args.delim, f"invalid option for input mode: {args.input_mode}"
    # build and run commands
    if len(args.command) >= 1:
        command_dicts = build_commands(args, stdin)
        return execute_commands(args, command_dicts)
    else:
        parser.print_usage()
        return 2


if __name__ == "__main__":
    sys.exit(main())

