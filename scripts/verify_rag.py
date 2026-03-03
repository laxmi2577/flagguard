
import sys
try:
    import chromadb
    print("✅ chromadb imported successfully")
except ImportError as e:
    print(f"❌ chromadb import failed: {e}")

try:
    from sentence_transformers import SentenceTransformer
    print("✅ sentence-transformers imported successfully")
except ImportError as e:
    print(f"❌ sentence-transformers import failed: {e}")
