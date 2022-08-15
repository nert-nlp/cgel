#!/usr/bin/env python3
"""
Library for parsing and manipulating CGEL trees in machine-readable
format, exposing useful helper functions.

@author: Aryaman Arora (@aryamanarora)
"""

from collections import defaultdict
import re, sys
from enum import Enum
from typing import List

nWarn = 0
def eprint(*args, **kwargs):
    global nWarn
    print(*args, file=sys.stderr, **kwargs)
    nWarn += 1

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

        assert ln.startswith('#')
        headers.append(ln.strip())  # the first header line
        ln = next(f)
        while ln.startswith('#'):
            headers.append(ln.strip())  # subsequent headers
            ln = next(f)

        while ln and ln.strip():
            assert '\t' not in ln, f"Tree line shouldn't contain tab character: {ln!r}"
            assert ln[0] in (' ', '('), f"Tree line starts with invalid character: {ln!r}"
            tree_lines.append(ln)
            ln = next(f, None)  # None in case of no blank line at the end of a file

        tree_lines[-1] = tree_lines[-1][:-1]    # remove newline at end of tree
        try:
            tree, = parse(''.join(tree_lines))
        except Exception as ex:
            ex.args += tuple(headers)
            raise

        # parse headers
        metadata = {}
        for header in headers:
            assert re.match(r'^# (\w+) = ', header),f'Invalid header line: {header}'
            _, k, _, v = header.split(' ',3)
            metadata[k] = v

        tree.sentid, tree.sentnum = metadata['sent_id'], metadata['sent_num']
        tree.text, tree.sent = metadata['text'], metadata['sent']
        tree.metadata = metadata

        if check_format:
            t = ''.join(tree_lines)
            u = tree.draw()
            assert t==u,linediff(t,u) + '\n' + repr((t[-3:],u[-3:]))
        yield tree

def linediff(a: str, b: str) -> str:
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

def escape_str(s: str) -> str:  # for outputting a double-quoted string
    return s.replace('\\', '\\\\').replace('"', r'\"')

def quote(s):
    return '"' + escape_str(s) + '"'

def cgel_unquote(s):
    assert s[0]=='"',s
    s = s[1:]
    assert s[-1]=='"',s
    s = s[:-1]
    s = re.sub(r'[^"\\]|\"|\\', lambda m: m.group(0).replace('\\', '', 1), s)
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
        self.prepunct = []
        self.postpunct = []
        self.correct = None
        self.substrings = None
        self.note = None
        self._lemma = None  # UD lemma

        # coindexation nodes (i.e. gaps) should only hold a label
        if self.constituent:
            if len(self.constituent) == 1 and self.constituent.islower():
                self.label = self.constituent
                self.constituent = 'GAP'

    @property
    def lemma(self):
        return self._lemma or self.correct or self.text

    @lemma.setter
    def lemma(self, lem):
        self._lemma = lem

    def __str__(self):
        cons = (f'{self.label} / ' if self.label else '') + self.constituent
        correction = f' :correct {quote(self.correct)}' if self.correct else ''    # includes omitted words with no text
        lemma = f' :l {quote(self._lemma)}' if self._lemma else ''  # lemma explicitly different from the token form
        suffix = ' :note ' + quote(self.note) if self.note else ''
        if self.text:
            s = f':{self.deprel} ({cons}'
            for p in self.prepunct:
                s += ' :p ' + quote(p)
            s += f' :t {quote(self.text)}'
            if correction:
                s += correction
            if lemma:
                s += lemma
            if self.substrings:
                for k,v in self.substrings:
                    s += ' ' + k + ' ' + quote(v)
            for p in self.postpunct:
                s += ' :p ' + quote(p)
            return s + suffix
        elif self.deprel:
            return f':{self.deprel} ({cons}' + correction + lemma + suffix
        else:
            return f'({cons}' + correction + lemma + suffix

class Tree:
    def __init__(self):
        self.tokens = {}
        self.children = defaultdict(list)
        self.labels = {}
        self.heads = {}
        self.mapping = {}
        self.sentid = None
        self.sentnum = None
        self.text = None
        self.sent = None
        self.metadata = None

    def add_token(self, token: str, deprel: str, constituent: str, i: int, head: int):
        # print(token, deprel, constituent, i, head)
        if token:
            if token != GAP_SYMBOL:
                if deprel == 'correct':
                    self.tokens[head].correct = token
                elif deprel == 'l':
                    self.tokens[head].lemma = token
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

            # Don't actually unify the coindexed nodes.
            # They will remain separate constituents in the tree, but with
            # variables stored in the node's label.
            if node.constituent == 'GAP':
                if node.label in self.labels: pass #self.children[i].append(self.labels[node.label])
                else: self.labels[node.label] = i
            elif node.label:
                if node.label in self.labels: pass #self.children[self.labels[node.label]].append(i)
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

    def head_lemma(self, i) -> str:
        """Get the lemma of the Head word of this constituent"""
        j = i
        while self.children[j]:
            for c in self.children[j]:
                if self.tokens[c].deprel=='Head':
                    j = c
        return self.tokens[j].lemma

    def validate(self) -> int:
        """Validate properties of the tree. Returns number of non-fatal warnings/notices."""

        global nWarn

        # Fused functions
        FUSED = ('Det-Head','Head-Prenucleus','Mod-Head','Marker-Head')

        # Category names
        RE_CAT = r'^[A-Z]([A-Za-z_]*)(\+[A-Z][A-Za-z_]*)*(-Coordination)?$'
        for node in self.tokens.values():
            assert re.match(RE_CAT, node.constituent),f'Invalid category name: {node.constituent!r}'

        # Invalid rules
        for p,cc in self.children.items():
            if p==-1: continue  # root

            par = self.tokens[p]

            # Heads
            if par.constituent not in ('Coordination','MultiSentence','Flat') and '+' not in par.constituent and cc:   # don't count terminals
                headFxns = [self.tokens[c].deprel for c in cc if 'Head' in self.tokens[c].deprel]
                if len(headFxns)!=1:
                    if headFxns not in (['Det-Head','Head'], ['Mod-Head','Head'], ['Marker-Head','Head'], ['Head-Prenucleus','Head']):
                        if not (len(headFxns)==0 and par.deprel=='Head' and any(self.tokens[x].deprel in FUSED for x in self.children[par.head])): # a fused Head
                            eprint(par.constituent, 'has heads', headFxns,
                                self.draw_rec(p, 0), sep='\n')

            for c in cc:
                ch = self.tokens[c]

                assert ch.deprel not in {'Subject','Object','Modifier'},f'"{ch.deprel}" should be abbreviated'

                c_d = (par.constituent,ch.deprel)

                # N, Nom, D, DP, V, P, PP
                if ch.constituent in ('N', 'N_pro'):
                    assert c_d in {('Nom','Head'), ('Flat','Flat')},self.draw_rec(p,0)
                    if ch.deprel=='Head':   # mainly to forbid Nom -> Mod:* Head:N (should be Head:Nom)
                        assert all(self.tokens[x].deprel=='Comp' for x in cc if x!=c),'MISSING Nom?\n' + self.draw_rec(p,0)
                        if len(cc)==1 and par.head>=0 and self.tokens[par.head].constituent not in ('NP','Coordination') and self.tokens[par.head].deprel!='Coordinate':
                            # check that it's not a superfluous layer
                            assert any(self.tokens[x].deprel in ('Mod','Det') for x in self.children[par.head]),'SUPERFLUOUS Nom?\n'+self.draw_rec(p,0)
                elif ch.constituent=='Nom':
                    assert c_d in {('Nom','Head'), ('Nom','Mod'), ('NP','Head'), ('Coordination','Coordinate')},self.draw_rec(p,0)
                elif ch.constituent in ('V', 'V_aux'):
                    assert c_d in {('Clause','Prenucleus'), ('V','Head'), # TODO: maybe eliminate these options
                        ('VP','Head'), ('Coordination','Coordinate')},self.draw_rec(p,0)
                elif ch.constituent=='D':
                    assert c_d in {('DP','Head'), ('Flat','Flat')},self.draw_rec(p,0)
                elif ch.constituent=='DP':
                    if ch.deprel=='Marker':
                        # in coordination: "both old enough...and"
                        assert par.deprel=='Coordinate'
                    elif ch.deprel=='Mod' and par.constituent in ('AdjP','AdvP','VP') \
                        and any('Head' in self.tokens[x].deprel for x in cc[:cc.index(c)]):  # postmodifier
                            assert self.head_lemma(c)=='enough' # X enough
                    elif par.constituent=='AdjP':
                        # a little ADJ
                        assert ch.deprel=='Mod'
                    else:
                        assert c_d in {('NP','Det'), ('NP', 'Det-Head'), ('Nom','Det-Head'),
                            ('DP', 'Mod'), # many more
                            ('Nom', 'Mod'), # the [Nom *many* women]
                            ('NP', 'PreDetMod'),  # [NP all [NP my diagrams]] (external modifier)
                            ('AdvP','Mod'), # [DP [D a little]] easier
                        },self.draw_rec(p,0)
                elif ch.constituent=='P':
                    assert c_d in {('PP','Head'), ('PP','Mod')  # back out
                        },self.draw_rec(p,0)
                elif ch.constituent=='PP':
                    if ch.deprel!='Supplement' and 'PP+' not in par.constituent and '+PP' not in par.constituent \
                        and self.head_lemma(c)!='along': # TODO: revisit "along with"
                        assert c_d in {('Nom','Comp'), ('VP','Comp'), ('VP','Particle'), ('VP','PredComp'), ('AdjP','Comp'),
                        ('Nom','Mod'), ('VP','Mod'), ('AdjP','Mod'), ('AdjP','Comp_ind'), ('AdvP','Comp_ind'),
                        ('Nom','Mod-Head'), # the above
                        ('NP','Det'),   # [about 30] seconds
                        ('NP','Mod'),   # [at least] half
                        ('PP','Head'),   # [PP seconds [PP into his address]]
                        ('PP','Comp'),  # out of...
                        ('PP','Mod'),   # over to... (directional) TODO: revisit cf. "back out"
                        ('Clause','Prenucleus'), ('Clause_rel','Prenucleus'), ('Clause','Mod'),
                        ('VP','Postnucleus'), ('AdjP','Postnucleus'),
                        ('Coordination','Coordinate')},self.draw_rec(p,0)

                # VP, Clause_rel
                if ch.constituent=='VP':
                    if ch.deprel!='Supplement':
                        assert c_d in {('Clause','Head'), ('Clause_rel','Head'), ('Clause','Prenucleus'),
                            ('VP','Head'), ('Nom','Mod'), ('Nom','Mod-Head'), # "the following"
                            ('Coordination','Coordinate')},self.draw_rec(p,0)
                    if ch.deprel=='Comp':
                        eprint(f'VP should not be :Comp in {par.constituent} in sentence {self.sentid}')
                    elif ch.deprel=='Coordinate' and par.deprel=='Comp':
                        eprint(f'VP Coordination should not be :Comp in sentence {self.sentid}')
                elif ch.constituent in ('V', 'V_aux') and 'Prenucleus' in ch.deprel:
                    eprint(f'Prenucleus should be VP, not {ch.constituent} in sentence {self.sentid} {self.metadata.get("alias","/").rsplit("/",1)[1]}')
                elif ch.constituent=='Clause_rel' and ch.deprel!='Supplement':
                    assert par.constituent=='Nom',self.draw_rec(p,0)
                    assert ch.deprel=='Mod',self.draw_rec(p,0)
                    siblings = [i for i in cc if self.tokens[i].deprel!='Supplement']
                    assert siblings.index(c)>0,self.draw_rec(p,0)
                    isister = siblings[siblings.index(c)-1]
                    sister = self.tokens[isister]
                    assert sister.label and 'Head' in sister.deprel and (sister.constituent in ('Nom','DP') or sister.constituent=='NP' and sister.deprel=='Head-Prenucleus'),self.draw_rec(p,0)

            # Coordinate structures (and MultiSentence)
            if par.constituent=='Coordination':
                for c in cc:
                    ch = self.tokens[c]
                    if ch.deprel=='Coordinate':
                        # could be unmarked or marked coordinate
                        dd = [d for d in self.children[c] if self.tokens[d].deprel!='Supplement']
                        if len(dd)>0 and self.tokens[dd[0]].deprel=='Marker':
                            # Note that the Marker may be part of the coordination construction (Coordinator or D),
                            # or may be a Sdr in an unmarked coordinate (coordination of clauses).
                            # Either way, it should have a Head.
                            assert len(dd)==2,self.draw_rec(c, 0)
                            d0 = self.tokens[dd[0]]
                            d1 = self.tokens[dd[1]]
                            if d1.deprel!='Head' or d1.constituent!=ch.constituent:
                                eprint(f'Invalid coordination structure: {d1.deprel}:{d1.constituent} in {ch.constituent} in sentence {self.sentid}')
            elif par.constituent=='MultiSentence':
                assert all(self.tokens[c].deprel=='Coordinate' for c in cc)
            else:
                for c in cc:
                    ch = self.tokens[c]
                    if ch.deprel=='Coordinate':
                        eprint(f':Coordinate is invalid under {par.constituent} (parent must be Coordination or MultiSentence) in sentence {self.sentid}')
                    elif ch.deprel=='Head' and ch.constituent=='Coordination' and len(cc)==1:
                        # Coordination as unary head of an X should not be of X types
                        dd = [d for d in self.children[c] if self.tokens[d].deprel=='Coordinate']
                        ddcats = [self.tokens[d].constituent for d in dd]
                        if par.constituent in ddcats:
                            if c!=cc[0] and self.tokens[cc[cc.index(c)-1]].deprel=='Marker':    # TODO: obsolete by unary condition?
                                # (X :Marker M :Head (Coordination :Coordinate X ...))
                                # `par`              `ch`                     `d`
                                # M could be a coordinator or subordinator
                                pass
                            else:
                                eprint(f'Possibly invalid coordination structure: coordinates {" ".join(ddcats)} under Head of {par.constituent} in sentence {self.sentid}',
                                    self.draw_rec(p, 0), sep='\n')

            # :Mod dependents
            if len(cc)>1 and p>=0:
                fxns = [self.tokens[c].deprel for c in cc if self.tokens[c].deprel!='Supplement']
                if 'Mod' in fxns:
                    if (len(fxns)>2 or 'Head' not in fxns and '+' not in par.constituent):
                        eprint(f':Mod dependent should only be sister to :Head (not counting Supplements) in sentence {self.sentid}', fxns)
                    # else: # TODO
                    #     head, = [self.tokens[c] for c in cc if self.tokens[c].deprel=='Head']
                    #     assert head.constituent in ('NP','VP','AdjP','AdvP','PP'),self.draw_rec(p, 0)

            # Unary rules
            if len(cc)==1 and p>=0:
                c = cc[0]
                ch = self.tokens[c]
                assert c>=0 and p>=0,(p,cc,ch.deprel)
                if 'Head' not in ch.deprel or ch.constituent==par.constituent: # X -> NonHead:Y   or   X -> Head:X
                    eprint(f'Invalid unary rule? {par.constituent} -> {ch.deprel}:{ch.constituent} in sentence {self.sentid}')
                elif ch.constituent=='Coordination':    # e.g. X -> Head:Coordination
                    eprint(f'Invalid unary rule - Coordination? {par.constituent} -> {ch.deprel}:{ch.constituent} in sentence {self.sentid}')
                # elif ch.deprel==par.deprel=='Head' and ch.constituent!='Nom' and par.constituent==self.tokens[par.head].constituent!='Nom':
                #     assert False,self.draw_rec(p,0)

                # TODO: look for extra layers like [VP [VP eat] [NP lunch]]
                # [XP :Head [XP Y]], where the inner XP is unary, should not occur unless there is a :Mod sister in the outer XP? (+ maybe other thinks like :Prenucleus)

        # Coindexation variables (we already checked the Nom sister of Clause_rel)
        idx2constits = defaultdict(set)
        for node in self.tokens.values():
            if node.label:
                idx2constits[node.label].add(node)
            elif node.constituent=='GAP':
                eprint(f'Notice: There is a GAP with no coindexation variable in sentence {self.sentid} (should be rare)')
        for idx,constits in idx2constits.items():
            if len(constits)<2:
                eprint(f'Likely error: Variable {idx} appears only once in sentence {self.sentid}')
            elif len(constits)>3:
                eprint(f'Likely error: Variable {idx} appears {len(constits)} times in sentence {self.sentid}')
            if not any(n.constituent=='GAP' for n in constits):
                eprint(f'Likely error: Variable {idx} does not appear on any GAP in sentence {self.sentid}')

        return nWarn

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
    TEXT_ESCAPE = 8

def parse(s: str) -> List[Tree]:
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
        elif char == '(' and status == State.NODE and token.strip():
            raise Exception(f'Open paren not allowed after node "{token.strip()}" (missing edge?)')
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
        elif char == "\\" and status in [State.TEXT]:
            status = State.TEXT_ESCAPE
        elif status in [State.TEXT_ESCAPE]:
            assert char=='"' or char=='\\',f'Unrecognized backslash escape in string: ' + repr("\\"+char)
            token += char
            status = State.TEXT
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
            try:
                stack.pop()
            except IndexError:
                raise Exception('Mismatched brackets')

    if result: res.append(result)
    return res
