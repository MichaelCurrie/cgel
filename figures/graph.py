import csv
from plotnine import aes, geom_point, geom_smooth, ggplot, scale_y_continuous
import pandas as pd
from mizani.formatters import percent_format

cols = ['# of Rules', 'Coverage', 'Type']
data = []
with open('CGEL.csv', 'r', encoding='utf-8') as fin:
    reader = csv.reader(fin)
    d = list(reader)
    # cols = d[0]
    for i in d[1:]:
        nRules = int(i[1])
        sentCoverage = int(i[2]) / 12543
        tokCoverage = int(i[3]) / 207234
        data.append([nRules, sentCoverage, 'sent'])
        data.append([nRules, tokCoverage, 'tok'])

df = pd.DataFrame(data, columns=cols)

g = ggplot(df, aes(x='# of Rules', y='Coverage', color='Type')) + \
    geom_smooth() + geom_point()
g += scale_y_continuous(labels=percent_format(), limits=(0, 1))
g.save('graph.png', width=5, height=3)