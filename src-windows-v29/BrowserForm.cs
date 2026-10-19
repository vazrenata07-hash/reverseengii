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
    readonly ToolStripTextBox address = new() { AutoSize = false, Width = 120 };
    readonly ToolStripButton configureProxy = new("Config. proxy") { ToolTipText="Configurar proxy" };
    readonly ToolStripButton toggleProxy = new("Proxy: desligado") { ToolTipText="Ativar ou desativar proxy sem recarregar a página" };
    readonly ToolStripStatusLabel status = new() { Text = "Iniciando…", Spring = true, TextAlign = ContentAlignment.MiddleLeft };
    readonly Settings settings = Program.LoadSettings();
    readonly Ledger ledger = new();
    ProxySettings proxySettings = Program.LoadProxySettings();
    FileSystemWatcher? proxyWatcher;
    readonly System.Windows.Forms.Timer sharedProxyTimer = new() { Interval=250 };
    ProxyRelay? proxyRelay;
    CoreWebView2Environment? environment;
    string script = "";
    bool closing, exitReady, resetting, applyingProxy, starting, networkBlocked;
    WebView2? Current => tabs.SelectedTab?.Controls.OfType<WebView2>().FirstOrDefault();

    internal BrowserForm()
    {
        Text = Program.WindowTitle;
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
        menu.DropDownItems.Add("Ferramentas de desenvolvedor", null, (_,_) => Current?.CoreWebView2?.OpenDevToolsWindow());
        menu.DropDownItems.Add("Configurar proxy…", null, async (_,_) => await ConfigureProxyAsync());
        menu.DropDownItems.Add("Ativar/desativar proxy", null, async (_,_) => await ToggleProxyAsync());
        menu.DropDownItems.Add("Sobre", null, (_,_) => MessageBox.Show("Mint Portable V29\nPerfil: nativo do Windows\nMotor: Microsoft Edge WebView2\nSenha de login: "+Program.Variant+"\nPIN configurado: 232691\n\nHistórico e contador: JDB Mines 9014.\nDados locais: "+Program.DataRoot,"Sobre",MessageBoxButtons.OK,MessageBoxIcon.Information));
        configureProxy.Click += async (_,_) => await ConfigureProxyAsync();
        toggleProxy.Click += async (_,_) => await ToggleProxyAsync();
        toolbar.Items.AddRange([back,forward,reload,home,address,configureProxy,toggleProxy,add,menu]);
        UpdateProxyButtons();
        var bar = new StatusStrip();bar.Items.Add(status);
        Controls.Add(tabs);Controls.Add(toolbar);Controls.Add(bar);
        tabs.SelectedIndexChanged += (_,_) => UpdateNavigation();
        address.KeyDown += (_,e) => {if(e.KeyCode==Keys.Enter){e.SuppressKeyPress=true;Navigate(address.Text);}};
        Resize += (_,_) => address.Width=Math.Max(90,toolbar.Width-400);
        sharedProxyTimer.Tick += async (_,_) =>
        {
            sharedProxyTimer.Stop();
            if(closing)return;
            if(applyingProxy || starting){sharedProxyTimer.Start();return;}
            var next=Program.LoadProxySettings();
            if(JsonSerializer.Serialize(next)!=JsonSerializer.Serialize(proxySettings))await ApplyProxySettingsAsync(next,false);
        };
        proxyWatcher=new FileSystemWatcher(Program.AppRoot,Path.GetFileName(Program.ProxyConfigPath)){
            NotifyFilter=NotifyFilters.FileName|NotifyFilters.LastWrite|NotifyFilters.Size
        };
        proxyWatcher.Changed += (_,_) => QueueSharedProxy();
        proxyWatcher.Created += (_,_) => QueueSharedProxy();
        proxyWatcher.Deleted += (_,_) => QueueSharedProxy();
        proxyWatcher.Renamed += (_,_) => QueueSharedProxy();
        proxyWatcher.EnableRaisingEvents=true;
        Shown += async (_,_) => await StartAsync();
        FormClosing += async (_,e) =>
        {
            if(exitReady)return;
            e.Cancel=true;if(closing)return;closing=true;Enabled=false;
            sharedProxyTimer.Stop();proxyWatcher?.Dispose();
            try{await ledger.AccessAsync();}catch{}
            foreach(TabPage page in tabs.TabPages)foreach(var browser in page.Controls.OfType<WebView2>())browser.Dispose();
            proxyRelay?.Dispose();
            exitReady=true;Close();
        };
        FormClosed += (_,_) => sharedProxyTimer.Dispose();
    }

    async Task StartAsync()
    {
        if(starting || closing)return;
        starting=true;UpdateProxyButtons();
        try
        {
            ProxyEndpoint? endpoint=null;
            if(proxySettings.Enabled)
            {
                try { endpoint=proxySettings.GetEndpoint(); }
                catch
                {
                    status.Text="Proxy precisa de configuração. Use Config. proxy ou desative-o.";
                    return;
                }
            }
            proxyRelay?.Dispose();
            proxyRelay=new ProxyRelay();
            proxyRelay.Configure(endpoint);
            // Keep the user's explicit certificate compatibility setting from Android.
            var options = new CoreWebView2EnvironmentOptions("--ignore-certificate-errors --autoplay-policy=no-user-gesture-required --proxy-server=http://127.0.0.1:"+proxyRelay.Port+" --proxy-bypass-list=<-loopback>");
            environment = await CoreWebView2Environment.CreateAsync(null,Path.Combine(Program.DataRoot,"WebView2"),options);
            script = Program.Script();
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
        finally { starting=false;if(!closing)UpdateProxyButtons(); }
    }

    async Task<WebView2?> AddTabAsync(string? url)
    {
        if(environment==null||closing)return null;
        var page=new TabPage("Nova aba");var browser=new WebView2{Dock=DockStyle.Fill,DefaultBackgroundColor=Color.White};
        page.Controls.Add(browser);tabs.TabPages.Add(page);tabs.SelectedTab=page;
        try
        {
            await browser.EnsureCoreWebView2Async(environment);
            var core=browser.CoreWebView2;
            core.BasicAuthenticationRequested += (_, e) =>
            {
                var relay=proxyRelay;
                if(relay!=null && string.Equals(e.Challenge.Trim(),relay.AuthenticationChallenge,StringComparison.Ordinal))
                {
                    e.Response.UserName=relay.LocalUsername;
                    e.Response.Password=relay.LocalPassword;
                }
            };
            core.Settings.AreDevToolsEnabled=true;
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
            core.NavigationCompleted += (_,e) => {if(browser==Current)status.Text=e.IsSuccess?ConnectionStatus():"Carregamento: "+e.WebErrorStatus;};
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
            if(url!=null)core.Navigate(url);
            return browser;
        }
        catch(Exception ex){status.Text="Não foi possível abrir a aba.";MessageBox.Show(ex.Message,"Mint Windows");browser.Dispose();tabs.TabPages.Remove(page);page.Dispose();return null;}
    }

    string ConnectionStatus() => networkBlocked?"Proxy inválido: conexão bloqueada. Configure ou desative.":"Pronto · Windows · "+(proxySettings.Enabled?"Proxy ligado":"Conexão direta");

    void UpdateProxyButtons()
    {
        toggleProxy.Checked=proxySettings.Enabled;
        toggleProxy.Text=proxySettings.Enabled?"Proxy: ligado":"Proxy: desligado";
        configureProxy.Enabled=toggleProxy.Enabled=!applyingProxy && !starting;
    }

    async Task ConfigureProxyAsync()
    {
        if(closing || applyingProxy || starting)return;
        using var dialog=new ProxyDialog(proxySettings);
        if(dialog.ShowDialog(this)!=DialogResult.OK)return;
        await ApplyProxySettingsAsync(dialog.Result);
    }

    async Task ToggleProxyAsync()
    {
        if(closing || applyingProxy || starting)return;
        if(!proxySettings.Enabled && !proxySettings.IsConfigured)
        {
            await ConfigureProxyAsync();
            if(!proxySettings.IsConfigured)return;
        }
        var next=new ProxySettings{
            Enabled=!proxySettings.Enabled,Protocol=proxySettings.Protocol,Host=proxySettings.Host,
            Port=proxySettings.Port,Username=proxySettings.Username,PasswordProtected=proxySettings.PasswordProtected
        };
        await ApplyProxySettingsAsync(next);
    }

    void QueueSharedProxy()
    {
        if(closing || IsDisposed || !IsHandleCreated)return;
        try { BeginInvoke(new Action(()=>{if(!closing){sharedProxyTimer.Stop();sharedProxyTimer.Start();}})); }
        catch(InvalidOperationException){}
    }

    async Task ApplyProxySettingsAsync(ProxySettings next,bool persist=true)
    {
        if(closing || applyingProxy)return;
        applyingProxy=true;UpdateProxyButtons();
        try
        {
            ProxyEndpoint? endpoint=null;
            try { if(next.Enabled)endpoint=next.GetEndpoint(); }
            catch when(!persist)
            {
                proxyRelay?.BlockConnections();
                proxySettings=next;networkBlocked=true;
                if(!closing)status.Text=ConnectionStatus();
                return;
            }
            var wasEnabled=proxySettings.Enabled;
            if(persist)Program.SaveProxySettings(next);
            proxySettings=next;
            networkBlocked=false;
            if(environment==null)
            {
                await StartAsync();
            }
            else if(next.Enabled || wasEnabled)
            {
                proxyRelay?.Configure(endpoint);
            }
            if(!closing)status.Text=ConnectionStatus();
        }
        catch
        {
            if(!closing)MessageBox.Show(this,"Não foi possível aplicar o proxy. Confira endereço, porta, credenciais e a permissão para salvar na pasta do EXE.","Proxy",MessageBoxButtons.OK,MessageBoxIcon.Information);
        }
        finally { applyingProxy=false;if(!closing)UpdateProxyButtons(); }
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
    void ResetAll()
    {
        if(resetting)return;resetting=true;
        try
        {
            var start=new ProcessStartInfo(Program.Exe){UseShellExecute=false};start.ArgumentList.Add("--reset");start.ArgumentList.Add(Environment.ProcessId.ToString());
            start.ArgumentList.Add("--instance");start.ArgumentList.Add(Program.InstanceId);
            start.ArgumentList.Add("--webview-pid");start.ArgumentList.Add((Current?.CoreWebView2?.BrowserProcessId ?? 0).ToString());
            Process.Start(start);Close();
        }
        catch(Exception ex){resetting=false;MessageBox.Show("Não foi possível reiniciar: "+ex.Message);}
    }
}
