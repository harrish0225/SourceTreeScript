import re
import os
import glob
import json
from customization import get_transit_and_matching, compare_result_split2, REPLACEMENT_MARKER_ONELINE
from difflib import Differ

all_articles_path = {}
properties_reg = "([ \t\r\f\v]*\<properties\s*(\n?\s*[^\>\n]+\s*)+/\>\s*)"
tags_reg = "(\<tags\s*(\n?\s*[^\>\n]+\s*)+/\>\s*)"
attr_reg = "([^\s\=]+)\s*\=\s*\"([^\"\n]*)\""

global acom_files_path

acom_files_path = None

link_with_full_width_symbol_reg = "https?://[\.\w/%_\-\=\+;?:@&\<\>#\[\]{}|\\^~]+[”，。？：；！]"

landingpages = {
    "/documentation/services/active-directory-b2c/":"/articles/active-directory-b2c/index.md",
    "/documentation/services/active-directory-domain-services/":"/articles/active-directory-domain-services/index.md",
    "/documentation/services/active-directory-ds/":"/articles/active-directory-ds/index.md",
    "/documentation/services/advisor/":"/articles/advisor/index.md",
    "/documentation/services/analysis-services/":"/articles/analysis-services/index.md",
    "/documentation/services/api-management/":"/articles/api-management/index.md",
    "/documentation/services/application-gateway/":"/articles/application-gateway/index.md",
    "/documentation/services/application-insights/":"/articles/application-insights/index.md",
    "/documentation/services/app-service/api/":"/articles/app-service-api/index.md",
    "/documentation/services/app-service/logic/":"/articles/app-service-logic/index.md",
    "/documentation/services/app-service/mobile/":"/articles/app-service-mobile/index.md",
    "/documentation/services/app-service/web/":"/articles/app-service-web/index.md",
    "/documentation/services/app-service/":"/articles/app-service/index.md",
    "/documentation/services/automation/":"/articles/automation/index.md",
    "/documentation/services/azure-functions/":"/articles/azure-functions/index.md",
    "/documentation/services/azure-government/":"/articles/azure-government/index.md",
    "/documentation/services/azure-portal/":"/articles/azure-portal/index.md",
    "/documentation/services/azure-resource-manager/":"/articles/azure-resource-manager/index.md",
    "/documentation/services/azure-stack/":"/articles/azure-stack/index.md",
    "/documentation/services/azure-supportability/":"/articles/azure-supportability/index.md",
    "/documentation/services/azure-operations-guide/":"/articles/azure-operations-guide/index.md",
    "/documentation/services/backup/":"/articles/backup/index.md",
    "/documentation/services/batch/":"/articles/batch/index.md",
    "/documentation/services/billing/":"/articles/billing/index.md",
    "/documentation/services/biztalk-services/":"/articles/biztalk-services/index.md",
    "/documentation/services/cache/":"/articles/cache/index.md",
    "/documentation/services/cdn/":"/articles/cdn/index.md",
    "/documentation/services/cloud-services/":"/articles/cloud-services/index.md",
    "/documentation/services/cognitive-services/":"/articles/cognitive-services/index.md",
    "/documentation/services/connectors/":"/articles/connectors/index.md",
    "/documentation/services/container-registry/":"/articles/container-registry/index.md",
    "/documentation/services/container-service/":"/articles/container-service/index.md",
    "/documentation/services/data-catalog/":"/articles/data-catalog/index.md",
    "/documentation/services/data-factory/":"/articles/data-factory/index.md",
    "/documentation/services/data-lake-analytics/":"/articles/data-lake-analytics/index.md",
    "/documentation/services/data-lake-store/":"/articles/data-lake-store/index.md",
    "/documentation/services/devtest-lab/":"/articles/devtest-lab/index.md",
    "/documentation/services/dns/":"/articles/dns/index.md",
    "/documentation/services/documentdb/":"/articles/documentdb/index.md",
    "/documentation/services/event-hubs/":"/articles/event-hubs/index.md",
    "/documentation/services/expressroute/":"/articles/expressroute/index.md",
    "/documentation/services/functions/":"/articles/functions/index.md",
    "/documentation/services/guidance/":"/articles/guidance/index.md",
    "/documentation/services/hdinsight/":"/articles/hdinsight/index.md",
    "/documentation/services/identity/":"/articles/active-directory/index.md",
    "/documentation/services/iot-hub/":"/articles/iot-hub/index.md",
    "/documentation/services/iot-suite/":"/articles/iot-suite/index.md",
    "/documentation/services/key-vault/":"/articles/key-vault/index.md",
    "/documentation/services/load-balancer/":"/articles/load-balancer/index.md",
    "/documentation/services/log-analytics/":"/articles/log-analytics/index.md",
    "/documentation/services/logic-apps/":"/articles/logic-apps/index.md",
    "/documentation/services/machine-learning/":"/articles/machine-learning/index.md",
    "/documentation/services/marketplace-consumer/":"/articles/marketplace-consumer/index.md",
    "/documentation/services/marketplace-publishing/":"/articles/marketplace-publishing/index.md",
    "/documentation/services/media-services/":"/articles/media-services/index.md",
    "/documentation/services/mobile-services/":"/articles/mobile-services/index.md",
    "/documentation/services/monitoring-and-diagnostics/":"/articles/monitoring-and-diagnostics/index.md",
    "/documentation/services/multi-factor-authentication/":"/articles/multi-factor-authentication/index.md",
    "/documentation/services/mysql/":"/articles/mysql/index.md",
    "/documentation/services/networking/":"/articles/virtual-network/index.md",
    "/documentation/services/notification-hubs/":"/articles/notification-hubs/index.md",
    "/documentation/services/operations-management-suite/":"/articles/operations-management-suite/index.md",
    "/documentation/services/power-bi-embedded/":"/articles/power-bi-embedded/index.md",
    "/documentation/services/redis-cache/":"/articles/redis-cache/index.md",
    "/documentation/services/remoteapp/":"/articles/remoteapp/index.md",
    "/documentation/services/resiliency/":"/articles/resiliency/index.md",
    "/documentation/services/resource-health/":"/articles/resource-health/index.md",
    "/documentation/services/scheduler/":"/articles/scheduler/index.md",
    "/documentation/services/search/":"/articles/search/index.md",
    "/documentation/services/security/":"/articles/security/index.md",
    "/documentation/services/security-center/":"/articles/security-center/index.md",
    "/documentation/services/service-bus/":"/articles/service-bus/index.md",
    "/documentation/services/service-bus-messaging/":"/articles/service-bus-messaging/index.md",
    "/documentation/services/service-bus-relay/":"/articles/service-bus-relay/index.md",
    "/documentation/services/service-fabric/":"/articles/service-fabric/index.md",
    "/documentation/services/site-recovery/":"/articles/site-recovery/index.md",
    "/documentation/services/sql-databases/":"/articles/sql-database/index.md",
    "/documentation/services/sql-data-warehouse/":"/articles/sql-data-warehouse/index.md",
    "/documentation/services/sql-server-stretch-database/":"/articles/sql-server-stretch-database/index.md",
    "/documentation/services/storage/":"/articles/storage/index.md",
    "/documentation/services/storsimple/":"/articles/storsimple/index.md",
    "/documentation/services/stream-analytics/":"/articles/stream-analytics/index.md",
    "/documentation/services/traffic-manager/":"/articles/traffic-manager/index.md",
    "/documentation/services/virtual-machines/":"/articles/virtual-machines/index.md",
    "/documentation/services/virtual-machines/linux/":"/articles/virtual-machines/linux/index.md",
    "/documentation/services/virtual-machines/windows/":"/articles/virtual-machines/windows/index.md",
    "/documentation/services/virtual-machine-scale-sets/":"/articles/virtual-machine-scale-sets/index.md",
    "/documentation/services/vpn-gateway/":"/articles/vpn-gateway/index.md",
    "/documentation/services/web-sites/":"/articles/app-service-web/index.md"
    }

def fitOPS(filepath, repopath, acompath, script_path):
    file = open(filepath, "r", encoding="utf8")
    mdcontent = file.read().strip()
    file.close()
    mdcontent = replace_properties_and_tags(mdcontent)
    mdcontent = replace_self_define_tags(mdcontent)
    mdcontent = replace_relative_links(mdcontent, filepath, repopath)
    mdcontent = replace_multiple_empty_lines(mdcontent)
    mdcontent = replace_others(mdcontent)
    mdcontent = replace_code_notation(mdcontent, filepath, repopath, acompath, script_path)
    file = open(filepath, "w", encoding="utf8")
    file.write(mdcontent)
    file.close()
    return

def replace_code_notation(mdcontent, filepath, repopath, acompath, script_path):
    mdcontent = re.sub("(\n\s*)~~~(\s*(\n|$))", "\\1```\\2", mdcontent)
    code_blocks = identify_code_block(mdcontent)
    result = ""
    if len(code_blocks)>0:
        acom_code_blocks = get_acom_code_blocks(filepath, repopath, acompath, script_path)
        
        code_blocks = get_programming_language(acom_code_blocks, code_blocks)
        
    for block in code_blocks:
        replaceBlock = block[1]+"```"+block[2]+("\n"+block[0]).replace("\n    ", "\n")+"\n"+block[1]+"```"
        i = mdcontent.find(block[0])
        result+= mdcontent[:i]+replaceBlock
        mdcontent = mdcontent[i+len(block[0]):]
    result+= mdcontent
    result = re.sub("```(\s*)\n\s*\<br/\>\s*\n(\s*)```", r"```\1\n\n\2```", result)
    return result

def update_acom_files_path(script_path):
    global acom_files_path
    if acom_files_path!=None:
        file = open(script_path+"/acom_files_path.json", "w", encoding="utf8")
        json_s = json.dumps(acom_files_path)
        file.write(json_s)
        file.close()

def get_acom_file(filepath, repopath, acompath, script_path):
    global acom_files_path
    if acom_files_path==None:
        file = open(script_path+"/acom_files_path.json", "r", encoding="utf8")
        acom_files_path = json.loads(file.read())
        file.close()
    filename = os.path.basename(filepath)
    if acom_files_path.get(filename)!=None:
        if acom_files_path[filename]=="":
            return None
        temp_path = acompath+acom_files_path[filename]
    else:
        temp_path = acompath+filepath[len(repopath):]
    if os.path.isfile(temp_path):
        file = open(temp_path, 'r', encoding="utf8")
        mdcontent = file.read()
        file.close()
        if "redirect_url:" not in mdcontent:
            acom_files_path[filename]=temp_path.replace("\\", "/")[len(acompath):]
            return mdcontent

    poss_filelist = glob.glob(acompath+"/**/"+filename)
    poss_filelist.extend(glob.glob(acompath+"/**/**/"+filename))
    poss_filelist.extend(glob.glob(acompath+"/**/**/**/"+filename))
    poss_filelist.extend(glob.glob(acompath+"/**/**/**/**/"+filename))
    poss_filelist.extend(glob.glob(acompath+"/**/**/**/**/**/"+filename))

    for temp_path in poss_filelist:
        file = open(temp_path, 'r', encoding="utf8")
        mdcontent = file.read()
        file.close()
        if "redirect_url:" not in mdcontent:
            acom_files_path[filename]=temp_path.replace("\\", "/")[len(acompath):]
            return mdcontent
    acom_files_path[filename]=""
    return None

def get_acom_code_blocks(filepath, repopath, acompath, script_path):
    mdcontent = get_acom_file(filepath, repopath, acompath, script_path)

    if mdcontent==None:
        return []

    mdcontent = re.sub("^(\s*)\~{3,}(\s*)$", r"\1```\2", mdcontent)

    if "```" not in mdcontent:
        return []
    mdcontent = re.sub("\`{3,}", "\1\1\1", mdcontent)

    m = re.findall("(\n([\n\s]*\1{3}([^\1\n]*)\s*\n(([^\1\n]*\s*\n)+)\s*(\1{3}|$))+[ \t\r\f\v]*\n*)", mdcontent)
    if len(m) > 0:
        last_one = m[len(m)-1][0].strip()
        if last_one[len(last_one)-1] != '\1':
            print("The md file contains odd numbers of '```'")
            return []
        result = []
        for i in m:
            if i[2].strip()!="":
                result.append((i[2].strip(), i[3].strip()))
        return result
    return []

def get_programming_language(acom_code_blocks, code_blocks):
    result = []
    for block in code_blocks:
        result.append((block[0], block[1], get_programming_language_for_one_block(acom_code_blocks, block)))
    return result

def get_programming_language_for_one_block(acom_code_blocks, block):
    code_lines = [line.strip() for line in block[0].split("\n")]
    transits = []
    matchings = []
    for acom_block in acom_code_blocks:
        acom_code_lines = [line.strip() for line in acom_block[1].split("\n")]
        
        differ = Differ()
        diff = list(differ.compare(code_lines, acom_code_lines))
        
        same_count = 0
        
        for diff_line in diff:
            if diff_line[0]==" ":
                same_count+=1
        
        if same_count!=len(code_lines):
            same_count+=get_similarity(diff)
        
        line_num_max = max(len(code_lines), len(acom_code_lines))
        line_num_min = min(len(code_lines), len(acom_code_lines))

        if same_count/len(code_lines)>0.7 and (line_num_max-line_num_min)/line_num_max<0.5:
            return acom_block[0]
        
    return ""

def get_similarity(diff):
    try:
        diff_set = compare_result_split2(diff)
    except:
        return 0
    result = 0
    for a_diff in diff_set:
        if len(a_diff)>=3 and a_diff[len(a_diff)-1]==REPLACEMENT_MARKER_ONELINE:
            removed = []
            added = []
            for line in a_diff[:len(a_diff)-1]:
                if line[0]=="-":
                    removed.append(line[2:])
                elif line[0]=="+":
                    added.append(line[2:])
            removed_words = " ".join(removed).split(" ")
            added_words = " ".join(added).split(" ")
            differ = Differ()
            if len(removed_words)<len(added_words):
                inline_diff = differ.compare(removed_words, added_words)
            else:
                inline_diff = differ.compare(added_words, removed_words)
            transit, matching = get_transit_and_matching(inline_diff)
            if transit<=2 and matching>0.7:
                result+=matching
    return result

def identify_code_block(mdcontent):
    lines = mdcontent.split("\n")
    i = 0
    result = []
    while i < len(lines)-2:
        if re.match("^\s*\<pre\s*class\=[\"']prettyprint[\"']\>\s*$", lines[i].strip()):
            i+=1
            while not re.match("^\s*\</pre\>\s*$", lines[i].strip()):
                i+=1
            if i >= len(lines)-2:
                break
        if re.match("^\s*````*\s*[\w#]*\s*$", lines[i].strip()):
            i+=1
            while not re.match("^\s*````*\s*$", lines[i].strip()):
                i+=1
            if i >= len(lines)-2:
                break
        if lines[i+1]=="":
            m = re.match("^\s*(\d+\.\s|[\*\-\+]\s)", lines[i])
            if not m:
                j = i-1
                while j>=0:
                    if lines[j]=="":
                        break
                    elif re.match("^\s*(\d+\.\s|[\*\-\+]\s)", lines[j]):
                        j-=1
                        break
                    j-=1
                j+=1
                while j<=i and lines[j][0]=="#":
                    j+=1
                m = re.match("^\s*(\d+\.\s|[\*\-\+]\s)", lines[j])
            else:
                
                j=i
            leading_white1 = get_leading_white(lines[j])
            leading_white2 = get_leading_white(lines[i+2])
            if m:
                leading_white_standard = len(leading_white1)+8
            else:
                leading_white_standard = len(leading_white1)+4
            if len(leading_white2) >= leading_white_standard:
                aBlock = [lines[i+2]]
                i = i+3
                while i < len(lines):
                    if lines[i] == "" or len(get_leading_white(lines[i]))>=leading_white_standard:
                        aBlock.append(lines[i])
                        i+=1
                        continue
                    else:
                        break
                if aBlock[len(aBlock)-1] == "":
                    result.append(("\n".join(aBlock[:len(aBlock)-1]), " "*(leading_white_standard-4)))
                else:
                    result.append(("\n".join(aBlock), " "*(leading_white_standard-4)))
            else:
                i+=1
        elif len(lines[i])>0 and lines[i][0]=="#" and lines[i+1][:4]=="    ":
            leading_white_standard = 4
            aBlock = [lines[i+1]]
            i = i+2
            while i < len(lines):
                if lines[i] == "" or len(get_leading_white(lines[i]))>=leading_white_standard:
                    aBlock.append(lines[i])
                    i+=1
                    continue
                else:
                    break
            if aBlock[len(aBlock)-1] == "":
                result.append(("\n".join(aBlock[:len(aBlock)-1]), ""))
            else:
                result.append(("\n".join(aBlock), ""))
        else:
            i+=1
    return result

def get_leading_white(aString):
    m = re.match("(\s*)", aString)
    return m.group()

def replace_others(mdcontent):
    while len(re.findall("\n *\t", mdcontent))>0:
        mdcontent = re.sub("(\n *)\t", r"\1    ", mdcontent)
    mdcontent = re.sub("\n +\n", "\n\n", mdcontent)
    mdcontent = re.sub("(\n *)(\d+\.|\*|\-|\+)\t", r"\1\2 ", mdcontent)
    return mdcontent

def replace_properties_and_tags(mdcontent):
    properties_m = re.findall(properties_reg, mdcontent)
    tags_m = re.findall(tags_reg, mdcontent)
    result = "---\n"
    if len(properties_m)>0:
        properties_str = properties_m[0][0]
        result += getAttributes(properties_str)
    else:
        properties_str=""
    if len(tags_m)>0:
        if properties_str!="":
            result += "\n"
        tags_str = tags_m[0][0]
        result += getAttributes(tags_str)
    else:
        tags_str = ""
    if tags_str=="" and properties_str=="":
        return mdcontent
    result += "---\n\n"
    properties_index = mdcontent.find(properties_str)
    if properties_index>=2:
        if mdcontent[properties_index-1]!="\n" or mdcontent[properties_index-2]!="\n":
            result = "\n"+result
    mdcontent = mdcontent.replace(properties_str+tags_str, result)
    return mdcontent

def getAttributes(attr_str):
    attr_m = re.findall(attr_reg, attr_str)
    result = ""
    for attr in attr_m:
        if attr[0] == "pageTitle":
            name = "title"
        else:
            name = attr[0]
        if attr[1].strip() == "":
            value = "''"
        else:
            value = attr[1]
        result += name+": "+value+"\n"
    return result


def replace_self_define_tags(mdcontent):
    mdcontent = re.sub("([ \t\r\f\v]*)\>?([ \t\r\f\v]*)\[(AZURE|WACOM)\.(NOTE\]|IMPORTANT\]|WARNING\]|TIP\])([ \t\r\f\v]*[^\s\n])",r"\1>\2[!\4\n\1>\5",mdcontent)
    mdcontent = re.sub("([ \t\r\f\v]*)\>?([ \t\r\f\v]*)\[(AZURE|WACOM)\.(NOTE\]|IMPORTANT\]|WARNING\]|TIP\])",r"\1>\2[!\4",mdcontent)
    mdcontent = mdcontent.replace("[AZURE.INCLUDE", "[!INCLUDE")
    mdcontent = re.sub("\[AZURE\.SELECTOR\][ \t\r\f\v]*", "[!div class=\"op_single_selector\"]", mdcontent)
    return mdcontent

def replace_relative_links(mdcontent, path, repopath):
    m = re.findall("((\]\(|\]:\s*|href\s*=\s*[\"'])((https?:)?(//)?(www\.)?azure\.cn)?(/zh-cn)?/documentation/articles/[^/#\)\"'\s\?]+(/|/?#|/?\)|/?[\"']|/?[\s\n]|/?\?))", mdcontent)
    links = sorted(list(set([x[0] for x in m])), reverse=True)
    for link in links:
        m = re.match("(\]\(|\]:\s*|href\s*=\s*[\"'])((https?:)?(//)?(www\.)?azure\.cn)?(/zh-cn)?/documentation/articles/([^/#\)\"'\s\?]+)(/|/?#|/?\)|/?[\"']|/?[\s\n]|/?\?)", link)
        m_group = m.groups()
        filename = m_group[6]+".md"
        prefix = m_group[0]
        filepath = get_path(filename, path)
        if filepath == None:
            continue
        l = len(link)
        if link[l-1] in ["#", ")", "\"", "'", " ", "\n", "\t", "\r", "\v", "\f", "?"]:
            filepath = prefix + filepath + link[l-1]
        else:
            filepath = prefix + filepath
        mdcontent = mdcontent.replace(link, filepath)
    mdcontent = re.sub("(\]\(|\]:\s*|href\s*=\s*\")((https?:)?(//)?(www\.)?azure\.cn)?(/zh-cn)?(/home/features/|/pricing/|/blog|/support/|/product-feedback|/solutions|/partnerancasestudy)", r"\1https://www.azure.cn\7", mdcontent)
    mdcontent = replace_landing_page(mdcontent, path, repopath)
    mdcontent = re.sub("((\]\(|\]:\s*|href\s*=\s*[\"'])(./|(../)+)[^\s\n\"'#]+.md#[^\s\n\"'/\)]+)/([\)\"'])", r"\1\5", mdcontent)
    m = re.findall("(\[http[^\]]+\]\([^\)]+\))", mdcontent)
    for i in m:
        matchlink = re.match("\[(https?://[^\]]+)\]\(([^\)]+)\)", i)
        m_group = matchlink.groups()
        if m_group[0]!=m_group[1]:
            mdcontent = mdcontent.replace(i, "["+m_group[1]+"]("+m_group[1]+")")
    return mdcontent

def replace_landing_page(mdcontent, path, repopath):
    m = re.findall("((\]\(|\]:\s*|href\s*=\s*[\"'])((https?:)?(//)?(www\.)?azure\.cn)?(/zh-cn)?/documentation/services/([\w-]+/?)(([\w-]+)/?)?)", mdcontent)
    links = sorted(list(set([x[0] for x in m])), reverse=True)
    for link in links:
        replaced = link
        m = re.match("(\]\(|\]:\s*|href\s*=\s*[\"'])((https?:)?(//)?(www\.)?azure\.cn)?(/zh-cn)?(/documentation/services/([\w-]+/?)(([\w-]+)/?)?)", link)
        m_group = m.groups()
        link = m_group[6]
        prefix = m_group[0]
        if link[len(link)-1]!="/":
            link+="/"
        linkpath = repopath+landingpages.get(link)
        if linkpath == None:
            continue
        filepath = get_path_with_2_path(path, linkpath)
        mdcontent = mdcontent.replace(replaced, prefix+filepath)
    return mdcontent

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

def get_path(filename, path):
    if all_articles_path.get(filename) == None:
        return None
    linkpath = all_articles_path[filename]
    return get_path_with_2_path(path, linkpath)

def get_path_with_2_path(path, linkpath):
    path_list = splitpath(path)
    linkpath_list = splitpath(linkpath)
    l = len(path_list)
    j = l-1
    for i in range(l):
        if path_list[i] != linkpath_list[i]:
            j = i
            break
    if j == l-1:
        return "./"+"/".join(linkpath_list[j:])
    else:
        return "/".join([".."]*(l-j-1))+"/"+"/".join(linkpath_list[j:])

def splitpath(path):
    path_list = []
    path, folder = os.path.split(path)
    while folder!="":
        path_list.append(folder)
        path, folder = os.path.split(path)
    path_list = reversed(path_list)
    return list(path_list)

def replace_multiple_empty_lines(mdcontent):
    mdcontent = re.sub("\n([ \t\r\f\v]*)\n([ \t\r\f\v]*\n)+", r"\n\n", mdcontent)
    return mdcontent

def get_all_articles_path(repopath):
    mdList = glob.glob(repopath+"/articles/**/*.md")
    mdList.extend(glob.glob(repopath+"/articles/*.md"))
    mdList.extend(glob.glob(repopath+"/articles/**/**/*.md"))
    mdList.extend(glob.glob(repopath+"/articles/**/**/**/*.md"))
    for path in mdList:
        path = path.replace("\\", "/")
        filepath, filename = os.path.split(path)
        if all_articles_path.get(filename)!=None:
            print("error: duplicate files: "+path+" and "+all_articles_path[filename])
            exit(-1)
        all_articles_path[filename] = path

if __name__ == '__main__':
    get_all_articles_path("E:/GitHub/techcontent/")
    
    for v,k in all_articles_path.items():
        print("Processing: "+k)
        fitOPS(k)
    for k in glob.iglob("E:/GitHub/techcontent/includes/*.md"):
        k = k.replace("\\", "/")
        print("Processing: "+k)
        fitOPS(k)
    mdList = glob.glob("E:/GitHub/techcontent/develop/**/*.md")
    mdList.extend(glob.glob("E:/GitHub/techcontent/develop/*.md"))
    mdList.extend(glob.glob("E:/GitHub/techcontent/develop/**/**/*.md"))
    mdList.extend(glob.glob("E:/GitHub/techcontent/develop/**/**/**/*.md"))
    for k in mdList:
        k = k.replace("\\", "/")
        print("Processing: "+k)
        fitOPS(k)
    for k in glob.iglob("E:/GitHub/techcontent/downloads/*.md"):
        k = k.replace("\\", "/")
        print("Processing: "+k)
        fitOPS(k)
    print("Processing: E:/GitHub/techcontent/downloads.md")
    fitOPS("E:/GitHub/techcontent/downloads.md")
    print("Processing: E:/GitHub/techcontent/documentation.md")
    fitOPS("E:/GitHub/techcontent/documentation.md")
    """
    print("Processing: E:/GitHub/techcontent/articles/hdinsight/hdinsight-hbase-geo-replication.md")
    fitOPS("E:/GitHub/techcontent/articles/hdinsight/hdinsight-hbase-geo-replication.md")
    print("Processing: E:/GitHub/techcontent/articles/hdinsight/hdinsight-use-oozie-linux-mac.md")
    fitOPS("E:/GitHub/techcontent/articles/hdinsight/hdinsight-use-oozie-linux-mac.md")
    """