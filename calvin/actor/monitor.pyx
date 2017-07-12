from cpython.mem cimport PyMem_Malloc, PyMem_Free
import time
import sys

cdef struct LogEntry:
  unsigned int type
  unsigned long timestamp
  unsigned int actor
  unsigned int method
  int valueDefined
  double value

cdef int bufferSize = 1
cdef LogEntry * buffer = <LogEntry *>PyMem_Malloc(sizeof(LogEntry)*bufferSize)

cdef int bufferIndex = 0
cdef int actorId = 0
cdef int methodId = 0
wrapped = False

actors=["error"]
types = ["enter", "trigger", "exit"]
methods=[""]

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
  return actorId

def update_actor(id, name):
  """ Store the actor name and return an ID to use in its place """
  global actors
  actors[id] = name

def register_method(method):
  """ Store the method name and return an ID to use in its place """
  global methodId,methods
  methods.append(method)
  methodId += 1
  return methodId

def store(int typeid, int actorid, unsigned int methodid, int valueDefined, double value):
  global buffer, bufferIndex, bufferSize, wrapped
  buffer[bufferIndex].type = typeid
  buffer[bufferIndex].timestamp = long(time.time()*1000000)
  buffer[bufferIndex].actor = actorid
  buffer[bufferIndex].method = methodid
  buffer[bufferIndex].valueDefined = valueDefined
  buffer[bufferIndex].value = value
  bufferIndex += 1
  if bufferIndex == bufferSize:
    bufferIndex = 0
    wrapped = True
  

def finish():
  global buffer,bufferIndex,bufferSize,actors,methods,wrapped
  if bufferSize > 1:
    start = 0
    end = bufferIndex
    if wrapped:
      start = bufferIndex
      end = bufferIndex+bufferSize
    for _i in range(start, end):
      i = _i%bufferSize;
      sys.stdout.write("{};{};{};{};".format(buffer[i].timestamp, actors[buffer[i].actor], 
        types[buffer[i].type], methods[buffer[i].method]))
      if buffer[i].valueDefined == 1:
        sys.stdout.write("{}".format(buffer[i].value))
      print("")
