# EgammaAnalysis-TnPTreeProducer

Package of the EGamma group to produce Tag-and-Probe trees

## Overview of branches

| Branch                                     | release            | tnpEleIDs          | tnpPhoIDs          | tnpEleTrig         | tnpEleReco         | purpose                                |
| ------------------------------------------ | ------------------ |:------------------:|:------------------:|:------------------:|:------------------:|:--------------------------------------:|
|                                            |                    | *miniAOD*          | *miniAOD*          | *miniAOD*          | *AOD*              |                                        |
| [RunIIfinal](../../tree/RunIIfinal)        | CMSSW\_10\_2       | :heavy_check_mark: | :heavy_check_mark: | :heavy_check_mark: | :heavy_check_mark: | Run II analysis                        |
| [RunIIfinal](../../tree/RunIIfinal)        | CMSSW\_10\_6       | :heavy_check_mark: | :heavy_check_mark: | :heavy_check_mark: | :heavy_check_mark: | Run II analysis using ultra-legacy     |
| [CMSSW\_11\_X\_Y](../../tree/CMSSW_11_X_Y) | CMSSW\_11          | :heavy_check_mark: | :heavy_check_mark: | :heavy_check_mark: | :white_check_mark: | Development for Run III (experimental) |
| [Run3_13X](../../tree/Run3_13X)   | CMSSW\_13                   | :heavy_check_mark: | :heavy_check_mark: | :heavy_check_mark: | :white_check_mark: | Run3 2022/2023 |

Note: because of a dataformat CMSSW\_10\_6 can only be used for ultra-legacy samples, and CMSSW\_10\_2 should be used for the rereco samples.

## Available tuples

### ReReco 2016, 2017 and 2018
If you do not need changes to the default code, you can simply use existing flat tag and probe trees, avalaible for both 2016, 2017 and 2018 (RunIIfinal branch):

```bash
ls /eos/cms/store/group/phys_egamma/tnpTuples/tomc/2020-06-09/*/merged/
```

These inlcude the tnpEleTrig, tnpEleIDs and tnpPhoIDs trees produced with the RunIIfinal branch.
*Main change with respect to the 2020-02-28 production is the inclusion of some additional branches, e.g. the leptonMva's*

### ReReco 2016, 2017 and 2018 - L1 matched
In case you need L1 matching for the measurement of doubleEle HLT triggers, you can use the tnpEleTrig trees found in:

```bash
ls /eos/cms/store/group/phys_egamma/tnpTuples/tomc/2020-03-03/*/merged/*L1matched.root
```

### UL2017 and UL2018
For ultra-legacy  we have tnpEleTrig, tnpEleIDs and tnpPhoIDs trees available at:
```
ls /eos/cms/store/group/phys_egamma/tnpTuples/tomc/2020-05-20/UL2018/merged
ls /eos/cms/store/group/phys_egamma/tnpTuples/tomc/2020-05-20/UL2017/merged
ls /eos/cms/store/group/phys_egamma/tnpTuples/rasharma/2021-02-10/UL2016postVFP/merged
ls /eos/cms/store/group/phys_egamma/tnpTuples/rasharma/2021-02-10/UL2016preVFP/merged
```


## To produce new tuples
### 1a. Install for rereco (CMSSW\_10\_2\_X with X=10 or higher, works for 2016, 2017 and 2018 data/MC)

```bash
cmsrel CMSSW_10_2_22
cd CMSSW_10_2_22/src
cmsenv
git clone -b RunIIfinal git@github.com:cms-egamma/EgammaAnalysis-TnPTreeProducer.git EgammaAnalysis/TnPTreeProducer
scram b -j8
```

### 1b. Install for ultra-legacy (CMSSW\_10\_6\_X, works for UL2017 and UL2018 data/MC)

```bash
cmsrel CMSSW_10_6_13
cd CMSSW_10_6_13/src
cmsenv
git clone -b RunIIfinal git@github.com:cms-egamma/EgammaAnalysis-TnPTreeProducer.git EgammaAnalysis/TnPTreeProducer
scram b -j8
```

### 1c. Install for Run3 (CMSSW\_13\_3\_X, works for 2022 and 2023 data/MC)

```bash
cmsrel CMSSW_13_3_1
cd CMSSW_13_3_1/src
cmsenv
git clone -b Run3_13X git@github.com:cms-egamma/EgammaAnalysis-TnPTreeProducer.git EgammaAnalysis/TnPTreeProducer
scram b -j8
```

### 2. Try-out
You can find the cmsRun executable in EgammaAnalysis/TnPTreeProducer/python:
```bash
cd EgammaAnalysis/TnPTreeProducer/python/
cmsRun TnPTreeProducer_cfg.py isMC=True doTrigger=True era=UL2018
```
Check [TnPTreeProducer\_cfg.py](python/TnPTreeProducer_cfg.py) for all available options. Update the code if you need to implement custom-made recipes.

Test files can be defined in [python/etc/tnpInputTestFiles\_cff.py](python/etc/tnpInputTestFiles_cff.py)
If you update the code, you can use the ./runTests.py script in the test directory to check for new differences in the 2016, 2017 and 2018 test files.

### 3. Submit jobs
Check in EgammaAnalysis/TnPTreeProducer//crab the tnpCrabSubmit.py script to submit your jobs using crab

```bash
source /cvmfs/cms.cern.ch/common/crab-setup.sh
```

## To make a pull request to this repository
1. On github fork the package https://github.com/cms-analysis/EgammaAnalysis-TnPTreeProducer
2. Add the remote
```bash
git remote add username-push git@github.com:username/EgammaAnalysis-TnPTreeProducer.git
```
3. push commits to fork and then standard pull request process
```bash
git push username-push branchname
```

## Adding new workingpoints
You can add new electron workingpoints in [python/egmElectronIDModules\_cff.py](python/egmElectronIDModules_cff.py) and new photon workingpoints
in [python/egmPhotonIDModules\_cff.py](python/egmPhotonIDModules_cff.py). Each new workingpoint added in these python config fragments will
add a new "passing<WP>" boolean in the electron and photon trees respectively. Of course, one can also choose to simply add a variable in
[python/egmTreesContent\_cff.py](python/egmTreesContent\_cff.py), which might be preferred for MVA variables when you want to have the
flexibility to explore different workingpoints: you can simply put a cut on these variable in the egm\_tnp\_analysis package.

## Description of variables

Description of some of variables in the output tree is given [here](VariablesInfo.md).

## Exported scouting IDs from correctionlib

For YAML-controlled multi-dataset Condor production, including local testing of
the same job shells and worker-scratch to EOS output, see
[the Condor workflow](condor/README.md) and [sample configuration](condor/scouting_ids.yaml).

With `objectBackend=scouting`, supply the full `scouting_id.json` or
`scouting_id.json.gz` produced by `Scouting_EGM_ID/export_id.py`. The ntuplizer
discovers all exported working points and creates passing probe collections and
tree flags. Do not supply the EA/scale-only `corrections_all.json` file.

| Option | Purpose |
| --- | --- |
| `scoutingElectronID` | Electron ID bundle; evaluate every WP on electron probes. |
| `scoutingPhotonID` | Photon ID bundle; evaluate every WP on photon probes and, as in the existing scouting setup, on electron probes. |
| `scoutingTagWP` | Optional `electron:<WP key>` or `photon:<WP key>` to select electron tags. |

For example, `Iso/WP70` in the electron bundle produces
`passingCorrectionlibElectron_Iso_WP70` in `tnpEleIDs/fitter_tree` (also in the
electron trigger tree when enabled). `PhotonIso/WP90` in the photon bundle
produces `passingCorrectionlibPhoton_PhotonIso_WP90` in both `tnpEleIDs/fitter_tree`
and `tnpPhoIDs/fitter_tree` when those trees are enabled. Non-alphanumeric
characters in WP keys become underscores; ambiguous resulting names are rejected.
Private correctionlib components are never exported as flags.

The probe denominator and the existing reference-ID flags are preserved. A WP
flag marks pass/fail on those baseline probes; it does not preselect the entire
probe sample. A configured tag WP replaces the legacy tag ID, applies
`ELECTRON_TAG_CUTS`, and keeps the existing tag trigger selection. Tags remain
electron candidates even when a photon WP is chosen. If `scoutingTagWP` is
omitted, the legacy tag selection is retained. Omitting all three options keeps
the existing configuration.

Rebuild in a Run 3 CMSSW release providing the `correctionlib` SCRAM tool, then
test on a scouting-enabled MiniAOD file (set `TNP_INPUT`, `ELECTRON_ID_JSON`, and
`PHOTON_ID_JSON` to the input file and the two exported bundles):

```bash
cd "${CMSSW_BASE:?}/src"
scram b -j 8
cmsRun EgammaAnalysis/TnPTreeProducer/python/TnPTreeProducer_cfg.py \
  objectBackend=scouting inputFormat=miniaod triggerBackend=patTrigger \
  isMC=True era=2024 doEleID=True doPhoID=True doTrigger=False doRECO=False \
  inputFiles="${TNP_INPUT:?}" maxEvents=1000 \
  scoutingElectronID="${ELECTRON_ID_JSON:?}" \
  scoutingPhotonID="${PHOTON_ID_JSON:?}" \
  scoutingTagWP=electron:Iso/WP70
```

Use the input-format, era, MC/data, and trigger options appropriate to the actual
sample. To select tags with a photon WP, replace the final argument with
`scoutingTagWP=photon:PhotonIso/WP70`. You may supply either bundle separately.
WP keys must match the JSON exactly; display labels such as Tight or AXOL1TL do
not rename correctionlib keys.

All evaluators receive **raw** scouting quantities. ECAL/HCAL/track isolation is
passed in GeV without division or additional calibration. The JSON defines
whether to use E or pT, applies EA/scale corrections and clamping, and includes
the exported fiducial cuts and Barrel/Endcap boundaries. Photon bundles do not
need `missingHits`. The rho input `ScoutingRho.fixedGridRhoFastjetAll` maps to the
event product selected by `scoutingRho` (default `hltScoutingPFPacker:rho`); this
must be the same physical rho used to derive the ID. Missing products, unknown
input mappings or WPs, and non-binary outputs raise errors. Non-finite raw inputs
fail the corresponding WP.

Equality with the Python evaluator assumes identical numeric inputs. The
training NanoAOD tables use reduced float precision, whereas this selector reads
the original scouting objects; candidates very near a cut can therefore migrate
when comparing these different data representations.

The mapping is centralized in `python/scoutingCorrectionlib_cff.py`. A custom
CMSSW config can override raw getters through
`options['SCOUTING_ID_VARIABLES'][particle][input_name] = expression` and event
double products through `options['SCOUTING_ID_EVENT_VARIABLES'][input_name] = input_tag`
before calling `setupTreeMaker`. Selection thresholds always come from the JSON.

For CRAB, place the two bundles in the submission directory with **different
basenames**, for example `electron_id.json.gz` and `photon_id.json.gz`, then add
these fields to the existing job configuration:

```python
cfg.JobType.inputFiles = ["electron_id.json.gz", "photon_id.json.gz"]
cfg.JobType.pyCfgParams += [
    "scoutingElectronID=electron_id.json.gz",
    "scoutingPhotonID=photon_id.json.gz",
    "scoutingTagWP=electron:Iso/WP70",
]
```

Keep any other required `inputFiles` entries. Relative paths are intentionally
preserved so the same parameters work inside the CRAB worker sandbox. Archive
the exact bundles with the production configuration to retain ID provenance.

Configuration checks run without CMSSW:
`python3 test/test_scouting_correctionlib.py`. The standalone C++ driver in
`test/scouting_correctionlib_evaluate.cc` is also used by
`Scouting_EGM_ID/tests/test_tnp_correctionlib.py` to compare both exported ID
families with their Python evaluator. These checks do not replace a CMSSW build
and a small `cmsRun` test on the intended input tier.
