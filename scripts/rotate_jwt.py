"""Rotate JWT_SECRET and INTERNAL_JWT_SECRET on production server."""
import paramiko
import secrets

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect("121.41.69.234", username="root", password="Lz88192603!@#", timeout=15)

def run(cmd, timeout=30):
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    return stdout.read().decode(), stderr.read().decode()

# Generate new strong secrets
jwt_key = secrets.token_urlsafe(48)
int_key = secrets.token_urlsafe(48)
print("New keys generated, length:", len(jwt_key))

# Backup current .env
print("1. Backup .env")
o, e = run("cp /root/gaokao-ai/.env /root/gaokao-ai/.env.bak_jwt_$(date +%Y%m%d_%H%M%S) && echo OK")
print(o.strip())

# Read current .env via SFTP
print("2. Read current .env")
sftp = ssh.open_sftp()
with sftp.open("/root/gaokao-ai/.env", "r") as f:
    env_text = f.read().decode("utf-8")
sftp.close()

# Replace JWT keys - using run() to sed on server side
print("3. Update JWT_SECRET via sed")
escaped_jwt = jwt_key.replace("'", "'\\''")
escaped_int = int_key.replace("'", "'\\''")

# Use awk to replace or append JWT_SECRET
o, e = run(
    "if grep -q '^JWT_SECRET=' /root/gaokao-ai/.env; then "
    "  sed -i \"s|^JWT_SECRET=.*|JWT_SECRET=\"'\"'\" + jwt_key + \"'\"'\"|\" /root/gaokao-ai/.env; "
    "else "
    "  echo 'JWT_SECRET=\"'\"'\" + jwt_key + \"'\"'\"' >> /root/gaokao-ai/.env; "
    "fi && echo JWTOK"
)
print(o.strip())

o, e = run(
    "if grep -q '^INTERNAL_JWT_SECRET=' /root/gaokao-ai/.env; then "
    "  sed -i \"s|^INTERNAL_JWT_SECRET=.*|INTERNAL_JWT_SECRET=\"'\"'\" + int_key + \"'\"'\"|\" /root/gaokao-ai/.env; "
    "else "
    "  echo 'INTERNAL_JWT_SECRET=\"'\"'\" + int_key + \"'\"'\"' >> /root/gaokao-ai/.env; "
    "fi && echo INT_OK"
)
print(o.strip())

# Restart
print("4. Restart service")
o, e = run("systemctl restart gaokao-api && sleep 2 && systemctl is-active gaokao-api")
print(o.strip())

# Health
print("5. Health check")
o, e = run("curl -s http://127.0.0.1:8000/health")
print(o.strip())

ssh.close()
print("\nDone. JWT keys rotated.")
