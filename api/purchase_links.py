# purchase_links.py
from __future__ import annotations

import os
from dataclasses import dataclass
from urllib.parse import quote_plus


AMAZON_TAG = os.getenv("AMAZON_AFFILIATE_TAG")  # e.g. SpecLabs-20
EBAY_CAMPID = os.getenv("EBAY_CAMPID")          # e.g. 5339141163


@dataclass(frozen=True)
class PartLinkInput:
    brand: str | None = None
    part_number: str | None = None
    name: str | None = None
    asin: str | None = None


def _query_for(p: PartLinkInput) -> str:
    # Prefer brand + part_number; fall back to name
    bits: list[str] = []
    if p.brand:
        bits.append(p.brand.strip())
    if p.part_number:
        bits.append(p.part_number.strip())
    if not bits and p.name:
        bits.append(p.name.strip())
    return " ".join(bits).strip()


def amazon_url(p: PartLinkInput) -> str | None:
    if not AMAZON_TAG:
        return None

    if p.asin:
        # Most precise
        return f"https://www.amazon.com/dp/{quote_plus(p.asin)}?tag={quote_plus(AMAZON_TAG)}"

    q = _query_for(p)
    if not q:
        return None

    # Search fallback
    return f"https://www.amazon.com/s?k={quote_plus(q)}&tag={quote_plus(AMAZON_TAG)}"


def ebay_url(p: PartLinkInput) -> str | None:
    if not EBAY_CAMPID:
        return None

    q = _query_for(p)
    if not q:
        return None

    # Stable search link + your campaign id
    return f"https://www.ebay.com/sch/i.html?_nkw={quote_plus(q)}&campid={quote_plus(EBAY_CAMPID)}"


def build_buy_links(part: dict) -> dict:
    """
    Takes a dict that already has brand/part_number/name/asin and returns:
      { "amazon": "...", "ebay": "..." }  (only includes keys that can be built)
    """
    p = PartLinkInput(
        brand=part.get("brand"),
        part_number=part.get("part_number"),
        name=part.get("name"),
        asin=part.get("asin"),
    )

    links: dict[str, str] = {}
    a = amazon_url(p)
    e = ebay_url(p)

    if a:
        links["amazon"] = a
    if e:
        links["ebay"] = e

    return links
