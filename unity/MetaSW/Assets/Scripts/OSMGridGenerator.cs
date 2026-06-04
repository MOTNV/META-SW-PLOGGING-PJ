using System;
using System.Collections.Generic;
using UnityEngine;

[Serializable]
public class GridCellData
{
    public Vector3 localPosition;
    public bool blocked;
    public bool walkable;
}

public class OSMGridGenerator : MonoBehaviour
{
    [Header("Data")]
    public TextAsset osmFeaturesJson;

    [Header("Map Reference")]
    public SpriteRenderer mapRenderer;
    public Transform gridParent;

    [Header("Bounds Override")]
    public bool useOverrideBounds = true;
    public double minLatitude = 35.94021206888745;
    public double maxLatitude = 35.95132986152265;
    public double minLongitude = 126.67510986328125;
    public double maxLongitude = 126.68609619140625;

    [Header("Grid Settings")]
    public float cellWorldSize = 0.25f;
    public float walkableDistanceThreshold = 0.18f;
    public bool generateOnStart = true;

    [Header("Visualization")]
    public bool visualizeGrid = true;
    public bool showBlockedCells = true;
    public bool showUnwalkableCells = false;
    public Material walkableMaterial;
    public Material blockedMaterial;
    public Material unwalkableMaterial;
    public Color walkableColor = new Color(0.1f, 0.8f, 0.25f, 0.22f);
    public Color blockedColor = new Color(0.85f, 0.15f, 0.15f, 0.32f);
    public Color unwalkableColor = new Color(0.5f, 0.5f, 0.5f, 0.18f);

    public List<GridCellData> Cells { get; private set; } = new List<GridCellData>();
    public List<GridCellData> WalkableCells { get; private set; } = new List<GridCellData>();

    private OSMFeaturesData parsedData;
    private readonly List<Vector3[]> walkableWayLocalPoints = new List<Vector3[]>();
    private readonly List<Vector2[]> buildingLocalPolygons = new List<Vector2[]>();
    private readonly List<Vector2[]> blockedAreaPolygons = new List<Vector2[]>();
    private readonly List<Vector2[]> allowedAreaPolygons = new List<Vector2[]>();
    private readonly List<Vector2[]> excludedZonePolygons = new List<Vector2[]>();
    private Vector2[] campusBoundaryPolygon;

    private void Start()
    {
        if (generateOnStart)
        {
            GenerateGrid();
        }
    }

    [ContextMenu("Generate Grid")]
    public void GenerateGrid()
    {
        if (osmFeaturesJson == null || mapRenderer == null)
        {
            Debug.LogWarning("OSMGridGenerator requires osmFeaturesJson and mapRenderer.");
            return;
        }

        if (gridParent == null)
        {
            gridParent = transform;
        }

        ClearGrid();

        parsedData = JsonUtility.FromJson<OSMFeaturesData>(osmFeaturesJson.text);
        if (parsedData == null)
        {
            Debug.LogWarning("Failed to parse osm_features.json");
            return;
        }

        CacheFeatureGeometry();
        BuildCells();
        Debug.Log($"[OSMGridGenerator] cells={Cells.Count}, walkable={WalkableCells.Count}");
    }

    [ContextMenu("Clear Grid")]
    public void ClearGrid()
    {
        Cells.Clear();
        WalkableCells.Clear();
        walkableWayLocalPoints.Clear();
        buildingLocalPolygons.Clear();
        blockedAreaPolygons.Clear();
        allowedAreaPolygons.Clear();
        excludedZonePolygons.Clear();
        campusBoundaryPolygon = null;

        if (gridParent == null)
        {
            return;
        }

        for (int i = gridParent.childCount - 1; i >= 0; i--)
        {
            var child = gridParent.GetChild(i);
            if (Application.isPlaying)
            {
                Destroy(child.gameObject);
            }
            else
            {
                DestroyImmediate(child.gameObject);
            }
        }
    }

    private void CacheFeatureGeometry()
    {
        if (parsedData.campusBoundary != null &&
            parsedData.campusBoundary.points != null &&
            parsedData.campusBoundary.points.Count >= 3)
        {
            campusBoundaryPolygon = new Vector2[parsedData.campusBoundary.points.Count];
            for (int i = 0; i < parsedData.campusBoundary.points.Count; i++)
            {
                var local = LatLonToLocalPosition(
                    parsedData.campusBoundary.points[i].latitude,
                    parsedData.campusBoundary.points[i].longitude);
                campusBoundaryPolygon[i] = new Vector2(local.x, local.y);
            }
        }

        if (parsedData.walkableWays != null)
        {
            foreach (var way in parsedData.walkableWays)
            {
                if (way.points == null || way.points.Count < 2)
                {
                    continue;
                }

                var localPoints = new Vector3[way.points.Count];
                for (int i = 0; i < way.points.Count; i++)
                {
                    localPoints[i] = LatLonToLocalPosition(way.points[i].latitude, way.points[i].longitude);
                }
                walkableWayLocalPoints.Add(localPoints);
            }
        }

        if (parsedData.buildings != null)
        {
            foreach (var building in parsedData.buildings)
            {
                if (building.points == null || building.points.Count < 3)
                {
                    continue;
                }

                var polygon = new Vector2[building.points.Count];
                for (int i = 0; i < building.points.Count; i++)
                {
                    var local = LatLonToLocalPosition(building.points[i].latitude, building.points[i].longitude);
                    polygon[i] = new Vector2(local.x, local.y);
                }
                buildingLocalPolygons.Add(polygon);
            }
        }

        if (parsedData.blockedAreas != null)
        {
            foreach (var area in parsedData.blockedAreas)
            {
                if (area.points == null || area.points.Count < 3)
                {
                    continue;
                }

                var polygon = new Vector2[area.points.Count];
                for (int i = 0; i < area.points.Count; i++)
                {
                    var local = LatLonToLocalPosition(area.points[i].latitude, area.points[i].longitude);
                    polygon[i] = new Vector2(local.x, local.y);
                }
                blockedAreaPolygons.Add(polygon);
            }
        }

        if (parsedData.allowedAreas != null)
        {
            foreach (var area in parsedData.allowedAreas)
            {
                if (area.points == null || area.points.Count < 3)
                {
                    continue;
                }

                var polygon = new Vector2[area.points.Count];
                for (int i = 0; i < area.points.Count; i++)
                {
                    var local = LatLonToLocalPosition(area.points[i].latitude, area.points[i].longitude);
                    polygon[i] = new Vector2(local.x, local.y);
                }
                allowedAreaPolygons.Add(polygon);
            }
        }

        if (parsedData.excludedZones != null)
        {
            foreach (var zone in parsedData.excludedZones)
            {
                if (zone.points == null || zone.points.Count < 3)
                {
                    continue;
                }

                var polygon = new Vector2[zone.points.Count];
                for (int i = 0; i < zone.points.Count; i++)
                {
                    var local = LatLonToLocalPosition(zone.points[i].latitude, zone.points[i].longitude);
                    polygon[i] = new Vector2(local.x, local.y);
                }
                excludedZonePolygons.Add(polygon);
            }
        }
    }

    private void BuildCells()
    {
        var bounds = mapRenderer.bounds;
        float width = bounds.size.x;
        float height = bounds.size.y;
        int cols = Mathf.Max(1, Mathf.FloorToInt(width / cellWorldSize));
        int rows = Mathf.Max(1, Mathf.FloorToInt(height / cellWorldSize));

        for (int y = 0; y < rows; y++)
        {
            for (int x = 0; x < cols; x++)
            {
                float localX = -width * 0.5f + cellWorldSize * (x + 0.5f);
                float localY = -height * 0.5f + cellWorldSize * (y + 0.5f);
                var localPos = new Vector3(localX, localY, 0f);

                if (!IsInsideCampusBoundary(localPos) || IsInsideExcludedZone(localPos))
                {
                    continue;
                }

                bool insideBuilding = IsInsideAnyBuilding(localPos);
                bool insideBlockedArea = IsInsideBlockedArea(localPos);
                bool insideAllowedArea = IsInsideAllowedArea(localPos);
                bool nearWalkableWay = IsNearWalkableWay(localPos);

                bool blocked = insideBuilding || (insideBlockedArea && !insideAllowedArea && !nearWalkableWay);
                bool walkable = !blocked && (nearWalkableWay || insideAllowedArea);

                var cell = new GridCellData
                {
                    localPosition = localPos,
                    blocked = blocked,
                    walkable = walkable,
                };
                Cells.Add(cell);

                if (walkable)
                {
                    WalkableCells.Add(cell);
                }

                if (visualizeGrid)
                {
                    CreateCellVisual(cell);
                }
            }
        }
    }

    private bool IsInsideAnyBuilding(Vector3 localPos)
    {
        var point = new Vector2(localPos.x, localPos.y);
        foreach (var polygon in buildingLocalPolygons)
        {
            if (PointInPolygon(point, polygon))
            {
                return true;
            }
        }
        return false;
    }

    private bool IsInsideCampusBoundary(Vector3 localPos)
    {
        if (campusBoundaryPolygon == null || campusBoundaryPolygon.Length < 3)
        {
            return true;
        }

        return PointInPolygon(new Vector2(localPos.x, localPos.y), campusBoundaryPolygon);
    }

    private bool IsInsideBlockedArea(Vector3 localPos)
    {
        if (blockedAreaPolygons.Count == 0)
        {
            return false;
        }

        var point = new Vector2(localPos.x, localPos.y);
        foreach (var polygon in blockedAreaPolygons)
        {
            if (PointInPolygon(point, polygon))
            {
                return true;
            }
        }

        return false;
    }

    private bool IsInsideAllowedArea(Vector3 localPos)
    {
        if (allowedAreaPolygons.Count == 0)
        {
            return false;
        }

        var point = new Vector2(localPos.x, localPos.y);
        foreach (var polygon in allowedAreaPolygons)
        {
            if (PointInPolygon(point, polygon))
            {
                return true;
            }
        }

        return false;
    }

    private bool IsInsideExcludedZone(Vector3 localPos)
    {
        if (excludedZonePolygons.Count == 0)
        {
            return false;
        }

        var point = new Vector2(localPos.x, localPos.y);
        foreach (var polygon in excludedZonePolygons)
        {
            if (PointInPolygon(point, polygon))
            {
                return true;
            }
        }

        return false;
    }

    private bool IsNearWalkableWay(Vector3 localPos)
    {
        float thresholdSqr = walkableDistanceThreshold * walkableDistanceThreshold;
        foreach (var points in walkableWayLocalPoints)
        {
            for (int i = 0; i < points.Length - 1; i++)
            {
                float distSqr = DistanceToSegmentSquared(localPos, points[i], points[i + 1]);
                if (distSqr <= thresholdSqr)
                {
                    return true;
                }
            }
        }
        return false;
    }

    private void CreateCellVisual(GridCellData cell)
    {
        if (cell.blocked && !showBlockedCells)
        {
            return;
        }

        if (!cell.blocked && !cell.walkable && !showUnwalkableCells)
        {
            return;
        }

        if (!cell.blocked && cell.walkable == false && showUnwalkableCells == false)
        {
            return;
        }

        var quad = GameObject.CreatePrimitive(PrimitiveType.Quad);
        quad.name = cell.blocked ? "BlockedCell" : (cell.walkable ? "WalkableCell" : "UnwalkableCell");
        quad.transform.SetParent(gridParent, false);
        quad.transform.localPosition = new Vector3(cell.localPosition.x, cell.localPosition.y, 0.1f);
        quad.transform.localScale = new Vector3(cellWorldSize, cellWorldSize, 1f);

        var collider = quad.GetComponent<Collider>();
        if (collider != null)
        {
            if (Application.isPlaying)
            {
                Destroy(collider);
            }
            else
            {
                DestroyImmediate(collider);
            }
        }

        var renderer = quad.GetComponent<MeshRenderer>();
        if (renderer == null)
        {
            return;
        }

        renderer.sortingOrder = -5;

        if (cell.blocked)
        {
            renderer.material = blockedMaterial != null ? blockedMaterial : new Material(Shader.Find("Sprites/Default"));
            renderer.material.color = blockedColor;
        }
        else if (cell.walkable)
        {
            renderer.material = walkableMaterial != null ? walkableMaterial : new Material(Shader.Find("Sprites/Default"));
            renderer.material.color = walkableColor;
        }
        else
        {
            renderer.material = unwalkableMaterial != null ? unwalkableMaterial : new Material(Shader.Find("Sprites/Default"));
            renderer.material.color = unwalkableColor;
        }
    }

    private Vector3 LatLonToLocalPosition(double latitude, double longitude)
    {
        var bounds = mapRenderer.bounds;
        float width = bounds.size.x;
        float height = bounds.size.y;

        double sourceMinLon = useOverrideBounds ? minLongitude : parsedData.bounds.minLongitude;
        double sourceMaxLon = useOverrideBounds ? maxLongitude : parsedData.bounds.maxLongitude;
        double sourceMinLat = useOverrideBounds ? minLatitude : parsedData.bounds.minLatitude;
        double sourceMaxLat = useOverrideBounds ? maxLatitude : parsedData.bounds.maxLatitude;

        double lonRatio = (longitude - sourceMinLon) / (sourceMaxLon - sourceMinLon);
        double latRatio = (latitude - sourceMinLat) / (sourceMaxLat - sourceMinLat);

        float x = (float)(lonRatio * width - width * 0.5f);
        float y = (float)(latRatio * height - height * 0.5f);
        return new Vector3(x, y, 0f);
    }

    private static bool PointInPolygon(Vector2 point, Vector2[] polygon)
    {
        bool inside = false;
        for (int i = 0, j = polygon.Length - 1; i < polygon.Length; j = i++)
        {
            bool intersect = ((polygon[i].y > point.y) != (polygon[j].y > point.y)) &&
                             (point.x < (polygon[j].x - polygon[i].x) * (point.y - polygon[i].y) /
                              ((polygon[j].y - polygon[i].y) + 0.000001f) + polygon[i].x);
            if (intersect)
            {
                inside = !inside;
            }
        }
        return inside;
    }

    private static float DistanceToSegmentSquared(Vector3 point, Vector3 a, Vector3 b)
    {
        var ab = b - a;
        float abSqr = Vector3.Dot(ab, ab);
        if (abSqr <= Mathf.Epsilon)
        {
            return (point - a).sqrMagnitude;
        }

        float t = Mathf.Clamp01(Vector3.Dot(point - a, ab) / abSqr);
        var projection = a + ab * t;
        return (point - projection).sqrMagnitude;
    }
}
