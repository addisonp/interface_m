try:
    # python 3.x
    from urllib.parse import quote_plus
except ImportError:
    # python 2.x
    from urllib import quote_plus

from pymongo.errors import ConnectionFailure
from pymongo import MongoClient


class MongoNotAvailable(Exception):
    """Base mongo exception class."""
    pass


class ConnectionHelper(object):
    """Database connection helper."""

    def __init__(self, host, port, username=None, password=None,
                 authentication_database=None, replica_set=None, **kwargs):
        """Start up Mongo connection.

        :Params:
          :host (str): Single or multiple hosts separated by comma i.e.
              single-host: 127.0.0.1
              multiple-hosts: 127.0.0.1,127.0.0.2
          :port (str): Single or multiple ports separated by comma, these must
              be in the same order as the hosts.
              single-port: 27017
              multi-port: 27017,27018
          :username (str): Username to use against mongo database, if no
             username is required  then do not include and leave default value.
          :password (str): Password to use against mongo database, if no
             password is requried then do not include and leave default value.
          :authentication_database (str): When username and password is present
             specify the databse to authenticate against, usually 'admin' is
             default. However the ConnectionHelper defaults to None
          :replica_set (str): Name of the replica set to use. You can find this
            by interrogating the db rs.status()
        """
        self.host = host.split(',') if ',' in host else host
        try:
            self.port = port.split(',') if ',' in port else port
        except TypeError as te:
            self.port = port

        self.username = username
        self.password = password
        self.auth_db = authentication_database
        self.replica_set = replica_set

    def _get_conn_url(self):
        """Return connection string to be used for connecting client."""
        if self.username and self.password and \
                self.replica_set and type(self.host) == list:
            # handle replica set connection
            hosts_ports = [u'{0}:{1}'.format(self.host[x], self.port[x]) for x in range(len(self.host))]
            logger.debug(hosts_ports)
            return u"mongodb://{0}:{1}@{2}/{3}?replicaSet={4}".format(
                quote_plus(self.username),
                quote_plus(self.password),
                u','.join(hosts_ports),
                quote_plus(self.auth_db),
                quote_plus(self.replica_set))
        if self.username and self.password:
            return u"mongodb://{0}:{1}@{2}:{3}/{4}".format(
                quote_plus(self.username),
                quote_plus(self.password),
                self.host,
                self.port,
                quote_plus(self.auth_db))
        return u"mongodb://{0}:{1}".format(
            self.host,
            self.port)

    def get_mongo_client(self):
        """Get mongo client to use for databsae queries."""
        conn_url = self._get_conn_url()
        client = MongoClient(conn_url)
        try:
            if self.replica_set:
                return client
            client.admin.command('ismaster')
        except ConnectionFailure as cf:
            raise MongoNotAvailable('Connection Failed to {0}:{1}'.format(
                self.host, cf))
        return client
