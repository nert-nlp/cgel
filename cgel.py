#!/usr/bin/env python3
"""
Library for parsing and manipulating CGEL trees in machine-readable
format, exposing useful helper functions.

@author: Aryaman Arora (@aryamanarora)
"""

from collections import defaultdict
import re
from enum import Enum

GAP_SYMBOL = '--'

def trees(f, check_format=False):
    """Given a file with trees and 2 lines of metadata each, iterate over trees."""
    while True:
        headers = []
        tree_lines = []
        try:
            ln = next(f)
            if not ln.strip():
                continue
        except StopIteration:
            return # reached the end

        headers.append(ln.strip())  # the sentence ID
        ln = next(f)
        headers.append(ln.strip())  # the sentence text

        while ln.strip():
            try:
                ln = next(f)
                if ln=='\n':
                    break
                assert '\t' not in ln, f"Tree line shouldn't contain tab character: {ln!r}"
                assert ln[0] in (' ', '('), f"Tree line starts with invalid character: {ln!r}"
                tree_lines.append(ln)
            except StopIteration:
                # In case of no blank line at the end of a file
                break
        tree_lines[-1] = tree_lines[-1][:-1]    # remove newline at end of tree
        tree, = parse(''.join(tree_lines))
        tree.sentid, tree.sent = headers
        if check_format:
            t = ''.join(tree_lines)
            u = tree.draw()
            assert t==u,linediff(t,u) + '\n' + repr((t[-3:],u[-3:]))
        yield tree

def linediff(a,b):
    """Given two strings, produce a string that shows a line-by-line comparison"""
    s = ''
    aa = a.splitlines()
    bb = b.splitlines()
    for i in range(len(aa)):
        aln = aa[i]
        if i<len(bb):
            bln = bb[i]
            if aln==bln:
                s += '= ' + aln + '\n'
            else:
                s += '< ' + aln + '\n' + '> ' + bln + '\n'
        else:
            s += '< ' + aln + '\n'
    if len(bb)>len(aa):
        for i in range(len(aa),len(bb)):
            s += '> ' + bb[i] + '\n'
    return s

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
        self.prepunct = ()
        self.postpunct = ()
        self.correct = None
        self.substrings = None
        self.note = None

        # coindexation nodes (i.e. gaps) should only hold a label
        if self.constituent:
            if len(self.constituent) == 1 and self.constituent.islower():
                self.label = self.constituent
                self.constituent = 'GAP'

    def __str__(self):
        cons = (f'{self.label} / ' if self.label else '') + self.constituent
        correction = f' :correct "{self.correct}"' if self.correct else ''    # includes omitted words with no text
        suffix = ' :note "' + self.note.replace('"', r'\"') + '"' if self.note else ''
        if self.text:
            s = f':{self.deprel} ({cons}'
            for p in self.prepunct:
                s += ' :p "' + p.replace('"', r'\"') + '"'
            s += f' :t "{self.text}"'
            for p in self.postpunct:
                s += ' :p "' + p.replace('"', r'\"') + '"'
            if correction:
                s += correction
            if self.substrings:
                for k,v in self.substrings:
                    s += ' ' + k + ' "' + v.replace('"', r'\"') + '"'
            return s + suffix
        elif self.deprel:
            return f':{self.deprel} ({cons}' + correction + suffix
        else:
            return f'({cons}' + correction + suffix

class Tree:
    def __init__(self):
        self.tokens = {}
        self.children = defaultdict(list)
        self.labels = {}
        self.heads = {}
        self.mapping = {}
        self.sentid = None
        self.sent = None

    def add_token(self, token: str, deprel: str, constituent: str, i: int, head: int):
        # print(token, deprel, constituent, i, head)
        if token:
            if token != GAP_SYMBOL:
                if deprel == 'correct':
                    self.tokens[head].correct = token
                elif deprel == 'subt':
                    self.tokens[head].substrings = (self.tokens[head].substrings or []) + [(':subt', token)]
                elif deprel == 'subp':
                    self.tokens[head].substrings = (self.tokens[head].substrings or []) + [(':subp', token)]
                elif deprel == 'p':
                    if self.tokens[head].text:
                        self.tokens[head].postpunct += (token,)
                    else:
                        self.tokens[head].prepunct += (token,)
                elif deprel == 'note':
                    self.tokens[head].note = token
                else:
                    self.tokens[head].text = token
        else:
            node = Node(deprel, constituent, head)

            if node.constituent == 'GAP':
                if node.label in self.labels: self.children[i].append(self.labels[node.label])
                else: self.labels[node.label] = i
            elif node.label:
                if node.label in self.labels: self.children[self.labels[node.label]].append(i)
                else: self.labels[node.label] = i

            self.tokens[i] = node
            self.children[head].append(i)

    def _mapping(self):
        count = 1
        for i in sorted(self.tokens.keys()):
            if self.tokens[i].text:
                self.mapping[i] = count
                count += 1

    def get_root(self):
        root = 0
        while self.tokens[root].head >= 0:
            root = self.tokens[root].head
        return root

    def draw_rec(self, head, depth):
        result = ""
        result += '    ' * depth + str(self.tokens[head])
        if self.tokens[head].constituent != 'GAP':
            for i in self.children[head]:
                result += '\n' + self.draw_rec(i, depth + 1)
        result += ')'
        return result

    def draw(self):
        return self.draw_rec(self.get_root(), 0)

    def sentence(self, gaps=False):
        return ' '.join(self.sentence_rec(self.get_root(), gaps=gaps))

    def sentence_rec(self, cur, gaps=False):
        result = []
        if self.tokens[cur].text:
            result.append(self.tokens[cur].text)
        if self.tokens[cur].constituent != 'GAP':
            for i in self.children[cur]:
                result.extend(self.sentence_rec(i, gaps=gaps))
        elif gaps:
            result.append(GAP_SYMBOL)
        return result

    def prune(self, string):
        self._prune_rec(self.get_root(), string)

    def _prune_rec(self, cur, string):
        removal = []
        if self.tokens[cur].constituent != 'GAP':
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
                if self.tokens[cur].constituent != 'GAP':
                    for i in self.children[cur]:
                        self._merge_text_rec(i, string)
                        self.children[head].append(i)
                return
        if self.tokens[cur].constituent != 'GAP':
            for i in self.children[cur]:
                self._merge_text_rec(i, string)

    def to_conllu(self) -> str:
        self.get_heads()
        result = ""
        for key, token in dict(sorted(self.tokens.items())).items():
            if token.text and token.constituent != 'GAP':
                head, deprel = self.heads[key]
                head = self.mapping.get(head, 0)
                result += '\t'.join(map(str, [self.mapping[key], token.text, '_', token.constituent, '_', '_', head, deprel, '_', '_'])) + '\n'
        return result

    def get_heads(self):
        self._mapping()
        x = self._get_heads(self.get_root())[0]
        self.heads[x[0]] = (0, 'Root' + x[1])

    def _get_heads(self, cur):
        if self.tokens[cur].text:
            return [[cur, self.tokens[cur].deprel + ':' + self.tokens[cur].constituent]]
        if self.tokens[cur].constituent == 'GAP':
            trg = self.children[cur][0]
            x = self._get_heads(trg)
            return [[x[0][0], self.tokens[cur].deprel + ':' + self.tokens[trg].constituent]]

        desc = []
        for i in self.children[cur]:
            add = self._get_heads(i)
            if add[0][0]: desc.extend(add)
        desc.sort(key=lambda x: x[0])

        true_head = None
        for child, deprel in desc:
            if 'Head' in deprel and deprel != 'Head':
                true_head = child
                break
        if not true_head:
            for child, deprel in desc:
                if 'Head' in deprel:
                    true_head = child
                    break
        # non-headed relations -> pick the first one as head
        if not true_head:
            for child, deprel in desc:
                if deprel.split(':')[0] in ['Coordinate', 'Sentence', 'Flat']:
                    true_head = child
                    break
        if not true_head and len(desc) == 1:
            true_head = desc[0][0]

        for child, deprel in desc:
            if child != true_head:
                self.heads[child] = (true_head, deprel)

        return [[true_head, self.tokens[cur].deprel + ':' + self.tokens[cur].constituent]]

    def validate(self):
        """Validate properties of the tree"""
        RE_CAT = r'^[A-Z]([A-Za-z]*)(\+[A-Z][A-Za-z]*)*(-Coordination)?$'
        for node in self.tokens.values():
            assert re.match(RE_CAT, node.constituent),f'Invalid category name: {node.constituent!r}'

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
    """Parse the given string into trees."""
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
            result.add_token(token, edge, None, count, stack[-1][1])
            count += 1
        elif state == State.CLOSE_PAREN:
            d -= 1
            stack.pop()

    if result: res.append(result)
    return res
