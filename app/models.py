from sqlalchemy import create_engine, Column, Integer, String, Date, Boolean, Text, TIMESTAMP, ForeignKey, LargeBinary, func, Index, UniqueConstraint
from sqlalchemy.orm import declarative_base, relationship, sessionmaker
from config import Config
from flask_bcrypt import generate_password_hash, check_password_hash
import os

Base = declarative_base()

# Definition der Tabellen

class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True, autoincrement=True)
    firstName = Column(String(255))
    lastName = Column(String(255))
    email = Column(String(255), index=True)
    birthDate = Column(Date)
    profilePicture = Column(String(255))
    passwordSalt = Column(String(255))
    passwordHash = Column(String(255))
    dateCreated = Column(TIMESTAMP, server_default=func.current_timestamp())
    dateModified = Column(TIMESTAMP, server_default=func.current_timestamp(), onupdate=func.current_timestamp())

    roles = relationship('UserRole', back_populates='user')
    settings = relationship('UserSetting', back_populates='user')
    items = relationship('Item', back_populates='creator')
    list_types = relationship('ListType', back_populates='creator')
    passkeys = relationship('Passkey', back_populates='user')

    def hash_password(self, password):
        # Generiere ein zufälliges Salt
        self.passwordSalt = os.urandom(16).hex()  # 16 Bytes random salt
        # Erstelle den Passwort-Hash mit Salt
        self.passwordHash = generate_password_hash(password + self.passwordSalt).decode('utf-8')
        return self.passwordHash, self.passwordSalt


    def check_password(self, password):
        return check_password_hash(self.passwordHash, password + self.passwordSalt)


    def get_id(self):
        return str(self.id)
    
class Passkey(Base):
    __tablename__ = 'passkeys'
    id = Column(Integer, primary_key=True, autoincrement=True)
    userID = Column(Integer, ForeignKey('users.id'))
    name = Column(String(255))  # Name des Schlüssels
    credential_id = Column(String(255), unique=True)  # Credential ID für WebAuthn
    public_key = Column(String(2048))  # Public key for FIDO2
    sign_count = Column(Integer, default=0)  # Sign Count für FIDO2
    dateCreated = Column(TIMESTAMP, server_default=func.current_timestamp())
    dateModified = Column(TIMESTAMP, server_default=func.current_timestamp(), onupdate=func.current_timestamp())

    user = relationship('User', back_populates='passkeys')

class Role(Base):
    __tablename__ = 'roles'
    id = Column(Integer, primary_key=True, autoincrement=True)
    roleName = Column(String(255))
    dateCreated = Column(TIMESTAMP, server_default=func.current_timestamp())
    dateModified = Column(TIMESTAMP, server_default=func.current_timestamp(), onupdate=func.current_timestamp())

    permissions = relationship('RolePermission', back_populates='role')
    users = relationship('UserRole', back_populates='role')

class Permission(Base):
    __tablename__ = 'permissions'
    id = Column(Integer, primary_key=True, autoincrement=True)
    permissionName = Column(String(255))
    listTypeID = Column(Integer, ForeignKey('listTypes.id'), nullable=True)
    dateCreated = Column(TIMESTAMP, server_default=func.current_timestamp())
    dateModified = Column(TIMESTAMP, server_default=func.current_timestamp(), onupdate=func.current_timestamp())

    roles = relationship('RolePermission', back_populates='permission')
    list_type = relationship('ListType', back_populates='permissions')

class RolePermission(Base):
    __tablename__ = 'rolePermissions'
    roleID = Column(Integer, ForeignKey('roles.id'), primary_key=True)
    permissionID = Column(Integer, ForeignKey('permissions.id'), primary_key=True)
    dateCreated = Column(TIMESTAMP, server_default=func.current_timestamp())
    dateModified = Column(TIMESTAMP, server_default=func.current_timestamp(), onupdate=func.current_timestamp())

    role = relationship('Role', back_populates='permissions')
    permission = relationship('Permission', back_populates='roles')

class UserRole(Base):
    __tablename__ = 'userRoles'
    userID = Column(Integer, ForeignKey('users.id'), primary_key=True)
    roleID = Column(Integer, ForeignKey('roles.id'), primary_key=True)
    dateCreated = Column(TIMESTAMP, server_default=func.current_timestamp())
    dateModified = Column(TIMESTAMP, server_default=func.current_timestamp(), onupdate=func.current_timestamp())

    user = relationship('User', back_populates='roles')
    role = relationship('Role', back_populates='users')

class Setting(Base):
    __tablename__ = 'settings'
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255))
    value = Column(Text)
    icon = Column(String(255))
    edition = Column(String(255))
    category = Column(String(255))
    type = Column(String(255))
    dateCreated = Column(TIMESTAMP, server_default=func.current_timestamp())
    dateModified = Column(TIMESTAMP, server_default=func.current_timestamp(), onupdate=func.current_timestamp())

class UserSetting(Base):
    __tablename__ = 'userSettings'
    id = Column(Integer, primary_key=True, autoincrement=True)
    userID = Column(Integer, ForeignKey('users.id'))
    name = Column(String(255))
    value = Column(Text)
    icon = Column(String(255))
    edition = Column(String(255))
    category = Column(String(255))
    type = Column(String(255))
    dateCreated = Column(TIMESTAMP, server_default=func.current_timestamp())
    dateModified = Column(TIMESTAMP, server_default=func.current_timestamp(), onupdate=func.current_timestamp())

    user = relationship('User', back_populates='settings')

class Item(Base):
    __tablename__ = 'items'
    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(255))
    content = Column(Text)
    contentType = Column(String(50))
    listType = Column(Integer, ForeignKey('listTypes.id'), index=True)
    contentURL = Column(Text)
    edition = Column(String(50), default='all')
    createdByUser = Column(Integer, ForeignKey('users.id'))
    dateCreated = Column(TIMESTAMP, server_default=func.current_timestamp())
    dateModified = Column(TIMESTAMP, server_default=func.current_timestamp(), onupdate=func.current_timestamp())

    creator = relationship('User', back_populates='items')
    list_type = relationship('ListType', back_populates='items')

class ItemShare(Base):
    __tablename__ = 'itemShares'
    id = Column(Integer, primary_key=True, autoincrement=True)
    itemID = Column(Integer, ForeignKey('items.id'), nullable=False, index=True)
    token = Column(String(16), unique=True, nullable=False, index=True)
    createdByUser = Column(Integer, ForeignKey('users.id'), nullable=False)
    createdAt = Column(TIMESTAMP, server_default=func.current_timestamp())
    expiresAt = Column(TIMESTAMP, nullable=True)
    passwordHash = Column(String(255), nullable=True)
    isActive = Column(Boolean, default=True, nullable=False)
    viewCount = Column(Integer, default=0, nullable=False)

    item = relationship('Item', backref='shares')
    creator = relationship('User', foreign_keys=[createdByUser])

class ListType(Base):
    __tablename__ = 'listTypes'
    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(255))
    icon = Column(String(255))
    contentURL = Column(Text)
    createdByUser = Column(Integer, ForeignKey('users.id'))
    navbarOrder = Column(Integer)
    navbar = Column(Boolean)
    routeID = Column(Integer, default=0)
    mainTitle = Column(String(255))
    dateCreated = Column(TIMESTAMP, server_default=func.current_timestamp())
    dateModified = Column(TIMESTAMP, server_default=func.current_timestamp(), onupdate=func.current_timestamp())

    creator = relationship('User', back_populates='list_types')
    items = relationship('Item', back_populates='list_type')
    permissions = relationship('Permission', back_populates='list_type')

class RelationshipStatus(Base):
    __tablename__ = 'relationship_status'
    id = Column(Integer, primary_key=True, autoincrement=True)
    dateCreated = Column(TIMESTAMP, server_default=func.current_timestamp())
    dateModified = Column(TIMESTAMP, server_default=func.current_timestamp(), onupdate=func.current_timestamp())

class Translation(Base):
    __tablename__ = 'translations'

    id = Column(Integer, primary_key=True)
    entityType = Column(String(50), nullable=False)  # Z.B. 'Role', 'Article'
    entityID = Column(Integer, nullable=False)       # ID der zugehörigen Entität
    languageCode = Column(String(2), nullable=False) # 'en', 'de', etc.
    fieldName = Column(String(50), nullable=False)   # Z.B. 'description', 'title'
    translatedText = Column(Text, nullable=False)            # Der übersetzte Text
    helpText = Column(Text)
    #dateCreated = Column(TIMESTAMP, server_default=func.current_timestamp())
    #dateModified = Column(TIMESTAMP, server_default=func.current_timestamp(), onupdate=func.current_timestamp())

    __table_args__ = (
        Index('idx_translation_entity', 'entityType', 'entityID', 'languageCode', 'fieldName'),
        UniqueConstraint('entityType', 'entityID', 'languageCode', 'fieldName', name='uq_translation_entity')
    )

# Database connection
engine = create_engine(Config.SQLALCHEMY_DATABASE_URI)
Base.metadata.create_all(engine)

# Session creation
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)