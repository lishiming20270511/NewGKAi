"""Test DB connection and check data in one shot."""
import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect("199.193.126.80", username="root", password="SGM7VVPAPfGe", timeout=15)

# Run with explicit working directory
stdin, stdout, stderr = ssh.exec_command(
    "cd /root/gaokao-crawler && PYTHONPATH=/root/gaokao-crawler venv/bin/python3 /tmp/test_db.py 2>&1",
    timeout=20
)
out = stdout.read().decode()
err = stderr.read().decode()
print("STDOUT:", out)
if err:
    print("STDERR:", err[:500])

ssh.close()
