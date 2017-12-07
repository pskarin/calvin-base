# -*- coding: utf-8 -*-

# Copyright (c) 2017 Ericsson AB
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

from calvin.runtime.south.calvinlib import base_calvinlib_object
import re


class Re(base_calvinlib_object.BaseCalvinlibObject):
    """
    Functions for handling regexp.
    """

    init_schema = {
        "description": "setup regexp module",
        "type": "object",
        "properties": {}
    }

    findall = {
        "description": "wrapper for python regexp findall",
        "type": "object",
        "properties": {
            "pattern": {"type": "string"},
            "string": {"type": "string"}
        }
    }

    match = {
        "description": "wrapper for python regexp match",
        "type": "object",
        "properties": {
            "pattern": {"type": "string"},
            "string": {"type": "string"}
        }

    }

    def init(self):
        pass

    def findall(self, pattern, string):
        return re.findall(pattern, string)

    def match(self, pattern, string):
        return re.match(pattern, string)
