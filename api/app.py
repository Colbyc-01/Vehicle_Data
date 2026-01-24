from fastapi import FastAPI, HTTPException
from pathlib import Path
import json

app = FastAPI(title="Car Maintenance API", version="0.1")

ROOT = Path(__file__).resolve().parents[1]  # project root
VEHICLES_PATH = ROOT / "data" / "canonical" / "vehicles.json"
ENGINES_PATH = ROOT / "data" / "canonical" / "engines.json"

def load_json(path: Path):
    if not path.exists():
        raise FileNotFoundError(str(path))
    return json.loads(path.read_text(encoding="utf-8"))

@app.get("/health")
def health():
    return {"ok": True}

@app.get("/vehicles")
def vehicles():
    data = load_json(VEHICLES_PATH)
    # supports {"vehicles":[...]} format
    if isinstance(data, dict) and "vehicles" in data:
        return {"vehicles": data["vehicles"]}
    # supports [...] format
    if isinstance(data, list):
        return {"vehicles": data}
    return {"vehicles": []}

@app.get("/vehicles/search")
def vehicle_search(year: int, make: str, model: str, trim: str | None = None):
    data = load_json(VEHICLES_PATH)
    items = data["vehicles"] if isinstance(data, dict) and "vehicles" in data else data

    make_l = make.strip().lower()
    model_l = model.strip().lower()
    trim_l = trim.strip().lower() if trim else None

    matches = []
    for v in items:
        if int(v.get("year", -1)) != year:
            continue
        if str(v.get("make", "")).strip().lower() != make_l:
            continue
        if str(v.get("model", "")).strip().lower() != model_l:
            continue
        if trim_l and str(v.get("trim", "")).strip().lower() != trim_l:
            continue
        matches.append(v)

    return {"count": len(matches), "vehicles": matches}

@app.get("/engines")
def engines():
    data = load_json(ENGINES_PATH)
    return data

@app.get("/catalog/makes")
def makes():
    data = load_json(VEHICLES_PATH)
    items = data["vehicles"] if "vehicles" in data else data
    return sorted({v.get("make") for v in items if v.get("make")})
