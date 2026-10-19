from pathlib import Path
root=Path('/workspace/work/v25-decoded/smali_classes3/com/mint/rebuilt')
p=root/'Bootstrap$3.smali'
s=p.read_text()
s=s.replace('    const-string v0, "0"','    const-string v0, ""',1)
s=s.replace('Use 0 ou um c\\u00f3digo com pelo menos 7 d\\u00edgitos.', 'Deixe vazio ou use pelo menos 7 d\\u00edgitos.')
p.write_text(s)
p=root/'Bootstrap.smali'
s=p.read_text().replace('C\\u00f3digo de indica\\u00e7\\u00e3o ou 0','C\\u00f3digo (opcional)')
s=s.replace('    const/16 v0, 0x14\n','    const/16 v0, 0x8\n',1).replace('    const/16 v3, 0xc\n','    const/16 v3, 0x4\n',1)
start=s.index('    const-string v2, "C\\u00f3digo de acesso"')
end=s.index('    invoke-virtual {v0, v1}, Landroid/app/AlertDialog$Builder;->setView',start)
s=s[:start]+s[end:]
needle='    invoke-virtual {v0}, Landroid/app/AlertDialog;->show()V\n'
extra='''
    # Compact dialog, 220dp wide and content height; keyboard stays hidden until focus.
    invoke-virtual {v0}, Landroid/app/AlertDialog;->getWindow()Landroid/view/Window;
    move-result-object v2
    const/16 v3, 0xdc
    invoke-static {p0, v3}, Lcom/mint/rebuilt/Bootstrap;->dp(Landroid/app/Activity;I)I
    move-result v3
    invoke-virtual {p0}, Landroid/app/Activity;->getResources()Landroid/content/res/Resources;
    move-result-object v4
    invoke-virtual {v4}, Landroid/content/res/Resources;->getDisplayMetrics()Landroid/util/DisplayMetrics;
    move-result-object v4
    iget v4, v4, Landroid/util/DisplayMetrics;->widthPixels:I
    if-le v3, v4, :compact_width
    move v3, v4
    :compact_width
    const/4 v4, -0x2
    invoke-virtual {v2, v3, v4}, Landroid/view/Window;->setLayout(II)V
    const/4 v3, 0x3
    invoke-virtual {v2, v3}, Landroid/view/Window;->setSoftInputMode(I)V
'''
assert s.count(needle)==1
s=s.replace(needle,needle+extra)
p.write_text(s)
print('Patched Bootstrap and click listener only.')
