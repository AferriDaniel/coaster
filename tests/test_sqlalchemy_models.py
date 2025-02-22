from datetime import datetime, timedelta
from time import sleep
import unittest
import uuid

from sqlalchemy import (
    Column,
    ForeignKey,
    Integer,
    Unicode,
    UnicodeText,
    UniqueConstraint,
    func,
    inspect,
)
from sqlalchemy.dialects import postgresql
from sqlalchemy.exc import IntegrityError, StatementError
from sqlalchemy.orm import relationship, synonym
from sqlalchemy.orm.exc import MultipleResultsFound

from flask import Flask
from werkzeug.routing import BuildError

from pytz import utc

from coaster.db import db
from coaster.sqlalchemy import (
    BaseIdNameMixin,
    BaseMixin,
    BaseNameMixin,
    BaseScopedIdMixin,
    BaseScopedIdNameMixin,
    BaseScopedNameMixin,
    JsonDict,
    UrlType,
    UuidMixin,
    UUIDType,
    add_primary_relationship,
    auto_init_default,
    failsafe_add,
)
from coaster.utils import uuid_to_base58, uuid_to_base64

from .test_auth import LoginManager

app1 = Flask(__name__)
app1.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite://'
app1.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app2 = Flask(__name__)
app2.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql:///coaster_test'
app2.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app1)
db.init_app(app2)
login_manager = LoginManager(app1)
LoginManager(app2)


# --- Models ------------------------------------------------------------------


class TimestampNaive(BaseMixin, db.Model):
    __tablename__ = 'timestamp_naive'
    __with_timezone__ = False


class TimestampAware(BaseMixin, db.Model):
    __tablename__ = 'timestamp_aware'
    __with_timezone__ = True


class Container(BaseMixin, db.Model):
    __tablename__ = 'container'
    name = Column(Unicode(80), nullable=True)
    title = Column(Unicode(80), nullable=True)

    content = Column(Unicode(250))


class UnnamedDocument(BaseMixin, db.Model):
    __tablename__ = 'unnamed_document'
    container_id = Column(Integer, ForeignKey('container.id'))
    container = relationship(Container)

    content = Column(Unicode(250))


class NamedDocument(BaseNameMixin, db.Model):
    __tablename__ = 'named_document'
    reserved_names = ['new']
    container_id = Column(Integer, ForeignKey('container.id'))
    container = relationship(Container)

    content = Column(Unicode(250))


class NamedDocumentBlank(BaseNameMixin, db.Model):
    __tablename__ = 'named_document_blank'
    __name_blank_allowed__ = True
    reserved_names = ['new']
    container_id = Column(Integer, ForeignKey('container.id'))
    container = relationship(Container)

    content = Column(Unicode(250))


class ScopedNamedDocument(BaseScopedNameMixin, db.Model):
    __tablename__ = 'scoped_named_document'
    reserved_names = ['new']
    container_id = Column(Integer, ForeignKey('container.id'))
    container = relationship(Container)
    parent = synonym('container')

    content = Column(Unicode(250))
    __table_args__ = (UniqueConstraint('container_id', 'name'),)


class IdNamedDocument(BaseIdNameMixin, db.Model):
    __tablename__ = 'id_named_document'
    container_id = Column(Integer, ForeignKey('container.id'))
    container = relationship(Container)

    content = Column(Unicode(250))


class ScopedIdDocument(BaseScopedIdMixin, db.Model):
    __tablename__ = 'scoped_id_document'
    container_id = Column(Integer, ForeignKey('container.id'))
    container = relationship(Container)
    parent = synonym('container')

    content = Column(Unicode(250))
    __table_args__ = (UniqueConstraint('container_id', 'url_id'),)


class ScopedIdNamedDocument(BaseScopedIdNameMixin, db.Model):
    __tablename__ = 'scoped_id_named_document'
    container_id = Column(Integer, ForeignKey('container.id'))
    container = relationship(Container)
    parent = synonym('container')

    content = Column(Unicode(250))
    __table_args__ = (UniqueConstraint('container_id', 'url_id'),)


class UnlimitedName(BaseNameMixin, db.Model):
    __tablename__ = 'unlimited_name'
    __name_length__ = __title_length__ = None

    @property
    def title_for_name(self):
        return "Custom1: " + self.title


class UnlimitedScopedName(BaseScopedNameMixin, db.Model):
    __tablename__ = 'unlimited_scoped_name'
    __name_length__ = __title_length__ = None
    container_id = Column(Integer, ForeignKey('container.id'))
    container = relationship(Container)
    parent = synonym('container')
    __table_args__ = (UniqueConstraint('container_id', 'name'),)

    @property
    def title_for_name(self):
        return "Custom2: " + self.title


class UnlimitedIdName(BaseIdNameMixin, db.Model):
    __tablename__ = 'unlimited_id_name'
    __name_length__ = __title_length__ = None

    @property
    def title_for_name(self):
        return "Custom3: " + self.title


class UnlimitedScopedIdName(BaseScopedIdNameMixin, db.Model):
    __tablename__ = 'unlimited_scoped_id_name'
    __name_length__ = __title_length__ = None
    container_id = Column(Integer, ForeignKey('container.id'))
    container = relationship(Container)
    parent = synonym('container')
    __table_args__ = (UniqueConstraint('container_id', 'url_id'),)

    @property
    def title_for_name(self):
        return "Custom4: " + self.title


class User(BaseMixin, db.Model):
    __tablename__ = 'user'
    username = Column(Unicode(80), nullable=False)


class MyData(db.Model):
    __tablename__ = 'my_data'
    id = Column(Integer, primary_key=True)  # noqa: A003
    data = Column(JsonDict)


class MyUrlModel(db.Model):
    __tablename__ = 'my_url'
    id = Column(Integer, primary_key=True)  # noqa: A003
    url = Column(UrlType)  # type: ignore[var-annotated]
    url_all_scheme = Column(UrlType(schemes=None))  # type: ignore[var-annotated]
    url_custom_scheme = Column(UrlType(schemes='ftp'))  # type: ignore[var-annotated]
    url_optional_scheme = Column(  # type: ignore[var-annotated]
        UrlType(optional_scheme=True)
    )
    url_optional_host = Column(  # type: ignore[var-annotated]
        UrlType(schemes=('mailto', 'file'), optional_host=True)
    )
    url_optional_scheme_host = Column(  # type: ignore[var-annotated]
        UrlType(optional_scheme=True, optional_host=True)
    )


class NonUuidKey(BaseMixin, db.Model):
    __tablename__ = 'non_uuid_key'
    __uuid_primary_key__ = False


class UuidKey(BaseMixin, db.Model):
    __tablename__ = 'uuid_key'
    __uuid_primary_key__ = True


class UuidKeyNoDefault(BaseMixin, db.Model):
    __tablename__ = 'uuid_key_no_default'
    __uuid_primary_key__ = True
    id = db.Column(UUIDType(binary=False), primary_key=True)  # noqa: A003


class UuidForeignKey1(BaseMixin, db.Model):
    __tablename__ = 'uuid_foreign_key1'
    __uuid_primary_key__ = False
    uuidkey_id = Column(None, ForeignKey('uuid_key.id'))  # type: ignore[call-overload]
    uuidkey = relationship(UuidKey)


class UuidForeignKey2(BaseMixin, db.Model):
    __tablename__ = 'uuid_foreign_key2'
    __uuid_primary_key__ = True
    uuidkey_id = Column(None, ForeignKey('uuid_key.id'))  # type: ignore[call-overload]
    uuidkey = relationship(UuidKey)


class UuidIdName(BaseIdNameMixin, db.Model):
    __tablename__ = 'uuid_id_name'
    __uuid_primary_key__ = True


class UuidIdNameMixin(UuidMixin, BaseIdNameMixin, db.Model):
    __tablename__ = 'uuid_id_name_mixin'
    __uuid_primary_key__ = True


class UuidIdNameSecondary(UuidMixin, BaseIdNameMixin, db.Model):
    __tablename__ = 'uuid_id_name_secondary'
    __uuid_primary_key__ = False


class NonUuidMixinKey(UuidMixin, BaseMixin, db.Model):
    __tablename__ = 'non_uuid_mixin_key'
    __uuid_primary_key__ = False


class UuidMixinKey(UuidMixin, BaseMixin, db.Model):
    __tablename__ = 'uuid_mixin_key'
    __uuid_primary_key__ = True


class ParentForPrimary(BaseMixin, db.Model):
    __tablename__ = 'parent_for_primary'


class ChildForPrimary(BaseMixin, db.Model):
    __tablename__ = 'child_for_primary'
    parent_for_primary_id = Column(  # type: ignore[call-overload]
        None, ForeignKey('parent_for_primary.id'), nullable=False
    )
    parent_for_primary = db.relationship(ParentForPrimary)
    parent = db.synonym('parent_for_primary')


add_primary_relationship(
    ParentForPrimary,
    'primary_child',
    ChildForPrimary,
    'parent',
    'parent_for_primary_id',
)

# Used for the tests below
parent_child_primary = db.Model.metadata.tables[
    'parent_for_primary_child_for_primary_primary'
]


class DefaultValue(BaseMixin, db.Model):
    __tablename__ = 'default_value'
    value = db.Column(db.Unicode(100), default='default')


auto_init_default(DefaultValue.value)


# --- Tests -------------------------------------------------------------------


class TestCoasterModels(unittest.TestCase):
    """SQLite tests"""

    app = app1

    def setUp(self):
        self.ctx = self.app.test_request_context()
        self.ctx.push()
        db.create_all()
        self.session = db.session

    def tearDown(self):
        self.session.rollback()
        db.drop_all()
        self.ctx.pop()

    def make_container(self):
        c = Container()
        self.session.add(c)
        return c

    def test_container(self):
        c = self.make_container()
        assert c.id is None
        self.session.commit()
        self.assertEqual(c.id, 1)

    def test_timestamp(self):
        now1 = self.session.query(func.utcnow()).scalar()
        # Start a new transaction so that NOW() returns a new value
        self.session.commit()
        # The db may not store microsecond precision, so sleep at least 1 second
        # to ensure adequate gap between operations
        sleep(1)
        c = self.make_container()
        self.session.commit()
        u = c.updated_at
        sleep(1)
        now2 = self.session.query(func.utcnow()).scalar()
        self.session.commit()
        # Convert timestamps to naive before testing because they may be mismatched:
        # 1. utcnow will have timezone in PostgreSQL, but not in SQLite
        # 2. columns will have timezone iff PostgreSQL and the model has __with_timezone__ = True
        self.assertNotEqual(
            now1.replace(tzinfo=None), c.created_at.replace(tzinfo=None)
        )
        assert now1.replace(tzinfo=None) < c.created_at.replace(tzinfo=None)
        assert now2.replace(tzinfo=None) > c.created_at.replace(tzinfo=None)
        sleep(1)
        c.content = "updated"
        self.session.commit()
        self.assertNotEqual(c.updated_at, u)
        assert c.updated_at.replace(tzinfo=None) > now2.replace(tzinfo=None)
        assert c.updated_at > c.created_at
        assert c.updated_at > u

    def test_unnamed(self):
        c = self.make_container()
        d = UnnamedDocument(content="hello", container=c)
        self.session.add(d)
        self.session.commit()
        self.assertEqual(c.id, 1)
        self.assertEqual(d.id, 1)

    def test_named(self):
        """Named documents have globally unique names."""
        c1 = self.make_container()
        d1 = NamedDocument(title="Hello", content="World", container=c1)
        self.session.add(d1)
        self.session.commit()
        self.assertEqual(d1.name, 'hello')
        self.assertEqual(NamedDocument.get('hello'), d1)

        c2 = self.make_container()
        d2 = NamedDocument(title="Hello", content="Again", container=c2)
        self.session.add(d2)
        self.session.commit()
        self.assertEqual(d2.name, 'hello2')

        # test insert in BaseNameMixin's upsert
        d3 = NamedDocument.upsert('hello3', title='hello3', content='hello3')
        self.session.commit()
        d3_persisted = NamedDocument.get('hello3')
        self.assertEqual(d3_persisted, d3)
        self.assertEqual(d3_persisted.content, 'hello3')

        # test update in BaseNameMixin's upsert
        d4 = NamedDocument.upsert('hello3', title='hello4', content='hello4')
        d4.make_name()
        self.session.commit()
        d4_persisted = NamedDocument.get('hello4')
        self.assertEqual(d4_persisted, d4)
        self.assertEqual(d4_persisted.content, 'hello4')

        with self.assertRaises(TypeError) as insert_error:
            NamedDocument.upsert(
                'invalid1', title='Invalid1', non_existent_field="I don't belong here."
            )
        self.assertEqual(TypeError, insert_error.expected)

        with self.assertRaises(TypeError) as update_error:
            NamedDocument.upsert('valid1', title='Valid1')
            self.session.commit()
            NamedDocument.upsert(
                'valid1', title='Invalid1', non_existent_field="I don't belong here."
            )
            self.session.commit()
        self.assertEqual(TypeError, update_error.expected)

    # TODO: Versions of this test are required for BaseNameMixin,
    # BaseScopedNameMixin, BaseIdNameMixin and BaseScopedIdNameMixin
    # since they replicate code without sharing it. Only BaseNameMixin
    # is tested here.
    def test_named_blank_disallowed(self):
        c1 = self.make_container()
        d1 = NamedDocument(title="Index", name="", container=c1)
        d1.name = (
            ""  # BaseNameMixin will always try to set a name. Explicitly blank it.
        )
        self.session.add(d1)
        self.assertRaises(IntegrityError, self.session.commit)

    def test_named_blank_allowed(self):
        c1 = self.make_container()
        d1 = NamedDocumentBlank(title="Index", name="", container=c1)
        d1.name = (
            ""  # BaseNameMixin will always try to set a name. Explicitly blank it.
        )
        self.session.add(d1)
        self.assertEqual(d1.name, "")

    def test_scoped_named(self):
        """Scoped named documents have names unique to their containers."""
        c1 = self.make_container()
        self.session.commit()
        d1 = ScopedNamedDocument(title="Hello", content="World", container=c1)
        u = User(username='foo')
        self.session.add(d1)
        self.session.commit()
        self.assertEqual(ScopedNamedDocument.get(c1, 'hello'), d1)
        self.assertEqual(d1.name, 'hello')
        self.assertEqual(d1.permissions(actor=u), set())
        self.assertEqual(d1.permissions(actor=u, inherited={'view'}), {'view'})

        d2 = ScopedNamedDocument(title="Hello", content="Again", container=c1)
        self.session.add(d2)
        self.session.commit()
        self.assertEqual(d2.name, 'hello2')

        c2 = self.make_container()
        self.session.commit()
        d3 = ScopedNamedDocument(title="Hello", content="Once More", container=c2)
        self.session.add(d3)
        self.session.commit()
        self.assertEqual(d3.name, 'hello')

        # test insert in BaseScopedNameMixin's upsert
        d4 = ScopedNamedDocument.upsert(
            c1, 'hello4', title='Hello 4', content='scoped named doc'
        )
        self.session.commit()
        d4_persisted = ScopedNamedDocument.get(c1, 'hello4')
        self.assertEqual(d4_persisted, d4)
        self.assertEqual(d4_persisted.content, 'scoped named doc')

        # test update in BaseScopedNameMixin's upsert
        d5 = ScopedNamedDocument.upsert(
            c1, 'hello4', container=c2, title='Hello5', content='scoped named doc'
        )
        d5.make_name()
        self.session.commit()
        d5_persisted = ScopedNamedDocument.get(c2, 'hello5')
        self.assertEqual(d5_persisted, d5)
        self.assertEqual(d5_persisted.content, 'scoped named doc')

        with self.assertRaises(TypeError) as insert_error:
            ScopedNamedDocument.upsert(
                c1,
                'invalid1',
                title='Invalid1',
                non_existent_field="I don't belong here.",
            )
        self.assertEqual(TypeError, insert_error.expected)

        ScopedNamedDocument.upsert(c1, 'valid1', title='Valid1')
        self.session.commit()
        with self.assertRaises(TypeError) as update_error:
            ScopedNamedDocument.upsert(
                c1,
                'valid1',
                title='Invalid1',
                non_existent_field="I don't belong here.",
            )
            self.session.commit()
        self.assertEqual(TypeError, update_error.expected)

    def test_scoped_named_short_title(self):
        """Test the short_title method of BaseScopedNameMixin."""
        c1 = self.make_container()
        self.session.commit()
        d1 = ScopedNamedDocument(title="Hello", content="World", container=c1)
        self.assertEqual(d1.short_title, "Hello")

        c1.title = "Container"
        d1.title = "Container Contained"
        self.assertEqual(d1.short_title, "Contained")

        d1.title = "Container: Contained"
        self.assertEqual(d1.short_title, "Contained")

        d1.title = "Container - Contained"
        self.assertEqual(d1.short_title, "Contained")

    def test_id_named(self):
        """Documents with a global id in the URL"""
        c1 = self.make_container()
        d1 = IdNamedDocument(title="Hello", content="World", container=c1)
        self.session.add(d1)
        self.session.commit()
        self.assertEqual(d1.url_name, '1-hello')

        d2 = IdNamedDocument(title="Hello", content="Again", container=c1)
        self.session.add(d2)
        self.session.commit()
        self.assertEqual(d2.url_name, '2-hello')

        c2 = self.make_container()
        d3 = IdNamedDocument(title="Hello", content="Once More", container=c2)
        self.session.add(d3)
        self.session.commit()
        self.assertEqual(d3.url_name, '3-hello')

    def test_scoped_id(self):
        """Documents with a container-specific id in the URL"""
        c1 = self.make_container()
        d1 = ScopedIdDocument(content="Hello", container=c1)
        u = User(username="foo")
        self.session.add(d1)
        self.session.commit()
        self.assertEqual(ScopedIdDocument.get(c1, d1.url_id), d1)
        self.assertEqual(d1.permissions(actor=u, inherited={'view'}), {'view'})
        self.assertEqual(d1.permissions(actor=u), set())

        d2 = ScopedIdDocument(content="New document", container=c1)
        self.session.add(d2)
        self.session.commit()
        self.assertEqual(d1.url_id, 1)
        self.assertEqual(d2.url_id, 2)

        c2 = self.make_container()
        d3 = ScopedIdDocument(content="Once More", container=c2)
        self.session.add(d3)
        self.session.commit()
        self.assertEqual(d3.url_id, 1)

        d4 = ScopedIdDocument(content="Third", container=c1)
        self.session.add(d4)
        self.session.commit()
        self.assertEqual(d4.url_id, 3)

    def test_scoped_id_named(self):
        """Documents with a container-specific id and name in the URL"""
        c1 = self.make_container()
        d1 = ScopedIdNamedDocument(title="Hello", content="World", container=c1)
        self.session.add(d1)
        self.session.commit()
        self.assertEqual(d1.url_name, '1-hello')
        self.assertEqual(
            d1.url_name, d1.url_id_name
        )  # url_name is now an alias for url_id_name
        self.assertEqual(ScopedIdNamedDocument.get(c1, d1.url_id), d1)

        d2 = ScopedIdNamedDocument(
            title="Hello again", content="New name", container=c1
        )
        self.session.add(d2)
        self.session.commit()
        self.assertEqual(d2.url_name, '2-hello-again')

        c2 = self.make_container()
        d3 = ScopedIdNamedDocument(title="Hello", content="Once More", container=c2)
        self.session.add(d3)
        self.session.commit()
        self.assertEqual(d3.url_name, '1-hello')

        d4 = ScopedIdNamedDocument(title="Hello", content="Third", container=c1)
        self.session.add(d4)
        self.session.commit()
        self.assertEqual(d4.url_name, '3-hello')

        # Queries work as well
        qd1 = ScopedIdNamedDocument.query.filter_by(
            container=c1, url_name=d1.url_name
        ).first()
        self.assertEqual(qd1, d1)
        qd2 = ScopedIdNamedDocument.query.filter_by(
            container=c1, url_id_name=d2.url_id_name
        ).first()
        self.assertEqual(qd2, d2)

    def test_scoped_id_without_parent(self):
        d1 = ScopedIdDocument(content="Hello")
        self.session.add(d1)
        self.assertRaises(IntegrityError, self.session.commit)
        self.session.rollback()
        d2 = ScopedIdDocument(content="Hello again")
        self.session.add(d2)
        self.assertRaises(IntegrityError, self.session.commit)

    def test_scoped_named_without_parent(self):
        d1 = ScopedNamedDocument(title="Hello", content="World")
        self.session.add(d1)
        self.assertRaises(IntegrityError, self.session.commit)
        self.session.rollback()
        d2 = ScopedIdNamedDocument(title="Hello", content="World")
        self.session.add(d2)
        self.assertRaises(IntegrityError, self.session.commit)

    def test_reserved_name(self):
        c = self.make_container()
        self.session.commit()
        d1 = NamedDocument(container=c, title="New")
        # 'new' is reserved in the class definition. Also reserve new2 here and
        # confirm we get new3 for the name
        d1.make_name(reserved=['new2'])
        self.assertEqual(d1.name, 'new3')
        d2 = ScopedNamedDocument(container=c, title="New")
        # 'new' is reserved in the class definition. Also reserve new2 here and
        # confirm we get new3 for the name
        d2.make_name(reserved=['new2'])
        self.assertEqual(d2.name, 'new3')

        # Now test again after adding to session. Results should be identical
        self.session.add(d1)
        self.session.add(d2)
        self.session.commit()

        d1.make_name(reserved=['new2'])
        self.assertEqual(d1.name, 'new3')
        d2.make_name(reserved=['new2'])
        self.assertEqual(d2.name, 'new3')

    def test_named_auto(self):
        """
        The name attribute is auto-generated on database insertion
        """
        c1 = self.make_container()
        d1 = NamedDocument(container=c1)
        d2 = ScopedNamedDocument(container=c1)
        d3 = IdNamedDocument(container=c1)
        d4 = ScopedIdNamedDocument(container=c1)
        d1.title = "Auto name"
        d2.title = "Auto name"
        d3.title = "Auto name"
        d4.title = "Auto name"
        self.session.add_all([d1, d2, d3, d4])
        assert d1.name is None
        assert d2.name is None
        assert d3.name is None
        assert d4.name is None
        self.session.commit()
        assert d1.name == 'auto-name'
        assert d2.name == 'auto-name'
        assert d3.name == 'auto-name'
        assert d4.name == 'auto-name'

    def test_scoped_id_auto(self):
        """
        The url_id attribute is auto-generated on database insertion
        """
        c1 = self.make_container()
        d1 = ScopedIdDocument()
        d1.container = c1
        d2 = ScopedIdNamedDocument()
        d2.container = c1
        d2.title = "Auto name"
        self.session.add_all([d1, d2])
        assert d1.url_id is None
        assert d2.url_id is None
        self.session.commit()
        assert d1.url_id == 1
        assert d2.url_id == 1

    def test_unlimited_name_title(self):
        """The four name mixins will switch from Unicode to UnicodeText if length is None"""
        for model in (
            NamedDocument,
            ScopedNamedDocument,
            IdNamedDocument,
            ScopedIdNamedDocument,
        ):
            assert isinstance(inspect(model.name).type, Unicode)
            assert isinstance(inspect(model.title).type, Unicode)

        for model in (
            UnlimitedName,
            UnlimitedScopedName,
            UnlimitedIdName,
            UnlimitedScopedIdName,
        ):
            assert isinstance(inspect(model.name).type, UnicodeText)
            assert isinstance(inspect(model.title).type, UnicodeText)

    def test_title_for_name(self):
        """Models can customise how their names are generated"""
        c1 = self.make_container()
        self.session.flush()  # Container needs an id for scoped names to be validated
        d1 = UnlimitedName(title="Document 1")
        d2 = UnlimitedScopedName(title="Document 2", parent=c1)
        d3 = UnlimitedIdName(title="Document 3")
        d4 = UnlimitedScopedIdName(title="Document 4", parent=c1)
        self.session.add_all([d1, d2, d3, d4])
        self.session.commit()

        assert d1.title == "Document 1"
        assert d1.title_for_name == "Custom1: Document 1"
        assert d1.name == 'custom1-document-1'

        assert d2.title == "Document 2"
        assert d2.title_for_name == "Custom2: Document 2"
        assert d2.name == 'custom2-document-2'

        assert d3.title == "Document 3"
        assert d3.title_for_name == "Custom3: Document 3"
        assert d3.name == 'custom3-document-3'

        assert d4.title == "Document 4"
        assert d4.title_for_name == "Custom4: Document 4"
        assert d4.name == 'custom4-document-4'

    def test_has_timestamps(self):
        # Confirm that a model with multiple base classes between it and
        # TimestampMixin still has created_at and updated_at
        c = self.make_container()
        d = ScopedIdNamedDocument(title="Hello", content="World", container=c)
        self.session.add(d)
        self.session.commit()
        sleep(1)
        assert d.created_at is not None
        assert d.updated_at is not None
        updated_at = d.updated_at
        assert d.updated_at - d.created_at < timedelta(seconds=1)
        assert isinstance(d.created_at, datetime)
        assert isinstance(d.updated_at, datetime)
        d.title = "Updated hello"
        self.session.commit()
        assert d.updated_at > updated_at

    def test_url_for_fail(self):
        d = UnnamedDocument(content="hello")
        with self.assertRaises(BuildError):
            d.url_for()

    def test_jsondict(self):
        m1 = MyData(data={'value': 'foo'})
        self.session.add(m1)
        self.session.commit()
        # Test for __setitem__
        m1.data['value'] = 'bar'
        self.assertEqual(m1.data['value'], 'bar')
        del m1.data['value']
        self.assertEqual(m1.data, {})
        self.assertRaises(ValueError, MyData, data='NonDict')

    def test_urltype(self):
        m1 = MyUrlModel(
            url="https://example.com",
            url_all_scheme="magnet://example.com",
            url_custom_scheme="ftp://example.com",
        )
        self.session.add(m1)
        self.session.commit()
        assert str(m1.url) == "https://example.com"
        assert str(m1.url_all_scheme) == "magnet://example.com"
        assert str(m1.url_custom_scheme) == "ftp://example.com"

    def test_urltype_invalid(self):
        with self.assertRaises(StatementError):
            m1 = MyUrlModel(url="example.com")
            self.session.add(m1)
            self.session.commit()

    def test_urltype_invalid_without_scheme(self):
        with self.assertRaises(StatementError):
            m2 = MyUrlModel(url="//example.com")
            self.session.add(m2)
            self.session.commit()

    def test_urltype_invalid_without_host(self):
        with self.assertRaises(StatementError):
            m2 = MyUrlModel(url="https:///test")
            self.session.add(m2)
            self.session.commit()

    def test_urltype_empty(self):
        m1 = MyUrlModel(url="", url_all_scheme="", url_custom_scheme="")
        self.session.add(m1)
        self.session.commit()
        assert str(m1.url) == ""
        assert str(m1.url_all_scheme) == ""
        assert str(m1.url_custom_scheme) == ""

    def test_urltype_invalid_scheme_default(self):
        with self.assertRaises(StatementError):
            m1 = MyUrlModel(url="magnet://example.com")
            self.session.add(m1)
            self.session.commit()

    def test_urltype_invalid_scheme_custom(self):
        with self.assertRaises(StatementError):
            m1 = MyUrlModel(url_custom_scheme="magnet://example.com")
            self.session.add(m1)
            self.session.commit()

    def test_urltype_optional_scheme(self):
        m1 = MyUrlModel(url_optional_scheme="//example.com/test")
        self.session.add(m1)
        self.session.commit()

        with self.assertRaises(StatementError):
            m2 = MyUrlModel(url_optional_scheme="example.com/test")
            self.session.add(m2)
            self.session.commit()

    def test_urltype_optional_host(self):
        m1 = MyUrlModel(url_optional_host="file:///test/path")
        self.session.add(m1)
        self.session.commit()

        with self.assertRaises(StatementError):
            m2 = MyUrlModel(url_optional_host="https:///test")
            self.session.add(m2)
            self.session.commit()

    def test_urltype_optional_scheme_host(self):
        m1 = MyUrlModel(url_optional_scheme_host='/test/path')
        self.session.add(m1)
        self.session.commit()

    def test_query(self):
        c1 = Container(name='c1')
        self.session.add(c1)
        c2 = Container(name='c2')
        self.session.add(c2)
        self.session.commit()

        self.assertEqual(Container.query.filter_by(name='c1').one_or_none(), c1)
        assert Container.query.filter_by(name='c3').one_or_none() is None
        self.assertRaises(MultipleResultsFound, Container.query.one_or_none)

    def test_failsafe_add(self):
        """
        failsafe_add gracefully handles IntegrityError from dupe entries
        """
        d1 = NamedDocument(name='add_and_commit_test', title="Test")
        d1a = failsafe_add(self.session, d1, name='add_and_commit_test')
        assert d1a is d1  # We got back what we created, so the commit succeeded

        d2 = NamedDocument(name='add_and_commit_test', title="Test")
        d2a = failsafe_add(self.session, d2, name='add_and_commit_test')
        assert d2a is not d2  # This time we got back d1 instead of d2
        assert d2a is d1

    def test_failsafe_add_existing(self):
        """
        failsafe_add doesn't fail if the item is already in the session
        """
        d1 = NamedDocument(name='add_and_commit_test', title="Test")
        d1a = failsafe_add(self.session, d1, name='add_and_commit_test')
        assert d1a is d1  # We got back what we created, so the commit succeeded

        d2 = NamedDocument(name='add_and_commit_test', title="Test")
        self.session.add(d2)  # Add to session before going to failsafe_add
        d2a = failsafe_add(self.session, d2, name='add_and_commit_test')
        assert d2a is not d2  # This time we got back d1 instead of d2
        assert d2a is d1

    def test_failsafe_add_fail(self):
        """
        failsafe_add passes through errors occuring from bad data
        """
        d1 = NamedDocument(name='missing_title')
        self.assertRaises(
            IntegrityError, failsafe_add, self.session, d1, name='missing_title'
        )

    def test_failsafe_add_silent_fail(self):
        """
        failsafe_add does not raise IntegrityError with bad data
        when no filters are provided
        """
        d1 = NamedDocument(name='missing_title')
        self.assertIsNone(failsafe_add(self.session, d1))

    def test_uuid_key(self):
        """
        Models with a UUID primary key work as expected
        """
        u1 = UuidKey()
        u2 = UuidKey()
        self.session.add(u1)
        self.session.add(u2)
        self.session.commit()
        assert isinstance(u1.id, uuid.UUID)
        assert isinstance(u2.id, uuid.UUID)
        self.assertNotEqual(u1.id, u2.id)

        fk1 = UuidForeignKey1(uuidkey=u1)
        fk2 = UuidForeignKey2(uuidkey=u2)
        db.session.add(fk1)
        db.session.add(fk2)
        db.session.commit()

        self.assertIs(fk1.uuidkey, u1)
        self.assertIs(fk2.uuidkey, u2)
        assert isinstance(fk1.uuidkey_id, uuid.UUID)
        assert isinstance(fk2.uuidkey_id, uuid.UUID)
        self.assertEqual(fk1.uuidkey_id, u1.id)
        self.assertEqual(fk2.uuidkey_id, u2.id)

    def test_uuid_url_id(self):
        """
        IdMixin provides a url_id that renders as a string of either the
        integer primary key or the UUID primary key. In addition, UuidMixin
        provides a uuid_hex that always renders a UUID against either the
        id or uuid columns.
        """
        # TODO: This test is a little muddled because UuidMixin renamed
        # its url_id property (which overrode IdMixin's url_id) to uuid_hex.
        # This test needs to be broken down into separate tests for each of
        # these properties.
        u1 = NonUuidKey()
        u2 = UuidKey()
        u3 = NonUuidMixinKey()
        u4 = UuidMixinKey()
        db.session.add_all([u1, u2, u3, u4])
        db.session.commit()

        # Regular IdMixin ids
        i1 = u1.id
        i2 = u2.id
        # UUID keys from UuidMixin
        i3 = u3.uuid
        i4 = u4.uuid

        self.assertEqual(u1.url_id, str(i1))

        self.assertIsInstance(i2, uuid.UUID)
        self.assertEqual(u2.url_id, i2.hex)
        self.assertEqual(len(u2.url_id), 32)  # This is a 32-byte hex representation
        assert '-' not in u2.url_id  # Without dashes

        self.assertIsInstance(i3, uuid.UUID)
        self.assertEqual(u3.uuid_hex, i3.hex)
        self.assertEqual(len(u3.uuid_hex), 32)  # This is a 32-byte hex representation
        assert '-' not in u3.uuid_hex  # Without dashes

        self.assertIsInstance(i4, uuid.UUID)
        self.assertEqual(u4.uuid_hex, i4.hex)
        self.assertEqual(len(u4.uuid_hex), 32)  # This is a 32-byte hex representation
        assert '-' not in u4.uuid_hex  # Without dashes

        # Querying against `url_id` redirects the query to
        # `id` (IdMixin) or `uuid` (UuidMixin).

        # With integer primary keys, `url_id` is simply a proxy for `id`
        self.assertEqual(
            str(
                (NonUuidKey.url_id == 1).compile(
                    dialect=postgresql.dialect(), compile_kwargs={'literal_binds': True}
                )
            ),
            "non_uuid_key.id = 1",
        )
        # We don't check the data type here, leaving that to the engine
        self.assertEqual(
            str(
                (NonUuidKey.url_id == '1').compile(
                    dialect=postgresql.dialect(), compile_kwargs={'literal_binds': True}
                )
            ),
            "non_uuid_key.id = '1'",
        )

        # With UUID primary keys, `url_id` casts the value into a UUID
        # and then queries against `id`

        # Note that `literal_binds` here doesn't know how to render UUIDs if
        # no engine is specified, and so casts them into a string. We test this
        # with multiple renderings.

        # Hex UUID
        self.assertEqual(
            str(
                (UuidKey.url_id == '74d588574a7611e78c27c38403d0935c').compile(
                    dialect=postgresql.dialect(), compile_kwargs={'literal_binds': True}
                )
            ),
            "uuid_key.id = '74d58857-4a76-11e7-8c27-c38403d0935c'",
        )
        # Hex UUID with !=
        self.assertEqual(
            str(
                (UuidKey.url_id != '74d588574a7611e78c27c38403d0935c').compile(
                    dialect=postgresql.dialect(), compile_kwargs={'literal_binds': True}
                )
            ),
            "uuid_key.id != '74d58857-4a76-11e7-8c27-c38403d0935c'",
        )
        # Hex UUID with dashes
        self.assertEqual(
            str(
                (UuidKey.url_id == '74d58857-4a76-11e7-8c27-c38403d0935c').compile(
                    dialect=postgresql.dialect(), compile_kwargs={'literal_binds': True}
                )
            ),
            "uuid_key.id = '74d58857-4a76-11e7-8c27-c38403d0935c'",
        )
        # UUID object
        self.assertEqual(
            str(
                (
                    UuidKey.url_id == uuid.UUID('74d58857-4a76-11e7-8c27-c38403d0935c')
                ).compile(
                    dialect=postgresql.dialect(), compile_kwargs={'literal_binds': True}
                )
            ),
            "uuid_key.id = '74d58857-4a76-11e7-8c27-c38403d0935c'",
        )
        # IN clause with mixed inputs, including an invalid input
        self.assertEqual(
            str(
                (
                    UuidKey.url_id.in_(
                        [
                            '74d588574a7611e78c27c38403d0935c',
                            uuid.UUID('74d58857-4a76-11e7-8c27-c38403d0935c'),
                            'garbage!',
                        ]
                    )
                ).compile(
                    dialect=postgresql.dialect(), compile_kwargs={'literal_binds': True}
                )
            ),
            "uuid_key.id IN ('74d58857-4a76-11e7-8c27-c38403d0935c', '74d58857-4a76-11e7-8c27-c38403d0935c')",
        )

        # None value
        self.assertEqual(
            str(
                (UuidKey.url_id == None).compile(  # noqa: E711
                    dialect=postgresql.dialect(), compile_kwargs={'literal_binds': True}
                )
            ),
            "uuid_key.id IS NULL",
        )
        self.assertEqual(
            str(
                (NonUuidKey.url_id.is_(None)).compile(
                    dialect=postgresql.dialect(), compile_kwargs={'literal_binds': True}
                )
            ),
            "non_uuid_key.id IS NULL",
        )
        self.assertEqual(
            str(
                (NonUuidMixinKey.uuid_hex == None).compile(  # noqa: E711
                    dialect=postgresql.dialect(), compile_kwargs={'literal_binds': True}
                )
            ),
            "non_uuid_mixin_key.uuid IS NULL",
        )

        # Query returns False (or True) if given an invalid value
        assert bool(UuidKey.url_id == 'garbage!') is False
        assert bool(UuidKey.url_id != 'garbage!') is True
        assert bool(NonUuidMixinKey.url_id == 'garbage!') is False
        assert bool(NonUuidMixinKey.url_id != 'garbage!') is True
        assert bool(UuidMixinKey.url_id == 'garbage!') is False
        assert bool(UuidMixinKey.url_id != 'garbage!') is True

        # Repeat against UuidMixin classes (with only hex keys for brevity)
        self.assertEqual(
            str(
                (
                    NonUuidMixinKey.uuid_hex == '74d588574a7611e78c27c38403d0935c'
                ).compile(
                    dialect=postgresql.dialect(), compile_kwargs={'literal_binds': True}
                )
            ),
            "non_uuid_mixin_key.uuid = '74d58857-4a76-11e7-8c27-c38403d0935c'",
        )
        self.assertEqual(
            str(
                (UuidMixinKey.uuid_hex == '74d588574a7611e78c27c38403d0935c').compile(
                    dialect=postgresql.dialect(), compile_kwargs={'literal_binds': True}
                )
            ),
            "uuid_mixin_key.id = '74d58857-4a76-11e7-8c27-c38403d0935c'",
        )

        # Running a database query with url_id works as expected.
        # This test should pass on both SQLite and PostgreSQL
        qu1 = NonUuidKey.query.filter_by(url_id=u1.url_id).first()
        self.assertEqual(u1, qu1)
        qu2 = UuidKey.query.filter_by(url_id=u2.url_id).first()
        self.assertEqual(u2, qu2)
        qu3 = NonUuidMixinKey.query.filter_by(url_id=u3.url_id).first()
        self.assertEqual(u3, qu3)
        qu4 = UuidMixinKey.query.filter_by(url_id=u4.url_id).first()
        self.assertEqual(u4, qu4)

    def test_uuid_buid_uuid_b58(self):
        """
        UuidMixin provides uuid_b64 (also as buid) and uuid_b58
        """
        u1 = NonUuidMixinKey()
        u2 = UuidMixinKey()
        db.session.add_all([u1, u2])
        db.session.commit()

        # The `uuid` column contains a UUID
        self.assertIsInstance(u1.uuid, uuid.UUID)
        self.assertIsInstance(u2.uuid, uuid.UUID)

        # Test readbility of `buid` attribute
        self.assertEqual(u1.buid, uuid_to_base64(u1.uuid))
        self.assertEqual(len(u1.buid), 22)  # This is a 22-char B64 representation
        self.assertEqual(u2.buid, uuid_to_base64(u2.uuid))
        self.assertEqual(len(u2.buid), 22)  # This is a 22-char B64 representation

        # Test readbility of `uuid_b58` attribute
        self.assertEqual(u1.uuid_b58, uuid_to_base58(u1.uuid))
        self.assertIn(len(u1.uuid_b58), (21, 22))  # 21 or 22-char B58 representation
        self.assertEqual(u2.uuid_b58, uuid_to_base58(u2.uuid))
        self.assertIn(len(u2.uuid_b58), (21, 22))  # 21 or 22-char B58 representation

        # SQL queries against `buid` and `uuid_b58` cast the value into a UUID
        # and then query against `id` or ``uuid``

        # Note that `literal_binds` here doesn't know how to render UUIDs if
        # no engine is specified, and so casts them into a string

        # UuidMixin with integer primary key queries against the `uuid` column
        self.assertEqual(
            str(
                (NonUuidMixinKey.buid == 'dNWIV0p2EeeMJ8OEA9CTXA').compile(
                    dialect=postgresql.dialect(), compile_kwargs={'literal_binds': True}
                )
            ),
            "non_uuid_mixin_key.uuid = '74d58857-4a76-11e7-8c27-c38403d0935c'",
        )

        # UuidMixin with UUID primary key queries against the `id` column
        self.assertEqual(
            str(
                (UuidMixinKey.buid == 'dNWIV0p2EeeMJ8OEA9CTXA').compile(
                    dialect=postgresql.dialect(), compile_kwargs={'literal_binds': True}
                )
            ),
            "uuid_mixin_key.id = '74d58857-4a76-11e7-8c27-c38403d0935c'",
        )

        # Repeat for `uuid_b58`
        self.assertEqual(
            str(
                (NonUuidMixinKey.uuid_b58 == 'FRn1p6EnzbhydnssMnHqFZ').compile(
                    dialect=postgresql.dialect(), compile_kwargs={'literal_binds': True}
                )
            ),
            "non_uuid_mixin_key.uuid = '74d58857-4a76-11e7-8c27-c38403d0935c'",
        )

        # UuidMixin with UUID primary key queries against the `id` column
        self.assertEqual(
            str(
                (UuidMixinKey.uuid_b58 == 'FRn1p6EnzbhydnssMnHqFZ').compile(
                    dialect=postgresql.dialect(), compile_kwargs={'literal_binds': True}
                )
            ),
            "uuid_mixin_key.id = '74d58857-4a76-11e7-8c27-c38403d0935c'",
        )

        # All queries work for None values as well
        self.assertEqual(
            str(
                (NonUuidMixinKey.buid == None).compile(  # noqa: E711
                    dialect=postgresql.dialect(), compile_kwargs={'literal_binds': True}
                )
            ),
            "non_uuid_mixin_key.uuid IS NULL",
        )
        self.assertEqual(
            str(
                (UuidMixinKey.buid == None).compile(  # noqa: E711
                    dialect=postgresql.dialect(), compile_kwargs={'literal_binds': True}
                )
            ),
            "uuid_mixin_key.id IS NULL",
        )
        self.assertEqual(
            str(
                (NonUuidMixinKey.uuid_b58 == None).compile(  # noqa: E711
                    dialect=postgresql.dialect(), compile_kwargs={'literal_binds': True}
                )
            ),
            "non_uuid_mixin_key.uuid IS NULL",
        )
        self.assertEqual(
            str(
                (UuidMixinKey.uuid_b58 == None).compile(  # noqa: E711
                    dialect=postgresql.dialect(), compile_kwargs={'literal_binds': True}
                )
            ),
            "uuid_mixin_key.id IS NULL",
        )

        # Query returns False (or True) if given an invalid value
        assert bool(NonUuidMixinKey.buid == 'garbage!') is False
        assert bool(NonUuidMixinKey.buid != 'garbage!') is True
        assert bool(NonUuidMixinKey.uuid_b58 == 'garbage!') is False
        assert bool(NonUuidMixinKey.uuid_b58 != 'garbage!') is True
        assert bool(UuidMixinKey.buid == 'garbage!') is False
        assert bool(UuidMixinKey.buid != 'garbage!') is True
        assert bool(UuidMixinKey.uuid_b58 == 'garbage!') is False
        assert bool(UuidMixinKey.uuid_b58 != 'garbage!') is True

    def test_uuid_url_id_name(self):
        """
        BaseIdNameMixin models with UUID primary or secondary keys should
        generate properly formatted url_id, url_id_name and url_name_uuid_b58.
        The url_id_name and url_name_uuid_b58 fields should be queryable as well.
        """
        u1 = UuidIdName(
            id=uuid.UUID('74d58857-4a76-11e7-8c27-c38403d0935c'),
            name='test',
            title='Test',
        )
        u2 = UuidIdNameMixin(
            id=uuid.UUID('74d58857-4a76-11e7-8c27-c38403d0935c'),
            name='test',
            title='Test',
        )
        u3 = UuidIdNameSecondary(
            uuid=uuid.UUID('74d58857-4a76-11e7-8c27-c38403d0935c'),
            name='test',
            title='Test',
        )
        db.session.add_all([u1, u2, u3])
        db.session.commit()

        self.assertEqual(u1.url_id, '74d588574a7611e78c27c38403d0935c')
        self.assertEqual(u1.url_id_name, '74d588574a7611e78c27c38403d0935c-test')
        # No uuid_b58 without UuidMixin
        with self.assertRaises(AttributeError):
            self.assertEqual(u1.url_name_uuid_b58, 'test-FRn1p6EnzbhydnssMnHqFZ')
        self.assertEqual(u2.uuid_hex, '74d588574a7611e78c27c38403d0935c')
        self.assertEqual(u2.url_id_name, '74d588574a7611e78c27c38403d0935c-test')
        self.assertEqual(u2.url_name_uuid_b58, 'test-FRn1p6EnzbhydnssMnHqFZ')
        self.assertEqual(u3.uuid_hex, '74d588574a7611e78c27c38403d0935c')
        # url_id_name in BaseIdNameMixin uses the id column, not the uuid column
        self.assertEqual(u3.url_id_name, '1-test')
        self.assertEqual(u3.url_name_uuid_b58, 'test-FRn1p6EnzbhydnssMnHqFZ')

        # url_name is legacy
        self.assertEqual(u1.url_id_name, u1.url_name)
        self.assertEqual(u2.url_id_name, u2.url_name)
        self.assertEqual(u3.url_id_name, u3.url_name)

        qu1 = UuidIdName.query.filter_by(url_id_name=u1.url_id_name).first()
        self.assertEqual(qu1, u1)
        qu2 = UuidIdNameMixin.query.filter_by(url_id_name=u2.url_id_name).first()
        self.assertEqual(qu2, u2)
        qu3 = UuidIdNameSecondary.query.filter_by(url_id_name=u3.url_id_name).first()
        self.assertEqual(qu3, u3)

        q58u2 = UuidIdNameMixin.query.filter_by(
            url_name_uuid_b58=u2.url_name_uuid_b58
        ).first()
        self.assertEqual(q58u2, u2)
        q58u3 = UuidIdNameSecondary.query.filter_by(
            url_name_uuid_b58=u3.url_name_uuid_b58
        ).first()
        self.assertEqual(q58u3, u3)

    def test_uuid_default(self):
        """
        Models with a UUID primary or secondary key have a default value before
        adding to session
        """
        uuid_no = NonUuidKey()
        uuid_yes = UuidKey()
        uuid_no_default = UuidKeyNoDefault()
        uuidm_no = NonUuidMixinKey()
        uuidm_yes = UuidMixinKey()
        # Non-UUID primary keys are not automatically generated
        u1 = uuid_no.id
        self.assertIsNone(u1)
        # However, UUID keys are generated even before adding to session
        u2 = uuid_yes.id
        self.assertIsInstance(u2, uuid.UUID)
        # Once generated, the key remains stable
        u3 = uuid_yes.id
        self.assertEqual(u2, u3)
        # A UUID primary key with a custom column with no default doesn't break
        # the default generator
        u4 = uuid_no_default.id
        self.assertIsNone(u4)

        # UuidMixin works likewise
        um1 = uuidm_no.uuid
        self.assertIsInstance(um1, uuid.UUID)
        um2 = uuidm_yes.uuid  # This should generate uuidm_yes.id
        self.assertIsInstance(um2, uuid.UUID)
        self.assertEqual(uuidm_yes.id, uuidm_yes.uuid)

    def test_parent_child_primary(self):
        """
        Test parents with multiple children and a primary child
        """
        parent1 = ParentForPrimary()
        parent2 = ParentForPrimary()
        child1a = ChildForPrimary(parent=parent1)
        child1b = ChildForPrimary(parent=parent1)
        child2a = ChildForPrimary(parent=parent2)
        child2b = ChildForPrimary(parent=parent2)

        self.session.add_all([parent1, parent2, child1a, child1b, child2a, child2b])
        self.session.commit()

        self.assertIsNone(parent1.primary_child)
        self.assertIsNone(parent2.primary_child)

        self.assertEqual(
            self.session.query(func.count()).select_from(parent_child_primary).scalar(),
            0,
        )

        parent1.primary_child = child1a
        parent2.primary_child = child2a

        self.session.commit()

        # The change has been committed to the database
        self.assertEqual(
            self.session.query(func.count()).select_from(parent_child_primary).scalar(),
            2,
        )
        qparent1 = ParentForPrimary.query.get(parent1.id)
        qparent2 = ParentForPrimary.query.get(parent2.id)

        self.assertEqual(qparent1.primary_child, child1a)
        self.assertEqual(qparent2.primary_child, child2a)

        # # A parent can't have a default that is another's child
        with self.assertRaises(ValueError):
            parent1.primary_child = child2b

        # The default hasn't changed despite the validation error
        self.assertEqual(parent1.primary_child, child1a)

        # Unsetting the default removes the relationship row,
        # but does not remove the child instance from the db
        parent1.primary_child = None
        self.session.commit()
        self.assertEqual(
            self.session.query(func.count()).select_from(parent_child_primary).scalar(),
            1,
        )
        self.assertIsNotNone(ChildForPrimary.query.get(child1a.id))

        # Deleting a child also removes the corresponding relationship row
        # but not the parent
        self.session.delete(child2a)
        self.session.commit()
        self.assertEqual(
            self.session.query(func.count()).select_from(parent_child_primary).scalar(),
            0,
        )
        self.assertEqual(ParentForPrimary.query.count(), 2)

    def test_auto_init_default(self):
        """
        Calling ``auto_init_default`` on a column makes it load defaults automatically
        """
        d1 = DefaultValue()
        d2 = DefaultValue(value='not-default')
        d3 = DefaultValue()
        d4 = DefaultValue(value='not-default')

        self.assertEqual(d1.value, 'default')
        self.assertEqual(d1.value, 'default')  # Also works on second access
        self.assertEqual(d2.value, 'not-default')
        self.assertEqual(d3.value, 'default')
        self.assertEqual(d4.value, 'not-default')

        d3.value = 'changed'
        d4.value = 'changed'

        self.assertEqual(d3.value, 'changed')
        self.assertEqual(d4.value, 'changed')

        db.session.add_all([d1, d2, d3, d4])
        db.session.commit()

        for d in DefaultValue.query.all():
            if d.id == d1.id:
                self.assertEqual(d.value, 'default')
            elif d.id == d2.id:
                self.assertEqual(d.value, 'not-default')
            elif d.id in (d3.id, d4.id):
                self.assertEqual(d.value, 'changed')


class TestCoasterModelsPG(TestCoasterModels):
    """PostgreSQL tests"""

    app = app2

    def test_parent_child_primary_sql_validator(self):
        parent1 = ParentForPrimary()
        parent2 = ParentForPrimary()
        child1a = ChildForPrimary(parent=parent1)
        child1b = ChildForPrimary(parent=parent1)
        child2a = ChildForPrimary(parent=parent2)
        child2b = ChildForPrimary(parent=parent2)

        parent1.primary_child = child1a

        self.session.add_all([parent1, parent2, child1a, child1b, child2a, child2b])
        self.session.commit()

        # The change has been committed to the database
        self.assertEqual(
            self.session.query(func.count()).select_from(parent_child_primary).scalar(),
            1,
        )
        # Attempting a direct write to the db works for valid children and fails for invalid children
        self.session.execute(
            parent_child_primary.update()
            .where(parent_child_primary.c.parent_for_primary_id == parent1.id)
            .values({'child_for_primary_id': child1b.id})
        )
        with self.assertRaises(IntegrityError):
            self.session.execute(
                parent_child_primary.update()
                .where(parent_child_primary.c.parent_for_primary_id == parent1.id)
                .values({'child_for_primary_id': child2a.id})
            )

    def test_timestamp_naive_is_naive(self):
        row = TimestampNaive()
        self.session.add(row)
        self.session.commit()

        assert row.created_at is not None
        assert row.created_at.tzinfo is None
        assert row.updated_at is not None
        assert row.updated_at.tzinfo is None

    def test_timestamp_aware_is_aware(self):
        row = TimestampAware()
        self.session.add(row)
        self.session.commit()

        assert row.created_at is not None
        assert row.created_at.tzinfo is not None
        assert row.created_at.astimezone(utc).utcoffset() == timedelta(0)
        assert row.updated_at is not None
        assert row.updated_at.tzinfo is not None
        assert row.updated_at.astimezone(utc).utcoffset() == timedelta(0)
