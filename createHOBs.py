# Program to create MODFLOW-2005 HOBS file from spreadsheet with target info
# Spreadsheet format should be:
# headerline(s)
# Name,x,y,water level,screen top elevation,screen bottom elevation

# Reads top/bottom information from Groundwater Vistas matrix exports
# Output is MODFLOW 2005 *.hob file
# See MF2005 Observation Process instructions for information on variable names

from xlrd import open_workbook
import numpy as np
from collections import defaultdict

# hard coded model dimensions
rows=800
columns=800
originX=649521.5
originY=5116116.1
spacing=76.2 # same units as origin
# layers will be based on length of input GWV matrix and number of cells

# Input files
botsfile='BR_L1L5bot.DAT' # GWV mat with bottom elevations for all layers
l1topfile='L1top.DAT' # GWV mat with top elevations for layer 1
headsxls='Head_targets.xlsx' # Head Targets spreadsheet

# Settings
IUHOBSV=500 # file unit for saving head observations
HOBDRY='NaN' # specifies what is written in hob file for dry cells
TOMULTH=0 # time-offset multiplier
IREFSP=1 # stress period to which the observation time is referenced.
TOFFSET=1 # time from the beginning of stress period IREFSP to the time of the observation

# Outputfiles
HOBfile='BadRiver.hob'
culled_headtargets='Head_targets.csv' # list of culled targets for re-import into Excel (and subsequent construction of PEST input files)

# set limits
xlim=originX+columns*spacing
ylim=originY+columns*spacing

# load in GWV matricies
bots=np.fromfile(botsfile,sep=" ")
layers=len(bots)/(rows*columns)
bots_rs=bots.reshape(layers,rows,columns) # apparently np convention is l,r,c
l1top=np.fromfile(l1topfile,sep=" ")
l1top=l1top.reshape(rows,columns)

tops=np.append(l1top,bots_rs[0:(layers-1),:,:])
tops_rs=tops.reshape(layers,rows,columns)

thicknesses=tops_rs-bots_rs
Row_coords=originY+spacing*(0.5+np.array(map(float,(reversed(range(rows))))))
Col_coords=originX+spacing*(0.5+np.array(map(float,(range(columns)))))

# get target info from Excelsheet
hbook = open_workbook(headsxls,on_demand=True)
hobs = hbook.sheet_by_index(0)
(obsname,x,y,WL,sctop,scbot) = [hobs.col_values(0),hobs.col_values(1),hobs.col_values(2),hobs.col_values(3),hobs.col_values(4),hobs.col_values(5)]

print "Processing head observations..."
obslines=[]
NH=0
MOBS=0
MAXM=2
ctargets=[]
for i in range(len(obsname))[1:]:
    
    if originX<x[i]<xlim and originY<y[i]<ylim:
        ctargets.append(','.join(map(str,[obsname[i],WL[i]])))
        NH+=1
        print '%s %s' %(obsname[i],NH) 
        # Determine horizontal offset coefficents for obs process
        distY=(y[i]-originY-0.5*spacing)
        row=rows-round(distY/spacing)
        ROFF=distY/spacing-(rows-row)
        
        distX=(x[i]-originX-0.5*spacing)
        column=round(distX/spacing)+1
        COFF=(distX/spacing-column+1)
        
        # Determine vertical averaging coeffcients for water level
        bots=list(bots_rs[:,int(row-1),int(column-1)])
        top=[l1top[int(row-1),int(column-1)]]
        bots=top+bots
        screenlength=sctop[i]-scbot[i]
        
        PR=dict()
        for b in range(len(bots)):
            # if the layer bottom is above the top of screen, continue
            if bots[b]>sctop[i]:
                continue
            # elif the screened interval is entirely within this layer, PR=1
            elif bots[b]<sctop[i]<bots[b-1] and bots[b]<scbot[i]<bots[b-1]:
                PR[b]=1
                break
            # elif the only the screen top is within the layer, calculate portion of screen in layer
            elif bots[b-1]>sctop[i]>bots[b]:
                PR[b]=round((sctop[i]-bots[b])/screenlength,3) # round to avoid floating point error
            # elif the screen top is above the layer, and screen bottom below the layer, calculate portion of screen thickness made up by entire layer
            elif bots[b-1]<sctop[i] and scbot[i]<bots[b]:
                PR[b]=round((bots[b-1]-bots[b])/screenlength,3)
            # elif the screen top is above the layer, and screen bottom within the layer, calculate portion of screen in the layer
            elif bots[b-1]<sctop[i] and scbot[i]>bots[b]:
                PR[b]=round((bots[b-1]-scbot[i])/screenlength,3)
                break
        
        # enforce that PR values sum to 1 (MODFLOW won't run otherwise)
        PRsum=sum(PR.itervalues())
        if PRsum!=1.0:
            residual=PRsum-1
            #print str(residual)
            if abs(residual)>0.01:
                raise ValueError("Extra layer in " + obsname[i])
            '''for layer in PR.iterkeys():
                PR[layer]=round(PR[layer],2)
        PRsum=sum(PR.itervalues())
        if PRsum!=1.0:
            raise ValueError("shit!"+obsname[i]+str(PRsum))'''
        
        # determine LAYER variable for HOB file
        if len(PR)>1:
            layer=len(PR)*-1
            MOBS+=1
            if len(PR)>MAXM:
                MAXM=len(PR)
        else:
            for key in PR.iterkeys():
                layer=key
            
        # add entry to hob output file
        obslines.append('%s %s %s %s %s %s %s %s %s\n' %(obsname[i],layer,int(row),int(column),IREFSP,TOFFSET,ROFF,COFF,WL[i]))
        if layer<0:
            for l in PR.iterkeys():
                obslines.append('%s,%s\n' %(l,PR[l]))
        else:
            continue
    else:
        continue

# save to output file
ofp=open(HOBfile,'w')
ofp.write('# HOBs file created by createHOBs.py\n')
ofp.write('%s %s %s %s %s\n' %(NH,MOBS,MAXM,IUHOBSV,HOBDRY))
ofp.write('%s\n' %(TOMULTH))
for line in obslines:
    ofp.write(line)
ofp.close()

# write list of culled targets (within model domain) to outfile for import into excel
ofp=open(culled_headtargets,'w')
for lines in ctargets:
    ofp.write(lines+'\n')
ofp.close()