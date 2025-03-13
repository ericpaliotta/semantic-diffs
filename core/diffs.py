'''
this python script takes in two yaml files as arguments and compares them semantically

Notes/Opitimizations:
- need to implement nested list diffs
- once this algo is neat and working, we could create a similarity matrix type, and override indexing operations or something to make it so that we can have a constant time access
  2-D like data structure, which is actually a 1-D list. This then allows us to sort in-place at the end without duplicating all of the data
- could we memoize the mismatch paths? rather than returning a growing list of lists up the call stack, just throw a pointer around? 
    - this can be more easily implemented once the mismatches are encapsulated as their own data type
    - could pass a pointer down the call stack and then have an append operation for the mismatch data structure which takes in a pointer and some mismatch indices or something. Use a linked list maybe
'''

import yaml


def _create_similarity_matrix(l1: list, l2: list) -> list:
    '''
    takes in two lists of data, and returns a 2-D matrix with by-index similarity scores for each index pair. The higher
    the similarity score, the better the match
    
    The returned similarity matrix is in the form: matrix[l1_index][l2_index]

    The similarity score for each index pair starts at 0, and is incremented by 1 for each of the following
    1. the two indices contain dictionaries, and share a simple key->value mapping (i.e. both dicts contain "isObject: true")
    2. the two indices contain dictionaries, and share a key for a nested complex data type mapping (i.e. both contain "dog: {...}"
        regardless of nested dictionary contents)
    3. the two indices contain a simple value and match. All simple value similarity scores should be 1 or 0

    TODO: implement list similarity based upon length
    '''
    # step 1: create the similarity matrix
    similarity_matrix = [[0] * len(l1) for _ in range(len(l2)) ] # here we take the inner arrays to be rows. Assign R = len(l1), C = len(l2), r_i = index in l1, c_j = index in l2

    # step 2: parse l2 into usable data structures
    simple_values = {} # map for simple values of the form { value -> [index1, index2, ...] }
    key_value_pairs = {} # map of keys in complex data types and their values of the form { (key,value) -> [index1, index2, ...] }
    complex_keys = {} # map of keys which map to more complex data types of the form { key -> [index1, index2, ...] }
    list_lengths = {} # map of list length to indices for nested lists of form { length => [index1, index2, ...]}

    for i in range(len(l2)):
        # sub-routine to parse the complex data type into constant time-access data structures
        if type(l2[i]) == dict:
            for k, v in l2[i].items():
                if type(v) == dict or type(v) == list:
                    complex_keys[k] = complex_keys.get(k, []) + [i]
                else:
                    key_value_pairs[(k,v)] = key_value_pairs.get((k, v), []) + [i]

        elif type(l2[i]) == list:
            # I'm not God...not yet implemented. Lists all score 0 with everything -> all labelled mis-matches
            list_lengths[len(l2[i])] = list_lengths.get(len(l2[i]), []) + [i]
        else:
            simple_values[l2[i]] = simple_values.get(l2[i], []) + [i]

    # step 3: populate the similarity matrix + find simple non-matches
    for i in range(len(l1)):
        if type(l1[i]) == dict:
            # iter over complex data type keys
            for k, v in l1[i].items():
                # nested complex data structure -> only use key for similarity mapping (i.e. limited depth matching)
                if type(v) == dict or type(v) == list:
                    # if there are no matches, this will not iterate
                    for l2_index in complex_keys.get(k, []):
                        similarity_matrix[i][l2_index] += 1
                # simple key-value mapping, try to compare both to l2
                else:
                    # if there are no matches, this will not iterate
                    for l2_index in key_value_pairs.get((k, v), []):
                        similarity_matrix[i][l2_index] += 1
        elif type(l1[i]) == list:
            # I'm not God...not yet implemented. Lists all score 0 with everything -> all labelled mis-matches
            for l2_index in list_lengths.get(len(l1[i]), []):
                similarity_matrix[i][l2_index] += 1
        else:
            for l2_index in simple_values.get(l1[i], []):
                similarity_matrix[i][l2_index] += 1

    return similarity_matrix


def _sort_similarity_list(sl: list) -> list:
    '''
    runs a descending merge sort on a list of the form:

    [... (score, row_index, column_index), ...]

    using "score" as the value to sort by

    This is a recursive function
    '''
    # base case
    if len(sl) <= 1:
        return sl
    # recursion case
    else:
        split_index = int(len(sl)/2)
        h1 = _sort_similarity_list(sl[0:split_index])
        h2 = _sort_similarity_list(sl[split_index:])

        # join the sorted halves
        sorted_list = []
        while len(h1) > 0 or len(h2) > 0:
            if len(h1) == 0:
                sorted_list.append(h2.pop(0))
            elif len(h2) == 0:
                sorted_list.append(h1.pop(0))
            elif h1[0][0] > h2[0][0]:
                sorted_list.append(h1.pop(0))
            else:
                sorted_list.append(h2.pop(0))
        return sorted_list


def _sort_similarity_matrix(sm: list) -> list:
    '''
    takes in a 2-D similarity matrix and returns a list sorted descending by similarity score of the form

    [... (score, row_index, column_index), ...]

    this uses merge sort
    '''
    # turn the similarity matrix into a similarity list
    sim_list = []
    for r in range(len(sm)):
        for c in range(len(sm[r])):
            sim_list.append((sm[r][c], r, c))

    # merge-sort the similarity list
    return _sort_similarity_list(sim_list)


def list_diff(l1: list, l2: list) -> list:
    '''
    recursively gets the differences between elements of two lists. This is done semantically using "similarity scores" to match
    indices across lists, rather than by index

    Returns a list of the form:

    [...[(index, None), ...], [(None, index), ...], ...]
    
    where each sub-list is a path from the list into where a mis-match occurs (i.e. if there are nested dicts, the next entry would be a key)
    Tuples are used for list indices to indicate whether we are seeing a mismatch in the list 1 or list 2 index
    '''
    # step 1: create similarity matrix, and data structures in which to store the results
    similarity_matrix = _create_similarity_matrix(l1, l2)

    # step 2: turn the similarity matrix into a list, and sort it by score
    similarity_list = _sort_similarity_matrix(similarity_matrix)
    similarity_matrix = None # de-alloc

    # step 3: label matches and mis-matches based upon the similarity list
    seen_l1_indices = set()
    mismatch_l1_indices = set()
    seen_l2_indices = set()
    mismatch_l2_indices = set()
    mismatch_set = set() # set of mismatching indices in the form [...(l1_index, l2_index)...]
    to_recurse = [] # array of complex data type indices to recursively compare with one another. This is in the form [...(l1_index, l2_index)...]
    for elem in similarity_list:
        # case 1: maximum score of both l1 and l2 index (non-zero), count as a match
        if elem[0] > 0 and not (elem[1] in seen_l1_indices or elem[2] in seen_l2_indices):
            seen_l1_indices.add(elem[1])
            seen_l2_indices.add(elem[2])
            # TODO: deal with simple matches here
            if type(l1[elem[1]]) == dict and type(l2[elem[2]]) == dict:
                to_recurse.append((elem[1], elem[2]))
            # this may blow up my computer
            elif type(l1[elem[1]]) == list and type(l2[elem[2]]) == list:
                to_recurse.append((elem[1], elem[2]))

        # case 2: zero score, automatically a mismatch
        elif elem[0] == 0:
            # if either index does not have a match, and has 0 similarity score, we label it a mismatch
            if not elem[1] in seen_l1_indices:
                mismatch_set.add((elem[1], None))
                mismatch_l1_indices.add(elem[1])
            if not elem[2] in seen_l2_indices:
                mismatch_set.add((None, elem[2]))
                mismatch_l2_indices.add(elem[2])

    # step 4: label straggler mis-matches
    labelled_l1 = seen_l1_indices.union(mismatch_l1_indices) # either a mismatch, or "seen" as a match
    for i in range(len(l1)):
        if i not in labelled_l1:
            mismatch_set.add((i, None))
    labelled_l2 = seen_l2_indices.union(mismatch_l2_indices) # either a mismatch, or "seen" as a match
    for i in range(len(l2)):
        if i not in labelled_l2:
            mismatch_set.add((None, i))

    # step 5: de-alloc all memory, run recursions
    # TEMP: in python, IDK if this even works but I'm prob going to re-write in C or something so it's good to have de-alloc placeholders
    similarity_list = None
    seen_l1_indices = None
    mismatch_l1_indices = None
    labelled_l2 = None
    seen_l2_indices = None
    mismatch_l2_indices = None

    mismatches = [ [elem] for elem in mismatch_set ]
    for elem in to_recurse:
        if type(l1[elem[0]]) == dict and type(l2[elem[1]]) == dict:
            tmp_non_match_list = dict_diff(l1[elem[0]], l2[elem[1]])
            for retvals in tmp_non_match_list:
                mismatches.append([elem] + retvals)
        # Not impl yet...I'm not God
        # this may blow up my computer
        elif type(l1[elem[0]]) == list and type(l2[elem[1]]) == list:
            tmp_non_match_list = list_diff(l1[elem[0]], l2[elem[1]])
            for retvals in tmp_non_match_list:
                mismatches.append([elem] + retvals)
        else:
            # TODO: edge case here for types not matching...should never hit this
            print('case for "to_recurse" index types do not match. If you hit this, something is wrong')
    return mismatches


def dict_diff(d1: dict, d2: dict) -> list:
    '''
    this function is recursive, and returns a list of key tuples, showing the differences between two
    dictionaries. Note that an empty value for a key will match a non-existent key in the other dict
    (i.e. a key set to None is the same as not having the key). All list indices taken w.r.t. d1

    For example

    a = {'a': 1, 'b': 2, 'c': {'d': 1}}
    b = {'a': 1, 'b': 1, 'c': {'d': 2}}

    would return [('b'), ('c', 'd')]
    '''
    dict_keys_to_recurse = [] # list of key tuples which represent dictionaries to recursively explore
    list_keys_to_recurse = [] # list of key tuples which represent lists to recursively explore
    return_values = []
    keys = set(d1.keys()).union(set(d2.keys()))
    for k in keys:
        if type(d1.get(k, None)) == dict and type(d2.get(k, None)) == dict:
            dict_keys_to_recurse.append(k) 
        elif type(d1.get(k, None)) == list and type(d2.get(k, None)) == list:
            list_keys_to_recurse.append(k)
        elif d1.get(k, None) != d2.get(k, None):
            return_values.append([k]) # adds the last key in the non-matching branch (rest will be added as we move up the call stack)
    
    for k in dict_keys_to_recurse:
        tmp_non_match_list = dict_diff(d1[k], d2[k])
        for retvals in tmp_non_match_list:
            return_values.append([k] + retvals)

    for k in list_keys_to_recurse:
        tmp_non_match_list = list_diff(d1[k], d2[k])
        for retvals in tmp_non_match_list:
            return_values.append([k] + retvals)
    return return_values


# def display(paths: list, d1: dict, d2: dict):
#     '''
#     prints out a legible summary of the differences between the dictionaries, given a list of paths to where these differences occur
#     '''
#     for path in paths:
#         readable_path = 'root' # builds a legible version of the path through the yaml file
#         curr_lvl1 = d1
#         curr_lvl2 = d2
#         for path_elem in path:
#             # indicates a list
#             if type(path_elem) == tuple:
#                 readable_path = f'{readable_path}->{'/'.join(str(path_elem))}'
#                 curr_lvl1 = None if path_elem[0] == None else curr_lvl1[path_elem[0]]
#                 curr_lvl2 = None if path_elem[1] == None else curr_lvl2[path_elem[1]]
#             # indicates a dict
#             else:
#                 readable_path = f'{readable_path}->{path_elem}'
#                 curr_lvl1 = curr_lvl1.get(path_elem, None)
#                 curr_lvl2 = curr_lvl2.get(path_elem, None)
#         print(f'for path: {readable_path} the inconsistent values are:')
#         print(f'file 1: \n {curr_lvl1}')
#         print(f'file 2: \n {curr_lvl2}')

if __name__=='__main__':
    # a = {'a': {'c': 2}, 'b': 2}
    # b = {'a': {'c': 2, 'h': 'help'}, 'b': 3}
    # a = {'a': [1, 2, 3, 5]}
    # b = {'a': [1, 2, 4, 5]}
    # display(dict_diff(a, b), a, b)

    a = [
        1,
        2,
        {
            'a':'b',
            'b': {
                'c': 2
            }
        },
        [
            1,
            2,
            {
                'a':'b',
                'b': {
                    'c': 2
                }
            }
        ]
    ]
    b = [
        1,
        4,
        {
            'k':'c',
            'a':'b',
            'b': {
                'd': 2
            }
        },
        [
            1,
            2,
            {
                'k':'c',
                'a':'b',
                'b': {
                    'd': 2
                }
            }
        ]
    ]
    print(list_diff(a, b))


    # # trying some bigger yaml
    # yaml_1 = {}
    # with open('test1.yaml') as yaml_1_file:
    #     yaml_1 = yaml.safe_load(yaml_1_file)
    # yaml_2 = {}
    # with open('test2.yaml') as yaml_2_file:
    #     yaml_2 = yaml.safe_load(yaml_2_file)
    # print(dict_diff(yaml_1, yaml_2))