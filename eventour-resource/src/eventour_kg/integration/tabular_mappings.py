from eventour_kg.integration.tabular_schema import EMPTY_ROW_TEMPLATE


def map_feature_row(dataset_name, feature):
    mapper = DATASET_MAPPERS.get(dataset_name)
    if mapper is None:
        raise ValueError(f"Unsupported dataset for tabular mapping: {dataset_name}")
    return mapper(dataset_name, feature)


def _map_bike_areesosta(dataset_name, feature):
    properties = _properties(feature)
    row = _new_row(dataset_name)
    identifier = _as_text(properties.get("id_amat"))
    address = _address(
        properties.get("via_tipo"),
        properties.get("via_nome"),
        properties.get("num_civico"),
    )
    row["source_record_key"] = identifier
    row["stable_identifier"] = identifier
    row["entity_family"] = "MobilityNode"
    row["entity_subtype"] = "BikeParking"
    row["transport_mode"] = "BICYCLE"
    row["label"] = _prefixed_label("Bike parking", address)
    row["label_construction_rule"] = "Bike parking - {via_tipo} {via_nome} {num_civico}"
    row["street_code"] = _as_text(properties.get("via_id"))
    row["street_type"] = _as_text(properties.get("via_tipo"))
    row["street_name"] = _as_text(properties.get("via_nome"))
    row["street_number"] = _as_text(properties.get("num_civico"))
    row["full_address"] = address
    row["placement_context"] = _as_text(properties.get("ubicazione"))
    row["municipio"] = _as_text(properties.get("municipio"))
    row["status"] = _as_text(properties.get("stato"))
    row["allowed_vehicle_category"] = _as_text(properties.get("veicoli"))
    row["installation_or_infrastructure_type"] = _as_text(properties.get("tipo_man"))
    row["capacity_total"] = _as_text(properties.get("stalli_totali"))
    row["capacity_per_unit"] = _as_text(properties.get("stalli_man"))
    row["num_structures"] = _as_text(properties.get("nmanufatti"))
    _apply_geometry(row, feature.get("geometry"))
    return row


def _map_bikemi_stazioni(dataset_name, feature):
    properties = _properties(feature)
    row = _new_row(dataset_name)
    identifier = _as_text(properties.get("id_amat"))
    row["source_record_key"] = identifier
    row["stable_identifier"] = identifier
    row["secondary_identifier"] = _as_text(properties.get("numero"))
    row["entity_family"] = "MobilityNode"
    row["entity_subtype"] = "BikeSharingStation"
    row["transport_mode"] = "BIKE_SHARING"
    row["label"] = _as_text(properties.get("nome"))
    row["label_construction_rule"] = "BikeMi station - {nome} ({numero})"
    row["street_code"] = _as_text(properties.get("id_via"))
    row["street_number"] = _as_text(properties.get("civico"))
    row["full_address"] = _address(properties.get("indirizzo"), properties.get("civico"))
    row["placement_context"] = _as_text(properties.get("sede"))
    row["municipio"] = _as_text(properties.get("zd_attuale"))
    row["status"] = _as_text(properties.get("stato"))
    row["year_or_installation_date"] = _as_text(properties.get("anno"))
    row["installation_or_infrastructure_type"] = _as_text(properties.get("tipo"))
    row["capacity_total"] = _as_text(properties.get("stalli"))
    _apply_geometry(row, feature.get("geometry"))
    return row


def _map_openwifi(dataset_name, feature):
    properties = _properties(feature)
    row = _new_row(dataset_name)
    identifier = _as_text(properties.get("AP"))
    row["source_record_key"] = identifier
    row["stable_identifier"] = identifier
    row["entity_family"] = "SupportService"
    row["entity_subtype"] = "WiFiHotspot"
    row["label"] = identifier
    row["label_construction_rule"] = "OpenWiFi hotspot - {AP}"
    row["full_address"] = _as_text(properties.get("indirizzo"))
    row["municipio"] = _as_text(properties.get("MUNICIPIO"))
    row["nil_id"] = _as_text(properties.get("ID_NIL"))
    row["nil_name"] = _as_text(properties.get("NIL"))
    row["postal_code"] = _as_text(properties.get("CAP"))
    row["source_coordinate_text"] = _as_text(properties.get("Location"))
    row["category_text"] = "municipal outdoor WiFi hotspot"
    _apply_geometry(row, feature.get("geometry"))
    return row


def _map_historic_shops(dataset_name, feature):
    properties = _properties(feature)
    row = _new_row(dataset_name)
    identifier = _as_text(properties.get("N."))
    row["source_record_key"] = identifier
    row["stable_identifier"] = identifier
    row["entity_family"] = "Place"
    row["entity_subtype"] = "HistoricShop"
    row["label"] = _as_text(properties.get("TARGA"))
    row["label_construction_rule"] = "TARGA"
    row["full_address"] = _as_text(properties.get("INDIRIZZO"))
    row["municipio"] = _as_text(properties.get("MUNICIPIO"))
    row["nil_id"] = _as_text(properties.get("ID_NIL"))
    row["nil_name"] = _as_text(properties.get("NIL"))
    row["postal_code"] = _as_text(properties.get("CAP"))
    row["source_coordinate_text"] = _as_text(properties.get("Location"))
    row["status"] = _as_text(properties.get("STATO"))
    row["year_or_installation_date"] = _as_text(properties.get("ANNO"))
    row["category_text"] = _as_text(properties.get("GENERE MERCEOLOGICO"))
    _apply_geometry(row, feature.get("geometry"))
    return row


def _map_public_toilets(dataset_name, feature):
    properties = _properties(feature)
    row = _new_row(dataset_name)
    identifier = _as_text(properties.get("OBJECTID"))
    address = _address(properties.get("VIA"), properties.get("LOCALITA"))
    row["source_record_key"] = identifier
    row["stable_identifier"] = identifier
    row["entity_family"] = "SupportService"
    row["entity_subtype"] = "PublicToilet"
    row["label"] = _prefixed_label("Public toilet", address)
    row["label_construction_rule"] = "Public toilet - {VIA} {LOCALITA}"
    row["full_address"] = address
    row["locality_text"] = _as_text(properties.get("LOCALITA"))
    row["municipio"] = _as_text(properties.get("MUNICIPIO"))
    row["nil_id"] = _as_text(properties.get("ID_NIL"))
    row["nil_name"] = _as_text(properties.get("NIL"))
    row["source_coordinate_text"] = _as_text(properties.get("Location"))
    row["availability_window"] = _as_text(properties.get("DISPONIBILITA"))
    row["notes"] = _as_text(properties.get("ULTERIORI_INFO"))
    row["category_text"] = _as_text(properties.get("TIPO"))
    _apply_geometry(row, feature.get("geometry"))
    return row


def _map_nil(dataset_name, feature):
    properties = _properties(feature)
    row = _new_row(dataset_name)
    identifier = _as_text(properties.get("ID_NIL"))
    row["source_record_key"] = identifier
    row["stable_identifier"] = identifier
    row["secondary_identifier"] = _as_text(properties.get("OBJECTID"))
    row["entity_family"] = "Area"
    row["entity_subtype"] = "NILArea"
    row["label"] = _as_text(properties.get("NIL"))
    row["label_construction_rule"] = "NIL"
    row["nil_id"] = identifier
    row["nil_name"] = _as_text(properties.get("NIL"))
    row["valid_from"] = _as_text(properties.get("Valido_dal"))
    row["valid_to"] = _as_text(properties.get("Valido_al"))
    row["source_reference"] = _as_text(properties.get("Fonte"))
    row["geometry_length_source"] = properties.get("Shape_Length")
    row["geometry_area_source"] = properties.get("Shape_Area")
    _apply_geometry(row, feature.get("geometry"))
    return row


def _map_alberi(dataset_name, feature):
    properties = _properties(feature)
    row = _new_row(dataset_name)
    identifier = _as_text(properties.get("obj_id"))
    botanical_name = _address(properties.get("genere"), properties.get("specie"))
    row["source_record_key"] = identifier
    row["stable_identifier"] = identifier
    row["entity_family"] = "EnvironmentalFeature"
    row["entity_subtype"] = "Tree"
    row["label"] = _tree_label(identifier, botanical_name)
    row["label_construction_rule"] = "Tree - {obj_id} - {genere} {specie}"
    row["municipio"] = _as_text(properties.get("municipio"))
    row["source_area_id"] = _as_text(properties.get("id_area"))
    row["area_code"] = _as_text(properties.get("area"))
    row["source_coordinate_text"] = _as_text(properties.get("Location"))
    row["year_or_installation_date"] = _as_text(properties.get("data_ini"))
    row["botanical_genus"] = _as_text(properties.get("genere"))
    row["botanical_species"] = _as_text(properties.get("specie"))
    row["botanical_variety"] = _as_text(properties.get("varieta"))
    row["trunk_diameter"] = _as_text(properties.get("diam_tronc"))
    row["crown_diameter"] = _as_text(properties.get("diam_chiom"))
    row["height_m"] = _as_text(properties.get("h_m"))
    _apply_geometry(row, feature.get("geometry"))
    return row


def _map_panchine(dataset_name, feature):
    properties = _properties(feature)
    row = _new_row(dataset_name)
    identifier = _as_text(properties.get("obj_id"))
    row["source_record_key"] = identifier
    row["stable_identifier"] = identifier
    row["entity_family"] = "SupportService"
    row["entity_subtype"] = "Bench"
    row["label"] = _as_text(properties.get("località"))
    row["label_construction_rule"] = "Bench - {località}"
    row["locality_text"] = _as_text(properties.get("località"))
    row["municipio"] = _as_text(properties.get("municipio"))
    row["source_area_id"] = _as_text(properties.get("id_area"))
    row["area_code"] = _as_text(properties.get("area"))
    row["year_or_installation_date"] = _as_text(properties.get("data_ini"))
    row["installation_or_infrastructure_type"] = _as_text(
        properties.get("descrizione_codice")
    )
    _apply_geometry(row, feature.get("geometry"))
    return row


def _map_metro_stops(dataset_name, feature):
    properties = _properties(feature)
    row = _new_row(dataset_name)
    identifier = _as_text(properties.get("id_amat"))
    row["source_record_key"] = identifier
    row["stable_identifier"] = identifier
    row["secondary_identifier"] = _as_text(properties.get("nome"))
    row["entity_family"] = "MobilityNode"
    row["entity_subtype"] = "MetroStation"
    row["transport_mode"] = "METRO"
    row["label"] = _as_text(properties.get("nome"))
    row["label_construction_rule"] = "Metro station - {nome}"
    row["line_code"] = _as_text(properties.get("linee"))
    _apply_geometry(row, feature.get("geometry"))
    return row


def _map_metro_timetables(dataset_name, feature):
    properties = _properties(feature)
    row = _new_row(dataset_name)
    composite_identifier = _composite_key(
        properties.get("linea"),
        properties.get("percorso"),
        properties.get("tipo_giorno"),
    )
    row["source_record_key"] = composite_identifier
    row["composite_identifier"] = composite_identifier
    row["entity_family"] = "OperationalLayer"
    row["entity_subtype"] = "MetroTimetableRecord"
    row["transport_mode"] = _as_text(properties.get("mezzo"))
    row["label"] = _prefixed_label(
        "Metro timetable",
        _line_route_day_identity(
            properties.get("linea"),
            properties.get("percorso"),
            properties.get("tipo_giorno"),
        ),
    )
    row["label_construction_rule"] = (
        "Metro timetable - line {linea} - route {percorso} - day type {tipo_giorno}"
    )
    row["line_code"] = _as_text(properties.get("linea"))
    row["route_code"] = _as_text(properties.get("percorso"))
    row["day_type"] = _as_text(properties.get("tipo_giorno"))
    row["timetable_period"] = _as_text(properties.get("orario"))
    row["service_start_time"] = _as_text(properties.get("inizio"))
    row["service_end_time"] = _as_text(properties.get("fine"))
    row["trip_count_total"] = _as_text(properties.get("corse_gior"))
    row["trip_count_peak"] = _as_text(properties.get("corse_punt"))
    row["trip_count_offpeak"] = _as_text(properties.get("corse_morb"))
    row["trip_count_evening"] = _as_text(properties.get("corse_sera"))
    _apply_geometry(row, feature.get("geometry"))
    return row


def _map_metro_routes(dataset_name, feature):
    properties = _properties(feature)
    row = _new_row(dataset_name)
    identifier = _as_text(properties.get("percorso"))
    row["source_record_key"] = identifier
    row["stable_identifier"] = identifier
    row["secondary_identifier"] = _as_text(properties.get("nome"))
    row["entity_family"] = "MobilityRoute"
    row["entity_subtype"] = "MetroRoute"
    row["transport_mode"] = _as_text(properties.get("mezzo"))
    row["label"] = _as_text(properties.get("nome"))
    row["label_construction_rule"] = "Metro route - {nome}"
    row["line_code"] = _as_text(properties.get("linea"))
    row["route_code"] = identifier
    row["route_name"] = _as_text(properties.get("nome"))
    row["route_length_km"] = _as_text(properties.get("lung_km"))
    row["stop_count"] = _as_text(properties.get("num_ferm"))
    _apply_geometry(row, feature.get("geometry"))
    return row


def _map_metro_sequences(dataset_name, feature):
    properties = _properties(feature)
    row = _new_row(dataset_name)
    composite_identifier = _composite_key(
        properties.get("percorso"),
        properties.get("num"),
    )
    row["source_record_key"] = composite_identifier
    row["composite_identifier"] = composite_identifier
    row["entity_family"] = "StructuralLayer"
    row["entity_subtype"] = "MetroRouteSequenceRecord"
    row["transport_mode"] = "METRO"
    row["label"] = _prefixed_label(
        "Metro route sequence",
        _route_position_identity(properties.get("percorso"), properties.get("num")),
    )
    row["label_construction_rule"] = (
        "Metro route sequence - route {percorso} - position {num}"
    )
    row["route_code"] = _as_text(properties.get("percorso"))
    row["stop_id_reference"] = _as_text(properties.get("id_ferm"))
    row["sequence_number"] = _as_text(properties.get("num"))
    _apply_geometry(row, feature.get("geometry"))
    return row


def _map_surface_timetables(dataset_name, feature):
    properties = _properties(feature)
    row = _new_row(dataset_name)
    composite_identifier = _composite_key(
        properties.get("linea"),
        properties.get("percorso"),
        properties.get("tipo_giorno"),
    )
    row["source_record_key"] = composite_identifier
    row["composite_identifier"] = composite_identifier
    row["entity_family"] = "OperationalLayer"
    row["entity_subtype"] = "SurfaceTimetableRecord"
    row["transport_mode"] = _as_text(properties.get("mezzo"))
    row["label"] = _prefixed_label(
        "Surface timetable",
        _line_route_day_identity(
            properties.get("linea"),
            properties.get("percorso"),
            properties.get("tipo_giorno"),
        ),
    )
    row["label_construction_rule"] = (
        "Surface timetable - line {linea} - route {percorso} - day type {tipo_giorno}"
    )
    row["line_code"] = _as_text(properties.get("linea"))
    row["route_code"] = _as_text(properties.get("percorso"))
    row["day_type"] = _as_text(properties.get("tipo_giorno"))
    row["timetable_period"] = _as_text(properties.get("orario"))
    row["service_start_time"] = _as_text(properties.get("inizio"))
    row["service_end_time"] = _as_text(properties.get("fine"))
    row["trip_count_total"] = _as_text(properties.get("corse_gior"))
    row["trip_count_peak"] = _as_text(properties.get("corse_punt"))
    row["trip_count_offpeak"] = _as_text(properties.get("corse_morb"))
    row["trip_count_evening"] = _as_text(properties.get("corse_sera"))
    _apply_geometry(row, feature.get("geometry"))
    return row


def _map_surface_routes(dataset_name, feature):
    properties = _properties(feature)
    row = _new_row(dataset_name)
    identifier = _as_text(properties.get("percorso"))
    row["source_record_key"] = identifier
    row["stable_identifier"] = identifier
    row["entity_family"] = "MobilityRoute"
    row["entity_subtype"] = "SurfaceRoute"
    row["transport_mode"] = _as_text(properties.get("mezzo"))
    row["label"] = _as_text(properties.get("nome"))
    row["label_construction_rule"] = "Surface route - line {linea} - {nome}"
    row["line_code"] = _as_text(properties.get("linea"))
    row["route_code"] = identifier
    row["route_name"] = _as_text(properties.get("nome"))
    row["direction_code"] = _as_text(properties.get("verso"))
    row["route_type"] = _as_text(properties.get("tipo_perc"))
    row["route_length_km"] = _as_text(properties.get("lung_km"))
    row["stop_count"] = _as_text(properties.get("num_ferm"))
    _apply_geometry(row, feature.get("geometry"))
    return row


def _map_surface_sequences(dataset_name, feature):
    properties = _properties(feature)
    row = _new_row(dataset_name)
    composite_identifier = _composite_key(
        properties.get("percorso"),
        properties.get("num"),
    )
    row["source_record_key"] = composite_identifier
    row["composite_identifier"] = composite_identifier
    row["entity_family"] = "StructuralLayer"
    row["entity_subtype"] = "SurfaceRouteSequenceRecord"
    row["transport_mode"] = "SURFACE_PUBLIC_TRANSPORT"
    row["label"] = _prefixed_label(
        "Surface route sequence",
        _route_position_identity(properties.get("percorso"), properties.get("num")),
    )
    row["label_construction_rule"] = (
        "Surface route sequence - route {percorso} - position {num}"
    )
    row["route_code"] = _as_text(properties.get("percorso"))
    row["stop_id_reference"] = _as_text(properties.get("id_ferm"))
    row["sequence_number"] = _as_text(properties.get("num"))
    _apply_geometry(row, feature.get("geometry"))
    return row


def _map_park_interscambio(dataset_name, feature):
    properties = _properties(feature)
    row = _new_row(dataset_name)
    identifier = _as_text(properties.get("Nome"))
    row["source_record_key"] = identifier
    row["stable_identifier"] = identifier
    row["entity_family"] = "MobilityNode"
    row["entity_subtype"] = "ParkAndRide"
    row["transport_mode"] = "INTERMODAL_PARKING"
    row["label"] = identifier
    row["label_construction_rule"] = "Park and ride - {Nome}"
    row["full_address"] = _as_text(properties.get("indirizzo"))
    row["zone_or_ring"] = _as_text(properties.get("Zona"))
    row["category_text"] = "park-and-ride facility"
    row["raw_capacity_text"] = _as_text(properties.get("TAB1"))
    row["interchange_info"] = _as_text(properties.get("INFO"))
    _apply_geometry(row, feature.get("geometry"))
    return row


def _map_public_parking(dataset_name, feature):
    properties = _properties(feature)
    row = _new_row(dataset_name)
    identifier = _as_text(properties.get("id"))
    row["source_record_key"] = identifier
    row["stable_identifier"] = identifier
    row["secondary_identifier"] = _as_text(properties.get("nome"))
    row["entity_family"] = "MobilityNode"
    row["entity_subtype"] = "ParkingFacility"
    row["transport_mode"] = "PARKING"
    row["label"] = _as_text(properties.get("nome"))
    row["label_construction_rule"] = "Public parking - {nome}"
    row["full_address"] = _as_text(properties.get("indirizzo"))
    row["city_name"] = _as_text(properties.get("comune"))
    row["category_text"] = _as_text(properties.get("tipo"))
    row["capacity_total"] = _as_text(properties.get("n_posti"))
    _apply_geometry(row, feature.get("geometry"))
    return row


def _map_ricarica_colonnine(dataset_name, feature):
    properties = _properties(feature)
    row = _new_row(dataset_name)
    identifier = _as_text(properties.get("id_amat"))
    row["source_record_key"] = identifier
    row["stable_identifier"] = identifier
    row["entity_family"] = "MobilityNode"
    row["entity_subtype"] = "EVChargingStation"
    row["transport_mode"] = "ELECTRIC_VEHICLE"
    row["label"] = _as_text(properties.get("localita"))
    row["label_construction_rule"] = "Charging station - {localita}"
    row["street_code"] = _as_text(properties.get("id_via"))
    row["street_name"] = _as_text(properties.get("nome_via"))
    row["full_address"] = _as_text(properties.get("localita"))
    row["municipio"] = _as_text(properties.get("municipio"))
    row["nil_id"] = _as_text(properties.get("id_nil"))
    row["nil_name"] = _as_text(properties.get("nome_nil"))
    row["sub_nil_id"] = _as_text(properties.get("id_sottonil"))
    row["zone_or_ring"] = _as_text(properties.get("cerchia"))
    row["parking_ambit_id"] = _as_text(properties.get("ambito_id"))
    row["parking_ambit_name"] = _as_text(properties.get("ambito_nome"))
    row["status"] = _as_text(properties.get("attuazione"))
    row["year_or_installation_date"] = _as_text(properties.get("anno"))
    row["notes"] = _as_text(properties.get("note"))
    row["operator"] = _as_text(properties.get("titolare"))
    row["installation_or_infrastructure_type"] = _as_text(properties.get("infra"))
    row["category_text"] = _as_text(properties.get("tipologia"))
    row["capacity_total"] = _as_text(properties.get("numero_pdr"))
    row["num_structures"] = _as_text(properties.get("numero_col"))
    row["project_name"] = _as_text(properties.get("progetto"))
    row["ordinance"] = _as_text(properties.get("ordinanza"))
    _apply_geometry(row, feature.get("geometry"))
    return row


def _map_vedovelle(dataset_name, feature):
    properties = _properties(feature)
    row = _new_row(dataset_name)
    identifier = _as_text(properties.get("objectID"))
    row["source_record_key"] = identifier
    row["stable_identifier"] = identifier
    row["entity_family"] = "SupportService"
    row["entity_subtype"] = "DrinkingFountain"
    row["label"] = f"Vedovella - {identifier} - {_as_text(properties.get('NIL'))}"
    row["label_construction_rule"] = "Vedovella - {objectID} - {NIL}"
    row["municipio"] = _as_text(properties.get("MUNICIPIO"))
    row["nil_id"] = _as_text(properties.get("ID_NIL"))
    row["nil_name"] = _as_text(properties.get("NIL"))
    row["postal_code"] = _as_text(properties.get("CAP"))
    row["source_coordinate_text"] = _as_text(properties.get("Location"))
    row["category_text"] = "drinking fountain"
    _apply_geometry(row, feature.get("geometry"))
    return row


def _map_surface_stops(dataset_name, feature):
    properties = _properties(feature)
    row = _new_row(dataset_name)
    identifier = _as_text(properties.get("id_amat"))
    row["source_record_key"] = identifier
    row["stable_identifier"] = identifier
    row["entity_family"] = "MobilityNode"
    row["entity_subtype"] = "SurfaceStop"
    row["transport_mode"] = "SURFACE_PUBLIC_TRANSPORT"
    row["label"] = _as_text(properties.get("ubicazione"))
    row["label_construction_rule"] = "Surface stop - {ubicazione}"
    row["locality_text"] = _as_text(properties.get("ubicazione"))
    row["line_code"] = _as_text(properties.get("linee"))
    _apply_geometry(row, feature.get("geometry"))
    return row


def _map_picnic_tables(dataset_name, feature):
    properties = _properties(feature)
    row = _new_row(dataset_name)
    identifier = _as_text(properties.get("obj_id"))
    row["source_record_key"] = identifier
    row["stable_identifier"] = identifier
    row["entity_family"] = "SupportService"
    row["entity_subtype"] = "PicnicTable"
    row["label"] = _as_text(properties.get("località"))
    row["label_construction_rule"] = "Picnic table - {località}"
    row["locality_text"] = _as_text(properties.get("località"))
    row["municipio"] = _as_text(properties.get("municipio"))
    row["source_area_id"] = _as_text(properties.get("id_area"))
    row["area_code"] = _as_text(properties.get("area"))
    row["year_or_installation_date"] = _as_text(properties.get("data_ini"))
    row["installation_or_infrastructure_type"] = _as_text(
        properties.get("descrizione_codice")
    )
    _apply_geometry(row, feature.get("geometry"))
    return row


def _new_row(dataset_name):
    row = dict(EMPTY_ROW_TEMPLATE)
    row["source_dataset_name"] = dataset_name
    return row


def _properties(feature):
    return feature.get("properties") or {}


def _as_text(value):
    if value is None:
        return None
    return str(value)


def _address(*parts):
    return _join_text(*(_as_text(part) for part in parts))


def _join_text(*parts):
    text_parts = [part for part in parts if part not in (None, "")]
    if not text_parts:
        return None
    return " ".join(" ".join(text_parts).split())


def _prefixed_label(prefix, text):
    if text is None:
        return None
    return f"{prefix} - {text}"


def _tree_label(identifier, botanical_name):
    if botanical_name is None:
        return _prefixed_label("Tree", identifier)
    return f"Tree - {identifier} - {botanical_name}"


def _line_route_day_identity(line_code, route_code, day_type):
    return _join_text(
        "line",
        _as_text(line_code),
        "- route",
        _as_text(route_code),
        "- day type",
        _as_text(day_type),
    )


def _route_position_identity(route_code, position):
    return _join_text(
        "route",
        _as_text(route_code),
        "- position",
        _as_text(position),
    )


def _composite_key(*parts):
    text_parts = [_as_text(part) for part in parts]
    if any(part is None for part in text_parts):
        return None
    return "|".join(text_parts)


def _apply_geometry(row, geometry):
    if not geometry:
        return
    geometry_type = geometry.get("type")
    row["geometry_type"] = _as_text(geometry_type)
    row["wkt_geometry"] = _geometry_to_wkt(geometry)
    if geometry_type == "Point":
        coordinates = geometry.get("coordinates") or []
        if len(coordinates) >= 2:
            row["longitude"] = coordinates[0]
            row["latitude"] = coordinates[1]


def _geometry_to_wkt(geometry):
    geometry_type = geometry.get("type")
    coordinates = geometry.get("coordinates")
    if geometry_type == "Point":
        return f"POINT ({_pair_to_wkt(coordinates)})"
    if geometry_type == "LineString":
        return f"LINESTRING ({_line_to_wkt(coordinates)})"
    if geometry_type == "MultiLineString":
        parts = [f"({_line_to_wkt(line)})" for line in coordinates or []]
        return f"MULTILINESTRING ({', '.join(parts)})"
    if geometry_type == "Polygon":
        rings = [f"({_line_to_wkt(ring)})" for ring in coordinates or []]
        return f"POLYGON ({', '.join(rings)})"
    if geometry_type == "MultiPoint":
        points = [f"({_pair_to_wkt(point)})" for point in coordinates or []]
        return f"MULTIPOINT ({', '.join(points)})"
    if geometry_type == "MultiPolygon":
        polygons = []
        for polygon in coordinates or []:
            rings = [f"({_line_to_wkt(ring)})" for ring in polygon]
            polygons.append(f"({', '.join(rings)})")
        return f"MULTIPOLYGON ({', '.join(polygons)})"
    raise ValueError(f"Unsupported geometry type: {geometry_type}")


def _line_to_wkt(coordinates):
    return ", ".join(_pair_to_wkt(pair) for pair in coordinates or [])


def _pair_to_wkt(pair):
    return f"{pair[0]} {pair[1]}"


DATASET_MAPPERS = {
    "bike_areesosta.geojson": _map_bike_areesosta,
    "bikemi_stazioni.geojson": _map_bikemi_stazioni,
    "ds69_openwifi_layer_0_open_wifi_outdoor_4326_final.geojson": _map_openwifi,
    "ds290_economia_botteghe_storiche_2024.geojson": _map_historic_shops,
    "ds630_servizi_igienici_pubblici_final.geojson": _map_public_toilets,
    "ds964_nil_wm.geojson": _map_nil,
    "ds2484_alberi_20240331.geojson": _map_alberi,
    "ds2748_panchine.geojson": _map_panchine,
    "tpl_metrofermate.geojson": _map_metro_stops,
    "tpl_metroorari.geojson": _map_metro_timetables,
    "tpl_metropercorsi.geojson": _map_metro_routes,
    "tpl_metrosequenza.geojson": _map_metro_sequences,
    "tpl_orari.geojson": _map_surface_timetables,
    "tpl_percorsi.geojson": _map_surface_routes,
    "tpl_sequenza.geojson": _map_surface_sequences,
    "park_interscambio.geojson": _map_park_interscambio,
    "park_pub.geojson": _map_public_parking,
    "ricarica_colonnine.geojson": _map_ricarica_colonnine,
    "vedovelle_20260315-233003_final.geojson": _map_vedovelle,
    "tpl_fermate.geojson": _map_surface_stops,
    "ds2749_tavoli_picnic.geojson": _map_picnic_tables,
}
