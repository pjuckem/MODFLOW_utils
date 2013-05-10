# Program to distribute boundary fluxes evenly among layers based on T.
# Uses exported matrices from Groundwater Vistas, and a WEL file with boundary fluxes
# Outputs new boundary cells to r,c,l,flux csv for input back into GWV
# for applying GFLOW solution, best way would be to base transmissivities on saturated thickness

import numpy as np
from collections import defaultdict

# hard coded model dimensions
rows=800
columns=800
layers=5

# Input files
botsfile='BR_L1L5bot.DAT' # GWV mat with bottom elevations for all layers
l1topfile='L1top.DAT' # GWV mat with top elevations for layer 1
Kfile='BR_Kmat.DAT' # GWV mat with K values for all layers
bfluxfile='BR_KC.wel' # WEL file with boundary fluxes

# hard coded wel file settings
field_width=10 # set field width to zero if wel file is delimited instead of fixed
header=2 #lines

# output file
outfile='Bflux_alllayers.csv'

# load in GWV matricies
bots=np.fromfile(botsfile,sep=" ")
bots_rs=bots.reshape(layers,rows,columns) # apparently np convention is l,r,c
l1top=np.fromfile(l1topfile,sep=" ")
l1top=l1top.reshape(rows,columns)
Kx=np.fromfile(Kfile,sep=" ")
Kx_rs=Kx.reshape(layers,rows,columns)

tops=np.append(l1top,bots_rs[0:(layers-1),:,:])
tops_rs=tops.reshape(layers,rows,columns)

thicknesses=tops_rs-bots_rs

cellnums=np.reshape(np.arange(1,(rows*columns+1)),(rows,columns))

if field_width>0:
    bflux=np.genfromtxt(bfluxfile,skip_header=header,delimiter=field_width,dtype=None)
else:
    bflux=np.genfromtxt(bfluxfile,skip_header=header,dtype=None)
bflux=list(bflux)


bcells=defaultdict()
for line in bflux:
    bcellnum=(int(line[1])-1)*columns+int(line[2])
    bcells.setdefault(str(bcellnum),[line[1],line[2],line[3]]) # rows, cols, fluxes


ofp=open(outfile,'w')
ofp.write('row,column,layer,flux\n')
for cell in bcells.iterkeys():
    r=bcells[cell][0]-1 # zero-based indexing
    c=bcells[cell][1]-1
    Kvalues=Kx_rs[0:,r,c]
    bvalues=thicknesses[0:,r,c]
    Tvalues=Kvalues*bvalues
    Ttotal=sum(Tvalues)
    totalflux=bcells[cell][2]
    for l in range(layers):
        flux=totalflux*Tvalues[l]/Ttotal
        ofp.write('%s,%s,%s,%s\n' %(r+1,c+1,l+1,flux))
ofp.close()
            









'''
#plot up thicknesses:
for l in range(layers):
    plt.figure(l)
    plt.imshow(thicknesses[l,:,:])
    plt.colorbar()
    plt.draw()
    
'''