import re
import os
from customization import customize_mdcontent, getRule
from fitOPS.common import get_all_articles_path, all_articles_path, landingpages
from xml.sax.saxutils import escape as html_escape

code_block_csv = None
code_block_csv_empty = None
collect_programming_language = False

def repace_landingpage_ops_to_acn(mdcontent, repopath, filepath):
    landingpages_inverse = {v: k for k, v in landingpages.items()}
    landingpages_inverse["/articles/app-service-web/index.md"] = "/documentation/services/app-service/web/"
    landingpages_inverse["/articles/active-directory/index.md"] = "/documentation/services/identity/"
    m = re.findall("((\]\(|\]:\s*|href\s*=\s*\")((\.\./|\./)*([\w-]*/)*index\.md))", mdcontent)
    if len(m)==0:
        return mdcontent
    path, filename = os.path.split(filepath)
    for ma in list(set(m)):
        index_path = os.path.realpath(path+"/"+ma[2]).replace("\\","/")[len(repopath):]
        link = landingpages_inverse[index_path]
        mdcontent = mdcontent.replace(ma[0], ma[1]+link)
    return mdcontent

def replace_properties_and_tags(repopath,filelist):
    mdlist = [repopath+"/"+x for x in filelist if x[len(x)-3:]==".md"]
    for filepath in mdlist:
        replace_pro_and_tag_one_path(filepath)

def replace_properties_and_tags_smartgit(filelist_path):
    file = open(filelist_path, "r")
    filelist = file.readlines()
    file.close()
    mdlist = [x.strip() for x in filelist if x.strip()[len(x.strip())-3:]==".md"]
    for filepath in mdlist:
        replace_pro_and_tag_one_path(filepath)

def replace_pro_and_tag_one_path(filepath):
    print("Proccessing: "+filepath.replace("\\", "/"))
    file = open(filepath, "r", encoding="utf8")
    mdcontent = file.read()
    file.close()
    mdcontent = replace_pro_and_tag_one(mdcontent)
    file = open(filepath, "w", encoding="utf8")
    file.write(mdcontent)
    file.close()

def replace_pro_and_tag_one(mdcontent):
    
    mdcontent = re.sub("(^|\ufeff|\n)-{3}(\s*\n)", "\\1\1\1\1\\2", mdcontent)
    match = re.findall("(^|\ufeff|\n)(\1{3}\s*\n(([^\1\n]*\s*\n)+)(\1{3}\s*\n|$))", mdcontent)
    if len(match)==0:
        print("Warnings: this file don't have properties and tags Type 1")
        mdcontent = re.sub("\1\1\1", "---", mdcontent)
    else:
        new_pro_and_tag = match[0][1]
        if match[0][4] == "":
            print("Warnings: this file don't have properties and tags Type 2")
            mdcontent = re.sub("\1\1\1", "---", mdcontent)
        else:
            pro_and_tag = [i.strip() for i in re.split("\n", match[0][2]) if i.strip()!=""]
            if len(pro_and_tag)==0 or pro_and_tag[0][:12]=="redirect_url":
                print("Warnings: this file don't have properties and tags Type 3")
                mdcontent = re.sub("\1\1\1", "---", mdcontent)
            else:
                pros = []
                tags = []
                line_num = 0
                while line_num < len(pro_and_tag):
                    m_pro_and_tag = re.match("([^:]+):[ \t\r\f\v]*(?!\s*\>\s*)(\'?.*\'?)[ \t\r\f\v]*", pro_and_tag[line_num])
                    if not m_pro_and_tag:
                        line_num+=1
                        if line_num < len(pro_and_tag):
                            m_pro_and_tag = re.match("([^:\n]+):[ \t\r\f\v]*\>\s*\n\s*(\'?.*\'?)[ \t\r\f\v]*", pro_and_tag[line_num-1]+"\n"+pro_and_tag[line_num])
                    if not m_pro_and_tag:
                        print("error: not correct pro and tag: "+str(pro_and_tag))
                        continue
                    if pro_and_tag[line_num][:3]=="ms." or pro_and_tag[line_num][:5]=="wacn.":
                        tags.append(m_pro_and_tag.groups())
                    else:
                        pros.append(m_pro_and_tag.groups())
                    line_num+=1
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
                if len(tags)>0:
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
    return mdcontent

def replace_self_define_tags(mdcontent):
    constant={
        "[!NOTE]": "[AZURE.NOTE]",
        "[!Note]": "[AZURE.NOTE]",
        "[!note]": "[AZURE.NOTE]",
        "[!IMPORTANT]": "[AZURE.IMPORTANT]",
        "[!Important]": "[AZURE.IMPORTANT]",
        "[!important]": "[AZURE.IMPORTANT]",
        "[!WARNING]": "[AZURE.WARNING]",
        "[!Warning]": "[AZURE.WARNING]",
        "[!warning]": "[AZURE.WARNING]",
        "[!INCLUDE": "[AZURE.INCLUDE",
        "[!Include": "[AZURE.INCLUDE",
        "[!include": "[AZURE.INCLUDE",
        "[!TIP]": "[AZURE.TIP]",
        "[!Tip]": "[AZURE.TIP]",
        "[!tip]": "[AZURE.TIP]"
        }

    constRegex = re.compile("(%s)" % "|".join(map(re.escape, constant.keys())))
    mdcontent = constRegex.sub(lambda mo: constant[mo.string[mo.start():mo.end()]], mdcontent)

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

def replace_code_notation_one(mdcontent):
    old_mdcontent = mdcontent
    mdcontent = re.sub("^(\s*)\~{3,}(\s*)$", "\\1```\\2", mdcontent)
    if "```" not in mdcontent:
        return old_mdcontent

    mdcontent = re.sub("\`{3,}", "\1\1\1", mdcontent)

    m = re.findall("(\n([\n\s]*\1{3}[^\1\n]*\s*\n(([^\1\n]*\s*\n)+)\s*(\1{3}|$))+[ \t\r\f\v]*\n*)", mdcontent)
    if len(m) > 0:
        last_one = m[len(m)-1][0].strip()
        if last_one[len(last_one)-1] != '\1':
            print("The md file contains odd numbers of '```'")
            return old_mdcontent
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
    mdcontent = mdcontent.replace("\1\1\1", "```")
    return mdcontent

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
        replace_code_notation_one_path(repopath+"/"+file)

def replace_code_notation_smartgit(filelist_temp):
    file = open(filelist_temp, "r");
    filelist = file.readlines();
    
    file.close()
    mdlist = [x.strip() for x in filelist if x.strip()[len(x.strip())-3:]==".md"]
    for filepath in mdlist:
        replace_code_notation_one_path(filepath.strip())

def replace_code_notation_one_path(filepath):
    print("Proccessing: "+filepath)
    file = open(filepath, "r", encoding="utf8")
    mdcontent = file.read()
    file.close()
    mdcontent = replace_code_notation_one(mdcontent)
    file = open(filepath, "w", encoding="utf8")
    file.write(mdcontent)
    file.close()

def OPS_to_acn(script_path, repopath, filelist):
    mdlist = [repopath+"/"+x.strip() for x in filelist if x.strip()[len(x.strip())-3:]==".md"]
    get_all_articles_path(repopath)
    for filepath in mdlist:
        OPS_to_acn_one_path(filepath, repopath, script_path)
    return

def OPS_to_acn_smartgit(script_path, repopath, filelist_temp):
    file = open(filelist_temp, "r");
    filelist = file.readlines();
    file.close()
    repopath = repopath.replace("\\", "/")
    mdlist = [x.strip() for x in filelist if x.strip()[len(x.strip())-3:]==".md"]
    get_all_articles_path(repopath)
    for filepath in mdlist:
        OPS_to_acn_one_path(filepath, repopath, script_path)
    return

def OPS_to_acn_one_path(filepath, repopath, script_path):
    print("Proccessing: "+filepath)
    file = open(filepath, "r", encoding="utf8")
    mdcontent = file.read()
    file.close()
    mdcontent = replace_code_notation_one(mdcontent)
    mdcontent = replace_pro_and_tag_one(mdcontent)
    mdcontent = repace_landingpage_ops_to_acn(mdcontent, repopath, filepath)
    getRule(script_path, "ops_to_acn_")
    mdcontent = customize_mdcontent(mdcontent)
    file = open(filepath, "w", encoding="utf8")
    file.write(mdcontent)
    file.close()

def replaceScript(filepath, clipath, pspath):
    file = open(filepath, "r", encoding="utf8")
    mdcontent = file.read()
    file.close()
    mdcontent = replaceScript_one(mdcontent, clipath, pspath)
    file = open(filepath, "w", encoding="utf8")
    file.write(mdcontent)
    file.close()
    return

def replaceScript_one(mdcontent, clipath, pspath):
    regex = '(\n([ \t\r\f\v]*)\[!code-(\w+)\[\w+\]\((\.\./)+([^\s"\?]+)(\?highlight\=(\d+-\d+|\d+))?( "[^\n"]+")?\)\][ \t\r\f\v]*(\n|$))'
    m = re.findall(regex, mdcontent)
    for a_m in m:
        whole = a_m[0]
        leading_empy = a_m[1]
        progLan = a_m[2]
        relative_scrip_path = a_m[4]
        highlight = a_m[5]
        replacement = get_script_replacement(leading_empy, progLan, relative_scrip_path, clipath, pspath)
        mdcontent = mdcontent.replace(whole, replacement)
    return mdcontent

def get_script_replacement(leading_empy, progLan, relative_scrip_path, clipath, pspath):
    if relative_scrip_path[:12] == "cli_scripts/":
        scrip_path = clipath+relative_scrip_path[12:]
    elif relative_scrip_path[:19] == "powershell_scripts/":
        scrip_path = pspath+relative_scrip_path[19:]
    else:
        print("new script root")
        exit(-1)
    file = open(scrip_path, "r", encoding="utf8")
    script = file.read()
    file.close()
    result = "\n```"+progLan+"\n"+script+"\n```\n"
    if leading_empy!="":
        lines = result.split("\n")
        lines = [leading_empy+line if line.strip()!="" else line for line in lines]
        result = "\n".join(lines)
    getRule("E:/GitHub/SourceTreeScript/SourceTreeScript")
    result = "\n"+leading_empy+customize_mdcontent(result)+"\n"

    return result