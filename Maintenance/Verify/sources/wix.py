from __future__ import annotations

import html
import re
import urllib.parse
import urllib.request
from dataclasses import dataclass, asdict
from typing import Any


WIX_APPLICATION_URL = "https://www2.wixfilters.com/Lookup/PartApplications.aspx?Part={part}"


@dataclass(frozen=True)
class WixApplication:
    make: str
    model: str
    year_min: int | None
    year_max: int | None
    engine: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _text(fragment: str) -> str:
    value = re.sub(r"<[^>]+>", " ", fragment)
    value = html.unescape(value)
    return " ".join(value.split())


def _years(value: str) -> tuple[int | None, int | None]:
    found = [int(x) for x in re.findall(r"\b(?:19|20)\d{2}\b", value)]
    if not found:
        return None, None
    if len(found) == 1:
        return found[0], found[0]
    return min(found), max(found)


def fetch_applications(part_number: str, timeout: float = 20.0) -> list[WixApplication]:
    part = re.sub(r"[^A-Za-z0-9]", "", str(part_number or "")).upper()
    if not part:
        return []

    url = WIX_APPLICATION_URL.format(part=urllib.parse.quote(part))
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0 AutoSpecVerification/1.0"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as response:
        page = response.read().decode("utf-8", errors="replace")

    applications: list[WixApplication] = []
    for row in re.findall(r"<tr\b[^>]*>(.*?)</tr>", page, flags=re.I | re.S):
        cells = [_text(cell) for cell in re.findall(r"<td\b[^>]*>(.*?)</td>", row, flags=re.I | re.S)]
        cells = [cell for cell in cells if cell]
        if len(cells) < 4:
            continue

        # WIX currently renders rows as: [image/marker], make, model, year, engine.
        # Some locales omit the marker column, so consume from the right.
        make, model, year_text, engine = cells[-4:]
        if make.lower() == "make" or year_text.lower() == "year":
            continue
        y0, y1 = _years(year_text)
        if not make or not model:
            continue
        applications.append(WixApplication(make=make, model=model, year_min=y0, year_max=y1, engine=engine))

    return applications
