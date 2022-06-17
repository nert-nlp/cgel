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
        if constituent and '_' in constituent and len(constituent.split('_')[1]) == 1:
            self.constituent, self.label = constituent.split('_')
        elif constituent and ' / ' in constituent:
            self.label, self.constituent = constituent.split(' / ')
        else:
            self.constituent = constituent
            self.label = None
        self.text = text
        self.head = head
    
    def __str__(self):
        cons = (f'{self.label} / ' if self.label else '') + self.constituent
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
        self.projections = {}
    
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
        self._prune_rec(self.get_root(), string)
    
    def _prune_rec(self, cur, string):
        removal = []
        for i in self.children[cur]:
            if self._prune_rec(i, string):
                removal.append(i)
        if self.tokens[cur].deprel:
            if string in self.tokens[cur].deprel and len(self.children[cur]) == 0:
                return True
        for i in removal:
            self.children[cur].remove(i)

    def merge_text(self, string):
        self._merge_text_rec(self.get_root(), string)

    def _merge_text_rec(self, cur, string):
        if self.tokens[cur].deprel:
            if string in self.tokens[cur].deprel:
                head = self.tokens[cur].head
                self.tokens[head].text = self.tokens[cur].constituent
                self.children[head].remove(cur)
                for i in self.children[cur]:
                    self._merge_text_rec(i, string)
                    self.children[head].append(i)
                return
        for i in self.children[cur]:
            self._merge_text_rec(i, string)

    def _get_projections(self, cur, d=0):
        print(cur, (' ' * d), self.tokens[cur])
        res = None
        for i in self.children[cur]:
            if (self.tokens[i].deprel != 'Head' and 'Head' in self.tokens[i].deprel) or self.tokens[i].deprel == 'Coordinate':
                res = self._get_projections(i, d + 1)
                break
        if not res:
            for i in self.children[cur]:
                if self.tokens[i].deprel == 'Head':
                    res = self._get_projections(i, d + 1)
                    break
        if (not self.children[cur]) and self.tokens[cur].text:
            res = cur
        self.projections[cur] = str(res)
        for i in self.children[cur]:
            if 'Head' not in self.tokens[i].deprel:
                self._get_projections(i, d + 1)
                self.projections[self.projections[i]] = str(res)
        return res

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
    TERMINAL = 7

def parse(s):
    s = s.replace('\n', ' ')
    
    tokens = []
    token = ""
    status = State.NODE
    for char in s:
        if char == ':' and status in [State.NODE, State.NONE]:
            token = token.strip()
            if token:
                if token[0] == '(':
                    tokens.append(('(', State.OPEN_PAREN))
                    tokens.append((token[1:], status))
                elif token[0] == '"':
                    tokens.append((token[1:-1], State.TEXT))
                else:
                    tokens.append((token, State.TERMINAL))
            token = ''
            status = State.EDGE
        elif char == ')' and status in [State.NODE, State.NONE]:
            token = token.strip()
            if token:
                if token[0] == '(':
                    tokens.append(('(', State.OPEN_PAREN))
                    tokens.append((token[1:], status))
                elif token[0] == '"':
                    tokens.append((token[1:-1], State.TEXT))
                else:
                    tokens.append((token, State.TERMINAL))
            tokens.append((')', State.CLOSE_PAREN))
            token = ''
            status = State.NODE
        elif char == ' ' and status in [State.EDGE]:
            tokens.append((token.strip(), status))
            token = ''
            token += char
            status = State.NODE
        elif char == '"' and status in [State.EDGE, State.NODE]:
            if token.strip(): tokens.append((token.strip(), status))
            token = ''
            status = State.TEXT
        elif char == '"' and status in [State.TEXT]:
            if token.strip(): tokens.append((token.strip(), status))
            token = ''
            status = State.NODE
        elif status in [State.NODE, State.EDGE, State.TEXT, State.TERMINAL]:
            token += char
            
    res = []
    result = None
    stack = []
    count = 0
    edge = None
    d = 0
    for token, state in tokens:
        # if state in [State.NODE, State.TERMINAL, State.TEXT]: print(state, token, stack)
        # else: print(state, stack)
        if state == State.OPEN_PAREN:
            d += 1
        elif state == State.NODE:
            assert len(stack) == d - 1
            if stack: result.add_token(None, edge, token, count, stack[-1][1])
            else:
                if result: res.append(result)
                result = Tree()
                count = 0
                result.add_token(None, '', token, count, -1)
            stack.append((token, count))
            count += 1
        elif state == State.EDGE:
            edge = token
        elif state == State.TERMINAL:
            result.add_token(None, edge, token, count, stack[-1][1])
            count += 1
        elif state == State.TEXT:
            result.add_token(token, None, None, count, stack[-1][1])
            count += 1
        elif state == State.CLOSE_PAREN:
            d -= 1
            stack.pop()
            
    if result: res.append(result)
    return res