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
    try:
        response = requests.get(ref, stream=True)
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
        if _handle_article(filename, tag, tech_content_path, messages):
            messages.put("Broken Link: "+ref)
    else:
        url = "https://www.azure.cn"+ref
        response = requests.get(url, stream=True)
        if 'errors/404' in response.url or 'errors/500' in response.url:
            messages.put("Broken Link: "+ref)
        response.close()

def _handle_article(filename, tag, tech_content_path, messages):
    if article_list.get(filename)==None:
        return True
    elif tag != None:
        file = open(article_list[filename], encoding="utf8")
        mdcontent = file.read()
        file.close()
        return _handle_inpage(tag, mdcontent, tech_content_path, False, messages)
    return False

def _handle_inpage(ref, mdcontent, tech_content_path, put_message, messages):
    mdcontent = _replace_include(mdcontent, tech_content_path)
    match = re.findall("(id|name)\s*=\s*['\"]"+ref[1:]+"['\"]", mdcontent)
    if len(match) == 0:
        if put_message:
            messages.put("Broken Link: "+ref)
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