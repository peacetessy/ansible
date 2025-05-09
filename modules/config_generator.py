import os
import json
import base64
import getpass
#from cryptography.fernet import Fernet
from tkinter import filedialog, Tk
from colorama import Fore, Style, init
# Initialize colorama
init(autoreset=True)



def choose_save_location():
    root = Tk()
    root.withdraw()  # Masquer la fenêtre principale
    root.attributes("-topmost", True)  # S'assurer que la fenêtre de dialogue apparaît devant
    file_path = filedialog.asksaveasfilename(
        title="Save As",
        defaultextension=".yml",
        filetypes=[("YAML files", "*.yml")]
    )
    root.destroy()
    return file_path


def generate_config_template():

    yaml_template = """
    # ================================================================================
    # Switch Configuration File
    # ================================================================================
    # This configuration file is used to define switch settings and AAA configurations.
    # Follow the instructions in each section to fill out the required fields.
    # If you need to add more switches or servers, copy and paste the relevant block.
    # ================================================================================
    # Notes:
    # - Fields left empty ("") must be filled with appropriate values.
    # - Examples are provided in comments to guide you.
    # ================================================================================

    # ------------------------------------------------------------------------------
    # SWITCHES CONFIGURATION
    # ------------------------------------------------------------------------------
    # Define the list of switches to configure.
    # Each switch must have:
    # - A unique hostname (e.g., "Switch_A").
    # - A management IP address (e.g., "192.168.1.10").
    # To add more switches, copy and paste the block below and modify the values.
    # ------------------------------------------------------------------------------
    switches:
      - hostname: ""              # Example: "Switch_A"
        management_ip: ""         # Example: "192.168.1.10"

      - hostname: ""              # Example: "Switch_B"
        management_ip: ""         # Example: "192.168.1.11"

    # ------------------------------------------------------------------------------
    # AAA CONFIGURATION
    # ------------------------------------------------------------------------------
    # Define the AAA server group name used for RADIUS authentication.
    # ------------------------------------------------------------------------------
    aaa_group_name: ""            # Example: "ISE_GROUP"

    # ------------------------------------------------------------------------------
    # ISE/RADIUS SERVERS CONFIGURATION
    # ------------------------------------------------------------------------------
    # Define the list of ISE or RADIUS servers used for authentication.
    # Each server must have:
    # - A unique name (e.g., "ISE_Server_1").
    # - An IP address (e.g., "192.168.100.10").
    # To add more servers, copy and paste the block below and modify the values.
    # ------------------------------------------------------------------------------
    ise_servers:
      - name: ""                  # Example: "ISE_Server_1"
        ip: ""                    # Example: "192.168.100.10"

    # ------------------------------------------------------------------------------
    # RADIUS TEST USERNAME
    # ------------------------------------------------------------------------------
    # Define the username used for testing RADIUS authentication.
    # This is typically a test account configured on the RADIUS server.
    # ------------------------------------------------------------------------------
    radius_test_username: ""      # Example: "radius-tester"

    # ------------------------------------------------------------------------------
    # ACCOUNTING CONFIGURATION
    # ------------------------------------------------------------------------------
    # Define the frequency of RADIUS accounting updates (in minutes).
    # ------------------------------------------------------------------------------
    accounting_update_period: ""  # Example: 10

    # ------------------------------------------------------------------------------
    # SOURCE INTERFACE CONFIGURATION
    # ------------------------------------------------------------------------------
    # Define the interface used as the source for RADIUS and SNMP traffic.
    # Specify the interface name (e.g., "GigabitEthernet1/0/48").
    # ------------------------------------------------------------------------------
    source_interface: ""          # Example: "GigabitEthernet1/0/48"

    # ------------------------------------------------------------------------------
    # VLAN CONFIGURATION
    # ------------------------------------------------------------------------------
    # Define the VLAN IDs for RADIUS dead and alive states.
    # - `radius_dead_vlan`: VLAN ID to assign when the RADIUS server is not reachable.
    # - `radius_alive_vlan`: VLAN ID to assign when the RADIUS server becomes reachable again.
    # ------------------------------------------------------------------------------
    radius_dead_vlan: ""          # Example: 999
    radius_alive_vlan: ""         # Example: 10
    """

    secret_template = """
    # ================================================================================
    # Sensitive Data Configuration File
    # ================================================================================
    # This file contains sensitive information required for switch and server configurations.
    # Ensure this file is stored securely and access is restricted to authorized personnel only.
    # ================================================================================
    # Notes:
    # - Do not share this file publicly or store it in an unsecured location.
    # - Fields left empty ("") must be filled with appropriate values.
    # - Choose either SSH or TACACS+ for switch authentication, not both.
    # - If all switches share the same SSH credentials, use "global_ssh_credentials".
    # - If switches have individual SSH credentials, use "per_switch_ssh_credentials".
    # ================================================================================

    # ------------------------------------------------------------------------------
    # SWITCH AUTHENTICATION CREDENTIALS
    # ------------------------------------------------------------------------------
    # Define the credentials used to connect to the switches.
    # Choose one of the following methods:
    # - SSH: Uncomment and fill either "global_ssh_credentials" or "per_switch_ssh_credentials".
    # - TACACS+: Uncomment and fill the "tacacs_credentials" block.
    # ------------------------------------------------------------------------------
 
    # Global SSH credentials (shared by all switches):
    # Uncomment this block if all switches use the same SSH credentials.
    #global_ssh_credentials:
    #  username: ""              # Example: "admin"
    #  password: ""              # Example: "GlobalSecurePassword"

    # Global enable password (used for all switches if the same):
    #global_enable_password: ""         # Example: "GlobalEnablePassword"

    # Per-switch credentials (specific to each switch):
    # Uncomment this block if each switch has its own credentials.
    #per_switch_credentials:
    #  - hostname: ""            # Example: "Switch_A"
    #    username: ""            # Example: "admin"
    #    ssh_password: ""        # Example: "PasswordA"
    #    enable_password:        # Example: "EnablePasswordA"
    #  - hostname: ""            # Example: "Switch_B"
    #    username: ""            # Example: "admin"
    #    ssh_password: ""        # Example: "PasswordB"
    #    enable_password:        # Example: "EnablePasswordB"

    # TACACS+ credentials:
    # Uncomment this block if switches use TACACS+ for authentication.
    #tacacs_credentials:
    #  username: ""              # Example: "tacacs-admin"
    #  password: ""              # Example: "SuperSecureTacacsPassword"

    # ------------------------------------------------------------------------------
    # RADIUS TEST USER PASSWORD
    # ------------------------------------------------------------------------------
    # Define the password for the RADIUS test user.
    # The username is already defined in the main configuration file.
    # ------------------------------------------------------------------------------
    radius_test_password: ""      # Example: "TestUserPassword"

    # ------------------------------------------------------------------------------
    # RADIUS SERVER SECRETS
    # ------------------------------------------------------------------------------
    # Define the shared secrets used for RADIUS server authentication.
    # ------------------------------------------------------------------------------
    radius_secrets:
    - server_name: ""           # Example: "ISE_Server_1"
      secret_key: ""                # Example: "SuperSecretRadiusKey"
    """   
    return yaml_template, secret_template

"""
def encrypt_sensitive_data(data, password):
    key = base64.urlsafe_b64encode(password.ljust(32)[:32].encode())
    f = Fernet(key)
    encrypted = f.encrypt(data.encode())
    return encrypted


def generate_config_files():
    print("\n[INFO] Generating default configuration templates...")
    
    # Generate the YAML and secret templates
    yaml_template, secret_template = generate_config_template()
    
    print("\n[INFO] Two files will be generated:")
    print("1. A YAML configuration file for switch and AAA settings.")
    print("2. A plain text file for sensitive data (e.g., passwords, secrets).")
    print("\n[WARNING] The sensitive data file will not be encrypted. Ensure it is stored securely.")

    # Ask the user where to save the files
    print("\n[INFO] Please choose where to save the configuration files...")
    config_path = choose_save_location()

    if config_path:
        # Save the YAML configuration file
        yaml_path = config_path
        with open(yaml_path, 'w') as yaml_file:
            yaml_file.write(yaml_template)
        print(f"[OK] YAML configuration file saved at: {yaml_path}")

        # Save the sensitive data file
        secret_path = config_path.replace(".yaml", "_secrets.txt")
        with open(secret_path, 'w') as secret_file:
            secret_file.write(secret_template)
        print(f"[OK] Sensitive data file saved at: {secret_path}")
    else:
        print("[WARN] File saving cancelled.")

"""

def generate_config_files():
    """
    Generates two configuration files:
    1. A YAML configuration file for switch and AAA settings.
    2. A YAML file for sensitive data (e.g., passwords, secrets).
    """

    # Generate the YAML and secret templates
    yaml_template, secret_template = generate_config_template()

    print(Fore.YELLOW + "\n[INFO] Two files will be generated:\n" + "1. A YAML configuration file for switch and AAA settings.\n" +
      "2. A YAML file for sensitive data (e.g., passwords, secrets).")

    input("\nPress ENTER to choose where to save the configuration files...\n")
    config_path = choose_save_location()

    if config_path:
        # Save the YAML configuration file
        yaml_path = config_path
        with open(yaml_path, 'w') as yaml_file:
            yaml_file.write(yaml_template)
        print(Fore.GREEN + f"\n[OK] YAML configuration file saved at: {yaml_path}")

        # Save the sensitive data file
        secret_path = config_path.replace(".yml", "_secrets.yml")
        with open(secret_path, 'w') as secret_file:
            secret_file.write(secret_template)
        print(Fore.GREEN + f"\n[OK] Sensitive data file saved at: {secret_path}")

    else:
        print(Fore.YELLOW + "\n[WARN] File saving cancelled.")
