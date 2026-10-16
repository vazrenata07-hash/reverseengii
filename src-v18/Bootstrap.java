package com.mint.rebuilt;
import android.app.*;
import android.content.*;
import android.view.*;
import android.widget.*;
import java.io.*;
public final class Bootstrap {
 private static boolean gateVisible;
 public static boolean isResetProcess(){
  try {FileInputStream in=new FileInputStream("/proc/self/cmdline");byte[] b=new byte[256];int n=in.read(b);in.close();return n>0&&new String(b,0,n,"UTF-8").contains(":mintreset");}catch(Exception e){return false;}
 }
 private static int dp(Activity a,int n){return (int)(n*a.getResources().getDisplayMetrics().density+0.5f);}
 public static void attach(final Activity a){
  if(a==null||a.isFinishing()||isResetProcess())return;
  a.getWindow().getDecorView().post(new Runnable(){public void run(){
   if(a.isFinishing())return;
   if(!gateVisible&&!a.getSharedPreferences("mint_rebuilt",0).getBoolean("code_entered",false))showGate(a);
  }});
 }
 public static void reset(Activity a){
  Intent reset=new Intent(a,ResetActivity.class);
  reset.putExtra("browser_pid",android.os.Process.myPid());
  a.startActivity(reset);
 }
 private static void showGate(final Activity a){
  gateVisible=true;
  final EditText input=new EditText(a);input.setInputType(2);input.setSingleLine(true);input.setHint("Código de indicação ou 0");input.setPadding(dp(a,20),dp(a,12),dp(a,20),dp(a,12));
  final AlertDialog dialog=new AlertDialog.Builder(a).setTitle("Código de acesso").setMessage("Digite 0 para abrir o site ou informe o código de indicação.").setView(input).setCancelable(false).setPositiveButton("Abrir",null).create();
  dialog.setOnDismissListener(new DialogInterface.OnDismissListener(){public void onDismiss(DialogInterface d){gateVisible=false;}});dialog.show();
  dialog.getButton(-1).setOnClickListener(new View.OnClickListener(){public void onClick(View v){
   String code=input.getText().toString().trim();
   if(!code.equals("0")&&!code.matches("[0-9]{7,}")){input.setError("Use 0 ou um código com pelo menos 7 dígitos.");return;}
   String url=code.equals("0")?"https://888pg.cc/":"https://888pg.cc/home/register?id="+code;
   Intent open=new Intent(Intent.ACTION_VIEW,android.net.Uri.parse(url));open.setPackage(a.getPackageName());
   try{a.startActivity(open);a.getSharedPreferences("mint_rebuilt",0).edit().putBoolean("code_entered",true).commit();dialog.dismiss();}catch(Exception e){input.setError("Não foi possível abrir. Tente novamente.");}
  }});
 }
}
