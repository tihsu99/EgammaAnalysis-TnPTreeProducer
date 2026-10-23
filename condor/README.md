# Scouting TnP: prepare, test locally, submit to Condor

All samples and settings live in `scouting_ids.yaml`. Run from the
`EgammaAnalysis/TnPTreeProducer` directory in your compiled CMSSW environment.
The generator needs Python 3 with PyYAML and `dasgoclient` for DAS input sources.
The configured CMSSW area must remain accessible to workers and unchanged between
the local test and the batch run. The generator does not submit jobs.

The supplied YAML enables the DY NLO and LO inputs from the existing scouting
CRAB configuration. The 2024F data samples are included but disabled. These are
dataset definitions, not a new verification of their disk availability.

## Configure once

Set these paths directly in the YAML, or export its environment variables:

```bash
export ELECTRON_ID_JSON=/absolute/path/to/electron/scouting_id.json.gz
export PHOTON_ID_JSON=/absolute/path/to/photon/scouting_id.json.gz
export TNP_EOS_OUTPUTDIR=root://eosuser.cern.ch//eos/user/t/tihsu/tnp/correctionlib_v1
voms-proxy-init --voms cms --valid 192:00
export X509_USER_PROXY="$(voms-proxy-info --path)"
```

`CMSSW_BASE`, `CMSSW_VERSION`, and `SCRAM_ARCH` come from `cmsenv`. Use a new EOS
campaign directory; completed output files are never overwritten. Data samples
require a downloaded certification JSON in `lumi_mask` (`TNP_LUMI_MASK` in the
example). The mask is copied into the payload and applied through
`process.source.lumisToProcess`.

Each sample chooses exactly one of `dataset`, `file_list`, or `files`:

```yaml
samples:
  MySample:
    enabled: true
    dataset: /PRIMARY/PROCESSING/MINIAODSIM
    files_per_job: 2
    cmsrun:
      isMC: true
      era: '2024'
```

Replace the dataset with an actual DAS path. For an existing file list, replace
the `dataset` entry with `file_list: /absolute/path/files.txt`. For a single file,
use `files: ["${TNP_INPUT}"]`. Lists accept `/store/...` LFNs or complete
`root://host//...` URLs. Relative file paths in the YAML are relative to the YAML
directory. `cmsrun` entries under a sample override the shared `cmsrun` mapping.

## Generate the production farm

```bash
python3 condor/prepare.py condor/scouting_ids.yaml --farm-dir farms/tnp_ids_v1
```

This queries all enabled datasets and splits their file lists. To prepare only
selected enabled samples, add `--samples DY_NLO_2024 DY_LO_2024`.
The farm contains per-job scripts in `jobs/`, frozen configuration and ID files
in `payload/`, `manifest.json`, `resolved.yaml`, and `submit.sub`. The manifest
records every job's files, CMS arguments, required WP flags, asset SHA256 values,
and EOS destination. Existing farms are not overwritten.

## Test the same shell on lxplus

```bash
bash farms/tnp_ids_v1/jobs/DY_NLO_2024_00000.sh 1000
```

The shell sets up CMSSW, creates a fresh directory under local `$TMPDIR` or
`/tmp`, and prints its path. Its ROOT file, `cmsRun.log`,
`FrameworkJobReport.xml`, and successful-test `receipt.json` remain there for
inspection. It checks the requested trees, exported WP branches, and readable
entries. A test with no probe pairs fails with a diagnostic; increase the event
cap or investigate the input/trigger/tag selection. No test output is uploaded
to EOS. Omitting the argument defaults to 1,000 events. Test a representative
job for each enabled sample before submission.

The cap is only a local test override. It never edits the prepared production
jobs, which retain `max_events: -1` by default. If you edit YAML settings or
export new IDs, prepare a new farm and repeat the test.

## Submit after the local test passes

```bash
condor_submit -dry-run farms/tnp_ids_v1/submit.ads farms/tnp_ids_v1/submit.sub && \
condor_submit farms/tnp_ids_v1/submit.sub
```

Condor transfers the payload and runs the same job shell. All processing and
intermediate output happens under `$_CONDOR_SCRATCH_DIR/tnp.*`. After a zero
`cmsRun` exit and ROOT validation, the worker uploads checksummed temporary files
and renames them to their final names under:

```text
<eos_outputdir>/<sample>/tnp_<sample>_<index>.root
<eos_outputdir>/<sample>/tnp_<sample>_<index>.root.json
<eos_outputdir>/<sample>/tnp_<sample>_<index>.root.xml
```

The ROOT file is published last. Uploads retry according to
`stageout_attempts`; failures exit nonzero and are held by Condor. Standard output
and error are in the farm's `logs/` directory; large ROOT files are not returned
to the submission directory. Empty production trees can be legitimate and are
recorded in the receipt, while local tests require at least one probe pair.
Submission only queues work; inspect worker logs and final EOS artifacts before
considering a campaign complete. The local test does not test worker credentials
or EOS upload; check the first completed batch job before relying on a large run.

Synthetic checks, without contacting CERN:

```bash
python3 test/test_condor_scouting.py
```
