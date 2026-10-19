using System.Diagnostics;
using System.Reflection;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using Microsoft.Data.Sqlite;

namespace MintWindows;

internal static class Program
{
    internal static string Variant => "danill0";
    internal static string DataRoot => Path.Combine(Path.GetDirectoryName(Exe)!, "MintData");
    internal static string ConfigPath => Path.Combine(DataRoot, "settings.json");
    internal static string ProxyConfigPath => Path.Combine(Path.GetDirectoryName(Exe)!, "MintProxy.json");
    internal static string Exe => Environment.ProcessPath!;

    [STAThread]
    static void Main(string[] args)
    {
        ApplicationConfiguration.Initialize();
        if (args.Length == 2 && args[0] == "--reset" && int.TryParse(args[1], out int parent))
        {
            try { if(!Process.GetProcessById(parent).WaitForExit(20000)){MessageBox.Show("O navegador ainda está fechando. Aguarde e tente novamente.");return;} } catch (ArgumentException) { }
            catch { MessageBox.Show("Não foi possível aguardar o fechamento do navegador."); return; }
            bool cleared = false;
            for (int i = 0; i < 60; i++)
            {
                try { if (Directory.Exists(DataRoot)) Directory.Delete(DataRoot, true); cleared = true; break; }
                catch (IOException) { Thread.Sleep(500); }
                catch (UnauthorizedAccessException) { Thread.Sleep(500); }
            }
            if (!cleared) { MessageBox.Show("O Windows ainda está usando os dados. Feche o navegador e tente Limpar dados novamente.", "Limpeza não concluída"); return; }
        }
        using var mutex = new Mutex(true, "Local\\MintBrowserPortable_" + Convert.ToHexString(SHA256.HashData(Encoding.UTF8.GetBytes(Path.GetFullPath(DataRoot).ToUpperInvariant())))[..20], out bool first);
        if (!first) { MessageBox.Show("Esta versão do navegador já está aberta.", "Mint Windows"); return; }
        try { Directory.CreateDirectory(DataRoot); Application.Run(new BrowserForm()); }
        catch (Exception ex) { MessageBox.Show("Não foi possível abrir o navegador.\n" + ex.Message, "Mint Windows"); }
        finally { SqliteConnection.ClearAllPools(); }
    }

    internal static Settings LoadSettings()
    {
        try { return JsonSerializer.Deserialize<Settings>(File.ReadAllText(ConfigPath)) ?? new(); } catch { return new(); }
    }
    internal static void SaveSettings(Settings settings)
    {
        var temp = ConfigPath + ".tmp";
        File.WriteAllText(temp, JsonSerializer.Serialize(settings));
        File.Move(temp, ConfigPath, true);
    }
    internal static ProxySettings LoadProxySettings()
    {
        if(!File.Exists(ProxyConfigPath))return new();
        try { return JsonSerializer.Deserialize<ProxySettings>(File.ReadAllText(ProxyConfigPath)) ?? new(){Enabled=true}; }
        catch { return new(){Enabled=true}; }
    }
    internal static void SaveProxySettings(ProxySettings settings)
    {
        var temp=ProxyConfigPath+".tmp";
        File.WriteAllText(temp,JsonSerializer.Serialize(settings));
        File.Move(temp,ProxyConfigPath,true);
    }
    internal static string Script()
    {
        using var reader = new StreamReader(Assembly.GetExecutingAssembly().GetManifestResourceStream("mint-script.js")!);
        return reader.ReadToEnd();
    }
}

internal sealed class Settings
{
    public bool CodeEntered { get; set; }
}
