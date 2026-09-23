"""
MongoDB & Document Database Skill for J.A.R.V.I.S.
Allows autonomous storage, querying, indexing, and retrieval of documents
using native MongoDB or local persistent fallback store.
"""
import json
from database.mongodb_manager import get_mongodb_manager

MANIFEST = {
    "name": "mongodb_document_store",
    "description": "Store, query, inspect, and manage JSON documents and collections in MongoDB or local persistent document store.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {
                "type": "STRING",
                "description": "Operation to perform: 'status', 'insert', 'find', 'delete', 'list_collections'"
            },
            "collection": {
                "type": "STRING",
                "description": "Collection name (e.g. 'trading_signals', 'user_preferences', 'system_telemetry')"
            },
            "document": {
                "type": "OBJECT",
                "description": "Document to insert, or filter dictionary to search/delete"
            },
            "limit": {
                "type": "INTEGER",
                "description": "Maximum number of records to return on find"
            }
        },
        "required": ["action"]
    }
}


def run(parameters: dict, player=None, speak=None) -> str:
    action = parameters.get("action", "status").lower()
    collection = parameters.get("collection", "general_logs")
    document = parameters.get("document", {})
    limit = parameters.get("limit", 20)

    mgr = get_mongodb_manager()

    if action == "status":
        st = mgr.status()
        res = (
            f"📦 [MONGODB / DOCUMENT STORE STATUS]\n"
            f"• Mode: {st['mode']}\n"
            f"• URI: {st['uri']}\n"
            f"• Database: {st['db_name']}\n"
            f"• Total Collections: {st['collections_count']}\n"
            f"• Engine: Native PyMongo v4.16 + Local SQLite JSON Fallback"
        )
        if speak:
            speak("MongoDB document store is operational.")
        return res

    elif action == "list_collections":
        cols = mgr.list_collections()
        return f"📂 Collections in database: {', '.join(cols) if cols else 'No collections yet'}"

    elif action in ("insert", "add", "save"):
        if not document:
            return "Error: Document payload is required for insertion."
        result = mgr.insert_one(collection, document)
        if result.get("ok"):
            return f"✅ Document inserted into '{collection}' [ID: {result.get('inserted_id')}] via {result.get('mode')}."
        return f"❌ Insertion failed: {result.get('error')}"

    elif action in ("find", "query", "search"):
        docs = mgr.find(collection, query=document, limit=limit)
        return (
            f"🔍 Found {len(docs)} documents in '{collection}':\n"
            f"{json.dumps(docs, indent=2, default=str)}"
        )

    elif action in ("delete", "remove"):
        if not document:
            return "Error: Query filter is required for document deletion."
        result = mgr.delete_one(collection, document)
        return f"🗑️ Deletion complete from '{collection}': deleted {result.get('deleted_count', 0)} document(s)."

    else:
        return f"Unknown action: '{action}'. Supported actions: status, insert, find, delete, list_collections."
