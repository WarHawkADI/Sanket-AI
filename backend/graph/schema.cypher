// ── Constraints (enforce uniqueness) ──────────────────────────────────────
CREATE CONSTRAINT equipment_tag IF NOT EXISTS
  FOR (e:Equipment) REQUIRE e.tag IS UNIQUE;

CREATE CONSTRAINT document_id IF NOT EXISTS
  FOR (d:Document) REQUIRE d.id IS UNIQUE;

CREATE CONSTRAINT failure_mode_code IF NOT EXISTS
  FOR (f:FailureMode) REQUIRE f.code IS UNIQUE;

// ── Indexes (speed up lookups) ─────────────────────────────────────────────
CREATE INDEX equipment_type IF NOT EXISTS
  FOR (e:Equipment) ON (e.type);

CREATE INDEX document_type IF NOT EXISTS
  FOR (d:Document) ON (d.type);

CREATE INDEX document_date IF NOT EXISTS
  FOR (d:Document) ON (d.date);

CREATE INDEX document_source IF NOT EXISTS
  FOR (d:Document) ON (d.source);

// ── Vector index for semantic search on document embeddings ───────────────
CREATE VECTOR INDEX document_embedding IF NOT EXISTS
  FOR (d:Document) ON (d.embedding)
  OPTIONS {
    indexConfig: {
      `vector.dimensions`: 1024,
      `vector.similarity_function`: 'cosine'
    }
  };
