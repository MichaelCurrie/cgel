"""Universal Dependencies (CoNLL-U) -> CGEL constituency trees.

DepEdit rewrites UD relations into CGEL functions using the rule file shipped at
``data/ud-to-cgel.ini``; `project_categories` then inserts the unary projections
CGEL requires but dependency syntax leaves implicit (N -> Nom -> NP, V -> VP ->
Clause, and so on).

Adapted from the CGELBank repository's top-level ``ud2cgel.py``. Differences:

* the DepEdit rule file is resolved inside the package rather than by the
  relative path ``convertor/ud-to-cgel.ini``, so the caller's working directory
  no longer matters;
* the corpus-specific ``main()``/``combine_conllus()`` drivers, which hard-coded
  ``datasets/*`` paths, are gone;
* progress output goes to stderr so stdout stays reserved for JSON;
* the root token is given the empty deprel ``''`` rather than ``None`` -- see
  ``ROOT_DEPREL`` below.
"""

from __future__ import annotations

import copy
from collections import defaultdict
from pathlib import Path
from typing import List

import conllu
from conllu import Token, TokenList, TokenTree
from depedit import DepEdit

from . import constituent
from .cgel import Tree
from .io_utils import log, open_read, open_write
from .resources import DEPEDIT_CONFIG_PATH

#: Function label for the tree root.
#:
#: The PENMAN reader in ``cgel.py`` gives a root node the empty string, and
#: ``Tree.add_token`` asserts ``deprel is not None``. The upstream script passed
#: ``None`` here, which trips that assertion; ``''`` both satisfies it and makes
#: a converted tree indistinguishable from a parsed one.
ROOT_DEPREL = ''


def token_tree_to_list(tree: TokenTree) -> TokenList:
    """Flatten a CoNLL-U tree back into a token list, renumbering ids and heads."""
    def flatten_tree(root_token: TokenTree, token_list: List[Token] = [], head: int = 0) -> List[Token]:
        root_token.token['id'] = len(token_list) + 1
        root_token.token['head'] = head
        head = len(token_list) + 1
        token_list.append(root_token.token)

        for child_token in root_token.children:
            flatten_tree(child_token, token_list, head)

        return token_list

    tokens = flatten_tree(tree)
    token_list = TokenList(tokens, tree.metadata)
    return token_list


def convert(infile: str | Path, resfile: str | Path | None, outfile: str | Path,
            config_path: str | Path = DEPEDIT_CONFIG_PATH) -> Path:
    """Convert a UD treebank to CGEL.

    Args:
        infile: UD source file in CoNLL-U format.
        resfile: Where to write the conversion-coverage report; None to skip it.
        outfile: Output *prefix*; ``.cgel`` and ``.conllu`` are appended to it.
        config_path: DepEdit rule file. Defaults to the packaged UD->CGEL rules.

    Returns:
        Path of the written ``.cgel`` file.
    """
    infile, outfile = Path(infile), Path(outfile)
    # Append rather than with_suffix(): a prefix like `out.v2` must become
    # `out.v2.cgel`, not `out.cgel`.
    cgel_out = outfile.with_name(outfile.name + '.cgel')
    conllu_out = outfile.with_name(outfile.name + '.conllu')

    log('Getting files...')
    with open_read(infile) as inF, open_read(config_path) as config_file:
        d = DepEdit(config_file)

        log('Running depedit...')
        result = d.run_depedit(inF)

    log('Done with depedit.')
    types: defaultdict[str, int] = defaultdict(int)
    pos: defaultdict[str, int] = defaultdict(int)

    sent = [0, 0, 0]
    tok = [0, 0]

    # create projected constituents recursively
    def project_categories(node):
        upos, _form, deprel = node.token['upos'], node.token['form'], node.token['deprel']

        if deprel == 'Clause':
            rel, pos = 'Root', 'Clause'
        elif ':' in deprel:
            rel, pos = deprel.split(':')
        else:
            rel, pos = deprel, upos

        # collect all the new projected categories for reference
        projected = {}

        # keep track of child to control
        last = node
        orig_node = copy.deepcopy(node)
        status = True
        if upos in constituent.projections:

            # go through all projected categories
            if upos != pos:
                for r, level in enumerate(constituent.projections[upos]):

                    # make new node
                    head = copy.deepcopy(orig_node)
                    head.token['form'] = '_'
                    head.token['upos'] = level
                    head.token['deprel'] = f'{rel}:{level}'
                    head.children = [last]
                    projected[level] = head

                    # deprel of child node must be Head
                    last.token['deprel'] = last.token['deprel'].replace(f'{rel}:', 'Head:')
                    last.token['head'] = head.token['id']
                    last = head

                    # if we reach last projected category, break
                    # its pos is simply what we stored in upos!
                    if level == pos:
                        node.token['deprel'] = node.token['deprel'].replace(f':{pos}', f':{upos}')
                        break

            # attach children
            remaining = []
            for i, child in enumerate(node.children):

                # figure out which level to attach the child on
                rel = child.token['deprel'].split(':')[0]
                level = constituent.level.get((rel, upos), None)
                result, status2 = project_categories(child)
                status = status and status2

                if level is not None and level in projected:
                    projected[level].children.append(result)
                    projected[level].children.sort(key=lambda x: x.token['id'])
                else:
                    remaining.append(result)

            last.children.extend(remaining)
            last.children.sort(key=lambda x: x.token['id'])
            node.children = []

        else:
            status = False
            for i, child in enumerate(node.children):
                node.children[i], _ = project_categories(child)

        return last, status

    # convert to constituency and write out CGEL trees
    log('Converting to constituency...')
    with open_write(cgel_out) as fout, open_write(conllu_out) as fout2:

        # get flattened CGEL trees (post-conversion)
        trees = conllu.parse(result)

        for i, sentence in enumerate(trees):

            # create the tree, project unary nodes
            tree = sentence.to_tree()
            fixed, status = project_categories(tree)
            if status:
                sent[2] += 1

            # convert to tokenlist, make cgel object
            orig = token_tree_to_list(fixed)
            fout2.write(orig.serialize())
            converted = Tree()
            converted.metadata = sentence.metadata
            converted.sentnum = converted.metadata['sent_num'] = i + 1
            converted.sent = converted.metadata['sent'] = ' '.join([str(token) for token in sentence if isinstance(token['id'], int)])

            # fix metadata
            keys = list(converted.metadata)
            for key in keys:
                if ' ' in key:
                    del converted.metadata[key]
            if 'sentid' not in converted.metadata:
                converted.metadata['sent_id'] = converted.sentnum
                converted.sentid = converted.sentnum
            if 'text' not in converted.metadata:
                converted.metadata['text'] = converted.sent
                converted.text = converted.sent

            # go through tokens and add to cgel
            complete = True
            words = []
            puncts: List[Token] = []
            for j, word in enumerate(orig):
                if not isinstance(word['id'], int):
                    continue
                word['id'] -= 1
                word['head'] -= 1

                # add token
                deprel: str = word['deprel'].split(':')[0]

                if deprel != 'Punct':
                    converted.add_token(
                        token=None,
                        deprel=deprel if deprel != 'Root' else ROOT_DEPREL,
                        constituent=word['upos'],
                        i=word['id'],
                        head=word['head']
                    )
                    # add text if it is there
                    if word['form'] != "_":

                        # clear punctuation buffer
                        for punct in puncts:
                            converted.add_token(punct['form'], 'p', None, punct['id'], word['id'])
                        puncts = []

                        # form, lemma
                        converted.add_token(word['form'], None, None, word['id'], word['id'])
                        if word['lemma'] != word['form']:
                            converted.add_token(word['lemma'], 'l', None, word['id'], word['id'])
                        words.append(word['id'])

                # add punctuation
                elif words:
                    converted.add_token(
                        token=word['form'],
                        deprel='p',
                        constituent=None,
                        i=word['id'],
                        head=words[-1]
                    )
                else:
                    puncts.append(word)

                # stats
                pos[word['upos']] += 1
                types[deprel] += 1
                if deprel.islower():
                    complete = False
                else:
                    tok[0] += 1
                tok[1] += 1

            # output
            fout.write(converted.draw(include_metadata=True) + '\n\n')
            sent[1] += 1
            if complete:
                sent[0] += 1

    if resfile is not None:
        with open_write(resfile) as fout:
            fout.write(f'{sent[0]} / {sent[1]} sentences fully parsed ({sent[0] * 100 / sent[1]:.2f}%).\n')
            fout.write(f'{sent[2]} / {sent[1]} sentences with all projections known ({sent[2] * 100 / sent[1]:.2f}%).\n')
            fout.write(f'{tok[0]} / {tok[1]} words fully parsed ({tok[0] * 100 / tok[1]:.2f}%).\n\n')
            fout.write('POS\n')
            for i in pos:
                fout.write(f'{i}, {pos[i]}\n')
            fout.write('\nDEP\n')
            for i in types:
                if i[1].islower():
                    fout.write('-->')
                fout.write(f'{i}, {types[i]}\n')

    return cgel_out
