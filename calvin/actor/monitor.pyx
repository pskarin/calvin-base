from cpython.mem cimport PyMem_Malloc, PyMem_Free
import time

cdef struct LogEntry:
  unsigned int type
  unsigned long timestamp
  unsigned int actor
  unsigned int method

cdef int bufferSize = 100000
cdef LogEntry * buffer = <LogEntry *>PyMem_Malloc(sizeof(LogEntry)*bufferSize)

cdef int bufferIndex = 0
cdef int actorId = 0
cdef int methodId = 0
wrapped = False

actors=["error"]
types = ["enter", "trigger", "exit"]
methods=[""]
cdef unsigned long startts = 0

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

def store(int typeid, int actorid, unsigned int methodid):
  global buffer, bufferIndex, bufferSize,startts,wrapped
  buffer[bufferIndex].type = typeid
  buffer[bufferIndex].timestamp = time.time()*1000000
  buffer[bufferIndex].actor = actorid
  buffer[bufferIndex].method = methodid
  bufferIndex += 1
  if bufferIndex == bufferSize:
    if startts == 0:
      startts = buffer[0].timestamp
    bufferIndex = 0
    wrapped = True
  

def finish():
  global buffer,bufferIndex,bufferSize,actors,methods,startts,wrapped
  cdef unsigned long ts = buffer[bufferIndex%bufferSize].timestamp
  start = 0
  end = bufferIndex
  if wrapped:
    start = bufferIndex
    end = bufferIndex+bufferSize
  else:
    startts = buffer[0].timestamp
  for _i in range(start, end):
    i = _i%bufferSize;
    print("{:10d}; {:10s}; {:10s}; {:10s}".format(buffer[i].timestamp-startts, actors[buffer[i].actor], 
      types[buffer[i].type], methods[buffer[i].method]))
    startts= buffer[i].timestamp
