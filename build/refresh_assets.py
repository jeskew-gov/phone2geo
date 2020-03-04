# This script will process two reports published by NANPA (the North American
# Numbering Plan Administrator) and one published the National Pooling
# Administrator. All reports were freely downloadable by the public as of 28
# February 2020.

import constants
import tempfile
import urllib.request
import zipfile

# The first, the NPA Database, contains the complete listing of NPA (area code)
# assignments of all countries within the North American Numbering Plan as well
# as the geography and intended usage associated with a given NPA. It can be
# downloaded from https://www.nationalnanpa.com/nanp1/npa_report.csv
npa_database_response = urllib.request.urlopen('https://www.nationalnanpa.com/nanp1/npa_report.csv')

with open(constants.DEFAULT_NPA_REPORT_PATH, 'wb') as outfile:
  outfile.write(npa_database_response.read())

# The second, Central Office Code Assignment Records, contains a listing of
# NPA-NXX (area code + three digit exchange prefix) allocations and the
# rate center and carrier with which an exchange is associated. In the case of a
# pooled exchange, the rate center and carrier may not be accurate for all
# numbers within the exchange. It can be downloaded in zip archive form from
# https://www.nationalnanpa.com/nanp1/allutlzd.zip. The relevant file will be at
# the top level of the archive with the name allutlzd.txt
nxx_listing_response = urllib.request.urlopen('https://www.nationalnanpa.com/nanp1/allutlzd.zip')

with tempfile.TemporaryFile() as tmp:
  tmp.write(nxx_listing_response.read())
  tmp.seek(0)

  with zipfile.ZipFile(tmp) as archive:
    with archive.open('allutlzd.txt') as nxx_listing:
      with open(constants.DEFAULT_NXX_LISTING_PATH, 'wb') as outfile:
        outfile.write(nxx_listing.read())

# The third report, Block Report by Region, details the assignment of individual
# thousands blocks within pooled exchanges. It can be downloaded in archive form
# from
# https://www.nationalpooling.com/reports/region/AllBlocksAugmentedReport.zip.
# The relevant file will be at the top level of the archive with the name
# AllBlocksAugmentedReport.txt
blocks_listing_response = urllib.request.urlopen('https://www.nationalpooling.com/reports/region/AllBlocksAugmentedReport.zip')

with tempfile.TemporaryFile() as tmp:
  tmp.write(blocks_listing_response.read())
  tmp.seek(0)

  with zipfile.ZipFile(tmp) as archive:
    with archive.open('AllBlocksAugmentedReport.txt') as nxx_listing:
      with open(constants.DEFAULT_BLOCKS_LISTING_PATH, 'wb') as outfile:
        outfile.write(nxx_listing.read())
