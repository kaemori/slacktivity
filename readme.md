# Slacktivity

[Slacktivity](https://slacktivity.hackclub.app) is a web service that generates dynamic activity cards based on a user's Slack presence and status!

All this, powered by Python.

> **Inspiration?**
> I use lanyard-profile-readme (cnrad) on my own website to show my Discord activity, but I wanted something similar for Slack. Since there wasn't already an existing solution, I decided to create Slacktivity!

## Usage

On Slack, you can run `/slacktivity-help` for a list of commands you can run. To get started, try running `/slacktivity-register` then `/slacktivity-preview` to see your activity card!

Via API, you will first have to visit `https://slacktivity.hackclub.app/signup` to register manually, then you can use the [API](docs/usage.md) to get your activity data and display it on your own website or application.

Either way, you should have recieved a link like this: https://slacktivity.hackclub.app/user/U0A5TC1FLHL. This link should be embeddable into any website. For example, include the following in your README.md, replacing `<id>` with your Slack user ID:

```markdown
![Slacktivity](https://slacktivity.hackclub.app/user/<id>)
```

It should look like the image below:

![Slacktivity](https://slacktivity.hackclub.app/user/U0A5TC1FLHL)

## Documentation

For detailed information on how to use the Slacktivity API and integrate it with your Slack workspace, please refer to the [API Documentation](docs/usage.md) and the [Slack Integration Guide](docs/slack.md). You may also head to [the website](https://slacktivity.hackclub.app) to see how to get started!

---

Copyright (c) 2026 Kaemori Yozzan ("Mandaesis"). All rights reserved, licensed under the MIT License.

Made w/ <3 by Kaemori & the Icarus Alliance
