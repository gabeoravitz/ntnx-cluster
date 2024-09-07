import subprocess
import time

# Function to start the cluster
def start_cluster():
    try:
        # Step 1: Power on nodes
        print("Powering on nodes...")
        subprocess.run(["python3", "power_on_nodes.py"], check=True)

        # Step 2: Wait for CVMs to be reachable via ping
        print("Waiting for CVMs to be reachable via ping...")
        subprocess.run(["python3", "wait_for_cvm_ping.py"], check=True)

        # Step 3: Wait for the cluster to be fully operational
        print("Waiting for the cluster to be fully operational...")
        subprocess.run(["python3", "wait_for_cluster_running.py"], check=True)

        # Step 4: Power on all VMs
        print("Powering on all VMs...")
        subprocess.run(
            ["python3", "ssh_execute_command.py", "192.168.1.184", "nutanix", "nutanix/4u", "/usr/local/nutanix/bin/acli vm.on '*'"],
            check=True
        )

    except subprocess.CalledProcessError as e:
        print(f"failure: {e}")

# Function to stop the cluster
def stop_cluster():
    try:
        # Step 1: Gracefully shut down all VMs
        print("Attempting graceful shutdown of all VMs...")
        subprocess.run(
            ["python3", "ssh_execute_command.py", "192.168.1.184", "nutanix", "nutanix/4u", "/usr/local/nutanix/bin/acli vm.shutdown '*'"],
            check=True
        )

        # Wait 60 seconds after attempting graceful shutdown
        time.sleep(60)

        # Step 2: Forcefully power off all VMs
        print("Forcing shutdown of all VMs...")
        subprocess.run(
            ["python3", "ssh_execute_command.py", "192.168.1.184", "nutanix", "nutanix/4u", "/usr/local/nutanix/bin/acli vm.off '*'"],
            check=True
        )

        # Wait 5 seconds before proceeding to stop the cluster
        time.sleep(5)

        # Step 3: Stop the cluster with "I agree"
        print("Stopping the cluster...")
        subprocess.run(
            ["python3", "ssh_execute_command.py", "192.168.1.184", "nutanix", "nutanix/4u", "/usr/local/nutanix/cluster/bin/cluster stop", "I agree"],
            check=True
        )
        time.sleep(10)

        # Step 4: Shut down all CVMs
        print("Shutting down all CVMs...")
        for cvm_ip in ["192.168.1.184", "192.168.1.185", "192.168.1.186"]:
            subprocess.run(
                ["python3", "ssh_execute_command.py", cvm_ip, "nutanix", "nutanix/4u", "sudo shutdown -h now"],
                check=True
            )

      # Step 5: Wait 30 seconds before shutting down AHV nodes
        print("Waiting 30 seconds for CVMs to shut down...")
        time.sleep(30)

        # Step 6: Shut down all AHV hosts
        print("Shutting down all AHV hosts...")
        for ahv_ip in ["192.168.1.180", "192.168.1.181", "192.168.1.182"]:
            subprocess.run(
                ["python3", "ssh_execute_command.py", ahv_ip, "root", "nutanix/4u", "shutdown -h now"],
                check=True
            )

    except subprocess.CalledProcessError as e:
        print(f"failure: {e}")

# Main function
if __name__ == "__main__":
    action = input("Enter 'start' to start the cluster or 'stop' to stop the cluster: ").lower()

    if action == 'start':
        start_cluster()
    elif action == 'stop':
        stop_cluster()
    else:
        print("Invalid action")