from modules.config_validator import validate_config_file,validate_secrets_file_ssh, validate_secrets_file_tacacs_plus, validate_switches_and_servers 
from modules.connectivity_checker import check_connectivity
from modules.ansible_manager import execute_full_process 
from tkinter import filedialog, Tk 
from colorama import Fore, Style, init 
import getpass 
import subprocess

# Initialize colorama
init(autoreset=True)

def choose_file():
    """
    Opens a file dialog to let the user select a file.

    """
    root = Tk()
    root.withdraw()  # Hide the main window
    root.attributes("-topmost", True)  # Ensure the dialog appears on top
    file_path = filedialog.askopenfilename(
        title="Open File",
        filetypes=[("YAML files", "*.yml"), ("All files", "*.*")]
    )
    root.destroy()
    return file_path



def apply_configurations_to_switches():
    """
    Main function to apply configurations to switches.
    """
    while True:
        # Step 1: Ask for the connection method
        print(Fore.YELLOW + "\n[INFO] Please select the connection method:")
        print("\n 1. SSH")
        print("\n 2. TACACS+")
        choice = input("\n Enter your choice >>>>>>>  ").strip()

        if choice == "1":
            # SSH Configuration
            input(Fore.YELLOW + "\n[INFO] Press ENTER to select the configuration file...")
            config_path = choose_file()
            if not config_path:
                print(Fore.RED + "\n[WARN] No configuration file selected. Returning to main menu.")
                return # Return to the main menu

            input(Fore.YELLOW + "\n[INFO] Press ENTER to select the sensitive data file...")
            secrets_path = choose_file()
            if not secrets_path:
                print(Fore.RED + "\n[WARN] No sensitive data file selected. Returning to main menu.")
                return  # Return to the main menu

            print(Fore.GREEN + f"\n[OK] Configuration file selected: {config_path}")
            print(Fore.GREEN + f"\n[OK] Sensitive data file selected: {secrets_path}")

            # Validate configuration and secrets files
            if not validate_config_file(config_path):
                print(Fore.RED + "\n[ERROR] Validation of the configuration file failed.")
                return # Return to the main menu

            if not validate_secrets_file_ssh(secrets_path):
                print(Fore.RED + "\n[ERROR] Validation of the sensitive data file failed.")
                return # Return to the main menu

            # Cross-validate switches and servers
            with open(config_path, 'r') as config_file, open(secrets_path, 'r') as secrets_file:
                import yaml
                config = yaml.safe_load(config_file)
                secrets = yaml.safe_load(secrets_file)

                if not validate_switches_and_servers(config, secrets):
                    print(Fore.RED + "\n[ERROR] Validation failed. Switches or servers do not match.")
                    return # Return to the main menu

            break

        elif choice == "2":
            # TACACS+ Configuration
            input(Fore.YELLOW + "\n[INFO] Press ENTER to select the configuration file...")
            config_path = choose_file()
            if not config_path:
                print(Fore.RED + "\n[WARN] No configuration file selected. Returning to main menu.")
                return  # Return to the main menu

            input(Fore.YELLOW + "\n[INFO] Press ENTER to select the sensitive data file...")
            secrets_path = choose_file()
            if not secrets_path:
                print(Fore.RED + "\n[WARN] No sensitive data file selected. Returning to main menu.")
                return

            print(Fore.GREEN + f"\n[OK] Configuration file selected: {config_path}")
            print(Fore.GREEN + f"\n[OK] Sensitive data file selected: {secrets_path}")

            # Validate configuration and secrets files
            if not validate_config_file(config_path):
                print(Fore.RED + "\n[ERROR] Validation of the configuration file failed.")
                return # Return to the main menu

            if not validate_secrets_file_tacacs_plus(secrets_path):
                print(Fore.RED + "\n[ERROR] Validation of the sensitive data file failed.")
                return

            # Cross-validate switches and servers
            with open(config_path, 'r') as config_file, open(secrets_path, 'r') as secrets_file:
                import yaml
                config = yaml.safe_load(config_file)
                secrets = yaml.safe_load(secrets_file)

                if not validate_switches_and_servers(config, secrets):
                    print(Fore.RED + "\n[ERROR] Validation failed. Switches or servers do not match.")
                    return # Return to the main menu

            break

        else:
            print(Fore.RED + "\n[ERROR] Invalid choice. Please select 1 or 2.")
            return

    # Step 2: Test connectivity
    if not check_connectivity(config_path, secrets_path):
        print(Fore.RED + "\n[ERROR] Connectivity test failed.")
        return

    # Step 3. Apply configurations
    execute_full_process(config_path, secrets_path)    
