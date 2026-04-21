from pox.core import core
import pox.openflow.libopenflow_01 as of
from pox.lib.util import dpid_to_str
from pox.lib.addresses import IPAddr

log = core.getLogger()

BLOCKED_SRC_IP = "10.0.0.1"
BLOCKED_DST_IP = "10.0.0.3"

class PacketDropController(object):

    def __init__(self, connection):
        self.connection = connection
        self.mac_to_port = {}
        connection.addListeners(self)
        log.info("Switch %s connected", dpid_to_str(connection.dpid))
        self._install_drop_rules()

    def _install_drop_rules(self):
        log.info("Installing DROP rules: %s -> %s",
                 BLOCKED_SRC_IP, BLOCKED_DST_IP)

        # Drop ICMP from h1 to h3 (highest priority)
        msg = of.ofp_flow_mod()
        msg.priority = 200
        msg.match.dl_type = 0x0800
        msg.match.nw_proto = 1
        msg.match.nw_src = IPAddr(BLOCKED_SRC_IP)
        msg.match.nw_dst = IPAddr(BLOCKED_DST_IP)
        msg.idle_timeout = 0
        msg.hard_timeout = 0
        self.connection.send(msg)

        # Drop all IP from h1 to h3
        msg2 = of.ofp_flow_mod()
        msg2.priority = 190
        msg2.match.dl_type = 0x0800
        msg2.match.nw_src = IPAddr(BLOCKED_SRC_IP)
        msg2.match.nw_dst = IPAddr(BLOCKED_DST_IP)
        msg2.idle_timeout = 0
        msg2.hard_timeout = 0
        self.connection.send(msg2)

        log.info("DROP rules installed.")

    def _handle_PacketIn(self, event):
        packet = event.parsed
        if not packet.parsed:
            log.warning("Unparsed packet, ignoring")
            return

        dpid = event.connection.dpid
        inport = event.port

        # Learn MAC to port mapping
        self.mac_to_port[packet.src] = inport
        log.debug("Learned MAC %s on port %s", packet.src, inport)

        # Find output port
        if packet.dst in self.mac_to_port:
            outport = self.mac_to_port[packet.dst]
            log.debug("Forwarding to port %s", outport)

            # Install forwarding flow rule
            msg = of.ofp_flow_mod()
            msg.priority = 10
            msg.idle_timeout = 60
            msg.hard_timeout = 120
            msg.match = of.ofp_match.from_packet(packet, inport)
            msg.actions.append(of.ofp_action_output(port=outport))
            msg.data = event.ofp
            self.connection.send(msg)
        else:
            # Flood — destination unknown
            log.debug("Flooding packet from %s", packet.src)
            msg = of.ofp_packet_out()
            msg.data = event.ofp
            action = of.ofp_action_output(port=of.OFPP_FLOOD)
            msg.actions.append(action)
            self.connection.send(msg)


def launch():
    def _handle_ConnectionUp(event):
        log.info("Connection up: %s", dpid_to_str(event.dpid))
        PacketDropController(event.connection)

    core.openflow.addListenerByName("ConnectionUp", _handle_ConnectionUp)
    log.info("Packet Drop Simulator started.")
    log.info("Blocking: %s -> %s", BLOCKED_SRC_IP, BLOCKED_DST_IP)