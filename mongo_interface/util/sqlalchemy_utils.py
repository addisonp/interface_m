from contextlib import contextmanager

import sqlalchemy
import sqlalchemy.engine
import sqlalchemy.orm
from sqlalchemy.pool import NullPool

class DbConnection():
    def __init__(self, config):
        dbargs = {
            'drivername': config['driver'],
            'username': config.get('username', None),
            'host': config['host'],
            'port': config.get('port', None),
            'password': config.get('password', None),
            'database': config['database'],
        }
        dburi = sqlalchemy.engine.url.URL(**dbargs)

        self.engine = sqlalchemy.create_engine(dburi, echo=config['echo'], pool_recycle=600, echo_pool=False, poolclass=NullPool)

        # Standard session
        self.session_factory = sqlalchemy.orm.sessionmaker(bind=self.engine)

    @contextmanager
    def session_local(self):
        session = self.session_factory()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            raise
        finally:
            session.close()

    @contextmanager
    def session_scoped(self):
        session = sqlalchemy.orm.scoped_session(self.session_factory)
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            raise
        finally:
            session.close()
