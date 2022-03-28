from collections import defaultdict

class Node:
    def __init__(self, deprel, constituent, head, text=None):
        self.deprel = deprel
        self.constituent = constituent
        self.text = text
        self.head = head
    
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
    
    def add_token(self, token: str, deprel: str, constituent: str, i: int, head: int):
        # print(token, deprel, constituent, i, head)
        if token:
            self.tokens[head].text = token
        else:
            self.tokens[i] = Node(deprel, constituent, head)
            self.children[head].append(i)

    def get_root(self):
        root = 0
        while self.tokens[root].head >= 0:
            root = self.tokens[root].head
        return root

    def draw_rec(self, head, depth):
        result = ""
        result += '\n' + '    ' * depth + str(self.tokens[head])
        for i in self.children[head]:
            result += self.draw_rec(i, depth + 1)
        result += ')'
        return result
    
    def draw(self):
        return self.draw_rec(self.get_root(), 0)

    def sentence(self):
        return ' '.join(self.sentence_rec(self.get_root()))
    
    def sentence_rec(self, cur):
        result = []
        if self.tokens[cur].text:
            result.append(self.tokens[cur].text)
        for i in self.children[cur]:
            result.extend(self.sentence_rec(i))
        return result

    def prune(self, string):
        self.prune_rec(self.get_root(), string)
    
    def prune_rec(self, cur, string):
        removal = []
        for i in self.children[cur]:
            if self.prune_rec(i, string):
                removal.append(i)
        if self.tokens[cur].deprel:
            if string in self.tokens[cur].deprel and len(self.children[cur]) == 0:
                return True
        for i in removal:
            self.children[cur].remove(i)

    def merge_text(self, string):
        self.merge_text_rec(self.get_root(), string)

    def merge_text_rec(self, cur, string):
        if self.tokens[cur].deprel:
            if string in self.tokens[cur].deprel:
                head = self.tokens[cur].head
                self.tokens[head].text = self.tokens[cur].constituent
                self.children[head].remove(cur)
                for i in self.children[cur]:
                    self.merge_text_rec(i, string)
                    self.children[head].append(i)
                return
        for i in self.children[cur]:
            self.merge_text_rec(i, string)
    
    def __str__(self):
        return self.draw().strip()