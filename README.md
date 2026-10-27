# pypsa-SMS++ instances generators

this repository contains a serie of jupyter notebooks (currently 1) for generating pypsa network instances for testing pypsa-SMS++

## CreateElecNetwork.ipynb 

creates a pypsa network for the european power system in 2030 based on ENVIS60 NECPEssentials scenario.

### Use

1- edit settings file: settings/settings_createElecNetwork.yml
In particular inputDir and timeseriespath must contain the location of the fixed and temporal input data, outputDir is the location for the results
You may also specify a sublist of countries , aggregate countries together, choose the time horizon and timestep duration, select scenarios, and define if you want a dataset with integer variables , or with capacity expansion.

2- Data contains a full dataset, composed of the following subrepos:
- TimeSeries : this repo contains a number of csv files, each one containing scenarised timeseries for power demand, RES potentials and hydraulic inflows (columns correspond to the available scenarios)
- envis13_2030: this repo contains the fixed data representing the generation mix 

3- CreateData.py is a python script with a set of functions used in the notebook

