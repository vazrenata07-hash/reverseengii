namespace MintWindows;

internal sealed class DeviceModeDialog : Form
{
    readonly ComboBox profiles = new() { DropDownStyle = ComboBoxStyle.DropDownList, Dock = DockStyle.Fill };
    readonly CheckBox landscape = new() { Text = "Paisagem", AutoSize = true };
    readonly CheckBox touch = new() { Text = "Emular toque", AutoSize = true };
    readonly Label details = new() { AutoSize = true, Dock = DockStyle.Fill };
    public string ProfileId => (profiles.SelectedItem as DeviceProfile)?.Id ?? "";
    public bool Landscape => landscape.Checked;
    public bool Touch => touch.Checked;

    internal DeviceModeDialog(Settings settings)
    {
        Text = "Modo dispositivo";
        ClientSize = new(500, 300);
        MinimumSize = new(460, 340);
        StartPosition = FormStartPosition.CenterParent;
        FormBorderStyle = FormBorderStyle.FixedDialog;
        MaximizeBox = false; MinimizeBox = false;
        AutoScaleMode = AutoScaleMode.Dpi;

        var layout = new TableLayoutPanel { Dock = DockStyle.Fill, Padding = new Padding(18), ColumnCount = 1, RowCount = 6 };
        layout.RowStyles.Add(new RowStyle(SizeType.AutoSize));
        layout.RowStyles.Add(new RowStyle(SizeType.AutoSize));
        layout.RowStyles.Add(new RowStyle(SizeType.AutoSize));
        layout.RowStyles.Add(new RowStyle(SizeType.AutoSize));
        layout.RowStyles.Add(new RowStyle(SizeType.Percent, 100));
        layout.RowStyles.Add(new RowStyle(SizeType.AutoSize));
        layout.Controls.Add(new Label { Text = "Perfil de visualização", AutoSize = true, Margin = new Padding(0, 0, 0, 8) }, 0, 0);
        profiles.Items.Add("Windows — tamanho da janela");
        foreach (var profile in DeviceProfiles.All) profiles.Items.Add(profile);
        profiles.SelectedIndex = 0;
        for (int i = 1; i < profiles.Items.Count; i++)
            if (profiles.Items[i] is DeviceProfile profile && profile.Id == settings.DeviceProfileId) profiles.SelectedIndex = i;
        profiles.Margin = new Padding(0, 0, 0, 12);
        layout.Controls.Add(profiles, 0, 1);

        landscape.Checked = settings.DeviceLandscape;
        touch.Checked = settings.DeviceTouch;
        var choices = new FlowLayoutPanel { AutoSize = true, Dock = DockStyle.Fill, Margin = new Padding(0, 0, 0, 10) };
        choices.Controls.Add(landscape); choices.Controls.Add(touch);
        layout.Controls.Add(choices, 0, 2);
        layout.Controls.Add(details, 0, 3);
        layout.Controls.Add(new Label {
            Text = "Os modelos ajustam a área de exibição e o toque.\nO navegador continua sendo Edge/WebView2 no Windows.",
            AutoSize = true, Dock = DockStyle.Fill, Margin = new Padding(0, 12, 0, 12)
        }, 0, 4);

        var apply = new Button { Text = "Aplicar", AutoSize = true, DialogResult = DialogResult.OK };
        var cancel = new Button { Text = "Cancelar", AutoSize = true, DialogResult = DialogResult.Cancel };
        var actions = new FlowLayoutPanel { AutoSize = true, Dock = DockStyle.Fill, FlowDirection = FlowDirection.RightToLeft, WrapContents = false };
        actions.Controls.Add(cancel); actions.Controls.Add(apply);
        layout.Controls.Add(actions, 0, 5);
        Controls.Add(layout);
        AcceptButton = apply; CancelButton = cancel;
        profiles.SelectedIndexChanged += (_, _) => UpdateDetails();
        landscape.CheckedChanged += (_, _) => UpdateDetails();
        UpdateDetails();
    }

    void UpdateDetails()
    {
        var profile = profiles.SelectedItem as DeviceProfile;
        landscape.Enabled = touch.Enabled = profile != null;
        details.Text = profile == null
            ? "Área de exibição automática, conforme o tamanho da janela."
            : $"{(landscape.Checked ? profile.Height : profile.Width)} × {(landscape.Checked ? profile.Width : profile.Height)} px CSS · DPR {profile.ScaleFactor:0.###}";
    }
}
