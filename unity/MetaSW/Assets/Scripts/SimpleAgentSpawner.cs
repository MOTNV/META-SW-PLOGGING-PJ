using System.Collections.Generic;
using UnityEngine;

public class SimpleAgentSpawner : MonoBehaviour
{
    [Header("References")]
    public OSMGridGenerator gridGenerator;
    public GameObject agentPrefab;
    public Transform agentParent;

    [Header("Spawn Settings")]
    public int initialAgentCount = 20;
    public bool spawnOnStart = true;
    public bool clearExistingAgentsOnSpawn = true;
    public float spawnZOffset = -0.1f;

    private readonly List<GameObject> spawnedAgents = new List<GameObject>();

    private void Start()
    {
        if (spawnOnStart)
        {
            SpawnAgents();
        }
    }

    [ContextMenu("Spawn Agents")]
    public void SpawnAgents()
    {
        if (gridGenerator == null)
        {
            Debug.LogWarning("gridGenerator is not assigned.");
            return;
        }

        if (agentPrefab == null)
        {
            Debug.LogWarning("agentPrefab is not assigned.");
            return;
        }

        if (agentParent == null)
        {
            agentParent = transform;
        }

        if (clearExistingAgentsOnSpawn)
        {
            ClearAgents();
        }

        var walkableCells = gridGenerator.WalkableCells;
        if (walkableCells == null || walkableCells.Count == 0)
        {
            gridGenerator.GenerateGrid();
            walkableCells = gridGenerator.WalkableCells;
        }

        if (walkableCells == null || walkableCells.Count == 0)
        {
            Debug.LogWarning("No walkable cells available. Generate grid first.");
            return;
        }

        for (int i = 0; i < initialAgentCount; i++)
        {
            var cell = walkableCells[Random.Range(0, walkableCells.Count)];
            var agent = Instantiate(agentPrefab, agentParent);
            agent.name = $"Agent_{i:000}";
            agent.transform.localPosition = new Vector3(cell.localPosition.x, cell.localPosition.y, spawnZOffset);
            var spriteRenderer = agent.GetComponent<SpriteRenderer>();
            if (spriteRenderer != null)
            {
                spriteRenderer.sortingOrder = 30;
            }
            spawnedAgents.Add(agent);
        }

        Debug.Log($"[SimpleAgentSpawner] spawned {initialAgentCount} agents");
    }

    [ContextMenu("Clear Agents")]
    public void ClearAgents()
    {
        for (int i = spawnedAgents.Count - 1; i >= 0; i--)
        {
            if (spawnedAgents[i] == null)
            {
                continue;
            }

            if (Application.isPlaying)
            {
                Destroy(spawnedAgents[i]);
            }
            else
            {
                DestroyImmediate(spawnedAgents[i]);
            }
        }
        spawnedAgents.Clear();

        if (agentParent != null)
        {
            for (int i = agentParent.childCount - 1; i >= 0; i--)
            {
                var child = agentParent.GetChild(i);
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
}
