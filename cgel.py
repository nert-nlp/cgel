from collections import defaultdict

class Node:
    def __init__(self, deprel, constituent, text=None):
        self.deprel = deprel
        self.constituent = constituent
        self.text = text
    
    def __str__(self):
        if self.text:
            return f':{self.deprel} ({self.constituent} :t "{self.text}"'
        elif self.deprel:
            return f':{self.deprel} ({self.constituent}'
        else:
            return f'({self.constituent}'

class Tree:
    def __init__(self):
        self.tokens = {}
        self.children = defaultdict(list)
    
    def add_token(self, token, deprel, constituent, i, head):
        # print(token, deprel, constituent, i, head)
        if token:
            self.tokens[head][0].text = token
        else:
            self.tokens[i] = (Node(deprel, constituent), head)
            self.children[head].append(i)

    def draw_rec(self, head, depth):
        result = ""
        result += '\n' + '    ' * depth + str(self.tokens[head][0])
        for i in self.children[head]:
            result += self.draw_rec(i, depth + 1)
        result += ')'
        return result
    
    def draw(self):
        head = 0
        while self.tokens[head][1] >= 0:
            head = self.tokens[head][1]
        return self.draw_rec(head, 0)
    
    def __str__(self):
        return self.draw()