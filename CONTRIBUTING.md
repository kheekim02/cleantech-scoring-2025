# Contributing to CleanTech Open 2025 Diligence Engine

Welcome! We are excited to collaborate with you on the CleanTech Open 2025 Diligence Engine. Please review these guidelines before submitting issues or pull requests.

---

## 1. Getting Started

### Prerequisites
- **Node.js**: v18.x or v20.x
- **Python**: 3.10, 3.11, or 3.12
- **Git**

### Local Environment Setup

1. **Clone the repository**:
   ```bash
   git clone https://github.com/kheekim02/cleantech-scoring-2025.git
   cd cleantech-scoring-2025
   ```

2. **Configure Python Virtual Environment**:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install --upgrade pip
   pip install -r requirements.txt
   ```

3. **Install Node Dependencies**:
   ```bash
   npm install
   ```

4. **Set Up Environment Variables**:
   Copy the provided `.env.example` template:
   ```bash
   cp .env.example .env
   ```
   Fill in your Supabase connection strings and API credentials.

---

## 2. Running Locally

### Development Server
To launch the scoring portal and admin dashboard locally:
```bash
npx serve site -p 3000
```
- **Scorer Portal**: [http://localhost:3000/index.html](http://localhost:3000/index.html)
- **Admin Dashboard**: [http://localhost:3000/admin.html](http://localhost:3000/admin.html)

---

## 3. Running Tests

Before committing code or submitting a pull request, ensure the test suite passes cleanly:

```bash
# Run full automated test suite
pytest

# Run tests with verbose output
pytest -v

# Run a specific test file
pytest tests/test_audit_metrics.py
```

---

## 4. Git Hygiene & Branch Conventions

### Branch Strategy
- Work on descriptive feature branches off `main`:
  ```bash
  git checkout -b feat/your-feature-name
  # or
  git checkout -b fix/issue-description
  ```

### Conventional Commit Standard
All commit messages must adhere to the Conventional Commits specification:
```text
<type>(<scope>): <imperative summary>

[optional body explaining why this change was made]
```

- **Types**:
  - `feat`: A new user-facing capability or endpoint
  - `fix`: A bug fix or patch
  - `refactor`: Code reorganization without functional behavior change
  - `test`: Adding or updating test coverage
  - `docs`: Documentation updates
  - `chore`: Dependency updates, tooling, or build configuration

### Pre-Commit Checklist
- [ ] Code builds and runs cleanly.
- [ ] `pytest` passes with 0 failures or errors.
- [ ] No temporary debug statements (`print()`, `console.log`, `debugger`, commented-out blocks) left behind.
- [ ] No credentials or secrets committed in code or configuration.
