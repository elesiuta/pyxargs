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
import argparse
import datetime
import textwrap
import multiprocessing


VERSION = "1.1.1"
user_namespace = {}


class ArgparseCustomFormatter(argparse.HelpFormatter):
    def _split_lines(self, text, width):
        if text[:2] == 'F!':
            return text.splitlines()[1:]
        return argparse.HelpFormatter._split_lines(self, text, width)


def replaceSurrogates(string):
    return string.encode('utf16', 'surrogatepass').decode('utf16', 'replace')


def colourPrint(string, colour):
    colours = {
        "HEADER": '\033[95m',
        "OKBLUE": '\033[94m',
        "OKGREEN": '\033[92m',
        "WARNING": '\033[93m',
        "FAIL": '\033[91m',
        "ENDC": '\033[0m',
        "BOLD": '\033[1m',
        "UNDERLINE": '\033[4m'
    }
    string = replaceSurrogates(string)
    print(colours[colour] + string + colours["ENDC"])


def safePrint(string):
    print(replaceSurrogates(string))


def writeCsv(args, file_dir, data, enc=None, delimiter=","):
    if args.csv:
        file_name = "pyxargs-" + datetime.datetime.now().strftime("%y%m%d-%H%M%S") + ".csv"
        file_path = os.path.join(file_dir, file_name)
        with open(file_path, "w", newline="", encoding=enc, errors="backslashreplace") as f:
            writer = csv.writer(f, delimiter=delimiter)
            for row in data:
                writer.writerow(row)


def buildCommand(dir_name, file_name, arg_input, args):
    # mode
    if arg_input is None:
        if args.input_mode == "file":
            arg_input = file_name
        elif args.input_mode == "dir":
            arg_input = dir_name
        elif args.input_mode == "path":
            arg_input = os.path.join(dir_name, file_name)
            arg_input = os.path.relpath(arg_input, args.base_directory)
        elif args.input_mode == "abspath":
            arg_input = os.path.join(dir_name, file_name)
    # check re match
    if not args.regex_fname and dir_name is not None and file_name is not None:
        relpath = os.path.join(dir_name, file_name)
        relpath = os.path.relpath(relpath, args.base_directory)
        if (re.search(args.regex, relpath) is not None) == args.regex_omit:
            return None
    elif args.regex_fname and file_name is not None:
        if (re.search(args.regex, file_name) is not None) == args.regex_omit:
            return None
    else:
        if (re.search(args.regex, arg_input) is not None) == args.regex_omit:
            return None
    # interpret command(s)
    if args.command_strings:
        command = args.command[:]
    else:
        command = [" ".join(args.command)]
    # re.sub input into command
    if args.resub is not None:
        for i in range(len(command)):
            command[i] = command[i].replace(args.resub[2], re.sub(args.resub[0], args.resub[1], arg_input))
    # sub input into command
    for i in range(len(command)):
        command[i] = command[i].replace(args.replace_str, arg_input)
    # and finally
    return command


def executeCommand(command_dict):
    args = command_dict["args"]
    dir_name = command_dict["dir"]
    cmds = command_dict["cmd"]
    # mode
    if args.input_mode in ["file", "stdin"]:
        os.chdir(dir_name)
    # no run
    if args.norun:
        if len(cmds) > 1:
            safePrint(str(cmds))
        else:
            safePrint(cmds[0])
        return ["NORUN"]
    else:
        # execute command(s) and return output for csv
        output = []
        if len(cmds) > 1:
            if args.verbose:
                colourPrint(str(cmds), "OKBLUE")
        for cmd in cmds:
            if args.verbose:
                colourPrint(cmd, "OKGREEN")
            if args.py:
                try:
                    exec(cmd, globals(), user_namespace)
                    output.append("EXEC SUCCESS")
                except Exception as e:
                    output.append("EXEC ERROR: " + str(e))
            elif args.pyev:
                try:
                    output.append(eval(cmd, globals(), user_namespace))
                except Exception as e:
                    output.append("EVAL ERROR: " + str(e))
            elif args.csv:
                with os.popen(cmd) as result:
                    result = result.read()
                    sys.stdout.write(result)
                    output.append(result)
            else:
                os.system(cmd)
                output.append("os.system")
        return output


def main():
    readme = ("Build and execute command lines or python code from standard input or file paths, "
              "a mostly complete implementation of xargs in python with some added features. "
              "The default input mode (file) builds commands using filenames only and executes them in their respective directories, "
              "this is useful when dealing with file paths containing multiple character encodings.")
    examples = textwrap.dedent("""
    comparing usage with find & xargs
        find ./ -name "*" -type f -print0 | xargs -0 -I {} echo {}
        find ./ -name "*" -type f -print0 | pyxargs -0 -I {} echo {}
        find ./ -name "*" -type f -print0 | pyxargs -0 echo {}
        pyxargs -m path echo ./{}
        pyxargs -m path --py "print('./{}')"

    use -- to separate options with multiple optional arguments from the command
        pyxargs --pre "print('spam')" "print('spam')" -- echo {}
    or separate with another option (they are parsed with argparse)
        pyxargs --pre "print('this is fine too')" -P 1 echo {}
    the command takes all remaining arguments, so this will not work
        pyxargs echo {} --pre "print('this statement will be echoed')"
    however pipes and redirects still work
        pyxargs echo {} > spam.txt

    multiple commands can be used as such
        pyxargs -s "echo No 1. {}" "echo And now... No 2. {}"

    regular expressions can be used to filter and modify inputs
        pyxargs -r \.py --resub \.py .txt {} echo {}
    the original inputs can easily be used with the subsituted versions
        pyxargs -r \.py --resub \.py .txt new echo {} new

    and now for something completely different
        pyxargs --pre "n=0" --post "print(n,'files')" --py n += 1
        pyxargs --pre "n=0" --post "print(n,'files')" --py -s "n+=1" "n+=1"
    a best effort is made to avoid side effects by executing in its own namespace
    """)
    parser = argparse.ArgumentParser(description=readme,
                                     formatter_class=lambda prog: ArgparseCustomFormatter(prog, max_help_position=24),
                                     usage="%(prog)s [options] command [initial-arguments ...]\n"
                                           "       %(prog)s [options] -s \"command [initial-arguments ...]\" ...\n"
                                           "       %(prog)s -h | --help | --examples | --version")
    parser.add_argument("command", action="store", type=str, nargs=argparse.REMAINDER,
                        help=argparse.SUPPRESS)
    parser.add_argument("--examples", action="store_true",
                        help="print example usage")
    parser.add_argument("-s", action="store_true", dest="command_strings",
                        help="support for multiple commands to be run sequentially by encapsulating in quotes (each its own string)")
    parser.add_argument("-b", type=str, default=os.getcwd(), metavar="base-directory", dest="base_directory",
                        help="default: os.getcwd()")
    parser.add_argument("-m", type=str, default="file", metavar="input-mode", choices=['file', 'path', 'abspath', 'dir', 'stdin'], dest="input_mode",
                        help="F!\n"
                             "options are:\n"
                             "file    = build commands from filenames and execute in\n"
                             "          each subdirectory respectively (default)\n"
                             "path    = build commands from file paths relative to\n"
                             "          the base directory and execute in the base\n"
                             "          directory\n"
                             "abspath = build commands from file paths relative to\n"
                             "          root and execute in the base directory\n"
                             "dir     = build commands from directory names instead\n"
                             "          of filenames\n"
                             "stdin   = build commands from standard input and\n"
                             "          execute in the base directory")
    parser.add_argument("-0", "--null", action="store_true", dest="null",
                        help="input items are terminated by a null character instead of by whitespace, automatically sets mode = stdin")
    parser.add_argument("-d", type=str, metavar="delim", dest="delim",
                        help="input items are terminated by the specified delimiter instead of whitespace and trailing whitespace is removed, automatically sets mode = stdin")
    parser.add_argument("-a", type=str, metavar="file", dest="file",
                        help="read items from file instead of standard input to build commands, automatically sets mode = stdin")
    parser.add_argument("-E", type=str, metavar="eof-str", dest="eof_str",
                        help="ignores any input after eof-str, automatically sets mode = stdin")
    parser.add_argument("-r", type=str, default=".", metavar="regex", dest="regex",
                        help="only build commands from inputs matching regex")
    parser.add_argument("-o", action="store_true", dest="regex_omit",
                        help="omit inputs matching regex instead")
    parser.add_argument("-f", action="store_true", dest="regex_fname",
                        help="only match regex to filenames")
    parser.add_argument("-I", action="store", type=str, default="{}", metavar="replace-str", dest="replace_str",
                        help="replace occurrences of replace-str in the command(s) with input, default: {}")
    parser.add_argument("--resub", nargs=3, type=str, metavar=("pattern", "repl", "replace-str"),
                        help="replace occurrences of replace-str in the command(s) with re.sub(patten, repl, input)")
    parser.add_argument("--py", action="store_true",
                        help="executes command(s) as python code using exec(), beware of side effects")
    parser.add_argument("--pyev", action="store_true",
                        help="evaluates command(s) as python expression(s) using eval()")
    parser.add_argument("--import", nargs="+", type=str, default=[], metavar=("library"), dest="imprt",
                        help="runs exec(\"import \" + library) on each library, beware of side effects")
    parser.add_argument("--importstar", nargs="+", type=str, default=[], metavar=("library"), dest="imprtstar",
                        help="runs exec(\"from \" + library + \" import *\") on each library, beware of side effects")
    parser.add_argument("--pre", nargs="+", type=str, default=[], metavar=("\"code\""),
                        help="runs exec(code) for each line of code before execution, beware of side effects")
    parser.add_argument("--post", nargs="+", type=str, default=[], metavar=("\"code\""),
                        help="runs exec(code) for each line of code after execution, beware of side effects")
    parser.add_argument("-P", "--max-procs", action="store", type=int, default=1, metavar="int", dest="max_procs",
                        help="number of processes, default is 1")
    parser.add_argument("-p", "--interactive", action="store_true",
                        help="prompt the user before executing each command, only proceeds if response starts with 'y' or 'Y'")
    parser.add_argument("-n", "--norun", action="store_true",
                        help="prints commands without executing them")
    parser.add_argument("-v", "--verbose", action="store_true",
                        help="prints commands")
    parser.add_argument("-w", "--csv", action="store_true",
                        help="writes results to pyxargs-<yymmdd-hhmmss>.csv in os.getcwd()")
    parser.add_argument("--version", action="store_true",
                        help="print version number")
    args = parser.parse_args()
    # check for any argument combination known to cause issues
    if ((not os.path.isdir(args.base_directory)) or
        (args.max_procs <= 0) or
        (args.null and args.delim is not None) or
        (args.py and args.pyev) or
        (args.max_procs > 1 and args.interactive)):
        colourPrint("Invalid argument(s): %s" % (args), "FAIL")
        sys.exit(0)
    if len(args.command) >= 1 and args.command[0] == "--":
        _ = args.command.pop(0)
    # process commands
    if len(args.command) >= 1:
        base_dir = args.base_directory
        start_dir = os.getcwd()
        command_dicts = []
        output = []
        # build commands using standard input mode or by walking the directory tree
        if args.input_mode == "stdin" or args.null or args.delim is not None or args.file is not None or args.eof_str is not None:
            args.input_mode = "stdin"
            # set seperator
            seperator = None
            if args.null:
                seperator = "\0"
            elif args.delim is not None:
                seperator = args.delim
            # read input from stdin or file
            if args.file is None:
                # stdin
                if args.eof_str is not None:
                    stdin = sys.stdin.read().split(args.eof_str, 1)[0]
                elif args.delim is not None:
                    stdin = sys.stdin.read().rstrip()
                else:
                    stdin = sys.stdin.read()
                arg_input_list = stdin.split(seperator)
            elif os.path.isfile(args.file):
                # file
                with open(args.file, "r") as f:
                    if args.eof_str is not None:
                        arg_input_list = f.read().split(args.eof_str, 1)[0].splitlines()
                    elif seperator is None:
                        arg_input_list = f.readlines()
                    else:
                        arg_input_list = f.read().split(seperator)
            else:
                # error
                colourPrint("Invalid file: %s" % (args.file), "FAIL")
                sys.exit(0)
            # build commands from input
            for arg_input in arg_input_list:
                command = buildCommand(None, None, arg_input, args)
                if command is not None:
                    command_dicts.append({"args": args, "dir": base_dir, "cmd": command})
        elif args.input_mode in ['file', 'path', 'abspath', 'dir']:
            # silly walk
            for dir_path, subdir_list, file_list in os.walk(base_dir):
                subdir_list.sort()
                if args.input_mode == "dir":
                    # build commands from directory names
                    command = buildCommand(dir_path, None, None, args)
                    if command is not None:
                        command_dicts.append({"args": args, "dir": dir_path, "cmd": command})
                elif args.input_mode in ["file", "path", "abspath"]:
                    # build commands from filenames or file paths
                    for f in sorted(file_list):
                        command = buildCommand(dir_path, f, None, args)
                        if command is not None:
                            command_dicts.append({"args": args, "dir": dir_path, "cmd": command})
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
                    for cmd in command_dict["cmd"]: colourPrint(cmd, "OKGREEN")
                    colourPrint("Run command(s) (Yes/No/QUIT)?", "WARNING")
                    run = input("> ")
                    if len(run) >= 1 and run[0].lower() == "y":
                        output.append(["COMMAND(S):"] + command_dict["cmd"] + ["OUTPUT(S):"] + executeCommand(command_dict))
                    elif len(run) >= 1 and run[0].lower() == "n":
                        output.append(["COMMAND(S):"] + command_dict["cmd"] + ["OUTPUT(S):"] + ["SKIPPED"])
                    else:
                        writeCsv(args, start_dir, output)
                        sys.exit(0)
            else:
                for command_dict in command_dicts:
                    output.append(["COMMAND(S):"] + command_dict["cmd"] + ["OUTPUT(S):"] + executeCommand(command_dict))
        elif args.max_procs > 1:
            with multiprocessing.Pool(args.max_procs) as pool:
                async_result = pool.map_async(executeCommand, command_dicts)
                results = async_result.get()
            for i in range(len(command_dicts)):
                output.append(["COMMAND(S):"] + command_dicts[i]["cmd"] + ["OUTPUT(S):"] + results[i])
        # post execution tasks
        for line in args.post:
            exec(line, globals(), user_namespace)
        # write csv
        writeCsv(args, start_dir, output)
    # no commands given, print examples or usage
    elif args.examples:
        print(examples)
    elif args.version:
        print(VERSION)
    else:
        parser.print_usage()


if __name__ == "__main__":
    sys.exit(main())

