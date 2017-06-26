import re
import json
import os
from .listAndCode import refineNestedListContent

CONSTANT_RULE_FILE = "rules/constant.json"
SEMI_RULE_FILE = "rules/semiconstant.json"
REGEX_RULE_FILES = "rules/regular_level"
CORRECTION_RULE_FILE = "rules/correction.json"

constant = None
regex_list = None
semi = None
correction = None
regex = None

file_belonging = {
      "application-gateway": "v-dazen",
      "app-service": "v-dazen",
      "app-service-api": "v-dazen",
      "app-service-web": "v-dazen",
      "automation": "v-dazen",
      "hdinsight": "v-dazen",
      "redis-cache": "v-dazen",
      "traffic-manager": "v-dazen",
      "virtual-machines": "v-dazen",
      "virtual-machine-scale-sets": "v-dazen",
      "virtual-network": "v-dazen",
      "vpn-gateway": "v-dazen",
      "app-service-mobile": "v-yiso",
      "azure-portal": "v-yiso",
      "cache": "v-yiso",
      "cloud-services": "v-yiso",
      "expressroute": "v-yiso",
      "iot-hub": "v-yiso",
      "iot-suite": "v-yiso",
      "monitoring-and-diagnostics": "v-yiso",
      "service-bus": "v-yiso",
      "service-bus-messaging": "v-yiso",
      "service-bus-relay": "v-yiso",
      "active-directory": "v-junlch",
      "backup": "v-junlch",
      "batch": "v-junlch",
      "documentdb": "v-junlch",
      "key-vault": "v-junlch",
      "media": "v-junlch",
      "multi-factor-authentication": "v-junlch",
      "notification-hubs": "v-junlch",
      "power-bi-embedded": "v-junlch",
      "Others": "v-junlch",
      "azure-resource-manager": "v-yeche",
      "cosmos-db": "v-yeche",
      "event-hubs": "v-yeche",
      "load-balancer": "v-yeche",
      "resiliency": "v-yeche",
      "sql-data-warehouse": "v-yeche",
      "sql-server-stretch-database": "v-yeche",
      "stream-analytics": "v-yeche",
      "cognitive-services": "v-johch",
      "media-services": "v-johch",
      "scheduler": "v-johch",
      "security": "v-johch",
      "service-fabric": "v-johch",
      "site-recovery": "v-johch",
      "sql-database": "v-johch",
      "storage": "v-johch"
}

def customize(filepath, script_path, repopath, prefix=""):
    getRule(script_path, prefix)
    file = open(filepath, "r", encoding="utf8")
    mdcontent = file.read()
    file.close()
    mdcontent = customize_mdcontent(mdcontent, repopath, filepath)
    file = open(filepath, "w", encoding="utf8")
    file.write(mdcontent)
    file.close()

def customize_mdcontent(mdcontent, repopath, filepath, add_domain=True):
    mdcontent = constant_replacement(mdcontent)
    mdcontent = regex_replacement(mdcontent)
    mdcontent = semi_replacement(mdcontent)
    mdcontent = correction_replacement(mdcontent)
    mdcontent = refineNestedListContent(mdcontent, True)
    mdcontent = change_ms_author(mdcontent, repopath, filepath)
    if add_domain:
        mdcontent = re.sub("(\]\(|\]:\s*|href\s*=\s*\")((https?:)?(//)?(www\.)?azure\.cn)?(/zh-cn)?(/home/features/|/pricing/|/blog|/support/|/product-feedback|/solutions|/partnerancasestudy)", r"\1https://www.azure.cn\7", mdcontent)
    return mdcontent.strip()

def change_ms_author(mdcontent, repopath, filepath):
    if len(re.findall("ms\.author:\s*", mdcontent))>0:
        mdcontent = re.sub("ms\.author: *.*\n", "ms.author: "+get_author(filepath, repopath)+"\n", mdcontent, 1)
    return mdcontent

def get_author(filepath, repopath):
    filepath = filepath.replace("\\", "/")
    relative_path = filepath[len(repopath)+10:].split("/")
    if file_belonging.get(relative_path[0]):
        return file_belonging.get(relative_path[0])
    else:
        return file_belonging["Others"]

def constant_replacement(mdcontent):
    if len(constant) > 0:
        constRegex = re.compile("(%s)" % "|".join(map(re.escape, constant.keys())))
        mdcontent = constRegex.sub(lambda mo: constant[mo.string[mo.start():mo.end()]], mdcontent)
    return mdcontent

def regex_replacement(mdcontent):
    global regex
    for i in regex_list:
        regex = i
        if len(regex) > 0:
            regexRegex = re.compile("(%s)" % "|".join([rule["regex"] for rule in regex]))
            mdcontent = regexRegex.sub(get_replacement_for_regex, mdcontent)
    return mdcontent

def get_replacement_for_regex(mo):
    found = mo.string[mo.start():mo.end()]
    for rule in regex:
        m = re.match(rule["regex"], found)
        if m:
            match_tuple=m.groups()
            for replacement in rule["replacements"]:
                correct_replacement = True
                for condition in replacement["conditions"]:
                    if (condition["match"]!=None and match_tuple[condition["parameter"]]==None) or (condition["match"]==None and match_tuple[condition["parameter"]]!=None) or not ((condition["match"]==None and match_tuple[condition["parameter"]]==None) or re.match(condition["match"], match_tuple[condition["parameter"]])):
                        correct_replacement = False
                        break
                if correct_replacement == True:
                    value = re.sub(rule["regex"], replacement["replacement"], found)
                    break
            return value
    return found

def semi_replacement(mdcontent):
    if len(semi) > 0:
        semiRegex = re.compile("(%s)" % "|".join(semi.keys()))
        mdcontent = semiRegex.sub(get_replacement_for_semi, mdcontent)
    return mdcontent

def get_replacement_for_semi(mo):
    found = mo.string[mo.start():mo.end()]
    for key, value in semi.items():
        if re.match(key, found):
            return value
    return found

def correction_replacement(mdcontent):
    if len(correction) > 0:
        correctionRegex = re.compile("(%s)" % "|".join(map(re.escape, correction.keys())))
        mdcontent = correctionRegex.sub(lambda mo: correction[mo.string[mo.start():mo.end()]], mdcontent)
    return mdcontent

def getRule(script_path, prefix=""):
    global constant
    global semi
    global regex_list
    global correction
    if constant == None:
        file = open(script_path+"/"+prefix+CONSTANT_RULE_FILE, "r", encoding="utf8")
        constant = json.loads(file.read())
        file.close()
    if semi == None:
        file = open(script_path+"/"+prefix+SEMI_RULE_FILE, "r", encoding="utf8")
        semi = json.loads(file.read())
        file.close()
    if regex_list == None:
        i = 0
        regex_list = []
        rule_file = script_path+"/"+prefix+REGEX_RULE_FILES+str(i)+".json"
        while os.path.isfile(rule_file):
            file = open(rule_file, "r", encoding="utf8")
            regex_list.append(json.loads(file.read()))
            file.close()
            i+=1
            rule_file = script_path+"/"+prefix+REGEX_RULE_FILES+str(i)+".json"
    if correction == None:
        file = open(script_path+"/"+prefix+CORRECTION_RULE_FILE, "r", encoding="utf8")
        correction = json.loads(file.read())
        file.close()