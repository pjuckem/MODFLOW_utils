# Program to fix inconsistencies between GHB stages and interpolated layer elevations
# Gets error info from Groundwater Vistas-generated *.err file
# Based on error_chkr.py, but includes fix for land surface elevations that are above GHB stages

import numpy as np
from collections import defaultdict

# hard coded model dimensions
rows=800
columns=800
layers=5

# Input files
botsfile='BR_L1L5bot.DAT' # GWV mat with bottom elevations for all layers
l1topfile='L1top.DAT' # GWV mat with top elevations for layer 1
err_file='modflow.err'
GHB_file='BadRiver.ghb'
GHB_stage=601.7 # for simple case of all GHBs having same stage

# Output file
GHBout=GHB_file[:-4]+'_fixed.csv'

# get offending cells
errs=open(err_file,'r').readlines()

err_cells=defaultdict(list)
for line in errs:
    if "*** Warning ***" in line:
        r,c,l=map(int,line[line.find("(")+1:line.find(")")].split(','))
        cellnum=(r-1)*columns+c
        err_cells[cellnum]=[r,c,l]

# load in GWV matricies
bots=np.fromfile(botsfile,sep=" ")
bots_rs=bots.reshape(layers,rows,columns) # apparently np convention is l,r,c
l1top=np.fromfile(l1topfile,sep=" ")
l1tops=l1top.reshape(rows,columns)
cellnums=np.reshape(np.arange(1,(rows*columns+1)),(rows,columns))

# add GHB stages, L1top, and cell bottoms for each layer
for cell in err_cells.iterkeys():
    err_cells[cell].append(GHB_stage)
    bots=list(bots_rs[:,err_cells[cell][0]-1,err_cells[cell][1]-1])
    l1top=l1tops[err_cells[cell][0]-1,err_cells[cell][1]-1]
    topandbots=[l1top]
    for l in range(layers):
        topandbots.append(bots[l])
    err_cells[cell].append(topandbots)
    
    # fix cell bottoms and tops for cells with lands surface above GHB stages
    
    # set land surface to GHB stage
    l1top_old=l1top
    l1top=GHB_stage
    
    # lower bottoms until all are lower than land surface
    for b in range(layers):
        # Reset L1 bot to 1 ft below L1top if it is <1 ft below L1top
        if b==0:
            if bots[b]>(l1top-1):
                bots[b]=l1top-1
        else:
            if bots[b]>(bots[b-1]-1): # if next layer is less than 1 foot below previous, reset to 1 ft below
                bots[b]=bots[b-1]-1
            else:
                break
    
    # append fixes to err_cells dictionary
    topandbots=[l1top]
    for l in range(layers):
        topandbots.append(bots[l])
    err_cells[cell].append(topandbots)
    
    # apply fixes to elevation arrays
    l1tops[err_cells[cell][0]-1,err_cells[cell][1]-1]=l1top
    bots_rs[:,err_cells[cell][0]-1,err_cells[cell][1]-1]=np.array(bots)
    
# While we're at it, create new tops array for all layers
tops=np.reshape(np.append(l1tops,bots_rs[:-1,:,:]),[4,800,800])

with file(l1topfile[:-4]+'_new.DAT','w') as outfile:
    for layer in tops:
        np.savetxt(outfile,layer,fmt='%.6e')
outfile.close()   

with file(botsfile[:-4]+'_new.DAT','w') as outfile:
    for layer in bots_rs:
        np.savetxt(outfile,layer,fmt='%.6e')
outfile.close()
    
# Writeout all original and fixed cell elevations to output file

ofp=open(GHBout,'w')
ofp.write('row,column,layer,GHBstage,L1top')
for l in range(layers):
    ofp.write('L'+str(l+1)+'bot')
ofp.write('newL1top')
for l in range(layers):
    ofp.write('newL'+str(l+1)+'bot')
ofp.write('\n')

for cell in err_cells.iterkeys():
    ofp.write(','.join(map(str,err_cells[cell][:4])))
    ofp.write(str(err_cells[cell][4][0]))
    for l in range(layers):
        ofp.write(','+str(err_cells[cell][4][l+1]))
    ofp.write(str(err_cells[cell][5][0]))
    for l in range(layers):
        ofp.write(','+str(err_cells[cell][5][l+1]))    
    ofp.write('\n')
ofp.close()
    
