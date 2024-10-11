# pyxargs

This started as a simple solution to the [encoding problem with xargs](https://en.wikipedia.org/wiki/Xargs#Encoding_problem). It is a partial and opinionated implementation of xargs with the goal of being easier to use for most use cases.  

It also contains additional features for AWK-like data processing, such as taking python code as arguments to be executed, or filtering with regular expressions. Some of these features take inspiration from [pyp](https://github.com/hauntsaninja/pyp), [Pyed Piper](https://github.com/thepyedpiper/pyp), and [Pyped](https://github.com/ksamuel/Pyped). A great comparison of them is provided by [pyp](https://github.com/hauntsaninja/pyp?tab=readme-ov-file#related-projects), which mainly differs from pyxargs in that pyxargs has more of an xargs-like interface and built in file tree traversal (replacing the need for find), but lacks the AST introspection and manipulation of pyp which infers more from the command without passing flags.  

You can install [pyxargs](https://github.com/elesiuta/pyxargs) from [PyPI](https://pypi.org/project/pyxargs/). Optionally depends on [duckdb](https://pypi.org/project/duckdb/) and [pandas](https://pypi.org/project/pandas/). Supports tab completion with [argcomplete](https://pypi.org/project/argcomplete/).  

## Command Line Interface
```
usage: pyxr [options] command [initial-arguments ...]
       pyxr -h | --help | --version

Build and execute command lines, python code, or mix from standard input or
file paths. The file input mode (default if stdin is not connected) builds
commands using filenames only and executes them in their respective
directories, this is useful when dealing with file paths containing multiple
character encodings. When executing python code, the following variables are
provided: i=index, j=remaining, n=total, x=input, s=split, d=dir,
a=all_inputs, out=previous_results, df=dataframe, js=json, db=duckdb

options:
  -h, --help            show this help message and exit
  --version             show program's version number and exit
  -m input-mode, --mode input-mode
                        options are:
                        (f)ile    = build commands from filenames and execute
                                    in each subdirectory respectively
                        (p)ath    = build commands from file paths relative
                                    to the current directory and execute in
                                    the current directory
                        (a)bspath = build commands from absolute file paths
                                    and execute in the current directory
                        (s)tdin   = build commands from standard input and
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
  -l, --lines           input items are separated by a newline character
                        instead of whitespace (for input mode: stdin)
  -d delim, --delimiter delim
                        input items are separated by the specified delimiter
                        instead of whitespace (for input mode: stdin)
  -s regex, --split regex
                        split each input item with re.split(regex, input)
                        before building command (after separating by
                        delimiter), use {0}, {1}, ... to specify placement
                        (implies --format), it is also stored as a list in the
                        variable s
  -g regex, --groups regex
                        use regex capturing groups on each input item with
                        re.search(regex, input).groups() before building
                        command (after separating by delimiter), use {0}, {1},
                        ... to specify placement (implies --format), it is
                        also stored as a tuple in the variable s
  --format              format command with input using str.format() instead
                        of appending or replacing via -I replace-str, use {0},
                        {1}, ... to specify placement, if the command is then
                        evaluated as an f-string (--fstring) escape using
                        double curly braces as {{expr}} to evaluate
                        expressions
  -I replace-str        replace occurrences of replace-str in command with
                        input, default: {}
  --resub pattern substitution replace-str
                        replace occurrences of replace-str in command with
                        re.sub(patten, substitution, input)
  -r regex, --filter regex
                        only build commands from inputs matching regex for
                        input mode stdin, and matching relative paths for all
                        other input modes, uses re.search
  -o, --omit            omit inputs matching regex instead
  -b, --basename        only match regex against basename of input (for input
                        modes: file, path, abspath)
  -f, --fstring         evaluates commands as python f-strings before
                        execution
  --df                  reads each input into a dataframe and stores it in
                        variable df, requires pandas
  --js                  reads each input as a json object and stores it in
                        variable js
  --max-chars n         omits any command line exceeding n characters, no
                        limit by default
  --sh, --shell         executes commands through the shell (subprocess
                        shell=True) (warning, shlex.quote is not guaranteed to
                        be correct on Windows)
  -x, --pyex            executes commands as python code using exec()
  -e, --pyev            evaluates commands as python expressions using eval()
                        then prints the result
  -p, --pypr            evaluates commands as python f-strings then prints
                        them (implies --fstring)
  -q, --sql             reads each input into variable db then runs commands
                        as SQL queries using duckdb.sql(), requires duckdb
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
  > pyxr echo

# instead of appending inputs, you can specify a location with {}
  > pyxr echo spam {} spam

# and like xargs, you can also specify the replace-str with -I
  > pyxr -I eggs echo spam eggs spam literal {}

# if stdin is connected, it will be used instead of filenames by default
  > echo bacon eggs | pyxr echo spam

# python code can be used in place of a command
  > pyxr --pyex "print(f'input file: {} executed in: {os.getcwd()}')"

# a shorter version of this command with --pypr (-p) and the magic variable d
  > pyxr -p "input file: {} executed in: {d}"

# python f-strings can also be used to format regular commands
  > pyxr -f echo "input file: {x} executed in: {d}"

# python code can also run before or after all the commands
  > pyxr --pre "n=0" --post "print(n,'files')" -x "n+=1"

# you can also evaluate and print python f-strings, the index i is provided
  > pyxr --pypr "number: {i}\tname: {}"

# provided variables:
# i = index, j = remaining, n = total, x = input, d = dir
# a = a list of all inputs, so a[i]=x
# out = a list of previous outputs, so out[i]=output (for -e, -p, -q)
# s = a list of columns if each x is a row, by default s=x.split()
# if the input mode is path or abspath, s=x.split(os.path.sep)
# if the input mode is file, s=os.path.splitext(x)
# if -s or -g is specified, then it is re.split() or re.search().groups()
# other variables are provided with flags: --df, --js, --sql
  > pyxr -p "i={i}\tj={j}\tn={n}\tx={x}\td={d}\ta[{i}]={a[i]}={a[-j]}\ts={s}"
  > pyxr -p "prev: {'START' if i<1 else a[i-1]}\t" \
               "current: {a[i]}\tnext: {'END' if j<1 else a[i+1]}"

# given variables are only in the global scope, so they won't overwrite locals
  > pyxr --pre "i=1;j=2;n=5;x=3;a=3;" -p "i={i} j={j} n={n} x={x} a={l}"

# you can also use dataframes as df with --df (requires pandas)
  > echo A,B,C\n1,2,3\n4,5,6 | pyxr -0 --df -p "{df}"

# or query sql databases as db with --sql (-q) (requires duckdb)
  > echo A,B,C\n1,2,3\n4,5,6 | pyxr -0 -q "SELECT * FROM db"
  > echo '{"a": 1,"b": 2}' | pyxr -0 -q "SELECT * FROM db"

# it can also read from databases, csv files, etc. (see duckdb extensions)
  > pyxr -t -r .sqlite -q "SELECT * FROM <table>"
  > pyxr -t -r .sqlite -f -q "SELECT * FROM {db[0]}"
  > pyxr -t -r .csv -q "SELECT * FROM db"
  > pyxr -t -q "SELECT * FROM db"
  > pyxr -t -q "SELECT * FROM '{}'"

# regular expressions can be used to filter and modify inputs
  > pyxr -r \.py --resub \.py .txt {new} echo {} -\> {new}

# you can test your command first with --dry-run (-n) or --interactive (-i)
  > pyxr -i echo filename: {}

# pyxargs can also run interactively in parallel by using byobu or tmux
  > pyxr -P 4 -i echo filename: {}

# you can use pyxargs to create a JSON mapping of /etc/hosts
  > cat /etc/hosts | pyxr -d \n --im json --pre "d={}" \
    --post "print(dumps(d))" -x "d['{}'.split()[0]] = '{}'.split()[1]"

# you can also do this with format strings and --split (-s) (uses regex)
  > cat /etc/hosts | pyxr -d \n -s "\s+" --im json --pre "d={}" \
    --post "print(dumps(d))" -x "d['{0}'] = '{1}'"

# use double curly braces to escape for f-strings since str.format() is first
  > cat /etc/hosts | pyxr -d \n -s "\s+" -p "{{i}}:{{'{1}'.upper()}}"

# this and the following examples will compare usage with find & xargs
  > find ./ -name "*" -type f -print0 | xargs -0 -I {} echo {}
  > find ./ -name "*" -type f -print0 | pyxr -0 -I {} echo {}

# pyxargs does not require '-I' to specify a replace-str (default: {})
  > find ./ -name "*" -type f -print0 | pyxr -0 echo {}

# and in the absence of a replace-str, exactly one input is appended
  > find ./ -name "*" -type f -print0 | pyxr -0 echo
  > find ./ -name "*" -type f -print0 | xargs -0 --max-args=1 echo
  > find ./ -name "*" -type f -print0 | xargs -0 --max-lines=1 echo

# pyxargs can use file paths as input without piping from another program
  > pyxr -m path echo ./{}

# and now for something completely different, python code for the command
  > pyxr -m path -x "print('./{}')"
```
