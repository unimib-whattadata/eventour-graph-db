You are classifying one Wikidata entity for Eventour.

Eventour generates urban itineraries of different lengths based on user preferences, preferred POI categories, and mobility constraints. It focuses on culturally meaningful, visitable, or narratively useful urban places.

Your task is to choose exactly one decision:
- keep_poi
- keep_context
- candidate_exception
- exclude

Decision meanings:
- keep_poi: the entity should be considered a candidate Eventour POI
- keep_context: the entity is useful in the knowledge graph as spatial or narrative context, but should not be a primary Eventour stop
- candidate_exception: the entity belongs to a generic or ambiguous class and may be relevant, but should be reviewed
- exclude: the entity is not useful for Eventour as a POI or as contextual urban information

If the decision is keep_poi, assign exactly one Eventour category from this list:
- museum_collection
- gallery_art_space
- religious_heritage
- historic_architecture
- monument_memorial
- public_art
- archaeological_ancient_site
- urban_landmark
- performing_arts_entertainment
- park_garden_nature
- cemetery_funerary_heritage
- science_education_attraction
- district_streetscape
- special_interest_attraction

Important policy rules:
- Do not invent new categories.
- Conservative precision first: when evidence is mixed, weak, or mostly generic, prefer `exclude` or `candidate_exception` rather than a false-positive `keep_poi`.
- Use keep_context mainly for districts, neighborhoods, historic quarters, and other contextual urban areas.
- Do not use Wikidata as the primary source for transport infrastructure. Metro stations, bus stops, tram stops, train stops, lines, and similar transport entities should usually be excluded in this classification step because they are modeled through dedicated local mobility datasets and GTFS.
- `direct_class_labels` are the strongest asserted typing signal for the entity.
- `class_ancestor_labels` provide broader semantic context and are especially important when the direct class is generic.
- `semantic_fact_texts` are ranked supporting facts about the specific entity. Use them to confirm or reject likely Eventour relevance.
- Generic location facts such as country, city, address, street, or administrative containment are weak background evidence and should not by themselves justify `keep_poi`.
- Rich event metadata such as organizer, participant count, sport, date, previous edition, or next edition does not make an event a stable POI.
- Retail, commercial, corporate, or brand-linked venues are not automatically Eventour POIs. Keep them only when the evidence clearly supports architectural, historic, artistic, memorial, religious, museum, park, district, or landmark significance; otherwise prefer `candidate_exception` or `exclude`.
- Use candidate_exception for generic but potentially notable classes such as building, house, office building, residential building, generic palace, or other broad place-like classes where some instances may be culturally relevant.
- For generic building-like classes, use `keep_poi` only when multiple signals support cultural, historic, architectural, or landmark significance. Use `candidate_exception` when there is some plausible relevance but the case remains ambiguous. Use `exclude` when the evidence points mainly to ordinary commercial, residential, or administrative use.
- Use exclude for organizations, sports seasons, championships, brands, abstract concepts, generic infrastructure, and non-place entities unless the description clearly shows they are relevant urban places.
- Prefer conservative judgments when uncertain.
- Use the label, description, direct classes, ancestor labels, and semantic facts together. Do not rely only on one field or one section.

Input fields:
- city_name
- entity_label
- entity_description
- direct_class_labels
- class_ancestor_labels
- semantic_fact_texts

Few-shot examples:

Example 1
Input:
- city_name: Milan
- entity_label: Pinacoteca di Brera
- entity_description: art museum in Milan, Italy
- direct_class_labels: ["museo d'arte", "pinacoteca"]
Output:
{"decision":"keep_poi","eventour_category":"museum_collection","confidence":0.98,"rationale":"A major public art museum and a clear cultural attraction."}

Example 2
Input:
- city_name: Milan
- entity_label: Duomo di Milano
- entity_description: cathedral church in Milan, Italy
- direct_class_labels: ["cattedrale cattolica", "chiesa"]
Output:
{"decision":"keep_poi","eventour_category":"religious_heritage","confidence":0.99,"rationale":"A major visitable religious heritage site and one of the main landmarks of the city."}

Example 3
Input:
- city_name: Milan
- entity_label: Brera
- entity_description: district of Milan
- direct_class_labels: ["quartiere di Milano", "distretto storico"]
Output:
{"decision":"keep_context","eventour_category":null,"confidence":0.94,"rationale":"Useful as spatial and narrative context, but not a primary attraction node by itself."}

Example 4
Input:
- city_name: Milan
- entity_label: Bolivar
- entity_description: Milan metro station
- direct_class_labels: ["stazione metropolitana", "stazione sotterranea"]
Output:
{"decision":"exclude","eventour_category":null,"confidence":0.97,"rationale":"Transport infrastructure should be modeled from dedicated local mobility datasets rather than selected here from Wikidata."}

Example 5
Input:
- city_name: Milan
- entity_label: Fermata via X
- entity_description: public transport stop in Milan
- direct_class_labels: ["fermata dell'autobus"]
Output:
{"decision":"exclude","eventour_category":null,"confidence":0.98,"rationale":"A transport stop is not a POI candidate in this semantic classification step and is covered by local transport sources."}

Example 6
Input:
- city_name: Milan
- entity_label: Palazzo Marino
- entity_description: historic palace and city hall in Milan
- direct_class_labels: ["palazzo", "palazzo comunale", "edificio storico"]
Output:
{"decision":"keep_poi","eventour_category":"historic_architecture","confidence":0.95,"rationale":"A historically and architecturally notable palace that is meaningful for urban itineraries."}

Example 7
Input:
- city_name: Milan
- entity_label: Generic office tower
- entity_description: office building in Milan
- direct_class_labels: ["edificio per uffici", "grattacielo"]
Output:
{"decision":"candidate_exception","eventour_category":null,"confidence":0.79,"rationale":"The class is potentially relevant only in special architectural or landmark cases and should be reviewed."}

Example 8
Input:
- city_name: Milan
- entity_label: Monumento ai Caduti
- entity_description: war memorial in Milan
- direct_class_labels: ["monumento commemorativo", "memoriale di guerra"]
Output:
{"decision":"keep_poi","eventour_category":"monument_memorial","confidence":0.96,"rationale":"A commemorative monument that is culturally meaningful and suitable as an itinerary stop."}

Example 9
Input:
- city_name: Milan
- entity_label: Parco Sempione
- entity_description: large city park in Milan
- direct_class_labels: ["parco cittadino", "giardino pubblico"]
Output:
{"decision":"keep_poi","eventour_category":"park_garden_nature","confidence":0.97,"rationale":"A major urban park and a clear outdoor attraction."}

Example 10
Input:
- city_name: Milan
- entity_label: 1957 Summer Deaflympics
- entity_description: sports event held in Milan
- direct_class_labels: ["stagione sportiva"]
Output:
{"decision":"exclude","eventour_category":null,"confidence":0.99,"rationale":"An event rather than a stable urban place."}

Example 11
Input:
- city_name: Milan
- entity_label: A.S.D. Centro Schuster
- entity_description: sports club in Milan
- direct_class_labels: ["societa sportiva"]
Output:
{"decision":"exclude","eventour_category":null,"confidence":0.97,"rationale":"An organization, not a culturally meaningful place for Eventour."}

Example 12
Input:
- city_name: Milan
- entity_label: Casa storica X
- entity_description: historic house in Milan associated with a notable family
- direct_class_labels: ["casa", "edificio storico"]
Output:
{"decision":"keep_poi","eventour_category":"historic_architecture","confidence":0.84,"rationale":"Despite the generic housing-related class, the description indicates historical relevance and landmark value."}

Example 13
Input:
- city_name: Milan
- entity_label: Albergo diurno Cobianchi
- entity_description: edificio storico di Milano
- direct_class_labels: ["edificio"]
- class_ancestor_labels: ["struttura architettonica"]
- semantic_fact_texts: ["parte di: alberghi diurni Cobianchi", "architetto: Marcello Troiani", "data di fondazione o creazione: 1923-01-01"]
Output:
{"decision":"keep_poi","eventour_category":"historic_architecture","confidence":0.89,"rationale":"The direct class is generic, but the historic description and architectural facts support a culturally relevant historic building."}

Example 14
Input:
- city_name: Milan
- entity_label: Apple Piazza Liberty
- entity_description: building in Milan, Italy
- direct_class_labels: ["Apple Store", "edificio"]
- class_ancestor_labels: ["negozio di computer", "negozio di elettronica", "struttura architettonica"]
- semantic_fact_texts: ["proprietario: Apple Inc.", "via: piazza del Liberty", "architetto: Norman Foster", "data di apertura ufficiale: 2018-07-27"]
Output:
{"decision":"candidate_exception","eventour_category":null,"confidence":0.78,"rationale":"Architectural interest is plausible, but the entity is primarily a branded retail venue and should be reviewed rather than automatically kept."}

Example 15
Input:
- city_name: Milan
- entity_label: 1988 World Rowing Championships
- entity_description: rowing regatta
- direct_class_labels: ["Campionati del mondo di canottaggio"]
- class_ancestor_labels: ["campionato mondiale", "competizione di canottaggio"]
- semantic_fact_texts: ["impianto di gioco: Idroscalo di Milano", "organizzatore: Federazione Internazionale Canottaggio", "sport: canottaggio", "numero dell'edizione: 18"]
Output:
{"decision":"exclude","eventour_category":null,"confidence":0.99,"rationale":"Even with rich metadata, this is still a sports event rather than a stable urban place or contextual district entity."}

Return only valid JSON with this exact schema:
{
  "decision": "keep_poi|keep_context|candidate_exception|exclude",
  "eventour_category": "museum_collection|gallery_art_space|religious_heritage|historic_architecture|monument_memorial|public_art|archaeological_ancient_site|urban_landmark|performing_arts_entertainment|park_garden_nature|cemetery_funerary_heritage|science_education_attraction|district_streetscape|special_interest_attraction|null",
  "confidence": 0.0,
  "rationale": "short explanation"
}

Additional output rules:
- eventour_category must be null unless decision is keep_poi
- confidence must be a number between 0 and 1
- rationale must be exactly one short sentence
- rationale must be factual, specific, and mention only the strongest evidence for the decision
- rationale should usually be 12-25 words
- rationale should mention at most 1-2 decisive signals
- for keep_poi, emphasize the strongest cultural, historic, architectural, artistic, memorial, park, district, or landmark signal
- for candidate_exception, state what makes the entity ambiguous
- for exclude, state the main reason the entity is not an Eventour place
- avoid boilerplate such as "not a POI or contextual district" unless it is necessary to disambiguate the case
- do not restate the full input; summarize only the key reason
