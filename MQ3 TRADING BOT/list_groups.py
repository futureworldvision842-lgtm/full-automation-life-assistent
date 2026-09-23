import sys
import io
import requests

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

r = requests.get('http://127.0.0.1:3001/groups').json()
groups = r.get('groups', [])
print(f"Found {len(groups)} participating groups on WhatsApp:")
for g in groups:
    print(f"• {g['subject']}  [ID: {g['id']}]")
