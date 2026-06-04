using System;
using System.Collections.Generic;
using UnityEngine;

[Serializable]
public class OSMPoint
{
    public double latitude;
    public double longitude;
}

[Serializable]
public class OSMWalkableWay
{
    public string id;
    public string highway;
    public string surface;
    public string foot;
    public string access;
    public List<OSMPoint> points;
}

[Serializable]
public class OSMBuilding
{
    public string id;
    public string building;
    public string name;
    public List<OSMPoint> points;
}

[Serializable]
public class OSMBounds
{
    public double minLatitude;
    public double minLongitude;
    public double maxLatitude;
    public double maxLongitude;
}

[Serializable]
public class OSMFeaturesData
{
    public OSMBounds bounds;
    public OSMFeatureSummary summary;
    public OSMCampusBoundary campusBoundary;
    public List<OSMExcludedZone> excludedZones;
    public List<OSMWalkableWay> walkableWays;
    public List<OSMBuilding> buildings;
    public List<OSMBlockedArea> blockedAreas;
    public List<OSMAllowedArea> allowedAreas;
}

[Serializable]
public class OSMFeatureSummary
{
    public int walkableWayCount;
    public int buildingCount;
    public int blockedAreaCount;
    public int allowedAreaCount;
    public bool hasCampusBoundary;
    public int excludedZoneCount;
}

[Serializable]
public class OSMCampusBoundary
{
    public string id;
    public string name;
    public List<OSMPoint> points;
}

[Serializable]
public class OSMExcludedZone
{
    public string id;
    public string name;
    public string reason;
    public List<OSMPoint> points;
}

[Serializable]
public class OSMBlockedArea
{
    public string id;
    public string name;
    public string natural;
    public string landuse;
    public List<OSMPoint> points;
}

[Serializable]
public class OSMAllowedArea
{
    public string id;
    public string name;
    public string leisure;
    public string sport;
    public List<OSMPoint> points;
}

public class OSMFeatureLoader : MonoBehaviour
{
    [Header("Data")]
    public TextAsset osmFeaturesJson;

    [Header("Map Reference")]
    public SpriteRenderer mapRenderer;
    public Transform walkableParent;
    public Transform buildingParent;

    [Header("Bounds Override")]
    public bool useOverrideBounds = true;
    public double minLatitude = 35.94021206888745;
    public double maxLatitude = 35.95132986152265;
    public double minLongitude = 126.67510986328125;
    public double maxLongitude = 126.68609619140625;

    [Header("Walkable Way Rendering")]
    public Material lineMaterial;
    public float lineWidth = 0.06f;
    public bool loadWalkableWaysOnStart = true;

    [Header("Building Rendering")]
    public Material buildingMaterial;
    public Color buildingColor = new Color(0.82f, 0.18f, 0.18f, 0.30f);
    public bool loadBuildingsOnStart = true;

    [Header("Cleanup")]
    public bool clearExistingOnLoad = true;

    private OSMFeaturesData parsedData;

    private void Start()
    {
        if (loadWalkableWaysOnStart || loadBuildingsOnStart)
        {
            LoadFeatures();
        }
    }

    [ContextMenu("Load OSM Features")]
    public void LoadFeatures()
    {
        if (osmFeaturesJson == null)
        {
            Debug.LogWarning("osmFeaturesJson is not assigned.");
            return;
        }

        if (mapRenderer == null)
        {
            Debug.LogWarning("mapRenderer is not assigned.");
            return;
        }

        if (walkableParent == null)
        {
            walkableParent = transform;
        }

        if (buildingParent == null)
        {
            buildingParent = transform;
        }

        if (clearExistingOnLoad)
        {
            ClearChildren(walkableParent);
            ClearChildren(buildingParent);
        }

        parsedData = JsonUtility.FromJson<OSMFeaturesData>(osmFeaturesJson.text);
        if (parsedData == null)
        {
            Debug.LogWarning("Failed to parse osm_features.json");
            return;
        }

        if (loadWalkableWaysOnStart && parsedData.walkableWays != null)
        {
            foreach (var way in parsedData.walkableWays)
            {
                CreateWalkableLine(way);
            }
        }

        if (loadBuildingsOnStart && parsedData.buildings != null)
        {
            foreach (var building in parsedData.buildings)
            {
                CreateBuildingPolygon(building);
            }
        }
    }

    [ContextMenu("Clear OSM Features")]
    public void ClearFeatures()
    {
        if (walkableParent != null)
        {
            ClearChildren(walkableParent);
        }

        if (buildingParent != null)
        {
            ClearChildren(buildingParent);
        }
    }

    private void ClearChildren(Transform parent)
    {
        for (int i = parent.childCount - 1; i >= 0; i--)
        {
            var child = parent.GetChild(i);
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

    private void CreateWalkableLine(OSMWalkableWay way)
    {
        if (way.points == null || way.points.Count < 2)
        {
            return;
        }

        var go = new GameObject($"Walkable_{way.id}_{way.highway}");
        go.transform.SetParent(walkableParent, false);

        var lr = go.AddComponent<LineRenderer>();
        lr.useWorldSpace = false;
        lr.loop = false;
        lr.positionCount = way.points.Count;
        lr.startWidth = lineWidth;
        lr.endWidth = lineWidth;
        lr.numCornerVertices = 2;
        lr.numCapVertices = 2;
        lr.sortingOrder = 1;

        if (lineMaterial != null)
        {
            lr.material = lineMaterial;
        }
        else
        {
            lr.material = new Material(Shader.Find("Sprites/Default"));
        }

        lr.startColor = GetWalkableColor(way.highway);
        lr.endColor = lr.startColor;

        for (int i = 0; i < way.points.Count; i++)
        {
            lr.SetPosition(i, LatLonToLocalPosition(way.points[i].latitude, way.points[i].longitude));
        }
    }

    private void CreateBuildingPolygon(OSMBuilding building)
    {
        if (building.points == null || building.points.Count < 3)
        {
            return;
        }

        var go = new GameObject($"Building_{building.id}");
        go.transform.SetParent(buildingParent, false);

        var lr = go.AddComponent<LineRenderer>();
        lr.useWorldSpace = false;
        lr.loop = true;
        lr.positionCount = building.points.Count;
        lr.startWidth = 0.03f;
        lr.endWidth = 0.03f;
        lr.sortingOrder = 2;
        lr.material = new Material(Shader.Find("Sprites/Default"));
        lr.startColor = new Color(0.55f, 0.12f, 0.12f, 0.9f);
        lr.endColor = lr.startColor;

        for (int i = 0; i < building.points.Count; i++)
        {
            var pos = LatLonToLocalPosition(building.points[i].latitude, building.points[i].longitude);
            lr.SetPosition(i, pos);
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

        float x = (float)(lonRatio * width - width / 2f);
        float y = (float)(latRatio * height - height / 2f);
        return new Vector3(x, y, 0f);
    }

    private Color GetWalkableColor(string highway)
    {
        switch (highway)
        {
            case "footway":
            case "pedestrian":
            case "steps":
            case "crossing":
                return new Color(0.10f, 0.55f, 0.95f, 1f);
            case "path":
            case "track":
            case "cycleway":
                return new Color(0.19f, 0.72f, 0.47f, 1f);
            case "residential":
            case "service":
            case "living_street":
                return new Color(0.98f, 0.78f, 0.26f, 1f);
            default:
                return Color.white;
        }
    }
}
