import pyperclip
import sys
import os
#from markdown import markdown
#from bs4 import BeautifulSoup
import re
import glob
import requests
import queue
from datetime import date
import time
import subprocess
import threading

            
    

def get_download_file_name():
    file_name = time.strftime("GetUpdateDescription-%Y%m%d-%H%M%S.txt")
    return file_name

def get_update_description_main(techcontent_dir,filelist_path):
    
    os.chdir(techcontent_dir)
    print("techcontent_dir" + techcontent_dir)
    
    file = open(filelist_path,"r",encoding="utf8")
    filelist = file.read().split("\n")
    file.close()
    
    mdlist = [x for x in filelist if x[len(x)-3:]==".md"]

    record_file = open(get_download_file_name(),'w',encoding="utf8")

    reEx = r"(\s*<!--\s*Update_Description\s*:\s*)(\s*.+)+(\s*-->\s*)"

    record_file.write("Path\tArticle\tUpdate_Description\n")
    

    for filepath in mdlist:

        filepath=filepath.replace("\\","/")
        print("Processing " + filepath)

        checkfile = open(filepath,"r",encoding="utf8")
        mdcontent = checkfile.read()
        match = re.search(reEx ,mdcontent,re.I|re.M)
      
        path, name = os.path.split(filepath)
        if match:
            record_file.write("%s\t%s\t%s\n" % (path,name,match.group(2)))
        else: 
            print("%s Not find Description." % (name))
            record_file.write("%s\t%s\t%s\n" % (path,name,"NOT Find Description"))

    record_file.close()

    

if __name__ == '__main__':
    filepath = "articles/azure-resource-manager/resource-group-audit.md"
    mooncake_path = "E:/gitrep/techcontent"
    mooncake_path = mooncake_path.replace("\\","/")
    os.chdir(mooncake_path)
    get_update_description_main(mooncake_path,filepath)