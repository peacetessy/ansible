from modules.connectivity_checker import check_connectivity
from modules.ansible_manager import execute_full_process 
from prompt_toolkit import prompt
from prompt_toolkit.completion import PathCompleter
from colorama import Fore, Style, init 
import os
from modules.config_validator import (
    validate_switches_config,
    validate_servers_config,
    validate_secrets_file_ssh,
    validate_secrets_file_tacacs_plus,
    validate_secrets_file_server,
    cross_validate_servers_and_secrets,
    cross_validate_switches_and_secrets
)

# Initialiser colorama
init(autoreset=True)


def choose_existing_file_cli(prompt_message="Enter the path to the file:"):
    """
    Prompt the user to enter the path to an existing file (with auto-completion).
    Keeps asking until a valid file is provided.
    """
    while True:
        path = prompt(
            prompt_message,
            completer=PathCompleter(only_directories=False, expanduser=True)
        ).strip()
        if not path or not os.path.isfile(path):
            print(Fore.RED + "\nFile does not exist. Please try again.")
            continue
        return path


def apply_configurations_to_switches():
    """
    Main function to apply configurations to switches and servers.
    """
    while True:
        # Step 1: Ask for the connection method
        print(Fore.YELLOW + "\n[INFO] Please select the connection method:\n")
        print("  [1] SSH\n")
        print("  [2] TACACS+\n")
        choice = input("Enter your choice >>> ").strip()

        if choice in ("1", "2"):
        
            switches_config_path = choose_existing_file_cli("\n[SWITCH] Enter the path to the SWITCHES configuration file: ")
            switches_secrets_path = choose_existing_file_cli("\n[SWITCH] Enter the path to the SWITCHES sensitive data file: ")
            servers_config_path = choose_existing_file_cli("\n[SERVER] Enter the path to the SERVERS configuration file: ")
            servers_secrets_path = choose_existing_file_cli("\n[SERVER] Enter the path to the SERVERS sensitive data file: ")

            # Validate each file with the correct function
            if not validate_switches_config(switches_config_path):
                print(Fore.RED + "\n[ERROR] Validation of the switches configuration file failed.")
                return
                

            if choice == "1":
                if not validate_secrets_file_ssh(switches_secrets_path):
                    print(Fore.RED + "\n[ERROR] Validation of the switches sensitive data file failed.")
                    return
            else:
                if not validate_secrets_file_tacacs_plus(switches_secrets_path):
                    print(Fore.RED + "\n[ERROR] Validation of the switches sensitive data file failed.")
                    return

            if not cross_validate_switches_and_secrets(switches_config_path, switches_secrets_path):
                print(Fore.RED + "\n[ERROR] Switch hostnames do not match between config and secrets. Please correct them.")
                return


            if not validate_servers_config(servers_config_path):
                print(Fore.RED + "\n[ERROR] Validation of the servers configuration file failed.")
                return

            if not validate_secrets_file_server(servers_secrets_path):
                print(Fore.RED + "\n[ERROR] Validation of the servers sensitive data file failed.")
                return

            if not cross_validate_servers_and_secrets(servers_config_path, servers_secrets_path):
                print(Fore.RED + "\n[ERROR] Server names do not match between config and secrets. Please correct them.")
                return

            print(Fore.GREEN + "\n[OK] Servers configuration and secrets files are valid and matching.")

            break

        else:
            print(Fore.RED + "\n[ERROR] Invalid choice. Please select 1 or 2.")
            return


    # Step 2: Test connectivity
    if not check_connectivity(switches_config_path, switches_secrets_path):
        print(Fore.RED + "\n[ERROR] Connectivity test failed.")
        return

    # Step 3. Apply configurations
    execute_full_process(switches_config_path, switches_secrets_path, servers_config_path, servers_secrets_path)
