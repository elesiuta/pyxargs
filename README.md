# pyxargs
## Purpose
I started this as a simple solution to the [encoding problem with xargs](https://en.wikipedia.org/wiki/Xargs#Encoding_problem). Since then, I've added some additional features such as taking python code as arguments to be executed.  

This is a *mostly* complete implementation of xargs, based entirely on what I felt like at the time, with no new features planned.  
## Command Line Interface
```
usage: pyxargs [options] command [initial-arguments ...]
       pyxargs [options] -s "command [initial-arguments ...]" ...
       pyxargs -h | --help | --examples | --version

Build and execute command lines or python code from standard input or file
paths, a mostly complete implementation of xargs in python with some added
features. The file input mode (default if stdin is empty) builds commands
using filenames only and executes them in their respective directories, this
is useful when dealing with file paths containing multiple character
encodings.

optional arguments:
  -h, --help            show this help message and exit
  --examples            print example usage
  -s                    support for multiple commands to be run sequentially
                        by encapsulating in quotes (each its own string)
  -b base-directory     default: os.getcwd()
  -m input-mode         options are:
                        file    = build commands from filenames and execute in
                                  each subdirectory respectively
                        path    = build commands from file paths relative to
                                  the base directory and execute in the base
                                  directory
                        abspath = build commands from file paths relative to
                                  root and execute in the base directory
                        dir     = build commands from directory names instead
                                  of filenames
                        stdin   = build commands from standard input and
                                  execute in the base directory
                        default: stdin unless empty, then file
  --symlinks            follow symlinks when scanning directories
  -0, --null            input items are terminated by a null character instead
                        of by whitespace, sets input-mode=stdin
  -d delim              input items are terminated by the specified delimiter
                        instead of whitespace and trailing whitespace is
                        removed, sets input-mode=stdin
  -a arg-file           read input items from arg-file instead of standard
                        input to build commands, sets input-mode=stdin
  -E eof-str            ignores any input after eof-str, sets input-mode=stdin
  -c max-chars          omits any command line exceeding max-chars, no limit
                        by default
  -I replace-str        replace occurrences of replace-str in the command(s)
                        with input, default: {}
  --resub pattern repl replace-str
                        replace occurrences of replace-str in the command(s)
                        with re.sub(patten, repl, input)
  -r regex              only build commands from inputs matching regex
  -o                    omit inputs matching regex instead
  -f                    only match regex against filenames, ignoring full
                        paths (if available)
  --py                  executes command(s) as python code using exec()
  --pyev                evaluates command(s) as python expression(s) using
                        eval()
  --import library [library ...]
                        executes 'import <library>' for each library
  --importstar library [library ...]
                        executes 'from <library> import *' for each library
  --pre "code" ["code" ...]
                        runs exec(code) for each line of code before execution
  --post "code" ["code" ...]
                        runs exec(code) for each line of code after execution
  -P max-procs          number of processes, default: 1
  -p, --interactive     prompt the user before executing each command, only
                        proceeds if response starts with 'y' or 'Y'
  -n, --dry-run         prints commands without executing them
  -v, --verbose         prints commands before executing them
  -w, --csv             writes results to pyxargs-<yymmdd-hhmmss>.csv in
                        os.getcwd()
  --version             print version number
```
## Examples
```
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
```
## Links
- https://github.com/elesiuta/pyxargs
- https://pypi.org/project/pyxargs/
