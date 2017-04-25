
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
