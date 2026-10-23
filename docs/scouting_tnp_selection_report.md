# Run 3 EGM Scouting Tag-and-Probe Selection Report

Prepared from the current `EgammaAnalysis/TnPTreeProducer` configuration for the
2024 scouting-reco production. This note is intended as the review-facing
description of the datasets, event selection, object definitions, tag
definitions, probe definitions, and output trees used by the production.

## Scope

This report documents the configuration driven by
`TnPTreeProducer/crab/tnpCrabSubmit_ScoutingReco.py` with
`submitVersion = 2026-04-09_scoutingReco`. The production runs the scouting
object backend for both HLTSCOUT and MiniAOD inputs and produces electron ID,
photon ID, and scouting RECO tag-and-probe trees. The submitted configs set
`doTrigger=False`, so trigger-efficiency trees are configured in the python
process but are not written in this production.

Primary source files:

- `TnPTreeProducer/crab/tnpCrabSubmit_ScoutingReco.py`
- `TnPTreeProducer/python/TnPTreeProducer_cfg.py`
- `TnPTreeProducer/python/egmGoodParticlesDef_cff.py`
- `TnPTreeProducer/python/egmTreesSetup_cff.py`
- `TnPTreeProducer/python/egmElectronIDModules_cff.py`
- `TnPTreeProducer/python/egmPhotonIDModules_cff.py`
- `TnPTreeProducer/plugins/ScoutingElectronRefSelector.cc`
- `TnPTreeProducer/plugins/ScoutingPhotonRefSelector.cc`

## Dataset Definition

The production uses four samples: two DY MC samples and two 2024F data streams.

| Sample label | Dataset | Input format | Request name | Splitting |
| --- | --- | --- | --- | --- |
| MC NLO DY to 2e | `/DYto2E-2Jets_Bin-MLL-50_TuneCP5_13p6TeV_amcatnloFXFX-pythia8/RunIII2024Summer24MiniAODv6-150X_mcRun3_2024_realistic_v2-v4/MINIAODSIM` | MiniAOD | `mc_nlo_scoutingReco_2024` | FileBased, 5 files/job |
| MC LO DY to 2e | `/DYto2E-4Jets_Bin-MLL-50_TuneCP5_13p6TeV_madgraphMLM-pythia8/RunIII2024Summer24MiniAOD-140X_mcRun3_2024_realistic_v26-v3/MINIAODSIM` | MiniAOD | `mc_lo_scoutingReco_2024` | FileBased, 5 files/job |
| Data HLTSCOUT | `/ScoutingPFRun3/Run2024F-v1/HLTSCOUT` | HLTSCOUT | `data_hltscout_scoutingReco_2024F` | LumiBased, 50 lumis/job |
| Data MiniAOD monitor | `/ScoutingPFMonitor/Run2024F-PromptReco-v1/MINIAOD` | MiniAOD | `data_miniaod_scoutingReco_2024F` | FileBased, 5 files/job |

For data, the lumi mask is the 2024 Golden JSON:

`https://cms-service-dqmdc.web.cern.ch/CAF/certification/Collisions24/Cert_Collisions2024_378981_386951_Golden.json`

CRAB writes output under:

`/store/user/${USER}/TnPTreeProducer/2026-04-09_scoutingReco`

with storage site `T2_TW_NCHC`.

## Processing Configuration

All four jobs use:

- `objectBackend=scouting`
- `doEleID=True`
- `doPhoID=True`
- `doRECO=True`
- `doTrigger=False`
- `era=2024`
- `HLTname=HLT`
- `scoutingElectronCollection=hltScoutingEgammaPacker`
- `scoutingPhotonCollection=hltScoutingEgammaPacker`
- `scoutingVertexCollection=hltScoutingPrimaryVertexPacker:primaryVtx`
- `scoutingRho=hltScoutingPFPacker:rho`

Input-format-specific settings:

| Input | Trigger backend | Trigger object collection | Trigger-object matching |
| --- | --- | --- | --- |
| MC MiniAOD | `patTrigger` | `slimmedPatTrigger` | Default `False` |
| Data HLTSCOUT | `triggerEvent` | `hltTriggerSummaryAOD` by backend default | `False` |
| Data MiniAOD | `patTrigger` | `slimmedPatTrigger` | `False` |

Global Tags selected by `era=2024`:

- MC: `140X_mcRun3_2024_realistic_v14`
- Data: `140X_dataRun3_Prompt_v3`

Scouting backend energy calibration through `calibEn` is disabled by design if
requested, because the scouting backend does not support the EGM calibration
sequence.

## Event Selection

The event-level HLT filter is always run in the main cmsRun path before object
building and tree writing. For scouting objects, the HLT path list is overridden
to:

`DST_PFScouting_SinglePhotonEB_v*`

The HLT process name is `HLT`, and `hltHighLevel.throw=True`. Therefore, events
must pass the configured scouting DST path, and missing HLT path configuration
will throw.

Important consequence for this production:

- `doTrigger=False` means the trigger-efficiency tree `tnpEleTrig` is not
  written.
- The event-level HLT filter is still applied, because `process.hltFilter`
  appears explicitly in the main path before `cand_sequence`.
- The tag module is configured with the filter label
  `hltEG30EBTightIDTightIsoTrackIsoFilter`, but in the submitted scouting
  configs `requireTriggerObjectMatch=False`. In this mode the scouting trigger
  candidate producer returns all input tag candidates without applying the
  object-to-trigger-filter matching. The effective tag requirement is therefore
  the offline scouting tag selection plus the event-level DST path selection.

## Object Definition

### Input Collections

Scouting objects are read from:

- Electrons: `hltScoutingEgammaPacker`
- Photons: `hltScoutingEgammaPacker`
- Vertices: `hltScoutingPrimaryVertexPacker:primaryVtx`
- Rho: `hltScoutingPFPacker:rho`

For MiniAOD scouting jobs, pileup information is taken from
`slimmedAddPileupInfo`. For HLTSCOUT jobs, pileup information is taken from
`addPileupInfo`.

### Scouting Electron Candidate

`Run3ScoutingElectron` objects are converted into `reco::LeafCandidate`
objects. The four-vector is built from `(pt, eta, phi, m)`.

The candidate charge is taken from the best scouting track when the best-track
value map is valid; otherwise it falls back to the first available
`trkcharge()` entry, or zero if no track charge exists.

The best-track producer uses separate barrel/endcap thresholds:

| Quantity | Barrel | Endcap |
| --- | ---: | ---: |
| Track pt minimum | 12.0 GeV | 12.0 GeV |
| Track chi2/ndof maximum | 3.0 | 2.0 |
| Relative energy-difference maximum | 1.0 | 1.0 |
| Delta phi maximum | 0.06 | 0.06 |

The selected best track is the passing track with the smallest relative
energy-difference score.

### Scouting Photon Candidate

`Run3ScoutingPhoton` objects are converted into neutral `reco::LeafCandidate`
objects. The four-vector is built from `(pt, eta, phi, m)`, the charge is set
to zero, and the PDG id is set to 22.

### Scouting Egamma Candidate

For the RECO probe, electrons and photons are merged into a common scouting
egamma candidate collection. Electron-like candidates carry the best-track
charge; photon-like candidates are neutral.

### Baseline Object Cuts

| Object collection | Baseline cut |
| --- | --- |
| `goodElectrons` | `pt > 5.0 && abs(eta) < 2.5` |
| `goodPhotons` | `pt > 10.0 && abs(eta) <= 2.5` |
| `goodScoutingEgammaCandidates` / `probeSC` | `abs(eta) < 2.5 && et > 5.0` |

## Scouting Working Points

All normalized isolation quantities below use:

`energy = max(1, pt * cosh(eta))`

and the barrel/endcap split is:

- Barrel: `abs(eta) < 1.479`
- Endcap: `abs(eta) >= 1.479`

### ScoutingElectronRecommendv1

| Variable | Barrel | Endcap |
| --- | ---: | ---: |
| `sigmaIetaIeta` | `< 0.015` | `< 0.045` |
| `hOverE` | `< 0.2` | `< 0.2` |
| `abs(dEtaIn)` | `< 0.008` | `< 0.012` |
| `abs(dPhiIn)` | `< 0.06` | `< 0.06` |
| `ecalIso / energy` | `< 0.25` | `< 0.1` |
| `trackIso / energy` | `< 0.001` | `< 0.001` |

### ScoutingElectronCustomizev1

This working point requires `ScoutingElectronRecommendv1` and adds:

| Variable | Barrel | Endcap |
| --- | ---: | ---: |
| `hcalIso / energy` | `< 0.4` | `< 0.6` |

### ScoutingPhotonRecommendv1

Applied both to `Run3ScoutingPhoton` probes and to electron objects when photon
style flags are stored in the electron tree.

| Variable | Barrel | Endcap |
| --- | ---: | ---: |
| `sigmaIetaIeta` | `< 0.015` | `< 0.045` |
| `hOverE` | `< 0.2` | `< 0.2` |
| `ecalIso / energy` | `< 0.25` | `< 0.1` |

### ScoutingPhotonCustomizev1

This working point requires `ScoutingPhotonRecommendv1` and adds:

| Variable | Barrel | Endcap |
| --- | ---: | ---: |
| `hcalIso / energy` | `< 0.6` | `< 1.0` |

## Tag Definition

The effective scouting tag electron starts from `goodElectrons` and is selected
by `ScoutingElectronRecommendv1`.

Therefore, in the current scouting implementation the effective tag kinematic
preselection is inherited from `goodElectrons`:

`pt > 5.0 && abs(eta) < 2.5`

The configuration also defines an intended tag cut:

`pt >= 30.0 && abs(eta) <= 2.5 && !(1.4442 <= abs(eta) < 1.566)`

However, this cut is not consumed by the scouting `tagEleCutBasedTight` module.
The scouting tag selector takes only the `goodElectrons` input collection and
the `ScoutingElectronRecommendv1` working point. This differs from the
non-scouting PAT/GSF tag selector path, where `ELECTRON_TAG_CUTS` is applied.

The tag module is configured with:

- HLT tag filter label: `hltEG30EBTightIDTightIsoTrackIsoFilter`
- Matching cone if trigger-object matching is enabled: `DeltaR < 0.3`
- AND semantics across filter labels

For the current submitted configs, trigger-object matching is disabled. The
effective tag therefore does not require an object-level match to
`hltEG30EBTightIDTightIsoTrackIsoFilter`; the event-level
`DST_PFScouting_SinglePhotonEB_v*` filter remains active.

## Probe Definitions

### Electron Probe

Electron probes start from `goodElectrons`:

`pt > 5.0 && abs(eta) < 2.5`

For electron ID trees, the following flags are written from scouting selectors:

- `passingScoutingElectronRecommendv1`
- `passingScoutingElectronCustomizev1`
- `passingScoutingPhotonRecommendv1`
- `passingScoutingPhotonCustomizev1`

The photon-style flags are intentionally also evaluated on scouting electron
objects through the electron selector implementation.

### Photon Probe

Photon probes start from `goodPhotons`:

`pt > 10.0 && abs(eta) <= 2.5`

For photon ID trees, the following flags are written:

- `passingScoutingPhotonRecommendv1`
- `passingScoutingPhotonCustomizev1`

### RECO Probe

The RECO probe starts from the merged scouting egamma candidate collection:

`abs(eta) < 2.5 && et > 5.0`

The RECO passing flag is:

- `passingRECO = probeSCEle`

where `probeSCEle` is the subset of merged scouting egamma candidates passing
the same kinematic selection and requiring `charge != 0`. In practice, this
marks electron-like scouting egamma probes as passing RECO.

## Pairing Definitions

All tag-probe pairs use the mass window:

`50 < mass < 130`

Pair definitions:

| Tree purpose | Pair module | Decay expression | Charge requirement |
| --- | --- | --- | --- |
| Trigger | `tnpPairingEleHLT` | `tagEle@+ probeEle@-` | Opposite-sign, enforced |
| RECO | `tnpPairingEleRec` | `tagEle probeSC` | No charge requirement |
| Electron ID | `tnpPairingEleIDs` | `tagEle probeEle` | No charge requirement |
| Photon ID | `tnpPairingPhoIDs` | `tagEle probePho` | No charge requirement |

Tree arbitration is set to `HighestPt`.

## MC Truth Definition

For MC samples, the gen electron collection is selected with:

`abs(pdgId) == 11 && pt > 3 && abs(eta) < 2.7 && isPromptFinalState`

Tag and probe objects are matched to gen electrons with:

- `DeltaR < 0.20`
- `DeltaPt/Pt < 50.0`
- Charge matching disabled
- Ambiguity resolution disabled
- Match-quality resolution enabled

MC trees use generator event weights and pileup weights from
`pileupReweightingProducer:pileupWeights`.

## Output Trees

The configured output file name is:

- `TnPTree_mc.root` for MC
- `TnPTree_data.root` for data

For this production, `doEleID=True`, `doPhoID=True`, `doRECO=True`, and
`doTrigger=False`, so the output tree sequence writes:

| Tree | Written in this production | Probe type | Main passing flags |
| --- | --- | --- | --- |
| `tnpEleReco` | Yes | merged scouting egamma / RECO probe | `passingRECO` |
| `tnpEleIDs` | Yes | scouting electron | scouting electron and photon-style electron flags |
| `tnpPhoIDs` | Yes | scouting photon | scouting photon flags |
| `tnpEleTrig` | No | scouting electron | configured but not written because `doTrigger=False` |

For scouting electron probes, stored variables include:

- `el_eta`, `el_phi`, `el_abseta`, `el_pt`, `el_e`, `el_q`
- `el_dEtaIn`, `el_dPhiIn`, `el_sieie`, `el_hoe`, `el_ooemoop`
- `el_mHits`, `el_ecalIso`, `el_hcalIso`, `el_trkIso`
- `el_r9`, `el_sMin`, `el_dxy`, `el_dz`, `el_sip`

For scouting photon probes, stored variables include:

- `ph_eta`, `ph_abseta`, `ph_et`, `ph_e`

For scouting RECO probes, stored variables include:

- `sc_eta`, `sc_phi`, `sc_abseta`, `sc_pt`, `sc_et`, `sc_e`, `sc_q`

Common pair variables include:

- `eta`, `abseta`, `pt`, `mass`

## Review Points

The following items are intentionally called out for review:

1. The effective tag does not require object-level trigger matching in the
   current production because `requireTriggerObjectMatch=False`. If the intended
   definition is a trigger-matched tag electron, this option should be set to
   `True` and validated separately for both `triggerEvent` and `patTrigger`
   backends.
2. The event-level HLT selection is `DST_PFScouting_SinglePhotonEB_v*` for all
   scouting-object jobs, including the MiniAOD-based data and MC scouting
   production.
3. `doTrigger=False` means the detailed HLT filter flags configured for Run 3
   are not written to the output in this production.
4. The RECO efficiency proxy is based on merged scouting egamma candidates, with
   `passingRECO` defined by nonzero charge. This should be reviewed as the
   intended scouting RECO denominator/numerator convention.
5. `ELECTRON_TAG_CUTS` defines `pt >= 30 GeV`, `abs(eta) <= 2.5`, and the ECAL
   gap veto, but this cut is not applied by the current scouting tag selector.
   The effective scouting tag uses `goodElectrons` plus
   `ScoutingElectronRecommendv1`. This should be confirmed or fixed before
   freezing the analysis note.
6. The same `ScoutingElectronRecommendv1` working point is used for the current
   effective tag and is also one of the measured electron probe flags.

## Code References

- Datasets, CRAB splitting, lumi mask, and cmsRun parameters:
  `TnPTreeProducer/crab/tnpCrabSubmit_ScoutingReco.py:8-176`
- Scouting baseline object cuts:
  `TnPTreeProducer/python/TnPTreeProducer_cfg.py:121-125`
- 2024 Global Tags:
  `TnPTreeProducer/python/TnPTreeProducer_cfg.py:154-181`
- Scouting event HLT path override and tag filter:
  `TnPTreeProducer/python/TnPTreeProducer_cfg.py:259-261`
- Main cmsRun path and active tree sequence:
  `TnPTreeProducer/python/TnPTreeProducer_cfg.py:477-509`
- Scouting object construction and best-track thresholds:
  `TnPTreeProducer/python/egmGoodParticlesDef_cff.py:112-163`
- Tag, probe, MC truth, and pair definitions:
  `TnPTreeProducer/python/egmTreesSetup_cff.py:44-187`
- HLT filter setup and tree arbitration:
  `TnPTreeProducer/python/egmTreesSetup_cff.py:278-296`
- Scouting electron working points:
  `TnPTreeProducer/plugins/ScoutingElectronRefSelector.cc:73-115`
- Scouting photon working points:
  `TnPTreeProducer/plugins/ScoutingPhotonRefSelector.cc:67-86`
