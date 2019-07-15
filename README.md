# pyxargs

```
usage: pyxargs.py [-h] [-d base-directory] [--stdin] [-0] [--delimiter delim]
                  [-m mode] [-r regex] [-o] [-f] [-I replace-str]
                  [--resub pattern repl replace-str] [--py] [--pyev]
                  [--imprt [library [library ...]]]
                  [--imprtstar [library [library ...]]] [-p num] [-n] [-v]
                  [-w] [--examples]
                  [command-string [command-string ...]]

build and execute command lines from file paths, a partial implementation of
xargs in python. note: argparse does not escape spaces in arguments, use
quotes.

positional arguments:
  command-string        command-string = "command [initial-arguments]"

optional arguments:
  -h, --help            show this help message and exit
  -d base-directory     base directory containing files to build commands
                        from, default: os.getcwd()
  --stdin               build commands from standard input instead of file
                        paths, -d becomes execution directory, -m and -f are
                        incompatible
  -0, --null            input items are terminated by a null character instead
                        of by whitespace, --stdin is implied and not necessary
  --delimiter delim     input items are terminated by the specified character
                        instead, --stdin is implied and not necessary
  -m mode               file = pass filenames while walking through each
                        subdirectory (default), path = pass full filepaths
                        relative to the base directory, abspath = pass full
                        filepaths relative to root, dir = pass directories
                        only
  -r regex              only pass inputs matching regex
  -o                    omit inputs matching regex instead
  -f                    only match regex to filenames
  -I replace-str        replace occurrences of replace-str in the initial-
                        arguments with input, default: {}
  --resub pattern repl replace-str
                        replace occurrences of replace-str in the initial-
                        arguments with re.sub(patten, repl, input)
  --py                  executes cmd as python code using exec(), takes
                        priority over --pyev flag
  --pyev                evaluates cmd as python expression using eval(), does
                        nothing if run with --py flag
  --imprt [library [library ...]]
                        runs exec("import " + library) on each library
  --imprtstar [library [library ...]]
                        runs exec("from " + library + " import *") on each
                        library
  -p num                number of processes (todo)
  -n, --norun           prints commands without executing them
  -v, --verbose         prints commands
  -w, --csv             writes results to pyxargs-<yymmdd-hhmmss>.csv in
                        os.getcwd()
  --examples            print example usage
```
