#!/usr/bin/env python3

"""
Copyright (C) 2025 Patrick Pedersen

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

ippdu - command-line utility to control 0816-series Smart PDUs

Usage examples
--------------
List all sockets
    ippdu -u USERNAME -p PASSWORD -H IP -l

Turn outlet #0 on
    ippdu -u USERNAME -p PASSWORD -H IP -o 0 -s 1

Toggle outlet by name
    ippdu -u USERNAME -p PASSWORD -H IP -o Socket-Name -s 0
"""

from __future__ import annotations

import argparse
import re
import sys
import xml.etree.ElementTree as ET
from enum import Enum
from typing import Callable, Dict, List, Tuple

import requests
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------


class OutletOperation(Enum):
    """Enumeration of outlet operations (as understood by the firmware)."""

    ON = "0"  # switch relay ON
    OFF = "1"  # switch relay OFF


# ---------------------------------------------------------------------------
# Helpers - HTTP fetch + HTML / XML parsing
# ---------------------------------------------------------------------------


def fetch(base_url: str, path: str, auth: Tuple[str, str], timeout: int) -> str:
    """Download *path* from *base_url* using HTTP-Basic *auth* and return text."""

    r = requests.get(f"{base_url}/{path.lstrip('/')}", auth=auth, timeout=timeout)
    r.raise_for_status()
    return r.text


_RX_CHECKBOX = re.compile(r"outlet(\d+)$")  # matches input[name="outletX"]


def parse_names(html: str) -> Dict[int, str]:
    """Extract outlet names from **control_outlet.htm**.

    Returns a mapping ``{number → name}``.
    """

    soup = BeautifulSoup(html, "html.parser")
    names: Dict[int, str] = {}

    for cb in soup.find_all("input", {"type": "checkbox"}):
        match = _RX_CHECKBOX.fullmatch(cb.get("name", ""))
        if not match:  # skip outlet_check_all
            continue
        num = int(match.group(1))
        tr = cb.find_parent("tr")
        names[num] = tr.find_all("td")[0].get_text(strip=True)

    return names


def parse_status(xml_text: str) -> Dict[int, str]:
    """Extract ON/OFF state from **status.xml** - returns ``{number → state}``."""

    root = ET.fromstring(xml_text)
    states: Dict[int, str] = {}

    for elem in root:
        if elem.tag.startswith("outletStat"):
            num = int(elem.tag.replace("outletStat", ""))
            states[num] = elem.text.strip().upper()

    return states


def list_outlets(
    base_url: str, auth: Tuple[str, str], timeout: int
) -> List[Tuple[int, str, str]]:
    """Return ``[(number, name, state), …]`` for the whole PDU."""

    names = parse_names(fetch(base_url, "control_outlet.htm", auth, timeout))
    stats = parse_status(fetch(base_url, "status.xml", auth, timeout))

    return [(n, names[n], stats.get(n, "(unknown)")) for n in sorted(names)]


# ---------------------------------------------------------------------------
# Actions - set relay state
# ---------------------------------------------------------------------------


def set_outlet(
    base_url: str,
    outlet: int,
    op: OutletOperation,
    auth: Tuple[str, str],
    timeout: int,
) -> None:
    """Send *op* command to *outlet* and wait until firmware PASSWORDs it."""

    query = f"outlet{outlet}=1&op={op.value}&submit=Apply"

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        ctx = browser.new_context(
            http_credentials={"username": auth[0], "password": auth[1]}
        )
        ctx.set_default_navigation_timeout(timeout * 1000)
        page = ctx.new_page()
        page.goto(f"{base_url}/control_outlet.htm?{query}", timeout=timeout * 1000)
        page.click("input[name='submit'][value='Apply']")
        browser.close()


# ---------------------------------------------------------------------------
# Outlet resolution - name <-> number
# ---------------------------------------------------------------------------


def resolve_outlet(arg: str, table: List[Tuple[int, str, str]]) -> int:
    """Convert *arg* (number or name) into a numeric outlet identifier."""

    # Numeric? - easy path
    if arg.isdigit():
        num = int(arg)
        if any(num == n for n, _, _ in table):
            return num
        raise ValueError(f"Outlet number {num} not present.")

    # Otherwise treat as case-insensitive name
    matches = [n for n, name, _ in table if name.lower() == arg.lower()]
    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:
        raise ValueError(
            f'Multiple outlets named "{arg}". Specify the number instead. Matches: {matches}'
        )
    raise ValueError(f'No outlet named "{arg}" found.')


# ---------------------------------------------------------------------------
# CLI parsing & orchestration
# ---------------------------------------------------------------------------


def build_cli() -> argparse.ArgumentParser:
    """Create and return the ArgumentParser for *ippdu* CLI."""

    parser = argparse.ArgumentParser(description="Control a Microchip-based IP PDU")

    parser.add_argument("-u", "--user", required=True, help="HTTP-Basic username")
    parser.add_argument("-p", "--password", required=True, help="HTTP-Basic password")
    parser.add_argument("-H", "--host", required=True, help="PDU hostname or IP")
    parser.add_argument(
        "-t",
        "--timeout",
        type=int,
        default=5,
        help="Network / browser timeout in seconds (default: 5)",
    )

    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("-l", "--list", action="store_true", help="List all outlets")
    mode.add_argument("-o", "--outlet", help="Outlet NUMBER or NAME to act on")

    parser.add_argument(
        "-s",
        "--state",
        choices=["0", "1"],
        help="Desired state for -o (0 = off, 1 = on)",
    )

    return parser


def main(argv: List[str] | None = None) -> None:  # noqa: D401 - simple style
    """Entry-point for the *ippdu* command-line utility."""

    parser = build_cli()
    args = parser.parse_args(argv)

    base_url = f"http://{args.host.strip('/')}"
    auth = (args.user, args.password)

    if args.list:
        for num, name, state in list_outlets(base_url, auth, args.timeout):
            print(f"{num}  {name:<15}  {state}")
        return

    # From here on we need -s/--state
    if args.state is None:
        parser.error("-s/--state is required when using -o/--outlet")

    table = list_outlets(base_url, auth, args.timeout)
    try:
        outlet_num = resolve_outlet(args.outlet, table)
    except ValueError as exc:
        parser.error(str(exc))

    outlet_name = next(name for n, name, _ in table if n == outlet_num)

    op = OutletOperation.ON if args.state == "1" else OutletOperation.OFF
    set_outlet(base_url, outlet_num, op, auth, args.timeout)
    print(
        f"Outlet {outlet_num} ({outlet_name}) set to {'ON' if op is OutletOperation.ON else 'OFF' }."
    )


if __name__ == "__main__":
    sys.exit(main())
