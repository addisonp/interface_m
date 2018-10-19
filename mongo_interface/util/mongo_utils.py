import tenacity

from mongo_interface.util.mongo_connection import ConnectionHelper

class DbConnection():
    def __init__(self, config):
        self.host = config['host']
        self.port = config.get('port', 27017)
        self.database = config['database']
        self.username = config.get('username', None)
        self.password = config.get('password', None)
        self.auth_db = config.get('authentication_database', None)
        self.replica_set = config.get('replica_set', None)
        self._conn_dict = {
            'host': self.host,
            'port': self.port,
            'username': self.username,
            'password': self.password,
            'authentication_database': self.auth_db,
            'replica_set': self.replica_set}

    @tenacity.retry(wait=tenacity.wait_random_exponential(multiplier=1, max=30), stop=tenacity.stop_after_attempt(5))
    def conn(self):
        conn = ConnectionHelper(**self._conn_dict)
        client = conn.get_mongo_client()
        return client[self.database]