import diagnostic.Recorder;
import java.lang.reflect.*;
public class RecorderV2Test {
 static Field field(String name)throws Exception {Field f=Recorder.class.getDeclaredField(name);f.setAccessible(true);return f;}
 static void check(boolean b,String message){if(!b)throw new AssertionError(message);}
 public static void main(String[] args)throws Exception {
  Field active=field("active"),lines=field("lines");
  StringBuilder buffer=(StringBuilder)lines.get(null);
  Recorder.page(null,"https://example.com/before");
  check(buffer.length()==0,"Recorded while inactive");
  active.setBoolean(null,true);
  Recorder.page(null,"https://user:password@example.com/private-path?token=SECRET#fragment");
  Recorder.error(null,-2,"password=SECRET", "https://example.com/private?token=SECRET");
  String log=buffer.toString();
  check(new org.json.JSONObject(log.split("\n")[0]).getString("detail").equals("https://example.com"),"Missing destination");
  check(log.contains("code=-2"),"Missing error code");
  check(!log.contains("SECRET")&&!log.contains("password")&&!log.contains("private")&&!log.contains("fragment"),"Sensitive data retained");
  active.setBoolean(null,false);int length=buffer.length();
  Recorder.resource(null,"https://after.example.com");
  check(buffer.length()==length,"Recorded after stopping");
  active.setBoolean(null,true);
  buffer.setLength(6*1024*1024+1);
  Recorder.page(null,"https://limit.example.com");int capped=buffer.length();
  Recorder.page(null,"https://overflow.example.com");
  check(buffer.length()==capped,"Buffer continues growing after cap");
  field("pending").set(null,"OLD_SESSION_SECRET");
  Method begin=Recorder.class.getDeclaredMethod("begin",android.app.Activity.class);begin.setAccessible(true);begin.invoke(null,new Object[]{null});
  check(active.getBoolean(null),"New session not active");
  check(field("pending").get(null)==null,"Previous export not discarded");
  String fresh=lines.get(null).toString();
  check(fresh.contains("START")&&!fresh.contains("example.com")&&!fresh.contains("OLD_SESSION_SECRET"),"Prior session retained");
  int initial=fresh.length();
  Recorder.probeEvent("old-token","TEST",new org.json.JSONObject());
  check(lines.get(null).toString().length()==initial,"Old probe leaked into new session");
  Recorder.probeEvent((String)field("session").get(null),"TEST_CURRENT",new org.json.JSONObject());
  check(lines.get(null).toString().contains("TEST_CURRENT"),"Current probe rejected");
  active.setBoolean(null,false);int stopped=lines.get(null).toString().length();
  Recorder.probeEvent((String)field("session").get(null),"TEST_STOPPED",new org.json.JSONObject());
  check(lines.get(null).toString().length()==stopped,"Stopped probe appended log");
  System.out.println("PASS: probe session isolation;  new session resets log and pending export;  inactive capture disabled; destination retained; credentials/path/query/fragment and error text omitted; stopped capture disabled; buffer limit enforced.");
 }
}
