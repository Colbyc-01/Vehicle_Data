import json
import os

# Folder containing your chunk files
CHUNK_DIR = "./vehicle_chunks"   # change if needed

# Allowed schema keys
ALLOWED_KEYS = {"year", "make", "model", "engine", "engine_code"}

def is_malformed_honda(entry):
    if entry.get("make", "").lower() != "honda":
        return False
    extra_keys = set(entry.keys()) - ALLOWED_KEYS
    return len(extra_keys) > 0

def audit_chunks():
    print("=== AUDITING HONDA ENTRIES FOR MALFORMED STRUCTURE ===\n")

    for filename in os.listdir(CHUNK_DIR):
        if not filename.endswith(".json"):
            continue

        path = os.path.join(CHUNK_DIR, filename)

        with open(path, "r", encoding="utf-8") as f:
            try:
                data = json.load(f)
            except Exception as e:
                print(f"ERROR reading {filename}: {e}")
                continue

        malformed = [entry for entry in data if is_malformed_honda(entry)]

        if malformed:
            print(f"\n--- Found malformed Honda entries in {filename} ---")
            for entry in malformed:
                print(json.dumps(entry, indent=2))

            # Uncomment this block to automatically remove them
            
            cleaned = [e for e in data if not is_malformed_honda(e)]
            with open(path, "w", encoding="utf-8") as f:
                json.dump(cleaned, f, indent=2)
            print(f"Cleaned malformed Honda entries from {filename}")
            

    print("\n=== AUDIT COMPLETE ===")

if __name__ == "__main__":
    audit_chunks()