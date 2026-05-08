import pandas as pd
from datetime import datetime
import numpy as np
import re
from fuzzywuzzy import fuzz


# Integrates all datasets
def integrate_datasets(trees, open_wifi, historic_shops, benches, picnic_tables, vedovelle_fountains, nils, wikidata_pois,
                       addressless_entities):
    # Data preparation
    trees = tree_data_preparation(trees)
    open_wifi = open_wifi_data_preparation(open_wifi)
    historic_shops = historic_shop_data_preparation(historic_shops)
    benches = bench_data_preparation(benches)
    picnic_tables = picnic_table_data_preparation(picnic_tables)
    vedovelle_fountains = vedovelle_fountain_data_preparation(vedovelle_fountains)
    nils = nil_data_preparation(nils)
    wikidata_pois = wikidata_poi_data_preparation(wikidata_pois)
    
    # trees AND open_wifi
    integrated_dataset = merge_datasets(trees, open_wifi,
                                        ['latitudine', 'longitudine', 'Location', 'indirizzo', 'civico',
                                         'municipio', 'categoria', 'nome_dataset', 'last_update'],
                                        'ID_ALBERO_ANTENNA', 'id_antenna', 2, 'trees_open-wifi.csv')

    # trees-open_wifi AND historic_shops
    wikidata_pois, historic_shops = check_pois(wikidata_pois, historic_shops)
    integrated_dataset = merge_datasets(integrated_dataset, historic_shops,
                                        ['latitudine', 'longitudine', 'Location', 'indirizzo', 'civico', 'municipio',
                                         'id_NIL', 'NIL', 'categoria', 'nome_dataset', 'last_update'],
                                         'ID_ALBERO_ANTENNA_BOTTEGA', 'id_bottega', 4, 'trees_open-wifi_historic-shops.csv')

    # trees-open_wifi-historic_shops AND benches
    integrated_dataset = merge_datasets(integrated_dataset, benches,
                                        ['latitudine', 'longitudine', 'Location', 'indirizzo', 'civico', 'municipio',
                                         'data_origine', 'categoria', 'nome_dataset', 'last_update'],
                                         'ID_ALBERO_ANTENNA_BOTTEGA_PANCHINA', 'id_panchina', 6,
                                         'trees_open-wifi_historic-shops_benches.csv')

    # trees-open_wifi-historic_shops-benches AND picnic_tables
    integrated_dataset = merge_datasets(integrated_dataset, picnic_tables,
                                        ['latitudine', 'longitudine', 'Location', 'indirizzo', 'civico', 'municipio',
                                         'data_origine', 'categoria', 'nome_dataset', 'last_update'],
                                         'ID_ALBERO_ANTENNA_BOTTEGA_PANCHINA_TAVOLO', 'id_tavolo', 8,
                                         'trees_open-wifi_historic-shops_benches_picnic-tables.csv')
    
    # trees-open_wifi-historic_shops-benches-picnic_tables AND vedovelle_fountains
    integrated_dataset = merge_datasets(integrated_dataset, vedovelle_fountains,
                                        ['latitudine', 'longitudine', 'Location', 'municipio', 'CAP', 'id_NIL', 'NIL',
                                         'categoria', 'nome_dataset', 'last_update'],
                                         'ID_ALBERO_ANTENNA_BOTTEGA_PANCHINA_TAVOLO_FONTANA', 'id_fontana', 10,
                                         'trees_open-wifi_historic-shops_benches_picnic-tables_vedovelle-fountains.csv')
    
    # trees-open_wifi-historic_shops-benches-picnic_tables-vedovelle_fountains AND nils
    integrated_dataset = merge_datasets(integrated_dataset, nils,
                                        ['latitudine', 'longitudine', 'Location', 'id_NIL', 'NIL', 'data_origine',
                                         'categoria', 'nome_dataset', 'last_update'],
                                         'ID_ALBERO_ANTENNA_BOTTEGA_PANCHINA_TAVOLO_FONTANA_NIL', 'id_NIL', 12,
                                         'trees_open-wifi_historic-shops_benches_picnic-tables_vedovelle-fountains_nils.csv')
    
    # trees-open_wifi-historic_shops-benches-picnic_tables-vedovelle_fountains-nils AND wikidata_pois
    integrated_dataset['CAP'] = [str(row)[:5] for row in integrated_dataset['CAP']]
    integrated_dataset = merge_datasets(integrated_dataset, wikidata_pois,
                                        ['latitudine', 'longitudine', 'Location', 'indirizzo', 'civico', 'Città', 'CAP',
                                         'categoria', 'nome_dataset', 'last_update', 'ent_WDPOI', 'P1566_WDPOI'],
                                         'ID_ALBERO_ANTENNA_BOTTEGA_PANCHINA_TAVOLO_FONTANA_NIL_WDPOI', 'id_WDPOI', 14,
                                         'trees_open-wifi_historic-shops_benches_picnic-tables_vedovelle-fountains_nils_wikidata-pois.csv')
    
    # Final column cleaning
    integrated_dataset.rename(columns={'ID_ALBERO_ANTENNA_BOTTEGA_PANCHINA_TAVOLO_FONTANA_NIL_WDPOI': 'ID_ENTITA'}, inplace=True)
    integrated_dataset = set_id_dataset_originale(integrated_dataset)
    integrated_dataset.drop(columns=['ID_ALBERO_ANTENNA_BOTTEGA_PANCHINA_TAVOLO_FONTANA_NIL',
                                     'ID_ALBERO_ANTENNA_BOTTEGA_PANCHINA_TAVOLO_FONTANA',
                                     'ID_ALBERO_ANTENNA_BOTTEGA_PANCHINA_TAVOLO', 'ID_ALBERO_ANTENNA_BOTTEGA_PANCHINA',
                                     'ID_ALBERO_ANTENNA_BOTTEGA', 'ID_ALBERO_ANTENNA', 'id_albero', 'id_antenna', 'id_bottega',
                                     'id_panchina', 'id_tavolo', 'id_fontana', 'id_NIL', 'id_WDPOI', 'streetAddress_WDPOI'],
                                     inplace=True)
    integrated_dataset = move_column(integrated_dataset, 'id_dataset_originale', 1)
    integrated_dataset = move_column(integrated_dataset, 'nome_dataset', 2)
    integrated_dataset = move_column(integrated_dataset, 'last_update', 3)
    #integrated_dataset.to_csv('integrated_datasets/integrated_dataset.csv', sep=';', index=False)

    # integrated_dataset AND addressless_entities
    addressless_entities = addressless_entities_data_preparation(addressless_entities)
    integrated_dataset = merge_final_datasets(integrated_dataset, addressless_entities)
    integrated_dataset['Città'] = 'MILANO'
    integrated_dataset = split_categories(integrated_dataset)
    integrated_dataset.to_csv('integrated_datasets/integrated_dataset.csv', sep=';', index=False)


# Tree data preparation
def tree_data_preparation(trees):
    trees = split_address_civic_number(trees)
    trees[['data_origine', 'ora_fuso_orario_origine']] = trees['data_ini'].str.split('T', expand=True)
    trees.drop(columns=['id_area', 'area', 'obj_id', 'None', 'localita', 'ora_fuso_orario_origine', 'data_ini'],
               inplace=True)
    trees = convert_to_date(trees, 'data_origine')
    trees = rename_long_lat_columns(trees, 'LONG_X_4326', 'LAT_Y_4326')
    trees.insert(0, column='id', value=[x for x in range(1, len(trees.index) + 1)])
    trees['categoria'] = 'albero'
    trees['nome_dataset'] = 'Territorio: localizzazione degli alberi'
    trees['last_update'] = '2023-10-26'
    trees = convert_to_date(trees, 'last_update')
    trees = move_column(trees, 'indirizzo', 2)
    trees = move_column(trees, 'civico', 3)
    trees = move_column(trees, 'data_origine', 5)
    trees = add_column_suffix(trees, '_albero')
    return trees


# Open Wi-Fi data preparation
def open_wifi_data_preparation(open_wifi):
    open_wifi['indirizzo'] = open_wifi['VIA___P_zza___Corso'].str.lower() + ' ' + open_wifi['Indirizzo']
    open_wifi.drop(columns=['OBJECTID', 'Area', 'VIA___P_zza___Corso', 'Indirizzo'], inplace=True)
    open_wifi.rename(columns={'Civico': 'civico', 'MUNICIPIO': 'municipio', 'ID_NIL': 'id_NIL'}, inplace=True)
    open_wifi = rename_long_lat_columns(open_wifi, 'LONG_X_4326', 'LAT_Y_4326')
    open_wifi.insert(0, column='id', value=[x for x in range(1, len(open_wifi.index) + 1)])
    open_wifi['categoria'] = 'wi-fi'
    open_wifi['nome_dataset'] = 'Amministrazione Comunale: localizzazione delle antenne di Open WiFi Milano Outdoor'
    open_wifi['last_update'] = '2024-07-02'
    open_wifi = convert_to_date(open_wifi, 'last_update')
    open_wifi = move_column(open_wifi, 'indirizzo', 3)
    open_wifi = add_column_suffix(open_wifi, '_antenna')
    return open_wifi


# Historic shop data preparation
def historic_shop_data_preparation(historic_shops):
    historic_shops.rename(columns={'INDIRIZZO': 'indirizzo', 'CIVICO': 'civico', 'MUNICIPIO': 'municipio',
                                   'GENERE MERCEOLOGICO': 'categoria', 'ID_NIL': 'id_NIL'}, inplace=True)
    historic_shops = rename_long_lat_columns(historic_shops, 'LONG_X_4326', 'LAT_Y_4326')
    historic_shops['indirizzo'] = historic_shops['indirizzo'].replace({'Via': 'via', 'Piazza': 'piazza', 'P.zza': 'piazza',
                                                                       'P.le': 'piazzale', 'C.so': 'corso', 'L.go': 'largo',
                                                                       'V.le': 'viale'}, regex=True)
    historic_shops['attivita_storica'] = 'Si'
    historic_shops['nome_dataset'] = 'Attività commerciali: botteghe storiche'
    historic_shops['last_update'] = '2023-02-01'
    historic_shops = convert_to_date(historic_shops, 'last_update')
    historic_shops = add_column_suffix(historic_shops, '_bottega')
    return historic_shops


# Bench data preparation
def bench_data_preparation(benches):
    benches = split_address_civic_number(benches)
    benches.drop(columns=['id_area', 'area', 'obj_id', 'None', 'localita'], inplace=True)
    benches.rename(columns={'data_ini': 'data_origine'}, inplace=True)
    benches = convert_to_date(benches, 'data_origine')
    benches = rename_long_lat_columns(benches, 'LONG_X_4326', 'LAT_Y_4326')
    benches.insert(0, column='id', value=[x for x in range(1, len(benches.index) + 1)])
    benches['categoria'] = 'panchina'
    benches['nome_dataset'] = 'Territorio: localizzazione delle panchine'
    benches['last_update'] = '2024-06-14'
    benches = convert_to_date(benches, 'last_update')
    benches = move_column(benches, 'indirizzo', 2)
    benches = move_column(benches, 'civico', 3)
    benches = add_column_suffix(benches, '_panchina')
    return benches


# Pic-nic table data preparation
def picnic_table_data_preparation(picnic_tables):
    picnic_tables[['indirizzo', 'civico']] = picnic_tables['localita'].str.split(' n. ', expand=True)
    picnic_tables.drop(columns=['id_area', 'area', 'obj_id', 'localita'], inplace=True)
    picnic_tables.rename(columns={'data_ini': 'data_origine'}, inplace=True)
    picnic_tables = convert_to_date(picnic_tables, 'data_origine')
    picnic_tables = rename_long_lat_columns(picnic_tables, 'LONG_X_4326', 'LAT_Y_4326')
    picnic_tables.insert(0, column='id', value=[x for x in range(1, len(picnic_tables.index) + 1)])
    picnic_tables['categoria'] = 'tavolo'
    picnic_tables['nome_dataset'] = 'Territorio: localizzazione dei tavoli da picnic'
    picnic_tables['last_update'] = '2024-06-14'
    picnic_tables = convert_to_date(picnic_tables, 'last_update')
    picnic_tables = move_column(picnic_tables, 'indirizzo', 2)
    picnic_tables = move_column(picnic_tables, 'civico', 3)
    picnic_tables = add_column_suffix(picnic_tables, '_tavolo')
    return picnic_tables


# Vedovelle fountain data preparation
def vedovelle_fountain_data_preparation(vedovelle_fountains):
    vedovelle_fountains.drop(columns='objectID', inplace=True)
    vedovelle_fountains.rename(columns={'MUNICIPIO': 'municipio', 'ID_NIL': 'id_NIL'}, inplace=True)
    vedovelle_fountains = rename_long_lat_columns(vedovelle_fountains, 'LONG_X_4326', 'LAT_Y_4326')
    vedovelle_fountains.insert(0, column='id_fontana', value=[x for x in range(1, len(vedovelle_fountains.index) + 1)])
    vedovelle_fountains['categoria'] = 'fontana'
    vedovelle_fountains['nome_dataset'] = 'Vedovelle (fontanelle) nel Comune di Milano'
    vedovelle_fountains['last_update'] = '2024-07-08'
    vedovelle_fountains = convert_to_date(vedovelle_fountains, 'last_update')
    return vedovelle_fountains


# NIL data preparation
def nil_data_preparation(nils):
    nils.rename(columns={'ID_NIL': 'id_NIL', 'Valido_dal': 'data_origine'}, inplace=True)
    nils['data_origine'] = pd.to_datetime(nils['data_origine'])
    nils['data_origine'] = [str(row) for row in nils['data_origine']]
    nils[['data_origine', 'ora_fine_validita']] = nils['data_origine'].str.split(' ', expand=True)
    nils.drop(columns=['OBJECTID', 'Valido_al', 'ora_fine_validita'], inplace=True)
    nils = convert_to_date(nils, 'data_origine')
    nils = rename_long_lat_columns(nils, 'LONG_X_4326_CENTROID', 'LAT_Y_4326_CENTROID')
    nils['categoria'] = 'NIL'
    nils['nome_dataset'] = 'Nuclei d\'Identità Locale (NIL) VIGENTI - PGT 2030'
    nils['last_update'] = '2021-02-12'
    nils = convert_to_date(nils, 'last_update')
    nils = add_column_suffix(nils, '_NIL')
    return nils


# Wikidata POI data preparation
def wikidata_poi_data_preparation(wikidata_pois):
    wikidata_pois.columns = wikidata_pois.columns.str.replace('original_', '')
    wikidata_pois = wikidata_pois[['ent', 'entLabel', 'coord', 'categoryLabels', 'P1566', 'streetAddress', 'description',
                                   'housenumber', 'street', 'postcode']]
    wikidata_pois[['longitudine', 'latitudine']] = wikidata_pois['coord'].str.split(', ', expand=True)
    wikidata_pois['longitudine'] = [float(row[1:]) for row in wikidata_pois['longitudine']]
    wikidata_pois['latitudine'] = [float(row[:-1]) for row in wikidata_pois['latitudine']]
    #wikidata_pois = fix_coord_syntax(wikidata_pois)
    wikidata_pois.rename(columns={'coord': 'Location', 'categoryLabels': 'categoria', 'housenumber': 'civico',
                                  'street': 'indirizzo', 'postcode': 'CAP'}, inplace=True)
    wikidata_pois['streetAddress'] = [str(row) for row in wikidata_pois['streetAddress']]
    wikidata_pois['civico'] = [str(row) for row in wikidata_pois['civico']]
    wikidata_pois['indirizzo'] = [str(row) for row in wikidata_pois['indirizzo']]
    wikidata_pois['CAP'] = [str(row) for row in wikidata_pois['CAP']]
    for row in range(len(wikidata_pois)):
        if len(wikidata_pois.at[row, 'civico']) > 3:
            wikidata_pois.at[row, 'civico'] = 'nan'
        if len(wikidata_pois.at[row, 'CAP']) != 5 or wikidata_pois.at[row, 'CAP'] == 'Isola':
            wikidata_pois.at[row, 'CAP'] = 'nan'
        if wikidata_pois.at[row, 'streetAddress'] == 'nan' and wikidata_pois.at[row, 'indirizzo'] != 'nan':
            street_address = wikidata_pois.at[row, 'indirizzo']
            if wikidata_pois.at[row, 'civico'] != 'nan':
                street_address += ', ' + wikidata_pois.at[row, 'civico']
            if wikidata_pois.at[row, 'CAP'] != 'nan':
                street_address += ', ' + wikidata_pois.at[row, 'CAP']
            wikidata_pois.at[row, 'streetAddress'] = street_address
    wikidata_pois.insert(0, column='id', value=[x for x in range(1, len(wikidata_pois.index) + 1)])
    wikidata_pois['Città'] = 'MILANO'
    wikidata_pois['wikidata_POI'] = 'Si'
    wikidata_pois['nome_dataset'] = 'Wikidata'
    wikidata_pois['last_update'] = '2024-07-31'
    wikidata_pois = convert_to_date(wikidata_pois, 'last_update')
    wikidata_pois.drop_duplicates(subset=['ent'], inplace=True)
    wikidata_pois = wikidata_pois[wikidata_pois['categoria'].str.contains('nucleo di identità locale di Milano') == False]
    wikidata_pois.reset_index(drop=True, inplace=True)
    wikidata_pois = add_column_suffix(wikidata_pois, '_WDPOI')
    return wikidata_pois


# Addressless entities data preparation
def addressless_entities_data_preparation(addressless_entities):
    addressless_entities.columns = addressless_entities.columns.str.replace('original_', '')
    addressless_entities.drop(columns=['civico', 'indirizzo', 'CAP', 'distance', 'formatted', 'lat', 'lon', 'name', 'district',
                                       'suburb', 'city', 'county', 'county_code', 'state', 'state_code', 'country', 'country_code',
                                       'attribution', 'attribution_license', 'attribution_url'], inplace=True)
    addressless_entities.rename(columns={'housenumber': 'civico', 'street': 'indirizzo', 'postcode': 'CAP'}, inplace=True)
    addressless_entities['codice_albero'] = [str(row) for row in addressless_entities['codice_albero']]
    addressless_entities['genere_albero'] = [str(row) for row in addressless_entities['genere_albero']]
    addressless_entities['specie_albero'] = [str(row) for row in addressless_entities['specie_albero']]
    addressless_entities['varieta_albero'] = [str(row) for row in addressless_entities['varieta_albero']]
    addressless_entities['Funzionante_antenna'] = [str(row) for row in addressless_entities['Funzionante_antenna']]
    addressless_entities['Città'] = [str(row) for row in addressless_entities['Città']]
    addressless_entities['NIL'] = [str(row) for row in addressless_entities['NIL']]
    addressless_entities['TARGA_bottega'] = [str(row) for row in addressless_entities['TARGA_bottega']]
    addressless_entities['attivita_storica'] = [str(row) for row in addressless_entities['attivita_storica']]
    addressless_entities['ent_WDPOI'] = [str(row) for row in addressless_entities['ent_WDPOI']]
    addressless_entities['codice_panchina'] = [str(row) for row in addressless_entities['codice_panchina']]
    addressless_entities['descrizione_codice_panchina'] = [str(row) for row in addressless_entities['descrizione_codice_panchina']]
    addressless_entities['codice_tavolo'] = [str(row) for row in addressless_entities['codice_tavolo']]
    addressless_entities['descrizione_codice_tavolo'] = [str(row) for row in addressless_entities['descrizione_codice_tavolo']]
    addressless_entities['Fonte_NIL'] = [str(row) for row in addressless_entities['Fonte_NIL']]
    addressless_entities['entLabel_WDPOI'] = [str(row) for row in addressless_entities['entLabel_WDPOI']]
    addressless_entities['wikidata_POI'] = [str(row) for row in addressless_entities['wikidata_POI']]
    return addressless_entities


# Splits address and civic number into two columns
def split_address_civic_number(dataset):
    dataset[['indirizzo', 'civico', 'None']] = dataset['localita'].str.split(' n. ', expand=True)
    return dataset


# Converts values into str format and then into date format
def convert_to_date(dataset, column_name):
    dataset[column_name] = [str(row) for row in dataset[column_name]]
    dataset[column_name] = dataset[column_name].replace({'/': '-'}, regex=True)
    dataset[column_name] = [datetime.strptime(row, '%Y-%m-%d').date() if row != 'nan' else row for row in dataset[column_name]]
    return dataset


# Renames longitude and latitude columns to be merged
def rename_long_lat_columns(dataset, long, lat):
    dataset.rename(columns={long: 'longitudine', lat: 'latitudine'}, inplace=True)
    return dataset


# Adds suffixes to all columns except for those ones to be merged
def add_column_suffix(dataset, suffix):
    dataset.rename(columns={c: c + suffix for c in dataset.columns
                            if c not in ['longitudine', 'latitudine', 'Location', 'indirizzo', 'civico', 'municipio',
                                         'id_NIL', 'NIL', 'Città', 'CAP', 'data_origine', 'categoria', 'attivita_storica',
                                         'nome_dataset', 'last_update', 'Shape_Length', 'Shape_Area', 'wikidata_POI']},
                                         inplace=True)
    return dataset


# Moves columns in the integrated dataset
def move_column(dataset, column_name, position):
    values = dataset.pop(column_name)
    dataset.insert(position, column_name, values)
    return dataset


# Fixes coordinate pair syntax to be merged
def fix_coord_syntax(wikidata_pois):
    coord = []
    for index, row in wikidata_pois.iterrows():
        coord.append(row['coord'][5:].replace(' ', ', '))
    wikidata_pois['coord'] = coord
    return wikidata_pois


# Merges two datasets
def merge_datasets(dataset1, dataset2, on_list, integration_id_column, dataset2_id_column, position, filename):
    integrated_dataset = pd.merge(dataset1, dataset2, on=on_list, how='outer')
    integrated_dataset.insert(0, column=integration_id_column, value=[x for x in range(1, len(integrated_dataset.index) + 1)])
    integrated_dataset = move_column(integrated_dataset, dataset2_id_column, position)
    integrated_dataset.to_csv('integrated_datasets/' + filename, sep=';', index=False)
    return integrated_dataset


# Takes id columns from original datasets and sets only one with those values
def set_id_dataset_originale(dataset):
    id_columns = dataset.filter(regex='id').columns.tolist()
    for row in range(len(dataset)):
        for col in id_columns:
            if np.isnan(dataset.at[row, 'id_albero']):
                dataset.at[row, 'id_albero'] = dataset.at[row, col]
    dataset['id_dataset_originale'] = dataset['id_albero']
    return dataset


# Checks if a Wikidata POI already exists in the historic shop dataset and updates its information
def check_pois(wikidata_pois, historic_shops):
    historic_shops['TARGA_bottega'] = [str(row) for row in historic_shops['TARGA_bottega']]
    historic_shops['indirizzo'] = [str(row) for row in historic_shops['indirizzo']]
    wikidata_pois['entLabel_WDPOI'] = [str(row) for row in wikidata_pois['entLabel_WDPOI']]
    wikidata_pois['streetAddress_WDPOI'] = [str(row) for row in wikidata_pois['streetAddress_WDPOI']]
    wd_indexes = []
    for wd_row in range(len(wikidata_pois)):
        for hs_row in range(len(historic_shops)):
            if wikidata_pois.at[wd_row, 'streetAddress_WDPOI'] != 'nan' and historic_shops.at[hs_row, 'civico'] != 'nan':
                numbers = extract_numbers(wikidata_pois.at[wd_row, 'streetAddress_WDPOI'])
                civic_number_found = is_civic_number_found(historic_shops.at[hs_row, 'civico'], numbers)
                if fuzz.token_set_ratio(wikidata_pois.at[wd_row, 'entLabel_WDPOI'].lower(), historic_shops.at[hs_row, 'TARGA_bottega'].lower()) > 85 and fuzz.token_set_ratio(wikidata_pois.at[wd_row, 'streetAddress_WDPOI'].lower(), historic_shops.at[hs_row, 'indirizzo'].lower()) > 85 and civic_number_found:
                    historic_shops.at[hs_row, 'ent_WDPOI'] = wikidata_pois.at[wd_row, 'ent_WDPOI']
                    historic_shops.at[hs_row, 'P1566_WDPOI'] = wikidata_pois.at[wd_row, 'P1566_WDPOI']
                    wd_indexes.append(wd_row)
    wikidata_pois.drop(index=wd_indexes, inplace=True)
    wikidata_pois.reset_index(drop=True, inplace=True)
    return wikidata_pois, historic_shops


# Extracts numbers (civic number and/or postcode) from the address in Wikidata dataset
def extract_numbers(street_address):
    numbers = re.findall(r'\d+', street_address)
    return numbers if numbers else None


# Checks if the civic number in the historic shop dataset is in the address in Wikidata dataset
def is_civic_number_found(civic_number, numbers):
    civic_number_string = str(civic_number)
    found = False
    if numbers != None:
        for x in numbers:
            if civic_number_string == x and not found:
                found = True
    else:
        found = True
    return found


# Adds the complete address to addressless entities in the final integrated dataset
def merge_final_datasets(integrated_dataset, addressless_entities):
    addressless_entities['civico'] = [str(row) for row in addressless_entities['civico']]
    addressless_entities['indirizzo'] = [str(row) for row in addressless_entities['indirizzo']]
    addressless_entities['CAP'] = [str(row) for row in addressless_entities['CAP']]
    for ae_row in range(len(addressless_entities)):
        for id_row in range(len(integrated_dataset)):
            if addressless_entities.at[ae_row, 'ID_ENTITA'] == integrated_dataset.at[id_row, 'ID_ENTITA']:
                if addressless_entities.at[ae_row, 'civico'] != 'nan':
                    integrated_dataset.at[id_row, 'civico'] = addressless_entities.at[ae_row, 'civico']
                if addressless_entities.at[ae_row, 'indirizzo'] != 'nan':
                    integrated_dataset.at[id_row, 'indirizzo'] = addressless_entities.at[ae_row, 'indirizzo']
                if addressless_entities.at[ae_row, 'CAP'] != 'nan':
                    integrated_dataset.at[id_row, 'CAP'] = addressless_entities.at[ae_row, 'CAP']
    return integrated_dataset


# Splits every category in a column
def split_categories(integrated_dataset):
    for row in range(len(integrated_dataset)):
        splitted_categories = re.split(', | - ', integrated_dataset.at[row, 'categoria'])
        for i in range(len(splitted_categories)):
            integrated_dataset.at[row, f'categoria_{i + 1}'] = splitted_categories[i]
    integrated_dataset.drop(columns='categoria', inplace=True)
    return integrated_dataset


if __name__ == "__main__":
    trees = pd.read_csv('datasets/ds2484_alberi_20230331.csv', sep=';')
    open_wifi = pd.read_csv('datasets/openwifi_layer_0_open_wifi_outdoor_4326_final.csv', sep=';')
    historic_shops = pd.read_csv('datasets/ds290_economia_botteghe_storiche_2017_.csv', sep=';')
    benches = pd.read_csv('datasets/ds2748_panchine.csv', sep=';')
    picnic_tables = pd.read_csv('datasets/ds2749_tavoli_picnic.csv', sep=';')
    vedovelle_fountains = pd.read_csv('datasets/vedovelle_20240708-001843_final.csv', sep=';')
    nils = pd.read_csv('datasets/nil/ds964_nil_wm_4326.csv', sep=';')
    wikidata_pois = pd.read_csv('datasets/query_geodecoded.csv')
    addressless_entities = pd.read_csv('datasets/addressless_entities_geodecoded.csv')
    integrate_datasets(trees, open_wifi, historic_shops, benches, picnic_tables, vedovelle_fountains, nils, wikidata_pois,
                       addressless_entities)