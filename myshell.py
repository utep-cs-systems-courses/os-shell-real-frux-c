import os
import sys
import re

# Function to print prompt string
def print_prompt():
    prompt = os.getenv('PS1', '$ ')
    sys.stdout.write(prompt)
    sys.stdout.flush()

# Function to search for command in PATH
def find_command(command):
    paths = os.getenv('PATH').split(':')
    for path in paths:
        cmd_path = os.path.join(path, command)
        if os.path.isfile(cmd_path) and os.access(cmd_path, os.X_OK):
            return cmd_path
    return None

# Function to execute a command
def execute_command(command):
    # Check for input/output redirection
    input_file = None
    output_file = None
    
    if '<' in command:
        command, input_file = re.split('<',command, 1)
        input_file = input_file.strip()
    
    if '>' in command:
        command, output_file = re.split('>',command, 1)
        output_file = output_file.strip()
    
    # Split the command by pipes
    commands = re.split(r'\|',command)
    num_commands = len(commands)
    
    # Create pipes
    pipes = [os.pipe() for _ in range(num_commands - 1)]
    
    # Fork processes for each command
    for i, cmd in enumerate(commands):
        # Remove leading/trailing whitespaces
        cmd = cmd.strip()
        
        # Create a child process
        pid = os.fork()
        
        if pid == 0:  # Child process
            # Connect pipes (except for the last command)
            if i < num_commands - 1:
                os.dup2(pipes[i][1], sys.stdout.fileno())  # Connect stdout to the write end of the pipe
            
            # Input redirection
            if input_file and i == 0:
                sys.stdin.close()
                sys.stdin = os.open(input_file, os.O_RDONLY)
            
            # Output redirection
            if output_file and i == num_commands - 1:
                sys.stdout.close()
                sys.stdout = os.open(output_file, os.O_WRONLY | os.O_CREAT | os.O_TRUNC)
            
            # Close unused pipe ends
            for p in pipes:
                os.close(p[0])
                os.close(p[1])
            
            # Split command and arguments
            args = cmd.split()
            command_path = args[0]
            
            # Check if command path is specified
            if os.path.isfile(command_path) and os.access(command_path, os.X_OK):
                # Execute the command
                try:
                    os.execve(command_path, args, os.environ)
                except FileNotFoundError:
                    print(f"{command_path}: command not found", file=sys.stderr)
                    sys.exit(1)
            else:
                # Search for command in PATH
                cmd_path = find_command(command_path)
                if cmd_path:
                    # Execute the command
                    try:
                        os.execve(cmd_path, args, os.environ)
                    except FileNotFoundError:
                        print(f"{command_path}: command not found", file=sys.stderr)
                        sys.exit(1)
                else:
                    print(f"{command_path}: command not found", file=sys.stderr)
                    sys.exit(1)
        
        elif pid > 0:  # Parent process
            # Connect pipes (except for the first command)
            if i > 0:
                os.dup2(pipes[i-1][0], sys.stdin.fileno())  # Connect stdin to the read end of the pipe
        
        else:  # Error
            sys.stderr.write("Error forking process\n")
            sys.exit(1)
    
    # Close all pipe ends in the parent process
    for p in pipes:
        os.close(p[0])
        os.close(p[1])
    
    # Wait for all child processes to finish
    for _ in range(num_commands):
        os.waitid(os.P_ALL, 0, os.WEXITED)

# Main shell loop
while True:
    print_prompt()
    user_input = sys.stdin.readline().rstrip('\n')  # Read user input
    # Parse input
    if user_input == 'exit':
        break
    execute_command(user_input)
