__author__ = 'aleaf'
'''
Route MODFLOW UZF Package groundwater discharge to landsurface to SFR segments, using catchment info from NHDplus v2
inputs:
NHDPlus v2 catchment files (e.g. NHDPlusV21_GL_04_NHDPlusCatchments_05.7z; available from http://www.horizon-systems.com/NHDPlus/NHDPlusV2_04.php)
shapefiles of model grid cells, model domain, and SFR cells (all in same projection)

requirements:
arcpy
GISio and GISops, from aleaf/GIS_utils on github
(these require the fiona, shapely, and pandas packages)
'''
import numpy as np
import arcpy
import os
import sys
GIS_utils_path = 'D:/ATLData/Documents/GitHub/GIS_utils'
if GIS_utils_path not in sys.path:
    sys.path.append(GIS_utils_path)
import GISio
import GISops

import pandas as pd

# NHDPlus v2 catchment files (list)
catchments = ['D:/ATLData/BadRiver/BCs/NHDPlusGL/NHDPlus07/NHDPlusV21_MS_07_NHDPlusCatchment_01/NHDPlusMS/NHDPlus07/NHDPlusCatchment/Catchment.shp',
              'D:/ATLData/BadRiver/BCs/NHDPlusGL/NHDPlus04/NHDPlusV21_GL_04_NHDPlusCatchments_05/NHDPlusGL/NHDPlus04/NHDPlusCatchment/Catchment.shp']
# input shapefile (should all be in same projection!)
MFdomain = 'D:/ATLData/BadRiver/BCs/Arcfiles/BadRiver_MFdomain_WISP.shp'
MFgrid = 'D:/ATLData/BadRiver/BCs/Arcfiles/BadRiver_gridcells_WISP.shp'
SFR_shapefile = 'D:/ATLData/Documents/GitHub/SFR/BR_SFR_with_WI_hydro.shp'

# output
out_IRUNBND = 'BadRiver_IRUNBND.dat'
out_IRUNBND_shp = 'BadRiver_IRUNBND.shp'

# initialize the arcpy environment
arcpy.env.workspace = os.getcwd()
arcpy.env.overwriteOutput = True
arcpy.env.qualifiedFieldNames = False
arcpy.CheckOutExtension("spatial") # Check spatial analyst license
'''
# preprocessing

print 'merging NHDPlus catchemnt files:'
for f in catchments:
    print f
if len(catchments) > 1:
    arcpy.Merge_management(catchments, os.path.join(os.getcwd(), 'temp.shp'))
else:
    arcpy.CopyFeatures_management(catchments[0], os.path.join(os.getcwd(), 'temp.shp'))

print '\nreprojecting to {}.prj'.format(SFR_shapefile[:-4])
arcpy.Project_management(os.path.join(os.getcwd(), 'temp.shp'), os.path.join(os.getcwd(), 'temp2.shp'),
                         SFR_shapefile[:-4] + '.prj')

print 'clipping to {}'.format(MFdomain)
arcpy.Clip_analysis(os.path.join(os.getcwd(), 'temp2.shp'), MFdomain, os.path.join(os.getcwd(), 'catchments.shp'))

print 'performing spatial join of catchments to SFR cells...'
arcpy.SpatialJoin_analysis(SFR_shapefile,
                           os.path.join(os.getcwd(), 'catchments.shp'),
                           os.path.join(os.getcwd(), 'catchments_joined.shp'))
print 'and to model grid (this may take awhile)...'
arcpy.SpatialJoin_analysis(MFgrid,
                           os.path.join(os.getcwd(), 'catchments.shp'),
                           os.path.join(os.getcwd(), 'MFgrid_catchments.shp'))
'''
# now figure out which SFR segment each catchment should drain to
print 'reading {} into pandas dataframe...'.format(os.path.join(os.getcwd(), 'catchments_joined.shp'))
SFRcatchments = GISio.shp2df(os.path.join(os.getcwd(), 'catchments_joined.shp'))

print 'assigning an SFR segment to each catchment... (this may take awhile)'
intersected_catchments = list(np.unique(SFRcatchments.FEATUREID))
segments_dict = {}
for cmt in intersected_catchments:
    try:
        segment = SFRcatchments[SFRcatchments.FEATUREID == cmt].segment.mode()[0]
    except: # pandas crashes if mode is called on df of length 1
        segment = SFRcatchments[SFRcatchments.FEATUREID == cmt].segment[0]
    segments_dict[cmt] = segment
    # can also use values_count() to get a frequency table for segments (reaches) in each catchment

print 'building UZF package IRUNBND array from {}'.format(MFgrid)
MFgrid_joined = GISio.shp2df(os.path.join(os.getcwd(), 'MFgrid_catchments.shp'), geometry=True)
MFgrid_joined.index = MFgrid_joined.node
nrows, ncols = np.max(MFgrid_joined.row), np.max(MFgrid_joined.column)

# make new column of SFR segment for each grid cell
MFgrid_joined['segment'] = MFgrid_joined.FEATUREID.apply(segments_dict.get).fillna(0)

print 'writing {}'.format(out_IRUNBND)
IRUNBND = np.reshape(MFgrid_joined['segment'].sort_index().values, (nrows, ncols))
np.savetxt(out_IRUNBND, IRUNBND, fmt='%i', delimiter=' ')

print 'writing {}'.format(out_IRUNBND_shp)
#df, shpname, geo_column, prj
GISio.df2shp(MFgrid_joined,
             os.path.join(os.getcwd(), 'MFgrid_segments.shp'),
             'geometry',
             os.path.join(os.getcwd(), 'MFgrid_catchments.shp')[:-4]+'.prj')

MFgrid_joined_dissolved = GISops.dissolve_df(MFgrid_joined, 'segment')

GISio.df2shp(MFgrid_joined_dissolved,
             os.path.join(os.getcwd(), 'MFgrid_segments_dissolved.shp'),
             'geometry',
             os.path.join(os.getcwd(), 'MFgrid_catchments.shp')[:-4]+'.prj')