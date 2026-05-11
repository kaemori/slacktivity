# Slack Integration Guide

This guide explains how to integrate and use Slacktivity within a Slack workspace.

## Getting Started

To begin using Slacktivity, users must first link their Slack account by executing the following command in any channel:

`/slacktivity-register`

Users will be prompted to authorize the application, allowing Slacktivity to access the necessary presence and status information to generate their activity card.

## Slash Commands

| Command                     | Description                                                                          |
| :-------------------------- | :----------------------------------------------------------------------------------- |
| `/slacktivity-help`         | Displays a list of available commands and usage instructions.                        |
| `/slacktivity-register`     | Initiates the account linking process (opens Slack OAuth register button).           |
| `/slacktivity-unregister`   | Removes the user's token and unlinks the account.                                    |
| `/slacktivity-preview`      | Generates a preview of the current activity card with links to SVG and PNG versions. |
| `/slacktivity-create`       | Opens a configuration modal to customize the card's appearance.                      |
| `/slacktivity-badge-add`    | Opens a modal to add a custom emoji badge to your card (limited to 2 badges).        |
| `/slacktivity-badge-remove` | Opens an interface to remove an existing badge from your card.                       |
| `/slacktivity-badge-token`  | Generates a secret API token for programmatic badge management (returned in DM).     |

## Card Customization

The `/slacktivity-create` command provides a modal interface to adjust the following settings:

- **Theme**: Choose between `dark` and `light` modes.
- **Background**: Define a custom CSS color or gradient for the card background. Hex colors must include the leading `#` (e.g. `#1a1a2e`). For gradients, use `linear-gradient(...)` and include `#` in hex color stops (e.g. `linear-gradient(135deg,#1a1a2e,#16213e)`). `rgb(...)` values remain accepted without `#`.
- **Border Radius**: Adjust the curvature of the card's corners.
- **Idle Message**: Customize the text displayed when the user is inactive.
- **Status Visibility**: Toggle the visibility of the Slack status emoji and text.

## Sharing Cards

Users can share their generated cards directly into a channel using the options provided in the `/slacktivity-preview` and `/slacktivity-create` commands.
