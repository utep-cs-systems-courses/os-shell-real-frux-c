import re
import os
import sys

# Function to print prompt string
def print_prompt():
    prompt = os.getenv('PS1', '$ ')
    sys.stdout.write(prompt)
    sys.stdout.flush()

def find_executable(command):
    paths = os.getenv('PATH').split(':')
    for path in paths:
        cmd_path = os.path.join(path, command)
        if os.path.isfile(cmd_path) and os.access(cmd_path, os.X_OK):
            return cmd_path
    return None

def execute(command):
    cmd_path = find_executable(command)
    if cmd_path:
        os.execv(cmd_path, [command])
    else:
        print(f'Command not found: {command}')

def parse_command(command):
    pattern = re.compile(r'\||<|>', re.IGNORECASE)
    operators = pattern.findall(command)
    execs = list(map(str.strip,pattern.split(command)))
    return execs, operators

def run_command(command):
    executables, operators = parse_command(command)
    if len(operators) == 0:
        pid = os.fork()
        if pid == 0:
            execute(executables[0])
        else:
            os.waitpid(pid, 0)
            return
    prev_stdin = sys.stdin.fileno()
    prev_stdout = sys.stdout.fileno()
    for i, operator in enumerate(operators):
        if operator == '|':
            fd = os.pipe()
            pid = os.fork()
            if pid == 0:
                os.dup2(fd[1], sys.stdout.fileno())
                os.close(fd[0])
                os.close(fd[1])
                execute(executables[i])
            else:
                os.dup2(fd[0], sys.stdin.fileno())
                os.close(fd[0])
                os.close(fd[1])
                execute(executables[i+1])
        elif operator == '<':
            fd = os.open(executables[i+1], os.O_RDONLY)
            os.dup2(fd, sys.stdin.fileno())
            os.close(fd)
            pid = os.fork()
            if pid == 0:
                execute(executables[i])
            else:
                os.waitpid(pid, 0)
        elif operator == '>':
            fd = os.open(executables[i+1], os.O_WRONLY | os.O_CREAT | os.O_TRUNC)
            os.dup2(fd, sys.stdout.fileno())
            os.close(fd)
            pid = os.fork()
            if pid == 0:
                execute(executables[i])
            else:
                os.waitpid(pid, 0)
        else:
            pid = os.fork()
            if pid == 0:
                execute(executables[i])
            else:
                os.waitpid(pid, 0)
    sys.stdin.flush()
    sys.stdout.flush()
    os.dup2(prev_stdin, sys.stdin.fileno())
    os.dup2(prev_stdout, sys.stdout.fileno())

def main():
    # Main shell loop
    while True:
        print_prompt()
        user_input = sys.stdin.readline().rstrip('\n')  # Read user input
        # Parse input
        if user_input == 'exit':
            break
        run_command(user_input)

if __name__ == '__main__':
    main()