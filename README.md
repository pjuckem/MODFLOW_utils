MODFLOW_utils
=============
process_NWIS_levels.py
  - takes groundwater levels and Site info from NWIS and creates GFLOW or MODFLOW (observation process) targets
  - outputs are set of *tp files for 4 categories of data quality, or one single csv that can be used as input for create_Hobs.py to build hobs file for MF2k observation process
  - also outputs PDF containing timeseries plots of water levels for wells with multiple measurements
    - measurements are compared to computed pre and post-1970 averages
    - graph titles display selected quality category for the well
