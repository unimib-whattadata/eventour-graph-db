import pandas as pd
from datetime import datetime


# Moves columns in the dataset
def move_column(dataset, column_name, position):
    values = dataset.pop(column_name)
    dataset.insert(position, column_name, values)
    return dataset


nil_shapes = pd.read_csv('datasets/nil/ds964_nil_wm.csv', sep=';')

nil_shapes.rename(columns={'Valido_dal': 'data_origine'}, inplace=True)
nil_shapes['data_origine'] = pd.to_datetime(nil_shapes['data_origine'])
nil_shapes['data_origine'] = [str(row) for row in nil_shapes['data_origine']]
nil_shapes[['data_origine', 'ora_fine_validita']] = nil_shapes['data_origine'].str.split(' ', expand=True)
nil_shapes = nil_shapes[['geometry', 'coordinates', 'ID_NIL', 'NIL', 'data_origine', 'Fonte', 'Shape_Length', 'Shape_Area']]
nil_shapes['categoria'] = 'NIL'
nil_shapes['nome_dataset'] = 'Nuclei d\'Identità Locale (NIL) VIGENTI - PGT 2030'
nil_shapes['last_update'] = '2020-04-01'
nil_shapes = move_column(nil_shapes, 'ID_NIL', 0)
nil_shapes.sort_values(by=['ID_NIL'], inplace=True)

nil_shapes.to_csv('datasets/nil/nil_shapes.csv', sep=';', index=False)