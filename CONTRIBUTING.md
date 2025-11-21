# Contributing to Spark GCP Automation

## 🌿 Branching Strategy

We use a simplified Git Flow:

- `main` - Production-ready code
- `lontsi` - Lontsi's development branch
- `lado` - Lado's development branch

## 📝 Commit Convention

We follow [Conventional Commits](https://www.conventionalcommits.org/):
```
<type>(<scope>): <description>

[optional body]
[optional footer]
```

### Types

- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation only
- `style`: Code style (formatting, semicolons, etc.)
- `refactor`: Code refactoring
- `test`: Adding tests
- `chore`: Maintenance tasks
- `ci`: CI/CD changes

### Examples
```bash
feat(terraform): add VPC module for networking
fix(ansible): correct spark master configuration
docs(readme): update installation instructions
ci(github): add terraform validation workflow
```

## 🔄 Pull Request Process

1. Create a feature branch from your dev branch:
```bash
   git checkout lontsi  # ou lado
   git pull origin lontsi
   git checkout -b feat/your-feature-name
```

2. Make your changes and commit:
```bash
   git add .
   git commit -m "feat(scope): description"
```

3. Push to GitHub:
```bash
   git push origin feat/your-feature-name
```

4. Create a Pull Request on GitHub
5. Wait for CI/CD checks to pass
6. Request review from team member
7. Merge after approval

## ✅ Code Quality

- Run `terraform fmt` before committing Terraform code
- Run `ansible-lint` before committing Ansible playbooks
- Ensure all CI/CD checks pass
- Add tests for new features

## 🐛 Reporting Bugs

Use GitHub Issues with the bug report template.

## 💡 Suggesting Features

Use GitHub Issues with the feature request template.