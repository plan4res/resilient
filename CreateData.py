from __future__ import annotations
from typing import Tuple, Optional
import numpy as np
import pandas as pd
import pypsa
import yaml
import os
import geopandas as gpd


def read_input_timeseries(cfg, ts_name, which_path='timeseriespath', **kwargs):
    file = os.path.join(cfg[which_path], ts_name)
    print('Read '+file)
    if not os.path.isfile(file):
        print('File '+file+' does not exist ')
        sys.exit(2)
    return pd.read_csv(file, **kwargs)

def read_excel_timeseries(cfg, file_name, which_path='timeseriespath', **kwargs): 
	file = os.path.join(cfg[which_path], file_name)
	if not os.path.isfile(file):
		print('File '+file+' does not exist. Use key '+which_path+' in configuration file '+settings_format+(' or configuration file '+settings_create if settings_create is not None else '')+' to specify input directory.')
		sys.exit(2)
	print('Read '+file)
	return pd.read_excel(file, **kwargs)

def read_input_csv(cfg, file_name_key,**kwargs):
	file = os.path.join(cfg['inputDir'], cfg['csvfiles'][file_name_key])
	if not os.path.isfile(file):
		print(f'File {file} does not exist. Use key {input} in configuration file to specify input directory.')
		sys.exit(2)
	if 'csv_delim' in cfg.keys():
		kwargs.update({'sep' : cfg['csv_delim']})
	print('Read file '+file)
	data = pd.read_csv(file, **kwargs)
	if data.index.has_duplicates:
		msg = 'Error: input csv '+file+' has some duplicated names '
		if 'index_col' in kwargs.keys():
			msg += 'in columns ['+', '.join(kwargs['index_col'])+']'
		msg += '. Duplicates are '+'\n\t'.join(str(i) for i in data.index[data.index.duplicated()])
		print(msg)
		sys.exit(3)
	return data

def parse_datetime_index(index, dayfirst=None):
    import re
    if len(index) == 0:
        return pd.to_datetime(index, dayfirst=dayfirst)
    sample_date = str(index[0])
    iso_pattern = r'^\d{4}-\d{2}-\d{2}'
    is_iso8601 = bool(re.match(iso_pattern, sample_date))
    if is_iso8601:
        return pd.to_datetime(index, format='ISO8601', errors='coerce')
    else:
        return pd.to_datetime(index, dayfirst=dayfirst)

def has_value(val): 
    return not (pd.isna(val) or str(val).strip() == "")

def type_of_value(val):
    # Valeur vide
    if pd.isna(val) or str(val).strip() == "":
        return "vide"
    # Test si c'est un nombre (int ou float)
    try:
        float(val)
        return "number"
    except ValueError:
        return "text"
def abspath_to_relpath(path, basepath):
    return os.path.relpath(path, basepath) #if os.path.abspath(path) else path

def read_plan4res_config(config_path="settings/",settings="settings.yml"):    
    print("read config from ",settings)
        
    # read config file
    cfg={}
    with open(os.path.join(config_path, settings),"r") as mysettings:
        cfg=yaml.load(mysettings,Loader=yaml.FullLoader)
    return cfg

def read_ZP(cfg, Coupling):
    # Read sheet ZP_ZonePartition
    #################################################################################################################################################
    if 'ZP_ZonePartition' in cfg['csvfiles']:
        if cfg['inputformat']=='excel':
            p4r_excel=cfg['inputDir']+cfg['excelfile']
            ZP=pd.read_excel(p4r_excel,sheet_name='ZP_ZonePartition',skiprows=0,index_col=None)
        else:
            ZP=read_input_csv(cfg, 'ZP_ZonePartition', skiprows=0, index_col=None)
        
        ZP=ZP.drop_duplicates()                    
        Nodes=ZP[Coupling['Partition'].loc['ActivePowerDemand']]
        NumberNodes=len(Nodes)
        NumberSlackUnits=NumberNodes  # there is one slack unit per node
    
        # create partitions
        # Partition['Leveli'] is a dictionnary whose keys are the regions at level i and values are the list of nodes in each region
        Partition=pd.Series(dtype=object)
        for level in ZP.columns:
            if level==Coupling['Partition'].loc['ActivePowerDemand']: 
                Partition.loc[level]=dict(zip(list(Nodes),[ [node] for node in list(Nodes)]))
            else:
                keys=list(set(list(ZP[level])))
                values= []
                for key in keys:
                    values.append(list(set(list(ZP.loc[ZP[level]==key][Coupling['Partition'].loc['ActivePowerDemand']]))))
                Partition.loc[level]=dict(zip(keys,values))
                
        if 'PrimaryDemand' in Coupling.index:
            NumberPrimaryZones=len(Partition.loc[Coupling['Partition']['PrimaryDemand']])
        else: NumberPrimaryZones=0
        if 'SecondaryDemand' in Coupling.index:
            NumberSecondaryZones=len(Partition.loc[Coupling['Partition']['SecondaryDemand']])
        else: NumberSecondaryZones=0
        if 'InertiaDemand' in Coupling.index:
            NumberInertiaZones=len(Partition.loc[Coupling['Partition']['InertiaDemand']])
        else: NumberInertiaZones=0
        return ZP
    else:
        print('ZP_Partition missing')
        sys.exit(2)
    

def read_ZV(cfg):
    # Read sheet ZV_ZoneValues
    #################################################################################################################################################
    if 'ZV_ZoneValues' in cfg['csvfiles']:
        if cfg['inputformat']=='excel':
            ZV=pd.read_excel(p4r_excel,sheet_name='ZV_ZoneValues',skiprows=0,index_col=['Type', 'Zone'])
        else:
            ZV=read_input_csv(cfg, 'ZV_ZoneValues',skiprows=0,index_col=['Type', 'Zone'])
    
        # drop_duplicates does not work right wiuth multi indexes 
        if 'Profile_Timeserie' in ZV.columns:
            ZV['Profile_Timeserie']=ZV['Profile_Timeserie'].fillna('')
        else:
            ZV['Profile_Timeserie']=''
        ZV['Profile_Timeserie']=ZV['Profile_Timeserie'].fillna('')                                                           
        ZV=ZV.fillna(0)
        return ZV
    else: 
        print('ZV_ZoneValues missing')
        sys.exit(1)
    

def read_TU(cfg):
    # Read sheet TU_ThermalUnits
    #################################################################################################################################################
    if 'TU_ThermalUnits' in cfg['csvfiles']:
        if cfg['inputformat']=='excel':
            TU=pd.read_excel(p4r_excel,sheet_name='TU_ThermalUnits',skiprows=0,index_col=['Name','Zone'])
        else:
            TU=read_input_csv(cfg, 'TU_ThermalUnits', skiprows=0, index_col=['Name','Zone'])
        TU=TU[TU['NumberUnits'] != 0]
        TU=TU.reset_index().drop_duplicates().set_index(['Name','Zone'])
        TU=TU.drop( TU[ TU['NumberUnits']==0 ].index )
        if ('MaxAddedCapacity' not in TU.columns and 'MaxRetCapacity' not in TU.columns):
            TU=TU.drop( TU[ TU['MaxPower']<=cfg['Parameters']['zerocapacity'] ].index )
        else:
            TU=TU.drop( TU[ ( TU['MaxPower']        <=cfg['Parameters']['zerocapacity'] )    \
                &           ( TU['MaxAddedCapacity']<=cfg['Parameters']['zerocapacity'] )    \
                &           ( TU['MaxRetCapacity']  <=cfg['Parameters']['zerocapacity'] ) ].index )
    
        if 'MaxPowerProfile' in TU.columns:
            TU['MaxPowerProfile']=TU['MaxPowerProfile'].fillna('')
        return TU
    else: 
        logger.warning('No thermal mix in this dataset')
        return None
    

def read_RES(cfg):
    # Read sheet RES_RenewableUnits
    #################################################################################################################################################
    if 'RES_RenewableUnits' in cfg['csvfiles']:
        if cfg['inputformat']=='excel':
            RES=pd.read_excel(p4r_excel,sheet_name='RES_RenewableUnits',skiprows=0,index_col=['Name','Zone'])
        else:
            RES=read_input_csv(cfg, 'RES_RenewableUnits',skiprows=0,index_col=['Name','Zone'])
        RES=RES.reset_index().drop_duplicates().set_index(['Name','Zone'])
        RES=RES.drop( RES[ RES['NumberUnits']==0 ].index )
        if ('MaxAddedCapacity' not in RES.columns and 'MaxRetCapacity' not in RES.columns):
            RES=RES.drop( RES[ RES['MaxPower']<=cfg['Parameters']['zerocapacity'] ].index )
        else:
            RES=RES.drop( RES[ (RES['MaxPower']<=cfg['Parameters']['zerocapacity']) & ( RES['MaxAddedCapacity']<=cfg['Parameters']['zerocapacity']) & (RES['MaxRetCapacity']<=cfg['Parameters']['zerocapacity'] ) ].index )
    
        if 'Energy_Timeserie' in RES.columns and 'Energy' in RES.columns:
            RES['EnergyMaxPower']=RES.apply(lambda x: ( x.Energy if (x.name[0]=="Hydro|Run of River") else x.Energy_Timeserie*x.MaxPower),axis=1)
        RES['MaxPowerProfile']=RES['MaxPowerProfile'].fillna('')
        
        return RES
    else: 
        logger.warning('No intermittent generation mix in this dataset')
        return None
    

def read_SS(cfg):
    # Read sheet SS_SeasonalStorage
    #################################################################################################################################################
    if 'SS_SeasonalStorage' in cfg['csvfiles']:
        if cfg['inputformat']=='excel':
            SS=pd.read_excel(p4r_excel,sheet_name='SS_SeasonalStorage',skiprows=0,index_col=['Name','Zone'])
        else:
            SS=read_input_csv(cfg, 'SS_SeasonalStorage',skiprows=0,index_col=['Name','Zone'])
        if not SS.empty:
            SS=SS.drop( SS[ SS['NumberUnits']==0 ].index )
            SS=SS.drop( SS[ SS['MaxPower']==0.0 ].index )
            SS['InflowsProfile']=SS['InflowsProfile'].fillna('')
            SS=SS.reset_index().drop_duplicates().set_index(['Name','Zone'])
            if 'WaterValues' in SS:
                SS['WaterValues']=SS['WaterValues'].fillna('')
            
            SS['NumberReservoirs']=1
            SS['NumberArcs']=1
            for reservoir in SS.index:
                if 'MinPower' in SS.columns and SS['MinPower'][reservoir]<0:
                    SS.loc[reservoir]['NumberReservoirs']=2
                    SS.loc[reservoir]['NumberArcs']=2
            return SS
        else: 
            logger.warning('No seasonal storage mix in this dataset')
            return None
    else: 
        logger.warning('No seasonal storage mix in this dataset')
        return None

def read_STS(cfg):
    # Read sheet STS_ShortTermStorage
    #################################################################################################################################################
    if 'STS_ShortTermStorage' in cfg['csvfiles']:
        if cfg['inputformat']=='excel':
            STS=pd.read_excel(p4r_excel,sheet_name='STS_ShortTermStorage',skiprows=0,index_col=['Name','Zone'])
        else:
            STS=read_input_csv(cfg, 'STS_ShortTermStorage',skiprows=0,index_col=['Name','Zone'])
        STS=STS.reset_index().drop_duplicates().set_index(['Name','Zone'])

        STS=STS.drop( STS[ STS['NumberUnits']==0 ].index )
        return STS       
    else: 
        logger.warning('No short term storage mix in this dataset')
        return None
    
def read_IN(cfg):
    # Read sheet IN_Interconnections
    #################################################################################################################################################
    if 'IN_Interconnections' in cfg['csvfiles']:
        if cfg['inputformat']=='excel':
            IN=pd.read_excel(p4r_excel,sheet_name='IN_Interconnections',skiprows=0,index_col=0)
        else:
            IN=read_input_csv(cfg, 'IN_Interconnections', skiprows=0,index_col=0)

        if ('MaxAddedCapacity' not in IN.columns and 'MaxRetCapacity' not in IN.columns):
            IN=IN.drop( IN[ (IN['MaxPowerFlow']<=cfg['Parameters']['zerocapacity']) & (IN['MinPowerFlow']>=(-1)*cfg['Parameters']['zerocapacity'])  ].index )
        else:
            IN=IN.drop( IN[ (IN['MaxPowerFlow']<=cfg['Parameters']['zerocapacity']) & (IN['MinPowerFlow']>=(-1)*cfg['Parameters']['zerocapacity']) & (IN['MaxAddedCapacity']<=cfg['Parameters']['zerocapacity']) & (IN['MaxRetCapacity']<=cfg['Parameters']['zerocapacity'])  ].index )
    
        IN=IN.drop_duplicates()
        return IN
    else: 
        logger.warning('No interconnections in this dataset')
        return None

def read_coupling(cfg):
    # create table of coupling constraints
    ListPossibleTypesCoupling=['ActivePowerDemand','PrimaryDemand','SecondaryDemand','InertiaDemand','PollutantBudget']
    
    ListCouplingConstraints=[elem for elem in cfg['CouplingConstraints'] if 'Pollutant' not in elem]
    ListPollutants=[]
    if 'PollutantBudget' in cfg['CouplingConstraints']:
        for pollutant in cfg['CouplingConstraints']['PollutantBudget']:
            ListPollutants=ListPollutants+[pollutant]
    Coupling=pd.DataFrame(index=ListCouplingConstraints+ListPollutants,dtype=object,columns=['Partition','Sum'])
    
    NumberPollutants=0
    for coupling_constraint in cfg['CouplingConstraints']:
        if coupling_constraint not in ListPossibleTypesCoupling:
            print('Constraint '+coupling_constraint+'is not possible')
            print('Possible constraints are: '+', '.join(ListPossibleTypesCoupling))
            sys.exit(1)
        if coupling_constraint=="PollutantBudget":
            NumberPollutants=len(cfg['CouplingConstraints']['PollutantBudget'])
            for pollutant in ListPollutants:
                Coupling.loc[pollutant]['Sum']=[cfg['CouplingConstraints']['PollutantBudget'][pollutant]['SumOf']]
                Coupling.loc[pollutant]['Partition']=cfg['CouplingConstraints']['PollutantBudget'][pollutant]['Partition']
        else:
            Coupling.loc[coupling_constraint,'Sum']=cfg['CouplingConstraints'][coupling_constraint]['SumOf']
            Coupling.loc[coupling_constraint,'Partition']=cfg['CouplingConstraints'][coupling_constraint]['Partition']
    print('Coupling constraints:'+', '.join(ListCouplingConstraints))
    print('Emissions constraints:'+', '.join(ListPollutants))
    return Coupling

def ExtendAndResample(name,TS,dates,UCTimeStep,isEnergy=True):
    # change timeindex to adapt to dataset calendarb
    beginSerie=TS.index[0]
    if beginSerie>dates['UCBeginDataYearP4R']:
        datesDelta=pd.Timedelta(beginSerie-dates['UCBeginDataYearP4R'])
        TS.index=TS.index-datesDelta
    else:
        datesDelta=pd.Timedelta(dates['UCBeginDataYearP4R']-beginSerie)
        TS.index=TS.index+datesDelta
    
    # Extension is a copy of TS on the extended dates UCBeginExtendedData and UCEndExtendedData 
    #Extension=TS[ TS.index>= dates['UCBeginExtendedData'] ]
    #Extension=Extension[ Extension.index<= dates['UCEndExtendedData'] ]
    
    # resample
    newfreq=str(UCTimeStep)+'h'
    TS_freq=pd.infer_freq(TS.index)

    # upsample=True means that timeseries is given at a frequency
    # bigger than hour (eg 2 hours, daily, weekly)
    upsample=False
    
    # calcul de la frequence de la série en nombre d'heures
    if TS_freq is None:
        raise ValueError("Impossible to infer frequency")
    if 'D' in TS_freq or 'W' in TS_freq or 'M' in TS_freq:
        upsample=True
        if 'D' in TS_freq:
            Hours_freq = int(TS_freq[:-1]) * 24 if len(TS_freq) > 1 else 24
        elif 'W' in TS_freq:
            if '-' in TS_freq: TS_freq=TS_freq.split('-')[0]
            Hours_freq = int(TS_freq[:-1]) * 168 if len(TS_freq) > 1 else 168
        elif 'M' in TS_freq:
            Hours_freq = int(TS_freq[:-1]) * 728 if len(TS_freq) > 1 else 728
                
    elif 'H' in TS_freq or 'h' in TS_freq:
        Hours_freq = int(TS_freq[:-1]) if len(TS_freq) > 1 else 1
        if Hours_freq>int(UCTimeStep): upsample=True
    else:
        raise ValueError(f"Unknown Frequency : {TS_freq}")

    TS_duration = TS.index[-1] - TS.index[0] + pd.Timedelta(hours=Hours_freq)
    desired_duration = dates['UCEnd'] - dates['UCBegin']

    # nombre d’extensions nécessaires
    n_extensions = int(np.ceil(desired_duration / TS_duration))

    # Construire la série étendue
    # Extension is a copy of TS on the extended dates UCBeginExtendedData and UCEndExtendedData 
    TS_extended = TS.copy()
    last_index = TS.index[-1]
    for i in range(n_extensions):
        shift = (i + 1) * TS_duration
        TS_shifted = TS.copy()
        TS_shifted.index = TS_shifted.index + shift
        TS_extended = pd.concat([TS_extended, TS_shifted])

    # case where timeserie is given at frequency bigger than hour
    # resample to hour frequecy before resampling to the required frequency
    if upsample:
        TS_extended=TS_extended.resample('h').ffill()        # convert to hourly frequency

        # extend with missing dates: duplicate last dates
        if TS_extended.index[-1]< dates['UCEnd']:
            dur_missing=dates['UCEnd']-TS_extended.index[-1] # compute duration of missing data
            Extension=TS_extended[ TS_extended.index> (TS_extended.index[-1]-dur_missing) ] # take last period of TS of this duration
            Extension.index=Extension.index+dur_missing # shift over time
            TS_extended=pd.concat([TS_extended,Extension]) # add at end of serie

        TS_extended=TS_extended.resample(newfreq).sum()
    else:
        TS_extended=TS_extended.resample(newfreq).sum()

    # keep only period of dataset
    TS_extended = TS_extended[
        (TS_extended.index >= dates['UCBegin']) &
        (TS_extended.index <= dates['UCEnd'])
    ]

    # case where there is only one value in TS_freq
    if len(TS_extended.index)==1:
        TS2 = TS_extended.copy()
        TS2.index=TS2.index+pd.Timedelta(hours=Hours_freq)
        TS_extended=pd.concat([TS_extended,TS2])
    return TS_extended

def read_deterministic_timeseries(cfg,datesData,dates,UCTimeStep):
    if 'DeterministicTimeSeries' in cfg:
        DeterministicTS=read_input_timeseries(cfg, cfg['DeterministicTimeSeries'], skiprows=0,index_col=0)
                                                                                                                
        DeterministicTS.index=parse_datetime_index(DeterministicTS.index,dayfirst=cfg['Calendar']['dayfirst'])
    
        DeterministicTS=ExtendAndResample('DET',DeterministicTS,dates,UCTimeStep)

        # add constant serie
        DeterministicTS['One']=1.0
        DeterministicTS['Zero']=0.0
    else:
        DeterministicTS=pd.DataFrame(index=datesData['start'])
        DeterministicTS.index=parse_datetime_index(DeterministicTS.index)
        DeterministicTS['One']=1.0
        DeterministicTS['Zero']=0.0
        DeterministicTS=ExtendAndResample('DET',DeterministicTS,dates,UCTimeStep)
    return DeterministicTS
    
def create_demand_scenarios(cfg,Nodes,Coupling,ZV,ListScenarios,DeterministicTimeSeries,dates,UCTimeStep):
    DemandScenarios=pd.Series(dtype=object)
    isEnergy=(cfg['Parameters']['ScenarisedData']['ActivePowerDemand']['MultiplyTimeSerieBy']=='Energy')
    for node in Nodes:
        firstPart=True
        for component in Coupling.loc['ActivePowerDemand']['Sum']:
            nameTS=ZV.loc[component,node]['Profile_Timeserie']
            valTS=ZV.loc[component,node]['value']
            # case without a profile
            if nameTS=='':
                if firstPart:
                    DemandScenarios.loc[node]=pd.DataFrame(columns=ListScenarios)
                    for col in ListScenarios: DemandScenarios.loc[node][col]=DeterministicTimeSeries['One']
                    firstPart=False
                else:
                    for col in ListScenarios: DemandScenarios.loc[node][col]=DemandScenarios.loc[node][col]+DeterministicTimeSeries['One']
            # read timeserie if deterministic
            elif '.csv' in nameTS: # stochastic OR deterministic series
                isDeterministic=False
                TS=read_input_timeseries(cfg, nameTS, skiprows=0,index_col=0)
                if len(TS.columns)==1: isDeterministic=True # the serie is deterministic
                    
                TS.index=parse_datetime_index(TS.index,dayfirst=cfg['Calendar']['dayfirst'])
                TS=ExtendAndResample(nameTS,TS,dates,UCTimeStep,isEnergy)
                    
                if firstPart:
                    DemandScenarios[node]=pd.DataFrame(index=TS.index,columns=ListScenarios)
                    if isDeterministic: 
                        for col in ListScenarios: DemandScenarios.loc[node][col]=valTS*TS[TS.columns.tolist()[0]]
                    else: DemandScenarios[node]=valTS*TS
                    firstPart=False
                else:
                    if isDeterministic:
                        for col in ListScenarios: DemandScenarios.loc[node][col]=DemandScenarios.loc[node][col]+valTS*TS[TS.columns.tolist()[0]]
                    else: DemandScenarios[node]=DemandScenarios.loc[node]+valTS*TS
                    
            else:
                # deterministic serie in DeterministicTimeSeries dataframe
                DTS=valTS*DeterministicTimeSeries[nameTS]
                if firstPart:
                    DemandScenarios.loc[node]=pd.DataFrame(columns=ListScenarios)
                    for col in ListScenarios: DemandScenarios.loc[node][col]=DTS
                    firstPart=False
                else:
                    for col in ListScenarios: DemandScenarios.loc[node][col]=DemandScenarios.loc[node][col]+DTS
                                                                                        
                
        
    return DemandScenarios
    
def create_inflows_scenarios(cfg,SS,ListScenarios,DeterministicTimeSeries,dates,UCTimeStep):
    isEnergy=(cfg['Parameters']['ScenarisedData']['Hydro:Inflows']['MultiplyTimeSerieBy']['reservoir']=='Energy')
    InflowsScenarios=pd.Series(dtype=object,index=SS.index)
    
    for reservoir in SS.index:
        nameTS=SS.loc[reservoir]['InflowsProfile']
        valTS=SS.loc[reservoir]['Inflows']
        # read timeserie 
        # case without a profile
        if nameTS=='':
            InflowsScenarios[reservoir]=pd.DataFrame(columns=ListScenarios)
            for col in ListScenarios: InflowsScenarios.loc[reservoir][col]=(valTS/cfg['Parameters']['NumberHoursInYear'])*DeterministicTimeSeries['One'] # valTS is an energy per year
        elif '.csv' in nameTS:  # stochastic series
            TS=read_input_timeseries(cfg, nameTS, index_col=0)
            TS.index=parse_datetime_index(TS.index,dayfirst=cfg['Calendar']['dayfirst'])
            TS=ExtendAndResample(nameTS,TS,dates,UCTimeStep,isEnergy)
            if len(TS.columns) > 1: # stochastic serie
                InflowsScenarios[reservoir]=pd.DataFrame(index=TS.index,columns=TS.columns)
                InflowsScenarios[reservoir]=valTS*TS
            else: # deterministic serie
                InflowsScenarios[reservoir]=pd.DataFrame(index=TS.index,columns=ListScenarios)
                for col in ListScenarios: InflowsScenarios.loc[reservoir][col]=valTS*TS[TS.columns.tolist()[0]]
        else:  # deterministic series
            DTS=valTS*DeterministicTimeSeries[nameTS]
            InflowsScenarios.loc[reservoir]=pd.DataFrame(columns=ListScenarios)
            for col in ListScenarios: InflowsScenarios.loc[reservoir][col]=DTS
                                                                                                    
                    
    return InflowsScenarios
    
def create_res_scenarios(cfg,RES,ListScenarios,DeterministicTimeSeries,dates,UCTimeStep):
    ResScenarios=pd.Series(dtype=object,index=RES.index)
    newIndex=[]
    for res in RES.index:
        nameTS=RES.loc[res]['MaxPowerProfile']
        valTS=RES.loc[res]['MaxPower']
        nameAsset=res[0]
        carrier=cfg['Technos']['RES'][nameAsset]['carrier']
        
        isEnergy=(cfg['Parameters']['ScenarisedData']['Renewable:MaxPowerProfile']['MultiplyTimeSerieBy'][carrier]=='Energy')
                    
        # read timeserie 
        if '.csv' in nameTS:  # stochastic series
            TS=read_input_timeseries(cfg, nameTS, skiprows=0,index_col=0)
            TS.index=parse_datetime_index(TS.index,dayfirst=cfg['Calendar']['dayfirst'])
            TS=ExtendAndResample(nameTS,TS,dates,UCTimeStep,isEnergy)
            if len(TS.columns) > 1: # stochastic serie
                ResScenarios[res]=pd.DataFrame(index=TS.index,columns=TS.columns)
                #ResScenarios[res]=valTS*TS
                ResScenarios[res]=TS
                
            else: #deterministic
                ResScenarios[res]=pd.DataFrame(index=TS.index,columns=ListScenarios)
                for col in ListScenarios: ResScenarios[res][col]=valTS*TS[TS.columns.tolist()[0]]
                
            newIndex.append(res)
    
    
    ResScenarios=ResScenarios[ newIndex ]
    return ResScenarios
    
def create_thermal_scenarios(cfg,TU,ListScenarios,DeterministicTimeSeries,dates,UCTimeStep):
    # define wether there is one profile per techno/region, or one profile per unit
    newIndex=[]
    isEnergy=(cfg['Parameters']['ScenarisedData']['Thermal:MaxPowerProfile']['MultiplyTimeSerieBy']=='Energy')

    if True in np.column_stack(TU['MaxPowerProfile'].str.contains(r",", na=False)): # there exist multiple profiles for the same row
        multipleTHSeries=True
        listIndexes=[list(TU.index[0]),list(TU.index[1]),list(range(TU['NumberUnits'].max()))]
        ThermalScenarios=pd.Series(dtype=object,index=pd.MultiIndex.from_tuples((list(product(*listIndexes)))))
        for th in TU.index:
            for unit in range(TU.loc[th]['NumberUnits']):
                if ',' in str(TU.loc[th]['MaxPowerProfile']):
                    nameTS=TU.loc[th]['MaxPowerProfile'].split(',')[unit]
                else:
                    nameTS=TU.loc[th]['MaxPowerProfile']
                valTS=TU.loc[th]['MaxPower']
                
                # read timeserie 
                if '.csv' in nameTS:  # stochastic series
                    TS=read_input_timeseries(cfg, nameTS,skiprows=0,index_col=0)
                    TS.index=parse_datetime_index(TS.index,dayfirst=cfg['Calendar']['dayfirst'])
                    TS=ExtendAndResample(nameTS,TS,dates,UCTimeStep,isEnergy)
                    
                    if len(TS.columns) > 1: # stochastic serie
                        ThermalScenarios[th[0],th[1],unit]=pd.DataFrame(index=TS.index,columns=TS.columns)
                        ThermalScenarios[th[0],th[1],unit]=valTS*TS
                    else:
                        ThermalScenarios[th[0],th[1],unit]=pd.DataFrame(index=TS.index,columns=ListScenarios)
                        for col in ListScenarios: ThermalScenarios[th[0],th[1],unit]=valTS*TS[TS.columns.tolist()[0]]
                    newIndex.append( (th[0],th[1],unit) )
    else:
        multipleTHSeries=False
        ThermalScenarios=pd.Series(dtype=object,index=TU.index)
        for th in TU.index:
            nameTS=TU.loc[th]['MaxPowerProfile']
            valTS=TU.loc[th]['MaxPower']
            
            # read timeserie 
            if '.csv' in nameTS:  # stochastic series
                TS=read_input_timeseries(cfg,nameTS,skiprows=0,index_col=0)
                TS.index=parse_datetime_index(TS.index,dayfirst=cfg['Calendar']['dayfirst'])
                TS=ExtendAndResample(nameTS,TS,dates,UCTimeStep)
                
                if len(TS.columns) > 1: # stochastic serie
                    ThermalScenarios[th]=pd.DataFrame(index=TS.index,columns=TS.columns)
                    ThermalScenarios[th]=valTS*TS
                else:
                    ThermalScenarios[th]=pd.DataFrame(index=TS.index,columns=ListScenarios)
                    for col in ListScenarios: ThermalScenarios[th]=valTS*TS[TS.columns.tolist()[0]]
            newIndex.append(th)
    
    ThermalScenarios=ThermalScenarios[newIndex]
    return ThermalScenarios

    #################################################################################################################################################
    #                                                                                                                                                #
    #                                            Read timeseries                                                                                        #
    #                                                                                                                                                #
    #                                                                                                                                                #
    #################################################################################################################################################
    
def centroid_country(
    country_name: str,
    geojson_path: str ,
    field_name: str = "name",           # Nom du champ contenant le nom du pays dans ton GeoJSON
    allow_partial: bool = True,         # True => appariement partiel (substring)
    use_representative_point: bool = False,  # True => point garanti à l'intérieur du polygone
    prefer_largest_part: bool = True,   # True => pour MultiPolygon, prendre la plus grande partie
) -> Tuple[float, float]:
    """
    Computes (x, y) = (longitude, latitude WGS84) du centroïde du pays `country_name`
    à partir d'un GeoJSON (1 ligne = 1 pays avec sa géométrie).

    Parameters
    ----------
    
    country_name : str
        Nom (ou sous-chaîne) du pays à chercher (insensible à la casse).
    geojson_path : str
        Chemin du fichier GeoJSON (Polygon ou MultiPolygon par pays).
    field_name : str
        Nom du champ attributaire qui contient le nom du pays.
    allow_partial : bool
        Si True, permet la recherche par sous-chaîne si pas d'égalité exacte.
    use_representative_point : bool
        Si True, utilise `representative_point()` (toujours dans le polygone) plutôt que `centroid`.
    prefer_largest_part : bool
        Si True et si le pays est un MultiPolygon, calcule le centroïde de la plus grande partie.

    Retour
    ------
    (lon, lat) : Tuple[float, float]
        Coordonnées WGS84 du centroïde (longitude, latitude).

    Exceptions
    ----------
    FileNotFoundError : si le fichier n'existe pas.
    ValueError : si le pays est introuvable ou si la géométrie est vide.
    """
    # 1) Lire le GeoJSON
    gdf = gpd.read_file(geojson_path)
    if gdf.empty:
        raise ValueError("Le GeoJSON ne contient aucune géométrie.")

    # 2) S'assurer d'un CRS
    #    Si ton GeoJSON n'a pas de CRS défini mais est bien en WGS84, on force EPSG:4326
    if gdf.crs is None:
        gdf = gdf.set_crs(epsg=4326)

    # 3) Filtrer sur le champ des noms
    if field_name not in gdf.columns:
        raise ValueError(f"Champ '{field_name}' introuvable dans le GeoJSON.")

    name_norm = country_name.strip().lower()
    names_series = gdf[field_name].astype(str)

    # a) essai correspondance exacte
    mask_exact = names_series.str.strip().str.lower() == name_norm
    candidates = gdf[mask_exact]

    # b) sinon, correspondance partielle
    if candidates.empty and allow_partial:
        mask_part = names_series.str.strip().str.lower().str.contains(name_norm, regex=False)
        candidates = gdf[mask_part]

    if candidates.empty:
        raise ValueError(f"Pays introuvable pour '{country_name}' via le champ '{field_name}'.")

    # Si plusieurs lignes correspondent (homonymes, territoires), on garde la plus grande surface
    if len(candidates) > 1:
        candidates_eq = candidates.to_crs("EPSG:6933")
        idx = candidates_eq.geometry.area.idxmax()
        candidates = candidates.loc[[idx]]

    geom = candidates.geometry.iloc[0]
    if geom is None or geom.is_empty:
        raise ValueError(f"Géométrie vide pour '{country_name}'.")

    # 4) Option : pour un MultiPolygon, ne garder que la plus grande partie
    if prefer_largest_part and isinstance(geom, MultiPolygon):
        parts = list(geom.geoms)
        parts_gdf = gpd.GeoDataFrame(geometry=parts, crs=gdf.crs).to_crs("EPSG:6933")
        largest = parts_gdf.loc[parts_gdf.geometry.area.idxmax()].geometry
        # Reprojetter cette partie en CRS source (au cas où)
        largest = gpd.GeoSeries([largest], crs="EPSG:6933").to_crs(gdf.crs).iloc[0]
        geom = largest

    # 5) Calcul du centroïde (ou point représentatif) en égale-aire, puis retour WGS84
    one = gpd.GeoDataFrame(geometry=[geom], crs=gdf.crs).to_crs("EPSG:6933")
    if use_representative_point:
        pt_eq = one.geometry.representative_point().iloc[0]
    else:
        pt_eq = one.geometry.centroid.iloc[0]

    pt_wgs84 = gpd.GeoSeries([pt_eq], crs="EPSG:6933").to_crs(epsg=4326).iloc[0]
    lon, lat = float(pt_wgs84.x), float(pt_wgs84.y)
    return lon, lat  

def create_map(cfg,list_regions):
    print('create map')
    listcountrymap=list_regions
    if 'nameregions' in cfg.keys(): listcountrymap=cfg['nameregions']
    
    if 'private_map' in cfg:
        print('use private map')
        file_extension = os.path.splitext(cfg['private_map'])[1] 
        if file_extension == '.csv':
            df_continent = pd.read_csv(os.path.join(cfg['inputDir'],cfg['private_map']),index_col=0)
            df_continent['geometry'] = df_continent['geometry'].apply(wkt.loads)
            continent=gpd.GeoDataFrame(df_continent, crs='epsg:4326')
        elif file_extension == '.geojson':
            continent = gpd.read_file(os.path.join(cfg['inputDir'],cfg['private_map']))
            continent = continent.to_crs(epsg=4326)						   
        else:
            print('unrecognised map file: maps will not be created')	
            sys.exit(2)											 
    else:
        print('this function only works with a private map, to define in settings')
        sys.exit(2)
        
    continent['Aggr']=continent['name']
    continent['country']=continent['name']
    continent['index']=continent['name']
    continent=continent.set_index('index')
    if cfg['aggregateregions']:
        for Aggr in cfg['aggregateregions']:
            for country in cfg['aggregateregions'][Aggr]:
                continent.loc[country,'Aggr']=Aggr
    else: 
        print('no aggregated regions')

    # create list of countries and sample of values (to delete)
    mycountries=[]
    myvalue=[]
    i=0
    for country in listcountrymap:
        if cfg['aggregateregions']:
            if country in cfg['aggregateregions']: 
                #if not (cfg['countryaggregates'] and country in cfg['countryaggregates']):
                for smallcountry in cfg['aggregateregions'][country]:
                    mycountries.append(smallcountry)
                else:
                    mycountries.append(country)
            else: mycountries.append(country)
        else:
            mycountries.append(country)
    # keep only country names and geometry
    continent['name']=continent['Aggr']
    
    #continent = continent[ ['continent','name','Aggr','country','geometry','pop_est'] ]
    continent = continent[ ['continent','name','Aggr','country','geometry'] ]																		   
    continent['isin']=0
    for i in continent.index:
        if continent.loc[i,'country'] in mycountries: 
            continent.at[i,'isin']=1
    mycontinent = continent [ continent['isin'] ==1 ]
    restofcontinent = continent [ continent['isin'] == 0 ]
    del mycontinent['isin']
    del restofcontinent['isin']

    # aggregate countries in the map
    if cfg['aggregateregions']: 
        mycontinent["geometry"] = mycontinent.buffer(0)
        mycontinent = mycontinent.dissolve(by='Aggr')

    # compute representative point of countries and get their coordinates
    centers=mycontinent.representative_point()
    numcenters=pd.Series(mycontinent.index,index=mycontinent['name'])
    mycontinent['x']=centers.x
    mycontinent['y']=centers.y
    mycontinent['centers']=centers
    mycontinent=mycontinent.set_index('name')

    return mycontinent  
    
