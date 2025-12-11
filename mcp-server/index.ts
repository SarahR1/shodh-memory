#!/usr/bin/env node
/**
 * Shodh-Memory MCP Server
 *
 * Gives Claude persistent memory across sessions.
 * Connects to shodh-memory REST API running locally.
 *
 * Features:
 * - Semantic search with vector similarity
 * - Context summary for quick session bootstrapping
 * - Graceful network failure handling with retries
 * - Memory categorization by type and importance
 */

import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
  ListResourcesRequestSchema,
  ReadResourceRequestSchema,
} from "@modelcontextprotocol/sdk/types.js";

// Configuration
const API_URL = process.env.SHODH_API_URL || "http://127.0.0.1:3030";
const API_KEY = process.env.SHODH_API_KEY || "shodh-dev-key-change-in-production";
const USER_ID = process.env.SHODH_USER_ID || "claude-code";
const RETRY_ATTEMPTS = 3;
const RETRY_DELAY_MS = 1000;
const REQUEST_TIMEOUT_MS = 10000;

// Types matching the Rust API response structure
interface Experience {
  content: string;
  experience_type?: string;
  tags?: string[];
}

interface Memory {
  id: string;
  experience: Experience;
  score?: number;
  created_at?: string;
  importance?: number;
  tier?: string;
}

interface ApiResponse<T> {
  data?: T;
  error?: string;
}

// Helper: Get content from memory (handles nested structure)
function getContent(m: Memory): string {
  return m.experience?.content || '';
}

// Helper: Get experience type from memory
function getType(m: Memory): string {
  return m.experience?.experience_type || 'Observation';
}

// Helper: Sleep for retry delays
function sleep(ms: number): Promise<void> {
  return new Promise(resolve => setTimeout(resolve, ms));
}

// Robust API call with retries and timeout
async function apiCall<T>(
  endpoint: string,
  method: string = "GET",
  body?: object
): Promise<T> {
  let lastError: Error | null = null;

  for (let attempt = 1; attempt <= RETRY_ATTEMPTS; attempt++) {
    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);

      const options: RequestInit = {
        method,
        headers: {
          "Content-Type": "application/json",
          "X-API-Key": API_KEY,
        },
        signal: controller.signal,
      };

      if (body) {
        options.body = JSON.stringify(body);
      }

      const response = await fetch(`${API_URL}${endpoint}`, options);
      clearTimeout(timeoutId);

      if (!response.ok) {
        const errorText = await response.text().catch(() => 'Unknown error');
        throw new Error(`API error ${response.status}: ${errorText}`);
      }

      return await response.json() as T;
    } catch (error) {
      lastError = error instanceof Error ? error : new Error(String(error));

      // Don't retry on client errors (4xx)
      if (lastError.message.includes('API error 4')) {
        throw lastError;
      }

      // Log retry attempt
      if (attempt < RETRY_ATTEMPTS) {
        console.error(`Attempt ${attempt} failed: ${lastError.message}. Retrying in ${RETRY_DELAY_MS}ms...`);
        await sleep(RETRY_DELAY_MS * attempt); // Exponential backoff
      }
    }
  }

  throw new Error(`Failed after ${RETRY_ATTEMPTS} attempts: ${lastError?.message || 'Unknown error'}`);
}

// Check if server is available
async function isServerAvailable(): Promise<boolean> {
  try {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 2000);

    const response = await fetch(`${API_URL}/health`, {
      signal: controller.signal,
    });
    clearTimeout(timeoutId);

    return response.ok;
  } catch {
    return false;
  }
}

// Create MCP server
const server = new Server(
  {
    name: "shodh-memory",
    version: "0.1.5",
  },
  {
    capabilities: {
      tools: {},
      resources: {},
    },
  }
);

// List available tools
server.setRequestHandler(ListToolsRequestSchema, async () => {
  return {
    tools: [
      {
        name: "remember",
        description: "Store a memory for future recall. Use this to remember important information, decisions, user preferences, project context, or anything you want to recall later.",
        inputSchema: {
          type: "object",
          properties: {
            content: {
              type: "string",
              description: "The content to remember (observation, decision, learning, etc.)",
            },
            type: {
              type: "string",
              enum: ["Observation", "Decision", "Learning", "Error", "Discovery", "Pattern", "Context", "Task", "CodeEdit", "FileAccess", "Search", "Command", "Conversation"],
              description: "Type of memory",
              default: "Observation",
            },
            tags: {
              type: "array",
              items: { type: "string" },
              description: "Optional tags for categorization",
            },
          },
          required: ["content"],
        },
      },
      {
        name: "recall",
        description: "Search memories using different retrieval modes. Use this to find relevant past experiences, decisions, or context. Modes: 'semantic' (vector similarity), 'associative' (graph traversal - follows learned connections between memories), 'hybrid' (combines both with density-dependent weighting).",
        inputSchema: {
          type: "object",
          properties: {
            query: {
              type: "string",
              description: "Natural language search query",
            },
            limit: {
              type: "number",
              description: "Maximum number of results (default: 5)",
              default: 5,
            },
            mode: {
              type: "string",
              enum: ["semantic", "associative", "hybrid"],
              description: "Retrieval mode: 'semantic' for pure vector similarity, 'associative' for graph-based traversal (follows learned connections), 'hybrid' for density-dependent combination (default)",
              default: "hybrid",
            },
          },
          required: ["query"],
        },
      },
      {
        name: "context_summary",
        description: "Get a condensed summary of recent learnings, decisions, and context. Use this at the start of a session to quickly understand what you've learned before.",
        inputSchema: {
          type: "object",
          properties: {
            include_decisions: {
              type: "boolean",
              description: "Include recent decisions (default: true)",
              default: true,
            },
            include_learnings: {
              type: "boolean",
              description: "Include recent learnings (default: true)",
              default: true,
            },
            include_context: {
              type: "boolean",
              description: "Include project context (default: true)",
              default: true,
            },
            max_items: {
              type: "number",
              description: "Maximum items per category (default: 5)",
              default: 5,
            },
          },
        },
      },
      {
        name: "list_memories",
        description: "List all stored memories",
        inputSchema: {
          type: "object",
          properties: {
            limit: {
              type: "number",
              description: "Maximum number of results",
              default: 20,
            },
          },
        },
      },
      {
        name: "forget",
        description: "Delete a specific memory by ID",
        inputSchema: {
          type: "object",
          properties: {
            memory_id: {
              type: "string",
              description: "The ID of the memory to delete",
            },
          },
          required: ["memory_id"],
        },
      },
      {
        name: "memory_stats",
        description: "Get statistics about stored memories",
        inputSchema: {
          type: "object",
          properties: {},
        },
      },
      {
        name: "recall_by_tags",
        description: "Search memories by tags. Returns memories matching ANY of the provided tags.",
        inputSchema: {
          type: "object",
          properties: {
            tags: {
              type: "array",
              items: { type: "string" },
              description: "Tags to search for (returns memories matching ANY tag)",
            },
            limit: {
              type: "number",
              description: "Maximum number of results (default: 20)",
              default: 20,
            },
          },
          required: ["tags"],
        },
      },
      {
        name: "recall_by_date",
        description: "Search memories within a date range.",
        inputSchema: {
          type: "object",
          properties: {
            start: {
              type: "string",
              description: "Start date (ISO 8601 format, e.g., '2024-01-01T00:00:00Z')",
            },
            end: {
              type: "string",
              description: "End date (ISO 8601 format, e.g., '2024-12-31T23:59:59Z')",
            },
            limit: {
              type: "number",
              description: "Maximum number of results (default: 20)",
              default: 20,
            },
          },
          required: ["start", "end"],
        },
      },
      {
        name: "forget_by_tags",
        description: "Delete memories matching ANY of the provided tags.",
        inputSchema: {
          type: "object",
          properties: {
            tags: {
              type: "array",
              items: { type: "string" },
              description: "Tags to match for deletion",
            },
          },
          required: ["tags"],
        },
      },
      {
        name: "forget_by_date",
        description: "Delete memories within a date range.",
        inputSchema: {
          type: "object",
          properties: {
            start: {
              type: "string",
              description: "Start date (ISO 8601 format)",
            },
            end: {
              type: "string",
              description: "End date (ISO 8601 format)",
            },
          },
          required: ["start", "end"],
        },
      },
      {
        name: "consolidation_report",
        description: "Get a report of what the memory system has been learning. Shows memory strengthening/decay events, edge formation, fact extraction, and maintenance cycles. Use this to understand how your memories are evolving.",
        inputSchema: {
          type: "object",
          properties: {
            since: {
              type: "string",
              description: "Start of report period (ISO 8601 format). Defaults to 24 hours ago.",
            },
            until: {
              type: "string",
              description: "End of report period (ISO 8601 format). Defaults to now.",
            },
          },
        },
      },
    ],
  };
});

// Handle tool calls
server.setRequestHandler(CallToolRequestSchema, async (request) => {
  const { name, arguments: args } = request.params;

  // Check server availability first
  const serverUp = await isServerAvailable();
  if (!serverUp) {
    return {
      content: [
        {
          type: "text",
          text: `Memory server unavailable at ${API_URL}. Please ensure shodh-memory-server is running.\n\nTo start: cd shodh-memory && cargo run`,
        },
      ],
      isError: true,
    };
  }

  try {
    switch (name) {
      case "remember": {
        const { content, type = "Observation", tags = [] } = args as {
          content: string;
          type?: string;
          tags?: string[];
        };

        const result = await apiCall<{ memory_id: string }>("/api/record", "POST", {
          user_id: USER_ID,
          experience: {
            content,
            experience_type: type,
            tags,
          },
        });

        return {
          content: [
            {
              type: "text",
              text: `Remembered: "${content.slice(0, 50)}${content.length > 50 ? '...' : ''}"\nMemory ID: ${result.memory_id}`,
            },
          ],
        };
      }

      case "recall": {
        const { query, limit = 5, mode = "hybrid" } = args as { query: string; limit?: number; mode?: string };

        interface RetrievalStats {
          mode: string;
          semantic_candidates: number;
          graph_candidates: number;
          graph_density: number;
          graph_weight: number;
          semantic_weight: number;
          graph_hops: number;
          entities_activated: number;
          retrieval_time_us: number;
        }

        interface RecallResponse {
          memories: Memory[];
          count: number;
          retrieval_stats?: RetrievalStats;
        }

        const result = await apiCall<RecallResponse>("/api/recall", "POST", {
          user_id: USER_ID,
          query,
          limit,
          mode,
        });

        const memories = result.memories || [];
        const stats = result.retrieval_stats;

        if (memories.length === 0) {
          return {
            content: [
              {
                type: "text",
                text: `No memories found for: "${query}" (mode: ${mode})`,
              },
            ],
          };
        }

        const formatted = memories
          .map((m, i) => {
            const content = getContent(m);
            const score = ((m.score || 0) * 100).toFixed(0);
            return `${i + 1}. [${score}% match] ${content}\n   Type: ${getType(m)} | ID: ${m.id.slice(0, 8)}...`;
          })
          .join("\n\n");

        // Build stats summary for associative/hybrid modes
        let statsText = "";
        if (stats && (mode === "associative" || mode === "hybrid")) {
          const graphPct = (stats.graph_weight * 100).toFixed(0);
          const semPct = (stats.semantic_weight * 100).toFixed(0);
          statsText = `\n\n[Stats: ${stats.mode} mode | graph=${graphPct}% semantic=${semPct}% | density=${stats.graph_density.toFixed(2)} | ${stats.graph_candidates} graph + ${stats.semantic_candidates} semantic candidates | ${stats.entities_activated} entities | ${(stats.retrieval_time_us / 1000).toFixed(1)}ms]`;
        }

        return {
          content: [
            {
              type: "text",
              text: `Found ${memories.length} relevant memories (${mode} mode):\n\n${formatted}${statsText}`,
            },
          ],
        };
      }

      case "context_summary": {
        const {
          include_decisions = true,
          include_learnings = true,
          include_context = true,
          max_items = 5,
        } = args as {
          include_decisions?: boolean;
          include_learnings?: boolean;
          include_context?: boolean;
          max_items?: number;
        };

        // Fetch all memories
        const result = await apiCall<{ memories: Memory[] }>("/api/memories", "POST", {
          user_id: USER_ID,
        });

        const memories = result.memories || [];

        if (memories.length === 0) {
          return {
            content: [
              {
                type: "text",
                text: "No memories stored yet. Start remembering things to build context!",
              },
            ],
          };
        }

        // Categorize memories
        const decisions: Memory[] = [];
        const learnings: Memory[] = [];
        const context: Memory[] = [];
        const patterns: Memory[] = [];
        const errors: Memory[] = [];

        for (const m of memories) {
          const type = getType(m);
          switch (type) {
            case 'Decision':
              decisions.push(m);
              break;
            case 'Learning':
              learnings.push(m);
              break;
            case 'Context':
              context.push(m);
              break;
            case 'Pattern':
              patterns.push(m);
              break;
            case 'Error':
              errors.push(m);
              break;
          }
        }

        // Build summary
        const sections: string[] = [];

        if (include_context && context.length > 0) {
          const items = context.slice(0, max_items).map(m => `  - ${getContent(m).slice(0, 100)}`);
          sections.push(`PROJECT CONTEXT:\n${items.join('\n')}`);
        }

        if (include_decisions && decisions.length > 0) {
          const items = decisions.slice(0, max_items).map(m => `  - ${getContent(m).slice(0, 100)}`);
          sections.push(`DECISIONS MADE:\n${items.join('\n')}`);
        }

        if (include_learnings && learnings.length > 0) {
          const items = learnings.slice(0, max_items).map(m => `  - ${getContent(m).slice(0, 100)}`);
          sections.push(`LEARNINGS:\n${items.join('\n')}`);
        }

        if (patterns.length > 0) {
          const items = patterns.slice(0, max_items).map(m => `  - ${getContent(m).slice(0, 100)}`);
          sections.push(`PATTERNS NOTICED:\n${items.join('\n')}`);
        }

        if (errors.length > 0) {
          const items = errors.slice(0, Math.min(3, max_items)).map(m => `  - ${getContent(m).slice(0, 100)}`);
          sections.push(`ERRORS TO AVOID:\n${items.join('\n')}`);
        }

        const summary = sections.length > 0
          ? sections.join('\n\n')
          : `${memories.length} memories stored, but none categorized as decisions, learnings, or context. Consider using those types when remembering.`;

        return {
          content: [
            {
              type: "text",
              text: `CONTEXT SUMMARY (${memories.length} total memories)\n${'='.repeat(40)}\n\n${summary}`,
            },
          ],
        };
      }

      case "list_memories": {
        const { limit = 20 } = args as { limit?: number };

        const result = await apiCall<{ memories: Memory[] }>("/api/memories", "POST", {
          user_id: USER_ID,
        });

        const memories = (result.memories || []).slice(0, limit);

        if (memories.length === 0) {
          return {
            content: [
              {
                type: "text",
                text: "No memories stored yet.",
              },
            ],
          };
        }

        const formatted = memories
          .map((m, i) => {
            const content = getContent(m);
            return `${i + 1}. ${content.slice(0, 80)}${content.length > 80 ? '...' : ''}\n   Type: ${getType(m)} | ID: ${m.id.slice(0, 8)}...`;
          })
          .join("\n\n");

        return {
          content: [
            {
              type: "text",
              text: `${memories.length} memories:\n\n${formatted}`,
            },
          ],
        };
      }

      case "forget": {
        const { memory_id } = args as { memory_id: string };

        await apiCall(`/api/memory/${memory_id}?user_id=${USER_ID}`, "DELETE");

        return {
          content: [
            {
              type: "text",
              text: `Deleted memory: ${memory_id}`,
            },
          ],
        };
      }

      case "memory_stats": {
        const result = await apiCall<Record<string, unknown>>(`/api/users/${USER_ID}/stats`, "GET");

        return {
          content: [
            {
              type: "text",
              text: `Memory Statistics:\n${JSON.stringify(result, null, 2)}`,
            },
          ],
        };
      }

      case "recall_by_tags": {
        const { tags, limit = 20 } = args as { tags: string[]; limit?: number };

        const result = await apiCall<{ memories: Memory[]; count: number }>("/api/recall/tags", "POST", {
          user_id: USER_ID,
          tags,
          limit,
        });

        const memories = result.memories || [];

        if (memories.length === 0) {
          return {
            content: [
              {
                type: "text",
                text: `No memories found with tags: ${tags.join(", ")}`,
              },
            ],
          };
        }

        const formatted = memories
          .map((m, i) => {
            const content = getContent(m);
            return `${i + 1}. ${content.slice(0, 80)}${content.length > 80 ? '...' : ''}\n   Type: ${getType(m)} | ID: ${m.id.slice(0, 8)}...`;
          })
          .join("\n\n");

        return {
          content: [
            {
              type: "text",
              text: `Found ${memories.length} memories with tags [${tags.join(", ")}]:\n\n${formatted}`,
            },
          ],
        };
      }

      case "recall_by_date": {
        const { start, end, limit = 20 } = args as { start: string; end: string; limit?: number };

        const result = await apiCall<{ memories: Memory[]; count: number }>("/api/recall/date", "POST", {
          user_id: USER_ID,
          start,
          end,
          limit,
        });

        const memories = result.memories || [];

        if (memories.length === 0) {
          return {
            content: [
              {
                type: "text",
                text: `No memories found between ${start} and ${end}`,
              },
            ],
          };
        }

        const formatted = memories
          .map((m, i) => {
            const content = getContent(m);
            return `${i + 1}. ${content.slice(0, 80)}${content.length > 80 ? '...' : ''}\n   Type: ${getType(m)} | Created: ${m.created_at || 'unknown'}`;
          })
          .join("\n\n");

        return {
          content: [
            {
              type: "text",
              text: `Found ${memories.length} memories between ${start} and ${end}:\n\n${formatted}`,
            },
          ],
        };
      }

      case "forget_by_tags": {
        const { tags } = args as { tags: string[] };

        const result = await apiCall<{ deleted_count: number }>("/api/forget/tags", "POST", {
          user_id: USER_ID,
          tags,
        });

        return {
          content: [
            {
              type: "text",
              text: `Deleted ${result.deleted_count} memories with tags: ${tags.join(", ")}`,
            },
          ],
        };
      }

      case "forget_by_date": {
        const { start, end } = args as { start: string; end: string };

        const result = await apiCall<{ deleted_count: number }>("/api/forget/date", "POST", {
          user_id: USER_ID,
          start,
          end,
        });

        return {
          content: [
            {
              type: "text",
              text: `Deleted ${result.deleted_count} memories between ${start} and ${end}`,
            },
          ],
        };
      }

      case "consolidation_report": {
        const { since, until } = args as { since?: string; until?: string };

        interface ConsolidationStats {
          total_memories: number;
          memories_strengthened: number;
          memories_decayed: number;
          memories_at_risk: number;
          edges_formed: number;
          edges_strengthened: number;
          edges_potentiated: number;
          edges_pruned: number;
          facts_extracted: number;
          facts_reinforced: number;
          maintenance_cycles: number;
          total_maintenance_duration_ms: number;
        }

        interface MemoryChange {
          memory_id: string;
          content_preview: string;
          activation_before: number;
          activation_after: number;
          change_reason: string;
          at_risk: boolean;
          timestamp: string;
        }

        interface AssociationChange {
          from_memory_id: string;
          to_memory_id: string;
          strength_before: number | null;
          strength_after: number;
          co_activations: number | null;
          reason: string;
          timestamp: string;
        }

        interface ConsolidationReport {
          period: {
            start: string;
            end: string;
          };
          strengthened_memories: MemoryChange[];
          decayed_memories: MemoryChange[];
          formed_associations: AssociationChange[];
          strengthened_associations: AssociationChange[];
          potentiated_associations: AssociationChange[];
          pruned_associations: AssociationChange[];
          extracted_facts: unknown[];
          reinforced_facts: unknown[];
          statistics: ConsolidationStats;
        }

        const result = await apiCall<ConsolidationReport>("/api/consolidation/report", "POST", {
          user_id: USER_ID,
          since,
          until,
        });

        const stats = result.statistics;
        const sections: string[] = [];

        // Calculate event count
        const eventCount =
          result.strengthened_memories.length +
          result.decayed_memories.length +
          result.formed_associations.length +
          result.strengthened_associations.length +
          result.potentiated_associations.length +
          result.pruned_associations.length +
          result.extracted_facts.length +
          result.reinforced_facts.length;

        // Summary header
        sections.push(`CONSOLIDATION REPORT (${eventCount} events)`);
        sections.push(`Period: ${result.period.start} to ${result.period.end}`);
        sections.push('='.repeat(50));

        // Memory changes
        if (stats.memories_strengthened > 0 || stats.memories_decayed > 0 || stats.memories_at_risk > 0) {
          const memoryLines: string[] = [];
          if (stats.memories_strengthened > 0) memoryLines.push(`  + ${stats.memories_strengthened} memories strengthened`);
          if (stats.memories_decayed > 0) memoryLines.push(`  - ${stats.memories_decayed} memories decayed`);
          if (stats.memories_at_risk > 0) memoryLines.push(`  ! ${stats.memories_at_risk} memories at risk of forgetting`);
          sections.push(`MEMORY CHANGES:\n${memoryLines.join('\n')}`);
        }

        // Edge changes (associations)
        if (stats.edges_formed > 0 || stats.edges_strengthened > 0 || stats.edges_potentiated > 0 || stats.edges_pruned > 0) {
          const edgeLines: string[] = [];
          if (stats.edges_formed > 0) edgeLines.push(`  + ${stats.edges_formed} new associations formed`);
          if (stats.edges_strengthened > 0) edgeLines.push(`  + ${stats.edges_strengthened} associations strengthened`);
          if (stats.edges_potentiated > 0) edgeLines.push(`  * ${stats.edges_potentiated} associations became permanent (LTP)`);
          if (stats.edges_pruned > 0) edgeLines.push(`  - ${stats.edges_pruned} weak associations pruned`);
          sections.push(`ASSOCIATIONS (Hebbian Learning):\n${edgeLines.join('\n')}`);
        }

        // Fact changes
        if (stats.facts_extracted > 0 || stats.facts_reinforced > 0) {
          const factLines: string[] = [];
          if (stats.facts_extracted > 0) factLines.push(`  + ${stats.facts_extracted} facts extracted`);
          if (stats.facts_reinforced > 0) factLines.push(`  + ${stats.facts_reinforced} facts reinforced`);
          sections.push(`FACTS:\n${factLines.join('\n')}`);
        }

        // Maintenance cycles
        if (stats.maintenance_cycles > 0) {
          const durationSec = (stats.total_maintenance_duration_ms / 1000).toFixed(2);
          sections.push(`MAINTENANCE: ${stats.maintenance_cycles} cycle(s) completed (${durationSec}s total)`);
        }

        // No activity message
        if (eventCount === 0) {
          sections.push('No consolidation activity in this period. Store and access memories to trigger learning.');
        }

        return {
          content: [
            {
              type: "text",
              text: sections.join('\n\n'),
            },
          ],
        };
      }

      default:
        throw new Error(`Unknown tool: ${name}`);
    }
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);

    // Provide helpful error messages
    let helpText = '';
    if (message.includes('ECONNREFUSED') || message.includes('fetch failed')) {
      helpText = '\n\nThe memory server appears to be offline. Start it with:\n  cd shodh-memory && cargo run';
    } else if (message.includes('API error 401')) {
      helpText = '\n\nAuthentication failed. Check your SHODH_API_KEY.';
    } else if (message.includes('API error 404')) {
      helpText = '\n\nEndpoint not found. The server may be running an older version.';
    }

    return {
      content: [
        {
          type: "text",
          text: `Error: ${message}${helpText}`,
        },
      ],
      isError: true,
    };
  }
});

// List resources (memories as browsable resources)
server.setRequestHandler(ListResourcesRequestSchema, async () => {
  try {
    const result = await apiCall<{ memories: Memory[] }>("/api/memories", "POST", {
      user_id: USER_ID,
    });

    const memories = result.memories || [];

    return {
      resources: memories.slice(0, 50).map((m) => {
        const content = getContent(m);
        return {
          uri: `memory://${m.id}`,
          name: content.slice(0, 50) + (content.length > 50 ? "..." : ""),
          mimeType: "text/plain",
          description: `Type: ${getType(m)}`,
        };
      }),
    };
  } catch {
    return { resources: [] };
  }
});

// Read a specific memory resource
server.setRequestHandler(ReadResourceRequestSchema, async (request) => {
  const uri = request.params.uri;
  const memoryId = uri.replace("memory://", "");

  try {
    const result = await apiCall<{ memories: Memory[] }>("/api/memories", "POST", {
      user_id: USER_ID,
    });

    const memory = (result.memories || []).find((m) => m.id === memoryId);

    if (!memory) {
      throw new Error(`Memory not found: ${memoryId}`);
    }

    const content = getContent(memory);

    return {
      contents: [
        {
          uri,
          mimeType: "text/plain",
          text: `Content: ${content}\n\nType: ${getType(memory)}\nCreated: ${memory.created_at || "unknown"}\nID: ${memory.id}`,
        },
      ],
    };
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    throw new Error(`Failed to read memory: ${message}`);
  }
});

// Start server
async function main() {
  const transport = new StdioServerTransport();
  await server.connect(transport);
  console.error("Shodh-Memory MCP server v0.1.5 running");
  console.error(`Connecting to: ${API_URL}`);
  console.error(`User ID: ${USER_ID}`);
}

main().catch(console.error);
