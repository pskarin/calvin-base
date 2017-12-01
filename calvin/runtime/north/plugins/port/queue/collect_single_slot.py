# -*- coding: utf-8 -*-

# Copyright (c) 2015 Ericsson AB
#
# Licensed under the Apache License, Version 2.0 (the 'License');
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an 'AS IS' BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from calvin.runtime.north.calvin_token import Token
from calvin.runtime.north.plugins.port.queue.common import COMMIT_RESPONSE
from calvin.runtime.north.plugins.port import DISCONNECT
from calvin.utilities import calvinlogger

_log = calvinlogger.get_logger(__name__)

class CollectSingleSlot(object):

    '''
    Just one slot
    '''

    def __init__(self, port_properties, peer_port_properties):
        super(CollectSingleSlot, self).__init__()
        # Set default queue length to 4 if not specified

        self.token = None
        self.direction = port_properties.get('direction', 'in')
        self.nbr_peers = port_properties.get('nbr_peers', 1)
        self.readers = set()
        # NOTE: For simplicity, modulo operation is only used in lifo access,
        #       all read and write positions are monotonousy increasing
        self.read_ready = {}
        self.tentative_read_ready = {}
        self._type = 'collect_single_slot'
        self.writer = None  # Not part of state, assumed not needed in migrated information
        self.exhausted_tokens = {}
        self.termination = {}

    def __str__(self):
        return 'Token: %s' % any(self.tentative_read_ready)

    def _state(self, remap=None):
        if remap is None:
            state = {
                'queuetype': self._type,
                'token': self.token,
                'readers': list(self.readers),
                'read_ready': self.read_ready,
                'tentative_read_ready': self.tentative_read_ready,
            }
        else:
            # Remapping of port ids, also implies reset of tokens
            state = {
                'queuetype': self._type,
                'token': Token(0).encode(),
                'readers': [remap[pid] if pid in remap else pid for pid in self.readers],
                'read_ready': {remap[pid] if pid in remap else pid: False for pid, pos in self.read_ready.items()},
                'tentative_read_ready': {remap[pid] if pid in remap else pid: False for pid, pos in self.tentative_read_ready.items()},
            }
        return state

    def _set_state(self, state):
        self._type = state.get('queuetype',self._type)
        self.lifo = Token.decode(state['token']) 
        self.readers = set(state['readers'])
        self.read_ready = state['read_ready']
        self.tentative_read_ready = state['tentative_read_ready']
  
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
            #oldest = min(self.read_ready.values())
            #_log.info('ADD_READER %s %s %d' % (reader, str(id(self)), oldest))
            self.read_ready[reader] = False
            self.tentative_read_ready[reader] = False
        else:
            self.read_ready[reader] = False
            self.tentative_read_ready[reader] = False

    def remove_reader(self, reader):
        if reader not in self.readers:
            return
        del self.read_ready[reader]
        del self.tentative_read_ready[reader]
        self.readers.discard(reader)
        self.nbr_peers -= 1

    def is_exhausting(self, peer_id=None):
        if peer_id is None:
            return bool(self.termination)
        else:
            return peer_id in self.termination

    def exhaust(self, peer_id, terminate):
        self.termination[peer_id] = (terminate, False)
        _log.debug('exhaust %s %s %s' % (self._type, peer_id, DISCONNECT.reverse_mapping[terminate]))
        if peer_id not in self.readers:
            return []
        if terminate in [DISCONNECT.EXHAUST_PEER_SEND, DISCONNECT.EXHAUST_OUTPORT]:
            # Retrive remaining tokens to be returned
            tokens = [self.token]
            # Remove the peer, so no more waiting for this peer to read
            self.remove_reader(peer_id)
            _log.debug('Send exhaust tokens %s' % tokens)
            del self.termination[peer_id]
            return tokens 
        return []

    def any_outstanding_exhaustion_tokens(self):
        # Between having asked actor to exhaust and receiving exhaustion tokens we don't want to assume that
        # the exhaustion is done.
        return any([not t[1] for t in self.termination.values()])

    def set_exhausted_tokens(self, tokens):
        _log.debug('set_exhausted_tokens %s %s %s' % (self._type, tokens, {k:DISCONNECT.reverse_mapping[v[0]] for k, v in self.termination.items()}))
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
                any(self.tentative_read_ready.values())):
                del self.termination[peer_id]
                # Acting as inport then only one reader, remove it if still around
                try:
                    reader = next(iter(self.readers))
                    self.remove_reader(reader)
                except:
                    _log.exception('Tried to remove reader on collect single slot')
        return self.nbr_peers

    def _transfer_exhaust_tokens(self, peer_id, exhausted_tokens):
        # exhausted tokens are in sequence order, but could contain tokens already in queue
        for pos, token in exhausted_tokens[:]:
            if not self.slots_available(1, peer_id):
                break
            r = self.com_write(token, peer_id, pos)
            _log.debug('exhausted_tokens on %s: (%d, %s) %s' % (
                peer_id, pos, str(token), COMMIT_RESPONSE.reverse_mapping[r]))
            # This is a token that now is in the queue, was in the queue or is invalid, for all cases remove it
            exhausted_tokens.pop(0)
        return not bool(exhausted_tokens)

    def get_peers(self):
        if self.direction == 'out':
            return self.readers
        elif self.direction == 'in' and self.writer is not None:
            return set([self.writer])
        else:
            return None

    def write(self, data, metadata):
        self.token = data
        
        # Set all readers to True
        for metadata in self.tentative_read_ready:
            self.tentative_read_ready[metadata] = True

        return True

    def slots_available(self, length, metadata):
        return True

    def tokens_available(self, length, metadata): # Disregards length argument. Suspect this is for scheduling. "Who has >= than n tokens?"
        if not self.readers:
            return False
        if metadata not in self.readers:
            raise Exception('No reader %s in %s' % (metadata, self.readers))
        return self.tentative_read_ready[metadata] 

    #
    # Reading is done tentatively until committed
    #
    def peek(self, metadata):
        if metadata not in self.readers:
            raise Exception('Unknown reader: %s' % metadata)
        if not self.tokens_available(1, metadata):
            raise QueueEmpty(reader=metadata)

        self.tentative_read_ready[metadata] = False
        return self.token

    def commit(self, metadata):
        _log.debug('COMMIT EXHAUSTING???')
        self.read_ready[metadata] = self.tentative_read_ready[metadata]
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
            _log.debug('COMMIT %s %s' % (metadata, {k:DISCONNECT.reverse_mapping[v[0]] for k, v in self.termination.items()}))
        if (self.termination.get(metadata, (-1,))[0] in [DISCONNECT.EXHAUST_PEER_RECV, DISCONNECT.EXHAUST_INPORT] and
            any(self.read_ready.values()) and
            self.termination.get(metadata, (-1, False))[1]):
            del self.termination[metadata]
            terminated = True
            # Acting as inport then only one reader, remove it if still around
            try:
                reader = self.readers[0]
                self.remove_reader(reader)
            except:
                _log.exception('Tried to remove reader on collect single slot')
        return terminated

    def cancel(self, metadata):
        for writer in self.writers:
            self.tentative_read_ready[writer] = self.read_ready[writer]
        
    #
    # Queue operations used by communication which utilize a sequence number
    #   William - TO_DO: What does sequence number represent? 
    # 

    def com_write(self, data, metadata, sequence_nbr):
        if sequence_nbr == self.write_pos:
            self.write(data, metadata)
            return COMMIT_RESPONSE.handled
        elif sequence_nbr < self.write_pos:
            return COMMIT_RESPONSE.unhandled
        else:
            return COMMIT_RESPONSE.invalid