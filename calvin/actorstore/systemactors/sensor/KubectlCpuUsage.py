# -*- coding: utf-8 -*-

# Copyright (c) 2016 Ericsson AB
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

from calvin.actor.actor import Actor, ActionResult, manage, condition, guard
from calvin.utilities.calvinlogger import get_actor_logger

_log = get_actor_logger(__name__)


class KubectlCpuUsage(Actor):

    """
        Get cpu usage of Kubernetes cluster
    Outputs:
        usage : cpu usage in millicores
    """

    @manage(["data", "last_timestamp"])
    def init(self):
        self.setup()
        self.data = None
        self.last_timestamp = 0.0

    def setup(self):
        self.use('calvinsys.sensors.kubectl', shorthand='kube')
        self['kube'].enable(metric="cpu/usage_rate")

        
    def will_migrate(self):
        self['kube'].disable()
        
    def did_migrate(self):
        self.setup()
    
    @condition([], [])
    @guard(lambda self: self['kube'].has_metric("cpu/usage_rate"))
    def measure(self):
        metrics = self['kube'].get_metric("cpu/usage_rate")
        self['kube'].ack_metric("cpu/usage_rate")
        self.data = [item for item in metrics["metrics"] if item["timestamp"] > self.last_timestamp ]
        return ActionResult()
        
    @condition([], ['usage'])
    @guard(lambda self: self.data)
    def dispatch_single(self):
        item = self.data.pop(0)
        payload = { "values" : item }
        self.last_timestamp = item["timestamp"]
        # Node-red wants millisecs
        payload["timestamp"] = item["timestamp"] * 1000
        del item["timestamp"]

        return ActionResult(production=(payload,))

    action_priority = (dispatch_single, measure,)
    requires =  ['calvinsys.sensors.kubectl']


