# Cython implementation for Common Trace Format definitions
# In addition to using LTTng one can request that Calvin outputs data directly as CTF
# files. This further reduces tracing impact since it reduces data conversion and communication.
# In the LTTng implementation data such as actor names are sent as strings while dumping it
# to CTF just stures ids and the names are written into the meta-data structures. It should be
# feasable to hook into LTTng as a client and provide an updating meta-data stream which allows
# this format with LTTng.

cdef struct CTF_event_packet_header:
  uint32_t  magic
  uint8_t   uuid[16]
  uint32_t  stream_id

cdef struct CTF_event_header:
  uint32_t  fill
  uint32_t  id
  uint64_t  nstime

cdef struct CTF_event_packet_context:
  uint64_t  nstime_start
  uint64_t  nstime_end
  uint64_t  content_size
  uint64_t  packet_size
  uint32_t  events_discarded
  uint32_t  cpu_id

##### Returns the CTF meta-data file
import re

def get_CTF_metadata(trace_uuid, platform, clock_offset, actors, methods):
  actorenum = "enum e_actors: uint32_t {\n"
  for i in range(0, len(actors)):
    actorenum += "  " + re.sub("[.:]", "_", actors[i])+ ",\n"
  actorenum += "};\n"

  methodenum = "enum e_methods: uint32_t {\n"
  for i in range(0, len(methods)):
    methodenum += "  " + methods[i] + ",\n"
  methodenum += "};\n"

  # TODO: Set the Calvin UUID somewhere (trace:uuid, env:hostname etc)
  return """
typealias integer { size = 8;  signed = false; } := uint8_t;
typealias integer { size = 16; signed = false; } := uint16_t;
typealias integer { size = 32; signed = false; } := uint32_t;
typealias integer { size = 64; signed = false; } := uint64_t;

typealias floating_point {
    exp_dig = 11;
    mant_dig = 53;
    align = 32;
} := double;

typealias floating_point {
    exp_dig = 8;
    mant_dig = 24;
    align = 32;
} := float;

trace {
  major = 1;

  minor = 8;
  uuid = """ + '"' + str(trace_uuid) + '"' + """;
  byte_order = le;
  packet.header := struct {
    uint32_t magic;
    uint8_t  uuid[16];
    uint32_t stream_id;
  };
};

env {
  hostname = \"""" + platform.node() + """\";
};

clock {
  name = monotonic;
  uuid = "f8e0885e-d597-4ee9-8771-30daf06bb645";
  description = "Monotonic Clock";
  freq = 1000000000;
  offset = """ + str(clock_offset) + """;
};

typealias integer {
  size = 64;
  align = 8;
  signed = false;
  map = clock.monotonic.value;
} := nano_timestamp_t;

stream {
  id = 0;
  event.header := struct {
    uint32_t fill;
    uint32_t id;
    nano_timestamp_t timestamp;
  };
  packet.context := struct {
    nano_timestamp_t timestamp_begin;
    nano_timestamp_t timestamp_end;
    uint64_t content_size;
    uint64_t packet_size;
    uint32_t events_discarded;
    uint32_t cpu_id;
  };
};
""" + actorenum + """
""" + methodenum + """

event {
  id = 0;
  name = "calvin:actor_enter";
  stream_id = 0;
  fields := struct {
    enum e_actors actor;
  };
};

event {
  id = 1;
  name = "calvin:actor_trigger";
  stream_id = 0;
  fields := struct {
    enum e_actors actor;
    enum e_methods _func;
    double value;
  };
};

event {
  id = 2;
  name = "calvin:actor_exit";
  stream_id = 0;
  fields := struct {
    enum e_actors actor;
  };
};

"""

##### CTF stream buffer
from libc.string cimport memcpy

cdef checkpoint(Buffer * packet, uint64_t ts):
  packet.checkpoint_index = packet.index
  if packet.index == 0:
    packet.startts = ts
  packet.endts = ts

cdef ensure_capacity(Buffer * packet, uint32_t size):
  if packet.capacity < packet.index + size:
    writepacket(packet)

cdef addUint32(Buffer * packet, uint32_t d):
  ensure_capacity(packet, sizeof(uint32_t))
  memcpy(&packet.data[packet.index], &d, sizeof(uint32_t))
  packet.index += sizeof(uint32_t)  

cdef addUint64(Buffer * packet, uint64_t d):
  ensure_capacity(packet, sizeof(uint64_t))
  memcpy(&packet.data[packet.index], &d, sizeof(uint64_t))
  packet.index += sizeof(uint64_t)  

cdef addDouble(Buffer * packet, double d):
  ensure_capacity(packet, sizeof(double))
  memcpy(&packet.data[packet.index], &d, sizeof(double))
  packet.index += sizeof(double)  


##### Stores a CTF packet to file
from libc.stdio cimport fwrite

cdef writepacket(Buffer * packet):
  if packet.checkpoint_index == 0:
    return

  cdef CTF_event_packet_header eventpacketheader
  cdef CTF_event_packet_context eventpacketcontext

  eventpacketheader.magic = 0xc1fc1fc1
  for i in range(0,16):
    eventpacketheader.uuid[i] = packet.uuid[i]
  eventpacketheader.stream_id = 0
  
  eventpacketcontext.nstime_start = packet.startts
  eventpacketcontext.nstime_end = packet.endts
  eventpacketcontext.packet_size = (sizeof(eventpacketheader) + sizeof(eventpacketcontext) + packet.checkpoint_index)*8
  eventpacketcontext.content_size = eventpacketcontext.packet_size
  eventpacketcontext.events_discarded = 0
  eventpacketcontext.cpu_id = 0

  fwrite(&eventpacketheader, sizeof(eventpacketheader), 1, packet.fp)
  fwrite(&eventpacketcontext, sizeof(eventpacketcontext), 1, packet.fp)
  fwrite(&packet.data[0], 1, packet.checkpoint_index, packet.fp)

  for i in range(packet.checkpoint_index, packet.index):
    packet.data[i-packet.checkpoint_index] = packet.data[i]
  packet.index = packet.index - packet.checkpoint_index
  packet.checkpoint_index = 0
