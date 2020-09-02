from tqdm import tqdm
from time import sleep

class tqdmm(tqdm):

    @property
    def format_dict(self):
        d = super(tqdmm, self).format_dict

        rate_min = '{:.2f}'.format(1/d['rate'] /60) if d['rate'] else '?'
        d.update(rate_min = (rate_min + 'min/' + d['unit']))

        return d

w = tqdmm(
    dynamic_ncols=True,
    total=8,
    unit='song',
    bar_format='{l_bar}{bar}|ETA: {remaining_s}, {rate_min}'
)

name = [
    'qwe',
    'rty',
    'uio',
    'asd',
    'fgh',
    'jkl',
    'zxc',
    'vbn'
]

for i in range(4):
    w.set_description(name[i] + ' ')
    w.update(1)
    sleep(2)

for i in range(4):
    w.set_description(name[i+4] + ' ')
    w.update(0)
    sleep(2)

w.close()