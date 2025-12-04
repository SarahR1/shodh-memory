# Gravitational Salience Memory: Research Foundation

## Core Hypothesis

Memory formation and retrieval follows a **gravitational model** where:
- **Nouns/Entities** act as gravitational wells with varying mass (salience)
- **Verbs** create traversable pathways between entities
- **Adjectives** modify traversal characteristics (filtering, direction)
- **Forgetting** is salience-weighted, not purely temporal

---

## Competitive Landscape

### Existing Memory Systems for LLMs

| System | Architecture | Limitations |
|--------|-------------|-------------|
| **Mem0** | Hybrid vector+graph+KV store | Treats all text equally, no linguistic structure |
| **Zep** | Temporal knowledge graph (Graphiti) | Entity-based graph, not grammar-aware |
| **MemGPT/Letta** | OS-style memory swapping | No understanding of *what* to remember |

### Key Papers

1. **Mem0 Architecture**
   - Source: https://arxiv.org/html/2504.19413v1
   - Key finding: Hybrid memory (vector + graph + KV) outperforms single-store approaches
   - Limitation: No linguistic/cognitive foundation

2. **Zep Temporal Knowledge Graph**
   - Source: https://arxiv.org/html/2501.13956v1
   - Key finding: Temporal graphs capture context shifts (94.8% on DMR benchmark)
   - Limitation: Graph is entity-relationship based, not grammar-aware

3. **Comparison Survey**
   - Source: https://www.graphlit.com/blog/survey-of-ai-agent-memory-frameworks
   - Key finding: Robust systems compose multiple memory layers

---

## Cognitive Psychology Research

### Emotional Salience and Memory Formation

**Key Paper**: "The selective effects of emotional arousal on memory"
- Source: https://www.apa.org/science/about/psa/2012/02/emotional-arousal
- Key findings:
  - Arousal enhances memory for HIGH PRIORITY stimuli
  - Arousal IMPAIRS memory for LOW PRIORITY stimuli
  - Priority can be determined by bottom-up salience or top-down goals

**Emotional Tagging Hypothesis**
- Source: https://pmc.ncbi.nlm.nih.gov/articles/PMC10410470/
- Key findings:
  - Amygdala activation marks experiences as "important"
  - Enhances synaptic plasticity for emotionally arousing events
  - Facilitates transformation from transient to permanent memory

**Central vs Peripheral Memory**
- Source: https://pmc.ncbi.nlm.nih.gov/articles/PMC4183265/
- Key findings:
  - Violence/trauma improve memory for CENTRAL GIST
  - Violence/trauma IMPAIR memory for PERIPHERAL DETAILS
  - Implication: Store the gist (nouns), not every detail (adjectives)

### Forgetting Mechanisms

**Retrieval-Induced Forgetting (RIF)**
- Source: https://link.springer.com/article/10.3758/s13415-016-0460-1
- Key findings:
  - Practicing retrieval of items from a category causes forgetting of competing items
  - Reducing negative emotions facilitates RIF
  - Arousal levels affect what gets forgotten

---

## Cognitive Linguistics Research

### Construction Grammar

**Key Paper**: "Usage-based Grammar Induction from Minimal Cognitive Principles"
- Source: https://direct.mit.edu/coli/article/50/4/1375/123787/Usage-based-Grammar-Induction-from-Minimal
- Key findings:
  - Sequence memory + chunking are key cognitive mechanisms for grammar learning
  - Memory stores "constructions" (chunks), not individual words
  - Frequent patterns become deeply entrenched (high token frequency)

**Construction Grammar and Memory**
- Source: https://www.degruyterbrill.com/document/doi/10.1515/cllt-2024-0009/html
- Key findings:
  - Type frequency strengthens constructional schema in memory
  - Token frequency restricts extension to new items
  - High token frequency expressions resist change (entrenchment)

### Semantic Roles and Frame Semantics

**Key Paper**: "Construction Grammar and Frame Semantics"
- Source: https://sites.la.utexas.edu/hcb/files/2021/07/Boas-CxG-and-FS-2021-DRAFT.pdf
- Key findings:
  - Semantic meaning is made of: image-schemas, frames, conceptual metaphors
  - Constructions carry meaning independent of the words that fill them
  - Implication: Verbs define the "frame", nouns fill the "slots"

---

## Our Unique Approach: Gravitational Salience Memory

### What Sets Us Apart

1. **First memory system grounded in cognitive linguistics**
   - Not just engineering, but cognitive science foundation

2. **Salience-based gravitational model**
   - Entities have "mass" based on importance/frequency/emotional charge
   - High-mass entities attract related memories

3. **Grammar-aware memory formation**
   - Nouns: Create gravitational wells (stored as entities)
   - Verbs: Create pathways (stored as edges)
   - Adjectives: Filter/select during retrieval
   - Tense: Stratifies temporal layers

4. **Emotion-tagged memory**
   - High-arousal verbs ("killed", "discovered", "failed") boost memory importance
   - Structural verbs ("is", "has", "was") just connect, don't boost

5. **Salience-weighted forgetting**
   - High-salience memories decay slowly
   - Low-salience memories decay quickly
   - Based on cognitive research, not arbitrary FIFO/LRU

6. **100% local/offline capability**
   - Unique market position for robotics/edge AI
   - No cloud dependency

---

## Implementation Phases

### Phase 1: Foundation (COMPLETE)
- Semantic search at 100% accuracy
- Vector embeddings for content matching
- Basic importance scoring
- Graph structure exists

### Phase 2: Salience Detection (NEXT)
- Add salience scoring to entity extraction
- Track entity frequency across memories
- Flag proper nouns as higher salience
- Store salience per entity in graph

### Phase 3: Emotion-Aware Verbs
- Classify verbs into memory-forming vs structural
- Memory-forming verbs boost importance
- Structural verbs create edges only

### Phase 4: Access-Based Reinforcement
- Hebbian learning: accessed memories strengthen
- Salience = base_salience * log(1 + access_count)
- Co-accessed entities strengthen connections

### Phase 5: Salience-Weighted Forgetting
- Decay function with salience modifier
- Compress low-salience (keep gist, lose details)
- Never fully delete, just demote

---

## Open Questions

1. **How to detect salience without LLM?**
   - NER for named entities
   - Frequency tracking
   - User-defined important entities

2. **How to classify emotional verbs?**
   - Curated verb lists by arousal level
   - Sentiment analysis on context
   - Verb embeddings clustering

3. **What's the optimal decay function?**
   - Exponential with salience modifier
   - Power law (more realistic for human memory)
   - Access-based reinforcement

---

## References

### AI Memory Systems
- Mem0: https://arxiv.org/html/2504.19413v1
- Zep: https://arxiv.org/html/2501.13956v1
- MemGPT: https://arxiv.org/abs/2310.08560
- Survey: https://www.graphlit.com/blog/survey-of-ai-agent-memory-frameworks
- Comparison: https://www.marktechpost.com/2025/11/10/comparing-memory-systems-for-llm-agents-vector-graph-and-event-logs/

### Cognitive Psychology
- Emotional arousal: https://www.apa.org/science/about/psa/2012/02/emotional-arousal
- Memory overview: https://pmc.ncbi.nlm.nih.gov/articles/PMC10410470/
- Courtroom memory: https://pmc.ncbi.nlm.nih.gov/articles/PMC4183265/
- Emotional salience: https://link.springer.com/article/10.3758/s13415-016-0460-1
- Forward-flow: https://www.researchgate.net/publication/381340482_Emotional_salience_modulates_the_forward-flow_of_memory

### Cognitive Linguistics
- Usage-based grammar: https://direct.mit.edu/coli/article/50/4/1375/123787/Usage-based-Grammar-Induction-from-Minimal
- Construction grammar history: https://www.degruyterbrill.com/document/doi/10.1515/cllt-2024-0009/html
- Frame semantics: https://sites.la.utexas.edu/hcb/files/2021/07/Boas-CxG-and-FS-2021-DRAFT.pdf
- Syntactico-semantic patterns: https://pmc.ncbi.nlm.nih.gov/articles/PMC11268157/
