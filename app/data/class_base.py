from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase):
    pass

    repr_cols_num = 4
    repr_cols = ' '

    def __repr__(self):
        cols = []

        for idx, col in enumerate(self.__table__.columns.keys()):
            if col in self.repr_cols or idx < self.repr_cols_num:
                cols.append(f'{col}={getattr(self, col)}')

        return f'<{self.__class__.__name__} {','.join(cols)}>'