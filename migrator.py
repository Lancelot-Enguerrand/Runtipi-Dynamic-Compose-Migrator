import yaml
import json
import os

def handle_deploy_section(deploy):
    result = {}
    if not deploy:
        return result

    # Handle resources
    resources = deploy.get("resources")
    if resources:
        result["resources"] = {}
        # Handle limits
        limits = resources.get("limits")
        if limits:
            result["resources"]["limits"] = {}
            for key, value in limits.items():
                result["resources"]["limits"][key] = value

        # Handle reservations
        reservations = resources.get("reservations")
        if reservations:
            result["resources"]["reservations"] = {}
            # Handle cpus, memory, etc.
            for key, value in reservations.items():
                result["resources"]["reservations"][key] = value

            # Handle devices
            devices = reservations.get("devices")
            if devices:
                result["resources"]["reservations"]["devices"] = []
                for device in devices:
                    device_dict = {
                        "driver": device.get("driver"),
                        "count": device.get("count"),
                        "capabilities": device.get("capabilities", []),
                    }
                    # Add options only if not empty
                    options = device.get("options", {})
                    if options:
                        device_dict["options"] = options
                    
                    result["resources"]["reservations"]["devices"].append(device_dict)

    return result

def handle_healthcheck(healthcheck):
    if not healthcheck:
        return None

    result = {}

    # Handle interval, timeout, retries, and start_period dynamically
    for key in ["interval", "timeout", "retries", "start_period"]:
        if key in healthcheck:
            # Convert start_period to JSON-compatible key name
            if key == "start_period":
                result["startPeriod"] = healthcheck[key]
            else:
                result[key] = healthcheck[key]

    # Handle test conversion
    test = healthcheck.get("test")
    if isinstance(test, list) and len(test) > 0: 
        # Remove the first element if it starts with "CMD" or "CMD-SHELL"
        if test[0].upper() in ["CMD", "CMD-SHELL"]:
            test = test[1:]
        # Join the remaining elements into a single string
        result["test"] = " ".join(test)
    elif isinstance(test, str):
        # Remove "CMD " or "CMD-SHELL " prefix from a single string
        if test.upper().startswith("CMD "):
            result["test"] = test[4:].strip()
        elif test.upper().startswith("CMD-SHELL "):
            result["test"] = test[10:].strip()
        else:
            result["test"] = test.strip()
    else:
        result["test"] = None  # Set to None if no valid test is provided

    return result

def migrate_docker_compose(yaml_file_path, json_file_path, app_name):
    # Load YAML file
    with open(yaml_file_path, 'r') as yaml_file:
        yaml_data = yaml.safe_load(yaml_file)

    # Create services array
    services = []
    
    # Track handled sections
    handled_sections = {
        'image',
        'ports',
        'environment',
        'depends_on', 'volumes',
        'healthcheck',
        'command',
        'network_mode','network-mode',
        'extra_hosts',
        'hostname',
        'user',
        'labels',
        'privileged',
        'stop_grace_period',
        'entrypoint',
        'ulimits', 
        'expose',
        'working_dir',
        'stdin_open',
        'pid',
        'cap_add', 'cap_drop',
        'sysctls', 
        'devices', 
        'logging',    
        'shm_size',
        'tty',
        'stop_signal',
        'security_opt',
        'deploy',
        'read_only'
        }
    not_handled_sections = {}
    ignored_sections = {'restart', 'build', 'dns', 'networks', 'container_name', 'env_file', 'links'}
    
    for service_name, service_details in yaml_data.get('services', {}).items():
        # image and name
        service = {
            "name": service_name,
            "image": service_details.get("image")
        }
        
        # Main service check
        if service_name == app_name:
            service["isMain"] = True

        # Ports
        ports = service_details.get("ports", [])
        add_ports = []
        internal_port_set = False
        port_mappings = {}

        for port in ports:
            # Split port definition to extract interface, hostPort, containerPort, and protocol
            parts = port.rsplit(":", 2)  # Ensure that only the last two colons are split (for host and container ports)
            protocol = None
            container_port = None

            # Check if the last part contains a protocol (tcp or udp)
            if "/" in parts[-1]:
                container_port, protocol = parts[-1].split("/")
                container_port = int(container_port) if container_port.isdigit() else container_port
            else:
                container_port = int(parts[-1]) if parts[-1].isdigit() else parts[-1]

            # Determine the host port and interface
            host_port = int(parts[-2]) if parts[-2].isdigit() else parts[-2]
            interface = parts[0] if len(parts) > 2 else None

            # Set internalPort based on ${APP_PORT} and ignore protocol if present
            if "${APP_PORT}" in port:
                if not internal_port_set:
                    service["internalPort"] = container_port  # Set internalPort
                    internal_port_set = True
                continue  # Skip adding this to addPorts

            # Group TCP and UDP under the same port if they match
            port_key = (host_port, container_port, interface)
            if port_key not in port_mappings:
                port_mappings[port_key] = {
                    "hostPort": host_port,
                    "containerPort": container_port,
                }

                # Add interface if it exists
                if interface:
                    port_mappings[port_key]["interface"] = interface

            # Add protocol flags to the existing mapping
            if protocol == "tcp":
                port_mappings[port_key]["tcp"] = True
            elif protocol == "udp":
                port_mappings[port_key]["udp"] = True

        # Convert the port mappings to addPorts format
        add_ports = list(port_mappings.values())

        # Add addPorts section only if there are additional ports
        if add_ports:
            service["addPorts"] = add_ports

        # Hostname
        hostname = service_details.get("hostname")
        if hostname:
            service["hostname"] = hostname

        # Extra Hosts
        extra_hosts = service_details.get("extra_hosts")
        if extra_hosts:
            service["extraHosts"] = extra_hosts
        
        # User
        user = service_details.get("user")
        if user:
            service["user"] = user

        # Restart
        #restart = service_details.get("restart")
        #if restart:
        #    service["restart"] = restart
        
        # PID
        pid = service_details.get("pid")
        if pid:
            service["pid"] = pid
        
        # DNS
        #dns = service_details.get("dns")
        #if dns:
        #    service["dns"] = dns

        # Expose
        expose = service_details.get("expose")
        if expose:
            service["expose"] = expose

        # Network Mode
        network_mode = service_details.get("network_mode")
        if network_mode:
            service["networkMode"] = network_mode
        else:
            network_mode = service_details.get("network-mode")
            if network_mode:
                service["networkMode"] = network_mode

        # Environment
        environment = service_details.get("environment", {})
        if environment:
            if isinstance(environment, list):
                # Handle list format: "KEY=VALUE"
                service["environment"] = {
                    env.split('=')[0]: env.split('=')[1] for env in environment if '=' in env
                }
            elif isinstance(environment, dict):
                # Handle dict format: "KEY: VALUE"
                service["environment"] = environment
        
        # Links
        #links = service_details.get("links")
        #if links:
        #    service["links"] = links

        # Depends on (can be dict or list)
        depends_on = service_details.get("depends_on")
        if depends_on:
            if isinstance(depends_on, dict):
                # Format: dict with conditions
                service["dependsOn"] = {key: {"condition": value.get("condition")} for key, value in depends_on.items()}
            elif isinstance(depends_on, list):
                # Format: list of services without conditions
                service["dependsOn"] = depends_on
        
        # volumes
        volumes = service_details.get("volumes", [])
        if volumes:
            service["volumes"] = []
            for volume in volumes:
                parts = volume.split(":")
                volume_mapping = {"hostPath": parts[0]}
                if len(parts) > 1:
                    volume_mapping["containerPath"] = parts[1]
                if len(parts) > 2 and parts[2] == "ro":
                    volume_mapping["readOnly"] = True
                service["volumes"].append(volume_mapping)

        # Working Dir
        working_dir = service_details.get("working_dir")
        if working_dir:
            service["workingDir"] = working_dir
        
        # Read Only
        read_only = service_details.get("read_only")
        if read_only:
            service["readOnly"] = read_only
        
        # Entrypoint
        entrypoint = service_details.get("entrypoint")
        if entrypoint:
            service["entrypoint"] = entrypoint
        
        # Command
        command = service_details.get("command")
        if command:
            service["command"] = command

        # Sysctls
        sysctls = service_details.get("sysctls")
        if sysctls:
            service["sysctls"] = sysctls

        # Privileged
        privileged = service_details.get("privileged")
        if privileged:
            service["privileged"] = privileged
        
        # TTY
        tty = service_details.get("tty")
        if tty:
            service["tty"] = tty

        # stdin open
        stdin_open = service_details.get("stdin_open")
        if stdin_open:
            service["stdinOpen"] = stdin_open
        
        # Deploy - handled with modular function
        deploy = service_details.get("deploy")
        if deploy:
            service["deploy"] = handle_deploy_section(deploy)
        
        # Devices
        devices = service_details.get("devices")
        if devices:
            service["devices"] = devices
        
        # Cap Add
        cap_add = service_details.get("cap_add")
        if cap_add:
            service["capAdd"] = cap_add
        
        # Cap Drop
        cap_drop = service_details.get("cap_drop")
        if cap_drop:
            service["capDrop"] = cap_drop

        # Logging
        logging = service_details.get("logging")
        if logging:
            service["logging"] = {
                "driver": logging.get("driver"),
                "options": logging.get("options", {})
            }

        # Shared Memory Size
        shm_size = service_details.get("shm_size")
        if shm_size:
            service["shmSize"] = shm_size

        # Stop Signal
        stop_signal = service_details.get("stop_signal")
        if stop_signal:
            service["stopSignal"] = stop_signal

        # Security Opt
        security_opt = service_details.get("security_opt")
        if security_opt:
            service["securityOpt"] = security_opt

        # Ulimits
        ulimits = service_details.get("ulimits")
        if ulimits:
            service["ulimits"] = {}
            for limit_name, limit_values in ulimits.items():
                if isinstance(limit_values, dict):
                    # Case where soft and hard are provided separately
                    service["ulimits"][limit_name] = {
                        "soft": limit_values.get("soft"),
                        "hard": limit_values.get("hard")
                    }
                else:
                    # Case where a single value is provided
                    service["ulimits"][limit_name] = limit_values

        # Stop grace period
        stop_grace_period = service_details.get("stop_grace_period")
        if stop_grace_period:
            service["stop_grace_period"] = stop_grace_period

        # Healthchecks - handled with modular function
        healthcheck = service_details.get("healthcheck")
        if healthcheck:
            service["healthCheck"] = handle_healthcheck(healthcheck)
        
        # Labels
        labels = service_details.get("labels", {})
        filtered_labels = {key: value for key, value in labels.items() if not key.startswith("traefik") and not key.startswith("runtipi")}
        if filtered_labels:
            service["labels"] = filtered_labels
            
        services.append(service)

        # Track unhandled sections
        unhandled_sections = set(service_details.keys()) - handled_sections - set(ignored_sections)
        if unhandled_sections:
            print(f"Warning: Unhandled sections in service '{service_name}': {', '.join(unhandled_sections)}")
            break

    # Create JSON data
    json_data = {"$schema": "../dynamic-compose-schema.json", "services": services}

    # Write JSON file
    with open(json_file_path, 'w') as json_file:
        json.dump(json_data, json_file, indent=2)   
        json_file.write('\n')  # Add empty line

    #print(f"Migration done. JSON file : '{json_file_path}'.")

def migrate_all_applications(applications_dir, on_existing_json='ignore'):
    # Parcourir tous les dossiers dans le répertoire des applications
    for app_folder in os.listdir(applications_dir):
        app_path = os.path.join(applications_dir, app_folder)

        # Vérifier que c'est bien un dossier
        if os.path.isdir(app_path):
            yaml_file_path = os.path.join(app_path, 'docker-compose.yml')
            json_file_path = os.path.join(app_path, 'docker-compose.json')

            # Vérifier si le fichier YAML existe dans le dossier
            if os.path.exists(yaml_file_path):
                # Gérer le cas où le fichier JSON existe déjà
                if os.path.exists(json_file_path):
                    if on_existing_json == 'ignore':
                        print(f"Skipping migration for {app_folder} because JSON file already exists.")
                        continue
                    elif on_existing_json == 'new_extension':
                        json_file_path = os.path.join(app_path, 'docker-compose.json.new')
                
                #print(f"Migrating {app_folder}...")
                # Appeler la fonction de migration avec le nom de l'application
                migrate_docker_compose(yaml_file_path, json_file_path, app_folder)
            else:
                print(f"Warning: No docker-compose.yml found in {app_folder}. Skipping.")

applications_directory = '.'  # Replace if necessary
migrate_all_applications(applications_directory, on_existing_json='ignore')
