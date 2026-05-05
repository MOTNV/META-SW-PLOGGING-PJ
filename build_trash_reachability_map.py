from __future__ import annotations

import json
from pathlib import Path

from movement_rules import DEFAULT_MOVEMENT_RULES_PATH, MovementRules
from simulate_greedy_plogging import (
    attach_trash_to_walkable_graph,
    build_trash_states,
    calculate_trash_metrics,
    load_json,
    trash_pickup_latitude,
    trash_pickup_longitude,
)
from walkable_route_graph import DEFAULT_OSM_FEATURES_PATH, WalkableRouteGraph


ROOT = Path(__file__).resolve().parent
OUTPUT_PATH = ROOT / "simulation" / "trash_reachability_map.html"
ZONE_PATH = ROOT / "simulation" / "simple_zones.json"
RUN_DIR = ROOT / "simulation" / "comparison_until_done" / "runs"
OSM_FEATURES_PATH = ROOT / "unity" / "MetaSW" / "Assets" / "Data" / "osm_features.json"
OSM_TILE_PLAN_PATH = ROOT / "unity" / "MetaSW" / "Assets" / "Data" / "osm_tile_plan.json"
MOVEMENT_RULES_PATH = ROOT / "simulation" / "movement_rules.json"


def build_payload() -> dict:
    zone_payload = load_json(ZONE_PATH)
    osm_payload = load_json(OSM_FEATURES_PATH)
    tile_plan = load_json(OSM_TILE_PLAN_PATH)
    movement_rules = MovementRules.load(MOVEMENT_RULES_PATH)
    route_graph = WalkableRouteGraph.from_osm_features(DEFAULT_OSM_FEATURES_PATH, movement_rules=movement_rules)

    trash_states = build_trash_states(zone_payload)
    attach_trash_to_walkable_graph(trash_states, route_graph, blocked_pickup_access_radius_meters=80.0)
    state_by_index = {trash.trash_index: trash for trash in trash_states}

    records = []
    for record in zone_payload["trashRecords"]:
        index = int(record["recordIndex"])
        trash = state_by_index.get(index)
        trash_count, trash_mass = calculate_trash_metrics(record.get("items") or [])
        if trash is None:
            continue
        records.append(
            {
                "recordIndex": index,
                "zoneId": record.get("zoneId", ""),
                "latitude": float(record["latitude"]),
                "longitude": float(record["longitude"]),
                "trashCount": trash_count,
                "trashMass": trash_mass,
                "reachable": bool(trash.reachable),
                "unreachableReason": trash.unreachable_reason,
                "pickupMode": trash.pickup_mode,
                "pickupLatitude": trash_pickup_latitude(trash),
                "pickupLongitude": trash_pickup_longitude(trash),
                "pickupAccessDistanceMeters": trash.pickup_access_distance_m,
            }
        )

    strategies = {}
    for strategy in ("random", "trash_priority", "uniform"):
        run_path = RUN_DIR / f"greedy_{strategy}_run_000_result.json"
        replay = load_json(run_path)
        history = replay.get("history", [])
        final_step = history[-1] if history else {}
        collected = set(int(value) for value in final_step.get("collectedTrashIndices", []))
        active = set(record["recordIndex"] for record in records if record["reachable"])
        excluded = set(record["recordIndex"] for record in records if not record["reachable"])
        remaining = sorted(active - collected)
        strategies[strategy] = {
            "metadata": replay.get("metadata", {}),
            "summary": replay.get("summary", {}),
            "collectedTrashIndices": sorted(collected),
            "remainingTrashIndices": remaining,
            "excludedTrashIndices": sorted(excluded),
        }

    return {
        "bounds": {
            "minLatitude": float(tile_plan["coveredBounds"]["south"]),
            "maxLatitude": float(tile_plan["coveredBounds"]["north"]),
            "minLongitude": float(tile_plan["coveredBounds"]["west"]),
            "maxLongitude": float(tile_plan["coveredBounds"]["east"]),
        },
        "imagePath": "../unity/MetaSW/Assets/Sprites/gunsan_campus_map.png",
        "campusBoundary": osm_payload.get("campusBoundary"),
        "walkableWays": osm_payload.get("walkableWays", []),
        "buildings": osm_payload.get("buildings", []),
        "blockedAreas": osm_payload.get("blockedAreas", []),
        "allowedAreas": osm_payload.get("allowedAreas", []),
        "movementRules": load_json(MOVEMENT_RULES_PATH),
        "trashRecords": records,
        "strategies": strategies,
    }


def write_html(payload: dict) -> None:
    data_json = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    html = f"""<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Trash Reachability Map</title>
  <style>
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: "Segoe UI", "Malgun Gothic", Arial, sans-serif;
      background: #eef1e8;
      color: #182018;
    }}
    .app {{
      display: grid;
      grid-template-columns: 340px minmax(0, 1fr);
      height: 100vh;
    }}
    aside {{
      padding: 18px;
      overflow: auto;
      border-right: 1px solid #c8d0c0;
      background: #fbfcf7;
    }}
    h1 {{ margin: 0 0 12px; font-size: 22px; letter-spacing: 0; }}
    h2 {{ margin: 18px 0 8px; font-size: 15px; }}
    label {{ display: block; margin: 8px 0; font-size: 13px; }}
    select, button {{
      width: 100%;
      border: 1px solid #aeb9a6;
      border-radius: 6px;
      padding: 8px 10px;
      background: #fff;
      color: #182018;
      font: inherit;
    }}
    button {{ cursor: pointer; margin-top: 8px; }}
    .stage {{ position: relative; overflow: auto; background: #d8ded0; }}
    canvas {{ display: block; background: #e3e7dc; }}
    .stat {{
      display: grid;
      grid-template-columns: 1fr auto;
      gap: 6px 10px;
      padding: 10px;
      border: 1px solid #d5dccf;
      border-radius: 6px;
      background: #fff;
      font-size: 13px;
    }}
    .legend {{ display: grid; gap: 7px; margin-top: 10px; font-size: 13px; }}
    .legend div {{ display: flex; align-items: center; gap: 8px; }}
    .swatch {{ width: 13px; height: 13px; border-radius: 50%; border: 2px solid #fff; box-shadow: 0 0 0 1px rgba(0,0,0,.25); }}
    .green {{ background: #2e7d32; }}
    .red {{ background: #d32f2f; }}
    .gray {{ background: #6d7278; }}
    .purple {{ background: #7b1fa2; }}
    .blue {{ background: #1976d2; }}
    .hint, .detail {{
      color: #4e594a;
      font-size: 13px;
      line-height: 1.45;
    }}
    .detail {{
      min-height: 140px;
      padding: 10px;
      border: 1px solid #d5dccf;
      border-radius: 6px;
      background: #fff;
      white-space: pre-wrap;
      font-family: Consolas, "Malgun Gothic", monospace;
    }}
    .coord {{
      position: fixed;
      right: 14px;
      bottom: 14px;
      padding: 8px 10px;
      background: rgba(255,255,255,0.94);
      border: 1px solid #c8d0c0;
      border-radius: 6px;
      font: 12px Consolas, monospace;
      pointer-events: none;
    }}
  </style>
</head>
<body>
  <div class="app">
    <aside>
      <h1>Trash Reachability Map</h1>
      <p class="hint">시뮬레이션 종료 시점에서 수거 완료, 남은 쓰레기, 제외 쓰레기, 건물 내부 외부수거 처리 대상을 지도 위에 표시합니다. 파란 네모와 점선은 실제 이동 경로가 아니라 외부 수거 보조 표시입니다.</p>

      <h2>전략</h2>
      <select id="strategy">
        <option value="trash_priority">trash_priority</option>
        <option value="uniform">uniform</option>
        <option value="random">random</option>
      </select>

      <h2>통계</h2>
      <div class="stat" id="stats"></div>

      <h2>레이어</h2>
      <label><input type="checkbox" id="showWalkable" checked> 도로/보행 그래프</label>
      <label><input type="checkbox" id="showBuildings" checked> 건물</label>
      <label><input type="checkbox" id="showBlocked" checked> 못 가는 구역</label>
      <label><input type="checkbox" id="showCollected"> 수거 완료 쓰레기</label>
      <label><input type="checkbox" id="showRemaining" checked> 끝까지 남은 쓰레기</label>
      <label><input type="checkbox" id="showExcluded" checked> 제외 쓰레기</label>
      <label><input type="checkbox" id="showProxy" checked> 건물 내부 외부수거 지점</label>
      <label><input type="checkbox" id="showPickupLines"> 외부수거 보조선</label>
      <button id="fit">전체 보기</button>

      <div class="legend">
        <div><span class="swatch red"></span>끝까지 남은 쓰레기</div>
        <div><span class="swatch green"></span>수거 완료</div>
        <div><span class="swatch gray"></span>제외</div>
        <div><span class="swatch purple"></span>건물 내부, 외부에서 수거</div>
        <div><span class="swatch blue"></span>외부 수거 지점</div>
      </div>

      <h2>선택 정보</h2>
      <div class="detail" id="detail">점을 클릭하면 recordIndex, zone, 수거 상태가 표시됩니다.</div>
    </aside>
    <main class="stage" id="stage">
      <canvas id="mapCanvas"></canvas>
    </main>
  </div>
  <div class="coord" id="coord">lat -, lon -</div>

  <script>
    const data = {data_json};
    const canvas = document.getElementById('mapCanvas');
    const ctx = canvas.getContext('2d');
    const image = new Image();
    const stage = document.getElementById('stage');
    const coord = document.getElementById('coord');
    const detail = document.getElementById('detail');
    const strategySelect = document.getElementById('strategy');
    const layerIds = ['showWalkable','showBuildings','showBlocked','showCollected','showRemaining','showExcluded','showProxy','showPickupLines'];
    let markerHitboxes = [];

    function mercatorY(lat) {{
      const rad = lat * Math.PI / 180;
      return Math.log(Math.tan(Math.PI / 4 + rad / 2));
    }}
    function inverseMercatorY(value) {{
      return (2 * Math.atan(Math.exp(value)) - Math.PI / 2) * 180 / Math.PI;
    }}
    function lonToX(lon) {{
      const b = data.bounds;
      return ((lon - b.minLongitude) / (b.maxLongitude - b.minLongitude)) * canvas.width;
    }}
    function latToY(lat) {{
      const b = data.bounds;
      const north = mercatorY(b.maxLatitude);
      const south = mercatorY(b.minLatitude);
      return ((north - mercatorY(lat)) / (north - south)) * canvas.height;
    }}
    function xToLon(x) {{
      const b = data.bounds;
      return b.minLongitude + (x / canvas.width) * (b.maxLongitude - b.minLongitude);
    }}
    function yToLat(y) {{
      const b = data.bounds;
      const north = mercatorY(b.maxLatitude);
      const south = mercatorY(b.minLatitude);
      return inverseMercatorY(north - (y / canvas.height) * (north - south));
    }}
    function currentStrategy() {{ return data.strategies[strategySelect.value]; }}
    function indexSet(values) {{ return new Set(values || []); }}
    function isProxy(record) {{ return record.pickupMode === 'blocked_area_nearest_walkable'; }}
    function recordStatus(record, strategy) {{
      if (indexSet(strategy.excludedTrashIndices).has(record.recordIndex)) return 'excluded';
      if (indexSet(strategy.remainingTrashIndices).has(record.recordIndex)) return 'remaining';
      if (indexSet(strategy.collectedTrashIndices).has(record.recordIndex)) return 'collected';
      return record.reachable ? 'active' : 'excluded';
    }}
    function drawPolyline(points, color, width) {{
      if (!points || points.length < 2) return;
      ctx.beginPath();
      points.forEach((p, i) => {{
        const x = lonToX(Number(p.longitude));
        const y = latToY(Number(p.latitude));
        if (i === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
      }});
      ctx.strokeStyle = color;
      ctx.lineWidth = width;
      ctx.stroke();
    }}
    function drawPolygon(points, stroke, fill, width = 1.5) {{
      if (!points || points.length < 3) return;
      ctx.beginPath();
      points.forEach((p, i) => {{
        const x = lonToX(Number(p.longitude));
        const y = latToY(Number(p.latitude));
        if (i === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
      }});
      ctx.closePath();
      ctx.fillStyle = fill;
      ctx.strokeStyle = stroke;
      ctx.lineWidth = width;
      ctx.fill();
      ctx.stroke();
    }}
    function drawMarker(record, fill, stroke, radius, status) {{
      const x = lonToX(record.longitude);
      const y = latToY(record.latitude);
      ctx.beginPath();
      ctx.arc(x, y, radius, 0, Math.PI * 2);
      ctx.fillStyle = fill;
      ctx.strokeStyle = stroke;
      ctx.lineWidth = 2;
      ctx.fill();
      ctx.stroke();
      markerHitboxes.push({{ x, y, radius: Math.max(radius + 4, 8), record, status }});
    }}
    function drawPickupPoint(record) {{
      const x = lonToX(record.pickupLongitude);
      const y = latToY(record.pickupLatitude);
      if (document.getElementById('showPickupLines').checked) {{
        ctx.beginPath();
        ctx.moveTo(lonToX(record.longitude), latToY(record.latitude));
        ctx.lineTo(x, y);
        ctx.setLineDash([5, 5]);
        ctx.strokeStyle = 'rgba(25, 118, 210, 0.5)';
        ctx.lineWidth = 1.2;
        ctx.stroke();
        ctx.setLineDash([]);
      }}
      ctx.beginPath();
      ctx.rect(x - 4, y - 4, 8, 8);
      ctx.fillStyle = '#1976d2';
      ctx.strokeStyle = '#ffffff';
      ctx.lineWidth = 1.5;
      ctx.fill();
      ctx.stroke();
    }}
    function drawStats() {{
      const strategy = currentStrategy();
      const summary = strategy.summary || {{}};
      const metadata = strategy.metadata || {{}};
      const proxyRemaining = data.trashRecords.filter(r => isProxy(r) && indexSet(strategy.remainingTrashIndices).has(r.recordIndex)).length;
      document.getElementById('stats').innerHTML = `
        <span>수거율</span><b>${{((summary.collectionRate || 0) * 100).toFixed(1)}}%</b>
        <span>남은 질량</span><b>${{summary.remainingTrashMass ?? '-'}}</b>
        <span>활성 쓰레기</span><b>${{metadata.reachableTrashRecordCount ?? '-'}}</b>
        <span>제외</span><b>${{metadata.unreachableTrashRecordCount ?? '-'}}</b>
        <span>외부수거 처리</span><b>${{metadata.blockedPickupProxyTrashRecordCount ?? '-'}}</b>
        <span>외부수거 중 남음</span><b>${{proxyRemaining}}</b>
      `;
    }}
    function redraw() {{
      markerHitboxes = [];
      const strategy = currentStrategy();
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      ctx.drawImage(image, 0, 0, canvas.width, canvas.height);
      if (document.getElementById('showWalkable').checked) {{
        for (const way of data.walkableWays) drawPolyline(way.points, 'rgba(245, 159, 0, 0.82)', 2.2);
      }}
      if (document.getElementById('showBuildings').checked) {{
        for (const area of data.buildings) drawPolygon(area.points, 'rgba(113, 64, 43, 0.85)', 'rgba(113, 64, 43, 0.2)', 1.4);
      }}
      if (document.getElementById('showBlocked').checked) {{
        for (const area of data.blockedAreas) drawPolygon(area.points, 'rgba(211, 47, 47, 0.75)', 'rgba(211, 47, 47, 0.18)', 2);
        for (const area of data.movementRules.manualBlockedAreas || []) drawPolygon(area.points, 'rgba(183, 28, 28, 0.95)', 'rgba(183, 28, 28, 0.24)', 2.6);
      }}

      for (const record of data.trashRecords) {{
        const status = recordStatus(record, strategy);
        const proxy = isProxy(record);
        if (proxy && document.getElementById('showProxy').checked) drawPickupPoint(record);
        if (status === 'collected' && document.getElementById('showCollected').checked) drawMarker(record, '#2e7d32', '#fff', 3.5, status);
        if (status === 'remaining' && document.getElementById('showRemaining').checked) drawMarker(record, proxy ? '#7b1fa2' : '#d32f2f', '#fff', proxy ? 6 : 5, status);
        if (status === 'excluded' && document.getElementById('showExcluded').checked) drawMarker(record, '#6d7278', '#fff', 4.5, status);
        if (proxy && status !== 'remaining' && document.getElementById('showProxy').checked) drawMarker(record, '#7b1fa2', '#fff', 4, status);
      }}
      drawStats();
    }}
    function pickMarker(x, y) {{
      for (let i = markerHitboxes.length - 1; i >= 0; i--) {{
        const h = markerHitboxes[i];
        const dx = x - h.x;
        const dy = y - h.y;
        if (Math.sqrt(dx * dx + dy * dy) <= h.radius) return h;
      }}
      return null;
    }}
    function showDetail(hit) {{
      if (!hit) {{
        detail.textContent = '점을 클릭하면 recordIndex, zone, 수거 상태가 표시됩니다.';
        return;
      }}
      const r = hit.record;
      detail.textContent =
        `recordIndex: ${{r.recordIndex}}\\n` +
        `zoneId: ${{r.zoneId}}\\n` +
        `status: ${{hit.status}}\\n` +
        `trashCount: ${{r.trashCount}}\\n` +
        `trashMass: ${{r.trashMass}}\\n` +
        `pickupMode: ${{r.pickupMode}}\\n` +
        `pickupAccessDistanceMeters: ${{Number(r.pickupAccessDistanceMeters).toFixed(2)}}\\n` +
        `lat/lon: ${{r.latitude.toFixed(8)}}, ${{r.longitude.toFixed(8)}}\\n` +
        `pickup: ${{Number(r.pickupLatitude).toFixed(8)}}, ${{Number(r.pickupLongitude).toFixed(8)}}`;
    }}
    image.onload = () => {{
      canvas.width = image.naturalWidth;
      canvas.height = image.naturalHeight;
      redraw();
      stage.scrollLeft = Math.max(0, (canvas.width - stage.clientWidth) / 2);
      stage.scrollTop = Math.max(0, (canvas.height - stage.clientHeight) / 2);
    }};
    image.src = data.imagePath;
    for (const id of layerIds) document.getElementById(id).addEventListener('change', redraw);
    strategySelect.addEventListener('change', redraw);
    document.getElementById('fit').addEventListener('click', () => {{
      stage.scrollLeft = Math.max(0, (canvas.width - stage.clientWidth) / 2);
      stage.scrollTop = Math.max(0, (canvas.height - stage.clientHeight) / 2);
    }});
    canvas.addEventListener('mousemove', event => {{
      const rect = canvas.getBoundingClientRect();
      const x = (event.clientX - rect.left) * (canvas.width / rect.width);
      const y = (event.clientY - rect.top) * (canvas.height / rect.height);
      coord.textContent = `lat ${{yToLat(y).toFixed(8)}}, lon ${{xToLon(x).toFixed(8)}}`;
    }});
    canvas.addEventListener('click', event => {{
      const rect = canvas.getBoundingClientRect();
      const x = (event.clientX - rect.left) * (canvas.width / rect.width);
      const y = (event.clientY - rect.top) * (canvas.height / rect.height);
      showDetail(pickMarker(x, y));
    }});
  </script>
</body>
</html>
"""
    OUTPUT_PATH.write_text(html, encoding="utf-8")


def main() -> None:
    payload = build_payload()
    write_html(payload)
    print(f"wrote {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
