import diagnostic.*;
import java.io.*;
import java.util.*;
public class AdvancedTest {
 static int count;
 static void ok(boolean b,String why){count++;if(!b)throw new AssertionError(why);}
 static byte[] reply(int rcode,boolean truncated,boolean address)throws Exception{
  byte[] q=DnsWire.query("example.com",1,0x1234);q[2]=(byte)(truncated?0x83:0x81);q[3]=(byte)(0x80|rcode);q[7]=(byte)(address?1:0);
  ByteArrayOutputStream b=new ByteArrayOutputStream();b.write(q);
  if(address){DataOutputStream d=new DataOutputStream(b);d.writeShort(0xc00c);d.writeShort(1);d.writeShort(1);d.writeInt(300);d.writeShort(4);d.write(new byte[]{93,(byte)184,(byte)216,34});}
  return b.toByteArray();
 }
 interface Throwing {void run()throws Exception;}
 static void reject(Throwing r,String s)throws Exception{boolean bad=false;try{r.run();}catch(Exception e){bad=true;}ok(bad,s);}
 public static void main(String[] args)throws Exception{
  ok(DnsWire.host("https://EXAMPLE.com/path?secret=1").equals("example.com"),"host extraction");
  reject(new Throwing(){public void run(){DnsWire.host("example.com\r\nX: value");}},"header injection accepted");
  reject(new Throwing(){public void run(){DnsWire.host("https://user:pass@example.com");}},"credentials accepted");
  DnsWire.Reply good=DnsWire.parse(reply(0,false,true),"example.com",1,0x1234);
  ok(good.addresses.equals(Arrays.asList("93.184.216.34")),"A answer");ok(good.answers.get(0).ttl==300,"TTL");
  ok(DnsWire.parse(reply(3,false,false),"example.com",1,0x1234).rcode==3,"NXDOMAIN");
  ok(DnsWire.parse(reply(2,false,false),"example.com",1,0x1234).rcode==2,"SERVFAIL");
  reject(new Throwing(){public void run()throws Exception{DnsWire.parse(reply(0,false,true),"example.com",1,8);}},"wrong transaction accepted");
  reject(new Throwing(){public void run()throws Exception{DnsWire.parse(reply(0,false,true),"other.com",1,0x1234);}},"wrong question accepted");
  reject(new Throwing(){public void run()throws Exception{byte[] b=reply(0,false,true);b[29]=(byte)0xc0;b[30]=29;DnsWire.parse(b,"example.com",1,0x1234);}},"pointer loop accepted");
  byte[] tc=reply(0,true,false);tc[7]=1;
  ok(DnsWire.parse(tc,"example.com",1,0x1234).truncated,"truncated reply must allow TCP fallback");
  byte[] body=reply(0,false,true);ByteArrayOutputStream http=new ByteArrayOutputStream();http.write(("HTTP/1.1 200 OK\r\nContent-Type: application/dns-message\r\nContent-Length: "+body.length+"\r\n\r\n").getBytes("US-ASCII"));http.write(body);
  ok(Arrays.equals(HttpWire.read(new ByteArrayInputStream(http.toByteArray()),true).body,body),"DoH content-length");
  http.reset();http.write(("HTTP/1.1 200 OK\r\nContent-Type: application/dns-message\r\nTransfer-Encoding: chunked\r\n\r\n"+Integer.toHexString(body.length)+"\r\n").getBytes("US-ASCII"));http.write(body);http.write("\r\n0\r\n\r\n".getBytes("US-ASCII"));
  ok(Arrays.equals(HttpWire.read(new ByteArrayInputStream(http.toByteArray()),true).body,body),"chunked DoH");
  reject(new Throwing(){public void run()throws Exception{HttpWire.read(new ByteArrayInputStream("HTTP/1.1 200 OK\r\nContent-Type: text/html\r\nContent-Length: 0\r\n\r\n".getBytes("US-ASCII")),true);}},"HTML considered DNS");
  reject(new Throwing(){public void run()throws Exception{HttpWire.read(new ByteArrayInputStream("HTTP/1.1 200 OK\r\nContent-Type: application/dns-message\r\nContent-Length: 999999\r\n\r\n".getBytes("US-ASCII")),true);}},"unbounded body accepted");
  List<Findings.DnsFact> dns=new ArrayList<Findings.DnsFact>();List<Findings.TransportFact> net=new ArrayList<Findings.TransportFact>();
  Findings.DnsFact sys=new Findings.DnsFact("system","SYSTEM","A+AAAA");dns.add(sys);
  Findings.DnsFact local=new Findings.DnsFact("local","DNS_UDP","A");local.rcode=3;dns.add(local);
  Findings.DnsFact ref=new Findings.DnsFact("google","DOH","A");ref.rcode=0;ref.ips.add("1.2.3.4");dns.add(ref);
  String findings=Findings.evaluate(dns,net,false,false,false).toString();ok(findings.contains("DIVERGENCIA_DNS_SISTEMA")&&findings.contains("DIVERGENCIA_NXDOMAIN"),"DNS divergence missing");ok(!findings.contains("bloqueio comprovado"),"unsupported censorship attribution");
  net.add(new Findings.TransportFact("1.2.3.4",443,"TCP","OK",0));net.add(new Findings.TransportFact("::1",443,"TCP","TIMEOUT",0));net.add(new Findings.TransportFact("1.2.3.4",443,"TLS","CERTIFICATE_ERROR",0));
  findings=Findings.evaluate(dns,net,true,true,false).toString();ok(findings.contains("DIFERENCA_IPV4_IPV6")&&findings.contains("CERTIFICADO_REJEITADO")&&findings.contains("REDE_MUDOU")&&findings.contains("INCOMPLETO"),"transport findings missing");
  sys.ips.add("1.2.3.4");ok(Findings.evaluate(dns,net,false,false,true).toString().contains("WEBVIEW_DIVERGE_DO_SISTEMA"),"WebView comparison");
  System.out.println("PASS: "+count+" assertions (DNS packets, mismatch/loop/truncation, HTTP framing, hostname validation and bounded causal conclusions)");
 }
}
