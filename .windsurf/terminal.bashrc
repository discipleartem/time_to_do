# Custom bash profile for Windsurf terminal
# Automatically activates virtual environment for Time to DO project

# Check if we're in the project directory
if [[ "$PWD" == "/home/tomas/WORK/task_to_do"* ]]; then
    # Check if virtual environment exists
    if [ -d "/home/tomas/WORK/task_to_do/.venv" ]; then
        # Activate virtual environment
        source "/home/tomas/WORK/task_to_do/.venv/bin/activate"

        # Update prompt to show virtual environment
        export PS1="(.venv) $PS1"

        # Set PYTHONPATH
        export PYTHONPATH="/home/tomas/WORK/task_to_do:$PYTHONPATH"
    fi
fi

# Useful aliases for the project
alias dev='make dev'
alias test='make test'
alias lint='make lint'
alias format='make format'
alias install='make install'
