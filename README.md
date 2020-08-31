# MongoDB and Knowledge Graphs
How to model a knowledge graph in MongoDB, incl. ontologies and an example based on public data from OpenStreetMap

# Prerequisites

* Latest stable Python 3 with the following (TODO: pyld, requests, rdflib, rdflib-jsonld, esy, esy-osm-pbf) modules installed
* Java JDK
* Latest stable MongoDB installed locally or accessible. Connection is currently configured to use local instance without authentication

# TODO:

* Add attributes to ontology
* Store ontology in JSON-LD format in MongoDB
* Import instance data to MongoDB in JSON-LD format
* Derive and execute Query Patterns to MongoDB

# Steps

## Create Ontology

* Import raw data of keys and values of OSM data: `import_osm_metadata.py`
* Derive ontology `derive_ontology.py`

After running `import_osm_metadata.py` and `derive_ontology.py` the files `osmpower.ttl` and `osmpower.jsonld` are created.

## Create Instances

* Import OSM data (can be a whole country, or just some parts): https://www.geofabrik.de/data/download.html e.g. `bayern-latest.osm.pbf`. Change INPUT_OSM_FILE in `import_osm_data.py` accordingly.
* To import raw data of .osm.pbf file to MongoDB `import_osm_data.py` the file `pbf2json.darwin-x64` is needed (download from https://github.com/pelias/pbf2json). Change command in `import_osm_data.py` accordingly. When running, the script seems to hang, but it does finish (needs to be documented or changed, as the Java process is called from the Python script. Bit hacky, but works more or less fine). You can stop with Control-C, as soon as no new objects are inserted into raw_objects_germany (should be just raw_objects <- final polishing).
* Next step is to run `derive_instances.py` to get the instance data as TTL file and in the collection "instance". The file `owl2jsonld` is needed (download from https://github.com/stain/owl2jsonld). Please double-check if the collection name in `derive_instances.py` is correct, must be "raw_objects_germany" (those imported earlier).

When running script reports progress creating assets:

```Processed 295000 Assets
Processed 296000 Assets
Processed 297000 Assets
Create partOf and hasPart relationships
```
After running the file `osmpower_bavaria.ttl` is created (NOTE: file name is hardcoded in script) .

