import subprocess

# Function to start the cluster
def start_cluster():
    try:
        # Step 1: Power on nodes
        print("Powering on nodes...")
        result = subprocess.run(["python3", "power_on_nodes.py"], check=True)
        if result.returncode == 0:
            print("Nodes powered on.")

        # Step 2: Wait for CVMs to be reachable via ping
        print("Waiting for CVMs to be reachable via ping...")
        result = subprocess.run(["python3", "wait_for_cvm_ping.py"], check=True)
        if result.returncode == 0:
            print("CVMs are now reachable.")

        # Step 3: Wait for the cluster to be fully operational
        print("Waiting for the cluster to be fully operational...")
        result = subprocess.run(["python3", "wait_for_cluster_running.py"], check=True)
        if result.returncode == 0:
            print("Cluster is fully operational.")

        # Step 4: Power on all VMs using Acropolis CLI
        print("Powering on all VMs...")
        result = subprocess.run(["python3", "ssh_execute_command.py", "192.168.1.184", "nutanix", "nutanix/4u", "source /home/nutanix/.bash_profile; acli vm.on '*'"], check=True)
        if result.returncode == 0:
            print("All VMs powered on.")
        
        print("Cluster startup process completed.")
        
    except subprocess.CalledProcessError as e:
        print(f"Error during cluster startup: {e}")

# Main function
if __name__ == "__main__":
    action = input("Enter 'start' to start the cluster or 'stop' to stop the cluster: ").lower()

    if action == 'start':
        start_cluster()
    elif action == 'stop':
        subprocess.run(["python3", "stop_cluster.py"], check=True)
    else:
        print("Invalid action")
