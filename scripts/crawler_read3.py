"""Read crawler DB connection and check data flow."""
import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect("199.193.126.80", username="root", password="SGM7VVPAPfGe", timeout=20)

sftp = ssh.open_sftp()

# Read DB connection config
try:
    with sftp.open("/root/gaokao-crawler/db/connection.py", "r") as f:
        content = f.read().decode("utf-8")
    print("=== db/connection.py ===")
    print(content)
except Exception as e:
    print("ERROR:", e)

# Read the full fetch_school_facts.py to see complete data flow
try:
    with sftp.open("/root/fetch_school_facts.py", "r") as f:
        content = f.read().decode("utf-8")
    print("\n=== fetch_school_facts.py ===")
    print(content)
except Exception as e:
    print("ERROR:", e)

# Check if there's a data push script
stdin, stdout, stderr = ssh.exec_command("find /root -name '*.py' -exec grep -l 'internal/crawler/ingest\\|121.41.69.234' {} \\; 2>/dev/null")
print("\n=== Scripts referencing production server ===")
print(stdout.read().decode())

sftp.close()
ssh.close()
