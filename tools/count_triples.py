content = open(r"src\db\mixins\stock_mixin.py", encoding='utf-8', errors='replace').read()
lines = content.split('\n')
# Count triple quotes from the beginning - look for the first unmatched one
triple_count = 0
in_string = False
for i, line in enumerate(lines[1032:], start=1033):
    cnt = line.count('"""')
    if cnt > 0:
        triple_count += cnt
        print(f'{i}: cnt={cnt} cumulative={triple_count}: {repr(line[:80])}')
    if i > 1055:
        break
