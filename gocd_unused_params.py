#!/bin/python

import os, re
from bs4 import BeautifulSoup
import argparse

class GoCDConfig(object):
	def __init__(self, config_file):
		self.config_file = config_file
		self.tree = BeautifulSoup(open(self.config_file), 'xml')
		self.template_map = self.build_template_map()
		self.pipeline_map = self.build_pipeline_map()

	@classmethod
	def find_all(cls, root, tag):
		return [ c for c in root.children if c.name and tag in c.name ]

	"""
	Loads the config_file(XML) as a DOM Tree and 
	returns a map of pipeline name to its sub-tree
	"""
	def build_pipeline_map(self):
		pipeline_groups = self.tree.cruise.find_all('pipelines', group=True)
		pipeline_map = dict()
		for gp in pipeline_groups:
			pipelines = GoCDConfig.find_all(gp, 'pipeline')
			for pipeline in pipelines:
				name = gp['group']+"_"+pipeline['name']
				pipeline_map[name] = pipeline

		return pipeline_map

	def build_template_map(self):
		templates = GoCDConfig.find_all(self.tree.cruise.templates, 'pipeline')
		template_map = dict()
		for pipeline_template in templates:
			template_map[pipeline_template['name']] = pipeline_template
		return template_map

class Pipelines(object):
	def __init__(self, pipeline_map, template_map):
		self.pipeline_map = pipeline_map
		self.template_map = template_map

	def pipeline_stages_of(self, pipeline_name):
		if pipeline_name in self.pipeline_map:
			pipeline = self.pipeline_map[pipeline_name]
			stages = []
			if pipeline.has_attr('template'):
				template = self.template_map[pipeline['template']]
				stages = template.find_all('stage')
			else:
				stages = pipeline.find_all('stage')
			return stages
		else:
			print "[ERROR] Pipeline %s not found" % pipeline_name
			print "List of available pipeline names %s" % self.pipeline_map.keys()
			return None

	def tasks_for(self, pipeline_name):
		stages = self.pipeline_stages_of(pipeline_name)
		tasks_in_pipeline = []
		for stage in stages:
			tasks_stage = stage.find_all("tasks")
			for ts in tasks_stage:
				tasks_in_pipeline.extend(ts.children)
		return tasks_in_pipeline

	"""
	Fetches and returns all the parameters for the pipeline
	"""
	def parameter_map(self, pipeline_name):
		params = self.pipeline_map[pipeline_name].params.find_all('param')
		param_map = dict()
		for param in params:
			param_map[param['name']] = param.text
		return param_map

	def unused_parameters(self, pipeline_name):
		PARAM_REGEX = re.compile("#\\{([\w]+)\\}", re.M|re.I)
		parameters = self.parameter_map(pipeline_name)
		keys = set(parameters.keys())
		tasks = self.tasks_for(pipeline_name)
		used_keys = []
		for task in tasks:
			task_str = str(task)
			for line in task_str.split("\n"):
				matches = PARAM_REGEX.findall(line)
				if matches:
					used_keys.extend(list(matches))

		used = set(used_keys)
		unused = keys.difference(used)
		return unused


if __name__ == '__main__':
	arg_parser = argparse.ArgumentParser(prog="Inspect GoCD Parameter")
	arg_parser.add_argument('-i', '--input', 
		help='Input location of config.xml', 
		required=True)
	arg_parser.add_argument('-g', '--pipeline_group', 
		help='Pipeline group name', 
		required=True)
	arg_parser.add_argument('-p', '--pipeline_name', 
		help='Pipeline name for which this inspection needs to be performed', 
		required=True)

	args = arg_parser.parse_args()
	pipeline_name = args.pipeline_name
	pipeline_group = args.pipeline_group
	input_file = args.input

	cfg = GoCDConfig(input_file)
	pipelines = Pipelines(cfg.pipeline_map, cfg.template_map)
	pipeline_with_group = pipeline_group+"_"+pipeline_name
	unused_params = pipelines.unused_parameters(pipeline_with_group)
	print "Pipeline group: %s, name: %s" % (pipeline_group, pipeline_name)
	print "# of unused parameters %s" % (len(unused_params))
	print unused_params
	pass