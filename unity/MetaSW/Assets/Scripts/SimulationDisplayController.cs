using UnityEngine;
#if ENABLE_INPUT_SYSTEM
using UnityEngine.InputSystem;
#endif

public class SimulationDisplayController : MonoBehaviour
{
    public enum DisplayMode
    {
        AgentsOnly,
        TrashOnly,
        AgentsAndTrash
    }

    [Header("References")]
    public GameObject agentsRoot;
    public GameObject trashRoot;

    [Header("Display")]
    public DisplayMode displayMode = DisplayMode.AgentsAndTrash;
    public bool applyOnStart = true;
    public bool enableKeyboardShortcuts = true;

    private void Start()
    {
        if (applyOnStart)
        {
            ApplyDisplayMode();
        }
    }

    private void Update()
    {
        if (!enableKeyboardShortcuts)
        {
            return;
        }

        if (PressedDigit1())
        {
            displayMode = DisplayMode.AgentsOnly;
            ApplyDisplayMode();
        }
        else if (PressedDigit2())
        {
            displayMode = DisplayMode.TrashOnly;
            ApplyDisplayMode();
        }
        else if (PressedDigit3())
        {
            displayMode = DisplayMode.AgentsAndTrash;
            ApplyDisplayMode();
        }
    }

    private bool PressedDigit1()
    {
#if ENABLE_INPUT_SYSTEM
        return Keyboard.current != null && Keyboard.current.digit1Key.wasPressedThisFrame;
#else
        return Input.GetKeyDown(KeyCode.Alpha1);
#endif
    }

    private bool PressedDigit2()
    {
#if ENABLE_INPUT_SYSTEM
        return Keyboard.current != null && Keyboard.current.digit2Key.wasPressedThisFrame;
#else
        return Input.GetKeyDown(KeyCode.Alpha2);
#endif
    }

    private bool PressedDigit3()
    {
#if ENABLE_INPUT_SYSTEM
        return Keyboard.current != null && Keyboard.current.digit3Key.wasPressedThisFrame;
#else
        return Input.GetKeyDown(KeyCode.Alpha3);
#endif
    }

    [ContextMenu("Apply Display Mode")]
    public void ApplyDisplayMode()
    {
        if (agentsRoot == null || trashRoot == null)
        {
            Debug.LogWarning("SimulationDisplayController requires agentsRoot and trashRoot.");
            return;
        }

        switch (displayMode)
        {
            case DisplayMode.AgentsOnly:
                agentsRoot.SetActive(true);
                trashRoot.SetActive(false);
                break;
            case DisplayMode.TrashOnly:
                agentsRoot.SetActive(false);
                trashRoot.SetActive(true);
                break;
            case DisplayMode.AgentsAndTrash:
                agentsRoot.SetActive(true);
                trashRoot.SetActive(true);
                break;
        }
    }
}
