#!/usr/bin/env python3
"""Prepare TnP job shells for local testing and later Condor submission."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import sys
import threading
import time
from urllib.parse import urlsplit
from urllib.request import urlopen

import yaml

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "python"))
from scoutingCorrectionlib_cff import load_working_points


class Progress:
    """Keep elapsed time visible even while a blocking DAS or filesystem call waits."""

    def __init__(self, label, total, unit, stream=None, interval=None):
        self.label, self.total, self.unit = label, total, unit
        self.stream = sys.stderr if stream is None else stream
        self.terminal = self.stream.isatty()
        self.interval = (0.25 if self.terminal else 5.) if interval is None else interval
        self.completed, self.detail, self.width = 0, "", 0
        self.started, self.last_render = time.monotonic(), 0.
        self.lock, self.stop = threading.Lock(), threading.Event()

    def __enter__(self):
        self.render(force=True)
        self.thread = threading.Thread(target=self.refresh, daemon=True)
        self.thread.start()
        return self

    def refresh(self):
        while not self.stop.wait(self.interval):
            self.render()

    def describe(self, detail):
        with self.lock:
            self.detail = detail
        self.render(force=True)

    def advance(self, detail=None):
        with self.lock:
            self.completed += 1
            if detail is not None:
                self.detail = detail
        self.render()

    def render(self, force=False, failed=False):
        with self.lock:
            now = time.monotonic()
            if not force and now - self.last_render < self.interval:
                return
            fraction = self.completed / self.total if self.total else 0.
            filled = int(20 * fraction)
            elapsed = int(now - self.started)
            label = self.label + (" FAILED" if failed else "")
            line = (f"{label} [{'#' * filled}{'-' * (20 - filled)}] "
                    f"{self.completed}/{self.total} {self.unit} ({fraction:.0%}) "
                    f"{elapsed // 60:02d}:{elapsed % 60:02d}")
            if self.detail:
                line += " | " + self.detail
            if self.terminal:
                line = line[:max(20, shutil.get_terminal_size().columns - 1)]
                self.stream.write("\r" + line.ljust(self.width))
                self.width = len(line)
            else:
                self.stream.write(line + "\n")
            self.stream.flush()
            self.last_render = now

    def __exit__(self, exception_type, exception, traceback):
        self.stop.set()
        self.thread.join()
        self.render(force=True, failed=exception_type is not None)
        if self.terminal:
            self.stream.write("\n")
            self.stream.flush()


def expand(value):
    if isinstance(value, dict):
        return {key: expand(item) for key, item in value.items()}
    if isinstance(value, list):
        return [expand(item) for item in value]
    if isinstance(value, str):
        value = os.path.expandvars(os.path.expanduser(value))
        if "$" in value:
            raise ValueError("Unset environment variable or unsupported '$' in: " + value)
    return value


def local_path(value, base):
    path = Path(value)
    return (base / path).resolve() if not path.is_absolute() else path.resolve()


def positive(value, name):
    if type(value) is not int or value < 1:
        raise ValueError(name + " must be a positive integer")
    return value


def submit_path(value):
    # Condor path fields are not shell strings; do not quote them like shell arguments.
    if not re.fullmatch(r"/[A-Za-z0-9_./-]+", str(value)):
        raise ValueError("Use Condor paths without spaces or special characters: " + str(value))
    return str(value)


def root_url(value):
    parsed = urlsplit(value)
    if (parsed.scheme != "root" or not parsed.netloc or not parsed.path.startswith("//")
            or parsed.query or parsed.fragment or ".." in parsed.path.split("/")
            or re.search(r"[\s,$]", value)):
        raise ValueError("Expected root://host//absolute/path: " + value)
    return value.rstrip("/")


def eos_output_url(value):
    # Resolve mounted EOS namespaces without requiring an EOS mount on workers.
    for prefix, endpoint in (("/eos/user/", "root://eosuser.cern.ch"),
                             ("/eos/cms/", "root://eoscms.cern.ch")):
        if value.startswith(prefix):
            return root_url(endpoint + "/" + value)
    if value.startswith("/eos/"):
        raise ValueError("Provide a root://host//absolute/path URL for this EOS instance: " + value)
    return root_url(value)


def input_files(config, base, proxy):
    sources = [key for key in ("files", "file_list", "dataset") if config.get(key)]
    if len(sources) != 1:
        raise ValueError("Choose exactly one input source: files, file_list, or dataset")
    if sources[0] == "files":
        raw = config["files"]
        if not isinstance(raw, list):
            raise ValueError("input.files must be a list")
    elif sources[0] == "file_list":
        raw = local_path(config["file_list"], base).read_text().splitlines()
    else:
        dataset, instance = config["dataset"], config.get("das_instance", "prod/global")
        if not re.fullmatch(r"/[^/\s]+/[^/\s]+/[^/\s]+", dataset) or not re.fullmatch(r"prod/[a-z]+", instance):
            raise ValueError("Invalid DAS dataset or instance")
        raw = subprocess.run(["dasgoclient", "--query", f"file dataset={dataset} instance={instance}",
                              "--limit", "0"], check=True, text=True, capture_output=True,
                             env=dict(os.environ, X509_USER_PROXY=str(proxy))).stdout.splitlines()
    files, seen = [], set()
    for line in raw:
        name = line.strip()
        if not name or name.startswith("#"):
            continue
        if name.startswith("/store/"):
            name = config["redirector"].rstrip("/") + "/" + name
        root_url(name)
        if name in seen:
            raise ValueError("Duplicate input file: " + name)
        seen.add(name)
        files.append(name)
    if not files:
        raise ValueError("Input contains no ROOT files")
    return files


def resolve_options(arguments, sample, base, assets):
    if set(arguments) & {"inputFiles", "inputFiles_load", "maxEvents", "outputFile"}:
        raise ValueError("Set inputs and max_events in input/production, not cmsrun")
    if arguments.get("objectBackend") != "scouting":
        raise ValueError("This recipe requires objectBackend=scouting")
    for key, value in arguments.items():
        if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]*", key) or type(value) not in (str, bool, int, float):
            raise ValueError("cmsrun options must be named scalar values: " + key)
    for key in ("isMC", "doEleID", "doPhoID", "doTrigger", "doRECO"):
        if type(arguments.get(key, False)) is not bool:
            raise ValueError("cmsrun." + key + " must be a YAML boolean")
    if "isMC" not in arguments:
        raise ValueError("Specify cmsrun.isMC")
    wp_flags, tag_choices = {"electron": [], "photon": []}, []
    for kind in wp_flags:
        key = "scouting" + kind.title() + "ID"
        if not arguments.get(key):
            continue
        source = local_path(arguments[key], base)
        _, entries = load_working_points(str(source))
        digest = hashlib.sha256(source.read_bytes()).hexdigest()[:16]
        target = kind + "_" + digest + ".json" + (".gz" if source.name.endswith(".gz") else "")
        assets[target] = source
        arguments[key] = target
        for name in entries:
            flag = "passingCorrectionlib{}_{}".format(kind.title(), re.sub(r"[^A-Za-z0-9_]", "_", name))
            if flag in wp_flags[kind]:
                raise ValueError("Correctionlib WP flag collision: " + flag)
            wp_flags[kind].append(flag)
            tag_choices.append(kind + ":" + name)
    if arguments.get("scoutingTagWP") and arguments["scoutingTagWP"] not in tag_choices:
        raise ValueError("Unknown scoutingTagWP; available: " + ", ".join(tag_choices))
    required = {}
    for option, tree in (("doEleID", "tnpEleIDs"), ("doTrigger", "tnpEleTrig"),
                         ("doPhoID", "tnpPhoIDs"), ("doRECO", "tnpEleReco")):
        if arguments.get(option):
            required[tree] = ([] if option == "doRECO" else wp_flags["photon"] if option == "doPhoID"
                              else wp_flags["electron"] + wp_flags["photon"])
    if not required:
        raise ValueError("Enable at least one TnP tree")
    mask = None
    if not arguments["isMC"]:
        if not sample.get("lumi_mask"):
            raise ValueError("Data production requires lumi_mask in its sample configuration")
        location = sample["lumi_mask"]
        if location.startswith(("https://", "http://")):
            with urlopen(location, timeout=60) as response:
                content = response.read()
            source = content
        else:
            source = local_path(location, base)
            content = source.read_bytes()
        lumis = json.loads(content)
        if not isinstance(lumis, dict) or not lumis:
            raise ValueError("Data lumi_mask must be a nonempty certification JSON")
        mask = "lumimask_" + hashlib.sha256(content).hexdigest()[:16] + ".json"
        assets[mask] = source
    return required, mask


def prepare(config_path, farm_dir, selected=None):
    print("Checking configuration...", file=sys.stderr, flush=True)
    config_path = Path(config_path).resolve()
    raw = yaml.safe_load(config_path.read_text())
    samples = {name: sample for name, sample in raw["samples"].items()
               if sample.get("enabled", True) and (not selected or name in selected)}
    if not samples or (selected and set(selected) - samples.keys()):
        raise ValueError("No selected samples, or a selected sample is missing/disabled")
    # Do not require environment variables belonging only to disabled samples.
    config = expand(dict(raw, samples=samples))
    base = config_path.parent
    runtime, production, condor = (config[name] for name in ("cmssw", "production", "condor"))
    area = local_path(runtime["base"], base)
    if not (area / "src").is_dir():
        raise ValueError("Missing compiled CMSSW area: " + str(area))
    pset = local_path(runtime["pset"], base)
    cmsset = local_path(runtime["cmsset_default"], base)
    for item in (pset, cmsset):
        if not item.is_file():
            raise ValueError("Missing file: " + str(item))
    for key in ("release", "scram_arch"):
        if not re.fullmatch(r"[A-Za-z0-9_.-]+", runtime[key]):
            raise ValueError("Invalid CMSSW " + key)
    for key in ("job_flavour", "os"):
        if not re.fullmatch(r"[A-Za-z0-9_.-]+", condor[key]):
            raise ValueError("Invalid Condor " + key)
    for key in ("cpus", "memory_mb", "disk_mb"):
        positive(condor[key], "condor." + key)
    proxy = local_path(condor["proxy"], base)
    submit_path(proxy)
    if not proxy.is_file():
        raise ValueError("Create the X509 proxy first: " + str(proxy))
    attempts = positive(production["stageout_attempts"], "production.stageout_attempts")
    individual = production.get("process_files_individually", False)
    skip_bad = production.get("skip_bad_files", False)
    if type(individual) is not bool or type(skip_bad) is not bool:
        raise ValueError("process_files_individually and skip_bad_files must be YAML booleans")
    if skip_bad and not individual:
        raise ValueError("skip_bad_files requires process_files_individually")
    stage_locally = production.get("stage_inputs_locally", False)
    if type(stage_locally) is not bool:
        raise ValueError("stage_inputs_locally must be a YAML boolean")
    if stage_locally and not individual:
        raise ValueError("stage_inputs_locally requires process_files_individually")
    stagein_attempts = positive(production.get("stagein_attempts", 3), "production.stagein_attempts")
    logging = config.get("logging", {})
    if not isinstance(logging, dict):
        raise ValueError("logging must be a YAML mapping")
    logging = {"stream_cmsrun": False, "failure_tail_bytes": 16384, **logging}
    if set(logging) - {"stream_cmsrun", "failure_tail_bytes"}:
        raise ValueError("Unknown logging setting")
    if type(logging["stream_cmsrun"]) is not bool:
        raise ValueError("logging.stream_cmsrun must be a YAML boolean")
    positive(logging["failure_tail_bytes"], "logging.failure_tail_bytes")
    config["logging"] = logging
    destination = eos_output_url(production["eos_outputdir"])
    assets = {"TnPTreeProducer_cfg.py": pset, "worker.py": HERE / "worker.py"}
    jobs = []
    with Progress("Datasets", len(config["samples"]), "samples") as progress:
        for name, sample in config["samples"].items():
            if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]*", name):
                raise ValueError("Invalid sample name: " + name)
            progress.describe(name + ": checking IDs and lumi mask")
            arguments = dict(config["cmsrun"], **sample.get("cmsrun", {}))
            required, mask = resolve_options(arguments, sample, base, assets)
            source = "DAS query" if sample.get("dataset") else "file list"
            progress.describe(name + ": waiting for " + source)
            files = input_files(dict(config["input"], **sample), base, proxy)
            count = positive(sample.get("files_per_job", production["files_per_job"]), "files_per_job")
            events = sample.get("max_events", production["max_events"])
            if type(events) is not int or (events != -1 and events < 1):
                raise ValueError("max_events must be -1 or a positive integer")
            total_jobs = (len(files) + count - 1) // count
            progress.describe(f"{name}: {len(files)} files; splitting {total_jobs} jobs")
            for start in range(0, len(files), count):
                job_id = f"{name}_{start // count:05d}"
                jobs.append(dict(job_id=job_id, sample=name, dataset=sample.get("dataset"),
                                 input_files=files[start:start + count], max_events=events,
                                 process_files_individually=individual, skip_bad_files=skip_bad,
                                 stage_inputs_locally=stage_locally, stagein_attempts=stagein_attempts,
                                 logging=logging,
                                 cmsrun_args=[f"{key}={value}" for key, value in arguments.items()],
                                 root_filename="TnPTree_{}.root".format("mc" if arguments["isMC"] else "data"),
                                 required_trees=required, lumi_mask=mask,
                                 output_url=f"{destination}/{name}/tnp_{job_id}.root", stageout_attempts=attempts))

            progress.advance(f"{name}: {len(files)} files, {total_jobs} jobs")

    farm = Path(farm_dir).resolve()
    submit_path(farm)
    farm.mkdir(parents=True, exist_ok=False)
    for directory in ("logs", "jobs", "payload"):
        (farm / directory).mkdir()
    checksums = {}
    with Progress("Snapshot assets", len(assets), "files") as progress:
        for target, source in assets.items():
            progress.describe(target)
            if isinstance(source, bytes):
                (farm / "payload" / target).write_bytes(source)
            else:
                shutil.copyfile(source, farm / "payload" / target)
            checksums[target] = hashlib.sha256((farm / "payload" / target).read_bytes()).hexdigest()
            progress.advance()
    settings = dict(farm_dir=str(farm), cmssw_area=str(area), cmsset_default=str(cmsset),
                    cmssw_release=runtime["release"], scram_arch=runtime["scram_arch"], proxy_file=str(proxy))
    launcher = (HERE / "run.sh").read_text().split("\n", 1)[1]
    with Progress("Write jobs", len(jobs), "jobs") as progress:
        for job in jobs:
            job_id = job["job_id"]
            job["sha256"] = checksums
            (farm / "payload" / (job_id + ".json")).write_text(json.dumps(job, indent=2) + "\n")
            shell = "#!/bin/bash\n" + "".join(f"{key}={shlex.quote(value)}\n" for key, value in dict(settings, job_id=job_id).items())
            shell += "extra_assets=(" + " ".join(shlex.quote(name) for name in assets if name not in
                                                 ("worker.py", "TnPTreeProducer_cfg.py")) + ")\n"
            shell += launcher
            script = farm / "jobs" / (job_id + ".sh")
            script.write_text(shell)
            script.chmod(0o755)
            progress.advance(job_id)
    lines = ["universe = vanilla", f"initialdir = {farm}", f"executable = {farm}/jobs/$(job).sh",
             "should_transfer_files = YES", "when_to_transfer_output = ON_EXIT", 'transfer_output_files = ""',
             "transfer_input_files = " + ",".join(str(farm / "payload" / name) for name in [*assets, "$(job).json"]),
             "use_x509userproxy = True", f"x509userproxy = {proxy}", "getenv = False",
             f"request_cpus = {condor['cpus']}", f"request_memory = {condor['memory_mb']}MB",
             f"request_disk = {condor['disk_mb']}MB", f'+JobFlavour = "{condor["job_flavour"]}"',
             f'+WantOS = "{condor["os"]}"', "on_exit_hold = (ExitBySignal == True) || (ExitCode != 0)",
             "output = logs/$(job).$(ClusterId).$(ProcId).out", "error = logs/$(job).$(ClusterId).$(ProcId).err",
             "log = logs/cluster.$(ClusterId).log", "queue job from ("]
    lines += [job["job_id"] for job in jobs] + [")"]
    with Progress("Finalize", 3, "files") as progress:
        (farm / "submit.sub").write_text("\n".join(lines) + "\n")
        progress.advance("submit.sub")
        (farm / "manifest.json").write_text(json.dumps(jobs, indent=2) + "\n")
        progress.advance("manifest.json")
        (farm / "resolved.yaml").write_text(yaml.safe_dump(config, sort_keys=False))
        progress.advance("resolved.yaml")
    print(f"Prepared {len(jobs)} jobs from {len(config['samples'])} samples; no submission.")
    print("EOS outputdir:", destination)
    print(f"Local test: bash {farm}/jobs/{jobs[0]['job_id']}.sh 1000")
    print(f"Submit after checking: condor_submit -dry-run {farm}/submit.ads {farm}/submit.sub && condor_submit {farm}/submit.sub")
    return farm


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("config")
    parser.add_argument("--farm-dir", required=True, help="New directory; existing farms are never overwritten")
    parser.add_argument("--samples", nargs="+", help="Only prepare these enabled samples")
    args = parser.parse_args()
    try:
        prepare(args.config, args.farm_dir, args.samples)
    except (ValueError, OSError, KeyError, subprocess.CalledProcessError) as error:
        parser.exit(1, f"Error: {error}\n")


if __name__ == "__main__":
    main()
