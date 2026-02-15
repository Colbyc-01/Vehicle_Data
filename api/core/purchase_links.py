# purchase_links.py
from __future__ import annotations
print("purchase_links loaded from:", __file__)
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
    if p.name:
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


from urllib.parse import quote_plus

def build_buy_links(p: dict) -> dict:
    print("BUY LINK INPUT:", p)

    link_input = PartLinkInput(
        brand=p.get("brand"),
        part_number=p.get("part_number"),
        name=p.get("name"),
    )

    return {
        "amazon": amazon_url(link_input),
        "ebay": ebay_url(link_input),
    }
