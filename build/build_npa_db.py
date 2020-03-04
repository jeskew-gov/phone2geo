# This script will process two reports published by NANPA (the North American
# Numbering Plan Administrator) and one published the National Pooling
# Administrator. All reports were freely downloadable by the public as of 28
# February 2020.
#
# The first, the NPA Database, contains the complete listing of NPA (area code)
# assignments of all countries within the North American Numbering Plan as well
# as the geography and intended usage associated with a given NPA. It can be
# downloaded from https://www.nationalnanpa.com/nanp1/npa_report.csv
#
# The second, Central Office Code Assignment Records, contains a listing of
# NPA-NXX (area code + three digit exchange prefix) allocations and the
# rate center and carrier with which an exchange is associated. In the case of a
# pooled exchange, the rate center and carrier may not be accurate for all
# numbers within the exchange. It can be downloaded from
# https://www.nationalnanpa.com/nanp1/allutlzd.zip
#
# The third report, Block Report by Region, details the assignment of individual
# thousands blocks within pooled exchanges. It can be downloaded from
# https://www.nationalpooling.com/reports/region/AllBlocksAugmentedReport.zip

import argparse
import csv
import constants
import datetime
import json
import logging
import os
import re
import sqlite3
import uuid

parser = argparse.ArgumentParser(description='''Imports the NANPA NPA database,
  the NANPA Central Office Code Assignment Records, and the National Pooling
  Administrator's Augmented Block Report for all states into a SQLite3 database
  for quick querying by this module.''')
parser.add_argument('-o', '--output', dest='output_path',
  default='../carrier_meta.sqlite3', type=str, help='''The path to which the
  imported database will be written. Any file at the path provided will be
  overwritten.''')
parser.add_argument('--npa', dest='npa_report_path',
  default=constants.DEFAULT_NPA_REPORT_PATH, type=str, help='''The path at which
  the NPA Database to import is located.''')
parser.add_argument('--nxx', dest='npanxx_report_path',
  default=constants.DEFAULT_NXX_LISTING_PATH, type=str, help='''The path at
  which the NPA-NXX report to import is located.''')
parser.add_argument('--blocks', dest='block_report_path',
  default=constants.DEFAULT_BLOCKS_LISTING_PATH, type=str, help='''The path at
  which the Augmented Block report for all states can be found.''')
parser.add_argument('--manifest-out', dest='import_manifest_path',
  default=constants.DEFAULT_IMPORT_MANIFEST_PATH, type=str, help='''The path to
  which the manifest for this import task should be written.''')
parser.add_argument('--prev-manifest', dest='prev_import_manifest_path',
  default=constants.DEFAULT_IMPORT_MANIFEST_PATH, type=str, help='''The path at
  which the most recent import manifest may be found.''')

args = parser.parse_args()

import_manifest = {}
prev_manifest = {}

print(f"Attempting to load previous manifest from {os.path.abspath(args.prev_import_manifest_path)}")
try:
  with open(args.prev_import_manifest_path, 'r') as prev_manifest_file:
    prev_manifest = json.load(prev_manifest_file)
except OSError as err:
  print(f"Manifest could not be loaded from {args.prev_import_manifest_path}; proceeding with fresh import")

# Initialize the new manifest
import_manifest['importDate'] = datetime.datetime.utcnow().isoformat()
import_manifest['importId'] = str(uuid.uuid4())
import_manifest['tablesImported'] = {}

# Create an SQLite3 DB into which carrier metadata will be imported at a
# temporary path
temporary_db_path = args.output_path + '.' + import_manifest['importId']
carrier_meta = sqlite3.connect(temporary_db_path)

def import_report(fd, table_name, primary_key_columns, delimiter=','):
  reader = csv.reader(fd, delimiter=delimiter)
  with carrier_meta:
    headers = [re.sub('\\W', '_', col.strip()) for col in next(reader)]
    import_manifest['tablesImported'][table_name] = headers

    cols = ', '.join(headers)
    key_cols = ', '.join([re.sub('\\W', '_', col) for col in primary_key_columns])
    carrier_meta.execute(f"CREATE TABLE {table_name} ({cols}, PRIMARY KEY({key_cols})) WITHOUT ROWID")
    for row in reader:
      value_count = min(len(row), len(headers))
      carrier_meta.execute(
        f"INSERT INTO {table_name} ({', '.join(headers[:value_count])}) VALUES ({', '.join(['?' for x in range(0, value_count)])})",
        [col.strip() for col in row[:value_count]]
      )

print(f'Importing NPA database from {os.path.abspath(args.npa_report_path)}')
with open(args.npa_report_path, 'r') as npa_report:
  # The first line reports the date the file was generated
  # E.g., "File Date,03/01/2020"
  (_, date_generated) = next(npa_report).split(',')
  print(f'Importing NPA database generated on {date_generated.strip()}')

  # The rest of the file is a standard CSV file
  import_report(npa_report, 'npa', ['NPA_ID'])

print(f'Importing Central Office Code assignment records from {os.path.abspath(args.npanxx_report_path)}')
with open(args.npanxx_report_path, 'r') as nxx_report:
  import_report(nxx_report, 'npa_nxx', ['NPA-NXX'], delimiter="\t")

print(f'Importing pooling block assignment records from {os.path.abspath(args.block_report_path)}')
with open(args.block_report_path, 'r') as block_report:
  import_report(block_report, 'blocks', ['NPA', 'NXX', 'X'])

carrier_meta.close()

try:
  os.replace(temporary_db_path, args.output_path)
except OSError as err:
  logging.error(err)
  os.remove(temporary_db_path)

for table, columns in import_manifest['tablesImported'].items():
  prev_columns = prev_manifest.get('tablesImported', {}).get(table, [])
  if sorted(columns) != sorted(prev_columns):
    columns_added = [col for col in columns if col not in prev_columns]
    columns_removed = [col for col in prev_columns if col not in columns]
    print(f"WARNING: The structure of {table} does not match the last import.")
    if len(columns_added) > 0:
      print(f"         The following columns have been added: {', '.join(columns_added)}")
    if len(columns_removed) > 0:
      print(f"         The following columns have been removed: {', '.join(columns_removed)}")
    print(f"         Any code reading from {table} may need to be adjusted to account for these changes")
    print("")

with open(args.import_manifest_path, 'w') as import_manifest_file:
  json.dump(import_manifest, import_manifest_file, indent='  ')
