#!/usr/bin/env python3
"""
Library for parsing and manipulating CGEL trees in machine-readable
format, exposing useful helper functions.

@author: Aryaman Arora (@aryamanarora)
"""

from collections import defaultdict
import re
from enum import Enum

class Node:
    def __init__(self, deprel, constituent, head, text=None):
        self.deprel = deprel
        if constituent and '_' in constituent:
            self.constituent, self.label = constituent.split('_')
        else:
            self.constituent = constituent
            self.label = None
        self.text = text
        self.head = head
    
    def __str__(self):
        cons = self.constituent + (self.label if self.label else '')
        if self.text:
            return f':{self.deprel} ({cons} :t "{self.text}"'
        elif self.deprel:
            return f':{self.deprel} ({cons}'
        else:
            return f'({cons}'

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

    def to_conllu(self) -> str:
        result = ""
        count = 1
        for key, token in dict(sorted(self.tokens.items())).items():
            if token.text and token.constituent != 'GAP':
                result += '\t'.join([str(count), token.text, '_', token.constituent, '_', '_', '_', '_', '_', '_']) + '\n'
                count += 1
        return result
    
    def __str__(self):
        return self.draw().strip()

class State(Enum):
    NONE = 0
    NODE = 1
    EDGE = 2
    PROPERTY = 3
    TEXT = 4
    OPEN_PAREN = 5
    CLOSE_PAREN = 6

def parse(s):
    s = s.replace('\n', ' ')
    
    tokens = []
    token = ""
    status = State.NONE
    for char in s:
        if char == '(' and status in [State.NONE, State.EDGE]:
            if token: tokens.append((token.strip(), status))
            tokens.append(('(', State.OPEN_PAREN))
            token = ''
            status = State.NODE
        elif char == ':' and status in [State.NODE, State.NONE]:
            tokens.append((token.strip(), status))
            token = ''
            status = State.EDGE
        elif char == '"' and status in [State.EDGE]:
            tokens.append((token.strip(), status))
            token = ''
            status = State.TEXT
        elif char == '"' and status in [State.TEXT]:
            tokens.append((token.strip(), status))
            token = ''
            status = State.NONE
        elif char == ')' and status in [State.NODE, State.NONE]:
            if status == State.NODE: tokens.append((token.strip(), status))
            tokens.append((')', State.CLOSE_PAREN))
            token = ''
            status = State.NONE
        elif status in [State.NODE, State.EDGE, State.TEXT]:
            token += char
            
    res = []
    result = None
    stack = []
    count = 0
    edge = None
    d = 0
    for token, state in tokens:
        if state == State.OPEN_PAREN:
            d += 1
        elif state == State.NODE:
            assert len(stack) == d - 1
            if stack: result.add_token(None, edge, token, count, stack[-1][1])
            else:
                if result: res.append(result)
                result = Tree()
                result.add_token(None, '', token, count, -1)
            stack.append((token, count))
            count += 1
        elif state == State.EDGE:
            edge = token
        elif state == State.TEXT:
            result.add_token(token, None, None, count, stack[-1][1])
            count += 1
        elif state == State.CLOSE_PAREN:
            d -= 1
            stack.pop()
    if result: res.append(result)
    return res