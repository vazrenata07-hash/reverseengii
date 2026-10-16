package com.mint.rebuilt;
import java.io.File;
public final class DataWiper {
 public static int clear(File directory,boolean keepNativeLibrary){
  try{
   File root=directory.getCanonicalFile();
   if(!root.exists())return 0;
   File[] children=root.listFiles();if(children==null)return 1;
   int failures=0;
   for(File child:children)if(!keepNativeLibrary||!child.getName().equals("lib"))failures+=erase(child,root);
   return failures;
  }catch(Exception e){return 1;}
 }
 private static int erase(File file,File root){
  try{
   String real=file.getCanonicalPath(),absolute=file.getAbsolutePath();
   // Delete a link itself, never anything it points at, inside or outside the profile.
   if(!real.equals(absolute))return file.delete()?0:1;
   if(!real.startsWith(root.getPath()+File.separator))return 1;
   int failures=0;
   if(file.isDirectory()){
    File[] children=file.listFiles();if(children==null)return 1;
    for(File child:children)failures+=erase(child,root);
   }
   if(!file.delete())failures++;
   return failures;
  }catch(Exception e){return 1;}
 }
}
