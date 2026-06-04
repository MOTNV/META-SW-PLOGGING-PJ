using System;
using System.Collections.Generic;
using System.Globalization;
using UnityEngine;
#if ENABLE_INPUT_SYSTEM
using UnityEngine.InputSystem;
#endif

[Serializable]
public class ReplayRoot
{
    public ReplayMetadata metadata;
    public ReplaySummary summary;
    public List<int> activeTrashRecordIndices;
    public List<int> excludedTrashRecordIndices;
    public List<ReplayAgentFinal> agents;
    public List<ReplayStep> history;
}

[Serializable]
public class ReplayMetadata
{
    public string strategy;
    public float stepSeconds;
    public float maxSeconds;
    public int agentCount;
    public int trashRecordCount;
    public string distanceMode;
    public int unitySampleSeconds;
    public float localCleanupRadiusMeters;
    public string localCleanupSelectionMode;
    public float maxTargetRouteDistanceMeters;
    public bool allowDuplicateTargets;
}

[Serializable]
public class ReplaySummary
{
    public float elapsedTimeSeconds;
    public int initialTrashMass;
    public int remainingTrashMass;
    public int collectedTrashMass;
    public float collectionRate;
    public float totalIdleTimeSeconds;
    public float totalTravelDistanceMeters;
    public bool allTrashCollected;
}

[Serializable]
public class ReplayAgentFinal
{
    public string agent_id;
    public string assigned_zone_id;
    public double latitude;
    public double longitude;
}

[Serializable]
public class ReplayAgentSnapshot
{
    public string agentId;
    public string assignedZoneId;
    public double latitude;
    public double longitude;
    public int targetTrashIndex = -1;
    public int collectedMass;
    public int collectedCount;
}

[Serializable]
public class ReplayStep
{
    public float timeSeconds;
    public int remainingTrashMass;
    public int remainingTrashCount;
    public int idleAgentCount;
    public float zoneImbalance;
    public List<ReplayAgentSnapshot> agentSnapshots;
    public List<int> collectedTrashIndices;
}

public class PythonSimulationReplay : MonoBehaviour
{
    [Header("Data")]
    public TextAsset simulationResultJson;
    public TextAsset[] replayFiles;
    public int activeReplayIndex = 0;

    [Header("Map Bounds")]
    public SpriteRenderer mapRenderer;
    public double minLatitude = 35.94021206888745;
    public double maxLatitude = 35.95132986152265;
    public double minLongitude = 126.67510986328125;
    public double maxLongitude = 126.68609619140625;

    [Header("Scene References")]
    public GameObject agentPrefab;
    public Transform agentsRoot;
    public Transform trashRoot;

    [Header("Playback")]
    public bool playOnStart = true;
    public bool loopPlayback;
    public bool paused;
    public float playbackSpeed = 1f;

    [Header("Overlay")]
    public bool showOverlay = true;
    public int overlayFontSize = 18;

    private readonly Dictionary<string, GameObject> spawnedAgents = new Dictionary<string, GameObject>();
    private readonly Dictionary<int, List<GameObject>> trashMarkersByRecordIndex = new Dictionary<int, List<GameObject>>();
    private ReplayRoot replayData;
    private float playbackTime;
    private int lastAppliedStepIndex = -1;
    private int lastHiddenTrashCount;
    private GUIStyle overlayStyle;

    private void Start()
    {
        if (playOnStart)
        {
            LoadReplay();
        }
    }

    private void Update()
    {
        if (replayData == null || replayData.history == null || replayData.history.Count < 2)
        {
            return;
        }

        HandleKeyboardInput();

        if (!paused)
        {
            playbackTime += Time.deltaTime * playbackSpeed;
        }

        float totalDuration = replayData.history[replayData.history.Count - 1].timeSeconds;
        if (playbackTime > totalDuration)
        {
            if (loopPlayback)
            {
                playbackTime = 0f;
                ResetTrashMarkers();
                ApplyReplayTrashVisibility();
                lastHiddenTrashCount = 0;
            }
            else
            {
                playbackTime = totalDuration;
            }
        }

        ApplyReplayAtTime(playbackTime);
    }

    [ContextMenu("Load Replay")]
    public void LoadReplay()
    {
        if (replayFiles != null && replayFiles.Length > 0 && activeReplayIndex >= 0 && activeReplayIndex < replayFiles.Length)
        {
            simulationResultJson = replayFiles[activeReplayIndex];
        }

        if (simulationResultJson == null || mapRenderer == null || agentPrefab == null)
        {
            Debug.LogWarning("PythonSimulationReplay requires simulationResultJson, mapRenderer, and agentPrefab.");
            return;
        }

        replayData = JsonUtility.FromJson<ReplayRoot>(simulationResultJson.text);
        if (replayData == null || replayData.history == null || replayData.history.Count == 0)
        {
            Debug.LogWarning("Failed to parse simulation replay JSON.");
            return;
        }

        if (agentsRoot == null)
        {
            agentsRoot = transform;
        }

        var trashLoader = FindAnyObjectByType<TrashMapLoader>();
        if (trashLoader != null)
        {
            trashLoader.LoadMarkers();
        }

        BuildTrashLookup();
        ApplyReplayTrashVisibility();
        string strategy = replayData.metadata != null ? replayData.metadata.strategy : "-";
        string localMode = replayData.metadata != null ? replayData.metadata.localCleanupSelectionMode : "-";
        float localRadius = replayData.metadata != null ? replayData.metadata.localCleanupRadiusMeters : 0f;
        Debug.Log($"[PythonSimulationReplay] loaded strategy={strategy}, localCleanup={localRadius:0.#}m/{localMode}, replayIndex={activeReplayIndex}, frames={replayData.history.Count}, agents={replayData.history[0].agentSnapshots.Count}, trashRecordLookups={trashMarkersByRecordIndex.Count}");
        SpawnReplayAgents();
        playbackTime = 0f;
        lastAppliedStepIndex = -1;
        lastHiddenTrashCount = 0;
        ResetTrashMarkers();
        ApplyReplayTrashVisibility();
        ApplyReplayAtTime(0f);
    }

    public void LoadReplayIndex(int index)
    {
        if (replayFiles == null || replayFiles.Length == 0)
        {
            return;
        }

        activeReplayIndex = Mathf.Clamp(index, 0, replayFiles.Length - 1);
        ResetTrashMarkers();
        LoadReplay();
    }

    private void SpawnReplayAgents()
    {
        ClearReplayAgents();
        var firstStep = replayData.history[0];
        if (firstStep.agentSnapshots == null)
        {
            return;
        }

        foreach (var snapshot in firstStep.agentSnapshots)
        {
            var go = Instantiate(agentPrefab, agentsRoot);
            go.name = snapshot.agentId;
            go.transform.localPosition = LatLonToLocalPosition(snapshot.latitude, snapshot.longitude);
            var spriteRenderer = go.GetComponent<SpriteRenderer>();
            if (spriteRenderer != null)
            {
                spriteRenderer.sortingOrder = 30;
            }
            spawnedAgents[snapshot.agentId] = go;
        }
    }

    private void ClearReplayAgents()
    {
        foreach (var pair in spawnedAgents)
        {
            if (pair.Value == null)
            {
                continue;
            }

            if (Application.isPlaying)
            {
                Destroy(pair.Value);
            }
            else
            {
                DestroyImmediate(pair.Value);
            }
        }

        spawnedAgents.Clear();

        if (agentsRoot != null)
        {
            for (int i = agentsRoot.childCount - 1; i >= 0; i--)
            {
                var child = agentsRoot.GetChild(i);
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
    }

    private void BuildTrashLookup()
    {
        trashMarkersByRecordIndex.Clear();
        if (trashRoot == null)
        {
            return;
        }

        foreach (Transform child in trashRoot)
        {
            var meta = child.GetComponent<TrashMarkerMeta>();
            if (meta == null || meta.trashRecordIndex < 0)
            {
                continue;
            }

            if (!trashMarkersByRecordIndex.TryGetValue(meta.trashRecordIndex, out var list))
            {
                list = new List<GameObject>();
                trashMarkersByRecordIndex[meta.trashRecordIndex] = list;
            }
            list.Add(child.gameObject);
        }
    }

    private void ResetTrashMarkers()
    {
        foreach (var pair in trashMarkersByRecordIndex)
        {
            foreach (var go in pair.Value)
            {
                if (go != null)
                {
                    go.SetActive(true);
                }
            }
        }
    }

    private void ApplyReplayTrashVisibility()
    {
        if (replayData == null)
        {
            return;
        }

        HashSet<int> activeRecords = null;
        if (replayData.activeTrashRecordIndices != null && replayData.activeTrashRecordIndices.Count > 0)
        {
            activeRecords = new HashSet<int>(replayData.activeTrashRecordIndices);
        }

        HashSet<int> excludedRecords = null;
        if (replayData.excludedTrashRecordIndices != null && replayData.excludedTrashRecordIndices.Count > 0)
        {
            excludedRecords = new HashSet<int>(replayData.excludedTrashRecordIndices);
        }

        foreach (var pair in trashMarkersByRecordIndex)
        {
            bool visible = true;
            if (activeRecords != null && !activeRecords.Contains(pair.Key))
            {
                visible = false;
            }
            if (excludedRecords != null && excludedRecords.Contains(pair.Key))
            {
                visible = false;
            }

            foreach (var go in pair.Value)
            {
                if (go != null)
                {
                    go.SetActive(visible);
                }
            }
        }
    }

    private void ApplyReplayAtTime(float timeSeconds)
    {
        int currentIndex = 0;
        while (currentIndex < replayData.history.Count - 1 && replayData.history[currentIndex + 1].timeSeconds <= timeSeconds)
        {
            currentIndex++;
        }

        int nextIndex = Mathf.Min(currentIndex + 1, replayData.history.Count - 1);
        var currentStep = replayData.history[currentIndex];
        var nextStep = replayData.history[nextIndex];
        float segmentDuration = Mathf.Max(0.0001f, nextStep.timeSeconds - currentStep.timeSeconds);
        float t = currentIndex == nextIndex ? 0f : Mathf.Clamp01((timeSeconds - currentStep.timeSeconds) / segmentDuration);

        if (currentIndex != lastAppliedStepIndex)
        {
            ApplyTrashCollection(currentStep);
            lastAppliedStepIndex = currentIndex;
        }
        ApplyAgentPositions(currentStep, nextStep, t);
    }

    private void ApplyTrashCollection(ReplayStep step)
    {
        if (step.collectedTrashIndices == null)
        {
            return;
        }

        int hiddenMarkers = 0;
        int missingRecords = 0;
        foreach (int recordIndex in step.collectedTrashIndices)
        {
            if (!trashMarkersByRecordIndex.TryGetValue(recordIndex, out var list))
            {
                missingRecords++;
                continue;
            }

            foreach (var go in list)
            {
                if (go != null)
                {
                    go.SetActive(false);
                    hiddenMarkers++;
                }
            }
        }

        if (hiddenMarkers > lastHiddenTrashCount)
        {
            Debug.Log($"[PythonSimulationReplay] collected records={step.collectedTrashIndices.Count}, hiddenMarkers={hiddenMarkers}, missingRecords={missingRecords}, time={step.timeSeconds:0}s");
            lastHiddenTrashCount = hiddenMarkers;
        }
    }

    private void ApplyAgentPositions(ReplayStep currentStep, ReplayStep nextStep, float t)
    {
        if (currentStep.agentSnapshots == null)
        {
            return;
        }

        var nextById = new Dictionary<string, ReplayAgentSnapshot>();
        if (nextStep.agentSnapshots != null)
        {
            foreach (var snapshot in nextStep.agentSnapshots)
            {
                nextById[snapshot.agentId] = snapshot;
            }
        }

        foreach (var snapshot in currentStep.agentSnapshots)
        {
            if (!spawnedAgents.TryGetValue(snapshot.agentId, out var go) || go == null)
            {
                continue;
            }

            var currentPos = LatLonToLocalPosition(snapshot.latitude, snapshot.longitude);
            Vector3 finalPos = currentPos;
            if (nextById.TryGetValue(snapshot.agentId, out var nextSnapshot))
            {
                var nextPos = LatLonToLocalPosition(nextSnapshot.latitude, nextSnapshot.longitude);
                finalPos = Vector3.Lerp(currentPos, nextPos, t);
            }

            go.transform.localPosition = finalPos;
        }
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
        return new Vector3(x, y, -0.1f);
    }

    private void HandleKeyboardInput()
    {
        if (WasPressed("space", KeyCode.Space))
        {
            paused = !paused;
        }
        if (WasPressed("r", KeyCode.R))
        {
            playbackTime = 0f;
            lastAppliedStepIndex = -1;
            lastHiddenTrashCount = 0;
            ResetTrashMarkers();
            ApplyReplayTrashVisibility();
            ApplyReplayAtTime(0f);
        }
        if (WasPressed("equals", KeyCode.Equals) || WasPressed("numpadPlus", KeyCode.KeypadPlus))
        {
            playbackSpeed = Mathf.Min(20f, playbackSpeed + 0.5f);
        }
        if (WasPressed("minus", KeyCode.Minus) || WasPressed("numpadMinus", KeyCode.KeypadMinus))
        {
            playbackSpeed = Mathf.Max(0.25f, playbackSpeed - 0.5f);
        }
        if (WasPressed("leftBracket", KeyCode.LeftBracket))
        {
            LoadReplayIndex(activeReplayIndex - 1);
        }
        if (WasPressed("rightBracket", KeyCode.RightBracket))
        {
            LoadReplayIndex(activeReplayIndex + 1);
        }
    }

    private bool WasPressed(string inputSystemKeyName, KeyCode legacyKey)
    {
#if ENABLE_INPUT_SYSTEM
        if (Keyboard.current == null)
        {
            return false;
        }

        switch (inputSystemKeyName)
        {
            case "space":
                return Keyboard.current.spaceKey.wasPressedThisFrame;
            case "r":
                return Keyboard.current.rKey.wasPressedThisFrame;
            case "equals":
                return Keyboard.current.equalsKey.wasPressedThisFrame;
            case "numpadPlus":
                return Keyboard.current.numpadPlusKey.wasPressedThisFrame;
            case "minus":
                return Keyboard.current.minusKey.wasPressedThisFrame;
            case "numpadMinus":
                return Keyboard.current.numpadMinusKey.wasPressedThisFrame;
            case "leftBracket":
                return Keyboard.current.leftBracketKey.wasPressedThisFrame;
            case "rightBracket":
                return Keyboard.current.rightBracketKey.wasPressedThisFrame;
            default:
                return false;
        }
#else
        return Input.GetKeyDown(legacyKey);
#endif
    }

    private void OnGUI()
    {
        if (!showOverlay || replayData == null || replayData.summary == null)
        {
            return;
        }

        if (overlayStyle == null)
        {
            overlayStyle = new GUIStyle(GUI.skin.box)
            {
                alignment = TextAnchor.UpperLeft,
                fontSize = overlayFontSize,
                richText = true,
                padding = new RectOffset(12, 12, 10, 10),
            };
        }

        string strategy = replayData.metadata != null ? replayData.metadata.strategy : "-";
        string distanceMode = replayData.metadata != null ? replayData.metadata.distanceMode : "-";
        string localMode = replayData.metadata != null ? replayData.metadata.localCleanupSelectionMode : "-";
        float localRadius = replayData.metadata != null ? replayData.metadata.localCleanupRadiusMeters : 0f;
        int frameCount = replayData.history != null ? replayData.history.Count : 0;
        string text =
            $"<b>Heuristic Replay</b>\n" +
            $"Strategy: {strategy} ({distanceMode})\n" +
            $"Local cleanup: {localRadius:0.#}m / {localMode}  Duplicate targets: {(replayData.metadata != null && replayData.metadata.allowDuplicateTargets ? "On" : "Off")}\n" +
            $"Time: {playbackTime:0}s / {replayData.summary.elapsedTimeSeconds:0}s  Speed: x{playbackSpeed:0.0}  {(paused ? "Paused" : "Playing")}\n" +
            $"Collection: {replayData.summary.collectionRate * 100f:0.0}%  Collected Mass: {replayData.summary.collectedTrashMass}\n" +
            $"Remaining: {replayData.summary.remainingTrashMass} mass / {replayData.summary.remainingTrashMass + replayData.summary.collectedTrashMass} mass\n" +
            $"Frames: {frameCount}  Controls: Space, R, +/-, [ ]";

        GUI.Box(new Rect(12f, 12f, 620f, 175f), text, overlayStyle);
    }
}
