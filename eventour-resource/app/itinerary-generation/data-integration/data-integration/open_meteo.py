import pandas as pd


# Manages Open Meteo descriptions and images depending on if it is day or night
def integrate_descriptions(open_meteo):
    description = []
    image = []

    for index, row in open_meteo.iterrows():
        if row['giorno_notte'] == 1:
            description.append(row['day/description'])
            image.append(row['day/image'])
        else:
            description.append(row['night/description'])
            image.append(row['night/image'])

    open_meteo['descrizione'] = description
    open_meteo['immagine'] = image
    open_meteo.drop(columns=['day/description', 'night/description', 'day/image', 'night/image'], inplace=True)

    return open_meteo


# Adds latitude, longitude and location columns
def add_coordinates(open_meteo):
    latitude = []
    longitude = []
    location = []

    for index, row in open_meteo.iterrows():
        latitude.append(45.46)
        longitude.append(9.18)
        location.append('(45.46, 9.18)')
    
    open_meteo.insert(0, 'latitudine', latitude)
    open_meteo.insert(1, 'longitudine', longitude)
    open_meteo.insert(2, 'Location', location)

    return open_meteo


# Moves columns in the dataset
def move_column(dataset, column_name, position):
    values = dataset.pop(column_name)
    dataset.insert(position, column_name, values)
    return dataset


meteo = pd.read_csv('datasets/meteo/open-meteo-45.46N9.18E145m.csv', header=2)
descriptions = pd.read_csv('datasets/meteo/descriptions.csv')

meteo.rename(columns={'time': 'data', 'temperature_2m (°C)': 'temperatura_C',
                      'precipitation_probability (%)': 'probabilita_precipitazioni',
                      'precipitation (mm)': 'precipitazioni_mm', 'weather_code (wmo code)': 'codice_wmo',
                      'wind_speed_10m (km/h)': 'velocita_vento_kmh', 'is_day ()': 'giorno_notte'}, inplace=True)
descriptions.rename(columns={'_key': 'codice_wmo'}, inplace=True)
meteo[['data', 'ora']] = meteo['data'].str.split('T', expand=True)
meteo = move_column(meteo, 'ora', 1)
meteo_descriptions = integrate_descriptions(pd.merge(meteo, descriptions, on='codice_wmo'))
meteo_descriptions = add_coordinates(meteo_descriptions)
meteo_descriptions.insert(0, column='id', value=[x for x in range(1, len(meteo_descriptions.index) + 1)])
meteo_descriptions['categoria'] = 'meteo'
meteo_descriptions['nome_dataset'] = 'Open-Meteo'
meteo_descriptions['last_update'] = '2024-09-02'

meteo_descriptions.to_csv('datasets/meteo/open_meteo_descriptions.csv', sep=';', index=False)