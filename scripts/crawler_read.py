"""Read crawler source code from remote server."""
import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect("199.193.126.80", username="root", password="SGM7VVPAPfGe", timeout=20)

# Read fetch_school_facts.py
sftp = ssh.open_sftp()
with sftp.open("/root/fetch_school_facts.py", "r") as f:
    fetch_school = f.read().decode("utf-8")
print("=== /root/fetch_school_facts.py (", len(fetch_school), "bytes) ===")
print(fetch_school[:5000])
print("... [TRUNCATED] ...")

# Read gaokao-crawler main files
for path in [
    "/root/gaokao-crawler/dispatch_pending.py",
    "/root/gaokao-crawler/tasks/crawl_task.py",
    "/root/gaokao-crawler/db/models.py",
]:
    try:
        with sftp.open(path, "r") as f:
            content = f.read().decode("utf-8")
        print("\n=== " + path + " (" + str(len(content)) + " bytes) ===")
        print(content[:3000])
        if len(content) > 3000:
            print("... [TRUNCATED] ...")
    except Exception as e:
        print("\n=== " + path + " ERROR:", e)

sftp.close()
ssh.close()
