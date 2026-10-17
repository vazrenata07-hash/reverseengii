package diagnostic;
import java.util.*;

/** Conclusions restricted to the observed tests; divergent DNS does not establish censorship. */
public final class Findings {
    public static final class DnsFact {
        public String source,transport,family,outcome;public int rcode=-1;public List<String> ips=new ArrayList<String>();
        public DnsFact(String s,String t,String f){source=s;transport=t;family=f;}
    }
    public static final class TransportFact {
        public String ip,stage,outcome;public int port,status;public boolean v6;
        public TransportFact(String i,int p,String s,String o,int code){ip=i;port=p;stage=s;outcome=o;status=code;v6=i.indexOf(':')>=0;}
    }
    public static List<String> evaluate(List<DnsFact> dns,List<TransportFact> net,boolean routeChanged,boolean interrupted,boolean browserDnsFailure) {
        List<String> out=new ArrayList<String>();
        boolean sysTried=false,sysGood=false,refGood=false,refA=false,refAAAA=false,localNegative=false,refSplit=false;
        Map<String,Set<String>> referenceByType=new HashMap<String,Set<String>>();
        for(DnsFact d:dns){
            if(d.transport.equals("SYSTEM")){sysTried=true;if(!d.ips.isEmpty())sysGood=true;}
            if(d.transport.equals("DOH")){
                if(!d.ips.isEmpty()){refGood=true;if(d.family.equals("A"))refA=true;if(d.family.equals("AAAA"))refAAAA=true;}
                if(d.rcode>=0){Set<String> statuses=referenceByType.get(d.family);if(statuses==null){statuses=new HashSet<String>();referenceByType.put(d.family,statuses);}statuses.add(d.rcode==3?"NXDOMAIN":!d.ips.isEmpty()?"ADDRESS":"OTHER");}
            }
        }
        for(Set<String> statuses:referenceByType.values())if(statuses.contains("NXDOMAIN")&&statuses.contains("ADDRESS"))refSplit=true;
        for(DnsFact d:dns)if(d.transport.startsWith("DNS_")&&d.rcode==3&&(d.family.equals("A")&&refA||d.family.equals("AAAA")&&refAAAA))localNegative=true;
        if(routeChanged)out.add("REDE_MUDOU: a rede padrão mudou durante a rodada; não comparar resultados como se fossem da mesma conexão.");
        if(interrupted)out.add("INCOMPLETO: rodada interrompida ou prazo esgotado; testes ausentes não passaram nem falharam.");
        if(sysTried&&!sysGood&&refGood)out.add("DIVERGENCIA_DNS_SISTEMA: a resolução do sistema falhou, mas uma referência DoH autenticada retornou IP. A falha está no caminho de resolução do sistema nesta rodada; não prova bloqueio da operadora.");
        if(localNegative)out.add("DIVERGENCIA_NXDOMAIN: um DNS configurado respondeu NXDOMAIN e uma referência DoH retornou IP para o mesmo tipo. Divergência comprovada; cache, política e DNS dividido ainda precisam ser diferenciados.");
        if(refSplit)out.add("REFERENCIAS_DIVERGEM: as referências DoH discordam entre NXDOMAIN e endereço; não tratar uma única referência como verdade absoluta.");
        if(!sysGood&&!refGood)out.add("DNS_INCONCLUSIVO: não houve IP pela resolução do sistema nem pelas referências; consultar os RCODEs e erros de transporte. Não é prova de domínio inexistente.");
        if(sysGood&&browserDnsFailure)out.add("WEBVIEW_DIVERGE_DO_SISTEMA: WebView retornou ERROR_HOST_LOOKUP apesar de a sonda do sistema resolver. Investigar cache, resolvedor próprio e instante/rede do navegador.");
        boolean ipv4Good=false,ipv6Good=false,ipv6Fail=false,httpsGood=false,certFail=false,httpDenied=false;
        for(TransportFact f:net){
            if(f.stage.equals("TCP")&&f.port==443){if(f.outcome.equals("OK")){if(f.v6)ipv6Good=true;else ipv4Good=true;}else if(!f.outcome.equals("CANCELED")){if(f.v6)ipv6Fail=true;}}
            if(f.stage.equals("TLS")&&f.outcome.equals("CERTIFICATE_ERROR"))certFail=true;
            if(f.stage.equals("HTTPS")&&f.outcome.equals("OK"))httpsGood=true;
            if((f.stage.equals("HTTP")||f.stage.equals("HTTPS"))&&(f.status==403||f.status==451))httpDenied=true;
        }
        if(ipv4Good&&ipv6Fail&&!ipv6Good)out.add("DIFERENCA_IPV4_IPV6: TCP/443 funcionou em IPv4 e falhou nos IPv6 testados. É uma diferença de conectividade; não prova que o WebView escolheu IPv6.");
        if(certFail)out.add("CERTIFICADO_REJEITADO: houve conexão TCP seguida de rejeição na validação TLS com hostname/SNI original; ver exceção e IP. A validação não foi desativada.");
        if(httpDenied)out.add("RECUSA_HTTP: a sonda recebeu HTTP 403 ou 451. Houve resposta HTTP; o status sozinho não identifica quem impôs a restrição.");
        if(httpsGood)out.add("HTTPS_RAIZ_RESPONDEU: pelo menos um IP aceitou TCP, TLS validado e respondeu HTTP para GET /. Isso não valida login, caminho original, JavaScript ou recursos da página.");
        if(out.isEmpty())out.add("SEM_CAUSA_UNICA: consultar DNS e os estágios TCP/TLS/HTTP; não houve evidência suficiente para atribuir uma causa raiz.");
        return out;
    }
}
