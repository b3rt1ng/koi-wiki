# Known Issues

This page documents known limitations and issues in Koi.

## Linux / PTY Upgrade

### TUI applications (vim, nano, etc.) render incorrectly

Terminal User Interfaces like `vim`, `nano`, `htop`, etc. display with completely broken rendering - flickering, missing UI elements, mangled text. **However**, the application technically works fine: you can navigate, edit, and execute commands blindly if you know the keybindings. The issue is purely visual (ANSI escape sequences, terminal size signaling, or cursor control not being handled correctly by Koi's PTY layer).

**Workaround:** Use line-based editors (`sed`, `ed`) or open the file in a regular shell editor (`cat > file`, then paste), or navigate blind if you're feeling brave 😄
