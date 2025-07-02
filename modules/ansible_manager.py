import re
import getpass
import subprocess
import sys
import tempfile
import os
import yaml
import json
from colorama import Fore, init
from modules.report_generator import generate_pdf_report

# Initialize colorama
init(autoreset=True)

output_dir = "ansible_files"  # Directory where Ansible files will be generated

# Global variable to store the Vault password
inventory_path = os.path.join(output_dir, "inventory.ini")


def generate_ansible_files(switches_config_path, switches_secrets_path, servers_config_path, servers_secrets_path):
    """
    Generates Ansible inventory, host_vars, and group_vars files based on the configuration and secrets files.
    :param config_path: Path to the configuration file.
    :param secrets_path: Path to the secrets file.
    """
    try:
        # Load all configs and secrets
        with open(switches_config_path, 'r') as f:
            switches_config = yaml.safe_load(f)

        with open(switches_secrets_path, 'r') as f:
            switches_secrets = yaml.safe_load(f)

        with open(servers_config_path, 'r') as f:
            servers_config = yaml.safe_load(f)

        with open(servers_secrets_path, 'r') as f:
            servers_secrets = yaml.safe_load(f)

        # Create output directories
        os.makedirs(output_dir, exist_ok=True)
        os.makedirs(os.path.join(output_dir, "host_vars"), exist_ok=True)
        os.makedirs(os.path.join(output_dir, "group_vars"), exist_ok=True)

        # Generate inventory.ini
        with open(inventory_path, 'w') as inventory_file:
            inventory_file.write("[switches]\n")
            for switch in switches_config.get("switches", []):
                inventory_file.write(f"{switch['hostname']} ansible_host={switch.get('ip')}\n")

        # Prepare ISE servers and secrets
        ise_servers = servers_config.get("ise_servers", [])
        ise_servers_secrets = servers_secrets.get("ise_servers_secrets", []) 
        # Associate ISE servers with their keys
        for server in ise_servers:
            matching_secret = next(
                (secret for secret in ise_servers_secrets if secret.get("server_name") == server.get("name")), None
            )
            server["key"] = matching_secret["secret_key"] if matching_secret else "default_key"
        
        # Determine if global Port is set
        global_source_interface = switches_config.get("Port")

        # Build group_vars
        group_vars = {
            "radius_user": switches_config.get("radius_test_username"),
            "radius_password": switches_secrets.get("radius_test_password"),
            "update_period": switches_config.get("accounting_update_period"),
            "vlan_dead": switches_config.get("radius_dead_vlan"),
            "aaa_group": switches_config.get("aaa_group_name"),
            "ise_servers": ise_servers
        }
        if global_source_interface:
            group_vars["source_interface"] = global_source_interface

        # Write the group_vars/switches.yml file
        group_vars_path = os.path.join(output_dir, "group_vars", "switches.yml")
        with open(group_vars_path, 'w') as group_vars_file:
            yaml.dump(
                group_vars,
                group_vars_file,
                default_flow_style=False,
                sort_keys=False,
                indent=2
            )

        # Generate host_vars/<hostname>.yml for each switch
        for switch in switches_config.get("switches", []):
            hostname = switch["hostname"]
            host_vars_path = os.path.join(output_dir, "host_vars", f"{hostname}.yml")

            # Check if per_switch_credentials is used
            per_switch_creds = next(
                (cred for cred in switches_secrets.get("per_switch_credentials", []) if cred.get("hostname") == hostname), None
            )

            if per_switch_creds:
                # Use per-switch credentials
                host_vars = {
                    "ansible_user": per_switch_creds.get("username"),
                    "ansible_password": per_switch_creds.get("ssh_password"),
                    "ansible_network_os": "cisco.ios.ios",
                    "ansible_connection": "network_cli",
                    "ansible_command_timeout": 1200,
                    "ansible_connect_timeout": 600,
                    "ansible_persistent_connect_timeout": 300,
                    "ansible_become": True,
                    "ansible_become_method": "enable",
                    "ansible_become_password": per_switch_creds.get("enable_password")
                }
            else:
                # Use global SSH credentials
                global_creds = switches_secrets.get("global_ssh_credentials", {})
                host_vars = {
                    "ansible_user": global_creds.get("Username"),
                    "ansible_password": global_creds.get("Password"),
                    "ansible_network_os": "cisco.ios.ios",
                    "ansible_connection": "network_cli",
                    "ansible_command_timeout": 1200,
                    "ansible_connect_timeout": 600,
                    "ansible_persistent_connect_timeout": 300,
                    "ansible_become": True,
                    "ansible_become_method": "enable",
                    "ansible_become_password": switches_secrets.get("global_enable_password")
                }

            # Add source_interface only if global Port is not set and switch has 'port'
            if not global_source_interface and switch.get("port"):
                host_vars["source_interface"] = switch["port"]

            # Write the host_vars/<hostname>.yml file
            with open(host_vars_path, 'w') as host_vars_file:
                yaml.dump(host_vars, host_vars_file, default_flow_style=False)

    except Exception as e:
        print(Fore.RED + f"\n[ERROR] Failed to generate Ansible files: {e}")

def validate_vault_password(password):
    """
    Validates the Ansible Vault password based on complexity requirements.
    :param password: The password to validate.
    :return: True if the password is valid, False otherwise.
    """
    if len(password) < 10:
        print(Fore.RED + "\n[ERROR] Password must be at least 10 characters long.")
        return False
    if not re.search(r"[A-Z]", password):
        print(Fore.RED + "\n[ERROR] Password must contain at least one uppercase letter.")
        return False
    if not re.search(r"[a-z]", password):
        print(Fore.RED + "\n[ERROR] Password must contain at least one lowercase letter.")
        return False
    if not re.search(r"[0-9]", password):
        print(Fore.RED + "\n[ERROR] Password must contain at least one digit.")
        return False
    if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
        print(Fore.RED + "\n[ERROR] Password must contain at least one special character.")
        return False
    return True


def encrypt_host_vars(vault_password):
    """
    Encrypts host_vars and group_vars files using the provided vault password.
    """
    host_vars_dir = os.path.join(output_dir, "host_vars")
    group_vars_dir = os.path.join(output_dir, "group_vars")

    if not os.path.exists(host_vars_dir) or not os.path.exists(group_vars_dir):
        return None

    # Create a temporary file containing the password
    with tempfile.NamedTemporaryFile(mode='w+', delete=False) as temp_file:
        temp_file.write(vault_password)
        temp_file.flush()
        temp_path = temp_file.name
    try:
        # Encrypt files in host_vars
        for file_name in os.listdir(host_vars_dir):
            file_path = os.path.join(host_vars_dir, file_name)
            subprocess.run(
                ["ansible-vault", "encrypt", file_path, "--vault-password-file", temp_path],
                check=True,
		stdout=subprocess.DEVNULL
            )

        # Encrypt files in group_vars
        for file_name in os.listdir(group_vars_dir):
            file_path = os.path.join(group_vars_dir, file_name)
            
            subprocess.run(
                ["ansible-vault", "encrypt", file_path, "--vault-password-file", temp_path],
                check=True,
                stdout=subprocess.DEVNULL
            )
    except subprocess.CalledProcessError as e:
        return False

    return temp_path

def apply_with_ansible():
    """
    Applies configurations using Ansible.
    Executes multiple playbooks, displays the output in the terminal, and parses the results.
    """
    playbook_dir = os.path.join(os.getcwd(), "playbook")
    playbooks = ["get_access_interfaces.yml", "configure_switches.yml"]

    if not os.path.exists(inventory_path):
        print(Fore.RED + "\n[ERROR] Inventory path not found.")
        return

    # Prompt and validate the Vault password BEFORE running playbooks
    while True:
        vault_password = getpass.getpass(Fore.YELLOW + "\n[INFO] Enter Ansible Vault password: ")
        if not validate_vault_password(vault_password):
            continue
        confirm_password = getpass.getpass(Fore.YELLOW + "\n[INFO] Confirm Ansible Vault password: ")
        if vault_password != confirm_password:
            print(Fore.RED + "\n[ERROR] Passwords do not match. Please try again.")
            continue
        break

	
    print(Fore.YELLOW + "\n[INFO] Applying configurations with Ansible...")

    #Create a temporary file for ansible output
    tmp_dir = tempfile.gettempdir()
    ansible_output_path = os.path.join(tmp_dir, "all_playbooks_output.txt")
    with open(ansible_output_path, "w", encoding="utf-8") as f:
        f.write("")

    for playbook in playbooks:
        playbook_path = os.path.join(playbook_dir, playbook)
        if not os.path.exists(playbook_path):
            print(Fore.RED + f"\n[ERROR] Playbook not found: {playbook_path}.")
            continue

        try:
            # Using tee via the shell to display and save raw output
            cmd = f"script -q -c 'ANSIBLE_FORCE_COLOR=1 ansible-playbook -f 1 -i {inventory_path} {playbook_path}' /dev/null | grep -v '\\[WARNING\\]' | tee -a {ansible_output_path}"

            completed_process = subprocess.run(
                cmd,
                shell=True,
                check=True,
                stderr=subprocess.PIPE
            )

        except subprocess.CalledProcessError as e:
            # Handle errors and capture stderr
            print(Fore.RED + f"\n[ERROR] Failed to execute {playbook}: {e}")
            continue

    # Encrypt the files
    temp_path = encrypt_host_vars(vault_password)

    # Clean up the temporary vault password file
    if temp_path and os.path.exists(temp_path):
        os.remove(temp_path)
	    
    # Generate the PDF report BEFORE encryption
    try:
        generate_pdf_report(ansible_output_path)
    except ImportError:
        print("Error: reportlab is not installed. Install it with:\npip install reportlab")
    except Exception as e:
        print(f"Error while generating the report: {e}")
        import traceback
        traceback.print_exc()

        

def execute_full_process(switches_config_path, switches_secrets_path, servers_config_path, servers_secrets_path):
    """
    Main function that calls all the functions in the correct order to execute the entire process.
    :param config_path: Path to the configuration file.
    :param secrets_path: Path to the secrets file.
    """
    # 1. Generate Ansible files
    generate_ansible_files(switches_config_path, switches_secrets_path, servers_config_path, servers_secrets_path)

    # 2. Apply configurations using Ansible
    apply_with_ansible()
    
