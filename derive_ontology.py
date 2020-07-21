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

OPENSTREETMAP_NAMESPACE = 'osmpower'
OPENSTREETMAP = 'openstreetmap'
KEY_TO_ANALYZE = 'power'

mongo_client = pymongo.MongoClient('mongodb+srv://USER:PASSWORD@knowledgegraphfreetier.XXXXX.mongodb.net/osm?retryWrites=true&w=majority')

raw_class_tags_coll = mongo_client.osm.raw_class_tags
raw_releated_tags_coll = mongo_client.osm.raw_releated_tags

def main():
	tags = [taginfo for taginfo in raw_class_tags_coll.aggregate([{'$unwind': {'path': '$data'}}])]	
	create_ttl_file(tags)

def create_ttl_file(tags):
	namespace = 'osmpower'

	print(
"""@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix owl: <http://www.w3.org/2002/07/owl#> .
@prefix owl2: <http://www.w3.org/2006/12/owl2#> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
@prefix osmpower: <http://christian-kurze.de/ontology/osm/power#> .""")

	print(
"""###########################################
# Classes
###########################################""")

	for taginfo in tags:
		if taginfo['data']['on_node'] or taginfo['data']['on_way'] or taginfo['data']['on_area'] or taginfo['data']['on_relation']:
			print(namespace + ':' + to_classname(taginfo['data']['value']) + " rdf:type owl:Class .")
			if taginfo['key'] == 'power':
				print(namespace + ':' + to_classname(taginfo['data']['value']) + ' rdfs:subClassOf owl:Thing .')
			else:
				print(namespace + ':' + to_classname(taginfo['data']['value']) + ' rdfs:subClassOf ' + namespace + ':' + to_classname(taginfo['key']) + ' .')
			
			if taginfo['data']['wiki']['en']['description']:
				print(namespace + ':' + to_classname(taginfo['data']['value']) + ' rdfs:comment "' + taginfo['data']['wiki']['en']['description'] + '" .')
			
			print('')

def to_classname(tag):
	return snake_to_camel(tag)

def snake_to_camel(word):
	return ''.join(x.capitalize() or '_' for x in word.split('_'))

if __name__ == '__main__':
	main()
