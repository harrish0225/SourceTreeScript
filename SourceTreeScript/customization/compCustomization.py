import re
import os
import git
from .regexCutomization import customize_mdcontent, getRule
from .matchingSeq import get_diff_set, construct_com_md, apply_modification


g = None

def customize_compare(filepath, script_path, repopath=".", mooncakepath="E:\GitHub\azure-content-mooncake-pr", prefix=""):
    getRule(script_path, prefix)
    file = open(filepath, "r", encoding="utf8")
    mdcontent = file.read().replace("\ufeff", "")
    file.close()
    mdcontent = customize_mdcontent(mdcontent)
    mdcontent = mdcontent.replace("\r", "").strip()
    relative_path = filepath[len(repopath)+1:].replace("\\","/")
    mooncake_file_path = mooncakepath+"/"+relative_path
    if os.path.isfile(mooncake_file_path):
        try:
            lastmonth_md = getlastmonthmd(relative_path, repopath).replace("\r", "")
        except git.exc.GitCommandError:
            "do nothing"
        else:
            file = open(mooncake_file_path, "r", encoding="utf8")
            mc_md = file.read().replace("\ufeff", "").replace("\r", "").strip()
            file.close()
            mdcontent = customize_compare_mdcontent2(mdcontent, lastmonth_md, mc_md)
    file = open(filepath, "w", encoding="utf8")
    file.write(mdcontent)
    file.close()

def customize_compare_mdcontent(mdcontent, lastmonth_md,  mc_md):
    lastmonth_lines = lastmonth_md.split("\n")
    md_lines = mc_md.split("\n")
    lastmonth_empty_leadings, lastmonth_lines = split_empty_leadings(lastmonth_lines)
    mc_empty_leadings, mc_lines = split_empty_leadings(md_lines)
    result, diff_set = get_diff_set(lastmonth_lines, mc_lines, lastmonth_empty_leadings, mc_empty_leadings)
    #print("\n".join([str(x) for x in diff_set]))
    com_md, modification = construct_com_md("\n".join(result), diff_set)
    #print("\n".join([str(x) for x in modification]))
    com_md = re.sub("(^|\n)  ", r"\1", com_md)
    mdcontent = apply_modification(mdcontent, com_md, modification)
    #mdcontent = com_md
    return mdcontent

def customize_compare_mdcontent2(mdcontent, lastmonth_md,  mc_md):
    diff_set = get_diff_set(lastmonth_md.split("\n"), mc_md.split("\n"))
    com_content, modification = construct_com_md(diff_set)
    mdcontent = apply_modification(mdcontent, com_content, modification)
    return mdcontent

def split_empty_leadings(lines):
    empty_leadings = []
    content_lines = []
    for line in lines:
        line_stripped = line.strip()
        index = line.find(line_stripped)
        empty_leadings.append(line[:index])
        content_lines.append(line[index:])
    return empty_leadings, content_lines

def getlastmonthmd(filepath, repopath):
    global g
    if g==None:
        g = git.Git(repopath)
    result = g.show("lastmonthcustomized:"+filepath).replace("\ufeff", "")
    return result.strip()
