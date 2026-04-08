#!/usr/bin/env python3

import argparse
import math
import sys

import ROOT
from DataFormats.FWLite import Events, Handle


def parse_args():
    parser = argparse.ArgumentParser(
        description="Check whether Run3ScoutingElectron and Run3ScoutingPhoton overlap in an EDM file."
    )
    parser.add_argument("input_file", help="Input EDM ROOT file")
    parser.add_argument("--events", type=int, default=-1, help="Number of events to inspect (-1 means all events)")
    parser.add_argument("--process", default="HLT", help="Process name (default: HLT)")
    parser.add_argument("--module", default="hltScoutingEgammaPacker", help="Module label for scouting egamma")
    parser.add_argument("--electron-instance", default="", help="Product instance name for scouting electrons")
    parser.add_argument("--photon-instance", default="", help="Product instance name for scouting photons")
    parser.add_argument("--pt-tol", type=float, default=1e-6, help="Absolute pt tolerance for one-to-one overlap test")
    parser.add_argument("--eta-tol", type=float, default=1e-6, help="Absolute eta tolerance for one-to-one overlap test")
    parser.add_argument("--phi-tol", type=float, default=1e-6, help="Absolute phi tolerance for one-to-one overlap test")
    parser.add_argument(
        "--dr-report-threshold",
        type=float,
        default=0.01,
        help="Report events with electron-photon pairs closer than this deltaR threshold",
    )
    parser.add_argument(
        "--max-print",
        type=int,
        default=20,
        help="Maximum number of overlap / close-pair events to print",
    )
    return parser.parse_args()


def make_event_id(event):
    aux = event.eventAuxiliary()
    return "%d:%d:%d" % (aux.run(), aux.luminosityBlock(), aux.event())


def delta_phi(phi1, phi2):
    dphi = phi1 - phi2
    while dphi > math.pi:
        dphi -= 2.0 * math.pi
    while dphi <= -math.pi:
        dphi += 2.0 * math.pi
    return dphi


def delta_r(obj1, obj2):
    deta = obj1.eta() - obj2.eta()
    dphi = delta_phi(obj1.phi(), obj2.phi())
    return math.sqrt(deta * deta + dphi * dphi)


def same_candidate(ele, pho, args):
    return (
        abs(ele.pt() - pho.pt()) <= args.pt_tol
        and abs(ele.eta() - pho.eta()) <= args.eta_tol
        and abs(delta_phi(ele.phi(), pho.phi())) <= args.phi_tol
    )


def format_obj(obj):
    return "pt={:.6f} eta={:.6f} phi={:.6f}".format(obj.pt(), obj.eta(), obj.phi())


def main():
    args = parse_args()
    ROOT.gROOT.SetBatch(True)

    ele_handle = Handle("std::vector<Run3ScoutingElectron>")
    pho_handle = Handle("std::vector<Run3ScoutingPhoton>")

    processed = 0
    total_ele = 0
    total_pho = 0
    overlap_events = []
    close_events = []
    exact_overlap_pairs = 0
    events_with_exact_overlap = 0
    events_with_close_pairs = 0
    global_min_dr = None
    global_min_dr_event = None

    events = Events([args.input_file])

    for event in events:
        if args.events >= 0 and processed >= args.events:
            break

        processed += 1
        event_id = make_event_id(event)
        event.getByLabel(args.module, args.electron_instance, args.process, ele_handle)
        event.getByLabel(args.module, args.photon_instance, args.process, pho_handle)

        if not ele_handle.isValid() or not pho_handle.isValid():
            print(
                "Missing collection in event {} (electrons valid: {}, photons valid: {})".format(
                    event_id, ele_handle.isValid(), pho_handle.isValid()
                ),
                file=sys.stderr,
            )
            return 2

        electrons = ele_handle.product()
        photons = pho_handle.product()
        total_ele += len(electrons)
        total_pho += len(photons)

        event_exact_pairs = []
        event_close_pairs = []
        event_min_dr = None

        for ie, ele in enumerate(electrons):
            for ip, pho in enumerate(photons):
                dr = delta_r(ele, pho)
                if event_min_dr is None or dr < event_min_dr:
                    event_min_dr = dr
                if global_min_dr is None or dr < global_min_dr:
                    global_min_dr = dr
                    global_min_dr_event = (event_id, ie, ip, format_obj(ele), format_obj(pho))
                if same_candidate(ele, pho, args):
                    event_exact_pairs.append((ie, ip, dr, format_obj(ele), format_obj(pho)))
                if dr < args.dr_report_threshold:
                    event_close_pairs.append((ie, ip, dr, format_obj(ele), format_obj(pho)))

        if event_exact_pairs:
            exact_overlap_pairs += len(event_exact_pairs)
            events_with_exact_overlap += 1
            if len(overlap_events) < args.max_print:
                overlap_events.append((event_id, event_exact_pairs))

        if event_close_pairs:
            events_with_close_pairs += 1
            if len(close_events) < args.max_print:
                close_events.append((event_id, event_close_pairs[:10]))

    if processed == 0:
        print("No events processed.", file=sys.stderr)
        return 1

    print("Input file: {}".format(args.input_file))
    print("Process: {}".format(args.process))
    print("Module: {}".format(args.module))
    print("Electron instance: {!r}".format(args.electron_instance))
    print("Photon instance: {!r}".format(args.photon_instance))
    print("Events inspected: {}".format(processed))
    print("Total scouting electrons: {}".format(total_ele))
    print("Total scouting photons: {}".format(total_pho))
    print("")
    print("Exact-overlap test:")
    print("  tolerances: pt <= {}, eta <= {}, |deltaPhi| <= {}".format(args.pt_tol, args.eta_tol, args.phi_tol))
    print("  events with exact overlaps: {}".format(events_with_exact_overlap))
    print("  total exact-overlap pairs: {}".format(exact_overlap_pairs))
    print("")
    print("Close-pair report:")
    print("  deltaR threshold: {}".format(args.dr_report_threshold))
    print("  events with close e-gamma pairs: {}".format(events_with_close_pairs))
    if global_min_dr is not None:
        print("  global minimum deltaR: {:.6g}".format(global_min_dr))
        print("  at event {} (electron #{}, photon #{})".format(global_min_dr_event[0], global_min_dr_event[1], global_min_dr_event[2]))
        print("    electron: {}".format(global_min_dr_event[3]))
        print("    photon:   {}".format(global_min_dr_event[4]))
    print("")

    if overlap_events:
        print("First events with exact overlaps:")
        for event_id, pairs in overlap_events:
            print("  {}".format(event_id))
            for ie, ip, dr, ele_desc, pho_desc in pairs:
                print("    ele #{}, pho #{}, dR={:.6g}".format(ie, ip, dr))
                print("      electron: {}".format(ele_desc))
                print("      photon:   {}".format(pho_desc))
    print("")

    if close_events:
        print("First events with close e-gamma pairs:")
        for event_id, pairs in close_events:
            print("  {}".format(event_id))
            for ie, ip, dr, ele_desc, pho_desc in pairs:
                print("    ele #{}, pho #{}, dR={:.6g}".format(ie, ip, dr))
                print("      electron: {}".format(ele_desc))
                print("      photon:   {}".format(pho_desc))

    return 0


if __name__ == "__main__":
    sys.exit(main())
