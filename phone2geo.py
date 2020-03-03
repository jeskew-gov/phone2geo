import contextlib
import dataclasses
import os
import re
import sqlite3
import typing

PHONE_NUMBER_PATTERN = re.compile(r"^[2-9]\d{9}$")

@dataclasses.dataclass(frozen=True)
class MetadataRecord:
  phone_number: str
  country: typing.Optional[str]
  time_zone: typing.Optional[str]
  region: typing.Optional[str]
  rate_center: typing.Optional[str]
  operating_company_number: typing.Optional[str]
  carrier: typing.Optional[str]


class InvalidNumberError(Exception):
  f"""An error raised when the number provided does not match the expected
  format of {PHONE_NUMBER_PATTERN.pattern}"""
  pass


class InvalidAreaCodeError(Exception):
  """An error raised when the provided number uses an unassignable area code"""

  # The area code (NPA) of the number submitted
  area_code: str
  # The explanation provided by NANPA for why the code is not assignable
  explanation: str

  def __init__(self, area_code: str, explanation: str):
    self.area_code = area_code
    self.explanation = explanation


class AreaCodeNotFoundError(Exception):
  """An error raised when the provided number is valid, but not corresponding
  entry is found in the NPA table."""

  area_code: str # The area code (NPA) of the number submitted

  def __init__(self, area_code: str):
    self.area_code = area_code


class InvalidExchangeError(Exception):
  """An error raised when a number identified by NANPA as belonging to a US
  geography does not match any existing NPA-NXX records or belongs to an
  exchange identified by NANPA as unassignable"""

  area_code: str # The area code (NPA) of the number submitted
  exchange: str # The exchange (NXX) of the number submitted

  def __init__(self, area_code: str, exchange: str):
    self.area_code = area_code
    self.exchange = exchange


class __MetadataRepository:
  """An interface into the carrier metadata database. Because SQLite uses
  stateful connections and cursors, this class is designed to be used as a
  context manager."""

  def __init__(self, db_path):
    self.db_path = db_path

  def __enter__(self):
    self.conn = sqlite3.connect(self.db_path)
    self.conn.row_factory = sqlite3.Row
    return self

  def __exit__(self, exc_type, exc_value, traceback):
    self.conn.close()
    del self.conn

  def has_us_area_code(self, number: str) -> bool:
    """Determine whether the provided number belongs to an area code allocated
    to the United States."""

    try:
      return self.locate_number(number).country in ('US', None)
    except InvalidExchangeError:
      return True
    except:
      return False

  def is_potentially_valid_number(self, number: str) -> bool:
    """Determine whether the provided number belongs to an assignable exchange
    within an assignable area code. Does NOT indicate whether any number
    actually has been assigned to a subscriber."""

    try:
      self.locate_number(number)
      return True
    except:
      return False

  def locate_number(self, number: str) -> MetadataRecord:
    """Build a metadata record from the various datasets in the repository"""

    number = re.sub(r'\W', '', number)
    if PHONE_NUMBER_PATTERN.match(number) is None:
      raise InvalidNumberError

    npa_record = self.__fetch_npa_metadata(number)

    if npa_record.country != 'US':
      # Further metadata tables are only available for US numbers, but NANPA
      # also administers the numbering plan for Canada and a good chunk of the
      # caribbean. If the number isn't from the US, return basic NANPA geodata
      return npa_record

    nxx_record = self.__fetch_nxx_metadata(npa_record)
    return self.__fetch_block_metadata(nxx_record)

  def __fetch_npa_metadata(self, number: str) -> MetadataRecord:
    """Build a barebones record from NANPA's NPA database table. All area code
    from 200-999 should have an entry in this table identifying the country,
    region, and timezone of a given area code, as well as whether a given area
    code is reserved for future expansion or otherwise unassignable."""

    area_code = number[0:3]
    cursor = self.conn.cursor()
    try:
      cursor.execute('SELECT * FROM npa WHERE NPA_ID = ?', [area_code])
      npa_data = cursor.fetchone()

      if npa_data is None:
        raise AreaCodeNotFoundError(area_code)

      if npa_data['ASSIGNABLE'] == 'No':
        raise InvalidAreaCodeError(area_code, npa_data['EXPLANATION'])

      if npa_data['IN_SERVICE'] == 'N' or npa_data['ASSIGNED'] == 'No':
        raise InvalidAreaCodeError(area_code, "Area code not in service")

      # Some area codes have no or limited geographic affinity and should return
      # sparser data
      return MetadataRecord(
        number,
        npa_data['COUNTRY'] if npa_data['COUNTRY'] != '' else None,
        npa_data['TIME_ZONE'] if npa_data['TIME_ZONE'] != '' else None,
        npa_data['LOCATION'] if npa_data['LOCATION'] != '' else None,
        None,
        None,
        None
      )
    finally:
      cursor.close()

  def __fetch_nxx_metadata(self, metadata: MetadataRecord) -> MetadataRecord:
    """Build a MetadataRecord from NANPA's exchange assignment listing. This
    table identifies whether an exchange is assignable and provides a state,
    rate center, and carrier for any assignable exchange. Note: rate center and
    carrier may not be accurate if the exchange participates in number
    pooling."""

    area_code = metadata.phone_number[0:3]
    exchange = metadata.phone_number[3:6]
    cursor = self.conn.cursor()

    try:
      cursor.execute(
        'SELECT * FROM npa_nxx WHERE NPA_NXX = ?',
        [f"{area_code}-{exchange}"])
      nxx_data = cursor.fetchone()

      if nxx_data is None or nxx_data['Use'] == 'UA':
        raise InvalidExchangeError(area_code, exchange)

      return MetadataRecord(
        metadata.phone_number,
        metadata.country,
        metadata.time_zone,
        nxx_data['State'],
        nxx_data['RateCenter'],
        nxx_data['OCN'],
        nxx_data['Company']
      )
    finally:
      cursor.close()

  def __fetch_block_metadata(self, metadata: MetadataRecord) -> MetadataRecord:
    """Build a metadata record from the pooling block assignment table. Not all
    valid exchanges are pooled, so numbers belonging to unpooled exchanges will
    return None from this method"""

    cursor = self.conn.cursor()

    try:
      cursor.execute(
        'SELECT * FROM blocks WHERE NPA = ? AND NXX = ? AND X = ?',
        [
          metadata.phone_number[0:3],
          metadata.phone_number[3:6],
          metadata.phone_number[6:7]
        ]
      )
      block_record = cursor.fetchone()
      if block_record is None:
        return metadata

      return MetadataRecord(
        metadata.phone_number,
        metadata.country,
        metadata.time_zone,
        block_record['State'],
        block_record['Rate_Center'],
        block_record['OCN'],
        block_record['Assigned_To']
      )
    finally:
      cursor.close()


def number_locator() -> __MetadataRepository:
  """Open a connection to the metadata repository as a managed context. Will
  maintain an open connection until the context is exited."""

  return __MetadataRepository(os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    'carrier_meta.sqlite3'
  ))


def locate_number(number: str) -> MetadataRecord:
  """Fetch broad geolocation data for a number administered by the North
  American Numbering Plan Administrator."""

  with number_locator() as locator:
    return locator.locate_number(number)
