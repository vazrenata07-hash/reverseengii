.class Lcom/mint/rebuilt/Bootstrap$1;
.super Ljava/lang/Object;
.source "Bootstrap.java"

# interfaces
.implements Ljava/lang/Runnable;


# annotations
.annotation system Ldalvik/annotation/EnclosingMethod;
    value = Lcom/mint/rebuilt/Bootstrap;->attach(Landroid/app/Activity;)V
.end annotation

.annotation system Ldalvik/annotation/InnerClass;
    accessFlags = 0x0
    name = null
.end annotation


# instance fields
.field private final synthetic val$a:Landroid/app/Activity;


# direct methods
.method constructor <init>(Landroid/app/Activity;)V
    .locals 0

    .line 15
    iput-object p1, p0, Lcom/mint/rebuilt/Bootstrap$1;->val$a:Landroid/app/Activity;

    invoke-direct {p0}, Ljava/lang/Object;-><init>()V

    return-void
.end method


# virtual methods
.method public run()V
    .locals 3

    .line 16
    iget-object v0, p0, Lcom/mint/rebuilt/Bootstrap$1;->val$a:Landroid/app/Activity;

    invoke-virtual {v0}, Landroid/app/Activity;->isFinishing()Z

    move-result v0

    if-eqz v0, :cond_0

    return-void

    .line 17
    :cond_0
    invoke-static {}, Lcom/mint/rebuilt/Bootstrap;->access$0()Z

    move-result v0

    if-nez v0, :cond_1

    iget-object v0, p0, Lcom/mint/rebuilt/Bootstrap$1;->val$a:Landroid/app/Activity;

    const-string v1, "mint_rebuilt"

    const/4 v2, 0x0

    invoke-virtual {v0, v1, v2}, Landroid/app/Activity;->getSharedPreferences(Ljava/lang/String;I)Landroid/content/SharedPreferences;

    move-result-object v0

    const-string v1, "code_entered"

    invoke-interface {v0, v1, v2}, Landroid/content/SharedPreferences;->getBoolean(Ljava/lang/String;Z)Z

    move-result v0

    if-nez v0, :cond_1

    iget-object v0, p0, Lcom/mint/rebuilt/Bootstrap$1;->val$a:Landroid/app/Activity;

    invoke-static {v0}, Lcom/mint/rebuilt/Bootstrap;->access$1(Landroid/app/Activity;)V

    .line 18
    :cond_1
    return-void
.end method
