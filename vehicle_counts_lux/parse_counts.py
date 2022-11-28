import os, io

vcd = 'vehicle_counts_data/'
ccd = 'cycling_counts_data/'

# sorted list of files to process
flist = os.listdir(vcd)
flist.sort()

cdfh = open(ccd + 'cycling_data.csv', 'w')
cmfh = open(ccd + 'metadata.csv', 'w')

# metadata dict
metadata = {}

header = True
for fn in flist:
    with io.open(vcd + fn, encoding="latin-1") as fh:
        print("Processing " + fn)
        file_header = True
        for line in fh:
            p = line.strip().split(',')

            # only keep the first heading for the first file
            if header:
                cdfh.write(",".join(p[0:29]) + "\n")
                cmfh.write(",".join(p[29:]) + "\n")
                header = False
                continue

            # skip headings
            if file_header:
                file_header = False
                continue

            post_id = int(p[0])
            # only want cycling counters - not others
            if post_id < 2000 or post_id > 3000:
                continue

            # add data
            cdfh.write(",".join(p[0:29]) + "\n")

            # build up metadata
            if p[0] not in metadata:
                metadata[p[0]] = ",".join(p[29:]) + "\n"

keys = list(metadata.keys())
keys.sort()
for key in keys:
    cmfh.write(key + "," + metadata[key])


