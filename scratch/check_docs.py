import sys
import os
sys.path.append(os.getcwd())
from core.vectorstore import get_qdrant_client
from config import settings

client = get_qdrant_client()
collection_name = settings.QDRANT_COLLECTION_NAME

if client.collection_exists(collection_name):
    info = client.get_collection(collection_name)
    print(f"Collection: {collection_name}")
    print(f"Points count: {info.points_count}")
    print(f"Status: {info.status}")
else:
    print(f"Collection {collection_name} does NOT exist.")

from knowledge.registry import load_registry
records = load_registry()
print(f"Registry documents count: {len(records)}")
for r in records:
    print(f" - {r.get('source_file')} (id: {r.get('doc_id')})")
