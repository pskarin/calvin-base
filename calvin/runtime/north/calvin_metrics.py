# -*- coding: utf-8 -*-

# Copyright (c) 2015 Ericsson AB
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import calvin.utilities.calvinconfig as calviconfig
import re
from calvin.utilities import calvinlogger

regex_identifier = "(([_a-zA-Z][_a-zA-Z0-9]{0,30}:){2}[_a-zA-Z][_a-zA-Z0-9]{0,30})"
re_id = re.compile(regex_identifier)
_log = calvinlogger.get_logger(__name__)

class BasicMetric:
  """ A simple float valued metric
  """
  def __init__(self, id, init):
    self.id = id
    self.value = init
    _log.info("{:s} {:5.3f}".format(self.id, self.value))

  def post(self, data):
    self.value = data
    _log.info("{:s} {:5.3f}".format(self.id, self.value))


  def getValue(self):
    return self.value

class CalvinMetrics:
  """ Handles metrics for resource management (actor placement)
  """
  def __init__(self):
    self.metrics = {}
    config = calviconfig.get()
    for metric in config.get_in_order('metrics') or []:
      if not re_id.match(metric['id']):
        raise NameError("Invalid metric identifier: " + metric['id'])
      self.metrics[metric['id']] = BasicMetric(metric['id'], float(metric['init']))

  def post(self, id, data):
    if id in self.metrics:
      self.metrics[id].post(data)
      return True
    return False

  def ids(self):
    return list(self.metrics.keys())