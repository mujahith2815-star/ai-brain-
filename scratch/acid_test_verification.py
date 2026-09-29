"""
Acid Test Verification for P.H.A.S.S Autonomic Recovery Circuit.
Demonstrates:
1. Deleting 'import re' from tools/web_search.py.
2. Triggering a search and intercepting the NameError.
3. Observing the Autonomic Circuit catch, classify, sandbox-validate, and hot-deploy the fix.
4. Confirming search immediately succeeds after autonomous hot-repair.
"""

import asyncio
import importlib
import sys
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from core.autonomic_circuit import autonomic_circuit


async def run_acid_test():
    web_search_file = PROJECT_ROOT / "tools" / "web_search.py"
    print(f"=== ACID TEST: AUTONOMIC ERROR RECOVERY CIRCUIT ===")
    print(f"Target Module: {web_search_file}\n")

    # Step 1: Intentionally remove 'import re' from tools/web_search.py
    print("[Step 1] Intentionally deleting 'import re' from tools/web_search.py...")
    content = web_search_file.read_text(encoding="utf-8")
    corrupted_content = content.replace("import re\n", "")
    web_search_file.write_text(corrupted_content, encoding="utf-8")

    # Invalidate caches and unload module completely to simulate fresh process execution
    if "tools.web_search" in sys.modules:
        del sys.modules["tools.web_search"]
    importlib.invalidate_caches()
    import tools.web_search

    # Step 2: Trigger web search and observe failure
    print("[Step 2] Executing search query 'arduino decoupling capacitor'...")
    caught_error = None
    try:
        await tools.web_search.web_search("arduino decoupling capacitor")
        print("UNEXPECTED: Search did not raise error!")
    except NameError as ne:
        caught_error = ne
        print(f"-> CAUGHT RUNTIME ERROR: {type(ne).__name__}: {ne}")

    assert caught_error is not None, "Acid test failed: NameError was not raised."

    # Step 3: Trigger Autonomic Circuit Self-Healing
    print("\n[Step 3] Engaging Autonomic Circuit closed-loop self-repair...")
    heal_result = autonomic_circuit.heal_runtime_error(
        error_or_text=caught_error,
        file_path=str(web_search_file),
    )

    print(f"-> Diagnosis: {heal_result.analyzed_error.error_type} ({heal_result.analyzed_error.category})")
    print(f"-> Similarity Match: {heal_result.analyzed_error.cached_fix.get('description') if heal_result.analyzed_error.cached_fix else 'None'}")
    print(f"-> Generated Fix Confidence: {heal_result.generated_fix.confidence * 100:.1f}%")
    print(f"-> Sandbox Syntax OK: {heal_result.validation_result.syntax_ok}")
    print(f"-> Pre-Fix Backup: {Path(heal_result.deployment_result.backup_path).name}")
    print(f"-> Hot Deployment Success: {heal_result.deployment_result.success}")
    print(f"-> Circuit Message: {heal_result.message}")

    # Step 4: Verify search now succeeds seamlessly
    print("\n[Step 4] Re-triggering search query through restored module...")
    if "tools.web_search" in sys.modules:
        del sys.modules["tools.web_search"]
    importlib.invalidate_caches()
    import tools.web_search

    res = await tools.web_search.web_search("arduino decoupling capacitor")
    print(f"-> Search Status: {res.get('status')}")
    print(f"-> Snippet: {res.get('results', [{}])[0].get('snippet', '')[:120]}...")

    # Step 5: Verify live file has import re restored
    final_content = web_search_file.read_text(encoding="utf-8")
    assert "import re" in final_content
    print("\n[SUCCESS] ACID TEST COMPLETE: System autonomously detected, validated, deployed, and verified fix!")


if __name__ == "__main__":
    asyncio.run(run_acid_test())
