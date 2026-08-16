import io
import sys
from cgel_json_converter import cgel
import fileinput

# Always use UTF-8, whatever the platform's locale encoding says.
for _stream in (sys.stdout, sys.stderr):
    if isinstance(_stream, io.TextIOWrapper):
        _stream.reconfigure(encoding='utf-8')

MODE = ['tags', 'trees'][1]
PUNCT = [True, False][0]
#with open('datasets/twitter.cgel') as f, open('datasets/ewt.cgel') as f2, open('datasets/ewt-new1-nschneid.cgel') as f3:
for tree in cgel.trees(fileinput.input(encoding='utf-8')):
    print(tree.tagging(gap_symbol='_.') if MODE=='tags' else tree.ptb(punct = PUNCT, complex_lexeme_separator='_'))
