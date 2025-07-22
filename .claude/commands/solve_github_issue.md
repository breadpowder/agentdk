Please analyze and fix the GitHub issue: $ARGUMENTS.

Follow these steps:
## 🔹 PLAN

1. Use `gh issue view` to get the issue details.
2. Understand the problem described in the issue.
3. Ask clarifying questions if necessary from PR comments.
4. Understand the prior art for this issue:
   - Search for other github issues and looking for potential dependancies which makes you better plan for future. 
   - Search the scratchpads  under <project_root>/plan for previous thoughts related to the issue.
   - Search PRs to see if you can find history on this issue.
   - Search the codebase for relevant files.
5. Think harder about how to break the issue down into a series of small, manageable tasks.
6. Must Document your plan in a **new scratchpad** under <project_root>/plan:
   - Include the issue name in the filename.
   - Include a link to the issue in the scratchpad.

Ask user for review and approval before move forward.
---

## 🔹 CREATE
- Create a new branch for the issue
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
Open a PR and request to review.

Remember to use the GITHUB CLI (`gh`) for all github related issues.
