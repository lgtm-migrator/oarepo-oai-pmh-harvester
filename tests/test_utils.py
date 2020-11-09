import pytest
from sickle.models import Header

from oarepo_oai_pmh_harvester.utils import get_oai_header_data, merge


def test_get_oai_header_data(load_entry_points, app, db, record_xml):
    header_xml = record_xml[0]
    header = Header(header_xml)
    res_tuple = get_oai_header_data(header)
    assert res_tuple == ('2017-09-11T08:12:53Z', False, 'oai:dspace.cuni.cz:20.500.11956/2623')


def test_get_oai_header_data_2(load_entry_points, app, db, record_xml):
    res_tuple = get_oai_header_data(xml=record_xml)
    assert res_tuple == ('2017-09-11T08:12:53Z', False, 'oai:dspace.cuni.cz:20.500.11956/2623')


def test_merge():
    res = merge({1: {"a": "A"}, 2: {"b": "B"}}, {2: {"c": "C"}, 3: {"d": "D"}})
    with pytest.raises(Exception):
        merge({1: {"a": "A"}, 2: {"b": "B"}}, {1: {"a": "A"}, 2: {"b": "C"}})
    assert res == {1: {'a': 'A'}, 2: {'b': 'B', 'c': 'C'}, 3: {'d': 'D'}}
