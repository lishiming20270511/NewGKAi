"""Deploy v5.4 to 121.41.69.234"""
import subprocess, sys

cmds = [
    'cd /root/gaokao-ai',
    'git -c http.proxy= -c https.proxy= fetch origin main',
    'git -c http.proxy= -c https.proxy= reset --hard origin/main',
    'find /root/gaokao-ai -name "*.pyc" -delete',
    'find /root/gaokao-ai -name __pycache__ -type d -exec rm -rf {} + 2>/dev/null',
    'redis-cli KEYS "recommend:*" 2>/dev/null | xargs -r redis-cli DEL 2>/dev/null',
    'systemctl restart gaokao-api',
    'sleep 2',
    'systemctl is-active gaokao-api',
    'curl -s http://127.0.0.1:8000/health',
]
script = ' && echo "---SEP---" && '.join(cmds)
cmd = f'sshpass -p "Lz88192603!@#" ssh -o StrictHostKeyChecking=no root@121.41.69.234 "{script}"'

try:
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=60)
    print("STDOUT:", result.stdout[:500])
    if result.stderr:
        print("STDERR:", result.stderr[:200])
    print("EXIT:", result.returncode)
except Exception as e:
    print(f"Error: {e}")
