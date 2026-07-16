import os
from neo4j import GraphDatabase
from dotenv import load_dotenv

load_dotenv()


class Neo4jClient:
    _instance = None

    def __init__(self):
        self.driver = GraphDatabase.driver(
            os.getenv("NEO4J_URI", "bolt://localhost:7687"),
            auth=(
                os.getenv("NEO4J_USERNAME", "neo4j"),
                os.getenv("NEO4J_PASSWORD", "sanket123"),
            ),
            # short timeout so the MemStore fallback is snappy when Neo4j is absent
            connection_timeout=int(os.getenv("NEO4J_CONNECTION_TIMEOUT", "3")),
            connection_acquisition_timeout=int(os.getenv("NEO4J_CONNECTION_TIMEOUT", "3")),
        )

    @classmethod
    def get(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def run(self, query, **params):
        with self.driver.session() as session:
            return list(session.run(query, **params))

    def close(self):
        self.driver.close()
        Neo4jClient._instance = None
