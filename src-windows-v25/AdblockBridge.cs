using System.Runtime.InteropServices;

namespace MintWindows;

// The six JavascriptInterface methods in Android Mint's AdblockWebView$d.
// An explicit IDispatch surface avoids exposing reflection or host internals.
[ComVisible(true)]
[Guid("F9E685AD-106D-4ED3-908F-2E558BE3DB71")]
[InterfaceType(ComInterfaceType.InterfaceIsIDispatch)]
public interface IAdblockBridge
{
    [DispId(1)] bool getAddDomListener();
    [DispId(2)] string getElemhideSelectors();
    [DispId(3)] bool isElementsHidden();
    [DispId(4)] void setAddDomListener(bool value);
    [DispId(5)] void setElementsHidden(bool value);
    [DispId(6)] void setHideElementCount(int value);
}

[ComVisible(true)]
[Guid("5D48B013-6F55-4C76-BA2A-FCA788AA5A1B")]
[ClassInterface(ClassInterfaceType.None)]
[ComDefaultInterface(typeof(IAdblockBridge))]
public sealed class AdblockBridge : IAdblockBridge
{
    readonly Func<bool> allowed;
    bool listener=true, hidden;
    int hiddenCount;

    internal AdblockBridge(Func<bool> allowed) { this.allowed=allowed; }
    internal void Reset() { listener=true;hidden=false;hiddenCount=0; }
    bool Enabled { get { try{return allowed();}catch{return false;} } }
    public bool getAddDomListener() => Enabled && listener;
    public string getElemhideSelectors() => Enabled ? "[\".float-bar-main .fast-entry-item\",\"[data-mint17-ad]\"]" : "[]";
    public bool isElementsHidden() => Enabled && hidden;
    public void setAddDomListener(bool value) { if(Enabled)listener=value; }
    public void setElementsHidden(bool value) { if(Enabled)hidden=value; }
    public void setHideElementCount(int value) { if(Enabled)hiddenCount=Math.Clamp(value,0,1000000); }
}
