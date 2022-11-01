#!/usr/bin/env python3
# -*- coding: utf-8 -*-

""" Generator of random GEDCOM databases.

 Using varioius statistical databases, generates a genealogical database.

"""

# Copyright (C) 2022 Mefistotelis <mefistotelis@gmail.com>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

__version__ = "0.0.1"
__author__ = "Mefistotelis"
__license__ = "GPL"

import sys
import argparse
import collections
import csv
import re

FIRSTNAMES_MALE_PL_FNAME="3-_wykaz_imion_meskich_nadanych_dzieciom_urodzonym_w_2021_r._wg_pola_imie_pierwsze__statystyka_ogolna_dla_calej_polski.csv"
FIRSTNAMES_FEML_PL_FNAME="3-_wykaz_imion_zenskich_nadanych_dzieciom_urodzonym_w_2021_r._wg_pola_imie_pierwsze__statystyka_ogolna_dla_calej_polski.csv"
LASTNAMES_MALE_PL_FNAME="nazwiska_meskie-z_uwzglednieniem_osob_zmarlych.csv"
LASTNAMES_FEML_PL_FNAME="nazwiska_zenskie-z_uwzglednieniem_osob_zmarlych.csv"

WeightedString = collections.namedtuple('WeightedString', ['s', 'weight'])


def eprint(*args, **kwargs):
  print(*args, file=sys.stderr, **kwargs)


def csv_read_weighted_list(po, fname, strcol, weightcol, fix_case):
  if (po.verbose > 0):
     print("{}: Reading '{:s}'".format(po.gedcom, fname))
  wslist = []
  with open(fname, newline='', encoding='utf-8') as csvfile:
    reader = csv.reader(csvfile, delimiter=',', quotechar='|')
    try:
        for row in reader:
            if reader.line_num == 1: continue
            s = row[strcol]
            weight = int(row[weightcol], 10)
            if fix_case:
                s = s.title()
            wslist.append(WeightedString(s, weight))
    except csv.Error as e:
        sys.exit('{}:{}: {}'.format(fname, reader.line_num, e))
    return wslist


def gedcom_generate(po, gedfile):
  if (po.verbose > 0):
     print("{}: XXX {:d}".format(po.gedcom,0))

  fname = "input_data/{:s}".format(FIRSTNAMES_MALE_PL_FNAME)
  po.firstnames_male = csv_read_weighted_list(po, fname, 0, 2, True)
  #print(po.firstnames_male)

  fname = "input_data/{:s}".format(FIRSTNAMES_FEML_PL_FNAME)
  po.firstnames_feml = csv_read_weighted_list(po, fname, 0, 2, True)
  #print(po.firstnames_feml)

  fname = "input_data/{:s}".format(LASTNAMES_MALE_PL_FNAME)
  po.lastnames_male = csv_read_weighted_list(po, fname, 0, 1, True)
  #print(po.lastnames_male)

  fname = "input_data/{:s}".format(LASTNAMES_FEML_PL_FNAME)
  po.lastnames_feml = csv_read_weighted_list(po, fname, 0, 1, True)
  #print(po.lastnames_feml)

def main():
  """ Main executable function.

  Its task is to parse command line options and call a function which performs requested command.
  """
  # Parse command line options

  parser = argparse.ArgumentParser(description=__doc__.split('.')[0])

  parser.add_argument("-v", "--verbose", action="count", default=0,
          help="increases verbosity level; max level is set by -vvv")

  subparser = parser.add_mutually_exclusive_group()

  parser.add_argument("-o", "--gedcom", type=str,
          help="output GEDCOM (*.ged) file name")

  subparser.add_argument("--version", action='version', version="%(prog)s {version} by {author}"
            .format(version=__version__,author=__author__),
          help="display version information and exit")

  po = parser.parse_args()

  if po.gedcom:

     if (po.verbose > 0):
        print("{}: Opening for conversion to ELF".format(po.gedcom))
     gedfile = open(po.gedcom, "w")

     gedcom_generate(po, gedfile)

     gedfile.close();

  else:

    raise NotImplementedError('Unsupported command.')


if __name__ == "__main__":
    try:
        main()
    except Exception as ex:
        eprint("Error: "+str(ex))
        raise
        sys.exit(10)
