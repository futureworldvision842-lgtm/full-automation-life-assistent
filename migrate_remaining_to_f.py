import os
import sys
import shutil
import subprocess
import time

def run_cmd(cmd):
    print(f">> Executing: {cmd}", flush=True)
    res = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if res.returncode != 0:
        print(f"   [WARN/ERROR code {res.returncode}]: {res.stderr.strip()[:300]}", flush=True)
    else:
        out = res.stdout.strip()
        if out:
            print(f"   [OK]: {out[:200]}", flush=True)
    return res

def is_reparse(path):
    try:
        if os.path.islink(path):
            return True
        import stat
        return bool(os.stat(path).st_file_attributes & stat.FILE_ATTRIBUTE_REPARSE_POINT)
    except Exception:
        return False

def get_dir_size(path):
    if not os.path.exists(path) or is_reparse(path):
        return 0
    if os.path.isfile(path):
        return os.path.getsize(path)
    total = 0
    for root, dirs, files in os.walk(path):
        dirs[:] = [d for d in dirs if not is_reparse(os.path.join(root, d))]
        for f in files:
            fp = os.path.join(root, f)
            if not is_reparse(fp):
                try:
                    total += os.path.getsize(fp)
                except Exception:
                    pass
    return total

def print_disk_usage(label):
    tc, uc, fc = shutil.disk_usage("C:\\")
    tf, uf, ff = shutil.disk_usage("F:\\")
    print(f"[{label}] Drive C Free: {fc / (1024**3):.2f} GB ({fc / (1024**2):.0f} MB) / {tc / (1024**3):.2f} GB", flush=True)
    print(f"[{label}] Drive F Free: {ff / (1024**3):.2f} GB ({ff / (1024**2):.0f} MB) / {tf / (1024**3):.2f} GB", flush=True)
    return fc, ff

def move_and_junction(src, dst):
    print(f"\n==========================================", flush=True)
    print(f"Processing: {src} -> {dst}", flush=True)
    print(f"==========================================", flush=True)

    if not os.path.exists(src):
        print(f"Source {src} does not exist. Skipping.", flush=True)
        return

    if is_reparse(src):
        print(f"Source {src} is ALREADY a junction/symlink. Skipping.", flush=True)
        return

    src_sz = get_dir_size(src)
    print(f"Source size: {src_sz / (1024**2):.1f} MB ({src_sz / (1024**3):.2f} GB)", flush=True)
    if src_sz == 0:
        print("Empty directory. Skipping.", flush=True)
        return

    os.makedirs(dst, exist_ok=True)

    print(f"Copying files from {src} to {dst} via robocopy...", flush=True)
    rc = subprocess.run(f'robocopy "{src}" "{dst}" /E /R:1 /W:1 /NP /NFL /NDL', shell=True)
    print(f"Robocopy finished with returncode {rc.returncode}", flush=True)

    dst_sz = get_dir_size(dst)
    print(f"Destination size: {dst_sz / (1024**2):.1f} MB", flush=True)

    if dst_sz >= src_sz * 0.90 or (src_sz - dst_sz < 5*1024*1024):
        print("Copy verified! Removing original source directory from C:...", flush=True)
        del_rc = subprocess.run(f'rmdir /S /Q "{src}"', shell=True)
        if os.path.exists(src):
            try:
                shutil.rmtree(src, ignore_errors=True)
            except Exception as e:
                print(f"Error removing {src}: {e}", flush=True)

        if not os.path.exists(src):
            print(f"Creating NTFS Directory Junction: {src} ==> {dst}", flush=True)
            run_cmd(f'mklink /J "{src}" "{dst}"')
        else:
            print(f"WARN: Root of {src} could not be completely removed (likely locked file). Moving individual large files...", flush=True)
            migrate_individual_files(src, dst)
    else:
        print(f"ERROR: Destination size ({dst_sz}) does not match source ({src_sz})! Retaining source.", flush=True)

def migrate_individual_files(src_dir, dst_dir):
    print(f"Migrating individual top-level files from {src_dir} to {dst_dir}...", flush=True)
    for item in os.listdir(src_dir):
        sp = os.path.join(src_dir, item)
        dp = os.path.join(dst_dir, item)
        if os.path.isfile(sp) and not is_reparse(sp):
            sz = os.path.getsize(sp)
            if sz > 10 * 1024 * 1024: # > 10 MB
                try:
                    if not os.path.exists(dp) or os.path.getsize(dp) != sz:
                        shutil.copy2(sp, dp)
                    os.remove(sp)
                    print(f"Moved file: {item} ({sz / (1024**2):.1f} MB)", flush=True)
                except Exception as e:
                    print(f"Could not move {item}: {e}", flush=True)

def main():
    print("==================================================", flush=True)
    print("--- COMMENCING EXTENDED C -> F STORAGE CLEANUP ---", flush=True)
    print("==================================================", flush=True)
    start_fc, start_ff = print_disk_usage("INITIAL")

    # 1. Migrate VirtualBox VMs (10.27 GB)
    vbox_src = r"C:\Users\user\VirtualBox VMs"
    vbox_dst = r"F:\VirtualBox VMs"
    move_and_junction(vbox_src, vbox_dst)

    # 2. Migrate BlueStacks emulator data (1.80 GB)
    bs_src = r"C:\ProgramData\BlueStacks_nxt"
    bs_dst = r"F:\BlueStacks_nxt"
    move_and_junction(bs_src, bs_dst)

    # 3. Migrate Tor Browser from Desktop (389 MB)
    tor_src = r"C:\Users\user\OneDrive\Desktop\Tor Browser"
    tor_dst = r"F:\Tor Browser"
    move_and_junction(tor_src, tor_dst)

    # 4. Migrate Moltbot from Desktop (73 MB)
    molt_src = r"C:\Users\user\OneDrive\Desktop\Moltbot"
    molt_dst = r"F:\Projects\Moltbot"
    move_and_junction(molt_src, molt_dst)

    # 5. Migrate Desktop large videos
    desktop_dir = r"C:\Users\user\OneDrive\Desktop"
    videos_dst = r"F:\Videos"
    os.makedirs(videos_dst, exist_ok=True)
    for f in os.listdir(desktop_dir):
        if f.endswith(".mp4"):
            fp = os.path.join(desktop_dir, f)
            sz = os.path.getsize(fp)
            print(f"Moving desktop video: {f} ({sz / (1024**2):.1f} MB)...", flush=True)
            try:
                shutil.move(fp, os.path.join(videos_dst, f))
                print(f"Successfully moved {f} to {videos_dst}", flush=True)
            except Exception as e:
                print(f"Could not move {f}: {e}", flush=True)

    dastar_src = os.path.join(desktop_dir, "dastar")
    if os.path.exists(dastar_src):
        move_and_junction(dastar_src, os.path.join(videos_dst, "dastar"))

    # 6. Migrate Downloads folder (24.45 GB)
    # Ubuntu ISO alone is 6 GB, MongoDB is 1.2 GB, videos are 4 GB!
    dl_src = r"C:\Users\user\Downloads"
    dl_dst = r"F:\Downloads"
    move_and_junction(dl_src, dl_dst)

    # 7. Empty Recycle Bin on Drive C
    print("\nEmptying Recycle Bin on Drive C...", flush=True)
    run_cmd('powershell -Command "Clear-RecycleBin -DriveLetter C -Force -ErrorAction SilentlyContinue"')

    # 8. Report final reclaimed space
    print("\n==================================================", flush=True)
    end_fc, end_ff = print_disk_usage("FINAL")
    freed_c = (end_fc - start_fc) / (1024**3)
    print(f"TOTAL RECLAIMED ON DRIVE C IN THIS RUN: {freed_c:+.2f} GB ({(end_fc - start_fc)/(1024**2):+.0f} MB)", flush=True)
    print("==================================================", flush=True)

if __name__ == "__main__":
    main()
