"""Wire exported full scouting IDs into TnP probe flags and optional tag selection."""
import gzip
import json
import os
import re


COMMON_VARIABLES = {name: name for name in
                    ("pt", "eta", "phi", "m", "sigmaIetaIeta", "hOverE", "ecalIso", "hcalIso", "r9")}
OBJECT_VARIABLES = {
    "electron": dict(COMMON_VARIABLES, **{name: name for name in
                     ("dEtaIn", "dPhiIn", "ooEMOop", "missingHits", "trackIso")}),
    "photon": dict(COMMON_VARIABLES, trkIso="trkIso"),
}


def load_working_points(filename):
    """Discover full IDs, excluding private components; no correctionlib Python dependency."""
    filename = os.path.expandvars(os.path.expanduser(filename))
    opener = gzip.open if filename.endswith(".gz") else open
    with opener(filename, "rt") as handle:
        payload = json.load(handle)
    if payload.get("schema_version") != 2:
        raise ValueError("Scouting ID correctionlib must use schema version 2: " + filename)
    entries = payload.get("compound_corrections") or payload.get("corrections", [])
    result = {}
    for entry in entries:
        name = entry["name"]
        if name.startswith("__id__/"):
            continue
        if name in result:
            raise ValueError("Duplicate correctionlib WP: " + name)
        if entry.get("output", {}).get("name") != "pass" or entry["output"].get("type") != "real":
            raise ValueError("Provide scouting_id.json(.gz), not calibration or scale-factor JSON: " + name)
        inputs = entry["inputs"]
        if any(item["type"] != "real" for item in inputs):
            raise ValueError("Scouting full IDs require real raw inputs: " + name)
        if len({item["name"] for item in inputs}) != len(inputs):
            raise ValueError("Duplicate correctionlib inputs: " + name)
        result[name] = entry
    if not result:
        raise ValueError("No full ID working points found in " + filename)
    return filename, result


def _selector(options, particle, filename, entry, cut=""):
    import FWCore.ParameterSet.Config as cms

    variables = dict(OBJECT_VARIABLES[particle])
    variables.update(options.get("SCOUTING_ID_VARIABLES", {}).get(particle, {}))
    event_variables = {"ScoutingRho.fixedGridRhoFastjetAll": options["SCOUTING_RHO"]}
    event_variables.update(options.get("SCOUTING_ID_EVENT_VARIABLES", {}))
    mappings = []
    for item in entry["inputs"]:
        name = item["name"]
        if name in variables and name in event_variables:
            raise ValueError("Ambiguous correctionlib input mapping: " + name)
        if name in event_variables:
            mappings.append(cms.PSet(name=cms.string(name), src=cms.InputTag(event_variables[name])))
        elif name in variables:
            mappings.append(cms.PSet(name=cms.string(name), expression=cms.string(variables[name])))
        else:
            raise ValueError("Unmapped raw input for {} WP {}: {}".format(particle, entry["name"], name))
    return cms.EDProducer(
        "Scouting{}CorrectionlibRefSelector".format(particle.title()),
        input=cms.InputTag("goodElectrons" if particle == "electron" else "goodPhotons"),
        src=cms.InputTag(options["ELECTRON_COLL" if particle == "electron" else "PHOTON_COLL"]),
        candidates=cms.InputTag("scoutingElectrons" if particle == "electron" else "scoutingPhotons"),
        correctionFile=cms.string(filename), workingPoint=cms.string(entry["name"]),
        variables=cms.VPSet(*mappings), cut=cms.string(cut),
    )


def configure_scouting_ids(process, options, sequence, particle):
    """Add passing collections without changing the baseline probes or pair denominator."""
    bundles = {}
    for kind in ("electron", "photon"):
        filename = options.get("SCOUTING_{}_ID".format(kind.upper()), "")
        if filename:
            bundles[kind] = load_working_points(filename)

    # Photon IDs are also measured on electron probes, as in the existing scouting setup.
    for kind, (filename, entries) in bundles.items():
        if particle == "photon" and kind != "photon":
            continue
        for name, entry in entries.items():
            suffix = re.sub(r"[^A-Za-z0-9_]", "_", name)
            module_name = "probe{}Correctionlib{}_{}".format("Ele" if particle == "electron" else "Pho",
                                                             kind.title(), suffix)
            if hasattr(process, module_name):
                raise ValueError("Correctionlib WP module name collision: " + module_name)
            module = _selector(options, particle, filename, entry)
            setattr(process, module_name, module)
            sequence += module

    tag = options.get("SCOUTING_TAG_WP", "")
    if particle == "electron" and tag:
        kind, separator, name = tag.partition(":")
        if not separator or kind not in bundles or name not in bundles[kind][1]:
            available = ["{}:{}".format(kind, name) for kind, (_, entries) in bundles.items() for name in entries]
            raise ValueError("Unknown scoutingTagWP {!r}; available: {}".format(tag, ", ".join(available)))
        filename, entries = bundles[kind]
        process.tagEleCutBasedTight = _selector(options, "electron", filename, entries[name],
                                               cut=options["ELECTRON_TAG_CUTS"])
