import paramiko
import subprocess
import time
import os

# Define constants (IPs, credentials)
IPMI_NODES = [
    {"ip": "192.168.1.224", "user": "ADMIN", "password": "ADMIN"},  # IPMI node 1
    {"ip": "192.168.1.225", "user": "ADMIN", "password": "ADMIN"},  # IPMI node 2
    {"ip": "192.168.1.226", "user": "ADMIN", "password": "ADMIN"},  # IPMI node 3
]

AHV_NODES = [
    {"ip": "192.168.1.180", "user": "root", "password": "nutanix/4u"},  # AHV node 1
    {"ip": "192.168.1.181", "user": "root", "password": "nutanix/4u"},  # AHV node 2
    {"ip": "192.168.1.182", "user": "root", "password": "nutanix/4u"},  # AHV node 3
]

CVM_NODES = [
    {"ip": "192.168.1.184", "user": "nutanix", "password": "nutanix/4u"},  # CVM node 1
    {"ip": "192.168.1.185", "user": "nutanix", "password": "nutanix/4u"},  # CVM node 2
    {"ip": "192.168.1.186", "user": "nutanix", "password": "nutanix/4u"},  # CVM node 3
]

# Run IPMI commands using subprocess to interact with ipmitool
def run_ipmitool_command(ip, user, password, command):
    full_command = f"ipmitool -I lanplus -H {ip} -U {user} -P {password} {command}"
    result = subprocess.run(full_command, shell=True, capture_output=True, text=True)
    if result.returncode == 0:
        print(result.stdout)
    else:
        print(f"Error executing IPMI command: {result.stderr}")

# Power-On Function using ipmitool
def power_on_nodes():
    for node in IPMI_NODES:
        print(f"Powering on node {node['ip']}")
        run_ipmitool_command(node['ip'], node['user'], node['password'], "chassis power on")
        time.sleep(5)

# Ping check function
def is_ping_successful(ip):
    response = os.system(f"ping -c 1 -W 1 {ip} > /dev/null 2>&1")
    return response == 0

# SSH Functions using paramiko
def ssh_execute_command(ip, user, password, command):
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(ip, username=user, password=password)
    stdin, stdout, stderr = ssh.exec_command(command)
    output = stdout.read().decode()
    errors = stderr.read().decode()
    ssh.close()
    return output, errors

# Wait for CVMs to be reachable via ping
def wait_for_cvm_ping(cvm):
    print(f"Pinging CVM {cvm['ip']} to check if it's online...")
    while not is_ping_successful(cvm['ip']):
        print(f"CVM {cvm['ip']} is not reachable. Waiting...")
        time.sleep(10)  # Wait before retrying
    print(f"CVM {cvm['ip']} is online.")

# Enhanced check for CVM readiness by parsing the "cluster status" output
def wait_for_cvm_ready(cvm):
    print(f"Checking if CVM {cvm['ip']} is ready to accept cluster commands...")
    while True:
        output, _ = ssh_execute_command(cvm['ip'], cvm['user'], cvm['password'], "cluster status")
        
        # Check if the output contains the line that indicates all services are running
        if 'No cluster' not in output and 'CVM is down' not in output:
            print(f"CVM {cvm['ip']} is ready.")
            break
        
        print(f"Waiting for CVM {cvm['ip']} to be fully ready...")
        time.sleep(30)

# Wait for the cluster to be fully operational
def wait_for_cluster_running(cvm):
    print(f"Checking cluster status on CVM {cvm['ip']} to ensure it is fully running...")
    while True:
        output, _ = ssh_execute_command(cvm['ip'], cvm['user'], cvm['password'], "cluster status")
        
        # Look for the string that indicates the cluster is running and healthy
        if 'Cluster is running' in output and 'down' not in output:
            print(f"Cluster is fully operational on CVM {cvm['ip']}.")
            break
        
        print(f"Cluster is not fully running yet. Waiting...")
        time.sleep(30)

# Function to start the cluster with environment sourcing
def start_cluster():
    # Step 1: Power on all AHV nodes via IPMI
    power_on_nodes()

    # Step 2: Wait for CVMs to be reachable by ping
    print("Waiting for CVMs to be reachable via ping...")
    for cvm in CVM_NODES:
        wait_for_cvm_ping(cvm)

    # Step 3: Wait for CVMs to be fully ready by checking cluster status
    print("Waiting for CVMs to start services...")
    for cvm in CVM_NODES:
        wait_for_cvm_ready(cvm)

    # Step 4: Start the cluster on one of the CVMs and log output/errors
    cvm = CVM_NODES[0]  # Use the first CVM to start the cluster
    print(f"Starting cluster on CVM {cvm['ip']}")

    # Modify the command to source the profile and then run "cluster start"
    command = "source /home/nutanix/.bash_profile; cluster start"
    output, errors = ssh_execute_command(cvm['ip'], cvm['user'], cvm['password'], command)

    if output:
        print(f"Cluster start output: {output}")
    if errors:
        print(f"Cluster start errors: {errors}")

    # Step 5: Wait for the cluster to be fully operational
    wait_for_cluster_running(cvm)

    # Step 6: Power on all VMs using acli on the same CVM and log output/errors
    print(f"Powering on all VMs on CVM {cvm['ip']}")
    output, errors = ssh_execute_command(cvm['ip'], cvm['user'], cvm['password'], "acli vm.on '*'")
    if output:
        print(f"ACLI VM start output: {output}")
    if errors:
        print(f"ACLI VM start errors: {errors}")

# Stop the cluster and shut down VMs, CVMs, and AHV nodes
def stop_cluster():
    # Step 1: Gracefully shut down VMs using acli
    cvm = CVM_NODES[0]  # Use the first CVM to manage the cluster
    print(f"Attempting graceful shutdown of VMs on CVM {cvm['ip']}")
    output, errors = ssh_execute_command(cvm['ip'], cvm['user'], cvm['password'], "acli vm.shutdown")
    if output:
        print(f"ACLI VM shutdown output: {output}")
    if errors:
        print(f"ACLI VM shutdown errors: {errors}")
    time.sleep(60)  # Wait for shutdown to complete

    # Step 2: Forcefully shut down VMs if necessary
    print(f"Forcing shutdown of VMs on CVM {cvm['ip']}")
    output, errors = ssh_execute_command(cvm['ip'], cvm['user'], cvm['password'], "acli vm.off '*'")
    if output:
        print(f"ACLI VM force shutdown output: {output}")
    if errors:
        print(f"ACLI VM force shutdown errors: {errors}")

    # Step 3: Stop the cluster with "I agree" confirmation
    print(f"Stopping the cluster on CVM {cvm['ip']}")
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(cvm['ip'], username=cvm['user'], password=cvm['password'])
    stdin, stdout, stderr = ssh.exec_command("cluster stop")
    stdin.write("I agree\n")
    stdin.flush()
    output = stdout.read().decode()
    errors = stderr.read().decode()
    if output:
        print(f"Cluster stop output: {output}")
    if errors:
        print(f"Cluster stop errors: {errors}")
    ssh.close()

    # Step 4: Shut down all CVMs
    for cvm in CVM_NODES:
        print(f"Shutting down CVM {cvm['ip']}")
        output, errors = ssh_execute_command(cvm['ip'], cvm['user'], cvm['password'], "sudo shutdown -h now")
        if output:
            print(f"Shutdown output: {output}")
        if errors:
            print(f"Shutdown errors: {errors}")

    # Step 5: Wait for CVMs to power off before shutting down AHV nodes
    for cvm in CVM_NODES:
        while True:
            try:
                ssh_execute_command(cvm['ip'], cvm['user'], cvm['password'], "echo 'check'")
            except:
                print(f"CVM {cvm['ip']} is powered off.")
                break
            time.sleep(30)

    # Step 6: Power off the AHV nodes via SSH
    for node in AHV_NODES:
        print(f"Shutting down AHV node {node['ip']}")
        ssh_execute_command(node['ip'], node['user'], node['password'], "sudo shutdown -h now")

# Main function
if __name__ == "__main__":
    action = input("Enter 'start' to start the cluster or 'stop' to stop the cluster: ").lower()

    if action == 'start':
        start_cluster()
    elif action == 'stop':
        stop_cluster()
    else:
        print("Invalid action")
