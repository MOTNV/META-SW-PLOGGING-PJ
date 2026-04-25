from __future__ import annotations

import json
import os
from pathlib import Path


ROOT = Path(__file__).resolve().parent
OSM_FEATURES_PATH = ROOT / "unity" / "MetaSW" / "Assets" / "Data" / "osm_features.json"
TILE_PLAN_PATH = ROOT / "unity" / "MetaSW" / "Assets" / "Data" / "osm_tile_plan.json"
ZONE_PATH = ROOT / "simulation" / "simple_zones.json"
MOVEMENT_RULES_PATH = ROOT / "simulation" / "movement_rules.json"
MAP_IMAGE_PATH = ROOT / "unity" / "MetaSW" / "Assets" / "Sprites" / "gunsan_campus_map.png"
OUTPUT_HTML = ROOT / "simulation" / "movement_rules_map.html"


def load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def compact_trash_records(zone_payload: dict) -> list[dict]:
    records = []
    for record in zone_payload.get("trashRecords", []):
        records.append(
            {
                "recordIndex": record.get("recordIndex"),
                "zoneId": record.get("zoneId"),
                "latitude": record.get("latitude"),
                "longitude": record.get("longitude"),
                "items": record.get("items", []),
            }
        )
    return records


def enabled_areas(items: list[dict]) -> list[dict]:
    return [item for item in items if item.get("enabled") is not False and len(item.get("points", [])) >= 3]


def build_html() -> str:
    features = load_json(OSM_FEATURES_PATH)
    tile_plan = load_json(TILE_PLAN_PATH)
    zones = load_json(ZONE_PATH)
    movement_rules = load_json(MOVEMENT_RULES_PATH)

    bounds = tile_plan["coveredBounds"]
    payload = {
        "bounds": {
            "minLatitude": bounds["south"],
            "maxLatitude": bounds["north"],
            "minLongitude": bounds["west"],
            "maxLongitude": bounds["east"],
        },
        "imagePath": Path(os.path.relpath(MAP_IMAGE_PATH, OUTPUT_HTML.parent)).as_posix(),
        "walkableWays": features.get("walkableWays", []),
        "buildings": features.get("buildings", []),
        "blockedAreas": features.get("blockedAreas", []),
        "allowedAreas": features.get("allowedAreas", []),
        "trashRecords": compact_trash_records(zones),
        "movementRules": {
            "manualBlockedAreas": enabled_areas(movement_rules.get("manualBlockedAreas", [])),
            "manualPickupOnlyAreas": enabled_areas(movement_rules.get("manualPickupOnlyAreas", [])),
            "manualAllowedAreas": enabled_areas(movement_rules.get("manualAllowedAreas", [])),
            "manualExcludedTrashAreas": enabled_areas(movement_rules.get("manualExcludedTrashAreas", [])),
            "pickupAccessRadiusMeters": movement_rules.get("pickupAccessRadiusMeters", 15.0),
        },
    }

    payload_json = json.dumps(payload, ensure_ascii=False)
    return f"""<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Movement Rules Map</title>
  <style>
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: "Segoe UI", "Malgun Gothic", Arial, sans-serif;
      background: #f4f6f1;
      color: #1e251d;
    }}
    .app {{
      display: grid;
      grid-template-columns: 360px minmax(0, 1fr);
      min-height: 100vh;
    }}
    aside {{
      padding: 18px;
      border-right: 1px solid #cfd7c8;
      background: #fbfcf8;
      overflow: auto;
    }}
    h1 {{
      margin: 0 0 14px;
      font-size: 22px;
      letter-spacing: 0;
    }}
    h2 {{
      margin: 18px 0 8px;
      font-size: 15px;
    }}
    .row {{
      display: flex;
      gap: 8px;
      flex-wrap: wrap;
      margin: 8px 0;
    }}
    button, select {{
      border: 1px solid #aebca5;
      background: #fff;
      color: #1e251d;
      border-radius: 6px;
      padding: 8px 10px;
      font: inherit;
      cursor: pointer;
    }}
    button.primary {{
      background: #355f2e;
      color: #fff;
      border-color: #355f2e;
    }}
    label {{
      display: block;
      margin: 7px 0;
      font-size: 13px;
    }}
    input[type="checkbox"] {{
      vertical-align: middle;
      margin-right: 6px;
    }}
    textarea {{
      width: 100%;
      min-height: 190px;
      resize: vertical;
      border: 1px solid #cfd7c8;
      border-radius: 6px;
      padding: 10px;
      font: 12px Consolas, monospace;
      background: #fff;
    }}
    .hint, .stat {{
      font-size: 13px;
      line-height: 1.45;
      color: #4b5547;
    }}
    .stage {{
      position: relative;
      overflow: auto;
      background: #d9dfd2;
    }}
    canvas {{
      display: block;
      background: #e5e8df;
      cursor: crosshair;
    }}
    .coord {{
      position: fixed;
      right: 14px;
      bottom: 14px;
      padding: 8px 10px;
      background: rgba(255,255,255,0.92);
      border: 1px solid #cfd7c8;
      border-radius: 6px;
      font: 12px Consolas, monospace;
    }}
  </style>
</head>
<body>
  <div class="app">
    <aside>
      <h1>Movement Rules Map</h1>
      <p class="hint">지도 위를 클릭해서 수동 영역 polygon 좌표를 만듭니다. 만든 JSON 조각을 <code>simulation/movement_rules.json</code>의 해당 배열에 붙여 넣으면 됩니다.</p>

      <h2>표시 레이어</h2>
      <label><input type="checkbox" id="showWalkable" checked>길(walkableWays)</label>
      <label><input type="checkbox" id="showBuildings" checked>건물</label>
      <label><input type="checkbox" id="showBlocked" checked>OSM blocked area</label>
      <label><input type="checkbox" id="showTrash" checked>쓰레기 위치</label>
      <label><input type="checkbox" id="showRules" checked>현재 수동 규칙</label>
      <p class="hint">수동 규칙 색상: 빨강=아예 못 가는 곳, 노랑=잠깐 접근만 가능한 곳, 초록=자유 이동 허용, 보라=수거 제외</p>

      <h2>새 영역 만들기</h2>
      <select id="areaType">
        <option value="manualBlockedAreas">못 가는 곳</option>
        <option value="manualPickupOnlyAreas">잠깐 접근만 가능</option>
        <option value="manualAllowedAreas">갈 수 있는 곳</option>
        <option value="manualExcludedTrashAreas">수거 제외 구역</option>
      </select>
      <div class="row">
        <button id="undo">마지막 점 삭제</button>
        <button id="clear">초기화</button>
      </div>
      <div class="row">
        <button class="primary" id="makeJson">JSON 만들기</button>
      </div>
      <p class="stat" id="pointCount">선택한 점: 0</p>
      <textarea id="output" spellcheck="false" placeholder="여기에 복사할 JSON이 표시됩니다."></textarea>

      <h2>사용 순서</h2>
      <p class="hint">1. 지도 확대/축소는 브라우저 확대 기능을 사용합니다.<br>2. 영역 꼭짓점을 순서대로 클릭합니다.<br>3. JSON 만들기를 누릅니다.<br>4. 결과를 movement_rules.json의 맞는 배열에 붙입니다.<br>5. enabled를 true로 둔 뒤 시뮬레이션을 다시 실행합니다.</p>
    </aside>
    <main class="stage">
      <canvas id="mapCanvas"></canvas>
    </main>
  </div>
  <div class="coord" id="coord">lat -, lon -</div>

  <script>
    const data = {payload_json};
    const canvas = document.getElementById('mapCanvas');
    const ctx = canvas.getContext('2d');
    const image = new Image();
    const selected = [];
    const coord = document.getElementById('coord');
    const pointCount = document.getElementById('pointCount');
    const output = document.getElementById('output');
    const layerIds = ['showWalkable', 'showBuildings', 'showBlocked', 'showTrash', 'showRules'];

    function lonToX(lon) {{
      const b = data.bounds;
      return ((lon - b.minLongitude) / (b.maxLongitude - b.minLongitude)) * canvas.width;
    }}

    function latToY(lat) {{
      const b = data.bounds;
      return ((b.maxLatitude - lat) / (b.maxLatitude - b.minLatitude)) * canvas.height;
    }}

    function xToLon(x) {{
      const b = data.bounds;
      return b.minLongitude + (x / canvas.width) * (b.maxLongitude - b.minLongitude);
    }}

    function yToLat(y) {{
      const b = data.bounds;
      return b.maxLatitude - (y / canvas.height) * (b.maxLatitude - b.minLatitude);
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

    function drawTrash(records) {{
      ctx.fillStyle = 'rgba(238, 88, 35, 0.68)';
      for (const r of records) {{
        const x = lonToX(Number(r.longitude));
        const y = latToY(Number(r.latitude));
        ctx.beginPath();
        ctx.arc(x, y, 2.2, 0, Math.PI * 2);
        ctx.fill();
      }}
    }}

    function drawSelected() {{
      if (!selected.length) return;
      ctx.fillStyle = '#111';
      for (const p of selected) {{
        ctx.beginPath();
        ctx.arc(lonToX(p.longitude), latToY(p.latitude), 4, 0, Math.PI * 2);
        ctx.fill();
      }}
      drawPolyline(selected, '#111', 2);
      if (selected.length >= 3) drawPolygon(selected, '#111', 'rgba(255,255,255,0.18)', 2);
    }}

    function redraw() {{
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      ctx.drawImage(image, 0, 0, canvas.width, canvas.height);

      if (document.getElementById('showWalkable').checked) {{
        for (const way of data.walkableWays) drawPolyline(way.points, 'rgba(25, 118, 210, 0.75)', 1.5);
      }}
      if (document.getElementById('showBuildings').checked) {{
        for (const area of data.buildings) drawPolygon(area.points, 'rgba(120, 57, 35, 0.75)', 'rgba(120, 57, 35, 0.18)');
      }}
      if (document.getElementById('showBlocked').checked) {{
        for (const area of data.blockedAreas) drawPolygon(area.points, 'rgba(194, 24, 91, 0.75)', 'rgba(194, 24, 91, 0.14)');
      }}
      if (document.getElementById('showTrash').checked) drawTrash(data.trashRecords);
      if (document.getElementById('showRules').checked) {{
        for (const area of data.movementRules.manualBlockedAreas) drawPolygon(area.points, '#d32f2f', 'rgba(211, 47, 47, 0.26)', 3);
        for (const area of data.movementRules.manualPickupOnlyAreas) drawPolygon(area.points, '#f9a825', 'rgba(249, 168, 37, 0.32)', 3);
        for (const area of data.movementRules.manualAllowedAreas) drawPolygon(area.points, '#2e7d32', 'rgba(46, 125, 50, 0.26)', 3);
        for (const area of data.movementRules.manualExcludedTrashAreas) drawPolygon(area.points, '#6a1b9a', 'rgba(106, 27, 154, 0.24)', 3);
      }}
      drawSelected();
    }}

    function updatePointCount() {{
      pointCount.textContent = `선택한 점: ${{selected.length}}`;
    }}

    image.onload = () => {{
      canvas.width = image.naturalWidth;
      canvas.height = image.naturalHeight;
      redraw();
    }};
    image.src = data.imagePath;

    for (const id of layerIds) {{
      document.getElementById(id).addEventListener('change', redraw);
    }}

    canvas.addEventListener('mousemove', (event) => {{
      const rect = canvas.getBoundingClientRect();
      const x = (event.clientX - rect.left) * (canvas.width / rect.width);
      const y = (event.clientY - rect.top) * (canvas.height / rect.height);
      coord.textContent = `lat ${{yToLat(y).toFixed(8)}}, lon ${{xToLon(x).toFixed(8)}}`;
    }});

    canvas.addEventListener('click', (event) => {{
      const rect = canvas.getBoundingClientRect();
      const x = (event.clientX - rect.left) * (canvas.width / rect.width);
      const y = (event.clientY - rect.top) * (canvas.height / rect.height);
      selected.push({{ latitude: Number(yToLat(y).toFixed(8)), longitude: Number(xToLon(x).toFixed(8)) }});
      updatePointCount();
      redraw();
    }});

    document.getElementById('undo').addEventListener('click', () => {{
      selected.pop();
      updatePointCount();
      redraw();
    }});

    document.getElementById('clear').addEventListener('click', () => {{
      selected.length = 0;
      output.value = '';
      updatePointCount();
      redraw();
    }});

    document.getElementById('makeJson').addEventListener('click', () => {{
      const type = document.getElementById('areaType').value;
      const item = {{
        id: `${{type}}_${{new Date().toISOString().replace(/[-:.TZ]/g, '').slice(0, 14)}}`,
        name: '',
        enabled: true,
        points: selected
      }};
      output.value = JSON.stringify(item, null, 2);
      output.focus();
      output.select();
    }});
  </script>
</body>
</html>
"""


def main() -> None:
    OUTPUT_HTML.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_HTML.write_text(build_html(), encoding="utf-8")
    print(f"saved {OUTPUT_HTML}")


if __name__ == "__main__":
    main()
