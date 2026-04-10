from __future__ import annotations

import logging
from time import perf_counter

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
	start = perf_counter()
	with connection.cursor(row_factory=dict_row) as cur:
		cur.execute(sql, params)
		rows = cur.fetchall()
	elapsed = perf_counter() - start
	log = logger.warning if elapsed >= 5 else logger.info
	log(
		"Completed %s with %s rows in %.2fs",
		query_name,
		len(rows),
		elapsed,
	)
	return rows
