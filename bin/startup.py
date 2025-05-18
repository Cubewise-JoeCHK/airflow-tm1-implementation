import os
import subprocess
import logging
import sys

# Configure basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Define the Airflow home directory.
DEFAULT_AIRFLOW_HOME = os.path.expanduser("/home/cubewise-hk/airflow")
AIRFLOW_VERSION_COMMENT = "airflow=3.0.1" # User specified version context

# Path to the virtual environment's bin directory
VENV_BIN_PATH = "/home/cubewise-hk/airflow/bin"

def run_command(command, env=None):
    """
    Runs a shell command and logs its output.
    Exits script if command fails.
    """
    assert isinstance(command, list), "Command must be a list of arguments."
    assert len(command) > 0, "Command list cannot be empty."
    if env is not None:
        assert isinstance(env, dict), "Environment must be a dictionary."

    logging.info(f"Running command: {' '.join(command)}")
    try:
        # Using a loop with a fixed upper bound of 1 attempt for simplicity.
        for _i in range(1): # Fixed upper bound loop (1 iteration)
            process = subprocess.run(command, capture_output=True, text=True, check=False, env=env)
            
            if process.stdout:
                logging.info(f"STDOUT:\n{process.stdout}")
            if process.stderr:
                # Standalone mode often logs to stderr for normal operations too
                logging.info(f"STDERR:\n{process.stderr}") # Changed to INFO for standalone verbosity
            
            assert process.returncode is not None, "Process return code should not be None."
            # Standalone command might be long-running; this check is for immediate failures.
            if process.returncode != 0:
                logging.error(f"Command failed with exit code {process.returncode}: {' '.join(command)}")
                sys.exit(1) # Exit if command fails
            else:
                # For a long-running command like 'standalone', this means it launched.
                # If it exits immediately with 0, it might indicate an issue not caught.
                logging.info(f"Command {' '.join(command)} launched. It will run in the foreground.")
            break # Exit loop after one attempt
        
    except FileNotFoundError:
        logging.error(f"Error: The command '{command[0]}' was not found. Ensure it's in the PATH for the specified Python environment.")
        sys.exit(1)
    except Exception as e:
        logging.error(f"An unexpected error occurred while running command {' '.join(command)}: {e}")
        sys.exit(1)

def main():
    """
    Main function to set up environment and start Airflow in standalone mode.
    """
    airflow_home_env_var = os.environ.get("AIRFLOW_HOME")
    final_airflow_home = ""

    if not airflow_home_env_var:
        logging.info(f"AIRFLOW_HOME environment variable not set. Using default: {DEFAULT_AIRFLOW_HOME}")
        final_airflow_home = DEFAULT_AIRFLOW_HOME
    else:
        logging.info(f"AIRFLOW_HOME environment variable is set to: {airflow_home_env_var}")
        final_airflow_home = airflow_home_env_var

    assert final_airflow_home != "", "AIRFLOW_HOME path must be determined."

    # Ensure AIRFLOW_HOME directory exists
    if not os.path.isdir(final_airflow_home):
        try:
            os.makedirs(final_airflow_home, exist_ok=True)
            logging.info(f"Created AIRFLOW_HOME directory: {final_airflow_home}")
        except OSError as e:
            logging.error(f"Could not create AIRFLOW_HOME directory {final_airflow_home}: {e}")
            sys.exit(1)
    
    assert os.path.isdir(final_airflow_home), f"AIRFLOW_HOME directory {final_airflow_home} does not exist or is not a directory."

    # Prepare environment for the subprocess
    # Copy current environment to modify it for the subprocess
    subprocess_env = os.environ.copy()
    subprocess_env["AIRFLOW_HOME"] = final_airflow_home # Ensure AIRFLOW_HOME is set for the subprocess

    # Ensure the virtual environment's bin directory is in PATH for the subprocess
    # This makes 'airflow' (installed in that venv) findable
    original_path = subprocess_env.get("PATH", "")
    # Prepend the venv bin path to the existing PATH
    if VENV_BIN_PATH not in original_path.split(os.pathsep):
        modified_path = f"{VENV_BIN_PATH}{os.pathsep}{original_path}"
        subprocess_env["PATH"] = modified_path
        logging.info(f"Prepended VENV_BIN_PATH to PATH: {modified_path}")
    else:
        modified_path = original_path # Already there, no change needed
        logging.info(f"VENV_BIN_PATH already in PATH: {modified_path}")


    logging.info(f"Using AIRFLOW_HOME: {final_airflow_home}")
    logging.info(f"Using PATH for subprocess: {subprocess_env.get('PATH')}")
    assert VENV_BIN_PATH in subprocess_env.get("PATH", "").split(os.pathsep), "Venv bin path was not correctly added to PATH."
    
    # Check if airflow executable is found in the modified PATH
    airflow_executable_path = ""
    for path_dir in subprocess_env.get("PATH", "").split(os.pathsep):
        potential_path = os.path.join(path_dir, "airflow")
        if os.path.isfile(potential_path) and os.access(potential_path, os.X_OK):
            airflow_executable_path = potential_path
            break
    
    assert airflow_executable_path != "", f"Airflow executable not found in PATH: {subprocess_env.get('PATH')}"
    logging.info(f"Found airflow executable at: {airflow_executable_path}")

    # Start Airflow in standalone mode
    # This command initializes DB, starts webserver & scheduler in one process.
    # It runs in the foreground.
    logging.info("Starting Airflow in standalone mode...")
    run_command(["airflow", "standalone"], env=subprocess_env)

    # The script will remain here while 'airflow standalone' runs.
    # If 'airflow standalone' exits, this script will also exit.
    logging.info("Airflow standalone process has been initiated and is running in the foreground.")
    logging.info("To stop Airflow, terminate this script (e.g., Ctrl+C).")

if __name__ == "__main__":
    # This script is intended to be run directly.
    # It follows simple control flow and scoping rules.
    main()
