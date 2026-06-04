using UnityEngine;

public class TrashMarkerMeta : MonoBehaviour
{
    public string imagePath;
    public string timestamp;
    public string label;
    public int quantity;
    public int trashRecordIndex = -1;
    public string latitude;
    public string longitude;
    public string source;
    public int remainingQuantity = 1;
    public bool isCollected;

    public bool IsAvailableTarget => !isCollected && remainingQuantity > 0 && gameObject.activeInHierarchy;

    public void InitializeQuantity(int quantityValue)
    {
        remainingQuantity = Mathf.Max(1, quantityValue);
        isCollected = false;
    }

    public void MarkCollected()
    {
        isCollected = true;
        remainingQuantity = 0;
        gameObject.SetActive(false);
    }

    private void OnMouseDown()
    {
        Debug.Log(
            $"[TrashMarker] label={label}, quantity={quantity}, remaining={remainingQuantity}, image={imagePath}, time={timestamp}, lat={latitude}, lon={longitude}, source={source}"
        );
    }
}
