import re

with open('web/sovereign_masterpiece.html', 'r', encoding='utf-8') as f:
    content = f.read()

views = re.findall(r'id=["\']view-([a-zA-Z0-9_-]+)["\']', content)
print('Existing views in HTML:', views)

tabs = re.findall(r'data-tab=["\']([a-zA-Z0-9_-]+)["\']', content)
print('Sidebar tabs in HTML:', tabs)

missing = [t for t in tabs if t not in views]
print('Missing view panes for tabs:', missing)
