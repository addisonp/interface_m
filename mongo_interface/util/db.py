def get_next_sequence(collection, name):
    return collection.find_one_and_update(filter={'_id': name}, update={'$inc': {'seq': 1}}, new=True).get('seq')
