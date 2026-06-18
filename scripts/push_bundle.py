"""Apply git bundle on server and push to GitHub."""
import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect("121.41.69.234", username="root", password="Lz88192603!@#", timeout=15)

def run(cmd, timeout=30):
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    return stdout.read().decode(), stderr.read().decode()

# 1. Verify bundle
print("1. Verify bundle")
o, e = run("cd /root/gaokao-ai && git bundle verify /tmp/newgkai.bundle 2>&1")
print(o)

# 2. Pull from bundle
print("\n2. Pull from bundle")
o, e = run("cd /root/gaokao-ai && git pull /tmp/newgkai.bundle main 2>&1")
print(o)

# 3. Check log
print("\n3. Check log")
o, e = run("cd /root/gaokao-ai && git log --oneline -5")
print(o)

# 4. Push to GitHub
print("\n4. Push to GitHub")
o, e = run("cd /root/gaokao-ai && git -c http.proxy= -c https.proxy= push origin main 2>&1")
print(o)

# 5. Verify
print("\n5. Verify remote")
o, e = run("cd /root/gaokao-ai && git fetch origin main 2>&1 && git log origin/main --oneline -3")
print(o)

ssh.close()
print("\nDone")
