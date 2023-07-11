# pyxargs

This started as a simple solution to the [encoding problem with xargs](https://en.wikipedia.org/wiki/Xargs#Encoding_problem). It is a partial and opinionated implementation of xargs with the goal of being easier to use for most use cases.  

It also contains some additional features which may or may not be useful, such as taking python code as arguments to be executed, or filtering input with regular expressions. No new features are planned.  

You can install [pyxargs](https://github.com/elesiuta/pyxargs/) from [PyPI](https://pypi.org/project/pyxargs/).  
## Command Line Interface
```
usage: pyxargs [options] command [initial-arguments ...]
       pyxargs -h | --help | --examples | --version

Build and execute command lines or python code from standard input or file
paths, a partial and opinionated implementation of xargs in python with some
added features. The file input mode (default if stdin is not connected) builds
commands using filenames only and executes them in their respective
directories, this is useful when dealing with file paths containing multiple
character encodings.

options:
  -h, --help            show this help message and exit
  --examples            show example usage and exit
  --version             show program's version number and exit
  -m input-mode         options are:
                        file    = build commands from filenames and execute in
                                  each subdirectory respectively
                        path    = build commands from file paths relative to
                                  the current directory and execute in the
                                  current directory
                        abspath = build commands from absolute file paths and 
                                  execute in the current directory
                        stdin   = build commands from standard input and
                                  execute in the current directory
                        default: stdin if connected, otherwise file
  --folders             use folders instead files (for input modes: file,
                        path, abspath)
  -t, --top             do not recurse into subdirectories (for input modes:
                        file, path, abspath)
  --sym, --symlinks     follow symlinks when scanning directories (for input
                        modes: file, path, abspath)
  -a file, --arg-file file
                        read input items from file instead of standard input
                        (for input mode: stdin)
  -0, --null            input items are separated by a null character instead
                        of whitespace (for input mode: stdin)
  -d delim, --delimiter delim
                        input items are separated by the specified delimiter
                        instead of whitespace (for input mode: stdin)
  -s regex, --split regex
                        split each input item with re.split(regex, input)
                        before building command (after separating by
                        delimiter), use {0}, {1}, ... to specify placement
                        (implies --format)
  -f, --format          format command with input using str.format() instead
                        of appending or replacing via -I replace-str
  -I replace-str        replace occurrences of replace-str in command with
                        input, default: {}
  --resub pattern substitution replace-str
                        replace occurrences of replace-str in command with
                        re.sub(patten, substitution, input)
  -r regex              only build commands from inputs matching regex for
                        input mode stdin, and matching relative paths for all
                        other input modes, uses re.search
  -o                    omit inputs matching regex instead
  -b                    only match regex against basename of input (for input
                        modes: file, path, abspath)
  --max-chars n         omits any command line exceeding n characters, no
                        limit by default
  --sh, --shell         executes commands through the shell (subprocess
                        shell=True) (no effect on Windows)
  --py, --pyex          executes commands as python code using exec()
  --pyev                evaluates commands as python expressions using eval()
  --import library      executes 'import <library>' for each library
  --im library, --importstar library
                        executes 'from <library> import *' for each library
  --pre "code"          runs exec(code) before execution
  --post "code"         runs exec(code) after execution
  -P P, --procs P       split into P chunks and execute each chunk in parallel
                        as a separate process and window with byobu or tmux
  -c c, --chunk c       runs chunk c of P (0 <= c < P) (without multiplexer)
  --no-mux              do not use a multiplexer for multiple processes
  -i, --interactive     prompt the user before executing each command, only
                        proceeds if response starts with 'y' or 'Y'
  -n, --dry-run         prints commands without executing them
  -v, --verbose         prints commands before executing them
```
## Examples
```bash
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
```
