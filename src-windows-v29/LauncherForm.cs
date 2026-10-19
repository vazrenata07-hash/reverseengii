using System;
using System.Collections.Generic;
using System.Drawing;
using System.Linq;
using System.Windows.Forms;

namespace MintWindows;

public sealed class LauncherForm : Form
{
    private readonly ListView _instances = new()
    {
        Dock = DockStyle.Fill, View = View.Details, FullRowSelect = true,
        MultiSelect = false, HideSelection = false, HeaderStyle = ColumnHeaderStyle.Nonclickable
    };
    private readonly Button _open = new() { Text = "Abrir instância", AutoSize = true, MinimumSize = new Size(120, 30) };
    private readonly Button _toggleProxy = new() { AutoSize = true, MinimumSize = new Size(115, 30) };
    private readonly Label _proxyStatus = new() { AutoSize = true, Anchor = AnchorStyles.Left, Margin = new Padding(0, 0, 8, 0) };
    private readonly Label _status = new() { AutoSize = true, Dock = DockStyle.Fill, ForeColor = SystemColors.GrayText };
    private readonly System.Windows.Forms.Timer _timer = new() { Interval = 2000 };
    private IReadOnlyList<BrowserInstance> _knownInstances = Array.Empty<BrowserInstance>();
    private bool _opening;

    public LauncherForm()
    {
        Text = "Mint Browser · Instâncias";
        Font = new Font("Segoe UI", 9F);
        AutoScaleMode = AutoScaleMode.Dpi;
        ClientSize = new Size(650, 440);
        MinimumSize = new Size(600, 420);
        StartPosition = FormStartPosition.CenterScreen;
        BackColor = SystemColors.Window;

        var layout = new TableLayoutPanel { Dock = DockStyle.Fill, Padding = new Padding(20, 16, 20, 12), ColumnCount = 1, RowCount = 6 };
        layout.ColumnStyles.Add(new ColumnStyle(SizeType.Percent, 100));
        layout.RowStyles.Add(new RowStyle(SizeType.AutoSize));
        layout.RowStyles.Add(new RowStyle(SizeType.AutoSize));
        layout.RowStyles.Add(new RowStyle(SizeType.Percent, 100));
        layout.RowStyles.Add(new RowStyle(SizeType.AutoSize));
        layout.RowStyles.Add(new RowStyle(SizeType.AutoSize));
        layout.RowStyles.Add(new RowStyle(SizeType.AutoSize));
        Controls.Add(layout);
        layout.Controls.Add(new Label
        {
            Text = "Suas instâncias", AutoSize = true, Font = new Font("Segoe UI", 17F, FontStyle.Bold),
            ForeColor = Color.FromArgb(35, 46, 63), Margin = new Padding(0, 0, 0, 5)
        }, 0, 0);
        layout.Controls.Add(new Label
        {
            Text = "Cookies e armazenamento separados. Proxy e preferências compartilhados.",
            AutoSize = true, ForeColor = SystemColors.GrayText, Margin = new Padding(0, 0, 0, 14)
        }, 0, 1);

        _instances.Columns.Add("Nome", 455);
        _instances.Columns.Add("Estado", 120);
        _instances.Margin = new Padding(0);
        _instances.SelectedIndexChanged += (_, _) => UpdateOpenButton();
        _instances.ItemActivate += (_, _) => OpenSelected();
        _instances.Resize += (_, _) =>
        {
            int stateWidth = (int)(110 * DeviceDpi / 96F);
            _instances.Columns[1].Width = stateWidth;
            _instances.Columns[0].Width = Math.Max(150, _instances.ClientSize.Width - stateWidth - SystemInformation.VerticalScrollBarWidth - 3);
        };
        layout.Controls.Add(_instances, 0, 2);

        var actions = new FlowLayoutPanel { AutoSize = true, Dock = DockStyle.Fill, Margin = new Padding(0, 10, 0, 12) };
        var create = new Button { Text = "Criar e abrir", AutoSize = true, MinimumSize = new Size(110, 30), Margin = new Padding(0, 0, 8, 0) };
        create.Click += (_, _) => CreateInstance();
        _open.Click += (_, _) => OpenSelected();
        actions.Controls.Add(create); actions.Controls.Add(_open);
        layout.Controls.Add(actions, 0, 3);

        var proxy = new TableLayoutPanel
        {
            Dock = DockStyle.Fill, AutoSize = true, ColumnCount = 3, RowCount = 2,
            Padding = new Padding(10), BackColor = Color.FromArgb(244, 247, 251), Margin = new Padding(0, 0, 0, 10)
        };
        proxy.ColumnStyles.Add(new ColumnStyle(SizeType.Percent, 100));
        proxy.ColumnStyles.Add(new ColumnStyle(SizeType.AutoSize));
        proxy.ColumnStyles.Add(new ColumnStyle(SizeType.AutoSize));
        proxy.Controls.Add(_proxyStatus, 0, 0);
        var configureProxy = new Button { Text = "Configurar proxy", AutoSize = true, MinimumSize = new Size(125, 30), Margin = new Padding(0, 0, 8, 0) };
        configureProxy.Click += (_, _) => ConfigureProxy();
        _toggleProxy.Click += (_, _) => ToggleProxy();
        proxy.Controls.Add(configureProxy, 1, 0); proxy.Controls.Add(_toggleProxy, 2, 0);
        var proxyInfo = new Label
        {
            Text = "Alterações do proxy valem para instâncias abertas, sem recarregar páginas.",
            AutoSize = true, ForeColor = SystemColors.GrayText, Margin = new Padding(0, 8, 0, 0)
        };
        proxy.Controls.Add(proxyInfo, 0, 1); proxy.SetColumnSpan(proxyInfo, 3);
        layout.Controls.Add(proxy, 0, 4);
        _status.Text = "Selecione uma instância para abrir.";
        layout.Controls.Add(_status, 0, 5);
        AcceptButton = _open;

        _timer.Tick += (_, _) => { RefreshRunningStates(); RefreshProxyStatus(); };
        Shown += (_, _) => { RefreshInstances(); RefreshProxyStatus(); _timer.Start(); };
        Activated += (_, _) => { RefreshInstances(); RefreshProxyStatus(); };
    }

    private void RefreshInstances(string? selectId = null)
    {
        if (IsDisposed) return;
        selectId ??= SelectedInstance()?.Id;
        try
        {
            var instances = Program.GetInstances();
            bool same = instances.Count == _knownInstances.Count
                && instances.Select(instance => (instance.Id, instance.Name)).SequenceEqual(_knownInstances.Select(instance => (instance.Id, instance.Name)));
            if (!same || _instances.Items.Count != instances.Count)
            {
                _knownInstances = instances;
                _instances.BeginUpdate();
                try
                {
                    _instances.Items.Clear();
                    foreach (var instance in instances)
                    {
                        var item = new ListViewItem(instance.Name) { Tag = instance };
                        item.SubItems.Add(string.Empty);
                        _instances.Items.Add(item);
                    }
                }
                finally { _instances.EndUpdate(); }
            }
            var selected = _instances.Items.Cast<ListViewItem>().FirstOrDefault(item => ((BrowserInstance)item.Tag!).Id == selectId)
                ?? _instances.Items.Cast<ListViewItem>().FirstOrDefault(item => ((BrowserInstance)item.Tag!).Id == "default")
                ?? _instances.Items.Cast<ListViewItem>().FirstOrDefault();
            if (selected is not null) { selected.Selected = true; selected.Focused = true; }
            RefreshRunningStates();
        }
        catch { _status.Text = "Não foi possível carregar a lista de instâncias."; }
        UpdateOpenButton();
    }

    private BrowserInstance? SelectedInstance() => _instances.SelectedItems.Count == 1 ? _instances.SelectedItems[0].Tag as BrowserInstance : null;

    private void RefreshRunningStates()
    {
        foreach (ListViewItem item in _instances.Items)
        {
            try
            {
                bool running = Program.IsInstanceRunning(((BrowserInstance)item.Tag!).Id);
                string state = running ? "Aberta" : "Fechada";
                if (item.SubItems[1].Text != state) item.SubItems[1].Text = state;
            }
            catch { item.SubItems[1].Text = "Indisponível"; }
        }
    }

    private void UpdateOpenButton() => _open.Enabled = !_opening && SelectedInstance() is not null;

    private void CreateInstance()
    {
        string defaultName = "Instância " + (_knownInstances.Count + 1);
        using var dialog = new InputDialog("Nova instância", "Escolha um nome. A nova instância será criada e aberta.", defaultName, value =>
        {
            if (string.IsNullOrWhiteSpace(value)) return "Digite um nome para a instância.";
            if (value.Length > 60 || value.Any(char.IsControl)) return "Use até 60 caracteres, sem quebras de linha.";
            if (_knownInstances.Any(instance => string.Equals(instance.Name, value.Trim(), StringComparison.OrdinalIgnoreCase))) return "Já existe uma instância com esse nome.";
            return null;
        });
        if (dialog.ShowDialog(this) != DialogResult.OK) return;
        try
        {
            var instance = Program.CreateInstance(dialog.Input.Text.Trim());
            RefreshInstances(instance.Id);
            OpenSelected();
        }
        catch { ShowError("Não foi possível criar a instância. Confira se a pasta do Mint permite gravação."); }
    }

    private void OpenSelected()
    {
        var instance = SelectedInstance();
        if (instance is null || _opening) return;
        _opening = true; UpdateOpenButton();
        try
        {
            Program.LaunchInstance(instance.Id);
            _status.Text = "Abertura solicitada: " + instance.Name + ".";
            RefreshRunningStates();
        }
        catch { ShowError("Não foi possível abrir a instância selecionada."); }
        finally { _opening = false; UpdateOpenButton(); }
    }

    private void ConfigureProxy()
    {
        try
        {
            using var dialog = new ProxyDialog(Program.LoadProxySettings());
            if (dialog.ShowDialog(this) != DialogResult.OK) return;
            Program.SaveProxySettings(dialog.Result);
            RefreshProxyStatus();
            _status.Text = "Proxy salvo. As alterações valem para instâncias abertas, sem recarregar páginas.";
        }
        catch { ShowError("Não foi possível salvar a configuração do proxy."); }
    }

    private void ToggleProxy()
    {
        try
        {
            var proxy = Program.LoadProxySettings();
            if (!proxy.Enabled)
            {
                if (!proxy.IsConfigured)
                {
                    ConfigureProxy();
                    _status.Text = "Configure o proxy e clique em Ativar proxy para conectar.";
                    return;
                }
                proxy.GetEndpoint();
            }
            proxy.Enabled = !proxy.Enabled;
            Program.SaveProxySettings(proxy);
            RefreshProxyStatus();
            _status.Text = "Proxy " + (proxy.Enabled ? "ativado" : "desativado") + ". Vale para instâncias abertas, sem recarregar páginas.";
        }
        catch { ShowError("Não foi possível alterar o proxy. Confira a configuração e a senha salva."); }
    }

    private void RefreshProxyStatus()
    {
        try
        {
            var proxy = Program.LoadProxySettings();
            _proxyStatus.Text = "Proxy compartilhado: " + (proxy.Enabled ? "ON" : "OFF");
            _proxyStatus.ForeColor = proxy.Enabled ? Color.FromArgb(32, 110, 68) : Color.FromArgb(76, 85, 99);
            _toggleProxy.Text = proxy.Enabled ? "Desativar proxy" : "Ativar proxy";
        }
        catch { _proxyStatus.Text = "Proxy indisponível"; _toggleProxy.Text = "Ativar proxy"; }
    }

    private void ShowError(string message) => MessageBox.Show(this, message, "Mint Browser", MessageBoxButtons.OK, MessageBoxIcon.Warning);

    protected override void Dispose(bool disposing)
    {
        if (disposing) _timer.Dispose();
        base.Dispose(disposing);
    }
}
