package com.mint.rebuilt;
import android.webkit.*;
import java.io.*;
public final class PageScripts {
 private static String source="";
 public static void init(WebView view){
  if(source.length()>0)return;
  try{InputStream in=view.getContext().getAssets().open("mint-rebuilt.js");ByteArrayOutputStream out=new ByteArrayOutputStream();byte[] b=new byte[4096];int n;while((n=in.read(b))!=-1)out.write(b,0,n);in.close();source=out.toString("UTF-8");}catch(Exception e){android.util.Log.e("MintRebuilt","Não foi possível carregar o script",e);}
 }
 public static void install(WebView view){
  init(view);
  if(source.length()==0)return;
  try{
   // Use the WebView support boundary already shipped by this APK.
   Class<?> loader=Class.forName("androidx.webkit.c.e");
   java.lang.reflect.Method getter=loader.getDeclaredMethod("d");getter.setAccessible(true);
   Object adapter=getter.invoke(null);
   java.lang.reflect.Field field=adapter.getClass().getDeclaredField("a");field.setAccessible(true);
   Object factory=field.get(adapter);
   Class<?> factoryType=Class.forName("org.chromium.support_lib_boundary.WebViewProviderFactoryBoundaryInterface");
   String[] features=(String[])factoryType.getMethod("getSupportedFeatures").invoke(factory);
   boolean supported=false;for(String feature:features)if(feature.equals("DOCUMENT_START_SCRIPT")||feature.equals("DOCUMENT_START_SCRIPT:1"))supported=true;
   if(!supported)return;
   java.lang.reflect.InvocationHandler handler=(java.lang.reflect.InvocationHandler)factoryType.getMethod("createWebView",WebView.class).invoke(factory,view);
   Class<?> api=Class.forName("org.chromium.support_lib_boundary.WebViewProviderBoundaryInterface");
   Object provider=java.lang.reflect.Proxy.newProxyInstance(api.getClassLoader(),new Class<?>[]{api},handler);
   api.getMethod("addDocumentStartJavaScript",String.class,String[].class).invoke(provider,source,new String[]{"*"});
  }catch(Throwable e){android.util.Log.i("MintRebuilt","WebView sem injeção antecipada; usando eventos de página");}
 }
 public static String script(){return source;}
 public static void apply(WebView view){if(view==null)return;init(view);if(source.length()>0)try{view.evaluateJavascript(source,null);}catch(Exception e){android.util.Log.e("MintRebuilt","Não foi possível aplicar o script",e);}}
}
