"""
Shared fixtures for backend tests.

Uses mongomock-like in-memory dicts to avoid needing a real MongoDB.
We patch app.database.get_db to return a fake DB object whose collections
are backed by simple lists, supporting the MongoDB operations used by the routes.
"""
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from bson import ObjectId


# ---------------------------------------------------------------------------
# Fake MongoDB collection that supports the operations our routes use
# ---------------------------------------------------------------------------
class FakeCollection:
    """Minimal async MongoDB collection backed by a Python list."""

    def __init__(self):
        self.docs: list[dict] = []

    async def insert_one(self, doc: dict):
        if "_id" not in doc:
            doc["_id"] = ObjectId()
        self.docs.append(doc)
        result = MagicMock()
        result.inserted_id = doc["_id"]
        return result

    async def find_one(self, filter_: dict):
        for doc in self.docs:
            if all(doc.get(k) == v for k, v in filter_.items()):
                return dict(doc)
        return None

    async def update_one(self, filter_: dict, update: dict):
        matched = 0
        modified = 0
        for doc in self.docs:
            if all(doc.get(k) == v for k, v in filter_.items()):
                matched += 1
                if "$set" in update:
                    doc.update(update["$set"])
                    modified += 1
                if "$inc" in update:
                    for k, v in update["$inc"].items():
                        doc[k] = doc.get(k, 0) + v
                    modified += 1
                break
        result = MagicMock()
        result.matched_count = matched
        result.modified_count = modified
        return result
