import os
import json
import yaml
from prompt_toolkit import prompt
from prompt_toolkit.completion import PathCompleter
from colorama import Fore, Style, init
# Initialize colorama
init(autoreset=True)


def choose_save_location_cli(default_name, extension):
    """
    Ask the user to enter a file path (with auto-completion).
    - If empty: use current directory + default_name
    - If a directory: use default_name in that directory
    """
    while True:
        path = prompt(
            f"\nEnter the full path and file name to save (default: {default_name}): ",
            completer=PathCompleter(only_directories=False, expanduser=True)
        ).strip()
        if not path:
            # Just Enter: default name in current directory
            path = os.path.join(os.getcwd(), default_name)
        elif os.path.isdir(path):
            # User entered a directory, use default_name in that directory
            path = os.path.join(path, default_name)
        # Ensure .yml extension
        if not path.lower().endswith(extension):
            path += extension
        return path

def generate_config_template(mode="switch"):
    """
    Generates configuration and sensitive data templates.
    mode: "switch" for switches, "server" for server parameters.
    Returns (yaml_template, secret_template)
    """

    if mode == "switch":
        yaml_template = """
# ===================================================================================================================================================================
#                                                                 Switch Configuration File
# ===================================================================================================================================================================

# This configuration file is used to define switch settings and AAA configurations.
# Follow the instructions in each section to fill out the required fields.
# ===================================================================================================================================================================
# Notes:
# - Fields left empty ("") must be filled with appropriate values.
# - Examples are provided in comments to guide you.
# ===================================================================================================================================================================
# -------------------------------------------------------------------------------------------------------------------------------------------------------------------
# PORT CONFIGURATION
# -------------------------------------------------------------------------------------------------------------------------------------------------------------------
# Indicate here the name of the network port (interface) that will be used by ALL switches as the source to communicate with the RADIUS server for authentication.
# This can be a physical port (like "GigabitEthernet1/0/48") or a virtual interface (like "Vlan10").
# If each switch uses a different interface, comment this field and uncomment "port" under each switch in the list below.
Port: ""            
# -------------------------------------------------------------------------------------------------------------------------------------------------------------------
# SWITCHES CONFIGURATION
# -------------------------------------------------------------------------------------------------------------------------------------------------------------------
# List the switches you want to configure below.
# For each switch, fill in:
# - A name to identify the switch (for example: "Switch_A")
# - The IP address used to connect to the switch (for example: "192.168.1.10")
# - (Optional) The network port (interface) if each switch uses a different one.
# If you have several switches, copy the block below and fill in the values for each one. 
   
switches:
  - hostname: ""              
    ip: ""                    
    #port: ""   
            
  - hostname: ""              
    ip: ""                    
    #port: ""                         
# -------------------------------------------------------------------------------------------------------------------------------------------------------------------
# AAA CONFIGURATION
# -------------------------------------------------------------------------------------------------------------------------------------------------------------------
# Enter here the name of the AAA group that will be used for authentication.
# This is usually a name that identifies your RADIUS or ISE server group.
# Example: "ISE_GROUP"
aaa_group_name: ""           

# -------------------------------------------------------------------------------------------------------------------------------------------------------------------
# RADIUS TEST USERNAME
# -------------------------------------------------------------------------------------------------------------------------------------------------------------------
# Enter here the username of a test user account that will be used by the SWITCH to check if the RADIUS authentication is working correctly.
# This user is only for testing the connection between the switch and the RADIUS server.
# Example: "radius-tester"
radius_test_username: ""      

# -------------------------------------------------------------------------------------------------------------------------------------------------------------------
# ACCOUNTING CONFIGURATION
# -------------------------------------------------------------------------------------------------------------------------------------------------------------------
# Specify here how often (in minutes) the SWITCH should send accounting updates to the RADIUS server.
# For example, if you set this to 10, the switch will send an update every 10 minutes.
# Example: 10
accounting_update_period: "" 

# -------------------------------------------------------------------------------------------------------------------------------------------------------------------
# VLAN CONFIGURATION
# -------------------------------------------------------------------------------------------------------------------------------------------------------------------
# Enter here the VLAN number to use on the SWITCH if the RADIUS server is unreachable or if authentication fails.
# Devices that cannot be authenticated will be placed in this VLAN, often called a "quarantine" or "guest" VLAN.
# This allows you to limit access for devices that are not properly authenticated.
# Example: 999
radius_dead_vlan: ""          
"""

        secret_template = """
# ===================================================================================================================================================================
#                                                       Sensitive Data Configuration File for Switches
# ===================================================================================================================================================================
# This file contains sensitive information required for switch configurations, such as passwords and secret keys.
# Store this file in a secure location and restrict access to authorized personnel only.
# ===================================================================================================================================================================
# Notes:
# - Do NOT share this file publicly or store it in an unsecured location (such as a shared folder or email).
# - All fields left empty ("") must be filled with the correct values before use.
# - For switch authentication, choose either SSH or TACACS+, not both.
# - If all switches use the same SSH credentials, fill in "global_ssh_credentials" below.
# - If each switch has its own SSH credentials, use "per_switch_credentials" below.
# ===================================================================================================================================================================
# -------------------------------------------------------------------------------------------------------------------------------------------------------------------
# SSH CREDENTIALS
# -------------------------------------------------------------------------------------------------------------------------------------------------------------------

# Global SSH credentials (use this section if all switches use the same login and password)
#global_ssh_credentials:
#  Username: ""              
#  Password: ""              

# Per-switch credentials (use this section if each switch has its own login and password)
#per_switch_credentials:
#  - hostname: ""           
#    username: ""            
#    ssh_password: ""        
#    enable_password:        
#  - hostname: ""            
#    username: ""            
#    ssh_password: ""       
#    enable_password:        

# Global enable password (if all switches use the same password to access advanced/administrator mode)
# For example: "GlobalEnablePassword"
#global_enable_password: "" 

# -------------------------------------------------------------------------------------------------------------------------------------------------------------------
# RADIUS TEST USER PASSWORD
# -------------------------------------------------------------------------------------------------------------------------------------------------------------------
# This password is used by the test user account to verify RADIUS authentication.
# Example: "TestUserPassword"
radius_test_password: ""    

# -------------------------------------------------------------------------------------------------------------------------------------------------------------------
# TACACS+ CREDENTIALS
# -------------------------------------------------------------------------------------------------------------------------------------------------------------------
# TACACS+ credentials (use this section if you use TACACS+ authentication for all switches)
#tacacs_credentials:
#  username: ""              
#  secret: ""                
    """

    elif mode == "server":
        yaml_template = """

# ===================================================================================================================================================================
#                                                               Server Parameters Configuration File
# ===================================================================================================================================================================
# This configuration file is used to define the details of your ISE/RADIUS servers and related parameters.
# Fill in each section carefully. 
# ===================================================================================================================================================================
# Notes:
# - Fields left empty ("") must be filled with appropriate values before use.
# - Examples are provided in comments to guide you.
# ===================================================================================================================================================================

# -------------------------------------------------------------------------------------------------------------------------------------------------------------------
# ISE/RADIUS SERVERS CONFIGURATION
# -------------------------------------------------------------------------------------------------------------------------------------------------------------------
# List here all the ISE or RADIUS servers that will be used for authentication.
# For each server, provide:
#   - A name to identify the server (for example: "ISE_Server_1")
#   - The IP address of the server (for example: "192.168.100.10")
# If you have several servers, copy the block below and fill in the values for each one.
ise_servers:
  - name: ""                 
    Ip: ""
                    
    """

        secret_template = """
# ===================================================================================================================================================================
#                                                           Sensitive Data Configuration File for Servers
# ===================================================================================================================================================================
# This file contains sensitive information required for server parameters (such as passwords and secret keys).
# Store this file in a secure location and restrict access to authorized personnel only.
# ===================================================================================================================================================================
# Notes:
# - Do NOT share this file publicly or store it in an unsecured location (such as a shared folder or email).
# - All fields left empty ("") must be filled with the correct values before use.
# ===================================================================================================================================================================
# -------------------------------------------------------------------------------------------------------------------------------------------------------------------
# RADIUS SERVER SECRETS
# -------------------------------------------------------------------------------------------------------------------------------------------------------------------
# This section contains the secret keys used by RADIUS servers for secure communication.
# For each server, provide its name and the corresponding secret key.
# To add more RADIUS servers, copy the lines above and change the values.
ise_servers_secrets:
  - server_name: ""          
    secret_key: ""            
    """

    else:
        yaml_template = ""
        secret_template = ""

    return yaml_template, secret_template

def generate_config_files():
    """
    Generates four configuration files:
    1. YAML configuration file for switches
    2. Sensitive data file for switches
    3. YAML configuration file for server parameters
    4. Sensitive data file for server parameters
    """

    yaml_switches, secret_switches = generate_config_template(mode="switch")
    yaml_servers, secret_servers = generate_config_template(mode="server")

    print(Fore.YELLOW + "\n[INFO] Four files will be generated:")
    print("\n1. Two files for SWITCHES: one for general settings and another for sensitive information.")
    print("\n2. Two files for SERVERS: one for general settings and another for sensitive information.")

    # SWITCHES
    path_switches = choose_save_location_cli("switches_config.yml", ".yml")
    if path_switches:
        with open(path_switches, "w", encoding="utf-8") as f:
            f.write(yaml_switches)
        print(Fore.GREEN + f"\nSwitches configuration saved at: {path_switches}")

        # Sensitive file: same folder, _secrets suffix
        base, ext = os.path.splitext(path_switches)
        path_switches_secrets = f"{base}_secrets{ext}"
        with open(path_switches_secrets, "w", encoding="utf-8") as f:
            f.write(secret_switches)
        print(Fore.GREEN + f"\nSwitches sensitive data saved at: {path_switches_secrets}")

    # SERVERS
    path_servers = choose_save_location_cli("servers_config.yml", ".yml")
    if path_servers:
        with open(path_servers, "w", encoding="utf-8") as f:
            f.write(yaml_servers)
        print(Fore.GREEN + f"\nServers configuration saved at: {path_servers}")

        # Sensitive file: same folder, _secrets suffix
        base, ext = os.path.splitext(path_servers)
        path_servers_secrets = f"{base}_secrets{ext}"
        with open(path_servers_secrets, "w", encoding="utf-8") as f:
            f.write(secret_servers)
        print(Fore.GREEN + f"\nServers sensitive data saved at: {path_servers_secrets}")
