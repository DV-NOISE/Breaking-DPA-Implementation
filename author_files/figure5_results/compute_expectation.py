zetas = [2226, 430, 555, 843, 2078, 871, 1550, 105, 422, 587, 177, 3094, 3038, 2869, 1574, 1653, 3083, 778, 1159, 3182, 2552, 1483, 2727, 1119, 1739, 644, 2457, 349, 418, 329, 3173, 3254, 817, 1097, 603, 610, 1322, 2044, 1864, 384, 2114, 3193, 1218, 1994, 2455, 220, 2142, 1670, 2144, 1799, 2051, 794, 1819, 2475, 2459, 478, 3221, 3021, 996, 991, 958, 1869, 1522, 1628]

def compute_mean(fname):
    mean = 0
    NUM_SAMPLES = 10000
    mean_dist = {1: 0, 2: 0, 3: 0, 4: 0}
    f = open(fname, 'r')
    i = 0
    for line in f.readlines():
        line = line.rstrip()
        tokens = line.split(',')
        for tok in tokens:
            typestr, pstr = tok.split(':')
            coltype = int(typestr)
            p = float(pstr)
            if i > 0:
                mean_dist[coltype] = (mean_dist[coltype] + p)/2
            else:
                mean_dist[coltype] = p

        i += 1
    return mean_dist



def main():
    COL_DATA = [[] for i in range(5)]
    for i in range(0, 64):
        fname = "zetas/zeta-{}-{}.dat".format(i, zetas[i])
        mean_dist = compute_mean(fname)
        for col in mean_dist:
            COL_DATA[col].append(mean_dist[col])
        # print("zeta={}, dist={}".format(zetas[i], mean_dist))
        total = sum(mean_dist.values())
        # print("Total: {}".format(total))

        fname = "zetas/zeta-{}-{}.dat".format(i, -zetas[i])
        mean_dist = compute_mean(fname)
        for col in mean_dist:
            COL_DATA[col].append(mean_dist[col])
        # print("zeta={}, dist={}".format(zetas[i], mean_dist))
        total = sum(mean_dist.values())
        # print("Total: {}".format(total))


    for col in range(len(COL_DATA))[1:]:
        print(COL_DATA[col])
        mu = sum(COL_DATA[col])/len(COL_DATA[col])
        print("Mean col({}): {}\n".format(col, mu))
main()
