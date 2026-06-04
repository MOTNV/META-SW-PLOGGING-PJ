using System.Text;
using UnityEngine;

public class SimulationDebugOverlay : MonoBehaviour
{
    [Header("References")]
    public OSMGridGenerator gridGenerator;
    public Transform agentsRoot;
    public Transform trashRoot;
    public SimulationDisplayController displayController;
    public GreedyPloggingManager greedyManager;

    [Header("Display")]
    public bool showOverlay = true;
    public int fontSize = 18;
    public Vector2 startPosition = new Vector2(12f, 12f);
    public Vector2 boxSize = new Vector2(420f, 200f);

    private GUIStyle style;

    private void OnGUI()
    {
        if (!showOverlay)
        {
            return;
        }

        if (style == null)
        {
            style = new GUIStyle(GUI.skin.box)
            {
                alignment = TextAnchor.UpperLeft,
                fontSize = fontSize,
                richText = true,
                wordWrap = true,
                padding = new RectOffset(12, 12, 12, 12),
            };
        }

        var sb = new StringBuilder();
        sb.AppendLine("<b>Simulation Debug</b>");
        sb.AppendLine($"Display Mode: {GetDisplayModeText()}");
        sb.AppendLine($"Agents Visible: {IsRootActive(agentsRoot)}");
        sb.AppendLine($"Trash Visible: {IsRootActive(trashRoot)}");
        sb.AppendLine($"Spawned Agents: {GetChildCount(agentsRoot)}");
        sb.AppendLine($"Trash Markers: {GetChildCount(trashRoot)}");

        if (greedyManager != null)
        {
            sb.AppendLine($"Idle Agents: {greedyManager.idleAgentCount}");
            sb.AppendLine($"Moving Agents: {greedyManager.movingAgentCount}");
            sb.AppendLine($"Collecting Agents: {greedyManager.collectingAgentCount}");
            sb.AppendLine($"Remaining Trash Markers: {greedyManager.remainingTrashMarkers}");
            sb.AppendLine($"Remaining Trash Quantity: {greedyManager.remainingTrashQuantity}");
        }

        if (gridGenerator != null)
        {
            int totalCells = gridGenerator.Cells != null ? gridGenerator.Cells.Count : 0;
            int walkableCells = gridGenerator.WalkableCells != null ? gridGenerator.WalkableCells.Count : 0;
            int blockedCells = 0;
            if (gridGenerator.Cells != null)
            {
                foreach (var cell in gridGenerator.Cells)
                {
                    if (cell.blocked)
                    {
                        blockedCells++;
                    }
                }
            }

            sb.AppendLine($"Grid Cells: {totalCells}");
            sb.AppendLine($"Walkable Cells: {walkableCells}");
            sb.AppendLine($"Blocked Cells: {blockedCells}");
        }

        GUI.Box(new Rect(startPosition.x, startPosition.y, boxSize.x, boxSize.y), sb.ToString(), style);
    }

    private string GetDisplayModeText()
    {
        if (displayController == null)
        {
            return "-";
        }
        return displayController.displayMode.ToString();
    }

    private bool IsRootActive(Transform root)
    {
        return root != null && root.gameObject.activeInHierarchy;
    }

    private int GetChildCount(Transform root)
    {
        return root == null ? 0 : root.childCount;
    }
}
