import bark
import dataset


def no_iters(attrs):
    '''only simple datatypes can be added to database'''
    return {k: attrs[k]
            for k in attrs
            if isinstance(attrs[k], str) or not hasattr(attrs[k], '__iter__')}


def root_to_record(root):
    '''Converts a bark root to a dictionary'''
    return dict(name=root.name, path=root.path)


def entry_to_record(entry, root):
    rec = entry.attrs.copy()
    rec['path'] = entry.path
    rec['name'] = entry.name
    rec['root'] = root.path
    rec['timestamp'] = entry.timestamp
    return no_iters(rec)


def dset_to_record(dset, entry):
    rec = dset.attrs.copy()
    rec['name'] = dset.name
    rec['path'] = dset.path
    rec['entry'] = entry.path
    rec['n_columns'] = len(rec['columns'])
    if 'datatype' not in rec:
        if 'dtype' in rec:
            rec['datatype'] = 0
        else:
            rec['datatype'] = 1000
    return no_iters(rec)


def dset_columns_to_records(dset):
    for col in dset.attrs['columns']:
        rec = dset.attrs['columns'][col].copy()
        rec['dataset'] = dset.path
        rec['name'] = str(col)
        yield no_iters(rec)


def events_to_records(dset):
    if 'datatype' in dset.attrs:
        datatype = dset.attrs['datatype']
    else:
        datatype = dset.default_datatype()
    rows = dset.data.to_dict('records')
    print(dset.path)
    for i, row in enumerate(rows):
        row['dataset'] = dset.path
        row['datatype'] = datatype
        if 'name' in row:
            row['name'] = str(row['name'])
        row['index'] = i
        yield row


def add_root(root, db_connection_string, events=False):
    db = dataset.connect(db_connection_string)
    root_table = db['root']
    entry_table = db['entry']
    dataset_table = db['dataset']
    column_table = db['column']
    if events:
        event_table = db['event']
    root_table.upsert(root_to_record(root), ['path'])
    for entry in root.entries.values():
        entry_table.upsert(entry_to_record(entry, root), ['path'])
        for dset in entry.datasets.values():
            dataset_table.upsert(dset_to_record(dset, entry), ['path'])
            for column in dset_columns_to_records(dset):
                column_table.upsert(column, ['path', 'name'])
            if events and isinstance(dset, bark.EventData):
                for event in events_to_records(dset):
                    event_table.upsert(event, ['path', 'index'])


def format_db_string(path, backend='sqlite', user='', pw='', port='', host=''):
    if port:
        port = ':' + str(port)
    if user:
        user = user + ':'
    if host:
        host = '@' + host
    connection = '{prot}://{user}{pw}{host}{port}/{path}'.format(prot=backend,
                                                                 user=user,
                                                                 pw=pw,
                                                                 host=host,
                                                                 port=port,
                                                                 path=path)
    print(connection)
    return connection


def main(bark_root_path, db_path, events, **connection_kwargs):
    connection_string = format_db_string(db_path, **connection_kwargs)
    root = bark.read_root(bark_root_path)
    add_root(root, connection_string, events)


def _run():
    import argparse
    p = argparse.ArgumentParser(description='''
    Add a bark root to a database. Database is created if it doesn't exist yet.
    The absolute path of each bark file is the unique key of each record.

    Remake the database if you move your data.
    ''')
    p.add_argument('barkroot', help='path to the bark root directory')
    p.add_argument('path', help='path to database')
    p.add_argument('-e',
                   '--events',
                   help='add event data to database',
                   action='store_true')
    p.add_argument('--backend',
                   help='database backend, default: sqlite',
                   default='sqlite')
    p.add_argument('--user', help='database user', default='')
    p.add_argument('--password', help='database password', default='')
    p.add_argument('--port', help='database port', default='')
    p.add_argument('--host', help='database host', default='')
    args = p.parse_args()
    main(args.barkroot,
         args.path,
         args.events,
         backend=args.backend,
         user=args.user,
         pw=args.password,
         port=args.port,
         host=args.host)


if __name__ == '__main__':
    _run()
