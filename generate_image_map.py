from __future__ import annotations

import json
from pathlib import Path
from statistics import mean
from typing import Iterable

from PIL import Image
from PIL.ExifTags import GPSTAGS, TAGS


ROOT = Path(__file__).resolve().parent
IMAGE_DIR = ROOT / "image"
OUTPUT_GEOJSON = ROOT / "image_locations.geojson"
OUTPUT_HTML = ROOT / "image_map.html"


def rational_to_float(value) -> float:
    if hasattr(value, "numerator") and hasattr(value, "denominator"):
        return float(value.numerator) / float(value.denominator)
    if isinstance(value, tuple) and len(value) == 2:
        return float(value[0]) / float(value[1])
    return float(value)


def dms_to_decimal(dms: Iterable, ref: str) -> float:
    degrees, minutes, seconds = [rational_to_float(part) for part in dms]
    decimal = degrees + (minutes / 60.0) + (seconds / 3600.0)
    if ref in {"S", "W"}:
        decimal *= -1
    return decimal


def extract_gps(image_path: Path):
    with Image.open(image_path) as img:
        exif = img.getexif()
        gps_tag_id = None
        for tag_id, value in exif.items():
            if TAGS.get(tag_id) == "GPSInfo":
                gps_tag_id = tag_id
                break
        if gps_tag_id is None:
            return None

        gps_raw = exif.get_ifd(gps_tag_id)
        gps = {GPSTAGS.get(key, key): value for key, value in gps_raw.items()}
        lat = gps.get("GPSLatitude")
        lat_ref = gps.get("GPSLatitudeRef")
        lon = gps.get("GPSLongitude")
        lon_ref = gps.get("GPSLongitudeRef")
        if not all([lat, lat_ref, lon, lon_ref]):
            return None

        return {
            "latitude": dms_to_decimal(lat, lat_ref),
            "longitude": dms_to_decimal(lon, lon_ref),
        }


def build_feature(image_path: Path, latitude: float, longitude: float) -> dict:
    return {
        "type": "Feature",
        "geometry": {
            "type": "Point",
            "coordinates": [longitude, latitude],
        },
        "properties": {
            "filename": image_path.name,
            "imagePath": f"image/{image_path.name}",
        },
    }


def build_html(features: list[dict], center_lat: float, center_lon: float) -> str:
    feature_json = json.dumps(features, ensure_ascii=False)
    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Image Map</title>
  <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" crossorigin="">
  <style>
    :root {{
      --bg: #f3f1ea;
      --panel: rgba(255, 252, 245, 0.92);
      --text: #18230f;
      --accent: #355f2e;
      --border: rgba(24, 35, 15, 0.12);
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: "Segoe UI", "Malgun Gothic", sans-serif;
      color: var(--text);
      background:
        radial-gradient(circle at top left, rgba(53, 95, 46, 0.16), transparent 24rem),
        linear-gradient(180deg, #f7f6f2 0%, var(--bg) 100%);
    }}
    .layout {{
      display: grid;
      grid-template-columns: 360px 1fr;
      min-height: 100vh;
    }}
    .sidebar {{
      padding: 24px;
      background: var(--panel);
      backdrop-filter: blur(10px);
      border-right: 1px solid var(--border);
    }}
    .sidebar h1 {{
      margin: 0 0 10px;
      font-size: 28px;
    }}
    .sidebar p {{
      margin: 0 0 12px;
      line-height: 1.5;
    }}
    .stats {{
      margin-top: 20px;
      padding: 16px;
      border: 1px solid var(--border);
      border-radius: 16px;
      background: rgba(255, 255, 255, 0.56);
    }}
    #map {{
      width: 100%;
      min-height: 100vh;
    }}
    .leaflet-popup-content {{
      min-width: 220px;
    }}
    .popup img {{
      width: 100%;
      border-radius: 10px;
      margin-top: 8px;
    }}
    .popup .name {{
      font-weight: 700;
      word-break: break-all;
    }}
    .popup .coord {{
      margin-top: 6px;
      font-size: 12px;
      opacity: 0.8;
    }}
    @media (max-width: 900px) {{
      .layout {{
        grid-template-columns: 1fr;
      }}
      .sidebar {{
        border-right: 0;
        border-bottom: 1px solid var(--border);
      }}
      #map {{
        min-height: 70vh;
      }}
    }}
  </style>
</head>
<body>
  <div class="layout">
    <aside class="sidebar">
      <h1>플로깅 이미지 지도</h1>
      <p>사진 EXIF의 GPS 좌표를 읽어 마커로 표시했습니다.</p>
      <p>마커를 누르면 파일명과 미리보기를 확인할 수 있습니다.</p>
      <div class="stats">
        <div>총 마커: <strong>{len(features)}</strong></div>
        <div>중심 좌표: <strong>{center_lat:.6f}, {center_lon:.6f}</strong></div>
      </div>
    </aside>
    <main id="map"></main>
  </div>

  <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js" crossorigin=""></script>
  <script>
    const features = {feature_json};
    const map = L.map('map').setView([{center_lat:.6f}, {center_lon:.6f}], 15);

    L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
      maxZoom: 19,
      attribution: '&copy; OpenStreetMap contributors'
    }}).addTo(map);

    const bounds = [];
    for (const feature of features) {{
      const [lon, lat] = feature.geometry.coordinates;
      const props = feature.properties;
      const popup = `
        <div class="popup">
          <div class="name">${{props.filename}}</div>
          <div class="coord">${{lat.toFixed(6)}}, ${{lon.toFixed(6)}}</div>
          <img src="${{props.imagePath}}" alt="${{props.filename}}">
        </div>
      `;
      L.marker([lat, lon]).addTo(map).bindPopup(popup);
      bounds.push([lat, lon]);
    }}

    if (bounds.length > 1) {{
      map.fitBounds(bounds, {{ padding: [30, 30] }});
    }}
  </script>
</body>
</html>
"""


def main() -> None:
    features: list[dict] = []
    skipped: list[str] = []

    for image_path in sorted(IMAGE_DIR.glob("*.jpg")):
        gps = extract_gps(image_path)
        if not gps:
            skipped.append(image_path.name)
            continue
        features.append(build_feature(image_path, gps["latitude"], gps["longitude"]))

    if not features:
        raise SystemExit("GPS metadata가 포함된 이미지가 없습니다.")

    center_lat = mean(feature["geometry"]["coordinates"][1] for feature in features)
    center_lon = mean(feature["geometry"]["coordinates"][0] for feature in features)

    geojson = {
        "type": "FeatureCollection",
        "features": features,
    }
    OUTPUT_GEOJSON.write_text(json.dumps(geojson, ensure_ascii=False, indent=2), encoding="utf-8")
    OUTPUT_HTML.write_text(build_html(features, center_lat, center_lon), encoding="utf-8")

    print(f"saved_geojson\\t{OUTPUT_GEOJSON}")
    print(f"saved_html\\t{OUTPUT_HTML}")
    print(f"feature_count\\t{len(features)}")
    print(f"skipped\\t{len(skipped)}")
    if skipped:
        print("skipped_files")
        for name in skipped:
            print(name)


if __name__ == "__main__":
    main()
