# Using Cliche Data in Documentation

When writing documentation, **never include real data** from your codebase, configuration, or task context. Documentation must use only generic, commonly recognized placeholder data.

## When to Use

- Writing or updating READMEs, CHANGELOGs, or files under a `docs/` directory
- Creating example code or configuration templates for public consumption
- Documenting features that reference account names, credentials, or organization-specific paths

**Do NOT use** when the output is a local runtime script, configuration file, or git-ignored file that needs real data to function.

## The Core Rule

> **If data came from a prompt, a local file, a script, a config, or a task — it does NOT go into documentation.**
>
> Documentation examples use only well-known, fictional, or obviously placeholder data.

## What Counts as Real Data

Any value that originates from:

- Local configuration files (e.g., `config.json`, `.env`, account modules)
- Scripts and task files (e.g., batch scripts, shell scripts, task runners)
- Prompt context (e.g., data the user supplies when asking an agent to build or update the tool)
- Map or filter files (e.g., JSON mappings, data extraction rules)
- Git-ignored files (e.g., files excluded from version control that contain environment-specific values)

## Approved Placeholder Data

Use these generic, cliche substitutes in all documentation and examples:

| Category | Approved Placeholder Examples |
|----------|-------------------------------|
| **People** | Jane Doe, John Smith, Alice, Bob |
| **Email addresses** | `jane.doe@example.com`, `admin@example.org` |
| **Organizations** | Acme Corp, Contoso, Northwind Traders |
| **Domains** | `example.com`, `example.org`, `example.net` |
| **Addresses** | 123 Main Street, Suite 100, Springfield |
| **Phone numbers** | `(555) 123-4567` |
| **Accounts / usernames** | `demo-user`, `test-account` |
| **File paths** | `accounts/acme.mjs`, `config/reports.json` |
| **Project names** | My Project, Sample App, Demo Tool |

## The Boundary Between Code and Docs

| Context | Real Data Allowed? |
|---------|-------------------|
| Local scripts and config files used at runtime | Yes |
| Git-ignored files with environment-specific values | Yes |
| Prompt data provided to build or configure the tool | Yes (in code only) |
| README.md, docs/ folder, and example templates | **No — use placeholders only** |
| CHANGELOG.md entries | **No — describe changes generically** |
| Code comments in committed source files | **No — keep generic** |

## Summary

Documentation is public. Implementation data is private. Keep them separate. Every example in every doc file should pass a simple test: *could a stranger read this and learn nothing about the real users, clients, or organizations behind this tool?* If the answer is no, replace the data with cliche placeholders.
