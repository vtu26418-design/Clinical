"""Download a user-selected frozen AACT ZIP and verify its independently recorded SHA-256."""
import argparse
from datetime import date, datetime, timezone
import hashlib
import json
from pathlib import Path
import re
from urllib.parse import urlsplit, urlunsplit
from urllib.request import urlopen
import zipfile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", required=True, help="Exact HTTPS snapshot URL acquired from the official AACT download page")
    parser.add_argument("--sha256", required=True, help="Expected 64-character SHA-256 from a trusted acquisition record")
    parser.add_argument("--snapshot-date", required=True, help="Frozen snapshot date YYYY-MM-DD")
    parser.add_argument("--output", required=True, help="New .zip path; existing raw files are never overwritten")
    args = parser.parse_args()
    parsed = urlsplit(args.url)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
        parser.error("Supply an HTTPS URL without embedded credentials.")
    if not re.fullmatch(r"[a-fA-F0-9]{64}", args.sha256):
        parser.error("--sha256 must contain 64 hexadecimal characters.")
    date.fromisoformat(args.snapshot_date)
    target = Path(args.output)
    receipt = target.with_suffix(target.suffix + ".acquisition.json")
    temporary = target.with_suffix(target.suffix + ".part")
    if target.exists() or receipt.exists() or temporary.exists():
        parser.error("Output, receipt or partial download already exists; choose a new path.")
    target.parent.mkdir(parents=True, exist_ok=True)
    digest, size = hashlib.sha256(), 0
    try:
        with urlopen(args.url, timeout=60) as response, temporary.open("xb") as output:
            if urlsplit(response.url).scheme != "https":
                raise ValueError("Snapshot download redirected away from HTTPS.")
            for block in iter(lambda: response.read(1024 * 1024), b""):
                digest.update(block)
                output.write(block)
                size += len(block)
        if digest.hexdigest() != args.sha256.lower():
            raise ValueError("Downloaded checksum differs from the expected SHA-256; no raw snapshot saved.")
        if not zipfile.is_zipfile(temporary):
            raise ValueError("Downloaded bytes are not a ZIP archive (an authentication page may have been returned).")
        # Link publishes without replacing a preexisting target, then remove the partial name.
        target.hardlink_to(temporary)
        temporary.unlink()
        receipt.write_text(json.dumps({"snapshot_date": args.snapshot_date, "sha256": digest.hexdigest(), "bytes": size,
                                      "source_url": urlunsplit((parsed.scheme, parsed.netloc, parsed.path, "", "")),
                                      "downloaded_at": datetime.now(timezone.utc).isoformat(), "checksum_verified": True}, indent=2), encoding="utf-8")
        print(f"Verified frozen archive: {target} ({size:,} bytes). Extract to a new raw directory, then run verify_aact.py.")
    except Exception:
        temporary.unlink(missing_ok=True)
        raise


if __name__ == "__main__":
    main()
