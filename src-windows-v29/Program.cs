using System.Diagnostics;
using System.Reflection;
using System.Runtime.InteropServices;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using Microsoft.Data.Sqlite;

namespace MintWindows;

internal static class Program
{
    internal static string Variant => "danill0";
    internal static string Exe => Environment.ProcessPath!;
    internal static string AppRoot => Path.GetDirectoryName(Exe)!;
    internal static string SharedRoot => Path.Combine(AppRoot,"MintSettings");
    internal static string InstanceId { get; private set; } = "default";
    internal static string InstanceName => GetInstances().FirstOrDefault(item=>item.Id==InstanceId)?.Name ?? "Principal";
    internal static string WindowTitle => "Mint · "+InstanceName+" · V29";
    internal static string DataRoot => InstanceDataRoot(InstanceId);
    internal static string ConfigPath => Path.Combine(SharedRoot,"settings.json");
    internal static string ProxyConfigPath => Path.Combine(AppRoot,"MintProxy.json");
    static string CatalogPath => Path.Combine(SharedRoot,"instances.json");
    static string InstanceDataRoot(string id) => id=="default"?Path.Combine(AppRoot,"MintData"):Path.Combine(AppRoot,"MintInstances",id);
    static string LockName(string path) => "Local\\MintBrowserPortable_"+Convert.ToHexString(SHA256.HashData(Encoding.UTF8.GetBytes(Path.GetFullPath(path).ToUpperInvariant())))[..20];
    static bool ValidId(string id) => id=="default" || id.Length==32 && Guid.TryParseExact(id,"N",out _);

    [STAThread]
    static void Main(string[] args)
    {
        ApplicationConfiguration.Initialize();
        try
        {
            Directory.CreateDirectory(SharedRoot);
            var requested=Argument(args,"--instance");
            if(requested!=null)
            {
                if(!ValidId(requested) || !GetInstances().Any(item=>item.Id==requested))throw new InvalidOperationException("Instância inválida.");
                InstanceId=requested;
            }
            var reset=Argument(args,"--reset");
            if(reset!=null)
            {
                if(requested==null || !int.TryParse(reset,out int parent))throw new InvalidOperationException("Limpeza inválida.");
                if(!WaitForProcess(parent,20000))throw new InvalidOperationException("A instância ainda está fechando. Aguarde e tente novamente.");
                if(int.TryParse(Argument(args,"--webview-pid"),out int webview) && webview>0 && !WaitForProcess(webview,20000))
                    throw new InvalidOperationException("O motor ainda está fechando. Nenhum dado foi apagado.");
            }
            string scope=requested==null?Path.Combine(AppRoot,"MintLauncher"):DataRoot;
            using var mutex=new Mutex(true,LockName(scope),out bool first);
            if(!first)
            {
                if(!FocusWindow(requested==null?"Mint Browser · Instâncias":WindowTitle))
                    MessageBox.Show("Esta instância já está aberta. Feche a versão anterior antes de abrir a mesma sessão.","Mint");
                return;
            }
            if(reset!=null)
            {
                bool cleared=false;
                for(int i=0;i<60;i++)
                {
                    try { if(Directory.Exists(DataRoot))Directory.Delete(DataRoot,true);cleared=true;break; }
                    catch(IOException){Thread.Sleep(500);}
                    catch(UnauthorizedAccessException){Thread.Sleep(500);}
                }
                if(!cleared)throw new InvalidOperationException("O Windows ainda está usando os dados desta instância. Nenhuma outra sessão foi alterada.");
            }
            if(!File.Exists(ConfigPath))SaveSettings(LoadSettings());
            if(requested==null)Application.Run(new LauncherForm());
            else
            {
                Directory.CreateDirectory(DataRoot);
                Application.Run(new BrowserForm());
            }
        }
        catch(Exception ex){MessageBox.Show("Não foi possível abrir o Mint.\n"+ex.Message,"Mint Windows");}
        finally { SqliteConnection.ClearAllPools(); }
    }

    static string? Argument(string[] args,string key)
    {
        int index=Array.IndexOf(args,key);
        return index>=0 && index+1<args.Length?args[index+1]:null;
    }
    static bool WaitForProcess(int id,int milliseconds)
    {
        if(id<=0 || id==Environment.ProcessId)return false;
        try { using var process=Process.GetProcessById(id);return process.WaitForExit(milliseconds); }
        catch(ArgumentException){return true;}
    }

    internal static IReadOnlyList<BrowserInstance> GetInstances()
    {
        var result=new List<BrowserInstance>{new("default","Principal (dados existentes)")};
        if(!File.Exists(CatalogPath))return result;
        var saved=JsonSerializer.Deserialize<List<BrowserInstance>>(File.ReadAllText(CatalogPath)) ?? new();
        foreach(var item in saved)
            if(item!=null && item.Id!="default" && ValidId(item.Id) && !string.IsNullOrWhiteSpace(item.Name) &&
               item.Name.Length<=60 && !item.Name.Any(char.IsControl) && !result.Any(existing=>existing.Id==item.Id))result.Add(item);
        return result;
    }

    internal static BrowserInstance CreateInstance(string name)
    {
        name=name.Trim();
        if(name.Length is <1 or >60 || name.Any(char.IsControl))throw new ArgumentException("Nome inválido.");
        using var gate=new Mutex(false,LockName(CatalogPath));
        bool acquired=false;
        try
        {
            try { acquired=gate.WaitOne(5000); } catch(AbandonedMutexException){acquired=true;}
            if(!acquired)throw new IOException("A lista de instâncias está em uso.");
            var all=GetInstances().ToList();
            if(all.Any(item=>string.Equals(item.Name,name,StringComparison.OrdinalIgnoreCase)))throw new ArgumentException("Nome já usado.");
            var created=new BrowserInstance(Guid.NewGuid().ToString("N"),name);
            all.Add(created);
            SaveJson(CatalogPath,all.Where(item=>item.Id!="default").ToArray());
            return created;
        }
        finally { if(acquired)gate.ReleaseMutex(); }
    }

    internal static void LaunchInstance(string id)
    {
        if(!ValidId(id) || !GetInstances().Any(item=>item.Id==id))throw new ArgumentException("Instância inválida.");
        if(IsInstanceRunning(id))
        {
            var name=GetInstances().First(item=>item.Id==id).Name;
            if(!FocusWindow("Mint · "+name+" · V29"))MessageBox.Show("A instância já está aberta. Feche a versão anterior se estiver usando os mesmos dados.","Mint");
            return;
        }
        var start=new ProcessStartInfo(Exe){UseShellExecute=false,WorkingDirectory=AppRoot};
        start.ArgumentList.Add("--instance");start.ArgumentList.Add(id);
        Process.Start(start)?.Dispose();
    }
    internal static bool IsInstanceRunning(string id)
    {
        if(!ValidId(id))return false;
        if(!Mutex.TryOpenExisting(LockName(InstanceDataRoot(id)),out var mutex))return false;
        mutex.Dispose();return true;
    }

    internal static Settings LoadSettings()
    {
        string path=File.Exists(ConfigPath)?ConfigPath:Path.Combine(AppRoot,"MintData","settings.json");
        try { return JsonSerializer.Deserialize<Settings>(File.ReadAllText(path)) ?? new(); } catch { return new(); }
    }
    internal static void SaveSettings(Settings settings) => SaveJson(ConfigPath,settings);
    internal static ProxySettings LoadProxySettings()
    {
        if(!File.Exists(ProxyConfigPath))return new();
        try { return JsonSerializer.Deserialize<ProxySettings>(File.ReadAllText(ProxyConfigPath)) ?? new(){Enabled=true}; }
        catch { return new(){Enabled=true}; }
    }
    internal static void SaveProxySettings(ProxySettings settings) => SaveJson(ProxyConfigPath,settings);
    static void SaveJson<T>(string path,T value)
    {
        Directory.CreateDirectory(Path.GetDirectoryName(path)!);
        string temp=path+"."+Guid.NewGuid().ToString("N")+".tmp";
        try { File.WriteAllText(temp,JsonSerializer.Serialize(value));File.Move(temp,path,true); }
        finally { if(File.Exists(temp))File.Delete(temp); }
    }
    internal static string Script()
    {
        using var reader=new StreamReader(Assembly.GetExecutingAssembly().GetManifestResourceStream("mint-script.js")!);
        return reader.ReadToEnd();
    }
    static bool FocusWindow(string title)
    {
        var handle=FindWindow(null,title);
        if(handle==IntPtr.Zero)return false;
        ShowWindow(handle,9);SetForegroundWindow(handle);return true;
    }
    [DllImport("user32.dll",CharSet=CharSet.Unicode)] static extern IntPtr FindWindow(string? className,string windowName);
    [DllImport("user32.dll")] static extern bool ShowWindow(IntPtr window,int command);
    [DllImport("user32.dll")] static extern bool SetForegroundWindow(IntPtr window);
}

public sealed record BrowserInstance(string Id,string Name);
internal sealed class Settings { public bool CodeEntered { get; set; } }
