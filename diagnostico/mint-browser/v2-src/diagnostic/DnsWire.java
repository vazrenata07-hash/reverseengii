package diagnostic;

import java.io.*;
import java.net.*;
import java.util.*;

/** Bounded DNS wire codec. Validates transaction, question and compressed names. */
public final class DnsWire {
    public static final int MAX = 8192;
    public static final class Answer {
        public String name, value; public int type; public long ttl;
        public String toString(){return name+" type="+type+" ttl="+ttl+" value="+value;}
    }
    public static final class Reply {
        public int rcode; public boolean truncated, authenticated;
        public final List<Answer> answers=new ArrayList<Answer>();
        public final List<String> addresses=new ArrayList<String>();
        public String outcome(){return rcodeName(rcode)+(truncated?" TRUNCATED":"")+(addresses.isEmpty()?" NO_ADDRESS":" ADDRESS");}
    }
    public static String host(String value) {
        if(value==null)throw new IllegalArgumentException("Informe o domínio");
        String s=value.trim();
        if(s.contains("://")) {
            try { URI u=new URI(s); if(!"https".equalsIgnoreCase(u.getScheme())&&!"http".equalsIgnoreCase(u.getScheme()))throw new Exception();
                if(u.getUserInfo()!=null)throw new Exception(); s=u.getHost();
            } catch(Exception e){throw new IllegalArgumentException("Use um domínio ou endereço HTTP/HTTPS sem credenciais");}
        }
        if(s==null)throw new IllegalArgumentException("Domínio inválido");
        if(s.endsWith("."))s=s.substring(0,s.length()-1);
        try{s=IDN.toASCII(s,IDN.USE_STD3_ASCII_RULES).toLowerCase(Locale.US);}catch(Exception e){throw new IllegalArgumentException("Domínio inválido");}
        if(s.length()==0||s.length()>253||s.indexOf('.')<0||s.matches("[0-9.]+"))throw new IllegalArgumentException("Informe um domínio completo, sem porta ou IP");
        for(String label:s.split("\\.",-1))if(label.length()==0||label.length()>63||!label.matches("[a-z0-9](?:[a-z0-9-]*[a-z0-9])?"))throw new IllegalArgumentException("Domínio inválido");
        return s;
    }
    public static byte[] query(String host,int type,int id)throws IOException {
        host=host(host);
        if(type!=1&&type!=28)throw new IOException("unsupported qtype");
        ByteArrayOutputStream bytes=new ByteArrayOutputStream();DataOutputStream out=new DataOutputStream(bytes);
        out.writeShort(id);out.writeShort(0x0100);out.writeShort(1);out.writeShort(0);out.writeShort(0);out.writeShort(0);
        for(String label:host.split("\\.")){byte[] b=label.getBytes("US-ASCII");out.writeByte(b.length);out.write(b);}
        out.writeByte(0);out.writeShort(type);out.writeShort(1);return bytes.toByteArray();
    }
    private static int u16(byte[] b,int o)throws IOException {if(o<0||o+2>b.length)throw new IOException("short DNS packet");return ((b[o]&255)<<8)|(b[o+1]&255);}
    private static long u32(byte[] b,int o)throws IOException{return ((long)u16(b,o)<<16)|u16(b,o+2);}
    private static String name(byte[] b,int[] pos)throws IOException {
        int at=pos[0],next=-1,hops=0,length=0;StringBuilder out=new StringBuilder();Set<Integer> seen=new HashSet<Integer>();
        while(true){
            if(at<0||at>=b.length||!seen.add(at)||++hops>128)throw new IOException("invalid DNS name/pointer loop");
            int n=b[at++]&255;
            if((n&0xc0)==0xc0){if(at>=b.length)throw new IOException("short pointer");int to=((n&63)<<8)|(b[at++]&255);if(to>=at-2)throw new IOException("forward DNS pointer");if(next<0)next=at;at=to;continue;}
            if((n&0xc0)!=0||n>63)throw new IOException("invalid DNS label");
            if(n==0){pos[0]=next<0?at:next;return out.toString().toLowerCase(Locale.US);}
            if(at+n>b.length||(length+=n+1)>254)throw new IOException("invalid DNS name size");
            if(out.length()>0)out.append('.');
            for(int j=0;j<n;j++){int c=b[at++]&255;if(c<=32||c>=127)throw new IOException("non-ASCII DNS label");out.append((char)c);}
        }
    }
    public static Reply parse(byte[] b,String host,int type,int id)throws IOException {
        if(b.length<12||b.length>MAX)throw new IOException("invalid DNS packet size");
        if(u16(b,0)!=(id&65535))throw new IOException("DNS transaction mismatch");
        int flags=u16(b,2);
        if((flags&0x8000)==0||(flags&0x7800)!=0)throw new IOException("not a standard DNS response");
        if(u16(b,4)!=1)throw new IOException("DNS question count mismatch");
        int[] p={12};String question=name(b,p);
        if(!question.equalsIgnoreCase(host(host))||u16(b,p[0])!=type||u16(b,p[0]+2)!=1)throw new IOException("DNS question mismatch");
        p[0]+=4;Reply r=new Reply();r.rcode=flags&15;r.truncated=(flags&0x200)!=0;r.authenticated=(flags&0x20)!=0;
        if(r.truncated)return r;
        int answers=u16(b,6),authority=u16(b,8),extra=u16(b,10);
        if(answers+authority+extra>512)throw new IOException("too many DNS records");
        for(int i=0;i<answers+authority+extra;i++){
            String owner=name(b,p);int t=u16(b,p[0]),cl=u16(b,p[0]+2);long ttl=u32(b,p[0]+4);int len=u16(b,p[0]+8);p[0]+=10;
            int end=p[0]+len;if(end>b.length)throw new IOException("short DNS record");
            if(i<answers&&cl==1){
                Answer a=new Answer();a.name=owner;a.type=t;a.ttl=ttl;
                if(t==1&&len==4||t==28&&len==16){a.value=InetAddress.getByAddress(Arrays.copyOfRange(b,p[0],end)).getHostAddress();}
                else if(t==5){int[] q={p[0]};a.value=name(b,q);if(q[0]!=end)throw new IOException("invalid CNAME length");}
                if(a.value!=null)r.answers.add(a);
            }
            p[0]=end;
        }
        // Only addresses for the queried owner or its answer CNAME chain are usable.
        Set<String> owners=new HashSet<String>();owners.add(host(host));
        for(int loop=0;loop<r.answers.size();loop++)for(Answer a:r.answers)if(a.type==5&&owners.contains(a.name))owners.add(a.value);
        if(r.rcode==0&&!r.truncated)for(Answer a:r.answers)if(a.type==type&&owners.contains(a.name)&&!r.addresses.contains(a.value))r.addresses.add(a.value);
        return r;
    }
    public static String rcodeName(int r){switch(r){case 0:return "NOERROR";case 1:return "FORMERR";case 2:return "SERVFAIL";case 3:return "NXDOMAIN";case 4:return "NOTIMP";case 5:return "REFUSED";default:return "RCODE_"+r;}}
    public static String hex(byte[] b){StringBuilder s=new StringBuilder();for(byte v:b)s.append(String.format(Locale.US,"%02x",v&255));return s.toString();}
}
