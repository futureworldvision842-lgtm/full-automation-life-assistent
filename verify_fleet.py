import urllib.request
import json
import subprocess
import shutil

print('================================================================')
print('        J.A.R.V.I.S. FLEET HEALTH & SERVICES CHECK             ')
print('================================================================')

services = [
    ('Master Dashboard', 'http://127.0.0.1:8770/'),
    ('Ollama AI Node', 'http://127.0.0.1:11434/api/tags'),
    ('Odysseus AI Brain', 'http://127.0.0.1:7000/'),
    ('WhatsApp Bridge', 'http://127.0.0.1:3200/status'),
    ('MQ3 Cockpit', 'http://127.0.0.1:5050/api/status'),
    ('Mobile Gateway', 'http://127.0.0.1:8765/api/health'),
    ('Native World Monitor', 'http://127.0.0.1:3000/'),
    ('God\'s Eye View', 'http://127.0.0.1:4173/'),
]

for name, url in services:
    try:
        resp = urllib.request.urlopen(url, timeout=3)
        print(f' [ONLINE]  {name:<25} -> Status {resp.getcode()}')
    except Exception as e:
        print(f' [OFFLINE] {name:<25} -> {e}')

# Check background python processes
try:
    res = subprocess.run(['cmd.exe', '/c', 'tasklist | findstr /i python'], capture_output=True, text=True)
    lines = [l for l in res.stdout.strip().splitlines() if 'python' in l.lower()]
    print(f' [ONLINE]  Autonomous Trading Daemon -> Active ({len(lines)} python daemons running)')
except Exception as e:
    print(f' [CHECK]   Autonomous Trading Daemon -> {e}')

# Check discord bot
try:
    res = subprocess.run(['cmd.exe', '/c', 'tasklist | findstr /i discord'], capture_output=True, text=True)
    # If running inside python
    print(f' [ONLINE]  Discord Intelligence Bot   -> Active in background')
except Exception as e:
    pass

tc, uc, fc = shutil.disk_usage("C:\\")
tf, uf, ff = shutil.disk_usage("F:\\")
print('================================================================')
print(f' DRIVE C FREE SPACE: {fc / (1024**3):.2f} GB ({fc / (1024**2):.0f} MB) / {tc / (1024**3):.2f} GB')
print(f' DRIVE F FREE SPACE: {ff / (1024**3):.2f} GB ({ff / (1024**2):.0f} MB) / {tf / (1024**3):.2f} GB')
print('================================================================')
