# This tracing module supports two modes using the Common Trace Format. 
#   1. It stores an in memory circular buffer with lookups which is written to file as the runtime exist. This is for the lowest impact tracing.
#   2. The module can forward trace points to LTTng and be traced through LTTng sessions using the LTTng user space library (lttng-usst). In this mode
#      the module does lookup before forwarding to LTTng (which means transfering actor names as strings etc). The benefits however are a rich set of
#      tools, real-time monitoring, low memory footprint and potentially trace time synchronization between peers.  

##### Action types. These go into the typeid of CTF data.
ACTOR_FIRE_ENTER = 0
ACTOR_FIRE_EXIT = 1
ACTOR_METHOD_FIRE = 2
ACTOR_METHOD_FIRE_D = 3

##### Define trace buffer

from cpython.mem cimport PyMem_Malloc, PyMem_Free
from libc.stdint cimport uint8_t, uint32_t, uint64_t

cdef struct LogEntry:
  uint32_t type
  uint64_t timestamp
  uint32_t actor
  uint32_t method
  double value

cdef int bufferSize = 1
cdef LogEntry * buffer = <LogEntry *>PyMem_Malloc(sizeof(LogEntry)*bufferSize)


##### Module setup

import uuid
import time

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


##### Actor tracepoint registration

import sys

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


##### Generic store tracepoint
# This binds to a store function
#def _store_ctf(int typeid, int actorid, unsigned int methodid, value):
#  global buffer, bufferIndex, bufferSize, wrapped
#  buffer[bufferIndex].type = typeid
#  buffer[bufferIndex].timestamp = long(time.time()*1000000000)
#  buffer[bufferIndex].actor = actorid
#  buffer[bufferIndex].method = methodid
#  buffer[bufferIndex].value = value
#  bufferIndex += 1
#  if bufferIndex == bufferSize:
#    bufferIndex = 0
#    wrapped = True

# ĹTTng tracepoints
cdef extern:
  void lttng_calvin_actor_fire_enter(const char *)
  void lttng_calvin_actor_fire_exit(const char *)
  void lttng_calvin_actor_method_fire(const char * actor_id, const char * method_id)
  void lttng_calvin_actor_method_fire_d(const char * actor_id, const char * method_id, double value)
  void lttng_calvin_actor_method_fire_dd(const char * actor_id, const char * method_id, double value1, double value2)

# LTTng function dict
lttngf = {
  0: lambda aid,mid,value: lttng_calvin_actor_fire_enter(actors[aid]),
  1: lambda aid,mid,value: lttng_calvin_actor_fire_exit(actors[aid]),
  2: lambda aid,mid,value: lttng_calvin_actor_method_fire(actors[aid],methods[mid]),
  3: lambda aid,mid,value: lttng_calvin_actor_method_fire_d(actors[aid],methods[mid],value),
};

def _store_lttng(int typeid, int actorid, unsigned int methodid, value):
  if not isinstance(value, (list, tuple)):
    lttngf[typeid](actorid, methodid, value)
  else:
    lttng_calvin_actor_method_fire_dd(actors[actorid],methods[methodid],value[0],value[1])
    
#def _store_both(int typeid, int actorid, unsigned int methodid, value):
#  _store_lttng(typeid, actorid, methodid, value)
#  _store_ctf(typeid, actorid, methodid, value)

store = _store_lttng

##### Write to file
import platform
from libc.string cimport memset
from libc.stdio cimport FILE, fopen, fclose, fwrite
import ctf          # CTF Python bindings
cimport ctf as ctfc   # CTF C bindings
import os

def finish(name):
  global buffer,bufferIndex,bufferSize,actors,methods,wrapped,trace_uuid,clock_offset

  cdef ctfc.Buffer packet
  cdef ctfc.CTF_metadata_packet_header metaheader
  memset(&metaheader, 0, sizeof(metaheader))

  metaheader.magic = 0x75D11D57
  metaheader.content_size = 0
  metaheader.packet_size = 0
  metaheader.major = 1
  metaheader.minor = 8

  for i in range(0,16):
    packet.uuid[i] = ord(trace_uuid.bytes[i])

  metadata = ctf.get_CTF_metadata(trace_uuid, platform, clock_offset, actors, methods).encode('utf8')

  tracedirpath = os.path.join(os.environ['HOME'], "trace", name or "noname")
  if not os.path.exists(tracedirpath):
    os.makedirs(tracedirpath)
  cdef FILE * fp = fopen(os.path.join(tracedirpath, "metadata"), "wb+")
  if (fp):
    header = "/* CTF 1.8 */".encode('utf8')
    fwrite(<char *>header, 1, len(header), fp)
    fwrite(<char *>metadata, 1, len(metadata), fp)
    fclose(fp)

 
  fp = fopen(os.path.join(tracedirpath, "channel0"), "wb")
  memset(&packet, 0, sizeof(packet))
  packet.fp = fp
  packet.capacity = ctfc.PACKET_BUFFER_SIZE
  
  if bufferSize > 1:
    start = 0
    end = bufferIndex
    if wrapped:
      start = bufferIndex
      end = bufferIndex+bufferSize
    for _i in range(start, end):
      i = _i%bufferSize;

      # Semicolon separated terminal output 
      sys.stdout.write("{};{};{};{};".format(int(buffer[i].timestamp/1000), actors[buffer[i].actor], 
        types[buffer[i].type], methods[buffer[i].method]))
      sys.stdout.write("{}".format(buffer[i].value))
      print("")

      # CTF trace
      if (fp):
        # Writes the event header
        ctfc.addUint32(&packet, 0xaaddaadd)
        ctfc.addUint32(&packet, buffer[i].type)
        ctfc.addUint64(&packet, buffer[i].timestamp-clock_offset)
                
        # Write event
        ctfc.addUint32(&packet, buffer[i].actor)
        if buffer[i].type == ACTOR_METHOD_FIRE or buffer[i].type == ACTOR_METHOD_FIRE_D:
          ctfc.addUint32(&packet, buffer[i].method)
          if buffer[i].type == ACTOR_METHOD_FIRE_D:
            ctfc.addDouble(&packet, buffer[i].value)
          else:
            ctfc.addDouble(&packet, 0)

        ctfc.checkpoint(&packet, buffer[i].timestamp-clock_offset)

  ctfc.writepacket(&packet)
  if (fp): fclose(fp) 
  trace_uuid = uuid.uuid4()
