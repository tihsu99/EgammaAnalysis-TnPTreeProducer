"""Run in scratch, validate TnP output, then publish the ROOT file to EOS."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import time
import tarfile
import xml.etree.ElementTree as ET
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


def input_failure(report_path, log_path, returncode):
    """Classify the fatal exception, never just the truncated shell exit code."""
    with log_path.open("rb") as handle:
        handle.seek(max(0, log_path.stat().st_size - 65536))
        detail = handle.read().decode("utf-8", errors="replace")
    # Earlier warnings must not supply input context for an unrelated fatal error.
    marker = detail.rfind("----- Begin Fatal Exception")
    if marker >= 0:
        detail = detail[marker:]
    categories = re.findall(r"An exception of category '([^']+)'", detail)
    try:
        errors = ET.parse(report_path).getroot().findall("FrameworkError")
    except (OSError, ET.ParseError):
        errors = []
    for error in errors:
        text = "".join(error.itertext())
        found = re.findall(r"An exception of category '([^']+)'", text)
        categories.extend(found or [error.get("Type", "Unknown")])
        detail += "\n" + text
    # FatalRootError is also used for output errors; require explicit input-source context.
    categories = set(categories)
    allowed = categories <= {"FileOpenError", "FileReadError"}
    if categories == {"FatalRootError"}:
        allowed = any(name in detail for name in ("InputSource::", "RootInputFileSequence::", "RootFile::read"))
    reason = detail[-8000:]
    return dict(category=", ".join(sorted(categories)) or "Unknown", reason=reason,
                skippable=returncode > 0 and bool(categories) and allowed)


def process_individually(job, events):
    output = Path(job["root_filename"])
    reports, parts = Path("file_reports"), Path("file_outputs")
    reports.mkdir()
    parts.mkdir()
    records, blacklist, good = [], [], []
    remaining = events
    total = len(job["input_files"])
    started = time.monotonic()
    for index, source in enumerate(job["input_files"]):
        if remaining == 0:
            break
        filled = 20 * index // total
        print(f"Files [{'#' * filled}{'-' * (20 - filled)}] {index}/{total} "
              f"({100 * index // total}%) | running {source}", flush=True)
        report_path = reports / f"input_{index:05d}.xml"
        log_path = reports / f"input_{index:05d}.log"
        command = ["cmsRun", "-j", str(report_path), "TnPTreeProducer_cfg.py",
                   *job["cmsrun_args"], "inputFiles=" + source, "maxEvents=" + str(remaining)]
        print("Running:", " ".join(command), flush=True)
        with log_path.open("w") as log:
            with subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                  text=True, errors="replace") as process:
                for line in process.stdout:
                    log.write(line)
                    print(line, end="", flush=True)
                code = process.wait()
        record = dict(input_file=source, returncode=code, max_events=remaining,
                      framework_report=str(report_path), log=str(log_path))
        if code:
            failure = input_failure(report_path, log_path, code)
            record.update(failure)
            output.unlink(missing_ok=True)
            if not job.get("skip_bad_files", False) or not failure["skippable"]:
                raise RuntimeError(f"Non-skippable cmsRun failure ({code}, {failure['category']}) for {source}; see {log_path}")
            record["status"] = "skipped"
            blacklist.append(record)
            # Retain every skip immediately, including jobs where all inputs eventually fail.
            Path("blacklist.json").write_text(json.dumps(dict(job_id=job["job_id"],
                dataset=job.get("dataset"), files=blacklist), indent=2) + "\n")
            print("BLACKLIST:", json.dumps(record), flush=True)
        else:
            report = ET.parse(report_path).getroot()
            if report.findall("FrameworkError"):
                raise RuntimeError(f"cmsRun returned success with FrameworkError in {report_path}")
            inputs = [item for item in report.findall("InputFile")
                      if item.findtext("InputType") == "primaryFiles"]
            if not inputs:
                raise RuntimeError(f"Missing primary input event count in {report_path}")
            counts = [int(item.findtext("EventsRead", "-1")) for item in inputs]
            if min(counts) < 0:
                raise RuntimeError(f"Invalid primary input event count in {report_path}")
            read = sum(counts)
            if remaining != -1:
                if read > remaining:
                    raise RuntimeError(f"Event cap exceeded in {report_path}")
                remaining -= read
            entries = inspect_root(output, job["required_trees"])
            part = parts / f"input_{index:05d}.root"
            output.rename(part)
            good.append(part)
            record.update(status="success", events_read=read, entries=entries)
        records.append(record)
        done = index + 1
        filled = 20 * done // total
        print(f"Files [{'#' * filled}{'-' * (20 - filled)}] {done}/{total} "
              f"({100 * done // total}%) | good={len(good)} skipped={len(blacklist)} "
              f"elapsed={time.monotonic() - started:.0f}s", flush=True)
    if not good:
        raise RuntimeError("No successful inputs; no ROOT output published. See BLACKLIST lines and blacklist.json")
    Path("blacklist.json").write_text(json.dumps(dict(job_id=job["job_id"],
        dataset=job.get("dataset"), files=blacklist), indent=2) + "\n")
    if len(good) == 1:
        good[0].rename(output)
    else:
        print(f"Merging {len(good)} successful input outputs in scratch", flush=True)
        run("hadd", "-f", output, *good)
    entries = inspect_root(output, job["required_trees"])
    expected = {name: sum(record["entries"][name] for record in records if record["status"] == "success")
                for name in job["required_trees"]}
    if entries != expected:
        raise RuntimeError(f"Merged probe counts differ: expected {expected}, found {entries}")
    for part in good:
        part.unlink(missing_ok=True)
    with tarfile.open("file_reports.tar.gz", "w:gz") as archive:
        archive.add(reports, arcname=reports.name)
    return entries, dict(files=records,
        successful_input_files=[r["input_file"] for r in records if r["status"] == "success"],
        skipped_input_files=[r["input_file"] for r in blacklist],
        unattempted_input_files=job["input_files"][len(records):],
        events_read=sum(r["events_read"] for r in records if r["status"] == "success"))


def execute(job, local_max_events=None):
    for filename, expected in job["sha256"].items():
        if hashlib.sha256(Path(filename).read_bytes()).hexdigest() != expected:
            raise RuntimeError("Prepared asset changed: " + filename)
    if job.get("lumi_mask"):
        with Path("TnPTreeProducer_cfg.py").open("a") as handle:
            handle.write('\nfrom FWCore.PythonUtilities.LumiList import LumiList\n'
                         'process.source.lumisToProcess = LumiList(filename=' + repr(job["lumi_mask"]) + ').getVLuminosityBlockRange()\n')
    events = job["max_events"] if local_max_events is None else local_max_events
    output = Path(job["root_filename"])
    details = {}
    if job.get("process_files_individually", False):
        entries, details = process_individually(job, events)
        diagnostics = [("file_reports.tar.gz", ".reports.tar.gz"), ("blacklist.json", ".blacklist.json")]
    else:
        run("cmsRun", "-j", "FrameworkJobReport.xml", "TnPTreeProducer_cfg.py",
            *job["cmsrun_args"], "inputFiles=" + ",".join(job["input_files"]), "maxEvents=" + str(events))
        entries = inspect_root(output, job["required_trees"])
        diagnostics = [("FrameworkJobReport.xml", ".xml")]
    if local_max_events is not None and not any(entries.values()):
        raise RuntimeError("No probe pairs in this local test; increase the event cap or check input/trigger/tag selection")
    report = dict(job, processed_max_events=events, entries=entries,
                  local_test=local_max_events is not None, output_bytes=output.stat().st_size, **details)
    Path("receipt.json").write_text(json.dumps(report, indent=2) + "\n")
    if local_max_events is not None:
        print("LOCAL TEST PASSED; no EOS upload. Output:", output.resolve(), flush=True)
        return
    # Publish diagnostics before the ROOT file, which is the final completion artifact.
    published = []
    try:
        for filename, suffix in [*diagnostics, ("receipt.json", ".json")]:
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
