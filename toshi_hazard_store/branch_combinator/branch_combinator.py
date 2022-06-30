from toshi_hazard_store.branch_combinator.SLT_test1 import *
import itertools
import math


DTOL = 1.0e-6

def get_branches():

    #TODO: only handles one combined job and one permutation set
    permute = logic_tree_permutations[0][0]['permute']

    # check that each permute group weights sum to 1.0
    for group in permute:
        group_weight = 0
        for member in group['members']:
            group_weight += member['weight']
        if (group_weight < 1.0-DTOL) | (group_weight > 1.0+DTOL):
            raise Exception(f'group {group["group"]} weight does not sum to 1.0')
    

    # do the thing
    id_groups = []
    for group in permute:
        id_group = []
        for member in group['members']:
            id_group.append( {'id':member['hazard_id'], 'weight':member['weight']} )
        id_groups.append(id_group)
    
    branches = itertools.product(*id_groups)
    source_branches = []
    for i, branch in enumerate(branches):
        name = str(i)
        ids = [leaf['id'] for leaf in branch]
        weights = [leaf['weight'] for leaf in branch]
        weight = math.prod(weights)
        branch_dict = dict(name=name, ids=ids, weight=weight)
        source_branches.append(branch_dict)

    # double check that the weights are done correctly
    
    weight = 0
    for branch in source_branches:
        weight += branch['weight']
    if not ((weight > 1.0-DTOL) & (weight < 1.0+DTOL)):
        print(weight)
        raise Exception('weights do not sum to 1')

    return source_branches
    


