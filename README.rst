phone2geo
=========


This is a utility for checking the validity and broad geolocation of phone
numbers using only data made freely available under the auspices of the Federal
Communications Commission. This includes reports by the North American Numbering
Plan Administrator, which is responsible for managing area codes and exchanges
for the United States and other countries participating in the North American
Numbering Plan, as well as data reported by the National Pooling Administrator,
which oversees the reallocation of blocks within exchanges.


Introduction
------------

Phone numbers within the North American Numbering Plan follow a simple pattern:

| (**NPA**) **NXX** - **T** 999

A number's :abbr:`NPA (Numbering Plan Area)` (aka its *area code*) identifies
the broad geographic area to which a call is directed, and its **NXX** (aka its
*exchange* or :abbr:`COC (Central Office Code)`) identifies a partition of an
area code that was historically handled by a single switch or central office
assigned to a particular **rate center**. Multiple exchanges may handle a single
large rate center, such as New York, NY.

With the introduction of number pooling, exchanges can be further broken down
into blocks of 1,000 numbers each, identified by the first digit of the phone
number suffix (**T** in the diagram above). **T** blocks within an exchange may
be allocated to another carrier and may not serve the same rate center as the
original exchange allocation.

This library uses NPA assignment, NXX allocation, and block reallocation data to
identify the **country**, **time zone**, and intra-country **region** of numbers
within the North American Numbering Plan. US numbers are also associated with
the **rate center** and **carrier** responsible for the number.

The library will also identify numbers which *cannot be valid* under the North
American Numbering Plan. Not all area codes are assignable, nor necessarily are
all exchanges within and otherwise valid area code.


Use
---

This library provides a query mechanism that is designed to be used as a managed
context.

.. code-block:: python

  import phone2geo

  with phone2geo.number_locator() as locator:
    number = '2128675309' # A valid number. Hi Jenny!
    is_user_number = locator.has_us_area_code(number) # True
    may_be_valid = locator.is_potentially_valid_number(number) # True
    number_metadata = locator.locate_number(number)

    print(number_metadata.country) # 'US'
    print(number_metadata.time_zone) # 'E'
    print(number_metadata.region) # 'NY'
    print(number_metadata.rate_center) # 'NWYRCYZN01' (NYC) as of 4 March 2020
    print(number_metadata.carrier) # 'VERIZON NEW YORK INC.' as of 4 March 2020
    print(number_metadata.operating_company_number) # '9104' as of 4 March 2020
    print(number_metadata.phone_number) # '2128675309'

The ``locate_number`` method will raise an ``InvalidNumberError`` when the
number is not formatted as a :abbr:`NANP (North American Numbering Plan)` number
(``^[2-9]\d{9}$``). It will raise an ``InvalidAreaCodeError`` exception if the
number's area code is unavailable for use or otherwise unassigned, and it will
raise an ``InvalidExchangeError`` when the area code/exchange pair is not
assigned to any carrier.


Caveats
-------

* Exchange, rate center, and carrier metadata is not available for numbers
assigned outside of the United States. Valid :abbr:`NANP (North American
Numbering Plan)` numbers outside the US will report the assigned country,
region, and time zone.
* The geographic affinity of a given number to its original assignment area is
not 100% reliable, as people do not necessarily change their cell phone numbers
after moving to another rate center or state.
* Carrier data may not be accurate for numbers that have been ported to another
provider.
* Numbers that belong to a valid area code and exchange have not necessarily
been assigned to a subscriber. This library does not verify if a number is in
service, just if it could be a valid number.
