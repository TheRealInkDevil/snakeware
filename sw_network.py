import socket, shlex, time, threading, uuid, pathlib, sys, json, queue

maindir: pathlib.Path = pathlib.Path(__file__).parent
sys.path.append(str(maindir))

from sw_network_internal.node import NetworkNode

running = False
current_user_uuid: None | uuid.UUID = None

class MessageData:
	def __init__(self, data, conn_id, addr, flags):
		self.data: dict = data
		self.conn_id: str = conn_id
		self.addr = addr
		self.flags = flags

message_queue = queue.Queue()

def node_callback(d, conn_id, addr, flags):
	data = json.loads(d.decode())
	message_queue.put(MessageData(data, conn_id, addr, flags))

def stop_sw_network_node():
	global running
	running = False

def _message_data_recv_loop(output_queue: queue.Queue):
	while running:
		try:
			msg: MessageData = message_queue.get(False, 1)
			try:
				senderid = uuid.UUID(msg.data.get("sender"))
			except:
				continue
			output_queue.put({"type": "recv-msg", "data": msg, "sender": senderid})
			message_queue.task_done()
		except queue.Empty:
			continue

def gen_msg_data(cmd: str, uid, args: dict, use_udp: bool, is_bcast: bool = False, flags: int = 0, sequence_id: int = None, tcp_fragment: bool = False):
	r = {
		"cmd": cmd,
		"sender": str(uuid.UUID(uid))
	}
	r.update(args)
	msg = json.dumps(r).encode()
	res = {
		"payload": msg,
		"flags": flags,
		"sequence_id": sequence_id,
		"fragmented": tcp_fragment
	}
	if use_udp:
		if is_bcast:
			res.update({"type": "udp-bcast-bytes"})
		else:
			res.update({"type": "udp-send-bytes"})
	else:
		if is_bcast:
			res.update({"type": "tcp-bcast-bytes"})
		else:
			res.update({"type": "tcp-send-bytes"})
	
	return res

def run_sw_network_node(input_queue: queue.Queue, output_queue: queue.Queue):
	global running, current_user_uuid
	running = True
	node = NetworkNode()
	threading.Thread(target=node.tcp_listen, args=[node_callback]).start()
	threading.Thread(target=node.udp_listen, args=[node_callback]).start()
	threading.Thread(target=_message_data_recv_loop, args=[output_queue]).start()
	while running:
		try:
			cmd: dict = input_queue.get(False, 1)
			match cmd.get("type"):
				case "set-current-uuid":
					current_user_uuid = uuid.UUID(cmd.get("uuid"))
				case "tcp-send-bytes":
					node.tcp_send(cmd.get("id"), cmd.get("payload"), cmd.get("flags", 0), cmd.get("sequence_id", None), cmd.get("fragmented", False))
				case "tcp-bcast-bytes":
					node.tcp_bcast_connected(cmd.get("payload"), cmd.get("flags", 0), cmd.get("sequence_id", None), cmd.get("fragmented", False))
				case "tcp-send-str":
					node.tcp_send(cmd.get("id"), cmd.get("payload").encode(), cmd.get("flags", 0), cmd.get("sequence_id", None), cmd.get("fragmented", False))
				case "tcp-bcast-str":
					node.tcp_bcast_connected(cmd.get("payload").encode(), cmd.get("flags", 0), cmd.get("sequence_id", None), cmd.get("fragmented", False))
				case "tcp-connect":
					new_conn = node.tcp_connect(cmd.get("addr"), node_callback)
					output_queue.put({"type": "new-outgoing-conn", "id": new_conn})
				case "tcp-disconnect":
					node.tcp_disconnect(cmd.get("id"))
				case "tcp-req-ids":
					ids = node.get_tcp_ids()
					output_queue.put({"type": "tcp-id-list", "ids": ids})
				case "udp-send-bytes":
					node.udp_send(cmd.get("payload"), cmd.get("addr"), cmd.get("flags", 0), cmd.get("sequence_id", None))
				case "udp-send-str":
					node.udp_send(cmd.get("payload").encode(), cmd.get("addr"), cmd.get("flags", 0), cmd.get("sequence_id", None))
				case "udp-bcast-bytes":
					node.udp_lan_bcast(cmd.get("payload"), cmd.get("flags", 0), cmd.get("sequence_id", None))
				case "udp-bcast-str":
					node.udp_lan_bcast(cmd.get("payload").encode(), cmd.get("flags", 0), cmd.get("sequence_id", None))
			input_queue.task_done()
		except queue.Empty:
			continue
		except:
			continue