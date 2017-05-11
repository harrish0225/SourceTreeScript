from matchingSeq import *


def test_whole():
    acom_path = "E:/GitHub/azure-content-pr/articles/redis-cache/cache-configure.md"
    mc_path = "E:/GitHub/mc-docs-pr.en-us/articles/redis-cache/cache-configure.md"

    acom_file = open(acom_path, "r", encoding="utf8")
    acom_content = acom_file.read().strip()
    acom_file.close()

    mc_file = open(mc_path, "r", encoding="utf8")
    mc_content = mc_file.read().strip()
    mc_file.close()

    diff_set = get_diff_set(acom_content.split("\n"), mc_content.split("\n"))
    com_content, (additions, replacements, inline_replacements, inline_additions) = construct_com_md(diff_set)
    
    out_file = open("cache-configure.md", "w", encoding="utf8")
    out_file.write(com_content)
    out_file.close()
    
    com_content = apply_modification(acom_content, com_content, (additions, replacements, inline_replacements, inline_additions))
    out_file = open("cache-configure2.md", "w", encoding="utf8")
    out_file.write(com_content)
    out_file.close()

def test_refine_ops():
    s1 = "1\n2\n3\n4\n5"
    s2 = "1\n"+REPLACEMENT_IDENTIFIER_BEGIN%("0")+"\n2\n3\n4\n5\n"+REPLACEMENT_IDENTIFIER_END+""
    lines1 = [Article_line(line) for line in s1.split("\n")]
    lines2 = [Article_line(line) for line in s1.split("\n")]
    ops = [("equal",0,5,0,5)]
    origin_com_lines = s2.split("\n")
    print("\n".join([str(x) for x in ops]))
    print("--------------------------------------------")
    ops = refine_ops(lines1, lines1, ops, origin_com_lines)
    print("\n".join([str(x) for x in ops]))

def test_apply_one_line():
    new_line = Article_line("1 2 3 4 5")
    com_line = Article_line("1 2 "+ADDITION_IDENTIFIER_INLINE%(str(0))+" 3 4 5")
    modification = ([], [], [], ["9"])
    line = apply_one_line(new_line, com_line, modification)
    print(line)
    return

def test_word():
    a = "* [Using Azure CDN](../cdn/cdn-create-new-endpoint.md)"
    b = "* [ASP.NET Bundling and Minification](http://www.asp.net/mvc/tutorials/mvc-4/bundling-and-minification)"
    aa = Article_line(a)
    ab = Article_line(b)

    print(aa == ab)


if __name__ == '__main__':

    
    test_word()

    """
    a = Article_line("The **Settings** section allows you to access and configure the following settings for your cache.")
    b = Article_line('The settings in the **General** section allow you to access and configure the following settings for your cache.')

    inline_replacements = []
    inline_additions = []

    print(handle_replace_one_line(a, b, inline_replacements, inline_additions))

    print("replacements")
    print("\n".join(inline_replacements))
    print("additions")
    print("\n".join(inline_additions))
    """

    """
    com_content = "This is a test\n"

    com_content+=DELETION_IDENTIFIER_BEGIN+"\n"
    com_content+="1\n"
    com_content+=DELETION_IDENTIFIER_END+"\n"
    com_content+=DELETION_IDENTIFIER_BEGIN+"\n"
    com_content+="2\n"
    com_content+=DELETION_IDENTIFIER_END+"\n"
    com_content+="\n"

    com_content+=DELETION_IDENTIFIER_BEGIN+"\n"
    com_content+="3\n"
    com_content+=DELETION_IDENTIFIER_END+"\n"
    com_content+=REPLACEMENT_IDENTIFIER_BEGIN%("0")+"\n"
    com_content+="4\n"
    com_content+=REPLACEMENT_IDENTIFIER_END+"\n"
    com_content+="\n"

    com_content+=DELETION_IDENTIFIER_BEGIN+"\n"
    com_content+="5\n"
    com_content+=DELETION_IDENTIFIER_END+"\n"
    com_content+=ADDITION_IDENTIFIER%("0")+"\n"
    com_content+="\n"

    com_content+=REPLACEMENT_IDENTIFIER_BEGIN%("1")+"\n"
    com_content+="6\n"
    com_content+=REPLACEMENT_IDENTIFIER_END+"\n"
    com_content+=DELETION_IDENTIFIER_BEGIN+"\n"
    com_content+="7\n"
    com_content+=DELETION_IDENTIFIER_END+"\n"
    com_content+="\n"

    com_content+=REPLACEMENT_IDENTIFIER_BEGIN%("2")+"\n"
    com_content+="8\n"
    com_content+=REPLACEMENT_IDENTIFIER_END+"\n"
    com_content+=REPLACEMENT_IDENTIFIER_BEGIN%("3")+"\n"
    com_content+="9\n"
    com_content+=REPLACEMENT_IDENTIFIER_END+"\n"
    com_content+="\n"

    com_content+=REPLACEMENT_IDENTIFIER_BEGIN%("4")+"\n"
    com_content+="10\n"
    com_content+=REPLACEMENT_IDENTIFIER_END+"\n"
    com_content+=ADDITION_IDENTIFIER%("1")+"\n"
    com_content+="\n"

    com_content+=ADDITION_IDENTIFIER%("2")+"\n"
    com_content+=DELETION_IDENTIFIER_BEGIN+"\n"
    com_content+="11\n"
    com_content+=DELETION_IDENTIFIER_END+"\n"
    com_content+="\n"

    com_content+=ADDITION_IDENTIFIER%("3")+"\n"
    com_content+=REPLACEMENT_IDENTIFIER_BEGIN%("5")+"\n"
    com_content+="12\n"
    com_content+=REPLACEMENT_IDENTIFIER_END+"\n"
    com_content+="\n"

    com_content+=ADDITION_IDENTIFIER%("4")+"\n"
    com_content+=ADDITION_IDENTIFIER%("5")+"\n"
    com_content+="\n"


    print(com_content)

    additions = ["a0", "a1", "a2", "a3", "a4", "a5"]

    replacements = ["r4", "r6", "r8", "r9", "r10", "r12"]

    print(additions)

    print(replacements)

    print(refine_com_content(com_content, additions, replacements))

    print(additions)

    print(replacements)


    """