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

from calvin.runtime.north.calvin_token import Token
from calvin.runtime.north.plugins.port.queue.common import QueueFull, QueueEmpty, COMMIT_RESPONSE
from calvin.runtime.north.plugins.port import DISCONNECT
from calvin.utilities import calvinlogger

_log = calvinlogger.get_logger(__name__)

class CollectLIFO(object):

    """
    Last in first out 
    """

    def __init__(self, port_properties, peer_port_properties):
        super(CollectLIFO, self).__init__()
        # Set default queue length to 4 if not specified

        length = port_properties.get('queue_length', 4)
        self.lifo = [Token(0)] * length
        self.N = length
        self.direction = port_properties.get('direction', None)
        self.nbr_peers = port_properties.get('nbr_peers', 1)
        self.readers = set()
        # NOTE: For simplicity, modulo operation is only used in lifo access,
        #       all read and write positions are monotonousy increasing
        self.write_pos = 0
        self.read_pos = {}
        self.tentative_read_pos = {}
        self._type = "collect_lifo"
        self.writer = None  # Not part of state, assumed not needed in migrated information
        self.exhausted_tokens = {}
        self.termination = {}

    def __str__(self):
        return "Tokens: %s, w:%i, r:%s, tr:%s" % (self.lifo, self.write_pos, self.read_pos, self.tentative_read_pos)

    def _state(self, remap=None):
        if remap is None:
            state = {
                'queuetype': self._type,
                'lifo': [t.encode() for t in self.lifo],
                'N': self.N,
                'readers': list(self.readers),
                'write_pos': self.write_pos,
                'read_pos': self.read_pos,
                'tentative_read_pos': self.tentative_read_pos,
            }
        else:
            # Remapping of port ids, also implies reset of tokens
            state = {
                'queuetype': self._type,
                'lifo': [Token(0).encode()] * len(self.lifo),
                'N': self.N,
                'readers': [remap[pid] if pid in remap else pid for pid in self.readers],
                'write_pos': 0,
                'read_pos': {remap[pid] if pid in remap else pid: [] for pid, pos in self.read_pos.items()},
                'tentative_read_pos': {remap[pid] if pid in remap else pid: [] for pid, pos in self.tentative_read_pos.items()},
             }
        return state

    def _set_state(self, state):
        self._type = state.get('queuetype',"collect_lifo")
        self.lifo = [Token.decode(d) for d in state['lifo']]
        self.N = state['N']
        self.readers = set(state['readers'])
        self.write_pos = state['write_pos']
        self.read_pos = state['read_pos']
        self.tentative_read_pos = state['tentative_read_pos']
        self.reader_offset = state.get('reader_offset', {pid: 0 for pid in self.readers})

    @property
    def queue_type(self):
        return self._type

    def add_writer(self, writer, properties):
        self.writer = writer

    def remove_writer(self, writer):
        pass

    def add_reader(self, reader, properties):
        if not isinstance(reader, basestring):
            raise Exception('Not a string: %s' % reader)
        if reader in self.readers:
            return
        self.readers.add(reader)
        if len(self.readers) > self.nbr_peers:
            self.nbr_peers = len(self.readers)
            # Replicated actor connect for first time, start from oldest possible
            #oldest = min(self.read_pos.values())
            #_log.info("ADD_READER %s %s %d" % (reader, str(id(self)), oldest))
            self.reader_offset[reader] = 0
            self.read_pos[reader] = []
            self.tentative_read_pos[reader] = []
        else:
            self.reader_offset[reader] = 0
            self.read_pos[reader] = []
            self.tentative_read_pos[reader] = []

    def remove_reader(self, reader):
        if reader not in self.readers:
            return
        del self.read_pos[reader]
        del self.tentative_read_pos[reader]
        del self.reader_offset[reader]
        self.readers.discard(reader)
        self.nbr_peers -= 1

    def is_exhausting(self, peer_id=None):
        if peer_id is None:
            return bool(self.termination)
        else:
            return peer_id in self.termination

    def exhaust(self, peer_id, terminate):
        self.termination[peer_id] = (terminate, False)
        _log.debug("exhaust %s %s %s" % (self._type, peer_id, DISCONNECT.reverse_mapping[terminate]))
        if peer_id not in self.readers:
            return []
        if terminate in [DISCONNECT.EXHAUST_PEER_SEND, DISCONNECT.EXHAUST_OUTPORT]:
            # Retrive remaining tokens to be returned
            tokens = []
            for read_pos in range(self.read_pos[peer_id], self.write_pos):
                tokens.append([read_pos, self.lifo[read_pos % self.N]])
            # Remove the peer, so no more waiting for this peer to read
            self.remove_reader(peer_id)
            _log.debug("Send exhaust tokens %s" % tokens)
            del self.termination[peer_id]
            return tokens 
        return []

    def any_outstanding_exhaustion_tokens(self):
        # Between having asked actor to exhaust and receiving exhaustion tokens we don't want to assume that
        # the exhaustion is done.
        return any([not t[1] for t in self.termination.values()])

    def set_exhausted_tokens(self, tokens):
        _log.debug("set_exhausted_tokens %s %s %s" % (self._type, tokens, {k:DISCONNECT.reverse_mapping[v[0]] for k, v in self.termination.items()}))
        self.exhausted_tokens.update(tokens)
        for peer_id in tokens.keys():
            try:
                # We can get set_exhaust_token even after done with the termination, since it is a confirmation
                # from peer port it has handled the exhaustion also
                self.termination[peer_id] = (self.termination[peer_id][0], True)
            except:
                pass
        remove = []
        for peer_id, exhausted_tokens in self.exhausted_tokens.items():
            if self._transfer_exhaust_tokens(peer_id, exhausted_tokens):
                remove.append(peer_id)
        for peer_id in remove:
            del self.exhausted_tokens[peer_id]
        # If fully consumed remove peer_ids in tokens
        for peer_id in tokens.keys():
            if (self.termination.get(peer_id, (-1,))[0] in [DISCONNECT.EXHAUST_PEER_RECV, DISCONNECT.EXHAUST_INPORT] and
                min(self.read_pos.values() or [0]) == self.write_pos):
                del self.termination[peer_id]
                # Acting as inport then only one reader, remove it if still around
                try:
                    reader = next(iter(self.readers))
                    self.remove_reader(reader)
                except:
                    _log.exception("Tried to remove reader on fanout lifo")
        return self.nbr_peers

    def _transfer_exhaust_tokens(self, peer_id, exhausted_tokens):
        # exhausted tokens are in sequence order, but could contain tokens already in queue
        for pos, token in exhausted_tokens[:]:
            if not self.slots_available(1, peer_id):
                break
            r = self.com_write(token, peer_id, pos)
            _log.debug("exhausted_tokens on %s: (%d, %s) %s" % (
                peer_id, pos, str(token), COMMIT_RESPONSE.reverse_mapping[r]))
            # This is a token that now is in the queue, was in the queue or is invalid, for all cases remove it
            exhausted_tokens.pop(0)
        return not bool(exhausted_tokens)

    def get_peers(self):
        if self.direction == "out":
            return self.readers
        elif self.direction == "in" and self.writer is not None:
            return set([self.writer])
        else:
            return None

    def write(self, data, metadata):
        self.lifo[self.write_pos % self.N] = data # %self.n, just to be safe?
        self.update_read_pos(self.write_pos)
        self.write_pos += 1
        return True

    def slots_available(self, length, metadata):
        return True

    def tokens_available(self, length, metadata):
        if not self.readers:
            return False
        if metadata not in self.readers:
            raise Exception("No reader %s in %s" % (metadata, self.readers))
        return len(self.tentative_read_pos[metadata]) >= length 

    #
    # Reading is done tentatively until committed
    #
    def peek(self, metadata):
        if metadata not in self.readers:
            raise Exception("Unknown reader: '%s'" % metadata)
        if not self.tokens_available(1, metadata):
            raise QueueEmpty(reader=metadata)

        data = self.lifo[ self.tentative_read_pos[metadata].pop() % self.N]
        return data

    def commit(self, metadata):
        _log.debug("COMMIT EXHAUSTING???")
        self.read_pos[metadata] = self.tentative_read_pos[metadata]
        remove = []
        for peer_id, exhausted_tokens in self.exhausted_tokens.items():
            if self._transfer_exhaust_tokens(peer_id, self.exhausted_tokens[peer_id]):
                # Emptied
                remove.append(peer_id)
        for peer_id in remove:
            del self.exhausted_tokens[peer_id]
        # If fully consumed remove queue
        terminated = False
        if self.termination:
            _log.debug("COMMIT %s %s" % (metadata, {k:DISCONNECT.reverse_mapping[v[0]] for k, v in self.termination.items()}))
        if (self.termination.get(metadata, (-1,))[0] in [DISCONNECT.EXHAUST_PEER_RECV, DISCONNECT.EXHAUST_INPORT] and
            min([len(poss) for poss in self.read_pos.values()] or [0]) and
            self.termination.get(metadata, (-1, False))[1]):
            del self.termination[metadata]
            terminated = True
            # Acting as inport then only one reader, remove it if still around
            try:
                reader = self.readers[0]
                self.remove_reader(reader)
            except:
                _log.exception("Tried to remove reader on fanout lifo")
        return terminated

    def cancel(self, metadata):
        for writer in self.writers:
            self.tentative_read_pos[writer] = self.read_pos[writer]

    #
    # Read pos management
    #

    def update_read_pos(self, write_pos):
        for metadata in self.tentative_read_pos:
            self.tentative_read_pos[metadata].append(write_pos)
            self.tentative_read_pos[metadata] = [pos for pos in self.tentative_read_pos[metadata] if pos >= max(write_pos - (self.N-1), 0)]

    #
    # Queue operations used by communication which utilize a sequence number
    #

    def com_write(self, data, metadata, sequence_nbr):
        if sequence_nbr == self.write_pos:
            self.write(data, metadata)
            return COMMIT_RESPONSE.handled
        elif sequence_nbr < self.write_pos:
            return COMMIT_RESPONSE.unhandled
        else:
            return COMMIT_RESPONSE.invalid
