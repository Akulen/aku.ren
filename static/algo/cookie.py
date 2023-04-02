import argparse
import time

parser = argparse.ArgumentParser(
                    description='Compute optimal layout for an N x M grid')
parser.add_argument('N', type=int, help='side of the grid')
parser.add_argument('-M', default=-1, type=int,
                    help='defaults to N')
parser.add_argument('--show', action='store_true', default=False,
                    help='Show an optimal grid')

args = parser.parse_args()
n = args.N
m = args.M
if m < 0:
    m = n
if n < m:
    n, m = m, n

start = time.time()
cnt = [[[-1] * 2**n for _ in range(2**n)] for _ in range(2**n)]

def mask2str(mask):
    s = ""
    for _ in range(n):
        s += ".X"[mask & 1]
        mask >>= 1
    return s

def test(mask, i):
    return (mask >> i) & 1

def cnt_ones(mask):
    t = 0
    while mask:
        t += mask & 1
        mask >>= 1
    return t

for c1 in range(2**n):
    for c2 in range(2**n):
        for c3 in range(2**n):
            t = 0
            ct = test(c1, 0) + test(c2, 0) + test(c3, 0)
            for i in range(n):
                if i < n-1:
                    ct += test(c1, i+1) + test(c2, i+1) + test(c3, i+1)
                if test(c2, i) == 0 and ct >= 3:
                    t += 1
                if i > 0:
                    ct -= test(c1, i-1) + test(c2, i-1) + test(c3, i-1)

            cnt[c1][c2][c3] = t

dyn = [
    [
        [0] * (m if args.show else 2)
        for _ in range(2**n)
    ] for _ in range(2**n)
]
if args.show:
    o = [[[0] * m for _ in range(2**n)] for _ in range(2**n)]
for c1 in range(2**n):
    for c2 in range(2**n):
        dyn[c1][c2][0] = (cnt[c1][c2][0], -cnt_ones(c2))
for k in range(1, m):
    for c1 in range(2**n):
        for c2 in range(2**n):
            maxi = (0, n*m)
            sol = 0
            for c3 in range(2 ** n):
                a, b = dyn[c2][c3][(k-1) if args.show else ((k & 1) ^ 1)]
                opt = (a + cnt[c1][c2][c3], b - cnt_ones(c2))
                if opt > maxi:
                    maxi = opt
                    sol = c3
            dyn[c1][c2][k if args.show else (k & 1)] = maxi
            if args.show:
                o[c1][c2][k] = sol

def build(k, c1, c2):
    print(mask2str(c2))
    if k > 1:
        build(k-1, c2, o[c1][c2][k-1])

c1 = 0
maxi = (0, n*m)
for c2 in range(2 ** n):
    cur = dyn[0][c2][m-1 if args.show else ((m & 1) ^ 1)]
    if cur > maxi:
        maxi = cur
        c1 = c2
print(maxi[0], -maxi[1])
if args.show:
    build(m, 0, c1)

print(f"Computed in {int((time.time() - start) * 100)/100}s")
