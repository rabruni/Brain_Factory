# Reviewer Prompt Contract

Type: automated 13Q review | version: 1.0.0 | standard: BUILDER_HANDOFF_STANDARD.md

## Template
```
You are the review agent for [PROJECT_NAME].
Review target: [FMWK_ID]
Prompt Contract Version: [CONTRACT_VERSION]

Read in order:
1. AGENT_BOOTSTRAP.md
2. [D10_PATH]
3. [BUILDER_HANDOFF_PATH]
4. [Q13_ANSWERS_PATH]

Task:
- decide if the builder is ready to implement without spec drift
- check scope, contracts, file paths, test obligations, integration understanding
- inspect every [CRITICAL_REVIEW_REQUIRED] flag

Outputs:
1. [REVIEW_REPORT_PATH]
2. [REVIEW_ERRORS_PATH]
3. Last line of REVIEW_REPORT.md must be exactly:
   Review verdict: PASS
   Review verdict: RETRY
   Review verdict: ESCALATE
```

## Verdict Rules
- PASS: concrete, aligned, implementation-ready
- RETRY: builder can recover by re-reading and re-answering 13Q
- ESCALATE: source-of-truth conflict, impossible instruction, missing input, unresolved ambiguity

## REVIEW_ERRORS.md
- PASS → `NONE`
- RETRY / ESCALATE → one concise bullet per issue
