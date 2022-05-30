from oaipmh_config import config as config


class OaipmhConfigExt(object):
    """ extension."""

    def __init__(self, app=None):
        """Extension initialization."""
        self.resource = None
        self.service = None
        if app:
            self.init_app(app)

    def init_app(self, app):
        """Flask application initialization."""
        self.init_config(app)
        self.init_resource(app)
        app.extensions["oaipmh_config"] = self

    def init_resource(self, app):
        """Initialize vocabulary resources."""
        self.service = app.config["OAIPMH_CONFIG_SERVICE_CLASS"](
            config=app.config["OAIPMH_CONFIG_SERVICE_CONFIG"](),
        )
        self.resource = app.config["OAIPMH_CONFIG_RESOURCE_CLASS"](
            service=self.service,
            config=app.config["OAIPMH_CONFIG_RESOURCE_CONFIG"](),
        )

    def init_config(self, app):
        """Initialize configuration."""
        app.config.setdefault("OAIPMH_CONFIG_RESOURCE_CONFIG", config.OAIPMH_CONFIG_RESOURCE_CONFIG)
        app.config.setdefault("OAIPMH_CONFIG_RESOURCE_CLASS", config.OAIPMH_CONFIG_RESOURCE_CLASS)
        app.config.setdefault("OAIPMH_CONFIG_SERVICE_CONFIG", config.OAIPMH_CONFIG_SERVICE_CONFIG)
        app.config.setdefault("OAIPMH_CONFIG_SERVICE_CLASS", config.OAIPMH_CONFIG_SERVICE_CLASS)