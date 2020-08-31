# MongoDB and Knowledge Graphs
How to model a knowledge graph in MongoDB, incl. ontologies and an example based on public data from OpenStreetMap

# Prerequisites

* Latest stable Python 3 with the following (TODO: pyld, requests, rdflib, rdflib-jsonld, esy, esy-osm-pbf) modules installed
* Java JDK
* pbf2json download from https://github.com/pelias/pbf2json
* owl2jsonld download from https://github.com/stain/owl2jsonld
* Latest stable MongoDB installed locally or accessible. Connection is currently configured to use local instance without authentication
* OSM data in PBF format at choice.

# TODO:

* Visualization

# Steps

## Create Ontology

* Import raw data of keys and values of OSM data: `python3 import_osm_metadata.py`
* Derive ontology `python3 derive_ontology.py`

After running `derive_ontology.py` the files `osmpower.jsonld` and `osmpower.ttl` are created.

## Create Instances

* Import OSM data (can be a whole country, or just some parts): https://www.geofabrik.de/data/download.html e.g. `bayern-latest.osm.pbf`. Change `INPUT_OSM_FILE` in `import_osm_data.py` accordingly.
* To import raw data of .osm.pbf file to MongoDB `import_osm_data.py` the file `pbf2json.darwin-x64` (for your OS of choice) is needed. Change `command` in `import_osm_data.py` accordingly. Then run with `python3 import_osm_data.py`. When running, the script seems to hang, but it does finish (needs to be documented or changed, as the Java process is called from the Python script. Bit hacky, but works more or less fine). You can stop with Control-C, as soon as no new objects are inserted into raw_objects_germany (should be just raw_objects <- final polishing).
* Next step is to run `python3 derive_instances.py` to get the instance data as TTL file and in the collection "instance". The file `owl2jsonld` is needed. Change `OWL_TO_JSON_JAR_ABSOLUTE_PATH` in `derive_instances.py` accordingly. Please double-check if the collection name in `derive_instances.py` is correct, must be "raw_objects_germany" (those imported earlier).

When running script reports progress creating assets:

```Processed 295000 Assets
Processed 296000 Assets
Processed 297000 Assets
Create partOf and hasPart relationships
```
After running `derive_instances.py` the file `osmpower_bavaria.ttl` is created (NOTE: file name is hardcoded in script).

