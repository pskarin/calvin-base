# See ctf.pyx for documentation

from libc.stdint cimport uint8_t, uint32_t, uint64_t

##### CTF standard definitions

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


##### CTF stream buffer

from libc.stdio cimport FILE

cdef enum:
  PACKET_BUFFER_SIZE = 4098

cdef struct Buffer:
  FILE * fp
  uint8_t  uuid[16]
  uint64_t startts
  uint64_t endts
  uint32_t checkpoint_index
  uint32_t capacity
  uint32_t index
  uint8_t data[PACKET_BUFFER_SIZE]


#### Buffer API
cdef checkpoint(Buffer * packet, uint64_t ts)
cdef ensure_capacity(Buffer * packet, uint32_t size)
cdef addUint32(Buffer * packet, uint32_t d)
cdef addUint64(Buffer * packet, uint64_t d)
cdef addDouble(Buffer * packet, double d)
cdef writepacket(Buffer * packet)