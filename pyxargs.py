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


import os
import re
import csv
import sys
import shlex
import shutil
import typing
import argparse
import datetime
import textwrap
import subprocess
import multiprocessing


VERSION = "1.3.0"
user_namespace = {}


class ArgparseCustomFormatter(argparse.HelpFormatter):
    def _split_lines(self, text, width):
        if text[:2] == 'F!':
            return text.splitlines()[1:]
        return argparse.HelpFormatter._split_lines(self, text, width)


class StatusBar:
    def __init__(self, title: str, total: int, display: bool) -> "StatusBar":
        self.total = total
        self.display = display
        terminal_width = shutil.get_terminal_size()[0]
        if terminal_width < 16 or total <= 0:
            self.display = False
        if self.display:
            self.bar_len = min(100, terminal_width - (7 + len(title)))
            self.progress = 0
            self.bar_progress = 0
            sys.stdout.write(title + ": [" + "-"*self.bar_len + "]\b" + "\b"*self.bar_len)
            sys.stdout.flush()

    def initTotal(self, total: int) -> None:
        if total <= 0:
            self.endProgress()
        elif self.progress == 0:
            self.total = total

    def update(self) -> None:
        if self.display:
            self.progress += 1
            bar_progression = int(self.bar_len * self.progress // self.total) - self.bar_progress
            if bar_progression != 0:
                self.bar_progress += bar_progression
                sys.stdout.write("#" * bar_progression)
                sys.stdout.flush()

    def endProgress(self) -> None:
        if self.display:
            sys.stdout.write("#" * (self.bar_len - self.bar_progress) + "]\n")
            sys.stdout.flush()
            self.display = False


def replaceSurrogates(string: str) -> str:
    return string.encode('utf16', 'surrogatepass').decode('utf16', 'replace')


def colourPrint(string: str, colour: str) -> None:
    colours = {
        "R": "\033[91m",
        "B": "\033[94m",
        "G": "\033[92m",
        "Y": "\033[93m",
    }
    string = replaceSurrogates(string)
    print(colours[colour] + string + "\033[0m")


def safePrint(string: str) -> None:
    print(replaceSurrogates(string))


def writeCsv(args: argparse.Namespace, file_dir: str, data: str) -> None:
    if args.csv:
        file_name = "pyxargs-" + datetime.datetime.now().strftime("%y%m%d-%H%M%S") + ".csv"
        file_path = os.path.join(file_dir, file_name)
        with open(file_path, "w", newline="", encoding="utf-8", errors="backslashreplace") as f:
            writer = csv.writer(f, delimiter=",")
            for row in data:
                writer.writerow(row)


def processInput(args: argparse.Namespace, stdin: typing.Union[str, None]) -> list:
    command_dicts = []
    append_input = not (args.py or args.pyev or args.command_strings) and args.replace_str == "{}" and all("{}" not in arg for arg in args.command)
    # build commands using standard input mode or by walking the directory tree
    if args.input_mode == "stdin":
        # set seperator
        seperator = None
        if args.null:
            seperator = "\0"
        elif args.delim is not None:
            seperator = args.delim
        # read input from stdin or file
        if args.arg_file is None:
            # stdin
            if args.eof_str is not None:
                stdin = stdin.split(args.eof_str, 1)[0]
            elif args.delim is not None:
                stdin = stdin.rstrip()
            arg_input_list = stdin.split(seperator)
        elif os.path.isfile(args.arg_file):
            # file
            with open(args.arg_file, "r") as f:
                if args.eof_str is not None:
                    arg_input_list = f.read().split(args.eof_str, 1)[0].splitlines()
                elif seperator is None:
                    arg_input_list = f.read().splitlines()
                else:
                    arg_input_list = f.read().split(seperator)
        else:
            # error
            colourPrint("Invalid file: %s" % (args.arg_file), "R")
            sys.exit(0)
        # build commands from input
        process_status = StatusBar("Building commands", len(arg_input_list), args.verbose)
        for arg_input in arg_input_list:
            process_status.update()
            commands = buildCommand(None, None, arg_input, append_input, args)
            if commands is not None:
                command_dicts.append({"args": args, "dir": args.base_dir, "cmd": commands})
    elif args.input_mode in ['file', 'path', 'abspath', 'dir']:
        process_status = StatusBar("Building commands", 1, args.verbose)
        if args.verbose == True:
            if args.input_mode == "dir":
                process_status.initTotal(sum(len(d) for r, d, f in os.walk(args.base_dir, topdown=False, followlinks=args.symlinks)))
            else:
                process_status.initTotal(sum(len(f) for r, d, f in os.walk(args.base_dir, topdown=False, followlinks=args.symlinks)))
        # silly walk
        for dir_path, subdir_list, file_list in os.walk(args.base_dir, topdown=True, followlinks=args.symlinks):
            subdir_list.sort()
            if args.input_mode == "dir":
                # build commands from directory names
                process_status.update()
                commands = buildCommand(dir_path, None, None, append_input, args)
                if commands is not None:
                    command_dicts.append({"args": args, "dir": dir_path, "cmd": commands})
            elif args.input_mode in ["file", "path", "abspath"]:
                # build commands from filenames or file paths
                for f in sorted(file_list):
                    process_status.update()
                    commands = buildCommand(dir_path, f, None, append_input, args)
                    if commands is not None:
                        command_dicts.append({"args": args, "dir": dir_path, "cmd": commands})
    process_status.endProgress()
    return command_dicts


def processCommands(start_dir: str, command_dicts: list, args: argparse.Namespace) -> list:
    output = []
    if args.py or args.pyev:
        cmd_join = lambda cmds: [cmd[0] for cmd in cmds]
    else:
        cmd_join = lambda cmds: [shlex.join(cmd) for cmd in cmds]
    # pre execution tasks
    for i in args.imprt:
        exec("import " + i, globals(), user_namespace)
    for i in args.imprtstar:
        exec("from " + i + " import *", globals(), user_namespace)
    for line in args.pre:
        exec(line, globals(), user_namespace)
    # execute commands
    if args.max_procs == 1:
        if args.interactive:
            for command_dict in command_dicts:
                command_list = cmd_join(command_dict["cmd"])
                for cmd in command_list: colourPrint(cmd, "G")
                colourPrint("Run command(s) (Yes/No/QUIT)?", "Y")
                run = input("> ")
                if len(run) >= 1 and run[0].lower() == "y":
                    output.append(["COMMAND(S):"] + command_list + ["OUTPUT(S):"] + executeCommand(command_dict))
                elif len(run) >= 1 and run[0].lower() == "n":
                    output.append(["COMMAND(S):"] + command_list + ["OUTPUT(S):"] + ["SKIPPED"])
                else:
                    writeCsv(args, start_dir, output)
                    sys.exit(0)
        else:
            for command_dict in command_dicts:
                command_list = cmd_join(command_dict["cmd"])
                output.append(["COMMAND(S):"] + command_list + ["OUTPUT(S):"] + executeCommand(command_dict))
    elif args.max_procs > 1:
        with multiprocessing.Pool(args.max_procs) as pool:
            async_result = pool.map_async(executeCommand, command_dicts)
            results = async_result.get()
        for i in range(len(command_dicts)):
            command_list = cmd_join(command_dicts[i]["cmd"])
            output.append(["COMMAND(S):"] + command_list + ["OUTPUT(S):"] + results[i])
    # post execution tasks
    for line in args.post:
        exec(line, globals(), user_namespace)
    return output


def buildCommand(dir_name: typing.Union[str, None], file_name: typing.Union[str, None], arg_input: typing.Union[str, None], append_input: bool, args: argparse.Namespace) -> list:
    # mode
    if arg_input is None:
        if args.input_mode == "file":
            arg_input = file_name
        elif args.input_mode == "dir":
            arg_input = dir_name
        elif args.input_mode == "path":
            arg_input = os.path.join(dir_name, file_name)
            arg_input = os.path.relpath(arg_input, args.base_dir)
        elif args.input_mode == "abspath":
            arg_input = os.path.join(dir_name, file_name)
    # check re match
    if not args.regex_fname and dir_name is not None and file_name is not None:
        relpath = os.path.join(dir_name, file_name)
        relpath = os.path.relpath(relpath, args.base_dir)
        if (re.search(args.regex, relpath) is not None) == args.regex_omit:
            return None
    elif args.regex_fname and file_name is not None:
        if (re.search(args.regex, file_name) is not None) == args.regex_omit:
            return None
    else:
        if (re.search(args.regex, arg_input) is not None) == args.regex_omit:
            return None
    # interpret command(s)
    if args.py or args.pyev:
        if args.command_strings:
            commands = [[cmd] for cmd in args.command]
        else:
            commands = [[" ".join(args.command)]]
    elif args.command_strings:
        commands = [shlex.split(cmd) for cmd in args.command]
    else:
        commands = [args.command[:]]
    # re.sub input into command
    if args.resub is not None:
        for i in range(len(commands)):
            for j in range(len(commands[i])):
                commands[i][j] = commands[i][j].replace(args.resub[2], re.sub(args.resub[0], args.resub[1], arg_input))
    # sub input into command or append
    if append_input:
        commands[0].append(arg_input)
    else:
        for i in range(len(commands)):
            for j in range(len(commands[i])):
                commands[i][j] = commands[i][j].replace(args.replace_str, arg_input)
    # check length of command(s)
    if args.max_chars is not None:
        for cmd in commands:
            if len(shlex.join(cmd)) > args.max_chars:
                return None
    # and finally
    return commands


def executeCommand(command_dict: dict) -> list:
    args = command_dict["args"]
    dir_name = command_dict["dir"]
    cmds = command_dict["cmd"]
    # mode
    if args.input_mode in ["file", "stdin"]:
        os.chdir(dir_name)
    # no run
    if args.dry_run:
        if len(cmds) > 1:
            if args.py or args.pyev:
                safePrint(str([cmd[0] for cmd in cmds]))
            else:
                safePrint(str([shlex.join(cmd) for cmd in cmds]))
        else:
            if args.py or args.pyev:
                safePrint(cmds[0][0])
            else:
                safePrint(shlex.join(cmds[0]))
        return ["DRY-RUN"]
    else:
        # execute command(s) and return output for csv
        output = []
        if len(cmds) > 1:
            if args.verbose:
                colourPrint(str(cmds), "B")
        for cmd in cmds:
            if args.verbose:
                colourPrint(cmd[0], "G")
            if args.py:
                try:
                    exec(cmd[0], globals(), user_namespace)
                    output.append("EXEC SUCCESS")
                except Exception as e:
                    output.append("EXEC ERROR: " + str(e))
            elif args.pyev:
                try:
                    output.append(eval(cmd[0], globals(), user_namespace))
                except Exception as e:
                    output.append("EVAL ERROR: " + str(e))
            elif args.csv:
                with os.popen(shlex.join(cmd)) as result:
                    result = result.read()
                    sys.stdout.write(result)
                    output.append(result)
            else:
                subprocess.run(cmd)
                output.append("subprocess.run")
        return output


def main() -> None:
    readme = ("Build and execute command lines or python code from standard input or file paths, "
              "a mostly complete implementation of xargs in python with some added features. "
              "The file input mode (default if stdin is empty) builds commands using filenames only and executes them in their respective directories, "
              "this is useful when dealing with file paths containing multiple character encodings.")
    examples = textwrap.dedent(r"""
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
    you can also use python code as your command
        pyxargs -m path --py "print('./{}')"

    use -- to separate options with multiple optional arguments from the command
        pyxargs --pre "print('spam')" "print('spam')" -- echo {}
    or separate with another option (they are parsed with argparse)
        pyxargs --pre "print('this is fine too')" -P 1 echo {}
    the command takes all remaining arguments, so this will not work
        pyxargs echo {} --pre "print('this statement will be echoed')"
    however pipes and redirects still work
        pyxargs echo {} > spam.txt

    multiple commands can be used by providing them as strings with '-s' set
        echo Larch | pyxargs -s "echo No 1. The {}" "echo And now... No 2. The {}"
    note: the same input is used for replace-str in both commands
    however the input will not be appended in the absence of a replace-str

    regular expressions can be used to filter and modify inputs
        pyxargs -r \.py --resub \.py .txt {} echo {}
    the original inputs can easily be used with the subsituted versions
        pyxargs -r \.py --resub \.py .txt new echo {} new

    and now for something completely different, python code
        pyxargs --pre "n=0" --post "print(n,'files')" --py n+=1
    a best effort is made to avoid side effects by executing in its own namespace
    """)
    parser = argparse.ArgumentParser(description=readme,
                                     formatter_class=lambda prog: ArgparseCustomFormatter(prog, max_help_position=24),
                                     usage="%(prog)s [options] command [initial-arguments ...]\n"
                                           "       %(prog)s [options] -s \"command [initial-arguments ...]\" ...\n"
                                           "       %(prog)s -h | --help | --examples | --version")
    parser.add_argument("command", action="store", type=str, nargs=argparse.REMAINDER,
                        help=argparse.SUPPRESS)
    parser.add_argument("--examples", action="store_true", dest="examples",
                        help="print example usage")
    parser.add_argument("-s", action="store_true", dest="command_strings",
                        help="support for multiple commands to be run sequentially by encapsulating in quotes (each its own string)")
    parser.add_argument("-b", type=str, default=os.getcwd(), metavar="base-directory", dest="base_dir",
                        help="default: os.getcwd()")
    parser.add_argument("-m", type=str, default=None, metavar="input-mode", choices=['file', 'path', 'abspath', 'dir', 'stdin'], dest="input_mode",
                        help="F!\n"
                             "options are:\n"
                             "file    = build commands from filenames and execute in\n"
                             "          each subdirectory respectively\n"
                             "path    = build commands from file paths relative to\n"
                             "          the base directory and execute in the base\n"
                             "          directory\n"
                             "abspath = build commands from file paths relative to\n"
                             "          root and execute in the base directory\n"
                             "dir     = build commands from directory names instead\n"
                             "          of filenames\n"
                             "stdin   = build commands from standard input and\n"
                             "          execute in the base directory\n"
                             "default: stdin unless empty, then file")
    parser.add_argument("--symlinks", action="store_true", dest="symlinks",
                        help="follow symlinks when scanning directories")
    parser.add_argument("-0", "--null", action="store_true", dest="null",
                        help="input items are terminated by a null character instead of by whitespace, sets input-mode=stdin")
    parser.add_argument("-d", type=str, metavar="delim", dest="delim",
                        help="input items are terminated by the specified delimiter instead of whitespace and trailing whitespace is removed, sets input-mode=stdin")
    parser.add_argument("-a", type=str, metavar="arg-file", dest="arg_file",
                        help="read input items from arg-file instead of standard input to build commands, sets input-mode=stdin")
    parser.add_argument("-E", type=str, metavar="eof-str", dest="eof_str",
                        help="ignores any input after eof-str, sets input-mode=stdin")
    parser.add_argument("-c", type=int, metavar="max-chars", dest="max_chars",
                        help="omits any command line exceeding max-chars, no limit by default")
    parser.add_argument("-I", action="store", type=str, default="{}", metavar="replace-str", dest="replace_str",
                        help="replace occurrences of replace-str in the command(s) with input, default: {}")
    parser.add_argument("--resub", nargs=3, type=str, metavar=("pattern", "repl", "replace-str"), dest="resub",
                        help="replace occurrences of replace-str in the command(s) with re.sub(patten, repl, input)")
    parser.add_argument("-r", type=str, default=".", metavar="regex", dest="regex",
                        help="only build commands from inputs matching regex")
    parser.add_argument("-o", action="store_true", dest="regex_omit",
                        help="omit inputs matching regex instead")
    parser.add_argument("-f", action="store_true", dest="regex_fname",
                        help="only match regex against filenames, ignoring full paths (if available)")
    parser.add_argument("--py", action="store_true", dest="py",
                        help="executes command(s) as python code using exec()")
    parser.add_argument("--pyev", action="store_true", dest="pyev",
                        help="evaluates command(s) as python expression(s) using eval()")
    parser.add_argument("--import", nargs="+", type=str, default=[], metavar=("library"), dest="imprt",
                        help="executes 'import <library>' for each library")
    parser.add_argument("--importstar", nargs="+", type=str, default=[], metavar=("library"), dest="imprtstar",
                        help="executes 'from <library> import *' for each library")
    parser.add_argument("--pre", nargs="+", type=str, default=[], metavar=("\"code\""), dest="pre",
                        help="runs exec(code) for each line of code before execution")
    parser.add_argument("--post", nargs="+", type=str, default=[], metavar=("\"code\""), dest="post",
                        help="runs exec(code) for each line of code after execution")
    parser.add_argument("-P", action="store", type=int, default=1, metavar="max-procs", dest="max_procs",
                        help="number of processes, default: 1")
    parser.add_argument("-p", "--interactive", action="store_true", dest="interactive",
                        help="prompt the user before executing each command, only proceeds if response starts with 'y' or 'Y'")
    parser.add_argument("-n", "--dry-run", action="store_true", dest="dry_run",
                        help="prints commands without executing them")
    parser.add_argument("-v", "--verbose", action="store_true", dest="verbose",
                        help="prints commands before executing them")
    parser.add_argument("-w", "--csv", action="store_true", dest="csv",
                        help="writes results to pyxargs-<yymmdd-hhmmss>.csv in os.getcwd()")
    parser.add_argument("--version", action="store_true", dest="version",
                        help="print version number")
    args = parser.parse_args()
    # check for any argument combination known to cause issues
    if ((not os.path.isdir(args.base_dir)) or
        (args.max_procs <= 0) or
        (args.null and args.delim is not None) or
        (args.py and args.pyev) or
        (args.max_procs > 1 and args.interactive)):
        colourPrint("Invalid argument(s): %s" % (args), "R")
        sys.exit(1)
    if len(args.command) >= 1 and args.command[0] == "--":
        _ = args.command.pop(0)
    # set arguments implied by others and read stdin if required
    if args.null or args.delim is not None or args.arg_file is not None or args.eof_str is not None:
        args.input_mode = "stdin"
    if args.input_mode == "stdin" and args.arg_file is None:
        stdin = sys.stdin.read()
    elif args.input_mode is None and not sys.stdin.isatty():
        stdin = sys.stdin.read()
        if stdin:
            args.input_mode = "stdin"
        else:
            stdin = None
    else:
        stdin = None
    if args.input_mode is None:
        args.input_mode = "file"
    # build and run commands
    if len(args.command) >= 1:
        start_dir = os.getcwd()
        command_dicts = processInput(args, stdin)
        output = processCommands(start_dir, command_dicts, args)
        writeCsv(args, start_dir, output)
    # no commands given, print examples, version, or usage
    elif args.examples:
        print(examples)
    elif args.version:
        print(VERSION)
    else:
        parser.print_usage()


if __name__ == "__main__":
    sys.exit(main())

