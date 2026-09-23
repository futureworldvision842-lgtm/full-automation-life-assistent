import os
import pathlib
import win32com.client

desktop = pathlib.Path(os.path.expanduser('~')) / 'OneDrive' / 'Desktop'
if not desktop.exists():
    desktop = pathlib.Path(os.path.expanduser('~')) / 'Desktop'

shell = win32com.client.Dispatch('WScript.Shell')
f_root = r'F:\Jarvis Command Center'

# 1. JARVIS - START ALL
s1 = shell.CreateShortCut(str(desktop / 'JARVIS - START ALL.lnk'))
s1.TargetPath = os.path.join(f_root, 'JARVIS - START ALL.bat')
s1.WorkingDirectory = f_root
s1.IconLocation = 'shell32.dll,238'
s1.Description = 'Start J.A.R.V.I.S. Sovereign Ecosystem & God\'s Eye (SSD F:)'
s1.Save()

# 2. JARVIS - STOP ALL
s2 = shell.CreateShortCut(str(desktop / 'JARVIS - STOP ALL.lnk'))
s2.TargetPath = os.path.join(f_root, 'JARVIS - STOP ALL.bat')
s2.WorkingDirectory = f_root
s2.IconLocation = 'shell32.dll,131'
s2.Description = '1-Click Stop All J.A.R.V.I.S. Services'
s2.Save()

# 3. JARVIS - MASTER DASHBOARD
s3 = shell.CreateShortCut(str(desktop / 'JARVIS - MASTER DASHBOARD.lnk'))
s3.TargetPath = 'http://127.0.0.1:8770'
s3.IconLocation = 'shell32.dll,14'
s3.Description = 'Open J.A.R.V.I.S. Master War Room & Control Center'
s3.Save()

# 4. JARVIS - GODS EYE 3D GLOBE
s4 = shell.CreateShortCut(str(desktop / 'JARVIS - GODS EYE 3D.lnk'))
s4.TargetPath = 'http://127.0.0.1:4173'
s4.IconLocation = 'shell32.dll,18'
s4.Description = 'Open J.A.R.V.I.S. God\'s Eye View 3D Globe (Port 4173)'
s4.Save()

print('Successfully created shortcuts on desktop:', desktop)
for f in desktop.glob('*JARVIS*'):
    print('  ->', f.name)
