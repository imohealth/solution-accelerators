# Section Priorities Guide for Entity Context Selection

This guide explains **where to look for context** based on the section where an entity is found.

The priority rules below are used by the notebook logic in the dynamic rules-based approaches.

## How to use this guide

- Identify the section where the entity appears.
- Start with that same section first (**self-context**).
- If more context is needed, add sections in the exact order listed.
- Stop when enough context is collected (the notebook currently limits context length).

## Section-to-Context Priority Map

| If entity is found in... | Look for context in this order |
|---|---|
| `assessment and plan` | `assessment` → `assessment and plan` → `hpi` → `problem list` → `history` → `physical exam` |
| `problem list` | `problem list` → `assessment` → `assessment and plan` → `hpi` → `reason for visit` |
| `hpi` | `hpi` → `assessment` → `assessment and plan` → `problem list` → `physical exam` → `review of systems` → `medical decision making` |
| `physical exam` | `physical exam` → `problem list` → `hpi` |
| `reason for visit` | `reason for visit` → `assessment` → `assessment and plan` → `hpi` |
| `review of systems` | `review of systems` → `hpi` → `assessment` → `assessment and plan` |
| `chief complaint` | `chief complaint` → `hpi` → `assessment` → `assessment and plan` |
| `impression` | `impression` → `hpi` → `problem list` |
| `medical decision making` | `medical decision making` → `assessment` → `assessment and plan` → `hpi` |
| `presenting complaint` | `presenting complaint` → `hpi` → `assessment` → `assessment and plan` |
| `patient instructions` | `patient instructions` → `assessment` → `assessment and plan` → `plan` |

## Normalization of section names (important)

The notebook normalizes similar section labels before applying priorities. Common examples:

- `history of present illness` and `history of present illness (hpi)` are treated as `hpi`.
- `reason` is treated as `reason for visit`.
- `physical examinations` is treated as `physical exam`.
- Variants containing both words `assessment` and `plan` are treated as `assessment and plan`.

## Fallback when section is not mapped

If the entity section does not match one of the rules above, the default fallback order is:

`assessment` → `assessment and plan` → `hpi` → `problem list` → `physical exam` → `plan` → `past medical history` → `history`

## Practical interpretation

- **Assessment / A&P / HPI / Problem List** usually carry the strongest diagnostic context.
- **Physical Exam / ROS / MDM** often refine specificity.
- **Reason for Visit / Chief Complaint / Presenting Complaint** help anchor encounter intent.
- For non-priority sections, use fallback conservatively or proceed with minimal/no context depending on your normalization strategy.
