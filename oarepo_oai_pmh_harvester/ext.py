from collections import defaultdict
from typing import List

from pkg_resources import iter_entry_points

from oarepo_oai_pmh_harvester.transformer import OAITransformer
from oarepo_oai_pmh_harvester.utils import infinite_dd
from . import config
from .provider import OAIProvider
from .synchronization import OAISynchronizer
from .views import oai_client_blueprint


class Singleton(type):
    _instances = {}

    # Rewritten type() method, where built_in type method has this signature "type(name, bases,
    # dict)"
    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]


class OArepoOAIClientState(metaclass=Singleton):
    def __init__(self, app, _rules: defaultdict = None, _parsers: defaultdict = None,
                 _providers: dict = None, _synchronizers=None, transformer_class=OAITransformer,
                 _endpoints=None):
        self.app = app
        self._rules = _rules
        self._parsers = _parsers
        self._providers = _providers
        self._synchronizers = _synchronizers
        self.transformer_class = transformer_class
        self._endpoints = _endpoints

    @property
    def providers(self):
        if self._providers is None:
            self.create_providers()
        return self._providers

    @property
    def rules(self):
        if self._rules is None:
            self._load_rules()
        return self._rules

    @property
    def parsers(self):
        if self._parsers is None:
            self._load_parsers()
        return self._parsers

    @property
    def endpoints(self):
        if not self._endpoints:
            self.load_endpoints()
        return self._endpoints

    def load_endpoints(self):
        self._endpoints = self.app.config.get("RECORDS_REST_ENDPOINTS", {})

    def _load_rules(self):
        for ep in iter_entry_points('oarepo_oai_pmh_harvester.rules'):
            ep.load()

    def _load_parsers(self):
        for ep in iter_entry_points('oarepo_oai_pmh_harvester.parsers'):
            ep.load()

    def create_providers(self):
        providers = self.app.config.get("OAREPO_OAI_PROVIDERS")
        if providers:
            for k, v in providers.items():
                provider = OAIProvider(
                    code=k,
                    description=v.get("description"),
                ) # vytvořím providera
                provider.synchronizers = {}
                for sync_config in v.get("synchronizers", []):
                    synchronizer = self.create_synchronizer(provider.code, sync_config)
                    provider.synchronizers[sync_config["name"]] = synchronizer
                if not self._providers:
                    self._providers = {}
                self._providers.setdefault(k, provider)



    def add_rule(self, func, provider, parser_name, path, phase):
        if not self._rules:
            self._rules = infinite_dd()
        self._rules[provider][parser_name][path][phase] = func

    def add_parser(self, func, name):
        if not self._parsers:
            self._parsers = infinite_dd()
        self._parsers[name] = func

    def create_synchronizer(self, provider_code, config):
        return OAISynchronizer(
            provider_code=provider_code,
            metadata_prefix=config["metadata_prefix"],
            set_=config["set"],
            constant_fields=config.get("constant_field", {}),
            oai_endpoint=config["oai_endpoint"],
            parser=self.parsers[config["metadata_prefix"]],
            transformer=self.transformer_class(
                rules=self.rules[provider_code][config["metadata_prefix"]],
                unhandled_paths=set(config.get("unhandled_paths", []))),
            endpoints=self.endpoints,
            default_endpoint=config.get("default_endpoint", "recid"),
            endpoint_mapping=config.get("endpoint_mapping", {}),
            from_=config.get("from")
        )

    def run(self, providers_codes: List[str] = None, synchronizers_codes: List[str] = None,
            break_on_error: bool = True, start_oai: str = None,
            start_id: int = 0):
        if not providers_codes:
            providers_codes = [_ for _ in self.providers.keys()]
        if len(providers_codes) > 1:
            for code in providers_codes:
                self._run_provider(code, break_on_error=break_on_error)
        elif len(providers_codes) == 1:
            if not synchronizers_codes:
                synchronizers_codes = [_ for _ in
                                       self.providers[providers_codes[0]].synchronizers.keys()]
            if len(synchronizers_codes) > 1:
                for code in synchronizers_codes:
                    self._run_synchronizer(providers_codes[0], code, break_on_error=break_on_error)
            elif len(synchronizers_codes) == 1:
                if start_oai and start_id != 0:
                    raise Exception("You can not enter start_oai and START_ID simultaneously.")
                elif start_oai:
                    self._run_synchronizer(providers_codes[0], synchronizers_codes[0],
                                           break_on_error=break_on_error, start_oai=start_oai)
                elif start_id != 0:
                    self._run_synchronizer(providers_codes[0], synchronizers_codes[0],
                                           break_on_error=break_on_error, start_id=start_id)
                else:
                    self._run_synchronizer(providers_codes[0], synchronizers_codes[0],
                                           break_on_error=break_on_error)
            else:
                raise Exception("Something unexpected happened.")
        else:
            raise Exception("Something unexpected happened.")

    def _run_provider(self, provider: str, break_on_error: bool = True):
        provider_ = self.providers[provider]
        for synchronizer in provider_.synchronizers.keys():
            self._run_synchronizer(provider, synchronizer, break_on_error=break_on_error)

    def _run_synchronizer(self, provider: str, synchronizer: str, start_oai: str = None,
                          start_id: int = 0, break_on_error: bool = True):
        provider = self.providers[provider]
        synchronizer = provider.synchronizers[synchronizer]
        synchronizer.run(start_oai=start_oai, start_id=start_id, break_on_error=break_on_error)


class OArepoOAIClient:

    def __init__(self, app=None):
        """Extension initialization."""
        if app:
            self.init_app(app)

    def init_app(self, app):
        self.init_config(app)

        # register blueprint
        prefix = app.config.get('OAREPO_OAI_CLIENT_URL_PREFIX', "/oai-client")
        if prefix.startswith('/api'):
            prefix = prefix[4:]
        app.register_blueprint(oai_client_blueprint, url_prefix=prefix)

        app.extensions['oarepo-oai-client'] = OArepoOAIClientState(app)

    def init_config(self, app):
        for k in dir(config):
            if k.startswith('OAREPO_OAI_'):
                app.config.setdefault(k, getattr(config, k))
