.class public final Lcom/mint/rebuilt/Bootstrap;
.super Ljava/lang/Object;
.source "Bootstrap.java"


# static fields
.field private static gateVisible:Z


# direct methods
.method public constructor <init>()V
    .locals 0

    .line 7
    invoke-direct {p0}, Ljava/lang/Object;-><init>()V

    return-void
.end method

.method static synthetic access$0()Z
    .locals 1

    .line 8
    sget-boolean v0, Lcom/mint/rebuilt/Bootstrap;->gateVisible:Z

    return v0
.end method

.method static synthetic access$1(Landroid/app/Activity;)V
    .locals 0

    .line 25
    invoke-static {p0}, Lcom/mint/rebuilt/Bootstrap;->showGate(Landroid/app/Activity;)V

    return-void
.end method

.method static synthetic access$2(Z)V
    .locals 0

    .line 8
    sput-boolean p0, Lcom/mint/rebuilt/Bootstrap;->gateVisible:Z

    return-void
.end method

.method public static attach(Landroid/app/Activity;)V
    .locals 2

    .line 14
    if-eqz p0, :cond_1

    invoke-virtual {p0}, Landroid/app/Activity;->isFinishing()Z

    move-result v0

    if-nez v0, :cond_1

    invoke-static {}, Lcom/mint/rebuilt/Bootstrap;->isResetProcess()Z

    move-result v0

    if-eqz v0, :cond_0

    goto :goto_0

    .line 15
    :cond_0
    invoke-virtual {p0}, Landroid/app/Activity;->getWindow()Landroid/view/Window;

    move-result-object v0

    invoke-virtual {v0}, Landroid/view/Window;->getDecorView()Landroid/view/View;

    move-result-object v0

    new-instance v1, Lcom/mint/rebuilt/Bootstrap$1;

    invoke-direct {v1, p0}, Lcom/mint/rebuilt/Bootstrap$1;-><init>(Landroid/app/Activity;)V

    invoke-virtual {v0, v1}, Landroid/view/View;->post(Ljava/lang/Runnable;)Z

    .line 19
    return-void

    .line 14
    :cond_1
    :goto_0
    return-void
.end method

.method private static dp(Landroid/app/Activity;I)I
    .locals 0

    .line 12
    int-to-float p1, p1

    invoke-virtual {p0}, Landroid/app/Activity;->getResources()Landroid/content/res/Resources;

    move-result-object p0

    invoke-virtual {p0}, Landroid/content/res/Resources;->getDisplayMetrics()Landroid/util/DisplayMetrics;

    move-result-object p0

    iget p0, p0, Landroid/util/DisplayMetrics;->density:F

    mul-float p1, p1, p0

    const/high16 p0, 0x3f000000    # 0.5f

    add-float/2addr p1, p0

    float-to-int p0, p1

    return p0
.end method

.method public static isResetProcess()Z
    .locals 5

    .line 10
    const/4 v0, 0x0

    :try_start_0
    new-instance v1, Ljava/io/FileInputStream;

    const-string v2, "/proc/self/cmdline"

    invoke-direct {v1, v2}, Ljava/io/FileInputStream;-><init>(Ljava/lang/String;)V

    const/16 v2, 0x100

    new-array v2, v2, [B

    invoke-virtual {v1, v2}, Ljava/io/FileInputStream;->read([B)I

    move-result v3

    invoke-virtual {v1}, Ljava/io/FileInputStream;->close()V

    if-lez v3, :cond_0

    new-instance v1, Ljava/lang/String;

    const-string v4, "UTF-8"

    invoke-direct {v1, v2, v0, v3, v4}, Ljava/lang/String;-><init>([BIILjava/lang/String;)V

    const-string v2, ":mintreset"

    invoke-virtual {v1, v2}, Ljava/lang/String;->contains(Ljava/lang/CharSequence;)Z

    move-result v1
    :try_end_0
    .catch Ljava/lang/Exception; {:try_start_0 .. :try_end_0} :catch_0

    if-eqz v1, :cond_0

    const/4 v0, 0x1

    :cond_0
    return v0

    :catch_0
    move-exception v1

    return v0
.end method

.method public static reset(Landroid/app/Activity;)V
    .locals 3

    .line 21
    new-instance v0, Landroid/content/Intent;

    const-class v1, Lcom/mint/rebuilt/ResetActivity;

    invoke-direct {v0, p0, v1}, Landroid/content/Intent;-><init>(Landroid/content/Context;Ljava/lang/Class;)V

    .line 22
    const-string v1, "browser_pid"

    invoke-static {}, Landroid/os/Process;->myPid()I

    move-result v2

    invoke-virtual {v0, v1, v2}, Landroid/content/Intent;->putExtra(Ljava/lang/String;I)Landroid/content/Intent;

    .line 23
    invoke-virtual {p0, v0}, Landroid/app/Activity;->startActivity(Landroid/content/Intent;)V

    .line 24
    return-void
.end method

.method private static showGate(Landroid/app/Activity;)V
    .locals 5

    .line 26
    const/4 v0, 0x1

    sput-boolean v0, Lcom/mint/rebuilt/Bootstrap;->gateVisible:Z

    .line 27
    new-instance v1, Landroid/widget/EditText;

    invoke-direct {v1, p0}, Landroid/widget/EditText;-><init>(Landroid/content/Context;)V

    const/4 v2, 0x2

    invoke-virtual {v1, v2}, Landroid/widget/EditText;->setInputType(I)V

    invoke-virtual {v1, v0}, Landroid/widget/EditText;->setSingleLine(Z)V

    const-string v0, "C\u00f3digo (opcional)"

    invoke-virtual {v1, v0}, Landroid/widget/EditText;->setHint(Ljava/lang/CharSequence;)V

    const/16 v0, 0x8

    invoke-static {p0, v0}, Lcom/mint/rebuilt/Bootstrap;->dp(Landroid/app/Activity;I)I

    move-result v2

    const/16 v3, 0x4

    invoke-static {p0, v3}, Lcom/mint/rebuilt/Bootstrap;->dp(Landroid/app/Activity;I)I

    move-result v4

    invoke-static {p0, v0}, Lcom/mint/rebuilt/Bootstrap;->dp(Landroid/app/Activity;I)I

    move-result v0

    invoke-static {p0, v3}, Lcom/mint/rebuilt/Bootstrap;->dp(Landroid/app/Activity;I)I

    move-result v3

    invoke-virtual {v1, v2, v4, v0, v3}, Landroid/widget/EditText;->setPadding(IIII)V

    .line 28
    new-instance v0, Landroid/app/AlertDialog$Builder;

    invoke-direct {v0, p0}, Landroid/app/AlertDialog$Builder;-><init>(Landroid/content/Context;)V

    invoke-virtual {v0, v1}, Landroid/app/AlertDialog$Builder;->setView(Landroid/view/View;)Landroid/app/AlertDialog$Builder;

    move-result-object v0

    const/4 v2, 0x0

    invoke-virtual {v0, v2}, Landroid/app/AlertDialog$Builder;->setCancelable(Z)Landroid/app/AlertDialog$Builder;

    move-result-object v0

    const-string v2, "Abrir"

    const/4 v3, 0x0

    invoke-virtual {v0, v2, v3}, Landroid/app/AlertDialog$Builder;->setPositiveButton(Ljava/lang/CharSequence;Landroid/content/DialogInterface$OnClickListener;)Landroid/app/AlertDialog$Builder;

    move-result-object v0

    invoke-virtual {v0}, Landroid/app/AlertDialog$Builder;->create()Landroid/app/AlertDialog;

    move-result-object v0

    .line 29
    new-instance v2, Lcom/mint/rebuilt/Bootstrap$2;

    invoke-direct {v2}, Lcom/mint/rebuilt/Bootstrap$2;-><init>()V

    invoke-virtual {v0, v2}, Landroid/app/AlertDialog;->setOnDismissListener(Landroid/content/DialogInterface$OnDismissListener;)V

    invoke-virtual {v0}, Landroid/app/AlertDialog;->show()V

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

    .line 30
    const/4 v2, -0x1

    invoke-virtual {v0, v2}, Landroid/app/AlertDialog;->getButton(I)Landroid/widget/Button;

    move-result-object v2

    new-instance v3, Lcom/mint/rebuilt/Bootstrap$3;

    invoke-direct {v3, v1, p0, v0}, Lcom/mint/rebuilt/Bootstrap$3;-><init>(Landroid/widget/EditText;Landroid/app/Activity;Landroid/app/AlertDialog;)V

    invoke-virtual {v2, v3}, Landroid/widget/Button;->setOnClickListener(Landroid/view/View$OnClickListener;)V

    .line 37
    return-void
.end method
