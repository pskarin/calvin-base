from cpython.mem cimport PyMem_Malloc, PyMem_Free
from libc.stdint cimport uint8_t, uint32_t, uint64_t
from libc.string cimport memset, memcpy
from libc.stdio cimport FILE, fopen, fclose, fwrite
import time
import sys
import uuid
import platform
import re

cdef struct CTF_metadata_packet_header:
  uint32_t  magic
  uint8_t   uuid[16]
  uint32_t  checksum
  uint32_t  content_size
  uint32_t  packet_size
  uint8_t   compression_scheme
  uint8_t   encryption_scheme
  uint8_t   checksum_scheme
  uint8_t   major
  uint8_t   minor

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

cdef enum:
  PACKET_BUFFER_SIZE = 4098

cdef struct Buffer:
  FILE * fp
  uint64_t startts
  uint64_t endts
  uint32_t checkpoint_index
  uint32_t capacity
  uint32_t index
  uint8_t data[PACKET_BUFFER_SIZE]

cdef struct LogEntry:
  uint32_t type
  uint64_t timestamp
  uint32_t actor
  uint32_t method
  int valueDefined
  double value

cdef int bufferSize = 1
cdef LogEntry * buffer = <LogEntry *>PyMem_Malloc(sizeof(LogEntry)*bufferSize)

cdef int bufferIndex = 0
cdef int actorId = 0
cdef int methodId = 0
cdef clock_offset =  int(time.time()*1000000000)
trace_uuid = uuid.uuid4()
wrapped = False

actors=["error"]
types = ["enter", "trigger", "exit"]
methods=["error"]

def allocate(int size):
  global buffer, bufferIndex, bufferSize
  """ Initialize the log buffer to a certain size. Throws MemoryError. The
      old buffer is released first so it cannot be reused on error. """
  PyMem_Free(buffer)
  buffer = <LogEntry *>PyMem_Malloc(sizeof(LogEntry)*size)
  if not buffer:
    raise MemoryError()
  bufferSize = size
  bufferIndex = 0

def deallocate():
  global buffer, bufferSize
  PyMem_Free(buffer)
  bufferSize = 0

def register_actor(name):
  """ Store the actor name and return an ID to use in its place """
  global actorId,actors
  actors.append(name)
  actorId += 1
  sys.stderr.write("Register actor {}\n".format(name))
  return actorId

def get_actor_id(name):
  global actors

  if name in actors:
    return actors.index(name)
  else:
    return register_actor(name)

def update_actor(id, name):
  """ Store the actor name and return an ID to use in its place """
  global actors
  sys.stderr.write("Update actor {} => {}\n".format(actors[id], name))
  actors[id] = name

def register_method(method):
  """ Store the method name and return an ID to use in its place """
  global methodId,methods
  methods.append(method)
  methodId += 1
  sys.stderr.write("Register method  {}\n".format(method))
  return methodId

def refresh_method_id(method):
  global methods

  if method in actors:
    return methods.index(method)
  else:
    return register_method(method)

def store(int typeid, int actorid, unsigned int methodid, int valueDefined, double value):
  sys.stderr.write("Monitor:store\n")
  global buffer, bufferIndex, bufferSize, wrapped
  buffer[bufferIndex].type = typeid
  buffer[bufferIndex].timestamp = long(time.time()*1000000000)
  buffer[bufferIndex].actor = actorid
  buffer[bufferIndex].method = methodid
  buffer[bufferIndex].valueDefined = valueDefined
  buffer[bufferIndex].value = value
  bufferIndex += 1
  if bufferIndex == bufferSize:
    bufferIndex = 0
    wrapped = True

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

cdef writepacket(Buffer * packet):
  global trace_uuid

  if packet.checkpoint_index == 0:
    return

  cdef CTF_event_packet_header eventpacketheader
  cdef CTF_event_packet_context eventpacketcontext

  eventpacketheader.magic = 0xc1fc1fc1
  for i in range(0,16):
    eventpacketheader.uuid[i] = ord(trace_uuid.bytes[i])
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

def finish():
  global buffer,bufferIndex,bufferSize,actors,methods,wrapped,trace_uuid,clock_offset

  cdef Buffer packet
  cdef CTF_metadata_packet_header metaheader
  memset(&metaheader, 0, sizeof(metaheader))

  metaheader.magic = 0x75D11D57
  metaheader.content_size = 0
  metaheader.packet_size = 0
  metaheader.major = 1
  metaheader.minor = 8

  metadata = get_CTF_metadata().encode('utf8')

  # TODO: Create folder trace/
  cdef FILE * fp = fopen("trace/metadata", "wb")
  if (fp):
    header = "/* CTF 1.8 */".encode('utf8')
    fwrite(<char *>header, 1, len(header), fp)
    fwrite(<char *>metadata, 1, len(metadata), fp)
    fclose(fp)
  
  fp = fopen("trace/channel0", "wb")
  memset(&packet, 0, sizeof(packet))
  packet.fp = fp
  packet.capacity = PACKET_BUFFER_SIZE
  
  if bufferSize > 1:
    start = 0
    end = bufferIndex
    if wrapped:
      start = bufferIndex
      end = bufferIndex+bufferSize
    for _i in range(start, end):
      i = _i%bufferSize;
      sys.stdout.write("{};{};{};{};".format(int(buffer[i].timestamp/1000), actors[buffer[i].actor], 
        types[buffer[i].type], methods[buffer[i].method]))
      if buffer[i].valueDefined == 1:
        sys.stdout.write("{}".format(buffer[i].value))
      print("")

      if (fp):
        # Writes the event header
        addUint32(&packet, 0xaaddaadd)
        addUint32(&packet, buffer[i].type)
        addUint64(&packet, buffer[i].timestamp-clock_offset)
                
        # Write event
        addUint32(&packet, buffer[i].actor)
        if buffer[i].type == 1:
          addUint32(&packet, buffer[i].method)
          if buffer[i].valueDefined == 1:
            addDouble(&packet, buffer[i].value)
          else:
            addDouble(&packet, 0)

        checkpoint(&packet, buffer[i].timestamp-clock_offset)

  writepacket(&packet)
  fclose(fp) 
  trace_uuid = uuid.uuid4()

def get_CTF_metadata():
  global actors, methods

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
