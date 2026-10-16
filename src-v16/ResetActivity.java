package com.mint.rebuilt;
import android.app.*;
import android.content.*;
import android.os.*;
import android.view.*;
import android.widget.*;
import java.io.*;
public final class ResetActivity extends Activity {
 private int failures;
 public void onCreate(Bundle state){super.onCreate(state);getWindow().addFlags(128);TextView text=new TextView(this);text.setText("Limpando dados e cache…");text.setGravity(Gravity.CENTER);text.setTextSize(18);setContentView(text);startCleanup();}
 public void onBackPressed(){}
 private void startCleanup(){new Thread(new Runnable(){public void run(){
  failures=0;
  int old=getIntent().getIntExtra("browser_pid",-1);
  if(old>0&&old!=android.os.Process.myPid()){
   android.os.Process.killProcess(old);
   for(int i=0;i<100&&new File("/proc/"+old).exists();i++)try{Thread.sleep(20);}catch(InterruptedException e){Thread.currentThread().interrupt();}
   if(new File("/proc/"+old).exists()){failures++;showResult();return;}
  }
  // Other processes of this package can otherwise recreate databases/cookies.
  ActivityManager am=(ActivityManager)getSystemService(ACTIVITY_SERVICE);
  java.util.List<ActivityManager.RunningAppProcessInfo> processes=am==null?null:am.getRunningAppProcesses();
  if(processes!=null)for(ActivityManager.RunningAppProcessInfo p:processes)
   if(p.uid==android.os.Process.myUid()&&p.pid!=android.os.Process.myPid())android.os.Process.killProcess(p.pid);
  failures+=DataWiper.clear(new File(getApplicationInfo().dataDir),true);
  if(Build.VERSION.SDK_INT>=24){
   android.content.Context device=createDeviceProtectedStorageContext();
   if(!device.getDataDir().equals(getDataDir()))failures+=DataWiper.clear(device.getDataDir(),true);
  }
  for(File f:getExternalCacheDirs())if(f!=null)failures+=DataWiper.clear(f,false);
  for(File f:getExternalFilesDirs(null))if(f!=null)failures+=DataWiper.clear(f,false);
  showResult();
 }} ,"mint-data-reset").start();}
 private void showResult(){runOnUiThread(new Runnable(){public void run(){
  if(failures==0){reopen();return;}
  new AlertDialog.Builder(ResetActivity.this).setTitle("Limpeza incompleta").setMessage("Alguns arquivos ainda estão em uso. Você pode tentar novamente antes de reabrir.").setCancelable(false).setPositiveButton("Tentar novamente",new DialogInterface.OnClickListener(){public void onClick(DialogInterface d,int n){startCleanup();}}).setNegativeButton("Reabrir",new DialogInterface.OnClickListener(){public void onClick(DialogInterface d,int n){reopen();}}).show();
 }});}
 private void reopen(){
  Intent launch=getPackageManager().getLaunchIntentForPackage(getPackageName());
  if(launch==null){Toast.makeText(this,"Abra o navegador pelo ícone do aplicativo.",Toast.LENGTH_LONG).show();finish();return;}
  launch.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK|Intent.FLAG_ACTIVITY_CLEAR_TASK);
  startActivity(launch);finish();new Handler(Looper.getMainLooper()).postDelayed(new Runnable(){public void run(){android.os.Process.killProcess(android.os.Process.myPid());}},700);
 }
}
