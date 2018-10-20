import arrow
import datetime
import json
import jsonschema
import logging
import pymongo

from typing import Dict, List, TYPE_CHECKING

from mongo_interface import GenConfig
from mongo_interface.util.mongo_utils import DbConnection
from mongo_interface.util.db import get_next_sequence
from mongo_interface.util.json_date_manipulation import string_to_date, date_to_string

from pymongo import ASCENDING, DESCENDING
from pymongo.errors import ConnectionFailure

if TYPE_CHECKING:
    from urllib.parse import quote_plus
else:
    try:
        # python 3.X
        from urllib.parse import quote_plus
    except ImportError:
        # python 2.X
        from urllib import quote_plus

logging.basicConfig(
    filename="mongo_api.log",
    level=logging.DEBUG,
    format="%(asctime)s:%(levelname)s:%(message)s"
)

logger = logging.getLogger(__name__)


class MongoNotAvailable(Exception):
    """Base Connection Error to Mongo DB."""
    pass


class FLMException(Exception):
    def __init__(self, msg: str = None, input: str = None, original_exception: Exception = None) -> None:
        msg = msg + str(original_exception)
        super(FLMException, self).__init__(msg)
        self.original_exception = original_exception
        self.input = input


class FLM:
    """
    For all FLM related queries into the flm collections
    """

    def __init__(self, config=None, init_value=0):
        self.config = GenConfig(config=config)
        self.db = DbConnection(self.config['flm-db'])

        self._initialize_sequence(init_value)
        self._initialize_collections()

    def _initialize_collections(self):
        db = self.db.conn()
        if 'smpte_flm' not in db.collection_names():
            db.smpte_flm.create_index([('flm.FacilityID', ASCENDING)], unique=True)
            db.smpte_flm.create_index([('flm.FacilityInfo.FacilityName', ASCENDING)])
            db.smpte_flm.create_index([('last_modified', DESCENDING)])
            db.smpte_flm.create_index([('flm.Source', DESCENDING)])
            db.smpte_flm.create_index([('flm.FacilityInfo.Addresses.Physical.City', ASCENDING)])
            db.smpte_flm.create_index([('flm.FacilityInfo.Addresses.Physical.Country', ASCENDING)])

    def _initialize_sequence(self, value=0):
        if value:
            self.set_sequence(value=value)

    def set_sequence(self, value: int = 0):
        db = self.db.conn()

        if value < 0:
            raise FLMException(
                'Unable to set the sequence to {}, expecting a positive integer value'.format(value))
        try:
            db.sequences.update_one({"_id": "flm"}, {"$set": {"seq": value}}, upsert=True)
        except Exception as e:
            raise FLMException(msg='Unable to upsert the sequence collection', input=None, original_exception=e)

    def get_sequence(self):
        db = self.db.conn()
        data = db.sequences.find({}, {"seq": 1, "_id": 0})
        for x in data:
            return x['seq']

    def auto_set_sequence(self):
        db = self.db.conn()
        max_smpte_id = db.smpte_flm.find_one(sort=[("flm.FacilityID", -1)],
                                             projection={"flm.FacilityID": 1, "_id": 0})
        if max_smpte_id and isinstance(max_smpte_id["flm"]["FacilityID"], int):
            self.set_sequence(max_smpte_id["flm"]["FacilityID"])
        else:
            self.set_sequence()

    def _validate_smpte_id(self, smpte_id) -> int:
        """ Validates that the smpte id passed is either an integer, a string representation of either an
        integer or accepted format [SMPTE-## | SMPTE-##-CC] also allow the base_urn to be included

        :param smpte_id: raw smpte id
        :return: smpte_id that is an integer
        :rtype smpte_id: int
        """

        smpte_urn = "SMPTE-"
        base_urn = 'smpte.org:SMPTE-'
        # strip out the leading SMPTE- and any trailing values after the facility id (ie country code)
        if smpte_id and isinstance(smpte_id, str) and smpte_id[:len(smpte_urn)] == smpte_urn:
            smpte_id = int(smpte_id[len(smpte_urn):].split('-')[0])
        if smpte_id and isinstance(smpte_id, str) and smpte_id[:len(base_urn)] == base_urn:
            smpte_id = int(smpte_id[len(base_urn):].split('-')[0])
        elif smpte_id and isinstance(smpte_id, str) and smpte_id.isdigit():
            smpte_id = int(smpte_id)
        elif smpte_id and isinstance(smpte_id, str) and not smpte_id.isdigit():
            raise FLMException(
                "Invalid override smpte facility id: {}, expected facility_id to start with SMPTE".format(smpte_id)
            )
        return smpte_id

    def populate_smpte_flm(self, flm_data: Dict, smpte_id: str = None) -> str:
        """ To insert/update the smpte FLM data
        expected a FLM with either an smpte ID or None in the FacilityID

        :param dict flm_data:
        :param str smpte_id:
        :return: primary key (_id) of the flm collection
        :rtype str
        """

        try_insert_update = False
        if smpte_id and flm_data:
            clean_smpte_id = self._validate_smpte_id(smpte_id)
            if clean_smpte_id and not isinstance(clean_smpte_id, int):
                raise FLMException(
                    'Invalid smpte facility id: {}, expected numeric values only {}'.format(clean_smpte_id,
                                                                                            type(clean_smpte_id)))

            try_insert_update = True
            flm_data['FacilityID'] = clean_smpte_id

        if not flm_data:
            raise FLMException('Unable to processed smpte FLM, no data provided')
        if type(flm_data) is not dict:
            raise FLMException('Invalid input type {}, expected json dict'.format(type(flm_data)))

        if flm_data["FacilityID"]:
            self._validate_smpte_schema(flm_data=flm_data)
            if try_insert_update:
                try:
                    object_id = self._update_smpte_flm(flm_data=flm_data)
                except:
                    object_id = self._insert_smpte_flm(flm_data=flm_data)
            else:
                object_id = self._update_smpte_flm(flm_data=flm_data)
        else:
            object_id = self._insert_smpte_flm(flm_data=flm_data)

        return object_id

    def _validate_smpte_schema(self, flm_data: Dict) -> bool:
        """ Validate the given flm against the current smpte FLM schema

        :param dict flm_data:
        :return: whether the flm schema validated or not
        :rtype bool
        """
        try:
            flm_schema_path = self.config['flm_schema_path']
            with open(flm_schema_path, "r") as fin:
                schema = json.load(fin)

            jsonschema.validate(flm_data, schema)
            return True
        except jsonschema.exceptions.ValidationError as e:
            raise FLMException('Schema validation failure', json.dumps(flm_data), e)

    def _insert_smpte_flm(self, flm_data: Dict) -> str:
        """ This is used only for inserting into the smpte flm as a new flm, comes with no FacilityID

        :param dict flm_data:
        :return: primary key (_id) of the flm collection
        :rtype str
        """

        now = datetime.datetime.now(datetime.timezone.utc)
        db = self.db.conn()

        if not flm_data['FacilityID']:
            flm_data['FacilityID'] = int(get_next_sequence(db.sequences, "flm"))

        self.convert_flm_to_date(flm_data)
        doc_object = {'flm': flm_data, 'last_modified': now, 'created_date': now}
        try:
            db = db['smpte_flm']
            object_id = db.insert_one(doc_object)
            return object_id.inserted_id
        except pymongo.errors.DuplicateKeyError as e:
            # search and start inserting at the latest value
            self.auto_set_sequence()
            db = self.db.conn()
            flm_data['FacilityID'] = int(get_next_sequence(db.sequences, "flm"))
            doc_object = {'flm': flm_data, 'last_modified': now, 'created_date': now}
            db = db['smpte_flm']
            object_id = db.insert_one(doc_object)
            return object_id.inserted_id
        except Exception as e:
            raise FLMException(msg='Unable to insert FLM', input=flm_data["FacilityID"], original_exception=e)

    def _update_smpte_flm(self, flm_data: Dict) -> str:
        """ Only for updating the smpte flm, it comes with a FacilityID

        :param dict flm_data:
        :return: primary key (_id) of the flm collection
        :rtype str
        """

        now = datetime.datetime.now(datetime.timezone.utc)
        try:
            db = self.db.conn()
            db = db['smpte_flm']
            self.convert_flm_to_date(flm_data)
            return_data = db.find_one_and_update(
                {"flm.FacilityID": flm_data["FacilityID"]},
                {'$set': {"flm": flm_data, "last_modified": now}}
            )

        except Exception as e:
            raise FLMException('Unable to update FLM {}, one already exists in collection. Error: {}'.format(
                flm_data["FacilityID"], e))
        return return_data['_id']

    def convert_flm_to_date(self, flm_data: Dict):
        """ Takes a FLM and converts all the string representations of dates into datetimes

        :param dict flm_data: raw flm data
        :return: None
        """
        auditorium_info = flm_data.get("AuditoriumInfo", {})
        auditorium_list = auditorium_info.get('AuditoriumList', [])
        for auditorium in auditorium_list:
            string_to_date(auditorium)

        facility_info = flm_data.get("FacilityInfo", {})
        facility_device_list = facility_info.get('FacilityDeviceList', {})
        for device in facility_device_list:
            string_to_date(device)
        if 'IssueDate' in flm_data:
            flm_data['IssueDate'] = arrow.get(flm_data['IssueDate']).floor('second').datetime

    def delete_one_smpte_flm(self, facility_id):
        """ Delete one smpte FLM IFF there is a single match

        :param str or int facility_id: ie "83"
        :return: instance of pymongo.results.DeleteResult
        """
        return self._delete_one_flm(facility_id=facility_id, target='smpte')

    def _delete_one_flm(self, facility_id: str, target: str = 'source'):
        """ Will search and delete a document IFF there is a single match

        :param str facility_id:
        :param str target: ['source'|'smpte'] for which collection to target (default 'source')
        :return: instance of pymongo.results.DeleteResult
        """
        db = self.db.conn()
        if target == 'source':
            db = db.source_flm
        elif target == 'smpte':
            db = db.smpte_flm
        else:
            raise FLMException('Invalid target: {}, expected {}'.format(target, ['smpte', 'source']))
        verify_number_of_delete = db.count({"flm.FacilityID": facility_id})
        del_result = None
        if verify_number_of_delete == 1:
            del_result = db.delete_one({"flm.FacilityID": facility_id})

        return del_result

    def extract_smpte_flm(self, facility_id: str = None, alternate_facility_id: str = None,
                          object_id: str = None) -> List:
        """ Retrieve a single FLM either from smpte FLM collections, wrapper for _extract_flm

        :param str facility_id: ie. aam.com:ZA-SKK-946427-02
        :param str alternate_facility_id: alternate facility id, only for smpte flms (default None)
        :param str object_id: collection's _id
        :return: N documents containing the particular FLM
        :rtype facility_id: list
        """
        db = self.db.conn()
        db = db['smpte_flm']

        return_doc = None
        if object_id:
            return_doc = db.find(
                {"_id": object_id}
            )
        elif facility_id and not alternate_facility_id:
            return_doc = db.find({"flm.FacilityID": facility_id})

        elif not facility_id and alternate_facility_id:
            return_doc = db.find(
                {"flm.FacilityInfo.AlternateFacilityIDList.AlternateFacilityID": alternate_facility_id}
            )

        elif facility_id and alternate_facility_id:
            return_doc = db.find(
                {"$and": [
                    {"flm.FacilityInfo.AlternateFacilityIDList.AlternateFacilityID": alternate_facility_id},
                    {"flm.FacilityID": facility_id}
                ]}
            )

        d = list()

        if return_doc and return_doc.count() >= 1:
            for doc in return_doc:
                for auditorium in doc['flm']['AuditoriumInfo']['AuditoriumList']:
                    date_to_string(auditorium)
                try:
                    doc['flm']['IssueDate'] = doc['flm']['IssueDate'].strftime("%Y-%m-%dT%H:%M:%S")
                except KeyError:
                    raise FLMException('Invalid FLM: no Issue Date provided for {}'.format(facility_id))
                d.append(doc)
        return d

    def _extract_flm(self, facility_id,
                     target: str = 'source',
                     alternate_facility_id: str = None,
                     object_id: str = None) -> List:
        """ Retrieve a single FLM either from the source FLM or smpte FLM collections

        :param str or int facility_id:
        :param str target: ['source'|'smpte'] for which collection to target (default 'source')
        :param str alternate_facility_id: alternate facility id, only for smpte flms (default None)
        :param str object_id: collection's _id
        :return: N documents containing the particular FLM
        :rtype facility_id: list
        """
        db = self.db.conn()

        if target == 'source':
            db = db['source_flm']
        elif target == 'smpte':
            db = db['smpte_flm']
        else:
            raise FLMException('Invalid target: {}, expected {}'.format(target, ['smpte', 'source']))

        return_doc = None
        if object_id:
            return_doc = db.find(
                {"_id": object_id}
            )
        elif facility_id:
            # check smpte facility ID if it contains an extra country code in it
            smpte_urn = "SMPTE-"

            if not isinstance(facility_id, int) and facility_id[:4] == smpte_urn:
                facility_id = int(facility_id.split("-")[1])

            return_doc = db.find({"flm.FacilityID": facility_id})

        elif not facility_id and target is 'smpte' and alternate_facility_id:
            return_doc = db.find(
                {"flm.FacilityInfo.AlternateFacilityIDList.AlternateFacilityID": alternate_facility_id}
            )

        elif facility_id and target is 'smpte' and alternate_facility_id:
            return_doc = db.find(
                {"$and": [
                    {"flm.FacilityInfo.AlternateFacilityIDList.AlternateFacilityID": alternate_facility_id},
                    {"flm.FacilityID": facility_id}

                ]}
            )

        d = list()

        if return_doc and return_doc.count() >= 1:
            for doc in return_doc:
                for auditorium in doc['flm']['AuditoriumInfo']['AuditoriumList']:
                    date_to_string(auditorium)
                # [date_to_string(x) for x in doc['flm']['AuditoriumInfo']['AuditoriumList']]
                try:
                    doc['flm']['IssueDate'] = doc['flm']['IssueDate'].strftime("%Y-%m-%dT%H:%M:%S")
                except KeyError:
                    raise FLMException('Invalid FLM: no Issue Date provided for {}'.format(facility_id))

                d.append(doc)
        return d


if __name__ == '__main__':
    import doctest

    doctest.testmod()
