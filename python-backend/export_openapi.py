"""Export the FastAPI OpenAPI spec to a static JSON file."""

import json
from pathlib import Path

if __name__ == "__main__":
    from src.main import app

    spec = app.openapi()
    output = Path(__file__).parent.parent / "openapi.json"
    output.write_text(json.dumps(spec, indent=2))
    print(f"OpenAPI spec exported to {output}")
