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
TTL_INSTANCE_FILENAME = OPENSTREETMAP_NAMESPACE + '_bavaria.ttl'
OWL_TO_JSON_JAR_ABSOLUTE_PATH = '/Users/christian.kurze/development/owl2jsonld/target/uberjar/owl2jsonld-0.2.2-SNAPSHOT-standalone.jar'

#mongo_client = pymongo.MongoClient('mongodb+srv://knowledge:graph@knowledgegraphfreetier.9cnxl.mongodb.net/osm?retryWrites=true&w=majority')
mongo_client = pymongo.MongoClient('localhost:27017')

raw_class_tags_coll = mongo_client.osm.raw_class_tags
raw_objects_coll = mongo_client.osm.raw_objects
context_coll = mongo_client.osm.context
ontology_coll = mongo_client.osm.ontology

attribute_comments = {}
tags_used_for_classes = set(())

def main():
	tags = [taginfo for taginfo in raw_class_tags_coll.aggregate([{'$unwind': {'path': '$data'}}])]	
	
	for tag in raw_class_tags_coll.aggregate([{'$unwind': {'path': '$data'}}, {'$project': {'_id': 0, 'key': '$data.key','value': '$data.value'}}]):
		tags_used_for_classes.add(tag['key'])
		tags_used_for_classes.add(tag['value'])

	create_ttl_file(tags)
	# create_jsonld_context()

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

def old():
	print('Creating TTL file for Ontology: ' + TTL_FILENAME)

	ttl_file = open(TTL_FILENAME, 'w')

	ttl_file.write(
"""@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix owl: <http://www.w3.org/2002/07/owl#> .
@prefix owl2: <http://www.w3.org/2006/12/owl2#> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> . \n""")
	ttl_file.write('@prefix osmpower: <' + OSMPOWER_URL + '#> .\n\n')

	ttl_file.write(
"""###########################################
# Classes
###########################################\n\n""")

	ttl_file.write(OPENSTREETMAP_NAMESPACE + ':PowerThing rdf:type owl:Class .\n')
	ttl_file.write(OPENSTREETMAP_NAMESPACE + ':PowerThing rdfs:subClassOf owl:Thing .\n')
	ttl_file.write(OPENSTREETMAP_NAMESPACE + ':PowerThing rdfs:comment "Parent class of all power-related things." .\n')

	for taginfo in tags:
		#if taginfo['data']['on_node'] or taginfo['data']['on_way'] or taginfo['data']['on_area'] or taginfo['data']['on_relation']:
			
		# Class
		ttl_file.write(OPENSTREETMAP_NAMESPACE + ':' + to_classname(taginfo['data']['value']) + ' rdf:type owl:Class .\n')
		if taginfo['key'] == 'power':
			ttl_file.write(OPENSTREETMAP_NAMESPACE + ':' + to_classname(taginfo['data']['value']) + ' rdfs:subClassOf ' + OPENSTREETMAP_NAMESPACE + ':PowerThing .\n')
		else:
			ttl_file.write(OPENSTREETMAP_NAMESPACE + ':' + to_classname(taginfo['data']['value']) + ' rdfs:subClassOf ' + OPENSTREETMAP_NAMESPACE + ':' + to_classname(taginfo['key']) + ' .\n')
		
		if taginfo['data']['wiki']['en']['description']:
			ttl_file.write(OPENSTREETMAP_NAMESPACE + ':' + to_classname(taginfo['data']['value']) + ' rdfs:comment "' + taginfo['data']['wiki']['en']['description'] + '" .\n')

		# All Attributes from related tags
		# Needs pruning for subclasses, currently all classes get all possible attributes
		for attribute in raw_releated_tags_coll.aggregate([
			{'$match':{'key':taginfo['key'],'value':taginfo['data']['value']}}, 
			{'$unwind': {'path':'$data'}},
			{'$group': {'_id': None,'keys':{'$addToSet': '$data.other_key'}}}, 
			{'$project':{'_id': 0,'keys': 1}}]):

			if 'keys' in attribute:
				attribute['keys'].sort()
				for attr in attribute['keys']:
					if not attr in tags_used_for_classes:
						ttl_file.write(OPENSTREETMAP_NAMESPACE + ':' + to_attributename(attr) +' a owl:DatatypeProperty ;\n')
						ttl_file.write('    rdfs:domain ' + OPENSTREETMAP_NAMESPACE + ':' + to_classname(taginfo['data']['value']) + ' ;\n')

						if attr in attribute_comments and 'description' in attribute_comments[attr] and len(attribute_comments[attr]['description']) > 0:
							ttl_file.write('    rdfs:comment "' + attribute_comments[attr]['description'].replace('"', '') + '" ;\n')

						ttl_file.write('    rdfs:range xsd:string .\n')
		
		# partOf relationship
		ttl_file.write(OPENSTREETMAP_NAMESPACE + ':partOf a owl:ObjectProperty ; \n')
		ttl_file.write('    rdfs:domain ' + OPENSTREETMAP_NAMESPACE + ':' + to_classname(taginfo['data']['value']) + ' ;\n')
		ttl_file.write('    rdfs:range ' + OPENSTREETMAP_NAMESPACE + ':PowerThing .\n')

		ttl_file.write('\n')

	ttl_file.close()

def create_jsonld_context():
	print('Creating JSON-LD context for Ontology: ' + TTL_FILENAME + ' (_id: ' + OSMPOWER_URL + ')')

	# Note: this requires owl2json: https://github.com/stain/owl2jsonld
	command = '/usr/bin/java -jar ' + OWL_TO_JSON_JAR_ABSOLUTE_PATH
	command = command + ' -o ' + os.getcwd() + '/' + OPENSTREETMAP_NAMESPACE + '.context.jsonld'
	command = command + ' file://' + os.getcwd() + '/' + OPENSTREETMAP_NAMESPACE + '.ttl'
	result = jarWrapper(command.split(' '))

	context_doc = json.load(open(os.getcwd() + '/' + OPENSTREETMAP_NAMESPACE + '.context.jsonld', 'r'))
	context_doc['_id'] = OSMPOWER_URL

	result = context_coll.replace_one({'_id': context_doc['_id']}, context_doc, upsert=True)
	print(result.raw_result)
	
def to_classname(tag):
	return snake_to_camel(tag)

def snake_to_camel(word):
	return ''.join(x.capitalize() or '_' for x in word.split('_'))

def to_attributename(word):
	return word.replace(':', '_')

def escape_value(value):
	return value.replace('"', '\\"')

def run_command(command):
    p = subprocess.Popen(command,
                         stdout=subprocess.PIPE)
    # in case we want to also see the errors:  ,stderr=subprocess.STDOUT
    return iter(p.stdout.readline, '')

def jarWrapper(command):
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    ret = []
    while process.poll() is None:
        line = process.stdout.readline()
        if line != '':
            ret.append(line[:-1])
    stdout, stderr = process.communicate()
    #ret += stdout.split('\n')
    #if stderr != '':
    #    ret += stderr.split('\n')
    # ret.remove('')
    return ret

if __name__ == '__main__':
	main()
