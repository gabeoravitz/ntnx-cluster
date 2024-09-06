import paramiko
import time
from pyipmi import create_connection
from pyipmi.interfaces import Ipmitool

# Define constants (IPs, credentials)
CLUSTER_NODES = [
    {"ip": "192.168.1.180", "user": "root", "password": "nutanix/4u"},  # AHV node 1
    {"ip": "192.168.1.181", "user": "root", "password": "nutanix/4u"},  # AHV node 2
    {"ip": "192.168.1.182", "user": "root", "password": "nutanix/4u"},  # AHV node 3
]

CVM_NODES = [
    {"ip": "192.168.1.184", "user": "nutanix", "password": "nutanix/4u"},  # CVM node 1
    {"ip": "192.168.1.185", "user": "nutanix", "password": "nutanix/4u"},  # CVM node 2
    {"ip": "192.168.1.186", "user": "nutanix", "password": "nutanix/4u"},  # CVM node 3
]

# IPMI functions for powering nodes
def power_on_node(ip, user, password):
    interface = Ipmitool()
    conn = create_connection(interface)
    conn.target = ip
    conn.username = user
    conn.password = password
    conn.session.establish()
    conn.chassis.power_on()

# SSH Functions
def ssh_execute_command(ip, user, password, command):
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(ip, username=user, password=password)
    stdin, stdout, stderr = ssh.exec_command(command)
    output = stdout.read().decode()
    ssh.close()
    return output

# Cluster start function
def start_cluster():
    # Power on all nodes via IPMI
    for node in CLUSTER_NODES:
        print(f"Powering on {node['ip']}")
        power_on_node(node['ip'], node['user'], node['password'])

    # Wait and verify that the CVMs are powered on and the services are up
    time.sleep(120)  # Adjust as needed
    for cvm in CVM_NODES:
        output = ssh_execute_command(cvm['ip'], cvm['user'], cvm['password'], "cluster status")
        while 'CVM is down' in output:
            print(f"Waiting for CVM {cvm['ip']} to be up...")
            time.sleep(30)
            output = ssh_execute_command(cvm['ip'], cvm['user'], cvm['password'], "cluster status")

    # Issue cluster start command
    for cvm in CVM_NODES:
        print(f"Starting cluster on {cvm['ip']}")
        ssh_execute_command(cvm['ip'], cvm['user'], cvm['password'], "cluster start")

    # Power on all VMs using acli
    for cvm in CVM_NODES:
        print(f"Powering on all VMs on CVM {cvm['ip']}")
        ssh_execute_command(cvm['ip'], cvm['user'], cvm['password'], "acli vm.on '*'")

# Cluster stop function
def stop_cluster():
    # Gracefully shutdown CVMs via acli
    for cvm in CVM_NODES:
        try:
            print(f"Attempting graceful shutdown on CVM {cvm['ip']}")
            ssh_execute_command(cvm['ip'], cvm['user'], cvm['password'], "acli vm.shutdown")
            time.sleep(60)  # Adjust as needed for graceful shutdown
        except Exception as e:
            print(f"Graceful shutdown failed on {cvm['ip']}. Forcing shutdown.")
            ssh_execute_command(cvm['ip'], cvm['user'], cvm['password'], "acli vm.force_shutdown")

    # Issue cluster stop command
    for cvm in CVM_NODES:
        print(f"Stopping cluster on {cvm['ip']}")
        ssh_execute_command(cvm['ip'], cvm['user'], cvm['password'], "echo 'I agree' | cluster stop")

    # Power off the CVMs
    for cvm in CVM_NODES:
        print(f"Shutting down CVM {cvm['ip']}")
        ssh_execute_command(cvm['ip'], cvm['user'], cvm['password'], "sudo shutdown -h now")

    # Wait for CVMs to power off
    for cvm in CVM_NODES:
        while True:
            try:
                ssh_execute_command(cvm['ip'], cvm['user'], cvm['password'], "echo 'check'")  # Dummy command to check
            except:
                print(f"CVM {cvm['ip']} is powered off.")
                break
            time.sleep(30)

    # Power off the AHV nodes via SSH after CVMs are powered off
    for node in CLUSTER_NODES:
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
