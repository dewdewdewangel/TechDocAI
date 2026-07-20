# Security Policy

## Supported versions

TechDoc AI is currently an active MVP. Security fixes are applied to the
latest commit on the default branch; older commits and local forks are not
maintained as supported releases.

## Reporting a vulnerability

Please do not disclose suspected vulnerabilities in a public issue. Use
GitHub's private vulnerability reporting for this repository. Include the
affected component, reproduction steps, impact, and any suggested mitigation.

Do not include real API keys, passwords, uploaded documents, personal data, or
other secrets in a report. Use synthetic examples and redact logs before
attaching them.

## Deployment responsibility

The repository contains an MVP and is not a managed service. Operators must
replace all placeholder secrets, restrict database and administration
endpoints, protect metrics, keep dependencies updated, and back up PostgreSQL,
Redis, and uploaded files before exposing a deployment to untrusted networks.
