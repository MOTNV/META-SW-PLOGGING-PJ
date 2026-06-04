using System.IO;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;

public static class PloggingReplaySceneConfigurator
{
    private const string ScenePath = "Assets/Scenes/SampleScene.unity";

    [MenuItem("Plogging/Configure Replay Scene")]
    public static void ConfigureActiveScene()
    {
        ConfigureScene(false);
    }

    [MenuItem("Plogging/Configure And Save Replay Scene")]
    public static void ConfigureAndSaveActiveScene()
    {
        ConfigureScene(true);
    }

    public static void ConfigureAndSaveDefaultScene()
    {
        EditorSceneManager.OpenScene(ScenePath);
        ConfigureScene(true);
    }

    private static void ConfigureScene(bool saveScene)
    {
        var mapBackground = GameObject.Find("MapBackground");
        var agents = GameObject.Find("Agents");
        var markers = GameObject.Find("Markers");

        if (mapBackground == null || agents == null || markers == null)
        {
            Debug.LogError("Scene must contain MapBackground, Agents, and Markers objects.");
            return;
        }

        var replayObject = GameObject.Find("PythonSimulationReplay");
        if (replayObject == null)
        {
            replayObject = new GameObject("PythonSimulationReplay");
        }

        var replay = replayObject.GetComponent<PythonSimulationReplay>();
        if (replay == null)
        {
            replay = replayObject.AddComponent<PythonSimulationReplay>();
        }

        replay.mapRenderer = mapBackground.GetComponent<SpriteRenderer>();
        replay.agentsRoot = agents.transform;
        replay.trashRoot = markers.transform;
        replay.agentPrefab = AssetDatabase.LoadAssetAtPath<GameObject>("Assets/Prefabs/AgentMarker.prefab");
        replay.replayFiles = new[]
        {
            LoadReplay("unity_replay_random.json"),
            LoadReplay("unity_replay_trash_priority.json"),
            LoadReplay("unity_replay_uniform.json"),
        };
        replay.activeReplayIndex = 0;
        replay.simulationResultJson = replay.replayFiles[0];
        replay.playOnStart = true;
        replay.loopPlayback = false;
        replay.paused = false;
        replay.playbackSpeed = 4f;
        replay.showOverlay = true;

        var trashLoader = Object.FindFirstObjectByType<TrashMapLoader>();
        if (trashLoader != null)
        {
            var simpleZones = AssetDatabase.LoadAssetAtPath<TextAsset>("Assets/Data/simple_zones.json");
            if (simpleZones != null)
            {
                trashLoader.mergedRecordsJson = simpleZones;
            }
            trashLoader.baseMarkerScale = 0.04f;
            trashLoader.quantityScaleStep = 0.0025f;
            trashLoader.maxMarkerScale = 0.065f;
            trashLoader.markerOffsetStep = 0.012f;
            trashLoader.clearExistingMarkersOnLoad = true;
            trashLoader.loadOnStart = false;
            trashLoader.enabled = true;
        }

        var displayController = Object.FindFirstObjectByType<SimulationDisplayController>();
        if (displayController != null)
        {
            displayController.displayMode = SimulationDisplayController.DisplayMode.AgentsAndTrash;
            displayController.applyOnStart = true;
            displayController.enabled = true;
        }

        var greedyManager = Object.FindFirstObjectByType<GreedyPloggingManager>();
        if (greedyManager != null)
        {
            greedyManager.enabled = false;
        }

        var spawner = Object.FindFirstObjectByType<SimpleAgentSpawner>();
        if (spawner != null)
        {
            spawner.spawnOnStart = false;
        }

        EditorUtility.SetDirty(replayObject);
        if (greedyManager != null)
        {
            EditorUtility.SetDirty(greedyManager);
        }
        if (trashLoader != null)
        {
            EditorUtility.SetDirty(trashLoader);
        }
        if (displayController != null)
        {
            EditorUtility.SetDirty(displayController);
        }
        if (spawner != null)
        {
            EditorUtility.SetDirty(spawner);
        }

        if (saveScene)
        {
            EditorSceneManager.SaveScene(EditorSceneManager.GetActiveScene());
        }

        Debug.Log("Configured PythonSimulationReplay with Unity replay JSON files.");
    }

    private static TextAsset LoadReplay(string fileName)
    {
        string path = Path.Combine("Assets/Data", fileName).Replace("\\", "/");
        var asset = AssetDatabase.LoadAssetAtPath<TextAsset>(path);
        if (asset == null)
        {
            Debug.LogError($"Missing replay JSON: {path}");
        }
        return asset;
    }
}
