package diagnostic;

import android.app.*;
import android.content.*;
import android.content.pm.PackageInfo;
import android.net.*;
import android.net.http.SslError;
import android.os.*;
import android.provider.Settings;
import android.view.*;
import android.webkit.*;
import android.widget.*;
import android.graphics.Color;
import android.graphics.drawable.GradientDrawable;
import java.io.*;
import java.lang.ref.WeakReference;
import java.lang.reflect.*;
import java.util.*;
import org.json.JSONObject;

public final class Recorder implements Application.ActivityLifecycleCallbacks {
    private static final int SAVE = 27927, LIMIT = 6 * 1024 * 1024;
    private static final Handler MAIN = new Handler(Looper.getMainLooper());
    private static final WeakHashMap<Activity, Button> BUTTONS = new WeakHashMap<Activity, Button>();
    private static final WeakHashMap<WebView, String> STATES = new WeakHashMap<WebView, String>();
    private static WeakReference<Activity> foreground = new WeakReference<Activity>(null);
    private static StringBuilder lines = new StringBuilder();
    private static boolean active, installed, capped;
    private static String pending, session;
    private static Application app;
    private static long start;
    private static String target="888pg.cc";

    public static synchronized void init(Application a) {
        if (installed) return;
        installed = true; app = a;
        a.registerActivityLifecycleCallbacks(new Recorder());
    }
    private static boolean browser(Activity a) {
        for (Class<?> c=a.getClass(); c!=null; c=c.getSuperclass())
            if (c.getName().equals("com.miui.org.chromium.chrome.browser.ChromeActivity")) return true;
        return false;
    }
    private static synchronized boolean recording() { return active; }
    private static synchronized void event(String type, String detail) {
        if (!active) return;
        if (lines.length() > LIMIT) {
            if (!capped) { capped=true; lines.append("{\"event\":\"LIMIT\",\"detail\":\"Limite de 6 MiB atingido; desative e salve.\"}\n"); }
            return;
        }
        try {
            JSONObject j=new JSONObject();
            java.text.SimpleDateFormat fmt=new java.text.SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ss.SSS'Z'", Locale.US);
            fmt.setTimeZone(TimeZone.getTimeZone("UTC")); j.put("time_utc",fmt.format(new Date()));
            j.put("elapsed_ms",SystemClock.elapsedRealtime()-start);
            j.put("event",type); j.put("detail",detail);
            lines.append(j.toString()).append('\n');
        } catch (Exception ignored) {}
    }
    public static synchronized void probeEvent(String token,String type,JSONObject data) {
        if(!active || !token.equals(session)) return;
        try { JSONObject j=new JSONObject(); j.put("time_utc_ms",System.currentTimeMillis()); j.put("elapsed_ms",SystemClock.elapsedRealtime()-start); j.put("event",type); j.put("data",data);
            if(lines.length()<LIMIT) lines.append(j.toString()).append('\n');
        } catch(Exception ignored){}
    }
    private static void chooseTarget(final Activity a) {
        final EditText input=new EditText(a); input.setSingleLine(true); input.setInputType(android.text.InputType.TYPE_CLASS_TEXT|android.text.InputType.TYPE_TEXT_VARIATION_URI);input.setText(target);
        final AlertDialog dialog=new AlertDialog.Builder(a).setTitle("Diagnóstico avançado V2").setMessage("Informe o domínio. Testes de DNS, TCP, TLS e GET / serão feitos nesta conexão, sem login. Google e Cloudflare receberão consultas DNS do domínio. Aguarde até 45 s, reproduza o erro e desative para salvar. Pressione o botão por mais tempo para ver os resultados.").setView(input).setPositiveButton("Ativar",null).setNegativeButton("Cancelar",null).create();
        dialog.setOnShowListener(new DialogInterface.OnShowListener(){public void onShow(DialogInterface d){dialog.getButton(AlertDialog.BUTTON_POSITIVE).setOnClickListener(new View.OnClickListener(){public void onClick(View v){try{target=DnsWire.host(input.getText().toString());dialog.dismiss();begin(a);}catch(IllegalArgumentException e){input.setError(e.getMessage());}}});}});dialog.show();
    }
    public static String origin(String value) {
        if(value==null) return "null";
        try { Uri u=Uri.parse(value); String s=u.getScheme(), h=u.getHost();
            if(h!=null) return s+"://"+h+(u.getPort()<0?"":":"+u.getPort());
            return s==null?"[endereco omitido]":s+":";
        } catch(Exception e) { return "[endereco omitido]"; }
    }
    public static void page(WebView w, String url) { if(recording()) event("PAGE",origin(url)); }
    public static void started(WebView w,String url) { if(recording()) event("PAGE_STARTED",origin(url)); }
    public static void finished(WebView w,String url) { if(recording()) event("PAGE_FINISHED",origin(url)); }
    public static void commit(WebView w,String url) { if(recording()) event("PAGE_COMMIT",origin(url)); }
    public static void resource(WebView w, String url) { if(recording()) event("RESOURCE",origin(url)); }
    public static void error(WebView w, int code, String description, String url) {
        if(recording()) {event("WEB_ERROR", "code="+code+" origin="+origin(url)+" chromium="+chromium(description)); Probe.browserError(url,code);}
    }
    private static String chromium(String text) {if(text==null)return "unknown";java.util.regex.Matcher m=java.util.regex.Pattern.compile("(?:net::)?ERR_[A-Z0-9_]+").matcher(text);return m.find()?m.group():"unknown";}
    public static void ssl(WebView w, SslErrorHandler h, SslError e) {
        if(!recording()) return;
        try { event("TLS_ERROR","primary="+e.getPrimaryError()+" origin="+origin(e.getUrl())); }
        catch(Exception ignored) {}
    }
    public static void request(WebView w, WebResourceRequest r) {
        if(!recording()) return;
        try { event("REQUEST","method="+r.getMethod()+" main_frame="+r.isForMainFrame()+" origin="+origin(r.getUrl().toString())); }
        catch(Exception ignored) {}
    }
    public static void http(WebView w, WebResourceRequest r, WebResourceResponse response) {
        if(!recording()) return;
        try { event("HTTP_ERROR","status="+response.getStatusCode()+" main_frame="+r.isForMainFrame()+" origin="+origin(r.getUrl().toString())); }
        catch(Exception ignored) {}
    }
    public static void modernError(WebView w, WebResourceRequest r, WebResourceError e) {
        if(!recording()) return;
        try { event("WEB_ERROR","code="+e.getErrorCode()+" main_frame="+r.isForMainFrame()+" origin="+origin(r.getUrl().toString())+" chromium="+chromium(String.valueOf(e.getDescription()))); Probe.browserError(r.getUrl().toString(),e.getErrorCode()); }
        catch(Exception ignored) {}
    }
    private static void updateButtons() {
        for(Button b:new ArrayList<Button>(BUTTONS.values())) if(b!=null) {
            b.setText(recording()?"Desativar":"Ativar diagnóstico");
            GradientDrawable d=new GradientDrawable(); d.setCornerRadius(28);
            d.setColor(recording()?0xffa51d27:0xff075b83); b.setBackground(d);
        }
    }
    private static void begin(Activity a) {
        Probe.cancel();
        synchronized(Recorder.class) {
            lines=new StringBuilder(); pending=null; capped=false; STATES.clear();
            start=SystemClock.elapsedRealtime(); session="mint-diagnostico-"+System.currentTimeMillis(); active=true;
        }
        updateButtons();
        event("START", "diagnostic_version=2; target="+target+"; session="+session+"; gravacao local; sem senhas, cookies, cabecalhos, texto digitado, caminhos ou parametros de URL; toques e rolagem sem conteudo; nao captura pacotes nem todo trafego interno");
        event("DEVICE","manufacturer="+Build.MANUFACTURER+" model="+Build.MODEL+" android="+Build.VERSION.RELEASE+" api="+Build.VERSION.SDK_INT);
        try { PackageInfo p=app.getPackageManager().getPackageInfo(app.getPackageName(),0); event("APP","package="+app.getPackageName()+" version="+p.versionName); } catch(Exception ignored) {}
        try { if(Build.VERSION.SDK_INT>=26) { PackageInfo p=WebView.getCurrentWebViewPackage(); event("WEBVIEW",p==null?"unknown":p.packageName+" "+p.versionName); } } catch(Throwable ignored) {}
        try { event("PRIVATE_DNS","mode="+Settings.Global.getString(app.getContentResolver(),"private_dns_mode")+" host="+Settings.Global.getString(app.getContentResolver(),"private_dns_specifier")); } catch(Exception e) { event("PRIVATE_DNS","unavailable"); }
        network(); MAIN.removeCallbacks(POLL); MAIN.post(POLL);
        if(app!=null && Build.VERSION.SDK_INT>=24) {
            try { Probe.start(app,target,session,new Probe.Sink(){
                public void emit(String token,String type,JSONObject data){probeEvent(token,type,data);}
                public void finished(final String token,String summary){MAIN.post(new Runnable(){public void run(){Activity a=foreground.get();if(a!=null&&recording()&&token.equals(session))Toast.makeText(a,"Sondas encerradas. Mantenha Desativar pressionado para ver o relatório.",Toast.LENGTH_LONG).show();}});}
            }); } catch(Exception e){event("PROBE_START_ERROR",e.getClass().getName());}
        } else event("PROBE_UNAVAILABLE","Sondas avançadas requerem Android 7/API 24 ou superior");
        Toast.makeText(a,"Diagnóstico ativado. Reproduza o problema e toque em Desativar.",Toast.LENGTH_LONG).show();
    }
    private static void stop(Activity a) {
        Probe.cancel();
        event("STOP","gravacao encerrada pelo usuario");
        synchronized(Recorder.class) { active=false; pending=lines.toString(); }
        MAIN.removeCallbacks(POLL); updateButtons();
        try {
            Intent i=new Intent(Intent.ACTION_CREATE_DOCUMENT);
            i.addCategory(Intent.CATEGORY_OPENABLE); i.setType("text/plain");
            i.putExtra(Intent.EXTRA_TITLE,session+".jsonl");
            a.startActivityForResult(i,SAVE);
        } catch(Exception e) {
            new AlertDialog.Builder(a).setTitle("Não foi possível abrir o seletor")
                .setMessage("O log continua na memória. Tentar salvar novamente?")
                .setPositiveButton("Salvar",new DialogInterface.OnClickListener(){ public void onClick(DialogInterface d,int w){stop(a);} })
                .setNegativeButton("Cancelar",null).show();
        }
    }
    public static boolean result(final Activity a,int code,int result,Intent data) {
        if(code!=SAVE) return false;
        if(result!=Activity.RESULT_OK || data==null || data.getData()==null) {
            new AlertDialog.Builder(a).setTitle("Log não salvo").setMessage("Tentar escolher o destino novamente? Ativar outra sessão descartará este log.")
                .setPositiveButton("Salvar",new DialogInterface.OnClickListener(){public void onClick(DialogInterface d,int w){stop(a);}})
                .setNegativeButton("Cancelar",null).show();
            return true;
        }
        final Uri uri=data.getData(); final String output;
        synchronized(Recorder.class) { output=pending; }
        if(output==null) { Toast.makeText(a,"Não há log pendente.",Toast.LENGTH_LONG).show(); return true; }
        new Thread(new Runnable(){ public void run(){
            String message;
            try { OutputStream os=a.getContentResolver().openOutputStream(uri,"wt");
                if(os==null) throw new IOException("no output");
                try { os.write(output.getBytes("UTF-8")); } finally { os.close(); }
                message="Log salvo.";
            } catch(Exception e) { message="Falha ao salvar. O log continua na memória; mantenha pressionado Ativar para tentar novamente."; }
            final String msg=message; MAIN.post(new Runnable(){public void run(){ Toast.makeText(a,msg,Toast.LENGTH_LONG).show(); }});
        }},"diagnostic-export").start();
        return true;
    }
    private static void network() {
        try {
            ConnectivityManager cm=(ConnectivityManager)app.getSystemService(Context.CONNECTIVITY_SERVICE);
            if(Build.VERSION.SDK_INT<23) { android.net.NetworkInfo info=cm.getActiveNetworkInfo(); event("NETWORK",info==null?"no active network":"type="+info.getTypeName()+" connected="+info.isConnected()); return; }
            Network n=cm.getActiveNetwork(); NetworkCapabilities c=cm.getNetworkCapabilities(n);
            event("NETWORK",c==null?"no active network":"wifi="+c.hasTransport(NetworkCapabilities.TRANSPORT_WIFI)+" cellular="+c.hasTransport(NetworkCapabilities.TRANSPORT_CELLULAR)+" vpn="+c.hasTransport(NetworkCapabilities.TRANSPORT_VPN)+" internet="+c.hasCapability(NetworkCapabilities.NET_CAPABILITY_INTERNET)+" validated="+c.hasCapability(NetworkCapabilities.NET_CAPABILITY_VALIDATED));
            LinkProperties lp=cm.getLinkProperties(n);
            if(lp!=null) { event("DNS_SERVERS",lp.getDnsServers().toString());
                if(Build.VERSION.SDK_INT>=28) event("DNS_STATUS","private_active="+lp.isPrivateDnsActive()+" private_host="+lp.getPrivateDnsServerName()); }
        } catch(Exception e) { event("NETWORK","unavailable: "+e.getClass().getSimpleName()); }
    }
    private static final Runnable POLL=new Runnable(){ int ticks;
        public void run(){
            if(!recording())return;
            Activity a=foreground.get();
            if(a!=null) scan(a.getWindow().getDecorView());
            if(ticks++%8==0)network();
            MAIN.postDelayed(this,1000);
        }
    };
    private static void scan(View v) {
        try {
            if(v instanceof WebView) {
                WebView w=(WebView)v; String s=origin(w.getUrl())+" progress="+w.getProgress()+" loading="+(w.getProgress()<100)+" back="+w.canGoBack();
                if(!s.equals(STATES.get(w))) {
                    STATES.put(w,s); event("WEBVIEW_STATE",s);
                    event("WEBVIEW_SETTINGS","javascript="+w.getSettings().getJavaScriptEnabled()+" cache_mode="+w.getSettings().getCacheMode()+" user_agent="+w.getSettings().getUserAgentString());
                }
            }
            if(v instanceof ViewGroup) { ViewGroup g=(ViewGroup)v; for(int i=0;i<g.getChildCount();i++)scan(g.getChildAt(i)); }
        } catch(Exception ignored) {}
    }
    private static void attach(final Activity a) {
        if(!browser(a)||BUTTONS.containsKey(a))return;
        try {
            final Button b=new Button(a); b.setTextColor(Color.WHITE); b.setTextSize(12); b.setAllCaps(false);
            int dp=(int)(a.getResources().getDisplayMetrics().density*12);
            b.setPadding(dp,dp/2,dp,dp/2); if(Build.VERSION.SDK_INT>=21) b.setElevation(dp);
            FrameLayout.LayoutParams p=new FrameLayout.LayoutParams(-2,-2,Gravity.RIGHT|Gravity.CENTER_VERTICAL);
            p.rightMargin=dp; a.addContentView(b,p); BUTTONS.put(a,b); updateButtons();
            b.setOnClickListener(new View.OnClickListener(){public void onClick(View v){if(recording())stop(a);else chooseTarget(a);}});
            b.setOnLongClickListener(new View.OnLongClickListener(){public boolean onLongClick(View v){if(recording())new AlertDialog.Builder(a).setTitle("Diagnóstico V2 — "+target).setMessage(Probe.describe()).setPositiveButton("Continuar",null).setNegativeButton("Desativar e salvar",new DialogInterface.OnClickListener(){public void onClick(DialogInterface d,int w){stop(a);}}).show();else if(pending!=null)stop(a);return true;}});
            b.setOnTouchListener(new View.OnTouchListener(){float x,y,bx,by;boolean moved;
                public boolean onTouch(View v,MotionEvent e){
                    if(e.getActionMasked()==MotionEvent.ACTION_DOWN){x=e.getRawX();y=e.getRawY();bx=v.getTranslationX();by=v.getTranslationY();moved=false;}
                    else if(e.getActionMasked()==MotionEvent.ACTION_MOVE){float dx=e.getRawX()-x,dy=e.getRawY()-y;if(Math.abs(dx)+Math.abs(dy)>18)moved=true;if(moved){v.setTranslationX(bx+dx);v.setTranslationY(by+dy);return true;}}
                    else if(e.getActionMasked()==MotionEvent.ACTION_UP&&moved)return true;
                    return false;
                }});
            final Window.Callback original=a.getWindow().getCallback();
            Window.Callback wrapper=(Window.Callback)java.lang.reflect.Proxy.newProxyInstance(Window.Callback.class.getClassLoader(),new Class<?>[]{Window.Callback.class},new InvocationHandler(){
                float downX,downY;
                public Object invoke(Object proxy,Method m,Object[] args)throws Throwable{
                    if(recording()&&m.getName().equals("dispatchTouchEvent")&&args!=null&&args[0] instanceof MotionEvent){
                        MotionEvent e=(MotionEvent)args[0];
                        if(e.getActionMasked()==MotionEvent.ACTION_DOWN){downX=e.getX();downY=e.getY();}
                        if(e.getActionMasked()==MotionEvent.ACTION_UP)event("TOUCH",Math.abs(e.getX()-downX)+Math.abs(e.getY()-downY)>24?"swipe":"tap");
                    }
                    try{return m.invoke(original,args);}catch(InvocationTargetException e){throw e.getCause();}
                }});
            a.getWindow().setCallback(wrapper);
        } catch(Throwable e) { Toast.makeText(a,"Falha ao adicionar diagnóstico: "+e.getClass().getSimpleName(),Toast.LENGTH_LONG).show(); }
    }
    public void onActivityCreated(final Activity a,Bundle b){if(browser(a))MAIN.post(new Runnable(){public void run(){attach(a);}});}
    public void onActivityResumed(Activity a){if(browser(a)){foreground=new WeakReference<Activity>(a);attach(a);event("LIFECYCLE","browser resumed");}}
    public void onActivityPaused(Activity a){if(foreground.get()==a)foreground.clear();if(browser(a))event("LIFECYCLE","browser paused");}
    public void onActivityDestroyed(Activity a){BUTTONS.remove(a);}
    public void onActivityStarted(Activity a){}
    public void onActivityStopped(Activity a){}
    public void onActivitySaveInstanceState(Activity a,Bundle b){}
}
