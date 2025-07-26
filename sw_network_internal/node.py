import socket, random, types, threading, time, struct, uuid, zlib
from .protocol import NETWORK_TCP_PORT, NETWORK_UDP_PORT, build_fragments, FLAGS_ACK_REQUIRED, FLAGS_CHK, FLAGS_CONTROL_FRAME, FLAGS_FRAGMENTED, FLAGS_IS_ACK, MAX_UDP_SIZE, split_header, HEADER_SIZE, parse_header, MAX_FRAGMENT_SIZE, build_header

class NetworkNode:
    def __init__(self, udp_port: int = NETWORK_UDP_PORT, tcp_port: int = NETWORK_TCP_PORT):
        #init sockets
        self.udp_socket: socket.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        self.tcp_server_socket: socket.socket = None
        self.tcp_connections = {}
        self.udp_port = udp_port
        self.tcp_port = tcp_port
        self.running_udp = False
        self.running_tcp = False
        self.await_ack = []
        self.ignore_seq_ids = []
        #default config
        self.force_crc32 = True #force checksum

    def get_tcp_ids(self):
        res = []
        for key, value in self.tcp_connections:
            res.append((key, self.tcp_connections.get(key).get("addr")))
        return res

    #stop UDP traffic
    def udp_stop(self):
        self.running_udp = False
        try:
            self.udp_socket.close()
        finally:
            pass

    #UDP listen loop
    def udp_listen(self, callback: types.FunctionType):
        self.udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        self.udp_socket.bind(('', self.udp_port))
        recvaddrs: dict[socket._Address, dict[int, list[bytes]]] = {}
        self.running_udp = True
        while self.running_udp:
            try:
                data, addr = self.udp_socket.recvfrom(MAX_UDP_SIZE)
            except OSError:
                break
            if not self.running_udp:
                break
            payload, ver, flags, frag_idx, frag_count, seq_id, crcstatus = split_header(data, self.force_crc32)
            if seq_id in self.ignore_seq_ids:
                continue
            if flags & FLAGS_ACK_REQUIRED == FLAGS_ACK_REQUIRED:
                self.udp_send(struct.pack("!HH", frag_idx, frag_count), addr, FLAGS_IS_ACK, seq_id)
            if flags & FLAGS_IS_ACK == FLAGS_IS_ACK:
                fidx, fcount = struct.unpack("!HH", payload)
                ack_id = "sid" + str(seq_id) + "fidx" + str(fidx) + "fcount" + str(fcount)
                try:
                    self.await_ack.remove(ack_id)
                except:
                    raise
            elif flags & FLAGS_FRAGMENTED == FLAGS_FRAGMENTED:
                if recvaddrs.get(addr):
                    addrdat: dict[int, list[bytes]] = recvaddrs.get(addr)
                else:
                    addrdat: dict[int, list[bytes]] = {}
                if addrdat.get(seq_id):
                    sequence: list[bytes] = addrdat.get(seq_id)
                    if len(sequence) != frag_count:
                        #raise IndexError("Fragment Count Mismatch")
                        pass
                else:
                    sequence: list[bytes] = []
                    for i in range(frag_count):
                        sequence.append(None)
                sequence[frag_idx] = payload
                addrdat.update({seq_id: sequence})
                recvaddrs.update({addr: addrdat})
                if None not in sequence:
                    final_data = bytes()
                    for dat in sequence:
                        final_data = final_data + dat
                    callback(final_data, "*UDP*", addr, flags)
                    addrdat.pop(seq_id)
                    recvaddrs.update({addr: addrdat})
            else:
                callback(payload, "*UDP*", addr, flags)
        try:
            self.udp_socket.close()
        finally:
            self.udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

    #udp LAN broadcast
    def udp_lan_bcast(self, payload: bytes, flags: int = 0, seqID: int = None, port: int = NETWORK_UDP_PORT):
        self.udp_send(payload, ('255.255.255.255', port), flags, seqID)

    #udp send    
    def udp_send(self, payload: bytes, addr, flags: int = 0, seqID: int = None):
        if not seqID:
            seqID = int.from_bytes(random.randbytes(4))
        frags = build_fragments(seqID, payload, FLAGS_CHK | flags)
        fidx = 0
        fcount = len(frags)
        self.ignore_seq_ids.append(seqID)
        for frag in frags:
            if flags & FLAGS_ACK_REQUIRED == FLAGS_ACK_REQUIRED:
                ack_wait_id = "sid" + str(seqID) + "fidx" + str(fidx) + "fcount" + str(fcount)
                self.await_ack.append(ack_wait_id)
                self.udp_socket.sendto(frag, addr)
                if self.running_udp:
                    while ack_wait_id in self.await_ack:
                        time.sleep(0.01)
                        if ack_wait_id in self.await_ack:
                            self.udp_socket.sendto(frag, addr)
            else:
                self.udp_socket.sendto(frag, addr)
            fidx += 1
            time.sleep(0.01)
            self.ignore_seq_ids.remove(seqID)

    #stop tcp functions
    def tcp_stop(self):
        self.running_tcp = False
        try:
            self.tcp_server_socket.shutdown(socket.SHUT_RDWR)
            self.tcp_server_socket.close()
        except:
            pass
        for tcp_conn in self.tcp_connections.copy().values():
            conn: socket.socket = tcp_conn.get("socket")
            try:
                conn.shutdown(socket.SHUT_RDWR)
                conn.close()
            except:
                pass

    #tcp connection accept loop
    def tcp_listen(self, callback: types.FunctionType):
        self.running_tcp = True
        self.tcp_server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.tcp_server_socket.bind(('', self.tcp_port))
        while self.running_tcp:
            self.tcp_server_socket.listen(5)
            conn, addr = self.tcp_server_socket.accept()
            connectionid = str(uuid.uuid4())
            self.tcp_connections.update({connectionid: {"outgoing": False, "socket": conn, "addr": addr}})
            threading.Thread(target=self.tcp_accept, args=[connectionid, conn, addr, callback]).start()
            if not self.running_tcp:
                break
        self.tcp_server_socket.shutdown(socket.SHUT_RDWR)
        self.tcp_server_socket.close()
    
    #tcp recv loop
    def tcp_accept(self, connid: str, conn: socket.socket, addr, callback: types.FunctionType):
        fragments = {}
        self.running_tcp = True
        while self.running_tcp:
            try:
                header = conn.recv(HEADER_SIZE)
            except OSError:
                break
            else:
                if not header:
                    break
            ver, flags, frag_idx, frag_count, seq_id, payload_len, crc = parse_header(header)
            if flags & FLAGS_CHK == FLAGS_CHK or self.force_crc32:
                check_crc32 = True
            else:
                check_crc32 = False
            try:
                payload = conn.recv(payload_len)
            except OSError:
                break
            else:
                if not payload:
                    break
            if check_crc32:
                if zlib.crc32(payload) != crc:
                    #raise ValueError("CRC32 Invalid.")
                    pass
            if seq_id in self.ignore_seq_ids:
                continue
            elif flags & FLAGS_FRAGMENTED == FLAGS_FRAGMENTED:
                if fragments.get(seq_id):
                    sequence: list[bytes] = fragments.get(seq_id)
                    if len(sequence) != frag_count:
                        #raise IndexError("Fragment Count Mismatch")
                        pass
                else:
                    sequence: list[bytes] = []
                    for i in range(frag_count):
                        sequence.append(None)
                sequence[frag_idx] = payload
                fragments.update({seq_id: sequence})
                if None not in sequence:
                    final_data = bytes()
                    for dat in sequence:
                        final_data = final_data + dat
                    callback(final_data, connid, addr, flags)
                    fragments.pop(seq_id)
            else:
                callback(payload, connid, addr, flags)
        try:
            conn.shutdown(socket.SHUT_RDWR)
            conn.close()
            self.tcp_connections.pop(connid)
        except:
            pass

    #tcp connect to other
    def tcp_connect(self, addr, callback: types.FunctionType):
        conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        conn.connect(addr)
        connectionid = str(uuid.uuid4())
        self.tcp_connections.update({connectionid: {"outgoing": True, "socket": conn, "addr": addr}})
        threading.Thread(target=self.tcp_accept, args=[connectionid, conn, addr, callback]).start()
        return connectionid
    
    #tcp broadcast to all connected
    def tcp_bcast_connected(self, payload: bytes, flags: int = 0, seqID: int = None, fragmented: bool = False):
        if not seqID:
            seqID = int.from_bytes(random.randbytes(4))
        fragments: list[bytes] = []
        if fragmented:
            fragments.extend(build_fragments(seqID, payload, FLAGS_CHK | flags))
        else:
            fragments.extend([build_header(FLAGS_CHK | flags, 0, 1, seqID, payload) + payload])
        for frag in fragments:
            for tcp_conn in self.tcp_connections.values():
                conn: socket.socket = tcp_conn.get("socket")
                conn.send(frag)
    
    #tcp send to connection_id
    def tcp_send(self, id: str, payload: bytes, flags: int = 0, seqID: int = None, fragmented: bool = False):
        if not seqID:
            seqID = int.from_bytes(random.randbytes(4))
        fragments: list[bytes] = []
        if fragmented:
            fragments.extend(build_fragments(seqID, payload, FLAGS_CHK | flags))
        else:
            fragments.extend([build_header(FLAGS_CHK | flags, 0, 1, seqID, payload) + payload])
        conn: socket.socket = self.tcp_connections.get(id).get("socket")
        for frag in fragments:
            conn.send(frag)
    
    def tcp_disconnect(self, id: str):
        try:
            conn: socket.socket = self.tcp_connections.get(id).get("socket")
            conn.shutdown(socket.SHUT_RDWR)
            conn.close()
        except:
            pass