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
import time
import subprocess
from customization import customize, customize_compare, refineNestedListContent, replaceUrlRelativeLink
from pantool import convert
from fitOPS import fitOPS_main, fitOPS_main_smartgit, OPS_to_acn, OPS_to_acn_smartgit, replace_properties_and_tags, replace_properties_and_tags_smartgit, replace_code_notation, replace_code_notation_smartgit, replaceScript, refine_properties_and_tags_smartgit, refine_properties_and_tags

from Study import get_update_description_main
import json

article_list = {}

include_reg = r"(?P<includeText>\[(AZURE\.INCLUDE|\!include|\!Include|\!INCLUDE)\s+\[[^\[\]]*\]\(\.\./(\.\./)*includes/(?P<fileName>[\w|\-]+(\.md)?)\)\])"
headers_list = [{'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8', 'Accept-Encoding': 'gzip, deflate', 'Connection': 'keep-alive', 'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; WOW64; rv:49.0) Gecko/20100101 Firefox/49.0', 'Accept-Language': 'en-US,en;q=0.8,zh-Hans-CN;q=0.5,zh-Hans;q=0.3', 'Upgrade-Insecure-Requests': '1'},
                {'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8', 'Accept-Encoding': 'gzip, deflate, sdch, br', 'Connection': 'keep-alive', 'Cache-Control': 'max-age=0', 'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/57.0.2987.133 Safari/537.36', 'Accept-Language': 'en-US,en;q=0.8,zh-Hans-CN;q=0.5,zh-Hans;q=0.3', 'Upgrade-Insecure-Requests': '1'},
                {'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8', 'Accept-Encoding': 'gzip, deflate, sdch, br', 'Connection': 'keep-alive', 'Cache-Control': 'no-cache', 'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/51.0.2704.79 Safari/537.36 Edge/14.14393', 'Accept-Language': 'en-US,en;q=0.8,zh-Hans-CN;q=0.5,zh-Hans;q=0.3', 'Upgrade-Insecure-Requests': '1'},
                {'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8', 'Accept-Encoding': 'gzip, deflate, sdch, br', 'Connection': 'keep-alive', 'Cache-Control': 'no-cache', 'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; WOW64; Trident/7.0; rv:11.0) like Gecko', 'Accept-Language': 'en-US,en;q=0.8,zh-Hans-CN;q=0.5,zh-Hans;q=0.3', 'Upgrade-Insecure-Requests': '1'}
                ]

headers = headers_list[0]

current_headers_index = 0

good_links = {}

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

def check_broken_link(file_path, tech_content_path, ACN=True):
    messages = check_broken_link_queque(file_path, tech_content_path, ACN)
    while not messages.empty():
        print(messages.get())


def check_broken_link_queque(file_path, tech_content_path, ACN=True):
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
    if ACN:
        handle_hrefs(refs, mdcontent, file_path, tech_content_path, messages)
    else:
        handle_hrefs2(refs, mdcontent, file_path, tech_content_path, messages)
    return messages

def handle_hrefs(refs, mdcontent, file_path, tech_content_path, messages):
    threads=[]
    for ref in refs:
        if "\n" in ref:
            continue
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

def handle_hrefs2(refs, mdcontent, file_path, tech_content_path, messages):
    threads=[]
    for ref in refs:
        if "\n" in ref:
            continue
        t = None
        if len(ref) == 0:
            messages.put("Broken Link: empty link")
        elif ref[:5] == "http:" or ref[:6] == "https:":
            t = threading.Thread(target=_handle_full, args=[ref, messages])
        elif ref[0] == "/":
            t = threading.Thread(target=_handle_relative2, args=[ref, tech_content_path, messages])
        elif ref[0] == "#":
            t = threading.Thread(target=_handle_inpage, args=[ref, mdcontent, tech_content_path, True, messages])
        elif ref[:9] == "{%image%}":
            t = threading.Thread(target=_handle_image2, args=[ref[9:], file_path, messages])
        else:
            t = threading.Thread(target=_handle_file, args=[ref, file_path, tech_content_path, messages])
        if t != None:
            threads.append(t)
            t.start()
    for t in threads:
         t.join()

def _handle_file(ref, file_path, tech_content_path, messages):
    filepath = re.match("([^#?]*[\d\w])/?[#?]*.*", ref).groups()[0]
    if not os.path.isfile(os.path.dirname(file_path)+"/"+filepath):
        messages.put("Broken Link: "+ref)
    else:
        match = re.match(".+(#.+)", ref[len(filepath):])
        if match != None:
            tag = match.group(1)
            _handle_article2(os.path.dirname(file_path)+"/"+filepath, tag, tech_content_path, messages, ref)

def _handle_image2(ref, file_path, messages):
    if ref[:5] == "http:" or ref[:6] == "https:":
        _handle_full(ref, messages)
    else:
        _handle_relative_image2(ref, file_path, messages)

def _handle_relative_image2(ref, file_path, messages):
    path = os.path.dirname(file_path)+"/"+ref
    if not os.path.isfile(path):
        messages.put("Broken Image: "+ref)

def _handle_relative2(ref, tech_content_path, messages):
    if ref[:8] == "/develop" or ref[:10] == "/downloads" or ref[:5] == "/cdn/" or ref[:7] == "/mysql/" or ref[:10] == "/articles/":
        if ref[:5] == "/cdn/":
            if ref[5:]=="":
                return
            ref2 =  "/documentation/articles/"+ref[5:]
        elif ref[:7] == "/mysql/":
            if ref[7:]=="":
                return
            ref2 =  "/documentation/articles/"+ref[7:]
        elif ref[:10] == "/articles/":
            if ref[10:]=="":
                return
            ref2 =  "/documentation/articles/"+ref[10:]
        else:
            ref2 = ref
        url = "https://www.azure.cn"+ref2
        if good_links.get(url):
            return
        try:
            response = requests.get(url, stream=True, headers=headers, timeout=1000)
            while response.status_code == 302 or response.status_code == 301:
                response.close()
                response = requests.get(response.headers["Location"], stream=True, headers=headers, timeout=1000)
        except:
            messages.put("Broken Link: "+ref)
            return
        if 'errors/404' in response.url or 'errors/500' in response.url:
            messages.put("Broken Link: "+ref)
        else:
            good_links[url]=True
        response.close()
    else:
        match = re.match("([^#?]*[\d\w])/?[#?]*.*", ref)
        if match == None:
            if re.match("/([#?].*|)", ref):
                filepath = "/index"
            else:
                messages.put("Broken Link: "+ref)
        else:
            filepath = match.groups()[0]
        if not os.path.isfile(tech_content_path+"articles"+filepath+".md") and not os.path.isfile(tech_content_path+"articles"+filepath+"/index.md") and not os.path.isfile(tech_content_path+"articles"+filepath+"/index.yml"):
            messages.put("Broken Link: "+ref)
        else:
            match = re.match(".+(#.+)", ref[len(filepath):])
            if match != None:
                tag = match.group(1)
                _handle_article2(tech_content_path+"articles"+filepath+".md", tag, tech_content_path, messages, ref)

def _handle_article2(filepath, tag, tech_content_path, messages, ref):
    file = open(filepath, encoding="utf8")
    mdcontent = file.read()
    file.close()
    if _handle_inpage(tag, mdcontent, tech_content_path, False, messages):
        messages.put("Anchor Broken: "+ref)


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
    global headers
    global current_headers_index
    if ref[:16] == "http://localhost" or ref[:17] == "https://localhost":
        return
    if good_links.get(ref):
        return
    try:
        response = requests.get(ref, stream=True, headers=headers, timeout=1000)
        url = ref
        while response.status_code == 302 or response.status_code == 301:
            response.close()
            url = response.headers["Location"]
            response = requests.get(url, stream=True, headers=headers, timeout=1000)
        pre_current_headers_index = current_headers_index
        """
        while response.status_code == 403:
            current_headers_index = (current_headers_index+1)%4
            headers = headers_list[current_headers_index]
            if current_headers_index == pre_current_headers_index:
                break
            response.close()
            response = requests.get(url, stream=True, headers=headers, timeout=1000)
        """
        if response.status_code == 403 and ("docs.microsoft.com" in url or "msdn.microsoft.com" in url):
            return
            """
            while response.status_code == 403:
                response.close()
                time.sleep(300)
                response = requests.get(url, stream=True, headers=headers, timeout=1000)
            """
    except Exception as e:
        messages.put("Broken Link: "+ref)
        return
    if response.status_code != 200:
        messages.put("Broken Link: "+ref)
    else:
        good_links[ref]=True
    response.close()

def _handle_relative(ref, tech_content_path, messages):
    if ref[:24] == "/documentation/articles/":
        match = re.match("([^#/]+)/?(#[^#/]+)/?", ref[24:])
        if match == None:
            match = re.match("([^#/]+)/?#?", ref[24:])
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
        if good_links.get(url):
            return
        try:
            response = requests.get(url, stream=True, headers=headers, timeout=1000)
            while response.status_code == 302 or response.status_code == 301:
                response.close()
                response = requests.get(response.headers["Location"], stream=True, headers=headers, timeout=1000)
        except:
            messages.put("Broken Link: "+ref)
            return
        if 'errors/404' in response.url or 'errors/500' in response.url:
            messages.put("Broken Link: "+ref)
        else:
            good_links[url]=True
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
        includeFile = include[3]
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

def replace_date(acomRepo, acnRepo, script_path):
    acom_filelist = _get_file_list(acomRepo)
    acom_file_dict = _get_file_dict(acom_filelist)
    acom_file_dict = _add_vm_file(acom_file_dict, acomRepo, script_path)
    acn_filelist = _get_file_list(acnRepo)
    today = datetime.now()
    for filepath in acn_filelist:
        path, filename = os.path.split(filepath)
        relativepath = filepath[len(acnRepo):]
        if acom_file_dict.get(filename):
            print("processing: "+relativepath)
            for acom_file_path in acom_file_dict[filename]:
                file = open(acom_file_path, encoding="utf8")
                content = file.read()
                file.close()
                match1 = re.findall(r"(ms\.date\s*:\s*([\d/]+)\s*)", content)
                if match1:
                    break
            if not match1:
                continue
            file = open(filepath, encoding="utf8")
            content = file.read()
            file.close()

            match2 = re.findall(r"(ms\.date\s*=\s*\"([^\"]*)\")", content)

            if match1[0][1] != match2[0][1]:
                file = open(filepath, "w", encoding="utf8")
                content = re.sub(r"wacn\.date\s*=\s*\"[^\"]*\"", "wacn.date=\""+today.strftime("%m/%d/%Y")+"\"", content)
                file.write(content.replace(match2[0][0],"ms.date=\""+match1[0][1]+"\""))
                file.close()

def _add_vm_file(acom_file_dict, acomRepo, script_path):
    file = open(script_path+"/vm_file.json", "r", encoding="utf8")
    mvlist = json.loads(file.read())
    file.close()
    for filepath in glob.iglob(acomRepo+"articles/virtual-machines/**/*.md", recursive=True):
        filepath = filepath.replace("\\", "/")
        path, filename = os.path.split(filepath)
        if filename[:15]!="virtual-machine":
            relative_path = filepath[len(acomRepo)+9:len(filepath)-3]
            if mvlist.get(relative_path):
                filename = mvlist[relative_path]+".md"
            else:
                filename = relative_path.replace("/","-")+".md"
            if acom_file_dict.get(filename):
                acom_file_dict[filename].append(filepath)
            else:
                acom_file_dict[filename] = [filepath]
    return acom_file_dict

def _get_file_dict(filelist):
    result = {}
    for file in filelist:
        path, filename = os.path.split(file)
        if result.get(filename):
            result[filename].append(file)
        else:
            result[filename] = [file]
    return result

def _get_file_list(acomRepo):
    filelist1 = [i.replace("\\","/") for i in glob.glob(acomRepo+"articles/*.md")]
    filelist2 = [i.replace("\\","/") for i in glob.glob(acomRepo+"articles/**/*.md")]
    filelist3 = [i.replace("\\","/") for i in glob.glob(acomRepo+"articles/**/**/*.md")]
    filelist4 = [i.replace("\\","/") for i in glob.glob(acomRepo+"articles/**/**/**/*.md")]
    filelist1.extend(filelist2)
    filelist1.extend(filelist3)
    filelist1.extend(filelist4)
    return filelist1

def _update_wacn_date(repopath, filelist, date):
    mdlist = [repopath+"/"+x for x in filelist if x[len(x)-3:]==".md"]
    for filepath in mdlist:
        _update_wacn_date_one(filepath, date)

def _update_wacn_date_smartgit(selection, date):
    file = open(selection, "r")
    filelist = file.readlines()
    file.close()
    mdlist = [x for x in filelist if x[len(x)-3:]==".md"]
    for filepath in mdlist:
        _update_wacn_date_one(filepath, date)

def _update_wacn_date_one(filepath, date):
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

def open_in_browser_OPS(filepath, domain_name):
    if filepath[:9]=="articles/":
        if filepath[len(filepath)-3:]==".md":
            subprocess.call(["explorer",domain_name+"/"+filepath[9:len(filepath)-3]], shell=False)
        elif filepath[len(filepath)-4:]==".yml":
            subprocess.call(["explorer",domain_name+"/"+filepath[9:len(filepath)-4]], shell=False)
        else:
            print("error: "+filepath+" is not an md or yml")
    else:
        print("error: "+filepath+" is not an article")

def scan_list(mdlist, output_mssg, threads, tech_content_path, ACN=True):
    for filepath in mdlist:
        filepath = filepath.replace("\\", "/")
        t = threading.Thread(target=scan_one, args=[filepath, output_mssg, tech_content_path, ACN])
        threads.append(t)

def scan_one(filepath, output_mssg, tech_content_path, ACN=True):
    messages = check_broken_link_queque(filepath,tech_content_path, ACN)
    if messages.empty():
        return
    output_mssg.put("\n"+filepath.replace(tech_content_path,""))
    while not messages.empty():
        output_mssg.put(messages.get())

def check_broken_link_multiple(tech_content_path,repo_path,filelist, ACN=True):
    mdlist = [repo_path+"/"+x for x in filelist if x[len(x)-3:]==".md"]
    check_broken_link_multiple_common(tech_content_path, mdlist, ACN)

def check_broken_link_multiple_smartgit(tech_content_path,filelist_path, ACN=True):
    file = open(filelist_path, "r")
    filelist = file.read().split("\n")
    file.close()
    mdlist = [x for x in filelist if x[len(x)-3:]==".md"]
    check_broken_link_multiple_common(tech_content_path, mdlist, ACN)

def check_broken_link_multiple_common(tech_content_path, mdlist, ACN=True):
    threads = []
    output_mssgs = queue.Queue()
    scan_list(mdlist, output_mssgs, threads, tech_content_path, ACN)
    for t in threads:
        while threading.active_count()>50:
            time.sleep(1)
        t.start()

    for t in threads:
        t.join()

    while not output_mssgs.empty():
        print(output_mssgs.get()+"\n")

def customize_files(script_path, repopath, filelist):
    mdlist = [repopath+"/"+x.strip() for x in filelist if x.strip()[len(x.strip())-3:]==".md" or x.strip()[len(x.strip())-4:]==".yml"]
    for filepath in mdlist:
        print("Proccessing: "+filepath)
        customize(filepath, script_path, repopath)

def customize_files_smartgit(script_path, filelist_temp, repopath):
    file = open(filelist_temp, "r");
    filelist = file.readlines();
    
    file.close()
    mdlist = [x.strip() for x in filelist if x.strip()[len(x.strip())-3:]==".md" or x.strip()[len(x.strip())-4:]==".yml"]
    for filepath in mdlist:
        print("Proccessing: "+filepath)
        customize(filepath, script_path, repopath)

def customize_files_compare(script_path, repopath, mooncakepath, filelist):
    mdlist = [repopath+"/"+x.strip() for x in filelist if x.strip()[len(x.strip())-3:]==".md" or x.strip()[len(x.strip())-4:]==".yml"]
    for filepath in mdlist:
        print("Proccessing: "+filepath)
        customize_compare(filepath, script_path, repopath, mooncakepath)

def customize_files_compare_smartgit(script_path, repopath, mooncakepath, filelist_temp):
    file = open(filelist_temp, "r");
    filelist = file.readlines();
    
    file.close()
    mdlist = [x.strip() for x in filelist if x.strip()[len(x.strip())-3:]==".md" or x.strip()[len(x.strip())-4:]==".yml"]
    for filepath in mdlist:
        print("Proccessing: "+filepath)
        customize_compare(filepath, script_path, repopath, mooncakepath)

def pandoctool(script_path, repopath, filelist):
    mdlist = [x.strip() for x in filelist if x.strip()[len(x.strip())-3:]==".md"]
    for filepath in mdlist:
        convert(filepath, repopath)
    return

def pandoctool_smartgit(script_path, repopath, filelist_temp):
    file = open(filelist_temp, "r");
    filelist = file.readlines();
    file.close()
    repopath = repopath.replace("\\", "/")
    mdlist = [x.strip().replace("\\", "/")[len(repopath)+1:] for x in filelist if x.strip()[len(x.strip())-3:]==".md"]
    for filepath in mdlist:
        convert(filepath, repopath)
    return

def refine_nested_list(script_path, repopath, filelist):
    mdlist = [repopath+"/"+x.strip() for x in filelist if x.strip()[len(x.strip())-3:]==".md"]
    for filepath in mdlist:
        print("Proccessing: "+filepath)
        refineNestedList(filepath)
    return

def refine_nested_list_smartgit(script_path, repopath, filelist_temp):
    file = open(filelist_temp, "r");
    filelist = file.readlines();
    file.close()
    repopath = repopath.replace("\\", "/")
    mdlist = [x.strip() for x in filelist if x.strip()[len(x.strip())-3:]==".md"]
    for filepath in mdlist:
        print("Proccessing: "+filepath)
        refineNestedList(filepath)
    return

def replace_url_relative_link(script_path, repopath, filelist):
    mdlist = [repopath+"/"+x.strip() for x in filelist if x.strip()[len(x.strip())-3:]==".md"]
    for filepath in mdlist:
        print("Proccessing: "+filepath)
        replaceUrlRelativeLink(filepath, repopath)
    return

def replace_url_relative_link_smartgit(script_path, repopath, filelist_temp):
    file = open(filelist_temp, "r");
    filelist = file.readlines();
    file.close()
    repopath = repopath.replace("\\", "/")
    mdlist = [x.strip() for x in filelist if x.strip()[len(x.strip())-3:]==".md"]
    for filepath in mdlist:
        print("Proccessing: "+filepath)
        replaceUrlRelativeLink(filepath, repopath)
    return

def replace_script(script_path, repopath, clipath, pspath, filelist):
    mdlist = [repopath+"/"+x.strip() for x in filelist if x.strip()[len(x.strip())-3:]==".md"]
    for filepath in mdlist:
        print("Proccessing: "+filepath)
        replaceScript(filepath, clipath, pspath)
    return

def replace_script_smartgit(script_path, repopath, clipath, pspath, filelist_temp):
    file = open(filelist_temp, "r");
    filelist = file.readlines();
    file.close()
    repopath = repopath.replace("\\", "/")
    mdlist = [x.strip() for x in filelist if x.strip()[len(x.strip())-3:]==".md"]
    for filepath in mdlist:
        print("Proccessing: "+filepath)
        replaceScript(filepath, clipath, pspath)
    return

def get_update_description(tech_content_path,filelist_path):
    get_update_description_main(tech_content_path,filelist_path)
    return

def stage_for(script_path, repopath, member, filelist):
    stage_for_list(script_path, member, filelist)
    return

def stage_for_smartgit(script_path, repopath, member, filelist_temp):
    file = open(filelist_temp, "r");
    filelist = file.readlines();
    file.close()
    repopath = repopath.replace("\\", "/")
    filelist = [x.strip().replace("\\", "/")[len(repopath):] for x in filelist]
    stage_for_list(script_path, member, filelist)
    return

def stage_for_list(script_path, member, filelist):
    belong_list = []
    belong_list_temp = []
    for filepath in filelist:
        if belong_to(script_path, member, filepath):
            belong_list_temp.append(filepath)
            if len(" ".join(belong_list_temp))>4000:
                command_list = ["git.exe", "add", "--force", "--"]
                command_list.extend(belong_list)
                ret = subprocess.call(command_list, shell=True)
                belong_list = [filepath]
                belong_list_temp = [filepath]
            else:
                belong_list.append(filepath)
    if belong_list != []:
        command_list = ["git.exe", "add", "--force", "--"]
        command_list.extend(belong_list)
        ret = subprocess.call(command_list, shell=True)

def belong_to(script_path, member, filepath):
    file_folder_list = filepath.split("/")
    file = open(script_path+"/file_belong.json", "r", encoding="utf8")
    belonging = json.loads(file.read())
    file.close()
    if belonging[member][file_folder_list[0]].get(file_folder_list[1]):
        return True
    if file_folder_list[0] == "articles" and file_folder_list[1][len(file_folder_list[1])-3:] in [".md", "yml"] and belonging[member][file_folder_list[0]].get("Others"):
        return True
    return False

if __name__ == '__main__':
    if sys.argv[1] == "copy_relative_path":
        copy_relative_path(sys.argv[2])
    elif sys.argv[1] == "copy_file_name":
        copy_file_name(sys.argv[2])
    elif sys.argv[1] == "check_broken_link":
        check_broken_link(sys.argv[2],sys.argv[3])
    elif sys.argv[1] == "replace_date":
        script_path, script_file = os.path.split(sys.argv[0])
        replace_date(sys.argv[2],sys.argv[3], script_path)
    elif sys.argv[1] == "update_wacn_date":
        if sys.argv[2] != "--today":
            date = sys.argv[2]
        else:
            date = datetime.now().strftime("%m/%d/%Y")
        _update_wacn_date(sys.argv[3], sys.argv[4:], date)
    elif sys.argv[1] == "update_wacn_date_smartgit":
        if sys.argv[2] != "--today":
            date = sys.argv[2]
        else:
            date = datetime.now().strftime("%m/%d/%Y")
        _update_wacn_date_smartgit(sys.argv[3], date)
    elif sys.argv[1] == "open_ppe_in_browser":
        open_in_browser(sys.argv[2], "https://wacn-ppe.chinacloudsites.cn")
    elif sys.argv[1] == "open_production_in_browser":
        open_in_browser(sys.argv[2], "https://www.azure.cn")
    elif sys.argv[1] == "open_OPS_in_browser":
        open_in_browser_OPS(sys.argv[2], "https://review.docs.azure.cn/en-us")
    elif sys.argv[1] == "check_broken_link_multiple":
        check_broken_link_multiple(sys.argv[2],sys.argv[3],sys.argv[4:])
    elif sys.argv[1] == "check_broken_link_multiple_smartgit":
        check_broken_link_multiple_smartgit(sys.argv[2],sys.argv[3])
    elif sys.argv[1] == "check_broken_link_OPS_multiple":
        check_broken_link_multiple(sys.argv[2],sys.argv[3],sys.argv[4:], False)
    elif sys.argv[1] == "check_broken_link_OPS_multiple_smartgit":
        check_broken_link_multiple_smartgit(sys.argv[2],sys.argv[3], False)
    elif sys.argv[1] == "refine_properties_and_tags":
        refine_properties_and_tags(sys.argv[2],sys.argv[3:])
    elif sys.argv[1] == "refine_properties_and_tags_smartgit":
        refine_properties_and_tags_smartgit(sys.argv[2])
    elif sys.argv[1] == "replace_properties_and_tags":
        replace_properties_and_tags(sys.argv[2],sys.argv[3:])
    elif sys.argv[1] == "replace_properties_and_tags_smartgit":
        replace_properties_and_tags_smartgit(sys.argv[2])
    elif sys.argv[1] == "replace_code_notation":
        replace_code_notation(sys.argv[2], sys.argv[3:])
    elif sys.argv[1] == "replace_code_notation_smartgit":
        replace_code_notation_smartgit(sys.argv[2])
    elif sys.argv[1] == "customize_files":
        script_path, script_file = os.path.split(sys.argv[0])
        customize_files(script_path, sys.argv[2], sys.argv[3:])
    elif sys.argv[1] == "customize_files_smartgit":
        script_path, script_file = os.path.split(sys.argv[0])
        customize_files_smartgit(script_path, sys.argv[2], sys.argv[3])
    elif sys.argv[1] == "customize_files_compare":
        script_path, script_file = os.path.split(sys.argv[0])
        customize_files_compare(script_path, sys.argv[2], sys.argv[3], sys.argv[4:])
    elif sys.argv[1] == "customize_files_compare_smartgit":
        script_path, script_file = os.path.split(sys.argv[0])
        customize_files_compare_smartgit(script_path, sys.argv[2], sys.argv[3], sys.argv[4])
    elif sys.argv[1] == "pantool":
        script_path, script_file = os.path.split(sys.argv[0])
        pandoctool(script_path, sys.argv[2], sys.argv[3:])
    elif sys.argv[1] == "pantool_smartgit":
        script_path, script_file = os.path.split(sys.argv[0])
        pandoctool_smartgit(script_path, sys.argv[2], sys.argv[3])
    elif sys.argv[1] == "fitOPS":
        script_path, script_file = os.path.split(sys.argv[0])
        fitOPS_main(script_path, sys.argv[2], sys.argv[4:], sys.argv[3])
    elif sys.argv[1] == "fitOPS_smartgit":
        script_path, script_file = os.path.split(sys.argv[0])
        fitOPS_main_smartgit(script_path, sys.argv[2], sys.argv[4], sys.argv[3])
    elif sys.argv[1] == "OPS_to_acn":
        script_path, script_file = os.path.split(sys.argv[0])
        OPS_to_acn(script_path, sys.argv[2], sys.argv[3:])
    elif sys.argv[1] == "OPS_to_acn_smartgit":
        script_path, script_file = os.path.split(sys.argv[0])
        OPS_to_acn_smartgit(script_path, sys.argv[2], sys.argv[3])
    elif sys.argv[1] == "refine_nested_list":
        script_path, script_file = os.path.split(sys.argv[0])
        refine_nested_list(script_path, sys.argv[2], sys.argv[3:])
    elif sys.argv[1] == "refine_nested_list_smartgit":
        script_path, script_file = os.path.split(sys.argv[0])
        refine_nested_list_smartgit(script_path, sys.argv[2], sys.argv[3])
    elif sys.argv[1] == "get_update_description":
        get_update_description( sys.argv[2], sys.argv[3])
    elif sys.argv[1] == "replace_script":
        script_path, script_file = os.path.split(sys.argv[0])
        replace_script(script_path, sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5:])
    elif sys.argv[1] == "replace_script_smartgit":
        script_path, script_file = os.path.split(sys.argv[0])
        replace_script_smartgit(script_path, sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5])
    elif sys.argv[1] == "replace_url_relative_link":
        script_path, script_file = os.path.split(sys.argv[0])
        replace_url_relative_link(script_path, sys.argv[2], sys.argv[3:])
    elif sys.argv[1] == "replace_url_relative_link_smartgit":
        script_path, script_file = os.path.split(sys.argv[0])
        replace_url_relative_link_smartgit(script_path, sys.argv[2], sys.argv[3])
    elif sys.argv[1] == "stage_for":
        script_path, script_file = os.path.split(sys.argv[0])
        stage_for(script_path, sys.argv[2], sys.argv[3], sys.argv[4:])
    elif sys.argv[1] == "stage_for_smartgit":
        script_path, script_file = os.path.split(sys.argv[0])
        stage_for_smartgit(script_path, sys.argv[2], sys.argv[3], sys.argv[4])