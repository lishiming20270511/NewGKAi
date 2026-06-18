import paramiko
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect("121.41.69.234", username="root", password="Lz88192603!@#", timeout=15)

def run(cmd):
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=10)
    return stdout.read().decode(), stderr.read().decode()

# Check nginx config
print("=== Nginx config ===")
o, e = run("grep -n 'root\|proxy_pass\|index' /etc/nginx/sites-enabled/* 2>/dev/null | head -20")
print(o)

# Check where index.html is served from
print("\n=== Check file paths ===")
o, e = run("ls -la /www/wwwroot/gaokao.lumenaistudio.co/index.html 2>/dev/null; echo '---'; grep title /www/wwwroot/gaokao.lumenaistudio.co/index.html 2>/dev/null | head -1")
print(o)

o, e = run("grep title /root/gaokao-ai/frontend/index.html | head -1")
print("FastAPI frontend:", o.strip())

# Copy to nginx path if needed
print("\n=== Copying frontend ===")
o, e = run("cp /root/gaokao-ai/frontend/index.html /www/wwwroot/gaokao.lumenaistudio.co/index.html && echo 'copied' || echo 'no www dir'")
print(o)

ssh.close()
