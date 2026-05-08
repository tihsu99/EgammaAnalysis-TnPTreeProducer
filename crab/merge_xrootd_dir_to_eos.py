#!/usr/bin/env python3
import argparse
import os
import shutil
import subprocess
import sys
from urllib.parse import urlparse

from tqdm import tqdm


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
    return sorted(f"root://{host}{line.strip()}" for line in out if line.strip().endswith(".root"))


def chunk_list(items, size):
    return [items[i : i + size] for i in range(0, len(items), size)]


def stage_in_file(remote_file, local_dir, overwrite=False):
    local_path = os.path.join(local_dir, os.path.basename(urlparse(remote_file).path))
    if overwrite and os.path.exists(local_path):
        os.remove(local_path)
    run(["xrdcp", "--force", remote_file, local_path] if overwrite else ["xrdcp", remote_file, local_path])
    return local_path


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
        description="Stage in ROOT files chunk-by-chunk from xrootd, merge locally, and copy the final file to EOS."
    )
    parser.add_argument("remote_dir", help="Remote xrootd directory, e.g. root://se01.grid.nchc.org.tw//store/...")
    parser.add_argument("destination", help="Output file on EOS, either /eos/... or root://eosuser.cern.ch//eos/...")
    parser.add_argument("--chunk-size", type=int, default=100, help="Number of input files per partial hadd")
    parser.add_argument("--workdir", required=True, help="Working directory with enough free space")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite destination and local intermediates")
    parser.add_argument("--keep-partials", action="store_true", help="Keep partial files and staged-in chunk files")
    parser.add_argument("--dry-run", action="store_true", help="List files and planned chunks without merging")
    args = parser.parse_args()

    if args.chunk_size <= 0:
        raise ValueError("--chunk-size must be > 0")

    os.makedirs(args.workdir, exist_ok=True)
    files = list_remote_root_files(args.remote_dir)
    if not files:
        raise RuntimeError(f"No ROOT files found under {args.remote_dir}")

    args.worker = args.destination

    chunks = chunk_list(files, args.chunk_size)
    print(f"Found {len(files)} ROOT files")
    print(f"Will process {len(chunks)} chunk(s)")
    print(f"Working directory: {args.workdir}")

    if args.dry_run:
        for i, chunk in enumerate(chunks):
            print(f"chunk {i}: {len(chunk)} files")
        return

    partials = []
    final_local = os.path.join(args.workdir, "merged.root")
    if args.overwrite and os.path.exists(final_local):
        os.remove(final_local)

    os.makedirs(os.path.dirname(args.workdir), exist_ok=True)

    for chunk_id, chunk in enumerate(tqdm(chunks, desc="chunks", unit="chunk"), start=1):
        chunk_dir = os.path.join(args.workdir, f"chunk_{chunk_id:04d}")
        os.makedirs(chunk_dir, exist_ok=True)

        local_inputs = []
        with tqdm(total=len(chunk), desc=f"stage-in {chunk_id}/{len(chunks)}", unit="file", leave=False) as pbar:
            for remote_file in chunk:
                local_inputs.append(stage_in_file(remote_file, chunk_dir, overwrite=args.overwrite))
                pbar.update(1)

        partial = os.path.join(args.workdir, f"partial_{chunk_id:04d}.root")
        if args.overwrite and os.path.exists(partial):
            os.remove(partial)
        tqdm.write(f"[{chunk_id}/{len(chunks)}] hadd -> {partial}")
        run(["hadd", "-f", "-k", partial] + local_inputs)
        partials.append(partial)

        if not args.keep_partials:
            shutil.rmtree(chunk_dir)

    tqdm.write(f"Final hadd of {len(partials)} partial file(s) -> {final_local}")
    run(["hadd", "-f", "-k", final_local] + partials)

    # tqdm.write(f"Copying merged file to {args.destination}")
    # copy_to_destination(final_local, args.destination, overwrite=args.overwrite)
    tqdm.write("Done")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)
