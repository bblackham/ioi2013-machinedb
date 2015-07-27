
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

db_string = 'postgresql+psycopg2://cmsuser:password@localhost/database'
db = create_engine(db_string, pool_size=20, pool_recycle=120)
Base = declarative_base(db)
Session = sessionmaker(db)

class SessionGen:
    """This allows us to create handy local sessions simply with:

    with SessionGen() as session:
        session.do_something()

    and at the end the session is automatically closed.

    commit (bool): whether to commit or to rollback the session by
                   default, when no other instruction has been
                   specified. To do the commit or the rollback
                   idependently of this setting, just call the
                   relevant function from the session.  ATTENTION: by
                   default, the session is not committed.

    """
    def __init__(self, commit=False):
        self.commit = commit
        self.session = None

    def __enter__(self):
        self.session = Session()
        return self.session

    def __exit__(self, unused1, unused2, unused3):
        if self.commit:
            self.session.commit()
        else:
            self.session.rollback()
        self.session.close()
