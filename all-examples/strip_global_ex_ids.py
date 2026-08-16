import yaml
import re
import io
import sys
from typing import Mapping
from collections import defaultdict
from yaml.representer import Representer

from pagified_html_to_yaml import mk_double_quote

try:
    from yaml import CLoader as Loader
except ImportError:
    from yaml import Loader

RE_GLOBAL_EX_ID = re.compile(r'^ex[0-9]+')

yaml.add_representer(defaultdict, Representer.represent_dict)

# Always use UTF-8, whatever the platform's locale encoding says.
for _stream in (sys.stdin, sys.stdout, sys.stderr):
    if isinstance(_stream, io.TextIOWrapper):
        _stream.reconfigure(encoding='utf-8')

yaml.add_representer(str, mk_double_quote)

def recurse(d: Mapping):
    firstFullLocator = None
    for k,v in d.items():
        if k=='page' or k=='title':
            continue
        if isinstance(v, list):
            globalexid = v[0]
            newexid = RE_GLOBAL_EX_ID.sub('', globalexid)
            v[0] = newexid
            if not firstFullLocator:
                firstFullLocator = newexid
        else:
            loc = recurse(v)
            if not firstFullLocator:
                firstFullLocator = loc
    return firstFullLocator


with (open(sys.argv[1], encoding='utf-8') if sys.argv[1:] else sys.stdin) as inF:
    doc = yaml.load(inF, Loader)
    for k in list(doc.keys()):
        globalexid = k
        v = doc[globalexid]
        newexid = recurse(v)
        del doc[globalexid]
        assert newexid not in doc,newexid
        doc[newexid] = v

print(yaml.dump(doc, width=float("inf"), sort_keys=False))
