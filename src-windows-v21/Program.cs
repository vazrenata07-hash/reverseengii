using System.Diagnostics;
using System.Reflection;
using System.Text.Json;
using Microsoft.Data.Sqlite;

namespace MintWindows;

internal static class Program
{
    internal static string Variant => Assembly.GetExecutingAssembly().GetName().Name!.EndsWith("87654321") ? "87654321" : "danill0";
    internal static string DataRoot => Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "MintBrowserWindows", "v21-" + Variant);
    internal static string ConfigPath => Path.Combine(DataRoot, "settings.json");
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
        using var mutex = new Mutex(true, "Local\\MintBrowserWindowsV21_" + Variant, out bool first);
        if (!first) { MessageBox.Show("Esta versão do navegador já está aberta.", "Mint Windows"); return; }
        Directory.CreateDirectory(DataRoot);
        try { Application.Run(new BrowserForm()); }
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
    internal static string Script()
    {
        using var reader = new StreamReader(Assembly.GetExecutingAssembly().GetManifestResourceStream("mint-script.js")!);
        return reader.ReadToEnd();
    }
}

internal sealed class Settings
{
    public bool CodeEntered { get; set; }
    public string UserAgent { get; set; } = "";
}
