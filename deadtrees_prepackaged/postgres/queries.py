from __future__ import annotations

import logging

from psycopg import Connection
from psycopg.rows import dict_row


logger = logging.getLogger(__name__)


def fetch_dataset_rows(
	connection: Connection,
	sql: str,
	limit: int | None = None,
	query_name: str = 'dataset query',
) -> list[dict]:
	params: tuple = ()
	if limit is not None:
		sql += "\nlimit %s"
		params = (limit,)

	logger.info("Running %s with limit=%s", query_name, limit)
	with connection.cursor(row_factory=dict_row) as cur:
		cur.execute(sql, params)
		rows = cur.fetchall()
	logger.info("Completed %s with %s rows", query_name, len(rows))
	return rows
