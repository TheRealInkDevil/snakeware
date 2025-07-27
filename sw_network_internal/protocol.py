#SW_NETWORKv1 spec
# Magic Number (4 bytes) - Always 0xDEADBEEF
# Version (1 byte)
# Flags (1 byte)
# Fragment Idx (2 bytes)
# Fragment Count (2 bytes)
# Sequence ID (4 bytes)
# Payload Length (4 bytes)
# CRC32 (4 bytes)
# Reserved (2 bytes)

import struct, zlib

# Header constants
HEADER_FORMAT = "!IBBHHIIIB"
MAGIC_NUMBER = 0xD1AB10C4
PROTOCOL_VERSION = 0x01
HEADER_SIZE = struct.calcsize(HEADER_FORMAT)
MAX_FRAGMENT_SIZE = 1024
MAX_UDP_SIZE = HEADER_SIZE + 1024
FLAGS_ACK_REQUIRED = 0b00000001
FLAGS_IS_ACK = 0b00000010
FLAGS_FRAGMENTED = 0b00000100
FLAGS_CONTROL_FRAME = 0b00001000
FLAGS_CHK = 0b00010000

# NetworkNode constants
NETWORK_IPC_PORT = 5000
NETWORK_UDP_PORT = 5001
NETWORK_TCP_PORT = 5002

def build_header(flags: int, frag_idx: int, frag_count: int, seq_id: int, payload: bytes):
    payload_len = len(payload)
    crc = zlib.crc32(payload)
    reserved = 0
    return struct.pack(HEADER_FORMAT,
        MAGIC_NUMBER,
        PROTOCOL_VERSION,
        flags,
        frag_idx,
        frag_count,
        seq_id,
        payload_len,
        crc,
        reserved
    )

def build_fragments(sequence_id: int, full_payload: bytes, other_flags: int = 0):
    fragments = []
    fragment_count = (len(full_payload) + MAX_FRAGMENT_SIZE) // MAX_FRAGMENT_SIZE
    for idx in range(fragment_count):
        start = idx * MAX_FRAGMENT_SIZE
        end = min(start + MAX_FRAGMENT_SIZE, len(full_payload))
        fragment_data = full_payload[start:end]

        flags = (FLAGS_FRAGMENTED if fragment_count > 1 else 0) | other_flags
        header = build_header(flags, idx, fragment_count, sequence_id, fragment_data)
        fragment = header + fragment_data
        fragments.append(fragment)
    return fragments

def parse_header(data: bytes):
    if len(data) > HEADER_SIZE:
        header = data[0:HEADER_SIZE]
    else:
        header = data

    magic, ver, flags, frag_idx, frag_count, seq_id, payload_len, crc, reserved = struct.unpack(HEADER_FORMAT, header)
    if magic != MAGIC_NUMBER:
        raise ValueError("Magic Number is invalid")
    if ver > PROTOCOL_VERSION:
        raise ValueError("Unsupported protocol version!")
    if frag_count > 1 and flags & FLAGS_FRAGMENTED != FLAGS_FRAGMENTED:
        raise ValueError("Fragmented message has no fragmented flag!")
    if frag_idx < 0 or frag_idx >= frag_count:
        raise ValueError("Fragment Idx is invalid!")
    if payload_len < 0:
        raise ValueError("Payload Length invalid!")
    
    return (ver, flags, frag_idx, frag_count, seq_id, payload_len, crc)

def split_header(data: bytes, force_crc32: bool = False):
    header = data[0:HEADER_SIZE]

    ver, flags, frag_idx, frag_count, seq_id, payload_len, crc = parse_header(header)
    
    payload = data[(HEADER_SIZE):(HEADER_SIZE+payload_len)]
    crcstatus = False
    if flags & FLAGS_CHK or force_crc32:
        if zlib.crc32(payload) != crc:
            if force_crc32:
                raise ValueError("CRC32 invalid!")
        else:
            crcstatus = True
    
    return (payload, ver, flags, frag_idx, frag_count, seq_id, crcstatus)