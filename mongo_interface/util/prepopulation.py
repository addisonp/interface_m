import bson
import datetime

from sqlalchemy import and_
from sqlalchemy.orm import sessionmaker
from multiprocessing import Process

from mongo_interface.util.mongo_utils import DbConnection
from mongo_interface import GenConfig
from mongo_interface.util.json_manipulation import update_device
from mongo_interface.util.sqlalchemy_utils import DbConnection as PGDbConnection
from mongo_interface.models.models import TrustedDevice, Certificate


def device_worker(query, config):
    print(f'starting worker for this many items: {len(query)}')
    config = GenConfig(config=config)  # for my local instance
    db = DbConnection(config['flm-db'])
    db_conn = db.conn()
    lookup_db_conn = db_conn['device_lookup']
    start_time = datetime.datetime.now()
    for counter, (td, cert) in enumerate(query):
        item = {}
        item['Manufacturer'] = cert.device_make
        item['ModelNumber'] = cert.device_model
        item['DeviceSerial'] = cert.device_serial
        item['DeviceTypeID'] = cert.device_type
        default_id = str(bson.ObjectId())
        matching_trusted_device_id = cert.trusted_device_id
        update_device(item, default_id, lookup_db_conn, matching_trusted_device_id)
    end_time = datetime.datetime.now()
    print(f'prcess started: {start_time}\nended: {end_time}\nelapsed: {end_time-start_time}')


def get_cert_data(session=None, limit=None, offset=None):
    # Create session to mantain the data
    query = session.query(TrustedDevice).join(TrustedDevice.active_certificate).add_entity(Certificate).filter(and_(
        TrustedDevice.is_active == True,
        Certificate.is_blacklisted == False
    ))

    if limit:
        query = query.limit(limit)
    if offset:
        query = query.offset(offset)

    query = query.all()
    return query


def start_multiprocessing(certs_in_group=None, number_of_workers=None, limit=None, offset=None, config=None):
    config = GenConfig(config=config)

    cert_db = PGDbConnection(config['certdb'])
    Session = sessionmaker(bind=cert_db.engine)
    session = Session()

    all_certs = get_cert_data(session=session, limit=limit, offset=offset)

    number_of_certs_in_a_group = certs_in_group or 10000
    if number_of_workers:
        number_of_certs_in_a_group = all_certs.count() / number_of_workers

    processes = []

    for i in range(0, len(all_certs), number_of_certs_in_a_group):
        x = all_certs[i:i + number_of_certs_in_a_group]
        print(f'got my certs! starting at {i} ending at {len(x) + i}')
        results = Process(target=device_worker, args=(x, config,))
        # run processes
        results.start()
        processes.append(results)

    # exit the completed processes
    for p in processes:
        p.join()

    session.close()


if __name__ == "__main__":
    local_config = {
        'flm-db': {'host': '172.29.0.5'},
        'cert-db': {'host': '192.168.1.100'}}
    start_multiprocessing(number_of_workers=12, config=local_config)
