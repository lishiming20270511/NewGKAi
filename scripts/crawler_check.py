"""Check crawler server status and current code."""
import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect("199.193.126.80", username="root", password="SGM7VVPAPfGe", timeout=20)

def run(cmd):
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=30)
    out = stdout.read().decode()
    err = stderr.read().decode()
    if err:
        print("ERR:", err[:300])
    return out

print("=== Server Info ===")
print(run("hostname && whoami && uname -a"))

print("\n=== Python Version ===")
print(run("python3 --version 2>&1 || python --version 2>&1"))

print("\n=== Root Directory ===")
print(run("ls -la /root/ 2>/dev/null | head -30"))

print("\n=== Crawler Scripts ===")
print(run("find /root -name '*.py' -maxdepth 3 2>/dev/null | head -20"))

print("\n=== Git Repos ===")
print(run("find /root -name '.git' -maxdepth 3 -type d 2>/dev/null"))

ssh.close()
