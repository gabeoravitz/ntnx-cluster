import subprocess

def stop_cluster():
    subprocess.run(["python3", "wait_for_cvm_poweroff.py"])
    print("Cluster stopped successfully.")

if __name__ == "__main__":
    stop_cluster()
