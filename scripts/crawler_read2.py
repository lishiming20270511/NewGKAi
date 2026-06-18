"""Read the ChsiCrawler source from remote server."""
import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect("199.193.126.80", username="root", password="SGM7VVPAPfGe", timeout=20)

sftp = ssh.open_sftp()

# Read ChsiCrawler
try:
    with sftp.open("/root/gaokao-crawler/crawler/parsers/chsi.py", "r") as f:
        content = f.read().decode("utf-8")
    print("=== /root/gaokao-crawler/crawler/parsers/chsi.py (", len(content), "bytes) ===")
    print(content)
except Exception as e:
    print("chsi.py ERROR:", e)
    # Try to find it
    import io
    stdin, stdout, stderr = ssh.exec_command("find /root/gaokao-crawler -name '*.py' -type f | sort")
    print("Files:", stdout.read().decode())

# Read gaokao-crawler crawl_task.py in full
try:
    with sftp.open("/root/gaokao-crawler/tasks/crawl_task.py", "r") as f:
        content = f.read().decode("utf-8")
    print("\n=== /root/gaokao-crawler/tasks/crawl_task.py FULL ===")
    print(content)
except Exception as e:
    print("ERROR:", e)

sftp.close()
ssh.close()
