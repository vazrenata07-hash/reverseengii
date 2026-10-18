namespace MintWindows;

internal sealed class InputDialog : Form
{
    internal TextBox Input { get; } = new() { Dock = DockStyle.Fill };
    readonly Label error = new() { AutoSize = true, ForeColor = Color.Firebrick, Dock = DockStyle.Fill };
    internal InputDialog(string title, string description, string value, Func<string, string?> validate)
    {
        Text = title; Width = 480; Height = 220; MinimumSize = new(380, 200);
        StartPosition = FormStartPosition.CenterParent; MinimizeBox = false; MaximizeBox = false;
        var layout = new TableLayoutPanel { Dock = DockStyle.Fill, Padding = new(16), RowCount = 4, ColumnCount = 1 };
        layout.RowStyles.Add(new(SizeType.AutoSize));layout.RowStyles.Add(new(SizeType.AutoSize));
        layout.RowStyles.Add(new(SizeType.Percent, 100));layout.RowStyles.Add(new(SizeType.AutoSize));
        layout.Controls.Add(new Label { Text = description, AutoSize = true, Dock = DockStyle.Fill, Padding = new(0,0,0,10) }, 0, 0);
        Input.Text = value;layout.Controls.Add(Input,0,1);layout.Controls.Add(error,0,2);
        var submit = new Button { Text = "Abrir", AutoSize = true, Anchor = AnchorStyles.Right };
        submit.Click += (_, _) => { string? issue = validate(Input.Text.Trim()); if (issue != null) { error.Text = issue; return; } DialogResult = DialogResult.OK; Close(); };
        layout.Controls.Add(submit,0,3); Controls.Add(layout); AcceptButton = submit;
        Shown += (_,_) => {Input.Focus();Input.SelectAll();};
    }
}
