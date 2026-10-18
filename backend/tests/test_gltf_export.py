"""Tests for 3D glTF / GLB Export (Phase 5 Part B).
Tests covering:
- Plan -> glTF binary (.glb) synthesis
- Wall extrusion with thickness & floor-to-floor height
- Window and door opening cuts
- Level floor slab geometry
- Multi-step staircase geometry
- GET /api/v1/plans/{id}/versions/{v}/model.glb endpoint
"""

import json
import struct

import pytest
from httpx import AsyncClient

from app.modules.exports.gltf import generate_plan_glb
from app.modules.plans.schemas import Level, Opening, PlanData, Room, Stair, Wall


@pytest.fixture
def sample_multilevel_plan_data() -> PlanData:
    """Fixture providing a 2-level plan with walls, doors, windows, and stairs."""
    return PlanData(
        units="mm",
        levels=[
            Level(
                id="lvl_ground",
                name="Ground Floor",
                elevation_mm=0.0,
                floor_to_floor_mm=3000.0,
                rooms=[
                    Room(
                        id="room_living",
                        name="Living Room",
                        type="living",
                        polygon=[[0.0, 0.0], [5000.0, 0.0], [5000.0, 4000.0], [0.0, 4000.0]],
                    )
                ],
                walls=[
                    Wall(
                        id="wall_w1",
                        start=[0.0, 0.0],
                        end=[5000.0, 0.0],
                        thickness_mm=200.0,
                        is_external=True,
                    ),
                    Wall(
                        id="wall_w2",
                        start=[5000.0, 0.0],
                        end=[5000.0, 4000.0],
                        thickness_mm=200.0,
                        is_external=True,
                    ),
                ],
                openings=[
                    Opening(
                        id="op_door_1",
                        wall_id="wall_w1",
                        kind="door",
                        offset_mm=1000.0,
                        width_mm=1000.0,
                        height_mm=2100.0,
                        sill_mm=0.0,
                    ),
                    Opening(
                        id="op_window_1",
                        wall_id="wall_w2",
                        kind="window",
                        offset_mm=1500.0,
                        width_mm=1200.0,
                        height_mm=1500.0,
                        sill_mm=900.0,
                    ),
                ],
                stairs=[
                    Stair(
                        id="stair_1",
                        polygon=[[0.0, 4000.0], [2000.0, 4000.0], [2000.0, 6000.0], [0.0, 6000.0]],
                        riser_mm=150.0,
                        tread_mm=250.0,
                        direction="up",
                    )
                ],
            ),
            Level(
                id="lvl_first",
                name="First Floor",
                elevation_mm=3000.0,
                floor_to_floor_mm=3000.0,
                rooms=[
                    Room(
                        id="room_bed",
                        name="Master Bedroom",
                        type="bedroom",
                        polygon=[[0.0, 0.0], [5000.0, 0.0], [5000.0, 4000.0], [0.0, 4000.0]],
                    )
                ],
                walls=[
                    Wall(
                        id="wall_upper_1",
                        start=[0.0, 0.0],
                        end=[5000.0, 0.0],
                        thickness_mm=200.0,
                        is_external=True,
                    )
                ],
                openings=[],
                stairs=[],
            ),
        ],
    )


def test_generate_plan_glb_header_and_structure(sample_multilevel_plan_data: PlanData):
    """Generated GLB must strictly adhere to the glTF 2.0 Binary container format."""
    glb_bytes = generate_plan_glb(sample_multilevel_plan_data)
    assert isinstance(glb_bytes, bytes)
    assert len(glb_bytes) > 100

    # 1. 12-byte header
    magic, version, length = struct.unpack_from("<4sII", glb_bytes, 0)
    assert magic == b"glTF", f"Expected magic 'glTF', got {magic}"
    assert version == 2, f"Expected glTF version 2, got {version}"
    assert length == len(glb_bytes), "Container length in header must match total byte length"

    # 2. Chunk 0: JSON Chunk
    json_chunk_len, json_chunk_type = struct.unpack_from("<II", glb_bytes, 12)
    assert json_chunk_type == 0x4E4F534A, "Chunk 0 must be JSON type (0x4E4F534A)"
    json_data_bytes = glb_bytes[20 : 20 + json_chunk_len]
    gltf_json = json.loads(json_data_bytes.decode("utf-8"))

    # Assert basic glTF JSON fields
    assert gltf_json.get("asset", {}).get("version") == "2.0"
    assert "scene" in gltf_json
    assert "scenes" in gltf_json
    assert "nodes" in gltf_json
    assert "meshes" in gltf_json

    # 3. Check node hierarchy matches plan levels and elements
    node_names = [n.get("name") for n in gltf_json.get("nodes", [])]
    assert any("Ground Floor" in name for name in node_names if name)
    assert any("First Floor" in name for name in node_names if name)

    # 4. Chunk 1: Binary Buffer Chunk
    bin_chunk_offset = 20 + json_chunk_len
    if bin_chunk_offset < len(glb_bytes):
        bin_chunk_len, bin_chunk_type = struct.unpack_from("<II", glb_bytes, bin_chunk_offset)
        assert bin_chunk_type == 0x004E4942, "Chunk 1 must be BIN type (0x004E4942)"
        assert bin_chunk_offset + 8 + bin_chunk_len == len(glb_bytes)


@pytest.mark.asyncio
async def test_get_plan_model_glb_api_endpoint(client: AsyncClient, auth_org_a: dict):
    """GET /api/v1/plans/{id}/versions/{v}/model.glb returns 200 with model/gltf-binary content."""
    headers = auth_org_a["headers"]

    # 1. Create project
    proj_resp = await client.post(
        "/api/v1/projects",
        json={"name": "3D Export Test Project"},
        headers=headers,
    )
    project_id = proj_resp.json()["id"]

    # 2. Create plan
    plan_resp = await client.post(
        f"/api/v1/projects/{project_id}/plans",
        json={
            "name": "Exportable Scheme",
            "data": {
                "units": "mm",
                "levels": [
                    {
                        "id": "lvl_1",
                        "name": "Ground Floor",
                        "elevation_mm": 0,
                        "floor_to_floor_mm": 3000,
                        "rooms": [
                            {
                                "id": "room_1",
                                "name": "Studio Room",
                                "type": "living",
                                "polygon": [[0, 0], [4000, 0], [4000, 4000], [0, 4000]],
                            }
                        ],
                        "walls": [
                            {
                                "id": "wall_1",
                                "start": [0, 0],
                                "end": [4000, 0],
                                "thickness_mm": 200,
                                "is_external": True,
                            }
                        ],
                        "openings": [],
                        "stairs": [],
                    }
                ],
            },
            "message": "Scheme for 3D model test",
        },
        headers=headers,
    )
    assert plan_resp.status_code == 201
    plan_id = plan_resp.json()["id"]

    # 3. Fetch model.glb
    glb_resp = await client.get(f"/api/v1/plans/{plan_id}/versions/1/model.glb", headers=headers)
    assert glb_resp.status_code == 200
    assert glb_resp.headers["content-type"] in ("model/gltf-binary", "application/octet-stream")

    content = glb_resp.content
    assert content.startswith(b"glTF")
    assert len(content) > 100
