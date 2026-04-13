#!/usr/bin/env python3
import argparse
import math
import os
import shutil
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urlparse


def run(cmd):
    return subprocess.run(cmd, check=True, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)


def parse_xrootd_url(url):
    parsed = urlparse(url)
    if parsed.scheme != "root":
        raise ValueError(f"Expected root:// URL, got: {url}")
    host = parsed.netloc
    path = parsed.path or "/"
    if not path.startswith("/"):
        path = "/" + path
    return host, path


def list_remote_root_files(remote_dir):
    host, path = parse_xrootd_url(remote_dir)
    out = run(["xrdfs", host, "ls", "-R", path]).stdout.splitlines()
    files = [f"root://{host}{line.strip()}" for line in out if line.strip().endswith(".root")]
    return sorted(files)


def chunk_list(items, size):
    return [items[i : i + size] for i in range(0, len(items), size)]


def hadd_chunk(chunk_id, files, workdir):
    output = os.path.join(workdir, f"partial_{chunk_id:04d}.root")
    cmd = ["hadd", "-f", "-k", output] + files
    run(cmd)
    return output


def copy_to_destination(local_file, destination, overwrite=False):
    if destination.startswith("root://"):
        cmd = ["xrdcp"]
        if overwrite:
            cmd.append("--force")
        cmd.extend([local_file, destination])
        run(cmd)
        return

    dest_dir = os.path.dirname(destination)
    if dest_dir:
        os.makedirs(dest_dir, exist_ok=True)
    if overwrite and os.path.exists(destination):
        os.remove(destination)
    shutil.copy2(local_file, destination)


def main():
    parser = argparse.ArgumentParser(
        description="Merge all ROOT files under a remote xrootd directory and copy the merged file to EOS."
    )
    parser.add_argument("remote_dir", help="Remote xrootd directory, e.g. root://se01.nchc.grid.org.tw//store/...")
    parser.add_argument("destination", help="Output file on EOS, either /eos/... or root://eosuser.cern.ch//eos/...")
    parser.add_argument("--chunk-size", type=int, default=100, help="Number of input files per partial hadd")
    parser.add_argument("--threads", type=int, default=4, help="Number of partial hadd jobs to run in parallel")
    parser.add_argument("--workdir", default=None, help="Temporary working directory for partial files")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite destination if it already exists")
    parser.add_argument("--keep-partials", action="store_true", help="Keep partial files and final local file")
    parser.add_argument("--dry-run", action="store_true", help="List files and planned chunks without merging")
    args = parser.parse_args()

    if args.chunk_size <= 0:
        raise ValueError("--chunk-size must be > 0")
    if args.threads <= 0:
        raise ValueError("--threads must be > 0")

    files = list_remote_root_files(args.remote_dir)
    if not files:
        raise RuntimeError(f"No ROOT files found under {args.remote_dir}")

    chunks = chunk_list(files, args.chunk_size)
    print(f"Found {len(files)} ROOT files")
    print(f"Will merge in {len(chunks)} chunk(s) with up to {args.threads} parallel hadd job(s)")

    if args.dry_run:
        for i, chunk in enumerate(chunks):
            print(f"chunk {i}: {len(chunk)} files")
        return

    cleanup_workdir = False
    workdir = args.workdir
    if workdir is None:
        workdir = tempfile.mkdtemp(prefix="tnp_merge_")
        cleanup_workdir = True
    else:
        os.makedirs(workdir, exist_ok=True)

    partials = []
    final_local = os.path.join(workdir, "merged.root")

    try:
        with ThreadPoolExecutor(max_workers=args.threads) as executor:
            futures = {
                executor.submit(hadd_chunk, chunk_id, chunk_files, workdir): chunk_id
                for chunk_id, chunk_files in enumerate(chunks)
            }
            for future in as_completed(futures):
                chunk_id = futures[future]
                partial = future.result()
                partials.append(partial)
                print(f"Finished partial {chunk_id}: {partial}")

        partials = sorted(partials)
        print(f"Merging {len(partials)} partial file(s) into {final_local}")
        run(["hadd", "-f", "-k", final_local] + partials)

        print(f"Copying merged file to {args.destination}")
        copy_to_destination(final_local, args.destination, overwrite=args.overwrite)
        print("Done")
    finally:
        if cleanup_workdir and not args.keep_partials and os.path.isdir(workdir):
            shutil.rmtree(workdir)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)
