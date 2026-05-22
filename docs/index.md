---
title: Koi Wiki
description: Official Koi reverse shell handler documentation
image: assets/images/logo.png
---

# Getting Started

## Installation

I made it easy to download and stay up to date thanks to pipx 🙏

### For general users

```bash
pipx install git+https://github.com/b3rt1ng/Koi
```
This will use the github repo as the source of your tool. If any update is done there, you will be able to get the latest version.

### For developers

```bash
git clone https://github.com/b3rt1ng/koi
cd koi
pipx install --editable .
```

This way, you will be able to edit your tool live, allowing you to make your own modules.

!!! note
    there is also the `pipx install koi-handler` command possible but maintained through PyPI, I don't like it, so I update it but less frequently than the GitHub repo. Use GitHub.