package com.mint.rebuilt;
import android.content.*;
import android.database.Cursor;
import android.database.sqlite.*;
import android.net.Uri;
import android.webkit.JavascriptInterface;

/** Local counter only. No account, cookie, navigation, or transaction methods. */
public final class WagerStore {
 private static final Object LOCK=new Object();
 private static Database helper;
 private volatile boolean enabled;
 public WagerStore(Context context){synchronized(LOCK){if(helper==null)helper=new Database(context.getApplicationContext());}}
 public void allow(String url){
  boolean valid=false;
  try{Uri uri=Uri.parse(url==null?"":url);String host=uri.getHost();valid=host!=null&&(host.equalsIgnoreCase("888pg.cc")||host.toLowerCase(java.util.Locale.US).endsWith(".888pg.cc"))&&("https".equals(uri.getScheme())||"http".equals(uri.getScheme()));}catch(Exception ignored){}
  enabled=valid;
 }
 @JavascriptInterface public String total(){
  if(!enabled)return "{\"error\":true}";
  synchronized(LOCK){try{return summary(helper.getReadableDatabase());}catch(Exception e){return "{\"error\":true}";}}
 }
 @JavascriptInterface public String record(String game,String round,long milli){
  if(!enabled||!"jdb-mines-9014".equals(game)||round==null||!round.matches("[0-9]{1,24}")||milli<=0||milli>1000000000L)return "{\"error\":true}";
  synchronized(LOCK){SQLiteDatabase db=null;boolean transaction=false;try{
   db=helper.getWritableDatabase();db.beginTransaction();transaction=true;
   ContentValues values=new ContentValues();values.put("round_key",game+":"+round);values.put("milli",milli);
   long added=db.insertWithOnConflict("rounds",null,values,SQLiteDatabase.CONFLICT_IGNORE);
   if(added!=-1)db.execSQL("UPDATE totals SET milli=milli+? WHERE id=1",new Object[]{milli});
   String result=summary(db);db.setTransactionSuccessful();return result;
  }catch(Exception e){return "{\"error\":true}";}finally{if(transaction&&db!=null)db.endTransaction();}}
 }
 private static String summary(SQLiteDatabase db){Cursor c=db.rawQuery("SELECT milli FROM totals WHERE id=1",null);try{return "{\"milli\":"+(c.moveToFirst()?c.getLong(0):0)+"}";}finally{c.close();}}
 private static final class Database extends SQLiteOpenHelper {
  Database(Context c){super(c,"mint_wager_counter.db",null,1);}
  public void onCreate(SQLiteDatabase db){db.execSQL("CREATE TABLE rounds(round_key TEXT PRIMARY KEY,milli INTEGER NOT NULL)");db.execSQL("CREATE TABLE totals(id INTEGER PRIMARY KEY,milli INTEGER NOT NULL)");db.execSQL("INSERT INTO totals(id,milli) VALUES(1,0)");}
  public void onUpgrade(SQLiteDatabase db,int oldVersion,int newVersion){}
 }
}
