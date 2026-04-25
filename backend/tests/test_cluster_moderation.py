"""Tests for cluster hide/restore moderation endpoints."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from bson import ObjectId
from httpx import AsyncClient, ASGITransport

FAKE_CLUSTER_ID = str(ObjectId())


@pytest.fixture
def mock_db():
    db = MagicMock()
    db.clusters = MagicMock()
    db.clusters.update_one = AsyncMock()
    return db


@pytest.fixture
def patched_app(mock_db):
    with patch("app.routes.clusters.get_db", return_value=mock_db):
        with patch("app.database.connect_db", new_callable=AsyncMock):
            with patch("app.database.close_db", new_callable=AsyncMock):
                from app.main import app
                yield app, mock_db


@pytest.mark.asyncio
async def test_hide_cluster_success(patched_app):
    app, mock_db = patched_app
    mock_db.clusters.update_one.return_value = MagicMock(matched_count=1)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        resp = await c.patch(f"/api/clusters/{FAKE_CLUSTER_ID}/hide")
    assert resp.status_code == 200
    data = resp.json()
    assert data["cluster_id"] == FAKE_CLUSTER_ID
    assert data["status"] == "hidden"
    args = mock_db.clusters.update_one.call_args[0]
    assert args[0]["_id"] == ObjectId(FAKE_CLUSTER_ID)
    assert args[1]["$set"]["status"] == "hidden"


@pytest.mark.asyncio
async def test_hide_cluster_not_found(patched_app):
    app, mock_db = patched_app
    mock_db.clusters.update_one.return_value = MagicMock(matched_count=0)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        resp = await c.patch(f"/api/clusters/{str(ObjectId())}/hide")
    assert resp.status_code == 404
    assert "not found" in resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_restore_cluster_success(patched_app):
    app, mock_db = patched_app
    mock_db.clusters.update_one.return_value = MagicMock(matched_count=1)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        resp = await c.patch(f"/api/clusters/{FAKE_CLUSTER_ID}/restore")
    assert resp.status_code == 200
    data = resp.json()
    assert data["cluster_id"] == FAKE_CLUSTER_ID
    assert data["status"] == "pending"
    args = mock_db.clusters.update_one.call_args[0]
    assert args[0]["_id"] == ObjectId(FAKE_CLUSTER_ID)
    assert args[1]["$set"]["status"] == "pending"


@pytest.mark.asyncio
async def test_restore_cluster_not_found(patched_app):
    app, mock_db = patched_app
    mock_db.clusters.update_one.return_value = MagicMock(matched_count=0)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        resp = await c.patch(f"/api/clusters/{str(ObjectId())}/restore")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_hide_then_restore_roundtrip(patched_app):
    app, mock_db = patched_app
    mock_db.clusters.update_one.return_value = MagicMock(matched_count=1)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        r1 = await c.patch(f"/api/clusters/{FAKE_CLUSTER_ID}/hide")
        assert r1.json()["status"] == "hidden"
        r2 = await c.patch(f"/api/clusters/{FAKE_CLUSTER_ID}/restore")
        assert r2.json()["status"] == "pending"
    assert mock_db.clusters.update_one.await_count == 2
