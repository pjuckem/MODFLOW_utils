__author__ = 'aleaf'
'''
fixes MODFLOW "altitude errors" in GHB file, by moving GHB cell to highest layer with bottom above the GHB elevation
requires discomb_utilities (for reading MODFLOW DIS file)
'''

import sys
DISutils_path = 'D:\\ATLData\\Documents\\GitHub\\SFR'
if DISutils_path not in sys.path:
    sys.path.append(DISutils_path)
import discomb_utilities
import os
import numpy as np

GHBfile = 'D:\\ATLData\\BadRiver\\Calibration_base\\BadRiver_GHB.tpl'
DISfile = 'D:\\ATLData\\Documents\\GitHub\\SFR\\BadRiver.dis'


# read in DIS information
DX, DY, nlay, nrows, ncols, i = discomb_utilities.read_meta_data(DISfile)

layer_elevs = np.zeros((nlay+1, nrows, ncols))
for c in range(nlay + 1):
    tmp, i = discomb_utilities.read_nrow_ncol_vals(DISfile, nrows, ncols, 'float', i)
    layer_elevs[c, :, :] = tmp

# read in GHBfile
header = 4
indat = open(GHBfile).readlines()
if "ptf" in indat[0]:
    header += 1

# write new GHB file
ofp = open(GHBfile+'_new', 'w')
logfile = open(os.path.split(GHBfile)[0]+'\\fix_GHB_log.txt', 'w')
logfile.write('Adjustments to GHB layering:\nl,r,c,elevation,new_layer\n')
for i in range(header):
    ofp.write(indat[i])
for i in range(len(indat))[header:]:
    line = indat[i].strip().split()
    l, r, c, = map(int, line[:3])
    elevation = float(line[3])
    cond = line[4]

    if elevation < layer_elevs[l-1, r-1, c-1]:
        bots = list(layer_elevs[:, r-1, c-1])
        bots.append(elevation)
        old_layer = l
        l = sorted(bots, reverse=True).index(elevation) + 1
        logfile.write('{},{},{},{},{}\n'.format(old_layer, r, c, elevation, l))
    ofp.write('{} {} {} {} {}\n'.format(l, r, c, elevation, cond))
logfile.close()
ofp.close()
