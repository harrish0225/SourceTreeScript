import subprocess
import os
import re

include_reg = r"(?P<includeText>\[\!INCLUDE\s\[[^\[|^\]]*\]\((?P<fileName>[\.\w\-/\d]+)\)\])"

def replaceInclude(fileRelativePath, filename, mooncake_path, parent_path="../../"):
    input = open(mooncake_path + "/" + fileRelativePath+"/"+filename, "r", encoding="utf8")
    text = input.read()
    old_text = text
    input.close()
    includeList = list(set(re.findall(include_reg, text)))
    for include in includeList:
        includeText = include[0]
        includeFile = include[1]
        try:
            input = open(mooncake_path + "/" + fileRelativePath+"/" + includeFile, "r", encoding="utf8")
            include_path, include_filename = os.path.split(includeFile)
            replacement = re.sub("(\]\(|\]: *|src=[\"'])([\.\w\-/\d]+|)media", "\\1"+include_path+"/\\2media", input.read())
            input.close()
        except IOError:
            replacement = ""
        text = text.replace(includeText, replacement)
    output = open(mooncake_path + "/" + fileRelativePath+"/"+filename, "w", encoding="utf8")
    output.writelines(text)
    output.close()
    return old_text

def convert(filepath, mooncake_path):
    dir, file = os.path.split(filepath)
    old_text = replaceInclude(dir, file, mooncake_path)
    print("processing: "+file)
    os.chdir(mooncake_path+"/"+dir)
    depth = filepath.count("/")
    relative = "../"*depth+"output/"
    if not os.path.isdir(relative+dir):
        os.makedirs(relative+dir)
    ret = subprocess.call(["pandoc","-s", "-S", file, "-o", relative+dir+"/"+file[:len(file)-3]+'.docx'], shell=True)
    revertfile = open(mooncake_path+"/"+filepath, "w", encoding="utf8")
    revertfile.write(old_text)
    revertfile.close()
    return

if __name__ == '__main__':
    filepath = "articles/virtual-network/virtual-networks-create-vnet-classic-portal.md"
    mooncake_path = "E:/GitHub/azure-content-mooncake-pr"
    os.chdir(mooncake_path)
    convert(filepath, mooncake_path)