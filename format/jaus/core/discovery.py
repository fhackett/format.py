import format as _format
import format.jaus as _jaus

class ServiceRecord(_format.Specification):
    @classmethod
    def _data(cls, data):
        yield from super()._data(data)
        yield from _jaus.counted_string('uri', bytes=1)
        yield _format.Integer('major_version', bytes=1)
        yield _format.Integer('minor_version', bytes=1)

class RegisterServices(_jaus.Message):
    _variant_key = _jaus.Message.Code.RegisterServices
    @classmethod
    def _data(cls, data):
        yield from super()._data(data)
        yield from _jaus.counted_list('services', ServiceRecord, bytes=1)

class QueryIdentification(_jaus.Message):
    _variant_key = _jaus.Message.Code.QueryIdentification
    class QueryType(_enum.Enum):
        SYSTEM = 1
        SUBSYSTEM = 2
        NODE = 3
        COMPONENT = 4
    @classmethod
    def _data(cls, data):
        yield from super()._data(data)
        yield _format.Enum('type', enum=QueryType, bytes=1)

class QueryConfiguration(_jaus.Message):
    _variant_key = _jaus.Message.Code.QueryConfiguration
    class QueryType(_enum.Enum):
        SUBSYSTEM = 2
        NODE = 3
    @classmethod
    def _data(cls, data):
        yield from super()._data(data)
        yield _format.Enum('type', enum=QueryType, bytes=1)

class QuerySubsystemList(_jaus.Message):
    _variant_key = _jaus.Message.Code.QuerySubsystemList

class ComponentRequest(_format.Specification):
    @classmethod
    def _data(cls, data):
        yield from super()._data(data)
        yield _format.Integer('id', bytes=1)

class NodeRequest(_format.Specification):
    @classmethod
    def _data(cls, data):
        yield from super()._data(data)
        yield _format.Integer('id', bytes=1)
        yield from _jaus.counted_list('components', ComponentRequest, bytes=1)

class QueryServices(_jaus.Message):
    _variant_key = _jaus.Message.Code.QueryServices
    @classmethod
    def _data(cls, data):
        yield from super()._data(data)
        yield from _jaus.counted_list('nodes', NodeRequest, bytes=1)

class ComponentListRequest(_format.Specification):
    @classmethod
    def _data(cls, data):
        yield from super()._data(data)
        yield from _jaus.with_presence_vector(
            required=[
                _format.Integer('id', bytes=1),
            ],
            optional=[
                _format.Composite('search_filter', _jaus.counted_string, bytes=1),
            ])

class NodeListRequest(_format.Specification):
    @classmethod
    def _data(cls, data):
        yield from super()._data(data)
        yield _format.Integer('id', bytes=1)
        yield from _jaus.counted_list('components', ComponentListRequest, bytes=1)

class SubsystemListRequest(_format.Specification):
    @classmethod
    def _data(cls, data):
        yield from super()._data(data)
        yield _format.Integer('id', bytes=2, le=True)
        yield from _jaus.counted_list('nodes', NodeListRequest, bytes=1)

class QueryServiceList(_jaus.Message):
    _variant_key = _jaus.Message.Code.QueryServiceList
    @classmethod
    def _data(cls, data):
        yield from super()._data(data)
        yield from _jaus.counted_list('subsystems', SubsystemListRequest, bytes=2, le=True)

class IdentificationType(_enum.Enum):
    VEHICLE = 10001
    OCU = 20001
    OTHER_SUBSYSTEM = 30001
    NODE = 40001
    PAYLOAD = 50001
    COMPONENT = 60001

class ReportIdentification(_jaus.Message):
    _variant_key = _jaus.Message.Code.ReportIdentification
    @classmethod
    def _data(cls, data):
        yield from super()._data(data)
        yield _format.Enum('query_type', enum=QueryIdentification.QueryType, bytes=1)
        yield _format.Enum('type', enum=IdentificationType, bytes=2, le=True)
        yield from _jaus.counted_string('identification', bytes=2, endianness='le')

class ComponentConfigurationReport(_format.Specification):
    @classmethod
    def _data(cls, data):
        yield from super()._data(data)
        yield _format.Integer('id', bytes=1)
        yield _format.Integer('instance_id', bytes=1, default=0)

class NodeConfigurationReport(_format.Specification):
    @classmethod
    def _data(cls, data):
        yield from super()._data(data)
        yield _format.Integer('id', bytes=1)
        yield from _jaus.counted_list('components', ComponentConfigurationReport, bytes=1)

class ReportConfiguration(_jaus.Message):
    _variant_key = _jaus.Message.Code.ReportConfiguration
    @classmethod
    def _data(cls, data):
        yield from super()._data(data)
        yield from _jaus.counted_list('nodes', NodeConfigurationReport, bytes=1)

class ReportSubsystemList(_jaus.Message):
    _variant_key = _jaus.Message.Code.ReportSubsystemList
    @classmethod
    def _data(cls, data):
        yield from super()._data(data)
        yield from _jaus.counted_list('subsystems', Id, bytes=1)

class ComponentServiceListReport(_format.Specification):
    @classmethod
    def _data(cls, data):
        yield from super()._data(data)
        yield _format.Integer('id', bytes=1)
        yield _format.Int('instance_id', bytes=1, default=0)
        yield from _jaus.counted_list('services', ServiceRecord, bytes=1)

class NodeServiceListReport(_format.Specification):
    @classmethod
    def _data(cls, data):
        yield from super()._data(data)
        yield _format.Integer('id', bytes=1)
        yield from _jaus.counted_list('components', ComponentServiceListReport, bytes=1)

class ReportServices(_jaus.Message):
    _variant_key = _jaus.Message.Code.ReportServices
    @classmethod
    def _data(cls, data):
        yield from super()._data(data)
        yield from _jaus.counted_list('nodes', NodeServiceListReport, bytes=1)

class SubsystemServiceListReport(_format.Specification):
    @classmethod
    def _data(cls, data):
        yield from super()._data(data)
        yield _format.Integer('id', bytes=2, le=True)
        yield from _jaus.counted_list('nodes', NodeServiceListReport, bytes=1)

class ReportServiceList(_jaus.Message):
    _variant_key = _jaus.Message.Code.ReportServiceList
    @classmethod
    def _data(cls, data):
        yield from super()._data(data)
        yield from _jaus.counted_list('subsystems', SubsystemServiceListReport, bytes=2, le=True)


class Service(_jaus.Service):
    name = 'discovery'
    uri = 'urn:jaus:jss:core:Discovery'
    version = (1, 0)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.mapping = {}

    def bootstrap(self):
        super().bootstrap()
        records = self._get_records_for(self.component.id)
        records += [
            ServiceRecord(
                uri=service.uri,
                major_version=service.version[0],
                minor_version=service.version[1])
            for service in self.component.services.values()]

    def _get_records_for(self, component_id):
        return self.mapping.setdefault(
            component_id.subsystem, {}).setdefault(
                component_id.node, {}).setdefault(
                    component_id.component, [])

    @_jaus.message_handler(
        _jaus.Message.Code.RegisterServices,
        supports_events=False)
    @_asyncio.coroutine
    def on_register_services(self, source_id, message, **kwargs):
        records = self._get_records_for(source_id)
        records += message.services
        _logging.debug('SERVICES: {}'.format(self.mapping))

    @_jaus.message_handler(_jaus.Message.Code.QueryIdentification)
    @_asyncio.coroutine
    def on_query_identification(self, message, **kwargs):
        if message.type is QueryIdentification.QueryType.SUBSYSTEM:
            return ReportIdentification(
                query_type=message.type,
                type=IdentificationType.VEHICLE,
                identification=self.component.subsystem_name)
        elif message.type is QueryIdentification.QueryType.NODE:
            return ReportIdentification(
                query_type=message.type,
                type=IdentificationType.NODE,
                identification=self.component.node_name)
        elif message.type is QueryIdentification.QueryType.COMPONENT:
            return ReportIdentification(
                query_type=message.type,
                type=IdentificationType.COMPONENT,
                identification=self.component.name)

    @_jaus.message_handler(_jaus.Message.Code.QueryConfiguration)
    @_asyncio.coroutine
    def on_query_configuration(self, message, **kwargs):
        if message.query_type is QueryConfiguration.QueryType.SUBSYSTEM:
            selector = lambda id: id.subsystem == self.component.id.subsystem
        elif message.query_type is QueryConfiguration.QueryType.NODE:
            selector = lambda id: id.subsystems == self.component.id.subsystem and id.node == self.component.id.node
        return ReportConfiguration(
            nodes=[
                NodeConfigurationReport(
                    id=node.id,
                    components=[
                        ComponentConfigurationReport(
                            id=component_id)
                        for component_id in components.keys()])
                for node_id, components in nodes
                for subsystem_id, nodes in self.mapping
                if selector(_jaus.Id(subsystem=subsystem_id, node=node_id))])

    @_jaus.message_handler(_jaus.Message.Code.QuerySubsystemList)
    @_asyncio.coroutine
    def on_query_subsystem_list(self, **kwargs):
        subsystems = [
            _jaus.Id(subsystem=subsystem, node=node, component=component)
            for component in components.keys()
            for node, components in nodes
            for subsystem, nodes in self.mapping]
        return ReportSubsystemList(
            subsystems=subsystems)

    @_jaus.message_handler(_jaus.Message.Code.QueryServices)
    @_asyncio.coroutine
    def on_query_services(self, message, **kwargs):
        # bow before my nested list comprehensions of glory
        return ReportServices(
            nodes=[
                NodeServiceListReport(
                    id=node.id,
                    components=[
                        ComponentServiceListReport(
                            id=component.id,
                            services=self._get_records_for(_jaus.Id(
                                subsystem=self.component.id.subsystem,
                                node=node.id,
                                component=component.id)))
                        for component in node.components])
                for node in message.nodes])

    @_jaus.message_handler(_jaus.Message.Code.QueryServiceList)
    @_asyncio.coroutine
    def on_query_service_list(self, message, **kwargs):
        # bow more so to the extra level of nesting :P
        return ReportServiceList(
            subsystems=[
                SubsystemServiceListReport(
                    id=subsystem.id,
                    nodes=[
                        NodeServiceListReport(
                            id=node.id,
                            components=[
                                ComponentServiceListReport(
                                    id=component.id,
                                    services=self._get_records_for(_jaus.Id(
                                        subsystem=subsystem.id,
                                        node=node.id,
                                        component=component.id)))
                                for component in node.components])
                        for node in subsystem.nodes])
                for subsystem in message.subsystems])
