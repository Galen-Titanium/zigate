#
# Copyright (c) 2018 Sébastien RAMAGE
#
# For the full copyright and license information, please view the LICENSE
# file that was distributed with this source code.
#

import struct
from collections import OrderedDict
from binascii import hexlify
from .const import DATA_TYPE

RESPONSES = {}


def register_response(o):
    RESPONSES[o.msg] = o
    return o


class Response(object):
    msg = 0x0
    type = 'Base response'
    s = OrderedDict()
    format = {'addr': '{:04x}',
              'ieee': '{:016x}',
              'group': '{:04x}'}

    def __init__(self, msg_data, rssi):
        self.msg_data = msg_data
        self.rssi = rssi
        self.data = OrderedDict()
        self.decode()

    def __str__(self):
        d = ['{}:{}'.format(k, v) for k, v in self.data.items()]
        return 'RESPONSE 0x{:04X} - {} : {}'.format(self.msg,
                                                    self.type,
                                                    ', '.join(d))

    def __setitem__(self, key, value):
        self.data[key] = value

    def __getitem__(self, key):
        return self.data[key]

    def __delitem__(self, key):
        return self.data.__delitem__(key)

    def get(self, key, default):
        return self.data.get(key, default)

    def __contains__(self, key):
        return self.data.__contains__(key)

    def __len__(self):
        return len(self.data)

    def __iter__(self):
        return self.data.__iter__()

    def items(self):
        return self.data.items()

    def keys(self):
        return self.data.keys()

    def __getattr__(self, attr):
        return self.data[attr]

    def decode(self):
        fmt = '!'
        msg_data = self.msg_data
        keys = list(self.s.keys())
        for k, v in self.s.items():
            if isinstance(v, OrderedDict):
                keys.remove(k)
                self.data[k] = []
                rest = len(msg_data) - struct.calcsize(fmt)
                if rest == 0:
                    continue
                subfmt = '!' + ''.join(v.values())
                count = rest // struct.calcsize(subfmt)
                submsg_data = msg_data[-rest:]
                msg_data = msg_data[:-rest]
                for i in range(count):
                    sdata, submsg_data = self.__decode(subfmt,
                                                       v.keys(),
                                                       submsg_data)
                    self._format(sdata)
                    self.data[k].append(sdata)
            elif v == 'rawend':
                fmt += '{}s'.format(len(msg_data) - struct.calcsize(fmt))
            else:
                fmt += v
        sdata, msg_data = self.__decode(fmt, keys, msg_data)
        self.data.update(sdata)
        if msg_data:
            self.data['additionnal'] = msg_data

        # reformat output, TODO: do it live
        self._format(self.data)
        self.data['rssi'] = self.rssi

    def __decode(self, fmt, keys, data):
        size = struct.calcsize(fmt)
        sdata = OrderedDict(zip(keys, struct.unpack(fmt, data[:size])))
        data = data[size:]
        return sdata, data

    def _format(self, data):
        for k in data.keys():
            if k in self.format:
                data[k] = self.format[k].format(data[k])

    def _filter_data(self, include=[], exclude=[]):
        if include:
            return {k: v for k, v in self.data.items() if k in include}
        elif exclude:
            return {k: v for k, v in self.data.items() if k not in exclude}

    def cleaned_data(self):
        ''' return cleaned data
        need to be override in subclass
        '''
        return self.data


@register_response
class R8000(Response):
    msg = 0x8000
    type = 'Status response'
    s = OrderedDict([('status', 'B'),
                    ('sequence', 'B'),
                    ('packet_type', 'H'),
                    ('error', 'rawend')])

    def decode(self):
        Response.decode(self)
#         self.data['packet_type'] = hexlify(self.data['packet_type'])

    def status_text(self):
        status_codes = {0: 'Success',
                        1: 'Incorrect parameters',
                        2: 'Unhandled command',
                        3: 'Command failed',
                        4: ('Busy (Node is carrying out a lengthy operation '
                            'and is currently unable to handle'
                            ' the incoming command)'),
                        5: ('Stack already started'
                            ' (no new configuration accepted)'),
                        }
        return status_codes.get(self.data.get('status'),
                                'Failed (ZigBee event codes) {}'.format(self.data.get('status')))


@register_response
class R8001(Response):
    msg = 0x8001
    type = 'Log message'
    s = OrderedDict([('level', 'B')])


@register_response
class R8002(Response):
    msg = 0x8002
    type = 'Data indication'
    s = OrderedDict([('status', 'B'),
                     ('profile_id', 'H'),
                     ('cluster_id', 'H'),
                     ('source_endpoint', 'B'),
                     ('destination_endpoint', 'B'),
                     ('source_address_mode', 'B'),
                     ('source_address', 'H'),
                     ('dst_address_mode', 'B'),
                     ('dst_address', 'H'),
                     ('payload_size', 'B'),
                     ('payload', 'rawend')
                     ])

    def decode(self):
        Response.decode(self)
        self.data['payload'] = struct.unpack('!{}B'.format(self.data['payload_size']),
                                             self.data['payload'])[0]


@register_response
class R8003(Response):
    msg = 0x8003
    type = 'Clusters list'
    s = OrderedDict([('endpoint', 'B'),
                     ('profile_id', 'H'),
                     ('clusters', OrderedDict([('cluster', 'H')]))
                     ])


@register_response
class R8004(Response):
    msg = 0x8004
    type = 'Attribute list'
    s = OrderedDict([('endpoint', 'B'),
                     ('profile_id', 'H'),
                     ('cluster', 'H'),
                     ('attributes', OrderedDict([('attribute', 'H')]))
                     ])


@register_response
class R8005(Response):
    msg = 0x8005
    type = 'Command list'
    s = OrderedDict([('endpoint', 'B'),
                     ('profile_id', 'H'),
                     ('cluster', 'H'),
                     ('commands', OrderedDict([('command', 'B')]))
                     ])


@register_response
class R8006(Response):
    msg = 0x8006
    type = 'Non “Factory new” Restart'
    s = OrderedDict([('status', 'B'),
                     ])


@register_response
class R8007(Response):
    msg = 0x8007
    type = '“Factory New” Restart'
    s = OrderedDict([('status', 'B'),
                     ])


@register_response
class R8009(Response):
    msg = 0x8009
    type = 'Network state response'
    s = OrderedDict([('addr', 'H'),
                     ('ieee', 'Q'),
                     ('pan', 'H'),
                     ('extend_pan', 'Q'),
                     ('channel', 'B'),
                     ])


@register_response
class R8010(Response):
    msg = 0x8010
    type = 'Version list'
    s = OrderedDict([('major', 'H'),
                     ('installer', 'H')])
    format = {'installer': '{:x}',
              }

    def decode(self):
        Response.decode(self)
        self.data['version'] = '{}.{}'.format(self.data['installer'][0],
                                              self.data['installer'][1:])


@register_response
class R8014(Response):
    msg = 0x8014
    type = 'Permit join status'
    s = OrderedDict([('status', '?')])


@register_response
class R8015(Response):
    msg = 0x8015
    type = 'Device list'
    s = OrderedDict([('devices', OrderedDict([('id', 'B'),
                                              ('addr', 'H'),
                                              ('ieee', 'Q'),
                                              ('power_type', 'B'),
                                              ('rssi', 'B')]))])


@register_response
class R8017(Response):
    msg = 0x8017
    type = 'TimeServer'
    s = OrderedDict([('timestamp', 'L'),
                     ])


@register_response
class R8024(Response):
    msg = 0x8024
    type = 'Network joined / formed'
    s = OrderedDict([('status', 'B'),
                     ])

    def decode(self):
        Response.decode(self)
        if self.data['status'] < 2:
            data = self.data.pop('additionnal')
            data = struct.unpack('!HQB', data)
            self.data['addr'] = data[0]
            self.data['ieee'] = data[1]
            self.data['channel'] = data[2]
            self._format(self.data)


@register_response
class R802B(Response):
    msg = 0x802B
    type = 'User Descriptor Notify'
    s = OrderedDict([('sequence', 'B'),
                     ('status', 'B'),
                     ('addr', 'H')
                     ])


@register_response
class R802C(Response):
    msg = 0x802C
    type = 'User Descriptor Response'
    s = OrderedDict([('sequence', 'B'),
                     ('status', 'B'),
                     ('addr', 'H'),
                     ('length', 'B'),
                     ('data', 'rawend')
                     ])


@register_response
class R8030(Response):
    msg = 0x8030
    type = 'Bind response'
    s = OrderedDict([('sequence', 'B'),
                     ('status', 'B'),
                     ])


@register_response
class R8031(R8030):
    msg = 0x8031
    type = 'unBind response'


@register_response
class R8040(Response):
    msg = 0x8040
    type = 'Network Address response'
    s = OrderedDict([('sequence', 'B'),
                     ('status', 'B'),
                     ('ieee', 'Q'),
                     ('addr', 'H'),
                     ('count', 'B'),
                     ('index', 'B'),
                     ('devices', OrderedDict([('addr', 'H')]))
                     ])


@register_response
class R8041(R8040):
    msg = 0x8041
    type = 'IEEE Address response'


@register_response
class R8042(Response):
    msg = 0x8042
    type = 'Node descriptor'
    s = OrderedDict([('sequence', 'B'),
                     ('status', 'B'),
                     ('addr', 'H'),
                     ('manufacturer_code', 'H'),
                     ('max_rx', 'H'),
                     ('max_tx', 'H'),
                     ('server_mask', 'H'),
                     ('descriptor_capability', 'B'),
                     ('mac_capability', 'B'),
                     ('max_buffer', 'B'),
                     ('bit_field', 'H')
                     ])
    format = {'addr': '{:04x}',
              'manufacturer_code': '{:04x}',
              'descriptor_capability': '{:08b}',
              'mac_capability': '{:08b}',
              'bit_field': '{:016b}'}
#     Bitfields:
#     Logical type (bits 0-2
#     0 – Coordinator
#     1 – Router
#     2 – End Device)
#     Complex descriptor available (bit 3)
#     User descriptor available (bit 4)
#     Reserved (bit 5-7)
#     APS flags (bit 8-10 – currently 0)
#     Frequency band(11-15 set to 3 (2.4Ghz))

#     Server mask bits:
#     0 – Primary trust center
#     1 – Back up trust center
#     2 – Primary binding cache
#     3 – Backup binding cache
#     4 – Primary discovery cache
#     5 – Backup discovery cache
#     6 – Network manager
#     7 to15 – Reserved

#     MAC capability
#     Bit 0 – Alternate PAN Coordinator
#     Bit 1 – Device Type
#     Bit 2 – Power source
#     Bit 3 – Receiver On when Idle
#     Bit 4-5 – Reserved
#     Bit 6 – Security capability
#     Bit 7 – Allocate Address

#     Descriptor capability:
#     0 – extended Active endpoint list available
#     1 – Extended simple descriptor list available
#     2 to 7 – Reserved

    def cleaned_data(self):
        return self._filter_data(exclude=['sequence', 'status'])

    @property
    def extended_active_endpoint_list(self):
        return self.data['descriptor_capability'][0] == '1'

    @property
    def extended_simple_descriptor_list(self):
        return self.data['descriptor_capability'][1] == '1'


@register_response
class R8043(Response):
    msg = 0x8043
    type = 'Simple descriptor'
    s = OrderedDict([('sequence', 'B'),
                     ('status', 'B'),
                     ('addr', 'H'),
                     ('length', 'B'),
                     ('endpoint', 'B'),
                     ('profile', 'H'),
                     ('device', 'H'),
                     ('bit_field', 'B'),
                     ('inout_clusters', 'rawend')
                     ])
    format = {'addr': '{:04x}',
              'bit_field': '{:08b}'}

    def decode(self):
        Response.decode(self)
        data = self.data['inout_clusters']
        in_cluster_count = struct.unpack('!B', data[:1])[0]
        cluster_size = struct.calcsize('!H')
        in_clusters = struct.unpack('!{}H'.format(in_cluster_count),
                                    data[1:in_cluster_count * cluster_size + 1])
        data = data[in_cluster_count * 2 + 1:]
        out_cluster_count = struct.unpack('!B', data[:1])[0]
        out_clusters = struct.unpack('!{}H'.format(out_cluster_count),
                                     data[1:out_cluster_count * cluster_size + 1])
        self.data['in_clusters'] = in_clusters
        self.data['out_clusters'] = out_clusters

    def cleaned_data(self):
        return self._filter_data(['profile', 'device',
                                  'in_clusters', 'out_clusters'])


@register_response
class R8044(Response):
    msg = 0x8044
    type = 'Power descriptor'
    s = OrderedDict([('sequence', 'B'),
                     ('status', 'B'),
                     ('bit_field', 'H'),
                     ])
    format = {'bit_field': '{:016b}'}
    #     Bit fields
    # 0 to 3: current power mode
    # 4 to 7: available power source
    # 8 to 11: current power source
    # 12 to15: current power source level


@register_response
class R8045(Response):
    msg = 0x8045
    type = 'Active endpoints'
    s = OrderedDict([('sequence', 'B'),
                     ('status', 'B'),
                     ('addr', 'H'),
                     ('endpoint_count', 'B'),
                     ('endpoints', OrderedDict([('endpoint', 'B')]))
                     ])


@register_response
class R8046(Response):
    msg = 0x8046
    type = 'Match Descriptor response'
    s = OrderedDict([('sequence', 'B'),
                     ('status', 'B'),
                     ('addr', 'H'),
                     ('match_count', 'B'),
                     ('matches', OrderedDict([('match', 'B')]))
                     ])


@register_response
class R8047(Response):
    msg = 0x8047
    type = 'Management Leave indication'
    s = OrderedDict([('sequence', 'B'),
                     ('status', 'B'),
                     ])


@register_response
class R8048(Response):
    msg = 0x8048
    type = 'Leave indication'
    s = OrderedDict([('ieee', 'Q'),
                     ('rejoin_status', 'B'),
                     ])


@register_response
class R004D(Response):
    msg = 0x004D
    type = 'Device announce'
    s = OrderedDict([('addr', 'H'),
                     ('ieee', 'Q'),
                     ('mac_capability', 'B')
                     ])
    format = {'addr': '{:04x}',
              'ieee': '{:016x}',
              'mac_capability': '{:08b}'}
#     MAC capability
#     Bit 0 – Alternate PAN Coordinator
#     Bit 1 – Device Type
#     Bit 2 – Power source
#     Bit 3 – Receiver On when Idle
#     Bit 4,5 – Reserved
#     Bit 6 – Security capability
#     Bit 7 – Allocate Address


@register_response
class R804E(Response):
    msg = 0x804E
    type = 'Management LQI response'
    s = OrderedDict([('sequence', 'B'),
                     ('status', 'B'),
                     ('entries', 'B'),
                     ('count', 'B'),
                     ('index', 'B'),
                     ('neighbour', OrderedDict([('addr', 'H'),
                                                ('extend_pan', 'Q'),
                                                ('ieee', 'Q'),
                                                ('depth', 'B'),
                                                ('rssi', 'B'),
                                                ('bit_field', 'B')]))])
# Bit map of attributes Described below: uint8_t
# {bit 0-1 Device Type
# (0-Coordinator 1-Router 2-End Device)
# bit 2-3 Permit Join status
# (1- On 0-Off)
# bit 4-5 Relationship
# (0-Parent 1-Child 2-Sibling)
# bit 6-7 Rx On When Idle status
# (1-On 0-Off)}


@register_response
class R8060(Response):
    msg = 0x8060
    type = 'Add group response'
    s = OrderedDict([('sequence', 'B'),
                     ('endpoint', 'B'),
                     ('cluster', 'H'),
                     ('addr', 'H'),
                     ('status', 'B'),
                     ('group', 'H'),
                     ])

    def decode(self):
        if len(self.msg_data) == 7:  # firmware < 3.0f
            self.s = self.s.copy()
            del self.s['addr']
        Response.decode(self)


@register_response
class R8061(Response):
    msg = 0x8061
    type = 'View group response'
    s = OrderedDict([('sequence', 'B'),
                     ('endpoint', 'B'),
                     ('cluster', 'H'),
                     ('status', 'B'),
                     ('group', 'H'),
                     ])


@register_response
class R8062(Response):
    msg = 0x8062
    type = 'Get group membership'
    s = OrderedDict([('sequence', 'B'),
                     ('endpoint', 'B'),
                     ('cluster', 'H'),
                     ('addr', 'H'),
                     ('capacity', 'B'),
                     ('group_count', 'B'),
                     ('groups', OrderedDict([('group', 'H')]))
                     ])

    def cleaned_data(self):
        self.data['groups'] = [g['group'] for g in self.data['groups']]
        return self.data


@register_response
class R8063(R8061):
    msg = 0x8063
    type = 'Remove group response'


@register_response
class R80A0(Response):
    msg = 0x80A0
    type = 'View Scene response'
    s = OrderedDict([('sequence', 'B'),
                     ('endpoint', 'B'),
                     ('cluster', 'H'),
                     ('status', 'B'),
                     ('group', 'H'),
                     ('scene', 'B'),
                     ('transition', 'H'),
                     ])


@register_response
class R80A1(Response):
    msg = 0x80A1
    type = 'Add Scene response'
    s = OrderedDict([('sequence', 'B'),
                     ('endpoint', 'B'),
                     ('cluster', 'H'),
                     ('status', 'B'),
                     ('group', 'H'),
                     ('scene', 'B'),
                     ])


@register_response
class R80A2(R80A1):
    msg = 0x80A2
    type = 'Remove Scene response'


@register_response
class R80A3(Response):
    msg = 0x80A3
    type = 'Remove all Scenes response'
    s = OrderedDict([('sequence', 'B'),
                     ('endpoint', 'B'),
                     ('cluster', 'H'),
                     ('status', 'B'),
                     ('group', 'H'),
                     ])


@register_response
class R80A4(R80A1):
    msg = 0x80A4
    type = 'Store Scene response'


@register_response
class R80A6(Response):
    msg = 0x80A6
    type = 'Scene membership response'
    s = OrderedDict([('sequence', 'B'),
                     ('endpoint', 'B'),
                     ('cluster', 'H'),
                     ('status', 'B'),
                     ('capacity', 'B'),
                     ('group', 'H'),
                     ('scene_count', 'B'),
                     ('scenes', OrderedDict([('scene', 'B')]))
                     ])


@register_response
class R8100(Response):
    msg = 0x8100
    type = 'Read Attribute response'
    s = OrderedDict([('sequence', 'B'),
                     ('addr', 'H'),
                     ('endpoint', 'B'),
                     ('cluster', 'H'),
                     ('attribute', 'H'),
                     ('status', 'B'),
                     ('data_type', 'B'),
                     ('size', 'H'),
                     ('data', 'rawend')
                     ])

    def decode(self):
        Response.decode(self)
        fmt = DATA_TYPE.get(self.data['data_type'], 's')
        fmt = '!{}{}'.format(self.data['size'] // struct.calcsize(fmt), fmt)
        data = struct.unpack(fmt, self.data['data'])[0]
        if isinstance(data, bytes):
            try:
                data = data.decode()
            except UnicodeDecodeError:
                data = hexlify(data).decode()
        self.data['data'] = data

    def cleaned_data(self):
        return self._filter_data(['attribute', 'data'])


@register_response
class R8101(Response):
    msg = 0x8101
    type = 'Default device response'
    s = OrderedDict([('sequence', 'B'),
                     ('endpoint', 'B'),
                     ('cluster', 'H'),
                     ('cmd', 'B'),
                     ('status', 'B'),
                     ])


@register_response
class R8102(R8100):
    msg = 0x8102
    type = 'Individual Attribute Report'


@register_response
class R8110(R8100):
    msg = 0x8110
    type = 'Write Attribute response'


@register_response
class R8120(Response):
    msg = 0x8120
    type = 'Configure Reporting response'
    s = OrderedDict([('sequence', 'B'),
                     ('addr', 'H'),
                     ('endpoint', 'B'),
                     ('cluster', 'H'),
                     ('status', 'B'),
                     ])


@register_response
class R8140(Response):
    msg = 0x8140
    type = 'Attribute Discovery response'
    s = OrderedDict([('complete', 'B'),
                     ('data_type', 'B'),
                     ('attribute', 'H'),
                     ('addr', 'H'),
                     ('endpoint', 'B'),
                     ('cluster', 'H'),
                     ])

    def decode(self):
        if len(self.msg_data) == 4:  # firmware < 3.0f
            self.s = self.s.copy()
            del self.s['addr']
            del self.s['endpoint']
            del self.s['cluster']
        Response.decode(self)

    def cleaned_data(self):
        return self._filter_data(['attribute'])


@register_response
class R8401(Response):
    msg = 0x8401
    type = 'IAS Zone Status Change'
    s = OrderedDict([('sequence', 'B'),
                     ('endpoint', 'B'),
                     ('cluster', 'H'),
                     ('address_mode', 'B'),
                     ('addr', 'H'),  # ou Q suivant mode
                     ('zone_status', 'H'),
                     ('status', 'B'),
                     ('zone_id', 'B'),
                     ('delay', 'H'),
                     ])

    format = {'addr': '{:04x}',
              'zone_status': '{:016b}'}

    def cleaned_data(self):
        return self._filter_data(['addr', 'zone_status', 'zone_id'])


@register_response
class R8501(Response):
    msg = 0x8501
    type = 'OTA image block request'
    s = OrderedDict([('sequence', 'B'),
                     ('endpoint', 'B'),
                     ('cluster', 'H'),
                     ('address_mode', 'B'),
                     ('addr', 'H'),
                     ('node_address', 'Q'),
                     ('file_offset', 'L'),
                     ('image_version', 'L'),
                     ('image_type', 'H'),
                     ('manufacturer_code', 'H'),
                     ('block_request_delay', 'H'),
                     ('max_data_size', 'B'),
                     ('field_control', 'B')
                     ])


@register_response
class R8503(Response):
    msg = 0x8503
    type = 'OTA upgrade end request'
    s = OrderedDict([('sequence', 'B'),
                     ('endpoint', 'B'),
                     ('cluster', 'H'),
                     ('address_mode', 'B'),
                     ('addr', 'H'),
                     ('file_version', 'L'),
                     ('image_type', 'H'),
                     ('manufacture_code', 'H'),
                     ('status', 'B')
                     ])


@register_response
class R8701(Response):
    msg = 0x8701
    type = 'Route Discovery Confirmation'
    s = OrderedDict([('status', 'B'),
                     ('network_status', 'B'),
                     ])


@register_response
class R8702(Response):
    msg = 0x8702
    type = 'APS Data Confirm Fail'
    s = OrderedDict([('status', 'B'),
                     ('source_endpoint', 'B'),
                     ('dst_endpoint', 'B'),
                     ('dst_address_mode', 'B'),
                     ('dst_address', 'Q'),
                     ('sequence', 'B')
                     ])
