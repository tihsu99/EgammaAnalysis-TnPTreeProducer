#!/usr/bin/env python3
import copy
import os

from CRABClient.UserUtilities import config


submitVersion = "2026-04-09_scoutingReco"
storageSite = "T2_TW_NCHC"
workArea = f"crab_{submitVersion}"
outLFNDirBase = f"/store/user/{os.environ['USER']}/TnPTreeProducer/{submitVersion}"

MC_DATASET = "/DYto2E-2Jets_Bin-MLL-50_TuneCP5_13p6TeV_amcatnloFXFX-pythia8/RunIII2024Summer24MiniAODv6-150X_mcRun3_2024_realistic_v2-v4/MINIAODSIM"
DATA_DATASET = "/ScoutingPFRun3/Run2024F-v1/HLTSCOUT"


def get_lumi_mask(era):
    if era == "2024":
        return "https://cms-service-dqmdc.web.cern.ch/CAF/certification/Collisions24/Cert_Collisions2024_378981_386951_Golden.json"
    raise ValueError(f"Unsupported era for lumi mask: {era}")


base = config()
base.General.requestName = ""
base.General.transferLogs = False
base.General.workArea = workArea

base.JobType.pluginName = "Analysis"
base.JobType.psetName = "../python/TnPTreeProducer_cfg.py"
base.JobType.sendExternalFolder = True
base.JobType.allowUndistributedCMSSW = True

base.Data.inputDBS = "global"
base.Data.publication = False
base.Data.outLFNDirBase = outLFNDirBase

base.Site.storageSite = storageSite


def write_config(filename, crab_config):
    with open(filename, "w") as out:
        print(crab_config, file=out)


def make_mc_config():
    cfg = copy.deepcopy(base)
    cfg.General.requestName = "mc_scoutingReco_2024"
    cfg.Data.inputDataset = MC_DATASET
    cfg.Data.splitting = "FileBased"
    cfg.Data.unitsPerJob = 5
    cfg.JobType.pyCfgParams = [
        "inputFormat=miniaod",
        "objectBackend=scouting",
        "triggerBackend=patTrigger",
        "isMC=True",
        "doTrigger=False",
        "doEleID=True",
        "doPhoID=True",
        "doRECO=True",
        "era=2024",
        "HLTname=HLT",
        "triggerObjectCollection=slimmedPatTrigger",
        "scoutingElectronCollection=hltScoutingEgammaPacker",
        "scoutingPhotonCollection=hltScoutingEgammaPacker",
        "scoutingVertexCollection=hltScoutingPrimaryVertexPacker:primaryVtx",
        "scoutingRho=hltScoutingPFPacker:rho",
    ]
    return cfg


def make_data_config():
    cfg = copy.deepcopy(base)
    cfg.General.requestName = "data_scoutingReco_2024F"
    cfg.Data.inputDataset = DATA_DATASET
    cfg.Data.lumiMask = get_lumi_mask("2024")
    cfg.Data.splitting = "LumiBased"
    cfg.Data.unitsPerJob = 50
    cfg.JobType.pyCfgParams = [
        "inputFormat=hltscout",
        "objectBackend=scouting",
        "triggerBackend=triggerEvent",
        "isMC=False",
        "doTrigger=False",
        "doEleID=True",
        "doPhoID=True",
        "doRECO=True",
        "era=2024",
        "HLTname=HLT",
        "scoutingElectronCollection=hltScoutingEgammaPacker",
        "scoutingPhotonCollection=hltScoutingEgammaPacker",
        "scoutingVertexCollection=hltScoutingPrimaryVertexPacker:primaryVtx",
        "scoutingRho=hltScoutingPFPacker:rho",
        "requireTriggerObjectMatch=False",
    ]
    return cfg


def write_helper_scripts(config_names):
    with open("crab_sub.sh", "w") as sub:
        for name in config_names:
            sub.write(f"crab submit -c {name}\n")

    with open("crab_status.sh", "w") as status:
        for request_name in ["mc_scoutingReco_2024", "data_scoutingReco_2024F"]:
            status.write(f"crab status -d {workArea}/crab_{request_name} --verboseErrors\n")

    with open("crab_resub.sh", "w") as resub:
        for request_name in ["mc_scoutingReco_2024", "data_scoutingReco_2024F"]:
            resub.write(f"crab resubmit -d {workArea}/crab_{request_name}\n")


def main():
    mc_cfg_name = "crab_submit_mc_scoutingReco_2024.py"
    data_cfg_name = "crab_submit_data_scoutingReco_2024F.py"

    write_config(mc_cfg_name, make_mc_config())
    write_config(data_cfg_name, make_data_config())
    write_helper_scripts([mc_cfg_name, data_cfg_name])

    print(f"Wrote {mc_cfg_name}")
    print(f"Wrote {data_cfg_name}")
    print("Wrote crab_sub.sh, crab_status.sh, crab_resub.sh")
    print("Review DATA_DATASET before submission if your DAS name differs.")


if __name__ == "__main__":
    main()
