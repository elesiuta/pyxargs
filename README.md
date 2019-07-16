# pyxargs

```
usage: pyxargs.py [-h] [-s] [-d base-directory] [-m mode] [-0] [--delim char]
                  [-r regex] [-o] [-f] [-I replace-str]
                  [--resub pattern repl replace-str] [--py] [--pyev]
                  [--imprt [library [library ...]]]
                  [--imprtstar [library [library ...]]]
                  [--pre [code [code ...]]] [--post [code [code ...]]]
                  [-p int] [-n] [-v] [-w] [--examples]
                  [command-part [command-part ...]]

build and execute command lines from standard input or file paths, a partial
implementation of xargs in python. note: argparse does not escape spaces in
arguments, use quotes.

positional arguments:
  command-part          (default)
                        command-part[0] = base-command
                        command-part[1:n] = initial-argument(s)
                        (-s)
                        command-part = "base-command [initial-argument(s)]"

optional arguments:
  -h, --help            show this help message and exit
  -s                    interpret each command-part as a separate command to
                        be run sequentially
  -d base-directory     default: os.getcwd()
  -m mode               options are:
                        file    = build commands from filenames and execute in
                                  each subdirectory respectively (default)
                        path    = build commands from file paths relative to
                                  the base directory and execute in the base
                                  directory
                        abspath = build commands from file paths relative to
                                  root and execute in the base directory
                        dir     = pass directories only
                        stdin   = build commands from standard input and
                                  execute in the base-directory
  -0, --null            input items are terminated by a null character instead
                        of by whitespace, automatically sets mode = stdin
  --delim char          input items are terminated by the specified delimiter
                        instead of whitespace and trailing whitespace is
                        removed, automatically sets mode = stdin
  -r regex              only build commands from inputs matching regex
  -o                    omit inputs matching regex instead
  -f                    only match regex to filenames
  -I replace-str        replace occurrences of replace-str in the command(s)
                        with input, default: {}
  --resub pattern repl replace-str
                        replace occurrences of replace-str in the command(s)
                        with re.sub(patten, repl, input)
  --py                  executes command(s) as python code using exec(), takes
                        priority over --pyev flag, beware of side effects
  --pyev                evaluates command(s) as python expression(s) using
                        eval(), does nothing if run with --py flag
  --imprt [library [library ...]]
                        runs exec("import " + library) on each library, beware
                        of side effects
  --imprtstar [library [library ...]]
                        runs exec("from " + library + " import *") on each
                        library, beware of side effects
  --pre [code [code ...]]
                        runs exec(code) for each line of code before
                        execution, beware of side effects
  --post [code [code ...]]
                        runs exec(code) for each line of code after execution,
                        beware of side effects
  -p int                number of processes (be careful!)
  -n, --norun           prints commands without executing them
  -v, --verbose         prints commands
  -w, --csv             writes results to pyxargs-<yymmdd-hhmmss>.csv in
                        os.getcwd()
  --examples            print example usage
```
