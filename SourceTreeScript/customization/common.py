import re
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


def replaceUrlRelativeLink(filepath, repopath, replace_landing_page=False):
    file = open(filepath, "r", encoding="utf8")
    mdcontent = file.read()
    file.close()
    mdcontent = replaceUrlRelativeLink_mdcontent(mdcontent, filepath, repopath, replace_landing_page)
    file = open(filepath, "w", encoding="utf8")
    file.write(mdcontent)
    file.close()

def replaceUrlRelativeLink_mdcontent(mdcontent, filepath, repopath, replace_landing_page=False):
    global replaceUrlRelativeLink_filepath
    replaceUrlRelativeLink_filepath = filepath
    global replaceUrlRelativeLink_repopath
    replaceUrlRelativeLink_repopath = repopath
    global replaceUrlRelativeLink_replace_landing_page
    replaceUrlRelativeLink_replace_landing_page = replace_landing_page
    relative_link_regex = "('|\"|\()/azure/([\w\-]+(/[\w\-]+)*/?)('|\"|\)|\?|$)"
    regexRegex = re.compile(relative_link_regex)
    mdcontent = regexRegex.sub(get_replacement_for_UrlRelativeLink, mdcontent)
    relative_link_regex = "\]: */azure/([\w\-]+(/[\w\-]+)*/?)"
    regexRegex = re.compile(relative_link_regex)
    mdcontent = regexRegex.sub(get_replacement_for_UrlRelativeLink2, mdcontent)
    return mdcontent

def get_replacement_for_UrlRelativeLink(mo):
    found = mo.string[mo.start():mo.end()]
    filepath = replaceUrlRelativeLink_filepath
    repopath = replaceUrlRelativeLink_repopath
    if found[len(found)-1] not in ["'", "\"", ")", "?"]:
        return found
    relative_link = found[8:len(found)-1]
    left = found[0]
    right = found[len(found)-1]
    if relative_link[len(relative_link)-1]=="/":
        relative_link = relative_link[:len(relative_link)-1]
    mdpath = repopath+"/articles/"+relative_link+".md"
    if os.path.isfile(mdpath):
        return left + get_path_with_2_path(filepath, mdpath) + right
    if replaceUrlRelativeLink_replace_landing_page:
        mdpath = repopath+"/articles/"+relative_link+"/index.md"
        if os.path.isfile(mdpath):
            return left + get_path_with_2_path(filepath, mdpath) + right
    return found

def get_replacement_for_UrlRelativeLink2(mo):
    found = mo.string[mo.start():mo.end()]
    filepath = replaceUrlRelativeLink_filepath
    repopath = replaceUrlRelativeLink_repopath
    relative_link_regex = "(\]: *)/azure/([\w\-]+(/[\w\-]+)*/?)"
    m = re.match(relative_link_regex, found).groups()
    relative_link = m[1]
    left = m[0]
    if relative_link[len(relative_link)-1]=="/":
        relative_link = relative_link[:len(relative_link)-1]
    mdpath = repopath+"/articles/"+relative_link+".md"
    if os.path.isfile(mdpath):
        return left + get_path_with_2_path(filepath, mdpath)
    if replaceUrlRelativeLink_replace_landing_page:
        mdpath = repopath+"/articles/"+relative_link+"/index.md"
        if os.path.isfile(mdpath):
            return left + get_path_with_2_path(filepath, mdpath)
    return found

