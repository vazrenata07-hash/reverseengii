package diagnostic;

import android.content.Context;
import android.net.*;
import android.os.Build;
import android.os.SystemClock;
import java.io.*;
import java.net.*;
import java.security.*;
import java.security.cert.X509Certificate;
import java.util.*;
import java.util.concurrent.*;
import javax.net.ssl.*;
import org.json.*;

public final class Probe {
    public interface Sink { void emit(String session,String type,JSONObject data); void finished(String session,String summary); }
    private static final ExecutorService WORKERS=Executors.newFixedThreadPool(4);
    private static final ScheduledExecutorService TIMER=Executors.newSingleThreadScheduledExecutor();
    private static volatile Run current;
    public static void start(Context c,String host,String session,Sink sink) {
        cancel(); Run r=new Run(c,DnsWire.host(host),session,sink);current=r;r.launch();
    }
    public static void cancel(){Run r=current;if(r!=null)r.finish(true);}
    public static String describe(){Run r=current;return r==null?"Sem rodada ativa":r.description;}
    public static void browserError(String url,int code){Run r=current;if(r!=null&&code==-2)try{if(r.host.equalsIgnoreCase(new URI(url).getHost()))r.observeBrowserDns();}catch(Exception ignored){}}
    static JSONObject json(Object... kv){JSONObject j=new JSONObject();try{for(int i=0;i<kv.length;i+=2)j.put((String)kv[i],kv[i+1]);}catch(Exception ignored){}return j;}
    static String exception(Throwable e){StringBuilder s=new StringBuilder();for(int n=0;e!=null&&n<4;n++,e=e.getCause()){if(n>0)s.append(" <- ");String m=e.getMessage();s.append(e.getClass().getName()).append(": ").append(m==null?"":m.substring(0,Math.min(500,m.length())));}return s.toString();}
    static boolean certificateError(Throwable e){for(int n=0;e!=null&&n<8;n++,e=e.getCause())if(e instanceof java.security.cert.CertificateException||e instanceof SSLPeerUnverifiedException||e.getClass().getName().contains("CertPath"))return true;return false;}
    private static final class Run {
        final String host,session; final Sink sink; final ConnectivityManager cm;final Network network;final String initialNetwork;
        final List<InetAddress> servers=new ArrayList<InetAddress>();
        final List<Findings.DnsFact> dns=new ArrayList<Findings.DnsFact>();
        final List<Findings.TransportFact> transport=new ArrayList<Findings.TransportFact>();
        final List<Closeable> sockets=new ArrayList<Closeable>();final List<Future<?>> jobs=new ArrayList<Future<?>>();
        final Map<String,String> candidates=new LinkedHashMap<String,String>();
        volatile boolean done,browserDnsFailure; boolean finalInterrupted,finalRouteChanged;volatile String description="Testes em andamento. Aguarde até 45 segundos.";
        int dnsPending,ipPending;ScheduledFuture<?> deadline;
        Run(Context context,String h,String s,Sink k){host=h;session=s;sink=k;
            cm=(ConnectivityManager)context.getSystemService(Context.CONNECTIVITY_SERVICE);
            Network n=null;if(Build.VERSION.SDK_INT>=23){n=cm.getBoundNetworkForProcess();if(n==null)n=cm.getActiveNetwork();}network=n;initialNetwork=networkId();
        }
        String networkId(){try{if(Build.VERSION.SDK_INT<23)return "legacy-default";Network n=cm.getBoundNetworkForProcess();if(n==null)n=cm.getActiveNetwork();return String.valueOf(n);}catch(Exception e){return "unavailable:"+e.getClass().getSimpleName();}}
        synchronized void emit(String type,JSONObject data){if(!done)sink.emit(session,type,data);}
        synchronized void register(Closeable socket)throws IOException{if(done){socket.close();throw new InterruptedIOException("diagnostic canceled");}sockets.add(socket);}
        synchronized void close(Closeable socket){sockets.remove(socket);try{socket.close();}catch(Exception ignored){}}
        synchronized void check()throws IOException{if(done||Thread.currentThread().isInterrupted())throw new InterruptedIOException("diagnostic canceled");}
        void launch(){
            emit("PROBE_START",json("version",2,"host",host,"network",initialNetwork,"deadline_ms",45000,"scope","explicit domain; DNS A/AAAA, GET / only; no cookies; original browser requests unchanged","doh_references","dns.google via 8.8.8.8; cloudflare-dns.com via 1.1.1.1; hostname/TLS validation enabled"));
            try{if(network!=null){LinkProperties lp=cm.getLinkProperties(network);NetworkCapabilities caps=cm.getNetworkCapabilities(network);
                if(lp!=null){servers.addAll(lp.getDnsServers());emit("PROBE_NETWORK",json("network",initialNetwork,"interface",lp.getInterfaceName(),"dns_servers",new JSONArray(servers),"routes",String.valueOf(lp.getRoutes()),"proxy",String.valueOf(lp.getHttpProxy()),"capabilities",String.valueOf(caps),"private_dns",Build.VERSION.SDK_INT>=28?lp.isPrivateDnsActive():JSONObject.NULL,"private_dns_host",Build.VERSION.SDK_INT>=28?lp.getPrivateDnsServerName():JSONObject.NULL));}
            }}catch(Exception e){emit("NETWORK_ERROR",json("error",exception(e)));}
            synchronized(this){dnsPending=1+Math.min(servers.size(),4)*2+4;
                deadline=TIMER.schedule(new Runnable(){public void run(){finish(true);}},45,TimeUnit.SECONDS);
                submitDns(new Runnable(){public void run(){systemDns();}});
                for(int i=0;i<Math.min(servers.size(),4);i++)for(final int q:new int[]{1,28}){final InetAddress server=servers.get(i);submitDns(new Runnable(){public void run(){directDns(server,q);}});}
                for(final int q:new int[]{1,28}){submitDns(new Runnable(){public void run(){doh("dns.google","8.8.8.8",q);}});submitDns(new Runnable(){public void run(){doh("cloudflare-dns.com","1.1.1.1",q);}});}
            }
        }
        void submitDns(final Runnable task){jobs.add(WORKERS.submit(new Runnable(){public void run(){try{if(!done)task.run();}catch(Throwable e){emit("PROBE_INTERNAL_ERROR",json("error",e.getClass().getName()));}finally{dnsFinished();}}}));}
        synchronized void addDns(Findings.DnsFact f){if(done)return;dns.add(f);for(String ip:f.ips)if(!candidates.containsKey(ip))candidates.put(ip,f.source);}
        void systemDns(){long t=SystemClock.elapsedRealtime();Findings.DnsFact f=new Findings.DnsFact("android-process-default","SYSTEM","A+AAAA");
            try{check();for(InetAddress a:InetAddress.getAllByName(host))f.ips.add(a.getHostAddress());f.outcome=f.ips.isEmpty()?"EMPTY":"OK";emit("SYSTEM_DNS",json("host",host,"resolver",f.source,"ips",new JSONArray(f.ips),"elapsed_ms",SystemClock.elapsedRealtime()-t,"note","Android resolver may use cache/private DNS; does not reveal upstream packet or server"));}
            catch(Exception e){f.outcome="ERROR";emit("SYSTEM_DNS",json("host",host,"outcome","ERROR","error",exception(e),"elapsed_ms",SystemClock.elapsedRealtime()-t));}addDns(f);
        }
        byte[] direct(InetAddress server,byte[] q,boolean tcp)throws Exception{
            if(!tcp){DatagramSocket socket=new DatagramSocket();register(socket);
                try{if(network!=null)network.bindSocket(socket);socket.setSoTimeout(1800);socket.connect(server,53);socket.send(new DatagramPacket(q,q.length));byte[] buf=new byte[DnsWire.MAX];DatagramPacket p=new DatagramPacket(buf,buf.length);socket.receive(p);return Arrays.copyOfRange(p.getData(),p.getOffset(),p.getOffset()+p.getLength());}finally{close(socket);}}
            Socket socket=socket(server,53);try{DataOutputStream out=new DataOutputStream(socket.getOutputStream());out.writeShort(q.length);out.write(q);out.flush();DataInputStream in=new DataInputStream(socket.getInputStream());int len=in.readUnsignedShort();if(len>DnsWire.MAX||len<12)throw new IOException("invalid DNS TCP length");byte[] b=new byte[len];in.readFully(b);return b;}finally{close(socket);}
        }
        void directDns(InetAddress server,int type){String path="DNS_UDP";long t=SystemClock.elapsedRealtime();Findings.DnsFact f=new Findings.DnsFact(server.getHostAddress(),path,type==1?"A":"AAAA");
            try{check();int id=new SecureRandom().nextInt(65536);byte[] q=DnsWire.query(host,type,id),b=direct(server,q,false);DnsWire.Reply r=DnsWire.parse(b,host,type,id);
                dnsEvent(f,r,b,t);if(r.truncated){path="DNS_TCP";f=new Findings.DnsFact(server.getHostAddress(),path,type==1?"A":"AAAA");b=direct(server,q,true);r=DnsWire.parse(b,host,type,id);dnsEvent(f,r,b,t);}
                f.rcode=r.rcode;f.ips.addAll(r.addresses);f.outcome=r.outcome();
            }catch(Exception e){f.outcome="ERROR";emit("DNS_QUERY_ERROR",json("host",host,"server",server.getHostAddress(),"port",53,"transport",path,"qtype",f.family,"error",exception(e),"elapsed_ms",SystemClock.elapsedRealtime()-t,"note","direct port 53 diagnostic; does not prove the browser used this server"));}addDns(f);
        }
        void dnsEvent(Findings.DnsFact f,DnsWire.Reply r,byte[] raw,long t){JSONArray answers=new JSONArray();for(DnsWire.Answer a:r.answers)answers.put(json("name",a.name,"type",a.type,"ttl",a.ttl,"value",a.value));
            emit("DNS_REPLY",json("host",host,"server",f.source,"transport",f.transport,"qtype",f.family,"rcode",r.rcode,"rcode_name",DnsWire.rcodeName(r.rcode),"truncated",r.truncated,"ad_flag",r.authenticated,"addresses",new JSONArray(r.addresses),"answers",answers,"elapsed_ms",SystemClock.elapsedRealtime()-t,"wire_hex",DnsWire.hex(raw),"scope",f.transport.equals("DOH")?"independent TLS-authenticated resolver":"explicit configured server, not intercepted browser DNS"));
        }
        void doh(String name,String ip,int type){long t=SystemClock.elapsedRealtime();Findings.DnsFact f=new Findings.DnsFact(name,"DOH",type==1?"A":"AAAA");Socket raw=null;SSLSocket tls=null;
            try{check();int id=new SecureRandom().nextInt(65536);byte[] q=DnsWire.query(host,type,id);raw=socket(InetAddress.getByName(ip),443);tls=tls(raw,name);HttpWire.doh(tls.getOutputStream(),name,q);HttpWire.Response h=HttpWire.read(tls.getInputStream(),true);if(h.status!=200)throw new IOException("DoH HTTP status "+h.status);
                DnsWire.Reply r=DnsWire.parse(h.body,host,type,id);f.rcode=r.rcode;f.ips.addAll(r.addresses);f.outcome=r.outcome();dnsEvent(f,r,h.body,t);
            }catch(Exception e){f.outcome="ERROR";emit("DOH_ERROR",json("host",host,"provider",name,"bootstrap_ip",ip,"qtype",f.family,"error",exception(e),"elapsed_ms",SystemClock.elapsedRealtime()-t));}
            finally{if(tls!=null)close(tls);if(raw!=null)close(raw);}addDns(f);
        }
        Socket socket(InetAddress ip,int port)throws Exception{check();Socket s=new Socket();register(s);try{if(network!=null)network.bindSocket(s);s.setSoTimeout(4000);s.connect(new InetSocketAddress(ip,port),3500);return s;}catch(Exception e){close(s);throw e;}}
        SSLSocket tls(Socket raw,String peer)throws Exception{
            check();SSLSocket s=(SSLSocket)((SSLSocketFactory)SSLSocketFactory.getDefault()).createSocket(raw,peer,443,true);register(s);
            try{SSLParameters p=s.getSSLParameters();p.setEndpointIdentificationAlgorithm("HTTPS");if(Build.VERSION.SDK_INT>=24)p.setServerNames(Collections.singletonList(new SNIHostName(peer)));s.setSSLParameters(p);s.setSoTimeout(4000);s.startHandshake();return s;}catch(Exception e){close(s);throw e;}
        }
        synchronized void dnsFinished(){if(done)return;if(--dnsPending!=0)return;
            List<String> chosen=new ArrayList<String>();int v4=0,v6=0;
            for(String ip:candidates.keySet()){if(ip.contains(":")){if(v6++<2)chosen.add(ip);}else if(v4++<2)chosen.add(ip);}
            emit("IP_SELECTION",json("candidates",new JSONArray(candidates.keySet()),"tested",new JSONArray(chosen),"limit","max 2 IPv4 + 2 IPv6; addresses obtained from system/configured DNS/DoH, source logged"));
            if(chosen.isEmpty()){finish(false);return;}ipPending=chosen.size()*2;
            for(final String ip:chosen)for(final int port:new int[]{80,443})jobs.add(WORKERS.submit(new Runnable(){public void run(){try{if(!done)endpoint(ip,port);}finally{ipFinished();}}}));
        }
        synchronized void fact(String ip,int port,String stage,String outcome,int code){if(!done)transport.add(new Findings.TransportFact(ip,port,stage,outcome,code));}
        void endpoint(String ip,int port){Socket raw=null;SSLSocket secure=null;long t=SystemClock.elapsedRealtime();String stage="TCP";
            try{check();raw=socket(InetAddress.getByName(ip),port);fact(ip,port,"TCP","OK",0);emit("TCP_RESULT",json("ip",ip,"family",ip.contains(":")?"IPv6":"IPv4","port",port,"outcome","OK","dns_source",candidates.get(ip),"elapsed_ms",SystemClock.elapsedRealtime()-t,"local_ip",raw.getLocalAddress().getHostAddress(),"network",initialNetwork));
                Socket stream=raw;
                if(port==443){stage="TLS";t=SystemClock.elapsedRealtime();secure=tls(raw,host);stream=secure;SSLSession ss=secure.getSession();JSONArray certs=new JSONArray();
                    for(java.security.cert.Certificate cert:ss.getPeerCertificates())if(cert instanceof X509Certificate){X509Certificate c=(X509Certificate)cert;certs.put(json("subject",c.getSubjectX500Principal().getName(),"issuer",c.getIssuerX500Principal().getName(),"not_before_utc_ms",c.getNotBefore().getTime(),"not_after_utc_ms",c.getNotAfter().getTime(),"sha256",DnsWire.hex(MessageDigest.getInstance("SHA-256").digest(c.getEncoded()))));}
                    fact(ip,port,"TLS","OK",0);emit("TLS_RESULT",json("ip",ip,"sni",host,"hostname_verification",true,"outcome","OK","protocol",ss.getProtocol(),"cipher",ss.getCipherSuite(),"certificates",certs,"elapsed_ms",SystemClock.elapsedRealtime()-t));}
                stage=port==443?"HTTPS":"HTTP";t=SystemClock.elapsedRealtime();HttpWire.get(stream.getOutputStream(),host);HttpWire.Response h=HttpWire.read(stream.getInputStream(),false);
                fact(ip,port,stage,"OK",h.status);emit("HTTP_RESULT",json("ip",ip,"scheme",stage.toLowerCase(Locale.US),"port",port,"host",host,"path","/","status",h.status,"server",h.headers.get("server"),"content_type",h.headers.get("content-type"),"location_origin",safeLocation(h.headers.get("location")),"elapsed_ms",SystemClock.elapsedRealtime()-t,"note","synthetic GET /; no cookies or original URL path; no redirect following; body not captured"));
            }catch(Exception e){String outcome=certificateError(e)?"CERTIFICATE_ERROR":e instanceof SocketTimeoutException?"TIMEOUT":done?"CANCELED":"ERROR";fact(ip,port,stage,outcome,0);emit(stage+"_ERROR",json("ip",ip,"port",port,"host",host,"outcome",outcome,"error",exception(e),"elapsed_ms",SystemClock.elapsedRealtime()-t));}
            finally{if(secure!=null)close(secure);if(raw!=null)close(raw);}
        }
        String safeLocation(String location){if(location==null)return null;try{return Recorder.origin(new URI("https://"+host+"/").resolve(location).toString());}catch(Exception e){return "[omitted]";}}
        synchronized void observeBrowserDns(){
            if(browserDnsFailure)return;browserDnsFailure=true;
            if(done){List<String> findings=Findings.evaluate(new ArrayList<Findings.DnsFact>(dns),new ArrayList<Findings.TransportFact>(transport),finalRouteChanged,finalInterrupted,true);
                StringBuilder text=new StringBuilder();for(String f:findings)text.append("• ").append(f).append("\n\n");description=text.toString();
                sink.emit(session,"DIAGNOSIS_WEBVIEW_UPDATE",json("host",host,"findings",new JSONArray(findings),"note","WebView error observed after active probes; measurements may differ in time"));
            }
        }
        synchronized void ipFinished(){if(!done&&--ipPending==0)finish(false);}
        synchronized void finish(boolean interrupted){if(done)return;
            boolean changed=!initialNetwork.equals(networkId());finalRouteChanged=changed;finalInterrupted=interrupted;List<String> findings=Findings.evaluate(new ArrayList<Findings.DnsFact>(dns),new ArrayList<Findings.TransportFact>(transport),changed,interrupted,browserDnsFailure);
            StringBuilder text=new StringBuilder();for(String f:findings)text.append("• ").append(f).append("\n\n");description=text.toString();
            emit("DIAGNOSIS",json("host",host,"complete",!interrupted,"initial_network",initialNetwork,"current_network",networkId(),"network_changed",changed,"dns_results",dns.size(),"transport_results",transport.size(),"findings",new JSONArray(findings),"limits","active independent probes; no packet interception; actual Chromium DNS upstream not observable; no claim of censorship from DNS divergence alone"));
            done=true;if(deadline!=null)deadline.cancel(false);for(Future<?> f:jobs)f.cancel(true);
            for(Closeable s:new ArrayList<Closeable>(sockets))try{s.close();}catch(Exception ignored){}sockets.clear();
            sink.finished(session,description);
        }
    }
}
