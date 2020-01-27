# pyxargs
## Command Line Interface
```
usage: pyxargs [options] command [initial-arguments ...]
       pyxargs [options] -s "command [initial-arguments ...]" ...
       pyxargs -h | --help | --examples

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
  -d base-directory     default: os.getcwd()
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
  -0, --null            input items are terminated by a null character instead
                        of by whitespace, automatically sets mode = stdin
  --delim char          input items are terminated by the specified delimiter
                        instead of whitespace and trailing whitespace is
                        removed, automatically sets mode = stdin
  -a file               read items from file instead of standard input to
                        build commands, automatically sets mode = stdin
  -r regex              only build commands from inputs matching regex
  -o                    omit inputs matching regex instead
  -f                    only match regex to filenames
  -I replace-str        replace occurrences of replace-str in the command(s)
                        with input, default: {}
  --resub pattern repl replace-str
                        replace occurrences of replace-str in the command(s)
                        with re.sub(patten, repl, input)
  --py                  executes command(s) as python code using exec(),
                        beware of side effects
  --pyev                evaluates command(s) as python expression(s) using
                        eval()
  --import library [library ...]
                        runs exec("import " + library) on each library, beware
                        of side effects
  --importstar library [library ...]
                        runs exec("from " + library + " import *") on each
                        library, beware of side effects
  --pre "code" ["code" ...]
                        runs exec(code) for each line of code before
                        execution, beware of side effects
  --post "code" ["code" ...]
                        runs exec(code) for each line of code after execution,
                        beware of side effects
  -p int                number of processes
  --interactive         prompt the user before executing each command
  -n, --norun           prints commands without executing them
  -v, --verbose         prints commands
  -w, --csv             writes results to pyxargs-<yymmdd-hhmmss>.csv in
                        os.getcwd()
```
## Examples
```
comparing usage with find & xargs
    find ./ -name "*" -type f -print0 | xargs -0 -I {} echo {}
    find ./ -name "*" -type f -print0 | pyxargs -0 -I {} echo {}
    find ./ -name "*" -type f -print0 | pyxargs -0 echo {}
    pyxargs -m path echo ./{}
    pyxargs -m path --py "print('./{}')"

use -- to separate options with multiple optional arguments from the command
    pyxargs --pre "print('spam')" "print('spam')" -- echo {}
or change the order of options (they are parsed with argparse)
    pyxargs --pre "print('this is fine too')" -p 1 echo {}
the command takes all remaining arguments, so this will not work
    pyxargs echo {} --pre "print('this statement will be echoed')"
however pipes and redirects still work
    pyxargs echo {} > spam.txt

multiple commands can be used as such
    pyxargs -s "echo No 1. {}" "echo And now... No 2. {}"

regular expressions can be used to filter and modify inputs
    pyxargs -r py --resub py txt {} echo {}
the original inputs can easily be used with the subsituted versions
    pyxargs -r py --resub py txt new echo {}  new

and now for something completely different
    pyxargs --pre "n=0" --post "print(n,'files')" --py "n+=1"
a best effort is made to avoid side effects by executing in its own namespace
```
## Links
- https://github.com/elesiuta/pyxargs
- https://pypi.org/project/pyxargs/
