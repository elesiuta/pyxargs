# pyxargs
## Purpose
This began as a solution to the [encoding problem](https://en.wikipedia.org/wiki/Xargs#Encoding_problem) with [xargs](https://www.gnu.org/software/findutils/manual/html_node/find_html/xargs-options.html) [(additional reference)](http://man7.org/linux/man-pages/man1/xargs.1.html). It eventually grew as I found being able to quickly mix python code with command lines and files to be useful.

Most of xargs functionality has been implemented, however the original focus with fixing the encoding problem via the file input-mode, not to be confused with arg-file, remains. The goal is not to replace xargs but to compliment it for slightly different, and more modern use cases, therefore not all features are included, such as max-lines or max-args.

Going forward development will slow with no major features or changes planned, with the main focus being on having a clear and stable command line interface and documentation. However bugs are still planned to be fixed as soon as possible whenever they are discovered and any new & interesting pythonic features may be considered depending on usefulness and scope.
## Command Line Interface
```
usage: pyxargs [options] command [initial-arguments ...]
       pyxargs [options] -s "command [initial-arguments ...]" ...
       pyxargs -h | --help | --examples | --version

Build and execute command lines or python code from standard input or file
paths, a mostly complete implementation of xargs in python with some added
features. The default input mode (file) builds commands using filenames only
and executes them in their respective directories, this is useful when dealing
with file paths containing multiple character encodings.

optional arguments:
  -h, --help            show this help message and exit
  --examples            print example usage
  -s                    support for multiple commands to be run sequentially
                        by encapsulating in quotes (each its own string)
  -b base-directory     default: os.getcwd()
  -m input-mode         options are:
                        file    = build commands from filenames and execute in
                                  each subdirectory respectively (default)
                        path    = build commands from file paths relative to
                                  the base directory and execute in the base
                                  directory
                        abspath = build commands from file paths relative to
                                  root and execute in the base directory
                        dir     = build commands from directory names instead
                                  of filenames
                        stdin   = build commands from standard input and
                                  execute in the base directory
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
  -n, --norun           prints commands without executing them
  -v, --verbose         prints commands before executing them
  -w, --csv             writes results to pyxargs-<yymmdd-hhmmss>.csv in
                        os.getcwd()
  --version             print version number
```
## Examples
```
comparing usage with find & xargs
    find ./ -name "*" -type f -print0 | xargs -0 -I {} echo {}
    find ./ -name "*" -type f -print0 | pyxargs -0 -I {} echo {}
    find ./ -name "*" -type f -print0 | pyxargs -0 echo {}
    pyxargs -m path echo ./{}
    pyxargs -m path --py "print('./{}')"
note: pyxargs requires a replace-str ({} in this example) to insert inputs,
inputs are not appended in the absence of a replace-str like in xargs,
this also implies the equivalent of xargs --max-lines=1

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

and now for something completely different, python code
    pyxargs --pre "n=0" --post "print(n,'files')" --py n+=1
a best effort is made to avoid side effects by executing in its own namespace
```
## Links
- https://github.com/elesiuta/pyxargs
- https://pypi.org/project/pyxargs/
