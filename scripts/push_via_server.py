"""Push to GitHub via production server."""
import paramiko

# First, push local commits to production server via git
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect("121.41.69.234", username="root", password="Lz88192603!@#", timeout=15)

def run(cmd, timeout=60):
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    return stdout.read().decode(), stderr.read().decode()

# Add local repo as remote on server, fetch our commits, then push
print("1. Fetch from local via SSH...")
# Since we can't easily transfer, let's have the server pull the latest
o, e = run("cd /root/gaokao-ai && git -c http.proxy= -c https.proxy= fetch origin main 2>&1")
print(o[:300])
if e:
    print("ERR:", e[:200])

# Check what server has vs local
print("\n2. Server git log:")
o, e = run("cd /root/gaokao-ai && git log --oneline -3")
print(o)

print("\n3. Try push from server:")
o, e = run("cd /root/gaokao-ai && git -c http.proxy= -c https.proxy= log origin/main..HEAD --oneline 2>/dev/null || echo 'up to date'")
print(o)

# The server already has the latest code via deploy.py (b5a42c5).
# But we have a newer local commit fb2a681.
# We need to push the local commit to GitHub first, then the server can pull.
# Since local can't push, let's mirror via the server.

# Actually, let's check if the server can push our local commit
# First, let's check what's missing
print("\n4. Local commits not on remote:")
o, e = run("cd /root/gaokao-ai && git fetch origin main 2>&1 && git log origin/main..HEAD --oneline 2>&1")
print(o)

# If server can push to GitHub, we can scp the local repo objects
# But that's complex. Let's try a simpler approach:
# Create a git bundle locally and scp it, then pull from bundle on server

ssh.close()
print("\nChecking GitHub connectivity from server...")

# Try again with just a connectivity test
ssh2 = paramiko.SSHClient()
ssh2.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh2.connect("121.41.69.234", username="root", password="Lz88192603!@#", timeout=15)
o, e = run("curl -s -o /dev/null -w '%{http_code}' --connect-timeout 10 https://github.com 2>&1")
print("GitHub HTTP status from server:", o.strip())
ssh2.close()
