# Gravitational Salience Memory - Implementation Roadmap

## Current State (December 2025)

### Completed
- [x] **Phase 1: Foundation** - 100% semantic search accuracy
- [x] **Phase 1: Hybrid Retrieval** - Graph boost integrated with semantic search
  - Formula: `final_score = semantic_score * (1.0 + graph_boost)`
  - Entity extraction on memory storage
  - Episode-entity linking in knowledge graph
  - 1-hop relationship traversal for indirect activation
  - Benchmark: 22/22 tests passing, avg relevance 0.75

---

## Phase 2: Salience Detection (NEXT)

Goal: Identify which entities are "gravitational wells" vs noise.

### 2.1 Enhanced Entity Extraction
- [ ] **Detect proper nouns vs common nouns**
  - Proper nouns (names, places, products) = higher salience
  - Common nouns (things, concepts) = medium salience
  - File: `src/graph_memory.rs` - `EntityExtractor::extract()`

- [ ] **Add salience score to EntityNode**
  ```rust
  pub struct EntityNode {
      // ... existing fields ...
      pub salience: f32,  // 0.0 - 1.0
      pub salience_factors: SalienceFactors,
  }

  pub struct SalienceFactors {
      pub proper_noun_boost: f32,      // 0.3 for proper nouns
      pub frequency_score: f32,        // log(mention_count)
      pub recency_score: f32,          // time-decay factor
      pub user_defined: f32,           // explicit importance markers
  }
  ```

### 2.2 Frequency Tracking
- [ ] **Increment mention_count on entity recognition**
  - Already exists: `entity.mention_count += 1`
  - Add: salience update formula

- [ ] **Salience Formula**
  ```
  salience = base_salience * (1 + 0.1 * ln(mention_count))

  where:
    base_salience = 0.7 for proper nouns, 0.4 for common nouns
    mention_count = times entity appears across all memories
  ```

### 2.3 Proper Noun Detection
- [ ] **Rule-based detection** (no LLM required)
  - Capitalized words not at sentence start
  - Preceded by determiners ("the John" vs "a thing")
  - In tech_keywords list = Technology entity
  - In org_indicators list = Organization entity
  - Single capitalized word = likely Person

- [ ] **Pattern-based indicators**
  - "my X" = user's X (higher salience)
  - "the X project" = project entity
  - "@username" = social handle
  - "v1.2.3" = version number

---

## Phase 3: Emotion-Aware Verbs

Goal: Verbs determine memory importance, not just connectivity.

### 3.1 Verb Classification
- [ ] **Create verb arousal dictionary**
  ```rust
  pub struct VerbClassifier {
      memory_forming: HashSet<String>,  // "killed", "discovered", "failed"
      structural: HashSet<String>,       // "is", "has", "was"
      action: HashSet<String>,           // "runs", "makes", "builds"
  }
  ```

- [ ] **Memory-forming verbs** (high arousal)
  - Emotional: killed, loved, hated, feared, crashed, exploded
  - Achievement: discovered, solved, completed, fixed, broke
  - Change: transformed, converted, migrated, upgraded, deprecated

- [ ] **Structural verbs** (low arousal, connectivity only)
  - Being: is, are, was, were, been, being
  - Having: has, have, had, contains, includes
  - Linking: seems, appears, becomes, remains

### 3.2 Importance Boost from Verbs
- [ ] **Apply verb boost on memory storage**
  ```
  memory.importance += verb_arousal_score

  where:
    verb_arousal_score = 0.3 for memory-forming verbs
    verb_arousal_score = 0.0 for structural verbs
    verb_arousal_score = 0.1 for action verbs
  ```

---

## Phase 4: Access-Based Reinforcement (Hebbian Learning)

Goal: Frequently accessed memories become more salient.

### 4.1 Access Tracking
- [ ] **Track retrieval events**
  ```rust
  pub struct AccessLog {
      pub memory_id: MemoryId,
      pub accessed_at: DateTime<Utc>,
      pub query_context: String,  // what query triggered this
  }
  ```

- [ ] **Update salience on access**
  ```
  entity.salience = entity.salience * (1 + 0.05 * access_count)
  ```

### 4.2 Co-Access Strengthening
- [ ] **Strengthen relationships between co-retrieved memories**
  - If memory A and B are retrieved together, strengthen edge A-B
  - Formula: `edge.strength = edge.strength * 1.1`

---

## Phase 5: Salience-Weighted Forgetting

Goal: Low-salience memories fade, high-salience persist.

### 5.1 Decay Function
- [ ] **Implement salience-weighted decay**
  ```
  effective_age = actual_age * (1 / salience)

  High salience (0.9): effective_age = 1.1x actual
  Low salience (0.1): effective_age = 10x actual
  ```

### 5.2 Memory Compression
- [ ] **Compress low-salience memories to gist**
  - Keep: nouns (entities) and relationships
  - Discard: adjectives, adverbs, filler words
  - Store: compressed summary + original for later expansion

### 5.3 Memory Demotion (Not Deletion)
- [ ] **Implement tier demotion**
  - Working memory -> Session memory (after 1 hour)
  - Session memory -> Long-term memory (after 24 hours)
  - Long-term memory -> Archive (after 30 days of no access)
  - Archive: compressed, not searchable by default

---

## Implementation Order

### Sprint 1: Salience Foundation
1. Add `salience` field to `EntityNode`
2. Implement proper noun detection in `EntityExtractor`
3. Update salience on entity creation/recognition
4. Test: benchmark should maintain 100% accuracy

### Sprint 2: Verb Classification
1. Create `VerbClassifier` with arousal dictionaries
2. Integrate verb extraction in `process_experience_into_graph`
3. Apply importance boost based on verb type
4. Test: high-arousal memories should rank higher

### Sprint 3: Retrieval Enhancement
1. Add access logging
2. Implement co-access strengthening
3. Update graph boost formula to use salience
4. Test: frequently accessed memories should rank higher

### Sprint 4: Forgetting
1. Implement decay function
2. Add memory compression for low-salience
3. Implement tier demotion logic
4. Test: old low-salience memories should fade

---

## Files to Modify

| File | Changes |
|------|---------|
| `src/graph_memory.rs` | Add salience to EntityNode, improve EntityExtractor |
| `src/main.rs` | Update graph boost formula, add access logging |
| `src/memory/mod.rs` | Add decay function, compression logic |
| `src/memory/types.rs` | Add AccessLog, VerbClassification enums |
| NEW: `src/verbs.rs` | VerbClassifier with arousal dictionaries |
| NEW: `src/salience.rs` | Salience calculation module |

---

## Success Metrics

| Metric | Current | Target |
|--------|---------|--------|
| Semantic accuracy | 100% | 100% |
| Avg relevance score | 0.75 | 0.85+ |
| Graph boost applied | Yes | Yes |
| Salience-based ranking | No | Yes |
| Proper noun detection | Basic | Advanced |
| Verb classification | No | Yes |
| Access-based learning | No | Yes |
| Salience-weighted decay | No | Yes |

---

## Phase 6: Universe Visualization

Goal: Render memory graph as an interactive 3D universe.

### 6.1 Visual Metaphors
| Concept | Visual Representation |
|---------|----------------------|
| **High-salience entities** | Large glowing stars (size = salience) |
| **Low-salience entities** | Small dim stars |
| **Memories** | Planets orbiting their entity stars |
| **Relationships** | Gravitational lines / orbital paths |
| **Verbs (pathways)** | Warp lanes / hyperspace routes |
| **Adjectives** | Planetary atmosphere color |
| **Entity clusters** | Galaxies / constellations |
| **Time** | Distance from center (older = further) |
| **Access frequency** | Brightness / luminosity |

### 6.2 3D Force-Directed Layout
- [ ] **Implement force simulation**
  - Salience = mass (gravitational pull)
  - Relationships = springs (attract connected nodes)
  - Unrelated entities repel (prevent overlap)
  - Libraries: Three.js, D3-force-3d, or WebGL

- [ ] **Position calculation**
  ```
  position = f(entity.salience, entity.relationships, entity.age)

  High salience entities: closer to center, larger
  Old memories: pushed to outer rings
  Related entities: clustered together
  ```

### 6.3 API Endpoint for Visualization Data
- [ ] **Add `/api/graph/{user_id}/universe` endpoint**
  ```json
  {
    "stars": [
      {
        "id": "uuid",
        "name": "TypeScript",
        "type": "Technology",
        "salience": 0.85,
        "size": 50,
        "color": "#3178c6",
        "position": {"x": 100, "y": 50, "z": -20},
        "planets": [
          {
            "memory_id": "uuid",
            "content_preview": "User prefers TypeScript...",
            "orbit_distance": 20,
            "age_days": 3
          }
        ]
      }
    ],
    "connections": [
      {
        "from": "uuid1",
        "to": "uuid2",
        "type": "RelatedTo",
        "strength": 0.7,
        "label": "uses"
      }
    ],
    "galaxies": [
      {
        "name": "Programming",
        "center": {"x": 100, "y": 50, "z": 0},
        "members": ["TypeScript", "React", "Rust"]
      }
    ]
  }
  ```

### 6.4 Frontend Components (shodh-website)
- [ ] **3D Canvas Component**
  - File: `shodh-website/app/memory/UniverseView.tsx`
  - Use React Three Fiber or raw Three.js
  - Interactive: zoom, rotate, click on stars

- [ ] **Star Rendering**
  ```tsx
  function Star({ entity }: { entity: Entity }) {
    const size = entity.salience * 50;  // Scale by salience
    const color = entityTypeColor(entity.type);

    return (
      <mesh position={entity.position}>
        <sphereGeometry args={[size, 32, 32]} />
        <meshStandardMaterial
          color={color}
          emissive={color}
          emissiveIntensity={entity.accessFrequency * 0.5}
        />
        {/* Glow effect for high-salience */}
        {entity.salience > 0.7 && <Glow size={size * 1.5} />}
      </mesh>
    );
  }
  ```

- [ ] **Connection Lines (Warp Lanes)**
  ```tsx
  function Connection({ from, to, strength }: Connection) {
    return (
      <Line
        points={[from, to]}
        color="#ffffff"
        opacity={strength}
        lineWidth={strength * 3}
      />
    );
  }
  ```

- [ ] **Hover/Click Interactions**
  - Hover: Show entity name + memory count
  - Click: Expand to show all connected memories
  - Double-click: Focus camera on entity
  - Right-click: Show context menu (delete, boost, etc.)

### 6.5 Visual Effects
- [ ] **Star glow shader**
  - Fresnel effect for realistic star appearance
  - Bloom post-processing for brightness

- [ ] **Particle effects**
  - Memory "dust" around high-activity entities
  - Trails for recently accessed memories

- [ ] **Animation**
  - Slow orbit for planets around stars
  - Pulsing for recently modified entities
  - Fade-in for new memories

### 6.6 Color Coding
| Entity Type | Color | Hex |
|-------------|-------|-----|
| Person | Warm yellow | #ffd93d |
| Organization | Blue | #6c9bcf |
| Technology | Cyan | #3178c6 |
| Location | Green | #4caf50 |
| Concept | Purple | #9c27b0 |
| Event | Orange | #ff9800 |
| Product | Pink | #e91e63 |

---

## Visualization Milestones

### Sprint V1: Basic 3D Graph
1. Add universe endpoint to API
2. Create basic Three.js scene
3. Render entities as spheres
4. Add connection lines
5. Basic orbit controls

### Sprint V2: Visual Polish
1. Star shader with glow
2. Size based on salience
3. Color based on entity type
4. Hover/click interactions

### Sprint V3: Universe Feel
1. Background starfield
2. Galaxy clustering
3. Particle effects
4. Smooth animations
5. Camera fly-through mode

### Sprint V4: Real-time Updates
1. WebSocket for live updates
2. Animate new memories appearing
3. Animate access highlights
4. Time-lapse mode (watch memory growth)

---

## Research References

See `literature/RESEARCH_OVERVIEW.md` for:
- Cognitive psychology papers on emotional salience
- Construction grammar research
- Competitor analysis (Mem0, Zep, MemGPT)
