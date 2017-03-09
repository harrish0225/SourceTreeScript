import re

def refineNestedList(filepath):
    file = open(filepath, "r", encoding="utf8")
    mdcontent = file.read()
    file.close()
    mdcontent = refineNestedListContent(mdcontent, True)
    file = open(filepath, "w", encoding="utf8")
    file.write(mdcontent)
    file.close()

def refineNestedListContent(mdcontent, replace_leading_tab):
    allLists = nestedListDetect(mdcontent.split("\n"))
    for nestedList in allLists:
        replacement = refineNestedListAndCode(nestedList, replace_leading_tab)
        mdcontent = mdcontent.replace("\n".join(nestedList), "\n".join(replacement), 1)
    return mdcontent

def nestedListDetect(lines):
    i=0
    result = []
    if re.match("([*-+]|\d+\.)\s", lines[i]):
        start_index = i
        while i < len(lines)-1:
            if not re.match("([*-+]|\d+\.)\s", lines[i+1]) and lines[i+1].strip()!="" and lines[i+1][:2]!="  " and lines[i+1][:2]!=" \t" and lines[i+1][0]!="\t":
                i-=1
                break
            i+=1
        i+=1
        result.append(lines[start_index:i+1])
    while i < len(lines)-1:
        if (lines[i].strip()=="" or lines[i][0]=="#") and re.match("([*-+]|\d+\.)\s", lines[i+1]):
            i+=1
            start_index = i
            while i < len(lines)-1:
                if not re.match("([*-+]|\d+\.)\s", lines[i+1]) and lines[i+1].strip()!="" and lines[i+1][:2]!="  " and lines[i+1][:2]!=" \t" and lines[i+1][0]!="\t":
                    i-=1
                    break
                i+=1
            i+=1
            result.append(lines[start_index:i+1])
        else:
            i+=1
    return result

def refineNestedListAndCode(nestedList, replace_leading_tab):
    if replace_leading_tab:
        nestedList = replaceLeadingTab(nestedList)
    result = []
    i=0
    nested = []
    while i<len(nestedList):
        if re.match("([*-+]|\d+\.)\s", nestedList[i]):
            inner_lines = handle_nested(nested)
            result.extend(inner_lines)
            result.append(nestedList[i])
            nested = []
        else:
            nested.append(nestedList[i])
        i+=1
    inner_lines = handle_nested(nested)
    result.extend(inner_lines)
    return result

def replaceLeadingTab(nestedList):
    result = []
    for line in nestedList:
        m = re.match("(\s+)(.+)",line)
        if m:
            m_g = m.groups()
            if "\t" in m_g[0]:
                result.append(m_g[0].replace("\t", "    ")+m_g[1])
            else:
                result.append(line)
        else:
            result.append(line)
    return result

def handle_nested(nested):
    if len(nested)==0:
        return []
    first_line = nested[0]
    leading_lines = []
    while (not re.match("([*-+]|\d+\.)\s", first_line.strip())) or first_line.strip()[:2] not in ["> ", ">[", ""]:
        nested = nested[1:]
        leading_lines.append(first_line)
        if len(nested)==0:
            return leading_lines
        first_line = nested[0]
    leading = get_smallest(nested)
    mdcontent_lines = []
    for line in nested:
        if line.strip()=="":
            mdcontent_lines.append(line)
        else:
            mdcontent_lines.append(line[leading:])
    mdcontent = "\n".join(mdcontent_lines)
    mdcontent = refineNestedListContent(mdcontent, False)
    result = []
    for line in mdcontent.split("\n"):
        if line.strip()=="":
            result.append(line)
        else:
            result.append("    "+line)
    if len(leading_lines)!=0:
        leading_lines.extend(result)
        return leading_lines
    return result

def get_smallest(nested):
    result = 4
    for line in nested:
        if line.strip()=="":
            continue
        m = re.match("(\s+)(.+)",line)
        if m:
            m_g = m.groups()
            if len(m_g[0])<result:
                result = len(m_g[0])
        else:
            raise Exception("nestedListDetectionError")
    return result