import subprocess
import os
from pantoolPre import replaceInclude

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