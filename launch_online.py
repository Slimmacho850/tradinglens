import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

def find_cloudflared():
    downloads = Path.home() / "Downloads"
    candidates = [
        Path.cwd() / "cloudflared.exe",
        Path.cwd() / "cloudflared-windows-amd64.exe",
        downloads / "cloudflared.exe",
        downloads / "cloudflared-windows-amd64.exe",
        downloads / "cloudflared-windows-amd64 (1).exe",
    ]
    for c in candidates:
        if c.exists():
            return str(c)
    p = shutil.which("cloudflared")
    if p:
        return p
    return None

def find_app_file():
    candidates = [
        Path.cwd() / "app.py",
        Path.cwd() / "src" / "dashboard.py",
        Path.cwd() / "trading lens" / "trading lens" / "app.py",
        Path.cwd() / "trading lens" / "trading lens" / "src" / "dashboard.py",
    ]
    for c in candidates:
        if c.exists():
            return str(c)
    return "app.py"

def main():
    print("=" * 70)
    print("   DR LENS / TRADING LENS - 1-CLICK FREE ONLINE HOSTING")
    print("=" * 70)
    print("\n[1/3] Locating cloudflared tunnel client...")
    
    cf_bin = find_cloudflared()
    if not cf_bin:
        print("\n[ERROR] cloudflared was not found in Downloads or PATH.")
        print("Please download cloudflared-windows-amd64.exe to your Downloads folder.")
        input("\nPress Enter to exit...")
        return

    print(f"      Found: {cf_bin}")
    app_path = find_app_file()
    print(f"[2/3] Starting Streamlit server ({app_path})...")

    # Start Streamlit process
    streamlit_cmd = [sys.executable, "-m", "streamlit", "run", app_path, "--server.port=8501", "--server.headless=true", "--browser.gatherUsageStats=false"]
    st_proc = subprocess.Popen(
        streamlit_cmd,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )

    print("[3/3] Generating secure public URL (Cloudflare Tunnel)...")
    time.sleep(2)

    # Start Cloudflare tunnel process
    cf_cmd = [cf_bin, "tunnel", "--url", "http://localhost:8501"]
    cf_proc = subprocess.Popen(
        cf_cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace"
    )

    tunnel_url = None
    url_pattern = re.compile(r"https://[a-zA-Z0-9-]+\.trycloudflare\.com")

    # Read tunnel output to extract the public URL
    start_time = time.time()
    while time.time() - start_time < 30:
        line = cf_proc.stdout.readline()
        if not line:
            time.sleep(0.1)
            continue
        match = url_pattern.search(line)
        if match:
            tunnel_url = match.group(0)
            break

    if tunnel_url:
        print("\n" + "=" * 70)
        print("⚡ YOUR APP IS NOW LIVE ON THE INTERNET!")
        print("=" * 70)
        print(f"\n   📱 Open this link on your phone, laptop, or anywhere in the world:\n")
        print(f"   👉  {tunnel_url}\n")
        print("=" * 70)
        print("   NOTE: Keep this window open while you use the app.")
        print("   To stop the server, press Ctrl + C in this window.")
        print("=" * 70 + "\n")
    else:
        print("\n[!] Could not automatically capture the tunnel URL, but the tunnel is running.")
        print("    Check the log output below for the https://...trycloudflare.com address.")

    try:
        # Stream remaining logs or wait
        while True:
            line = cf_proc.stdout.readline()
            if not line and cf_proc.poll() is not None:
                break
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping servers...")
    finally:
        st_proc.terminate()
        cf_proc.terminate()
        print("Done.")

if __name__ == "__main__":
    main()
