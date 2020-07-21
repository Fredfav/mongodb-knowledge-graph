# MongoDB and Knowledge Graphs
How to model a knowledge graph in MongoDB, incl. ontologies and an example based on public data from OpenStreetMap

# TODO:

* Add attributes to ontology
* Store ontology in JSON-LD format in MongoDB
* Import instance data to MongoDB in JSON-LD format
* Derive and execute Query Patterns to MongoDB

# Steps

## Create Ontology

* Import raw data of keys and values of OSM data: `import_osm_metadata.py`
* Derive ontology `derive_ontoloty.py`

## Create Instances

* Import OSM data (can be a whole country, or just some parts): https://www.geofabrik.de/data/download.html
* Import raw data of .osm.pbf file to MongoDB `import_osm_data.py`

