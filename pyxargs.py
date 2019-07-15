import os
import re
import csv
import sys
import argparse
import datetime

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
    if not args.f and dirName != None and file_name != None:
        relpath = os.path.join(dir_name, file_name)
        relpath = os.path.relpath(relpath, args.d)
        if (re.search(args.r, relpath) != None) == args.o:
            return None
    elif file_name != None:
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
    if args.m == "file":
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
                    exec(cmd)
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
    readme = ("build and execute command lines from file paths, "
              "a partial implementation of xargs in python. "
              "note: argparse does not escape spaces in arguments, use quotes. ")
    examples = """
    comparing usage with find | xargs
    find ./ -name "*" -type f -print0 | xargs -0 -I{} echo {}
    find ./ -name "*" -type f -print0 | python pyxargs.py -0 "echo {}"
    python pyxargs.py -m path "echo ./{}"
    """
    parser = argparse.ArgumentParser(description=readme)
    parser.add_argument("command", action="store", type=str, metavar="command-string", nargs="*",
                        help="command-string = \"command [initial-arguments]\"")
    parser.add_argument("-d", type=str, default=os.getcwd(), metavar="base-directory",
                        help="base directory containing files to build commands from, default: os.getcwd()")
    parser.add_argument("--stdin", action="store_true",
                        help="build commands from standard input instead of file paths, -d becomes execution directory, -m and -f are incompatible")
    parser.add_argument("-0", "--null", action="store_true",
                        help="input items are terminated by a null character instead of by whitespace, --stdin is implied and not necessary")
    parser.add_argument("--delimiter", type=str, metavar="delim",
                        help="input items are terminated by the specified character instead, --stdin is implied and not necessary")
    parser.add_argument("-m", type=str, default="file", metavar="mode", choices=['file', 'path', 'abspath', 'dir'],
                        help="file = pass filenames while walking through each subdirectory (default), path = pass full filepaths relative to the base directory, abspath = pass full filepaths relative to root, dir = pass directories only")
    parser.add_argument("-r", type=str, default=".", metavar="regex",
                        help="only pass inputs matching regex")
    parser.add_argument("-o", action="store_true",
                        help="omit inputs matching regex instead")
    parser.add_argument("-f", action="store_true",
                        help="only match regex to filenames")
    parser.add_argument("-I", action="store", type=str, default="{}", metavar="replace-str",
                        help="replace occurrences of replace-str in the initial-arguments with input, default: {}")
    parser.add_argument("--resub", nargs=3, type=str, metavar=("pattern", "repl", "replace-str"),
                        help="replace occurrences of replace-str in the initial-arguments with re.sub(patten, repl, input)")
    parser.add_argument("--py", action="store_true",
                        help="executes cmd as python code using exec(), takes priority over --pyev flag")
    parser.add_argument("--pyev", action="store_true",
                        help="evaluates cmd as python expression using eval(), does nothing if run with --py flag")
    parser.add_argument("--imprt", nargs="*", type=str, default=[], metavar=("library"),
                        help="runs exec(\"import \" + library) on each library")
    parser.add_argument("--imprtstar", nargs="*", type=str, default=[], metavar=("library"),
                        help="runs exec(\"from \" + library + \" import *\") on each library")
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
        # imports
        for i in args.imprt:
            exec("import " + i)
        for i in args.imprtstar:
            exec("from " + i + " import *")
        # use standard input or files from directory
        if (args.stdin or args.null or args.delimiter != None) and args.m == "file" and not args.f:
            # set seperator
            seperator = None
            if args.null:
                seperator = "\0"
            elif args.delimiter != None:
                seperator = args.delimiter
            # read input
            stdin = sys.stdin.read()
            for arg in stdin.split(seperator):
                command = buildCommand(None, None, arg, args)
                if command != None:
                    command_dicts.append({"args": args, "dir": args.d, "cmd": command})
        elif not args.stdin:
            # silly walk
            for dirName, subdirList, fileList in os.walk(root_dir):
                subdirList.sort()
                if args.m == "dir":
                    command = buildCommand(dirName, None, None, args)
                    if command != None:
                        command_dicts.append({"args": args, "dir": dirName, "cmd": command})
                elif args.m == "file" or args.m == "path" or args.m == "abspath": 
                    for f in sorted(fileList):
                        command = buildCommand(dirName, f, None, args)
                        if command != None:
                            command_dicts.append({"args": args, "dir": dirName, "cmd": command})
        else:
            colourPrint("Invalid argument combination: %s" %(args), "FAIL")
            sys.exit(0)
        # execute commands
        for command_dict in command_dicts:
            output.append(["COMMAND(S):"] + command_dict["cmd"] + ["OUTPUT(S):"] + executeCommand(command_dict))
        # write csv
        if args.csv:
            file_name = "pyxargs" + datetime.datetime.now().strftime("%y%m%d-%H%M%S") + ".csv"
            writeCsv(os.path.join(start_dir, file_name), output)
