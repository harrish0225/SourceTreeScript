from difflib import SequenceMatcher
import re

"""
DELETION_IDENTIFIER_BEGIN = "{{d_b}}"
REPLACEMENT_IDENTIFIER_BEGIN = "{{r%s_b}}"
ADDITION_IDENTIFIER = "{{a%s}}"

DELETION_IDENTIFIER_END = "{{d_e}}"
REPLACEMENT_IDENTIFIER_END = "{{r_e}}"

DELETION_IDENTIFIER_BEGIN_INLINE = "{{di_b}}"
REPLACEMENT_IDENTIFIER_BEGIN_INLINE = "{{ri_%sb}}"
ADDITION_IDENTIFIER_BEGIN_INLINE = "{{ai_b}}"
ADDITION_IDENTIFIER_INLINE = "{{ai%s}}"

DELETION_IDENTIFIER_END_INLINE = "{{di_e}}"
REPLACEMENT_IDENTIFIER_END_INLINE = "{{ri_e}}"
ADDITION_IDENTIFIER_END_INLINE = "{{ai_e}}"
"""
DELETION_IDENTIFIER_BEGIN = "\x01"
REPLACEMENT_IDENTIFIER_BEGIN = "\x02%s\x02"
ADDITION_IDENTIFIER = "\x03%s\x03"

DELETION_IDENTIFIER_END = "\x04"
REPLACEMENT_IDENTIFIER_END = "\x02"

DELETION_IDENTIFIER_BEGIN_INLINE = "\x05"
REPLACEMENT_IDENTIFIER_BEGIN_INLINE = "\x06%s\x06"
ADDITION_IDENTIFIER_BEGIN_INLINE = "\x07"
ADDITION_IDENTIFIER_INLINE = "\x08%s\x08"

DELETION_IDENTIFIER_END_INLINE = "\x0e"
REPLACEMENT_IDENTIFIER_END_INLINE = "\x06"
ADDITION_IDENTIFIER_END_INLINE = "\x0f"


neighbor_regex = "("+DELETION_IDENTIFIER_END+"|"+REPLACEMENT_IDENTIFIER_END+"|"+ADDITION_IDENTIFIER%("\d+")+")\n("+DELETION_IDENTIFIER_BEGIN+"|"+REPLACEMENT_IDENTIFIER_BEGIN%("\d+")+"|"+ADDITION_IDENTIFIER%("\d+")+")"

class Article_line:
    line = ""
    formated_line = ""
    stripped_line = ""
    words = []

    def __init__(self, line):
        self.line = line
        self.stripped_line = self.line.strip()
        self.formated_line = re.sub("[ \t\r\f\v]+", " ", self.stripped_line.lower())
        self.words = self.formated_line.split(" ")
        return

    def __eq__(self, another):
        if self.stripped_line == "" and another.stripped_line == "":
            return True
        elif self.stripped_line == "" or another.stripped_line == "":
            return False

        s = SequenceMatcher(lambda x: False, self.words, another.words)
        ops = list(s.get_opcodes())
        if len(ops)==1 and ops[0][0]=="replace":
            return False
        del_and_ins_count = 0
        have_replace = False
        for op in ops:
            if op[0] in ["delete", "insert"]:
                del_and_ins_count+=1
            if op[0] == "replace":
                have_replace = True
                break
        if del_and_ins_count<=2 and have_replace == False:
            return True
        return s.ratio()>0.8

    def __hash__(self):
        return hash(self.formated_line)

class Article_word:
    word = ""
    formated_word = ""

    def __init__(self, word):
        self.word = word
        self.formated_word = self.word.lower()
        return

    def __eq__(self, another):
        return self.formated_word == another.formated_word

    def __hash__(self):
        return hash(self.formated_word)

def get_diff_set(string_lines1, string_lines2):
    diff_set = []
    lines1 = [Article_line(line) for line in string_lines1]
    lines2 = [Article_line(line) for line in string_lines2]
    return lines1, lines2, list(SequenceMatcher(lambda x: False, lines1, lines2).get_opcodes())

def get_diff_set_word(string_words1, string_words2):
    diff_set = []
    words1 = [Article_word(word) for word in string_words1]
    words2 = [Article_word(word) for word in string_words2]
    return words1, words2, list(SequenceMatcher(lambda x: False, words1, words2).get_opcodes())

def construct_com_md(diff_set):
    additions = []
    replacements = []
    inline_replacements = []
    inline_additions = []
    lines1 = diff_set[0]
    lines2 = diff_set[1]
    ops = diff_set[2]
    com_content = ""
    for op in ops:
        if op[0]=='equal':
            com_content += handle_equal(lines1, lines2, op, replacements, additions, inline_replacements, inline_additions)
        elif op[0]=='replace':
            com_content += handle_replace(lines1, lines2, op, replacements)
        elif op[0]=='insert':
            com_content += handle_insert(lines2, op, additions)
        elif op[0]=='delete':
            com_content += handle_delete(lines1, op)
    com_content = refine_com_content(com_content, additions, replacements).strip()
    return com_content, (additions, replacements, inline_replacements, inline_additions)

def refine_com_content(com_content, additions, replacements):
    neighbors = re.findall(neighbor_regex, com_content)
    while len(neighbors)!=0:
        neighbor = neighbors[0][0]+"\n"+neighbors[0][1]+"\n"
        neighbor_index = com_content.find(neighbor)
        if neighbors[0][0] == DELETION_IDENTIFIER_END:
            if neighbors[0][1] == DELETION_IDENTIFIER_BEGIN:
                com_content = com_content.replace(neighbor, "", 1)
            elif re.match(REPLACEMENT_IDENTIFIER_BEGIN%("\d+"), neighbors[0][1]):
                start_com_content = com_content[:neighbor_index]
                deletion_begin_index = findlast(DELETION_IDENTIFIER_BEGIN, start_com_content)
                com_content = com_content[:deletion_begin_index]+neighbors[0][1]+com_content[deletion_begin_index+len(DELETION_IDENTIFIER_BEGIN):neighbor_index]+com_content[neighbor_index+len(neighbor):]
            elif re.match(ADDITION_IDENTIFIER%("\d+"), neighbors[0][1]):
                start_com_content = com_content[:neighbor_index]
                deletion_begin_index = findlast(DELETION_IDENTIFIER_BEGIN, start_com_content)
                com_content = com_content[:deletion_begin_index]+REPLACEMENT_IDENTIFIER_BEGIN%(str(len(replacements)))+com_content[deletion_begin_index+len(DELETION_IDENTIFIER_BEGIN):].replace(neighbor, REPLACEMENT_IDENTIFIER_END+"\n")
                m = re.match(ADDITION_IDENTIFIER%("(\d+)"), neighbors[0][1])
                addition_index2 = int(m.groups()[0])
                replacements.append(additions[addition_index2])
            else:
                print("re error1")
                exit(-1)
        elif neighbors[0][0] == REPLACEMENT_IDENTIFIER_END:
            if neighbors[0][1] == DELETION_IDENTIFIER_BEGIN:
                start_com_content = com_content[:neighbor_index]
                rest_com_content = com_content[neighbor_index:]
                com_content = start_com_content+rest_com_content.replace(neighbor, "", 1).replace(DELETION_IDENTIFIER_END, REPLACEMENT_IDENTIFIER_END, 1)
            elif re.match(REPLACEMENT_IDENTIFIER_BEGIN%("\d+"), neighbors[0][1]):
                m = re.findall(REPLACEMENT_IDENTIFIER_BEGIN%("(\d+)"), com_content[:neighbor_index])
                replacement_index = int(m[len(m)-1])
                m = re.match(REPLACEMENT_IDENTIFIER_BEGIN%("(\d+)"), neighbors[0][1])
                replacement_index2 = int(m.groups()[0])
                replacements[replacement_index]+="\n"+replacements[replacement_index2]
                com_content = com_content.replace(neighbor, "", 1)
            elif re.match(ADDITION_IDENTIFIER%("\d+"), neighbors[0][1]):
                m = re.findall(REPLACEMENT_IDENTIFIER_BEGIN%("(\d+)"), com_content[:neighbor_index])
                replacement_index = int(m[len(m)-1])
                m = re.match(ADDITION_IDENTIFIER%("(\d+)"), neighbors[0][1])
                addition_index2 = int(m.groups()[0])
                replacements[replacement_index]+="\n"+additions[addition_index2]
                com_content = com_content.replace(neighbors[0][1]+"\n", "", 1)
            else:
                print("re error2")
                exit(-1)
        elif re.match(ADDITION_IDENTIFIER%("\d+"), neighbors[0][0]):
            m = re.match(ADDITION_IDENTIFIER%("(\d+)"), neighbors[0][0])
            addition_index = int(m.groups()[0])
            if neighbors[0][1] == DELETION_IDENTIFIER_BEGIN:
                start_com_content = com_content[:neighbor_index]
                rest_com_content = com_content[neighbor_index:]
                com_content = start_com_content+REPLACEMENT_IDENTIFIER_BEGIN%(str(len(replacements)))+"\n"+rest_com_content[len(neighbor):].replace(DELETION_IDENTIFIER_END, REPLACEMENT_IDENTIFIER_END,1)
                replacements.append(additions[addition_index])
            elif re.match(REPLACEMENT_IDENTIFIER_BEGIN%("\d+"), neighbors[0][1]):
                m = re.match(REPLACEMENT_IDENTIFIER_BEGIN%("(\d+)"), neighbors[0][1])
                replacement_index = int(m.groups()[0])
                com_content = com_content.replace(neighbors[0][0]+"\n", "", 1)
                replacements[replacement_index] = additions[addition_index]+"\n"+replacements[replacement_index]
            elif re.match(ADDITION_IDENTIFIER%("\d+"), neighbors[0][1]):
                m = re.match(ADDITION_IDENTIFIER%("(\d+)"), neighbors[0][1])
                addition_index2 = int(m.groups()[0])
                additions[addition_index] += "\n"+additions[addition_index2]
                com_content = com_content.replace(neighbors[0][1]+"\n", "", 1)
            else:
                print("re error3")
                exit(-1)
        else:
            print("re error4")
            exit(-1)
        neighbors = re.findall(neighbor_regex, com_content)
    return com_content

def findlast(aSubstr, aStr):
    aStrR = aStr[::-1]
    aSubstrR = aSubstr[::-1]
    index_r = aStrR.find(aSubstrR)
    if index_r == -1:
        return -1
    return len(aStr)-index_r-len(aSubstr)

def handle_equal(lines1, lines2, op, replacements, additions, inline_replacements, inline_additions):
    begin1 = op[1]
    end1 = op[2]
    begin2 = op[3]
    diff_md = ""
    for i in range(end1-begin1):
        if lines1[begin1+i].formated_line == lines2[begin2+i].formated_line:
            diff_md += lines2[begin2+i].line + "\n"
        else:
            diff_md += handle_replace_one_line(lines1[begin1+i], lines2[begin2+i], replacements, additions, inline_replacements, inline_additions)
    return diff_md

def handle_replace_one_line(line1, line2, replacements, additions, inline_replacements, inline_additions):
    if line1.stripped_line == "" and line2.stripped_line != "":
        replacements.append(line2.line)
        return REPLACEMENT_IDENTIFIER_BEGIN%(str(len(replacements)-1))+"\n"+"\n"+REPLACEMENT_IDENTIFIER_END+"\n"
    if line2.stripped_line == "" and line1.stripped_line != "":
        replacements.append("")
        return REPLACEMENT_IDENTIFIER_BEGIN%(str(len(replacements)-1))+"\n"+line1.line+"\n"+REPLACEMENT_IDENTIFIER_END+"\n"
    strip_index1 = line1.line.find(line1.stripped_line)
    empty_leading1 = line1.line[:strip_index1]
    empty_end1 = line1.line[strip_index1+len(line1.stripped_line):]
    strip_index2 = line2.line.find(line2.stripped_line)
    empty_leading2 = line2.line[:strip_index2]
    empty_end2 = line2.line[strip_index2+len(line2.stripped_line):]
    words1 = [Article_word(word) for word in re.split("[ \t\r\f\v]+", line1.stripped_line)]
    words2 = [Article_word(word) for word in re.split("[ \t\r\f\v]+", line2.stripped_line)]
    empty_spaces_list1 = re.findall("[ \t\r\f\v]+", line1.stripped_line)
    empty_spaces_list1.append("")
    empty_spaces_list2 = re.findall("[ \t\r\f\v]+", line2.stripped_line)
    empty_spaces_list2.append("")
    s = SequenceMatcher(lambda x: False, words1, words2)
    ops = s.get_opcodes()
    result = ""
    for op in ops:
        if op[0] == "equal":
            for i in range(op[3], op[4]):
                result += words2[i].word+empty_spaces_list2[i]
        elif op[0] == "replace":
            result += REPLACEMENT_IDENTIFIER_BEGIN_INLINE%(str(len(inline_replacements)))+" "
            for i in range(op[1], op[2]-1):
                result += words1[i].word+empty_spaces_list1[i]
            result += words1[op[2]-1].word+" "
            result += REPLACEMENT_IDENTIFIER_END_INLINE+empty_spaces_list2[op[4]-1]
            replacement = ""
            for i in range(op[3], op[4]-1):
                replacement += words2[i].word+empty_spaces_list2[i]
            replacement += words2[op[4]-1].word
            inline_replacements.append(replacement)
        elif op[0] == "insert":
            result += ADDITION_IDENTIFIER_INLINE%(str(len(inline_additions)))+empty_spaces_list2[op[4]-1]
            addition = ""
            for i in range(op[3], op[4]-1):
                addition += words2[i].word+empty_spaces_list2[i]
            addition += words2[op[4]-1].word
            inline_additions.append(addition)
        elif op[0] == "delete":
            if empty_spaces_list2[op[3]-1] == "" and result!="":
                result += " "
            result += DELETION_IDENTIFIER_BEGIN_INLINE+" "
            for i in range(op[1], op[2]-1):
                result += words1[i].word+empty_spaces_list1[i]
            result += words1[op[2]-1].word+" "
            result += DELETION_IDENTIFIER_END_INLINE+empty_spaces_list1[op[2]-1]
    return empty_leading2+result+empty_end2+"\n"

def handle_replace(lines1, lines2, op, replacements):
    origin = "\n".join([article_line.line for article_line in lines1[op[1]:op[2]]])
    replacement = "\n".join([article_line.line for article_line in lines2[op[3]:op[4]]])
    diff_md = REPLACEMENT_IDENTIFIER_BEGIN%(str(len(replacements)))+"\n"+origin+"\n"+REPLACEMENT_IDENTIFIER_END+"\n"
    replacements.append(replacement)
    return diff_md

def handle_insert(lines2, op, additions):
    addition = "\n".join([article_line.line for article_line in lines2[op[3]:op[4]]])
    diff_md = ADDITION_IDENTIFIER%(str(len(additions)))+"\n"
    additions.append(addition)
    return diff_md

def handle_delete(lines1, op):
    deletion = "\n".join([article_line.line for article_line in lines1[op[1]:op[2]]])
    diff_md = DELETION_IDENTIFIER_BEGIN+"\n"+deletion+"\n"+DELETION_IDENTIFIER_END+"\n"
    return diff_md

def apply_modification(mdcontent, com_md, modification):
    origin_com_lines = com_md.split("\n")
    com_lines_removed_identifier = [line for line in origin_com_lines if not re.match("("+DELETION_IDENTIFIER_BEGIN+"|"+REPLACEMENT_IDENTIFIER_BEGIN%("\d+")+"|"+ADDITION_IDENTIFIER%("\d+")+"|"+DELETION_IDENTIFIER_END+"|"+REPLACEMENT_IDENTIFIER_END+")", line)]
    new_lines, com_lines, ops = get_diff_set(mdcontent.split("\n"), com_lines_removed_identifier)
    ops = refine_ops(new_lines, com_lines, ops, origin_com_lines)
    com_lines = [Article_line(line) for line in origin_com_lines]
    md_result = ""
    i = 0
    while i< len(ops):
        if ops[i][0]=='equal':
            delta_content, delta_i= apply_equal(new_lines, com_lines, ops, modification, i)
            md_result += delta_content
            i+= delta_i
        elif ops[i][0]=='replace':
            delta_content, delta_i= apply_replace(new_lines, com_lines, ops, modification, i)
            md_result += delta_content
            i+= delta_i
        elif ops[i][0]=='insert':
            delta_content, delta_i= apply_insert(new_lines, com_lines, ops, modification, i)
            md_result += delta_content
            i+= delta_i
        elif ops[i][0]=='delete':
            delta_content, delta_i= apply_delete(new_lines, com_lines, ops, modification, i)
            md_result += delta_content
            i+= delta_i
        i+=1
    return md_result

def refine_ops(new_lines, com_lines, ops, origin_com_lines):
    op_index = 0
    identifier_count = 0
    for i in range(len(com_lines)):
        if com_lines[i].line != origin_com_lines[i+identifier_count]:
            while i+identifier_count>ops[op_index][4]:
                op_index+=1
            if ops[op_index][0]=="equal":
                ops_remained = ops[op_index+1:]
                splitting_op = ops[op_index]
                ops = ops[:op_index]
                ops.append(("equal", splitting_op[1], splitting_op[2]-(splitting_op[4]-(i+identifier_count)), splitting_op[3], i+identifier_count))
                ops.append(("insert", splitting_op[2]-(splitting_op[4]-(i+identifier_count)), splitting_op[2]-(splitting_op[4]-(i+identifier_count)), i+identifier_count, i+identifier_count+1))
                if splitting_op[4]>i+identifier_count:
                    ops.append(("equal", splitting_op[2]-(splitting_op[4]-(i+identifier_count)), splitting_op[2], i+identifier_count+1, splitting_op[4]+1))
                for op in ops_remained:
                    ops.append((op[0], op[1], op[2], op[3]+1, op[4]+1))
            elif ops[op_index][0]=="replace":
                ops_remained = ops[op_index+1:]
                splitting_op = ops[op_index]
                ops = ops[:op_index]
                if i+identifier_count==splitting_op[3]:
                    ops.append(("insert", splitting_op[1], splitting_op[1], splitting_op[3], splitting_op[3]+1))
                    ops.append(("replace", splitting_op[1], splitting_op[2], splitting_op[3]+1, splitting_op[4]+1))
                else:
                    if i+identifier_count - splitting_op[3]>splitting_op[4]-i+identifier_count:
                        ops.append(("replace", splitting_op[1], splitting_op[2], splitting_op[3], i+identifier_count))
                        ops.append(("insert", splitting_op[2], splitting_op[2], i+identifier_count, i+identifier_count+1))
                        if splitting_op[4]>i+identifier_count:
                            ops.append(("insert", splitting_op[2], splitting_op[2], i+identifier_count+1, splitting_op[4]+1))
                    else:
                        ops.append(("insert", splitting_op[1], splitting_op[1], splitting_op[3], i+identifier_count))
                        ops.append(("insert", splitting_op[1], splitting_op[1], i+identifier_count, i+identifier_count+1))
                        ops.append(("replace", splitting_op[1], splitting_op[2], i+identifier_count+1, splitting_op[4]+1))
                for op in ops_remained:
                    ops.append((op[0], op[1], op[2], op[3]+1, op[4]+1))
            elif ops[op_index][0]=="insert":
                ops_remained = ops[op_index+1:]
                splitting_op = ops[op_index]
                ops = ops[:op_index]
                if i+identifier_count>splitting_op[3]:
                    ops.append(("insert", splitting_op[1], splitting_op[2], splitting_op[3], i+identifier_count))
                ops.append(("insert", splitting_op[1], splitting_op[2], i+identifier_count, i+identifier_count+1))
                if splitting_op[4]>i+identifier_count:
                    ops.append(("insert", splitting_op[1], splitting_op[2], i+identifier_count+1, splitting_op[4]+1))
                for op in ops_remained:
                    ops.append((op[0], op[1], op[2], op[3]+1, op[4]+1))
            else:
                print("ops error")
                exit(-1)
            identifier_count+=1
    if len(com_lines)+identifier_count==len(origin_com_lines)-1:
        ops.append(("insert", ops[len(ops)-1][2], ops[len(ops)-1][2], len(com_lines)+identifier_count, len(com_lines)+identifier_count+1))
    return ops

def refine_ops_word(new_words, com_words, ops, origin_com_words):
    op_index = 0
    identifier_count = 0
    for i in range(len(com_words)):
        if com_words[i].word != origin_com_words[i+identifier_count]:
            while i+identifier_count>ops[op_index][4]:
                op_index+=1
            if ops[op_index][0]=="equal":
                ops_remained = ops[op_index+1:]
                splitting_op = ops[op_index]
                ops = ops[:op_index]
                ops.append(("equal", splitting_op[1], splitting_op[2]-(splitting_op[4]-(i+identifier_count)), splitting_op[3], i+identifier_count))
                ops.append(("insert", splitting_op[2]-(splitting_op[4]-(i+identifier_count)), splitting_op[2]-(splitting_op[4]-(i+identifier_count)), i+identifier_count, i+identifier_count+1))
                if splitting_op[4]>i+identifier_count:
                    ops.append(("equal", splitting_op[2]-(splitting_op[4]-(i+identifier_count)), splitting_op[2], i+identifier_count+1, splitting_op[4]+1))
                for op in ops_remained:
                    ops.append((op[0], op[1], op[2], op[3]+1, op[4]+1))
            elif ops[op_index][0]=="replace":
                ops_remained = ops[op_index+1:]
                splitting_op = ops[op_index]
                ops = ops[:op_index]
                if i+identifier_count==splitting_op[3]:
                    ops.append(("insert", splitting_op[1], splitting_op[1], splitting_op[3], splitting_op[3]+1))
                    ops.append(("replace", splitting_op[1], splitting_op[2], splitting_op[3]+1, splitting_op[4]+1))
                else:
                    if i+identifier_count - splitting_op[3]>splitting_op[4]-i+identifier_count:
                        ops.append(("replace", splitting_op[1], splitting_op[2], splitting_op[3], i+identifier_count))
                        ops.append(("insert", splitting_op[2], splitting_op[2], i+identifier_count, i+identifier_count+1))
                        if splitting_op[4]>i+identifier_count:
                            ops.append(("insert", splitting_op[2], splitting_op[2], i+identifier_count+1, splitting_op[4]+1))
                    else:
                        ops.append(("insert", splitting_op[1], splitting_op[1], splitting_op[3], i+identifier_count))
                        ops.append(("insert", splitting_op[1], splitting_op[1], i+identifier_count, i+identifier_count+1))
                        ops.append(("replace", splitting_op[1], splitting_op[2], i+identifier_count+1, splitting_op[4]+1))
                for op in ops_remained:
                    ops.append((op[0], op[1], op[2], op[3]+1, op[4]+1))
            elif ops[op_index][0]=="insert":
                ops_remained = ops[op_index+1:]
                splitting_op = ops[op_index]
                ops = ops[:op_index]
                if i+identifier_count>splitting_op[3]:
                    ops.append(("insert", splitting_op[1], splitting_op[2], splitting_op[3], i+identifier_count))
                ops.append(("insert", splitting_op[1], splitting_op[2], i+identifier_count, i+identifier_count+1))
                if splitting_op[4]>i+identifier_count:
                    ops.append(("insert", splitting_op[1], splitting_op[2], i+identifier_count+1, splitting_op[4]+1))
                for op in ops_remained:
                    ops.append((op[0], op[1], op[2], op[3]+1, op[4]+1))
            else:
                print("ops error")
                exit(-1)
            identifier_count+=1
    if len(com_words)+identifier_count==len(origin_com_words)-1:
        ops.append(("insert", ops[len(ops)-1][2], ops[len(ops)-1][2], len(com_words)+identifier_count, len(com_words)+identifier_count+1))
    return ops

def create_ops_insert(op1, op2, op3, op4, new_ops, indices):
    pre = op3
    for index in indices:
        if pre<index:
            new_ops.append(('insert', op1, op2, pre, index))
        new_ops.append(('insert', op1, op2, index, index+1))
        pre = index+1
    if pre<op4:
        new_ops.append(('insert', op1, op2, pre, op4))

def find_identifier(lines):
    try:
        d_b_index = lines.index(DELETION_IDENTIFIER_BEGIN)
    except ValueError:
        d_b_index = -1
    try:
        r_b_index = lines.index(REPLACEMENT_IDENTIFIER_BEGIN)
    except ValueError:
        r_b_index = -1
    try:
        a_index = lines.index(ADDITION_IDENTIFIER)
    except ValueError:
        a_index = -1
    try:
        d_e_index = lines.index(DELETION_IDENTIFIER_END)
    except ValueError:
        d_e_index = -1
    try:
        r_e_index = lines.index(REPLACEMENT_IDENTIFIER_END)
    except ValueError:
        r_e_index = -1
    return [d_b_index, r_b_index, a_index, d_e_index, r_e_index]

def apply_equal(new_lines, com_lines, ops, modification, i):
    delta_content = ""
    for j in range(ops[i][4]-ops[i][3]):
        if new_lines[j+ops[i][1]].formated_line == com_lines[j+ops[i][3]].formated_line:
            delta_content+=com_lines[j+ops[i][3]].line+"\n"
        else:
            delta_content+=apply_one_line(new_lines[j+ops[i][1]], com_lines[j+ops[i][3]], modification)+"\n"
    delta_i = 0
    return delta_content, delta_i

def apply_one_line(new_line, com_line, modification):
    origin_com_words = [word for word in re.split("[ \t\r\f\v]+", com_line.stripped_line)]
    com_white_spaces = re.findall("[ \t\r\f\v]+", com_line.stripped_line)
    com_white_spaces.append("")
    com_leading_white_spaces = com_line.line[:com_line.line.find(com_line.stripped_line)]
    new_leading_white_spaces = new_line.line[:new_line.line.find(new_line.stripped_line)]
    ending_white_spaces = new_line.line[new_line.line.find(new_line.stripped_line)+len(new_line.stripped_line):]
    com_words_removed_identifier = [word for word in origin_com_words if not re.match("("+DELETION_IDENTIFIER_BEGIN_INLINE+"|"+REPLACEMENT_IDENTIFIER_BEGIN_INLINE%("\d+")+"|"+ADDITION_IDENTIFIER_INLINE%("\d+")+"|"+DELETION_IDENTIFIER_END_INLINE+"|"+REPLACEMENT_IDENTIFIER_END_INLINE+")", word)]
    new_words, com_words, ops = get_diff_set_word([word for word in re.split("[ \t\r\f\v]+", new_line.stripped_line)], com_words_removed_identifier)
    new_white_spaces = re.findall("[ \t\r\f\v]+", new_line.stripped_line)
    new_white_spaces.append("")
    ops = refine_ops_word(new_words, com_words, ops, origin_com_words)
    com_words = [Article_word(word) for word in origin_com_words]
    md_result = ""
    i = 0
    while i< len(ops):
        if ops[i][0]=='equal':
            delta_content, delta_i= apply_equal_word(new_words, com_words, ops, com_white_spaces, modification, i)
            
            md_result += delta_content
            i+= delta_i
        elif ops[i][0]=='replace':
            delta_content, delta_i= apply_replace_word(new_words, com_words, ops, new_white_spaces, modification, i)
            
            md_result += delta_content
            i+= delta_i
        elif ops[i][0]=='insert':
            delta_content, delta_i= apply_insert_word(new_words, com_words, ops, com_white_spaces, new_white_spaces, modification, i)
            md_result += delta_content
            i+= delta_i
        elif ops[i][0]=='delete':
            delta_content, delta_i= apply_delete_word(new_words, com_words, ops, new_white_spaces, modification, i, md_result=="")
            md_result += delta_content
            i+= delta_i
        i+=1
    if md_result.strip()=="":
        return ""
    else:
        return com_leading_white_spaces+md_result.strip()+ending_white_spaces

def apply_equal_word(new_words, com_words, ops, white_spaces, modification, i):
    delta_content = ""
    for j in range(ops[i][3],ops[i][4]):
        delta_content += com_words[j].word+white_spaces[j]
    delta_i = 0
    return delta_content, delta_i

def apply_replace_word(new_words, com_words, ops, white_spaces, modification, i):
    delta_content = ""
    for j in range(ops[i][1],ops[i][2]):
        delta_content += new_words[j].word+white_spaces[j]
    delta_i = 0
    return delta_content, delta_i

def apply_insert_word(new_words, com_words, ops, com_white_spaces, new_white_spaces, modification, i):
    (additions, replacements, inline_replacements, inline_additions) = modification
    delta_i = 0
    delta_content = ""
    if ops[i][4]-ops[i][3] == 1:
        if com_words[ops[i][3]].word == DELETION_IDENTIFIER_BEGIN_INLINE:
            if i+2<len(ops) and ops[i+1][0] == "equal" and ops[i+2][0] == "insert" and com_words[ops[i+2][3]].word == DELETION_IDENTIFIER_END_INLINE:
                delta_content = ""
                delta_i = 2
            else:
                delta_content, delta_i = abort_modification_word(new_words, com_words, ops, new_white_spaces, i, DELETION_IDENTIFIER_END_INLINE)
        elif re.match(ADDITION_IDENTIFIER_INLINE%("\d+"), com_words[ops[i][3]].word):
            addition_index = int(re.match(ADDITION_IDENTIFIER_INLINE%("(\d+)"), com_words[ops[i][3]].word).groups()[0])
            delta_content = inline_additions[addition_index]+com_white_spaces[ops[i][3]]
        elif re.match(REPLACEMENT_IDENTIFIER_BEGIN_INLINE%("\d+"), com_words[ops[i][3]].word):
            if i+2<len(ops) and ops[i+1][0] == "equal" and ops[i+2][0] == "insert" and com_words[ops[i+2][3]].word == REPLACEMENT_IDENTIFIER_END_INLINE:
                replacement_index = int(re.match(REPLACEMENT_IDENTIFIER_BEGIN_INLINE%("(\d+)"), com_words[ops[i][3]].word).groups()[0])
                delta_content = inline_replacements[replacement_index]+com_white_spaces[ops[i+2][3]]
                delta_i = 2
            else:
                delta_content, delta_i = abort_modification_word(new_words, com_words, ops, new_white_spaces, i, REPLACEMENT_IDENTIFIER_END_INLINE)
    return delta_content, delta_i

def apply_delete_word(new_words, com_words, ops, white_spaces, modification, i, result_is_empty):
    delta_content = ""
    for j in range(ops[i][1],ops[i][2]):
        delta_content += new_words[j].word+white_spaces[j]
    delta_i = 0
    if not result_is_empty:
        if ops[i][1]-1>0:
            delta_content = white_spaces[ops[i][1]-1]+delta_content
        else:
            delta_content = " "+delta_content
    return delta_content, delta_i

def abort_modification_word(new_words, com_words, ops, white_spaces, i, IDENTIFIER_END):
    delta_i = 1
    delta_content = ""
    delta_i = 0
    while com_words[ops[i+delta_i][3]].word != IDENTIFIER_END:
        if ops[i+delta_i][0] in ["equal", "replace", "delete"]:
            for j in range(ops[i+delta_i][1],ops[i+delta_i][2]):
                delta_content += new_words[j].word+white_spaces[j]
        delta_i+=1
    return delta_content, delta_i

def apply_replace(new_lines, com_lines, ops, modification, i):
    delta_content = "\n".join([article_line.line for article_line in new_lines[ops[i][1]:ops[i][2]]])+"\n"
    delta_i = 0
    return delta_content, delta_i

def apply_insert(new_lines, com_lines, ops, modification, i):
    (additions, replacements, inline_replacements, inline_additions) = modification
    delta_i = 0
    delta_content = ""
    if ops[i][4]-ops[i][3] == 1:
        if com_lines[ops[i][3]].line == DELETION_IDENTIFIER_BEGIN:
            if i+2<len(ops) and ops[i+1][0] == "equal" and ops[i+2][0] == "insert" and com_lines[ops[i+2][3]].line == DELETION_IDENTIFIER_END:
                delta_content = ""
                delta_i = 2
            else:
                delta_content, delta_i = abort_modification(new_lines, com_lines, ops, i, DELETION_IDENTIFIER_END)
        elif re.match(ADDITION_IDENTIFIER%("\d+"), com_lines[ops[i][3]].line):
            addition_index = int(re.match(ADDITION_IDENTIFIER%("(\d+)"), com_lines[ops[i][3]].line).groups()[0])
            delta_content = additions[addition_index]+"\n"
        elif re.match(REPLACEMENT_IDENTIFIER_BEGIN%("\d+"), com_lines[ops[i][3]].line):
            if i+2<len(ops) and ops[i+1][0] == "equal" and ops[i+2][0] == "insert" and com_lines[ops[i+2][3]].line == REPLACEMENT_IDENTIFIER_END:
                replacement_index = int(re.match(REPLACEMENT_IDENTIFIER_BEGIN%("(\d+)"), com_lines[ops[i][3]].line).groups()[0])
                delta_content = replacements[replacement_index]+"\n"
                delta_i = 2
            else:
                delta_content, delta_i = abort_modification(new_lines, com_lines, ops, i, REPLACEMENT_IDENTIFIER_END)
    return delta_content, delta_i

def apply_delete(new_lines, com_lines, ops, modification, i):
    (additions, replacements, inline_replacements, inline_additions) = modification
    delta_i = 0
    delta_content = "\n".join([article_line.line for article_line in new_lines[ops[i][1]:ops[i][2]]])+"\n"
    return delta_content, delta_i

def abort_modification(new_lines, com_lines, ops, i, IDENTIFIER_END):
    delta_i = 1
    delta_content = ""
    while com_lines[ops[i+delta_i][3]].line != IDENTIFIER_END:
        if ops[i+delta_i][0] in ["equal", "replace", "delete"]:
            delta_content += "\n".join([article_line.line for article_line in new_lines[ops[i+delta_i][1]:ops[i+delta_i][2]]])+"\n"
        delta_i+=1
    return delta_content, delta_i