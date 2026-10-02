import os
import sys
import time
import hashlib
import urllib.request

DATASET_URL = "https://pub-3483b4c265914de3a2a27c0a3b2076ee.r2.dev/d0nj0n_mlkem_dataset.zip"
TARGET_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "datasets")
TARGET_FILE = os.path.join(TARGET_DIR, "d0nj0n_mlkem_dataset.zip")
CHECKSUM_FILE = os.path.join(TARGET_DIR, "d0nj0n_mlkem_dataset_sha256.txt")
CHUNK_SIZE = 8 * 1024 * 1024  # 8 MB chunks

def download_dataset():
    os.makedirs(TARGET_DIR, exist_ok=True)
    print("=" * 75)
    print("  PHASE C: MAGAZIN & ABDELLATIF DATASET DOWNLOAD & SHA-256 VERIFICATION")
    print("=" * 75)
    print(f"[*] Target URL:      {DATASET_URL}")
    print(f"[*] Destination:     {TARGET_FILE}")
    print(f"[*] Checksum output: {CHECKSUM_FILE}\n")

    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}

    max_retries = 20
    retries = 0
    total_bytes = None

    while True:
        downloaded_bytes = 0
        if os.path.exists(TARGET_FILE):
            downloaded_bytes = os.path.getsize(TARGET_FILE)

        if total_bytes is not None and downloaded_bytes >= total_bytes:
            print(f"[*] All {total_bytes:,} bytes downloaded successfully!")
            break

        req = urllib.request.Request(DATASET_URL, headers=headers)
        if downloaded_bytes > 0:
            req.headers['Range'] = f"bytes={downloaded_bytes}-"
            print(f"[*] Resuming from byte {downloaded_bytes:,} ({downloaded_bytes / (1024**3):.2f} GB)...")

        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                content_range = resp.headers.get('Content-Range')
                if content_range:
                    total_bytes = int(content_range.split('/')[-1])
                elif total_bytes is None:
                    total_bytes = int(resp.headers.get('Content-Length', 0)) + downloaded_bytes

                print(f"[*] Total file size: {total_bytes / (1024**3):.2f} GB ({total_bytes:,} bytes)")
                
                mode = 'ab' if downloaded_bytes > 0 and resp.status == 206 else 'wb'
                if mode == 'wb':
                    downloaded_bytes = 0

                start_time = time.time()
                last_log_time = start_time
                last_bytes = downloaded_bytes

                with open(TARGET_FILE, mode) as out_f:
                    while downloaded_bytes < total_bytes:
                        chunk = resp.read(CHUNK_SIZE)
                        if not chunk:
                            print("[*] Connection closed by server. Preparing to resume...")
                            break
                        out_f.write(chunk)
                        downloaded_bytes += len(chunk)

                        now = time.time()
                        if now - last_log_time >= 15.0 or downloaded_bytes == total_bytes:
                            speed = (downloaded_bytes - last_bytes) / (now - last_log_time) / (1024**2)
                            pct = (downloaded_bytes / total_bytes) * 100 if total_bytes else 0
                            print(f"[*] Progress: {downloaded_bytes / (1024**3):.2f} / {total_bytes / (1024**3):.2f} GB "
                                  f"({pct:.1f}%) | Speed: {speed:.2f} MB/s | Elapsed: {int(now - start_time)}s", flush=True)
                            last_log_time = now
                            last_bytes = downloaded_bytes

                if downloaded_bytes >= total_bytes:
                    print("\n[+] Full file received! Verifying completeness...")
                    break

        except Exception as e:
            retries += 1
            print(f"[-] Connection error: {e}. Retrying ({retries}/{max_retries}) in 5s...", file=sys.stderr)
            time.sleep(5)
            if retries >= max_retries:
                print("[-] Exceeded max retries!", file=sys.stderr)
                sys.exit(1)

    print("\n[+] Download completed successfully! Computing SHA-256 checksum...")
    sha256 = hashlib.sha256()
    with open(TARGET_FILE, 'rb') as f:
        while True:
            data = f.read(64 * 1024 * 1024)
            if not data:
                break
            sha256.update(data)
    
    digest = sha256.hexdigest()
    print(f"\n[+] SHA-256 CHECKSUM: {digest}")
    
    with open(CHECKSUM_FILE, 'w') as f_sum:
        f_sum.write(f"# Magazin & Abdellatif (ePrint 2026/1851) Dataset Archive\n")
        f_sum.write(f"# Source: {DATASET_URL}\n")
        f_sum.write(f"# Size: {total_bytes} bytes\n")
        f_sum.write(f"SHA256 (d0nj0n_mlkem_dataset.zip) = {digest}\n")
    
    print(f"[+] Recorded checksum to: {CHECKSUM_FILE}")
    print("=" * 75)

if __name__ == '__main__':
    download_dataset()
