# Slacktivity API Documentation

This documentation provides details on how to interact with the Slacktivity API to retrieve user data and render activity cards.

## General Routes

These endpoints handle the web interface and the authentication process.

### Landing Page

`GET /`

The main entry point of the application, providing a user interface for the service.

### Registration Initiation

`GET /signup`

Redirects the user to the Slack OAuth authorization page to begin the account linking process. There is currently no method to manually submit a user's API key directly to the service, as all authentication is handled through Slack's OAuth flow for security reasons.

### OAuth Callback

`GET /oauth/callback`

Handles the redirection from Slack after authorization. This endpoint exchanges the authorization code for an access token and stores it securely in the database. This endpoint is not intended for direct user interaction and should only be accessed by Slack during the OAuth process.

## API Endpoints

### Retrieve User Data

`GET /api/user/<slack_id>`

Returns the raw data used for rendering the user's activity card.

**Response:**

- `success` (boolean): Indicates if the request was successful.
- `data` (object): The user's profile and activity data (provided if `success` is true).
- `error` (string): An error message explaining the failure (provided if `success` is false).

**Example Request:**
`/api/user/U12345678`

**Example Response:**

```json
{
    "success": true,
    "data": {
        "huddle_state": "default_unset",
        "slack_status": "active",
        "slack_user": {
            "avatar_url": "https://avatars.slack-edge.com/2026-04-05/10876566843744_48dfc29582816cbae91a_192.png",
            "display_name": "wyvbxnr",
            "id": "U098A2QC2LF",
            "pronouns": "professional ultrasound cannon",
            "real_name": "jane mandaesis",
            "title": "playing the musician, magician and the fool"
        },
        "status_emoji": "",
        "status_text": ""
    }
}
```

### Delete User Token

`POST /api/delete/<slack_id>`

Removes the user's authentication token from the database. The user will need to re-register to generate a new card.

**Response:**

- `success` (boolean): Indicates if the token was successfully deleted.
- `message` (string): A confirmation or error message.

**Example Request:**
`POST /api/delete/U12345678`

**Example Response:**

```json
{
    "success": true,
    "message": "deleted token for user U12345678"
}
```

---

## Card Rendering

Activity cards can be generated via the following endpoint:

`GET /user/<slack_id>`

### Query Parameters

The following parameters can be used to customize the appearance of the rendered card:

| Parameter      | Type    | Default                 | Description                                                                                                                                                                                                                                                                  |
| :------------- | :------ | :---------------------- | :--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `theme`        | string  | `dark`                  | The visual theme of the card (`dark` or `light`).                                                                                                                                                                                                                            |
| `bg`           | string  | `none`                  | A CSS-compatible background. Hex colors must include the leading `#` (e.g. `#1a1a2e`). Gradients are supported via `linear-gradient(...)` — color stops using hex must include `#` (e.g. `linear-gradient(45deg, #ff69b4, #0000ff)`). `rgb(...)` is still accepted (no `#`). |
| `borderRadius` | string  | `12px`                  | The CSS border-radius value for the card's corners.                                                                                                                                                                                                                          |
| `idleMessage`  | string  | `not doing anything rn` | The text displayed when the user is idle or away.                                                                                                                                                                                                                            |
| `hideStatus`   | string  | `false`                 | Set to `true` to hide the Slack status emoji and text.                                                                                                                                                                                                                       |
| `format`       | string  | `svg`                   | The output format of the card (`svg` or `png`).                                                                                                                                                                                                                              |
| `scale`        | integer | `4`                     | The resolution scale factor (applicable only to `png` format, clamped from 0.2 to 10).                                                                                                                                                                                       |

**Example Request:**
`/user/U098A2QC2LF?theme=dark&bg=linear-gradient(45deg,%23000000,%23333333)&borderRadius=24px&idleMessage=sillying+around+:3`
