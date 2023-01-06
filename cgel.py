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
from pylatexenc.latexencode import unicode_to_latex

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

def texquote(s):
    return unicode_to_latex(s).replace(',', '{,}')  # forest package doesn't like unescaped commas in terminals for some reason

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
        """
        Lemma (canonical form) of the intended/correct word.
        If there is an explicit lemma specified with :l, use that.
        Otherwise, if there is an explicit correction with :correct, use that;
        else default to the surface form.
        If the correction is a deletion (:correct ""), the lemma defaults to None.
        """
        return self._lemma or self.correct or (self.text if self.correct!="" else None)

    @lemma.setter
    def lemma(self, lem):
        self._lemma = lem

    @property
    def isMod(self):
        return self.deprel in ('Mod', 'Mod_ext')

    @property
    def isSupp(self):
        return self.deprel in ('Supplement', 'Vocative')

    def __str__(self):
        cons = (f'{self.label} / ' if self.label else '') + self.constituent
        correction = f' :correct {quote(self.correct)}' if self.correct is not None else ''    # includes omitted words with no text
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

    def ptb(self, gap_token_symbol='_.'):
        s = f'({self.constituent.replace("_","")}'
        if self.label:
            s += f'.{self.label}'
        if self.deprel:
            s += f'-{self.deprel.replace("-","")}'

        if self.correct or self.text:
            s += f' {(self.correct or self.text).replace(" ","++")}'
        elif self.constituent=='GAP':
            s += f' {gap_token_symbol}'
        return s

    def tex(self):
        """Produce LaTeX for just the syntactically important parts of the tree (no lemmas, punctuation, or subtokens)"""
        cons = self.constituent
        if '_' in cons:
            x, y = cons.split('_')
            cons = x + '\\textsubscript{' + y + '}'
        if self.label:
            cons += '\\idx{' + texquote(self.label) + '}'
        correction = f' ({texquote(self.correct)})' if self.correct is not None else ''    # includes omitted words with no text
        suffix = r' \hlgreen{\Info}' if self.note else ''

        if self.deprel:
            d = self.deprel
            if '_' in d:
                x, y = d.split('_')
                d = x + '\\textsubscript{' + y + '}'
            s = '[\\Node{' + d + '}{' + cons + '}' + suffix
            if self.text:
                s += f'[{texquote(self.text)}{correction}]'
            elif self.constituent=='GAP':
                s += f'[--{correction}]'
        else:
            assert not self.text
            s = f'[{cons}' + suffix
        return s

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
        if token is not None:
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
                pass
            elif node.label:
                self.labels[node.label] = i

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

    def leaves(self):
        return [t for i,t in sorted(self.tokens.items()) if not self.children.get(i)]

    def draw_rec(self, head, depth):
        result = ""
        result += '    ' * depth + str(self.tokens[head])
        if self.tokens[head].constituent != 'GAP':
            for i in self.children[head]:
                result += '\n' + self.draw_rec(i, depth + 1)
        result += ')'
        return result

    def draw(self, include_metadata=False):
        """Generate PENMAN-notation string representation of the tree."""
        result = ''
        if include_metadata:
            for k, v in self.metadata.items():
                    result += f'# {k} = {v}\n'
        return result + self.draw_rec(self.get_root(), 0)

    def ptb_rec(self, head, depth):
        result = self.tokens[head].ptb()
        if self.tokens[head].constituent != 'GAP':
            for i in self.children[head]:
                result += ' ' + self.ptb_rec(i, depth + 1)
        result += ')'
        return result

    def ptb(self, include_metadata=False):
        """Generate PTB-style, single-line bracketed representation of the tree."""
        return self.ptb_rec(self.get_root(), 0)

    def tagging(self, gap_symbol=GAP_SYMBOL, complex_lexeme_separator="++"):
        """Generate string representation of tagged terminals."""
        return ' '.join(f'{gap_symbol if t.constituent == "GAP" else (t.correct or t.text).replace(" ",complex_lexeme_separator)}/{t.constituent.replace("_","")}{t.label and ("."+t.label) or ""}' for t in self.leaves())

    def drawtex_rec(self, head, depth):
        n = self.tokens[head]
        result = ""
        result += '    ' * depth + n.tex()
        if n.deprel.endswith('-Head') or n.deprel.startswith('Head-'):
            # omit the "natural" edge as we will draw both incoming edges specially
            result += ', no edge'
        if self.tokens[head].constituent != 'GAP':
            cc = self.children[head]
            assert n.text or cc,'Empty nonterminal due to old-style fusion: '+self.draw_rec(head,0)
            if any(self.tokens[c].deprel.startswith('Head-') or self.tokens[c].deprel.endswith('-Head') for c in cc):
                # this is an intermediate node--shift to the right; its first child has the fused functions
                amt = '1.5em' if len(cc)==1 else '4em'    # need more space if there are other children
                result += ', before drawing tree={x+=' + amt + '}'

            for i in cc:
                result += '\n' + self.drawtex_rec(i, depth + 1)
        result += ']'
        if n.deprel.endswith('-Head') or n.deprel.startswith('Head-'):
            # draw both incoming edges
            result += ' { \draw[-] (!uu.south) -- (); \draw[-] (!u.south) -- (); }'
        return result

    def drawtex(self):
        BEFORE = r'''
        \begin{forest}
        where n children=0{% for each terminal node
            font=\itshape, 			% italics
            tier=word          			% align at the "word" tier (bottom)
          }{%								% no false conditions, so empty
          },
        '''
        AFTER = r'''
        \end{forest}
        '''
        return BEFORE + self.drawtex_rec(self.get_root(), 0) + AFTER

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
        # base case: is text or is a gap
        if self.tokens[cur].text:
            return [[cur, self.tokens[cur].deprel + ':' + self.tokens[cur].constituent]]
        if self.tokens[cur].constituent == 'GAP':
            assert self.tokens[cur].label
            trg = self.labels[self.tokens[cur].label]
            x = self._get_heads(trg)
            return [[x[0][0], self.tokens[cur].deprel + ':' + self.tokens[trg].constituent]]

        desc = []
        for i in self.children[cur]:
            add = self._get_heads(i)
            if add[0][0]: desc.extend(add)
        desc.sort(key=lambda x: x[0])

        # find the "true" head, i.e. prioritise fused heads
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

        # set heads of all non-head children to be their chosen head sibling
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
                    break
            else:   # no head found; could be Flat
                break
        return self.tokens[j].lemma

    def validate(self) -> int:
        """Validate properties of the tree. Returns number of non-fatal warnings/notices."""

        global nWarn

        # Fused functions
        FUSED = ('Det-Head','Head-Prenucleus','Mod-Head','Marker-Head')

        # Lexical categories that project phrases vs. ones that don't
        LEX_projecting = {'N': 'Nom', 'N_pro': 'Nom', 'V': 'VP', 'V_aux': 'VP',
            'D': 'DP', 'P': 'PP', 'Adj': 'AdjP', 'Adv': 'AdvP', 'Int': 'IntP'}
        LEX_nonprojecting = {'Sdr', 'Coordinator'}
        LEX = LEX_projecting.keys() | LEX_nonprojecting

        FIXED_EXPRS = {
            'D': {'a few', 'a little', 'many a', 'no one'},
            'P': {'in order', 'so long as'}
        }

        VP_CORE_INT_DEPS = {'Obj', 'Obj_dir', 'Obj_ind', 'DisplacedSubj', 'Particle', 'PredComp'}
        VP_INT_DEPS = VP_CORE_INT_DEPS | {'Comp'}
        # ExtraposedSubj, ExtraposedObj go in a separate VP layer from other complements

        # Category names
        RE_CAT = r'^[A-Z]([A-Za-z_]*)(\+[A-Z][A-Za-z_]*)*(-Coordination)?$'
        for node in self.tokens.values():
            assert re.match(RE_CAT, node.constituent),f'Invalid category name: {node.constituent!r}'
            if node.text and ' ' in node.text and node.text not in FIXED_EXPRS.get(node.constituent,()):
                eprint(f'Unregistered complex fixed {node.constituent} lexeme: {node.text}')

        # Invalid rules
        for p, cc in self.children.items():
            if p == -1: continue  # root

            par = self.tokens[p]

            children = [self.tokens[c] for c in cc]
            cc_non_supp = [c for c in cc if not self.tokens[c].isSupp]

            # Heads
            if par.constituent not in ('Coordination','MultiSentence') and '+' not in par.constituent and cc:   # don't count terminals
                headFxns = [x.deprel for x in children if x.deprel=='Head' or '-Head' in x.deprel]  # excludes Head-Prenucleus because there the Head part isn't local
                if len(headFxns) != 1 and not all(x.deprel in {'Flat','Compounding'} for x in children):
                    if len(headFxns)==0 and len(children)==1 and children[0].constituent=='Clause_rel' and children[0].deprel=='Mod':
                        # outer Clause_rel of fused relative - will be checked below
                        pass
                    else:
                        eprint(f'{par.constituent} has {"zero" if len(headFxns) == 0 else "multiple"} heads {headFxns} (incorrect handling of fusion?) in sentence {self.sentid}')

            for c,ch in zip(cc,children):

                assert not any(x in ch.deprel.lower() for x in {'subject','object','modifier','determiner'}),f'"{ch.deprel}" should be abbreviated'

                if ch.constituent in LEX:
                    assert ch.deprel!='Coordinate','Coordinates must be phrases\n'+self.draw_rec(p,0)

                if ch.deprel=='Flat':
                    assert par.constituent in LEX,'Flat must be sublexical\n'+self.draw_rec(p,0)

                c_d = (par.constituent,ch.deprel)

                # Nonce-constituents
                if '+' in ch.constituent:
                    if ch.deprel=='Head':
                        assert par.constituent==ch.constituent,self.draw_rec(p,0)
                    elif not (ch.deprel=='Coordinate' and par.constituent=='Coordination'): # '+' in par.deprel and
                        eprint(f'Unexpected context for {ch.constituent} in sentence {self.sentid}')

                # N, Nom, D, DP, V, P, PP
                if ch.constituent in ('N', 'N_pro'):
                    assert c_d in {('Nom','Head'), ('N', 'Flat')},self.draw_rec(p,0)
                    if ch.deprel=='Head':
                        #assert all(self.tokens[x].deprel=='Comp' for x in cc if x!=c),'MISSING Nom?\n' + self.draw_rec(p,0)
                        if len(cc)==1 and par.head>=0 and self.tokens[par.head].constituent not in ('NP','Coordination') and self.tokens[par.head].deprel!='Coordinate':
                            # check that it's not a superfluous layer
                            assert any(self.tokens[x].deprel in ('Mod','Det') for x in self.children[par.head]),'SUPERFLUOUS Nom?\n'+self.draw_rec(p,0)
                elif ch.constituent=='Nom':
                    assert c_d in {('Nom','Head'), ('Nom','Mod'), ('NP','Head'), ('Coordination','Coordinate')},self.draw_rec(p,0)
                elif ch.constituent=='V':
                    assert c_d in {('VP','Head')},self.draw_rec(p,0)
                elif ch.constituent=='V_aux':
                    assert c_d in {('VP','Head'), ('Clause','Prenucleus')},self.draw_rec(p,0)
                elif ch.constituent=='D':
                    assert c_d in {('DP','Head'), ('D','Flat')},self.draw_rec(p,0)
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
                            ('DP', 'Head'), # many more
                            ('Nom', 'Mod'), # the [Nom *many* women]
                            ('NP', 'Mod'),  # [NP all [NP my diagrams]] (external modifier)
                            ('AdvP', 'Mod'), # [DP [D a little]] easier
                            ('PP', 'Mod')   # all over
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
                        ('Clause_rel','Head-Prenucleus'), # [PP where] I come from
                        ('VP','Postnucleus'), ('AdjP','Postnucleus'),
                        ('Coordination','Coordinate'), ('Nom','Compounding')},repr(c_d)+'\n'+self.draw_rec(p,0)
                elif ch.constituent=='Coordinator':
                    assert ch.deprel.startswith('Marker'),self.draw_rec(p,0)
                    if par.head>=0 and not par.isSupp and self.tokens[par.head].constituent!='Coordination' and ch.deprel!='Marker-Head':
                        eprint(f'Coordinator in invalid context? "{ch.text}" in sentence {self.sentid}')
                elif ch.constituent=='Sdr':
                    assert ch.deprel=='Marker'
                    assert par.constituent in ('VP','Clause','Clause_rel'),self.draw_rec(p,0)
                    if ch.lemma=='to':
                        assert par.constituent=='VP',self.draw_rec(p,0)

                elif ch.constituent=='Clause':
                    assert c_d!=('Clause_rel', 'Head'),self.draw_rec(p,0)
                elif ch.constituent=='Clause_rel':
                    assert c_d!=('Clause', 'Head'),self.draw_rec(p,0)

                # VP, Clause_rel
                if ch.constituent=='VP':
                    if not ch.isSupp:
                        assert c_d in {('Clause','Head'), ('Clause_rel','Head'), ('Clause','Prenucleus'),
                            ('VP','Head'), ('Nom','Mod'), ('Nom','Mod-Head'), # "the following"
                            ('Coordination','Coordinate'), ('Nom','Compounding')},self.draw_rec(p,0)
                        if c_d==('Clause','Prenucleus'):
                            # unmodified V_aux should not project a VP
                            if len(self.children[c])>1:
                                # ...but this could be [VP V] in another inversion construction ("attached are...")
                                gc = self.children[c][0]
                                gch = self.tokens[gc]
                                assert gch.deprel=='Head' and gch.constituent=='V',self.draw_rec(p,0)
                        elif c_d==('VP','Head'):    # VP as head of VP
                            # Check that internal complements are not split unnecessarily into multiple VP layers
                            # (the only reason to do this is if they are separated linearly by a Mod)
                            daughterfxns = [self.tokens[x].deprel for x in cc if not self.tokens[x].isSupp]
                            siblingfxns = [self.tokens[x].deprel for x in self.children[c] if not self.tokens[x].isSupp]
                            assert not (set(daughterfxns)&VP_INT_DEPS and set(siblingfxns)&VP_INT_DEPS),self.draw_rec(p,0)
                        elif ch.deprel=='Mod':
                            assert any(x.deprel=='Head' for x in children[cc.index(c):]),'post-head modifier cannot be VP (should it be a Clause?)\n'+self.draw_rec(p,0)
                    if ch.deprel=='Comp':
                        eprint(f'VP should not be :Comp in {par.constituent} in sentence {self.sentid}')
                    elif ch.deprel=='Coordinate' and par.deprel=='Comp':
                        eprint(f'VP Coordination should not be :Comp in sentence {self.sentid}')
                elif ch.constituent=='V' and ch.deprel=='Prenucleus':
                    eprint(f'Prenucleus should be VP or V_aux, not {ch.constituent} in sentence {self.sentid} {self.metadata.get("alias","/").rsplit("/",1)[1]}')
                elif ch.constituent=='Clause_rel' and not ch.isSupp:
                    assert c_d in {('Nom','Mod'), ('PP','Mod'), ('AdjP','Mod'), ('AdvP','Mod'), ('Clause_rel','Head')},self.draw_rec(p,0)
                    handled = False
                    if c_d==('Nom','Mod') and cc_non_supp.index(c)==0:
                        assert len(cc_non_supp)==1
                        # ch is outer RC of a fused relative
                        # with a Head-Prenucleus and inner RC as Head
                        gc = self.children[c][0]
                        assert self.tokens[gc].deprel=='Head-Prenucleus'
                        handled = True

                    # The sister of the relative clause that heads its parent constituent is usually coindexed with the gap.
                    # However, CGELBank uses Clause_rel for two layers in many cases.
                    # - In a fused relative we want the sister of the inner Clause_rel.
                    # - In a subject WH-relative we want the sister of the inner Clause_rel.
                    # - In a that-relative we want the sister of the outer Clause_rel (the inner one incorporates the Marker).
                    # - In a bare relative, there is just one Clause_rel, so we want its sister.

                    # It-clefts are not handled yet (so far none in the data).

                    hasHigherRC = (c_d==('Clause_rel','Head'))
                    hasLowerRC = any(self.tokens[x].deprel=='Head' and self.tokens[x].constituent=='Clause_rel' for x in self.children[c])
                    hasLowerThatRC = False
                    if hasLowerRC:
                        gc = self.children[c][0]
                        gch = self.tokens[gc]
                        if gch.constituent=='Sdr':
                            assert gch.deprel=='Marker'
                            hasLowerThatRC = True
                    assert not (hasLowerRC and hasHigherRC),self.draw_rec(c,0)

                    isister = cc_non_supp[cc_non_supp.index(c)-1]
                    sister = self.tokens[isister]
                    if sister.constituent=='Sdr':
                        assert sister.lemma in ('that','for'),(self.sentid, self.draw_rec(isister,0))
                        assert sister.deprel=='Marker'
                        handled = True
                    elif (not hasLowerRC) or hasLowerThatRC:
                        assert not handled

                        if hasHigherRC:
                            assert 'Prenucleus' in sister.deprel,self.draw_rec(isister,0)
                        else:
                            assert 'Head' in sister.deprel
                            assert sister.constituent in ('N','N_pro','Nom','DP')

                        # sister is usually coindexed with the gap (exception: resumptive pronoun)
                        if sister.label is None:
                            eprint('RC head missing coindexation (if not resumptive pronoun)?', self.draw_rec(isister,0), 'in', self.sentid)
                        else:
                            assert f'({sister.label} / GAP)' in self.draw_rec(p,0),'Relative clause must have GAP:\n'+self.draw_rec(p,0)
                        handled = True
                    #assert handled, self.draw_rec(p,0)

                # Functions
                if ch.deprel in ('Obj','Obj_dir','Obj_ind','DisplacedSubj'):
                    assert ch.constituent in ('NP','GAP','Coordination'),self.draw_rec(p,0)
                    if par.constituent!='VP':
                        assert ch.deprel=='Obj'
                        assert par.constituent=='PP' or '+' in par.constituent or par.constituent=='AdjP' and '"worth"' in self.draw_rec(p,0),self.draw_rec(p,0)
                elif ch.deprel=='Subj':
                    assert ch.constituent in ('NP','Clause','GAP','Coordination')
                    assert par.constituent in ('Clause','Clause_rel') or ('+' in par.constituent and 'Clause' in par.constituent),self.draw_rec(p,0)
                elif ch.deprel in ('ExtraposedSubj','ExtraposedObj'):
                    assert ch.constituent in ('NP','Clause','GAP','Coordination')
                    assert par.constituent=='VP',self.draw_rec(p,0)
                    gpar = self.tokens[par.head]
                    # should be the outermost VP layer, and VP should be head of the clause
                    assert gpar.constituent in ('Clause','Clause_rel') and par.deprel=='Head'
                elif ch.deprel=='Particle':
                    assert ch.constituent=='PP'
                    assert par.constituent=='VP'
                elif ch.deprel=='PredComp':
                    assert ch.constituent!='AdvP'
                    assert par.constituent=='VP' or '+' in par.constituent or par.constituent=='PP' and self.tokens[cc[0]].lemma=='as',self.draw_rec(p,0)
                elif ch.deprel=='Marker':
                    assert ch.constituent in ('Coordinator','Sdr','DP'),self.draw_rec(p,0)  # DP for "both" (X and Y)
                elif ch.deprel=='Det':
                    assert ch.constituent in ('DP','NP') or ch.constituent=='PP' and '(P :t "about")' in self.draw_rec(c,0),self.draw_rec(p,0)
                elif ch.deprel in FUSED:
                    assert cc.index(c)==0
                    assert par.head>-1,self.draw_rec(p,0)
                    gpar = self.tokens[par.head]
                    ancestry = (gpar.constituent, par.deprel, par.constituent)
                    if ch.deprel=='Head-Prenucleus':
                        assert ancestry[0] in ('Nom', 'PP', 'AdjP', 'AdvP')
                        assert ancestry[1:] == ('Mod', 'Clause_rel'),self.draw_rec(p,0)
                        assert ch.constituent in ('NP', 'PP', 'AdjP', 'AdvP')
                        sib = self.tokens[cc[1]]
                        assert sib.deprel=='Head'
                        assert sib.constituent=='Clause_rel'
                    elif ch.deprel=='Det-Head':
                        assert ancestry == ('NP', 'Head', 'Nom'),self.draw_rec(p,0)
                        assert ch.constituent in ('DP','NP') # NP: e.g. "mine"
                    elif ch.deprel=='Mod-Head':
                        assert ancestry == ('Nom', 'Head', 'Nom'),self.draw_rec(p,0)
                        assert ch.constituent in ('AdjP', 'VP', 'PP')
                    elif ch.deprel=='Marker-Head':  # "etc."
                        assert ancestry == ('NP', 'Head', 'Nom')
                        assert ch.constituent=='Coordinator'
                        assert gpar.deprel=='Coordinate'
                        assert len(cc)==1   # no siblings

                # Any kind of pre/postnucleus should normally trigger a GAP
                if ch.deprel in ('Prenucleus', 'Head-Prenucleus', 'Postnucleus'):
                    if ch.label is None:
                        assert ch.constituent=='NP' and par.constituent!='Clause_rel',self.draw_rec(p,0)

                # Check that gap is not coindexed to an ancestor
                if ch.constituent=='GAP':
                    ancestor = par
                    while ancestor:
                        assert ancestor.label!=ch.label,self.draw_rec(p,0)
                        # if ch.label=='z':
                        #     eprint(ancestor.constituent, ancestor.label)
                        if ancestor.head == -1:
                            ancestor = None
                            break
                        # if ch.label=='z':
                        #     eprint(self.draw_rec(ancestor.head,0))
                        ancestor = self.tokens[ancestor.head]

                # Lexical Projection Principle
                if ch.constituent in LEX_projecting:
                    if ch.deprel=='Flat':
                        assert par.constituent==ch.constituent and ch.constituent in {'D','N'}
                    else:
                        # lexical item should project a phrasal category
                        if not (ch.deprel=='Head' and par.constituent==LEX_projecting[ch.constituent]):
                            if ch.deprel=='Prenucleus' and ch.constituent=='V_aux':
                                # exception: Clause :Prenucleus V_aux
                                pass
                            else:
                                eprint("LEXICAL PROJECTION FAILURE\n"+self.draw_rec(p,0))
                        # and that phrase MAY contain complements/modifiers (change from before)
                        # i.e. if the parent node is unary, there should not be a grandparent node of the same type
                        if len(cc_non_supp)==1:
                            gpar = self.tokens[par.head]
                            if par.constituent==gpar.constituent and ch.deprel==par.deprel=='Head' and gpar.deprel!='Coordinate':
                                eprint('Lexical node is too deep:', self.draw_rec(c,0))
                # # Lexical category cannot be Mod or sister to Mod
                # if ch.constituent in LEX and any(child.isMod for child in children):
                #     if ch.constituent=='V_aux' and ch.deprel=='Head' and par.constituent=='VP':
                #         # [VP [V_aux is] [AdvP not]] and similar are OK
                #         pass
                #     else:
                #         eprint(f'Lexical node {ch.constituent} "{ch.text}" should not be sister to :Mod in sentence {self.sentid}')

            # Coordinate structures (and MultiSentence)
            if par.constituent=='Coordination':
                for c in cc:
                    ch = self.tokens[c]
                    if ch.deprel=='Coordinate':
                        # could be unmarked or marked coordinate
                        dd = [d for d in self.children[c] if self.tokens[d].deprel not in ('Supplement','Vocative')]
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
            if len(cc_non_supp)>1 and p>=0:
                fxns = [self.tokens[c].deprel for c in cc_non_supp]
                if 'Mod' in fxns:
                    if (len(fxns)>2 or not set(fxns)&{'Head','Det-Head','Mod-Head'} and '+' not in par.constituent):
                        eprint(f':Mod dependent should only be sister to Head (not counting Supplements) in sentence {self.sentid}', fxns)
                    # else: # TODO
                    #     head, = [self.tokens[c] for c in cc if self.tokens[c].deprel=='Head']
                    #     assert head.constituent in ('NP','VP','AdjP','AdvP','PP'),self.draw_rec(p, 0)

            # Unary rules
            if len(cc_non_supp)==1 and p>=0:
                c = cc_non_supp[0]
                ch = self.tokens[c]
                assert c>=0 and p>=0,(p,cc_non_supp,ch.deprel)
                if 'Head' not in ch.deprel and ch.deprel!='Compounding': # X -> NonHead:Y
                    if self.tokens[self.children[c][0]].deprel.startswith('Head-'): # par.deprel=='Head' and
                        # fusion (first child of `ch` is :Head-Prenucleus, and the Head part of the function really belongs with `ch`)
                        pass
                    else:
                        eprint(f'Invalid unary rule - no head? {par.constituent} -> {ch.deprel}:{ch.constituent} in sentence {self.sentid}')
                elif ch.constituent==par.constituent: # X -> Head:X
                    assert ch.deprel=='Head'
                    if not self.tokens[self.children[c][0]].deprel.endswith('-Head'):   # if there is fusion, then `ch` is really binary
                        eprint(f'Invalid unary rule - superfluous? {par.constituent} -> {ch.deprel}:{ch.constituent} in sentence {self.sentid}')
                elif ch.constituent=='Coordination':    # e.g. X -> Head:Coordination
                    assert ch.deprel=='Head'
                    eprint(f'Invalid unary rule - Coordination? {par.constituent} -> {ch.deprel}:{ch.constituent} in sentence {self.sentid}')
                else:
                    assert ch.deprel in ('Compounding','Det-Head','Mod-Head','Marker-Head') or ch.constituent in LEX_projecting or (ch.constituent,par.constituent) in {('Nom','NP'),('VP','Clause'),('VP','Clause_rel')},self.draw_rec(p, 0)

            elif len(cc_non_supp)>2: # more-than-binary rules
                ch_non_supp = [ch for ch in children if not ch.isSupp]
                ch_deprels_non_supp = [ch.deprel for ch in ch_non_supp]
                if par.constituent=='Coordination':
                    assert set(ch_deprels_non_supp)=={'Coordinate'}
                elif par.constituent=='VP':
                    if not set(ch_deprels_non_supp)<=VP_INT_DEPS | {'Head'}:
                        eprint('Mixing of core and non-core VP-internal functions (e.g. Obj and Comp):', ch_deprels_non_supp)
                else:
                    assert set(ch_deprels_non_supp)=={'Flat'},self.draw_rec(p,0)

        # Coindexation variables (we already checked the sister of Clause_rel)
        idx2constits = defaultdict(set)
        for i,node in self.tokens.items():
            if node.label:
                idx2constits[node.label].add(node)
                if node.constituent not in ('GAP','V_aux') and node.constituent in LEX:
                    # exception: sister to a relative clause
                    siboffset = self.children[node.head].index(i)
                    rsister = self.tokens[self.children[node.head][siboffset+1]]
                    if rsister.constituent=='Clause_rel' and rsister.deprel=='Mod':
                        pass
                    else:
                        eprint(f'Error: Non-gap coindexed constituent must not be a lexical category other than V_aux ({node.constituent}): "{node.text}" in sentence {self.sentid}')
            elif node.constituent=='GAP':
                eprint(f'Error: There is a GAP with no coindexation variable in sentence {self.sentid}')
        for idx,constits in idx2constits.items():
            if len(constits)<2:
                eprint(f'Likely error: Variable {idx} appears only once in sentence {self.sentid}')
            elif len(constits)>=3 and not any(x.deprel=='Postnucleus' for x in constits):
                # Valid with Postnucleus for delayed right constituent coordination: officiate at --x or bless --x [same gender marriages]x
                eprint(f'Likely error: Variable {idx} appears {len(constits)} times in sentence {self.sentid} (note that if an overt relativizer is coindexed to a GAP, its antecedent is not)')
            if not any(n.constituent=='GAP' for n in constits):
                eprint(f'Error: Variable {idx} does not appear on any GAP in sentence {self.sentid}')

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
            tokens.append((token.strip(), status))  # Note: may be empty string if input was ""
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
