using UnityEngine;

public class GreedyPloggerAgent : MonoBehaviour
{
    public enum AgentState
    {
        Idle,
        Moving,
        Collecting
    }

    [Header("Stats")]
    public float moveSpeed = 1.8f;
    public float maxStamina = 100f;
    public float currentStamina = 100f;
    public int bagCapacity = 20;
    public int bagLoad;
    public float moveStaminaCostPerSecond = 0.8f;
    public float collectDurationPerItem = 0.35f;

    [Header("Runtime")]
    public AgentState state = AgentState.Idle;
    public TrashMarkerMeta currentTarget;
    public int collectedAmount;

    private float collectingTimer;

    public bool IsAvailable => state == AgentState.Idle && currentStamina > 0f && bagLoad < bagCapacity;

    public void AssignTarget(TrashMarkerMeta target)
    {
        if (target == null)
        {
            return;
        }

        currentTarget = target;
        collectingTimer = 0f;
        state = AgentState.Moving;
    }

    public void TickAgent(float deltaTime)
    {
        switch (state)
        {
            case AgentState.Idle:
                break;
            case AgentState.Moving:
                TickMoving(deltaTime);
                break;
            case AgentState.Collecting:
                TickCollecting(deltaTime);
                break;
        }
    }

    private void TickMoving(float deltaTime)
    {
        if (currentTarget == null || !currentTarget.IsAvailableTarget)
        {
            ResetToIdle();
            return;
        }

        Vector3 targetPosition = currentTarget.transform.localPosition;
        transform.localPosition = Vector3.MoveTowards(transform.localPosition, targetPosition, moveSpeed * deltaTime);
        currentStamina = Mathf.Max(0f, currentStamina - moveStaminaCostPerSecond * deltaTime);

        if (Vector3.Distance(transform.localPosition, targetPosition) <= 0.02f)
        {
            collectingTimer = currentTarget.remainingQuantity * collectDurationPerItem;
            state = AgentState.Collecting;
        }
    }

    private void TickCollecting(float deltaTime)
    {
        if (currentTarget == null || !currentTarget.IsAvailableTarget)
        {
            ResetToIdle();
            return;
        }

        collectingTimer -= deltaTime;
        if (collectingTimer > 0f)
        {
            return;
        }

        int collectedNow = Mathf.Min(currentTarget.remainingQuantity, Mathf.Max(0, bagCapacity - bagLoad));
        bagLoad += collectedNow;
        collectedAmount += collectedNow;
        currentTarget.MarkCollected();
        ResetToIdle();
    }

    private void ResetToIdle()
    {
        currentTarget = null;
        collectingTimer = 0f;
        state = AgentState.Idle;
    }
}
