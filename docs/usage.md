# Slacktivity API Documentation

This documentation provides details on how to interact with the Slacktivity API to retrieve user data and render activity cards.

## General Routes

These endpoints handle the web interface and the authentication process.

### Landing Page

`GET /`

The main entry point of the application, providing a user interface for the service.

### Registration Initiation

`GET /signup`

Redirects the user to the Slack OAuth authorization page to begin the account linking process. Users may also start registration from Slack using the `/slacktivity-register` slash command which opens the same OAuth flow. Authentication is handled via Slack's OAuth flow and user tokens are stored encrypted on the server.

### OAuth Callback

`GET /oauth/callback`

Handles the redirection from Slack after authorization. This endpoint exchanges the authorization code for an access token and stores it securely in the database. This endpoint is not intended for direct user interaction and should only be accessed by Slack during the OAuth process.

## API Endpoints

### Retrieve User Data

`GET /api/user/<slack_id>`

Returns the structured data used for rendering the user's activity card. Requires that the user has previously registered (via `/slacktivity-register` or `GET /signup`).

**Response:**

- `success` (boolean): Indicates if the request was successful.
- `data` (object): The user's profile and activity data (present on success).
- `error` (string): An error message explaining the failure (present on failure).

**Example Request:**
`GET /api/user/U12345678`

**Example Response (trimmed):**

```json
{
    "success": true,
    "data": {
        "huddle_state": "default_unset",
        "slack_status": "active",
        "slack_user": {
            "id": "U12345678",
            "display_name": "yourname",
            "real_name": "Full Name",
            "avatar_url": "https://...png"
        },
        "status_emoji": ":smile:",
        "status_text": "working on stuff"
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
| `scale`        | integer | `4`                     | The resolution scale factor (applicable only to `png` format). The server parses this as an integer and enforces a minimum value of `1`.                                                                                                                                     |

**Notes:**

- `format=png` will return a PNG; otherwise the endpoint returns an SVG by default.
- `scale` is parsed as an integer (default `4`) and currently must be at least `1` when requesting PNG output.
- Badge management endpoints exist under the `/api/user/<slack_id>/badge` path and require an API token provided via the `X-Api-Token` header; a token can be generated by the `/slacktivity-badge-token` slash command.

**Example Request:**
`/user/U12345678?theme=dark&bg=linear-gradient(45deg,%23000000,%23333333)&borderRadius=24px&idleMessage=sillying+around+:3`
