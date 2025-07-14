import yaml
import ipaddress
from colorama import Fore, Style, init

init(autoreset=True)

def is_valid_ip(ip_str):
    try:
        ip = ipaddress.IPv4Address(ip_str)
        if ip.is_loopback or ip.is_multicast or ip.is_reserved:
            return False
        if ip_str.endswith('.0') or ip_str.endswith('.255'):
            return False
        return True
    except Exception:
        return False

def is_valid_vlan(vlan):
    try:
        vlan = int(vlan)
        return 1 <= vlan <= 4094
    except Exception:
        return False

def is_valid_update_period(value):
    try:
        period = int(value)
        return period > 0
    except Exception:
        return False

def validate_switches_config(switches_config_path):
    """
    Validates the switches configuration file.
    - Either a global 'Port' must be set, or each switch must have a 'port' field.
    """
    errors = []
    try:
        with open(switches_config_path, 'r', encoding='utf-8') as file:
            config = yaml.safe_load(file)
        if not config:
            errors.append("The configuration file is empty.")
            return False

        required_fields = [
            'switches', 'aaa_group_name',
            'radius_test_username', 'radius_dead_vlan'
        ]
        missing_fields = [field for field in required_fields if field not in config]
        if missing_fields:
            errors.append("Missing required fields:")
            for field in missing_fields:
                errors.append(f"   {field}")

        empty_fields = [field for field in required_fields if field in config and not config[field]]
        if empty_fields:
            errors.append("The following fields are empty:")
            for field in empty_fields:
                errors.append(f"  - {field}")

        # Validate switches
        switches = config.get("switches", [])
        for i, switch in enumerate(switches):
            if "hostname" not in switch or not switch["hostname"].strip():
                errors.append(f"Switch #{i + 1} is missing a 'hostname'.")
            if "ip" not in switch or not is_valid_ip(switch["ip"]):
                errors.append(f"Switch #{i + 1} has an invalid or missing 'ip'.")

        # Port logic: either global Port or per-switch port
        global_port = "Port" in config and config["Port"] and str(config["Port"]).strip() != ""
        if not global_port:
            # If no global Port, require 'port' for each switch
            for i, switch in enumerate(switches):
                if "port" not in switch or not str(switch["port"]).strip():
                    errors.append(f"Switch #{i + 1} is missing 'port' (required if no global Port is set).")
            # If all switches are missing 'port', add a global error
            if all(("port" not in sw or not str(sw["port"]).strip()) for sw in switches):
                errors.append("You must define either a global 'Port' or a 'port' for each switch.")

        # Validate VLAN
        if "radius_dead_vlan" in config and not is_valid_vlan(config["radius_dead_vlan"]):
            errors.append("'radius_dead_vlan' must be a valid VLAN ID (1-4094).")

        if errors:
            print(Fore.RED + "\n[ERROR] Switches configuration validation failed:")
            for error in errors:
                print(Fore.RED + f"  - {error}")
            return False

        print(Fore.GREEN + "\n[OK] Switches configuration file is valid.")
        return True

    except yaml.YAMLError as e:
        print(Fore.RED + f"\n[ERROR] YAML syntax error: {e}")
        return False
    except FileNotFoundError:
        print(Fore.RED + "\n[ERROR] Configuration file not found.")
        return False
    except Exception as e:
        print(Fore.RED + f"\n[ERROR] Unexpected error during validation: {e}")
        return False

def validate_servers_config(servers_secrets_path):
    """
    Validates the servers configuration file.
    """
    errors = []
    try:
        with open(servers_secrets_path, 'r', encoding='utf-8') as file:
            config = yaml.safe_load(file)
        if not config:
            errors.append("The configuration file is empty.")
            return False

        if "ise_servers" not in config or not isinstance(config["ise_servers"], list) or not config["ise_servers"]:
            errors.append("Missing or empty 'ise_servers' list.")
        else:
            for i, server in enumerate(config["ise_servers"]):
                if "name" not in server or not server["name"].strip():
                    errors.append(f"ISE server #{i + 1} is missing a 'name'.")
                if "Ip" not in server or not is_valid_ip(server["Ip"]):
                    errors.append(f"ISE server #{i + 1} has an invalid or missing 'Ip'.")

        if errors:
            print(Fore.RED + "\n[ERROR] Servers configuration validation failed:")
            for error in errors:
                print(Fore.RED + f"  - {error}")
            return False

        return True

    except yaml.YAMLError as e:
        print(Fore.RED + f"\n[ERROR] YAML syntax error: {e}")
        return False
    except FileNotFoundError:
        print(Fore.RED + "\n[ERROR] Configuration file not found.")
        return False
    except Exception as e:
        print(Fore.RED + f"\n[ERROR] Unexpected error during validation: {e}")
        return False

def validate_secrets_file_ssh(switches_secrets_path):
    """
    Validates the sensitive data file for SSH credentials.
    """
    errors = []
    try:
        with open(switches_secrets_path, 'r', encoding='utf-8') as file:
            secrets = yaml.safe_load(file)
        if not secrets:
            errors.append("The sensitive data file is empty.")
            return False

        has_global_ssh = "global_ssh_credentials" in secrets and secrets["global_ssh_credentials"]
        has_per_switch = "per_switch_credentials" in secrets and secrets["per_switch_credentials"]

        if has_global_ssh and has_per_switch:
            errors.append("Both 'global_ssh_credentials' and 'per_switch_credentials' are defined. Please choose only one.")

        if has_global_ssh:
            global_ssh = secrets["global_ssh_credentials"]
            if not global_ssh.get("Username"):
                errors.append("'global_ssh_credentials' is missing 'Username'.")
            if not global_ssh.get("Password"):
                errors.append("'global_ssh_credentials' is missing 'Password'.")

        if has_per_switch:
            per_switch = secrets["per_switch_credentials"]
            if not isinstance(per_switch, list) or len(per_switch) == 0:
                errors.append("'per_switch_credentials' must be a non-empty list.")
            else:
                for i, switch_cred in enumerate(per_switch):
                    if not switch_cred.get("hostname"):
                        errors.append(f"Switch #{i + 1} in 'per_switch_credentials' is missing 'hostname'.")
                    if not switch_cred.get("username"):
                        errors.append(f"Switch #{i + 1} in 'per_switch_credentials' is missing 'username'.")
                    if not switch_cred.get("ssh_password"):
                        errors.append(f"Switch #{i + 1} in 'per_switch_credentials' is missing 'ssh_password'.")
                    if not switch_cred.get("enable_password"):
                        errors.append(f"Switch #{i + 1} in 'per_switch_credentials' is missing 'enable_password'.")

        if "global_enable_password" not in secrets or not secrets["global_enable_password"]:
            errors.append("'global_enable_password' is missing or empty.")

        if "radius_test_password" not in secrets or not secrets["radius_test_password"]:
            errors.append("Missing or empty 'radius_test_password'.")

        if errors:
            print(Fore.RED + "\n[ERROR] SSH sensitive data validation failed:")
            for error in errors:
                print(Fore.RED + f"  - {error}")
            return False

        print(Fore.GREEN + "\n[OK] SSH sensitive data file is valid.")
        return True

    except yaml.YAMLError as e:
        print(Fore.RED + f"\n[ERROR] YAML syntax error in sensitive data file: {e}")
        return False
    except FileNotFoundError:
        print(Fore.RED + "\n[ERROR] Sensitive data file not found.")
        return False
    except Exception as e:
        print(Fore.RED + f"\n[ERROR] Unexpected error during validation of sensitive data file: {e}")
        return False

def validate_secrets_file_tacacs_plus(switches_secrets_path):
    """
    Validates the sensitive data file for TACACS+ credentials.
    """
    errors = []
    try:
        with open(switches_secrets_path, 'r', encoding='utf-8') as file:
            secrets = yaml.safe_load(file)
        if not secrets:
            errors.append("The sensitive data file is empty.")
            return False

        if "tacacs_credentials" not in secrets or not secrets["tacacs_credentials"]:
            errors.append("Missing or empty 'tacacs_credentials' section.")
        else:
            tacacs = secrets["tacacs_credentials"]
            if not tacacs.get("username"):
                errors.append("Missing or empty field: 'username' in 'tacacs_credentials'.")
            if not tacacs.get("secret"):
                errors.append("Missing or empty field: 'secret' in 'tacacs_credentials'.")

        if errors:
            print(Fore.RED + "\n[ERROR] TACACS+ sensitive data validation failed:")
            for error in errors:
                print(Fore.RED + f"  - {error}")
            return False

        print(Fore.GREEN + "\n[OK] TACACS+ sensitive data file is valid.")
        return True

    except yaml.YAMLError as e:
        print(Fore.RED + f"\n[ERROR] YAML syntax error in sensitive data file: {e}")
        return False
    except FileNotFoundError:
        print(Fore.RED + "\n[ERROR] Sensitive data file not found.")
        return False
    except Exception as e:
        print(Fore.RED + f"\n[ERROR] Unexpected error during validation of sensitive data file: {e}")
        return False

def validate_secrets_file_server(servers_secrets_path):
    """
    Validates the secrets file for servers (radius_secrets).
    """
    errors = []
    try:
        with open(servers_secrets_path, 'r', encoding='utf-8') as file:
            secrets = yaml.safe_load(file)
        if not secrets:
            errors.append("The sensitive data file is empty.")
            return False

        if "ise_servers_secrets" not in secrets or not isinstance(secrets["ise_servers_secrets"], list) or not secrets["ise_servers_secrets"]:
            errors.append("Missing or empty 'ise_servers_secrets' list.")
        else:
            for i, entry in enumerate(secrets["ise_servers_secrets"]):
                if not entry.get("server_name"):
                    errors.append(f"ise_servers_secrets #{i + 1} is missing 'server_name'.")
                if not entry.get("secret_key"):
                    errors.append(f"ise_servers_secrets #{i + 1} is missing 'secret_key'.")

        if errors:
            print(Fore.RED + "\n[ERROR] Servers sensitive data validation failed:")
            for error in errors:
                print(Fore.RED + f"  - {error}")
            return False

        return True

    except yaml.YAMLError as e:
        print(Fore.RED + f"\n[ERROR] YAML syntax error in sensitive data file: {e}")
        return False
    except FileNotFoundError:
        print(Fore.RED + "\n[ERROR] Sensitive data file not found.")
        return False
    except Exception as e:
        print(Fore.RED + f"\n[ERROR] Unexpected error during validation of sensitive data file: {e}")
        return False

def cross_validate_switches_and_secrets(switches_config_path, switches_secrets_path):
    """
    Cross-validate that all hostnames in switches config are present in per_switch_credentials and vice versa.
    Only applies if per_switch_credentials is used.
    """
    try:
        with open(switches_config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        with open(switches_secrets_path, 'r', encoding='utf-8') as f:
            secrets = yaml.safe_load(f)

        per_switch = secrets.get("per_switch_credentials")
        if per_switch:
            config_hostnames = set(sw['hostname'] for sw in config.get('switches', []) if sw.get('hostname'))
            secret_hostnames = set(cred['hostname'] for cred in per_switch if cred.get('hostname'))

            missing_in_secrets = config_hostnames - secret_hostnames
            missing_in_config = secret_hostnames - config_hostnames

            if missing_in_secrets:
                print(Fore.RED + f"Missing credentials for switches: {', '.join(missing_in_secrets)}")
                return False
            if missing_in_config:
                print(Fore.RED + f"Credentials provided for unknown switches: {', '.join(missing_in_config)}")
                return False

        print(Fore.GREEN + "[OK] Switches and per-switch credentials cross-validation passed.")
        return True
    except Exception as e:
        print(Fore.RED + f"[ERROR] Cross-validation error: {e}")
        return False

def cross_validate_servers_and_secrets(servers_config_path, servers_secrets_path):
    """
    Cross-validate that all server names in ise_servers are present in ise_servers_secrets and vice versa.
    """
    try:
        with open(servers_config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        with open(servers_secrets_path, 'r', encoding='utf-8') as f:
            secrets = yaml.safe_load(f)

        config_names = set(s['name'] for s in config.get('ise_servers', []) if s.get('name'))
        secret_names = set(s['server_name'] for s in secrets.get('ise_servers_secrets', []) if s.get('server_name'))

        missing_in_secrets = config_names - secret_names
        missing_in_config = secret_names - config_names

        if missing_in_secrets:
            print(Fore.RED + f"\nMissing secrets for servers: {', '.join(missing_in_secrets)}")
            return False
        if missing_in_config:
            print(Fore.RED + f"\nSecrets provided for unknown servers: {', '.join(missing_in_config)}")
            return False

        return True
    except Exception as e:
        print(Fore.RED + f"[ERROR] Cross-validation error: {e}")
        return False

def cross_validate_switches_and_secrets(switches_config_path, switches_secrets_path):
    """
    Cross-validate that all hostnames in switches config are present in per_switch_credentials and vice versa.
    Only applies if per_switch_credentials is used.
    """
    try:
        with open(switches_config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        with open(switches_secrets_path, 'r', encoding='utf-8') as f:
            secrets = yaml.safe_load(f)

        per_switch = secrets.get("per_switch_credentials")
        if per_switch:
            config_hostnames = set(sw['hostname'] for sw in config.get('switches', []) if sw.get('hostname'))
            secret_hostnames = set(cred['hostname'] for cred in per_switch if cred.get('hostname'))

            missing_in_secrets = config_hostnames - secret_hostnames
            missing_in_config = secret_hostnames - config_hostnames

            if missing_in_secrets:
                print(Fore.RED + f"\nMissing credentials for switches: {', '.join(missing_in_secrets)}")
                return False
            if missing_in_config:
                print(Fore.RED + f"\nCredentials provided for unknown switches: {', '.join(missing_in_config)}")
                return False

        return True
    except Exception as e:
        print(Fore.RED + f"[ERROR] Cross-validation error: {e}")
        return False
