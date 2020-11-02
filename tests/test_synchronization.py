from collections import defaultdict
from datetime import datetime
from itertools import islice

import pytest
import requests
from invenio_records import Record
from lxml.etree import _Element
from pytest import skip
from pytz import utc
from sickle.iterator import OAIItemIterator
from sqlalchemy.orm.exc import NoResultFound

from oarepo_oai_pmh_harvester.models import OAIRecord, OAISync, OAIProvider, OAIRecordExc
from oarepo_oai_pmh_harvester.proxies import current_oai_client


class TestSynchronization:
    def test_get_endpoint_config(self, load_entry_points, app, db, metadata):
        synchronizer = current_oai_client.providers["uk"]._synchronizers["xoai"]
        res = synchronizer.get_endpoint_config(metadata)
        assert res is not None
        assert isinstance(res, dict)

    def test_create_record(self, load_entry_points, app, db, metadata, ):
        synchronizer = current_oai_client.providers["uk"]._synchronizers["xoai"]
        rec, pid = synchronizer.create_record(metadata)
        assert rec == {'title': 'Testovací záznam', 'pid': '1'}

    def test_update_record(self, load_entry_points, app, db, metadata):
        synchronizer = current_oai_client.providers["uk"]._synchronizers["xoai"]
        record, id_ = synchronizer.create_record(metadata)
        provider = OAIProvider.query.filter_by(code="uk").one_or_none()
        if not provider:
            current_oai_client.create_providers()
        oai_sync = OAISync(provider_id=1)
        db.session.add(oai_sync)
        db.session.commit()
        oai_rec = OAIRecord(
            id=record.id,
            oai_identifier="oai:example.cz:1",
            creation_sync_id=oai_sync.id,
            pid="1",
            timestamp=datetime.now()
        )
        db.session.add(oai_rec)
        db.session.commit()
        metadata["title"] = "Updated record"
        record2 = synchronizer.update_record(oai_rec, metadata)
        assert record2 == {'title': 'Updated record', 'pid': '1'}

    def test_delete_record(self, load_entry_points, app, db, metadata):
        synchronizer = current_oai_client.providers["uk"]._synchronizers["xoai"]
        provider = OAIProvider.query.filter_by(code="uk").one_or_none()
        if not provider:
            current_oai_client.create_providers()
        record, id_ = synchronizer.create_record(metadata)
        oai_sync = OAISync(provider_id=1)
        db.session.add(oai_sync)
        db.session.commit()
        oai_rec = OAIRecord(
            id=record.id,
            oai_identifier="oai:example.cz:1",
            creation_sync_id=oai_sync.id,
            pid="1",
            timestamp=datetime.now()
        )
        db.session.add(oai_rec)
        db.session.commit()
        synchronizer.delete_record(oai_rec)
        with pytest.raises(NoResultFound):
            Record.get_record(oai_rec.id)
        deleted_record = Record.get_record(oai_rec.id, with_deleted=True)

    def test_delete(self, load_entry_points, app, db, metadata):
        synchronizer = current_oai_client.providers["uk"]._synchronizers["xoai"]
        provider = OAIProvider.query.filter_by(code="uk").one_or_none()
        if not provider:
            current_oai_client.create_providers()
        record, id_ = synchronizer.create_record(metadata)
        oai_sync = OAISync(provider_id=1)
        db.session.add(oai_sync)
        db.session.commit()
        oai_rec = OAIRecord(
            id=record.id,
            oai_identifier="oai:example.cz:1",
            creation_sync_id=oai_sync.id,
            pid="1",
            timestamp=datetime.now()
        )
        db.session.add(oai_rec)
        db.session.commit()
        metadata["title"] = "Updated record"
        synchronizer._delete(oai_rec)
        with pytest.raises(NoResultFound):
            Record.get_record(oai_rec.id)
        deleted_record = Record.get_record(oai_rec.id, with_deleted=True)

    def test_get_xml(self, load_entry_points, app, db):
        synchronizer = current_oai_client.providers["uk"]._synchronizers["xoai"]
        try:
            xml = synchronizer.get_xml("oai:dspace.cuni.cz:20.500.11956/111006")
        except requests.exceptions.RequestException:
            skip("Connection failed")
        assert isinstance(xml, _Element)

    def test_parse(self, load_entry_points, app, db, record_xml, parsed_record_xml):
        def default_to_regular(d):
            if isinstance(d, defaultdict):
                d = {k: default_to_regular(v) for k, v in d.items()}
            if isinstance(d, (list, tuple)):
                d = [default_to_regular(_) for _ in d]
            return d

        synchronizer = current_oai_client.providers["uk"]._synchronizers["xoai"]
        parsed = synchronizer.parse(record_xml)
        res = default_to_regular(parsed)
        assert res == parsed_record_xml

    def test_get_oai_identifiers(self, load_entry_points, app, db):
        synchronizer = current_oai_client.providers["uk"]._synchronizers["xoai"]
        ids = synchronizer._get_oai_identifiers()
        assert isinstance(ids, OAIItemIterator)

    def test_get_oai_identifiers_2(self, load_entry_points, app, db):
        synchronizer = current_oai_client.providers["uk"]._synchronizers["xoai"]
        ids = synchronizer._get_oai_identifiers(
            identifiers_list=["oai:dspace.cuni.cz:20.500.11956/111006"])
        assert len(ids) == 1
        assert isinstance(ids, list)

    def test_get_identifiers(self, load_entry_points, app, db):
        synchronizer = current_oai_client.providers["uk"]._synchronizers["xoai"]
        ids = synchronizer._get_identifiers()
        assert isinstance(ids, islice)

    def test_transform(self, load_entry_points, app, db):
        synchronizer = current_oai_client.providers["uk"]._synchronizers["xoai"]
        transformed = synchronizer.transform({})
        assert transformed == {}

    def test_create_or_update(self, load_entry_points, app, db, record_xml):
        synchronizer = current_oai_client.providers["uk"]._synchronizers["xoai"]
        oai_sync = OAISync(provider_id=1)
        synchronizer.oai_sync = oai_sync
        record = synchronizer.create_or_update("oai:dspace.cuni.cz:20.500.11956/2623",
                                               '2017-09-11T08:12:53Z', xml=record_xml)
        db.session.commit()
        assert record == {'pid': '1', 'title': 'Testovací záznam'}
        oai_rec = OAIRecord.query.filter_by(pid=1).one_or_none()
        record2 = synchronizer.create_or_update("oai:dspace.cuni.cz:20.500.11956/2623",
                                                '2017-09-11T08:12:53Z', xml=record_xml,
                                                oai_rec=oai_rec)
        assert record2 is None
        new_time_stemp = datetime.utcnow().replace(tzinfo=utc).isoformat()
        record3 = synchronizer.create_or_update("oai:dspace.cuni.cz:20.500.11956/2623",
                                                new_time_stemp, xml=record_xml,
                                                oai_rec=oai_rec)
        assert record3 == {'pid': '1', 'title': 'Testovací záznam'}

    def test_restart_counters(self, load_entry_points, app, db):
        synchronizer = current_oai_client.providers["uk"]._synchronizers["xoai"]
        synchronizer.created = 100
        synchronizer.modified = 100
        synchronizer.deleted = 100
        synchronizer.restart_counters()
        assert synchronizer.created == 0
        assert synchronizer.modified == 0
        assert synchronizer.deleted == 0

    def test_record_crud(self, load_entry_points, app, db, record_xml):
        synchronizer = current_oai_client.providers["uk"]._synchronizers["xoai"]
        oai_sync = OAISync(provider_id=1)
        synchronizer.oai_sync = oai_sync
        oai_identifier = "oai:dspace.cuni.cz:20.500.11956/2623"
        with pytest.raises(Exception, match="You have to provide oai_rec or oai_identifier"):
            synchronizer.record_crud()
        synchronizer.record_crud(oai_identifier=oai_identifier, xml=record_xml)
        db.session.commit()
        oai_rec = OAIRecord.get_record(oai_identifier)
        assert oai_rec is not None
        synchronizer.record_crud(oai_rec=oai_rec)
        db.session.commit()
        oai_rec2 = OAIRecord.get_record(oai_identifier)
        assert oai_rec == oai_rec2
        timestamp2 = oai_rec2.timestamp
        synchronizer.record_crud(oai_rec=oai_rec, timestamp='2050-10-22T08:18:08.567698+00:00',
                                 xml=record_xml)
        db.session.commit()
        oai_rec3 = OAIRecord.get_record(oai_identifier)
        assert oai_rec3.timestamp > timestamp2
        synchronizer.record_crud(oai_rec=oai_rec3, deleted=True)
        db.session.commit()
        # oai_rec4 = OAIRecord.get_record(oai_identifier)
        # assert oai_rec4 is None
        # TODO: zamyslet se co udělat se smazaným OAI recordem, invenio smaže metadata a označí
        #  PID jako smazaný, ale záznam zůstane. Otázka je co se stane,
        #  když OAI provider záznam obnoví a/nebo zaktualizuje.

    def test_record_crud_2(self, load_entry_points, app, db, record_xml):
        synchronizer = current_oai_client.providers["uk"]._synchronizers["xoai"]
        oai_sync = OAISync(provider_id=1)
        synchronizer.oai_sync = oai_sync
        oai_identifier = "oai:dspace.cuni.cz:20.500.11956/2623"

        # vytvoření záznamu
        synchronizer.record_crud(oai_identifier=oai_identifier, xml=record_xml)
        db.session.commit()
        oai_rec = OAIRecord.get_record(oai_identifier)
        assert oai_rec is not None

        # smazání záznamu
        synchronizer.record_crud(oai_rec=oai_rec, deleted=True)
        db.session.commit()
        oai_rec2 = OAIRecord.get_record(oai_identifier)
        assert oai_rec == oai_rec2

        # obnovení záznamu
        synchronizer.record_crud(oai_rec=oai_rec, timestamp='2050-10-22T08:18:08.567698+00:00',
                                 xml=record_xml)
        db.session.commit()
        oai_rec3 = OAIRecord.get_record(oai_identifier)
        assert oai_rec3 is not None
        record = Record.get_record(oai_rec.id)
        assert record is not None

    def test_exception_handler(self, load_entry_points, app, db):
        synchronizer = current_oai_client.providers["uk"]._synchronizers["xoai"]
        provider = OAIProvider.query.filter_by(code="uk").one_or_none()
        if not provider:
            current_oai_client.create_providers()
        oai_sync = OAISync(provider_id=1)
        db.session.add(oai_sync)
        db.session.commit()
        synchronizer.oai_sync = oai_sync
        oai_identifier = "oai:dspace.cuni.cz:20.500.11956/2623"
        try:
            raise Exception("Test exception")
        except Exception:
            synchronizer.exception_handler(oai_identifier)
        oai_exc = OAIRecordExc.query.filter_by(id=1).one_or_none()
        print(oai_exc.traceback)

    def test_record_handling(self, load_entry_points, app, db, record_xml):
        synchronizer = current_oai_client.providers["uk"]._synchronizers["xoai"]
        provider = OAIProvider.query.filter_by(code="uk").one_or_none()
        if not provider:
            current_oai_client.create_providers()
        oai_sync = OAISync(provider_id=1)
        db.session.add(oai_sync)
        db.session.commit()
        synchronizer.oai_sync = oai_sync

        synchronizer.record_handling(1, xml=record_xml)
        oai_rec = OAIRecord.get_record(oai_identifier="oai:dspace.cuni.cz:20.500.11956/2623")
        record = Record.get_record(id_=oai_rec.id)
        assert record == {'pid': '1', 'title': 'Testovací záznam'}

    def test_update_oai_sync(self, load_entry_points, app, db, record_xml):
        synchronizer = current_oai_client.providers["uk"]._synchronizers["xoai"]
        provider = OAIProvider.query.filter_by(code="uk").one_or_none()
        if not provider:
            current_oai_client.create_providers()
        oai_sync = OAISync(provider_id=1)
        db.session.add(oai_sync)
        db.session.commit()
        synchronizer.oai_sync = oai_sync

        synchronizer.created = 100
        db.session.commit()
        synchronizer.update_oai_sync("ok")

        res_oai_sync = OAISync.query.get(1)
        print(type(res_oai_sync.sync_end))
        assert res_oai_sync.rec_created == 100
        assert res_oai_sync.status == "ok"
        assert isinstance(res_oai_sync.sync_end, datetime)

    def test_update_oai_sync_2(self, load_entry_points, app, db, record_xml):
        synchronizer = current_oai_client.providers["uk"]._synchronizers["xoai"]
        provider = OAIProvider.query.filter_by(code="uk").one_or_none()
        if not provider:
            current_oai_client.create_providers()
        oai_sync = OAISync(provider_id=1)
        db.session.add(oai_sync)
        db.session.commit()
        synchronizer.oai_sync = oai_sync
        try:
            raise Exception("Test exception")
        except Exception:
            synchronizer.update_oai_sync("failed")

        res_oai_sync = OAISync.query.get(1)
        assert res_oai_sync.logs is not None

    def test_run(self, load_entry_points, app, db, record_xml):


        synchronizer = current_oai_client.providers["uk"]._synchronizers["xoai"]
        provider = OAIProvider.query.filter_by(code="uk").one_or_none()
        if not provider:
            current_oai_client.create_providers()
        print(synchronizer)
