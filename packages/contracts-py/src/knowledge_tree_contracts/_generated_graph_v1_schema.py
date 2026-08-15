"""Generated from docs/contracts/knowledge-tree-graph.v1.schema.json.

Do not hand-edit. Re-run: pnpm --filter @knowledge-tree/contracts-ts generate
"""

GRAPH_V1_SCHEMA_JSON = r"""{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://knowledge-tree.local/contracts/knowledge-tree-graph.v1.schema.json",
  "title": "Knowledge Tree graph contracts v1",
  "oneOf": [
    {
      "$ref": "#/$defs/Anchor"
    },
    {
      "$ref": "#/$defs/CourseGraph"
    },
    {
      "$ref": "#/$defs/GraphPatch"
    }
  ],
  "$defs": {
    "UuidV7": {
      "type": "string",
      "format": "uuidv7"
    },
    "Sha256": {
      "type": "string",
      "format": "sha256"
    },
    "Origin": {
      "type": "string",
      "enum": [
        "user",
        "ai",
        "import",
        "system"
      ]
    },
    "ReviewState": {
      "type": "string",
      "enum": [
        "unsupported_draft",
        "proposed",
        "accepted",
        "locked",
        "rejected"
      ]
    },
    "EdgeType": {
      "type": "string",
      "enum": [
        "prerequisite_of",
        "related_to",
        "part_of",
        "example_of"
      ]
    },
    "LockDimension": {
      "type": "string",
      "enum": [
        "content",
        "relations",
        "position",
        "annotations"
      ]
    },
    "Locks": {
      "type": "object",
      "additionalProperties": false,
      "required": [
        "content",
        "relations",
        "position",
        "annotations"
      ],
      "properties": {
        "content": {
          "type": "boolean"
        },
        "relations": {
          "type": "boolean"
        },
        "position": {
          "type": "boolean"
        },
        "annotations": {
          "type": "boolean"
        }
      }
    },
    "Annotation": {
      "type": "object",
      "additionalProperties": false,
      "required": [
        "kind",
        "value"
      ],
      "properties": {
        "kind": {
          "type": "string",
          "pattern": "^[a-z][a-z0-9_]{0,63}$"
        },
        "value": {
          "type": [
            "string",
            "number",
            "boolean",
            "null"
          ],
          "maxLength": 512
        }
      }
    },
    "Concept": {
      "type": "object",
      "additionalProperties": false,
      "required": [
        "id",
        "course_id",
        "label",
        "origin",
        "review_state",
        "confidence",
        "evidence_ids",
        "locks",
        "annotations",
        "revision_no"
      ],
      "properties": {
        "id": {
          "$ref": "#/$defs/UuidV7"
        },
        "course_id": {
          "$ref": "#/$defs/UuidV7"
        },
        "label": {
          "type": "string",
          "minLength": 1,
          "maxLength": 200
        },
        "origin": {
          "$ref": "#/$defs/Origin"
        },
        "review_state": {
          "$ref": "#/$defs/ReviewState"
        },
        "confidence": {
          "oneOf": [
            {
              "type": "null"
            },
            {
              "type": "number",
              "minimum": 0,
              "maximum": 1
            }
          ]
        },
        "evidence_ids": {
          "type": "array",
          "items": {
            "$ref": "#/$defs/UuidV7"
          },
          "uniqueItems": true,
          "maxItems": 100
        },
        "locks": {
          "$ref": "#/$defs/Locks"
        },
        "annotations": {
          "type": "array",
          "items": {
            "$ref": "#/$defs/Annotation"
          },
          "maxItems": 100
        },
        "revision_no": {
          "type": "integer",
          "minimum": 0
        }
      }
    },
    "ConceptEdge": {
      "type": "object",
      "additionalProperties": false,
      "required": [
        "id",
        "course_id",
        "source_concept_id",
        "target_concept_id",
        "edge_type",
        "origin",
        "review_state",
        "confidence",
        "evidence_ids",
        "locked",
        "revision_no"
      ],
      "properties": {
        "id": {
          "$ref": "#/$defs/UuidV7"
        },
        "course_id": {
          "$ref": "#/$defs/UuidV7"
        },
        "source_concept_id": {
          "$ref": "#/$defs/UuidV7"
        },
        "target_concept_id": {
          "$ref": "#/$defs/UuidV7"
        },
        "edge_type": {
          "$ref": "#/$defs/EdgeType"
        },
        "origin": {
          "$ref": "#/$defs/Origin"
        },
        "review_state": {
          "$ref": "#/$defs/ReviewState"
        },
        "confidence": {
          "oneOf": [
            {
              "type": "null"
            },
            {
              "type": "number",
              "minimum": 0,
              "maximum": 1
            }
          ]
        },
        "evidence_ids": {
          "type": "array",
          "items": {
            "$ref": "#/$defs/UuidV7"
          },
          "uniqueItems": true,
          "maxItems": 100
        },
        "locked": {
          "type": "boolean"
        },
        "revision_no": {
          "type": "integer",
          "minimum": 0
        }
      }
    },
    "LayoutItem": {
      "type": "object",
      "additionalProperties": false,
      "required": [
        "view_id",
        "concept_id",
        "x",
        "y",
        "pinned",
        "revision_no"
      ],
      "properties": {
        "view_id": {
          "$ref": "#/$defs/UuidV7"
        },
        "concept_id": {
          "$ref": "#/$defs/UuidV7"
        },
        "x": {
          "type": "number",
          "minimum": -1000000,
          "maximum": 1000000
        },
        "y": {
          "type": "number",
          "minimum": -1000000,
          "maximum": 1000000
        },
        "pinned": {
          "type": "boolean"
        },
        "revision_no": {
          "type": "integer",
          "minimum": 0
        }
      }
    },
    "SourceState": {
      "type": "object",
      "additionalProperties": false,
      "required": [
        "content_hash",
        "parser",
        "parser_version"
      ],
      "properties": {
        "content_hash": {
          "$ref": "#/$defs/Sha256"
        },
        "parser": {
          "type": "string",
          "pattern": "^[a-zA-Z0-9][a-zA-Z0-9_.-]{0,63}$"
        },
        "parser_version": {
          "type": "string",
          "minLength": 1,
          "maxLength": 64
        }
      }
    },
    "PageBboxSelector": {
      "type": "object",
      "additionalProperties": false,
      "required": [
        "type",
        "page",
        "bbox_norm"
      ],
      "properties": {
        "type": {
          "const": "page_bbox"
        },
        "page": {
          "type": "integer",
          "minimum": 1
        },
        "bbox_norm": {
          "type": "array",
          "prefixItems": [
            {
              "type": "number",
              "minimum": 0,
              "maximum": 1
            },
            {
              "type": "number",
              "minimum": 0,
              "maximum": 1
            },
            {
              "type": "number",
              "minimum": 0,
              "maximum": 1
            },
            {
              "type": "number",
              "minimum": 0,
              "maximum": 1
            }
          ],
          "items": false,
          "minItems": 4,
          "maxItems": 4
        }
      }
    },
    "TextQuoteSelector": {
      "type": "object",
      "additionalProperties": false,
      "required": [
        "type",
        "exact"
      ],
      "properties": {
        "type": {
          "const": "text_quote"
        },
        "exact": {
          "type": "string",
          "minLength": 1,
          "maxLength": 512
        },
        "prefix": {
          "type": "string",
          "maxLength": 128
        },
        "suffix": {
          "type": "string",
          "maxLength": 128
        }
      }
    },
    "TextPositionSelector": {
      "type": "object",
      "additionalProperties": false,
      "required": [
        "type",
        "start",
        "end"
      ],
      "properties": {
        "type": {
          "const": "text_position"
        },
        "start": {
          "type": "integer",
          "minimum": 0
        },
        "end": {
          "type": "integer",
          "minimum": 1
        }
      }
    },
    "HeadingPathSelector": {
      "type": "object",
      "additionalProperties": false,
      "required": [
        "type",
        "path"
      ],
      "properties": {
        "type": {
          "const": "heading_path"
        },
        "path": {
          "type": "array",
          "items": {
            "type": "string",
            "minLength": 1,
            "maxLength": 200
          },
          "minItems": 1,
          "maxItems": 32
        }
      }
    },
    "Selector": {
      "oneOf": [
        {
          "$ref": "#/$defs/PageBboxSelector"
        },
        {
          "$ref": "#/$defs/TextQuoteSelector"
        },
        {
          "$ref": "#/$defs/TextPositionSelector"
        },
        {
          "$ref": "#/$defs/HeadingPathSelector"
        }
      ]
    },
    "Anchor": {
      "type": "object",
      "additionalProperties": false,
      "required": [
        "schema_version",
        "resource_id",
        "resource_version_id",
        "source_state",
        "selectors",
        "status"
      ],
      "properties": {
        "schema_version": {
          "const": 1
        },
        "resource_id": {
          "$ref": "#/$defs/UuidV7"
        },
        "resource_version_id": {
          "$ref": "#/$defs/UuidV7"
        },
        "source_state": {
          "$ref": "#/$defs/SourceState"
        },
        "selectors": {
          "type": "array",
          "items": {
            "$ref": "#/$defs/Selector"
          },
          "minItems": 1,
          "maxItems": 16
        },
        "status": {
          "type": "string",
          "enum": [
            "valid",
            "recovered",
            "ambiguous",
            "drifted",
            "missing"
          ]
        }
      }
    },
    "CourseGraph": {
      "type": "object",
      "additionalProperties": false,
      "required": [
        "schema_version",
        "workspace_id",
        "course_id",
        "revision_no",
        "concepts",
        "edges",
        "layout_items"
      ],
      "properties": {
        "schema_version": {
          "const": 1
        },
        "workspace_id": {
          "$ref": "#/$defs/UuidV7"
        },
        "course_id": {
          "$ref": "#/$defs/UuidV7"
        },
        "revision_no": {
          "type": "integer",
          "minimum": 0
        },
        "concepts": {
          "type": "array",
          "items": {
            "$ref": "#/$defs/Concept"
          },
          "maxItems": 10000
        },
        "edges": {
          "type": "array",
          "items": {
            "$ref": "#/$defs/ConceptEdge"
          },
          "maxItems": 50000
        },
        "layout_items": {
          "type": "array",
          "items": {
            "$ref": "#/$defs/LayoutItem"
          },
          "maxItems": 10000
        }
      }
    },
    "Actor": {
      "type": "object",
      "additionalProperties": false,
      "required": [
        "type",
        "id"
      ],
      "properties": {
        "type": {
          "$ref": "#/$defs/Origin"
        },
        "id": {
          "type": "string",
          "minLength": 1,
          "maxLength": 100
        }
      }
    },
    "ConceptTarget": {
      "type": "object",
      "additionalProperties": false,
      "required": [
        "type",
        "id"
      ],
      "properties": {
        "type": {
          "const": "concept"
        },
        "id": {
          "$ref": "#/$defs/UuidV7"
        }
      }
    },
    "CreateConceptOperation": {
      "type": "object",
      "additionalProperties": false,
      "required": [
        "op_id",
        "op",
        "concept"
      ],
      "properties": {
        "op_id": {
          "$ref": "#/$defs/UuidV7"
        },
        "op": {
          "const": "create_concept"
        },
        "concept": {
          "$ref": "#/$defs/Concept"
        }
      }
    },
    "ConceptChanges": {
      "type": "object",
      "additionalProperties": false,
      "minProperties": 1,
      "properties": {
        "label": {
          "type": "string",
          "minLength": 1,
          "maxLength": 200
        },
        "review_state": {
          "$ref": "#/$defs/ReviewState"
        },
        "confidence": {
          "oneOf": [
            {
              "type": "null"
            },
            {
              "type": "number",
              "minimum": 0,
              "maximum": 1
            }
          ]
        },
        "evidence_ids": {
          "type": "array",
          "items": {
            "$ref": "#/$defs/UuidV7"
          },
          "uniqueItems": true,
          "maxItems": 100
        }
      }
    },
    "UpdateConceptOperation": {
      "type": "object",
      "additionalProperties": false,
      "required": [
        "op_id",
        "op",
        "target",
        "expected_updated_revision_no",
        "evidence_ids",
        "changes"
      ],
      "properties": {
        "op_id": {
          "$ref": "#/$defs/UuidV7"
        },
        "op": {
          "const": "update_concept"
        },
        "target": {
          "$ref": "#/$defs/ConceptTarget"
        },
        "expected_updated_revision_no": {
          "type": "integer",
          "minimum": 0
        },
        "evidence_ids": {
          "type": "array",
          "items": {
            "$ref": "#/$defs/UuidV7"
          },
          "uniqueItems": true,
          "maxItems": 100
        },
        "changes": {
          "$ref": "#/$defs/ConceptChanges"
        }
      }
    },
    "CreateEdgeOperation": {
      "type": "object",
      "additionalProperties": false,
      "required": [
        "op_id",
        "op",
        "expected_source_revision_no",
        "expected_target_revision_no",
        "edge"
      ],
      "properties": {
        "op_id": {
          "$ref": "#/$defs/UuidV7"
        },
        "op": {
          "const": "create_edge"
        },
        "expected_source_revision_no": {
          "type": "integer",
          "minimum": 0
        },
        "expected_target_revision_no": {
          "type": "integer",
          "minimum": 0
        },
        "edge": {
          "$ref": "#/$defs/ConceptEdge"
        }
      }
    },
    "SetLockOperation": {
      "type": "object",
      "additionalProperties": false,
      "required": [
        "op_id",
        "op",
        "target",
        "expected_updated_revision_no",
        "dimension",
        "value"
      ],
      "properties": {
        "op_id": {
          "$ref": "#/$defs/UuidV7"
        },
        "op": {
          "const": "set_lock"
        },
        "target": {
          "$ref": "#/$defs/ConceptTarget"
        },
        "expected_updated_revision_no": {
          "type": "integer",
          "minimum": 0
        },
        "dimension": {
          "$ref": "#/$defs/LockDimension"
        },
        "value": {
          "type": "boolean"
        }
      }
    },
    "UpsertAnnotationOperation": {
      "type": "object",
      "additionalProperties": false,
      "required": [
        "op_id",
        "op",
        "target",
        "expected_updated_revision_no",
        "annotation"
      ],
      "properties": {
        "op_id": {
          "$ref": "#/$defs/UuidV7"
        },
        "op": {
          "const": "upsert_annotation"
        },
        "target": {
          "$ref": "#/$defs/ConceptTarget"
        },
        "expected_updated_revision_no": {
          "type": "integer",
          "minimum": 0
        },
        "annotation": {
          "$ref": "#/$defs/Annotation"
        }
      }
    },
    "SetLayoutItemOperation": {
      "type": "object",
      "additionalProperties": false,
      "required": [
        "op_id",
        "op",
        "target",
        "expected_updated_revision_no",
        "layout_item"
      ],
      "properties": {
        "op_id": {
          "$ref": "#/$defs/UuidV7"
        },
        "op": {
          "const": "set_layout_item"
        },
        "target": {
          "$ref": "#/$defs/ConceptTarget"
        },
        "expected_updated_revision_no": {
          "type": "integer",
          "minimum": 0
        },
        "layout_item": {
          "$ref": "#/$defs/LayoutItem"
        }
      }
    },
    "EdgeTarget": {
      "type": "object",
      "additionalProperties": false,
      "required": [
        "type",
        "id"
      ],
      "properties": {
        "type": {
          "const": "edge"
        },
        "id": {
          "$ref": "#/$defs/UuidV7"
        }
      }
    },
    "DeleteConceptOperation": {
      "type": "object",
      "additionalProperties": false,
      "required": [
        "op_id",
        "op",
        "target",
        "expected_updated_revision_no"
      ],
      "properties": {
        "op_id": {
          "$ref": "#/$defs/UuidV7"
        },
        "op": {
          "const": "delete_concept"
        },
        "target": {
          "$ref": "#/$defs/ConceptTarget"
        },
        "expected_updated_revision_no": {
          "type": "integer",
          "minimum": 0
        }
      }
    },
    "DeleteEdgeOperation": {
      "type": "object",
      "additionalProperties": false,
      "required": [
        "op_id",
        "op",
        "target"
      ],
      "properties": {
        "op_id": {
          "$ref": "#/$defs/UuidV7"
        },
        "op": {
          "const": "delete_edge"
        },
        "target": {
          "$ref": "#/$defs/EdgeTarget"
        }
      }
    },
    "Operation": {
      "oneOf": [
        {
          "$ref": "#/$defs/CreateConceptOperation"
        },
        {
          "$ref": "#/$defs/UpdateConceptOperation"
        },
        {
          "$ref": "#/$defs/CreateEdgeOperation"
        },
        {
          "$ref": "#/$defs/SetLockOperation"
        },
        {
          "$ref": "#/$defs/UpsertAnnotationOperation"
        },
        {
          "$ref": "#/$defs/SetLayoutItemOperation"
        },
        {
          "$ref": "#/$defs/DeleteConceptOperation"
        },
        {
          "$ref": "#/$defs/DeleteEdgeOperation"
        }
      ]
    },
    "GraphPatch": {
      "type": "object",
      "additionalProperties": false,
      "required": [
        "schema_version",
        "patch_id",
        "workspace_id",
        "course_id",
        "base_revision_no",
        "actor",
        "reason",
        "requires_confirmation",
        "confirmed",
        "operations"
      ],
      "properties": {
        "schema_version": {
          "const": 1
        },
        "patch_id": {
          "$ref": "#/$defs/UuidV7"
        },
        "workspace_id": {
          "$ref": "#/$defs/UuidV7"
        },
        "course_id": {
          "$ref": "#/$defs/UuidV7"
        },
        "base_revision_no": {
          "type": "integer",
          "minimum": 0
        },
        "actor": {
          "$ref": "#/$defs/Actor"
        },
        "reason": {
          "type": "string",
          "minLength": 1,
          "maxLength": 500
        },
        "requires_confirmation": {
          "type": "boolean"
        },
        "confirmed": {
          "type": "boolean"
        },
        "operations": {
          "type": "array",
          "items": {
            "$ref": "#/$defs/Operation"
          },
          "minItems": 1,
          "maxItems": 5000
        }
      }
    }
  }
}"""
