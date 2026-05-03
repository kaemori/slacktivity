import requests

SLACK_API = "https://slack.com/api"


def get_user_data(slack_id: str, token: str) -> dict:
    headers = {"Authorization": f"Bearer {token}"}

    profile_res = requests.get(
        f"{SLACK_API}/users.profile.get",
        headers=headers,
        params={"user": slack_id},
    )
    presence_res = requests.get(
        f"{SLACK_API}/users.getPresence",
        headers=headers,
        params={"user": slack_id},
    )

    profile_data = profile_res.json()
    presence_data = presence_res.json()

    if not profile_data.get("ok"):
        raise ValueError(f"slack profile error: {profile_data.get('error', 'unknown')}")
    if not presence_data.get("ok"):
        raise ValueError(
            f"slack presence error: {presence_data.get('error', 'unknown')}"
        )

    profile = profile_data["profile"]
    presence = presence_data.get("presence", "away")

    return {
        "slack_user": {
            "id": slack_id,
            "real_name": profile.get("real_name", ""),
            "display_name": profile.get("display_name", ""),
            "title": profile.get("title", ""),
            "pronouns": profile.get("pronouns", ""),
            "avatar_url": profile.get("image_192", ""),
        },
        "slack_status": presence,
        "status_emoji": profile.get("status_emoji", ""),
        "status_text": profile.get("status_text", ""),
        "huddle_state": profile.get("huddle_state", "default_unset"),
    }


"""does anyone even read these..? weh,,,,,,,,,,,,"""
