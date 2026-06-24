"""
Read-only diagnostic for vector search.
Run from impl/web_app with the venv active and .env loaded (same as web_app.ps1):

    python diag_vector.py

It inspects:
  1) the container's vectorEmbeddingPolicy / vectorIndexes
  2) the type / length of the configured embedding field on a sample doc
  3) a small VectorDistance probe query (TOP 3) and the returned scores
"""

import asyncio
import json

from src.services.config_service import ConfigService
from src.services.ai_service import AiService
from src.services.cosmos_nosql_service import CosmosNoSQLService


async def main():
    db = ConfigService.graph_source_db()
    ctr = ConfigService.graph_source_container()
    attr = ConfigService.embedding_field_name()
    print(f"db='{db}' container='{ctr}' embedding_field='{attr}'")

    nosql = CosmosNoSQLService()
    await nosql.initialize()
    nosql.set_db(db)
    nosql.set_container(ctr)

    # 1) container policy
    props = await nosql._ctrproxy.read()
    print("\n--- vectorEmbeddingPolicy ---")
    print(json.dumps(props.get("vectorEmbeddingPolicy", {}), indent=2))
    print("\n--- indexingPolicy.vectorIndexes ---")
    print(json.dumps(props.get("indexingPolicy", {}).get("vectorIndexes", []), indent=2))

    # 2) sample doc field shape
    sample = await nosql.query_items(
        f"SELECT TOP 1 c.id, c.{attr} AS emb FROM c WHERE IS_DEFINED(c.{attr})",
        cross_partition=True,
    )
    if not sample:
        print(f"\nNo docs found with field '{attr}'.")
    else:
        emb = sample[0].get("emb")
        print(f"\nsample id={sample[0].get('id')}")
        print(f"  type(c.{attr}) = {type(emb).__name__}")
        if isinstance(emb, list):
            print(f"  len = {len(emb)}")
            print(f"  first 5 = {emb[:5]}")
            print(f"  all numeric = {all(isinstance(x, (int, float)) for x in emb[:50])}")
        else:
            print(f"  value (truncated) = {str(emb)[:200]}")

    # 3) VectorDistance probe
    ai = AiService()
    resp = ai.generate_embeddings("high-calorie protein snack for long-distance running")
    qvec = resp.data[0].embedding
    print(f"\nquery embedding length = {len(qvec)}")

    sql = (
        f"SELECT TOP 3 c.id, c.product_title_translated AS title, "
        f"VectorDistance(c.{attr}, @embedding) AS score "
        f"FROM c WHERE IS_DEFINED(c.{attr}) "
        f"ORDER BY VectorDistance(c.{attr}, @embedding)"
    )
    rows = nosql._ctrproxy.query_items(
        query=sql, parameters=[{"name": "@embedding", "value": qvec}]
    )
    print("\n--- VectorDistance probe (TOP 3) ---")
    async for r in rows:
        print(f"  score={r.get('score')}  title={r.get('title')}  id={r.get('id')}")

    await nosql.close()


if __name__ == "__main__":
    asyncio.run(main())
