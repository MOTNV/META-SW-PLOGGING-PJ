using System;
using System.Collections.Generic;
using System.Globalization;
using UnityEngine;

[Serializable]
public class TrashItem
{
    public string label;
    public string size;
    public int quantity;
}

[Serializable]
public class TrashRecord
{
    public int recordIndex = -1;
    public string imagePath;
    public double latitude;
    public double longitude;
    public string timestamp;
    public List<TrashItem> items;
    public string source;
    public string resolvedImagePath;
}

[Serializable]
public class TrashRecordList
{
    public List<TrashRecord> records;
}

[Serializable]
public class ZoneTrashRecordList
{
    public List<TrashRecord> trashRecords;
}

public class TrashMapLoader : MonoBehaviour
{
    [Header("Data")]
    public TextAsset mergedRecordsJson;
    public bool loadOnStart = true;

    [Header("Map Bounds")]
    public SpriteRenderer mapRenderer;
    public double minLatitude = 35.94021206888745;
    public double maxLatitude = 35.95132986152265;
    public double minLongitude = 126.67510986328125;
    public double maxLongitude = 126.68609619140625;

    [Header("Markers")]
    public GameObject markerPrefab;
    public Transform markerParent;
    public bool clearExistingMarkersOnLoad = true;

    [Header("Visual")]
    public float baseMarkerScale = 0.04f;
    public float quantityScaleStep = 0.0025f;
    public float maxMarkerScale = 0.065f;
    public float markerOffsetStep = 0.012f;
    public bool hideUnlabeled = false;

    private void Start()
    {
        if (loadOnStart)
        {
            LoadMarkers();
        }
    }

    [ContextMenu("Load Markers")]
    public void LoadMarkers()
    {
        if (mergedRecordsJson == null)
        {
            Debug.LogWarning("TrashMapLoader requires a trash JSON TextAsset.");
            return;
        }

        if (mapRenderer == null)
        {
            Debug.LogWarning("TrashMapLoader requires mapRenderer.");
            return;
        }

        if (markerPrefab == null)
        {
            Debug.LogWarning("TrashMapLoader requires markerPrefab.");
            return;
        }

        if (markerParent == null)
        {
            markerParent = transform;
        }

        if (clearExistingMarkersOnLoad)
        {
            ClearMarkers();
        }

        var records = ParseTrashRecords(mergedRecordsJson.text);
        if (records == null)
        {
            Debug.LogWarning("Failed to parse trash records JSON.");
            return;
        }

        int spawned = 0;
        for (int i = 0; i < records.Count; i++)
        {
            int recordIndex = records[i].recordIndex >= 0 ? records[i].recordIndex : i;
            spawned += SpawnRecordMarkers(records[i], recordIndex);
        }

        Debug.Log($"[TrashMapLoader] spawned {spawned} trash markers from {records.Count} records.");
    }

    private List<TrashRecord> ParseTrashRecords(string json)
    {
        if (string.IsNullOrWhiteSpace(json))
        {
            return null;
        }

        string trimmed = json.TrimStart();
        if (trimmed.StartsWith("[", StringComparison.Ordinal))
        {
            var wrappedJson = "{\"records\":" + json + "}";
            var parsed = JsonUtility.FromJson<TrashRecordList>(wrappedJson);
            return parsed != null ? parsed.records : null;
        }

        var zoneParsed = JsonUtility.FromJson<ZoneTrashRecordList>(json);
        if (zoneParsed != null && zoneParsed.trashRecords != null)
        {
            return zoneParsed.trashRecords;
        }

        var recordParsed = JsonUtility.FromJson<TrashRecordList>(json);
        return recordParsed != null ? recordParsed.records : null;
    }

    [ContextMenu("Clear Markers")]
    public void ClearMarkers()
    {
        if (markerParent == null)
        {
            return;
        }

        for (int i = markerParent.childCount - 1; i >= 0; i--)
        {
            var child = markerParent.GetChild(i);
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

    private int SpawnRecordMarkers(TrashRecord record, int recordIndex)
    {
        if (record == null || !IsWithinBounds(record.latitude, record.longitude))
        {
            return 0;
        }

        var items = record.items;
        if (items == null || items.Count == 0)
        {
            if (hideUnlabeled)
            {
                return 0;
            }

            SpawnMarker(record, recordIndex, "unknown", 1, 0);
            return 1;
        }

        int spawned = 0;
        for (int i = 0; i < items.Count; i++)
        {
            var item = items[i];
            SpawnMarker(record, recordIndex, item.label, item.quantity, i);
            spawned++;
        }
        return spawned;
    }

    private void SpawnMarker(TrashRecord record, int recordIndex, string label, int quantity, int indexOffset)
    {
        var localPos = LatLonToLocalPosition(record.latitude, record.longitude);
        localPos += new Vector3(indexOffset * markerOffsetStep, indexOffset * markerOffsetStep, 0f);

        var marker = Instantiate(markerPrefab, markerParent);
        marker.name = $"{recordIndex:0000}_{record.imagePath}_{indexOffset}";
        marker.transform.localPosition = localPos;

        float scaleMultiplier = Mathf.Max(1f, quantity);
        float markerScale = Mathf.Min(maxMarkerScale, baseMarkerScale + (scaleMultiplier - 1f) * quantityScaleStep);
        marker.transform.localScale = Vector3.one * markerScale;

        var spriteRenderer = marker.GetComponent<SpriteRenderer>();
        if (spriteRenderer != null)
        {
            spriteRenderer.color = GetColorForLabel(label);
            spriteRenderer.sortingOrder = 20;
        }

        var metadata = marker.GetComponent<TrashMarkerMeta>();
        if (metadata == null)
        {
            metadata = marker.AddComponent<TrashMarkerMeta>();
        }

        metadata.imagePath = record.imagePath;
        metadata.timestamp = record.timestamp;
        metadata.label = label;
        metadata.quantity = quantity;
        metadata.trashRecordIndex = recordIndex;
        metadata.latitude = record.latitude.ToString(CultureInfo.InvariantCulture);
        metadata.longitude = record.longitude.ToString(CultureInfo.InvariantCulture);
        metadata.source = record.source;
        metadata.InitializeQuantity(quantity);
    }

    private bool IsWithinBounds(double latitude, double longitude)
    {
        return latitude >= minLatitude
               && latitude <= maxLatitude
               && longitude >= minLongitude
               && longitude <= maxLongitude;
    }

    private Vector3 LatLonToLocalPosition(double latitude, double longitude)
    {
        var bounds = mapRenderer.bounds;
        float width = bounds.size.x;
        float height = bounds.size.y;

        double lonRatio = (longitude - minLongitude) / (maxLongitude - minLongitude);
        double latRatio = (latitude - minLatitude) / (maxLatitude - minLatitude);

        float x = (float)(lonRatio * width - width * 0.5f);
        float y = (float)(latRatio * height - height * 0.5f);
        return new Vector3(x, y, 0f);
    }

    private Color GetColorForLabel(string label)
    {
        if (string.IsNullOrWhiteSpace(label))
        {
            return new Color(0.62f, 0.64f, 0.67f);
        }

        if (label.Contains("담배"))
        {
            return new Color(0.82f, 0.29f, 0.36f);
        }
        if (label.Contains("종이"))
        {
            return new Color(0.93f, 0.68f, 0.29f);
        }
        if (label.Contains("플라스틱"))
        {
            return new Color(0.0f, 0.47f, 0.55f);
        }
        if (label.Contains("비닐"))
        {
            return new Color(0.19f, 0.40f, 0.75f);
        }
        if (label.Contains("캔") || label.Contains("금속"))
        {
            return new Color(0.46f, 0.50f, 0.55f);
        }
        if (label.Contains("유리"))
        {
            return new Color(0.33f, 0.65f, 0.28f);
        }

        return new Color(0.4f, 0.4f, 0.4f);
    }
}
