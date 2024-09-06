import subprocess

# Test if .bash_profile is sourcing the environment properly
def test_bash_profile():
    print("Checking the contents of .bash_profile...")

    # Step 1: Print the .bash_profile to see if it's setting the PATH
    subprocess.run(
        ["python3", "ssh_execute_command.py", "192.168.1.184", "nutanix", "nutanix/4u", "cat /home/nutanix/.bash_profile"]
    )

    # Step 2: Print the PATH after sourcing .bash_profile
    print("Printing the PATH after sourcing .bash_profile...")
    subprocess.run(
        ["python3", "ssh_execute_command.py", "192.168.1.184", "nutanix", "nutanix/4u", "source /home/nutanix/.bash_profile && echo $PATH"]
    )

if __name__ == "__main__":
    test_bash_profile()
