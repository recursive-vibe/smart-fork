"""Test script to debug embedding model loading."""
import sys
import logging

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

print("Step 1: Importing sentence_transformers...", flush=True)
from sentence_transformers import SentenceTransformer

print("Step 2: Creating SentenceTransformer instance...", flush=True)
print("  (This may download the model if not cached)", flush=True)

try:
    model = SentenceTransformer(
        "nomic-ai/nomic-embed-text-v1.5",
        trust_remote_code=True
    )
    print("Step 3: Model loaded successfully!", flush=True)

    print("Step 4: Testing embedding generation...", flush=True)
    result = model.encode(["test text"], show_progress_bar=False)
    print(f"Step 5: Embedding generated! Shape: {result.shape}", flush=True)

except Exception as e:
    print(f"ERROR: {e}", flush=True)
    import traceback
    traceback.print_exc()
