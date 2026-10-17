#!/usr/bin/env python3
"""
rea-tool-filter.py — cut REA's MCP tool list down to what a native-binary
rebuild actually needs, and write the result into OpenCode's config.

WHY THIS EXISTS
---------------
REA ships ~170 MCP tools. The agent must read every tool description before it
can call it, so all 170 descriptions alone came to ~150K tokens. The model in
this video had a 128K context window. It did not fit.

With all tools enabled the agent entered a compaction loop: context filled ->
OpenCode compacted -> the summary threw away completed work -> it started over
-> context filled again.

This script produces the `tools` block that disables 151 of them, leaving 19.

MODES
-----
  --list       Print every tool REA currently exposes.
  --derive     Work out the keep-list from an existing config:
               KEEP = (live tools) - (tools already set to false).
  --apply      Write the filtered config. Use --keep-list to override.

EXAMPLES
--------
  # see what is available
  ./rea-tool-filter.py --list

  # reproduce exactly the config from the video
  ./rea-tool-filter.py --derive --apply

  # curate by hand
  ./rea-tool-filter.py --apply --keep-list my-tools.txt

Requires: Python 3.9+, Node 20+ (for npx). REA must be installed
(`npx -y rea-agents@6.4.0 setup`) so the MCP server can start.
"""

import argparse
import json
import os
import shutil
import subprocess
import sys

DEFAULT_CMD = ["npx", "-y", "rea-agents@6.4.0", "mcp"]
DEFAULT_CONFIG = os.path.expanduser("~/.config/opencode/opencode.json")

# Tools confirmed in the recording from the video run. The full 19 are
# reconstructed by --derive; this list is the fallback when deriving is not
# possible (e.g. you cannot reach a previously generated config).
KNOWN_USED = [
    "rea_open_binary",
    "rea_list_procedures",
    "rea_batch_decompile",
    "rea_procedure_pseudo_code",
    "rea_read_bytes",
]


def die(msg, code=1):
    print(f"error: {msg}", file=sys.stderr)
    sys.exit(code)


def list_tools(cmd):
    """Speak just enough MCP-over-stdio to call tools/list."""
    if shutil.which(cmd[0]) is None:
        die(f"'{cmd[0]}' not found on PATH")

    proc = subprocess.Popen(
        cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        bufsize=1,
        encoding="utf-8",
    )

    def send(obj):
        proc.stdin.write(json.dumps(obj) + "\n")
        proc.stdin.flush()

    try:
        send({
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "rea-tool-filter", "version": "1.0.0"},
            },
        })
        send({"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}})
        send({"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}})

        # Drain stdout until tools/list answers (id 2) or we give up.
        for _ in range(200):
            line = proc.stdout.readline()
            if not line:
                break
            line = line.strip()
            if not line:
                continue
            try:
                msg = json.loads(line)
            except json.JSONDecodeError:
                continue
            if msg.get("id") != 2:
                continue
            tools = msg.get("result", {}).get("tools", [])
            return sorted(
                t["name"] for t in tools
                if t.get("name", "").startswith("rea_")
            )
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()

    return []


def load_config(path):
    if not os.path.exists(path):
        die(f"config not found: {path}")
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def derive_keep(live, config):
    """KEEP = live tools minus the ones this config already disables."""
    disabled = {
        name for name, val in (config.get("tools") or {}).items()
        if val is False
    }
    return [t for t in live if t not in disabled]


def write_config(path, keep):
    config = load_config(path)
    live = list_tools(DEFAULT_CMD)
    if not live:
        die("could not reach the REA MCP server; is `npx rea-agents@6.4.0 setup` done?")

    unknown = [t for t in keep if t not in live]
    if unknown:
        print(f"warning: not exposed by this REA version: {', '.join(unknown)}",
              file=sys.stderr)

    keep_set = set(keep)
    config["tools"] = {t: False for t in live if t not in keep_set}

    with open(path, "w", encoding="utf-8") as fh:
        json.dump(config, fh, indent=2, sort_keys=True)
        fh.write("\n")

    hidden = len(config["tools"])
    print(f"wrote {path}")
    print(f"  {len(live)} tools exposed -> {len(keep_set & set(live))} enabled, "
          f"{hidden} disabled")


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--list", action="store_true",
                    help="print every REA tool currently exposed")
    ap.add_argument("--derive", action="store_true",
                    help="derive the keep-list from an existing config")
    ap.add_argument("--apply", action="store_true",
                    help="write the filtered config")
    ap.add_argument("--config", default=DEFAULT_CONFIG,
                    help=f"path to opencode.json (default: {DEFAULT_CONFIG})")
    ap.add_argument("--keep-list", metavar="FILE",
                    help="file with one tool name per line")
    args = ap.parse_args()

    if not (args.list or args.derive or args.apply):
        args.list = True

    if args.list:
        live = list_tools(DEFAULT_CMD)
        if not live:
            die("could not reach the REA MCP server")
        print(f"{len(live)} rea_* tools:\n")
        for name in live:
            print(f"  {name}")
        return

    if args.derive:
        keep = derive_keep(list_tools(DEFAULT_CMD), load_config(args.config))
        print(f"derived keep-list ({len(keep)}):\n")
        for name in keep:
            print(f"  {name}")
        if not args.apply:
            return

    if args.apply:
        if args.keep_list:
            if not os.path.exists(args.keep_list):
                die(f"keep-list not found: {args.keep_list}")
            with open(args.keep_list, encoding="utf-8") as fh:
                keep = [ln.strip() for ln in fh if ln.strip()
                        and not ln.startswith("#")]
        elif args.derive:
            keep = derive_keep(list_tools(DEFAULT_CMD), load_config(args.config))
        else:
            keep = KNOWN_USED
        write_config(args.config, keep)


if __name__ == "__main__":
    main()