# Troubleshooting Commands

## Command Not Appearing

- For standalone files: check the file is in the correct `commands/` directory (`~/.config/opencode/commands/` or `.opencode/commands/`)
- For inline JSON: check JSON syntax in opencode.json
- Verify the command is under the `commands` key (JSON) or in a valid `.md` file
- Restart OpenCode after adding commands

## Command Fails

- Check agent has required tool permissions
- Verify prompt syntax is correct
- Test with simple arguments first
- Check agent logs for errors

## Command Too Slow

- Consider using a faster model
- Reduce scope of the command
- Break into multiple smaller commands
- Use `plan` agent for analysis-only tasks
