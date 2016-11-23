import pyperclip
import sys
import os
from markdown import markdown
from bs4 import BeautifulSoup
import re
import glob
import requests
import threading
import queue
from datetime import datetime
import subprocess

article_list = {}

include_reg = r"(?P<includeText>\[AZURE\.INCLUDE\s\[[^\[|^\]]*\]\(\.\./\.\./includes/(?P<fileName>[\w|\-]+(\.md)?)\)\])"
headers = {'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8', 'Accept-Encoding': 'gzip, deflate', 'Connection': 'keep-alive', 'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; WOW64; rv:49.0) Gecko/20100101 Firefox/49.0', 'Accept-Language': 'en-US,en;q=0.5', 'Upgrade-Insecure-Requests': '1'}

def copy_relative_path(file_path):
    pyperclip.copy(file_path)
    
def copy_file_name(file_path):
    pyperclip.copy(os.path.basename(file_path))

def get_article_list(tech_content_path):
    if article_list == {}:
        mdlist1 = glob.glob(tech_content_path + "articles/*.md")
        mdlist2 = glob.glob(tech_content_path + "articles/**/*.md")
        for md in mdlist1:
            path = md.replace("\\","/")
            filename = os.path.basename(path)
            article_list[filename] = path
        for md in mdlist2:
            path = md.replace("\\","/")
            filename = os.path.basename(path)
            article_list[filename] = path

def check_broken_link(file_path, tech_content_path):
    messages = check_broken_link_queque(file_path, tech_content_path)
    while not messages.empty():
        print(messages.get())


def check_broken_link_queque(file_path, tech_content_path):
    messages = queue.Queue()
    get_article_list(tech_content_path)
    mdfile = open(file_path, encoding="utf8")
    mdcontent = mdfile.read()
    mdfile.close()
    htmlcontent = markdown(mdcontent)
    soup = BeautifulSoup(htmlcontent,"html.parser")
    refs = []
    for a in soup.find_all("a"):
        ref = a.get("href")
        if ref != None and ref not in refs:
            refs.append(ref.strip())
    for img in soup.find_all("img"):
        src = img.get("src")
        if src != None and src not in refs:
            refs.append("{%image%}"+src.strip())
    handle_hrefs(refs, mdcontent, file_path, tech_content_path, messages)
    return messages

def handle_hrefs(refs, mdcontent, file_path, tech_content_path, messages):
    threads=[]
    for ref in refs:
        t = None
        if len(ref) == 0:
            messages.put("Broken Link: empty link")
        elif ref[:5] == "http:" or ref[:6] == "https:":
            t = threading.Thread(target=_handle_full, args=[ref, messages])
        elif ref[0] == "/":
            t = threading.Thread(target=_handle_relative, args=[ref, tech_content_path, messages])
        elif ref[0] == "#":
            t = threading.Thread(target=_handle_inpage, args=[ref, mdcontent, tech_content_path, True, messages])
        elif ref[:9] == "{%image%}":
            t = threading.Thread(target=_handle_image, args=[ref[9:], file_path, messages])
        elif "../includes/" in ref:
            continue
        else:
            messages.put("Broken Link: "+ref)
        if t != None:
            threads.append(t)
            t.start()
    for t in threads:
         t.join()

def _handle_image(ref, file_path, messages):
    if ref[:5] == "http:" or ref[:6] == "https:":
        _handle_full(ref, messages)
    elif ref[0] == ".":
        _handle_relative_image(ref, file_path, messages)
    else:
        messages.put("Broken Image: "+ref)

def _handle_relative_image(ref, file_path, messages):
    path = os.path.dirname(file_path)+"/"+ref
    if not _isfile_casesensitive(path):
        messages.put("Broken Image: "+ref)

def _isfile_casesensitive(path):
    if not os.path.isfile(path): return False
    directory, filename = os.path.split(path)
    return filename in os.listdir(directory)

def _handle_full(ref, messages):
    if ref[:16] == "http://localhost" or ref[:17] == "https://localhost":
        return
    try:
        response = requests.get(ref, stream=True, headers=headers)
        while response.status_code == 302 or response.status_code == 301:
            response.close()
            response = requests.get(response.headers["Location"], stream=True, headers=headers)
    except:
        messages.put("Broken Link: "+ref)
        return
    if response.status_code != 200:
        messages.put("Broken Link: "+ref)
    response.close()

def _handle_relative(ref, tech_content_path, messages):
    if ref[:24] == "/documentation/articles/":
        match = re.match("([^#|^/]+)/?(#[^#|^/]+)/?", ref[24:])
        if match == None:
            match = re.match("([^#|^/]+)/?#?", ref[24:])
            try:
                filename = match.group(1)+".md"
                tag = None
            except:
                messages.put("matching error: "+ref)
                return
        else:
            filename = match.group(1)+".md"
            tag = match.group(2)
        _handle_article(filename, tag, tech_content_path, messages, ref)
    else:
        url = "https://www.azure.cn"+ref
        try:
            response = requests.get(url, stream=True, headers=headers)
            while response.status_code == 302 or response.status_code == 301:
                response.close()
                response = requests.get(response.headers["Location"], stream=True, headers=headers)
        except:
            messages.put("Broken Link: "+ref)
            return
        if 'errors/404' in response.url or 'errors/500' in response.url:
            messages.put("Broken Link: "+ref)
        response.close()

def _handle_article(filename, tag, tech_content_path, messages, ref):
    if article_list.get(filename)==None:
        messages.put("Broken Link: "+ref)
    elif tag != None:
        file = open(article_list[filename], encoding="utf8")
        mdcontent = file.read()
        file.close()
        if _handle_inpage(tag, mdcontent, tech_content_path, False, messages):
            messages.put("Anchor Broken: "+ref)

def _handle_inpage(ref, mdcontent, tech_content_path, put_message, messages):
    mdcontent = _replace_include(mdcontent, tech_content_path)
    match = re.findall("(id|name)\s*=\s*['\"]"+re.escape(ref[1:])+"['\"]", mdcontent)
    if len(match) == 0:
        if put_message:
            messages.put("Anchor Broken: "+ref)
        return True
    return False

def _replace_include(mdcontent, tech_content_path):
    includeList = list(set(re.findall(include_reg, mdcontent)))
    for include in includeList:
        includeText = include[0]
        includeFile = include[1]
        try:
            if includeFile[len(includeFile)-3:]!=".md":
                includeFile += ".md"
            input = open(tech_content_path + "/includes/" + includeFile, "r", encoding="utf8")
            replacement = input.read().replace("./media", "../../includes/media")
            input.close()
        except IOError:
            replacement = ""
        mdcontent = mdcontent.replace(includeText, replacement)
    return mdcontent

def replace_date(acomRepo, acnRepo):
    filelist = _get_file_list(acomRepo)
    today = datetime.now()
    for filename in filelist:
        realname = filename[len(acomRepo):]
        if os.path.isfile(acnRepo+realname):
            print("processing: "+filename)
            file = open(filename, encoding="utf8")
            content = file.read()
            file.close()

            match1 = re.findall(r"(ms\.date\s*=\s*\"([^\"]*)\")", content)
            file = open(acnRepo+realname, encoding="utf8")
            content = file.read()
            file.close()

            match2 = re.findall(r"(ms\.date\s*=\s*\"([^\"]*)\")", content)
            if match1[0][1] != match2[0][1]:
                file = open(acnRepo+realname, "w", encoding="utf8")
                content = re.sub(r"wacn\.date\s*=\s*\"[^\"]*\"", "wacn.date=\""+today.strftime("%m/%d/%Y")+"\"", content)
                file.write(content.replace(match2[0][0],match1[0][0]))
                file.close()

def _get_file_list(acomRepo):
    filelist1 = [i.replace("\\","/") for i in glob.glob(acomRepo+"articles/**/*.md")]
    filelist2 = [i.replace("\\","/") for i in glob.glob(acomRepo+"articles/*.md")]
    filelist1.extend(filelist2)
    return filelist1

def _update_wacn_date(filepath, date):
    file = open(filepath, 'r', encoding="utf8")
    content = file.read()
    file.close()
    content = re.sub(r"wacn\.date\s*=\s*\"[^\"]*\"", "wacn.date=\""+date+"\"", content)
    file = open(filepath, 'w', encoding="utf8")
    file.write(content)
    file.close()

def open_in_browser(filepath, domain_name):
    filename = os.path.basename(filepath).strip()
    if filename[len(filename)-3:]!=".md":
        print("error: "+filepath+" is not a md file")
    else:
        subprocess.call(["explorer",domain_name+"/documentation/articles/"+filename[:len(filename)-3]+"/"], shell=False)

def scan_list(mdlist, output_mssg, threads, tech_content_path):
    for filepath in mdlist:
        filepath = filepath.replace("\\", "/")
        t = threading.Thread(target=scan_one, args=[filepath, output_mssg, tech_content_path])
        threads.append(t)

def scan_one(filepath, output_mssg, tech_content_path):
    messages = check_broken_link_queque(filepath,tech_content_path)
    if messages.empty():
        return
    output_mssg.put("\n"+filepath.replace(tech_content_path,""))
    while not messages.empty():
        output_mssg.put(messages.get())

def check_broken_link_multiple(tech_content_path,repo_path,filelist):
    threads = []
    output_mssgs = queue.Queue()
    mdlist = [tech_content_path+"/"+x for x in filelist if x[len(x)-3:]==".md"]
    scan_list(mdlist, output_mssgs, threads)

    for t in threads:
        while threading.active_count()>50:
            time.sleep(1)
        t.start()

    for t in threads:
        t.join()

    while not output_mssgs.empty():
        print(output_mssgs.get()+"\n")

def replace_properties_and_tags(repopath,filelist):
    mdlist = [repopath+"/"+x for x in filelist if x[len(x)-3:]==".md"]
    for filepath in mdlist:
        replace_pro_and_tag_one_file(filepath)

def replace_properties_and_tags_smartgit(filelist_path):
    file = open(filelist_path, "r")
    filelist = file.readlines()
    file.close()
    mdlist = [x.strip() for x in filelist if x.strip()[len(x.strip())-3:]==".md"]
    for filepath in mdlist:
        replace_pro_and_tag_one_file(filepath)

def replace_pro_and_tag_one_file(filepath):
    print("Proccessing: "+filepath.replace("\\", "/"))
    file = open(filepath, 'r', encoding="utf8")
    mdcontent = file.read()
    file.close()
    match = re.findall("(^|\ufeff|\n)(---\s*\n+((.*\n)+)---\s*\n)", mdcontent)
    if len(match)==0:
        print("Warnings: this file don't have properties and tags")
        return
    new_pro_and_tag = match[0][1]

    pro_and_tag = [i.strip() for i in re.split("\s*\n\s*\n", match[0][2]) if i.strip()!=""]

    if len(pro_and_tag)==0:
        print("Warnings: this file don't have properties and tags")
        return
    if len(pro_and_tag)==1:
        print("Warnings: this file don't have tags")
        pro = pro_and_tag[0]
        tag = ""
    else:
        pro = pro_and_tag[0]
        tag = pro_and_tag[1]
        if tag.strip()=="{}":
            print("Warnings: this file don't have tags")
            tag = ""
    pros = re.findall("([^:]+):\s*(?!\s*\>\s*)(\'?.+\'?)\s*\n", pro+"\n")
    pros.extend(re.findall("([^:|^\n]+):\s*\>\s*\n\s*(\'?.+\'?)\s*\n", pro+"\n"))
    properties="<properties\n"
    for property in pros:
        name = property[0]
        value = property[1].strip()
        if name=="title":
            name = "pageTitle"
            value = value.replace("Microsoft Docs", "Azure")
        if value[0]=="'":
            value = value[1:len(value)-1]
        properties+="    "+name+'="'+value+'"\n'
    properties = properties[:len(properties)-1]+" />\n"
    result = properties
    if tag != "":
        tags = re.findall("([^:]+):\s*(?!\s*\>\s*)(\'?.+\'?)\s*\n", tag+"\n")
        tags.extend(re.findall("([^:|^\n]+):\s*\>\s*\n\s*(\'?.+\'?)\s*\n", tag+"\n"))
        tag_str = "<tags\n"
        for name,value in tags:
            value = value.strip()
            if value[0]=="'":
                value = value[1:len(value)-1]
            tag_str+="    "+name+'="'+value+'"\n'
        tag_str = tag_str[:len(tag_str)-1]+" />\n"
        result+=tag_str
    file = open(filepath, "w", encoding="utf8")
    file.write(mdcontent.replace(new_pro_and_tag,result+"\n"))
    file.close()

if __name__ == '__main__':
    if sys.argv[1] == "copy_relative_path":
        copy_relative_path(sys.argv[2])
    elif sys.argv[1] == "copy_file_name":
        copy_file_name(sys.argv[2])
    elif sys.argv[1] == "check_broken_link":
        check_broken_link(sys.argv[2],sys.argv[3])
    elif sys.argv[1] == "replace_date":
        replace_date(sys.argv[2],sys.argv[3])
    elif sys.argv[1] == "update_wacn_date":
        if len(sys.argv) >= 4:
            date = sys.argv[3]
        else:
            date = datetime.now().strftime("%m/%d/%Y")
        _update_wacn_date(sys.argv[2], date)
    elif sys.argv[1] == "open_ppe_in_browser":
        open_in_browser(sys.argv[2], "http://wacn-ppe.chinacloudsites.cn")
    elif sys.argv[1] == "open_production_in_browser":
        open_in_browser(sys.argv[2], "https://www.azure.cn")
    elif sys.argv[1] == "check_broken_link_multiple":
        check_broken_link_multiple(sys.argv[2],sys.argv[3],sys.argv[4:])
    elif sys.argv[1] == "replace_properties_and_tags":
        replace_properties_and_tags(sys.argv[2],sys.argv[3:])
    elif sys.argv[1] == "replace_properties_and_tags_smartgit":
        replace_properties_and_tags_smartgit(sys.argv[2])