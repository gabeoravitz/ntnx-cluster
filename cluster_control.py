import paramiko
import subprocess
import time

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

# SSH Functions using paramiko
def ssh_execute_command(ip, user, password, command):
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(ip, username=user, password=password)
    stdin, stdout, stderr = ssh.exec_command(command)
    output = stdout.read().decode()
    ssh.close()
    return output

# Wait for CVMs to be up by checking cluster status
def wait_for_cvm_ready(cvm):
    while True:
        output = ssh_execute_command(cvm['ip'], cvm['user'], cvm['password'], "cluster status")
        if 'CVM is down' not in output:
            print(f"CVM {cvm['ip']} is ready.")
            break
        print(f"Waiting for CVM {cvm['ip']} to be up...")
        time.sleep(30)

# Start the cluster
def start_cluster():
    # Step 1: Power on all AHV nodes via IPMI
    power_on_nodes()

    # Step 2: Wait for CVMs to be ready
    print("Waiting for CVMs to start...")
    for cvm in CVM_NODES:
        wait_for_cvm_ready(cvm)

    # Step 3: Start the cluster on one of the CVMs
    cvm = CVM_NODES[0]  # Use the first CVM to start the cluster
    print(f"Starting cluster on CVM {cvm['ip']}")
    ssh_execute_command(cvm['ip'], cvm['user'], cvm['password'], "cluster start")

    # Step 4: Power on all VMs using acli on the same CVM
    print(f"Powering on all VMs on CVM {cvm['ip']}")
    ssh_execute_command(cvm['ip'], cvm['user'], cvm['password'], "acli vm.on '*'")

# Stop the cluster and shut down VMs, CVMs, and AHV nodes
def stop_cluster():
    # Step 1: Gracefully shut down VMs using acli
    cvm = CVM_NODES[0]  # Use the first CVM to manage the cluster
    print(f"Attempting graceful shutdown of VMs on CVM {cvm['ip']}")
    ssh_execute_command(cvm['ip'], cvm['user'], cvm['password'], "acli vm.shutdown")
    time.sleep(60)  # Wait for shutdown to complete

    # Step 2: Forcefully shut down VMs if necessary
    print(f"Forcing shutdown of VMs on CVM {cvm['ip']}")
    ssh_execute_command(cvm['ip'], cvm['user'], cvm['password'], "acli vm.off '*'")

    # Step 3: Stop the cluster with "I agree" confirmation
    print(f"Stopping the cluster on CVM {cvm['ip']}")
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(cvm['ip'], username=cvm['user'], password=cvm['password'])
    stdin, stdout, stderr = ssh.exec_command("cluster stop")
    stdin.write("I agree\n")
    stdin.flush()
    output = stdout.read().decode()
    print(output)
    ssh.close()

    # Step 4: Shut down all CVMs
    for cvm in CVM_NODES:
        print(f"Shutting down CVM {cvm['ip']}")
        ssh_execute_command(cvm['ip'], cvm['user'], cvm['password'], "sudo shutdown -h now")

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
