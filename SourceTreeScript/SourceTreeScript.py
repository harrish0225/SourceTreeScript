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
from customization import customize, customize_compare
from pantool import convert
from fitOPS import fitOPS, get_all_articles_path, repace_landingpage_ops_to_acn, update_acom_files_path
from listAndCode import refineNestedList

article_list = {}

include_reg = r"(?P<includeText>\[AZURE\.INCLUDE\s+\[[^\[\]]*\]\(\.\./(\.\./)*includes/(?P<fileName>[\w|\-]+(\.md)?)\)\])"
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
        includeFile = include[2]
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
    acom_filelist = _get_file_list(acomRepo)
    acom_file_dict = _get_file_dict(acom_filelist)
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
                match1 = re.findall(r"(ms\.date\s*=\s*\"([^\"]*)\")", content)
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
                file.write(content.replace(match2[0][0],match1[0][0]))
                file.close()

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
    if filepath[len(filepath)-3:]!=".md":
        print("error: "+filepath+" is not a md file")
    elif filepath[:9]!="articles/":
        print("error: "+filepath+" is not an article")
    else:
        subprocess.call(["explorer",domain_name+"/"+filepath[:len(filepath)-3]], shell=False)

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
    mdlist = [repo_path+"/"+x for x in filelist if x[len(x)-3:]==".md"]
    check_broken_link_multiple_common(tech_content_path, mdlist)

def check_broken_link_multiple_smartgit(tech_content_path,filelist_path):
    file = open(filelist_path, "r")
    filelist = file.read().split("\n")
    file.close()
    mdlist = [x for x in filelist if x[len(x)-3:]==".md"]
    check_broken_link_multiple_common(tech_content_path, mdlist)

def check_broken_link_multiple_common(tech_content_path, mdlist):
    threads = []
    output_mssgs = queue.Queue()
    scan_list(mdlist, output_mssgs, threads, tech_content_path)
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
    mdcontent = re.sub("(^|\ufeff|\n)-{3}(\s*\n)", "\\1\1\1\1\\2", mdcontent)
    match = re.findall("(^|\ufeff|\n)(\1{3}\s*\n(([^\1\n]*\s*\n)+)(\1{3}\s*\n|$))", mdcontent)
    if len(match)==0:
        print("Warnings: this file don't have properties and tags Type 1")
    else:
        new_pro_and_tag = match[0][1]
        if match[0][4] == "":
            print("Warnings: this file don't have properties and tags Type 2")
        else:
            pro_and_tag = [i.strip() for i in re.split("\s*\n\s*\n", match[0][2]) if i.strip()!=""]
            if len(pro_and_tag)==0:
                print("Warnings: this file don't have properties and tags Type 3")
            else:
                if len(pro_and_tag)==1:
                    if "ms." not in pro_and_tag[0]:
                        print("Warnings: this file don't have tags")
                        pro = pro_and_tag[0]
                        tag = ""
                    else:
                        p_and_t_m = re.findall("([ \t\r\f\v]*ms\..+(\n|$))", pro_and_tag[0])
                        pro = re.sub("[ \t\r\f\v]*ms\..+(\n|$)", "", pro_and_tag[0])
                        tag = "".join([x[0] for x in p_and_t_m])
                else:
                    pro = pro_and_tag[0]
                    tag = pro_and_tag[1]
                    if tag.strip()=="{}":
                        if "ms." not in pro_and_tag[0]:
                            print("Warnings: this file don't have tags")
                            tag = ""
                        else:
                            p_and_t_m = re.findall("([ \t\r\f\v]*ms\..+(\n|$))", pro_and_tag[0])
                            pro = re.sub("[ \t\r\f\v]*ms\..+(\n|$)", "", pro_and_tag[0])
                            tag = "".join([x[0] for x in p_and_t_m])
                
                pros = re.findall("([^:]+):[ \t\r\f\v]*(?!\s*\>\s*)(\'?.*\'?)[ \t\r\f\v]*\n", pro+"\n")
                pros.extend(re.findall("([^:\n]+):[ \t\r\f\v]*\>\s*\n\s*(\'?.*\'?)[ \t\r\f\v]*\n", pro+"\n"))
                properties="<properties\n"
                for property in pros:
                    name = property[0]
                    value = property[1].strip()
                    if name=="title":
                        name = "pageTitle"
                        value = value.replace("Microsoft Docs", "Azure")
                    if len(value)>0 and (value[0]=="'" or value[0]=="\""):
                        value = value[1:len(value)-1]
                    properties+="    "+name+'="'+value+'"\n'
                properties = properties[:len(properties)-1]+" />\n"
                result = properties
                if tag != "":
                    tags = re.findall("([^:]+):[ \t\r\f\v]*(?!\s*\>\s*)(\'?.*\'?)[ \t\r\f\v]*\n", tag+"\n")
                    tags.extend(re.findall("([^:\n]+):[ \t\r\f\v]*\>\s*\n\s*(\'?.*\'?)[ \t\r\f\v]*\n", tag+"\n"))
                    tag_str = "<tags\n"
                    for name,value in tags:
                        value = value.strip()
                        if len(value)>0 and (value[0]=="'" or value[0]=="\""):
                            value = value[1:len(value)-1]
                        tag_str+="    "+name+'="'+value+'"\n'
                    tag_str = tag_str[:len(tag_str)-1]+" />\n"
                    if not 'wacn.date="' in tag_str:
                        tag_str = re.sub('(\s*)(ms\.date\=\"[^"]*\")',r'\1\2\1wacn.date=""',tag_str)
                    result+=tag_str
                mdcontent = mdcontent.replace(new_pro_and_tag,result+"\n")
    mdcontent = replace_self_define_tags(mdcontent)
    file = open(filepath, "w", encoding="utf8")
    file.write(mdcontent.replace("\1","-"))
    file.close()

def replace_self_define_tags(mdcontent):
    mdcontent = mdcontent.replace("[!NOTE]", "[AZURE.NOTE]")
    mdcontent = mdcontent.replace("[!Note]", "[AZURE.NOTE]")
    mdcontent = mdcontent.replace("[!note]", "[AZURE.NOTE]")
    mdcontent = mdcontent.replace("[!IMPORTANT]", "[AZURE.IMPORTANT]")
    mdcontent = mdcontent.replace("[!Important]", "[AZURE.IMPORTANT]")
    mdcontent = mdcontent.replace("[!important]", "[AZURE.IMPORTANT]")
    mdcontent = mdcontent.replace("[!WARNING]", "[AZURE.WARNING]")
    mdcontent = mdcontent.replace("[!Warning]", "[AZURE.WARNING]")
    mdcontent = mdcontent.replace("[!warning]", "[AZURE.WARNING]")
    mdcontent = mdcontent.replace("[!INCLUDE", "[AZURE.INCLUDE")
    mdcontent = mdcontent.replace("[!Include", "[AZURE.INCLUDE")
    mdcontent = mdcontent.replace("[!include", "[AZURE.INCLUDE")
    mdcontent = mdcontent.replace("[!TIP]", "[AZURE.TIP]")
    mdcontent = mdcontent.replace("[!Tip]", "[AZURE.TIP]")
    mdcontent = mdcontent.replace("[!tip]", "[AZURE.TIP]")

    m = re.findall("(\s*\>\s*\[\!div\s+class\=\"op_single_selector\"\]\s*\n(\s*\>?\s*[\*\-]\s+(\[.+\]\(.+\))\s*\n)+\s*(\s*\>\s*\n)*)", mdcontent)
    if len(m) == 0:
        return mdcontent
    for i in m:
        selector = i[0]
        links = re.findall("\>?\s*[\*\-]\s+(\[.+\]\(.+\))\s*\n", selector+"\n")
        replace_selector = "> [AZURE.SELECTOR]\n"
        for link in links:
            replace_selector+="- "+link+"\n"
        mdcontent = mdcontent.replace(selector, "\n"+replace_selector+"\n")
    return mdcontent

def replace_code_notation_one(filepath):
    file = open(filepath, 'r', encoding="utf8")
    mdcontent = file.read()
    file.close()
    mdcontent = re.sub("^(\s*)\~{3,}(\s*)$", "\\1```\\2", mdcontent)
    if "```" not in mdcontent:
        return

    mdcontent = re.sub("\`{3,}", "\1\1\1", mdcontent)

    m = re.findall("(\n([\n\s]*\1{3}[^\1\n]*\s*\n(([^\1\n]*\s*\n)+)\s*(\1{3}|$))+[ \t\r\f\v]*\n*)", mdcontent)
    if len(m) > 0:
        last_one = m[len(m)-1][0].strip()
        if last_one[len(last_one)-1] != '\1':
            print("The md file contains odd numbers of '```'")
            return
    for i in m:
        whole = i[0]
        pieces = re.findall("\n[\n\s]*\1{3}([^\1\n]*\s*)\n(([^\1\n]*\s*\n)+)\s*\1{3}", whole)
        result = ""
        for piece in pieces:
            prg_language = piece[0]
            code = piece[1].replace("\t", "    ")
            if len(prg_language) > 20:
                code = "    "+prg_language+"\n"+code
            codelines = code.split("\n")
            lines = []
            for j in codelines:
                if j.strip()=="":
                    lines.append(j)
                else:
                    lines.append("    "+j)
            new_code = "\n".join(lines[:len(lines)-1])
            result += "\n\n"+new_code+"\n\n<br/>"
        result = result[:len(result)-5]
        mdcontent = mdcontent.replace(whole, result, 1)
    file = open(filepath, 'w', encoding="utf8")
    file.write(mdcontent.replace("\1","`"))
    file.close()

def replace_code_notation(repopath, filelist):
    mdlist = [x.strip() for x in filelist if x.strip()[len(x.strip())-3:]==".md"]
    for file in mdlist:
        print("Proccessing: "+repopath+"/"+file)
        replace_code_notation_one(repopath+"/"+file)

def replace_code_notation_smartgit(filelist_temp):
    file = open(filelist_temp, "r");
    filelist = file.readlines();
    
    file.close()
    mdlist = [x.strip() for x in filelist if x.strip()[len(x.strip())-3:]==".md"]
    for filepath in mdlist:
        print("Proccessing: "+filepath)
        replace_code_notation_one(filepath.strip())

def customize_files(script_path, repopath, filelist):
    mdlist = [repopath+"/"+x.strip() for x in filelist if x.strip()[len(x.strip())-3:]==".md"]
    for filepath in mdlist:
        print("Proccessing: "+filepath)
        customize(filepath, script_path)

def customize_files_smartgit(script_path, filelist_temp):
    file = open(filelist_temp, "r");
    filelist = file.readlines();
    
    file.close()
    mdlist = [x.strip() for x in filelist if x.strip()[len(x.strip())-3:]==".md"]
    for filepath in mdlist:
        print("Proccessing: "+filepath)
        customize(filepath, script_path)

def customize_files_compare(script_path, repopath, mooncakepath, filelist):
    mdlist = [repopath+"/"+x.strip() for x in filelist if x.strip()[len(x.strip())-3:]==".md"]
    for filepath in mdlist:
        print("Proccessing: "+filepath)
        customize_compare(filepath, script_path, repopath, mooncakepath)

def customize_files_compare_smartgit(script_path, repopath, mooncakepath, filelist_temp):
    file = open(filelist_temp, "r");
    filelist = file.readlines();
    
    file.close()
    mdlist = [x.strip() for x in filelist if x.strip()[len(x.strip())-3:]==".md"]
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

def fitOPS_main(script_path, repopath, filelist, acompath):
    mdlist = [repopath+"/"+x.strip() for x in filelist if x.strip()[len(x.strip())-3:]==".md"]
    get_all_articles_path(repopath)
    for filepath in mdlist:
        print("Proccessing: "+filepath)
        fitOPS(filepath, repopath, acompath, script_path)
    update_acom_files_path(script_path)
    return

def fitOPS_main_smartgit(script_path, repopath, filelist_temp, acompath):
    file = open(filelist_temp, "r");
    filelist = file.readlines();
    file.close()
    repopath = repopath.replace("\\", "/")
    mdlist = [x.strip() for x in filelist if x.strip()[len(x.strip())-3:]==".md"]
    get_all_articles_path(repopath)
    for filepath in mdlist:
        print("Proccessing: "+filepath)
        fitOPS(filepath, repopath, acompath, script_path)
    update_acom_files_path(script_path)
    return

def OPS_to_acn(script_path, repopath, filelist):
    mdlist = [repopath+"/"+x.strip() for x in filelist if x.strip()[len(x.strip())-3:]==".md"]
    get_all_articles_path(repopath)
    for filepath in mdlist:
        print("Proccessing: "+filepath)
        replace_code_notation_one(filepath)
        replace_pro_and_tag_one_file(filepath)
        repace_landingpage_ops_to_acn(filepath, repopath)
        customize(filepath, script_path, prefix="ops_to_acn_")
    return

def OPS_to_acn_smartgit(script_path, repopath, filelist_temp):
    file = open(filelist_temp, "r");
    filelist = file.readlines();
    file.close()
    repopath = repopath.replace("\\", "/")
    mdlist = [x.strip() for x in filelist if x.strip()[len(x.strip())-3:]==".md"]
    get_all_articles_path(repopath)
    for filepath in mdlist:
        print("Proccessing: "+filepath)
        replace_code_notation_one(filepath)
        replace_pro_and_tag_one_file(filepath)
        repace_landingpage_ops_to_acn(filepath, repopath)
        customize(filepath, script_path, prefix="ops_to_acn_")
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
        open_in_browser_OPS(sys.argv[2], "https://opsacndocsint.chinacloudsites.cn/zh-cn")
    elif sys.argv[1] == "check_broken_link_multiple":
        check_broken_link_multiple(sys.argv[2],sys.argv[3],sys.argv[4:])
    elif sys.argv[1] == "check_broken_link_multiple_smartgit":
        check_broken_link_multiple_smartgit(sys.argv[2],sys.argv[3])
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
        customize_files_smartgit(script_path, sys.argv[2])
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