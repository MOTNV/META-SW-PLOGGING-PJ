using System.Collections.Generic;
using UnityEngine;

public class GreedyPloggingManager : MonoBehaviour
{
    [Header("References")]
    public Transform agentsRoot;
    public Transform trashRoot;

    [Header("Greedy Scoring")]
    public float distanceWeight = 1f;
    public float quantityWeight = 1.5f;
    public bool assignOnStart = true;

    [Header("Runtime Debug")]
    public int idleAgentCount;
    public int movingAgentCount;
    public int collectingAgentCount;
    public int remainingTrashMarkers;
    public int remainingTrashQuantity;

    private readonly List<GreedyPloggerAgent> agents = new List<GreedyPloggerAgent>();
    private readonly List<TrashMarkerMeta> trashMarkers = new List<TrashMarkerMeta>();

    private void Start()
    {
        RefreshSceneReferences();
        if (assignOnStart)
        {
            AssignIdleAgents();
        }
    }

    private void Update()
    {
        TickAgents(Time.deltaTime);
        AssignIdleAgents();
        UpdateRuntimeDebug();
    }

    [ContextMenu("Refresh Scene References")]
    public void RefreshSceneReferences()
    {
        agents.Clear();
        trashMarkers.Clear();

        if (agentsRoot != null)
        {
            foreach (Transform child in agentsRoot)
            {
                var agent = child.GetComponent<GreedyPloggerAgent>();
                if (agent == null)
                {
                    agent = child.gameObject.AddComponent<GreedyPloggerAgent>();
                }
                agents.Add(agent);
            }
        }

        if (trashRoot != null)
        {
            foreach (Transform child in trashRoot)
            {
                var marker = child.GetComponent<TrashMarkerMeta>();
                if (marker != null)
                {
                    trashMarkers.Add(marker);
                }
            }
        }
    }

    [ContextMenu("Assign Idle Agents")]
    public void AssignIdleAgents()
    {
        if (agentsRoot == null || trashRoot == null)
        {
            return;
        }

        RefreshMarkersIfNeeded();

        foreach (var agent in agents)
        {
            if (agent == null || !agent.IsAvailable)
            {
                continue;
            }

            TrashMarkerMeta bestTarget = FindBestTarget(agent);
            if (bestTarget != null)
            {
                agent.AssignTarget(bestTarget);
            }
        }
    }

    private void TickAgents(float deltaTime)
    {
        RefreshAgentsIfNeeded();
        foreach (var agent in agents)
        {
            if (agent == null)
            {
                continue;
            }

            agent.TickAgent(deltaTime);
        }
    }

    private TrashMarkerMeta FindBestTarget(GreedyPloggerAgent agent)
    {
        TrashMarkerMeta bestTarget = null;
        float bestScore = float.NegativeInfinity;

        foreach (var marker in trashMarkers)
        {
            if (marker == null || !marker.IsAvailableTarget)
            {
                continue;
            }

            float distance = Vector3.Distance(agent.transform.localPosition, marker.transform.localPosition);
            float score = quantityWeight * Mathf.Max(1, marker.remainingQuantity) - distanceWeight * distance;

            if (score > bestScore)
            {
                bestScore = score;
                bestTarget = marker;
            }
        }

        return bestTarget;
    }

    private void UpdateRuntimeDebug()
    {
        idleAgentCount = 0;
        movingAgentCount = 0;
        collectingAgentCount = 0;
        remainingTrashMarkers = 0;
        remainingTrashQuantity = 0;

        foreach (var agent in agents)
        {
            if (agent == null)
            {
                continue;
            }

            switch (agent.state)
            {
                case GreedyPloggerAgent.AgentState.Idle:
                    idleAgentCount++;
                    break;
                case GreedyPloggerAgent.AgentState.Moving:
                    movingAgentCount++;
                    break;
                case GreedyPloggerAgent.AgentState.Collecting:
                    collectingAgentCount++;
                    break;
            }
        }

        foreach (var marker in trashMarkers)
        {
            if (marker == null || !marker.IsAvailableTarget)
            {
                continue;
            }

            remainingTrashMarkers++;
            remainingTrashQuantity += Mathf.Max(1, marker.remainingQuantity);
        }
    }

    private void RefreshAgentsIfNeeded()
    {
        if (agentsRoot == null)
        {
            return;
        }

        if (agents.Count == agentsRoot.childCount)
        {
            return;
        }

        RefreshSceneReferences();
    }

    private void RefreshMarkersIfNeeded()
    {
        if (trashRoot == null)
        {
            return;
        }

        if (trashMarkers.Count == trashRoot.childCount)
        {
            return;
        }

        RefreshSceneReferences();
    }
}
