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
import multiprocessing
import os
import pickle
import pty
import re
import shlex
import shutil
import signal
import subprocess
import sys
import tempfile
import textwrap
import time
import typing


__version__: typing.Final[str] = "2.4.1"


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
    append_input = not (args.pyex or args.pyev or args.resub or args.format_str) and args.replace_str is None and all("{}" not in arg for arg in args.command)
    args.replace_str = "{}" if args.replace_str is None else args.replace_str
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
    elif args.no_mux:
        with multiprocessing.Pool(args.procs) as pool:
            pool.starmap(execute_command, [(args, command_dict, user_namespace) for command_dict in command_dicts])
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
    # copy command first since some options mutate it
    command = args.command.copy()
    # re.sub input into command
    if args.resub is not None:
        command = [cmd.replace(args.resub[2], re.sub(args.resub[0], args.resub[1], arg_input)) for cmd in command]
    # build command with input via format, append, or replace-str
    if args.format_str:
        arg_input_list = [arg_input]
        if args.re_split is not None:
            arg_input_list = re.split(args.re_split, arg_input)
        command = [cmd.format(*arg_input_list) for cmd in command]
    elif append_input:
        command.append(arg_input)
    else:
        command = [cmd.replace(args.replace_str, arg_input) for cmd in command]
    # check length of command
    if args.max_chars is not None:
        if len(shlex.join(command)) > args.max_chars:
            if args.verbose:
                colour_print(f"Command too long for: {arg_input}", "Y")
            return []
    # join command if required
    if args.pyex or args.pyev or args.subprocess_shell:
        if len(command) > 1:
            command = [shlex.join(command)]
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
              "The file input mode (default if stdin is not connected) builds commands using filenames only and executes them in their respective directories, "
              "this is useful when dealing with file paths containing multiple character encodings.")
    examples = textwrap.dedent(r"""
    # by default, pyxargs will use filenames and run commands in each directory
      > pyxargs echo

    # instead of appending inputs, you can specify a location with {}
      > pyxargs echo spam {} spam

    # and like xargs, you can also specify the replace-str with -I
      > pyxargs -I eggs echo spam eggs spam literal {}

    # if stdin is connected, it will be used instead of filenames by default
      > echo bacon eggs | pyxargs echo spam

    # python code can be used in place of a command
      > pyxargs --py "print(f'input file: {} executed in: {os.getcwd()}')"

    # python code can also run before or after all the commands
      > pyxargs --pre "n=0" --post "print(n,'files')" --py "n+=1"

    # regular expressions can be used to filter and modify inputs
      > pyxargs -r \.py --resub \.py .txt {new} echo {} -\> {new}

    # you can test your command first with --dry-run (-n) or --interactive (-i)
      > pyxargs -i echo filename: {}

    # pyxargs can also run interactively in parallel by using byobu or tmux
      > pyxargs -P 4 -i echo filename: {}

    # you can use pyxargs to create a JSON mapping of /etc/hosts
      > cat /etc/hosts | pyxargs -d \n --im json --pre "d={}" \
        --post "print(dumps(d))" --py "d['{}'.split()[0]] = '{}'.split()[1]"

    # you can also do this with format strings and --split (-s) (uses regex)
      > cat /etc/hosts | pyxargs -d \n -s "\s+" --im json --pre "d={}" \
        --post "print(dumps(d))" --py "d['{0}'] = '{1}'"

    # this and the following examples will compare usage with find & xargs
      > find ./ -name "*" -type f -print0 | xargs -0 -I {} echo {}
      > find ./ -name "*" -type f -print0 | pyxargs -0 -I {} echo {}

    # pyxargs does not require '-I' to specify a replace-str (default: {})
      > find ./ -name "*" -type f -print0 | pyxargs -0 echo {}

    # and in the absence of a replace-str, exactly one input is appended
      > find ./ -name "*" -type f -print0 | pyxargs -0 echo
      > find ./ -name "*" -type f -print0 | xargs -0 --max-args=1 echo
      > find ./ -name "*" -type f -print0 | xargs -0 --max-lines=1 echo

    # pyxargs can use file paths as input without piping from another program
      > pyxargs -m path echo ./{}

    # and now for something completely different, python code for the command
      > pyxargs -m path --py "print('./{}')"
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
                        help="show example usage and exit")
    parser.add_argument("--version", action="version", version=__version__)
    parser.add_argument("--base-directory", type=str, default=os.getcwd(), metavar="base-directory", dest="base_dir",
                        help=argparse.SUPPRESS)
    parser.add_argument("-m", type=str, default=None, metavar="input-mode", choices=['file', 'path', 'abspath', 'stdin', "f", "p", "a", "s"], dest="input_mode",
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
                             "default: stdin if connected, otherwise file")
    parser.add_argument("--folders", action="store_true", dest="folders",
                        help="use folders instead files (for input modes: file, path, abspath)")
    parser.add_argument("-t", "--top", action="store_true", dest="top_level",
                        help="do not recurse into subdirectories (for input modes: file, path, abspath)")
    parser.add_argument("--sym", "--symlinks", action="store_true", dest="symlinks",
                        help="follow symlinks when scanning directories (for input modes: file, path, abspath)")
    parser.add_argument("-a", "--arg-file", type=str, default=None, metavar="file", dest="arg_file",
                        help="read input items from file instead of standard input (for input mode: stdin)")
    group0.add_argument("-0", "--null", action="store_true", dest="null",
                        help="input items are separated by a null character instead of whitespace (for input mode: stdin)")
    group0.add_argument("-d", "--delimiter", type=str, default=None, metavar="delim", dest="delim",
                        help="input items are separated by the specified delimiter instead of whitespace (for input mode: stdin)")
    parser.add_argument("-s", "--split", type=str, default=None, metavar="regex", dest="re_split",
                        help="split each input item with re.split(regex, input) before building command (after separating by delimiter), use {0}, {1}, ... to specify placement (implies --format)")
    parser.add_argument("-f", "--format", action="store_true", dest="format_str",
                        help="format command with input using str.format() instead of appending or replacing via -I replace-str")
    parser.add_argument("-I", action="store", type=str, default=None, metavar="replace-str", dest="replace_str",
                        help="replace occurrences of replace-str in command with input, default: {}")
    parser.add_argument("--resub", nargs=3, type=str, metavar=("pattern", "substitution", "replace-str"), dest="resub",
                        help="replace occurrences of replace-str in command with re.sub(patten, substitution, input)")
    parser.add_argument("-r", type=str, default=".", metavar="regex", dest="regex",
                        help="only build commands from inputs matching regex for input mode stdin, and matching relative paths for all other input modes, uses re.search")
    parser.add_argument("-o", action="store_true", dest="regex_omit",
                        help="omit inputs matching regex instead")
    parser.add_argument("-b", action="store_true", dest="regex_basename",
                        help="only match regex against basename of input (for input modes: file, path, abspath)")
    parser.add_argument("--max-chars", type=int, metavar="n", dest="max_chars",
                        help="omits any command line exceeding n characters, no limit by default")
    group1.add_argument("--sh", "--shell", action="store_true", dest="subprocess_shell",
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
    parser.add_argument("-P", "--procs", type=int, default=None, metavar="P", dest="procs",
                        help="split into P chunks and execute each chunk in parallel as a separate process and window with byobu or tmux")
    parser.add_argument("-c", "--chunk", type=int, default=None, metavar="c", dest="chunk",
                        help="runs chunk c of P (0 <= c < P) (without multiplexer)")
    parser.add_argument("--_command_pickle", nargs=2, default=None, dest="command_pickle",
                        help=argparse.SUPPRESS)
    parser.add_argument("--no-mux", action="store_true", dest="no_mux",
                        help="do not use a multiplexer for multiple processes")
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
    if args.input_mode in ["f", "p", "a", "s"]:
        short_forms = {"f": "file", "p": "path", "a": "abspath", "s": "stdin"}
        args.input_mode = short_forms[args.input_mode]
    if args.command_pickle is not None:
        args.input_mode = args.command_pickle[0]
    elif args.arg_file is not None and (args.input_mode is None or args.input_mode == "stdin"):
        with open(args.arg_file, "r") as f:
            stdin = f.read()
        args.input_mode = "stdin"
    elif args.input_mode is None:
        if not sys.stdin.isatty():
            stdin = sys.stdin.read()
            args.input_mode = "stdin"
        else:
            args.input_mode = "file"
    elif args.input_mode == "stdin":
        stdin = sys.stdin.read()
    # need to open new tty for interactive mode if input was piped to stdin (handled later if using mux)
    if args.interactive and not sys.stdin.isatty() and args.procs is None:
        sys.stdin = open("/dev/tty")
    # set delimiter
    if args.null:
        args.delim = "\0"
    # enable format string mode
    if args.re_split is not None:
        args.format_str = True
    # enable shell on windows
    if sys.platform.startswith("win32"):
        args.subprocess_shell = True
    # check for invalid arguments
    assert os.path.isdir(args.base_dir) and os.getcwd() == args.base_dir
    if args.input_mode == "stdin":
        assert not args.folders, "invalid option --folders for input mode: stdin"
        assert not args.top_level, "invalid option --top for input mode: stdin"
        assert not args.symlinks, "invalid option --symlinks for input mode: stdin"
        assert not args.regex_basename, "invalid option -b for input mode: stdin"
    else:
        assert not args.null, f"invalid option --null for input mode: {args.input_mode}"
        assert args.delim is None, f"invalid option --delimiter for input mode: {args.input_mode}"
        assert args.arg_file is None, f"invalid option --arg-file for input mode: {args.input_mode}"
    assert not args.format_str or args.replace_str is None, "invalid option --format-str: cannot specify -I replace-str"
    assert args.procs is None or args.procs > 0, "invalid option --procs: requires P > 0"
    assert args.chunk is None or args.procs is not None, "invalid option --chunk: --procs must be specified"
    assert args.chunk is None or 0 <= args.chunk < args.procs, "invalid option --chunk: requires 0 <= c < P"
    assert args.command_pickle is None or args.chunk is not None, "invalid option --_command_pickle: --chunk must be specified"
    assert not args.no_mux or args.procs is not None, "invalid option --no-mux: --procs must be specified"
    assert not args.no_mux or args.chunk is None, "invalid option --no-mux: --chunk must not be specified"
    assert not args.no_mux or not args.interactive, "invalid option --no-mux: interactive mode not supported"
    # build and run commands
    if len(args.command) >= 1:
        # build commands or load them from pickle if available
        if args.command_pickle is None:
            command_dicts = build_commands(args, stdin)
        else:
            with open(args.command_pickle[1], "rb") as f:
                command_dicts = pickle.load(f)
        # run subprocesses with multiplexer if requested
        if args.procs is not None and args.chunk is None and not args.no_mux:
            multiplexer = "byobu" if shutil.which("byobu") else "tmux" if shutil.which("tmux") else None
            assert multiplexer is not None, "multiplexer not found: install byobu or tmux"
            session = time.strftime("pyxargs_%Y%m%d_%H%M%S")
            command_pickle = tempfile.NamedTemporaryFile()
            pickle.dump(command_dicts, command_pickle.file)
            command_pickle.file.flush()
            pyxargs_command = [sys.executable, os.path.abspath(__file__), "--chunk", "0", "--_command_pickle", args.input_mode, command_pickle.name] + sys.argv[1:]
            subprocess.run([multiplexer, "new-session", "-d", "-s", session, shlex.join(pyxargs_command)])
            for i in range(1, args.procs):
                pyxargs_command[3] = str(i)
                subprocess.run([multiplexer, "new-window", "-t", f"{session}:{i}", shlex.join(pyxargs_command)])
            if not sys.stdin.isatty():
                sys.stdin = sys.__stdin__ = open("/dev/tty")
                os.dup2(sys.stdin.fileno(), 0)
                pty.spawn([multiplexer, "attach-session", "-t", session])
            else:
                subprocess.run([multiplexer, "attach-session", "-t", session])
            return 0
        # execute commands (in chunks if requested)
        if args.chunk is None:
            return execute_commands(args, command_dicts)
        else:
            _ = execute_commands(args, command_dicts[args.chunk::args.procs])
            _ = input(f"Chunk {args.chunk} complete. Press enter to exit. ")
            return 0
    else:
        parser.print_usage()
        return 2


if __name__ == "__main__":
    sys.exit(main())

