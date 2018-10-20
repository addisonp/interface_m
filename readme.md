# SMPTE FLM MongoDB Interface

This library provides methods into the MongoDB collection for SMPTE [www.smpte.org] FLMs.

## Requirements

* arrow
* bson
* dictalchemy
* jsonschema
* mock
* mongomock
* pymongo
* PyYAML
* python-box
* regex
* tenacity
* tzlocal


## Using the API Library

These are the available methods for the **FLM** class
```
convert_flm_to_date(flm_data)
delete_one_smpte_flm(facility_id)
extract_smpte_flm(facility_id, alternate_facility_id, object_id)
populate_smpte_flm(flm_data, smpte_id)
```

## Examples

### Retrieve a FLM
```python
from mongo_interface.mongo_api import FLM
flm = FLM()

flm_data = flm.extract_smpte_flm(facility_id=3)
```

## Change Log
0.0.0 Initial implementation with one sample test using mocking
0.0.1 Connection to PostgreSQL through SQLAlchemy and multiprocessing of all certificates for device lookup