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

import argparse
import collections
import csv
import datetime
import random
import re
import sys

FIRSTNAMES_MALE_PL_FNAME="3-_wykaz_imion_meskich_nadanych_dzieciom_urodzonym_w_2021_r._wg_pola_imie_pierwsze__statystyka_ogolna_dla_calej_polski.csv"
FIRSTNAMES_FEML_PL_FNAME="3-_wykaz_imion_zenskich_nadanych_dzieciom_urodzonym_w_2021_r._wg_pola_imie_pierwsze__statystyka_ogolna_dla_calej_polski.csv"
LASTNAMES_MALE_PL_FNAME="nazwiska_meskie-z_uwzglednieniem_osob_zmarlych.csv"
LASTNAMES_FEML_PL_FNAME="nazwiska_zenskie-z_uwzglednieniem_osob_zmarlych.csv"

WeightedString = collections.namedtuple('WeightedString', ['s', 'weight'])

class GPEvent(object):
    def __init__(self, typ, dat, place):
        self.typ = typ
        self.dat = dat
        self.place = place

class GPerson(object):
    def __init__(self, level, ind, givname, surname, sex, families, events):
        self.level = level # Ancestry level within the tree; not used for GEDCOM, useful for the generator only
        self.ind = ind # String identifier for the person
        self.givname = givname # Given name of a person; if multiple names, separate by space
        self.surname = surname
        self.sex = sex # One char string indicating sex with accordance to GEDCOM specification
        self.families = families # Array with indices of families within GTree families array
        self.events = events

class GFamily(object):
    def __init__(self, ind, legal, dat, father, mother, children):
        self.ind = ind # String identifier for the family
        self.legal = legal # Legal status of the parents
        self.dat = dat # Date of marriage / relation start of parents
        self.father = father # Index of father within GTree people array
        self.mother = mother # Index of mother within GTree people array
        self.children = children # Array with indices of children within GTree people array

class GTree(object):
    def __init__(self, people, families, sources, notes, objects):
        self.people = people
        self.families = families
        self.sources = sources
        self.notes = notes
        self.objects = objects

def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)


def csv_read_weighted_list(po, fname, strcol, weightcol, fix_case):
    """ Load a list of strings with weights from a CSV file.
    """
    if (po.verbose > 1):
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
        except Exception as ex:
            sys.exit('{}:{}: {}'.format(fname, reader.line_num, ex))
    return wslist


def weighted_list_to_cdf(po, wlist):
    """ Creates Cummulative Distribution Function out of a list with weighted elements.
    """
    cdf = []
    prevtotal = 0.0
    weightmax = sum(elem.weight for elem in wlist)
    for elem in wlist:
        prob = elem.weight / weightmax
        newtotal = prevtotal + prob
        cdf.append( (newtotal,elem.s) )
        prevtotal = newtotal

    return cdf


def cdf_random_value(cdf):
    """ Draws a random value from Cummulative Distribution Function.
    """
    probmax = cdf[-1][0]
    rand = random.random() * probmax
    for probupper, val in cdf:
        if probupper > rand:
            return val
    raise ValueError("Invalid cummmulative distribution function")


def cdf_random_value_not_in_list(cdf, reject_list):
    """ Draws a random value from Cummulative Distribution Function, skipping values in list.
    """
    probmin = 0.0
    newtotal = probmin
    smallcdf = []
    for probupper, val in cdf:
        if val in reject_list:
            probmin = probupper
            continue
        newtotal = newtotal + (probupper - probmin)
        smallcdf.append( (newtotal,val) )
        probmin = probupper

    return cdf_random_value(smallcdf)


def num_of_children_cdf(po, expected_num):
    """ Creates Cummulative Distribution Function for selecting amount of children.
        Probability linearly grows from 1 child to expected_num, then falls back to zero.
        Having no children is a special case, it has the same probability as expected_num - 1.
    """
    cdf = []
    max_num = int(expected_num * 3 / 2 + 1)

    newtotal = 0.0
    if expected_num == 0:
        a = 0.4 / 1
        b = 0.6 / 2
        for n in [0,1]:
            prob = a * (1-n) + b
            newtotal = newtotal + prob
            cdf.append( (newtotal,n) )
        return cdf

    total_upto_expected = (1.0 / (max_num+1)) * (6/5 * expected_num + 1)
    total_after_expected = 1.0  - total_upto_expected

    # First half - over 50% probability that selected value is lower or equal the expected
    if expected_num > 1:
        a = 0.8 * total_upto_expected / (expected_num-1 + sum(range(1, expected_num+1)))
        b = 0.2 * total_upto_expected / (expected_num+1)
        for n in [0,]:
            prob = a * (expected_num-1) + b
            newtotal = newtotal + prob
            cdf.append( (newtotal,n) )
        for n in range(1, expected_num+1):
            prob = a * n + b
            newtotal = newtotal + prob
            cdf.append( (newtotal,n) )
    else:
        a = 0.2 * total_upto_expected / 1
        b = 0.8 * total_upto_expected / (expected_num+1)
        for n in [0,1]:
            prob = a * n + b
            newtotal = newtotal + prob
            cdf.append( (newtotal,n) )

    # Second half - less than 50% probability that selected value is greater than the expected
    if max_num-expected_num > 1:
        a = 0.8 * total_after_expected / sum(range(1, max_num-expected_num))
        b = 0.2 * total_after_expected / (max_num-expected_num)
        for n in range(expected_num+1, max_num+1):
            prob = a * (max_num-n) + b
            newtotal = newtotal + prob
            cdf.append( (newtotal,n) )
    else:
        for n in range(expected_num+1, max_num+1):
            prob = 1.0 * total_after_expected
            newtotal = newtotal + prob
            cdf.append( (newtotal,n) )

    return cdf


def person_sex_cdf(po):
    """ Creates Cummulative Distribution Function for selecting sex of a person.
    """
    cdf = [
    (0.48,"M"),
    (0.96,"F"),
    (0.98,"X"),
    (0.99,"U"),
    (1.00,"N"),
    ]
    return cdf


def relation_type_cdf(po):
    """ Creates Cummulative Distribution Function for selecting type of parents relation in a family.
    """
    cdf = [
    (0.60,"marriage"),
    (0.70,"civil"),
    (0.80,"not married"),
    (0.85,"unknown"),
    (0.86,"religious"),
    (0.87,"common law"),
    (0.94,"partnership"),
    (0.97,"registered partnership"),
    (0.99,"living together"),
    (1.00,"living apart together"),
    ]
    return cdf


def create_father(po, gtree, gfamily_id, givname, surname, sex):
    """ Create a father for given family.

        If surname is Null, get it from other family members.
    """
    gfamily = gtree.families[gfamily_id]
    if gfamily.mother is not None:
        gmother = gtree.people[gfamily.mother]
        level = gmother.level
        if surname is None:
            surname = gmother.surname
    elif len(gfamily.children) > 0:
        gchild_first = gtree.people[gfamily.children[0]]
        level = gchild_first.level - 1
        if surname is None:
            surname = gchild_first.surname
    else:
        level = 0
        if surname is None:
            surname = ""
    families_list = [gfamily_id,]
    gfather = GPerson(level, "", givname, surname, sex, families_list, [])
    gfather_id = len(gtree.people)
    gtree.people.append(gchild)
    gfamily.father = gfather_id
    return gchild_id


def create_child(po, gtree, gfamily_id, givname, surname, sex):
    """ Create a child for given family.

        If surname is Null, get it from other family members.
    """
    gfamily = gtree.families[gfamily_id]
    if gfamily.father is not None:
        gfather = gtree.people[gfamily.father]
        level = gfather.level + 1
        if surname is None:
            surname = gfather.surname
    elif gfamily.mother is not None:
        gmother = gtree.people[gfamily.mother]
        level = gmother.level + 1
        if surname is None:
            surname = gmother.surname
    elif len(gfamily.children) > 0:
        gchild_first = gtree.people[gfamily.children[0]]
        level = gchild_first.level
        if surname is None:
            surname = gchild_first.surname
    else:
        level = 0
        if surname is None:
            surname = ""
    families_list = [gfamily_id,]
    gchild = GPerson(level, "", givname, surname, sex, families_list, [])
    gchild_id = len(gtree.people)
    gtree.people.append(gchild)
    gfamily.children.append(gchild_id)
    return gchild_id


def create_family(po, gtree, gfather_id, gmother_id, children_list):
    """ Create a family which includes given people.
    """
    legal = cdf_random_value(relation_type_cdf(po))
    # Create the family in list of families
    gfamily = GFamily("", legal, None, gfather_id, gmother_id, children_list)
    gfamily_id = len(gtree.families)
    gtree.families.append(gfamily)
    # Add family ID to all members
    if gfather_id is not None:
        gfather = gtree.people[gfather_id]
        gfather.families.append(gfamily_id)
    if gmother_id is not None:
        gmother = gtree.people[gmother_id]
        gmother.families.append(gfamily_id)
    for gchild_id in children_list:
        gchild = gtree.people[gchild_id]
        gchild.families.append(gfamily_id)
    return gfamily_id


def generate_child(po, gtree, gfamily_id, givname, surname, sex):
    """ Generate a child for given family.

        If any parameter is Null, generate random value.
    """
    if sex is None:
        sex = cdf_random_value(person_sex_cdf(po))
    if givname is None:
        if sex == "M":
            firstnames_cdf = po.firstnames_male_cdf
        elif sex == "F":
            firstnames_cdf = po.firstnames_feml_cdf
        else:
            if random.random() * 100 < 50:
                firstnames_cdf = po.firstnames_male_cdf
            else:
                firstnames_cdf = po.firstnames_feml_cdf
        givname = cdf_random_value(firstnames_cdf)
        secname = ""
        if random.random() * 100 < po.second_name_chance:
            secname = cdf_random_value(firstnames_cdf)
        if len(secname) > 0:
            givname = givname + " " + secname
    gchild_id = create_child(po, gtree, gfamily_id, givname, surname, sex)
    return gchild_id


def generate_parent(po, gtree, gfamily_id, givname, surname, sex):
    """ Generate a parent for given family.

        If any parameter is Null, generate random value.
    """
    if sex is None:
        sex = cdf_random_value(person_sex_cdf(po))
    if givname is None:
        if sex == "M":
            firstnames_cdf = po.firstnames_male_cdf
        elif sex == "F":
            firstnames_cdf = po.firstnames_feml_cdf
        else:
            if random.random() * 100 < 50:
                firstnames_cdf = po.firstnames_male_cdf
            else:
                firstnames_cdf = po.firstnames_feml_cdf
        givname = cdf_random_value(firstnames_cdf)
        secname = ""
        if random.random() * 100 < po.second_name_chance:
            secname = cdf_random_value(firstnames_cdf)
        if len(secname) > 0:
            givname = givname + " " + secname
    gchild_id = create_child(po, gtree, gfamily_id, givname, surname, sex)
    return gchild_id


def family_get_random_child(po, gtree, gfamily_id, givname, surname, sex):
    matches = []
    gfamily = gtree.families[gfamily_id]
    for gchild_id in gfamily.children:
        gchild = gtree.people[gchild_id]
        if sex is not None:
            if gchild.sex != sex:
                continue
        if surname is not None:
            if gchild.surname != surname:
                continue
        if givname is not None:
            if gchild.givname != givname:
                continue
        matches.append(gchild_id)
    return random.choice(matches)


def generate_family_incl_person(po, gtree, gperson_incl_id, gperson_role, num_children, min_male_children):
    """ Generate a family around given parent person.
    """
    # Create a new family
    gfather_id = None
    if gperson_role == "father":
        gfather_id = gperson_incl_id
    gmother_id = None
    if gperson_role == "mother":
        gmother_id = gperson_incl_id
    children_list = []
    gchild = None
    if gperson_role == "child":
        children_list.append(gperson_incl_id)
        gchild = gtree.people[gperson_incl_id]
    gfamily_id = create_family(po, gtree, gfather_id, gmother_id, children_list)
    # Create any missing parents
    if gfather_id is None:
        gfather_id = generate_parent(po, gtree, gfamily_id, None, None, "M")
    if gmother_id is None:
        gfather_id = generate_parent(po, gtree, gfamily_id, None, None, "F")
    # Add children to the family
    min_children = 0
    male_children = 0
    if gchild is not None:
        min_children += 1
        if gchild.sex == "M":
            male_children += 1
    for i in range(min_children, num_children):
        sex = cdf_random_value(person_sex_cdf(po))
        if (i == num_children - min_male_children) and (male_children < min_male_children):
            sex = "M"
        if sex == "M":
            male_children += 1
        gchild_id = generate_child(po, gtree, gfamily_id, None, None, sex)
    return gfamily_id

def generate_core_branch(po, gtree, start_date, num_w, num_h):
    """ Generate a string of families which will make core branch of the tree.
    """
    bdate = start_date + datetime.timedelta(days=random.randrange(365))
    # Generate a single person who will be the base for the branch
    surname = cdf_random_value(po.lastnames_male_cdf)
    gperson = None
    for i in [0,]:
        givname = cdf_random_value(po.firstnames_male_cdf)
        gperson = GPerson(i, "", givname, surname, "M", [], [])
        gperson_id = len(gtree.people)
        gtree.people.append(gperson)
    # Now create descending generations of families
    for i in range(1,num_h):
        gfamily_id = generate_family_incl_person(po, gtree, gperson_id, "father", num_w, 1)
        gperson_id = family_get_random_child(po, gtree, gfamily_id, None, None, "M")
    pass


def gedcom_reset_identifiers(po, gtree):
    """ Reset GEDCOM unique identifiers of people, families, notes, etc.
    """
    for idx, gperson in enumerate(gtree.people):
        gperson.ind = "I{:05d}".format(idx)
    for idx, gfamily in enumerate(gtree.families):
        gfamily.ind = "F{:05d}".format(idx)
    for idx, gsource in enumerate(gtree.sources):
        gsource.ind = "S{:05d}".format(idx)
    for idx, gnote in enumerate(gtree.notes):
        gnote.ind = "N{:05d}".format(idx)
    for idx, gobject in enumerate(gtree.objects):
        gobject.ind = "O{:05d}".format(idx)
    pass


def gedcom_date_format(date_obj):
    return date_obj.strftime("%d %b %Y").upper()


def gedcom_export_single_person_name(po, gedlines, gtree, gperson, pntype):
    givname = gperson.givname
    gedlines.append("1 NAME {:s} /{:s}/".format(givname, gperson.surname))
    if pntype is not None:
        gedlines.append("2 TYPE {:s}".format(pntype))
    if len(givname) > 0:
        gedlines.append("2 GIVN {:s}".format(givname))
    #if len(gperson.nickname) > 0:
    #    gedlines.append("2 NICK {:s}".format(gperson.nickname))
    #if len(gperson.nameprefix) > 0:
    #    gedlines.append("2 SPFX {:s}".format(gperson.nameprefix))
    if len(gperson.surname) > 0:
        gedlines.append("2 SURN {:s}".format(gperson.surname))
    #if len(gperson.namesuffix) > 0:
    #    gedlines.append("2 NSFX {:s}".format(gperson.namesuffix))


def gedcom_export_single_person(po, gedlines, gtree, gperson):
    if True:
        # Individual ID definition line
        gedlines.append("0 @{:s}@ INDI".format(gperson.ind))

    if True:
        gedcom_export_single_person_name(po, gedlines, gtree, gperson, "birth")

    #for pntype, pname in gperson.other_names.items():
    #    gedcom_export_single_person_name(po, gedlines, gtree, pntype)

    if len(gperson.sex) > 0:
        gedlines.append("1 SEX {:s}".format(gperson.sex.upper()))

    return#!!!TODO
    if True:
        if gperson.ind in family_children_lookup.keys():
            family_children_lk_id = family_children_lookup[gperson.ind]
        else:
            family_children_lk_id = None
        if (family_children_lk_id is not None):
            # Add Family Child entry
            gedlines.append("1 FAMC @{:s}@".format(family_children_lk_id))
            gedlines.append("2 PEDI birth")

    if True:
        if p['id'] in family_parents_lookup.keys():
            fam_parents_lk_list = family_parents_lookup[p['id']]
        else:
            fam_parents_lk_list = []
        for family_id in fam_parents_lk_list:
            # Add Family spouse/partner entry
            gedlines.append("1 FAMS @{:s}@".format(family_id))

    if 'birth_date' in p.keys() or 'birth_place' in p.keys() or 'birth_comment' in p.keys():
        gedlines.append("1 BIRT")
        if 'birth_date' in p.keys():
            export_single_date(gedfile, p['birth_date'])
        if 'birth_place' in p.keys():
            gedlines.append("2 PLAC {:s}".format(p['birth_place']))
        if 'birth_comment' in p.keys():
            gedlines.append("2 TYPE {:s}".format(p['birth_comment']))

    if 'death_date' in p.keys() or 'death_place' in p.keys() or 'death_comment' in p.keys():
        gedlines.append("1 DEAT")
        if 'death_date' in p.keys():
            export_single_date(gedfile, p['death_date'])
        if 'death_place' in p.keys():
            gedlines.append("2 PLAC {:s}".format(p['death_place']))
        if 'death_comment' in p.keys():
            gedlines.append("2 TYPE {:s}".format(p['death_comment']))

    if p['link'] is not None:
        gedlines.append("1 OBJE")
        gedlines.append("2 FORM URL")
        gedlines.append("2 FILE {:s}".format(p['link']))

    if 'image_link' in p.keys():
        image_fname = download_image(p, p['image_link'])
        if image_fname is not None:
            gedlines.append("1 OBJE")
            gedlines.append("2 FORM jpeg")
            gedlines.append("2 FILE {:s}".format(image_fname))

    if 'occupation' in p.keys() and len(p['occupation']) > 0:
        gedlines.append("1 OCCU {:s}".format(p['occupation']))

    if True:
        for source_id in gperson.sources:
            gedlines.append("1 SOUR @{:s}@".format(source_id))
            nt_source = note_sources[source_id]
            for note_id in nt_source['notes']:
                gedlines.append("2 NOTE @{:s}@".format(note_id))

    if True:
        for note_id in gperson.notes:
            gedlines.append("1 NOTE @{:s}@".format(note_id))

    if 'change_date' in p.keys():
            gedlines.append("1 CHAN")
            gedlines.append("2 DATE {:s}".format(p['change_date']))
            #gedlines.append("3 TIME 12:34:58")


def gedcom_export_single_family(po, gedlines, gtree, gfamily):
    gedlines.append("0 @{:s}@ FAM".format(gfamily.ind))
    gfather = None
    if gfamily.father is not None:
        gfather = gtree.people[gfamily.father]
    gmother = None
    if gfamily.mother is not None:
        gmother = gtree.people[gfamily.mother]
    if gfather is not None:
        gedlines.append("1 HUSB @{:s}@".format(gfather.ind))
    if gmother is not None:
        gedlines.append("1 WIFE @{:s}@".format(gmother.ind))
    for gchild_id in gfamily.children:
        gchild = gtree.people[gchild_id]
        gedlines.append("1 CHIL @{:s}@".format(gchild.ind))
    # Last change info lines
    gedlines.append("1 CHAN")
    gedlines.append("2 DATE {:s}".format(gedcom_date_format(po.final_date)))
    gedlines.append("2 TIME 01:23:46")
    pass

def gedcom_export_single_source(po, gedlines, gtree, gsource):
    if True:
        # Individual ID definition line
        gedlines.append("0 @{:s}@ SOUR".format(gsource.ind))
    #TODO
    pass


def gedcom_export_single_note(po, gedlines, gtree, gnote):
    if True:
        # Individual ID definition line
        gedlines.append("0 @{:s}@ NOTE".format(gnote.ind))
    #TODO
    pass


def gedcom_export_single_object(po, gedlines, gtree, gobject):
    if True:
        # Individual ID definition line
        gedlines.append("0 @{:s}@ OBJE".format(gobject.ind))
    #TODO
    pass


def gedcom_generate(po, gedfile):
    if (po.verbose > 0):
       print("{}: Reading name lists ...".format(po.gedcom))

    fname = "input_data/{:s}".format(FIRSTNAMES_MALE_PL_FNAME)
    firstnames_male = csv_read_weighted_list(po, fname, 0, 2, True)
    #print(firstnames_male)
    po.firstnames_male_cdf = weighted_list_to_cdf(po, firstnames_male)
    del firstnames_male

    fname = "input_data/{:s}".format(FIRSTNAMES_FEML_PL_FNAME)
    firstnames_feml = csv_read_weighted_list(po, fname, 0, 2, True)
    #print(firstnames_feml)
    po.firstnames_feml_cdf = weighted_list_to_cdf(po, firstnames_feml)
    del firstnames_feml

    fname = "input_data/{:s}".format(LASTNAMES_MALE_PL_FNAME)
    lastnames_male = csv_read_weighted_list(po, fname, 0, 1, True)
    #print(lastnames_male)
    po.lastnames_male_cdf = weighted_list_to_cdf(po, lastnames_male)
    del lastnames_male

    fname = "input_data/{:s}".format(LASTNAMES_FEML_PL_FNAME)
    lastnames_feml = csv_read_weighted_list(po, fname, 0, 1, True)
    #print(lastnames_feml)
    po.lastnames_feml_cdf = weighted_list_to_cdf(po, lastnames_feml)
    del lastnames_feml

    po.num_people = 1000
    po.num_generations = 10

    po.final_date = datetime.date(2020, 1, 1)
    start_date = datetime.date(2020 - 35 * po.num_generations, 1, 1)
    gtree = GTree([], [], [], [], [])

    core_branch_w = int(1/3 * po.num_people / po.num_generations)
    generate_core_branch(po, gtree, start_date, core_branch_w, po.num_generations)

    gedcom_reset_identifiers(po, gtree)


    if True:
        gedlines = []
        gedlines.append("0 HEAD")
        gedlines.append("1 SOUR Fake generated data")
        gedlines.append("2 VERS 2021")
        gedlines.append("2 NAME Python based generator")
        gedlines.append("1 DATE {:s}".format(gedcom_date_format(po.final_date)))
        gedlines.append("2 TIME 01:23:45")
        gedlines.append("1 SUBM @SUBM@")
        gedlines.append("1 FILE {:s}".format(po.gedcom))
        gedlines.append("1 COPR Copyright (c) 2021 Mefistotelis.")
        gedlines.append("1 GEDC")
        gedlines.append("2 VERS 5.5.1")
        gedlines.append("2 FORM LINEAGE-LINKED")
        gedlines.append("1 CHAR UTF-8")
        gedlines.append("0 @SUBM@ SUBM")
        gedlines.append("1 NAME")
        for line in gedlines:
            gedfile.write(line)
            gedfile.write("\n")

    for gperson in gtree.people:
        gedlines = []
        gedcom_export_single_person(po, gedlines, gtree, gperson)
        for line in gedlines:
            gedfile.write(line)
            gedfile.write("\n")

    for gfamily in gtree.families:
        gedlines = []
        gedcom_export_single_family(po, gedlines, gtree, gfamily)
        for line in gedlines:
            gedfile.write(line)
            gedfile.write("\n")

    for gsource in gtree.sources:
        gedlines = []
        gedcom_export_single_source(po, gedlines, gtree, gsource)
        for line in gedlines:
            gedfile.write(line)
            gedfile.write("\n")

    for gnote in gtree.notes:
        gedlines = []
        gedcom_export_single_note(po, gedlines, gtree, gnote)
        for line in gedlines:
            gedfile.write(line)
            gedfile.write("\n")

    for gobject in gtree.objects:
        gedlines = []
        gedcom_export_single_object(po, gedlines, gtree, gobject)
        for line in gedlines:
            gedfile.write(line)
            gedfile.write("\n")

    if True:
        gedlines = []
        gedlines.append("0 TRLR")
        for line in gedlines:
            gedfile.write(line)
            gedfile.write("\n")

    #print(num_of_children_cdf(po, 8))

def main():
    """ Main executable function.

    Its task is to parse command line options and call a function which performs requested command.
    """
    # Parse command line options

    parser = argparse.ArgumentParser(description=__doc__.split('.')[0])

    parser.add_argument("-v", "--verbose", action="count", default=0,
          help="increases verbosity level; max level is set by -vvv")

    parser.add_argument("--second-name-chance", type=int, default=7,
          help="chance of a person having two names, in percent; default is 7")

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
        gedfile = open(po.gedcom, "w", encoding="utf-8")

        gedcom_generate(po, gedfile)

        gedfile.close();

    else:

        raise NotImplementedError('Unsupported command.')

    pass


if __name__ == "__main__":
    try:
        main()
    except Exception as ex:
        eprint("Error: "+str(ex))
        raise
        sys.exit(10)
