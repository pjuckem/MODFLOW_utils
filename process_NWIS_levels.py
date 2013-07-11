# program to QC groundwater levels from NWIS database

# Required Inputs:
# NWIS Site File (with station info; tab delimited)
# NWIS groundwater levels file (with levels and dates; tab delimited)
# required NWIS fields: agency_cd, site_no, alt_va, alt_acy_va, lev_dt, lev_va, lev_status_cd, well_depth_va, qw_count_nu, reliability_cd
#
# Coordinates File (with coordinates in model coordinate system for each well)
# This can be created by exporting csv of stations and WGS84 coordinates into ArcMap
# A character needs to be added to ends of station numbers (e.g. '434238088592501n') so that Arc treats them as strings
# Coordinates exported from Arc should have columns site_no2,POINT_X,POINT_Y

import numpy as np
from collections import defaultdict
import datetime as dt
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.backends.backend_pdf import PdfPages

# Input files
infofile='Columbia_header.txt'
levelsfile='Columbia_levels.txt'
coordsfile= 'Columbia_NWIS_headsWTM.csv' 

# Outfiles
pdffile='extended_records.pdf'

mode='MODFLOW' # GFLOW or MODFLOW; writes either a tp file, or .hob file for MF2k observation process


print "getting well info, water levels, and coordinates..."

# get header info

def getheader(filename,indicator,delimiter):
    headervar=0
    infile=open(filename,'r').readlines()
    for line in infile:
        cline=line.strip().split(delimiter)
        if cline[0]=='agency_cd':
            break
        else:
            headervar+=1
    return(headervar)

info_header=getheader(infofile,'agency_cd','\t')
levels_header=getheader(levelsfile,'agency_cd','\t')
        
info=np.genfromtxt(infofile,delimiter='\t',skiprows=info_header,names=True,dtype=None)[1:]
levelsdata=np.genfromtxt(levelsfile,delimiter='\t',skiprows=levels_header,names=True,dtype=None)[1:]

wells=np.unique(levelsdata['site_no'])

# build dictionaries of levels,dates and codes by USGS well no.

levels=defaultdict(list)
dates=defaultdict(list)
codes=defaultdict(list)
WellDepth_elev=defaultdict()

for line in levelsdata:
    wellnum=line['site_no']
    info_ind=np.where(info['site_no']==wellnum)[0][0] 
    elevation=float(info['alt_va'][info_ind].strip())
    try:
        date=dt.datetime.strptime(line['lev_dt'],'%Y-%m-%d')
    except ValueError:
        continue
    level=line['lev_va']
    try:
        level=elevation-float(level)
    except ValueError:
        level=None
    status=line['lev_status_cd']
    try:
        welldepth_elev=elevation-float(info['well_depth_va'][info_ind].strip())   
    except ValueError:
        welldepth_elev=None
    dates[wellnum].append(date)
    levels[wellnum].append(level)
    codes[wellnum].append(status)
    WellDepth_elev[wellnum]=welldepth_elev

# get coordinates from coordsfile
coordsdata=np.genfromtxt(coordsfile,delimiter=',',names=True,dtype=None)
coords=defaultdict(list)
for well in coordsdata:
    site_no=well['site_no2'][1:-2] # had to modify original site_nos by adding a "n", so that Arc would treat as string
    coords[site_no]=[well['POINT_X'],well['POINT_Y']]

if len(coords)<>len(wells):
    raise Warning("Number of coordinates does not match number of wells!")
    
print "sorting wells based on QC criteria..."
names=defaultdict(list)
rejects=defaultdict(list)
wells2plot=[]

# open file to writeout information on "poor" wells that didn't meet any of the quality criteria
discarded=open('discarded_wells.txt','w')
discarded.write('well,num_measurements,reliability_code,alt_accuracy\n')

for well in wells:
    print well
    
    # reset variables
    name=None
    dateslist=[]
    maxmin=None
    n=0
    artesian=False
    
    # get list of measurement dates
    # toss wells with no dates
    dateslist=dates[well]
    if len(dateslist)==0:
        continue    
    
    # get info from header file
    info_ind=np.where(info['site_no']==well)[0][0]
    alt_acc=float(info['alt_acy_va'][info_ind].strip())
    numWQ=float(info['qw_count_nu'][info_ind].strip())
    Drely=info['reliability_cd'][info_ind]
    elevation=float(info['alt_va'][info_ind].strip())
    
    # before sorting, identify wells with more than one measurement
    # extract single value from list for wells with one measurement
    # for artesian wells, set GW elevation to wellhead elevation if no value
    if levels[well][0]==None:
        if 'F' or 'E' in codes[well]:
            levels[well]=elevation
    elif len(levels[well])>1:
        wells2plot.append(well)
        maxmin=np.max(levels[well])-np.min(levels[well])
    elif len(levels[well])==1:
        try:
            levels[well]=levels[well][0]
        except TypeError: # if no level, value obtained from file might be ''
            if 'F' or 'E' in codes[well]:
                artesian=True
                levels[well]=elevation                     
    # sort wells based on QC criteria
    if Drely=='C':
        
        after1970_inds=list(np.where(np.array(dateslist)>dt.datetime(1970,1,1,0,0))[0])
        if len(after1970_inds)>2 and alt_acc<=10:
            n=len(after1970_inds)
            if alt_acc<=5 and n>2:
                name=well[5:]+'_best'
            elif alt_acc<=10 and len(after1970_inds)>30:
                name=well[5:]+'_best'
            elif maxmin<20:
                name=well[5:]+'_good'
            elif n>10:
                name=well[5:]+'_good'
            else:
                name=well[5:]+'_fair'
        elif len(after1970_inds)==2 and alt_acc<=5:
            if maxmin<20:
                name=well[5:]+'_good'
            else:
                name=well[5:]+'_fair'
        elif len(after1970_inds)==1 and alt_acc<5:
            name=well[5:]+'_good'
        elif len(after1970_inds)==1 and numWQ>0 and alt_acc<=5:
            name=well[5:]+'_good'
        elif len(after1970_inds)==1 and artesian and alt_acc<=5:
            name=well[5:]+'_good'
        elif len(after1970_inds)==1 and alt_acc<=10: 
            name=well[5:]+'_fair'
        elif len(after1970_inds)==0:
            n=len(dateslist)
            if n>2 and alt_acc<=5:
                if n>10:
                    name=well[5:]+'_good'
                elif n<=10 and maxmin<20:
                    name=well[5:]+'_good'
                else:
                    name=well[5:]+'_fair'                
            elif n>0:
                name=well[5:]+'_fair'
            else:
                name=well[5:]+'_poor'
                rejects[well].append([n,Drely,alt_acc,name])
                discarded.write('%s,%s,%s,%s,%s\n' %(well,n,Drely,alt_acc,name))                
        else:
            name=well[5:]+'_poor'
            rejects[well].append([n,Drely,alt_acc,name])
            discarded.write('%s,%s,%s,%s,%s\n' %(well,n,Drely,alt_acc,name))
    else:
        name=well[5:]+'_poor'
        rejects[well].append([n,Drely,alt_acc,name])
        discarded.write('%s,%s,%s,%s,%s\n' %(well,n,Drely,alt_acc,name))
    names[well]=name
discarded.close()

# For wells with multiple measurements, calculate average values for post and pre-1970
# Plot out measurements and average values for comparison
# replace multiple levels with new average level
pdf=PdfPages(pdffile)

print 'calculating average values; plotting levels for wells with multiple levels:'
for well in wells2plot:
    
    print well
    #info_ind=np.where(info['site_no']==well)[0][0]
    dates2plot=list(mdates.date2num(dates[well]))
    WLs=levels[well]
    use_post1970=True
    
    if len(dates2plot)<>len(WLs):
        raise ValueError("Dates and WLs for %s have different lengths!" %(well))
    
    cutoff=mdates.date2num(dt.datetime(1970,1,1,0,0))
    
    # post 1970 average
    post1970=[d for d in dates2plot if d>cutoff]
    num2skip=len(WLs)-len(post1970)
    post1970WLs=WLs[num2skip:]
    avg_post1970=[np.mean(post1970WLs)]*len(post1970)    

    # pre 1970 average
    pre1970=[d for d in dates2plot if d<cutoff]
    pre1970WLs=WLs[:len(pre1970)]
    avg_pre1970=[np.mean(pre1970WLs)]*len(pre1970)
    
    # decide which set of water levels to use
    # replace multiple values in levels file with average
    if len(post1970)==0:
        use_post1970=False
        plot_title='WLs in well ' + names[well] + '; using pre-1970 average'
        levels[well]=np.mean(pre1970WLs)
    if use_post1970:
        plot_title='WLs in well ' + names[well] + '; using post-1970 average'
        levels[well]=np.mean(post1970WLs)
        
    fig, ax1 = plt.subplots(1,1,sharex=True,sharey=False)
    ax1.grid(True)
    p1=ax1.plot_date(dates2plot,WLs,'bo',label='WLs')
    plt.xticks(rotation=45,fontsize=10)
    plt.yticks(fontsize=10)
    # get axis limits
    # set plotting range for average values
    x1,x2,y1,y2=ax1.axis()
    if x1>cutoff:
        start=x1
    else:
        start=cutoff
    if x2>cutoff:
        end=cutoff
    else:
        end=x2
    
    # plot average values
    if len(post1970)>0:
        #ax1.axhline(y=avg_post1970, xmin=start, color='r',label='post-1970 avg')
        p2=ax1.plot_date(post1970,avg_post1970,'r',label='post-1970 avg')
            
    if len(pre1970)>0:
        #ax1.axhline(y=avg_pre1970, xmax=end, color='g',label='pre-1970 avg')
        p3=ax1.plot_date(pre1970,avg_pre1970,'g',label='pre-1970 avg')
    handles, labels = ax1.get_legend_handles_labels()
    ax1.legend(handles,labels)
    ax1.set_title(plot_title)
    pdf.savefig()
pdf.close()
plt.close('all')
print "Done plotting, see %s for results" %(pdffile)

# Writeout output files

if mode=='GFLOW':
    for category in ['best','good','fair','poor']:
        # create tp file for each
        fname=category+'_heads.tp'
        ofp=open(fname,'w')
        for well in wells:
            if category in names[well]:
                ofp.write('%s,%s,%s,0,piezometer,%s\n' %(coords[well][0],coords[well][1],levels[well],names[well]))
        ofp.close()
        
if mode=='MODFLOW':
    ofp=open('NWIS_MFhobs_export.csv','w')
    ofp.write('Name,POINT_X,POINT_Y,WL,ScreenTop,ScreenBot\n')
    for category in ['best','good','fair','poor']:
        for well in wells:
            if category in names[well]:
                if WellDepth_elev[well]==None:
                    continue
                else:
                    ofp.write('%s,%s,%s,%s,%s,%s\n' %(names[well],coords[well][0],coords[well][1],levels[well],WellDepth_elev[well],WellDepth_elev[well]))
    ofp.close()    