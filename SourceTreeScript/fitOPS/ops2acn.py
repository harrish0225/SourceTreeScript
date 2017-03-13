import re
import os
from customization import customize
from fitOPS.common import get_all_articles_path, all_articles_path, landingpages

code_block_csv = None
code_block_csv_empty = None
collect_programming_language = False

def repace_landingpage_ops_to_acn(filepath, repopath):
    landingpages_inverse = {v: k for k, v in landingpages.items()}
    landingpages_inverse["/articles/app-service-web/index.md"] = "/documentation/services/app-service/web/"
    file = open(filepath, "r", encoding="utf8")
    mdcontent = file.read()
    file.close()
    m = re.findall("((\]\(|\]:\s*|href\s*=\s*\")((\.\./|\./)*([\w-]*/)*index\.md))", mdcontent)
    if len(m)==0:
        return
    path, filename = os.path.split(filepath)
    for ma in list(set(m)):
        index_path = os.path.realpath(path+"/"+ma[2]).replace("\\","/")[len(repopath):]
        link = landingpages_inverse[index_path]
        mdcontent = mdcontent.replace(ma[0], ma[1]+link)
    file = open(filepath, "w", encoding="utf8")
    file.write(mdcontent)
    file.close()
    return

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
            prg_language = piece[0].strip()
            code = piece[1].replace("\t", "    ")
            if len(prg_language) > 20:
                code = "    "+prg_language+"\n"+code
            elif collect_programming_language:
                code_block_add(prg_language, piece[1].replace(",", "，"))
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

def code_block_add(prg_language, code):
    global code_block_csv
    global code_block_csv_empty
    if code_block_csv == None:
        code_block_csv = open("E:/code_block.csv", "w", encoding="utf8")
    if code_block_csv_empty == None:
        code_block_csv_empty = open("E:/code_block_empty.csv", "w", encoding="utf8")
    code_escape = str([code])
    if len(prg_language)>0:
        code_block_csv.write(prg_language+","+code_escape[1:len(code_escape)-1]+"\n")
    else:
        code_block_csv_empty.write(code_escape[1:len(code_escape)-1]+"\n")

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

def OPS_to_acn(script_path, repopath, filelist):
    mdlist = [repopath+"/"+x.strip() for x in filelist if x.strip()[len(x.strip())-3:]==".md"]
    get_all_articles_path(repopath)
    for filepath in mdlist:
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
        replace_code_notation_one(filepath)
        replace_pro_and_tag_one_file(filepath)
        repace_landingpage_ops_to_acn(filepath, repopath)
        customize(filepath, script_path, prefix="ops_to_acn_")
    return
