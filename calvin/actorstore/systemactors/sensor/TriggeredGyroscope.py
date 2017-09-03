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

from calvin.actor.actor import Actor, manage, condition, stateguard, calvinsys

class TriggeredGyroscope(Actor):

    """
    Measure the rotation

    Inputs:
        trigger : any token triggers meausurement

    Outputs:
        rotation :  Rotation around the x,y and z axis. Is returned as a dict with the x,y, and z keys.
    """

    @manage(exclude=['level'])
    def init(self):
        self.setup()

    def setup(self):
        self.level = calvinsys.open(self, "sensor.gyroscope")

    def teardown(self):
        calvinsys.close(self.level)

    def will_migrate(self):
        self.teardown()

    def did_migrate(self):
        self.setup()

    def will_end(self):
        self.teardown()

    @stateguard(lambda self: calvinsys.can_write(self.level))
    @condition(['trigger'], [])
    def trigger_measurement(self, _):
        calvinsys.write(self.level, True)
        
    @stateguard(lambda self: calvinsys.can_read(self.level))
    @condition([], ['rotation'])
    def read_measurement(self):
        level = calvinsys.read(self.level)
        return (level,)

    action_priority = (read_measurement, trigger_measurement)
    requires =  ['io.gyroscope']
