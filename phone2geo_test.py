import os
import phone2geo
import sqlite3
import tempfile
import unittest
import uuid

class DatasetIntegrationTest(unittest.TestCase):
  def test_provides_full_metadata_for_potentially_valid_us_number(self):
    """Uses a stable test case to potentially catch changes in the way the NPA
    database reports data elements"""

    number = '2128675309' # Hi, Jenny!
    record = phone2geo.locate_number(number)
    self.assertEqual(record.phone_number, number)
    self.assertEqual(record.country, 'US')
    self.assertEqual(record.region, 'NY')
    self.assertEqual(record.time_zone, 'E') # Eastern time zone abbreviation
    self.assertEqual(record.rate_center, 'NWYRCYZN01') # Metro NYC rate center
    self.assertIsNotNone(record.operating_company_number)
    self.assertIsNotNone(record.carrier)

  def test_raises_error_on_invalid_format(self):
    """Tests an invalid number (1 in first digit of NPA) to ensure basic pattern
    matching is working appropriately."""

    try:
      phone2geo.locate_number('1555555555')
      self.fail('An exception should have been raised.')
    except phone2geo.InvalidNumberError:
      pass

  def test_raises_error_on_invalid_area_code(self):
    """Tests a known-unassignable area code to make sure the appropriate
    exception is raised."""

    try:
      phone2geo.locate_number('9115555555')
      self.fail('An exception should have been raised.')
    except phone2geo.InvalidAreaCodeError:
      pass

  def test_raises_error_on_invalid_exchange(self):
    """Tests a known-unassignable exchange (NXX) to make sure the appropriate
    exception is raised."""

    try:
      phone2geo.locate_number('2129115555')
      self.fail('An exception should have been raised.')
    except phone2geo.InvalidExchangeError:
      pass

  def test_identifies_invalid_numbers(self):
    test_cases = [
      '212867530', # Too few digits
      '21286753094', # Too many digits
      '21286753o9', # Letters cannot be used
      '0555555555', # Area codes cannot start with '0'
      '1555555555', # Area codes cannot start with '1'
      '9115555555', # N11 area codes are reserved and not assignable
      '2129115555', # 911 is not an assignable exchange in any area code
    ]

    with phone2geo.number_locator() as locator:
      for case in test_cases:
        self.assertFalse(locator.is_potentially_valid_number(case))

  def test_identifies_us_numbers(self):
    """Area codes assigned by NANPA to non-US territories can be identified"""

    positive_test_cases = [
      '212', # New York, NY
      '907', # Alaska
      '808', # Hawai'i
      '787', # Puerto Rico
      '939', # Puerto Rico
      '671', # Guam
      '684', # American Samoa
      '670', # Mariana Islands
      '340', # US Virgin Islands
      '500', # Usable within NANP area (including US)
      '521', # Usable within NANP area (including US)
      '522', # Usable within NANP area (including US)
      '533', # Usable within NANP area (including US)
      '544', # Usable within NANP area (including US)
      '566', # Usable within NANP area (including US)
      '577', # Usable within NANP area (including US)
      '588', # Usable within NANP area (including US)
      '700', # Usable within NANP area (including US)
      '710', # Usable within NANP area (including US)
      '800', # Usable within NANP area (including US)
      '833', # Usable within NANP area (including US)
      '844', # Usable within NANP area (including US)
      '855', # Usable within NANP area (including US)
      '866', # Usable within NANP area (including US)
      '877', # Usable within NANP area (including US)
      '888', # Usable within NANP area (including US)
      '900', # Usable within NANP area (including US)

    ]

    negative_test_cases = [
      '204', # CANADA
      '226', # CANADA
      '236', # CANADA
      '242', # BAHAMAS
      '246', # BARBADOS
      '249', # CANADA
      '250', # CANADA
      '264', # ANGUILLA
      '268', # ANTIGUA/BARBUDA
      '284', # BRITISH VIRGIN ISLANDS
      '289', # CANADA
      '306', # CANADA
      '343', # CANADA
      '345', # CAYMAN ISLANDS
      '354', # CANADA
      '365', # CANADA
      '367', # CANADA
      '368', # CANADA
      '403', # CANADA
      '416', # CANADA
      '418', # CANADA
      '428', # CANADA
      '431', # CANADA
      '437', # CANADA
      '438', # CANADA
      '441', # BERMUDA
      '450', # CANADA
      '473', # GRENADA
      '474', # CANADA
      '506', # CANADA
      '514', # CANADA
      '519', # CANADA
      '548', # CANADA
      '579', # CANADA
      '581', # CANADA
      '587', # CANADA
      '604', # CANADA
      '613', # CANADA
      '639', # CANADA
      '647', # CANADA
      '649', # TURKS & CAICOS ISLANDS
      '658', # JAMAICA
      '664', # MONTSERRAT
      '672', # CANADA
      '705', # CANADA
      '709', # CANADA
      '721', # SINT MAARTEN
      '758', # ST. LUCIA
      '767', # DOMINICA
      '778', # CANADA
      '780', # CANADA
      '782', # CANADA
      '784', # ST. VINCENT & GRENADINES
      '807', # CANADA
      '809', # DOMINICAN REPUBLIC
      '819', # CANADA
      '825', # CANADA
      '829', # DOMINICAN REPUBLIC
      '849', # DOMINICAN REPUBLIC
      '867', # CANADA
      '868', # TRINIDAD AND TOBAGO
      '869', # ST. KITTS AND NEVIS
      '873', # CANADA
      '876', # JAMAICA
      '879', # CANADA
      '902', # CANADA
      '905', # CANADA
    ]

    with phone2geo.number_locator() as locator:
      for case in positive_test_cases:
        self.assertTrue(
          locator.has_us_area_code(case + '8675309'),
          f"Area code {case} should have been recognized as within US geo"
        )

      for case in negative_test_cases:
        self.assertFalse(
          locator.has_us_area_code(case + '8675309'),
          f"Area code {case} should have been recognized as not within US geo"
        )

if __name__ == '__main__':
  unittest.main()
