import requests
import pymongo
import re
import subprocess
import os

from  pprint import pprint
import json

from rdflib import Graph, plugin
from rdflib.serializer import Serializer

# Semantic Description of OpenStreetMap: https://wiki.openstreetmap.org/wiki/OSM_Semantic_Network

# API doc for tags in Openstreetmap: https://taginfo.openstreetmap.org/taginfo/apidoc#api_4_keys_all
# Need the attributes of the classes (tags to use in combination): https://wiki.openstreetmap.org/wiki/Tag%3Asubstation%3Dconverter
#   /api/4/tag/combinations?key=highway&value=residential&page=1&rp=10&sortname=together_count&sortorder=desc
# HTTP requests: https://requests.readthedocs.io/en/master/
# PyLD: JSON-LD in Python (pip3 install PyLD), https://github.com/digitalbazaar/pyld

# Example Ontology in JSON-LD https://gist.github.com/stain/7690362

# sudo yum -y install git python3 pymongo dnspython
# PyOSM: https://pypi.org/project/esy-osm-pbf/
# pip3 install pymongo dnspython requests esy-osm-pbf pyld rdflib-jsonld

# curl -OL https://download.geofabrik.de/europe/germany/bayern-latest.osm.pbf
# curl -OL https://download.geofabrik.de/europe/germany/germany-latest.osm.pbf

OPENSTREETMAP_NAMESPACE = 'osmpower'
OSMPOWER_URL = 'http://christian-kurze.de/ontology/osm/power'
KEY_TO_ANALYZE = 'power'
#TTL_INSTANCE_FILENAME = OPENSTREETMAP_NAMESPACE + '_germany.ttl'
TTL_INSTANCE_FILENAME = OPENSTREETMAP_NAMESPACE + '_bavaria.ttl'
OWL_TO_JSON_JAR_ABSOLUTE_PATH = '/Users/christian.kurze/development/owl2jsonld/target/uberjar/owl2jsonld-0.2.2-SNAPSHOT-standalone.jar'

#mongo_client = pymongo.MongoClient('mongodb+srv://knowledge:graph@knowledgegraphfreetier.9cnxl.mongodb.net/osm?retryWrites=true&w=majority')
mongo_client = pymongo.MongoClient('localhost:27017')

raw_class_tags_coll = mongo_client.osm.raw_class_tags
#raw_objects_coll = mongo_client.osm.raw_objects_germany
raw_objects_coll = mongo_client.osm.raw_objects
context_coll = mongo_client.osm.context
ontology_coll = mongo_client.osm.ontology
instance_coll = mongo_client.osm.instance
instance_coll.create_index([('geometry', pymongo.GEOSPHERE)])


attribute_comments = {}
tags_used_for_classes = set(())

def main():
	tags = [taginfo for taginfo in raw_class_tags_coll.aggregate([{'$unwind': {'path': '$data'}}])]	
	
	for tag in raw_class_tags_coll.aggregate([{'$unwind': {'path': '$data'}}, {'$project': {'_id': 0, 'key': '$data.key','value': '$data.value'}}]):
		tags_used_for_classes.add(tag['key'])
		tags_used_for_classes.add(tag['value'])

	create_ttl_file(tags)
	create_instances_mongodb(tags)
	create_part_of_relationship_ttl_and_mongodb()

def create_ttl_file(tags):
	ttl_file = open(TTL_INSTANCE_FILENAME, 'w')
	ttl_file.write(
"""@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix owl: <http://www.w3.org/2002/07/owl#> .
@prefix owl2: <http://www.w3.org/2006/12/owl2#> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> . \n""")
	ttl_file.write('@prefix osmpower: <' + OSMPOWER_URL + '#> .\n\n')

	cnt = 0
	for asset in raw_objects_coll.find({'$or': [ {'type':'node'}, {'type':'way'}]}):
		osmclass = derive_class(asset)
		ttl_file.write(OPENSTREETMAP_NAMESPACE + ':' + str(asset['_id']) + ' rdf:type ' + get_shortened_class_name_rdf_syntax(osmclass['_id']) + ' ; \n')
		for tag in asset['tags']:
			if not tag in tags_used_for_classes:
				ttl_file.write('    ' + OPENSTREETMAP_NAMESPACE + ':' + to_attributename(tag) + ' "' + escape_value(asset['tags'][tag]) + '" ; \n')

		# TODO: Geometry - if the first and last entry of nodes-array is the same --> Polygon, if not --> Line
		ttl_file.write(' . \n\n')

		cnt = cnt + 1
		if cnt % 1000 == 0:
			print ('Processed ' + str(cnt) + ' Assets')
	ttl_file.close()

def create_instances_mongodb(tags):
	print('Creating instances in MongoDB')

	cnt = 0
	for asset in raw_objects_coll.find({'$or': [  {'type':'node'}]}): # {'type':'way'},
		osmclass = derive_class(asset)

		instance = {
			'_id': OSMPOWER_URL + '#' + str(asset['_id']),
			'@type': osmclass['_id'],
			'@context': OSMPOWER_URL
		}
		
		for tag in asset['tags']:
			if not tag in tags_used_for_classes:
				instance[to_attributename(tag)] = escape_value(asset['tags'][tag])

		# Geometry - if the first and last entry of nodes-array is the same --> Polygon, if not --> Line
		if asset['type'] == 'way':
			if asset['nodes'][0] == asset['nodes'][-1]:
				instance['geometry'] = {
					'type': 'Polygon',
					'coordinates': [ [ [round(float(x['lon']),7), round(float(x['lat']),7)] for x in asset['nodes'] ] ] 
				}
			else:
				instance['geometry'] = {
					'type': 'LineString',
					'coordinates': [ [round(float(x['lon']),7), round(float(x['lat']),7)] for x in asset['nodes'] ] 
				}
		# Nodes are Points only
		if asset['type'] == 'node':
			instance['geometry'] = {
				'type': 'Point',
				'coordinates': [ round(asset['lon'],7), round(asset['lat'],7) ] 
			}

		cnt = cnt + 1
		if cnt % 1000 == 0:
			print ('Processed ' + str(cnt) + ' Assets')

		instance_coll.replace_one({'_id': instance['_id']}, instance, upsert=True)

def create_part_of_relationship_ttl_and_mongodb():
	print('Create partOf and hasPart relationships')
	ttl_file = open(TTL_INSTANCE_FILENAME, 'a') # append to TTL file

	# Start with all assets that have a polygon 
	for asset in instance_coll.find({'geometry.type': 'Polygon'}):
		# Find all assets within that polygon
		for i in instance_coll.find(
			{
				'geometry': {
					'$geoWithin': {
						'$geometry': asset['geometry']
					}
				},
				'_id': { '$ne': asset['_id']}
			}):
			# update hasPart
			hasPart_doc = { '_id': i['_id'], '@type': i['@type']}
			if 'name' in i:
				hasPart_doc['name'] = i['name']
			instance_coll.update_one(
				{'_id':asset['_id']},
				{'$addToSet': { 'hasPart': hasPart_doc}}
			)
			ttl_file.write(get_shortened_class_name_rdf_syntax(asset['_id']) + ' ' + OPENSTREETMAP_NAMESPACE + ':hasPart ' + get_shortened_class_name_rdf_syntax(i['_id']) + ' . \n')

			# update partOf 
			partOf_doc = { '_id': asset['_id'], '@type': asset['@type']}
			if 'name' in asset:
				hasPart_doc['name'] = asset['name']
			instance_coll.update_one(
				{'_id':i['_id']},
				{'$addToSet': { 'partOf': partOf_doc}}
			)
			ttl_file.write(get_shortened_class_name_rdf_syntax(i['_id']) + ' ' + OPENSTREETMAP_NAMESPACE + ':partOf ' + get_shortened_class_name_rdf_syntax(asset['_id']) + ' . \n')

	ttl_file.close()

def derive_class(asset):
	#print('*****************************************************')
	#print('Asset: ')
	#print(asset)
	# Which tags of this asset can be used to derive the class?
	potential_class_tags = []
	for class_tag in tags_used_for_classes:
		if class_tag in asset['tags']:
			potential_class_tags.append(class_tag)

	#print('potential_class_tags: ')
	#print(potential_class_tags)
	#print('ontology_class: ')
	ontology_class = get_ontology_class(potential_class_tags, asset)

	
	#print(ontology_class)

	return ontology_class

def get_ontology_class(tags, asset):
	'''
	Graph Lookup in MongoDB which of the tags provides us with the most elements in the class tree?
	This is the lowest class level that we should instantiate.
	'''

	candidate_classes = [ OSMPOWER_URL + '#' + to_classname(asset['tags'][t]) for t in tags ]

	return ontology_coll.aggregate([
		{ '$match': { '_id': { '$in': candidate_classes } } }, 
		{ '$graphLookup': { 
			'from': 'ontology', 'startWith': '$subClassOf.@id', 
		 	'connectFromField': 'subClassOf.@id', 'connectToField': '_id', 'as': 'class_hierarchy' 
		}},
		{ '$addFields': { 'cnt_parent_classes': { '$size': '$class_hierarchy' } } }, 
		{ '$sort': { 'cnt_parent_classes': -1 } }, 
		{ '$limit': 1 } ] ).next()

def get_shortened_class_name_rdf_syntax(class_name):
	return class_name.replace(OSMPOWER_URL + '#', OPENSTREETMAP_NAMESPACE + ':')
	
def to_classname(tag):
	return snake_to_camel(tag)

def snake_to_camel(word):
	return ''.join(x.capitalize() or '_' for x in word.split('_'))

def to_attributename(word):
	return word.replace(':', '_').replace('¹', '')

def escape_value(value):
	return value.replace('"', '\\"')

def run_command(command):
    p = subprocess.Popen(command,
                         stdout=subprocess.PIPE)
    # in case we want to also see the errors:  ,stderr=subprocess.STDOUT
    return iter(p.stdout.readline, '')

if __name__ == '__main__':
	main()
