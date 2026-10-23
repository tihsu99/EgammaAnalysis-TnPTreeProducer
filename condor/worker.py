"""Run in scratch, validate TnP output, then publish the ROOT file to EOS."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import time
from urllib.parse import urlsplit
import uuid


def run(*args):
    print("Running:", " ".join(map(str, args)), flush=True)
    subprocess.run(list(map(str, args)), check=True)


def inspect_root(filename, required):
    import ROOT

    handle = ROOT.TFile.Open(str(filename))
    if not handle or handle.IsZombie() or handle.TestBit(ROOT.TFile.kRecovered):
        raise RuntimeError("Invalid or recovered ROOT output: " + str(filename))
    entries = {}
    try:
        for name, flags in required.items():
            tree = handle.Get(name + "/fitter_tree")
            if not tree or not tree.InheritsFrom("TTree"):
                raise RuntimeError("Missing TnP tree: " + name)
            missing = set(flags) - {branch.GetName() for branch in tree.GetListOfBranches()}
            if missing:
                raise RuntimeError(name + " missing WP flags: " + ", ".join(sorted(missing)))
            entries[name] = int(tree.GetEntries())
            if entries[name] and tree.GetEntry(entries[name] - 1) <= 0:
                raise RuntimeError("Unreadable last entry in " + name)
            print(f"{name}: {entries[name]} probe pairs; {len(flags)} correctionlib flags", flush=True)
    finally:
        handle.Close()
    return entries


def stage_out(source, destination, attempts):
    parsed = urlsplit(destination)
    endpoint = "root://" + parsed.netloc
    remote = "/" + parsed.path.lstrip("/")
    temporary = remote + ".partial-" + uuid.uuid4().hex
    run("xrdfs", endpoint, "mkdir", "-p", str(Path(remote).parent))
    existing = subprocess.run(["xrdfs", endpoint, "stat", remote], capture_output=True, text=True)
    if existing.returncode == 0:
        raise RuntimeError("Output already exists; inspect it or use a new EOS outputdir: " + destination)
    try:
        for attempt in range(attempts):
            try:
                run("xrdcp", "--nopbar", "--force", "--cksum", "adler32", source, endpoint + "/" + temporary)
                break
            except subprocess.CalledProcessError:
                if attempt + 1 == attempts:
                    raise
                time.sleep(5 * (attempt + 1))
        run("xrdfs", endpoint, "mv", temporary, remote)
    except BaseException:
        subprocess.run(["xrdfs", endpoint, "rm", temporary], check=False)
        raise


def execute(job, local_max_events=None):
    for filename, expected in job["sha256"].items():
        if hashlib.sha256(Path(filename).read_bytes()).hexdigest() != expected:
            raise RuntimeError("Prepared asset changed: " + filename)
    if job.get("lumi_mask"):
        with Path("TnPTreeProducer_cfg.py").open("a") as handle:
            handle.write('\nfrom FWCore.PythonUtilities.LumiList import LumiList\n'
                         'process.source.lumisToProcess = LumiList(filename=' + repr(job["lumi_mask"]) + ').getVLuminosityBlockRange()\n')
    events = job["max_events"] if local_max_events is None else local_max_events
    run("cmsRun", "-j", "FrameworkJobReport.xml", "TnPTreeProducer_cfg.py",
        *job["cmsrun_args"], "inputFiles=" + ",".join(job["input_files"]), "maxEvents=" + str(events))
    output = Path(job["root_filename"])
    entries = inspect_root(output, job["required_trees"])
    if local_max_events is not None and not any(entries.values()):
        raise RuntimeError("No probe pairs in this local test; increase the event cap or check input/trigger/tag selection")
    report = dict(job, processed_max_events=events, entries=entries,
                  local_test=local_max_events is not None, output_bytes=output.stat().st_size)
    Path("receipt.json").write_text(json.dumps(report, indent=2) + "\n")
    if local_max_events is not None:
        print("LOCAL TEST PASSED; no EOS upload. Output:", output.resolve(), flush=True)
        return
    # Publish diagnostics before the ROOT file, which is the final completion artifact.
    published = []
    try:
        for filename, suffix in (("FrameworkJobReport.xml", ".xml"), ("receipt.json", ".json")):
            destination = job["output_url"] + suffix
            stage_out(filename, destination, job["stageout_attempts"])
            published.append(destination)
        stage_out(output, job["output_url"], job["stageout_attempts"])
    except BaseException:
        # Remove only diagnostics created by this attempt, so a failed upload can be retried.
        for destination in published:
            parsed = urlsplit(destination)
            subprocess.run(["xrdfs", "root://" + parsed.netloc, "rm", "/" + parsed.path.lstrip("/")], check=False)
        raise
    print("COMPLETE", job["output_url"], flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("job")
    parser.add_argument("--local-max-events", type=int)
    args = parser.parse_args()
    if args.local_max_events is not None and args.local_max_events < 1:
        parser.error("--local-max-events must be positive")
    execute(json.loads(Path(args.job).read_text()), args.local_max_events)


if __name__ == "__main__":
    main()
