## OSM Background Map Setup

### 1. Background map image
- Prepare a static background image of Gunsan National University from OpenStreetMap or an OSM-based map source.
- Save the image into `Assets/Sprites/` as something like `gunsan_campus_map.png`.
- In Unity, select the image asset and set:
  - Texture Type: `Sprite (2D and UI)`
  - Sprite Mode: `Single`

### 2. Scene objects
- Create an empty GameObject named `MapRoot`
- Under `MapRoot`, create:
  - `MapBackground` with a `SpriteRenderer`
  - `Markers` as an empty child
  - `WalkableWays` as an empty child
  - `Buildings` as an empty child
  - `Grid` as an empty child
  - `Agents` as an empty child
  - `TrashMapLoader` as an empty child with the `TrashMapLoader` component
  - `OSMFeatureLoader` as an empty child with the `OSMFeatureLoader` component
  - `OSMGridGenerator` as an empty child with the `OSMGridGenerator` component
  - `SimpleAgentSpawner` as an empty child with the `SimpleAgentSpawner` component
  - `GreedyPloggingManager` as an empty child with the `GreedyPloggingManager` component
  - `SimulationDisplayController` as an empty child with the `SimulationDisplayController` component
  - `SimulationDebugOverlay` as an empty child with the `SimulationDebugOverlay` component

### 3. Marker prefab
- Create a simple sprite marker prefab:
  - GameObject with `SpriteRenderer`
  - Use a circle sprite or small icon
  - Save it as `Assets/Prefabs/TrashMarker.prefab`

### 4. TrashMapLoader fields
- Assign `merged_records.json` from `Assets/Data`
- Assign the `MapBackground` sprite renderer
- Assign the marker prefab
- Assign `Markers` as marker parent

### 4-1. OSMFeatureLoader fields
- Assign `osm_features.json` from `Assets/Data`
- Assign the same `MapBackground` sprite renderer
- Assign `WalkableWays` as walkable parent
- Assign `Buildings` as building parent
- Leave materials empty at first if needed
- Turn on `Use Override Bounds`
- Set the same stitched-map bounds used by `TrashMapLoader`:
  - `minLatitude = 35.94021206888745`
  - `maxLatitude = 35.95132986152265`
  - `minLongitude = 126.67510986328125`
  - `maxLongitude = 126.68609619140625`

### 4-2. OSMGridGenerator fields
- Assign `osm_features.json`
- Assign `MapBackground`
- Assign `Grid` as grid parent
- Turn on `Use Override Bounds`
- Set the same stitched-map bounds:
  - `minLatitude = 35.94021206888745`
  - `maxLatitude = 35.95132986152265`
  - `minLongitude = 126.67510986328125`
  - `maxLongitude = 126.68609619140625`
- Recommended first values:
  - `Cell World Size = 0.25`
  - `Walkable Distance Threshold = 0.18`
  - `Visualize Grid = On`
  - `Show Blocked Cells = On`
  - `Show Unwalkable Cells = Off`

### 4-3. SimpleAgentSpawner fields
- Create a simple agent prefab and assign it
- Assign `OSMGridGenerator`
- Assign `Agents` as agent parent
- Set `Initial Agent Count` to the number of people you want as input

### 4-4. GreedyPloggingManager fields
- Assign `Agents` as agents root
- Assign `Markers` as trash root
- Recommended first values:
  - `Distance Weight = 1.0`
  - `Quantity Weight = 1.5`
  - `Assign On Start = On`
- The manager automatically adds `GreedyPloggerAgent` to spawned agents if missing.

### 4-4. SimulationDisplayController fields
- Assign `Agents` as agents root
- Assign `Markers` as trash root
- Display mode options:
  - `AgentsOnly`
  - `TrashOnly`
  - `AgentsAndTrash`
- Keyboard shortcuts:
  - `1`: 사람만
  - `2`: 쓰레기만
  - `3`: 둘 다

### 4-5. SimulationDebugOverlay fields
- Assign `OSMGridGenerator`
- Assign `Agents`
- Assign `Markers`
- Assign `SimulationDisplayController`
- Play mode에서 좌상단에 사람 수 / 쓰레기 마커 수 / 셀 수가 표시됩니다

### 4-6. Python simulation replay
- The prepared replay JSON files are in `Assets/Data`:
  - `unity_replay_random.json`
  - `unity_replay_trash_priority.json`
  - `unity_replay_uniform.json`
- In Unity, open `Assets/Scenes/SampleScene.unity`.
- Run menu `Plogging > Configure Replay Scene`.
- This creates or updates a `PythonSimulationReplay` object and connects `MapBackground`, `Agents`, `Markers`, `AgentMarker.prefab`, and the three replay JSON files.
- Press Play to show the heuristic simulation replay.
- Controls:
  - `Space`: play/pause
  - `R`: restart
  - `+` / `-`: speed up/down
  - `[` / `]`: switch replay strategy
- For replay mode, `GreedyPloggingManager` is disabled by the configurator so Unity does not run a second live greedy simulation on top of the Python result.

### 5. Geographic bounds
- The map image must match the latitude/longitude bounds below.
- Set these on `TrashMapLoader` after confirming the exported image bbox:
  - `minLatitude`
  - `maxLatitude`
  - `minLongitude`
  - `maxLongitude`
- Current recommended bbox from the merged trash dataset:
  - `minLatitude = 35.940530555555554`
  - `maxLatitude = 35.9493861111111`
  - `minLongitude = 126.67731666666667`
  - `maxLongitude = 126.68594166666666`
- These values are also stored in `Assets/Data/map_config.json`

### 6. Test
- Press Play
- Markers should appear on the map
- Click a marker and check the Console for metadata
- Agents should begin moving toward trash markers automatically
- Collected markers should disappear from the map

## Recommended workflow

1. Export a static OSM image of the Gunsan campus area.
2. Record the exact bbox used for export.
3. Enter the same bbox into `TrashMapLoader`.
4. Adjust background sprite scale if needed.
5. Run and verify a few known points visually.
6. Generate walkable grid and confirm buildings become blocked cells.
7. Spawn agents and verify they only appear on walkable cells.

## Note

- Current mapping is linear interpolation between bbox and sprite bounds.
- If the exported map is cropped or rotated later, the bbox values must be updated to match exactly.
- Current building fill is an approximate bounding box overlay for quick validation.
- If needed later, building polygons can be triangulated for exact blocked shapes.
- Current grid logic treats building interiors as blocked and cells near walkable OSM ways as walkable.
- `종합체육관`처럼 `building=*`가 아니라 `leisure=stadium`으로 표시된 영역도 blocked 후보에 포함하도록 반영했습니다.
