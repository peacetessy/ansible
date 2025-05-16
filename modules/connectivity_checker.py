import yaml
import paramiko
import socket
from colorama import Fore, Style, init

# Initialize colorama
init(autoreset=True)

def check_connectivity(config_path, secrets_path):
    """
    Tests connectivity to switches and servers based on the configuration and secrets files.
    :param config_path: Path to the configuration file.
    :param secrets_path: Path to the secrets file.
    :return: True if all connectivity tests pass, False otherwise.
    """
    try:
        # Load configuration and secrets files
        with open(config_path, 'r') as config_file, open(secrets_path, 'r') as secrets_file:
            config = yaml.safe_load(config_file)
            secrets = yaml.safe_load(secrets_file)

        # Determine the authentication method
        if "global_ssh_credentials" in secrets:
            return test_ssh_connectivity(config, secrets["global_ssh_credentials"])
        elif "per_switch_ssh_credentials" in secrets:
            return test_ssh_connectivity(config, secrets["per_switch_ssh_credentials"], per_switch=True)
        elif "tacacs_credentials" in secrets:
            return test_tacacs_connectivity(secrets["tacacs_credentials"])
        else:
            print(Fore.RED + "\n[ERROR] No valid authentication method found in the secrets file.")
            return False

    except Exception as e:
        print(Fore.RED + f"\n[ERROR] An unexpected error occurred during connectivity testing: {e}")
        return False

def test_ssh_connectivity(config, ssh_credentials, per_switch=False):
    """
    Tests SSH connectivity to switches.
    :param config: Configuration data containing switches.
    :param ssh_credentials: SSH credentials (global or per-switch).
    :param per_switch: Boolean indicating if per-switch credentials are used.
    :return: True if all connections are successful, False otherwise.
    """
    errors = []

    # Determine the list of switches and credentials
    if per_switch:
        switches = ssh_credentials
        config_switches = {switch["hostname"]: switch["management_ip"] for switch in config.get("switches", [])}
    else:
        switches = config.get("switches", [])
        username = ssh_credentials.get("username")
        password = ssh_credentials.get("password")

    # Test SSH connectivity to each switch
    for switch in switches:
        hostname = switch.get("hostname")
        management_ip = config_switches.get(hostname) if per_switch else switch.get("management_ip")
        username = switch.get("username") if per_switch else username
        password = switch.get("password") if per_switch else password

        try:
            print(Fore.YELLOW + f"\n[INFO] Testing SSH connectivity to {hostname} ({management_ip})...")
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(management_ip, username=username, password=password, timeout=7)
            print(Fore.GREEN + f"\n[OK] Successfully connected to {hostname} ({management_ip}).")
            ssh.close()
        except Exception as e:
            errors.append(f"\n[ERROR] Failed to connect to {hostname} ({management_ip}): {e}")

    # Display errors if any
    if errors:
        for error in errors:
            print(Fore.RED + error)
        return False

    return True

def test_tacacs_connectivity(tacacs_credentials):
    """
    Tests connectivity to TACACS+ servers.
    :param tacacs_credentials: TACACS+ credentials containing username, password, and servers.
    :return: True if all connections are successful, False otherwise.
    """
    errors = []

    tacacs_servers = tacacs_credentials.get("tacacs_servers", [])

    # Test connectivity to each TACACS+ server
    for server in tacacs_servers:
        server_ip = server.get("ip")
        server_port = server.get("port", 49)  # Default TACACS+ port is 49

        try:
            print(Fore.YELLOW + f"\n[INFO] Testing connectivity to TACACS+ server {server_ip}:{server_port}...")
            with socket.create_connection((server_ip, server_port), timeout=10):
                print(Fore.GREEN + f"\n[OK] Successfully connected to TACACS+ server {server_ip}:{server_port}.")
        except (socket.timeout, socket.error) as e:
            errors.append(f"\n[ERROR] Failed to connect to TACACS+ server {server_ip}:{server_port}: {e}")

    # Display errors if any
    if errors:
        for error in errors:
            print(Fore.RED + error)
        return False

    return True