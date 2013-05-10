# Program to retrieve Global Mass Bal., and Zone Budget Mass Bal. from MODFLOW *.cbb files, for any number of zones defined by .ij files containing the zone cell indices in the form:
# Row, Column (header)
# Row, Column (values; n lines for n cells)

# Zone Budget output files are created in each MODFLOW run folder; selected Zone Budget results
# and global Mass Bal. results are compiled into 'ZB_summary.out' in the same folder as Get_MB.py

# polygon ij files and zonbud.exe must be in same folder as Get_MB.py
# MODFLOW runs (cbb files) should be in subfolders, within the same folder as Get_MB.py
import os
import numpy as np
import shutil

outfile='20130315_runs_NWT_MB.out'
createzon='no' # 'yes' to create zonbudget input files

#MODFLOW model dimensions
rows=261
columns=277
layers=15

print 'finding polygon ij files and run folders...'
allfiles=os.listdir(os.getcwd())
plys = dict()
cind=-1
for cf in allfiles:
    if cf.lower().endswith('.ij'):
        cind = cind+1
        plys[cind]=cf[:-3] 
              
all_subdirs = [d for d in os.listdir('.') if os.path.isdir(d)]
all_subdirs = [all_subdirs for all_subdirs in all_subdirs if all_subdirs != 'NWT_files']
all_subdirs = [all_subdirs for all_subdirs in all_subdirs if all_subdirs != 'Python27']

all_subdirs = [all_subdirs for all_subdirs in all_subdirs if all_subdirs.endswith('NWT')]

print 'creating zonebud input files...'

if createzon=='yes':
    for p in plys:
	    outfile=plys[p]+'.zon'
	    pcells=[]
	    pinds=np.genfromtxt(plys[p]+'.ij',delimiter=',',names=True,dtype=None)
	    for i in range(len(pinds)):
		    prow=pinds[i][0]
		    pcol=pinds[i][1]
		    pcell=(prow-1)*columns+pcol
		    pcells.append(pcell)
	    pcells=np.array(pcells)
	    
	    # write zonbud input file cell by cell, row by row, layer by layer
	    ofp=open(outfile,'w')
	    ofp.write('%s %s %s\n' %(layers,rows,columns))
		      
	    for l in range(layers+1)[1:]:
		    ofp.write('INTERNAL ('+str(columns)+'I2)\n')
		    for r in range(rows):
			    for c in range(columns):
				    cellnum=r*columns+c+1
				    intersect=np.where(pcells==cellnum)[0]
				    # if cell is not within the polygon, assing to zone 0
				    if len(intersect)==0:
					    ofp.write('0 ')
				    # otherwise assing to zone 1    
				    else:
					    ofp.write('1 ')
			    ofp.write('\n')        
	    ofp.close()
	    for folder in all_subdirs:
		    shutil.copy(outfile,folder)
	    print outfile

print 'running Zone Budget...'

for folder in all_subdirs:
    os.chdir(folder)
    print "from folder "+ folder+'...'
    allfiles=os.listdir(os.getcwd())
    zons = dict()
    cbbs = dict()
    cind=-1
    zind=-1
    for cf in allfiles:
        if cf.lower().endswith('.zon'):
            zind=zind+1
            zons[zind]=cf[:-4]
        if cf.lower().endswith('.cbb'):
            cind = cind+1
            cbbs[cind]=cf[:-4]            
    for n in range(len(cbbs)):
        print 'Scenario '+ cbbs[n]
        for z in range(len(zons)):
            print 'running '+zons[z]
            basename=cbbs[n]+'_'+zons[z]
            respfile=basename+'_resp'
            ofp=open(respfile,'w')
            ofp.write(basename+'.zout\n')
            ofp.write(cbbs[n]+'.cbb\n')
            ofp.write(basename+'\n')
            ofp.write(zons[z]+'.zon\n')
            ofp.write('A\n')
            ofp.close()
            os.system("..\zonbud <" + respfile)
            os.remove(respfile) # cleanup folder
    os.remove(zons[z]+'.zon')
    os.chdir('..')

print 'Retrieving Zone Budget results...'  

ofp=open(outfile,'w')
ofp.write('Zone Budget Summary for Polygons\n')
for folder in all_subdirs:
    os.chdir(folder)
    print folder
    allfiles=os.listdir(os.getcwd())
    zouts = dict()
    lsts= dict()
    cind=-1
    zind=-1
    for cf in allfiles:
        if cf.lower().endswith('.zout'):
            zind=zind+1
            zouts[zind]=cf
        if cf.lower().endswith('.lst'):
            cind = cind+1
            lsts[cind]=cf
    
    for n in range(len(zouts)):
        print zouts[n]
        ofp.write('Mass Balance Summary for ' + zouts[n]+'\n')
        Nearfield=False
        with open(zouts[n]) as infile:
            for line in infile:
                if 'Nearfield_mass_balance' in line:
                    Nearfield=True
		if 'Quarries' in line:
			Quarries=True		    
                if Nearfield==False:
                    if 'IN:' in line:
			In=True
                        ofp.write(line)
                    if 'CONSTANT HEAD' in line:
                        ofp.write(line)
			if In:
			    CHDin=float(line.split()[3])
			if Out:
			    CHDout=float(line.split()[3])
		    if 'DRAINS' in line:
			ofp.write(line)
			if In:
				DRNin=float(line.split()[2])
			if Out:
				DRNout=float(line.split()[2])
		    if 'RIVER LEAKAGE' in line:
			ofp.write(line)
			if In:
			    RIVin=float(line.split()[3])
			if Out:
			    RIVout=float(line.split()[3])
		    if 'OUT:' in line:
			In=False
			Out=True
			ofp.write(line)
		    if 'Discrepancy' in line:
		    # we have reached the end of mass bal. info; print totals
			ofp.write('\n')
			ofp.write('Net fluxes for '+zouts[n]+'\n')
			Qnet=CHDout-CHDin+DRNout
			RIVnet=RIVout-RIVin
			if Quarries:
				ofp.write('Quarries = '+str(Qnet)+'\n')
			ofp.write('Net flux to River Cells (Out-In) = '+str(RIVnet)+'\n')
			ofp.write('\n')
                elif Nearfield and 'Percent Discrepancy' in line:
                    ofp.write('Nearfield Mass Bal. for '+ zouts[n]+ ' '+ line)
	    Out=False   
	    Quarries=False
    
    print 'Adding Global Mass Balance Discrepancies...'                    
    for n in range(len(lsts)):
        ofp.write('Global Mass Balance Discrepancy for '+lsts[n]+'\n')
        with open(lsts[n]) as infile:
            for line in infile:
                if 'PERCENT DISCREPANCY' in line:
                    ofp.write(line)
                    print lsts[n]
    os.chdir('..')
ofp.close()
                    
                    
        
    
    












'''print 'getting folder names...'
all_subdirs = [d for d in os.listdir('.') if os.path.isdir(d)]

for folder in all_subdirs:
    os.chdir(folder)
    allfiles=os.listdir(os.getcwd())
    _os = dict()
    cind=-1
    
    print 'finding _os files in ' + folder
    
    for cf in allfiles:
        if cf.endswith('._os'):
            cind = cind+1
            _os[cind]=cf[:-4]'''