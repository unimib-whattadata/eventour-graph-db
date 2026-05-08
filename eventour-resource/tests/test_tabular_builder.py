import csv
import json
import subprocess
import sys
from pathlib import Path

import pytest

from eventour_kg.integration.tabular_builder import build_integrated_superset
from eventour_kg.integration.tabular_schema import CANONICAL_COLUMNS


def _feature(properties, geometry):
    return {"type": "Feature", "properties": properties, "geometry": geometry}


def _feature_collection(feature):
    return {"type": "FeatureCollection", "features": [feature]}


def _point(longitude, latitude):
    return {"type": "Point", "coordinates": [longitude, latitude]}


def _line(*coordinates):
    return {"type": "LineString", "coordinates": list(coordinates)}


def _polygon(*rings):
    return {"type": "Polygon", "coordinates": [list(ring) for ring in rings]}


def _write_geojson(path: Path, feature):
    path.write_text(json.dumps(_feature_collection(feature), ensure_ascii=False), encoding="utf-8")


def test_build_integrated_superset_writes_csv_summary_and_preserves_row_counts(tmp_path: Path):
    datasets_dir = tmp_path / "datasets"
    datasets_dir.mkdir()

    cases = {
        "bike_areesosta.geojson": _feature(
            {
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
            _point(9.1, 45.5),
        ),
        "tpl_metropercorsi.geojson": _feature(
            {
                "linea": "1",
                "mezzo": "METRO",
                "percorso": "100002",
                "nome": "BISCEGLIE - SESTO 1 MAGGIO FS",
                "lung_km": "16.38",
                "num_ferm": "27",
            },
            _line(
                [9.11291318106982, 45.45538556070954],
                [9.116483230975913, 45.45606994057518],
            ),
        ),
        "ds964_nil_wm.geojson": _feature(
            {
                "ID_NIL": 48,
                "NIL": "RONCHETTO SUL NAVIGLIO - Q.RE LODOVICO IL MORO",
                "Valido_dal": "05/02/2020",
                "Valido_al": "Vigente",
                "Fonte": "Milano 2030 - PGT Approvato",
                "Shape_Length": 8723.368714059716,
                "Shape_Area": 2406306.0789698716,
                "OBJECTID": 89,
            },
            _polygon(
                [
                    [9.15422102515081, 45.43775166985864],
                    [9.1543, 45.4378],
                    [9.15422102515081, 45.43775166985864],
                ]
            ),
        ),
        "tpl_metroorari.geojson": _feature(
            {
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
            None,
        ),
        "tpl_metrosequenza.geojson": _feature(
            {
                "percorso": "100067",
                "num": "19",
                "id_ferm": "911",
            },
            None,
        ),
    }

    for name, feature in cases.items():
        _write_geojson(datasets_dir / name, feature)

    output_csv = tmp_path / "integrated.csv"
    summary_json = tmp_path / "reports" / "summary.json"
    dataset_names = list(cases)

    outputs = build_integrated_superset(
        datasets_dir=datasets_dir,
        output_csv=output_csv,
        summary_json=summary_json,
        dataset_names=dataset_names,
    )

    assert outputs.output_csv == output_csv
    assert outputs.summary_json == summary_json
    assert output_csv.exists()
    assert summary_json.exists()

    with output_csv.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))

    assert len(rows) == 5
    assert list(rows[0]) == list(CANONICAL_COLUMNS)
    assert [row["source_dataset_name"] for row in rows] == dataset_names
    assert rows[0]["geometry_type"] == "Point"
    assert rows[1]["geometry_type"] == "LineString"
    assert rows[2]["geometry_type"] == "Polygon"
    assert rows[3]["geometry_type"] == ""
    assert rows[4]["geometry_type"] == ""

    summary = json.loads(summary_json.read_text())
    assert summary["total_rows"] == 5
    assert summary["rows_per_dataset"] == {name: 1 for name in dataset_names}
    assert summary["rows_per_entity_family"] == {
        "MobilityNode": 1,
        "MobilityRoute": 1,
        "Area": 1,
        "OperationalLayer": 1,
        "StructuralLayer": 1,
    }
    assert summary["geometry_availability"] == {
        "with_geometry": 3,
        "without_geometry": 2,
    }
    assert summary["identifier_coverage"] == {
        "source_record_key": 5,
        "stable_identifier": 3,
        "secondary_identifier": 2,
        "composite_identifier": 2,
    }


def test_build_integrated_superset_raises_for_missing_dataset_file(tmp_path: Path):
    with pytest.raises(FileNotFoundError, match="Missing dataset file"):
        build_integrated_superset(
            datasets_dir=tmp_path / "datasets",
            output_csv=tmp_path / "integrated.csv",
            summary_json=tmp_path / "summary.json",
            dataset_names=["missing.geojson"],
        )


def test_build_integrated_superset_raises_for_non_feature_collection(tmp_path: Path):
    datasets_dir = tmp_path / "datasets"
    datasets_dir.mkdir()
    (datasets_dir / "broken.geojson").write_text(
        json.dumps({"type": "Feature", "properties": {}, "geometry": None}, ensure_ascii=False),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="Expected FeatureCollection"):
        build_integrated_superset(
            datasets_dir=datasets_dir,
            output_csv=tmp_path / "integrated.csv",
            summary_json=tmp_path / "summary.json",
            dataset_names=["broken.geojson"],
        )


def test_build_integrated_superset_raises_for_non_list_features(tmp_path: Path):
    datasets_dir = tmp_path / "datasets"
    datasets_dir.mkdir()
    (datasets_dir / "broken.geojson").write_text(
        json.dumps({"type": "FeatureCollection", "features": {}}, ensure_ascii=False),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="Expected features list"):
        build_integrated_superset(
            datasets_dir=datasets_dir,
            output_csv=tmp_path / "integrated.csv",
            summary_json=tmp_path / "summary.json",
            dataset_names=["broken.geojson"],
        )


def test_cli_main_writes_outputs_for_synthetic_dataset(tmp_path: Path):
    datasets_dir = tmp_path / "datasets"
    datasets_dir.mkdir()

    cases = {
        "bike_areesosta.geojson": _feature(
            {
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
            _point(9.1, 45.5),
        ),
        "bikemi_stazioni.geojson": _feature(
            {
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
            _point(9.189141462641942, 45.46474597341512),
        ),
        "ds69_openwifi_layer_0_open_wifi_outdoor_4326_final.geojson": _feature(
            {
                "AP": "CSPiazzaleAccursio5-04",
                "indirizzo": "Via SIMONI RENATO 15",
                "CAP": "20157",
                "MUNICIPIO": "8",
                "ID_NIL": "76",
                "NIL": "QUARTO OGGIARO - VIALBA - MUSOCCO",
                "Location": "(45.51833, 9.14502)",
            },
            _point(9.14502, 45.51833),
        ),
        "ds290_economia_botteghe_storiche_2024.geojson": _feature(
            {
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
            _point(9.19561447250575, 45.4658047226987),
        ),
        "ds630_servizi_igienici_pubblici_final.geojson": _feature(
            {
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
            _point(9.24947453826014, 45.4983057406496),
        ),
        "ds964_nil_wm.geojson": _feature(
            {
                "ID_NIL": 48,
                "NIL": "RONCHETTO SUL NAVIGLIO - Q.RE LODOVICO IL MORO",
                "Valido_dal": "05/02/2020",
                "Valido_al": "Vigente",
                "Fonte": "Milano 2030 - PGT Approvato",
                "Shape_Length": 8723.368714059716,
                "Shape_Area": 2406306.0789698716,
                "OBJECTID": 89,
            },
            _polygon(
                [
                    [9.15422102515081, 45.43775166985864],
                    [9.1543, 45.4378],
                    [9.15422102515081, 45.43775166985864],
                ]
            ),
        ),
        "ds2484_alberi_20240331.geojson": _feature(
            {
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
            _point(9.188071541304282, 45.473225113816696),
        ),
        "ds2748_panchine.geojson": _feature(
            {
                "id_area": "9_088",
                "municipio": 9,
                "area": "088",
                "località": "vie Guerzoni - Ciaia",
                "obj_id": 162523,
                "codice": "L219400",
                "descrizione_codice": "Panchina in legno a 16 listelli",
                "data_ini": "2022-08-23",
            },
            {
                "type": "MultiLineString",
                "coordinates": [
                    [
                        [9.175487622420906, 45.50189822443534],
                        [9.17549446023115, 45.501880876252656],
                    ]
                ],
            },
        ),
        "tpl_metrofermate.geojson": _feature(
            {
                "id_amat": 869,
                "nome": "BOLIVAR",
                "linee": "4",
            },
            _point(9.15314900789545, 45.45531900103459),
        ),
        "tpl_metroorari.geojson": _feature(
            {
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
            None,
        ),
        "tpl_metropercorsi.geojson": _feature(
            {
                "linea": "1",
                "mezzo": "METRO",
                "percorso": "100002",
                "nome": "BISCEGLIE - SESTO 1 MAGGIO FS",
                "lung_km": "16.38",
                "num_ferm": "27",
            },
            _line(
                [9.11291318106982, 45.45538556070954],
                [9.116483230975913, 45.45606994057518],
            ),
        ),
        "tpl_metrosequenza.geojson": _feature(
            {
                "percorso": "100067",
                "num": "19",
                "id_ferm": "911",
            },
            None,
        ),
        "tpl_orari.geojson": _feature(
            {
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
            None,
        ),
        "tpl_percorsi.geojson": _feature(
            {
                "linea": "1",
                "mezzo": "TRAM",
                "percorso": "14200",
                "verso": "As",
                "nome": "Greco - Sei Febbraio (LAV. MAMBRETTI/PALIZZI)",
                "tipo_perc": "Canonico",
                "lung_km": "8.95",
                "num_ferm": "33",
            },
            _line(
                [9.21625289912771, 45.494925615237285],
                [9.215380922734008, 45.49485986869782],
            ),
        ),
        "tpl_sequenza.geojson": _feature(
            {
                "percorso": "10151",
                "num": "7",
                "id_ferm": "13331",
            },
            None,
        ),
        "park_interscambio.geojson": _feature(
            {
                "Nome": "FAMAGOSTA",
                "TAB1": "2200 POSTI AUTO",
                "INFO": "CORRISPONDENZA  LINEA MM2",
                "Zona": "6",
                "indirizzo": "VLE FAMAGOSTA",
            },
            _point(9.169528930387113, 45.43662144463426),
        ),
        "park_pub.geojson": _feature(
            {
                "id": 11,
                "nome": "Giulio Cesare",
                "n_posti": 116.0,
                "indirizzo": "Piazza Giulio Cesare",
                "comune": "Milano",
                "tipo": "RESIDENTI/PUBBLICI",
            },
            _point(9.155567631859647, 45.47376994844666),
        ),
        "ricarica_colonnine.geojson": _feature(
            {
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
            _point(9.112836716769262, 45.455714852139025),
        ),
        "vedovelle_20260315-233003_final.geojson": _feature(
            {
                "objectID": "5407",
                "CAP": "20152",
                "MUNICIPIO": "6",
                "ID_NIL": "53",
                "NIL": "LORENTEGGIO",
                "Location": "(45.45100463400172, 9.104075763359273)",
            },
            _point(9.104075763359273, 45.45100463400172),
        ),
        "tpl_fermate.geojson": _feature(
            {
                "id_amat": 10003,
                "ubicazione": "Via Bovisasca, 18 dopo Via C.Battisti",
                "linee": "89",
            },
            _point(9.148258113563548, 45.52690564197453),
        ),
        "ds2749_tavoli_picnic.geojson": _feature(
            {
                "id_area": "9_280",
                "municipio": 9,
                "area": "280",
                "località": "giardino Maria Peron e suor Giovanna Mosna",
                "obj_id": 211291,
                "codice": "P214272",
                "descrizione_codice": "Tavolo da pic nic",
                "data_ini": "2011-11-01",
            },
            _point(9.196043969403172, 45.52149925593618),
        ),
    }

    for name, feature in cases.items():
        _write_geojson(datasets_dir / name, feature)

    output_csv = tmp_path / "cli" / "integrated.csv"
    summary_json = tmp_path / "cli" / "summary" / "summary.json"

    cli = Path("/Users/blespa/Desktop/Eventour RT ISWC 2026/implementation/.venv/bin/python")
    proc = subprocess.run(
        [
            str(cli),
            "-m",
            "eventour_kg.integration.build_integrated_superset",
            "milan",
            "--datasets-dir",
            str(datasets_dir),
            "--output-csv",
            str(output_csv),
            "--summary-json",
            str(summary_json),
        ],
        cwd=Path("/Users/blespa/Desktop/Eventour RT ISWC 2026/implementation"),
        capture_output=True,
        text=True,
    )

    assert proc.returncode == 0, proc.stderr
    payload = json.loads(proc.stdout.strip())
    assert payload["city_id"] == "milan"
    assert payload["output_csv"] == str(output_csv)
    assert payload["summary_json"] == str(summary_json)
    assert payload["total_rows"] == len(cases)
    assert output_csv.exists()
    assert summary_json.exists()
