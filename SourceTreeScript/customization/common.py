import os

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
