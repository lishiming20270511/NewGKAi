"""Add crawler SSH key to new production server and update tunnel."""
import paramiko

# 1. Add crawler pubkey to new server
print("=== Step 1: Add crawler key to 121.41.69.234 ===")
ssh_prod = paramiko.SSHClient()
ssh_prod.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh_prod.connect("121.41.69.234", username="root", password="Lz88192603!@#", timeout=15)

crawler_pubkey = "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIKQHAE4l041gahY7erhwssoTCCllhLaARVplZ/NcUkhg root@safe-bounty-2.localdomain"

# Check if key exists, add if not
stdin, stdout, stderr = ssh_prod.exec_command(
    "grep -q 'safe-bounty-2' /root/.ssh/authorized_keys 2>/dev/null && echo EXISTS || "
    "(echo '" + crawler_pubkey + "' >> /root/.ssh/authorized_keys && echo ADDED)"
)
result = stdout.read().decode().strip()
print("Key status:", result)
ssh_prod.close()

# 2. Update tunnel on crawler server
print("\n=== Step 2: Test key to new server ===")
ssh_crawl = paramiko.SSHClient()
ssh_crawl.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh_crawl.connect("199.193.126.80", username="root", password="SGM7VVPAPfGe", timeout=20)

def run(ssh_conn, cmd, timeout=30):
    stdin, stdout, stderr = ssh_conn.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode()
    err = stderr.read().decode()
    if err:
        print("  ERR:", err[:300])
    return out

# Test SSH key
o = run(ssh_crawl, "ssh -o StrictHostKeyChecking=no -o ConnectTimeout=10 -i /root/.ssh/id_crawler root@121.41.69.234 'hostname && echo KEY_OK' 2>&1")
print(o.strip())

if "KEY_OK" in o:
    print("Key auth works! Updating tunnel config...")
    
    # Update .env - change TUNNEL_SSH_HOST
    old_ip = "114.55.65.71"
    new_ip = "121.41.69.234"
    run(ssh_crawl, "sed -i 's/" + old_ip + "/" + new_ip + "/g' /root/gaokao-crawler/.env")
    print("Updated .env TUNNEL_SSH_HOST")
    
    # Update systemd service
    run(ssh_crawl, "sed -i 's/" + old_ip + "/" + new_ip + "/g' /etc/systemd/system/mysql-tunnel.service")
    print("Updated mysql-tunnel.service")
    
    # Restart tunnel
    print("Killing old tunnel...")
    run(ssh_crawl, "pkill -f 'autossh.*13306' 2>/dev/null; pkill -f 'ssh.*13306.*3306' 2>/dev/null; sleep 2")
    print("Starting new tunnel...")
    run(ssh_crawl, "systemctl daemon-reload && systemctl restart mysql-tunnel && sleep 3")
    o = run(ssh_crawl, "systemctl is-active mysql-tunnel")
    print("Tunnel status:", o.strip())
    
    # Verify tunnel port
    o = run(ssh_crawl, "ss -tlnp | grep 13306")
    print("Tunnel port:", o.strip())
    
    # Test MySQL through tunnel using venv
    print("\nTesting MySQL through tunnel...")
    test_cmd = (
        "cd /root/gaokao-crawler && venv/bin/python3 -c \""
        "from db.connection import SessionFactory; "
        "from sqlalchemy import text; "
        "db = SessionFactory(); "
        "r = db.execute(text('SELECT COUNT(*) FROM admission_history')).scalar(); "
        "print('admission_history rows:', r); "
        "r2 = db.execute(text('SELECT COUNT(*) FROM schools')).scalar(); "
        "print('schools rows:', r2); "
        "db.close()"
        "\""
    )
    o = run(ssh_crawl, test_cmd)
    print(o)
else:
    print("Key auth failed. Checking what went wrong...")
    # Check if key was added to server
    ssh_prod2 = paramiko.SSHClient()
    ssh_prod2.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh_prod2.connect("121.41.69.234", username="root", password="Lz88192603!@#", timeout=15)
    stdin, stdout, stderr = ssh_prod2.exec_command("grep safe-bounty /root/.ssh/authorized_keys")
    print("Key on server:", stdout.read().decode().strip())
    
    # Check perms
    stdin, stdout, stderr = ssh_prod2.exec_command("ls -la /root/.ssh/")
    print(stdout.read().decode())
    ssh_prod2.close()

ssh_crawl.close()
