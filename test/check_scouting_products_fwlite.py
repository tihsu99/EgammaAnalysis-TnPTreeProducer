#!/usr/bin/env python3

import argparse
import collections
import sys

import ROOT
from DataFormats.FWLite import Events, Handle


def parse_args():
    parser = argparse.ArgumentParser(
        description="Check per-event presence of scouting products in an EDM file."
    )
    parser.add_argument("input_file", help="Input EDM ROOT file")
    parser.add_argument(
        "--events",
        type=int,
        default=-1,
        help="Number of events to inspect (-1 means all events)",
    )
    parser.add_argument(
        "--process",
        default="HLT",
        help="Process name to inspect (default: HLT)",
    )
    parser.add_argument(
        "--module",
        default="hltScoutingEgammaPacker",
        help="Module label for scouting egamma objects (default: hltScoutingEgammaPacker)",
    )
    parser.add_argument(
        "--electron-instance",
        default="Run3ScoutingElectron",
        help="Product instance name for scouting electrons",
    )
    parser.add_argument(
        "--photon-instance",
        default="Run3ScoutingPhoton",
        help="Product instance name for scouting photons",
    )
    parser.add_argument(
        "--vertex-module",
        default="hltScoutingPrimaryVertexPacker",
        help="Module label for scouting vertices",
    )
    parser.add_argument(
        "--vertex-instance",
        default="primaryVtx",
        help="Product instance name for scouting vertices",
    )
    parser.add_argument(
        "--rho-module",
        default="hltScoutingPFPacker",
        help="Module label for scouting rho",
    )
    parser.add_argument(
        "--rho-instance",
        default="rho",
        help="Product instance name for scouting rho",
    )
    parser.add_argument(
        "--max-missing-print",
        type=int,
        default=20,
        help="Max number of missing events to print per product",
    )
    return parser.parse_args()


def make_event_id(event):
    aux = event.eventAuxiliary()
    return "%d:%d:%d" % (aux.run(), aux.luminosityBlock(), aux.event())


def format_label(module, instance, process):
    return "%s:%s:%s" % (module, instance, process)


def main():
    args = parse_args()
    ROOT.gROOT.SetBatch(True)

    handles = {
        "electrons": Handle("std::vector<Run3ScoutingElectron>"),
        "photons": Handle("std::vector<Run3ScoutingPhoton>"),
        "vertices": Handle("std::vector<Run3ScoutingVertex>"),
        "rho": Handle("double"),
    }

    labels = {
        "electrons": (args.module, args.electron_instance, args.process),
        "photons": (args.module, args.photon_instance, args.process),
        "vertices": (args.vertex_module, args.vertex_instance, args.process),
        "rho": (args.rho_module, args.rho_instance, args.process),
    }

    stats = collections.OrderedDict(
        (name, {"present": 0, "missing": 0, "missing_events": []})
        for name in ["electrons", "photons", "vertices", "rho"]
    )

    processed = 0
    events = Events([args.input_file])

    for event in events:
        if args.events >= 0 and processed >= args.events:
            break
        processed += 1
        event_id = make_event_id(event)

        for name, handle in handles.items():
            module, instance, process = labels[name]
            event.getByLabel(module, instance, process, handle)
            if handle.isValid():
                stats[name]["present"] += 1
            else:
                stats[name]["missing"] += 1
                if len(stats[name]["missing_events"]) < args.max_missing_print:
                    stats[name]["missing_events"].append(event_id)

    if processed == 0:
        print("No events processed.", file=sys.stderr)
        return 1

    print("Input file: %s" % args.input_file)
    print("Process: %s" % args.process)
    print("Events inspected: %d" % processed)
    print("")

    for name, result in stats.items():
        module, instance, process = labels[name]
        print("%s (%s)" % (name, format_label(module, instance, process)))
        print("  present: %d" % result["present"])
        print("  missing: %d" % result["missing"])
        if result["missing_events"]:
            print("  first missing events:")
            for event_id in result["missing_events"]:
                print("    %s" % event_id)
        print("")

    return 0


if __name__ == "__main__":
    sys.exit(main())
