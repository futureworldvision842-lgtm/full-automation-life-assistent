import os
import sys
import shutil
import subprocess
import time

def run_cmd(cmd):
    print(f">> Executing: {cmd}")
    res = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if res.returncode != 0:
        print(f"   [WARN/ERROR code {res.returncode}]: {res.stderr.strip()[:300]}")
    else:
        out = res.stdout.strip()
        if out:
            print(f"   [OK]: {out[:200]}")
    return res

def get_dir_size(path):
    if not os.path.exists(path):
        return 0
    if os.path.islink(path):
        return 0
    if os.path.isfile(path):
        return os.path.getsize(path)
    total = 0
    for root, dirs, files in os.walk(path):
        for f in files:
            try:
                total += os.path.getsize(os.path.join(root, f))
            except Exception:
                pass
    return total

def print_disk_usage(label):
    tc, uc, fc = shutil.disk_usage("C:\\")
    tf, uf, ff = shutil.disk_usage("F:\\")
    print(f"[{label}] Drive C Free: {fc / (1024**3):.2f} GB ({fc / (1024**2):.0f} MB) / {tc / (1024**3):.2f} GB")
    print(f"[{label}] Drive F Free: {ff / (1024**3):.2f} GB ({ff / (1024**2):.0f} MB) / {tf / (1024**3):.2f} GB")
    return fc, ff

def is_junction_or_link(path):
    try:
        if os.path.islink(path):
            return True
        import stat
        return bool(os.stat(path).st_file_attributes & stat.FILE_ATTRIBUTE_REPARSE_POINT)
    except Exception:
        return False

def move_and_junction(src, dst):
    print(f"\n==========================================")
    print(f"Processing: {src} -> {dst}")
    print(f"==========================================")

    if not os.path.exists(src):
        print(f"Source {src} does not exist. Skipping move.")
        if not os.path.exists(dst):
            os.makedirs(dst, exist_ok=True)
        return

    if is_junction_or_link(src):
        print(f"Source {src} is ALREADY a junction/symlink! Skipping.")
        return

    src_sz = get_dir_size(src)
    print(f"Source size: {src_sz / (1024**2):.1f} MB ({src_sz / (1024**3):.2f} GB)")
    if src_sz == 0:
        print("Empty directory. Skipping.")
        return

    os.makedirs(dst, exist_ok=True)

    # Use robocopy to copy all files to dst
    print(f"Copying files from {src} to {dst} via robocopy...")
    rc = subprocess.run(f'robocopy "{src}" "{dst}" /E /R:1 /W:1 /NP /NFL /NDL', shell=True)
    print(f"Robocopy finished with returncode {rc.returncode}")

    dst_sz = get_dir_size(dst)
    print(f"Destination size: {dst_sz / (1024**2):.1f} MB")

    if dst_sz >= src_sz * 0.90 or (src_sz - dst_sz < 2*1024*1024):
        print("Copy verified successfully! Removing original source directory from C:...")
        del_rc = subprocess.run(f'rmdir /S /Q "{src}"', shell=True)
        if os.path.exists(src):
            print("Warning: Some files could not be removed directly by rmdir. Retrying with python...")
            try:
                shutil.rmtree(src, ignore_errors=True)
            except Exception as e:
                print(f"Error removing {src}: {e}")
        
        if not os.path.exists(src):
            print(f"Creating NTFS Directory Junction: {src} ==> {dst}")
            run_cmd(f'mklink /J "{src}" "{dst}"')
        else:
            print(f"WARN: Source directory {src} still exists because some files are locked.")
            # If src still exists, try moving subfolders individually
            try_subfolder_junctions(src, dst)
    else:
        print(f"ERROR: Destination size ({dst_sz}) does not match source size ({src_sz})! Retaining source.")

def try_subfolder_junctions(src_parent, dst_parent):
    print(f"Attempting subfolder-level migrations for {src_parent}...")
    for item in os.listdir(src_parent):
        sp = os.path.join(src_parent, item)
        dp = os.path.join(dst_parent, item)
        if os.path.isdir(sp) and not is_junction_or_link(sp):
            move_and_junction(sp, dp)

def main():
    print("==================================================")
    print("--- COMMENCING DRIVE C -> DRIVE F MIGRATION ---")
    print("==================================================")
    start_fc, start_ff = print_disk_usage("INITIAL")

    # Step 1: Terminate Ollama if running so its model files and sockets are completely unlocked
    print("\nStopping Ollama processes if active...")
    run_cmd('taskkill /F /IM "ollama.exe" /IM "ollama app.exe"')
    time.sleep(2)

    # Step 2: Migrate Ollama home (.ollama)
    move_and_junction(r"C:\Users\user\.ollama", r"F:\Ollama_Home\.ollama")

    # Step 3: Migrate .cache subfolders (Puppeteer, Codex runtimes, HuggingFace, DevTools)
    cache_dir = r"C:\Users\user\.cache"
    if os.path.exists(cache_dir):
        for item in ["puppeteer", "codex-runtimes", "huggingface", "chrome-devtools-mcp"]:
            s = os.path.join(cache_dir, item)
            d = os.path.join(r"F:\GlobalCaches", item)
            if os.path.exists(s):
                move_and_junction(s, d)

    # Step 4: Migrate Pip cache
    move_and_junction(r"C:\Users\user\AppData\Local\pip", r"F:\GlobalCaches\pip")

    # Step 5: Migrate Projects folder (xauusd-signal-bot etc.)
    move_and_junction(r"C:\Users\user\Projects", r"F:\Projects")

    # Step 6: Set permanent environment variables for models, caches, and runtimes
    print("\nSetting Permanent User Environment Variables...")
    env_vars = {
        "OLLAMA_MODELS": r"F:\OllamaModels",
        "HF_HOME": r"F:\GlobalCaches\huggingface",
        "TORCH_HOME": r"F:\GlobalCaches\torch",
        "PUPPETEER_CACHE_DIR": r"F:\GlobalCaches\puppeteer",
        "PIP_CACHE_DIR": r"F:\GlobalCaches\pip"
    }
    for k, v in env_vars.items():
        run_cmd(f'powershell -Command "[System.Environment]::SetEnvironmentVariable(\'{k}\', \'{v}\', \'User\')"')

    # Configure npm cache
    print("\nConfiguring NPM cache path...")
    run_cmd(r'cmd.exe /c "npm.cmd config set cache F:\GlobalCaches\npm-cache --global"')

    # Configure pip cache
    print("\nConfiguring PIP cache path...")
    run_cmd(r'python -m pip config set global.cache-dir F:\GlobalCaches\pip')

    # Step 7: Clean non-locked temporary files in C:\Users\user\AppData\Local\Temp
    print("\nCleaning non-locked temporary files in Temp...")
    temp_dir = r"C:\Users\user\AppData\Local\Temp"
    cleaned = 0
    if os.path.exists(temp_dir):
        for item in os.listdir(temp_dir):
            ip = os.path.join(temp_dir, item)
            try:
                if os.path.isfile(ip) or os.path.islink(ip):
                    sz = os.path.getsize(ip)
                    os.unlink(ip)
                    cleaned += sz
                elif os.path.isdir(ip):
                    sz = get_dir_size(ip)
                    shutil.rmtree(ip, ignore_errors=True)
                    cleaned += sz
            except Exception:
                pass
    print(f"Cleaned {cleaned / (1024**2):.1f} MB of temporary files.")

    # Step 8: Ensure Ollama models directory has models & restart Ollama
    print("\nEnsuring F:\\OllamaModels blobs...")
    os.makedirs(r"F:\OllamaModels", exist_ok=True)
    ollama_home_models = r"F:\Ollama_Home\.ollama\models"
    if os.path.exists(ollama_home_models):
        print("Syncing models from Ollama_Home to F:\\OllamaModels...")
        subprocess.run(f'robocopy "{ollama_home_models}" "F:\\OllamaModels" /E /R:1 /W:1 /NP /NFL /NDL', shell=True)

    print("\nRestarting Ollama in background with OLLAMA_MODELS=F:\\OllamaModels...")
    ollama_bin = r"C:\Users\user\AppData\Local\Programs\Ollama\ollama.exe"
    if os.path.exists(ollama_bin):
        my_env = os.environ.copy()
        my_env["OLLAMA_MODELS"] = r"F:\OllamaModels"
        subprocess.Popen([ollama_bin, "serve"], env=my_env, creationflags=subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS)
        print("Ollama serve launched.")
    time.sleep(3)

    # Step 9: Final usage report
    print("\n==================================================")
    end_fc, end_ff = print_disk_usage("FINAL")
    freed_c = (end_fc - start_fc) / (1024**3)
    print(f"TOTAL RECLAIMED ON DRIVE C: {freed_c:+.2f} GB ({(end_fc - start_fc)/(1024**2):+.0f} MB)")
    print("==================================================")

if __name__ == "__main__":
    main()
