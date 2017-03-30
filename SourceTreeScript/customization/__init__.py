import re
import json
import collections
import os
import git
from difflib import Differ
from .listAndCode import refineNestedListContent

CONSTANT_RULE_FILE = "rules/constant.json"
SEMI_RULE_FILE = "rules/semiconstant.json"
REGEX_RULE_FILES = "rules/regular_level"
CORRECTION_RULE_FILE = "rules/correction.json"

DELETION_MARKER = "{{deletion}}"
ADDITION_MARKER = "{{addition}}"
REPLACEMENT_MARKER_ONELINE = "{{replacement_oneline}}"

TRANSIT_THRESHOLD_S = 2
TRANSIT_THRESHOLD_L = 5

MATCHING_THRESHOLD_S = 0.5
MATCHING_THRESHOLD_M = 0.7
MATCHING_THRESHOLD_L = 0.8

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


constant = None
regex_list = None
semi = None
correction = None
regex = None

g = None

def customize(filepath, script_path, prefix=""):
    getRule(script_path, prefix)
    file = open(filepath, "r", encoding="utf8")
    mdcontent = file.read()
    file.close()
    mdcontent = customize_mdcontent(mdcontent)
    file = open(filepath, "w", encoding="utf8")
    file.write(mdcontent)
    file.close()

def customize_compare(filepath, script_path, repopath=".", mooncakepath="E:\GitHub\azure-content-mooncake-pr", prefix=""):
    getRule(script_path, prefix)
    file = open(filepath, "r", encoding="utf8")
    mdcontent = file.read().replace("\ufeff", "")
    file.close()
    mdcontent = customize_mdcontent(mdcontent)
    mdcontent = mdcontent.replace("\r", "").strip()
    relative_path = filepath[len(repopath)+1:].replace("\\","/")
    mooncake_file_path = mooncakepath+"/"+relative_path
    if os.path.isfile(mooncake_file_path):
        try:
            lastmonth_md = getlastmonthmd(relative_path, repopath).replace("\r", "")
        except git.exc.GitCommandError:
            "do nothing"
        else:
            file = open(mooncake_file_path, "r", encoding="utf8")
            mc_md = file.read().replace("\ufeff", "").replace("\r", "").strip()
            file.close()
            differ = Differ()
            lastmonth_lines = lastmonth_md.split("\n")
            md_lines = mc_md.split("\n")
            lastmonth_empty_leadings, lastmonth_lines = split_empty_leadings(lastmonth_lines)
            mc_empty_leadings, mc_lines = split_empty_leadings(md_lines)
            result = list(differ.compare(lastmonth_lines, mc_lines))
            result = add_back_empty_leadings(result, lastmonth_empty_leadings, mc_empty_leadings)
            #print("\n".join(result))
            diff_set = compare_result_split2(result)
            #print("\n".join([str(x) for x in diff_set]))
            com_md, modification = construct_com_md("\n".join(result), diff_set)
            #print("\n".join([str(x) for x in modification]))
            com_md = re.sub("(^|\n)  ", r"\1", com_md)
            mdcontent = apply_modification(mdcontent, com_md, modification)
            #mdcontent = com_md
    file = open(filepath, "w", encoding="utf8")
    file.write(mdcontent)
    file.close()

def split_empty_leadings(lines):
    empty_leadings = []
    content_lines = []
    for line in lines:
        line_stripped = line.strip()
        index = line.find(line_stripped)
        empty_leadings.append(line[:index])
        content_lines.append(line[index:])
    return empty_leadings, content_lines

def add_back_empty_leadings(compare_result, removed_empty_leadings, added_empty_leadings):
    removed_count = 0
    added_count = 0
    for i in range(len(compare_result)):
        if compare_result[i][0]==" ":
            compare_result[i] = compare_result[i][:2]+added_empty_leadings[added_count]+compare_result[i][2:]
            removed_count += 1
            added_count += 1
        elif compare_result[i][0]=="+":
            compare_result[i] = compare_result[i][:2]+added_empty_leadings[added_count]+compare_result[i][2:]
            added_count += 1
        elif compare_result[i][0]=="-":
            compare_result[i] = compare_result[i][:2]+removed_empty_leadings[removed_count]+compare_result[i][2:]
            removed_count += 1
    return compare_result

def construct_com_md(diff_md, diff_set):
    additions = []
    replacements = []
    inline_replacements = []
    inline_additions = []
    for diff in diff_set:
        l = len(diff)
        origin = "\n".join(diff[:l-1])
        if diff[l-1] == DELETION_MARKER:
            replacement = DELETION_IDENTIFIER_BEGIN+"\n"+"\n".join(["  "+x[2:] for x in diff[:l-1]])+"\n"+DELETION_IDENTIFIER_END
        elif diff[l-1] == ADDITION_MARKER:
            replacement = ADDITION_IDENTIFIER%(str(len(additions)))
            added_lines = re.sub("(^|\n)\+ ", r"\1", origin)
            added_lines = re.sub("\n\? .+\n", "", added_lines)
            additions.append(added_lines)
        elif diff[l-1] == REPLACEMENT_MARKER_ONELINE:
            for line in diff:
                if line[0] == "-":
                    removed = line[2:]
                elif line[0] == "+":
                    added = line[2:]
            replacement = handle_one_line_replacemnt(removed, added, inline_replacements, inline_additions)
        replacement = replacement.replace("\\", "\\\\")
        diff_md = re.sub("(^|\n)"+re.escape(origin)+"(\n|$)", "\\1"+replacement+"\\2", diff_md, 1)
    m = re.findall("("+ADDITION_IDENTIFIER%("(\d+)")+"\n"+DELETION_IDENTIFIER_BEGIN+"\n)",diff_md)
    for i in m:
        index = diff_md.find(i[0])
        diff_md = diff_md[:index]+diff_md[index:].replace(i[0],REPLACEMENT_IDENTIFIER_BEGIN%(str(len(replacements)))+"\n",1).replace(DELETION_IDENTIFIER_END,REPLACEMENT_IDENTIFIER_END,1)
        replacements.append(additions[int(i[1])])
    m = re.findall("("+DELETION_IDENTIFIER_END+"\n"+ADDITION_IDENTIFIER%("(\d+)")+"(\n|$))",diff_md)
    for i in m:
        index = diff_md.find(i[0])
        diff_md = diff_md[:index][::-1].replace("\n"+DELETION_IDENTIFIER_BEGIN[::-1], (REPLACEMENT_IDENTIFIER_BEGIN%(str(len(replacements)))+"\n")[::-1], 1)[::-1]+diff_md[index:].replace(i[0],REPLACEMENT_IDENTIFIER_END+i[2],1)
        replacements.append(additions[int(i[1])])
    return diff_md, (additions, replacements, inline_replacements, inline_additions)

def handle_one_line_replacemnt(removed, added, inline_replacements, inline_additions):
    removed_stripped = removed.strip()
    added_stripped = added.strip()
    index = added.find(added_stripped)
    added_leading_spaces = added[:index]
    added_ending_spaces = added[index+len(added_stripped):]
    removed_sentences_raw = re.split("([\.\!\?]\s+)", removed_stripped)
    added_sentences_raw = re.split("([\.\!\?]\s+)", added_stripped)
    removed_sentences = []
    added_sentences = []
    ending_spaces_for_sentences = []
    for i in range(int((len(removed_sentences_raw)-1)/2)):
        ending_spaces_for_sentences.append(removed_sentences_raw[2*i+1][1:])
        removed_sentences.append(removed_sentences_raw[2*i]+removed_sentences_raw[2*i+1][0])
    removed_sentences.append(removed_sentences_raw[len(removed_sentences_raw)-1])
    for i in range(int((len(added_sentences_raw)-1)/2)):
        added_sentences.append(added_sentences_raw[2*i]+added_sentences_raw[2*i+1][0])
    added_sentences.append(added_sentences_raw[len(added_sentences_raw)-1])
    if len(removed_sentences) == 1 and len(added_sentences) == 1:
        replacement= handle_one_sentence_replacemnt(removed_stripped, added_stripped, inline_replacements)
        return "  "+added_leading_spaces+replacement[:len(replacement)-1]+added_ending_spaces
    differ = Differ()
    result = list(differ.compare(removed_sentences, added_sentences))
    diff_set = compare_result_split2(result)
    com_md, modification = construct_com_md("\n".join(result), diff_set)
    #print(com_md)
    for i in range(len(modification[2])):
        com_md = com_md[::-1].replace((REPLACEMENT_IDENTIFIER_BEGIN_INLINE%(str(i)))[::-1], (REPLACEMENT_IDENTIFIER_BEGIN_INLINE%(str(len(inline_replacements))))[::-1], 1)[::-1]
        inline_replacements.append(modification[2][i])
    for i in range(len(modification[1])):
        com_md = re.sub("(^|\n)"+re.escape(REPLACEMENT_IDENTIFIER_BEGIN%(str(i)))+"(\n  |$)", "\\1  "+REPLACEMENT_IDENTIFIER_BEGIN_INLINE%(str(len(inline_replacements))), com_md)
        replacement_sentences = modification[1][i].split("\n")
        if len(replacement_sentences)>1:
            regex = "\s*".join([re.escape(x) for x in replacement_sentences])
            m = re.findall(regex,added)
            if len(m)>0:
                inline_replacements.append(m[0])
        else:
            inline_replacements.append(modification[1][i])
    for i in range(len(modification[0])):
        all_adds = re.findall("((^|\n)"+re.escape(ADDITION_IDENTIFIER%(str(i)))+"(\n  |$))", com_md)
        if len(all_adds)>0:
            if all_adds[0][1] == "\n":
                add_lead = " "
            else:
                add_lead = ""
            com_md = com_md.replace(all_adds[0][0],add_lead+ADDITION_IDENTIFIER_INLINE%(str(len(inline_additions)))+all_adds[0][2])
            addition_sentences = modification[0][i].split("\n")
            if len(addition_sentences)>1:
                regex = "\s*".join([re.escape(x) for x in addition_sentences])
                m = re.findall(regex,added)
                if len(m)>0:
                    inline_additions.append(m[0])
            else:
                inline_additions.append(modification[0][i])
    com_md = com_md.replace("\n"+REPLACEMENT_IDENTIFIER_END, REPLACEMENT_IDENTIFIER_END_INLINE)
    com_md = com_md.replace(""+DELETION_IDENTIFIER_BEGIN+"\n  ", "  "+DELETION_IDENTIFIER_BEGIN_INLINE)
    com_md = com_md.replace("\n"+DELETION_IDENTIFIER_END, DELETION_IDENTIFIER_END_INLINE)
    if re.match("^"+ADDITION_IDENTIFIER_INLINE%("\d+")+"\n.+",com_md):
        temp = [" "]
        temp.extend(ending_spaces_for_sentences)
        ending_spaces_for_sentences = temp
    if re.match(".+"+ADDITION_IDENTIFIER_INLINE%("\d+")+"\s*$",com_md):
        ending_spaces_for_sentences.append(" ")
    for s in ending_spaces_for_sentences:
        com_md = com_md.replace("\n  ", s, 1)
    com_md = com_md.replace("\n  ", " ", 1)
    return "  "+added_leading_spaces+com_md.strip()+added_ending_spaces

def handle_one_sentence_replacemnt(removed, added, inlines):
    removed_words = removed.split(" ")
    added_words = added.split(" ")
    differ = Differ()
    differ_list = list(differ.compare(removed_words, added_words))
    same_count = 0
    delete_count = 0
    add_count = 0
    for word in differ_list:
        if word[0]==" " and word.strip()!=0:
            same_count+=1
        elif word[0]=="-":
            delete_count+=1
        elif word[0]=="+":
            add_count+=1
    if delete_count+add_count!=0 and same_count/(delete_count+add_count)<0.2:
        removed_strip = removed.strip()
        index = removed.find(removed_strip)
        result = removed[:index]+REPLACEMENT_IDENTIFIER_BEGIN_INLINE%(str(len(inlines)))+removed_strip+REPLACEMENT_IDENTIFIER_END_INLINE+removed[index+len(removed_strip):]+" "
        inlines.append(added)
        return result
    result = ""
    for word in differ_list:
        if word[0]==" ":
            result+= word[2:]+" "
        elif word[0]=="-":
            result+= DELETION_IDENTIFIER_BEGIN_INLINE+word[2:]+DELETION_IDENTIFIER_END_INLINE+" "
        elif word[0]=="+":
            result+= ADDITION_IDENTIFIER_BEGIN_INLINE+word[2:]+ADDITION_IDENTIFIER_END_INLINE+" "
    result = result.replace(DELETION_IDENTIFIER_END_INLINE+" "+DELETION_IDENTIFIER_BEGIN_INLINE, " ")
    result = result.replace(ADDITION_IDENTIFIER_END_INLINE+" "+ADDITION_IDENTIFIER_BEGIN_INLINE, " ")
    index = result.find(DELETION_IDENTIFIER_END_INLINE+" "+ADDITION_IDENTIFIER_BEGIN_INLINE)
    while index!=-1:
        part1 = result[:index]
        part2 = result[index:]
        part1 = part1[::-1].replace(DELETION_IDENTIFIER_BEGIN_INLINE[::-1],(REPLACEMENT_IDENTIFIER_BEGIN_INLINE%(str(len(inlines))))[::-1], 1)[::-1]
        index2 = part2.find(ADDITION_IDENTIFIER_END_INLINE)
        inlines.append(part2[len(DELETION_IDENTIFIER_END_INLINE+" "+ADDITION_IDENTIFIER_BEGIN_INLINE):index2])
        part2 = REPLACEMENT_IDENTIFIER_END_INLINE + part2[index2+len(ADDITION_IDENTIFIER_END_INLINE):]
        result = part1+part2
        index = result.find(DELETION_IDENTIFIER_END_INLINE+" "+ADDITION_IDENTIFIER_BEGIN_INLINE)
    index = result.find(ADDITION_IDENTIFIER_END_INLINE+" "+DELETION_IDENTIFIER_BEGIN_INLINE)
    while index!=-1:
        part1 = result[:index]
        part2 = result[index:]
        index2 = part1.rfind(ADDITION_IDENTIFIER_BEGIN_INLINE)
        replacement = part1[index2+len(ADDITION_IDENTIFIER_BEGIN_INLINE):]
        part1 = part1[:index2]+REPLACEMENT_IDENTIFIER_BEGIN_INLINE%(str(len(inlines)))
        inlines.append(replacement)
        part2 = part2[len(ADDITION_IDENTIFIER_END_INLINE+" "+DELETION_IDENTIFIER_BEGIN_INLINE):].replace(DELETION_IDENTIFIER_END_INLINE, REPLACEMENT_IDENTIFIER_END_INLINE, 1)
        result = part1+part2
        index = result.find(ADDITION_IDENTIFIER_END_INLINE+" "+DELETION_IDENTIFIER_BEGIN_INLINE)
    index = result.find(REPLACEMENT_IDENTIFIER_END_INLINE+" "+ADDITION_IDENTIFIER_BEGIN_INLINE)
    while index!=-1:
        part1 = result[:index]+REPLACEMENT_IDENTIFIER_END_INLINE
        part2 = result[index:]
        m = re.findall(REPLACEMENT_IDENTIFIER_BEGIN_INLINE%("(\d+)"), part1)
        replacement_index = int(m[len(m)-1])
        index2 = part2.find(ADDITION_IDENTIFIER_END_INLINE)
        inlines[replacement_index] += " " + part2[len(REPLACEMENT_IDENTIFIER_END_INLINE+" "+ADDITION_IDENTIFIER_BEGIN_INLINE):index2]
        part2 = part2[index2+len(ADDITION_IDENTIFIER_END_INLINE):]
        result = part1+part2
        index = result.find(ADDITION_IDENTIFIER_END_INLINE+" "+ADDITION_IDENTIFIER_BEGIN_INLINE)
    m = re.findall("("+ADDITION_IDENTIFIER_END_INLINE+" "+(REPLACEMENT_IDENTIFIER_BEGIN_INLINE%("(\d+)")+")"), result)
    for ma in m:
        index = result.find(ma[0])
        part1 = result[:index]
        part2 = result[index+len(ADDITION_IDENTIFIER_END_INLINE)+1:]
        index2 = part1.rfind(ADDITION_IDENTIFIER_BEGIN_INLINE)
        replacement_index = int(ma[1])
        inlines[replacement_index] = part1[index2+len(ADDITION_IDENTIFIER_BEGIN_INLINE):] + " " + inlines[replacement_index]
        part1 = part1[:index2]
        result = part1+part2
    index = result.find(ADDITION_IDENTIFIER_BEGIN_INLINE)
    while index!=-1:
        part1 = result[:index]
        part2 = result[index:]
        part1_stripped = part1.strip()
        if part1_stripped=="":
            part1 = part1 + REPLACEMENT_IDENTIFIER_BEGIN_INLINE%(str(len(inlines)))
            replacement=""
        else:
            index2 = part1_stripped.rfind(" ")
            if index2 == -1:
                pre_word = part1_stripped
            else:
                pre_word = part1_stripped[index2+1:]
            index2 = part1.rfind(pre_word)
            replacement = part1[index2:]
            part1 = part1[:index2] + REPLACEMENT_IDENTIFIER_BEGIN_INLINE%(str(len(inlines)))+part1[index2:]
        index2 = part2.find(ADDITION_IDENTIFIER_END_INLINE)
        replacement += part2[len(ADDITION_IDENTIFIER_BEGIN_INLINE):index2]
        part2 = part2[index2+len(ADDITION_IDENTIFIER_END_INLINE)+1:]
        part2_stripped = part2.strip()
        if part2_stripped=="":
            part2 = REPLACEMENT_IDENTIFIER_END_INLINE + part2
        else:
            index2 = part2_stripped.find(" ")
            if index2 == -1:
                next_word = part2_stripped
            else:
                next_word = part2_stripped[:index2]
            index2 = part2.find(next_word)
            part2 = part2[:index2] + next_word + REPLACEMENT_IDENTIFIER_END_INLINE+part2[index2+len(next_word):]
            replacement += " "+part2[:index2] + next_word
        result = part1+part2
        index = result.find(ADDITION_IDENTIFIER_BEGIN_INLINE)
        inlines.append(replacement)
    index = result.find(REPLACEMENT_IDENTIFIER_END_INLINE+" "+DELETION_IDENTIFIER_BEGIN_INLINE)
    while index!=-1:
        part1 = result[:index]
        part2 = result[index:]
        part2 = part2.replace(REPLACEMENT_IDENTIFIER_END_INLINE+" "+DELETION_IDENTIFIER_BEGIN_INLINE, " ", 1)
        part2 = part2.replace(DELETION_IDENTIFIER_END_INLINE, REPLACEMENT_IDENTIFIER_END_INLINE, 1)
        result = part1+part2
        index = result.find(REPLACEMENT_IDENTIFIER_END_INLINE+" "+DELETION_IDENTIFIER_BEGIN_INLINE)
    m = re.findall("("+DELETION_IDENTIFIER_END_INLINE+" ("+(REPLACEMENT_IDENTIFIER_BEGIN_INLINE%("\d+")+"))"), result)
    for ma in m:
        index = result.find(ma[0])
        part1 = result[:index]
        part2 = result[index:]
        part1 = part1[::-1].replace(DELETION_IDENTIFIER_BEGIN_INLINE[::-1], ma[1][::-1], 1)[::-1]
        part2 = part2.replace(ma[0], " ", 1)
        result = part1+part2
    return result[:len(result)]

def apply_modification(mdcontent, com_md, modification):
    new_lines = mdcontent.split("\n")
    com_lines = com_md.split("\n")
    new_empty_leadings, new_stripped_lines = split_empty_leadings(new_lines)
    com_empty_leadings, com_stripped_lines = split_empty_leadings(com_lines)
    differ = Differ()
    result = list(differ.compare(new_stripped_lines,com_stripped_lines))
    result = add_back_empty_leadings(result, new_empty_leadings, com_empty_leadings)
    md_result = get_final_result(result, modification)
    return md_result

def get_final_result(result, modification):
    i = 0
    final_result = []
    while i<len(result):
        if result[i][0]==" " or result[i][0]=="-":
            final_result.append(result[i][2:])
        elif result[i][0]=="+":
            if result[i][2:]==DELETION_IDENTIFIER_BEGIN:
                deletion_lines = []
                i+=1
                while i<len(result):
                    if result[i][2:]!=DELETION_IDENTIFIER_END:
                        deletion_lines.append(result[i])
                    else:
                        break
                    i+=1
                should_be_deleted, new_content = check_if_should_be_modified(deletion_lines)
                if should_be_deleted:
                    final_result.extend(new_content[0])
                    final_result.extend(new_content[1])
                else:
                    final_result.extend(new_content)
            else:
                m = re.match("\+ "+REPLACEMENT_IDENTIFIER_BEGIN%("(\d+)"), result[i])
                if m:
                    index = int(m.groups()[0])
                    replacement_lines = []
                    i+=1
                    while i<len(result):
                        if result[i][2:]!=REPLACEMENT_IDENTIFIER_END:
                            replacement_lines.append(result[i])
                        else:
                            break
                        i+=1
                    should_be_replaced, new_content = check_if_should_be_modified(replacement_lines)
                    if should_be_replaced:
                        final_result.extend(new_content[0])
                        final_result.extend(modification[1][index].split("\n"))
                        final_result.extend(new_content[1])
                    else:
                        final_result.extend(new_content)
                else:
                    m = re.match("\+ "+ADDITION_IDENTIFIER%("(\d+)"), result[i])
                    if m:
                        index = int(m.groups()[0])
                        final_result.extend(modification[0][index].split("\n"))
                    elif check_inline_modification(result[i]):
                        if i>=1:
                            if result[i-1][0]=="?" and result[i-2][0] =="-":
                                final_result[len(final_result)-1] = get_inline_result(result[i-2][2:], result[i][2:], modification[2], modification[3])
                                
                            elif result[i-1][0]=="-":
                                final_result[len(final_result)-1] = get_inline_result(result[i-1][2:], result[i][2:], modification[2], modification[3])
                                
                            elif i+1<len(result) and result[i+1][0]=="-":
                                final_result.append(get_inline_result(result[i+1][2:], result[i][2:], modification[2], modification[3]))
                                i+=1
                        elif i+1<len(result) and result[i+1][0]=="-":
                            final_result.append(get_inline_result(result[i+1][2:], result[i][2:], modification[2], modification[3]))
                            i+=1
        i+=1
    return "\n".join(final_result)

def get_inline_result(new_line, modified_line, replacements, additions):
    new_stripped = new_line.strip()
    modified_stripped = modified_line.strip()
    index = modified_line.find(modified_stripped)
    modified_leading_spaces = modified_line[:index]
    modified_ending_spaces = modified_line[index+len(modified_stripped):]
    new_sentences_raw = re.split("([\.\!\?]\s+)", new_stripped)
    modified_sentences_raw = re.split("([\.\!\?]["+DELETION_IDENTIFIER_END_INLINE+REPLACEMENT_IDENTIFIER_END_INLINE+"]?\s+|"+ADDITION_IDENTIFIER_INLINE%("\d+")+"\s+)", modified_stripped)
    new_sentences = []
    modified_sentences = []
    ending_spaces_for_sentences = []
    for i in range(int((len(new_sentences_raw)-1)/2)):
        ending_spaces_for_sentences.append(new_sentences_raw[2*i+1][1:])
        new_sentences.append(new_sentences_raw[2*i]+new_sentences_raw[2*i+1][0])
    new_sentences.append(new_sentences_raw[len(new_sentences_raw)-1])
    for i in range(int((len(modified_sentences_raw)-1)/2)):
        modified_sentences.append(modified_sentences_raw[2*i]+modified_sentences_raw[2*i+1].strip())
    modified_sentences.append(modified_sentences_raw[len(modified_sentences_raw)-1])
    if len(new_sentences) == 1 and len(modified_sentences) == 1:
        result = get_result_for_one_sentence(new_stripped, modified_stripped, replacements, additions)
        return modified_leading_spaces+result.strip()+modified_ending_spaces
    modified_sentences = refine_modified_sentences(modified_sentences)
    differ = Differ()
    result = list(differ.compare(new_sentences, modified_sentences))
    result = get_result_for_one_line(result, replacements, additions, ending_spaces_for_sentences)
    return modified_leading_spaces+result.strip()+modified_ending_spaces

def refine_modified_sentences(modified_sentences):
    result = []
    for sentence in modified_sentences:
        if sentence[:len(DELETION_IDENTIFIER_BEGIN_INLINE)] == DELETION_IDENTIFIER_BEGIN_INLINE:
            remain_sentence = sentence[len(DELETION_IDENTIFIER_BEGIN_INLINE):]
            if DELETION_IDENTIFIER_END_INLINE not in remain_sentence:
                result.append(DELETION_IDENTIFIER_BEGIN_INLINE)
                result.append(remain_sentence)
            else:
                if remain_sentence[len(remain_sentence)-len(DELETION_IDENTIFIER_END_INLINE):] == DELETION_IDENTIFIER_END_INLINE:
                    remain_sentence = remain_sentence[:len(remain_sentence)-len(DELETION_IDENTIFIER_END_INLINE)]
                    if DELETION_IDENTIFIER_END_INLINE not in remain_sentence and REPLACEMENT_IDENTIFIER_END_INLINE not in remain_sentence:
                        result.append(DELETION_IDENTIFIER_BEGIN_INLINE)
                        result.append(remain_sentence)
                        result.append(DELETION_IDENTIFIER_END_INLINE)
                else:
                    result.append(sentence)
        elif re.match("^"+REPLACEMENT_IDENTIFIER_BEGIN_INLINE%("\d+")+".+", sentence):
            m = re.match("^("+REPLACEMENT_IDENTIFIER_BEGIN_INLINE%("\d+")+")(.+)", sentence)
            ma = m.groups()
            leading_replace = ma[0]
            remain_sentence = ma[1]
            if REPLACEMENT_IDENTIFIER_END_INLINE not in remain_sentence:
                result.append(leading_replace)
                result.append(remain_sentence)
            else:
                if remain_sentence[len(remain_sentence)-len(REPLACEMENT_IDENTIFIER_END_INLINE):] == REPLACEMENT_IDENTIFIER_END_INLINE and REPLACEMENT_IDENTIFIER_END_INLINE not in remain_sentence[:len(remain_sentence)-len(REPLACEMENT_IDENTIFIER_END_INLINE)]:
                    remain_sentence = remain_sentence[:len(remain_sentence)-len(REPLACEMENT_IDENTIFIER_END_INLINE)]
                    if DELETION_IDENTIFIER_END_INLINE not in remain_sentence and REPLACEMENT_IDENTIFIER_END_INLINE not in remain_sentence:
                        result.append(leading_replace)
                        result.append(remain_sentence)
                        result.append(REPLACEMENT_IDENTIFIER_END_INLINE)
                else:
                    result.append(sentence)
        elif sentence[len(sentence)-len(DELETION_IDENTIFIER_END_INLINE):] == DELETION_IDENTIFIER_END_INLINE:
            remain_sentence = sentence[:len(sentence)-len(DELETION_IDENTIFIER_END_INLINE)]
            if DELETION_IDENTIFIER_BEGIN_INLINE not in remain_sentence:
                result.append(remain_sentence)
                result.append(DELETION_IDENTIFIER_END_INLINE)
            else:
                result.append(sentence)
        elif sentence[len(sentence)-len(REPLACEMENT_IDENTIFIER_END_INLINE):] == REPLACEMENT_IDENTIFIER_END_INLINE:
            remain_sentence = sentence[:len(sentence)-len(REPLACEMENT_IDENTIFIER_END_INLINE)]
            if re.match(".*"+REPLACEMENT_IDENTIFIER_BEGIN_INLINE%("\d+")+".*", remain_sentence):
                result.append(sentence)
            else:
                result.append(remain_sentence)
                result.append(REPLACEMENT_IDENTIFIER_END_INLINE)
        else:
            result.append(sentence)
    return result

def get_result_for_one_line(result, replacements, additions, ending_spaces_for_sentences):
    i = 0
    j = 0
    final_result = []
    ending_spaces_for_sentences.append("")
    while i<len(result):
        if result[i][0]==" " or result[i][0]=="-":
            final_result.append(result[i][2:]+ending_spaces_for_sentences[j])
            j+=1
        elif result[i][0]=="+":
            if result[i][2:]==DELETION_IDENTIFIER_BEGIN_INLINE:
                deletion_lines = []
                i+=1
                begin_j = j
                while i<len(result):
                    if result[i][2:]!=DELETION_IDENTIFIER_END_INLINE:
                        deletion_lines.append(result[i])
                    else:
                        break
                    if result[i][0]==" " or result[i][0]=="-":
                        j+=1
                    i+=1
                should_be_deleted, new_content = check_if_should_be_modified(deletion_lines)
                if should_be_deleted:
                    for k in range(len(new_content[0])):
                        new_content[0][k] = new_content[0][k]+ending_spaces_for_sentences[begin_j+k]
                    for k in range(len(new_content[1])):
                        new_content[1][k] = new_content[1][k]+ending_spaces_for_sentences[begin_j+len(new_content[0])+len([x for x in new_content[2] if x[0] in ["-", " "]])+k]
                    final_result.extend(new_content[0])
                    final_result.extend(new_content[1])
                else:
                    for k in range(len(new_content)):
                        new_content[k] = new_content[k]+ending_spaces_for_sentences[begin_j+k]
                    final_result.extend(new_content)
            else:
                m = re.match("^\+ "+REPLACEMENT_IDENTIFIER_BEGIN_INLINE%("(\d+)")+"$", result[i])
                if m:
                    index = int(m.groups()[0])
                    replacement_lines = []
                    i+=1
                    begin_j = j
                    while i<len(result):
                        if result[i][2:]!=REPLACEMENT_IDENTIFIER_END_INLINE:
                            replacement_lines.append(result[i])
                        else:
                            break
                        if result[i][0]==" " or result[i][0]=="-":
                            j+=1
                        i+=1
                    should_be_replaced, new_content = check_if_should_be_modified(replacement_lines)
                    if should_be_replaced:
                        for k in range(len(new_content[0])):
                            new_content[0][k] = new_content[0][k]+ending_spaces_for_sentences[begin_j+k]
                        for k in range(len(new_content[1])):
                            new_content[1][k] = new_content[1][k]+ending_spaces_for_sentences[begin_j+len(new_content[0])+len([x for x in new_content[2] if x[0] in ["-", " "]])+k]
                        final_result.extend(new_content[0])
                        final_result.append(replacements[index]+ending_spaces_for_sentences[j-1])
                        final_result.extend(new_content[1])
                    else:
                        for k in range(len(new_content)):
                            new_content[k] = new_content[k]+ending_spaces_for_sentences[begin_j+k]
                        final_result.extend(new_content)
                else:
                    m = re.match("\+ "+ADDITION_IDENTIFIER_INLINE%("(\d+)"), result[i])
                    if m:
                        index = int(m.groups()[0])
                        if i==len(result)-1:
                            final_result.append(" "+additions[index])
                        else:
                            final_result.append(additions[index]+" ")
                    else:
                        m = re.match("\+ "+REPLACEMENT_IDENTIFIER_BEGIN_INLINE%("(\d+)")+REPLACEMENT_IDENTIFIER_END_INLINE, result[i])
                        if m:
                            index = int(m.groups()[0])
                            if i==len(result)-1:
                                final_result.append(" "+replacements[index])
                            else:
                                final_result.append(replacements[index]+" ")
                        elif check_inline_modification(result[i]):
                            if i>=1:
                                if result[i-1][0]=="?" and result[i-2][0] =="-":
                                    final_result[len(final_result)-1] = get_result_for_one_sentence(result[i-2][2:], result[i][2:], replacements, additions)+ending_spaces_for_sentences[j-1]
                                elif result[i-1][0]=="-":
                                    final_result[len(final_result)-1] = get_result_for_one_sentence(result[i-1][2:], result[i][2:], replacements, additions)+ending_spaces_for_sentences[j-1]
                                elif i+1<len(result) and result[i+1][0]=="-":
                                    final_result.append(get_result_for_one_sentence(result[i+1][2:], result[i][2:], replacements, additions)+ending_spaces_for_sentences[j])
                                    j+=1
                                    i+=1
                            elif i+1<len(result) and result[i+1][0]=="-":
                                final_result.append(get_result_for_one_sentence(result[i+1][2:], result[i][2:], replacements, additions)+ending_spaces_for_sentences[j])
                                j+=1
                                i+=1
        i+=1
    return "".join(final_result)

def get_result_for_one_sentence(new, modified, replacements, additions):
    new_words = new.split(" ")
    modified_words = modified.split(" ")
    modified_words = refine_modified_words(modified_words)
    differ = Differ()
    result = list(differ.compare(new_words, modified_words))
    #print(result)
    ending_spaces_for_words = [" "]*(len(new_words)-1)
    result = get_result_for_one_line(result, replacements, additions, ending_spaces_for_words)
    return result

def refine_modified_words(modified_words):
    result = []
    for word in modified_words:
        m = re.match("^("+DELETION_IDENTIFIER_BEGIN_INLINE+"|"+REPLACEMENT_IDENTIFIER_BEGIN_INLINE%("\d+")+"|)([^"+DELETION_IDENTIFIER_END_INLINE+REPLACEMENT_IDENTIFIER_END_INLINE+"]+)("+DELETION_IDENTIFIER_END_INLINE+"|"+REPLACEMENT_IDENTIFIER_END_INLINE+"|)$",word)
        if m:
            ma = m.groups()
            if ma[0]!="":
                result.append(ma[0])
            result.append(ma[1])
            if ma[2]!="":
                result.append(ma[2])
        else:
            result.append(word)
    return result

def check_inline_modification(line):
    if DELETION_IDENTIFIER_BEGIN_INLINE in line or REPLACEMENT_IDENTIFIER_END_INLINE in line:
        return True
    m = re.findall(ADDITION_IDENTIFIER_INLINE%("\d+"), line)
    if len(m)>0:
        return True
    return False

def check_if_should_be_modified(lines):
    leading_removed, ending_removed, remained = get_leading_and_ending_removed(lines)
    transit, matching = get_transit_and_matching(remained)
    if matching<MATCHING_THRESHOLD_L:
        new_content=[]
        for line in lines:
            if line[0] in ["-", " "]:
                new_content.append(line[2:])
        return False, new_content
    return True, (leading_removed, ending_removed, remained)

def get_leading_and_ending_removed(lines):
    leading_removed=[]
    ending_removed=[]
    remained=lines
    for i in range(len(lines)):
        if lines[i][0]!="-":
            remained=lines[i:]
            break
        leading_removed.append(lines[i][2:])
    if len(remained)>0 and remained[0][0] in ["+", "?"] and len(leading_removed)>0:
        remained.insert(0, "- "+leading_removed[len(leading_removed)-1])
        leading_removed = leading_removed[:len(leading_removed)-1]
    for i in reversed(range(len(remained))):
        if remained[i][0]!="-":
            remained=remained[:i+1]
            break
        ending_removed.append(remained[i][2:])
    ending_removed = list(reversed(ending_removed))
    return leading_removed, ending_removed, remained

def get_transit_and_matching(lines):
    lines = [x for x in lines if x[0]!="?"]
    transit=0
    matching = 0
    removed = 0
    added = 0
    i = 0
    while i < len(lines)-1:
        if lines[i][0]==" ":
            removed+=1
            added+=1
            matching+=1
        elif lines[i][0]=="-":
            removed+=1
            if lines[i+1][0]=="+":
                sub_transit, sub_matching = get_transit_and_matching_for_one_line(lines[i][2:], lines[i+1][2:])
                if (sub_transit<TRANSIT_THRESHOLD_S and sub_matching>MATCHING_THRESHOLD_S) or (sub_transit>=TRANSIT_THRESHOLD_S and sub_transit<=TRANSIT_THRESHOLD_L and sub_matching>MATCHING_THRESHOLD_M) or (sub_transit>TRANSIT_THRESHOLD_L and sub_matching>MATCHING_THRESHOLD_L):
                    transit+=sub_transit/min(len(lines[i][2:].strip().split(" ")), len(lines[i+1][2:].strip().split(" ")))
                    matching+=sub_matching
                    added+=1
                    i+=1
            elif lines[i+1][0]==" ":
                transit+=1
        elif lines[i][0]=="+":
            added+=1
            if lines[i+1][0]=="-":
                sub_transit, sub_matching = get_transit_and_matching_for_one_line(lines[i+1][2:], lines[i][2:])
                if (sub_transit<TRANSIT_THRESHOLD_S and sub_matching>MATCHING_THRESHOLD_S) or (sub_transit>=TRANSIT_THRESHOLD_S and sub_transit<=TRANSIT_THRESHOLD_L and sub_matching>MATCHING_THRESHOLD_M) or (sub_transit>TRANSIT_THRESHOLD_L and sub_matching>MATCHING_THRESHOLD_L):
                    transit+=sub_transit/min(len(lines[i][2:].strip().split(" ")), len(lines[i+1][2:].strip().split(" ")))
                    matching+=sub_matching
                    removed+=1
                    i+=1
                else:
                    transit+=1
            elif lines[i+1][0]==" ":
                transit+=1
        i+=1
    if len(lines) > 0:
        lastline = lines[len(lines)-1]
        if lastline[0] == " ":
            removed+=1
            added+=1
            matching+=1
        elif lastline[0] == "+":
            if i<len(lines):
                transit+=1
            added+=1
        elif lastline[0] == "-":
            removed+=1
    minimum = min(removed,added)
    if minimum == 0:
        matching = 0
    else:
        matching = matching/minimum
    return transit, matching

def get_transit_and_matching_for_one_line(removed, added):
    
    removed_words = removed.strip().split(" ")
    added_words = added.strip().split(" ")
    if len(removed_words)==1 and len(added_words)==1:
        if removed_words[0]==added_words[0]:
            return 0, 1
        else:
            return 1, get_matching_for_one_word(removed_words[0], added_words[0])
    differ = Differ()
    diff = differ.compare(removed_words, added_words)
    transit1, matching1 = get_transit_and_matching(diff)
    return transit1, get_matching_for_one_word(removed, added)

def get_matching_for_one_word(removed, added):
    if len(removed)==1 and len(added)==1:
        if removed==added:
            return 1
        else:
            return 0
    differ = Differ()
    diff = differ.compare(removed, added)
    return get_transit_and_matching(diff)[1]

def compare_result_split(result):
    i = 0
    pre = " "
    diff_set = []
    types = []
    while i<len(result):
        if result[i][0] == "-":
            if pre == " " or pre == "+" or pre == "?":
                diff_set.append([result[i]])
                types.append(DELETION_MARKER)
            elif pre == "-":
                if i+1<len(result) and (result[i+1][0] == "+" or result[i+1][0] == "?"):
                    diff_set.append([result[i]])
                    if result[i+1][0] == "+":
                        types.append(DELETION_MARKER)
                    elif result[i+1][0] == "?":
                        types.append(REPLACEMENT_MARKER_ONELINE)
                else:
                    diff_set[len(diff_set)-1].append(result[i])
        elif result[i][0] == "+":
            if pre == " ":
                diff_set.append([result[i]])
                types.append(ADDITION_MARKER)
            elif pre == "-":
                if i+1 >= len(result) or result[i+1][0] == " " or result[i+1][0] == "?" or (i>=2 and result[i-2][0] == " ") or (result[i+1][0]=="-" and i+2<len(result) and result[i+2][0]=="?") or (result[i+1][0]=="-" and i+3<len(result) and result[i+2][0]=="+" and result[i+3][0]=="?"):
                    transit, matching = get_transit_and_matching_for_one_line(result[i-1][2:], result[i][2:])
                    #print([result[i-1][2:], result[i][2:]])
                    #print([transit, matching])
                    if (transit<TRANSIT_THRESHOLD_S and matching>MATCHING_THRESHOLD_S) or (transit>=TRANSIT_THRESHOLD_S and transit<=TRANSIT_THRESHOLD_L and matching>MATCHING_THRESHOLD_M) or (transit>TRANSIT_THRESHOLD_L and matching>MATCHING_THRESHOLD_L):
                        diff_set[len(diff_set)-1].append(result[i])
                        types[len(types)-1] = REPLACEMENT_MARKER_ONELINE
                    else:
                        types[len(types)-1] = DELETION_MARKER
                        diff_set.append([result[i]])
                        types.append(ADDITION_MARKER)
                elif i>=2 and result[i-2][0] == "-":
                    diff_set_len = len(diff_set)
                    diff_set[diff_set_len-2].append(diff_set[diff_set_len-1][0])
                    diff_set[diff_set_len-1][0] = result[i]
                    types[len(types)-1] = ADDITION_MARKER
                else:
                    diff_set.append([result[i]])
                    types.append(ADDITION_MARKER)
            elif pre == "+":
                if types[len(types)-1] == REPLACEMENT_MARKER_ONELINE:
                    diff_set.append([result[i]])
                    types.append(ADDITION_MARKER)
                else:
                    diff_set[len(diff_set)-1].append(result[i])
            elif pre == "?":
                if len(diff_set[len(diff_set)-1]) > 2 and types[len(types)-1] == REPLACEMENT_MARKER_ONELINE:
                    diff_set.append([result[i]])
                    types.append(ADDITION_MARKER)
                else:
                    transit, matching = get_transit_and_matching_for_one_line(result[i-2][2:], result[i][2:])
                    #print([result[i-2][2:], result[i][2:]])
                    #print([transit, matching])
                    if (transit<TRANSIT_THRESHOLD_S and matching>MATCHING_THRESHOLD_S) or (transit>=TRANSIT_THRESHOLD_S and transit<=TRANSIT_THRESHOLD_L and matching>MATCHING_THRESHOLD_M) or (transit>TRANSIT_THRESHOLD_L and matching>MATCHING_THRESHOLD_L):
                        diff_set[len(diff_set)-1].append(result[i])
                        types[len(types)-1] = REPLACEMENT_MARKER_ONELINE
                    else:
                        types[len(types)-1] = DELETION_MARKER
                        diff_set.append([result[i]])
                        types.append(ADDITION_MARKER)
        elif result[i][0] == "?":
            diff_set[len(diff_set)-1].append(result[i])
            
        pre = result[i][0]
        i+=1
    for j in range(len(diff_set)):
        diff_set[j].append(types[j])
    return diff_set

def compare_result_split2(result):
    i = 1
    pre = " "
    diff_set = []
    types = []
    indices = []
    if result[0][0]!=" ":
        diff_set.append([result[0]])
        types.append(result[0][0])
        indices.append(0)
    while i<len(result):
        if result[i][0]!=" ":
            if result[i][0]!=result[i-1][0]:
                diff_set.append([result[i]])
                types.append(result[i][0])
                indices.append(i)
            else:
                diff_set[len(diff_set)-1].append(result[i])
        i+=1
    i=0
    diff_set2 = []
    types2 = []
    while i<len(diff_set)-1:
        old = diff_set[i]
        diff_set[i] = [x for x in diff_set[i] if x[0]!="_"]
        old_len = len(old)
        if len(diff_set[i])==1:
            if indices[i+1]==indices[i]+old_len:
                if types[i+1]=="?":
                    if types[i]=="-":
                        transit, matching = get_transit_and_matching_for_one_line(diff_set[i][0][2:], diff_set[i+2][0][2:])
                        if (transit<TRANSIT_THRESHOLD_S and matching>MATCHING_THRESHOLD_S) or (transit>=TRANSIT_THRESHOLD_S and transit<=TRANSIT_THRESHOLD_L and matching>MATCHING_THRESHOLD_M) or (transit>TRANSIT_THRESHOLD_L and matching>MATCHING_THRESHOLD_L):
                            diff_set2.append([diff_set[i][0], diff_set[i+1][0], diff_set[i+2][0]])
                            types2.append(REPLACEMENT_MARKER_ONELINE)
                            if len(diff_set[i+2])>1:
                                diff_set2.append(diff_set[i+2][1:])
                                types2.append(ADDITION_MARKER)
                                i+=2
                            elif i+3<len(diff_set) and types[i+3]=="?":
                                diff_set2[len(diff_set2)-1].append(diff_set[i+3][0])
                                i+=3
                            else:
                                i+=2
                        else:
                            diff_set2.append([diff_set[i][0], diff_set[i+1][0]])
                            types2.append(DELETION_MARKER)
                            if len(diff_set[i+2])==1 and i+3<len(diff_set) and types[i+3]=="?":
                                diff_set[i+2].append(diff_set[i+3][0])
                                diff_set2.append(diff_set[i+2])
                                types2.append(ADDITION_MARKER)
                                i+=3
                            else:
                                diff_set2.append(diff_set[i+2])
                                types2.append(ADDITION_MARKER)
                                i+=2
                    else:
                        #print(diff_set2)
                        #print(diff_set[i])
                        #print("\ndiff: ".join([str(x) for x in diff_set]))
                        print("difflib error1")
                        raise Exception("difflib error1")
                else:
                    if types[i]=="-":
                        
                        if len(diff_set[i+1])==1:
                            transit, matching = get_transit_and_matching_for_one_line(diff_set[i][0][2:], diff_set[i+1][0][2:])
                            if (transit<TRANSIT_THRESHOLD_S and matching>MATCHING_THRESHOLD_S) or (transit>=TRANSIT_THRESHOLD_S and transit<=TRANSIT_THRESHOLD_L and matching>MATCHING_THRESHOLD_M) or (transit>TRANSIT_THRESHOLD_L and matching>MATCHING_THRESHOLD_L):
                                diff_set2.append([diff_set[i][0], diff_set[i+1][0]])
                                types2.append(REPLACEMENT_MARKER_ONELINE)
                                if i+2<len(diff_set) and types[i+2]=="?":
                                    diff_set2[len(diff_set2)-1].append(diff_set[i+2][0])
                                    i+=2
                                else:
                                    i+=1
                            else:
                                diff_set2.append(diff_set[i])
                                types2.append(DELETION_MARKER)
                                if i+2<len(diff_set) and types[i+2]=="?":
                                    diff_set[i+1].append(diff_set[i+2][0])
                                    diff_set2.append(diff_set[i+1])
                                    types2.append(ADDITION_MARKER)
                                    i+=2
                                else:
                                    diff_set2.append(diff_set[i+1])
                                    types2.append(ADDITION_MARKER)
                                    i+=1
                        else:
                            
                            transit1, matching1 = get_transit_and_matching_for_one_line(diff_set[i][0][2:], diff_set[i+1][0][2:])
                            transit2, matching2 = get_transit_and_matching_for_one_line(diff_set[i][0][2:], diff_set[i+1][len(diff_set[i+1])-1][2:])
                            if matching1>=matching2:
                                if (transit1<TRANSIT_THRESHOLD_S and matching1>MATCHING_THRESHOLD_S) or (transit1>=TRANSIT_THRESHOLD_S and transit1<=TRANSIT_THRESHOLD_L and matching1>MATCHING_THRESHOLD_M) or (transit1>TRANSIT_THRESHOLD_L and matching1>MATCHING_THRESHOLD_L):
                                    diff_set2.append([diff_set[i][0], diff_set[i+1][0]])
                                    types2.append(REPLACEMENT_MARKER_ONELINE)
                                    diff_set[i+1]= diff_set[i+1][1:]
                                    diff_set[i+1].append("_ ")
                                else:
                                    diff_set2.append(diff_set[i])
                                    types2.append(DELETION_MARKER)
                            else:
                                if (transit2<TRANSIT_THRESHOLD_S and matching2>MATCHING_THRESHOLD_S) or (transit2>=TRANSIT_THRESHOLD_S and transit2<=TRANSIT_THRESHOLD_L and matching2>MATCHING_THRESHOLD_M) or (transit2>TRANSIT_THRESHOLD_L and matching2>MATCHING_THRESHOLD_L):
                                    diff_set2.append(diff_set[i+1][:len(diff_set[i+1])-1])
                                    types2.append(ADDITION_MARKER)
                                    diff_set2.append([diff_set[i][0], diff_set[i+1][len(diff_set[i+1])-1]])
                                    for ri in range(len(diff_set[i+1])-1):
                                        result[indices[i+1]-1+ri] = diff_set[i+1][ri]
                                    result[indices[i+1]-2+len(diff_set[i+1])] = diff_set[i][0]
                                    result[indices[i+1]-1+len(diff_set[i+1])] = diff_set[i+1][len(diff_set[i+1])-1]
                                    types2.append(REPLACEMENT_MARKER_ONELINE)
                                    i+=1
                                else:
                                    diff_set2.append(diff_set[i])
                                    types2.append(DELETION_MARKER)
                    elif types[i]=="+":
                        if len(diff_set[i+1])==1:
                            if (i+2<len(diff_set) and types[i+2]=="?") or (i+3<len(diff_set) and types[i+2]=="+" and types[i+3]=="?"):
                                diff_set2.append(diff_set[i])
                                types2.append(ADDITION_MARKER)
                            else:
                                transit, matching = get_transit_and_matching_for_one_line(diff_set[i+1][0][2:], diff_set[i][0][2:])
                                if ((transit<TRANSIT_THRESHOLD_S and matching>MATCHING_THRESHOLD_S) or (transit>=TRANSIT_THRESHOLD_S and transit<=TRANSIT_THRESHOLD_L and matching>MATCHING_THRESHOLD_M) or (transit>TRANSIT_THRESHOLD_L and matching>MATCHING_THRESHOLD_L)) and min(len(diff_set[i+1][0][2:]), len(diff_set[i][0][2:]))/max(len(diff_set[i+1][0][2:]), len(diff_set[i][0][2:]))>0.4:
                                    diff_set2.append([diff_set[i][0], diff_set[i+1][0]])
                                    types2.append(REPLACEMENT_MARKER_ONELINE)
                                    i+=1
                                else:
                                    diff_set2.append(diff_set[i])
                                    types2.append(ADDITION_MARKER)
                                
                        else:
                            transit1, matching1 = get_transit_and_matching_for_one_line(diff_set[i+1][0][2:], diff_set[i][0][2:])
                            transit2, matching2 = get_transit_and_matching_for_one_line(diff_set[i+1][len(diff_set[i+1])-1][2:], diff_set[i][0][2:])
                            if matching1>=matching2:
                                if ((transit1<TRANSIT_THRESHOLD_S and matching1>MATCHING_THRESHOLD_S) or (transit1>=TRANSIT_THRESHOLD_S and transit1<=TRANSIT_THRESHOLD_L and matching1>MATCHING_THRESHOLD_M) or (transit1>TRANSIT_THRESHOLD_L and matching1>MATCHING_THRESHOLD_L)) and min(len(diff_set[i+1][0][2:]), len(diff_set[i][0][2:]))/max(len(diff_set[i+1][0][2:]), len(diff_set[i][0][2:]))>0.4:
                                    diff_set2.append([diff_set[i][0], diff_set[i+1][0]])
                                    types2.append(REPLACEMENT_MARKER_ONELINE)
                                    diff_set[i+1]= diff_set[i+1][1:]
                                    diff_set[i+1].append("_ ")
                                else:
                                    diff_set2.append(diff_set[i])
                                    types2.append(ADDITION_MARKER)
                            else:
                                if (not ((i+2<len(diff_set) and types[i+2]=="?") or (i+3<len(diff_set) and types[i+2]=="+" and types[i+3]=="?"))) and ((transit2<TRANSIT_THRESHOLD_S and matching2>MATCHING_THRESHOLD_S) or (transit2>=TRANSIT_THRESHOLD_S and transit2<=TRANSIT_THRESHOLD_L and matching2>MATCHING_THRESHOLD_M) or (transit2>TRANSIT_THRESHOLD_L and matching2>MATCHING_THRESHOLD_L)) and min(len(diff_set[i+1][len(diff_set[i+1])-1][2:]), len(diff_set[i][0][2:]))/max(len(diff_set[i+1][len(diff_set[i+1])-1][2:]), len(diff_set[i][0][2:]))>0.4:
                                    diff_set2.append(diff_set[i+1][:len(diff_set[i+1])-1])
                                    types2.append(DELETION_MARKER)
                                    diff_set2.append([diff_set[i+1][len(diff_set[i+1])-1], diff_set[i][0]])
                                    for ri in range(len(diff_set[i+1])):
                                        result[indices[i+1]-1+ri] = diff_set[i+1][ri]
                                    result[indices[i+1]-1+len(diff_set[i+1])] = diff_set[i][0]
                                    types2.append(REPLACEMENT_MARKER_ONELINE)
                                    i+=1
                                else:
                                    diff_set2.append(diff_set[i])
                                    types2.append(ADDITION_MARKER)
                    else:
                        #print(diff_set2)
                        #print(diff_set[i])
                        #print("\ndiff: ".join([str(x) for x in diff_set]))
                        print("difflib error2")
                        raise Exception("difflib error2")
            else:
                if types[i]=="-":
                    diff_set2.append(diff_set[i])
                    types2.append(DELETION_MARKER)
                elif types[i]=="+":
                    diff_set2.append(diff_set[i])
                    types2.append(ADDITION_MARKER)
                else:
                    #print(diff_set2)
                    #print(diff_set[i])
                    #print("\ndiff: ".join([str(x) for x in diff_set]))
                    print("difflib error3")
                    raise Exception("difflib error3")
        else:
            if indices[i+1]==indices[i]+old_len:
                
                if types[i+1]=="?":
                    if types[i]=="-":
                        transit, matching = get_transit_and_matching_for_one_line(diff_set[i][len(diff_set[i])-1][2:], diff_set[i+2][0][2:])
                        if (transit<TRANSIT_THRESHOLD_S and matching>MATCHING_THRESHOLD_S) or (transit>=TRANSIT_THRESHOLD_S and transit<=TRANSIT_THRESHOLD_L and matching>MATCHING_THRESHOLD_M) or (transit>TRANSIT_THRESHOLD_L and matching>MATCHING_THRESHOLD_L):
                            diff_set2.append(diff_set[i][:len(diff_set[i])-1])
                            types2.append(DELETION_MARKER)
                            diff_set2.append([diff_set[i][len(diff_set[i])-1], diff_set[i+1][0], diff_set[i+2][0]])
                            types2.append(REPLACEMENT_MARKER_ONELINE)
                            if len(diff_set[i+2])>1:
                                diff_set2.append(diff_set[i+2][1:])
                                types2.append(ADDITION_MARKER)
                                i+=2
                            elif i+3<len(diff_set) and types[i+3]=="?":
                                diff_set2[len(diff_set2)-1].append(diff_set[i+3][0])
                                i+=3
                            else:
                                i+=2
                        else:
                            diff_set[i].append(diff_set[i+1][0])
                            diff_set2.append(diff_set[i])
                            types2.append(DELETION_MARKER)
                            if len(diff_set[i+2])==1 and i+3<len(diff_set) and types[i+3]=="?":
                                diff_set[i+2].append(diff_set[i+3][0])
                                diff_set2.append(diff_set[i+2])
                                types2.append(ADDITION_MARKER)
                                i+=3
                            else:
                                diff_set2.append(diff_set[i+2])
                                types2.append(ADDITION_MARKER)
                                i+=2
                    else:
                        #print(diff_set2)
                        #print(diff_set[i])
                        #print("\ndiff: ".join([str(x) for x in diff_set]))
                        print("difflib error4")
                        raise Exception("difflib error4")
                else:
                    
                    if types[i]=="-":
                        transit, matching = get_transit_and_matching_for_one_line(diff_set[i][len(diff_set[i])-1][2:], diff_set[i+1][0][2:])
                        if (transit<TRANSIT_THRESHOLD_S and matching>MATCHING_THRESHOLD_S) or (transit>=TRANSIT_THRESHOLD_S and transit<=TRANSIT_THRESHOLD_L and matching>MATCHING_THRESHOLD_M) or (transit>TRANSIT_THRESHOLD_L and matching>MATCHING_THRESHOLD_L):
                            diff_set2.append(diff_set[i][:len(diff_set[i])-1])
                            types2.append(DELETION_MARKER)
                            diff_set2.append([diff_set[i][len(diff_set[i])-1], diff_set[i+1][0]])
                            types2.append(REPLACEMENT_MARKER_ONELINE)
                            if len(diff_set[i+1])>1:
                                diff_set2.append(diff_set[i+1][1:])
                                types2.append(ADDITION_MARKER)
                                i+=1
                            elif i+2<len(diff_set) and types[i+2]=="?":
                                diff_set2[len(diff_set2)-1].append(diff_set[i+2][0])
                                i+=2
                            else:
                                i+=1
                        else:
                            diff_set2.append(diff_set[i])
                            types2.append(DELETION_MARKER)
                            if len(diff_set[i+1])==1 and i+2<len(diff_set) and types[i+2]=="?":
                                diff_set[i+1].append(diff_set[i+2][0])
                                diff_set2.append(diff_set[i+1])
                                types2.append(ADDITION_MARKER)
                                i+=2
                            else:
                                diff_set2.append(diff_set[i+1])
                                types2.append(ADDITION_MARKER)
                                i+=1
                    elif types[i]=="+":
                        transit, matching = get_transit_and_matching_for_one_line(diff_set[i+1][0][2:], diff_set[i][len(diff_set[i])-1][2:])
                        if (not (i+2<len(diff_set) and types[i+2]=="?")) and ((transit<TRANSIT_THRESHOLD_S and matching>MATCHING_THRESHOLD_S) or (transit>=TRANSIT_THRESHOLD_S and transit<=TRANSIT_THRESHOLD_L and matching>MATCHING_THRESHOLD_M) or (transit>TRANSIT_THRESHOLD_L and matching>MATCHING_THRESHOLD_L)) and min(len(diff_set[i+1][0][2:]), len(diff_set[i][len(diff_set[i])-1][2:]))/max(len(diff_set[i+1][0][2:]), len(diff_set[i][len(diff_set[i])-1][2:]))>0.4:
                            diff_set2.append(diff_set[i][:len(diff_set[i])-1])
                            types2.append(ADDITION_MARKER)
                            diff_set2.append([diff_set[i][len(diff_set[i])-1], diff_set[i+1][0]])
                            types2.append(REPLACEMENT_MARKER_ONELINE)
                            if len(diff_set[i+1])>1:
                                diff_set[i+1] = diff_set[i+1][1:]
                                diff_set[i+1].append("_ ")
                            else:
                                i+=1
                        else:
                            diff_set2.append(diff_set[i])
                            types2.append(ADDITION_MARKER)
                    else:
                        #print(diff_set2)
                        #print(diff_set[i])
                        #print("\ndiff: ".join([str(x) for x in diff_set]))
                        print("difflib error5")
                        raise Exception("difflib error5")
            else:
                if types[i]=="-":
                    diff_set2.append(diff_set[i])
                    types2.append(DELETION_MARKER)
                elif types[i]=="+":
                    diff_set2.append(diff_set[i])
                    types2.append(ADDITION_MARKER)
                else:
                    #print(diff_set2)
                    #print(diff_set[i])
                    #print("\ndiff: ".join([str(x) for x in diff_set]))
                    print("difflib error6")
                    raise Exception("difflib error6")
        i+=1
    if i==len(diff_set)-1:
        diff_set[i] = [x for x in diff_set[i] if x[0]!="_"]
        diff_set2.append(diff_set[i])
        if types[i]=="-":
            types2.append(DELETION_MARKER)
        elif types[i]=="+":
            types2.append(ADDITION_MARKER)
        else:
            print("difflib error5")
            raise Exception("difflib error5")
    for j in range(len(diff_set2)):
        diff_set2[j].append(types2[j])
    return diff_set2

def getlastmonthmd(filepath, repopath):
    global g
    if g==None:
        g = git.Git(repopath)
    result = g.show("lastmonthcustomized:"+filepath).replace("\ufeff", "")
    return result.strip()

def customize_mdcontent(mdcontent):
    mdcontent = constant_replacement(mdcontent)
    mdcontent = regex_replacement(mdcontent)
    mdcontent = semi_replacement(mdcontent)
    mdcontent = correction_replacement(mdcontent)
    mdcontent = refineNestedListContent(mdcontent, True)
    return mdcontent.strip()

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
                    if not re.match(condition["match"], match_tuple[condition["parameter"]]):
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
    if len(constant) > 0:
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

def replaceUrlRelativeLink(filepath, repopath):
    file = open(filepath, "r", encoding="utf8")
    mdcontent = file.read()
    file.close()
    mdcontent = replaceUrlRelativeLink_mdcontent(mdcontent, filepath, repopath)
    file = open(filepath, "w", encoding="utf8")
    file.write(mdcontent)
    file.close()

def replaceUrlRelativeLink_mdcontent(mdcontent, filepath, repopath):
    global replaceUrlRelativeLink_filepath
    replaceUrlRelativeLink_filepath = filepath
    global replaceUrlRelativeLink_repopath
    replaceUrlRelativeLink_repopath = repopath
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
    mdpath = repopath+"/articles/"+relative_link+"/index.md"
    if os.path.isfile(mdpath):
        return left + get_path_with_2_path(filepath, mdpath)
    return found

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

