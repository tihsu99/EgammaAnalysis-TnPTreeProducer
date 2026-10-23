#!/bin/bash
set -eo pipefail

# The generator prepends this job's settings before the common launcher.
if [[ -n "${_CONDOR_SCRATCH_DIR:-}" ]]; then
    [[ $# -eq 0 ]] || { echo "Event overrides are only allowed for local tests" >&2; exit 2; }
    payload_dir="$_CONDOR_SCRATCH_DIR"
    work_dir=$(mktemp -d "$_CONDOR_SCRATCH_DIR/tnp.XXXXXX")
    mode=batch
else
    [[ $# -le 1 ]] || { echo "Usage: bash JOB.sh [LOCAL_MAX_EVENTS]" >&2; exit 2; }
    local_max_events="${1:-1000}"
    [[ "$local_max_events" =~ ^[1-9][0-9]*$ ]] || { echo "LOCAL_MAX_EVENTS must be positive" >&2; exit 2; }
    payload_dir="$farm_dir/payload"
    work_dir=$(mktemp -d "${TMPDIR:-/tmp}/tnp-${job_id}.XXXXXX")
    mode=local
fi
trap 'rc=$?; echo "Exit code: $rc; working directory: $work_dir"; exit "$rc"' EXIT
echo "Mode: $mode; working directory: $work_dir"
cp "$payload_dir/worker.py" "$payload_dir/TnPTreeProducer_cfg.py" "$work_dir/"
cp "$payload_dir/${job_id}.json" "$work_dir/job.json"
for asset in "${extra_assets[@]}"; do
    cp "$payload_dir/$asset" "$work_dir/"
done
export TMPDIR="$work_dir/tmp"
export XDG_CACHE_HOME="$work_dir/cache"
export PYTHONNOUSERSITE=1
mkdir -p "$TMPDIR" "$XDG_CACHE_HOME"
unset PYTHONHOME PYTHONPATH
export SCRAM_ARCH="$scram_arch"
export X509_USER_PROXY="${X509_USER_PROXY:-$proxy_file}"
source "$cmsset_default"
test -d "$cmssw_area/src"
cd "$cmssw_area/src"
cmssw_runtime=$(scram runtime -sh)
eval "$cmssw_runtime"
test "$CMSSW_VERSION" = "$cmssw_release"
cd "$work_dir"
if [[ "$mode" == local ]]; then
    python3 worker.py job.json --local-max-events "$local_max_events" 2>&1 | tee cmsRun.log
else
    python3 worker.py job.json 2>&1 | tee cmsRun.log
fi
