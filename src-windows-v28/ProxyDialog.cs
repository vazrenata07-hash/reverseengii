using System;
using System.Drawing;
using System.Security.Cryptography;
using System.Windows.Forms;

namespace MintWindows;

public sealed class ProxyDialog : Form
{
    private readonly bool _savedEnabled;
    private readonly ComboBox _protocol = new() { DropDownStyle = ComboBoxStyle.DropDownList, Dock = DockStyle.Fill };
    private readonly TextBox _host = new() { Dock = DockStyle.Fill };
    private readonly NumericUpDown _port = new() { Minimum = 1, Maximum = 65535, Width = 105 };
    private readonly TextBox _username = new() { Dock = DockStyle.Fill };
    private readonly TextBox _password = new() { Dock = DockStyle.Fill, UseSystemPasswordChar = true };
    private readonly CheckBox _clearCredentials = new() { Text = "Limpar credenciais", AutoSize = true };
    private bool _passwordDecryptionFailed;
    private ProxySettings? _result;

    public ProxySettings Result => _result ?? throw new InvalidOperationException("A configuração só está disponível depois de Salvar.");

    public ProxyDialog(ProxySettings saved)
    {
        if (saved is null) throw new ArgumentNullException(nameof(saved));
        _savedEnabled = saved.Enabled;
        Text = "Configurar proxy";
        Font = new Font("Segoe UI", 9F);
        AutoScaleMode = AutoScaleMode.Dpi;
        ClientSize = new Size(500, 480);
        FormBorderStyle = FormBorderStyle.FixedDialog;
        MaximizeBox = false;
        MinimizeBox = false;
        ShowInTaskbar = false;
        StartPosition = FormStartPosition.CenterParent;
        BackColor = SystemColors.Window;

        _protocol.Items.AddRange(new object[] { "HTTP", "HTTPS", "SOCKS5" });
        _protocol.SelectedIndex = Enum.IsDefined(typeof(ProxyProtocol), saved.Protocol) ? (int)saved.Protocol : 0;
        _host.Text = saved.Host ?? string.Empty;
        _port.Value = saved.Port >= 1 && saved.Port <= 65535 ? saved.Port : 8080;
        _username.Text = saved.Username ?? string.Empty;
        try { _password.Text = saved.ReadPassword(); }
        catch (CryptographicException) { _passwordDecryptionFailed = true; _password.Clear(); }

        var layout = new TableLayoutPanel { Dock = DockStyle.Fill, Padding = new Padding(16, 12, 16, 12), ColumnCount = 2, RowCount = 11 };
        layout.ColumnStyles.Add(new ColumnStyle(SizeType.Absolute, 108));
        layout.ColumnStyles.Add(new ColumnStyle(SizeType.Percent, 100));
        for (int i = 0; i < 11; i++) layout.RowStyles.Add(new RowStyle(i == 9 ? SizeType.Percent : SizeType.AutoSize, i == 9 ? 100 : 0));
        Controls.Add(layout);
        var intro = new Label { Text = "Use o botão de ativação para conectar. Se já estiver ligado, Salvar aplica as alterações e recarrega as abas.", AutoSize = true, ForeColor = SystemColors.GrayText, MaximumSize = new Size(460, 0), Margin = new Padding(0, 0, 0, 12) };
        layout.Controls.Add(intro, 0, 0); layout.SetColumnSpan(intro, 2);
        AddField(layout, 1, "Protocolo", _protocol);
        AddField(layout, 2, "Host ou IP", _host);
        AddField(layout, 3, "Porta", _port);
        AddField(layout, 4, "Usuário", _username);
        AddField(layout, 5, "Senha", _password);
        var options = new FlowLayoutPanel { AutoSize = true, Dock = DockStyle.Fill, Margin = new Padding(0, 0, 0, 3), WrapContents = true };
        var showPassword = new CheckBox { Text = "Mostrar senha", AutoSize = true };
        showPassword.CheckedChanged += (_, _) => _password.UseSystemPasswordChar = !showPassword.Checked;
        options.Controls.Add(showPassword);
        _clearCredentials.Visible = _passwordDecryptionFailed;
        _clearCredentials.CheckedChanged += (_, _) =>
        {
            bool clear = _clearCredentials.Checked;
            _username.Enabled = !clear; _password.Enabled = !clear; showPassword.Enabled = !clear;
            if (clear) { _username.Clear(); _password.Clear(); }
        };
        options.Controls.Add(_clearCredentials);
        layout.Controls.Add(options, 1, 6);
        var warning = new Label
        {
            Text = "Não foi possível recuperar a senha salva. Digite-a novamente ou marque Limpar credenciais.",
            AutoSize = true, ForeColor = Color.Firebrick, MaximumSize = new Size(460, 0),
            Visible = _passwordDecryptionFailed, Margin = new Padding(0, 3, 0, 5)
        };
        layout.Controls.Add(warning, 0, 7); layout.SetColumnSpan(warning, 2);
        var info = new Label
        {
            Text = "Usuário e senha são opcionais.\r\nAtivar/desativar recarrega as abas. A rotação depende do provedor.",
            AutoSize = true, ForeColor = SystemColors.GrayText, MaximumSize = new Size(460, 0), Margin = new Padding(0, 7, 0, 0)
        };
        layout.Controls.Add(info, 0, 8); layout.SetColumnSpan(info, 2);
        var buttons = new FlowLayoutPanel { Dock = DockStyle.Fill, AutoSize = true, FlowDirection = FlowDirection.RightToLeft, Margin = new Padding(0, 8, 0, 0) };
        var save = new Button { Text = "Salvar", AutoSize = true, MinimumSize = new Size(86, 28) };
        var cancel = new Button { Text = "Cancelar", DialogResult = DialogResult.Cancel, AutoSize = true, MinimumSize = new Size(86, 28) };
        save.Click += SaveSettings;
        buttons.Controls.Add(cancel); buttons.Controls.Add(save);
        layout.Controls.Add(buttons, 0, 10); layout.SetColumnSpan(buttons, 2);
        AcceptButton = save; CancelButton = cancel;
    }

    private static void AddField(TableLayoutPanel layout, int row, string text, Control input)
    {
        var label = new Label { Text = text, AutoSize = true, Anchor = AnchorStyles.Left, Margin = new Padding(0, 6, 8, 6) };
        input.Margin = new Padding(0, 3, 0, 5);
        layout.Controls.Add(label, 0, row); layout.Controls.Add(input, 1, row);
    }

    private void SaveSettings(object? sender, EventArgs e)
    {
        if (!ProxySettings.TryNormalizeHost(_host.Text, out string host))
        {
            ShowError("Informe somente um nome de host, IPv4 ou IPv6 válido, sem protocolo, caminho ou espaços.", _host);
            return;
        }
        if (_passwordDecryptionFailed && !_clearCredentials.Checked && _password.Text.Length == 0)
        {
            ShowError("Digite novamente a senha salva ou marque Limpar credenciais para continuar.", _password);
            return;
        }
        var protocol = (ProxyProtocol)_protocol.SelectedIndex;
        string username = _clearCredentials.Checked ? string.Empty : _username.Text;
        string password = _clearCredentials.Checked ? string.Empty : _password.Text;
        if (!ProxySettings.ValidateCredentials(protocol, username, password, out string error))
        {
            ShowError(error, _username);
            return;
        }
        var result = new ProxySettings { Enabled = _savedEnabled, Protocol = protocol, Host = host, Port = (int)_port.Value, Username = username };
        try { result.SetPassword(password); }
        catch (CryptographicException)
        {
            ShowError("Não foi possível proteger a senha no Windows. A configuração não foi salva.", _password);
            return;
        }
        _result = result;
        DialogResult = DialogResult.OK;
        Close();
    }

    private void ShowError(string message, Control input)
    {
        MessageBox.Show(this, message, "Configurar proxy", MessageBoxButtons.OK, MessageBoxIcon.Warning);
        input.Focus();
    }
}
