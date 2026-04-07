#!/usr/bin/env python3

import argparse
import collections
import fnmatch
import sys

import ROOT
from DataFormats.FWLite import Events, Handle


def parse_args():
    parser = argparse.ArgumentParser(
        description="Inspect HLT paths and trigger filters from a CMS EDM file."
    )
    parser.add_argument("input_file", help="Input EDM ROOT file")
    parser.add_argument(
        "--process",
        default="HLT",
        help="Process name for TriggerResults / trigger summary (default: HLT)",
    )
    parser.add_argument(
        "--events",
        type=int,
        default=50,
        help="Number of events to inspect (default: 50)",
    )
    parser.add_argument(
        "--path-pattern",
        default="*",
        help="Only show HLT paths matching this shell-style pattern (default: *)",
    )
    parser.add_argument(
        "--show-all-paths",
        action="store_true",
        help="Print all matching HLT paths from the first event, not just fired ones",
    )
    return parser.parse_args()


def main():
    args = parse_args()

    ROOT.gROOT.SetBatch(True)
    events = Events([args.input_file])

    trigger_bits = Handle("edm::TriggerResults")
    trigger_summary = Handle("trigger::TriggerEvent")

    path_counts = collections.Counter()
    filter_counts = collections.Counter()
    all_matching_paths = []
    seen_paths = False
    processed = 0

    for event in events:
        if processed >= args.events:
            break
        processed += 1

        event.getByLabel("TriggerResults", "", args.process, trigger_bits)
        if not trigger_bits.isValid():
            print(
                "TriggerResults not found for process '%s' in event %d"
                % (args.process, processed),
                file=sys.stderr,
            )
            continue

        names = event.object().triggerNames(trigger_bits.product())
        if not seen_paths:
            for i in range(trigger_bits.product().size()):
                name = names.triggerName(i)
                if fnmatch.fnmatch(name, args.path_pattern):
                    all_matching_paths.append(name)
            seen_paths = True

        for i in range(trigger_bits.product().size()):
            if not trigger_bits.product().accept(i):
                continue
            name = names.triggerName(i)
            if fnmatch.fnmatch(name, args.path_pattern):
                path_counts[name] += 1

        event.getByLabel("hltTriggerSummaryAOD", "", args.process, trigger_summary)
        if trigger_summary.isValid():
            summary = trigger_summary.product()
            for i in range(summary.sizeFilters()):
                try:
                    label = summary.filterLabel(i)
                except Exception:
                    tag = summary.filterTag(i)
                    label = tag.label()
                if label:
                    filter_counts[label] += 1

    if processed == 0:
        print("No events processed.", file=sys.stderr)
        return 1

    print("Input file: %s" % args.input_file)
    print("Trigger process: %s" % args.process)
    print("Events inspected: %d" % processed)
    print("")

    if seen_paths:
        print("Matching HLT paths in the file:")
        if all_matching_paths:
            for name in sorted(all_matching_paths):
                if args.show_all_paths or path_counts[name] > 0:
                    print("  %-80s fired %d times" % (name, path_counts[name]))
        else:
            print("  No HLT paths matched pattern '%s'" % args.path_pattern)
        print("")

    print("Fired HLT paths (sorted by count):")
    if path_counts:
        for name, count in sorted(path_counts.items(), key=lambda item: (-item[1], item[0])):
            print("  %-80s %d" % (name, count))
    else:
        print("  No fired HLT paths matched pattern '%s'" % args.path_pattern)
    print("")

    print("Trigger summary filters seen (sorted by count):")
    if filter_counts:
        for name, count in sorted(filter_counts.items(), key=lambda item: (-item[1], item[0])):
            print("  %-80s %d" % (name, count))
    else:
        print("  No trigger::TriggerEvent found at hltTriggerSummaryAOD::%s" % args.process)

    return 0


if __name__ == "__main__":
    sys.exit(main())
