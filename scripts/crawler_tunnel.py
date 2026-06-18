"""Fix: Switch SSH tunnel to new server + set up key auth."""
import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect("199.193.126.80", username="root", password="SGM7VVPAPfGe", timeout=20)

def run(cmd, timeout=30):
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode()
    err = stderr.read().decode()
    if err:
        print("  ERR:", err[:300])
    return out

# 1. Check existing SSH key
print("=== SSH Keys ===")
o = run("ls -la /root/.ssh/")
print(o)

# 2. Read the crawler private key
print("\n=== Crawler Key Pub ===")
o = run("cat /root/.ssh/id_crawler.pub 2>/dev/null")
pubkey = o.strip()
print(pubkey)

# 3. Test SSH to new server with key
print("\n=== Test SSH to 121.41.69.234 with key ===")
o = run("ssh -o StrictHostKeyChecking=no -o ConnectTimeout=10 -i /root/.ssh/id_crawler root@121.41.69.234 'hostname && echo OK' 2>&1")
print(o.strip())

# 4. Check current autossh service
print("\n=== Autossh Service ===")
o = run("systemctl status autossh-tunnel 2>&1 || cat /etc/systemd/system/autossh*.service 2>/dev/null || echo 'No systemd unit'")
print(o[:500])

# 5. Check how autossh is started
print("\n=== How autossh starts ===")
o = run("grep -r 'autossh' /etc/ 2>/dev/null; grep -r 'autossh' /root/ 2>/dev/null | head -5")
print(o[:500])

ssh.close()
