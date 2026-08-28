# SPDX-License-Identifier: Apache-2.0
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from szl_serve.schema import validate_plan
from szl_serve.energy import measure_or_unavailable
from szl_serve.pins import MODEL_ID, LIVE_LAB, GPU_ATTENTION

def test_rejects_hallucinated_citation():
    plan = json.loads((Path(__file__).parent / "fixtures" / "hallucinated.json").read_text())
    ok, msg = validate_plan(plan)
    assert ok is False
    assert "hallucinated" in msg

def test_energy_cpu_unavailable_or_measured():
    j, lab = measure_or_unavailable()
    assert lab in ("UNAVAILABLE", "MEASURED", "SAMPLE")
    if lab != "MEASURED":
        assert j is None

def test_pins():
    assert "67d60ec577730747055491640cfb91fc4a4b5d25" in MODEL_ID
    assert LIVE_LAB.startswith("https://szlholdings-szl-model-inference-lab")
    assert GPU_ATTENTION == "ROADMAP"
