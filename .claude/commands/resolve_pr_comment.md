# Analyze and Resolve PR review comment $ARGUMENTS.

## Purpose
Resolve PR comment workflow that integrates with GitHub PR, provides systematic analysis, and ensures quality through structured testing and validation.

---
## 🔹 PLAN

1. USe `gh pr view` to get PR details
2. Use `gh issue view` to get the issue details which the PR address
3. Understand the problem, implementation and comments.
   - Search relevant plan under <project_root>/plan
4. Ask clarifying questions if necessary regarding the comments.
5. Understand the prior art for this issue:
   - Search the scratchpads for previous thoughts related to the issue.
   - Search the codebase for relevant files.
6. Think harder about if need and/or how to address the comments.
7. Must Document your plan in a **new scratchpad** under <project_root>/plan:
   - Include the PR name in the filename prefixd by PR.
   - Include a link to the PR in the scratchpad.

Ask user for review and approval before move forward.
---

## 🔹 CREATE
- Use the same PR branch to address the issue.
- Solve the issue in small, manageable steps, according to plan
- Commit your changes after each step.

---
## 🔹 TEST

- Use **Puppeteer via MCP** to test the changes if you have made changes to the UI.
- Write **RSpec tests** to describe the expected behavior of your code.
- Run the **full test suite** to ensure you haven't broken anything.
- If the tests are **failing**, fix them.
- Ensure that **all tests are passing** before moving on to the next step.
---

## 🔹 DEPLOY
- Commit and Push the updates

Remember to use the GITHUB CLI (`gh`) for all github related issues.

