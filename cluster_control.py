import paramiko
import time

# Define constants (IPs, credentials)
CVM_NODES = [
    {"ip": "192.168.1.184", "user": "nutanix", "password": "nutanix/4u"},  # CVM node 1
    {"ip": "192.168.1.185", "user": "nutanix", "password": "nutanix/4u"},  # CVM node 2
    {"ip": "192.168.1.186", "user": "nutanix", "password": "nutanix/4u"},  # CVM node 3
]

AHV_NODES = [
    {"ip": "192.168.1.180", "user": "root", "password": "nutanix/4u"},  # AHV node 1
    {"ip": "192.168.1.181", "user": "root", "password": "nutanix/4u"},  # AHV node 2
    {"ip": "192.168.1.182", "user": "root", "password": "nutanix/4u"},  # AHV node 3
]

# SSH Functions
def ssh_execute_command(ip, user, password, command):
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(ip, username=user, password=password)
    stdin, stdout, stderr = ssh.exec_command(command)
    output = stdout.read().decode()
    ssh.close()
    return output

# Cluster stop function with graceful VM shutdown, forced shutdown if needed, and physical node shutdown
def stop_cluster():
    # Step 1: Gracefully shut down VMs using acli
    for cvm in CVM_NODES:
        try:
            print(f"Attempting graceful shutdown of VMs managed by CVM {cvm['ip']}")
            ssh_execute_command(cvm['ip'], cvm['user'], cvm['password'], "acli vm.shutdown")
            time.sleep(60)  # Wait for the VMs to shut down
        except Exception as e:
            print(f"Graceful shutdown failed on CVM {cvm['ip']}. Forcing shutdown.")
            ssh_execute_command(cvm['ip'], cvm['user'], cvm['password'], "acli vm.force_off")

    # Step 2: Stop the cluster (with "I agree" confirmation)
    for cvm in CVM_NODES:
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

    # Step 3: Power off the CVMs using "sudo shutdown -h now"
    for cvm in CVM_NODES:
        print(f"Shutting down CVM {cvm['ip']}")
        ssh_execute_command(cvm['ip'], cvm['user'], cvm['password'], "sudo shutdown -h now")

    # Step 4: Wait for CVMs to power off before shutting down the physical nodes
    for cvm in CVM_NODES:
        while True:
            try:
                ssh_execute_command(cvm['ip'], cvm['user'], cvm['password'], "echo 'check'")  # Dummy command to check
            except:
                print(f"CVM {cvm['ip']} is powered off.")
                break
            time.sleep(30)

    # Step 5: Power off the AHV nodes via SSH using "shutdown -h now"
    for node in AHV_NODES:
        print(f"Shutting down AHV node {node['ip']}")
        ssh_execute_command(node['ip'], node['user'], node['password'], "sudo shutdown -h now")

# Cluster start function (unchanged)
def start_cluster():
    # Power on all nodes via IPMI (if you're using IPMI elsewhere, otherwise skip IPMI commands)
    for node in AHV_NODES:
        print(f"Powering on {node['ip']}")

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

# Main function
if __name__ == "__main__":
    action = input("Enter 'start' to start the cluster or 'stop' to stop the cluster: ").lower()

    if action == 'start':
        start_cluster()
    elif action == 'stop':
        stop_cluster()
    else:
        print("Invalid action")
