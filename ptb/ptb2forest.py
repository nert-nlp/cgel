while True:
    tree = input('Enter a tree: ')
    toks = []
    for char in tree:
        if char == '(':
            toks.append('[')
            toks.append('')
        elif char == ')':
            toks.append(']')
        elif char == ' ':
            toks.append('')
        else:
            toks[-1] += char
    toks = [x for x in toks if x != '']
    print(toks)

    res = ""
    for i, tok in enumerate(toks):
        if tok == '[':
            res += "["
        elif tok == ']':
            res += "]"
        else:
            if toks[i - 1] != '[':
                res += f"[{tok}]"
            else:
                res += tok

    res = "\\begin{forest}" + res + "\\end{forest}"
    print(res)