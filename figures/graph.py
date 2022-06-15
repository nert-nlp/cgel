import csv
from plotnine import *
import pandas as pd
from mizani.formatters import percent_format

cols = ['# of Rules', 'Coverage', 'Type']
data = []
with open('CGEL.csv', 'r') as fin:
    reader = csv.reader(fin)
    d = list(reader)
    # cols = d[0]
    for i in d[1:]:
        i[1] = int(i[1])
        i[2] = int(i[2]) / 12543
        i[3] = int(i[3]) / 207234
        data.append([i[1], i[2], 'sent'])
        data.append([i[1], i[3], 'tok'])

df = pd.DataFrame(data, columns=cols)

g = ggplot(df, aes(x='# of Rules', y='Coverage', color='Type')) + \
    geom_smooth() + geom_point()
g += scale_y_continuous(labels=percent_format(), limits=[0, 1])
g.save('graph.png', width=5, height=3)