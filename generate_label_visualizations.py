from __future__ import annotations

import json
import math
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path


# 시각화 입력 설정
IMAGE_DIRS = [
    r"D:\4year\플로깅 라벨링\gdw_image",
    r"D:\4year\플로깅 라벨링\ocs_image",
    r"D:\4year\플로깅 라벨링\jsm_image",
    r"D:\4year\플로깅 라벨링\cgh_image",
    r"D:\4year\플로깅 라벨링\iwj_image"

]

JSON_PATHS = [
    r"D:\4year\플로깅 라벨링\gdw_json\output.json",
    r"D:\4year\플로깅 라벨링\ocs_json\0411.json",
    r"D:\4year\플로깅 라벨링\jsm_json\data.json",
    r"D:\4year\플로깅 라벨링\cgh_json\data.json",
    r"D:\4year\플로깅 라벨링\iwj_json\data.json"

]

# 선택 사항: 지역 경계를 GeoJSON Polygon/MultiPolygon으로 넣으면 지역별 통계를 생성합니다.
# 비워두면 자동 격자(grid) 기반 지역 통계를 생성합니다.
REGION_GEOJSON_PATH = ""

OUTPUT_DIR = Path(r"D:\4year\플로깅 라벨링\visualizations")

LABEL_COLORS = {
    "담배꽁초": "#d1495b",
    "종이류": "#edae49",
    "플라스틱류": "#00798c",
    "비닐류": "#3066be",
    "캔/금속류": "#6c757d",
    "유리류": "#53a548",
    "스티로폼": "#8f5db7",
    "일반쓰레기": "#7a4b2a",
    "대형/수거불가": "#111111",
    "미라벨": "#9aa0a6",
}

SIZE_WEIGHTS = {
    "small": 1,
    "medium": 2,
    "large": 3,
}


def load_json(path: Path):
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def resolve_image_path(image_path: str) -> str | None:
    raw = Path(image_path)
    candidates = []

    if raw.is_absolute():
        candidates.append(raw)
    else:
        rel = Path(*raw.parts)
        for base in IMAGE_DIRS:
            base_path = Path(base)
            candidates.append(base_path / rel)
            candidates.append(base_path / raw.name)

    seen = set()
    for candidate in candidates:
        normalized = str(candidate.resolve()) if candidate.exists() else str(candidate)
        if normalized in seen:
            continue
        seen.add(normalized)
        if candidate.exists():
            return str(candidate.resolve())
    return None


def record_key(record: dict) -> tuple[str, str, str, str]:
    return (
        str(record.get("imagePath", "")),
        str(record.get("timestamp", "")),
        str(record.get("latitude", "")),
        str(record.get("longitude", "")),
    )


def normalize_record(record: dict, source_name: str) -> dict:
    items = record.get("items")
    normalized_items = []
    if isinstance(items, list):
        for item in items:
            if not isinstance(item, dict):
                continue
            normalized_items.append(
                {
                    "label": item.get("label", "미라벨") or "미라벨",
                    "size": item.get("size", "small") or "small",
                    "quantity": int(item.get("quantity", 1) or 1),
                }
            )

    return {
        "imagePath": record.get("imagePath", ""),
        "latitude": record.get("latitude"),
        "longitude": record.get("longitude"),
        "timestamp": record.get("timestamp", ""),
        "items": normalized_items,
        "source": source_name,
        "resolvedImagePath": resolve_image_path(record.get("imagePath", "")),
    }


def merge_records(record_lists: list[list[dict]]) -> list[dict]:
    merged = {}
    order = []
    for records in record_lists:
        for record in records:
            key = record_key(record)
            if key not in merged:
                merged[key] = record
                order.append(key)
                continue
            existing = merged[key]
            if existing.get("latitude") in (None, "") and record.get("latitude") not in (None, ""):
                existing["latitude"] = record.get("latitude")
            if existing.get("longitude") in (None, "") and record.get("longitude") not in (None, ""):
                existing["longitude"] = record.get("longitude")
            if not existing.get("timestamp") and record.get("timestamp"):
                existing["timestamp"] = record.get("timestamp")
            if not existing.get("resolvedImagePath") and record.get("resolvedImagePath"):
                existing["resolvedImagePath"] = record.get("resolvedImagePath")

            seen_items = {
                (item.get("label"), item.get("size"), item.get("quantity"))
                for item in existing.get("items", [])
            }
            for item in record.get("items", []):
                item_key = (item.get("label"), item.get("size"), item.get("quantity"))
                if item_key not in seen_items:
                    existing.setdefault("items", []).append(item)
                    seen_items.add(item_key)

            if record.get("source") and record.get("source") not in existing.get("source", ""):
                existing["source"] = f"{existing.get('source', '')}, {record['source']}".strip(", ")
    return [merged[key] for key in order]


def flatten_items(records: list[dict]) -> list[dict]:
    rows = []
    for record in records:
        lat = record.get("latitude")
        lon = record.get("longitude")
        if lat in (None, "") or lon in (None, ""):
            continue
        if record.get("items"):
            for item in record["items"]:
                rows.append(
                    {
                        "imagePath": record.get("imagePath", ""),
                        "resolvedImagePath": record.get("resolvedImagePath"),
                        "timestamp": record.get("timestamp", ""),
                        "latitude": float(lat),
                        "longitude": float(lon),
                        "label": item.get("label", "미라벨") or "미라벨",
                        "size": item.get("size", "small") or "small",
                        "quantity": int(item.get("quantity", 1) or 1),
                        "source": record.get("source", ""),
                    }
                )
        else:
            rows.append(
                {
                    "imagePath": record.get("imagePath", ""),
                    "resolvedImagePath": record.get("resolvedImagePath"),
                    "timestamp": record.get("timestamp", ""),
                    "latitude": float(lat),
                    "longitude": float(lon),
                    "label": "미라벨",
                    "size": "small",
                    "quantity": 0,
                    "source": record.get("source", ""),
                }
            )
    return rows


def compute_center(records: list[dict]) -> tuple[float, float]:
    valid = [r for r in records if r.get("latitude") not in (None, "") and r.get("longitude") not in (None, "")]
    if not valid:
        return 36.0, 127.0
    return (
        sum(float(r["latitude"]) for r in valid) / len(valid),
        sum(float(r["longitude"]) for r in valid) / len(valid),
    )


def sanitize_json(obj) -> str:
    return json.dumps(obj, ensure_ascii=False)


def point_in_ring(x: float, y: float, ring: list[list[float]]) -> bool:
    inside = False
    n = len(ring)
    for i in range(n):
        x1, y1 = ring[i]
        x2, y2 = ring[(i + 1) % n]
        intersects = ((y1 > y) != (y2 > y)) and (
            x < (x2 - x1) * (y - y1) / ((y2 - y1) or 1e-12) + x1
        )
        if intersects:
            inside = not inside
    return inside


def point_in_polygon(lon: float, lat: float, polygon_coords: list) -> bool:
    if not polygon_coords:
        return False
    outer = polygon_coords[0]
    if not point_in_ring(lon, lat, outer):
        return False
    for hole in polygon_coords[1:]:
        if point_in_ring(lon, lat, hole):
            return False
    return True


def locate_region(lon: float, lat: float, regions: list[dict]) -> str | None:
    for region in regions:
        geom = region["geometry"]
        if geom["type"] == "Polygon":
            if point_in_polygon(lon, lat, geom["coordinates"]):
                return region["name"]
        elif geom["type"] == "MultiPolygon":
            for polygon in geom["coordinates"]:
                if point_in_polygon(lon, lat, polygon):
                    return region["name"]
    return None


def build_grid_regions(rows: list[dict], lat_step: float = 0.0015, lon_step: float = 0.0015) -> list[dict]:
    regions = []
    by_cell = defaultdict(list)
    for row in rows:
        lat_idx = math.floor(row["latitude"] / lat_step)
        lon_idx = math.floor(row["longitude"] / lon_step)
        by_cell[(lat_idx, lon_idx)].append(row)

    for (lat_idx, lon_idx), cell_rows in sorted(by_cell.items()):
        min_lat = lat_idx * lat_step
        min_lon = lon_idx * lon_step
        name = f"grid_{lat_idx}_{lon_idx}"
        regions.append(
            {
                "name": name,
                "type": "grid",
                "bounds": {
                    "min_lat": min_lat,
                    "max_lat": min_lat + lat_step,
                    "min_lon": min_lon,
                    "max_lon": min_lon + lon_step,
                },
                "rows": cell_rows,
            }
        )
    return regions


def build_region_stats(rows: list[dict], region_geojson_path: str) -> list[dict]:
    if region_geojson_path:
        region_file = Path(region_geojson_path)
        geojson = load_json(region_file)
        region_defs = []
        for feature in geojson.get("features", []):
            props = feature.get("properties", {})
            region_defs.append(
                {
                    "name": props.get("name") or props.get("region") or f"region_{len(region_defs) + 1}",
                    "geometry": feature.get("geometry", {}),
                }
            )
        buckets = defaultdict(list)
        for row in rows:
            region_name = locate_region(row["longitude"], row["latitude"], region_defs)
            if region_name is not None:
                buckets[region_name].append(row)
        results = []
        for region_name, region_rows in buckets.items():
            results.append({"name": region_name, "type": "geojson", "rows": region_rows})
        return results
    return build_grid_regions(rows)


def summarize_region(region: dict) -> dict:
    label_counter = Counter()
    quantity_sum = 0
    weighted_sum = 0
    image_set = set()
    for row in region["rows"]:
        label_counter[row["label"]] += row["quantity"]
        quantity_sum += row["quantity"]
        weighted_sum += row["quantity"] * SIZE_WEIGHTS.get(row["size"], 1)
        image_set.add(row["imagePath"])

    top_label = ""
    if label_counter:
        top_label = label_counter.most_common(1)[0][0]

    return {
        "name": region["name"],
        "type": region["type"],
        "image_count": len(image_set),
        "quantity_sum": quantity_sum,
        "weighted_pollution": weighted_sum,
        "top_label": top_label,
        "label_totals": dict(label_counter),
        "bounds": region.get("bounds"),
    }


def build_dashboard_data(records: list[dict], rows: list[dict]) -> dict:
    label_totals = Counter()
    size_totals = Counter()
    source_totals = Counter()
    image_with_labels = 0
    unlabeled_images = 0

    for record in records:
        if record.get("items"):
            image_with_labels += 1
        else:
            unlabeled_images += 1

    for row in rows:
        if row["quantity"] > 0:
            label_totals[row["label"]] += row["quantity"]
            size_totals[row["size"]] += row["quantity"]
        source_totals[row["source"] or "unknown"] += 1

    region_stats = [summarize_region(region) for region in build_region_stats(rows, REGION_GEOJSON_PATH)]
    region_stats.sort(key=lambda item: item["weighted_pollution"], reverse=True)

    return {
        "summary": {
            "record_count": len(records),
            "item_row_count": len(rows),
            "images_with_labels": image_with_labels,
            "unlabeled_images": unlabeled_images,
            "label_totals": dict(label_totals),
            "size_totals": dict(size_totals),
            "source_totals": dict(source_totals),
            "generated_at": datetime.now().isoformat(timespec="seconds"),
        },
        "regions": region_stats,
    }


def build_overview_html(records: list[dict], rows: list[dict], dashboard: dict) -> str:
    center_lat, center_lon = compute_center(records)
    records_json = sanitize_json(records)
    rows_json = sanitize_json(rows)
    dashboard_json = sanitize_json(dashboard)
    color_map_json = sanitize_json(LABEL_COLORS)
    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>라벨링 개요 지도</title>
  <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" crossorigin="">
  <style>
    :root {{
      --bg: #eef2eb;
      --panel: rgba(255,255,255,0.94);
      --text: #162312;
      --muted: #66725f;
      --border: rgba(22,35,18,0.12);
      --accent: #244c2a;
    }}
    * {{ box-sizing: border-box; }}
    body {{ margin:0; font-family:"Segoe UI","Malgun Gothic",sans-serif; color:var(--text); background:linear-gradient(180deg,#f5f7f2 0%,var(--bg) 100%); }}
    .layout {{ display:grid; grid-template-columns:360px 1fr; min-height:100vh; }}
    .sidebar {{ padding:20px; background:var(--panel); border-right:1px solid var(--border); overflow:auto; }}
    .sidebar h1 {{ margin:0 0 12px; font-size:28px; }}
    .sidebar p {{ margin:0 0 10px; color:var(--muted); line-height:1.5; }}
    .stat-card {{ margin:12px 0; padding:14px; border:1px solid var(--border); border-radius:16px; background:#fff; }}
    .legend-row {{ display:flex; align-items:center; gap:8px; margin:6px 0; font-size:14px; }}
    .swatch {{ width:14px; height:14px; border-radius:999px; display:inline-block; }}
    .region-list {{ margin-top:12px; font-size:14px; }}
    .region-item {{ padding:10px 0; border-top:1px solid var(--border); }}
    #map {{ min-height:100vh; }}
    .popup img {{ width:100%; border-radius:10px; margin-top:8px; }}
    .popup .meta {{ font-size:12px; color:#556; margin-top:6px; line-height:1.45; }}
    .popup ul {{ padding-left:18px; margin:8px 0 0; }}
    @media (max-width: 960px) {{
      .layout {{ grid-template-columns:1fr; }}
      .sidebar {{ border-right:0; border-bottom:1px solid var(--border); }}
      #map {{ min-height:70vh; }}
    }}
  </style>
</head>
<body>
  <div class="layout">
    <aside class="sidebar">
      <h1>라벨링 개요</h1>
      <p>여러 JSON을 병합해 라벨링 위치와 지역별 오염 통계를 한 번에 볼 수 있게 만든 페이지입니다.</p>
      <div class="stat-card" id="summary"></div>
      <div class="stat-card">
        <strong>라벨 범례</strong>
        <div id="legend"></div>
      </div>
      <div class="stat-card">
        <strong>지역별 통계</strong>
        <div class="region-list" id="regions"></div>
      </div>
    </aside>
    <main id="map"></main>
  </div>

  <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js" crossorigin=""></script>
  <script>
    const records = {records_json};
    const rows = {rows_json};
    const dashboard = {dashboard_json};
    const colorMap = {color_map_json};

    const map = L.map('map').setView([{center_lat:.6f}, {center_lon:.6f}], 15);
    L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
      maxZoom: 19,
      attribution: '&copy; OpenStreetMap contributors'
    }}).addTo(map);

    const summary = dashboard.summary;
    document.getElementById('summary').innerHTML = `
      <div><strong>레코드 수</strong>: ${{summary.record_count}}</div>
      <div><strong>라벨 행 수</strong>: ${{summary.item_row_count}}</div>
      <div><strong>라벨된 이미지</strong>: ${{summary.images_with_labels}}</div>
      <div><strong>미라벨 이미지</strong>: ${{summary.unlabeled_images}}</div>
      <div><strong>생성 시각</strong>: ${{summary.generated_at}}</div>
    `;

    const legend = document.getElementById('legend');
    Object.entries(summary.label_totals)
      .sort((a, b) => b[1] - a[1])
      .forEach(([label, total]) => {{
        const color = colorMap[label] || '#888';
        const row = document.createElement('div');
        row.className = 'legend-row';
        row.innerHTML = `<span class="swatch" style="background:${{color}}"></span><span>${{label}} (${{total}})</span>`;
        legend.appendChild(row);
      }});

    const regionList = document.getElementById('regions');
    dashboard.regions.slice(0, 12).forEach(region => {{
      const item = document.createElement('div');
      item.className = 'region-item';
      item.innerHTML = `
        <div><strong>${{region.name}}</strong></div>
        <div>총량: ${{region.quantity_sum}} / 오염도: ${{region.weighted_pollution}}</div>
        <div>주요 라벨: ${{region.top_label || '-'}}</div>
        <div>이미지 수: ${{region.image_count}}</div>
      `;
      regionList.appendChild(item);
    }});

    const bounds = [];
    records.forEach(record => {{
      const lat = record.latitude;
      const lon = record.longitude;
      if (lat == null || lon == null) return;
      const markerColor = record.items && record.items.length ? (colorMap[record.items[0].label] || '#666') : '#9aa0a6';
      const itemsHtml = (record.items || []).map(item => `<li>${{item.label}} / ${{item.size}} / quantity=${{item.quantity}}</li>`).join('');
      const imageHtml = record.resolvedImagePath ? `<img src="${{record.resolvedImagePath.replaceAll('\\\\', '/')}}" alt="${{record.imagePath}}">` : '';
      const popup = `
        <div class="popup">
          <strong>${{record.imagePath}}</strong>
          <div class="meta">timestamp: ${{record.timestamp || '-'}}<br>lat/lon: ${{lat}}, ${{lon}}<br>source: ${{record.source || '-'}} </div>
          <ul>${{itemsHtml || '<li>미라벨</li>'}}</ul>
          ${{imageHtml}}
        </div>
      `;
      const marker = L.circleMarker([lat, lon], {{
        radius: 6,
        color: markerColor,
        weight: 2,
        fillColor: markerColor,
        fillOpacity: 0.78
      }}).addTo(map);
      marker.bindPopup(popup);
      bounds.push([lat, lon]);
    }});

    if (bounds.length > 1) {{
      map.fitBounds(bounds, {{ padding: [28, 28] }});
    }}
  </script>
</body>
</html>
"""


def build_heatmap_html(rows: list[dict]) -> str:
    center_lat, center_lon = compute_center(rows)
    heat_rows = []
    for row in rows:
        weight = max(row["quantity"], 1)
        heat_rows.append([row["latitude"], row["longitude"], weight])
    heat_json = sanitize_json(heat_rows)
    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>라벨 히트맵</title>
  <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" crossorigin="">
  <style>
    body {{ margin:0; font-family:"Segoe UI","Malgun Gothic",sans-serif; }}
    #map {{ width:100vw; height:100vh; }}
    .panel {{ position:absolute; top:16px; left:16px; z-index:1000; background:rgba(255,255,255,0.94); padding:14px 16px; border-radius:14px; max-width:320px; box-shadow:0 10px 24px rgba(0,0,0,0.1); }}
    .panel h1 {{ margin:0 0 8px; font-size:22px; }}
    .panel p {{ margin:0; line-height:1.45; color:#445; }}
  </style>
</head>
<body>
  <div class="panel">
    <h1>오염 히트맵</h1>
    <p>각 포인트의 quantity를 가중치로 사용합니다. 숫자가 많을수록 더 뜨겁게 보입니다.</p>
  </div>
  <div id="map"></div>
  <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js" crossorigin=""></script>
  <script src="https://unpkg.com/leaflet.heat/dist/leaflet-heat.js"></script>
  <script>
    const points = {heat_json};
    const map = L.map('map').setView([{center_lat:.6f}, {center_lon:.6f}], 15);
    L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
      maxZoom: 19,
      attribution: '&copy; OpenStreetMap contributors'
    }}).addTo(map);
    const heat = L.heatLayer(points, {{
      radius: 28,
      blur: 22,
      maxZoom: 18,
      gradient: {{0.2: '#2b83ba', 0.45: '#abdda4', 0.7: '#fdae61', 1.0: '#d7191c'}}
    }}).addTo(map);
  </script>
</body>
</html>
"""


def build_pollution_map_html(rows: list[dict], dashboard: dict) -> str:
    center_lat, center_lon = compute_center(rows)
    region_json = sanitize_json(dashboard["regions"])
    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>오염도 지도</title>
  <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" crossorigin="">
  <style>
    body {{ margin:0; font-family:"Segoe UI","Malgun Gothic",sans-serif; }}
    #map {{ width:100vw; height:100vh; }}
    .panel {{ position:absolute; top:16px; left:16px; z-index:1000; background:rgba(255,255,255,0.96); padding:14px 16px; border-radius:14px; max-width:360px; box-shadow:0 10px 24px rgba(0,0,0,0.1); }}
    .panel h1 {{ margin:0 0 8px; font-size:22px; }}
    .panel p {{ margin:0; line-height:1.45; color:#445; }}
  </style>
</head>
<body>
  <div class="panel">
    <h1>지역별 오염도</h1>
    <p>기본은 자동 격자 기반입니다. `REGION_GEOJSON_PATH`를 지정하면 사용자가 정한 지역 경계로 통계가 나옵니다.</p>
  </div>
  <div id="map"></div>
  <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js" crossorigin=""></script>
  <script>
    const regions = {region_json};
    const map = L.map('map').setView([{center_lat:.6f}, {center_lon:.6f}], 15);
    L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
      maxZoom: 19,
      attribution: '&copy; OpenStreetMap contributors'
    }}).addTo(map);

    const values = regions.map(r => r.weighted_pollution);
    const maxValue = Math.max(...values, 1);
    function colorForValue(v) {{
      const ratio = v / maxValue;
      if (ratio > 0.75) return '#b10026';
      if (ratio > 0.5) return '#e31a1c';
      if (ratio > 0.25) return '#fc8d59';
      if (ratio > 0.1) return '#fdcc8a';
      return '#ffffcc';
    }}

    regions.forEach(region => {{
      if (!region.bounds) return;
      const bounds = [
        [region.bounds.min_lat, region.bounds.min_lon],
        [region.bounds.max_lat, region.bounds.max_lon]
      ];
      const rectangle = L.rectangle(bounds, {{
        color: colorForValue(region.weighted_pollution),
        weight: 1.5,
        fillOpacity: 0.38
      }}).addTo(map);
      rectangle.bindPopup(`
        <strong>${{region.name}}</strong><br>
        총량: ${{region.quantity_sum}}<br>
        오염도: ${{region.weighted_pollution}}<br>
        이미지 수: ${{region.image_count}}<br>
        주요 라벨: ${{region.top_label || '-'}}
      `);
    }});
  </script>
</body>
</html>
"""


def build_region_stats_html(dashboard: dict) -> str:
    regions = dashboard["regions"]
    rows = []
    for region in regions:
        top_labels = ", ".join(
            f"{label}:{total}" for label, total in sorted(region["label_totals"].items(), key=lambda x: x[1], reverse=True)[:5]
        )
        rows.append(
            f"<tr><td>{region['name']}</td><td>{region['image_count']}</td><td>{region['quantity_sum']}</td>"
            f"<td>{region['weighted_pollution']}</td><td>{region['top_label'] or '-'}</td><td>{top_labels}</td></tr>"
        )
    table_rows = "\n".join(rows)
    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>지역별 통계</title>
  <style>
    body {{ margin:0; padding:24px; font-family:"Segoe UI","Malgun Gothic",sans-serif; background:#f6f7f4; color:#1f2d1a; }}
    h1 {{ margin:0 0 12px; }}
    p {{ color:#4d5b48; line-height:1.5; }}
    table {{ width:100%; border-collapse:collapse; background:#fff; border-radius:14px; overflow:hidden; }}
    th, td {{ padding:12px 14px; border-bottom:1px solid #e6ebe2; text-align:left; vertical-align:top; }}
    th {{ background:#edf3ea; }}
    tr:last-child td {{ border-bottom:0; }}
  </style>
</head>
<body>
  <h1>지역별 통계</h1>
  <p>지역은 GeoJSON 경계가 있으면 그 기준으로, 없으면 자동 격자 기준으로 묶습니다. 사용자가 직접 위치 구역을 지정하려면 `REGION_GEOJSON_PATH`에 폴리곤 파일을 넣으면 됩니다.</p>
  <table>
    <thead>
      <tr>
        <th>지역</th>
        <th>이미지 수</th>
        <th>총 quantity</th>
        <th>오염도</th>
        <th>주요 라벨</th>
        <th>라벨 합계</th>
      </tr>
    </thead>
    <tbody>
      {table_rows}
    </tbody>
  </table>
</body>
</html>
"""


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    loaded = []
    for json_path_str in JSON_PATHS:
        json_path = Path(json_path_str)
        if not json_path.exists():
            raise SystemExit(f"JSON 파일을 찾을 수 없습니다: {json_path}")
        data = load_json(json_path)
        if not isinstance(data, list):
            raise SystemExit(f"JSON 파일은 리스트여야 합니다: {json_path}")
        source_name = json_path.parent.name
        loaded.append([normalize_record(record, source_name) for record in data])

    merged_records = merge_records(loaded)
    rows = flatten_items(merged_records)
    dashboard = build_dashboard_data(merged_records, rows)

    (OUTPUT_DIR / "merged_records.json").write_text(
        json.dumps(merged_records, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (OUTPUT_DIR / "overview_map.html").write_text(build_overview_html(merged_records, rows, dashboard), encoding="utf-8")
    (OUTPUT_DIR / "heatmap.html").write_text(build_heatmap_html(rows), encoding="utf-8")
    (OUTPUT_DIR / "pollution_map.html").write_text(build_pollution_map_html(rows, dashboard), encoding="utf-8")
    (OUTPUT_DIR / "region_stats.html").write_text(build_region_stats_html(dashboard), encoding="utf-8")

    print(f"saved\t{OUTPUT_DIR / 'overview_map.html'}")
    print(f"saved\t{OUTPUT_DIR / 'heatmap.html'}")
    print(f"saved\t{OUTPUT_DIR / 'pollution_map.html'}")
    print(f"saved\t{OUTPUT_DIR / 'region_stats.html'}")
    print(f"records\t{len(merged_records)}")
    print(f"rows\t{len(rows)}")


if __name__ == "__main__":
    main()
