from bs4 import BeautifulSoup
import sys


def _handle_inpage(ref, mdcontent, tech_content_path, put_message, messages):
    mdcontent = _replace_include(mdcontent, tech_content_path)
    match = re.findall("(id|name)\s*=\s*['\"]"+re.escape(ref[1:])+"['\"]", mdcontent)
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

def check_file(input_file, tech_content_path):
    file = open(input_file, 'r', encoding="utf8")
    list = file.read().split("/n")
    file.close()
    for filename in list:
        filename = filename.strip()
        if filename[len(filename)-3:] == ".md":
            handle_a_file(filename.strip(), tech_content_path)
    return True

def handle_a_file(filename, tech_content_path):
    file = open(tech_content_path+"/"+filename.strip(), 'r', encoding="utf8")
    print(file.read())
    file.close()

if __name__ == '__main__':
    if len(sys.argv) <= 2:
        print("Not enough arguments")
        sys.exit(-1)
    else:
        if check_file(sys.argv[1], sys.argv[2]):
            sys.exit(0)
        else:
            sys.exit(1)
