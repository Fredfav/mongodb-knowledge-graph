import requests
import pymongo
import re

from  pprint import pprint
import json
from pyld import jsonld

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

# Some classes appear twice, so we have multiple parent classes
classes = { }
properties = { }
all_class_names = set(())

mongo_client = pymongo.MongoClient('localhost')

raw_class_tags_coll = mongo_client.osm.raw_class_tags
raw_releated_tags_coll = mongo_client.osm.raw_releated_tags
raw_key_wiki_information_coll = mongo_client.osm.raw_key_wiki_information

def main():
	# Get the Classes
	getKey(KEY_TO_ANALYZE, 0)

	# Get the related tags, i.e. Properties of Classes
	for row in raw_class_tags_coll.find():
		get_related_tags(row)

def getKey(key, depth=0, parent_class_name=''):
	r = requests.get('https://taginfo.openstreetmap.org/api/4/tags/list?key=' + key)
	if r.status_code != 200:
		print('Error while calling service')
		return

	r_json = r.json()
	r_json['key'] = key

	if not key in classes and len(r_json['data']) > 0:
		all_class_names.add(key)

		raw_class_tags_coll.replace_one(
			{ 'key': key },
			r_json,
			upsert=True)
		classes[key] = { 'dummy': 1 }

	for tag in r_json['data']:
		padding = ' ' * depth
		print('Get tag information for: ' + padding + tag['key'] + ' ' + tag['value'])

		if tag['value'] not in classes:
			getKey(tag['value'], depth + 1, tag['value'])

def get_related_tags(class_key):
	for tag in class_key['data']:
		print('Get related tags for ' + tag['key'] + ': ' + tag['value'])
		r = requests.get('https://taginfo.openstreetmap.org/api/4/tag/combinations?key=' + tag['key'] + '&value=' + tag['value'])
		if r.status_code != 200:
			print('Error while calling service')
			return
		r_json = r.json()
		r_json['key'] = tag['key']
		r_json['value'] = tag['value']
		
		raw_releated_tags_coll.replace_one(
			{ 'key': r_json['key'], 'value': r_json['value'] },
			r_json,
			upsert=True)

		other_key = set(())
		[other_key.add(data['other_key']) for data in r_json['data']]
		for key in other_key:
			get_key_wiki_information(key)

def get_key_wiki_information(key):
		print('Get wiki information for ' + key)
		r = requests.get('https://taginfo.openstreetmap.org/api/4/key/wiki_pages?key=' + key)
		if r.status_code != 200:
			print('Error while calling service')
			return
		r_json = r.json()
		r_json['key'] = key
		
		raw_key_wiki_information_coll.replace_one(
			{ 'key': r_json['key'] },
			r_json,
			upsert=True)

if __name__ == '__main__':
	main()
