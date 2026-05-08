import pytest

from eventour_kg.integration.tabular_mappings import map_feature_row
from eventour_kg.integration.tabular_schema import CANONICAL_COLUMNS


def _point(longitude, latitude):
    return {"type": "Point", "coordinates": [longitude, latitude]}


def _line(*coordinates):
    return {"type": "LineString", "coordinates": list(coordinates)}


def _multi_line(*lines):
    return {"type": "MultiLineString", "coordinates": [list(line) for line in lines]}


def _polygon(*rings):
    return {"type": "Polygon", "coordinates": [list(ring) for ring in rings]}


DATASET_CASES = [
    pytest.param(
        "bike_areesosta.geojson",
        {
            "properties": {
                "id_amat": 3,
                "via_id": "1545",
                "via_tipo": "Viale",
                "via_nome": "Affori",
                "num_civico": "21",
                "stalli_man": "5",
                "stalli_totali": "30",
                "nmanufatti": "6",
                "stato": "Esistente",
                "veicoli": "Velocipedi",
                "tipo_man": "Verona _ Ambrogio",
                "ubicazione": "Area verde - Giardino - Parco",
                "municipio": "9",
            },
            "geometry": _point(9.1, 45.5),
        },
        {
            "source_record_key": "3",
            "stable_identifier": "3",
            "entity_family": "MobilityNode",
            "entity_subtype": "BikeParking",
            "full_address": "Viale Affori 21",
            "capacity_total": "30",
        },
        id="bike-areesosta",
    ),
    pytest.param(
        "bikemi_stazioni.geojson",
        {
            "properties": {
                "id_amat": 1,
                "stato": "attiva",
                "numero": "001",
                "nome": "Duomo",
                "tipo": "Monofacciale",
                "stalli": "24",
                "sede": "Carreggiata",
                "id_via": "1",
                "indirizzo": "PIAZZA DEL DUOMO",
                "civico": None,
                "zd_attuale": "1",
                "anno": "2008",
            },
            "geometry": _point(9.189141462641942, 45.46474597341512),
        },
        {
            "source_record_key": "1",
            "stable_identifier": "1",
            "secondary_identifier": "001",
            "entity_subtype": "BikeSharingStation",
            "label": "Duomo",
            "full_address": "PIAZZA DEL DUOMO",
            "capacity_total": "24",
        },
        id="bikemi-stazioni",
    ),
    pytest.param(
        "ds69_openwifi_layer_0_open_wifi_outdoor_4326_final.geojson",
        {
            "properties": {
                "AP": "CSPiazzaleAccursio5-04",
                "indirizzo": "Via SIMONI RENATO 15",
                "CAP": "20157",
                "MUNICIPIO": "8",
                "ID_NIL": "76",
                "NIL": "QUARTO OGGIARO - VIALBA - MUSOCCO",
                "Location": "(45.51833, 9.14502)",
            },
            "geometry": _point(9.14502, 45.51833),
        },
        {
            "source_record_key": "CSPiazzaleAccursio5-04",
            "stable_identifier": "CSPiazzaleAccursio5-04",
            "entity_family": "SupportService",
            "entity_subtype": "WiFiHotspot",
            "source_coordinate_text": "(45.51833, 9.14502)",
            "postal_code": "20157",
            "category_text": "municipal outdoor WiFi hotspot",
        },
        id="openwifi",
    ),
    pytest.param(
        "ds290_economia_botteghe_storiche_2024.geojson",
        {
            "properties": {
                "N.": "1",
                "TARGA": "a Santa Lucia",
                "GENERE MERCEOLOGICO": "Ristorante",
                "ANNO": "1929",
                "STATO": "attiva",
                "INDIRIZZO": "Via SAN PIETRO ALL'ORTO 3",
                "CAP": "20121",
                "MUNICIPIO": "1",
                "ID_NIL": "1",
                "NIL": "DUOMO",
                "Location": "(45.4658047226987, 9.19561447250575)",
            },
            "geometry": _point(9.19561447250575, 45.4658047226987),
        },
        {
            "source_record_key": "1",
            "stable_identifier": "1",
            "entity_family": "Place",
            "entity_subtype": "HistoricShop",
            "label": "a Santa Lucia",
            "full_address": "Via SAN PIETRO ALL'ORTO 3",
            "category_text": "Ristorante",
        },
        id="historic-shop",
    ),
    pytest.param(
        "ds630_servizi_igienici_pubblici_final.geojson",
        {
            "properties": {
                "OBJECTID": "1",
                "VIA": "Parco",
                "LOCALITA": "Lambro",
                "ULTERIORI_INFO": None,
                "DISPONIBILITA": "marzo - ottobre",
                "TIPO": "mobile",
                "MUNICIPIO": "3",
                "ID_NIL": "18",
                "NIL": "CIMIANO - ROTTOLE - Q.RE FELTRE",
                "Location": "(45.4983057406496, 9.24947453826014)",
            },
            "geometry": _point(9.24947453826014, 45.4983057406496),
        },
        {
            "source_record_key": "1",
            "stable_identifier": "1",
            "entity_subtype": "PublicToilet",
            "label": "Public toilet - Parco Lambro",
            "full_address": "Parco Lambro",
            "locality_text": "Lambro",
            "availability_window": "marzo - ottobre",
            "category_text": "mobile",
        },
        id="public-toilet",
    ),
    pytest.param(
        "ds964_nil_wm.geojson",
        {
            "properties": {
                "ID_NIL": 48,
                "NIL": "RONCHETTO SUL NAVIGLIO - Q.RE LODOVICO IL MORO",
                "Valido_dal": "05/02/2020",
                "Valido_al": "Vigente",
                "Fonte": "Milano 2030 - PGT Approvato",
                "Shape_Length": 8723.368714059716,
                "Shape_Area": 2406306.0789698716,
                "OBJECTID": 89,
            },
            "geometry": _polygon(
                [
                    [9.15422102515081, 45.43775166985864],
                    [9.1543, 45.4378],
                    [9.15422102515081, 45.43775166985864],
                ]
            ),
        },
        {
            "source_record_key": "48",
            "stable_identifier": "48",
            "secondary_identifier": "89",
            "entity_family": "Area",
            "entity_subtype": "NILArea",
            "geometry_length_source": 8723.368714059716,
            "geometry_area_source": 2406306.0789698716,
        },
        id="nil-area",
    ),
    pytest.param(
        "ds2484_alberi_20240331.geojson",
        {
            "properties": {
                "id_area": "1_018",
                "municipio": "1",
                "area": "018",
                "obj_id": "225",
                "codice": "P103108",
                "data_ini": "1965-02-06T00:00+01:00[Europe/Paris]",
                "genere": "Platanus",
                "specie": "x acerifolia",
                "varieta": None,
                "diam_tronc": "70",
                "diam_chiom": "15",
                "h_m": "20",
                "Location": "(45.473225113816696, 9.188071541304282)",
            },
            "geometry": _point(9.188071541304282, 45.473225113816696),
        },
        {
            "source_record_key": "225",
            "stable_identifier": "225",
            "entity_family": "EnvironmentalFeature",
            "entity_subtype": "Tree",
            "botanical_genus": "Platanus",
            "botanical_species": "x acerifolia",
            "source_coordinate_text": "(45.473225113816696, 9.188071541304282)",
        },
        id="trees",
    ),
    pytest.param(
        "ds2748_panchine.geojson",
        {
            "properties": {
                "id_area": "9_088",
                "municipio": 9,
                "area": "088",
                "località": "vie Guerzoni - Ciaia",
                "obj_id": 162523,
                "codice": "L219400",
                "descrizione_codice": "Panchina in legno a 16 listelli",
                "data_ini": "2022-08-23",
            },
            "geometry": _multi_line(
                [
                    [9.175487622420906, 45.50189822443534],
                    [9.17549446023115, 45.501880876252656],
                ]
            ),
        },
        {
            "source_record_key": "162523",
            "stable_identifier": "162523",
            "entity_subtype": "Bench",
            "locality_text": "vie Guerzoni - Ciaia",
            "installation_or_infrastructure_type": "Panchina in legno a 16 listelli",
            "longitude": None,
            "latitude": None,
        },
        id="benches",
    ),
    pytest.param(
        "tpl_metrofermate.geojson",
        {
            "properties": {
                "id_amat": 869,
                "nome": "BOLIVAR",
                "linee": "4",
            },
            "geometry": _point(9.15314900789545, 45.45531900103459),
        },
        {
            "source_record_key": "869",
            "stable_identifier": "869",
            "secondary_identifier": "BOLIVAR",
            "entity_family": "MobilityNode",
            "entity_subtype": "MetroStation",
            "transport_mode": "METRO",
            "line_code": "4",
        },
        id="metro-stops",
    ),
    pytest.param(
        "tpl_metroorari.geojson",
        {
            "properties": {
                "linea": "2",
                "mezzo": "METRO",
                "percorso": "100046",
                "orario": "INV2024-2025",
                "tipo_giorno": "L",
                "inizio": "20:42",
                "fine": "00:54",
                "corse_gior": "17",
                "corse_punt": "0",
                "corse_morb": "0",
                "corse_sera": "8",
            },
            "geometry": None,
        },
        {
            "source_record_key": "2|100046|L",
            "stable_identifier": None,
            "composite_identifier": "2|100046|L",
            "entity_family": "OperationalLayer",
            "entity_subtype": "MetroTimetableRecord",
            "trip_count_evening": "8",
            "wkt_geometry": None,
        },
        id="metro-timetable",
    ),
    pytest.param(
        "tpl_metropercorsi.geojson",
        {
            "properties": {
                "linea": "1",
                "mezzo": "METRO",
                "percorso": "100002",
                "nome": "BISCEGLIE - SESTO 1 MAGGIO FS",
                "lung_km": "16.38",
                "num_ferm": "27",
            },
            "geometry": _line(
                [9.11291318106982, 45.45538556070954],
                [9.116483230975913, 45.45606994057518],
            ),
        },
        {
            "source_record_key": "100002",
            "stable_identifier": "100002",
            "secondary_identifier": "BISCEGLIE - SESTO 1 MAGGIO FS",
            "entity_family": "MobilityRoute",
            "entity_subtype": "MetroRoute",
            "route_length_km": "16.38",
            "stop_count": "27",
        },
        id="metro-routes",
    ),
    pytest.param(
        "tpl_metrosequenza.geojson",
        {
            "properties": {
                "percorso": "100067",
                "num": "19",
                "id_ferm": "911",
            },
            "geometry": None,
        },
        {
            "source_record_key": "100067|19",
            "composite_identifier": "100067|19",
            "entity_family": "StructuralLayer",
            "entity_subtype": "MetroRouteSequenceRecord",
            "route_code": "100067",
            "stop_id_reference": "911",
            "sequence_number": "19",
        },
        id="metro-sequences",
    ),
    pytest.param(
        "tpl_orari.geojson",
        {
            "properties": {
                "linea": "83",
                "mezzo": "BUS",
                "percorso": "5812",
                "orario": "INV2024-2025",
                "tipo_giorno": "L",
                "inizio": "06:34",
                "fine": "01:40",
                "corse_gior": "33",
                "corse_punt": "5",
                "corse_morb": "0",
                "corse_sera": "8",
            },
            "geometry": None,
        },
        {
            "source_record_key": "83|5812|L",
            "composite_identifier": "83|5812|L",
            "entity_family": "OperationalLayer",
            "entity_subtype": "SurfaceTimetableRecord",
            "transport_mode": "BUS",
            "trip_count_peak": "5",
            "trip_count_evening": "8",
        },
        id="surface-timetable",
    ),
    pytest.param(
        "tpl_percorsi.geojson",
        {
            "properties": {
                "linea": "1",
                "mezzo": "TRAM",
                "percorso": "14200",
                "verso": "As",
                "nome": "Greco - Sei Febbraio (LAV. MAMBRETTI/PALIZZI)",
                "tipo_perc": "Canonico",
                "lung_km": "8.95",
                "num_ferm": "33",
            },
            "geometry": _line(
                [9.21625289912771, 45.494925615237285],
                [9.215380922734008, 45.49485986869782],
            ),
        },
        {
            "source_record_key": "14200",
            "stable_identifier": "14200",
            "entity_family": "MobilityRoute",
            "entity_subtype": "SurfaceRoute",
            "transport_mode": "TRAM",
            "direction_code": "As",
            "route_type": "Canonico",
        },
        id="surface-routes",
    ),
    pytest.param(
        "tpl_sequenza.geojson",
        {
            "properties": {
                "percorso": "10151",
                "num": "7",
                "id_ferm": "13331",
            },
            "geometry": None,
        },
        {
            "source_record_key": "10151|7",
            "composite_identifier": "10151|7",
            "entity_family": "StructuralLayer",
            "entity_subtype": "SurfaceRouteSequenceRecord",
            "transport_mode": "SURFACE_PUBLIC_TRANSPORT",
            "stop_id_reference": "13331",
            "sequence_number": "7",
        },
        id="surface-sequences",
    ),
    pytest.param(
        "park_interscambio.geojson",
        {
            "properties": {
                "Nome": "FAMAGOSTA",
                "TAB1": "2200 POSTI AUTO",
                "INFO": "CORRISPONDENZA  LINEA MM2",
                "Zona": "6",
                "indirizzo": "VLE FAMAGOSTA",
            },
            "geometry": _point(9.169528930387113, 45.43662144463426),
        },
        {
            "source_record_key": "FAMAGOSTA",
            "stable_identifier": "FAMAGOSTA",
            "entity_subtype": "ParkAndRide",
            "raw_capacity_text": "2200 POSTI AUTO",
            "interchange_info": "CORRISPONDENZA  LINEA MM2",
            "zone_or_ring": "6",
        },
        id="park-and-ride",
    ),
    pytest.param(
        "park_pub.geojson",
        {
            "properties": {
                "id": 11,
                "nome": "Giulio Cesare",
                "n_posti": 116.0,
                "indirizzo": "Piazza Giulio Cesare",
                "comune": "Milano",
                "tipo": "RESIDENTI/PUBBLICI",
            },
            "geometry": _point(9.155567631859647, 45.47376994844666),
        },
        {
            "source_record_key": "11",
            "stable_identifier": "11",
            "secondary_identifier": "Giulio Cesare",
            "entity_subtype": "ParkingFacility",
            "city_name": "Milano",
            "category_text": "RESIDENTI/PUBBLICI",
            "capacity_total": "116.0",
        },
        id="public-parking",
    ),
    pytest.param(
        "ricarica_colonnine.geojson",
        {
            "properties": {
                "id_amat": 1,
                "municipio": "7",
                "id_sottonil": "76",
                "id_nil": "56",
                "nome_nil": "FORZE ARMATE",
                "cerchia": "EXTRA-FILOVIARIA",
                "ambito_id": "36",
                "ambito_nome": "Bisceglie",
                "attuazione": "4",
                "tipologia": "QN",
                "titolare": "A2A Energy Solutions",
                "id_via": "6709",
                "nome_via": "VIA LUCCA",
                "localita": "VIA LUCCA 14",
                "numero_col": "2",
                "numero_pdr": "4",
                "infra": "AC Normal",
                "progetto": "ELECTRIC CITY MOVERS - ISOLE DIGITALI",
                "note": "attiva_revampizzata_revoca_70451/2013-70452/2013",
                "ordinanza": "215/2023-216/2023",
                "anno": "2023",
            },
            "geometry": _point(9.112836716769262, 45.455714852139025),
        },
        {
            "source_record_key": "1",
            "stable_identifier": "1",
            "entity_subtype": "EVChargingStation",
            "parking_ambit_id": "36",
            "parking_ambit_name": "Bisceglie",
            "project_name": "ELECTRIC CITY MOVERS - ISOLE DIGITALI",
            "ordinance": "215/2023-216/2023",
        },
        id="ev-charging",
    ),
    pytest.param(
        "vedovelle_20260315-233003_final.geojson",
        {
            "properties": {
                "objectID": "5407",
                "CAP": "20152",
                "MUNICIPIO": "6",
                "ID_NIL": "53",
                "NIL": "LORENTEGGIO",
                "Location": "(45.45100463400172, 9.104075763359273)",
            },
            "geometry": _point(9.104075763359273, 45.45100463400172),
        },
        {
            "source_record_key": "5407",
            "stable_identifier": "5407",
            "entity_subtype": "DrinkingFountain",
            "label": "Vedovella - 5407 - LORENTEGGIO",
            "source_coordinate_text": "(45.45100463400172, 9.104075763359273)",
            "category_text": "drinking fountain",
        },
        id="vedovelle",
    ),
    pytest.param(
        "tpl_fermate.geojson",
        {
            "properties": {
                "id_amat": 10003,
                "ubicazione": "Via Bovisasca, 18 dopo Via C.Battisti",
                "linee": "89",
            },
            "geometry": _point(9.148258113563548, 45.52690564197453),
        },
        {
            "source_record_key": "10003",
            "stable_identifier": "10003",
            "entity_subtype": "SurfaceStop",
            "transport_mode": "SURFACE_PUBLIC_TRANSPORT",
            "label": "Via Bovisasca, 18 dopo Via C.Battisti",
            "line_code": "89",
        },
        id="surface-stops",
    ),
    pytest.param(
        "ds2749_tavoli_picnic.geojson",
        {
            "properties": {
                "id_area": "9_280",
                "municipio": 9,
                "area": "280",
                "località": "giardino Maria Peron e suor Giovanna Mosna",
                "obj_id": 211291,
                "codice": "P214272",
                "descrizione_codice": "Tavolo da pic nic",
                "data_ini": "2011-11-01",
            },
            "geometry": _point(9.196043969403172, 45.52149925593618),
        },
        {
            "source_record_key": "211291",
            "stable_identifier": "211291",
            "entity_subtype": "PicnicTable",
            "locality_text": "giardino Maria Peron e suor Giovanna Mosna",
            "installation_or_infrastructure_type": "Tavolo da pic nic",
        },
        id="picnic-tables",
    ),
]


@pytest.mark.parametrize(("dataset_name", "feature", "expected"), DATASET_CASES)
def test_map_feature_row_supports_all_documented_datasets(
    dataset_name, feature, expected
):
    row = map_feature_row(dataset_name, feature)

    assert list(row.keys()) == list(CANONICAL_COLUMNS)
    assert row["source_dataset_name"] == dataset_name

    for key, value in expected.items():
        assert row[key] == value


def test_linestring_geometry_branch_sets_wkt_and_leaves_point_coordinates_empty():
    row = map_feature_row(
        "tpl_metropercorsi.geojson",
        {
            "properties": {
                "linea": "1",
                "mezzo": "METRO",
                "percorso": "100002",
                "nome": "BISCEGLIE - SESTO 1 MAGGIO FS",
                "lung_km": "16.38",
                "num_ferm": "27",
            },
            "geometry": _line(
                [9.11291318106982, 45.45538556070954],
                [9.116483230975913, 45.45606994057518],
            ),
        },
    )

    assert row["geometry_type"] == "LineString"
    assert (
        row["wkt_geometry"]
        == "LINESTRING (9.11291318106982 45.45538556070954, 9.116483230975913 45.45606994057518)"
    )
    assert row["longitude"] is None
    assert row["latitude"] is None


def test_multilinestring_geometry_branch_sets_wkt_and_leaves_point_coordinates_empty():
    row = map_feature_row(
        "ds2748_panchine.geojson",
        {
            "properties": {
                "id_area": "9_088",
                "municipio": 9,
                "area": "088",
                "località": "vie Guerzoni - Ciaia",
                "obj_id": 162523,
                "descrizione_codice": "Panchina in legno a 16 listelli",
                "data_ini": "2022-08-23",
            },
            "geometry": _multi_line(
                [
                    [9.175487622420906, 45.50189822443534],
                    [9.17549446023115, 45.501880876252656],
                ]
            ),
        },
    )

    assert row["geometry_type"] == "MultiLineString"
    assert (
        row["wkt_geometry"]
        == "MULTILINESTRING ((9.175487622420906 45.50189822443534, 9.17549446023115 45.501880876252656))"
    )
    assert row["longitude"] is None
    assert row["latitude"] is None


def test_polygon_geometry_branch_sets_wkt_and_leaves_point_coordinates_empty():
    row = map_feature_row(
        "ds964_nil_wm.geojson",
        {
            "properties": {
                "ID_NIL": 48,
                "NIL": "RONCHETTO SUL NAVIGLIO - Q.RE LODOVICO IL MORO",
                "Valido_dal": "05/02/2020",
                "Valido_al": "Vigente",
                "Fonte": "Milano 2030 - PGT Approvato",
                "Shape_Length": 8723.368714059716,
                "Shape_Area": 2406306.0789698716,
                "OBJECTID": 89,
            },
            "geometry": _polygon(
                [
                    [9.15422102515081, 45.43775166985864],
                    [9.1543, 45.4378],
                    [9.15422102515081, 45.43775166985864],
                ]
            ),
        },
    )

    assert row["geometry_type"] == "Polygon"
    assert (
        row["wkt_geometry"]
        == "POLYGON ((9.15422102515081 45.43775166985864, 9.1543 45.4378, 9.15422102515081 45.43775166985864))"
    )
    assert row["longitude"] is None
    assert row["latitude"] is None


def test_unsupported_geometry_type_raises_value_error():
    with pytest.raises(ValueError, match="Unsupported geometry type: GeometryCollection"):
        map_feature_row(
            "park_pub.geojson",
            {
                "properties": {
                    "id": 11,
                    "nome": "Giulio Cesare",
                    "n_posti": 116.0,
                    "indirizzo": "Piazza Giulio Cesare",
                    "comune": "Milano",
                    "tipo": "RESIDENTI/PUBBLICI",
                },
                "geometry": {"type": "GeometryCollection", "geometries": []},
            },
        )
