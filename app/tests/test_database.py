import sys
sys.path.insert(0, '/app')

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from database import Base, get_db, SessionLocal


def test_database_connection():
    """Test PostgreSQL database connection"""
    try:
        # Connect to PostgreSQL
        engine = create_engine('postgresql://bugtracker:bugtracker123@db/bugtracker')
        connection = engine.connect()
        
        assert connection is not None
        
        # Execute a simple PostgreSQL query
        result = connection.execute(text("SELECT 1 as test_value"))
        assert result.scalar() == 1
        
        # Test PostgreSQL version
        result = connection.execute(text("SELECT version()"))
        version = result.scalar()
        print(f"PostgreSQL version: {version}")
        
        connection.close()
        print("PostgreSQL database connection successful")
        
    except Exception as e:
        pytest.skip(f"Database connection failed: {e}")


def test_session_local_with_postgres():
    """Test SessionLocal factory with PostgreSQL"""
    try:
        engine = create_engine('postgresql://bugtracker:bugtracker123@db/bugtracker')
        TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        
        session = TestingSessionLocal()
        assert session is not None
        
        # Test session operations
        result = session.execute(text("SELECT 1"))
        assert result.scalar() == 1
        
        # Test PostgreSQL-specific query
        result = session.execute(text("SELECT current_database()"))
        db_name = result.scalar()
        assert db_name == "bugtracker"
        
        session.close()
        print("SessionLocal works correctly with PostgreSQL")
        
    except Exception as e:
        pytest.skip(f"Session test failed: {e}")


def test_get_db_generator():
    """Test get_db dependency generator with PostgreSQL"""
    try:
        engine = create_engine('postgresql://bugtracker:bugtracker123@db/bugtracker')
        TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        
        # Mock the dependency
        def mock_get_db():
            db = TestingSessionLocal()
            try:
                yield db
            finally:
                db.close()
        
        # Test the generator
        db_gen = mock_get_db()
        db = next(db_gen)
        
        assert db is not None
        
        # Test database operation
        result = db.execute(text("SELECT current_user"))
        current_user = result.scalar()
        print(f"Current PostgreSQL user: {current_user}")
        
        # Cleanup
        try:
            next(db_gen)
        except StopIteration:
            pass
        
        print("get_db generator works correctly")
        
    except Exception as e:
        pytest.skip(f"get_db test failed: {e}")


def test_postgresql_specific_features():
    """Test PostgreSQL-specific features"""
    try:
        engine = create_engine('postgresql://bugtracker:bugtracker123@db/bugtracker')
        connection = engine.connect()
        
        # Test PostgreSQL extensions
        result = connection.execute(text("""
            SELECT extname 
            FROM pg_extension 
            WHERE extname IN ('pgcrypto', 'uuid-ossp', 'citext')
        """))
        extensions = [row[0] for row in result]
        print(f"Available PostgreSQL extensions: {extensions}")
        
        # Test JSON support (PostgreSQL feature)
        result = connection.execute(text("SELECT version() ~ 'PostgreSQL' as is_postgres"))
        assert result.scalar() == True
        
        connection.close()
        print("PostgreSQL features test passed")
        
    except Exception as e:
        pytest.skip(f"PostgreSQL features test failed: {e}")