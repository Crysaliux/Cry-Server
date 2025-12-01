from collections import defaultdict

perms = [("288343463", "BAN"), ("288343463", "KISS"), ("288343463", "NUZZLE"),
         ("288343", "BOOP"), ("288343", "LICK"), ("288343", "SNUGGLE")]

struct = defaultdict(list)
for parent, perm in perms:
    struct[parent].append(perm)


print(dict(struct))