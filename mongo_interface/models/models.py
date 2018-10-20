from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, BigInteger, Numeric, String, DateTime, Boolean
from sqlalchemy.dialects import postgresql
from sqlalchemy import ForeignKey, Sequence
from sqlalchemy.orm import relationship
from dictalchemy import DictableModel

from mongo_interface.util.json_date_manipulation import localtz_now

Base = declarative_base(cls=DictableModel)


class Certificate(Base):
    __tablename__ = 'certificate'

    certificate_id_seq = Sequence('certificate_id_seq', metadata=Base.metadata)
    ID = Column('id', Integer, certificate_id_seq, server_default=certificate_id_seq.next_value(), primary_key=True)

    certificate_signer_chain_id = Column(Integer, ForeignKey('certificate_signer_chain.id'), nullable=True)
    trusted_device_id = Column(Integer, ForeignKey('trusted_device.id'), nullable=True)
    certificate_thumbprint = Column(String, nullable=False)
    public_key_thumbprint = Column(String, nullable=False)
    issuer_public_key_thumbprint = Column(String, nullable=False)
    certificate_serial_number = Column(Numeric, nullable=False)
    signature_algorithm = Column(String, nullable=False)
    subject_name = Column(String, nullable=False)
    issuer_name = Column(String, nullable=False)
    not_valid_before = Column(DateTime(timezone=True), nullable=False)
    not_valid_after = Column(DateTime(timezone=True), nullable=False)
    pem = Column(String, nullable=False)
    role_set = Column(postgresql.ARRAY(String, zero_indexes=True, as_tuple=False, dimensions=1), nullable=False)
    device_make = Column(String, nullable=False)
    device_model = Column(String, nullable=False)
    device_serial = Column(String, nullable=False)
    device_type = Column(String, nullable=False)
    is_blacklisted = Column(Boolean, nullable=False)
    created = Column(DateTime(timezone=True), default=localtz_now)
    modified = Column(DateTime(timezone=True), default=localtz_now, onupdate=localtz_now)

    signer_chain = relationship("CertificateSignerChain", foreign_keys=[certificate_signer_chain_id], back_populates="certificates")
    trusted_device = relationship("TrustedDevice", foreign_keys=[trusted_device_id], back_populates="certificates")


class TrustedDevice(Base):
    __tablename__ = 'trusted_device'

    trusted_device_id_seq = Sequence('trusted_device_id_seq', metadata=Base.metadata)
    ID = Column('id', Integer, trusted_device_id_seq, server_default=trusted_device_id_seq.next_value(), primary_key=True)

    certificate_id = Column(Integer, ForeignKey('certificate.id'), nullable=False)
    is_active = Column(Boolean, nullable=False)
    is_requires_review = Column(Boolean, nullable=False)
    created = Column(DateTime(timezone=True), default=localtz_now)
    modified = Column(DateTime(timezone=True), default=localtz_now, onupdate=localtz_now)

    certificates = relationship("Certificate", foreign_keys=[Certificate.trusted_device_id], order_by=Certificate.ID, back_populates="trusted_device")
    active_certificate = relationship('Certificate', foreign_keys=[certificate_id])

