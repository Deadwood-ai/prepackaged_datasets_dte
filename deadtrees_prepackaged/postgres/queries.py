from __future__ import annotations

from psycopg import Connection
from psycopg.rows import dict_row


def fetch_dataset_rows(
	connection: Connection,
	sql: str,
	limit: int | None = None,
) -> list[dict]:
	params: tuple = ()
	if limit is not None:
		sql += "\nlimit %s"
		params = (limit,)

	with connection.cursor(row_factory=dict_row) as cur:
		cur.execute(sql, params)
		return cur.fetchall()
