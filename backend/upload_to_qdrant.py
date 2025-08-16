from dotenv import load_dotenv
load_dotenv()

import asyncio
from typing import Dict, List, Tuple

from sqlalchemy import text

from models.db import async_session
from qdrant_client import QdrantClient
from qdrant_client.http import models as qmodels
from sentence_transformers import SentenceTransformer


CollectionName = str
RowId = int
TextVal = str


async def fetch_values() -> Dict[CollectionName, List[Tuple[RowId | None, TextVal]]]:
	"""Lee valores desde Postgres que servirán como vocabularios para Qdrant.

	Devuelve un dict por colección con pares (id, texto). Para valores DISTINCT
	sin id propio (p. ej. compuestos de neumáticos) el id puede venir como None.
	"""
	async with async_session() as session:
		results: Dict[CollectionName, List[Tuple[RowId | None, TextVal]]] = {}

		def dedupe(items: List[Tuple[RowId | None, TextVal]]):
			seen = {}
			for _id, txt in items:
				if not txt:
					continue
				key = txt.strip().lower()
				if key and key not in seen:
					seen[key] = (_id, txt.strip())
			return list(seen.values())

		# Drivers
		driver_full_names = await session.execute(text("""
			SELECT id, full_name FROM driver WHERE full_name IS NOT NULL
		"""))
		results["driver_full_name"] = dedupe([(row.id, row.full_name) for row in driver_full_names])

		driver_acronyms = await session.execute(text("""
			SELECT id, name_acronym FROM driver WHERE name_acronym IS NOT NULL
		"""))
		results["driver_acronym"] = dedupe([(row.id, row.name_acronym) for row in driver_acronyms])

		# Meetings
		meeting_names = await session.execute(text("""
			SELECT id, meeting_official_name FROM meeting WHERE meeting_official_name IS NOT NULL
		"""))
		results["meeting_name"] = dedupe([(row.id, row.meeting_official_name) for row in meeting_names])

		# Meeting standard names (nueva colección)
		meeting_standard_names = await session.execute(text("""
			SELECT id, meeting_standard_name FROM meeting WHERE meeting_standard_name IS NOT NULL
		"""))
		results["meeting_standard_name"] = dedupe([(row.id, row.meeting_standard_name) for row in meeting_standard_names])

		meeting_locations = await session.execute(text("""
			SELECT id, location FROM meeting WHERE location IS NOT NULL
		"""))
		results["meeting_location"] = dedupe([(row.id, row.location) for row in meeting_locations])

		# Sessions
		session_names = await session.execute(text("""
			SELECT id, session_name FROM session WHERE session_name IS NOT NULL
		"""))
		results["session_name"] = dedupe([(row.id, row.session_name) for row in session_names])

		session_types = await session.execute(text("""
			SELECT id, session_type FROM session WHERE session_type IS NOT NULL
		"""))
		results["session_type"] = dedupe([(row.id, row.session_type) for row in session_types])

		# Tyre compounds (distinct values only)
		tyre_compounds = await session.execute(text("""
			SELECT DISTINCT compound FROM stint WHERE compound IS NOT NULL
		"""))
		results["tyre_compound"] = dedupe([(None, row.compound) for row in tyre_compounds])

		return results


def ensure_collection(client: QdrantClient, name: str, vector_size: int):
	client.recreate_collection(
        collection_name=name,
        vectors_config=qmodels.VectorParams(
            size=vector_size,
            distance=qmodels.Distance.COSINE
        ),
        hnsw_config=qmodels.HnswConfigDiff(
            m=32,                 
            ef_construct=256
        )
    )

def chunked(seq, size):
	for i in range(0, len(seq), size):
		yield seq[i : i + size]


def upsert_collection(
	client: QdrantClient,
	model: SentenceTransformer,
	name: str,
	items: List[Tuple[RowId | None, TextVal]],
	vector_size: int,
	batch_size: int = 512,
):
	ensure_collection(client, name, vector_size)

	texts = [t for (_id, t) in items]
	# Generate simple local ids if DB id is None
	ids: List[int] = [(_id if _id is not None else i + 1) for i, (_id, _t) in enumerate(items)]

	for idxs in chunked(list(range(len(texts))), batch_size):
		batch_texts = [texts[i] for i in idxs]
		vectors = model.encode(batch_texts, batch_size=min(64, len(batch_texts)), show_progress_bar=False)
		points = [
			qmodels.PointStruct(
				id=ids[i],
				vector=vectors[j].tolist(),
				payload={"text": batch_texts[j], "source_id": ids[i]},
			)
			for j, i in enumerate(idxs)
		]
		client.upsert(collection_name=name, points=points)


async def main():
	# 1) Fetch values from Postgres
	data = await fetch_values()

	# 2) Init Qdrant and embedding model
	client = QdrantClient(url="http://localhost:6333")
	model = SentenceTransformer("all-MiniLM-L6-v2")
	dim = model.get_sentence_embedding_dimension()

	# 3) Upsert each collection
	for collection_name, items in data.items():
		if not items:
			continue
		upsert_collection(client, model, collection_name, items, dim)

	print("Qdrant collections populated:")
	for name, items in data.items():
		print(f"- {name}: {len(items)} items")


if __name__ == "__main__":
	try:
		asyncio.run(main())
	except KeyboardInterrupt:
		pass