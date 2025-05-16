import re
import getpass
import subprocess
import sys
import tempfile
import os
import yaml
import json
from colorama import Fore, init
from modules.report_generator import generate_report_pdf

# Initialize colorama
init(autoreset=True)

output_dir = "ansible_files"  # Directory where Ansible files will be generated

# Global variable to store the Vault password
inventory_path = os.path.join(output_dir, "inventory.ini")


def generate_ansible_files(config_path, secrets_path):
    """
    Generates Ansible inventory, host_vars, and group_vars files based on the configuration and secrets files.
    :param config_path: Path to the configuration file.
    :param secrets_path: Path to the secrets file.
    """
    try:
        # Load configuration and secrets files
        with open(config_path, 'r') as config_file, open(secrets_path, 'r') as secrets_file:
            config = yaml.safe_load(config_file)
            secrets = yaml.safe_load(secrets_file)

        # Create output directories
        os.makedirs(output_dir, exist_ok=True)
        os.makedirs(os.path.join(output_dir, "host_vars"), exist_ok=True)
        os.makedirs(os.path.join(output_dir, "group_vars"), exist_ok=True)

        # Generate inventory.ini
        with open(inventory_path, 'w') as inventory_file:
            inventory_file.write("[switches]\n")
            for switch in config.get("switches", []):
                inventory_file.write(f"{switch['hostname']} ansible_host={switch['management_ip']}\n")
	
        # Generate group_vars/data.yml
        group_vars_path = os.path.join(output_dir, "group_vars", "switches.yml")
        ise_servers = config.get("ise_servers", [])
        radius_secrets = secrets.get("radius_secrets", [])

        # Associate ISE servers with their keys
        for server in ise_servers:
            matching_secret = next(
                (secret for secret in radius_secrets if secret["server_name"] == server["name"]), None
            )
            server["key"] = matching_secret["secret_key"] if matching_secret else "default_key"

        group_vars = {
            "radius_user": config.get("radius_test_username"),
            "radius_password": secrets.get("radius_test_password"),
            "update_period": config.get("accounting_update_period"),
            "source_interface": config.get("source_interface"),
            "vlan_dead": config.get("radius_dead_vlan"),
            "aaa_group": config.get("aaa_group_name"),
            "ise_servers": ise_servers
        }

        # Write the group_vars/data.yml file with proper indentation
        with open(group_vars_path, 'w') as group_vars_file:
            yaml.dump(
                group_vars,
                group_vars_file,
                default_flow_style=False,
                sort_keys=False,
                indent=2
            )

        # Generate host_vars/<hostname>.yml for each switch
        for switch in config.get("switches", []):
            hostname = switch["hostname"]
            host_vars_path = os.path.join(output_dir, "host_vars", f"{hostname}.yml")

            # Check if per_switch_ssh_credentials is used
            per_switch_creds = next(
                (cred for cred in secrets.get("per_switch_credentials", []) if cred["hostname"] == hostname), None
            )

            if per_switch_creds:
                # Use per-switch credentials
                host_vars = {
                    "ansible_user": per_switch_creds["username"],
                    "ansible_password": per_switch_creds["ssh_password"],
                    "ansible_network_os": "cisco.ios.ios",
                    "ansible_connection": "network_cli",
                    "ansible_command_timeout": 600,
                    "ansible_become": True,
                    "ansible_become_method": "enable",
                    "ansible_become_password": per_switch_creds["enable_passsword"]
                }
            else:
                # Use global SSH credentials
                global_creds = secrets.get("global_ssh_credentials", {})
                host_vars = {
                    "ansible_user": global_creds.get("username"),
                    "ansible_password": global_creds.get("password"),
                    "ansible_network_os": "cisco.ios.ios",
                    "ansible_connection": "network_cli",
                    "ansible_command_timeout": 600,
                    "ansible_become": True,
                    "ansible_become_method": "enable",
                    "ansible_become_password": secrets.get("global_enable_password")
                }

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
                check=True
            )

        # Encrypt files in group_vars
        for file_name in os.listdir(group_vars_dir):
            file_path = os.path.join(group_vars_dir, file_name)
            
            subprocess.run(
                ["ansible-vault", "encrypt", file_path, "--vault-password-file", temp_path],
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
    except subprocess.CalledProcessError as e:
        return False

    return temp_path


def parse_ansible_output_raw(raw_output):
    """
    Parses raw Ansible output and structures it for reporting.
    :param raw_output: The raw output string from Ansible.
    :return: A structured dictionary with playbook results.
    """
    playbook_results = {}
    current_play = None
    current_task = None

    for line in raw_output.splitlines():
        try:
            # Detect the start of a play
            if line.startswith("PLAY ["):
                current_play = line.split("[")[1].split("]")[0]
                playbook_results[current_play] = {}

            # Detect the start of a task
            elif line.startswith("TASK ["):
                current_task = line.split("[")[1].split("]")[0]

            # Detect task results
            elif line.startswith("ok:") or line.startswith("changed:") or line.startswith("failed:"):
                parts = line.split(":", 2)
                status = parts[0].strip()
                host_info = parts[1].strip()

                # Remove brackets from host names like [ASW1]
                host = re.sub(r"^\[(.*?)\]$", r"\1", host_info)

                # Handle cases with (item=...)
                match = re.match(r"(.*?) => \(item=(.*?)\)", host_info)
                if match:
                    host = match.group(1).strip()
                    item = match.group(2).strip()
                    if host not in playbook_results[current_play]:
                        playbook_results[current_play][host] = {}
                    if item not in playbook_results[current_play][host]:
                        playbook_results[current_play][host][item] = []
                    message = parts[2].strip() if len(parts) > 2 else "No additional details."
                    playbook_results[current_play][host][item].append({
                        "task_name": current_task,
                        "status": status,
                        "message": message
                    })
                else:
                    # Handle regular cases without (item=...)
                    if host not in playbook_results[current_play]:
                        playbook_results[current_play][host] = []
                    message = parts[2].strip() if len(parts) > 2 else "No additional details."
                    playbook_results[current_play][host].append({
                        "task_name": current_task,
                        "status": status,
                        "message": message
                    })
        except Exception as e:
            print(f"[ERROR] Failed to parse line: {line}. Error: {e}")
            continue

    return playbook_results

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

    playbook_results = {}
	
    print(Fore.YELLOW + "\n[INFO] Applying configurations with Ansible...")
	
    for playbook in playbooks:
        playbook_path = os.path.join(playbook_dir, playbook)
        if not os.path.exists(playbook_path):
            print(Fore.RED + f"\n[ERROR] Playbook not found: {playbook_path}.")
            continue

        try:
            # First subprocess.run: Display output in the terminal without errors
            subprocess.run(
                [
                    "ansible-playbook",
                    "-i", inventory_path,
                    playbook_path
                ],
                stdout=sys.stdout,  # Display stdout in the terminal
                stderr=subprocess.DEVNULL,  # Suppress stderr
                check=True,
                text=True
            )

            # Second subprocess.run: Capture output for parsing
            completed_process = subprocess.run(
                [
                    "ansible-playbook",
                    "-i", inventory_path,
                    playbook_path
                ],
                stdout=subprocess.PIPE,  # Capture stdout
                stderr=subprocess.DEVNULL,  # Capture stderr
                check=True,
                text=True
            )

            # Parse raw output
            stdout_text = completed_process.stdout
            playbook_results[playbook] = parse_ansible_output_raw(stdout_text)

        except subprocess.CalledProcessError as e:
            # Handle errors and capture stderr
            print(Fore.RED + f"\n[ERROR] Failed to execute {playbook}: {e}")
            playbook_results[playbook] = {
                "error": str(e),
                "stderr": e.stderr.strip() if e.stderr else "",
                "stdout": e.stdout.strip() if e.stdout else ""
            }
            continue
    
    # Encrypt the files 
    temp_path = encrypt_host_vars(vault_password)
    
    # Clean up the temporary vault password file
    if temp_path and os.path.exists(temp_path):
    os.remove(temp_path)

    # Generate the PDF report BEFORE encryption
    generate_report_pdf(playbook_results)

    # Return the aggregated results for all playbooks
    return playbook_results


def execute_full_process(config_path, secrets_path):
    """
    Main function that calls all the functions in the correct order to execute the entire process.
    :param config_path: Path to the configuration file.
    :param secrets_path: Path to the secrets file.
    """
    # 1. Generate Ansible files
    generate_ansible_files(config_path, secrets_path)

    # 2. Apply configurations using Ansible
    playbook_results = apply_with_ansible()
    if not playbook_results:
        print(Fore.RED + "\n[ERROR] Failed to apply configurations with Ansible.")
        return
