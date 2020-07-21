import requests
import pymongo
import re

from  pprint import pprint
import json
from pyld import jsonld

import esy.osm.pbf

import subprocess

# Semantic Description of OpenStreetMap: https://wiki.openstreetmap.org/wiki/OSM_Semantic_Network

# API doc for tags in Openstreetmap: https://taginfo.openstreetmap.org/taginfo/apidoc#api_4_keys_all
# Need the attributes of the classes (tags to use in combination): https://wiki.openstreetmap.org/wiki/Tag%3Asubstation%3Dconverter
#   /api/4/tag/combinations?key=highway&value=residential&page=1&rp=10&sortname=together_count&sortorder=desc
# HTTP requests: https://requests.readthedocs.io/en/master/
# PyLD: JSON-LD in Python (pip3 install PyLD), https://github.com/digitalbazaar/pyld

# Example Ontology in JSON-LD https://gist.github.com/stain/7690362

# sudo yum -y install git python3 pymongo dnspython
# PyOSM: https://pypi.org/project/esy-osm-pbf/
# pip3 install esy-osm-pbf

# curl -OL https://download.geofabrik.de/europe/germany/bayern-latest.osm.pbf
# curl -OL https://download.geofabrik.de/europe/germany/germany-latest.osm.pbf

# pbf2json: https://github.com/pelias/pbf2json
# /home/ec2-user/pbf2json/build/pbf2json.linux-x64

OPENSTREETMAP_NAMESPACE = 'osmpower'
OPENSTREETMAP = 'openstreetmap'
KEY_TO_ANALYZE = 'power'

mongo_client = pymongo.MongoClient('localhost')

raw_class_tags_coll = mongo_client.osm.raw_class_tags
#raw_releated_tags_coll = mongo_client.osm.raw_releated_tags

raw_objects_coll = mongo_client.osm.raw_objects
raw_objects_coll.create_index([( "tags.$**", pymongo.ASCENDING)])

osm = esy.osm.pbf.File('/Users/christian.kurze/Downloads/bayern-latest.osm.pbf')

def main():
	# Alternative: get all tags from MongoDB:
	#tags = [row['key'] for row in raw_class_tags_coll.find({},{'_id': 0, 'key': 1})]

	tags = [row['key'] for row in raw_class_tags_coll.aggregate([{'$unwind': {'path': '$data'}},{'$project': {'_id': 0,'key': {'$concat': ['$data.key', '~', '$data.value']}}}])]
	# tags = ['power']
	tags.append('route~power')
	tags = ','.join(tags)
	print(tags)
	#command = '/Users/christian.kurze/development/pbf2json/build/pbf2json.darwin-x64 -tags="' + str(tags) +'" --waynodes=true /Users/christian.kurze/Documents/MongoDB/90-Demos/iot-demos/truck-demo/geo-payloads/germany-latest.osm.pbf'
	command = '/Users/christian.kurze/development/pbf2json/build/pbf2json.darwin-x64 -tags="' + str(tags) +'" --waynodes=true /Users/christian.kurze/Downloads/bayern-latest.osm.pbf'
	print(command)
	command = command.split()

	for line in run_command(command):
		if len(line) > 0:
			line = line.decode('utf-8')
			if line[0] == '{':
				doc = json.loads(line)
				# print(doc)
				doc['_id'] = doc.pop('id')
				raw_objects_coll.replace_one({'_id':doc['_id']}, doc, upsert=True)

	#print('Parse for power=tower')
	#objects = [entry for entry in osm if entry.tags.get('power') == 'tower']
	#print(objects)

def run_command(command):
    p = subprocess.Popen(command,
                         stdout=subprocess.PIPE)
    # in case we want to also see the errors:  ,stderr=subprocess.STDOUT
    return iter(p.stdout.readline, '')

if __name__ == '__main__':
	main()
