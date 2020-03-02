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
parser.add_argument('--npa', dest='npa_report_path', default='./npa_report.csv',
  type=str, help='''The path at which the NPA Database to import is located.''')
parser.add_argument('--nxx', dest='npanxx_report_path',
  default='./allutlzd.txt', type=str, help='''The path at which the NPA-NXX
  report to import is located.''')
parser.add_argument('--blocks', dest='block_report_path',
  default='./AllBlocksAugmentedReport.csv', type=str, help='''The path at which
  the Augmented Block report for all states can be found.''')
args = parser.parse_args()

# Create an SQLite3 DB into which carrier metadata will be imported at a
# temporary path
temporary_db_path = args.output_path + '.' + str(uuid.uuid4()) + '.tmp'
carrier_meta = sqlite3.connect(temporary_db_path)

def import_report(fd, table_name, primary_key_columns, delimiter=','):
  reader = csv.reader(fd, delimiter=delimiter)
  with carrier_meta:
    headers = next(reader)
    cols = ', '.join([re.sub('\\W', '_', col.strip()) for col in headers])
    key_cols = ', '.join([re.sub('\\W', '_', col) for col in primary_key_columns])
    carrier_meta.execute(f"CREATE TABLE {table_name} ({cols}, PRIMARY KEY({key_cols})) WITHOUT ROWID")
    carrier_meta.executemany(f"INSERT INTO {table_name} VALUES ({', '.join(['?' for col in headers])})", [row[:len(headers)] for row in reader])

with open(args.npa_report_path, 'r') as npa_report:
  # The first line reports the date the file was generated
  # E.g., "File Date,03/01/2020"
  (_, date_generated) = next(npa_report).split(',')
  logging.info(f'Importing NPA database generated on {date_generated}')

  # The rest of the file is a standard CSV file
  import_report(npa_report, 'npa', ['NPA_ID'])

with open(args.npanxx_report_path, 'r') as nxx_report:
  logging.info('Importing Central Office Code assignment records')
  import_report(nxx_report, 'npa_nxx', ['NPA-NXX'], delimiter="\t")

with open(args.block_report_path, 'r') as block_report:
  logging.info('Importing pooling block assignment records')
  import_report(block_report, 'blocks', ['NPA', 'NXX', 'X'])

carrier_meta.close()

try:
  os.replace(temporary_db_path, args.output_path)
except OSError as err:
  logging.error(err)
  os.remove(temporary_db_path)
