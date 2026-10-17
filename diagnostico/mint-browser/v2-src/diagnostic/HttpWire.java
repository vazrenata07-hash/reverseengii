package diagnostic;
import java.io.*;
import java.util.*;

/** Minimal bounded HTTP/1.1 response reader for diagnostic probes, never a browser replacement. */
public final class HttpWire {
    public static final class Response {
        public int status;
        public final Map<String,String> headers=new LinkedHashMap<String,String>();
        public byte[] body;
    }
    private static String line(InputStream in,int max)throws IOException {
        ByteArrayOutputStream out=new ByteArrayOutputStream();int c;
        while((c=in.read())!=-1){if(c=='\n'){byte[] b=out.toByteArray();int n=b.length;if(n>0&&b[n-1]=='\r')n--;return new String(b,0,n,"ISO-8859-1");}if(out.size()>=max)throw new IOException("HTTP line too long");out.write(c);}
        throw new EOFException("HTTP line incomplete");
    }
    private static byte[] exact(InputStream in,int n)throws IOException {
        if(n<0||n>DnsWire.MAX)throw new IOException("HTTP body too large");
        byte[] b=new byte[n];int at=0;
        while(at<n){int got=in.read(b,at,n-at);if(got<0)throw new EOFException("HTTP body incomplete");at+=got;}
        return b;
    }
    public static Response read(InputStream input,boolean dnsBody)throws IOException {
        InputStream in=input instanceof BufferedInputStream?input:new BufferedInputStream(input);
        Response r=null;
        for(int interim=0;interim<4;interim++){
            r=new Response();String status=line(in,4096);
            if(!status.matches("HTTP/1\\.[01] [1-5][0-9][0-9](?: .*)?"))throw new IOException("invalid HTTP status");
            r.status=Integer.parseInt(status.substring(9,12));int bytes=status.length();
            for(int count=0;;count++){
                String h=line(in,8192);bytes+=h.length()+2;if(bytes>32768||count>128)throw new IOException("HTTP headers too large");
                if(h.length()==0)break;int colon=h.indexOf(':');if(colon<1)throw new IOException("invalid HTTP header");
                String key=h.substring(0,colon).toLowerCase(Locale.US),value=h.substring(colon+1).trim();
                if(r.headers.containsKey(key))value=r.headers.get(key)+","+value;r.headers.put(key,value);
            }
            if(r.status<100||r.status>=200||r.status==101)break;
            if(interim==3)throw new IOException("too many interim HTTP responses");
        }
        if(!dnsBody||r.status!=200)return r;
        String contentType=r.headers.get("content-type");
        if(contentType==null||!contentType.toLowerCase(Locale.US).split(";",2)[0].trim().equals("application/dns-message"))throw new IOException("unexpected DoH content-type");
        String encoding=r.headers.get("content-encoding");if(encoding!=null&&!encoding.equalsIgnoreCase("identity"))throw new IOException("unexpected HTTP content encoding");
        String transfer=r.headers.get("transfer-encoding"),length=r.headers.get("content-length");
        if(transfer!=null&&length!=null)throw new IOException("ambiguous HTTP body framing");
        if(transfer!=null){
            if(!transfer.equalsIgnoreCase("chunked"))throw new IOException("unsupported transfer encoding");
            ByteArrayOutputStream out=new ByteArrayOutputStream();
            while(true){String l=line(in,256).split(";",2)[0].trim();int n;
                try{n=Integer.parseInt(l,16);}catch(Exception e){throw new IOException("invalid HTTP chunk size");}
                if(n<0||n>DnsWire.MAX-out.size())throw new IOException("HTTP body too large");
                if(n==0){for(int count=0;count<64;count++)if(line(in,8192).length()==0){r.body=out.toByteArray();return r;}throw new IOException("too many HTTP trailers");}
                out.write(exact(in,n));if(!line(in,2).equals(""))throw new IOException("invalid HTTP chunk end");
            }
        } else if(length!=null){try{r.body=exact(in,Integer.parseInt(length));}catch(NumberFormatException e){throw new IOException("invalid content-length");}}
        else{ByteArrayOutputStream out=new ByteArrayOutputStream();byte[] b=new byte[1024];int n;while((n=in.read(b))!=-1){if(n>DnsWire.MAX-out.size())throw new IOException("HTTP body too large");out.write(b,0,n);}r.body=out.toByteArray();}
        return r;
    }
    public static void get(OutputStream out,String host)throws IOException {
        out.write(("GET / HTTP/1.1\r\nHost: "+DnsWire.host(host)+"\r\nUser-Agent: Mint-Diagnostic/2\r\nAccept: */*\r\nAccept-Encoding: identity\r\nRange: bytes=0-0\r\nConnection: close\r\n\r\n").getBytes("US-ASCII"));out.flush();
    }
    public static void doh(OutputStream out,String host,byte[] query)throws IOException {
        out.write(("POST /dns-query HTTP/1.1\r\nHost: "+DnsWire.host(host)+"\r\nContent-Type: application/dns-message\r\nAccept: application/dns-message\r\nAccept-Encoding: identity\r\nContent-Length: "+query.length+"\r\nConnection: close\r\n\r\n").getBytes("US-ASCII"));out.write(query);out.flush();
    }
}
