using System.Diagnostics;
using System.Text.Json;
using System.Text.RegularExpressions;
using Microsoft.Web.WebView2.Core;
using Microsoft.Web.WebView2.WinForms;

namespace MintWindows;

internal sealed class BrowserForm : Form
{
    readonly TabControl tabs = new() { Dock = DockStyle.Fill };
    readonly ToolStrip toolbar = new() { GripStyle = ToolStripGripStyle.Hidden, Dock = DockStyle.Top };
    readonly ToolStripTextBox address = new() { AutoSize = false, Width = 260 };
    readonly ToolStripStatusLabel status = new() { Text = "Iniciando…", Spring = true, TextAlign = ContentAlignment.MiddleLeft };
    readonly Settings settings = Program.LoadSettings();
    readonly Ledger ledger = new();
    readonly System.Windows.Forms.Timer resizeTimer = new() { Interval = 250 };
    CoreWebView2Environment? environment;
    string script = "", chromeVersion = "131.0.0.0";
    bool closing, exitReady, resetting;
    WebView2? Current => tabs.SelectedTab?.Controls.OfType<WebView2>().FirstOrDefault();

    internal BrowserForm()
    {
        Text = "Mint Portable · V25 · " + Program.Variant;
        Size = new(520, 940); MinimumSize = new(380, 560); StartPosition = FormStartPosition.CenterScreen;
        var back = new ToolStripButton("‹"); back.Click += (_,_) => {if(Current?.CanGoBack==true)Current.GoBack();};
        var forward = new ToolStripButton("›"); forward.Click += (_,_) => {if(Current?.CanGoForward==true)Current.GoForward();};
        var reload = new ToolStripButton("↻"); reload.Click += (_,_) => Current?.Reload();
        var home = new ToolStripButton("⌂"); home.Click += (_,_) => Navigate("https://888pg.cc/");
        var add = new ToolStripButton("+");add.Click += async (_,_) => await AddTabAsync("https://888pg.cc/");
        var menu = new ToolStripDropDownButton("⋮") { Alignment = ToolStripItemAlignment.Right };
        menu.DropDownItems.Add("Nova aba", null, async (_,_) => await AddTabAsync("https://888pg.cc/"));
        menu.DropDownItems.Add("Fechar aba", null, (_,_) => CloseTab());
        menu.DropDownItems.Add(new ToolStripSeparator());
        menu.DropDownItems.Add("Limpar dados e reiniciar", null, (_,_) => ResetAll());
        menu.DropDownItems.Add("User agent…", null, (_,_) => EditUserAgent());
        menu.DropDownItems.Add("Ferramentas de desenvolvedor", null, (_,_) => Current?.CoreWebView2?.OpenDevToolsWindow());
        menu.DropDownItems.Add("Sobre", null, (_,_) => MessageBox.Show("Mint Portable V25\nPerfil: Samsung Galaxy A53 · Android 13\nMotor: Microsoft Edge WebView2\nSenha de login: "+Program.Variant+"\nPIN configurado: 232691\n\nHistórico e contador: JDB Mines 9014.\nDados locais: "+Program.DataRoot,"Sobre",MessageBoxButtons.OK,MessageBoxIcon.Information));
        toolbar.Items.AddRange([back,forward,reload,home,address,add,menu]);
        var bar = new StatusStrip();bar.Items.Add(status);
        Controls.Add(tabs);Controls.Add(toolbar);Controls.Add(bar);
        tabs.SelectedIndexChanged += (_,_) => UpdateNavigation();
        address.KeyDown += (_,e) => {if(e.KeyCode==Keys.Enter){e.SuppressKeyPress=true;Navigate(address.Text);}};
        Resize += (_,_) => {address.Width=Math.Max(100,toolbar.Width-210);resizeTimer.Stop();resizeTimer.Start();};
        resizeTimer.Tick += async (_,_) => {resizeTimer.Stop();foreach(TabPage page in tabs.TabPages)foreach(var browser in page.Controls.OfType<WebView2>())await SizeProfileAsync(browser);};
        Shown += async (_,_) => await StartAsync();
        FormClosing += async (_,e) =>
        {
            if(exitReady)return;
            e.Cancel=true;if(closing)return;closing=true;Enabled=false;resizeTimer.Stop();
            try{await ledger.AccessAsync();}catch{}
            foreach(TabPage page in tabs.TabPages)foreach(var browser in page.Controls.OfType<WebView2>())browser.Dispose();
            exitReady=true;Close();
        };
    }

    async Task StartAsync()
    {
        try
        {
            // Keep the user's explicit certificate compatibility setting from Android.
            var options = new CoreWebView2EnvironmentOptions("--ignore-certificate-errors --autoplay-policy=no-user-gesture-required") { Language = "pt-BR" };
            environment = await CoreWebView2Environment.CreateAsync(null,Path.Combine(Program.DataRoot,"WebView2"),options);
            chromeVersion = Regex.Match(environment.BrowserVersionString,@"\d+\.\d+\.\d+\.\d+").Value;
            if (chromeVersion.Length == 0) chromeVersion = "131.0.0.0";
            script = Program.Script().Replace("__MINT_CHROME_VERSION__",chromeVersion);
            var url = "https://888pg.cc/";
            if (!settings.CodeEntered)
            {
                using var dialog = new InputDialog("Código de acesso", "Digite 0 para abrir o site ou o código de indicação.", "0",
                    value => value == "0" || Regex.IsMatch(value,@"^[0-9]{7,}$") ? null : "Use 0 ou um código com pelo menos 7 dígitos.");
                if (dialog.ShowDialog(this) != DialogResult.OK) {Close();return;}
                if (dialog.Input.Text.Trim() != "0") url = "https://888pg.cc/home/register?id=" + dialog.Input.Text.Trim();
                settings.CodeEntered=true;Program.SaveSettings(settings);
            }
            await AddTabAsync(url);
        }
        catch (WebView2RuntimeNotFoundException)
        {
            status.Text="É necessário instalar Microsoft Edge WebView2 Runtime.";
            if(MessageBox.Show("Instale o Microsoft Edge WebView2 Runtime para abrir este navegador. Abrir a página oficial de instalação?","WebView2 necessário",MessageBoxButtons.YesNo)==DialogResult.Yes)
                Process.Start(new ProcessStartInfo("https://developer.microsoft.com/microsoft-edge/webview2/"){UseShellExecute=true});
        }
        catch(Exception ex){status.Text="Não foi possível iniciar.";MessageBox.Show(ex.Message,"Mint Windows");}
    }

    string UserAgent => settings.UserAgent.Length>0 ? settings.UserAgent : "Mozilla/5.0 (Linux; U; Android 13; pt-br; SM-A536B Build/TP1A.220624.014) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Mobile Safari/537.36 XiaoMi/Mint Browser/3.9.3";

    async Task<WebView2?> AddTabAsync(string? url)
    {
        if(environment==null||closing)return null;
        var page=new TabPage("Nova aba");var browser=new WebView2{Dock=DockStyle.Fill,DefaultBackgroundColor=Color.White};
        page.Controls.Add(browser);tabs.TabPages.Add(page);tabs.SelectedTab=page;
        try
        {
            await browser.EnsureCoreWebView2Async(environment);
            var core=browser.CoreWebView2;
            core.Settings.UserAgent=UserAgent;core.Settings.AreDevToolsEnabled=true;
            core.Settings.IsWebMessageEnabled=true;core.Settings.AreHostObjectsAllowed=true;
            var nativeBridge=new AdblockBridge(()=>SiteUrl(core.Source));
            core.AddHostObjectToScript("mintAdblock",nativeBridge);
            core.Settings.IsPasswordAutosaveEnabled=false;core.Settings.IsGeneralAutofillEnabled=false;
            await core.AddScriptToExecuteOnDocumentCreatedAsync(script);
            core.FrameCreated += (_,e) => BindFrame(core,e.Frame);
            core.ServerCertificateErrorDetected += (_,e) => e.Action=CoreWebView2ServerCertificateErrorAction.AlwaysAllow;
            core.NavigationStarting += (_,e) => {nativeBridge.Reset();if(!HttpUrl(e.Uri)&&e.Uri!="about:blank"){e.Cancel=true;return;}if(browser==Current)status.Text="Carregando…";};
            core.SourceChanged += (_,_) => UpdateNavigation();
            core.HistoryChanged += (_,_) => UpdateNavigation();
            core.DocumentTitleChanged += (_,_) => {string title=core.DocumentTitle;page.Text=title.Length>24?title[..24]+"…":title;};
            core.NavigationCompleted += (_,e) => {if(browser==Current)status.Text=e.IsSuccess?"Pronto · Perfil Android":"Carregamento: "+e.WebErrorStatus;};
            core.NewWindowRequested += async (_,e) =>
            {
                using var deferral=e.GetDeferral();e.Handled=true;
                if(!HttpUrl(e.Uri)&&e.Uri!="about:blank")return;
                var child=await AddTabAsync(null);if(child?.CoreWebView2!=null)e.NewWindow=child.CoreWebView2;
            };
            core.DownloadStarting += (_,e) =>
            {
                using var dialog=new SaveFileDialog {FileName=Path.GetFileName(e.ResultFilePath),Filter="Todos os arquivos|*.*",OverwritePrompt=true};
                if(dialog.ShowDialog(this)==DialogResult.OK)e.ResultFilePath=dialog.FileName;else e.Cancel=true;
            };
            browser.KeyDown += (_,e) =>
            {
                if(e.KeyCode==Keys.F12){e.Handled=true;core.OpenDevToolsWindow();}
                if(e.KeyCode==Keys.L&&e.Control){e.Handled=true;address.Focus();address.SelectAll();}
            };
            await ApplyProfileAsync(browser);
            if(url!=null)core.Navigate(url);
            return browser;
        }
        catch(Exception ex){status.Text="Não foi possível abrir a aba.";MessageBox.Show(ex.Message,"Mint Windows");browser.Dispose();tabs.TabPages.Remove(page);page.Dispose();return null;}
    }

    async Task ApplyProfileAsync(WebView2 browser)
    {
        try
        {
            // Omitting metadata suppresses Chromium Client Hint identification.
            // Android Browser 4.0 uses the legacy UA, not Chrome WebView brands.
            await browser.CoreWebView2.CallDevToolsProtocolMethodAsync("Emulation.setUserAgentOverride",JsonSerializer.Serialize(new{
                userAgent=UserAgent,acceptLanguage="pt-BR,pt,en-US,en",platform="Linux armv8l"
            }));
            await browser.CoreWebView2.CallDevToolsProtocolMethodAsync("Emulation.setTouchEmulationEnabled","{\"enabled\":true,\"maxTouchPoints\":5}");
            await SizeProfileAsync(browser);
        }
        catch{status.Text="Perfil Android aplicado por user agent; emulação limitada neste WebView2.";}
    }

    async Task SizeProfileAsync(WebView2 browser)
    {
        if(browser.IsDisposed||browser.CoreWebView2==null||browser.Width<=0)return;
        try
        {
            // Let WebView2 use the actual host client area at every DPI and size.
            // A fixed mobile width previously left an unused strip in the window.
            await browser.CoreWebView2.CallDevToolsProtocolMethodAsync("Emulation.clearDeviceMetricsOverride","{}");
        }catch{}
    }

    void BindFrame(CoreWebView2 owner,CoreWebView2Frame frame)
    {
        frame.FrameCreated += (_,e) => BindFrame(owner,e.Frame);
        frame.WebMessageReceived += async (_,e) => await HandleMessageAsync(owner,e.Source,e.WebMessageAsJson,frame.PostWebMessageAsJson);
    }

    async Task HandleMessageAsync(CoreWebView2 owner,string source,string json,Action<string> reply)
    {
        if(closing||json.Length>2048||!SiteUrl(owner.Source)||!GameUrl(source))return;
        string? id=null;
        try
        {
            using var doc=JsonDocument.Parse(json);var body=doc.RootElement;
            if(body.GetProperty("channel").GetString()!="mint-counter-windows-v21")return;
            id=body.GetProperty("id").GetString();if(id==null||id.Length>100)return;
            var action=body.GetProperty("action").GetString();long total;
            if(action=="total")total=await ledger.AccessAsync();
            else if(action=="record")
            {
                string? game=body.GetProperty("game").GetString(),round=body.GetProperty("round").GetString();long milli=body.GetProperty("milli").GetInt64();
                if(game!="jdb-mines-9014"||round==null||!Regex.IsMatch(round,@"^[0-9]{1,24}$")||milli<=0||milli>1000000000L)throw new InvalidOperationException();
                total=await ledger.AccessAsync(round,milli);
            }
            else return;
            if(!closing)reply(JsonSerializer.Serialize(new{channel="mint-counter-windows-v21",id,result=new{milli=total}}));
        }
        catch{try{if(id!=null&&!closing)reply(JsonSerializer.Serialize(new{channel="mint-counter-windows-v21",id,result=new{error=true}}));}catch{}}
    }

    static bool HttpUrl(string url)=>Uri.TryCreate(url,UriKind.Absolute,out var u)&&(u.Scheme=="https"||u.Scheme=="http");
    static bool SiteUrl(string url)=>HttpUrl(url)&&Uri.TryCreate(url,UriKind.Absolute,out var u)&&(u.Host.Equals("888pg.cc",StringComparison.OrdinalIgnoreCase)||u.Host.EndsWith(".888pg.cc",StringComparison.OrdinalIgnoreCase));
    static bool GameUrl(string url)=>HttpUrl(url)&&Uri.TryCreate(url,UriKind.Absolute,out var u)&&(u.Host.Equals("brteachcor.com",StringComparison.OrdinalIgnoreCase)||u.Host.EndsWith(".brteachcor.com",StringComparison.OrdinalIgnoreCase))&&u.AbsolutePath.StartsWith("/h5/games/9/9014/",StringComparison.Ordinal);
    void Navigate(string input)
    {
        string url=input.Trim();if(!url.Contains("://"))url="https://"+url;
        if(!HttpUrl(url)){status.Text="Digite um endereço http ou https.";return;}
        Current?.CoreWebView2?.Navigate(url);
    }
    void UpdateNavigation(){if(Current?.CoreWebView2!=null&&!address.Focused)address.Text=Current.CoreWebView2.Source;}
    void CloseTab(){if(tabs.TabPages.Count==1){Navigate("https://888pg.cc/");return;}var page=tabs.SelectedTab;if(page==null)return;foreach(var b in page.Controls.OfType<WebView2>())b.Dispose();tabs.TabPages.Remove(page);page.Dispose();}
    async void EditUserAgent()
    {
        using var dialog=new InputDialog("User agent","Vazio restaura o perfil Android padrão.",settings.UserAgent,value=>value.Length<=1000&&!value.Contains('\r')&&!value.Contains('\n')?null:"User agent inválido.");
        if(dialog.ShowDialog(this)!=DialogResult.OK)return;
        settings.UserAgent=dialog.Input.Text.Trim();Program.SaveSettings(settings);
        foreach(TabPage page in tabs.TabPages)foreach(var browser in page.Controls.OfType<WebView2>()){if(browser.CoreWebView2==null)continue;browser.CoreWebView2.Settings.UserAgent=UserAgent;await ApplyProfileAsync(browser);browser.Reload();}
    }
    void ResetAll()
    {
        if(resetting)return;resetting=true;
        try
        {
            var start=new ProcessStartInfo(Program.Exe){UseShellExecute=false};start.ArgumentList.Add("--reset");start.ArgumentList.Add(Environment.ProcessId.ToString());
            Process.Start(start);Close();
        }
        catch(Exception ex){resetting=false;MessageBox.Show("Não foi possível reiniciar: "+ex.Message);}
    }
}
