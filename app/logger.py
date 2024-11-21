class LoggingExtension:
    def __init__(self, crawler):

        self.settings = crawler.settings
        self.bot_name = self.settings.get('BOT_NAME', "blocket")
        self.log_level = self.settings.get('CUSTOM_LOG_LEVEL', 'INFO').upper()
        self.logger = self.create_logger()

    @classmethod
    def from_crawler(cls, crawler, *args, **kwargs):
        if not crawler.settings.getbool('LOG_ENABLED', True):
            raise NotConfigured
        return cls(crawler)

    def create_logger(self):
        logger = logging.getLogger(self.bot_name)
        logger.propagate = False
        if logger.handlers:
            logger.handlers = []
        handler = logging.StreamHandler()
        handler.setLevel(self.log_level)
        formatter = logging.Formatter(
            fmt=self.settings.get("LOG_FORMAT"), datefmt=self.settings.get("LOG_DATEFORMAT")
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        return logger