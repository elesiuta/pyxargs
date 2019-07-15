import os
import re
import csv
import sys
import argparse
import datetime

class ArgparseCustomFormatter(argparse.HelpFormatter):
    def _split_lines(self, text, width):
        if text[:2] == 'F!':
            return text.splitlines()[1:]
        return argparse.HelpFormatter._split_lines(self, text, width)

def replaceSurrogates(string):
    return string.encode('utf16', 'surrogatepass').decode('utf16', 'replace')

def colourPrint(string, colour):
    colours = {
        "HEADER" : '\033[95m',
        "OKBLUE" : '\033[94m',
        "OKGREEN" : '\033[92m',
        "WARNING" : '\033[93m',
        "FAIL" : '\033[91m',
        "ENDC" : '\033[0m',
        "BOLD" : '\033[1m',
        "UNDERLINE" : '\033[4m'
    }
    string = replaceSurrogates(string)
    print(colours[colour] + string + colours["ENDC"])

def safePrint(string):
    print(replaceSurrogates(string))

def writeCsv(fName, data, enc = None, delimiter = ","):
    with open(fName, "w", newline="", encoding=enc, errors="backslashreplace") as f:
        writer = csv.writer(f, delimiter=delimiter)
        for row in data:
            writer.writerow(row)

def buildCommand(dir_name, file_name, arg_input, args):
    # mode
    if arg_input == None:
        if args.m == "file":
            arg_input = file_name
        elif args.m == "dir":
            arg_input = dir_name
        elif args.m == "path":
            arg_input = os.path.join(dir_name, file_name)
            arg_input = os.path.relpath(arg_input, args.d)
        elif args.m == "abspath":
            arg_input = os.path.join(dir_name, file_name)
    # check re match
    if not args.f and dir_name != None and file_name != None:
        relpath = os.path.join(dir_name, file_name)
        relpath = os.path.relpath(relpath, args.d)
        if (re.search(args.r, relpath) != None) == args.o:
            return None
    elif args.f and file_name != None:
        if (re.search(args.r, file_name) != None) == args.o:
            return None
    else:
        if (re.search(args.r, arg_input) != None) == args.o:
            return None
    # copy commands
    command = args.command[:]
    # re.sub input into command
    if args.resub != None:
        for i in range(len(command)):
            command[i] = command[i].replace(args.resub[2], re.sub(args.resub[0], args.resub[1], arg_input))
    # sub input into command
    for i in range(len(command)):
        command[i] = command[i].replace(args.I, arg_input)
    # and finally
    return command

def executeCommand(command_dict):
    args = command_dict["args"]
    dir_name = command_dict["dir"]
    cmds = command_dict["cmd"]
    # mode
    if args.m in ["file", "stdin"]:
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
                colourPrint(cmd,"OKGREEN")
            if args.py:
                try:
                    exec(cmd, globals())
                    output.append("EXEC SUCCESS")
                except:
                    output.append("EXEC ERROR")
            elif args.pyev:
                try:
                    output.append(eval(cmd))
                except:
                    output.append("EVAL ERROR")
            elif args.csv:
                output.append(os.popen(cmd).read())
            else:
                os.system(cmd)
                output.append("os.system")
        return output

if __name__ == "__main__":
    readme = ("build and execute command lines from standard input or file paths, "
              "a partial implementation of xargs in python. "
              "note: argparse does not escape spaces in arguments, use quotes. ")
    examples = """
    comparing usage with find | xargs
    find ./ -name "*" -type f -print0 | xargs -0 -I{} echo {}
    find ./ -name "*" -type f -print0 | python pyxargs.py -0 "echo {}"
    python pyxargs.py -m path "echo ./{}"
    """
    parser = argparse.ArgumentParser(description=readme, formatter_class=ArgparseCustomFormatter)
    parser.add_argument("command", action="store", type=str, metavar="command-string", nargs="*",
                        help="command-string = \"command [initial-arguments]\"")
    parser.add_argument("-d", type=str, default=os.getcwd(), metavar="base-directory",
                        help="default: os.getcwd()")
    parser.add_argument("-m", type=str, default="file", metavar="mode", choices=['file', 'path', 'abspath', 'dir', 'stdin'],
                        help="F!\n"
                             "options are:\n"
                             "file    = build commands from filenames and execute in\n"
                             "          each subdirectory respectively (default)\n"
                             "path    = build commands from file paths relative to\n"
                             "          the base directory and execute in the base\n"
                             "          directory\n"
                             "abspath = build commands from file paths relative to\n"
                             "          root and execute in the base directory\n"
                             "dir     = pass directories only\n"
                             "stdin   = build commands from standard input and\n"
                             "          execute in the base-directory")
    parser.add_argument("-0", "--null", action="store_true",
                        help="input items are terminated by a null character instead of by whitespace, automatically sets mode to \"stdin\"")
    parser.add_argument("--delimiter", type=str, metavar="delim",
                        help="input items are terminated by the specified character instead of whitespace and trailing whitespace is removed, automatically sets mode to \"stdin\"")
    parser.add_argument("-r", type=str, default=".", metavar="regex",
                        help="only build commands from inputs matching regex")
    parser.add_argument("-o", action="store_true",
                        help="omit inputs matching regex instead")
    parser.add_argument("-f", action="store_true",
                        help="only match regex to filenames")
    parser.add_argument("-I", action="store", type=str, default="{}", metavar="replace-str",
                        help="replace occurrences of replace-str in the initial-arguments with input, default: {}")
    parser.add_argument("--resub", nargs=3, type=str, metavar=("pattern", "repl", "replace-str"),
                        help="replace occurrences of replace-str in the initial-arguments with re.sub(patten, repl, input)")
    parser.add_argument("--py", action="store_true",
                        help="executes cmd as python code using exec(), takes priority over --pyev flag, beware of side effects")
    parser.add_argument("--pyev", action="store_true",
                        help="evaluates cmd as python expression using eval(), does nothing if run with --py flag")
    parser.add_argument("--imprt", nargs="*", type=str, default=[], metavar=("library"),
                        help="runs exec(\"import \" + library) on each library, beware of side effects")
    parser.add_argument("--imprtstar", nargs="*", type=str, default=[], metavar=("library"),
                        help="runs exec(\"from \" + library + \" import *\") on each library, beware of side effects")
    parser.add_argument("--pre", nargs="*", type=str, default=[], metavar=("code"),
                        help="runs exec(code) for each line of code before execution, beware of side effects")
    parser.add_argument("--post", nargs="*", type=str, default=[], metavar=("code"),
                        help="runs exec(code) for each line of code after execution, beware of side effects")
    parser.add_argument("-p", action="store", type=int, default=1, metavar="num",
                        help="number of processes (todo)")
    parser.add_argument("-n", "--norun", action="store_true",
                        help="prints commands without executing them")
    parser.add_argument("-v", "--verbose", action="store_true",
                        help="prints commands")
    parser.add_argument("-w", "--csv", action="store_true",
                        help="writes results to pyxargs-<yymmdd-hhmmss>.csv in os.getcwd()")
    parser.add_argument("--examples", action="store_true",
                        help="print example usage")
    args = parser.parse_args()
    if args.examples:
        print(examples)
    if os.path.isdir(args.d) and len(args.command) >= 1:
        root_dir = args.d
        start_dir = os.getcwd()
        command_dicts = []
        output = []
        # use standard input or files from directory
        if args.m == "stdin" or args.null or args.delimiter != None:
            args.m = "stdin"
            # set seperator
            seperator = None
            if args.null:
                seperator = "\0"
            elif args.delimiter != None:
                seperator = args.delimiter
            # read input
            if args.delimiter != None:
                stdin = sys.stdin.read().rstrip()
            else:
                stdin = sys.stdin.read()
            for arg_input in stdin.split(seperator):
                command = buildCommand(None, None, arg_input, args)
                if command != None:
                    command_dicts.append({"args": args, "dir": args.d, "cmd": command})
        elif args.m in ['file', 'path', 'abspath', 'dir']:
            # silly walk
            for dirName, subdirList, fileList in os.walk(root_dir):
                subdirList.sort()
                if args.m == "dir":
                    command = buildCommand(dirName, None, None, args)
                    if command != None:
                        command_dicts.append({"args": args, "dir": dirName, "cmd": command})
                elif args.m in ["file", "path", "abspath"]:
                    for f in sorted(fileList):
                        command = buildCommand(dirName, f, None, args)
                        if command != None:
                            command_dicts.append({"args": args, "dir": dirName, "cmd": command})
        else:
            colourPrint("Invalid argument combination: %s" %(args), "FAIL")
            sys.exit(0)
        # pre execution tasks
        for i in args.imprt:
            exec("import " + i)
        for i in args.imprtstar:
            exec("from " + i + " import *")
        for line in args.pre:
            exec(line)
        # execute commands
        for command_dict in command_dicts:
            output.append(["COMMAND(S):"] + command_dict["cmd"] + ["OUTPUT(S):"] + executeCommand(command_dict))
        # post execution tasks
        for line in args.post:
            exec(line)
        # write csv
        if args.csv:
            file_name = "pyxargs" + datetime.datetime.now().strftime("%y%m%d-%H%M%S") + ".csv"
            writeCsv(os.path.join(start_dir, file_name), output)
